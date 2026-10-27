"""Unlock graces, map pieces and their play regions in a character slot.

Grace and map piece states are event flags. The map menu also keeps, per
map, the area it lets the cursor show (the union of the revealed pieces'
rectangles) and a fog of war grid; the art of a revealed piece is drawn only
on cleared fog cells. Unlocking pieces updates both (map_menu_bounds,
FOG_* below). A grace's play regions
(data/grace_regions.json) go into the slot's Regions list, a u32 count plus
that many u32 ids right before the horse data. Resizing the list moves every
later section; the slot keeps its size by dropping bytes from the end of
slot.rest, the stale buffer after PlayerGameDataHash, or by zero-filling it
when the list shrinks. The slot is parsed again afterwards so later writes use
the moved offsets.
"""

from __future__ import annotations

import struct
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

from er_save_manager.data.grace_data import grace_region_ids
from er_save_manager.data.map_pieces import MAP_PIECES
from er_save_manager.data.world_map import (
    MAP_LANDS_BETWEEN,
    MAP_REALM_OF_SHADOW,
    MAP_UNDERGROUND,
)
from er_save_manager.parser.event_flags import EventFlags
from er_save_manager.parser.inventory_ops import SLOT_DATA_SIZE
from er_save_manager.parser.user_data_x import UserDataX

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save


# Fog of war at MenuSaveLoad data +0x7F0: FOG_BYTES of bits, LSB first,
# 1 = cleared (a fully explored character has all of them set). Cells are
# FOG_CELL map units, 41 per row, rows running south to north:
#   index = floor((y0 - y) / FOG_CELL) * 41 + floor((x - x0) / FOG_CELL)
# A map row is wider than 41 cells only where it runs into the next row of
# bits. Bits 0-1680 hold the Lands Between, which the Underground shares,
# and the rest the Realm of Shadow. FOG_GRIDS gives (x0, y0, first bit,
# end bit) per map.
FOG_OFFSET = 0x7F0
FOG_BYTES = 0x1A8
FOG_ROW = 41
FOG_CELL = 256
FOG_GRIDS = {
    MAP_LANDS_BETWEEN: (5928, 10232, 0, 1681),
    MAP_UNDERGROUND: (5928, 10232, 0, 1681),
    MAP_REALM_OF_SHADOW: (4000, 20624, 1681, FOG_BYTES * 8),
}
_PIECES_BY_FLAG = {p.flag_id: p for p in MAP_PIECES}

# Shown map area per map: MenuSaveLoad data +0x08 + 0x20 * record, four f32
# (left, top, right, bottom) in map units and a u32 whose low byte is 1 once
# the map has an area. The Underground has no record of its own: the Lands
# Between record covers the pieces of both maps.
BOUNDS_OFFSET = 0x08
BOUNDS_STRIDE = 0x20
BOUNDS_RECORD = {MAP_LANDS_BETWEEN: 0, MAP_UNDERGROUND: 0, MAP_REALM_OF_SHADOW: 2}

# Flags the game sets on first entering a map. Without them the map menu
# does not offer that map (right stick for the Underground, the map switch
# for the Realm of Shadow), even with its pieces revealed.
MAP_ENTERED_FLAGS = {
    MAP_UNDERGROUND: (82001,),
    MAP_REALM_OF_SHADOW: (62002, 82002),
}


@dataclass
class UnlockResult:
    graces: int = 0
    pieces: int = 0
    regions: int = 0
    fog_cells: int = 0


def fog_cells(map_no: int, rect: tuple[float, float, float, float]) -> list[int]:
    """Bit indices of the fog cells a map-unit rectangle (left, top, right,
    bottom) on map_no overlaps."""
    left, top, right, bottom = rect
    x0, y0, first, end = FOG_GRIDS[map_no]
    columns = range(int((left - x0) // FOG_CELL), int((right - x0) // FOG_CELL) + 1)
    rows = range(int((y0 - bottom) // FOG_CELL), int((y0 - top) // FOG_CELL) + 1)
    return [
        k
        for row in rows
        for col in columns
        if first <= (k := row * FOG_ROW + col) < end
    ]


def _set_bounds(data: bytearray, event_flags: bytes) -> None:
    """Set each map's shown area to the union of its revealed pieces."""
    for record in set(BOUNDS_RECORD.values()):
        rects = [
            p.rect
            for p in MAP_PIECES
            if BOUNDS_RECORD.get(p.map_no) == record
            and EventFlags.get_flag(event_flags, p.flag_id)
        ]
        if not rects:
            continue
        off = BOUNDS_OFFSET + BOUNDS_STRIDE * record
        *old, state = struct.unpack_from("<4fI", data, off)
        if state & 0xFF == 1:
            rects.append(tuple(old))
        union = (
            min(r[0] for r in rects),
            min(r[1] for r in rects),
            max(r[2] for r in rects),
            max(r[3] for r in rects),
        )
        struct.pack_into("<4fI", data, off, *union, (state & ~0xFF) | 1)


def update_map_menu(save: Save, slot_idx: int, piece_flags: Iterable[int]) -> int:
    """Extend the shown map areas to the revealed pieces and clear the fog
    under the given pieces; when they are every piece of a map (Unlock Whole
    Map), all of that map's fog is cleared. Returns how many fog bits were cleared.
    Characters with the old map menu layout (version 0) are left unchanged."""
    slot = save.character_slots[slot_idx]
    menu = slot.menu_profile_save_load
    if menu.layout_version != 2:
        return 0
    pieces = [_PIECES_BY_FLAG[f] for f in piece_flags if f in _PIECES_BY_FLAG]
    cells = {cell for p in pieces for cell in fog_cells(p.map_no, p.rect)}
    given = {p.flag_id for p in pieces}
    for map_no in {p.map_no for p in pieces}:
        if all(p.flag_id in given for p in MAP_PIECES if p.map_no == map_no):
            _x0, _y0, first, end = FOG_GRIDS[map_no]
            cells.update(range(first, end))
    data = bytearray(menu.data)
    _set_bounds(data, slot.event_flags)
    cleared = 0
    for cell in cells:
        byte, bit = FOG_OFFSET + cell // 8, 1 << (cell % 8)
        if not data[byte] & bit:
            data[byte] |= bit
            cleared += 1
    if data != menu.data:
        # data follows the u16, u16, u32 MenuSaveLoad header
        off = slot.menu_profile_save_load_offset + 8
        save._raw_data[off : off + len(data)] = data
        menu.data = bytes(data)
    return cleared


def set_regions(save: Save, slot_idx: int, region_ids: list[int]) -> None:
    """Replace the slot's Regions list with region_ids, in that order.

    Only the list bytes change; every other section is moved as is.
    Raises ValueError when the parsed list does not match the bytes or the
    slot has no stale tail left to absorb the growth.
    """
    slot = save.character_slots[slot_idx]
    regions = slot.unlocked_regions
    start = slot.data_start
    list_end = slot.horse_offset
    count_off = list_end - 4 - 4 * regions.count
    if struct.unpack_from("<I", save._raw_data, count_off)[0] != regions.count:
        raise ValueError("the Regions list is not where the parse put it")
    grow = 4 * (len(region_ids) - regions.count)
    if len(slot.rest) < grow:
        raise ValueError("the slot has no room left for more regions")

    work = save._raw_data[start : start + SLOT_DATA_SIZE]
    work[count_off - start : list_end - start] = struct.pack(
        f"<I{len(region_ids)}I", len(region_ids), *region_ids
    )
    if len(work) > SLOT_DATA_SIZE:
        del work[SLOT_DATA_SIZE:]
    else:
        work.extend(bytes(SLOT_DATA_SIZE - len(work)))
    save._raw_data[start : start + SLOT_DATA_SIZE] = work

    stream = BytesIO(save._raw_data)
    stream.seek(start)
    save.character_slots[slot_idx] = UserDataX.read(
        stream, save.is_ps, start, SLOT_DATA_SIZE
    )


def add_regions(save: Save, slot_idx: int, region_ids: Iterable[int]) -> int:
    """Append the ids the slot's Regions list lacks. Returns how many were added.

    Raises ValueError as set_regions does.
    """
    have = save.character_slots[slot_idx].unlocked_regions.region_ids
    new = [rid for rid in dict.fromkeys(region_ids) if rid not in set(have)]
    if new:
        set_regions(save, slot_idx, have + new)
    return len(new)


def unlock(
    save: Save,
    slot_idx: int,
    grace_flags: Iterable[int] = (),
    piece_flags: Iterable[int] = (),
    convergence: bool = False,
) -> UnlockResult:
    """Set grace and map piece flags and add the graces' play regions.

    Regions are added for every given grace, also ones already unlocked.
    """
    grace_flags = list(grace_flags)
    piece_flags = list(piece_flags)
    entered = [
        flag_id
        for map_no in {
            _PIECES_BY_FLAG[f].map_no for f in piece_flags if f in _PIECES_BY_FLAG
        }
        for flag_id in MAP_ENTERED_FLAGS.get(map_no, ())
    ]
    slot = save.character_slots[slot_idx]
    flags = bytearray(slot.event_flags)
    result = UnlockResult()
    for flag_id in grace_flags + piece_flags:
        if EventFlags.get_flag(flags, flag_id):
            continue
        EventFlags.set_flag(flags, flag_id, True)
        if flag_id in piece_flags:
            result.pieces += 1
        else:
            result.graces += 1
    for flag_id in entered:
        EventFlags.set_flag(flags, flag_id, True)
    off = slot.event_flags_offset
    save._raw_data[off : off + len(flags)] = flags
    slot.event_flags = bytes(flags)
    result.fog_cells = update_map_menu(save, slot_idx, piece_flags)

    region_ids = [
        rid for flag_id in grace_flags for rid in grace_region_ids(flag_id, convergence)
    ]
    result.regions = add_regions(save, slot_idx, region_ids)
    return result
