"""DLC flag fix - clears DLC entry flag and invalid DLC data."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from er_save_manager.fixes.base import BaseFix, FixResult

if TYPE_CHECKING:
    from er_save_manager.parser import Save


class DLCFlagFix(BaseFix):
    """
    Fix for DLC entry flag.

    When a character enters the Shadow of the Erdtree DLC area, a flag is set.
    If the player doesn't own the DLC, this causes infinite loading.

    Use case: Someone else teleported your character into the DLC,
    then teleported you out, but the flag remains set.
    """

    name = "DLC Entry Flag"
    description = "Clears Shadow of the Erdtree entry flag"

    def detect(self, save: Save, slot_index: int) -> bool:
        """Check if DLC flag is set."""
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False
        return slot.has_dlc_flag()

    def apply(self, save: Save, slot_index: int) -> FixResult:
        """Clear the DLC entry flag."""
        slot = self.get_slot(save, slot_index)

        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        if not slot.has_dlc_flag():
            return FixResult(applied=False, description="DLC flag not set")

        # Store original for logging
        original_value = slot.get_dlc_flag_value()

        # Clear the flag
        slot.clear_dlc_flag()

        # Write to raw data
        if hasattr(slot, "dlc_offset") and slot.dlc_offset > 0:
            dlc_bytes = BytesIO()
            slot.dlc.write(dlc_bytes)
            dlc_data = dlc_bytes.getvalue()
            save._raw_data[slot.dlc_offset : slot.dlc_offset + len(dlc_data)] = dlc_data

            return FixResult(
                applied=True,
                description="DLC entry flag cleared",
                details=[
                    f"Original flag value: {original_value}",
                    "Character can now load without DLC",
                ],
            )

        return FixResult(applied=False, description="Could not write DLC data")


class TarnishedPackFlagFix(BaseFix):
    """
    Fix for Tarnished pack entry flag.

    Same failure mode as DLCFlagFix, but for the Tarnished pack flag
    instead of the Shadow of the Erdtree flag: if the character entered
    content that requires the Tarnished pack, this flag is set. If the
    player doesn't own the pack, this causes infinite loading.

    Use case: Someone else teleported your character into the content,
    then teleported you out, but the flag remains set.
    """

    name = "Tarnished Pack Entry Flag"
    description = "Clears Tarnished pack entry flag"

    def detect(self, save: Save, slot_index: int) -> bool:
        """Check if Tarnished pack flag is set."""
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False
        return slot.has_tarnished_pack_flag()

    def apply(self, save: Save, slot_index: int) -> FixResult:
        """Clear the Tarnished pack entry flag."""
        slot = self.get_slot(save, slot_index)

        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        if not slot.has_tarnished_pack_flag():
            return FixResult(applied=False, description="Tarnished pack flag not set")

        # Store original for logging
        original_value = slot.get_tarnished_pack_flag_value()

        # Clear the flag
        slot.clear_tarnished_pack_flag()

        # Write to raw data
        if hasattr(slot, "dlc_offset") and slot.dlc_offset > 0:
            dlc_bytes = BytesIO()
            slot.dlc.write(dlc_bytes)
            dlc_data = dlc_bytes.getvalue()
            save._raw_data[slot.dlc_offset : slot.dlc_offset + len(dlc_data)] = dlc_data

            return FixResult(
                applied=True,
                description="Tarnished pack entry flag cleared",
                details=[
                    f"Original flag value: {original_value}",
                    "Character can now load without the Tarnished pack",
                ],
            )

        return FixResult(applied=False, description="Could not write DLC data")


class InvalidDLCFix(BaseFix):
    """
    Fix for invalid data in unused DLC slots.

    The DLC structure has 50 bytes. Bytes [0-3] are used (pre-order
    gestures, DLC entry flag, Tarnished pack flag). Garbage data in the
    remaining bytes [4-49] can prevent the save from loading.
    """

    name = "Invalid DLC Data"
    description = "Clears garbage data in unused DLC slots"

    def detect(self, save: Save, slot_index: int) -> bool:
        """Check if unused DLC slots have invalid data."""
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False
        return slot.has_invalid_dlc()

    def apply(self, save: Save, slot_index: int) -> FixResult:
        """Clear invalid data in unused DLC slots."""
        slot = self.get_slot(save, slot_index)

        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        if not slot.has_invalid_dlc():
            return FixResult(applied=False, description="No invalid DLC data")

        # Clear invalid data
        slot.clear_invalid_dlc()

        # Write to raw data
        if hasattr(slot, "dlc_offset") and slot.dlc_offset > 0:
            dlc_bytes = BytesIO()
            slot.dlc.write(dlc_bytes)
            dlc_data = dlc_bytes.getvalue()
            save._raw_data[slot.dlc_offset : slot.dlc_offset + len(dlc_data)] = dlc_data

            return FixResult(
                applied=True,
                description="Invalid DLC data cleared",
                details=["Zeroed bytes [4-49] in DLC structure"],
            )

        return FixResult(applied=False, description="Could not write DLC data")
