"""
Elden Ring Item Database
Loads and provides access to all items organized by category.

Files ending in .csv are parsed as structured data with optional param columns.
Files ending in .txt are parsed as plain "id name" per line.

CSV column sets:
  Weapons/Ammo:  ID,Name,reinforcement,aow_allowed,wepType,wepTypeCol,maxArrowQuantity
  Goods:         ID,Name,maxNum,category
  Gems:          ID,Name,compatibleWepTypes  (pipe-separated wepTypeCol values)
  Plain CSV:     ID,Name
"""

import csv as _csv
import re as _re
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

_UPGRADE_SUFFIX_RE = _re.compile(r" \+\s*\d+$")


class ItemCategory(IntEnum):
    """Item categories matching game's encoding"""

    WEAPON = 0x00000000
    ARMOR = 0x10000000
    TALISMAN = 0x20000000
    GOODS = 0x40000000
    GEM = 0x80000000


@dataclass
class Item:
    """Represents an item in the database"""

    id: int
    name: str
    category: ItemCategory
    category_name: str

    # Weapon / ammo fields (populated from weapon CSVs)
    reinforcement: str = "standard"  # standard | somber | none
    aow_allowed: bool = True
    wep_type: int = 0
    wep_type_col: str = ""
    max_arrow_quantity: int = 1
    max_upgrade: int = (
        -1
    )  # -1 = derive from reinforcement; set explicitly for mod overrides

    # Goods fields (populated from goods CSVs)
    max_num: int = 1
    max_repository_num: int = (
        0  # 0 = same as max_num; set from maxRepositoryNum CSV column
    )

    # Gem fields (populated from gem CSVs)
    compatible_wep_types: list = field(default_factory=list)
    default_affinity: str = "Standard"
    allowed_affinities: list = field(default_factory=list)

    # Weapon affinities available under Convergence (vanilla weapons only;
    # convergence-exclusive weapons use allowed_affinities directly)
    convergence_affinities: list = field(default_factory=list)

    @property
    def full_id(self) -> int:
        return self.category | self.id

    def get_affinities(self, is_convergence: bool = False) -> list[str]:
        """Return the affinity list to show for this weapon.

        Convergence saves may unlock additional affinities for vanilla weapons.
        Falls back to allowed_affinities when no convergence list is present.
        """
        if is_convergence and self.convergence_affinities:
            return self.convergence_affinities
        return self.allowed_affinities

    def __str__(self) -> str:
        return self.name


class ItemDatabase:
    """Manages the Elden Ring item database"""

    def __init__(self):
        self.items: list[Item] = []
        self.items_by_id: dict[int, Item] = {}
        self.items_by_category: dict[str, list[Item]] = {}
        self.categories: list[tuple[str, ItemCategory]] = []
        self._loaded = False

    def load(self):
        if self._loaded:
            return

        base_path = Path(__file__).parent / "items"
        categories_file = base_path / "ItemCategories.txt"

        if not categories_file.exists():
            raise FileNotFoundError(
                f"ItemCategories.txt not found at {categories_file}"
            )

        with open(categories_file, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("//"):
                    continue

                parts = line.split(maxsplit=3)
                if len(parts) < 4:
                    continue

                category_hex = parts[0]
                rel_path = parts[2].replace("Items/", "")
                category_name = parts[3]
                category = int(category_hex, 16)

                item_file = base_path / rel_path
                if item_file.exists():
                    self._load_file(item_file, category, category_name)
                    self.categories.append((category_name, ItemCategory(category)))

        self._loaded = True

    def _load_file(self, filepath: Path, category: int, category_name: str):
        is_convergence = "Convergence" in str(filepath)
        if filepath.suffix == ".csv":
            self._load_csv(filepath, category, category_name, is_convergence)
        else:
            self._load_txt(filepath, category, category_name)

    def _load_txt(self, filepath: Path, category: int, category_name: str):
        with open(filepath, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                parts = line.split(maxsplit=1)
                if len(parts) != 2:
                    continue
                try:
                    item_id = int(parts[0])
                    item_name = parts[1].strip()
                    if _UPGRADE_SUFFIX_RE.search(item_name):
                        continue
                    self._register(
                        Item(
                            id=item_id,
                            name=item_name,
                            category=ItemCategory(category),
                            category_name=category_name,
                        )
                    )
                except ValueError:
                    continue

    def _load_csv(
        self,
        filepath: Path,
        category: int,
        category_name: str,
        convergence: bool = False,
    ):
        with open(filepath, encoding="utf-8-sig", newline="") as f:
            reader = _csv.DictReader(f)
            headers = set(reader.fieldnames or [])
            is_weapon = "reinforcement" in headers
            is_goods = "maxNum" in headers
            is_gem = "compatibleWepTypes" in headers

            for row in reader:
                try:
                    item_id = int(row["ID"])
                    item_name = row["Name"].strip()
                except (ValueError, KeyError):
                    continue

                if not item_name:
                    continue
                # Skip upgrade variants unless the file intentionally contains them.
                # Flasks and talismans have distinct +N items that are separate entries.
                _ALLOW_UPGRADES = {"Flasks", "Talismans", "DLCTalismans"}
                if (
                    not is_weapon
                    and not is_gem
                    and filepath.stem not in _ALLOW_UPGRADES
                    and _UPGRADE_SUFFIX_RE.search(item_name)
                ):
                    continue

                item = Item(
                    id=item_id,
                    name=item_name,
                    category=ItemCategory(category),
                    category_name=category_name,
                )

                if is_weapon:
                    item.reinforcement = row.get("reinforcement", "standard")
                    item.aow_allowed = row.get("aow_allowed", "1") == "1"
                    item.wep_type = int(row.get("wepType", 0) or 0)
                    item.wep_type_col = row.get("wepTypeCol", "")
                    item.max_arrow_quantity = int(row.get("maxArrowQuantity", 1) or 1)
                    item.max_num = 1
                    allowed = row.get("allowed_affinities", "")
                    item.allowed_affinities = (
                        [x for x in allowed.split("|") if x] if allowed else []
                    )
                    cnv = row.get("convergence_affinities", "")
                    item.convergence_affinities = (
                        [x for x in cnv.split("|") if x] if cnv else []
                    )
                    # Convergence raises both standard and somber cap to +15
                    if convergence and item.reinforcement in ("standard", "somber"):
                        item.max_upgrade = 15

                elif is_goods:
                    item.max_num = int(row.get("maxNum", 1) or 1)
                    item.max_repository_num = int(row.get("maxRepositoryNum", 0) or 0)

                elif is_gem:
                    compat = row.get("compatibleWepTypes", "")
                    item.compatible_wep_types = compat.split("|") if compat else []
                    item.default_affinity = (
                        row.get("defaultAffinity", "Standard") or "Standard"
                    )
                    allowed = row.get("allowedAffinities", "")
                    item.allowed_affinities = (
                        [x for x in allowed.split("|") if x] if allowed else []
                    )
                    cnv = row.get("convergence_affinities", "")
                    item.convergence_affinities = (
                        [x for x in cnv.split("|") if x] if cnv else []
                    )
                    item.max_num = 1

                self._register(item, is_convergence=convergence)

    def _register(self, item: Item, is_convergence: bool = False):
        self.items.append(item)
        if is_convergence and item.full_id in self.items_by_id:
            # Convergence renames a base-game item under the same ID.
            # Store it separately so non-convergence saves keep the original name.
            if not hasattr(self, "_convergence_overrides"):
                self._convergence_overrides: dict[int, Item] = {}
            self._convergence_overrides[item.full_id] = item
        else:
            self.items_by_id[item.full_id] = item
        # Always register in the category list so browser shows all items.
        if item.category_name not in self.items_by_category:
            self.items_by_category[item.category_name] = []
        self.items_by_category[item.category_name].append(item)

    # ---- public query methods ------------------------------------------------

    def get_item_by_id(
        self, full_item_id: int, is_convergence: bool = False
    ) -> "Item | None":
        if is_convergence and hasattr(self, "_convergence_overrides"):
            return self._convergence_overrides.get(
                full_item_id
            ) or self.items_by_id.get(full_item_id)
        return self.items_by_id.get(full_item_id)

    def get_item_by_base_id(
        self, base_id: int, category: ItemCategory
    ) -> "Item | None":
        return self.items_by_id.get(category | base_id)

    def get_items_by_category(self, category_name: str) -> list[Item]:
        return self.items_by_category.get(category_name, [])

    def get_all_categories(self) -> list[str]:
        return list(self.items_by_category.keys())

    def search_items(self, query: str) -> list[Item]:
        query_lower = query.lower()
        return [item for item in self.items if query_lower in item.name.lower()]

    def decode_item_id(self, full_id: int) -> "tuple[int, ItemCategory]":
        raw_cat = full_id & 0xF0000000
        try:
            category = ItemCategory(raw_cat)
        except ValueError:
            category = ItemCategory.GOODS
        return full_id & 0x0FFFFFFF, category


# ---- global instance --------------------------------------------------------

_item_db = ItemDatabase()


def get_item_database() -> ItemDatabase:
    if not _item_db._loaded:
        _item_db.load()
    return _item_db


# ---- convenience functions --------------------------------------------------


def get_item_name(
    full_item_id: int, upgrade_level: int = 0, is_convergence: bool = False
) -> str:
    db = get_item_database()
    base_id, category = db.decode_item_id(full_item_id)

    # Naked armor placeholder slots
    if category == ItemCategory.ARMOR and base_id in (0, 10000, 10100, 10200, 10300):
        return ""

    item = db.get_item_by_id(full_item_id, is_convergence)
    if item:
        if category == ItemCategory.WEAPON and upgrade_level > 0:
            return f"{item.name} +{upgrade_level}"
        return item.name

    # Ashes: some older saves have item_id = base + upgrade_level (1 per level).
    # Walk back up to 10 steps to find the base entry.
    if category == ItemCategory.GOODS:
        for delta in range(1, 11):
            candidate = category | (base_id - delta)
            item = db.get_item_by_id(candidate)
            if item and "Ashes" in item.category_name:
                return f"{item.name} +{delta}"

    # Weapons: trick weapon alternate forms are base_id + 5000.
    # If the ID is not in the DB, check if base_id - 5000 resolves.
    if category == ItemCategory.WEAPON:
        trick_base = base_id - 5000
        if trick_base > 0:
            item = db.get_item_by_id(category | trick_base, is_convergence)
            if item:
                if upgrade_level > 0:
                    return f"{item.name} +{upgrade_level}"
                return item.name

    # Weapons: strip affinity+upgrade (last 4 digits)
    if category == ItemCategory.WEAPON:
        true_base = (base_id // 10000) * 10000
        item = db.get_item_by_id(category | true_base)
        if item:
            if upgrade_level > 0:
                return f"{item.name} +{upgrade_level}"
            return item.name

    # Weapons/talismans: strip variant suffix - nearest 100 then nearest 10
    if category in (ItemCategory.WEAPON, ItemCategory.TALISMAN):
        for divisor in (100, 10):
            rounded = (base_id // divisor) * divisor
            item = db.get_item_by_id(category | rounded)
            if item:
                if upgrade_level > 0:
                    return f"{item.name} +{upgrade_level}"
                return item.name

    _LABELS = {
        ItemCategory.WEAPON: "Weapon",
        ItemCategory.ARMOR: "Armor",
        ItemCategory.TALISMAN: "Talisman",
        ItemCategory.GOODS: "Goods",
        ItemCategory.GEM: "Gem",
    }
    return f"Unknown {_LABELS.get(category, 'Item')} (ID: {base_id})"


def search_items(query: str) -> list[Item]:
    return get_item_database().search_items(query)


def get_categories() -> list[str]:
    return get_item_database().get_all_categories()
