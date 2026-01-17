"""Time sync fix - calculates correct time from seconds played."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from .base import BaseFix, FixResult

if TYPE_CHECKING:
    from er_save_manager.parser import Save


class TimeFix(BaseFix):
    """
    Fix for time corruption.

    The in-game time (hour:minute:second) should be derivable from
    the total seconds_played stored in ProfileSummary. A time of
    00:00:00 with non-zero playtime indicates corruption.
    """

    name = "Time Corruption"
    description = "Recalculates in-game time from total seconds played"

    def detect(self, save: Save, slot_index: int) -> bool:
        """Check if time is corrupted."""
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False

        seconds_played = self._get_seconds_played(save, slot_index)
        return slot.has_time_corruption(seconds_played)

    def apply(self, save: Save, slot_index: int) -> FixResult:
        """Calculate and set correct time from playtime."""
        slot = self.get_slot(save, slot_index)

        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        seconds_played = self._get_seconds_played(save, slot_index)
        if seconds_played is None:
            return FixResult(
                applied=False, description="Could not read seconds_played from profile"
            )

        if not slot.has_time_corruption(seconds_played):
            return FixResult(applied=False, description="Time not corrupted")

        time = slot.world_area_time
        if not time:
            return FixResult(applied=False, description="Missing time data")

        # Store original for logging
        original_time = f"{time.hour:02d}:{time.minute:02d}:{time.second:02d}"

        # Calculate correct time
        hours = seconds_played // 3600
        minutes = (seconds_played % 3600) // 60
        seconds = seconds_played % 60

        # Update in memory
        time.hour = hours
        time.minute = minutes
        time.second = seconds

        # Write to raw data
        if hasattr(slot, "time_offset") and slot.time_offset > 0:
            time_bytes = BytesIO()
            time.write(time_bytes)
            time_data = time_bytes.getvalue()
            save._raw_data[slot.time_offset : slot.time_offset + len(time_data)] = (
                time_data
            )

            new_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            return FixResult(
                applied=True,
                description=f"Time set to {new_time}",
                details=[
                    f"Original: {original_time}",
                    f"New: {new_time}",
                    f"Seconds played: {seconds_played}",
                ],
            )

        return FixResult(applied=False, description="Could not write time data")

    def _get_seconds_played(self, save: Save, slot_index: int) -> int | None:
        """Get seconds_played from ProfileSummary."""
        if not save.user_data_10_parsed:
            return None
        if not hasattr(save.user_data_10_parsed, "profile_summary"):
            return None

        profile_summary = save.user_data_10_parsed.profile_summary
        if slot_index >= len(profile_summary.profiles):
            return None

        return profile_summary.profiles[slot_index].seconds_played
