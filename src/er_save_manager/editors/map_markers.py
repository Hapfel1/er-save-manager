"""Map marker and beacon editor (MenuSaveLoad version 2).

Edits are staged on a list of MapMarker and written by apply(). Records keep
their position in the save; a deleted record becomes empty and a new marker
takes the first empty record. Beacons and markers share one id sequence and
the save holds no counter, so new ids continue from the highest id in use.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from er_save_manager.parser.world import MapMarkerRecord, MenuSaveLoad

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save
    from er_save_manager.parser.user_data_x import UserDataX

EXPORT_FORMAT = "er-save-manager map markers"
EXPORT_VERSION = 1

MARKER_ICONS = tuple(range(1, 11))

BEACON = "beacon"
MARKER = "marker"


@dataclass(eq=False)
class MapMarker:
    kind: str
    id: int
    x: float
    y: float
    map: int
    icon: int = 1
    flags: int = 0
    # Record index in the save; None until apply() places a new marker.
    index: int | None = field(default=None, repr=False)


class MarkerLayoutError(Exception):
    """The slot's MenuSaveLoad block is not the version 2 layout."""


class MapMarkerEditor:
    def __init__(self, save: Save, slot_index: int):
        self._save = save
        self._slot_index = slot_index
        self.markers: list[MapMarker] = []
        self.dirty = False
        if self.supported:
            self._load()

    @property
    def _slot(self) -> UserDataX:
        return self._save.character_slots[self._slot_index]

    @property
    def _block(self) -> MenuSaveLoad:
        return self._slot.menu_profile_save_load

    @property
    def supported(self) -> bool:
        return self._block.has_marker_layout

    @property
    def layout_version(self) -> int | None:
        return self._block.layout_version

    def _load(self):
        self.markers = []
        for kind, beacons in ((BEACON, True), (MARKER, False)):
            for index, rec in enumerate(self._block.records(beacons)):
                if not rec.is_empty:
                    self.markers.append(
                        MapMarker(
                            kind,
                            rec.id,
                            rec.x,
                            rec.y,
                            rec.map,
                            rec.icon,
                            rec.flags,
                            index,
                        )
                    )
        self.dirty = False

    def revert(self):
        self._load()

    # ------------------------------------------------------------------
    # Staged edits
    # ------------------------------------------------------------------

    def count(self, kind: str) -> int:
        return sum(1 for m in self.markers if m.kind == kind)

    def capacity(self, kind: str) -> int:
        return (
            MenuSaveLoad.BEACON_COUNT if kind == BEACON else MenuSaveLoad.MARKER_COUNT
        )

    def _next_id(self) -> int:
        return max((m.id for m in self.markers), default=0) + 1

    def add(
        self, x: float, y: float, map_no: int, icon: int = 1, kind: str = MARKER
    ) -> MapMarker | None:
        """Stage a new marker; None when every record of that kind is used."""
        if self.count(kind) >= self.capacity(kind):
            return None
        if kind == BEACON:
            icon = 1
        marker = MapMarker(kind, self._next_id(), x, y, map_no, icon)
        self.markers.append(marker)
        self.dirty = True
        return marker

    def move(self, marker: MapMarker, x: float, y: float):
        marker.x, marker.y = x, y
        self.dirty = True

    def set_icon(self, marker: MapMarker, icon: int):
        marker.icon = icon
        self.dirty = True

    def delete(self, marker: MapMarker):
        self.markers.remove(marker)
        self.dirty = True

    def clear(self, kind: str | None = None, map_no: int | None = None) -> int:
        keep = [
            m
            for m in self.markers
            if (kind is not None and m.kind != kind)
            or (map_no is not None and m.map != map_no)
        ]
        removed = len(self.markers) - len(keep)
        if removed:
            self.markers = keep
            self.dirty = True
        return removed

    # ------------------------------------------------------------------
    # Export / import / copy
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "format": EXPORT_FORMAT,
            "version": EXPORT_VERSION,
            "markers": [
                {"kind": m.kind, "x": m.x, "y": m.y, "map": m.map, "icon": m.icon}
                for m in self.markers
            ],
        }

    def merge(self, data: dict, replace: bool) -> tuple[int, int]:
        """Stage markers from an exported dict: (added, skipped for lack of room).

        replace removes every current beacon and marker first. Imported
        entries get new ids.
        """
        if data.get("format") != EXPORT_FORMAT:
            raise ValueError("Not a map marker export")
        if replace:
            self.clear()
        added = skipped = 0
        for entry in data.get("markers", []):
            kind = entry.get("kind", MARKER)
            if kind not in (MARKER, BEACON):
                continue
            marker = self.add(
                float(entry["x"]),
                float(entry["y"]),
                int(entry["map"]),
                int(entry.get("icon", 1)),
                kind,
            )
            if marker is None:
                skipped += 1
            else:
                added += 1
        self.dirty = self.dirty or replace
        return added, skipped

    def export_file(self, path: str | Path):
        Path(path).write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")

    def import_file(self, path: str | Path, replace: bool) -> tuple[int, int]:
        return self.merge(json.loads(Path(path).read_text(encoding="utf-8")), replace)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def apply(self):
        """Write the staged markers into the slot and the raw save bytes."""
        if not self.supported:
            raise MarkerLayoutError(
                f"MenuSaveLoad layout version {self.layout_version} is not supported"
            )
        block = self._block
        for kind, beacons in ((BEACON, True), (MARKER, False)):
            staged = [m for m in self.markers if m.kind == kind]
            kept = {m.index for m in staged if m.index is not None}
            free = [i for i in range(self.capacity(kind)) if i not in kept]
            for m in staged:
                if m.index is None:
                    m.index = free.pop(0)
            by_index = {m.index: m for m in staged}
            for index, old in enumerate(block.records(beacons)):
                m = by_index.get(index)
                if m is not None:
                    rec = MapMarkerRecord(m.id, m.x, m.y, m.map, m.icon, m.flags)
                elif old.is_empty:
                    continue
                else:
                    rec = MapMarkerRecord()
                block.set_record(beacons, index, rec)

        data_start = self._slot.menu_profile_save_load_offset + 8
        raw = self._save._raw_data
        raw[data_start : data_start + len(block.data)] = block.data
        self.dirty = False


def copy_markers(
    save: Save, markers: dict, dst_slot: int, replace: bool
) -> tuple[int, int]:
    """Stage an exported marker dict into dst_slot and apply it."""
    dst = MapMarkerEditor(save, dst_slot)
    if not dst.supported:
        raise MarkerLayoutError("The target character uses the older marker layout")
    result = dst.merge(markers, replace)
    dst.apply()
    return result
