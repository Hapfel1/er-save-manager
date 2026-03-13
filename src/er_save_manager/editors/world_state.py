"""World state editor - reads/writes character position/map data using parser-tracked offsets."""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

from er_save_manager.data.locations import LOCATIONS, get_name_for_map_id
from er_save_manager.parser.er_types import FloatVector3, MapId

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save
    from er_save_manager.parser.user_data_x import UserDataX


def _map_id_to_str(map_id: MapId) -> str:
    d = map_id.data
    return f"m{d[3]:02d}_{d[2]:02d}_{d[1]:02d}_{d[0]:02d}"


class WorldStateEditor:
    """Read and write player world state from a parsed save slot."""

    def __init__(self, save: Save, slot_index: int):
        self._save = save
        self._slot_index = slot_index

    @property
    def _slot(self) -> UserDataX:
        return self._save.character_slots[self._slot_index]

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_current_location(self) -> dict:
        slot = self._slot
        if slot.is_empty():
            return {"map_name": "Empty Slot", "coordinates": None, "map_id": None}

        map_id: MapId = slot.map_id
        map_id_str = _map_id_to_str(map_id)
        map_name = get_name_for_map_id(map_id_str)

        coords = None
        try:
            coords = slot.player_coordinates.coordinates
        except AttributeError:
            pass

        return {
            "map_name": map_name,
            "map_id_str": map_id_str,
            "coordinates": coords,
            "map_id": map_id,
        }

    def get_bloodstain_location(self) -> dict | None:
        slot = self._slot
        if slot.is_empty():
            return None
        try:
            bs = slot.blood_stain
            if bs is None:
                return None
            map_name = get_name_for_map_id(_map_id_to_str(bs.map_id))
            return {"map_name": map_name, "runes": bs.runes}
        except AttributeError:
            return None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def teleport_to_map_id(self, map_id_str: str) -> tuple[bool, str]:
        """
        Teleport character to a map by its string ID (e.g. "m60_42_36_00").
        Uses safe_coords from the location database if available, otherwise
        preserves current coordinates so the character doesn't void-spawn.
        Also adds the region unlock ID from the location database if not already present.
        """
        loc = LOCATIONS.get(map_id_str)
        if loc is None:
            return False, f"Unknown map ID: {map_id_str}"

        try:
            if loc.safe_coords is not None:
                x, y, z = loc.safe_coords
                coords = FloatVector3(x, y, z)
            else:
                info = self.get_current_location()
                coords = info["coordinates"] or FloatVector3(0.0, 0.0, 0.0)

            self._write_map_id_raw(MapId(loc.map_bytes), zero_coords=False)
            self._write_coordinates(coords)

            if loc.region_id:
                self._ensure_region_unlocked(loc.region_id)

            return True, f"Teleported to {loc.name}"
        except Exception as e:
            return False, str(e)

    def teleport_to_custom(self, map_id: MapId, coords=None) -> tuple[bool, str]:
        """Teleport to a custom MapId with optional coordinates."""
        try:
            self._write_map_id_raw(map_id, zero_coords=(coords is None))
            if coords is not None:
                self._write_coordinates(coords)
            return True, f"Teleported to {_map_id_to_str(map_id)}"
        except Exception as e:
            return False, str(e)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_map_id_raw(self, map_id: MapId, zero_coords: bool = True) -> None:
        """
        Write map_id to both the header field (offset 0x4) and PlayerCoordinates.map_id
        (coordinates_offset + 12). Optionally zeroes both xyz and unk_xyz so the game
        uses its internal spawn point instead of stale coordinates from the old map.
        """
        slot = self._slot
        raw = self._save._raw_data

        # Header map_id at slot data + 0x4
        header_offset = slot.data_start + 0x4
        raw[header_offset : header_offset + 4] = map_id.data
        slot.map_id = map_id

        # PlayerCoordinates.map_id at coordinates_offset + 12
        if hasattr(slot, "coordinates_offset") and slot.coordinates_offset:
            coord_base = slot.data_start + slot.coordinates_offset
            pc_map_id_offset = coord_base + 12
            raw[pc_map_id_offset : pc_map_id_offset + 4] = map_id.data
            try:
                slot.player_coordinates.map_id = map_id
            except AttributeError:
                pass

            if zero_coords:
                zero = struct.pack("<fff", 0.0, 0.0, 0.0)
                raw[coord_base : coord_base + 12] = zero
                raw[coord_base + 33 : coord_base + 45] = zero
                try:
                    pc = slot.player_coordinates
                    pc.coordinates.x = pc.coordinates.y = pc.coordinates.z = 0.0
                    pc.unk_coordinates.x = pc.unk_coordinates.y = (
                        pc.unk_coordinates.z
                    ) = 0.0
                except AttributeError:
                    pass

    def _write_coordinates(self, coords) -> None:
        """Write player coordinates using parser-tracked coordinates_offset."""
        slot = self._slot
        if not hasattr(slot, "coordinates_offset") or slot.coordinates_offset == 0:
            raise RuntimeError("coordinates_offset not available")

        offset = slot.data_start + slot.coordinates_offset
        raw = self._save._raw_data
        raw[offset : offset + 4] = struct.pack("<f", coords.x)
        raw[offset + 4 : offset + 8] = struct.pack("<f", coords.y)
        raw[offset + 8 : offset + 12] = struct.pack("<f", coords.z)

        try:
            slot.player_coordinates.coordinates.x = coords.x
            slot.player_coordinates.coordinates.y = coords.y
            slot.player_coordinates.coordinates.z = coords.z
        except AttributeError:
            pass

    def _ensure_region_unlocked(self, region_id: int) -> None:
        """Add region_id to the Regions list if not already present."""
        slot = self._slot
        try:
            regions = slot.unlocked_regions
            if region_id not in regions.region_ids:
                regions.region_ids.append(region_id)
                regions.count = len(regions.region_ids)
        except AttributeError:
            pass
