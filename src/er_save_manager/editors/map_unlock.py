"""Unlock graces, map pieces and their play regions in a character slot.

Grace and map piece states are event flags. A grace's play regions
(data/grace_regions.json) go into the slot's Regions list, a u32 count plus
that many u32 ids right before the horse data. Adding ids grows the list, so
every later section moves; the slot keeps its size by dropping as many bytes
from the end of slot.rest, the stale buffer after PlayerGameDataHash. The slot
is parsed again afterwards so later writes use the moved offsets.
"""

from __future__ import annotations

import struct
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

from er_save_manager.data.grace_data import grace_region_ids
from er_save_manager.parser.event_flags import EventFlags
from er_save_manager.parser.inventory_ops import SLOT_DATA_SIZE
from er_save_manager.parser.user_data_x import UserDataX

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save


@dataclass
class UnlockResult:
    graces: int = 0
    pieces: int = 0
    regions: int = 0


def add_regions(save: Save, slot_idx: int, region_ids: Iterable[int]) -> int:
    """Append the ids the slot's Regions list lacks. Returns how many were added.

    Raises ValueError when the parsed list does not match the bytes or the
    slot has no stale tail left to absorb the growth.
    """
    slot = save.character_slots[slot_idx]
    regions = slot.unlocked_regions
    have = set(regions.region_ids)
    new = [rid for rid in dict.fromkeys(region_ids) if rid not in have]
    if not new:
        return 0

    start = slot.data_start
    list_end = slot.horse_offset
    count_off = list_end - 4 - 4 * regions.count
    if struct.unpack_from("<I", save._raw_data, count_off)[0] != regions.count:
        raise ValueError("the Regions list is not where the parse put it")
    grow = 4 * len(new)
    if len(slot.rest) < grow:
        raise ValueError("the slot has no room left for more regions")

    work = save._raw_data[start : start + SLOT_DATA_SIZE]
    struct.pack_into("<I", work, count_off - start, regions.count + len(new))
    work[list_end - start : list_end - start] = struct.pack(f"<{len(new)}I", *new)
    del work[SLOT_DATA_SIZE:]
    save._raw_data[start : start + SLOT_DATA_SIZE] = work

    stream = BytesIO(save._raw_data)
    stream.seek(start)
    save.character_slots[slot_idx] = UserDataX.read(
        stream, save.is_ps, start, SLOT_DATA_SIZE
    )
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
    off = slot.event_flags_offset
    save._raw_data[off : off + len(flags)] = flags
    slot.event_flags = bytes(flags)

    region_ids = [
        rid for flag_id in grace_flags for rid in grace_region_ids(flag_id, convergence)
    ]
    result.regions = add_regions(save, slot_idx, region_ids)
    return result
