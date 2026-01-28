"""Event flags fix - fixes Ranni softlock and warp sickness issues."""

from __future__ import annotations

from typing import TYPE_CHECKING

from er_save_manager.fixes.base import BaseFix, FixResult
from er_save_manager.parser.event_flags import CorruptionDetector, CorruptionFixer

if TYPE_CHECKING:
    from er_save_manager.parser import Save


class EventFlagsFix(BaseFix):
    """
    Fix for event flag corruption.

    Handles multiple issues:
    - Ranni's Tower quest soft-lock
    - Radahn warp sickness (alive/dead variants)
    - Morgott warp sickness
    - Radagon warp sickness
    - Sealing Tree warp sickness (DLC)
    """

    name = "Event Flag Corruption"
    description = "Fixes quest soft-locks and warp sickness issues"

    def detect(self, save: Save, slot_index: int) -> bool:
        """Check if any event flag corruption exists."""
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False

        if not hasattr(slot, "event_flags") or not slot.event_flags:
            return False

        issues = CorruptionDetector.detect_all(slot.event_flags)
        return len(issues) > 0

    def apply(self, save: Save, slot_index: int) -> FixResult:
        """Apply all event flag fixes."""
        slot = self.get_slot(save, slot_index)

        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        if not hasattr(slot, "event_flags") or not slot.event_flags:
            return FixResult(applied=False, description="Event flags not found")

        # Detect issues
        issues = CorruptionDetector.detect_all(slot.event_flags)
        if not issues:
            return FixResult(applied=False, description="No event flag issues detected")

        # Make event_flags mutable
        event_flags_mutable = bytearray(slot.event_flags)

        # Apply fixes
        fixes_count, fix_descriptions = CorruptionFixer.fix_all(
            event_flags_mutable, issues
        )

        if fixes_count == 0:
            return FixResult(applied=False, description="Could not apply fixes")

        # Update in memory
        slot.event_flags = bytes(event_flags_mutable)

        # Write to raw data
        if hasattr(slot, "event_flags_offset") and slot.event_flags_offset > 0:
            # Calculate absolute offset
            absolute_event_flags_offset = slot.data_start + slot.event_flags_offset
            save._raw_data[
                absolute_event_flags_offset : absolute_event_flags_offset
                + len(event_flags_mutable)
            ] = event_flags_mutable

            return FixResult(
                applied=True,
                description=f"Fixed {fixes_count} event flag issue(s)",
                details=fix_descriptions,
            )

        return FixResult(applied=False, description="Could not write event flags")


class RanniSoftlockFix(BaseFix):
    """Specific fix for Ranni's Tower quest soft-lock."""

    name = "Ranni Softlock"
    description = "Fixes Ranni's Tower quest progression block"

    def detect(self, save: Save, slot_index: int) -> bool:
        """Check if Ranni softlock is present."""
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False

        if not hasattr(slot, "event_flags") or not slot.event_flags:
            return False

        return CorruptionDetector.check_ranni_softlock(slot.event_flags)

    def apply(self, save: Save, slot_index: int) -> FixResult:
        """Apply Ranni softlock fix."""
        slot = self.get_slot(save, slot_index)

        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        if not self.detect(save, slot_index):
            return FixResult(applied=False, description="Ranni softlock not detected")

        event_flags_mutable = bytearray(slot.event_flags)

        if CorruptionFixer.fix_ranni_softlock(event_flags_mutable):
            slot.event_flags = bytes(event_flags_mutable)

            if hasattr(slot, "event_flags_offset") and slot.event_flags_offset > 0:
                # Calculate absolute offset
                absolute_event_flags_offset = slot.data_start + slot.event_flags_offset
                save._raw_data[
                    absolute_event_flags_offset : absolute_event_flags_offset
                    + len(event_flags_mutable)
                ] = event_flags_mutable

                return FixResult(
                    applied=True,
                    description="Ranni's Tower soft-lock fixed",
                    details=[
                        "Cleared blocking flag 1034500738",
                        "Enabled 31 progression flags",
                    ],
                )

        return FixResult(applied=False, description="Could not apply Ranni fix")
