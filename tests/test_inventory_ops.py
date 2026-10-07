"""
Tests for er_save_manager.parser.inventory_ops.

 13 tracked offsets must all be updated by the same net_shift
(player_game_data_offset, inventory_held_offset, inventory_storage_offset,
gestures_offset, horse_offset, blood_stain_offset, event_flags_offset,
coordinates_offset, net_man_offset, weather_offset, time_offset,
steamid_offset, dlc_offset). Missing even one silently corrupts the save.

Test item IDs use a distinctive, clearly-synthetic base
(0x0549_xxxx-range values via 88880000+) to avoid colliding with real
items already present in the fixture's heavily-populated inventory -
_find_gaitem_by_item matches weapons by base_id // 10000 * 10000, so a
common low ID like a starting dagger could otherwise collide with a
real pre-existing entry in the fixture.
"""

from __future__ import annotations

import pytest

from er_save_manager.parser.inventory_ops import (
    UPGRADE_CAP_ASH,
    UPGRADE_CAP_SOMBER,
    UPGRADE_CAP_STANDARD,
    add_item,
    remove_item,
    set_quantity,
    validate_upgrade,
)
from er_save_manager.parser.slot_rebuild import rebuild_slot_with_map

_CAT_WEAPON = 0x00000000
_CAT_ARMOR = 0x10000000
_CAT_TALISMAN = 0x20000000
_CAT_GOODS = 0x40000000

TEST_WEAPON_ID = _CAT_WEAPON | 88880000
TEST_ARMOR_ID = _CAT_ARMOR | 88880000
TEST_TALISMAN_ID = _CAT_TALISMAN | 88880000
TEST_GOODS_ID = _CAT_GOODS | 88880000

# Sections that legitimately change on any add/remove: inventory arrays
# themselves, and the gaitem map (new entry, or a Gaitem() default reset
# on remove, which uses an item_id of 0 rather than the original empty
# slot's 0xFFFFFFFF sentinel - both mean "empty" via gaitem_handle == 0,
# so this is a cosmetic difference, not a correctness issue).
_INVENTORY_SECTION_NAMES = {"inventory_held", "inventory_storage_box", "gaitem_map"}


def _first_active_slot(save):
    for i, slot in enumerate(save.character_slots):
        if not slot.is_empty():
            return i
    raise AssertionError("fixture save has no active character slots")


def _slot_with_trailing_budget(save, min_bytes=64):
    """
    Find an active slot with at least min_bytes of genuine trailing zero
    padding at the slot end.
    """
    slot_size = 0x280000
    for i, slot in enumerate(save.character_slots):
        if slot.is_empty():
            continue
        end = slot.data_start + slot_size
        trailing = 0
        for j in range(end - 1, end - min_bytes - 1, -1):
            if save._raw_data[j] == 0:
                trailing += 1
            else:
                break
        if trailing >= min_bytes:
            return i
    raise AssertionError(
        f"no active slot in fixture has >= {min_bytes} bytes of trailing budget"
    )


def _assert_only_inventory_sections_changed(slot, before: bytes, after: bytes):
    _, sections = rebuild_slot_with_map(slot)
    protected_ranges = [
        (s["start"], s["end"])
        for s in sections
        if s["name"] not in _INVENTORY_SECTION_NAMES
    ]
    for start, end in protected_ranges:
        assert before[start:end] == after[start:end], (
            f"unexpected change outside inventory sections in range [{start}:{end}]"
        )


# ---------------------------------------------------------------------------
# validate_upgrade (pure logic, no save needed)
# ---------------------------------------------------------------------------


def test_validate_upgrade_accepts_cap_values():
    assert validate_upgrade(UPGRADE_CAP_STANDARD, "standard") == UPGRADE_CAP_STANDARD
    assert validate_upgrade(UPGRADE_CAP_SOMBER, "somber") == UPGRADE_CAP_SOMBER
    assert validate_upgrade(UPGRADE_CAP_ASH, "ash") == UPGRADE_CAP_ASH


def test_validate_upgrade_rejects_above_cap():
    with pytest.raises(ValueError):
        validate_upgrade(UPGRADE_CAP_STANDARD + 1, "standard")


def test_validate_upgrade_rejects_negative():
    with pytest.raises(ValueError):
        validate_upgrade(-1, "standard")


def test_validate_upgrade_convergence_caps_standard_and_somber_at_15():
    assert validate_upgrade(15, "standard", convergence=True) == 15
    assert validate_upgrade(15, "somber", convergence=True) == 15
    with pytest.raises(ValueError):
        validate_upgrade(20, "standard", convergence=True)


def test_validate_upgrade_rejects_unknown_reinforcement():
    with pytest.raises(ValueError):
        validate_upgrade(1, "nonsense")


# ---------------------------------------------------------------------------
# add_item
# ---------------------------------------------------------------------------


def test_add_item_goods_uses_direct_handle_no_gaitem(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    gaitem_count_before = len(
        [g for g in slot.gaitem_map if g.gaitem_handle not in (0, 0xFFFFFFFF)]
    )

    result = add_item(sanitized_save, i, TEST_GOODS_ID, quantity=5, location="held")

    assert result["quantity"] == 5
    gaitem_count_after = len(
        [g for g in slot.gaitem_map if g.gaitem_handle not in (0, 0xFFFFFFFF)]
    )
    assert gaitem_count_after == gaitem_count_before  # no gaitem entry created


def test_add_item_weapon_creates_gaitem_entry(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    result = add_item(
        sanitized_save, i, TEST_WEAPON_ID, quantity=1, location="held", upgrade=5
    )

    slot = sanitized_save.character_slots[i]  # re-read: offsets may have shifted
    gaitem = slot.gaitem_map[result["gaitem_slot"]]
    assert gaitem.gaitem_handle == result["gaitem_handle"]
    assert gaitem.item_id % 100 == 5  # upgrade encoded in item_id


def test_add_item_rejects_unknown_category(sanitized_save):
    i = _first_active_slot(sanitized_save)
    with pytest.raises(ValueError):
        add_item(sanitized_save, i, 0x30000000 | 1, quantity=1)


def test_add_item_rejects_duplicate_non_talisman(sanitized_save):
    i = _first_active_slot(sanitized_save)
    add_item(sanitized_save, i, TEST_GOODS_ID, quantity=1, location="held")
    with pytest.raises(ValueError):
        add_item(sanitized_save, i, TEST_GOODS_ID, quantity=1, location="held")


def test_add_item_allows_duplicate_talisman(sanitized_save):
    i = _first_active_slot(sanitized_save)
    add_item(sanitized_save, i, TEST_TALISMAN_ID, quantity=1, location="held")
    result = add_item(sanitized_save, i, TEST_TALISMAN_ID, quantity=1, location="held")
    assert result["quantity"] == 1


def test_add_item_increments_common_item_count(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    before = slot.inventory_held.common_item_count

    add_item(sanitized_save, i, TEST_GOODS_ID, quantity=1, location="held")

    slot = sanitized_save.character_slots[i]
    assert slot.inventory_held.common_item_count == before + 1


# ---------------------------------------------------------------------------
# gaitem handle allocation
# ---------------------------------------------------------------------------


def _map_with_handles(handles, size=0x1400):
    from types import SimpleNamespace

    from er_save_manager.parser.er_types import Gaitem

    gaitem_map = []
    for h in handles:
        g = Gaitem()
        g.gaitem_handle = h
        gaitem_map.append(g)
    while len(gaitem_map) < size:
        gaitem_map.append(Gaitem())
    return SimpleNamespace(gaitem_map=gaitem_map)


def test_next_gaitem_handle_wraps_index_and_bumps_generation():
    from er_save_manager.parser.inventory_ops import _next_gaitem_handle

    slot = _map_with_handles([0x90811234, 0x808113FF, 0xC0800000])
    assert _next_gaitem_handle(slot, 0x80000000) == 0x80820001


def test_next_gaitem_handle_skips_used_indices():
    from er_save_manager.parser.inventory_ops import _next_gaitem_handle

    slot = _map_with_handles([0x80800010, 0x90800011, 0xC07F0012])
    assert _next_gaitem_handle(slot, 0x90000000) == 0x90800013


def test_next_gaitem_handle_newest_generation_follows_ring_wrap():
    from er_save_manager.parser.inventory_ops import _next_gaitem_handle

    # 0xFF wrapped to 0x80, so 0x80 is the newest generation.
    slot = _map_with_handles([0x80FE1000, 0x80FF1200, 0x80800005])
    assert _next_gaitem_handle(slot, 0xC0000000) == 0xC0800006


def test_next_gaitem_handle_raises_when_every_index_is_used():
    from er_save_manager.parser.inventory_ops import _next_gaitem_handle

    slot = _map_with_handles([0x80800000 | i for i in range(8)], size=8)
    with pytest.raises(ValueError):
        _next_gaitem_handle(slot, 0x80000000)


def test_bulk_add_keeps_handle_indices_in_range_and_unique(sanitized_save):
    i = _first_active_slot(sanitized_save)
    for k in range(150):
        item = (TEST_ARMOR_ID if k % 2 else TEST_WEAPON_ID) + k * 10000
        add_item(sanitized_save, i, item, quantity=1, location="held")

    slot = sanitized_save.character_slots[i]
    indices = [g.gaitem_handle & 0xFFFF for g in slot.gaitem_map if g.gaitem_handle]
    assert max(indices) < len(slot.gaitem_map)
    assert len(set(indices)) == len(indices)


def test_add_item_full_inventory_leaves_gaitem_map_untouched(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    for inv in (slot.inventory_held, slot.inventory_storage_box):
        for it in inv.common_items:
            if it.gaitem_handle == 0:
                it.gaitem_handle = TEST_GOODS_ID
    before_map = [g.gaitem_handle for g in slot.gaitem_map]
    before_raw = bytes(sanitized_save._raw_data)

    with pytest.raises(ValueError):
        add_item(
            sanitized_save,
            i,
            TEST_WEAPON_ID,
            quantity=1,
            location="held",
            gem_full_id=0x80000000 | 10000,
        )

    assert [g.gaitem_handle for g in slot.gaitem_map] == before_map
    assert bytes(sanitized_save._raw_data) == before_raw


def test_add_item_counters_follow_entry_positions(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    held = slot.inventory_held
    top = len(held.key_items) + len(held.common_items) - 1
    # Drifted state from older versions: count one too high, counter past
    # the last valid index.
    held.common_item_count += 1
    held.equip_index_counter = top + 90

    result = add_item(sanitized_save, i, TEST_WEAPON_ID, quantity=1, location="held")

    assert result["location"] == "held"
    assert held.common_item_count == sum(
        1 for it in held.common_items if it.gaitem_handle != 0
    )
    assert held.equip_index_counter == top


def test_add_item_raises_counter_to_new_entry_index(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    held = slot.inventory_held
    held.equip_index_counter = 0

    result = add_item(sanitized_save, i, TEST_WEAPON_ID, quantity=1, location="held")

    assert held.equip_index_counter == len(held.key_items) + result["inventory_slot"]


# ---------------------------------------------------------------------------
# The critical offset-shift regression test
# ---------------------------------------------------------------------------


def test_add_then_remove_weapon_touches_only_inventory_sections(sanitized_save):
    """
    Checks the 13-offset shift math: adding a weapon
    grows the gaitem map, shifting everything after it; removing it
    shrinks it back. Everything outside inventory_held/
    inventory_storage_box/gaitem_map must be byte-identical before and
    after, regardless of which slot ends up holding the item (held or
    storage fallback).
    """
    i = _slot_with_trailing_budget(sanitized_save)
    slot = sanitized_save.character_slots[i]
    before = bytes(
        sanitized_save._raw_data[slot.data_start : slot.data_start + 0x280000]
    )

    result = add_item(
        sanitized_save, i, TEST_WEAPON_ID, quantity=1, location="held", upgrade=0
    )
    remove_item(sanitized_save, i, TEST_WEAPON_ID, location=result["location"])

    slot = sanitized_save.character_slots[i]
    after = bytes(
        sanitized_save._raw_data[slot.data_start : slot.data_start + 0x280000]
    )

    _assert_only_inventory_sections_changed(slot, before, after)


def test_add_then_remove_armor_touches_only_inventory_sections(sanitized_save):
    i = _slot_with_trailing_budget(sanitized_save)
    slot = sanitized_save.character_slots[i]
    before = bytes(
        sanitized_save._raw_data[slot.data_start : slot.data_start + 0x280000]
    )

    result = add_item(sanitized_save, i, TEST_ARMOR_ID, quantity=1, location="held")
    remove_item(sanitized_save, i, TEST_ARMOR_ID, location=result["location"])

    slot = sanitized_save.character_slots[i]
    after = bytes(
        sanitized_save._raw_data[slot.data_start : slot.data_start + 0x280000]
    )

    _assert_only_inventory_sections_changed(slot, before, after)


def test_offsets_are_independently_verifiable_after_reload(sanitized_save_copy):
    from er_save_manager.parser import load_save

    save = load_save(str(sanitized_save_copy))
    i = _first_active_slot(save)
    slot = save.character_slots[i]

    before_weather = (
        slot.world_area_weather.area_id,
        slot.world_area_weather.weather_type,
    )
    before_dlc = (slot.dlc.preorder_the_ring, slot.dlc.shadow_of_erdtree)
    before_steamid = slot.steam_id
    before_event_flags_sample = bytes(slot.event_flags[:200])

    add_item(save, i, TEST_WEAPON_ID, quantity=1, location="held", upgrade=3)
    save.recalculate_checksums()
    save.to_file(str(sanitized_save_copy))

    reloaded = load_save(str(sanitized_save_copy))
    rslot = reloaded.character_slots[i]

    assert (
        rslot.world_area_weather.area_id,
        rslot.world_area_weather.weather_type,
    ) == before_weather
    assert (rslot.dlc.preorder_the_ring, rslot.dlc.shadow_of_erdtree) == before_dlc
    assert rslot.steam_id == before_steamid
    assert bytes(rslot.event_flags[:200]) == before_event_flags_sample

    from er_save_manager.fixes.checksum import check_slot_checksum

    valid, _, _ = check_slot_checksum(reloaded, i)
    assert valid is True


# ---------------------------------------------------------------------------
# remove_item
# ---------------------------------------------------------------------------


def test_remove_item_decrements_common_item_count(sanitized_save):
    i = _first_active_slot(sanitized_save)
    add_item(sanitized_save, i, TEST_GOODS_ID, quantity=1, location="held")
    slot = sanitized_save.character_slots[i]
    before = slot.inventory_held.common_item_count

    remove_item(sanitized_save, i, TEST_GOODS_ID, location="held")

    slot = sanitized_save.character_slots[i]
    assert slot.inventory_held.common_item_count == before - 1


def test_remove_item_clears_gaitem_entry(sanitized_save):
    i = _first_active_slot(sanitized_save)
    result = add_item(
        sanitized_save, i, TEST_WEAPON_ID, quantity=1, location="held", upgrade=0
    )
    gaitem_slot = result["gaitem_slot"]

    remove_item(sanitized_save, i, TEST_WEAPON_ID, location=result["location"])

    slot = sanitized_save.character_slots[i]
    assert slot.gaitem_map[gaitem_slot].gaitem_handle == 0


def test_remove_item_raises_when_not_present(sanitized_save):
    i = _first_active_slot(sanitized_save)
    with pytest.raises(ValueError):
        remove_item(sanitized_save, i, TEST_GOODS_ID, location="held")


# ---------------------------------------------------------------------------
# set_quantity
# ---------------------------------------------------------------------------


def test_set_quantity_updates_existing_stack(sanitized_save):
    i = _first_active_slot(sanitized_save)
    add_item(sanitized_save, i, TEST_GOODS_ID, quantity=1, location="held")

    result = set_quantity(
        sanitized_save, i, TEST_GOODS_ID, quantity=99, location="held"
    )

    assert result["old_quantity"] == 1
    assert result["new_quantity"] == 99


def test_set_quantity_rejects_less_than_one(sanitized_save):
    i = _first_active_slot(sanitized_save)
    add_item(sanitized_save, i, TEST_GOODS_ID, quantity=1, location="held")
    with pytest.raises(ValueError):
        set_quantity(sanitized_save, i, TEST_GOODS_ID, quantity=0, location="held")


def test_set_quantity_raises_when_item_not_present(sanitized_save):
    i = _first_active_slot(sanitized_save)
    with pytest.raises(ValueError):
        set_quantity(sanitized_save, i, TEST_GOODS_ID, quantity=5, location="held")


def test_set_quantity_does_not_touch_offsets_or_gaitem_map(sanitized_save):
    """set_quantity only edits an existing InventoryItem in place - it
    must never trigger any gaitem-map growth/shrink or offset shift.
    """
    i = _first_active_slot(sanitized_save)
    add_item(sanitized_save, i, TEST_GOODS_ID, quantity=1, location="held")
    slot = sanitized_save.character_slots[i]
    before = bytes(
        sanitized_save._raw_data[slot.data_start : slot.data_start + 0x280000]
    )

    set_quantity(sanitized_save, i, TEST_GOODS_ID, quantity=50, location="held")

    slot = sanitized_save.character_slots[i]
    after = bytes(
        sanitized_save._raw_data[slot.data_start : slot.data_start + 0x280000]
    )
    _assert_only_inventory_sections_changed(slot, before, after)
