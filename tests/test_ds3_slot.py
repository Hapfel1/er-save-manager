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
    GESTURE_COUNT,
    LEVEL_STAT_OFFSET,
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


def test_level_matches_stat_sum(slot):
    stats = ("vig", "atn", "end", "vit", "str", "dex", "int", "fth", "lck")
    assert slot.level == sum(slot.get_stat(k) for k in stats) - LEVEL_STAT_OFFSET


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
    with pytest.raises(ValueError):
        slot.add_item(SMALL_DOLL, key_item=True, to_storage=True)


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
    """Killing Andre in game set m40_00 bit 95 (byte 11, mask 0x80) of the
    CHR block; revive must clear it or the game spawns him dead again."""
    andre = next(
        n
        for n in json.loads((DATA / "npcs.json").read_text(encoding="utf-8"))
        if n["name"] == "Andre"
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
