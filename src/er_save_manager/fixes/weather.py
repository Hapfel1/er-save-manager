"""Weather sync fix - fixes AreaID mismatch with current map."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from .base import BaseFix, FixResult

if TYPE_CHECKING:
    from ..parser import Save


class WeatherFix(BaseFix):
    """
    Fix for weather/area ID desync.

    The weather.area_id should match map_id[3]. A mismatch can cause
    weather-related visual glitches or loading issues.
    """

    name = "Weather Corruption"
    description = "Syncs weather AreaID with current map location"

    def detect(self, save: Save, slot_index: int) -> bool:
        """Check if weather is corrupted."""
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False
        return slot.has_weather_corruption()

    def apply(self, save: Save, slot_index: int) -> FixResult:
        """Sync weather AreaID to map ID."""
        slot = self.get_slot(save, slot_index)

        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        if not slot.has_weather_corruption():
            return FixResult(applied=False, description="Weather not corrupted")

        weather = slot.world_area_weather
        map_id = slot.map_id

        if not weather or not map_id:
            return FixResult(applied=False, description="Missing weather or map data")

        # Store original for logging
        original_area_id = weather.area_id
        correct_area_id = map_id.data[3]

        # Update in memory
        weather.area_id = correct_area_id

        # Write to raw data
        if hasattr(slot, "weather_offset") and slot.weather_offset > 0:
            weather_bytes = BytesIO()
            weather.write(weather_bytes)
            weather_data = weather_bytes.getvalue()
            save._raw_data[
                slot.weather_offset : slot.weather_offset + len(weather_data)
            ] = weather_data

            return FixResult(
                applied=True,
                description=f"AreaID set to {correct_area_id}",
                details=[
                    f"Original AreaID: {original_area_id}",
                    f"New AreaID: {correct_area_id}",
                    f"Map: {map_id.to_decimal()}",
                ],
            )

        return FixResult(applied=False, description="Could not write weather data")
