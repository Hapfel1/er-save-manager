"""
DSR doors, shortcuts, item pickups and world events from
data/world_flags.json.

Each entry lists the event flags the game sets when the object is used; the
first one decides the state. A door placed through the map's ObjAct list has
its ObjAct state flag (6xxxxxxx, holds the door open) first, then its ObjAct
event flag (removes the door's prompt on load); some doors open with the
state flag alone. A scripted door, lever or ladder replays its open
animation on load when its own event flag is set, followed by any flags the
event sets alongside it. An item pickup is gone from the map while its
ItemLotParam getItemFlagId is set; a chest also has its ObjAct flag.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "data" / "world_flags.json"


class FlagState(Enum):
    SET = "set"
    """The first flag is on."""
    CLEAR = "clear"
    """No flag is on."""
    PARTLY = "partly"
    """The first flag is off and another one is on."""


@dataclass(frozen=True)
class FlagGroup:
    """Flags that the game sets together for one door, lever or event; the
    first one decides the state."""

    area: str
    label: str
    flags: tuple[int, ...]
    keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class Pickup:
    area: str
    items: str
    flag: int
    chest_flag: int | None

    @property
    def flags(self) -> tuple[int, ...]:
        return (self.flag,) if self.chest_flag is None else (self.flag, self.chest_flag)


def _load() -> dict:
    return json.loads(_DATA_FILE.read_text(encoding="utf-8"))


_DATA = _load()
AREAS: dict[str, str] = _DATA["areas"]


def _group(entry: dict) -> FlagGroup:
    return FlagGroup(
        area=AREAS.get(entry["map"], ""),
        label=entry["label"],
        flags=tuple(entry["flags"]),
        keys=tuple(entry.get("keys", ())),
    )


DOORS: tuple[FlagGroup, ...] = tuple(_group(e) for e in _DATA["doors"])
SHORTCUTS: tuple[FlagGroup, ...] = tuple(_group(e) for e in _DATA["shortcuts"])
EVENTS: tuple[FlagGroup, ...] = tuple(
    FlagGroup(area="", label=e["label"], flags=tuple(e["flags"]))
    for e in _DATA["events"]
)
PICKUPS: tuple[Pickup, ...] = tuple(
    Pickup(
        area=AREAS[e["map"]],
        items=e["items"],
        flag=e["flag"],
        chest_flag=e.get("chest_flag"),
    )
    for e in _DATA["pickups"]
)


def flag_state(char, flags: tuple[int, ...]) -> FlagState:
    if char.get_flag(flags[0]):
        return FlagState.SET
    if any(char.get_flag(f) for f in flags[1:]):
        return FlagState.PARTLY
    return FlagState.CLEAR


def set_flags(char, groups, value: bool) -> int:
    """Set or clear every flag of each group. Returns how many groups had a
    flag changed."""
    changed = 0
    for group in groups:
        if all(char.get_flag(f) == value for f in group.flags):
            continue
        for flag in group.flags:
            char.set_flag(flag, value)
        changed += 1
    return changed
