"""
Crafting material gather nodes for Elden Ring.

A gather node is an MSB asset part (AEGxxx_yyy_iiii) whose
AssetEnvironmentGeometryParam row has a pickUpItemLotParamId. Nodes without
isEnableRepick respawn when the character rests; the save keeps them only
in WorldGeomMan (maps near the player, cleared on rest), so they have no
lasting state. Nodes with isEnableRepick do not respawn: the save lists
them in WorldGeomMan2 for every visited map.

Data lives in gather_nodes.json.gz (vanilla) and
gather_nodes_convergence.json.gz (The Convergence), both from game files:

    aeg   AEG id -> [non_respawning (0/1), [[goods id, quantity], ...]]
    maps  map id -> [[AEG id, part instance, x, y, z, grace flag], ...]
          with the MSB position in the map's local frame and the event flag
          of the Site of Grace nearest on the world map (0 if none)
"""

from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from er_save_manager.data.item_database import ItemCategory, get_item_name
from er_save_manager.data.item_pickups import Pickup

GATHER = "gather"
GATHER_ONCE = "gather_once"
MATERIALS = "Materials"

_DLC_MAP = re.compile(r"m(2[0-8]|4[0-3]|61)_")


@dataclass(frozen=True)
class GatherNode(Pickup):
    """A gather node as a flagless pickup; source is GATHER or GATHER_ONCE.
    items hold the largest quantity of each item, low the smallest."""

    part: str = ""
    low: tuple[int, ...] = ()

    @property
    def item_label(self) -> str:
        return ", ".join(
            name
            if high == 1
            else f"{name} x{low}-{high}"
            if low != high
            else f"{name} x{high}"
            for (_, high, name), low in zip(self.items, self.low, strict=True)
        )

    @property
    def key(self) -> tuple[str, str]:
        return (self.map_id, self.part)

    @property
    def non_respawning(self) -> bool:
        return self.source == GATHER_ONCE


@cache
def get_gather_nodes(is_convergence: bool = False) -> tuple[GatherNode, ...]:
    name = (
        "gather_nodes_convergence.json.gz" if is_convergence else "gather_nodes.json.gz"
    )
    with gzip.open(Path(__file__).parent / name, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    kinds = {}
    for aeg, (once, lot) in data["aeg"].items():
        # A lot rolls one of its rows; rows of one item differ in quantity
        qtys: dict[int, list[int]] = {}
        for goods_id, qty in lot:
            qtys.setdefault(goods_id, []).append(qty)
        items, low = [], []
        for goods_id, found in qtys.items():
            full_id = ItemCategory.GOODS | goods_id
            item = get_item_name(full_id, 0, is_convergence)
            if not item.startswith("Unknown "):
                items.append((full_id, max(found), item))
                low.append(min(found))
        if items:
            kinds[int(aeg)] = (
                GATHER_ONCE if once else GATHER,
                tuple(items),
                tuple(low),
            )
    nodes = []
    for map_id, parts in data["maps"].items():
        for aeg, instance, x, y, z, grace_flag in parts:
            if aeg not in kinds:
                continue
            source, items, low = kinds[aeg]
            nodes.append(
                GatherNode(
                    flag_id=0,
                    lot_id=0,
                    map_id=map_id,
                    grace_flag=grace_flag,
                    source=source,
                    items=items,
                    is_dlc=bool(_DLC_MAP.match(map_id)),
                    item_type=MATERIALS,
                    position=(x, y, z),
                    part=f"AEG{aeg // 1000:03d}_{aeg % 1000:03d}_{instance:04d}",
                    low=low,
                )
            )
    return tuple(nodes)
