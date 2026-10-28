"""Tests for er_save_manager.fixes.teleport. TeleportFix.apply() persists
through rebuild_slot, so these also cover rebuild_slot under a real fix."""

from __future__ import annotations

import pytest

from er_save_manager.fixes.checksum import check_slot_checksum
from er_save_manager.fixes.dlc import DLCFlagFix
from er_save_manager.fixes.teleport import (
    TELEPORT_LOCATIONS,
    DLCEscapeFix,
    TeleportFix,
)
from er_save_manager.parser.er_types import MapId
from er_save_manager.parser.slot_rebuild import rebuild_slot_with_map

DLC_MAP_ID = MapId(bytes([0, 0, 0, 61]))  # m61 - DLC overworld
SLOT_SIZE = 0x280000


def _coords(slot):
    c = slot.player_coordinates.coordinates
    return (c.x, c.y, c.z)


def test_locations():
    for key in TELEPORT_LOCATIONS:
        TeleportFix(key)
    with pytest.raises(ValueError):
        TeleportFix("nonexistent_place")
    assert not MapId(bytes([0, 36, 42, 60])).is_dlc() and DLC_MAP_ID.is_dlc()


def test_apply_moves_map_id_and_coordinates(sanitized_save):
    slot = sanitized_save.character_slots[0]
    coords = _coords(slot)
    limgrave = TELEPORT_LOCATIONS["limgrave"]
    # Limgrave has no coordinates, so the old ones stay
    assert TeleportFix("limgrave").apply(sanitized_save, 0).applied is True
    assert slot.map_id.data == limgrave.map_id.data
    assert slot.player_coordinates.map_id.data == limgrave.map_id.data
    assert _coords(slot) == coords
    assert check_slot_checksum(sanitized_save, 0)[0]

    TeleportFix("roundtable").apply(sanitized_save, 0)
    expected = TELEPORT_LOCATIONS["roundtable"].coordinates
    assert _coords(slot) == tuple(expected)
    assert slot.player_coordinates.unk_coordinates.x == expected[0]

    TeleportFix("liurnia").apply(sanitized_save, 0)
    header = slot.data_start + 0x4
    assert (
        bytes(sanitized_save._raw_data[header : header + 4])
        == TELEPORT_LOCATIONS["liurnia"].map_id.data
    )


def test_apply_only_touches_map_and_coordinate_related_bytes(sanitized_save):
    slot = sanitized_save.character_slots[0]
    before = bytes(
        sanitized_save._raw_data[slot.data_start : slot.data_start + SLOT_SIZE]
    )
    TeleportFix("altus").apply(sanitized_save, 0)
    slot = sanitized_save.character_slots[0]
    after = bytes(
        sanitized_save._raw_data[slot.data_start : slot.data_start + SLOT_SIZE]
    )

    allowed = {
        "inventory_held",
        "inventory_storage_box",
        "gaitem_map",
        "map_id",
        "player_coordinates",
        "player_data_hash",
    }
    for s in rebuild_slot_with_map(slot)[1]:
        if s["name"] not in allowed:
            assert before[s["start"] : s["end"]] == after[s["start"] : s["end"]], s[
                "name"
            ]


def test_dlc_escape(sanitized_save):
    assert DLCEscapeFix().detect(sanitized_save, 0) is False
    for clear_flag_first in (False, True):
        sanitized_save.character_slots[0].map_id = DLC_MAP_ID
        if clear_flag_first:
            DLCFlagFix().apply(sanitized_save, 0)
        assert DLCEscapeFix().detect(sanitized_save, 0) is True
        assert DLCEscapeFix().apply(sanitized_save, 0).applied is True
        slot = sanitized_save.character_slots[0]
        assert slot.map_id.is_dlc() is False
        assert slot.has_dlc_flag() is False
