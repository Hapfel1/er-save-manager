"""
Merchants of Elden Ring with their position and full shop lineup.

merchants.json (merchants_convergence.json for The Convergence) holds one row
per merchant part: [name, map, x, y, z, grace_flag, lineup], where the
position is the MSB part of the NPC whose talk script opens the shop ranges
(see shop_stock for the assignment) and grace_flag the nearest Site of
Grace. Each lineup row is

    [ShopLineupParam row, "kind:id", item name, price, costType,
     sellQuantity (-1 unlimited), eventFlag_forStock (0 unlimited),
     eventFlag_forRelease (0 always on sale)]

Limited rows count purchases in their stock flags like shop_stock.StockRow:
bit_length(quantity) flags, LSB first. A row with a release flag is only on
sale once that flag is set. costType 0 prices are in runes.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from er_save_manager.data.item_database import ItemCategory, get_item_name

_KIND_PREFIX = {
    "weapon": ItemCategory.WEAPON,
    "armor": ItemCategory.ARMOR,
    "talisman": ItemCategory.TALISMAN,
    "goods": ItemCategory.GOODS,
    "gem": ItemCategory.GEM,
}
RUNES = 0


@dataclass(frozen=True)
class ShopItem:
    row_id: int
    item_id: int  # full item id
    name: str
    price: int
    cost_type: int
    quantity: int  # -1 when unlimited
    flag_id: int  # first purchase counter flag, 0 when unlimited
    release_flag: int  # 0 when always on sale

    @property
    def limited(self) -> bool:
        return self.quantity > 0

    @property
    def counter_flags(self) -> range:
        """Event flags holding the purchase count, lowest bit first."""
        if not self.limited:
            return range(0)
        return range(self.flag_id, self.flag_id + self.quantity.bit_length())

    def bought(self, get_flag: Callable[[int], bool | None]) -> int:
        return sum(
            int(bool(get_flag(f))) << k for k, f in enumerate(self.counter_flags)
        )

    def counter_changes(self, count: int) -> dict[int, bool]:
        """Flag writes that set the purchase count (0 restocks, quantity
        sells out)."""
        return {f: bool(count >> k & 1) for k, f in enumerate(self.counter_flags)}


@dataclass(frozen=True)
class Merchant:
    name: str
    map_id: str
    position: tuple[float, float, float]
    grace_flag: int
    lineup: tuple[ShopItem, ...]


@cache
def get_merchants(is_convergence: bool = False) -> tuple[Merchant, ...]:
    name = "merchants_convergence.json" if is_convergence else "merchants.json"
    rows = json.loads((Path(__file__).parent / name).read_text(encoding="utf-8"))
    # One NPC can stand at one spot with several parts (Seluvis): merge them
    merged: dict[tuple[str, str], list] = {}
    for npc, map_id, x, y, z, grace_flag, lineup in rows:
        entry = merged.setdefault((npc, map_id), [(x, y, z), grace_flag, []])
        entry[2].extend(lineup)
    merchants = []
    for (npc, map_id), (pos, grace_flag, lineup) in merged.items():
        items = []
        for row_id, item, fallback, price, cost, qty, flag, release in lineup:
            kind, item_id = item.split(":")
            full_id = _KIND_PREFIX[kind] | int(item_id)
            name_ = get_item_name(full_id, 0, is_convergence)
            items.append(
                ShopItem(
                    row_id,
                    full_id,
                    fallback if name_.startswith("Unknown ") else name_,
                    price,
                    cost,
                    qty,
                    flag,
                    release,
                )
            )
        merchants.append(Merchant(npc, map_id, pos, grace_flag, tuple(items)))
    return tuple(merchants)
