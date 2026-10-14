"""World map geometry for Elden Ring.

Map units are the game's world map menu coordinates: map markers, beacons
and the map cursor in MenuSaveLoad use them, and one unit is one pixel of
the menu's finest map tiles (origin top-left). The overworld (m60) and the
Realm of Shadow (m61) share one transform from global world coordinates:

    map x = global x - 7168
    map y = 16640 - global z

with global = tile * 256 + 128 + local on small (_00) tiles, and
size = 256 << lod in place of 256 on larger tiles.

Legacy maps (dungeons, catacombs, the underground) are placed through
WorldMapLegacyConvParam (world_map_conversion.json): each row pairs a point
in a source map with a point in a destination map, and a position converts
through the row of its map with the nearest source point. Rows chain (m35
converts to m11, which converts to m60).

Map numbers follow the marker records: 0 Lands Between, 1 underground,
10 Realm of Shadow. Underground maps (m12) convert to m60 coordinates and
are drawn on map 1.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

MAP_LANDS_BETWEEN = 0
MAP_UNDERGROUND = 1
MAP_REALM_OF_SHADOW = 10

MAP_NAMES = {
    MAP_LANDS_BETWEEN: "Lands Between",
    MAP_UNDERGROUND: "Underground",
    MAP_REALM_OF_SHADOW: "Realm of Shadow",
}

_ORIGIN_X = 7168.0
_ORIGIN_Z = 16640.0

_CONVERSION: list[list] = json.loads(
    (Path(__file__).parent / "world_map_conversion.json").read_text(encoding="utf-8")
)


def parse_map_id(map_id_str: str) -> tuple[int, int, int, int]:
    """(area, x, z, lod) of an "mAA_BB_CC_DD" string."""
    area, x, z, lod = (int(part) for part in map_id_str[1:].split("_"))
    return area, x, z, lod


def global_to_map(gx: float, gz: float) -> tuple[float, float]:
    return gx - _ORIGIN_X, _ORIGIN_Z - gz


def map_to_global(mx: float, my: float) -> tuple[float, float]:
    return mx + _ORIGIN_X, _ORIGIN_Z - my


def tile_global_rect(x: int, z: int, lod: int = 0) -> tuple[float, float, float, float]:
    """(min x, min z, max x, max z) of an m60 / m61 tile in global units."""
    size = 256 << lod
    return x * size, z * size, (x + 1) * size, (z + 1) * size


def tile_map_rect(x: int, z: int, lod: int = 0) -> tuple[float, float, float, float]:
    """(left, top, right, bottom) of an m60 / m61 tile in map units."""
    gx0, gz0, gx1, gz1 = tile_global_rect(x, z, lod)
    left, bottom = global_to_map(gx0, gz0)
    right, top = global_to_map(gx1, gz1)
    return left, top, right, bottom


def _convert_once(
    area: int, x: int, z: int, px: float, pz: float
) -> tuple[int, int, int, float, float] | None:
    """Convert through the nearest row of the map, preferring rows that
    land on m60 / m61 over rows into another legacy map."""
    best = None
    best_key = (True, math.inf)
    for row in _CONVERSION:
        src_area, src_x, src_z, spx, spz, dst_area, dst_x, dst_z, dpx, dpz, _ = row
        if (src_area, src_x, src_z) != (area, x, z) or dst_area == src_area:
            continue
        key = (dst_area not in (60, 61), math.hypot(px - spx, pz - spz))
        if key < best_key:
            best_key = key
            best = (dst_area, dst_x, dst_z, px - spx + dpx, pz - spz + dpz)
    return best


def location_map_point(
    map_id_str: str, local_x: float, local_z: float
) -> tuple[int, float, float] | None:
    """(map number, map x, map y) of a position in any map, or None when
    the map has no world map placement."""
    try:
        area, x, z, lod = parse_map_id(map_id_str)
    except ValueError:
        return None
    map_no = MAP_UNDERGROUND if area == 12 else None
    px, pz = local_x, local_z
    for _ in range(4):
        if area in (60, 61):
            size = 256 << lod
            mx, my = global_to_map(x * size + size / 2 + px, z * size + size / 2 + pz)
            if map_no is None:
                map_no = MAP_LANDS_BETWEEN if area == 60 else MAP_REALM_OF_SHADOW
            return map_no, mx, my
        step = _convert_once(area, x, z, px, pz)
        if step is None:
            return None
        area, x, z, px, pz = step
        lod = 0
    return None
