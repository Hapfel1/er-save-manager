"""
Tests for er_save_manager.fixes.teleport.

TeleportFix.apply() relies on rebuild_slot to persist changes, so these
tests also serve as an integration check that the rebuild_slot fix
(preserving slot.rest and game_man_0x5be/0x5bf) holds up under a real
fix that calls it directly.

TeleportFix.detect() flags every slot in the real fixture regardless of
map location, because has_corruption() always reports steamid_corruption
on the sanitized fixture's zeroed SteamID (see test_corruption_detectors.py).
This is documented rather than asserted as "healthy save = no flag".
"""

from __future__ import annotations

import pytest

from er_save_manager.fixes.dlc import DLCFlagFix
from er_save_manager.fixes.teleport import (
    TELEPORT_LOCATIONS,
    DLCEscapeFix,
    TeleportFix,
)
from er_save_manager.parser.er_types import MapId
from er_save_manager.parser.slot_rebuild import rebuild_slot_with_map

DLC_MAP_ID = MapId(bytes([0, 0, 0, 61]))  # m61 - DLC overworld

_INVENTORY_SECTION_NAMES = {"inventory_held", "inventory_storage_box", "gaitem_map"}


def _first_active_slot(save):
    for i, slot in enumerate(save.character_slots):
        if not slot.is_empty():
            return i
    raise AssertionError("fixture save has no active character slots")


def _slot_with_trailing_budget(save, min_bytes=64):
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


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_unknown_destination_raises():
    with pytest.raises(ValueError):
        TeleportFix("nonexistent_place")


def test_all_locations_are_constructible():
    for key in TELEPORT_LOCATIONS:
        TeleportFix(key)  # must not raise


# ---------------------------------------------------------------------------
# detect()
# ---------------------------------------------------------------------------


def test_detect_flags_every_slot_in_real_save(sanitized_save):
    """Documents actual behavior: has_corruption() always reports
    steamid_corruption on this sanitized fixture, so detect() is True
    everywhere regardless of map location.
    """
    fix = TeleportFix("limgrave")
    for i, slot in enumerate(sanitized_save.character_slots):
        if slot.is_empty():
            continue
        assert fix.detect(sanitized_save, i) is True


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------


def test_apply_moves_map_id_to_destination(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    result = TeleportFix("limgrave").apply(sanitized_save, i)

    assert result.applied is True
    assert slot.map_id.data == TELEPORT_LOCATIONS["limgrave"].map_id.data
    assert (
        slot.player_coordinates.map_id.data
        == TELEPORT_LOCATIONS["limgrave"].map_id.data
    )


def test_apply_sets_coordinates_when_destination_has_them(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    TeleportFix("roundtable").apply(sanitized_save, i)

    expected = TELEPORT_LOCATIONS["roundtable"].coordinates
    assert slot.player_coordinates.coordinates.x == expected[0]
    assert slot.player_coordinates.coordinates.y == expected[1]
    assert slot.player_coordinates.coordinates.z == expected[2]
    assert slot.player_coordinates.unk_coordinates.x == expected[0]


def test_apply_leaves_coordinates_unset_when_destination_has_none(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    original_coords = (
        slot.player_coordinates.coordinates.x,
        slot.player_coordinates.coordinates.y,
        slot.player_coordinates.coordinates.z,
    )

    TeleportFix("limgrave").apply(sanitized_save, i)  # no coordinates defined

    assert (
        slot.player_coordinates.coordinates.x,
        slot.player_coordinates.coordinates.y,
        slot.player_coordinates.coordinates.z,
    ) == original_coords


def test_apply_recalculates_checksum(sanitized_save):
    from er_save_manager.fixes.checksum import check_slot_checksum

    i = _first_active_slot(sanitized_save)
    TeleportFix("limgrave").apply(sanitized_save, i)

    valid, _, _ = check_slot_checksum(sanitized_save, i)
    assert valid is True


def test_apply_persists_map_id_to_raw_data(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    TeleportFix("liurnia").apply(sanitized_save, i)

    header_offset = slot.data_start + 0x4
    raw_map_id = bytes(sanitized_save._raw_data[header_offset : header_offset + 4])
    assert raw_map_id == TELEPORT_LOCATIONS["liurnia"].map_id.data


def test_apply_only_touches_map_and_coordinate_related_bytes(sanitized_save):
    """
    Integration check on rebuild_slot: everything outside inventory
    sections, map_id, and player_coordinates should be untouched by a
    teleport that doesn't move location-dependent structures like
    event flags. A regression in rebuild_slot's handling of
    slot.rest/game_man_0x5be would show up here as unrelated changes.
    """
    i = _slot_with_trailing_budget(sanitized_save)
    slot = sanitized_save.character_slots[i]
    before = bytes(
        sanitized_save._raw_data[slot.data_start : slot.data_start + 0x280000]
    )

    TeleportFix("altus").apply(sanitized_save, i)

    slot = sanitized_save.character_slots[i]
    after = bytes(
        sanitized_save._raw_data[slot.data_start : slot.data_start + 0x280000]
    )

    _, sections = rebuild_slot_with_map(slot)
    allowed_to_change = _INVENTORY_SECTION_NAMES | {
        "map_id",
        "player_coordinates",
        "player_data_hash",  # checksum-adjacent hash, recalculated on apply
    }
    protected_ranges = [
        (s["start"], s["end"]) for s in sections if s["name"] not in allowed_to_change
    ]
    for start, end in protected_ranges:
        assert before[start:end] == after[start:end], (
            f"unexpected change in protected range [{start}:{end}]"
        )


# ---------------------------------------------------------------------------
# DLCEscapeFix
# ---------------------------------------------------------------------------


def test_dlc_escape_detects_dlc_location(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    slot.map_id = DLC_MAP_ID

    assert DLCEscapeFix().detect(sanitized_save, i) is True


def test_dlc_escape_apply_always_teleports_regardless_of_location(sanitized_save):
    """
    Documents a real inconsistency, not intended behavior: apply() has
    no is_dlc() guard, unlike detect(). Calling apply() on a character
    who is not in the DLC still teleports them to Limgrave and clears
    the DLC flag if set. A caller relying on detect() first to decide
    whether to call apply() would never hit this, but apply() alone
    does not enforce it.
    """
    i = _first_active_slot(sanitized_save)
    assert DLCEscapeFix().detect(sanitized_save, i) is False

    result = DLCEscapeFix().apply(sanitized_save, i)

    assert result.applied is True
    assert "Escaped from DLC area" in result.description


def test_dlc_escape_teleports_and_clears_dlc_flag(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    slot.map_id = DLC_MAP_ID
    assert slot.has_dlc_flag() is True  # fixture precondition, set on every slot

    result = DLCEscapeFix().apply(sanitized_save, i)

    assert result.applied is True
    slot = sanitized_save.character_slots[i]
    assert slot.map_id.is_dlc() is False
    assert slot.has_dlc_flag() is False


def test_dlc_escape_still_teleports_when_flag_already_clear(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    slot.map_id = DLC_MAP_ID
    DLCFlagFix().apply(sanitized_save, i)  # clear the flag first
    slot = sanitized_save.character_slots[i]
    assert slot.has_dlc_flag() is False

    result = DLCEscapeFix().apply(sanitized_save, i)

    assert result.applied is True
    assert sanitized_save.character_slots[i].map_id.is_dlc() is False
