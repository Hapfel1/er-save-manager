"""
Tests for er_save_manager.fixes.time_sync.TimeFix.
"""

from __future__ import annotations

from io import BytesIO

from er_save_manager.fixes.time_sync import TimeFix


def _first_active_slot(save):
    for i, slot in enumerate(save.character_slots):
        if not slot.is_empty():
            return i
    raise AssertionError("fixture save has no active character slots")


def _write_time(save, slot) -> None:
    buf = BytesIO()
    slot.world_area_time.write(buf)
    data = buf.getvalue()
    save._raw_data[slot.time_offset : slot.time_offset + len(data)] = data


def test_time_fix_flags_every_slot_in_real_save(sanitized_save):
    fix = TimeFix()
    for i, slot in enumerate(sanitized_save.character_slots):
        if slot.is_empty():
            continue
        assert fix.detect(sanitized_save, i) is True


def test_apply_sets_time_to_match_seconds_played_formula(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    seconds_played = sanitized_save.user_data_10_parsed.profile_summary.profiles[
        i
    ].seconds_played

    result = TimeFix().apply(sanitized_save, i)

    assert result.applied is True
    assert slot.world_area_time.hour == seconds_played // 3600
    assert slot.world_area_time.minute == (seconds_played % 3600) // 60
    assert slot.world_area_time.second == seconds_played % 60


def test_apply_persists_to_raw_data(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    TimeFix().apply(sanitized_save, i)

    reread = type(slot.world_area_time).read(
        BytesIO(
            bytes(sanitized_save._raw_data[slot.time_offset : slot.time_offset + 12])
        )
    )
    assert reread.hour == slot.world_area_time.hour
    assert reread.minute == slot.world_area_time.minute
    assert reread.second == slot.world_area_time.second


def test_detects_out_of_range_minute_directly():
    """has_time_corruption's minute/second range check is independent of
    seconds_played and should fire regardless of playtime comparison.
    """
    from er_save_manager.parser.user_data_x import UserDataX

    class _FakeTime:
        hour = 0
        minute = 60
        second = 0

    slot = UserDataX()
    slot.world_area_time = _FakeTime()
    assert slot.has_time_corruption(seconds_played=12345) is True


def test_apply_is_no_op_after_already_fixed(sanitized_save):
    i = _first_active_slot(sanitized_save)
    TimeFix().apply(sanitized_save, i)

    result = TimeFix().apply(sanitized_save, i)
    assert result.applied is False
