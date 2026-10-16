"""Equipment param data for DS3 and the supported mods: attunement slot
costs and limits, and the goods kept out of quick item slots.

data/equip_params.json holds, per source and from its params, each spell's
Magic slotLength, the items whose SpEffect changeMagicSlot adds slots
(rings: EquipParamAccessory refId with refCategory 2) and the goods with
goodsType 2 (upgrade materials and gems). The slots per Attunement level are
not in any param; the table below is the community wiki's for vanilla DS3
and is used for every source.
"""

from __future__ import annotations

import bisect
import json
from functools import cache, lru_cache
from pathlib import Path

# Attunement level at which the character has 1, 2, ... 10 slots.
_LEVELS = (10, 14, 18, 24, 30, 40, 50, 60, 80, 99)
_ID_MASK = 0x0FFFFFFF


@lru_cache(maxsize=1)
def _data() -> dict:
    path = Path(__file__).parent / "data" / "equip_params.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _source(source: str) -> dict:
    data = _data()
    return data.get(source, data["vanilla"])


def spell_cost(spell_id: int, source: str = "vanilla") -> int | None:
    """Slot cost of a spell (goods id, type nibble optional), None when it
    has no Magic row."""
    return _source(source)["spells"].get(str(spell_id & _ID_MASK))


@cache
def _materials(source: str) -> frozenset[int]:
    return frozenset(_source(source)["materials"])


def is_material(goods_id: int, source: str = "vanilla") -> bool:
    """Whether a good (type nibble optional) is an upgrade material or gem;
    those are not offered for quick item slots."""
    return goods_id & _ID_MASK in _materials(source)


def slots(attunement: int, item_ids: list[int], source: str = "vanilla") -> int:
    """Attunement slots at an Attunement level with the given items
    (full ids with the type nibble) equipped."""
    bonus = _source(source)["slot_items"]
    return bisect.bisect_right(_LEVELS, attunement) + sum(
        bonus.get(hex(item_id), 0) for item_id in item_ids
    )
