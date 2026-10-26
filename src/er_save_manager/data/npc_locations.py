"""
Where Elden Ring NPCs stand, from their life block's location flags.

Each map has placement events that enable an NPC's character part while any
of a set of flags in its life block (base+5..base+17, see npc_data) is on and
disable it once the NPC is dead (base+3); the location flags stay set.
npc_locations.json maps each such flag to the parts those events enable:
[name, map, x, y, z], with the part's
name from NpcParam and its MSB position in that map. An NPC can stand in
several places at once (Sellen's waypoint ruins and Academy parts share
flags). npc_locations_convergence.json is the same for The Convergence's
event and map files.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from er_save_manager.data.npc_data import NPC_FLAGS

# Life block offsets: hostile (absolvable, permanent) and dead
_HOSTILE = (1, 2)
_DEAD = 3


@dataclass(frozen=True)
class NpcSpot:
    npc: str  # NPC_FLAGS name(s) of the life block
    name: str  # in-game name of the placed part
    map_id: str
    position: tuple[float, float, float]
    flag_id: int  # location flag that places the part
    hostile: bool
    dead: bool  # placed where the flags left the NPC when it died


@cache
def _placements(is_convergence: bool) -> dict[int, list[list]]:
    name = "npc_locations_convergence.json" if is_convergence else "npc_locations.json"
    rows = json.loads((Path(__file__).parent / name).read_text(encoding="utf-8"))
    return {int(flag): parts for flag, parts in rows.items()}


@cache
def _blocks() -> dict[int, str]:
    """Life block base -> NPC name; one block can carry two names."""
    names: dict[int, list[str]] = {}
    for npc, (base, _location) in NPC_FLAGS.items():
        names.setdefault(base, []).append(npc)
    return {base: " / ".join(n) for base, n in names.items()}


def npc_spots(
    flag_state: Callable[[int], bool | None], is_convergence: bool = False
) -> list[NpcSpot]:
    """Parts the character's location flags place for every NPC. Death
    keeps the location flags, so dead NPCs are listed where they died."""
    placements = _placements(is_convergence)
    spots = []
    for base, npc in _blocks().items():
        dead = bool(flag_state(base + _DEAD))
        hostile = not dead and any(flag_state(base + k) for k in _HOSTILE)
        for flag_id in range(base + 5, base + 18):
            parts = placements.get(flag_id)
            if not parts or not flag_state(flag_id):
                continue
            for name, map_id, x, y, z in parts:
                spots.append(
                    NpcSpot(npc, name, map_id, (x, y, z), flag_id, hostile, dead)
                )
    return spots
