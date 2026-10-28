"""Tests for er_save_manager.fixes.weather.WeatherFix."""

from __future__ import annotations

from io import BytesIO

from er_save_manager.fixes.weather import WeatherFix


def _set_weather(save, area_id=None, timer=None):
    slot = save.character_slots[0]
    weather = slot.world_area_weather
    weather.area_id = slot.map_id.data[3] if area_id is None else area_id
    if timer is not None:
        weather.timer = timer
    buf = BytesIO()
    weather.write(buf)
    data = buf.getvalue()
    save._raw_data[slot.weather_offset : slot.weather_offset + len(data)] = data
    return weather


def test_area_id_zero_is_synced_to_map_id(sanitized_save):
    expected = sanitized_save.character_slots[0].map_id.data[3]
    assert expected != 0
    weather = _set_weather(sanitized_save, area_id=0)
    assert WeatherFix().detect(sanitized_save, 0) is True
    assert WeatherFix().apply(sanitized_save, 0).applied is True
    assert weather.area_id == expected
    assert WeatherFix().detect(sanitized_save, 0) is False


def test_timer_threshold(sanitized_save):
    _set_weather(sanitized_save, timer=100000)
    assert WeatherFix().detect(sanitized_save, 0) is False
    _set_weather(sanitized_save, timer=100001)
    assert WeatherFix().detect(sanitized_save, 0) is True
    # apply() only writes area_id; an oversized timer stays as it is
    weather = _set_weather(sanitized_save, timer=999999)
    assert WeatherFix().apply(sanitized_save, 0).applied is True
    assert weather.timer == 999999
