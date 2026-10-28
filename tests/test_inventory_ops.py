"""
Tests for er_save_manager.parser.inventory_ops.

A gaitem insert shifts 13 tracked offsets by the same amount; missing one
corrupts the save. Test item IDs (88880000+) collide with nothing in the
fixture's inventory: _find_gaitem_by_item matches weapons by
base_id // 10000 * 10000.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from er_save_manager.fixes.checksum import check_slot_checksum
from er_save_manager.parser import load_save
from er_save_manager.parser.er_types import Gaitem
from er_save_manager.parser.inventory_ops import (
    UPGRADE_CAP_ASH,
    UPGRADE_CAP_SOMBER,
    UPGRADE_CAP_STANDARD,
    _next_gaitem_handle,
    add_item,
    remove_item,
    set_quantity,
    validate_upgrade,
)
from er_save_manager.parser.slot_rebuild import rebuild_slot_with_map

WEAPON = 88880000
ARMOR = 0x10000000 | 88880000
TALISMAN = 0x20000000 | 88880000
GOODS = 0x40000000 | 88880000
SLOT_SIZE = 0x280000

# add/remove rewrite the inventory arrays and the gaitem map; a gaitem insert
# trims the stale serializer buffer after the parsed data (slot.rest)
_INVENTORY_SECTIONS = {"inventory_held", "inventory_storage_box", "gaitem_map", "rest"}


def _slot_bytes(save) -> bytes:
    start = save.character_slots[0].data_start
    return bytes(save._raw_data[start : start + SLOT_SIZE])


def _assert_only_inventory_changed(save, before: bytes):
    after = _slot_bytes(save)
    for s in rebuild_slot_with_map(save.character_slots[0])[1]:
        if s["name"] not in _INVENTORY_SECTIONS:
            assert before[s["start"] : s["end"]] == after[s["start"] : s["end"]], s[
                "name"
            ]


def _live_gaitems(slot) -> int:
    return sum(1 for g in slot.gaitem_map if g.gaitem_handle not in (0, 0xFFFFFFFF))


def test_validate_upgrade():
    assert validate_upgrade(UPGRADE_CAP_STANDARD, "standard") == UPGRADE_CAP_STANDARD
    assert validate_upgrade(UPGRADE_CAP_SOMBER, "somber") == UPGRADE_CAP_SOMBER
    assert validate_upgrade(UPGRADE_CAP_ASH, "ash") == UPGRADE_CAP_ASH
    assert validate_upgrade(15, "standard", convergence=True) == 15
    assert validate_upgrade(15, "somber", convergence=True) == 15
    for args in (
        (UPGRADE_CAP_STANDARD + 1, "standard"),
        (-1, "standard"),
        (1, "nonsense"),
    ):
        with pytest.raises(ValueError):
            validate_upgrade(*args)
    with pytest.raises(ValueError):
        validate_upgrade(20, "standard", convergence=True)


def test_next_gaitem_handle():
    def slot(handles, size=0x1400):
        gaitem_map = [Gaitem() for _ in range(size)]
        for g, h in zip(gaitem_map, handles, strict=False):
            g.gaitem_handle = h
        return SimpleNamespace(gaitem_map=gaitem_map)

    # Index past the map wraps and bumps the generation
    assert (
        _next_gaitem_handle(slot([0x90811234, 0x808113FF, 0xC0800000]), 0x80000000)
        == 0x80820001
    )
    # Used indices are skipped
    assert (
        _next_gaitem_handle(slot([0x80800010, 0x90800011, 0xC07F0012]), 0x90000000)
        == 0x90800013
    )
    # 0xFF wrapped to 0x80, so 0x80 is the newest generation
    assert (
        _next_gaitem_handle(slot([0x80FE1000, 0x80FF1200, 0x80800005]), 0xC0000000)
        == 0xC0800006
    )
    with pytest.raises(ValueError):
        _next_gaitem_handle(
            slot([0x80800000 | i for i in range(8)], size=8), 0x80000000
        )


def test_add_goods_and_talismans(sanitized_save):
    slot = sanitized_save.character_slots[0]
    gaitems = _live_gaitems(slot)
    count = slot.inventory_held.common_item_count

    # Goods and talismans use direct handles, never gaitem entries
    assert (
        add_item(sanitized_save, 0, GOODS, quantity=5, location="held")["quantity"] == 5
    )
    assert _live_gaitems(slot) == gaitems
    assert slot.inventory_held.common_item_count == count + 1
    with pytest.raises(ValueError):
        add_item(sanitized_save, 0, GOODS, quantity=1, location="held")
    add_item(sanitized_save, 0, TALISMAN, quantity=1, location="held")
    add_item(sanitized_save, 0, TALISMAN, quantity=1, location="held")
    with pytest.raises(ValueError):
        add_item(sanitized_save, 0, 0x30000000 | 1, quantity=1)


def test_add_weapon_counters_follow_entry_positions(sanitized_save):
    held = sanitized_save.character_slots[0].inventory_held
    top = len(held.key_items) + len(held.common_items) - 1
    # Drifted state from older versions: count one too high, counter past
    # the last valid index
    held.common_item_count += 1
    held.equip_index_counter = top + 90

    result = add_item(sanitized_save, 0, WEAPON, quantity=1, location="held", upgrade=5)
    slot = sanitized_save.character_slots[0]
    gaitem = slot.gaitem_map[result["gaitem_slot"]]
    assert gaitem.gaitem_handle == result["gaitem_handle"]
    assert gaitem.item_id % 100 == 5
    assert held.common_item_count == sum(
        1 for it in held.common_items if it.gaitem_handle
    )
    assert held.equip_index_counter == top

    held.equip_index_counter = 0
    result = add_item(sanitized_save, 0, WEAPON + 10000, quantity=1, location="held")
    assert held.equip_index_counter == len(held.key_items) + result["inventory_slot"]


def test_bulk_add_keeps_handle_indices_in_range_and_unique(sanitized_save):
    for k in range(150):
        item = (ARMOR if k % 2 else WEAPON) + k * 10000
        add_item(sanitized_save, 0, item, quantity=1, location="held")
    slot = sanitized_save.character_slots[0]
    indices = [g.gaitem_handle & 0xFFFF for g in slot.gaitem_map if g.gaitem_handle]
    assert max(indices) < len(slot.gaitem_map)
    assert len(set(indices)) == len(indices)


def test_add_to_full_inventory_changes_nothing(sanitized_save):
    slot = sanitized_save.character_slots[0]
    for inv in (slot.inventory_held, slot.inventory_storage_box):
        for it in inv.common_items:
            if it.gaitem_handle == 0:
                it.gaitem_handle = GOODS
    before_map = [g.gaitem_handle for g in slot.gaitem_map]
    before_raw = bytes(sanitized_save._raw_data)
    with pytest.raises(ValueError):
        add_item(
            sanitized_save,
            0,
            WEAPON,
            quantity=1,
            location="held",
            gem_full_id=0x80000000 | 10000,
        )
    assert [g.gaitem_handle for g in slot.gaitem_map] == before_map
    assert bytes(sanitized_save._raw_data) == before_raw


def test_add_then_remove_touches_only_inventory_sections(sanitized_save):
    before = _slot_bytes(sanitized_save)
    for item in (WEAPON, ARMOR):
        result = add_item(sanitized_save, 0, item, quantity=1, location="held")
        remove_item(sanitized_save, 0, item, location=result["location"])
        slot = sanitized_save.character_slots[0]
        assert slot.gaitem_map[result["gaitem_slot"]].gaitem_handle == 0
    _assert_only_inventory_changed(sanitized_save, before)


def test_offsets_hold_after_reload(sanitized_save_copy):
    save = load_save(str(sanitized_save_copy))
    slot = save.character_slots[0]
    before = (
        slot.world_area_weather.area_id,
        slot.world_area_weather.weather_type,
        slot.dlc.preorder_the_ring,
        slot.dlc.shadow_of_erdtree,
        slot.steam_id,
        bytes(slot.event_flags[:200]),
    )
    add_item(save, 0, WEAPON, quantity=1, location="held", upgrade=3)
    save.recalculate_checksums()
    save.to_file(str(sanitized_save_copy))

    reloaded = load_save(str(sanitized_save_copy))
    r = reloaded.character_slots[0]
    assert (
        r.world_area_weather.area_id,
        r.world_area_weather.weather_type,
        r.dlc.preorder_the_ring,
        r.dlc.shadow_of_erdtree,
        r.steam_id,
        bytes(r.event_flags[:200]),
    ) == before
    assert check_slot_checksum(reloaded, 0)[0]


def test_remove_and_set_quantity(sanitized_save):
    with pytest.raises(ValueError):
        remove_item(sanitized_save, 0, GOODS, location="held")
    with pytest.raises(ValueError):
        set_quantity(sanitized_save, 0, GOODS, quantity=5, location="held")

    add_item(sanitized_save, 0, GOODS, quantity=1, location="held")
    before = _slot_bytes(sanitized_save)
    result = set_quantity(sanitized_save, 0, GOODS, quantity=99, location="held")
    assert (result["old_quantity"], result["new_quantity"]) == (1, 99)
    # set_quantity edits the entry in place: no gaitem change, no offset shift
    _assert_only_inventory_changed(sanitized_save, before)
    with pytest.raises(ValueError):
        set_quantity(sanitized_save, 0, GOODS, quantity=0, location="held")

    count = sanitized_save.character_slots[0].inventory_held.common_item_count
    remove_item(sanitized_save, 0, GOODS, location="held")
    assert (
        sanitized_save.character_slots[0].inventory_held.common_item_count == count - 1
    )
