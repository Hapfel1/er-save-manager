"""
Elden Ring summoning pools, imp seals and painting solutions on the map.

map_objects.json (map_objects_convergence.json for The Convergence) holds

    pools  [flag, map, x, y, z] per SignPuddleParam row: the row id is the
           event flag set when the pool is activated, the map id and local
           position come from the row itself
    seals  [flag, map, x, y, z, keys] per imp seal: common event 90005620
           keeps the seal open while the flag is set; the position is the
           MSB part of the first statue or door asset the event names.
           keys is 2 when the event names a second door asset (its 2-key
           branch removes two Stonesword Keys), else 1

Paintings: a painting's pickup flag is 5800x0 and the reward placed at its
vista is the pickup at that flag + 300.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from er_save_manager.data.item_pickups import Pickup, get_pickups

POOL = "pool"
SEAL = "seal"
_PAINTING_REWARD_OFFSET = 300


@dataclass(frozen=True)
class MapObject:
    kind: str  # POOL or SEAL
    flag_id: int  # activated / opened
    map_id: str
    position: tuple[float, float, float]
    keys: int = 0  # Stonesword Keys an imp seal takes; 0 for pools


@dataclass(frozen=True)
class Painting:
    painting: Pickup  # the painting item
    reward: Pickup  # what the vista gives once found


@cache
def map_objects(is_convergence: bool = False) -> tuple[MapObject, ...]:
    name = "map_objects_convergence.json" if is_convergence else "map_objects.json"
    rows = json.loads((Path(__file__).parent / name).read_text(encoding="utf-8"))
    pools = (
        MapObject(POOL, flag, map_id, (x, y, z))
        for flag, map_id, x, y, z in rows["pools"]
    )
    seals = (
        MapObject(SEAL, flag, map_id, (x, y, z), keys)
        for flag, map_id, x, y, z, keys in rows["seals"]
    )
    return (*pools, *seals)


@cache
def paintings(is_convergence: bool = False) -> tuple[Painting, ...]:
    by_flag = {p.flag_id: p for p in get_pickups(is_convergence)}
    out = []
    for p in by_flag.values():
        if not any(name.endswith("Painting") for _, _, name in p.items):
            continue
        reward = by_flag.get(p.flag_id + _PAINTING_REWARD_OFFSET)
        if reward is not None:
            out.append(Painting(p, reward))
    return tuple(sorted(out, key=lambda x: x.painting.flag_id))
