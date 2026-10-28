"""Tests for er_save_manager.fixes.steamid.SteamIdFix."""

from __future__ import annotations

import struct

from er_save_manager.fixes.steamid import SteamIdFix

FAKE_STEAM_ID = 76561198000000123  # synthetic test value, not a real account


def test_zeroed_reference_does_not_resolve_corruption(sanitized_save):
    for i in range(10):
        assert SteamIdFix().detect(sanitized_save, i) is True
    assert SteamIdFix().apply(sanitized_save, 0).applied is True
    assert sanitized_save.character_slots[0].steam_id == 0
    assert SteamIdFix().detect(sanitized_save, 0) is True


def test_apply_syncs_mismatched_steamid_to_reference(sanitized_save):
    slot = sanitized_save.character_slots[0]
    sanitized_save.user_data_10_parsed.steam_id = FAKE_STEAM_ID
    slot.steam_id = FAKE_STEAM_ID - 1

    assert SteamIdFix().apply(sanitized_save, 0).applied is True
    assert slot.steam_id == FAKE_STEAM_ID
    raw = sanitized_save._raw_data[slot.steamid_offset : slot.steamid_offset + 8]
    assert struct.unpack("<Q", raw)[0] == FAKE_STEAM_ID
    assert SteamIdFix().detect(sanitized_save, 0) is False
    assert SteamIdFix().apply(sanitized_save, 0).applied is False
