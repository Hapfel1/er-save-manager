"""
DS2 doors, fog gates and area names from data/world_flags.json, and the door
open/close writes.

A door is open when its event flag is set and its map object holds the open
state; the game needs both. The open state is 30 for key and one-way doors
and 20 for bridges, golem gates and lever doors, as listed per door.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from er_save_manager.games.DS2.save import DOOR_CLOSED_STATE, EventFlags, WorldObjects

_DATA_FILE = Path(__file__).parent / "data" / "world_flags.json"


@dataclass(frozen=True)
class Door:
    map_id: int
    flag: int
    object_id: int
    open_state: int
    label: str
    near: str | None


@dataclass(frozen=True)
class FogGate:
    map_id: int
    flag: int
    object_id: int
    boss: bool
    near: str | None

    @property
    def label(self) -> str:
        return "Boss fog gate passed" if self.boss else "Fog gate passed"


class DoorStatus(Enum):
    """The values double as display labels."""

    OPEN = "Open"
    CLOSED = "Closed"
    PARTLY_OPEN = "Partly open"
    MISSING = "Not in this save"


def _load() -> tuple[dict[int, str], tuple[Door, ...], tuple[FogGate, ...]]:
    data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    areas = {int(k): v for k, v in data["areas"].items()}
    doors = tuple(
        Door(d["map"], d["flag"], d["object"], d["open"], d["label"], d["near"])
        for d in data["doors"]
    )
    fog = tuple(
        FogGate(f["map"], f["flag"], f["object"], f["boss"], f["near"])
        for f in data["fog_gates"]
    )
    return areas, doors, fog


AREAS, DOORS, FOG_GATES = _load()


def area_name(map_id: int) -> str:
    return AREAS.get(map_id, f"m{map_id >> 24:02d}_{map_id >> 16 & 0xFF:02d}")


def flag_map(flag_id: int) -> int | None:
    """Map id of a map event flag (A BB LLLLLL), None for a global flag."""
    if flag_id < 100_000_000:
        return None
    return (flag_id // 100_000_000 * 10) << 24 | (flag_id // 1_000_000 % 100) << 16


def flag_labels() -> dict[int, str]:
    """Flag id -> label for every door and fog gate flag."""
    labels = {}
    for gate in FOG_GATES:
        near = f" near {gate.near}" if gate.near else ""
        labels.setdefault(gate.flag, f"{gate.label}{near}")
    for door in DOORS:
        near = f" near {door.near}" if door.near else ""
        labels[door.flag] = f"{door.label} opened{near}"
    return labels


def door_status(door: Door, flags: EventFlags, objects: WorldObjects) -> DoorStatus:
    state = objects.object_state(door.object_id)
    if state is None or not flags.is_stored(door.flag):
        return DoorStatus.MISSING
    flag = flags.get_flag(door.flag)
    if flag and state == door.open_state:
        return DoorStatus.OPEN
    if not flag and state == DOOR_CLOSED_STATE:
        return DoorStatus.CLOSED
    return DoorStatus.PARTLY_OPEN


def set_doors(
    doors: list[Door], opened: bool, flags: EventFlags, objects: WorldObjects
) -> int:
    """Open or close doors (flag and object state). Returns how many changed."""
    changed = 0
    for door in doors:
        target = DoorStatus.OPEN if opened else DoorStatus.CLOSED
        status = door_status(door, flags, objects)
        if status in (DoorStatus.MISSING, target):
            continue
        flags.set_flag(door.flag, opened)
        objects.set_object_state(
            door.object_id, door.open_state if opened else DOOR_CLOSED_STATE
        )
        changed += 1
    return changed
