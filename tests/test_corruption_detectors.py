"""
Tests for UserDataX.has_* corruption detectors against a real save file.

The fixture save is a normal, healthy save (only SteamID and character
names have been zeroed for privacy). These tests assert no false positives
on healthy data; corrupted-state tests construct the corruption directly
rather than relying on a naturally corrupted fixture.
"""

from __future__ import annotations


def _active_slots(save):
    return [i for i, slot in enumerate(save.character_slots) if not slot.is_empty()]


def test_no_torrent_bug_false_positive(sanitized_save):
    for i in _active_slots(sanitized_save):
        slot = sanitized_save.character_slots[i]
        assert slot.has_torrent_bug() is False, f"slot {i} unexpectedly flagged"


def test_no_weather_corruption_false_positive(sanitized_save):
    for i in _active_slots(sanitized_save):
        slot = sanitized_save.character_slots[i]
        assert slot.has_weather_corruption() is False, f"slot {i} unexpectedly flagged"


def test_time_corruption_flags_all_zero_with_no_reference(sanitized_save):
    """Without a seconds_played reference, only an all-zero clock counts
    as corrupted. None of the fixture's active slots have an all-zero
    clock, so this should never flag here.
    """
    for i in _active_slots(sanitized_save):
        slot = sanitized_save.character_slots[i]
        assert slot.has_time_corruption(seconds_played=None) is False


def test_time_corruption_flags_out_of_range_minute_or_second(sanitized_save):
    i = _active_slots(sanitized_save)[0]
    slot = sanitized_save.character_slots[i]
    original_minute = slot.world_area_time.minute
    slot.world_area_time.minute = 60
    try:
        assert slot.has_time_corruption() is True
    finally:
        slot.world_area_time.minute = original_minute


def test_steamid_corruption_detected_after_zeroing_slot_steamid(sanitized_save):
    """SteamID is already zeroed for privacy, so a nonzero reference value
    from USER_DATA_10 should now read as a mismatch on every active slot.
    """
    i = _active_slots(sanitized_save)[0]
    slot = sanitized_save.character_slots[i]
    assert slot.steam_id == 0
    assert slot.has_steamid_corruption(correct_steam_id=76561198000000000) is True


def test_no_corruption_flags_beyond_known_zeroed_steamid(sanitized_save):
    """has_steamid_corruption always flags steam_id == 0, independent of
    correct_steam_id, so the fixture's zeroed SteamID is an expected,
    single-issue result here. Anything beyond that single issue would be
    a real corruption signal (torrent bug, weather, time, event flags).
    """
    for i in _active_slots(sanitized_save):
        slot = sanitized_save.character_slots[i]
        has_issue, issues = slot.has_corruption(correct_steam_id=None)
        assert has_issue is True
        assert issues == [f"steamid_corruption:SteamId = {slot.steam_id}"]
