"""
Collected state of non-respawning gather nodes (Arteria Leaf, gloveworts,
lilies, smithing stone nodes).

Picking such a node adds its MSB part to WorldGeomMan2 (state 1) and to
WorldGeomMan (state 3, 2 after the next rest); the lot has no event flag.
WorldGeomMan2 has a record for every map the character visited, so a node
can be marked collected only on a visited map. The item itself is neither
given nor taken.
"""

from __future__ import annotations

import struct
from io import BytesIO
from typing import TYPE_CHECKING

from er_save_manager.parser.inventory_ops import SLOT_DATA_SIZE
from er_save_manager.parser.user_data_x import UserDataX
from er_save_manager.parser.world import WorldGeomData, WorldGeomEntry

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save

# WorldGeomMan2 entry state, and the WorldGeomMan state kept after a rest
_STATE_PICKED = 1
_STATE_PERMANENT = 2


def _record(data: WorldGeomData, map_id: str):
    return next((r for r in data.records if r.map_name == map_id), None)


def _write_geom(save: Save, slot_idx: int, which: str, data: WorldGeomData):
    """Replace WorldGeomMan ("world_geom_man") or WorldGeomMan2 with data;
    the rest of the slot moves, its zero tail absorbing the size change."""
    slot = save.character_slots[slot_idx]
    old = getattr(slot, which)
    off = getattr(slot, f"{which}_offset")
    start = slot.data_start
    body = data.to_bytes()
    grow = len(body) - len(old.data)
    if len(slot.rest) < grow:
        raise ValueError("the slot has no room left for more entries")
    work = save._raw_data[start : start + SLOT_DATA_SIZE]
    work[off - start : off - start + 4 + len(old.data)] = (
        struct.pack("<i", len(body)) + body
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


def set_node_collected(
    save: Save, slot_idx: int, map_id: str, part: str, collected: bool
) -> None:
    """Mark a non-respawning node (map id, MSB part AEGaaa_bbb_iiii)
    collected, or remove it from both lists so the node appears again.

    Raises ValueError when the lists do not decode, or when marking it
    collected on a map the character never visited.
    """
    aeg = int(part[3:6]) * 1000 + int(part[7:10])
    instance = int(part[11:])
    model = 10000000 + aeg
    slot = save.character_slots[slot_idx]

    def matches(e: WorldGeomEntry) -> bool:
        return e.model == model and e.instance == instance

    foeg = slot.world_geom_man2.parse_geom()
    if foeg is None:
        raise ValueError("the collected node list could not be read")
    record = _record(foeg, map_id)
    if collected:
        if record is None:
            raise ValueError(
                "the character has not visited this area yet; the game "
                "lists collected nodes only for visited areas"
            )
        if not any(matches(e) for e in record.entries):
            record.entries.append(WorldGeomEntry(instance << 15 | _STATE_PICKED, model))
            _write_geom(save, slot_idx, "world_geom_man2", foeg)
    elif record is not None and any(matches(e) for e in record.entries):
        record.entries = [e for e in record.entries if not matches(e)]
        _write_geom(save, slot_idx, "world_geom_man2", foeg)

    # WorldGeomMan holds maps near the character only
    slot = save.character_slots[slot_idx]
    moeg = slot.world_geom_man.parse_geom()
    record = _record(moeg, map_id) if moeg is not None else None
    if record is None:
        return
    kept = [e for e in record.entries if not matches(e)]
    if collected:
        kept.append(WorldGeomEntry(instance << 15 | _STATE_PERMANENT, model))
    if kept != record.entries:
        record.entries = kept
        _write_geom(save, slot_idx, "world_geom_man", moeg)
