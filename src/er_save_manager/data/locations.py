"""
Map location database for Elden Ring.
One entry per unique map ID. Teleporting sets the map_id field;
the game spawns the player at the default position for that map.

Tile types:
  - grace: Site of Grace, safe_coords = the player warp point the game uses
    for fast travel (several per map, so not part of LOCATIONS)
  - dungeon: Legacy dungeons, mini-dungeons, special areas
  - small (_00): Small overworld tiles (256x256 units, most detailed)
  - medium (_01): Medium overworld tiles (contain some enemies/graces spanning multiple small tiles)
  - big (_02): Big overworld tiles (span entire region, contain cross-tile enemies and Sites of Grace)

map_bytes = bytes([d0, d1, d2, d3]) where map_id_str = m{d3}_{d2}_{d1}_{d0:02d}
region_id = 0 means no region unlock needed for this map.

Data lives in locations.json as rows of
[map_id_str, name, tile_type, region_id, is_dlc, safe_coords];
map_bytes is derived from map_id_str.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MapLocation:
    map_id_str: str
    name: str
    map_bytes: bytes  # [d0, d1, d2, d3] little-endian
    tile_type: str  # "dungeon", "small", "medium", "big"
    region_id: int = 0  # unlock ID to add to Regions; 0 = not required
    is_dlc: bool = False
    safe_coords: tuple[float, float, float] | None = None


def _location(
    map_id_str: str,
    name: str,
    tile_type: str,
    region_id: int,
    is_dlc: bool,
    safe_coords: list[float] | None,
) -> MapLocation:
    d3, d2, d1, d0 = (int(part) for part in map_id_str[1:].split("_"))
    return MapLocation(
        map_id_str,
        name,
        bytes([d0, d1, d2, d3]),
        tile_type,
        region_id,
        is_dlc,
        tuple(safe_coords) if safe_coords is not None else None,
    )


_ROWS = json.loads(
    (Path(__file__).parent / "locations.json").read_text(encoding="utf-8")
)

LOCATIONS: dict[str, MapLocation] = {
    row[0]: _location(*row) for row in _ROWS if row[2] != "grace"
}

GRACES: list[MapLocation] = [_location(*row) for row in _ROWS if row[2] == "grace"]


def get_name_for_map_id(map_id_str: str) -> str:
    loc = LOCATIONS.get(map_id_str)
    return loc.name if loc else map_id_str


def get_all_locations() -> list[MapLocation]:
    return list(LOCATIONS.values())


def get_grace_locations() -> list[MapLocation]:
    return list(GRACES)


def get_locations_by_type(tile_type: str) -> list[MapLocation]:
    """Filter by tile_type: dungeon, small, medium, big"""
    return [loc for loc in LOCATIONS.values() if loc.tile_type == tile_type]


def get_dlc_locations() -> list[MapLocation]:
    return [loc for loc in LOCATIONS.values() if loc.is_dlc]
