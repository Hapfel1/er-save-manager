"""
World State Editor - Teleportation and world state management.

Handles:
- Character teleportation to safe locations
- Custom coordinate teleportation
- World state viewing (map, coordinates, angle)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from er_save_manager.data.locations import (
    get_location_by_key,
    get_map_name,
)
from er_save_manager.parser.er_types import FloatVector3, FloatVector4, MapId
from er_save_manager.parser.slot_rebuild import rebuild_slot

if TYPE_CHECKING:
    from er_save_manager.parser import Save


class WorldStateEditor:
    """Editor for character position and world state."""

    def __init__(self, save: Save, slot_index: int):
        """
        Initialize editor.

        Args:
            save: Save file
            slot_index: Character slot (0-9)
        """
        self.save = save
        self.slot_index = slot_index
        self.slot = save.character_slots[slot_index]

    def get_current_location(self) -> dict:
        """
        Get current character location info.

        Returns:
            Dict with map_id, map_name, coordinates, angle
        """
        if self.slot.is_empty():
            return {
                "map_id": None,
                "map_name": "Empty Slot",
                "coordinates": None,
                "angle": None,
            }

        return {
            "map_id": self.slot.map_id,
            "map_name": get_map_name(self.slot.map_id),
            "coordinates": self.slot.player_coordinates.coordinates,
            "angle": self.slot.player_coordinates.angle,
        }

    def teleport_to_location(self, location_key: str) -> tuple[bool, str]:
        """
        Teleport character to a predefined safe location.

        Uses full save rebuild to handle variable-size regions structure.

        Args:
            location_key: Key from SAFE_LOCATIONS

        Returns:
            Tuple of (success, message)
        """
        if self.slot.is_empty():
            return False, "Cannot teleport: slot is empty"

        location = get_location_by_key(location_key)
        if not location:
            return False, f"Unknown location: {location_key}"

        # Update map ID in parsed structure so rebuild writes it
        self.slot.map_id.data = location.map_id.data
        # Keep player coordinate map ID in sync
        if hasattr(self.slot, "player_coordinates"):
            self.slot.player_coordinates.map_id.data = location.map_id.data

        # Update coordinates in parsed structure so rebuild writes them
        if location.coordinates:
            coords = self.slot.player_coordinates.coordinates
            coords.x = location.coordinates.x
            coords.y = location.coordinates.y
            coords.z = location.coordinates.z

            # Also update unknown secondary coordinates to match
            # (player_coords2 seems to be a duplicate)
            unk_coords = self.slot.player_coordinates.unk_coordinates
            unk_coords.x = location.coordinates.x
            unk_coords.y = location.coordinates.y
            unk_coords.z = location.coordinates.z

        # Add region ID to unlocked regions if not already present
        if hasattr(self.slot, "unlocked_regions"):
            if location.region_id > 0:
                if location.region_id not in self.slot.unlocked_regions.region_ids:
                    # Add the region
                    self.slot.unlocked_regions.region_ids.append(location.region_id)
                    self.slot.unlocked_regions.count = len(
                        self.slot.unlocked_regions.region_ids
                    )

                    # Rebuild entire slot to persist changes
                    try:
                        rebuilt_data = rebuild_slot(self.slot)

                        # Write rebuilt data at the character data start (after checksum)
                        slot_data_offset = self.slot.data_start
                        self.save._raw_data[
                            slot_data_offset : slot_data_offset + len(rebuilt_data)
                        ] = rebuilt_data

                        # Recalculate checksums for integrity
                        try:
                            self.save.recalculate_checksums()
                        except Exception:
                            pass
                    except Exception as e:
                        return False, f"Failed to unlock region: {e}"
        else:
            pass

        # Ensure slot changes (map/coordinates) are persisted even if region was already unlocked
        try:
            rebuilt_data = rebuild_slot(self.slot)
            slot_data_offset = self.slot.data_start
            self.save._raw_data[
                slot_data_offset : slot_data_offset + len(rebuilt_data)
            ] = rebuilt_data
            try:
                self.save.recalculate_checksums()
            except Exception:
                pass
        except Exception:
            # Fallback: ignore if rebuild already done above
            pass

        return True, f"Teleported to {location.display_name}"

    def teleport_to_custom(
        self,
        map_id: MapId,
        coordinates: FloatVector3 | None = None,
        angle: FloatVector4 | None = None,
    ) -> tuple[bool, str]:
        """
        Teleport to custom map ID and coordinates.

        WARNING: Teleporting to invalid coordinates can corrupt saves.

        Args:
            map_id: Target map ID
            coordinates: Target coordinates (optional)
            angle: Target angle/rotation (optional)

        Returns:
            Tuple of (success, message)
        """
        if self.slot.is_empty():
            return False, "Cannot teleport: slot is empty"

        # Update map ID - use struct to write bytes
        import struct

        map_offset = self.slot.data_start + 0x4
        struct.pack_into("4B", self.save._raw_data, map_offset, *map_id.data)

        # Update coordinates if provided
        if coordinates:
            self._write_coordinates(coordinates)

        # Update angle if provided
        if angle:
            self._write_angle(angle)

        map_name = get_map_name(map_id)
        return True, f"Teleported to {map_name}"

    def _write_coordinates(self, coords: FloatVector3):
        """Write coordinates to save file."""
        if not hasattr(self.slot, "coordinates_offset"):
            # Fallback: calculate from data_start
            # PlayerCoordinates is at tracked offset
            coords_offset = self.slot.data_start + self.slot.coordinates_offset
        else:
            coords_offset = self.slot.data_start + self.slot.coordinates_offset

        # Write FloatVector3 (12 bytes: 3x f32)
        import struct

        self.save._raw_data[coords_offset : coords_offset + 4] = struct.pack(
            "<f", coords.x
        )
        self.save._raw_data[coords_offset + 4 : coords_offset + 8] = struct.pack(
            "<f", coords.y
        )
        self.save._raw_data[coords_offset + 8 : coords_offset + 12] = struct.pack(
            "<f", coords.z
        )

    def _write_angle(self, angle: FloatVector4):
        """Write angle/rotation to save file."""
        if not hasattr(self.slot, "coordinates_offset"):
            return

        # Angle is 16 bytes after coordinates (FloatVector3 = 12 bytes, MapId = 4 bytes)
        angle_offset = self.slot.data_start + self.slot.coordinates_offset + 12 + 4

        # Write FloatVector4 (16 bytes: 4x f32)
        import struct

        self.save._raw_data[angle_offset : angle_offset + 4] = struct.pack(
            "<f", angle.x
        )
        self.save._raw_data[angle_offset + 4 : angle_offset + 8] = struct.pack(
            "<f", angle.y
        )
        self.save._raw_data[angle_offset + 8 : angle_offset + 12] = struct.pack(
            "<f", angle.z
        )
        self.save._raw_data[angle_offset + 12 : angle_offset + 16] = struct.pack(
            "<f", angle.w
        )

    def get_bloodstain_location(self) -> dict | None:
        """
        Get bloodstain (death) location.

        Returns:
            Dict with coordinates, map_id, runes or None if no bloodstain
        """
        if self.slot.is_empty():
            return None

        bloodstain = self.slot.blood_stain
        if not bloodstain:
            return None

        return {
            "coordinates": bloodstain.coordinates,
            "map_id": bloodstain.map_id,
            "map_name": get_map_name(bloodstain.map_id),
            "runes": bloodstain.runes,
        }
