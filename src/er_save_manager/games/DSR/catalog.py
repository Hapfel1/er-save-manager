"""
DSR item catalog: spawnable items and their limits.

data/items.csv is generated from the game's own files: EquipParam* rows for
ids, sort ids, icon ids, durability and stack sizes, ReinforceParam* for
upgrade caps, the item text for names, and item lots, shops and starting
classes for the obtainable flag (smithed and ascended weapons count when
their source weapon does). data/seamless_items.csv lists the goods the
Seamless Co-op mod adds at runtime (row fields read from ds1sc.dll).

Weapon ids are family * 1000 + infusion * 100 + upgrade level, except per-
level families such as the Pyromancy Flame, whose upgrades are rows 100
apart (level_step 100). Soul weapons keep their source weapon's infusion
digit; those rows are hidden (they resolve held items but are not spawned).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"

TYPE_WEAPON, TYPE_ARMOR, TYPE_RING, TYPE_GOODS = 0, 1, 2, 4

CATEGORY_LABELS: dict[str, str] = {
    "weapons": "Weapons",
    "ammo": "Ammo",
    "armor": "Armor",
    "rings": "Rings",
    "consumables": "Consumables",
    "materials": "Materials",
    "key_items": "Key Items",
    "spells": "Spells",
    "seamless": "Seamless Co-op",
}

INFUSIONS = [
    "Normal",
    "Crystal",
    "Lightning",
    "Raw",
    "Magic",
    "Enchanted",
    "Divine",
    "Occult",
    "Fire",
    "Chaos",
]
INFUSION_STEP = 100
WEAPON_FAMILY = 1000

# Placeholders the game keeps behind empty equipment slots: Fists and the
# bare head, chest, hands and legs. Never listed or spawned.
PLACEHOLDERS = frozenset(
    {
        (TYPE_WEAPON, 900000),
        (TYPE_ARMOR, 900000),
        (TYPE_ARMOR, 901000),
        (TYPE_ARMOR, 902000),
        (TYPE_ARMOR, 903000),
    }
)

# A character holds a single Estus Flask; each level and charge state is its
# own goods id (even = empty, odd = filled).
ESTUS_IDS = range(200, 216)

_INT_FIELDS = (
    "id",
    "type",
    "max_quantity",
    "max_upgrade",
    "level_step",
    "durability",
    "sort_id",
    "icon_id",
)
_FLAG_FIELDS = ("key_item", "spell", "obtainable", "hidden")


def _read(name: str, seamless: bool = False) -> list[dict]:
    path = _DATA_DIR / name
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            item: dict = {k: int(row[k]) for k in _INT_FIELDS}
            item.update({k: row[k] == "1" for k in _FLAG_FIELDS})
            item["category"] = row["category"]
            item["name"] = row["name"]
            item["infusion"] = row["infusion"]
            item["seamless"] = seamless
            out.append(item)
    return out


_items: list[dict] | None = None
_by_id: dict[tuple[int, int], tuple[dict, int]] | None = None
_families: dict[int, list[dict]] | None = None


def items() -> list[dict]:
    """Every catalog entry, Seamless Co-op goods last."""
    global _items
    if _items is None:
        _items = _read("items.csv") + _read("seamless_items.csv", seamless=True)
    return _items


def lookup(item_type: int, item_id: int) -> tuple[dict, int] | None:
    """(entry, upgrade level) for a held item's type and full id."""
    global _by_id
    if _by_id is None:
        _by_id = {}
        for e in items():
            for level in range(e["max_upgrade"] + 1):
                _by_id.setdefault(
                    (e["type"], e["id"] + level * e["level_step"]), (e, level)
                )
    return _by_id.get((item_type, item_id))


def infusion_variants(item: dict) -> list[dict]:
    """The spawnable infusions of a weapon's family, plain first; [item]
    when it has none."""
    global _families
    if not item["infusion"]:
        return [item]
    if _families is None:
        _families = {}
        for e in items():
            if e["type"] == TYPE_WEAPON and e["infusion"] and not e["hidden"]:
                _families.setdefault(e["id"] // WEAPON_FAMILY, []).append(e)
    return _families.get(item["id"] // WEAPON_FAMILY, [item])


def infusion_index(item: dict) -> int:
    return item["id"] % WEAPON_FAMILY // INFUSION_STEP


def item_id_at(item: dict, level: int) -> int:
    return item["id"] + level * item["level_step"]


def sort_key(item: dict, level: int = 0) -> int:
    """Inventory sort key: sortId * 100 + level for weapons and armor, the
    sortId for everything else (checked against every held item)."""
    if item["type"] in (TYPE_WEAPON, TYPE_ARMOR):
        return item["sort_id"] * 100 + level
    return item["sort_id"]


def display_name(item_type: int, item_id: int) -> str:
    hit = lookup(item_type, item_id)
    if hit is None:
        return f"Unknown ({item_type:#x}, {item_id})"
    entry, level = hit
    return f"{entry['name']} +{level}" if level else entry["name"]


def is_single(item: dict) -> bool:
    """True for items a character may hold only one of (the Estus Flask)."""
    return item["type"] == TYPE_GOODS and item["id"] in ESTUS_IDS


@dataclass(frozen=True)
class Limits:
    max_quantity: int
    max_upgrade: int
    durability: int


def limits(item: dict) -> Limits:
    return Limits(max(1, item["max_quantity"]), item["max_upgrade"], item["durability"])
