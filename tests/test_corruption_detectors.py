"""UserDataX.has_* corruption detectors on the healthy fixture and on
corruption written into it."""

from __future__ import annotations


def test_healthy_slots_report_only_the_zeroed_steamid(sanitized_save_readonly):
    """The fixture's SteamID is zeroed for privacy, which has_steamid_corruption
    always flags; any other issue would be a false positive."""
    for slot in sanitized_save_readonly.character_slots:
        # WorldAreaTime is the time of day, not play time
        assert slot.has_time_corruption(seconds_played=123456) is False
        assert slot.has_corruption(correct_steam_id=None) == (
            True,
            [f"steamid_corruption:SteamId = {slot.steam_id}"],
        )


def test_time_corruption_flags_out_of_range_values_and_fix_wraps(sanitized_save):
    slot = sanitized_save.character_slots[0]
    time = slot.world_area_time
    for hour, minute, second in ((24, 0, 0), (12, 60, 0), (12, 0, 60)):
        time.hour, time.minute, time.second = hour, minute, second
        assert slot.has_time_corruption() is True
    time.hour, time.minute, time.second = 0, 0, 0
    assert slot.has_time_corruption() is False

    time.hour, time.minute = 108, 54
    sanitized_save.fix_character_corruption(0)
    assert (time.hour, time.minute) == (12, 54)
