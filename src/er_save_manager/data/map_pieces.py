"""World map pieces (WorldMapPieceParam).

Each piece reveals part of the map art while its open event flag is on. The
per-tile mask in 71_maptile.mtmskbnd selects the art variant from the set of
open pieces. Fragment pieces are the ones the map fragment items open; the
others open on entering an area or are on from the start. Rectangles are
openTravelArea in world map units (see data/world_map.py), map numbers as in
MAP_NAMES. Convergence uses the same rows.

Pieces 62053 (Lands Between) and 62065 (Underground) are left out: their art
variants are unfinished map drawings.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MapPiece:
    flag_id: int
    name: str
    map_no: int
    rect: tuple[float, float, float, float]  # left, top, right, bottom
    fragment: bool

    def contains(self, x: float, y: float) -> bool:
        left, top, right, bottom = self.rect
        return left <= x <= right and top <= y <= bottom


MAP_PIECES: tuple[MapPiece, ...] = (
    MapPiece(62010, "Limgrave, West", 0, (1877, 5922, 4895, 7902), True),
    MapPiece(62011, "Weeping Peninsula", 0, (3041, 7341, 5089, 9096), True),
    MapPiece(62012, "Limgrave, East", 0, (3982, 5669, 5544, 7718), True),
    MapPiece(62020, "Liurnia, East", 0, (1907, 3344, 4154, 6688), True),
    MapPiece(62021, "Liurnia, North", 0, (1392, 3954, 2784, 5834), True),
    MapPiece(62022, "Liurnia, West", 0, (150, 3155, 2629, 6640), True),
    MapPiece(62030, "Altus Plateau", 0, (2607, 1971, 4377, 4810), True),
    MapPiece(62031, "Leyndell, Royal Capital", 0, (3432, 2687, 4979, 5636), True),
    MapPiece(62032, "Mt. Gelmir", 0, (1354, 1694, 3194, 3701), True),
    MapPiece(62040, "Caelid", 0, (4724, 6002, 7194, 7956), True),
    MapPiece(62041, "Dragonbarrow", 0, (4644, 4979, 7189, 6646), True),
    MapPiece(
        62050, "Mountaintops of the Giants, West", 0, (4559, 1644, 7659, 5701), True
    ),
    MapPiece(
        62051, "Mountaintops of the Giants, East", 0, (5719, 519, 8704, 4356), True
    ),
    MapPiece(
        62052, "Mountaintops of the Giants, North", 0, (2674, 0, 7499, 3316), True
    ),
    MapPiece(62004, "Center", 0, (4154, 3954, 7189, 6646), True),
    MapPiece(62005, "Southwest", 0, (0, 3954, 4154, 9112), False),
    MapPiece(62006, "Northwest", 0, (0, 0, 3432, 4979), False),
    MapPiece(62007, "Southeast", 0, (3982, 3954, 9648, 9112), False),
    MapPiece(62008, "Northeast", 0, (5544, 0, 9648, 5834), False),
    MapPiece(62009, "North", 0, (2784, 0, 8704, 2687), False),
    MapPiece(62000, "Map display", 0, (3561, 6957, 4036, 7588), False),
    MapPiece(62060, "Ainsel River", 1, (876, 2750, 3779, 6056), True),
    MapPiece(62061, "Lake of Rot", 1, (216, 3350, 2444, 6696), True),
    MapPiece(62062, "Mohgwyn Palace", 1, (3526, 6175, 6889, 8493), True),
    MapPiece(62063, "Siofra River", 1, (3467, 4814, 6834, 7333), True),
    MapPiece(62064, "Deeproot Depths", 1, (2187, 1455, 5779, 5063), True),
    MapPiece(62080, "Gravesite Plain", 10, (3037, 4606, 5368, 6988), True),
    MapPiece(62081, "Scadu Altus", 10, (4915, 1869, 7880, 5662), True),
    MapPiece(62082, "Southern Shore", 10, (3037, 5668, 7880, 7803), True),
    MapPiece(62083, "Rauh Ruins", 10, (3037, 1869, 5287, 4921), True),
    MapPiece(62084, "Abyss", 10, (5315, 4648, 7880, 6133), True),
    MapPiece(62002, "Map display", 10, (4450, 5940, 5075, 6537), False),
)


def pieces_on_map(map_no: int) -> list[MapPiece]:
    return [p for p in MAP_PIECES if p.map_no == map_no]


def fragment_at(map_no: int, x: float, y: float) -> MapPiece | None:
    """Smallest fragment piece whose rectangle holds the point."""
    hits = [
        p for p in MAP_PIECES if p.fragment and p.map_no == map_no and p.contains(x, y)
    ]
    return min(
        hits,
        key=lambda p: (p.rect[2] - p.rect[0]) * (p.rect[3] - p.rect[1]),
        default=None,
    )
