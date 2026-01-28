"""Torrent bug fix - fixes infinite loading when horse HP=0 and state=ACTIVE."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from er_save_manager.fixes.base import BaseFix, FixResult

if TYPE_CHECKING:
    from er_save_manager.parser import Save


class TorrentFix(BaseFix):
    """
    Fix for the Torrent infinite loading bug.

    Bug condition: Horse HP is 0 AND state is ACTIVE (13)
    Should be: Horse HP is 0 AND state is DEAD (3)

    This causes an infinite loading screen when trying to load the save.
    """

    name = "Torrent Bug"
    description = "Fixes infinite loading caused by Torrent HP=0 with state=ACTIVE"

    def detect(self, save: Save, slot_index: int) -> bool:
        """Check if Torrent has the bug."""
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False
        return slot.has_torrent_bug()

    def apply(self, save: Save, slot_index: int) -> FixResult:
        """Fix Torrent by setting state to DEAD."""
        slot = self.get_slot(save, slot_index)

        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        if not slot.has_torrent_bug():
            return FixResult(applied=False, description="Torrent bug not present")

        horse = slot.horse
        if not horse:
            return FixResult(applied=False, description="Horse data not found")

        # Store original state for logging
        original_state = horse.state.name

        # Apply fix
        horse.fix_bug()

        # Write to raw data
        if hasattr(slot, "horse_offset") and slot.horse_offset > 0:
            horse_bytes = BytesIO()
            horse.write(horse_bytes)
            horse_data = horse_bytes.getvalue()
            # Calculate absolute offset
            absolute_horse_offset = slot.data_start + slot.horse_offset
            save._raw_data[
                absolute_horse_offset : absolute_horse_offset + len(horse_data)
            ] = horse_data

            return FixResult(
                applied=True,
                description=f"State changed from {original_state} to {horse.state.name}",
                details=[
                    f"HP: {horse.hp}",
                    f"State: {original_state} -> {horse.state.name}",
                ],
            )

        return FixResult(applied=False, description="Could not write horse data")
