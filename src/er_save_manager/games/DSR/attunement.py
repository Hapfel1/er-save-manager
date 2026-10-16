"""Attunement slot costs and limits for DSR.

data/equip_params.json holds, from the game params, each spell's Magic
slotLength and maxQuantity and the rings whose SpEffect changeMagicSlot adds
slots. The slots per Attunement level are not in any param; the table below
is the community wiki's.
"""

from __future__ import annotations

import bisect
import json
from functools import lru_cache
from pathlib import Path

# Attunement level at which the character has 1, 2, ... 10 slots.
_LEVELS = (10, 12, 14, 16, 19, 23, 28, 34, 41, 50)


@lru_cache(maxsize=1)
def _data() -> dict:
    path = Path(__file__).parent / "data" / "equip_params.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def spell(spell_id: int) -> tuple[int, int] | None:
    """(slot cost, Magic maxQuantity) of a spell, None for an unknown id."""
    hit = _data()["spells"].get(str(spell_id))
    return (hit[0], hit[1]) if hit else None


def slots(attunement: int, ring_ids: list[int]) -> int:
    """Attunement slots at an Attunement level with the given rings worn."""
    rings = _data()["slot_items"].get("rings", {})
    return bisect.bisect_right(_LEVELS, attunement) + sum(
        rings.get(str(ring_id), 0) for ring_id in ring_ids
    )
