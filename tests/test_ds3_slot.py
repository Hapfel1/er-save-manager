"""
DS3 character slot tests against a real decrypted slot.

The fixture is slot 0 of a DS3 save written by the game (a fresh Knight,
level 9) with its SteamID zeroed. It is stored decrypted, since encrypted
BND4 data does not compress.
"""

from __future__ import annotations

import json
import struct
import zipfile
from pathlib import Path

import pytest

from er_save_manager.games.DS3 import catalog
from er_save_manager.games.DS3.slot import (
    _DIR_PAIRS,
    FISTS_ID,
    GESTURE_COUNT,
    DS3Slot,
    LayoutError,
)

FIXTURE = Path(__file__).parent / "fixtures" / "DS3_slot0_sanitized.bin.zip"
DATA = (
    Path(__file__).parent.parent / "src" / "er_save_manager" / "games" / "DS3" / "data"
)

DAGGER = 0x000F4240
KNIGHT_HELM = 0x11298BE0
LIFE_RING = 0x20004E20
TITANITE_SHARD = 0x400003E8
SMALL_DOLL = 0x400007D5
STANDARD_ARROW = 0x00061A80


@pytest.fixture(scope="module")
def slot_bytes() -> bytes:
    with zipfile.ZipFile(FIXTURE) as zf:
        return zf.read("DS3_slot0_sanitized.bin")


@pytest.fixture
def slot(slot_bytes) -> DS3Slot:
    return DS3Slot(0, bytearray(slot_bytes))


def _real(slot: DS3Slot):
    return [e for e in slot.iter_inventory() if slot.is_real_item(e)]


def _dir(data: bytes):
    return [struct.unpack_from("<II", data, f) for f in _DIR_PAIRS]


def test_parses_cleanly(slot):
    assert slot.layout_error is None
    assert slot.inventory_error is None
    assert slot.flags_error is None
    assert slot.name == "invtest"
    assert slot.ng_plus == 0


def test_level_matches_class_and_stats(slot):
    cls = catalog.starting_classes("vanilla")[slot.starting_class]
    stats = {k: slot.get_stat(k) for k in catalog.STAT_KEYS}
    assert slot.level == cls.level_for(stats)


@pytest.mark.parametrize("source", list(catalog.SOURCES))
def test_starting_classes(source):
    classes = catalog.starting_classes(source)
    assert len({c.name for c in classes}) == len(classes)
    for cls in classes:
        assert cls.level_for(cls.stats) == cls.level
    if source == "vanilla":
        # Every vanilla class sits at attribute sum - 89.
        assert len(classes) == 10
        assert all(sum(c.stats.values()) - c.level == 89 for c in classes)


def test_event_flags_known_state(slot):
    assert slot.get_flag(50)  # playthrough lap 0
    assert slot.get_flag(14000001)  # Cemetery of Ash bonfire
    assert not slot.get_flag(14000800)  # Iudex Gundyr alive


def test_set_flag_changes_one_bit(slot, slot_bytes):
    slot.set_flag(13000800, True)
    assert slot.get_flag(13000800)
    diff = [
        i
        for i, (a, b) in enumerate(zip(slot_bytes, slot.get_raw(), strict=True))
        if a != b
    ]
    assert len(diff) == 1
    slot.set_flag(13000800, False)
    assert bytes(slot.get_raw()) == slot_bytes


def test_gestures(slot):
    unlocked = {g for g in range(GESTURE_COUNT) if slot.gesture_unlocked(g)}
    assert unlocked == {0, 1, 2, 3, 9, 10, 15, 24}
    slot.set_gesture_unlocked(33, True)
    assert slot.gesture_unlocked(33)
    assert slot.layout_error is None


def test_ng_plus_keeps_lap_flags_one_hot(slot):
    slot.ng_plus = 2
    assert slot.ng_plus == 2
    assert [slot.get_flag(50 + n) for n in range(9)] == [n == 2 for n in range(9)]


def test_add_weapon_grows_gaitem_and_shifts_sections(slot, slot_bytes):
    before = _dir(slot_bytes)
    entry = slot.add_item(DAGGER, sort_key=5000000, durability=50)
    after = _dir(slot.get_raw())

    assert len(slot.get_raw()) == len(slot_bytes)
    assert entry.handle & 0xF0000000 == 0x80000000
    # Sections containing the gaitem table grow, later ones move.
    assert after[0][1] == before[0][1] + 52
    assert after[1][1] == before[1][1] + 52
    for (b_off, b_size), (a_off, a_size) in zip(before[2:], after[2:], strict=True):
        assert (a_off, a_size) == (b_off + 52, b_size)
        assert slot_bytes[b_off : b_off + b_size] == bytes(
            slot.get_raw()[a_off : a_off + a_size]
        )

    fresh = DS3Slot(0, bytearray(slot.get_raw()))
    assert fresh.layout_error is None and fresh.inventory_error is None
    assert fresh.name == "invtest"
    for index, gaitem in enumerate(fresh.iter_gaitem()):
        if gaitem.handle:
            assert gaitem.handle & 0xFFFF == index
    handles = {g.handle for g in fresh.iter_gaitem() if g.handle}
    assert entry.handle in handles


def test_add_items_of_every_kind(slot):
    count_before = len(_real(slot))
    slot.add_item(KNIGHT_HELM, sort_key=1013000, durability=380)
    slot.add_item(LIFE_RING, sort_key=20100)
    slot.add_item(STANDARD_ARROW, 50, sort_key=1020000, max_quantity=99)
    shard = slot.add_item(TITANITE_SHARD, 5, sort_key=16010, max_quantity=99)
    again = slot.add_item(TITANITE_SHARD, 3, sort_key=16010, max_quantity=99)
    doll = slot.add_item(SMALL_DOLL, key_item=True, max_quantity=1)

    assert again.offset == shard.offset and again.quantity == 8
    assert doll.is_key
    items = _real(slot)
    assert len(items) == count_before + 5
    common = [e for e in items if not e.is_key]
    # The held count field is two more than the real common items.
    count_field = struct.unpack_from("<I", slot.get_raw(), slot._get_layout().inv)[0]
    assert count_field == len(common) + 2
    assert DS3Slot(0, bytearray(slot.get_raw())).inventory_error is None


def test_storage_and_key_rules(slot):
    stored = slot.add_item(TITANITE_SHARD, 10, sort_key=16010, to_storage=True)
    assert slot.in_storage(stored)
    # Same index rule as held items: 0x80 + position, and the last-index
    # field tracks 0x80 + the highest used position.
    assert stored.index & 0xFFF == 0x80 + stored.position
    storage = slot._get_layout().storage
    last = struct.unpack_from("<I", slot.get_raw(), slot._last_index_off(storage))[0]
    assert last >= 0x80 + stored.position
    with pytest.raises(ValueError):
        slot.add_item(SMALL_DOLL, key_item=True, to_storage=True)


def test_storage_stack_cap(slot):
    lim = catalog.limits(catalog.lookup(TITANITE_SHARD))
    assert (lim.max_quantity, lim.max_storage) == (99, 600)
    assert catalog.limits(catalog.lookup(STANDARD_ARROW)).max_storage == 600
    cap = catalog.stack_cap(lim, True)
    for _ in range(2):
        stored = slot.add_item(
            TITANITE_SHARD, 500, sort_key=16010, max_quantity=cap, to_storage=True
        )
    assert stored.quantity == 600
    # A lower cap never shrinks an existing stack.
    stored = slot.add_item(
        TITANITE_SHARD, 1, sort_key=16010, max_quantity=99, to_storage=True
    )
    assert stored.quantity == 600


def test_fix_storage_indices(slot):
    stored = slot.add_item(TITANITE_SHARD, 10, sort_key=16010, to_storage=True)
    assert slot.bad_storage_indices() == 0
    # The old spawn wrote position index 1 and last-index 1 into an empty box.
    raw = slot._data
    storage = slot._get_layout().storage
    struct.pack_into("<I", raw, stored.offset + 12, (16010 << 12) | 1)
    struct.pack_into("<I", raw, slot._last_index_off(storage), 1)
    assert slot.bad_storage_indices() == 2
    assert slot.fix_storage_indices() == 2
    fixed = slot.entry_at(stored.offset)
    assert fixed.index == (16010 << 12) | (0x80 + stored.position)
    assert slot.bad_storage_indices() == 0


def test_equipped_items_cannot_be_removed(slot):
    fists = next(e for e in _real(slot) if e.item_id == 110000)
    assert slot.is_equipped(fists)
    with pytest.raises(ValueError):
        slot.remove_item(fists)


def test_remove_and_upgrade(slot):
    dagger = slot.add_item(DAGGER, sort_key=5000000, durability=50)
    dagger = slot.entry_at(dagger.offset)
    assert slot.set_weapon_level(dagger, 7) == DAGGER + 7
    gaitem = next(g for g in slot.iter_gaitem() if g.handle == dagger.handle)
    assert gaitem.item_id == DAGGER + 7

    before = len(_real(slot))
    slot.remove_item(dagger)
    assert len(_real(slot)) == before - 1


def test_malformed_lists_block_inventory_only(slot):
    # A handle written over the key item count is what earlier editor
    # versions left behind; flags and gestures must stay editable.
    key_count = slot._get_layout().inv + 4 + 0x780 * 16
    struct.pack_into("<I", slot.get_raw(), key_count, 0x80800DCB)
    fresh = DS3Slot(0, slot.get_raw())
    assert fresh.inventory_error
    assert fresh.flags_error is None and fresh.layout_error is None
    with pytest.raises(LayoutError):
        fresh.add_item(TITANITE_SHARD, sort_key=16010)


@pytest.mark.parametrize("source", ["vanilla", "convergence", "cinders"])
def test_item_data_has_icons_and_unique_ids(source):
    from er_save_manager.games.DS3.icon_manager import get_icon

    items = catalog.items(source)
    assert items, source
    for category, entries in items.items():
        ids = [e["Id"] for e in entries]
        assert len(ids) == len(set(ids)), (source, category)
        missing = [e["Name"] for e in entries if get_icon(e["IconId"], source) is None]
        assert not missing, (source, category, missing[:5])


def test_catalog_limits_and_names():
    dark_hand = next(
        e for e in catalog.items()["weapon_items"] if e["Name"] == "Dark Hand"
    )
    assert catalog.limits(dark_hand).max_upgrade == 0
    storm_ruler = next(
        e for e in catalog.items()["weapon_items"] if e["Name"] == "Storm Ruler"
    )
    assert catalog.limits(storm_ruler).max_upgrade == 5
    assert catalog.display_name(DAGGER + 3) == "Dagger +3"
    dagger = catalog.lookup(DAGGER)
    variants = catalog.infusion_variants(dagger)
    assert [v["Infusion"] for v in variants[:3]] == ["Normal", "Heavy", "Sharp"]


def test_move_between_inventory_and_storage(slot):
    dagger = slot.entry_at(
        slot.add_item(DAGGER, sort_key=5000000, durability=50).offset
    )
    held_before = len([e for e in _real(slot) if not e.is_key])
    stored = slot.move_item(dagger)
    assert slot.in_storage(stored) and stored.handle == dagger.handle
    assert len([e for e in _real(slot) if not e.is_key]) == held_before - 1
    back = slot.move_item(stored)
    assert not slot.in_storage(back)
    assert back.index & 0xFFF == 0x80 + back.position
    assert DS3Slot(0, bytearray(slot.get_raw())).inventory_error is None


def test_move_merges_stacks(slot):
    slot.add_item(TITANITE_SHARD, 90, sort_key=16010, max_quantity=99, to_storage=True)
    held = slot.entry_at(slot.add_item(TITANITE_SHARD, 20, sort_key=16010).offset)
    merged = slot.move_item(held, max_quantity=99)
    assert merged.quantity == 99
    assert slot.entry_at(held.offset).quantity == 11
    with pytest.raises(ValueError):
        slot.move_item(slot.entry_at(held.offset), max_quantity=99)


def test_cached_offsets_match_fresh_parse_after_many_inserts(slot):
    weapons = [i for i in catalog.items()["weapon_items"] if catalog.is_obtainable(i)][
        :40
    ]
    for item in weapons:
        lim = catalog.limits(item)
        slot.add_item(
            int(item["Id"], 16),
            sort_key=lim.sort_key,
            durability=lim.durability,
            max_quantity=lim.max_quantity,
        )
    fresh = DS3Slot(0, slot._data)
    assert fresh._get_layout() == slot._get_layout()
    assert fresh._gaitem_slots() == slot._gaitem_slots()
    assert fresh.inventory_error is None
    for entry in _real(slot):
        if entry.handle >> 28 in (0x8, 0x9):
            assert slot._find_gaitem(entry.handle).item_id == entry.item_id


def test_estus_flasks_are_one_group_per_kind():
    flasks = [i for i in catalog.items()["goods_items"] if "Estus Flask" in i["Name"]]
    groups = {catalog.single_group(int(i["Id"], 16)) for i in flasks}
    assert groups == {"Estus Flask", "Ashen Estus Flask"}
    assert catalog.single_group(TITANITE_SHARD) is None


def test_gesture_data_ids_are_table_rows():
    gestures = json.loads((DATA / "gestures.json").read_text(encoding="utf-8"))
    ids = [g["id"] for g in gestures]
    assert len(ids) == len(set(ids))
    assert all(0 <= i < GESTURE_COUNT for i in ids)


def test_seamless_goods_in_every_source():
    for source in catalog.SOURCES:
        item = catalog.lookup(0x4008FCC8, source)
        assert item is not None and catalog.is_seamless(item)


def test_character_death_bits(slot, slot_bytes):
    """Andre's death bit is m40_00 bit 95 (byte 11, mask 0x80) of the CHR
    block; revive must clear it or the game spawns him dead again."""
    andre = next(
        n
        for n in json.loads((DATA / "npcs.json").read_text(encoding="utf-8"))
        if n["name"] == "Blacksmith Andre"
    )
    assert andre["chr_bits"] == [{"map": "m40_00", "bit": 95}]
    assert slot.character_dead("m40_00", 95) is False
    assert slot.set_character_dead("m40_00", 95, True)
    changed = [
        i
        for i, (a, b) in enumerate(zip(slot_bytes, slot.get_raw(), strict=True))
        if a != b
    ]
    assert len(changed) == 1 and slot.get_raw()[changed[0]] == 0x80
    assert slot.character_dead("m40_00", 95) is True
    assert slot.set_character_dead("m40_00", 95, False)
    assert slot.get_raw() == slot_bytes
    # No record for a map the character has no state for: nothing to change.
    assert slot.character_dead("m31_00", 158) is None
    assert not slot.set_character_dead("m31_00", 158, False)


def test_npc_quest_state_follows_revive_and_kill(slot):
    """Rosaria stays removed while quest state 1501 is set, so Kill sets it
    and Revive moves her to the revived state 1502, one-hot in 1500-1514."""
    from er_save_manager.games.DS3.tabs.npcs import _set_state

    npcs = json.loads((DATA / "npcs.json").read_text(encoding="utf-8"))
    rosaria = next(n for n in npcs if n["alive_flag"] == 1515)
    assert rosaria["quest"] == [1500, 1514, 1502, 1501]
    quest = range(1500, 1515)
    _set_state(slot, rosaria, False)
    assert slot.get_flag(1518)
    assert [f for f in quest if slot.get_flag(f)] == [1501]
    _set_state(slot, rosaria, True)
    assert [f for f in range(1515, 1520) if slot.get_flag(f)] == [1515]
    assert [f for f in quest if slot.get_flag(f)] == [1502]


def test_equip_slots_reference_inventory_ids_and_handles(slot):
    for k in range(22):
        index, item_id, handle = slot.equip_slot(k)
        entry = slot.equipped_entry(k)
        if index == 0xFFFFFFFF:
            assert entry is None and item_id == 0xFFFFFFFF and handle == 0
        else:
            assert item_id == entry.item_id & 0x0FFFFFFF and handle == entry.handle


def test_set_equip_writes_index_id_and_handle(slot):
    ring = slot.add_item(LIFE_RING, sort_key=20100)
    arrows = slot.add_item(STANDARD_ARROW, 50, sort_key=1020000, max_quantity=99)
    slot.set_equip(17, ring)
    slot.set_equip(6, arrows)
    assert slot.equip_slot(17) == (
        ring.index & 0xFFF,
        LIFE_RING & 0x0FFFFFFF,
        ring.handle,
    )
    assert slot.equipped_entry(6).offset == arrows.offset
    assert slot.is_equipped(ring)
    slot.set_equip(17, None)
    assert slot.equip_slot(17) == (0xFFFFFFFF, 0xFFFFFFFF, 0)
    assert slot.equipped_ids()[6] == STANDARD_ARROW


def test_weapon_level_updates_equipped_ids(slot):
    k = next(k for k in range(6) if slot.equipped_ids()[k] != FISTS_ID)
    weapon = slot.equipped_entry(k)
    new_id = slot.set_weapon_level(weapon, 3)
    assert slot.equipped_ids()[k] == new_id & 0x0FFFFFFF
    assert slot.equipped_entry(k).offset == weapon.offset


def test_set_equip_rejects_items_that_do_not_fit(slot):
    ring = slot.add_item(LIFE_RING, sort_key=20100)
    helm = slot.add_item(KNIGHT_HELM, sort_key=1013000, durability=380)
    shard = slot.add_item(TITANITE_SHARD, 5, sort_key=16010, max_quantity=99)
    for k, entry in ((1, ring), (13, helm), (17, shard), (21, ring), (10, ring)):
        with pytest.raises(ValueError):
            slot.set_equip(k, entry)


def test_equip_slot_kinds():
    accepts = DS3Slot.equip_slot_accepts
    assert accepts(1, DAGGER) and not accepts(1, STANDARD_ARROW)
    assert accepts(6, STANDARD_ARROW) and not accepts(7, STANDARD_ARROW)
    assert accepts(7, 0x62A20) and not accepts(6, 0x62A20)  # Standard Bolt
    assert accepts(12, KNIGHT_HELM) and not accepts(13, KNIGHT_HELM)
    assert accepts(21, 0x20002710) and not accepts(17, 0x20002710)  # covenant
    assert DS3Slot.equip_placeholder_id(0) == 110000
    assert DS3Slot.equip_placeholder_id(15) == 0x100DC758
    assert DS3Slot.equip_placeholder_id(17) is None


def test_second_id_copy_matches_equip_and_quick_slots(slot):
    copy = slot._get_layout().id_copy
    for k in range(22):
        entry = slot.equipped_entry(k)
        want = 0xFFFFFFFF if entry is None else entry.item_id
        assert struct.unpack_from("<I", slot._data, copy + 4 * k)[0] == want
    for k in range(10):
        entry = slot.quick_entry(k)
        want = 0xFFFFFFFF if entry is None else entry.item_id
        assert struct.unpack_from("<I", slot._data, copy + 88 + 4 * k)[0] == want


def test_set_equip_and_quick_item_write_the_second_copy(slot):
    copy = slot._get_layout().id_copy
    ring = slot.add_item(LIFE_RING, sort_key=20100)
    doll = slot.add_item(SMALL_DOLL, sort_key=20010, max_quantity=1)
    shard = slot.add_item(TITANITE_SHARD, 5, sort_key=16010, max_quantity=99)
    copy = slot._get_layout().id_copy
    slot.set_equip(17, ring)
    assert struct.unpack_from("<I", slot._data, copy + 4 * 17)[0] == LIFE_RING
    slot.set_quick_item(3, shard)
    assert slot.quick_entry(3).offset == shard.offset
    assert struct.unpack_from("<I", slot._data, copy + 88 + 12)[0] == TITANITE_SHARD
    slot.set_quick_item(3, None)
    assert slot.quick_entry(3) is None
    with pytest.raises(ValueError):
        slot.set_quick_item(4, ring)
    assert doll is not None


def test_attune_records_and_selection(slot):
    slot.attune([0x4013D620, 1301000])
    assert slot.attuned_spells() == [1300000, 1301000]
    base = slot._get_layout().inv
    slot.attune([])
    assert slot.attuned_spells() == []
    assert base == slot._get_layout().inv


def test_attunement_slots_per_source():
    from er_save_manager.games.DS3 import attunement

    assert attunement.slots(10, []) == 1
    assert attunement.slots(13, []) == 1
    # Darkmoon Ring: 2 in vanilla, 3 in Convergence.
    assert attunement.slots(10, [0x20004F6A]) == 3
    assert attunement.slots(10, [0x20004F6A], "convergence") == 4
    assert attunement.spell_cost(0x4013D620) == 1


def test_upgrade_materials_are_not_quick_items():
    from er_save_manager.games.DS3 import attunement

    assert attunement.is_material(TITANITE_SHARD)
    assert not attunement.is_material(0x40000097)  # Estus Flask


def test_weapon_level_field(slot):
    off = slot._player(0xA3)
    slot.weapon_level = 7
    assert slot._data[off] == 7
    assert slot.weapon_level == 7


def test_matchmaking_level_scale():
    assert catalog.matchmaking_level(DAGGER + 7) == 7
    assert catalog.matchmaking_level(0x107AC0 + 3) == 6  # Tailbone Short Sword, +5 cap
    assert catalog.matchmaking_level(0x10000000 | 1000) == 0
