"""
Walkable floor points for teleporting to any spot on the world map.

floor_vanilla.bin holds, per map, the floor heights of the game's navmesh on
a 2-unit grid in the map's own frame (overworld tiles: tile-local, centered;
legacy maps: map-local). Points closer than 1 unit to a navmesh edge (walls,
tree trunks, ledges, the sea) are left out, as are the sea surface, the
seabed and the filler navmesh under the world. floor_convergence.bin holds
the Convergence maps whose record differs (floor, boss arenas, anchors, or
the world map placement of a legacy map under the Convergence conversion
table); other maps fall back to vanilla.

Grace and location warp points are stored as exact anchors; they reach
spots without navmesh (Convergence builds some areas without one).
Overworld tiles with an alternate version (world state) keep only floor
present in both versions.

Each point may carry the boss flag of the fog-walled arena it lies in.
Legacy map points carry their world map placement (the same conversion as
world_map.location_map_point, precomputed per point).

File layout (little endian):
  b"ERFL", u16 version, u16 map count
  per map: u8 area, u8 x, u8 z, u8 lod, u32 offset, u32 size of an lzma record
  record:
    u8 flags (1 floor, 2 arenas, 4 placement, 8 anchors)
    arenas: u8 n, u32 boss flag[n]
    placement: u8 n, n * (u8 map number, f32 ax, f32 az, f32 bbox[4]);
      world map point = (local x + ax, az - local z)
    anchors: u16 n, n * (f32 x, y, z, u32 arena flag, u8 map number, f32 mx, my)
    u16 block count, per block: i16 bx, i16 bz, u16 occupied cells, u16 points
    then streams, each holding every block in table order:
      occupancy: 128 bytes per block, bit c (LSB first) = cell c (z major)
        has floor
      extra floors: u8 per occupied cell, floors in the cell - 1
      heights: i16 per point, delta from the previous point of the block
        (first from 0), in HSTEP units, rounded up (never below the navmesh);
        points by cell, then height
      arena index: u8 per point (1-based, 0 none) with flag 2
      placement index: u8 per point (1-based) with flag 4
  Cell (i, j) of block (bx, bz) is centered at
  ((bx * 32 + i + 0.5) * 2, (bz * 32 + j + 0.5) * 2).
"""

from __future__ import annotations

import lzma
import math
import struct
import sys
from array import array
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path

from er_save_manager.data.locations import (
    CONVERGENCE_LOCATIONS,
    LOCATIONS,
    MapLocation,
    get_name_for_map_id,
)
from er_save_manager.data.world_map import (
    MAP_LANDS_BETWEEN,
    MAP_REALM_OF_SHADOW,
    global_to_map,
    map_to_global,
    parse_map_id,
)

CELL = 2.0
BLOCK = 32
VERSION = 2
HSTEP = 0.25
FLOOR_GAP = 2.0  # neighbouring points closer than this in height are one floor
SAME_SPOT = 4.0  # floors listed for a click: at most this much farther than the nearest

# Map areas under the ground: the underground rivers (m12), Stone Coffin
# Fissure (m22), Finger Birthing Grounds (m25), catacombs, caves, tunnels,
# the Shunning-Grounds, and the DLC catacombs, gaols, forges and caves.
# Divine Towers (m34) and the Ruin-Strewn Precipice (m39) stand above it.
_BELOW_GROUND = frozenset({12, 22, 25, 30, 31, 32, 35, 40, 41, 42, 43})
# Leyndell, Ashen Capital shares the Royal Capital's footprint
_ASHEN = "m11_05"

_HEAD = struct.Struct("<4sHH")
_INDEX = struct.Struct("<BBBBII")
_PLACE = struct.Struct("<B6f")
_BLOCK = struct.Struct("<hhHH")
_ANCHOR = struct.Struct("<3fIB2f")


@dataclass(frozen=True)
class FloorPoint:
    """A teleport target on the floor of a map."""

    map_id_str: str
    x: float
    y: float
    z: float
    map_no: int  # world map the point is drawn on
    mx: float
    my: float
    arena_flag: int = 0  # boss flag of the fog-walled arena, 0 outside arenas


@dataclass
class _Record:
    arenas: list[int]
    placement: list[tuple[int, float, float, tuple[float, float, float, float]]]
    anchors: list[tuple[float, float, float, int, int, float, float]]
    # (bx, bz) -> (block number, occupied cells before it, points before it,
    # points)
    blocks: dict[tuple[int, int], tuple[int, int, int, int]]
    data: bytes  # the streams
    streams: tuple[int, int, int, int]  # offsets of extra, heights, arena, placement
    decoded: dict[tuple[int, int], tuple]


class _FloorFile:
    def __init__(self, path: Path):
        raw = path.read_bytes()
        magic, version, count = _HEAD.unpack_from(raw, 0)
        if magic != b"ERFL" or version != VERSION:
            raise ValueError(f"{path.name}: not a version {VERSION} floor point file")
        self._raw = raw
        self.index: dict[str, tuple[int, int]] = {}
        for k in range(count):
            area, x, z, lod, off, size = _INDEX.unpack_from(
                raw, _HEAD.size + k * _INDEX.size
            )
            self.index[f"m{area}_{x:02d}_{z:02d}_{lod:02d}"] = (off, size)
        self._records: dict[str, _Record] = {}

    def record(self, map_id_str: str) -> _Record | None:
        rec = self._records.get(map_id_str)
        if rec is not None or map_id_str not in self.index:
            return rec
        off, size = self.index[map_id_str]
        b = lzma.decompress(self._raw[off : off + size])
        flags = b[0]
        p = 1
        arenas: list[int] = []
        placement = []
        if flags & 2:
            n = b[p]
            arenas = list(struct.unpack_from(f"<{n}I", b, p + 1))
            p += 1 + 4 * n
        if flags & 4:
            n = b[p]
            p += 1
            for _ in range(n):
                no, ax, az, x0, y0, x1, y1 = _PLACE.unpack_from(b, p)
                placement.append((no, ax, az, (x0, y0, x1, y1)))
                p += _PLACE.size
        anchors = []
        if flags & 8:
            (n,) = struct.unpack_from("<H", b, p)
            p += 2
            for _ in range(n):
                anchors.append(_ANCHOR.unpack_from(b, p))
                p += _ANCHOR.size
        (nblocks,) = struct.unpack_from("<H", b, p)
        p += 2
        blocks = {}
        occ_total = pts_total = 0
        for k in range(nblocks):
            bx, bz, nocc, npts = _BLOCK.unpack_from(b, p + k * _BLOCK.size)
            blocks[(bx, bz)] = (k, occ_total, pts_total, npts)
            occ_total += nocc
            pts_total += npts
        extra = nblocks * BLOCK * BLOCK // 8
        heights = extra + occ_total
        arena = heights + 2 * pts_total
        place = arena + (pts_total if arenas else 0)
        rec = _Record(
            arenas,
            placement,
            anchors,
            blocks,
            b[p + nblocks * _BLOCK.size :],
            (extra, heights, arena, place),
            {},
        )
        self._records[map_id_str] = rec
        return rec


def _decode(rec: _Record, key: tuple[int, int]):
    """(first point per cell, heights, arena index, placement index) of a block."""
    got = rec.decoded.get(key)
    if got is not None:
        return got
    k, occ_before, pts_before, npts = rec.blocks[key]
    d = rec.data
    extra_off, heights_off, arena_off, place_off = rec.streams
    occ = d[k * BLOCK * BLOCK // 8 : (k + 1) * BLOCK * BLOCK // 8]
    extra = extra_off + occ_before
    first = [0] * (BLOCK * BLOCK + 1)
    total = 0
    for c in range(BLOCK * BLOCK):
        first[c] = total
        if occ[c >> 3] >> (c & 7) & 1:
            total += 1 + d[extra]
            extra += 1
    first[-1] = total
    deltas = array("h")
    p = heights_off + 2 * pts_before
    deltas.frombytes(d[p : p + 2 * npts])
    if sys.byteorder != "little":
        deltas.byteswap()
    heights = []
    h = 0
    for delta in deltas:
        h += delta
        heights.append(h * HSTEP)
    arena = (
        d[arena_off + pts_before : arena_off + pts_before + npts]
        if rec.arenas
        else None
    )
    place = (
        d[place_off + pts_before : place_off + pts_before + npts]
        if rec.placement
        else None
    )
    got = (first, heights, arena, place)
    rec.decoded[key] = got
    return got


@cache
def _file(name: str) -> _FloorFile | None:
    path = Path(__file__).parent / name
    return _FloorFile(path) if path.exists() else None


def _record(map_id_str: str, convergence: bool) -> _Record | None:
    if convergence:
        f = _file("floor_convergence.bin")
        if f is not None and map_id_str in f.index:
            return f.record(map_id_str)
    f = _file("floor_vanilla.bin")
    return f.record(map_id_str) if f is not None else None


@cache
def _legacy_maps(convergence: bool) -> list[str]:
    names: set[str] = set()
    for name in ("floor_vanilla.bin", "floor_convergence.bin" if convergence else None):
        f = _file(name) if name else None
        if f is not None:
            names.update(m for m in f.index if not m.startswith(("m60", "m61")))
    return sorted(names)


def _points_near(
    rec: _Record, lx: float, lz: float, radius: float, place_idx: int | None
) -> list[tuple[float, float, float, int, int, int]]:
    """(x, y, z, arena flag, cell i, cell j) of every point within radius."""
    out = []
    i0 = math.floor((lx - radius) / CELL)
    i1 = math.floor((lx + radius) / CELL)
    j0 = math.floor((lz - radius) / CELL)
    j1 = math.floor((lz + radius) / CELL)
    r2 = radius * radius
    for bx in range(i0 // BLOCK, i1 // BLOCK + 1):
        for bz in range(j0 // BLOCK, j1 // BLOCK + 1):
            if (bx, bz) not in rec.blocks:
                continue
            first, heights, arena, place = _decode(rec, (bx, bz))
            for j in range(max(j0, bz * BLOCK), min(j1, bz * BLOCK + BLOCK - 1) + 1):
                cz = (j + 0.5) * CELL
                for i in range(
                    max(i0, bx * BLOCK), min(i1, bx * BLOCK + BLOCK - 1) + 1
                ):
                    cx = (i + 0.5) * CELL
                    if (cx - lx) ** 2 + (cz - lz) ** 2 > r2:
                        continue
                    c = (j - bz * BLOCK) * BLOCK + (i - bx * BLOCK)
                    for k in range(first[c], first[c + 1]):
                        if place_idx is not None and (
                            place is None or place[k] != place_idx
                        ):
                            continue
                        flag = rec.arenas[arena[k] - 1] if arena and arena[k] else 0
                        out.append((cx, heights[k], cz, flag, i, j))
    return out


def _floors(points, lx: float, lz: float):
    """Split points into floors (cells next to each other with heights within
    FLOOR_GAP join) and return the point of each floor nearest to (lx, lz)."""
    parent = list(range(len(points)))

    def root(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    by_cell: dict[tuple[int, int], list[int]] = {}
    for k, p in enumerate(points):
        by_cell.setdefault((p[4], p[5]), []).append(k)
    for (i, j), ks in by_cell.items():
        for di, dj in ((1, 0), (0, 1), (1, 1), (1, -1)):
            for k2 in by_cell.get((i + di, j + dj), ()):
                for k in ks:
                    if abs(points[k][1] - points[k2][1]) < FLOOR_GAP:
                        parent[root(k)] = root(k2)
    best: dict[int, int] = {}
    for k, p in enumerate(points):
        r = root(k)
        d = (p[0] - lx) ** 2 + (p[2] - lz) ** 2
        if r not in best or d < best[r][0]:
            best[r] = (d, k)
    return [points[k] for _, k in best.values()]


def _anchors_near(
    rec: _Record, map_id: str, map_no: int, mx: float, my: float, radius: float
):
    """(distance, FloorPoint) of the record's anchors within radius."""
    out = []
    for x, y, z, flag, no, amx, amy in rec.anchors:
        d = math.hypot(amx - mx, amy - my)
        if no == map_no and d <= radius:
            out.append((d, FloorPoint(map_id, x, y, z, no, amx, amy, flag)))
    return out


def floors_near(
    map_no: int, mx: float, my: float, convergence: bool, radius: float = 12.0
) -> list[FloorPoint]:
    """One teleport point per floor near a world map position. Floors more
    than SAME_SPOT farther than the nearest one are left out.

    Overworld maps (Lands Between, Realm of Shadow) search the small tiles
    around the point; every map also searches the legacy maps placed there
    (dungeons, catacombs, the underground). On overworld maps the surface
    comes first: overworld tile floors top first, then legacy dungeons, the
    Ashen Capital, and the maps under the ground (_BELOW_GROUND), each
    nearest first. Other maps list floors nearest first.
    """
    found: list[tuple[float, FloorPoint]] = []
    if map_no in (MAP_LANDS_BETWEEN, MAP_REALM_OF_SHADOW):
        area = 60 if map_no == MAP_LANDS_BETWEEN else 61
        gx, gz = map_to_global(mx, my)
        for tx in range(int((gx - radius) // 256), int((gx + radius) // 256) + 1):
            for tz in range(int((gz - radius) // 256), int((gz + radius) // 256) + 1):
                map_id = f"m{area}_{tx:02d}_{tz:02d}_00"
                rec = _record(map_id, convergence)
                if rec is None:
                    continue
                lx, lz = gx - tx * 256 - 128, gz - tz * 256 - 128
                found.extend(_anchors_near(rec, map_id, map_no, mx, my, radius))
                for x, y, z, flag, _i, _j in _floors(
                    _points_near(rec, lx, lz, radius, None), lx, lz
                ):
                    pmx, pmy = global_to_map(tx * 256 + 128 + x, tz * 256 + 128 + z)
                    found.append(
                        (
                            math.hypot(x - lx, z - lz),
                            FloorPoint(map_id, x, y, z, map_no, pmx, pmy, flag),
                        )
                    )
    for map_id in _legacy_maps(convergence):
        rec = _record(map_id, convergence)
        if rec is None:
            continue
        found.extend(_anchors_near(rec, map_id, map_no, mx, my, radius))
        for k, (no, ax, az, (x0, y0, x1, y1)) in enumerate(rec.placement):
            if no != map_no or not (
                x0 - radius <= mx <= x1 + radius and y0 - radius <= my <= y1 + radius
            ):
                continue
            lx, lz = mx - ax, az - my
            for x, y, z, flag, _i, _j in _floors(
                _points_near(rec, lx, lz, radius, k + 1), lx, lz
            ):
                found.append(
                    (
                        math.hypot(x - lx, z - lz),
                        FloorPoint(map_id, x, y, z, no, x + ax, az - z, flag),
                    )
                )
    found.sort(key=lambda t: (t[0], -t[1].y))
    if not found:
        return []
    out: list[FloorPoint] = []
    for d, p in found:
        if d > found[0][0] + SAME_SPOT:
            break
        if any(
            q.map_id_str == p.map_id_str and abs(q.y - p.y) < FLOOR_GAP for q in out
        ):
            continue
        out.append(p)
    if map_no in (MAP_LANDS_BETWEEN, MAP_REALM_OF_SHADOW):
        out.sort(key=_surface_rank)
    return out


def _surface_rank(p: FloorPoint) -> tuple[int, float]:
    """Sort key for floors_near on an overworld map. Heights of different
    legacy maps are in their own frames, so only overworld tiles (one shared
    frame) sort by height; the stable sort keeps the rest nearest first."""
    area = parse_map_id(p.map_id_str)[0]
    if area in (60, 61):
        return 0, -p.y
    if area in _BELOW_GROUND:
        return 3, 0.0
    return (2 if p.map_id_str.startswith(_ASHEN) else 1), 0.0


def known_map(map_id_str: str, convergence: bool) -> bool:
    """The map has floor data or a location entry."""
    if map_id_str in (CONVERGENCE_LOCATIONS if convergence else LOCATIONS):
        return True
    names = (
        ("floor_vanilla.bin", "floor_convergence.bin")
        if convergence
        else ("floor_vanilla.bin",)
    )
    return any((f := _file(n)) is not None and map_id_str in f.index for n in names)


def nearest_floor(
    map_id_str: str, x: float, y: float, z: float, convergence: bool, radius: float
) -> tuple[float, str, float, float, float] | None:
    """(distance, map id, x, y, z) of the floor point or anchor nearest in 3D to
    a position in the map's own frame, searched within radius horizontally.

    Overworld positions search the small tiles around them, also for map ids
    of the larger (_01, _02) tiles; a hit is returned in that small tile's
    frame and map id.
    """
    hit = _nearest_floor(map_id_str, x, y, z, convergence, radius)
    return hit[:5] if hit is not None else None


def floor_near(
    map_id_str: str,
    x: float,
    y: float,
    z: float,
    convergence: bool,
    radius: float,
    map_no: int,
    point: tuple[float, float],
) -> FloorPoint | None:
    """Floor point or anchor nearest in 3D to a position in the map's own
    frame, with its boss arena flag. map_no and point are the world map
    placement given to the result."""
    hit = _nearest_floor(map_id_str, x, y, z, convergence, radius)
    if hit is None:
        return None
    _d, map_id, px, py, pz, flag = hit
    return FloorPoint(map_id, px, py, pz, map_no, point[0], point[1], flag)


def _nearest_floor(
    map_id_str: str, x: float, y: float, z: float, convergence: bool, radius: float
) -> tuple[float, str, float, float, float, int] | None:
    area, tx, tz, lod = parse_map_id(map_id_str)
    frames = [(map_id_str, x, z)]
    if area in (60, 61):
        size = 256 << lod
        gx, gz = tx * size + size / 2 + x, tz * size + size / 2 + z
        frames = [
            (f"m{area}_{nx:02d}_{nz:02d}_00", gx - nx * 256 - 128, gz - nz * 256 - 128)
            for nx in range(int((gx - radius) // 256), int((gx + radius) // 256) + 1)
            for nz in range(int((gz - radius) // 256), int((gz + radius) // 256) + 1)
        ]
    best = None
    for map_id, lx, lz in frames:
        rec = _record(map_id, convergence)
        if rec is None:
            continue
        cands = [
            (px, py, pz, flag)
            for px, py, pz, flag, *_ in _points_near(rec, lx, lz, radius, None)
        ]
        cands += [
            (ax, ay, az, flag)
            for ax, ay, az, flag, *_ in rec.anchors
            if math.hypot(ax - lx, az - lz) <= radius
        ]
        for px, py, pz, flag in cands:
            d = math.sqrt((px - lx) ** 2 + (py - y) ** 2 + (pz - lz) ** 2)
            if best is None or d < best[0]:
                best = (d, map_id, px, py, pz, flag)
    return best


def tile_floor(
    map_id_str: str,
    point: tuple[float, float, float],
    convergence: bool,
    tolerance: float = 4.0,
) -> tuple[float, float, float] | None:
    """Teleport position for an overworld tile's stored point: the point
    itself when floor lies within tolerance of it, else the tile's nearest
    other grace or location warp point, else the top floor nearest to it
    horizontally inside the tile (the point clamped into the tile first).
    None when the tile has no floor."""
    x, y, z = point
    hit = _nearest_floor(map_id_str, x, y, z, convergence, tolerance)
    if hit is not None and hit[0] <= tolerance:
        return point
    rec = _record(map_id_str, convergence)
    if rec is None:
        return None
    lx, lz = (min(max(v, -127.0), 127.0) for v in (x, z))
    # The stored point is itself an anchor; only other warp points count
    anchors = [a[:3] for a in rec.anchors if math.dist(a[:3], point) > tolerance]
    if anchors:
        return min(anchors, key=lambda a: math.hypot(a[0] - x, a[2] - z))
    radius = 8.0
    while radius < 400.0:
        pts = _points_near(rec, lx, lz, radius, None)
        if pts:
            floors = sorted(
                (math.hypot(px - lx, pz - lz), -py, px, py, pz)
                for px, py, pz, *_ in _floors(pts, lx, lz)
            )
            near = [f for f in floors if f[0] <= floors[0][0] + SAME_SPOT]
            _d, _y, px, py, pz = min(near, key=lambda f: f[1])
            return px, py, pz
        radius *= 2
    return None


def warp_point(map_id_str: str, convergence: bool) -> tuple[float, float, float] | None:
    """Spawn position for a map: its location warp point, else its first anchor."""
    loc = (CONVERGENCE_LOCATIONS if convergence else LOCATIONS).get(map_id_str)
    if loc is not None and loc.safe_coords is not None:
        return loc.safe_coords
    rec = _record(map_id_str, convergence)
    if rec is not None and rec.anchors:
        return rec.anchors[0][:3]
    return None


def bloodstain_location(point: FloorPoint) -> MapLocation:
    """Teleport location for the character's bloodstain at point."""
    return replace(
        pin_location(point),
        name=f"bloodstain ({point.x:.0f}, {point.y:.0f}, {point.z:.0f})",
        tile_type="bloodstain",
    )


def pin_location(point: FloorPoint) -> MapLocation:
    """Teleport location for a floor point, with the DLC marker of its map."""
    base = CONVERGENCE_LOCATIONS.get(point.map_id_str)
    d3, d2, d1, d0 = (int(v) for v in point.map_id_str[1:].split("_"))
    return MapLocation(
        point.map_id_str,
        f"{get_name_for_map_id(point.map_id_str)} "
        f"({point.x:.0f}, {point.y:.0f}, {point.z:.0f})",
        bytes([d0, d1, d2, d3]),
        "pin",
        region_id=base.region_id if base else 0,
        is_dlc=base.is_dlc if base else d3 == 61,
        safe_coords=(point.x, point.y, point.z),
        arena_flag=point.arena_flag,
    )
