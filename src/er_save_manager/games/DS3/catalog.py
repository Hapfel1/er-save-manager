"""
DS3 item catalog: the spawnable item lists and per-item limits.

Each game data source (the vanilla game, Convergence, Cinders) has a full
item list, data/items.csv and data/<mod>_items.csv, one row per item,
generated from that source's own files: regulation params for
ids, limits, sort ids and icon ids; its English item text for names and
infusion labels; its item lots, shops and starting gear for the Obtainable
flag. A modded character uses its mod's list for every item, vanilla ones
included, since mods change vanilla items' limits too.

Weapon ids are family * 10000 + infusion index * 100 + upgrade level; list
entries are level 0 and infused weapons carry their infusion's label.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"

SOURCES: dict[str, str] = {
    "vanilla": "Vanilla",
    "convergence": "Convergence",
    "cinders": "Cinders",
}
CATEGORY_LABELS: dict[str, str] = {
    "weapon_items": "Weapons",
    "ammo_items": "Ammo",
    "armor_items": "Armor",
    "ring_items": "Rings",
    "goods_items": "Goods",
}
# Spells are goods; the Spells category is goods_items filtered by this flag.
SPELLS_LABEL = "Spells"

# Placeholders behind empty equipment slots: Fists and the bare Head, Body,
# Arms and Legs. The game never lists them in the inventory, so they are
# neither shown nor offered for spawning.
PLACEHOLDER_IDS = frozenset(
    {0x0001ADB0, 0x100DBBA0, 0x100DBF88, 0x100DC370, 0x100DC758}
)

WEAPON_FAMILY = 10000
INFUSION_STEP = 100

_TYPE_LABELS = {0x0: "Weapon", 0x1: "Armor", 0x2: "Ring", 0x4: "Goods"}
_CATEGORY_FOR_KIND = {
    0x0: "weapon_items",
    0x1: "armor_items",
    0x2: "ring_items",
    0x4: "goods_items",
}

_items: dict[str, dict] = {}
_lookups: dict[str, dict[int, dict]] = {}
_families: dict[str, dict[int, list[dict]]] = {}


def _item_from_row(row: dict[str, str]) -> dict:
    """One CSV row as an item entry. Optional flags are only set when true or
    present, so callers can test membership (Infusion) as with a sparse
    record."""
    item: dict = {
        "_cat": row["category"],
        "Name": row["name"],
        "Id": row["id"],
        "MaxQuantity": int(row["max_quantity"]),
        "MaxUpgrade": int(row["max_upgrade"]),
        "Durability": int(row["durability"]),
        "SortId": int(row["sort_id"]),
        "IconId": int(row["icon_id"]),
        "KeyItem": row["key_item"] == "1",
        "Spell": row["spell"] == "1",
    }
    if row["infusion"]:
        item["Infusion"] = row["infusion"]
    if row.get("obtainable"):
        item["Obtainable"] = row["obtainable"] == "1"
    return item


def items(source: str = "vanilla") -> dict[str, list[dict]]:
    """Category key to item list for a source, in the source's param order."""
    if source not in _items:
        name = "items.csv" if source == "vanilla" else f"{source}_items.csv"
        path = _DATA_DIR / name
        data: dict[str, list[dict]] = {}
        if path.exists():
            with path.open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    item = _item_from_row(row)
                    data.setdefault(item["_cat"], []).append(item)
        _items[source] = data
    return _items[source]


def lookup(item_id: int, source: str = "vanilla") -> dict | None:
    """Item entry for a full item id, ignoring a weapon's upgrade level."""
    if source not in _lookups:
        _lookups[source] = {
            int(item["Id"], 16): item
            for cat_items in items(source).values()
            for item in cat_items
        }
    table = _lookups[source]
    found = table.get(item_id)
    if found is None and item_id >> 28 == 0:
        found = table.get(item_id - item_id % INFUSION_STEP)
    return found


def infusion_index(item_id: int) -> int:
    return item_id % WEAPON_FAMILY // INFUSION_STEP


def infusion_variants(item: dict, source: str = "vanilla") -> list[dict]:
    """Every infusion of the item's weapon family, plain weapon first; a
    single-element list for items without infusions."""
    if "Infusion" not in item:
        return [item]
    if source not in _families:
        families: dict[int, list[dict]] = {}
        for entry in items(source).get("weapon_items", []):
            if "Infusion" in entry:
                families.setdefault(int(entry["Id"], 16) // WEAPON_FAMILY, []).append(
                    entry
                )
        for members in families.values():
            members.sort(key=lambda e: int(e["Id"], 16))
        _families[source] = families
    return _families[source].get(int(item["Id"], 16) // WEAPON_FAMILY, [item])


def category_of(item_id: int, source: str = "vanilla") -> str:
    item = lookup(item_id, source)
    if item is not None:
        return item["_cat"]
    return _CATEGORY_FOR_KIND.get(item_id >> 28, "")


def display_name(item_id: int, source: str = "vanilla") -> str:
    """Item name with a +N suffix for upgraded weapons."""
    entry = lookup(item_id, source)
    if entry is None:
        kind = _TYPE_LABELS.get(item_id >> 28, "Item")
        return f"Unknown {kind} ({item_id:#010x})"
    level = item_id % INFUSION_STEP if item_id >> 28 == 0 else 0
    return f"{entry['Name']} +{level}" if level else entry["Name"]


def is_spell(item: dict) -> bool:
    return bool(item.get("Spell"))


def is_obtainable(item: dict) -> bool:
    """False for items no item lot, shop or starting class of the source hands
    out (scripted rewards are covered where known)."""
    return item.get("Obtainable", True)


@dataclass(frozen=True)
class Limits:
    max_quantity: int
    max_upgrade: int
    durability: int
    sort_key: int
    key_item: bool


def limits(item: dict) -> Limits:
    """Limits for a catalog item. The sort key is for upgrade level 0."""
    kind = int(item["Id"], 16) >> 28
    sort_id = item["SortId"]
    return Limits(
        max_quantity=max(1, item["MaxQuantity"]),
        max_upgrade=item["MaxUpgrade"],
        durability=item["Durability"],
        # Weapons and armor sort by sortId * 100 (plus the weapon's level).
        sort_key=sort_id * 100 if kind in (0x0, 0x1) else sort_id,
        key_item=bool(item.get("KeyItem", False)),
    )
