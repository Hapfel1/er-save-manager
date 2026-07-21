"""
Tests for er_save_manager.fixes.steamid.SteamIdFix.
"""

from __future__ import annotations

from er_save_manager.fixes.steamid import SteamIdFix

FAKE_STEAM_ID = 76561198000000123  # synthetic test value, not a real account


def _first_active_slot(save):
    for i, slot in enumerate(save.character_slots):
        if not slot.is_empty():
            return i
    raise AssertionError("fixture save has no active character slots")


def test_zeroed_steamid_is_flagged_on_every_slot(sanitized_save):
    fix = SteamIdFix()
    for i, slot in enumerate(sanitized_save.character_slots):
        if slot.is_empty():
            continue
        assert fix.detect(sanitized_save, i) is True


def test_apply_with_zeroed_reference_does_not_resolve_corruption(sanitized_save):
    i = _first_active_slot(sanitized_save)
    result = SteamIdFix().apply(sanitized_save, i)

    assert result.applied is True
    assert sanitized_save.character_slots[i].steam_id == 0
    assert SteamIdFix().detect(sanitized_save, i) is True


def test_apply_syncs_mismatched_steamid_to_reference(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    sanitized_save.user_data_10_parsed.steam_id = FAKE_STEAM_ID
    slot.steam_id = FAKE_STEAM_ID - 1  # mismatched, but nonzero

    result = SteamIdFix().apply(sanitized_save, i)

    assert result.applied is True
    assert slot.steam_id == FAKE_STEAM_ID
    assert SteamIdFix().detect(sanitized_save, i) is False


def test_apply_persists_to_raw_data(sanitized_save):
    import struct

    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    sanitized_save.user_data_10_parsed.steam_id = FAKE_STEAM_ID
    slot.steam_id = FAKE_STEAM_ID - 1

    SteamIdFix().apply(sanitized_save, i)

    raw_value = struct.unpack(
        "<Q",
        bytes(sanitized_save._raw_data[slot.steamid_offset : slot.steamid_offset + 8]),
    )[0]
    assert raw_value == FAKE_STEAM_ID


def test_apply_is_no_op_when_already_synced(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    sanitized_save.user_data_10_parsed.steam_id = FAKE_STEAM_ID
    slot.steam_id = FAKE_STEAM_ID

    result = SteamIdFix().apply(sanitized_save, i)
    assert result.applied is False
