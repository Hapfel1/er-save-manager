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


def test_time_of_day_not_compared_with_play_time(sanitized_save_readonly):
    """WorldAreaTime is the time of day; a different play time is not corruption."""
    for i in _active_slots(sanitized_save_readonly):
        slot = sanitized_save_readonly.character_slots[i]
        assert slot.has_time_corruption() is False
        assert slot.has_time_corruption(seconds_played=123456) is False


def test_time_corruption_flags_out_of_range_values(sanitized_save):
    i = _active_slots(sanitized_save)[0]
    time = sanitized_save.character_slots[i].world_area_time
    original = (time.hour, time.minute, time.second)
    try:
        for hour, minute, second in ((24, 0, 0), (12, 60, 0), (12, 0, 60)):
            time.hour, time.minute, time.second = hour, minute, second
            assert sanitized_save.character_slots[i].has_time_corruption() is True
        time.hour, time.minute, time.second = 0, 0, 0
        assert sanitized_save.character_slots[i].has_time_corruption() is False
    finally:
        time.hour, time.minute, time.second = original


def test_time_fix_wraps_hour_into_a_day(sanitized_save):
    i = _active_slots(sanitized_save)[0]
    slot = sanitized_save.character_slots[i]
    slot.world_area_time.hour = 108
    slot.world_area_time.minute = 54
    sanitized_save.fix_character_corruption(i)
    assert (slot.world_area_time.hour, slot.world_area_time.minute) == (12, 54)


def test_steamid_corruption_detected_after_zeroing_slot_steamid(sanitized_save):
    """SteamID is already zeroed for privacy, so a nonzero reference value
    from USER_DATA_10 should now read as a mismatch on every active slot.
    """
    i = _active_slots(sanitized_save)[0]
    slot = sanitized_save.character_slots[i]
    assert slot.steam_id == 0
    assert slot.has_steamid_corruption(correct_steam_id=76561198000000000) is True


def test_no_corruption_flags_beyond_known_zeroed_steamid(sanitized_save_readonly):
    """has_steamid_corruption always flags steam_id == 0, independent of
    correct_steam_id, so the fixture's zeroed SteamID is an expected,
    single-issue result here. Anything beyond that single issue would be
    a real corruption signal (torrent bug, weather, time, event flags).
    """
    for i in _active_slots(sanitized_save_readonly):
        slot = sanitized_save_readonly.character_slots[i]
        has_issue, issues = slot.has_corruption(correct_steam_id=None)
        assert has_issue is True
        assert issues == [f"steamid_corruption:SteamId = {slot.steam_id}"]
