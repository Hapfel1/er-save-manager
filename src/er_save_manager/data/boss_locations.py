"""
Where Elden Ring bosses are on the map, with an item that stands for them.

boss_locations.json (boss_locations_convergence.json for The Convergence)
maps each boss_data.BOSSES name to [map, x, y, z, face]:

    map, x, y, z  MSB position of the boss part, whose entity id equals one
                  of its defeat flags. Roaming and large-tile bosses without
                  such a part use the open-world tile their flag id names:
                  the spot of their reward lot when it lies in that tile,
                  else the tile center.
    face          the item that stands for the boss, by the editor's item
                  name: from the lots its reward event awards, its NPC drop
                  lots, pickups flagged with its flags, or the reward placed
                  near it; a Remembrance or Great Rune first, items with an
                  icon before items without; empty when it has none

The Convergence file also holds the mod's own bosses as
[map, x, y, z, face, flags, region]: bosses only the mod's events defeat,
named by their health bar, and vanilla boss flags the mod gives another
boss (the vanilla flags kept, the mod's name shown). region is empty when
the map has no named location.

A boss counts as defeated when its first flag is set; killing and
respawning write all of its flags.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from er_save_manager.data.boss_data import BOSSES


@dataclass(frozen=True)
class BossSpot:
    name: str
    region: str
    flags: tuple[int, ...]
    map_id: str
    position: tuple[float, float, float]
    face: str


@cache
def boss_spots(is_convergence: bool = False) -> tuple[BossSpot, ...]:
    name = (
        "boss_locations_convergence.json" if is_convergence else "boss_locations.json"
    )
    rows = json.loads((Path(__file__).parent / name).read_text(encoding="utf-8"))
    spots = []
    for boss, row in rows.items():
        map_id, x, y, z, face = row[:5]
        if len(row) > 5:
            flags, region = tuple(row[5]), row[6]
        elif boss in BOSSES:
            flags, region = tuple(BOSSES[boss]["flags"]), BOSSES[boss]["category"]
        else:
            continue
        spots.append(BossSpot(boss, region, flags, map_id, (x, y, z), face))
    return tuple(spots)
