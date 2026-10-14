"""Per-item chest Auto-refill settings (AcquiredProjectiles).

Each entry is (u32 id, u32 on): id is an ammo weapon id or 0x40000000 |
goods id. The game adds an entry when the character first obtains an item
whose autoReplenishType is 1 (default off) or 2 (default on) and the chest's
Auto-refill option flips it. auto_refill_defaults.json holds that param
field for vanilla and the ids Convergence changes.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save

_DEFAULTS = json.loads(
    (Path(__file__).parent.parent / "data" / "auto_refill_defaults.json").read_text(
        encoding="utf-8"
    )
)
_VANILLA = {int(k): v for k, v in _DEFAULTS["vanilla"].items()}
_CONVERGENCE = _VANILLA | {int(k): v for k, v in _DEFAULTS["convergence"].items()}

# Ids other tools leave in the block; not items.
_JUNK_IDS = (0, 0xFFFFFFFF)


def default_on(item_id: int, is_convergence: bool = False) -> bool | None:
    """Default Auto-refill state of an item, None when it has none."""
    kind = (_CONVERGENCE if is_convergence else _VANILLA).get(item_id)
    return None if kind is None else kind == 2


@dataclass
class RefillEntry:
    index: int
    item_id: int
    on: bool
    default: bool | None


def read_entries(save: Save, slot_idx: int) -> list[RefillEntry]:
    slot = save.character_slots[slot_idx]
    is_cnv = bool(save.is_convergence)
    return [
        RefillEntry(i, p.id, p.auto_replenish != 0, default_on(p.id, is_cnv))
        for i, p in enumerate(slot.acquired_projectiles.projectiles)
        if p.id not in _JUNK_IDS
    ]


def write_entries(save: Save, slot_idx: int, entries: list[RefillEntry]) -> int:
    """Write the on/off state of entries into the slot; returns the number changed."""
    slot = save.character_slots[slot_idx]
    projectiles = slot.acquired_projectiles.projectiles
    base = slot.acquired_projectiles_offset + 4
    changed = 0
    for e in entries:
        proj = projectiles[e.index]
        if proj.id != e.item_id:
            raise ValueError(f"Auto-refill entry {e.index} no longer holds {e.item_id}")
        if (proj.auto_replenish != 0) == e.on:
            continue
        value = 1 if e.on else 0
        proj.auto_replenish = value
        off = base + e.index * 8 + 4
        save._raw_data[off : off + 4] = struct.pack("<I", value)
        changed += 1
    return changed
