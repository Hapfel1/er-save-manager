"""
Limited merchant stock for Elden Ring.

ShopLineupParam eventFlag_forStock is the first bit of a purchase counter:
the number bought, stored LSB-first in bit_length(sellQuantity) consecutive
event flags. The row is sold out when the counter reaches sellQuantity;
clearing the bits restocks it.

Data lives in shop_stock.csv (vanilla) and shop_stock_convergence.csv (The
Convergence). Columns:

    row         ShopLineupParam row id
    flag        eventFlag_forStock, the counter's lowest bit
    quantity    sellQuantity
    item        kind:id (kind is goods, weapon, armor, talisman or gem)
    price       rune cost
    merchant    NPC whose talk script opens the shop range holding the row
    map         where that NPC stands (mAA_BB_CC_DD)
    grace_flag  event flag of the nearest Site of Grace, 0 if unknown
    dlc         1 if the map is a Shadow of the Erdtree map
    name        game item name, used when the item database lacks the id
"""

from __future__ import annotations

import csv
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


@dataclass(frozen=True)
class StockRow:
    row_id: int
    flag_id: int
    quantity: int
    item_id: int  # full item id
    item_name: str
    price: int
    merchant: str
    map_id: str
    grace_flag: int
    is_dlc: bool

    @property
    def counter_flags(self) -> range:
        """Event flags holding the purchase count, lowest bit first."""
        return range(self.flag_id, self.flag_id + self.quantity.bit_length())


def bought(row: StockRow, get_flag) -> int:
    """Number bought, read from the counter through get_flag(flag_id)."""
    return sum(int(bool(get_flag(f))) << k for k, f in enumerate(row.counter_flags))


@cache
def get_stock(is_convergence: bool = False) -> tuple[StockRow, ...]:
    name = "shop_stock_convergence.csv" if is_convergence else "shop_stock.csv"
    rows: dict[int, StockRow] = {}
    with (Path(__file__).parent / name).open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            kind, item_id = r["item"].split(":")
            full_id = _KIND_PREFIX[kind] | int(item_id)
            item_name = get_item_name(full_id, 0, is_convergence)
            if item_name.startswith("Unknown "):
                item_name = r["name"]
            # Rows selling the same item can share one counter
            rows.setdefault(
                int(r["flag"]),
                StockRow(
                    row_id=int(r["row"]),
                    flag_id=int(r["flag"]),
                    quantity=int(r["quantity"]),
                    item_id=full_id,
                    item_name=item_name,
                    price=int(r["price"]),
                    merchant=r["merchant"],
                    map_id=r["map"],
                    grace_flag=int(r["grace_flag"]),
                    is_dlc=r["dlc"] == "1",
                ),
            )
    return tuple(rows.values())
