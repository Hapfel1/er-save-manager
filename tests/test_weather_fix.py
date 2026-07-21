"""Tests for er_save_manager.fixes.weather.WeatherFix."""

from __future__ import annotations

from io import BytesIO

from er_save_manager.fixes.weather import WeatherFix


def _first_active_slot(save):
    for i, slot in enumerate(save.character_slots):
        if not slot.is_empty():
            return i
    raise AssertionError("fixture save has no active character slots")


def _write_weather(save, slot) -> None:
    buf = BytesIO()
    slot.world_area_weather.write(buf)
    data = buf.getvalue()
    save._raw_data[slot.weather_offset : slot.weather_offset + len(data)] = data


def test_no_false_positive_on_healthy_save(sanitized_save):
    fix = WeatherFix()
    for i, slot in enumerate(sanitized_save.character_slots):
        if slot.is_empty():
            continue
        assert fix.detect(sanitized_save, i) is False, f"slot {i} unexpectedly flagged"


def test_detects_area_id_zero_with_real_map_location(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    assert slot.map_id.data != b"\x00\x00\x00\x00"  # fixture precondition

    slot.world_area_weather.area_id = 0
    _write_weather(sanitized_save, slot)

    assert WeatherFix().detect(sanitized_save, i) is True


def test_detects_unreasonably_large_timer(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    slot.world_area_weather.timer = 100001
    _write_weather(sanitized_save, slot)

    assert WeatherFix().detect(sanitized_save, i) is True


def test_timer_at_threshold_is_not_corruption(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    slot.world_area_weather.timer = 100000
    slot.world_area_weather.area_id = slot.map_id.data[3]  # keep other condition clean
    _write_weather(sanitized_save, slot)

    assert WeatherFix().detect(sanitized_save, i) is False


def test_apply_syncs_area_id_to_map_id(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    expected_area_id = slot.map_id.data[3]

    slot.world_area_weather.area_id = 0
    _write_weather(sanitized_save, slot)

    result = WeatherFix().apply(sanitized_save, i)

    assert result.applied is True
    assert slot.world_area_weather.area_id == expected_area_id
    assert WeatherFix().detect(sanitized_save, i) is False


def test_apply_does_not_reset_an_oversized_timer(sanitized_save):
    """apply() only ever writes area_id; a corruption triggered purely by
    an oversized timer is left with that timer value unchanged. This
    documents actual behavior, not necessarily ideal behavior.
    """
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    slot.world_area_weather.timer = 999999
    slot.world_area_weather.area_id = slot.map_id.data[3]
    _write_weather(sanitized_save, slot)

    result = WeatherFix().apply(sanitized_save, i)

    assert result.applied is True
    assert slot.world_area_weather.timer == 999999


def test_apply_is_no_op_when_not_corrupted(sanitized_save):
    i = _first_active_slot(sanitized_save)
    result = WeatherFix().apply(sanitized_save, i)
    assert result.applied is False
