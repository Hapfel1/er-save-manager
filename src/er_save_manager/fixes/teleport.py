"""Teleport fix - moves character to a safe location."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from er_save_manager.fixes.base import BaseFix, FixResult
from er_save_manager.parser.er_types import MapId
from er_save_manager.parser.slot_rebuild import rebuild_slot

if TYPE_CHECKING:
    from er_save_manager.parser import Save


@dataclass
class TeleportLocation:
    """A safe teleport destination."""

    name: str
    display_name: str
    map_id: MapId
    coordinates: tuple[float, float, float] | None = None
    is_dlc: bool = False


# Safe teleport locations
TELEPORT_LOCATIONS = {
    "limgrave": TeleportLocation(
        name="limgrave",
        display_name="Limgrave - First Step",
        map_id=MapId(bytes([0, 36, 42, 60])),  # 60 42 36 00
        is_dlc=False,
    ),
    "roundtable": TeleportLocation(
        name="roundtable",
        display_name="Roundtable Hold",
        map_id=MapId(bytes([0, 0, 10, 11])),  # 11 10 00 00
        coordinates=(-331.0, -22.0, -305.8),
        is_dlc=False,
    ),
    "liurnia": TeleportLocation(
        name="liurnia",
        display_name="Liurnia - Lake-Facing Cliffs",
        map_id=MapId(bytes([0, 37, 44, 60])),  # 60 44 37 00
        is_dlc=False,
    ),
    "altus": TeleportLocation(
        name="altus",
        display_name="Altus Plateau - Erdtree-Gazing Hill",
        map_id=MapId(bytes([0, 38, 46, 60])),  # 60 46 38 00
        is_dlc=False,
    ),
}


class TeleportFix(BaseFix):
    """
    Teleport a character to a safe location.

    Use cases:
    - Character stuck in DLC area without owning DLC
    - Character stuck in broken/inaccessible location
    - Character stuck after warp sickness
    """

    name = "Teleport"
    description = "Moves character to a safe location"

    def __init__(self, destination: str = "limgrave"):
        """
        Initialize teleport fix.

        Args:
            destination: Target location key (limgrave, roundtable, etc.)
        """
        if destination not in TELEPORT_LOCATIONS:
            raise ValueError(
                f"Unknown destination: {destination}. "
                f"Valid options: {list(TELEPORT_LOCATIONS.keys())}"
            )
        self.destination = TELEPORT_LOCATIONS[destination]

    def detect(self, save: Save, slot_index: int) -> bool:
        """
        Check if character might need teleporting.

        Returns True if:
        - Character is in DLC area
        - Character has any detected corruption
        """
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False

        # Check if in DLC area
        if hasattr(slot, "map_id") and slot.map_id:
            if slot.map_id.is_dlc():
                return True

        # Check for any corruption
        has_corruption, _ = slot.has_corruption()
        return has_corruption

    def apply(self, save: Save, slot_index: int) -> FixResult:
        """Teleport character to destination."""
        slot = self.get_slot(save, slot_index)

        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        # Store original location for logging
        original_map = "Unknown"
        if hasattr(slot, "map_id") and slot.map_id:
            original_map = slot.map_id.to_decimal()

        # Update map_id in parsed structure
        slot.map_id = self.destination.map_id

        # Keep player coordinate map ID in sync
        if hasattr(slot, "player_coordinates"):
            slot.player_coordinates.map_id.data = self.destination.map_id.data

        details = [
            f"From: {original_map}",
            f"To: {self.destination.map_id.to_decimal()}",
        ]

        # Also set coordinates if available
        if self.destination.coordinates and hasattr(slot, "player_coordinates"):
            try:
                # Update primary coordinates
                coords = slot.player_coordinates.coordinates
                coords.x = self.destination.coordinates[0]
                coords.y = self.destination.coordinates[1]
                coords.z = self.destination.coordinates[2]

                # Also update secondary coordinates to match (Rust has player_coords2)
                unk_coords = slot.player_coordinates.unk_coordinates
                unk_coords.x = self.destination.coordinates[0]
                unk_coords.y = self.destination.coordinates[1]
                unk_coords.z = self.destination.coordinates[2]

                details.append(f"Coordinates set to {self.destination.coordinates}")
            except (AttributeError, TypeError) as e:
                details.append(f"Note: Could not set coordinates ({e})")

        # Rebuild slot to persist all changes to raw data
        try:
            rebuilt_data = rebuild_slot(slot)
            slot_data_offset = slot.data_start
            save._raw_data[slot_data_offset : slot_data_offset + len(rebuilt_data)] = (
                rebuilt_data
            )

            # Recalculate checksums
            try:
                save.recalculate_checksums()
            except Exception:
                pass
        except Exception as e:
            return FixResult(
                applied=False,
                description=f"Failed to apply teleport: {e}",
                details=[str(e)],
            )

        return FixResult(
            applied=True,
            description=f"Teleported to {self.destination.display_name}",
            details=details,
        )


class DLCEscapeFix(BaseFix):
    """
    Escape from DLC area.

    Specifically for characters stuck in Shadow of the Erdtree
    who don't own the DLC.
    """

    name = "DLC Escape"
    description = "Teleports character out of DLC area and clears DLC flag"

    def detect(self, save: Save, slot_index: int) -> bool:
        """Check if character is in DLC area."""
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False

        if hasattr(slot, "map_id") and slot.map_id:
            return slot.map_id.is_dlc()

        return False

    def apply(self, save: Save, slot_index: int) -> FixResult:
        """Teleport out of DLC and clear flag."""
        slot = self.get_slot(save, slot_index)

        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        details = []

        # Teleport to Limgrave
        teleport = TeleportFix("limgrave")
        teleport_result = teleport.apply(save, slot_index)
        if teleport_result.applied:
            details.extend(teleport_result.details)

        # Clear DLC flag if set
        if slot.has_dlc_flag():
            from .dlc import DLCFlagFix

            dlc_fix = DLCFlagFix()
            dlc_result = dlc_fix.apply(save, slot_index)
            if dlc_result.applied:
                details.append("DLC entry flag cleared")

        if details:
            return FixResult(
                applied=True,
                description="Escaped from DLC area",
                details=details,
            )

        return FixResult(applied=False, description="Character not in DLC area")
