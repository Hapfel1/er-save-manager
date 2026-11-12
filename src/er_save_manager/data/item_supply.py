"""How many more copies of a limited good a vanilla character can legitimately hold.

items/LimitedSupply.csv lists goods that only one-time sources hand out
(flagged ItemLotParam lots, limited ShopLineupParam stock, flagged EMEVD
item gifts) with the number one playthrough yields. Goods with an
unflagged enemy drop, unlimited shop stock or a crafting recipe are not
listed and have no limit beyond their stack size. The world resets on
each NG+ cycle, so the supply scales with the cycle count.

Spent copies are derived from the character: Golden Seeds from the flask
charge count, Sacred Tears from the flask upgrade level, Scadutree
Fragments and Revered Spirit Ash from the blessing levels.
"""

import csv
from functools import cache
from pathlib import Path

GOLDEN_SEED = 10010
SACRED_TEAR = 10020
SCADUTREE_FRAGMENT = 2010000
REVERED_SPIRIT_ASH = 2010100

# Golden Seeds spent to reach a total flask charge count (4 at the start).
_SEED_COST = (0, 1, 2, 4, 6, 9, 12, 16, 20, 25, 30)
# Items spent to reach each blessing level, index = level.
_SCADUTREE_COST = (0, 1, 3, 5, 7, 9, 11, 13, 15, 17, *range(20, 51, 3))
_REVERED_COST = (0, 1, 2, 3, 5, 7, 10, 13, 16, 20, 25)

_CRIMSON = range(1001, 1026, 2)
_CERULEAN = range(1051, 1076, 2)


@cache
def _supply() -> dict[int, int]:
    path = Path(__file__).parent / "items" / "LimitedSupply.csv"
    with open(path, encoding="utf-8") as f:
        return {int(r["ID"]): int(r["Supply"]) for r in csv.DictReader(f)}


def _owned_goods(slot) -> dict[int, int]:
    owned: dict[int, int] = {}
    for inv in (slot.inventory_held, slot.inventory_storage_box):
        for it in list(inv.common_items) + list(inv.key_items):
            if it.quantity > 0 and it.gaitem_handle >> 28 == 0xB:
                base = it.gaitem_handle & 0x0FFFFFFF
                owned[base] = owned.get(base, 0) + it.quantity
    return owned


def _spent(slot, base_id: int, owned: dict[int, int]) -> int:
    pgd = slot.player_game_data
    if base_id == GOLDEN_SEED:
        charges = pgd.max_crimson_flask_count + pgd.max_cerulean_flask_count
        return _SEED_COST[min(max(charges, 4), 14) - 4]
    if base_id == SACRED_TEAR:
        return max(
            [(i - 1001) // 2 for i in _CRIMSON if i in owned]
            + [(i - 1051) // 2 for i in _CERULEAN if i in owned]
            + [0]
        )
    if base_id == SCADUTREE_FRAGMENT:
        return _SCADUTREE_COST[min(pgd.scadutree_blessing, 20)]
    if base_id == REVERED_SPIRIT_ASH:
        return _REVERED_COST[min(pgd.revered_spirit_ash_blessing, 10)]
    return 0


def remaining_supply(slot, base_id: int) -> int | None:
    """Copies of goods base_id the world still holds for slot, None if unlimited."""
    supply = _supply().get(base_id)
    if supply is None:
        return None
    owned = _owned_goods(slot)
    total = supply * (slot.get_ng_plus() + 1)
    return max(0, total - _spent(slot, base_id, owned) - owned.get(base_id, 0))
