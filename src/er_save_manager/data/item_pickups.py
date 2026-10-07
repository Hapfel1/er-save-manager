"""
Item pickup flags for Elden Ring (vanilla).

Every row is one ItemLotParam getItemFlagId. The game sets the flag when the
lot is collected and stops placing or awarding the lot while it is set, so
clearing the flag of a world pickup makes it appear again.

Data lives in item_pickups.csv, generated from the vanilla game files only:

    flag        ItemLotParam getItemFlagId (the event flag this checklist
                reads and writes)
    lot         ItemLotParam row id (ItemLotParam_map, or ItemLotParam_enemy
                for enemy drops). Lots with consecutive ids are rolled
                together and share the first lot's flag.
    map         map the lot is placed or awarded in (mAA_BB_CC_DD), empty if
                unknown. Lot and entity ids encode it: 8 digits AABBxxxx is
                mAA_BB_00_00, 10 digits 1AABBxxxxx / 2AABBxxxxx is the open
                world tile m60_AA_BB_00 / m61_AA_BB_00.
    grace_flag  event flag of the nearest Site of Grace (event_flags.json,
                Grace category), 0 if the location is unknown
    source      pickup = MSB treasure (corpse, chest, shiny item)
                enemy  = NpcParam itemLotId drop of a placed enemy
                reward = EMEVD Award Item Lot (bosses, scripted events)
                other  = awarded elsewhere (mostly NPC talk scripts)
    dlc         1 if the map is a Shadow of the Erdtree map
    items       kind:id:quantity separated by "|". kind is goods, weapon,
                armor, talisman or gem; id is the param row id (weapons
                include the upgrade level, e.g. 3070008 = base 3070000 +8)
    names       game item names in the same order, for reading the file;
                used only when the item database lacks an id
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from er_save_manager.data.item_database import (
    ItemCategory,
    get_item_database,
    get_item_name,
)

_KIND_PREFIX = {
    "weapon": ItemCategory.WEAPON,
    "armor": ItemCategory.ARMOR,
    "talisman": ItemCategory.TALISMAN,
    "goods": ItemCategory.GOODS,
    "gem": ItemCategory.GEM,
}

# Goods that raise flask, memory, talisman or spirit ash limits.
_PROGRESSION_IDS = frozenset(
    {
        0x4000271A,  # Golden Seed
        0x40002724,  # Sacred Tear
        0x4000272E,  # Memory Stone
        0x40002738,  # Talisman Pouch
        0x401EAB90,  # Scadutree Fragment
        0x401EABF4,  # Revered Spirit Ash
    }
)

# Item database category name (without "DLC ") -> checklist type
_TYPE_BY_CATEGORY = {
    "Melee Weapons": "Weapons",
    "Ranged Weapons": "Weapons",
    "Shields": "Weapons",
    "Spell Tools": "Weapons",
    "Armor": "Armor",
    "Talismans": "Talismans",
    "Magic": "Spells",
    "Ashes": "Spirit Ashes",
    "Gems": "Ashes of War",
    "Key Items": "Key Items",
    "Tools": "Key Items",
    "Crystal Tears": "Key Items",
    "Merchant Items": "Key Items",
    "Cookbooks": "Key Items",
    "Notes and Paintings": "Key Items",
    "Flasks": "Key Items",
    "Upgrade Materials": "Upgrade Materials",
}
_OTHER = "Consumables and Materials"

PROGRESSION = "Progression"
ITEM_TYPES = [
    PROGRESSION,
    "Weapons",
    "Armor",
    "Talismans",
    "Spells",
    "Spirit Ashes",
    "Ashes of War",
    "Key Items",
    "Upgrade Materials",
    _OTHER,
]

SOURCE_LABELS = {
    "pickup": "Pickup",
    "enemy": "Enemy drop",
    "reward": "Reward",
    "other": "NPC or script",
}


@dataclass(frozen=True)
class Pickup:
    flag_id: int
    lot_id: int
    map_id: str
    grace_flag: int
    source: str
    items: tuple[tuple[int, int, str], ...]  # (full item id, quantity, name)
    is_dlc: bool
    item_type: str

    @property
    def item_label(self) -> str:
        return ", ".join(
            f"{name} x{qty}" if qty > 1 else name for _, qty, name in self.items
        )


def _item_name(full_id: int, fallback: str) -> str:
    upgrade = 0
    if full_id & 0xF0000000 == ItemCategory.WEAPON:
        upgrade = full_id % 100
    name = get_item_name(full_id, upgrade)
    if name.startswith("Unknown ") and fallback:
        return fallback
    return name


def _item_type(full_ids: list[int]) -> str:
    db = get_item_database()
    types = []
    for full_id in full_ids:
        if full_id in _PROGRESSION_IDS:
            return PROGRESSION
        item = db.get_item_by_id(full_id)
        if item is None and full_id & 0xF0000000 == ItemCategory.WEAPON:
            item = db.get_item_by_id(full_id // 10000 * 10000)
        category = item.category_name.removeprefix("DLC ") if item else ""
        types.append(_TYPE_BY_CATEGORY.get(category, _OTHER))
    # A lot mixing types is listed under its most notable item
    return min(types, key=ITEM_TYPES.index) if types else _OTHER


def _parse_items(items: str, names: str) -> tuple[tuple[int, int, str], ...]:
    fallbacks = names.split("|")
    parsed = []
    for k, entry in enumerate(items.split("|")):
        kind, item_id, qty = entry.split(":")
        full_id = _KIND_PREFIX[kind] | int(item_id)
        fallback = fallbacks[k] if k < len(fallbacks) else ""
        parsed.append((full_id, int(qty), _item_name(full_id, fallback)))
    return tuple(parsed)


@cache
def get_pickups() -> tuple[Pickup, ...]:
    path = Path(__file__).parent / "item_pickups.csv"
    pickups = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            items = _parse_items(row["items"], row["names"])
            pickups.append(
                Pickup(
                    flag_id=int(row["flag"]),
                    lot_id=int(row["lot"]),
                    map_id=row["map"],
                    grace_flag=int(row["grace_flag"]),
                    source=row["source"],
                    items=items,
                    is_dlc=row["dlc"] == "1",
                    item_type=_item_type([full_id for full_id, _, _ in items]),
                )
            )
    return tuple(pickups)
