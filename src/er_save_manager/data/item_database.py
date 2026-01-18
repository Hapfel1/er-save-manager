"""
Elden Ring Item Database
Loads and provides access to all items organized by category
"""

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path


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
    category_name: str  # Human-readable category (e.g., "Melee Weapons", "Consumables")

    @property
    def full_id(self) -> int:
        """Get full item ID with category bits"""
        return self.category | self.id

    def __str__(self):
        return self.name


class ItemDatabase:
    """Manages the Elden Ring item database"""

    def __init__(self):
        self.items: list[Item] = []
        self.items_by_id: dict[int, Item] = {}  # full_id -> Item
        self.items_by_category: dict[str, list[Item]] = {}
        self.categories: list[tuple[str, ItemCategory]] = []
        self._loaded = False

    def load(self):
        """Load all items from resource files"""
        if self._loaded:
            return

        base_path = Path(__file__).parent / "items"
        categories_file = base_path / "ItemCategories.txt"

        if not categories_file.exists():
            raise FileNotFoundError(
                f"ItemCategories.txt not found at {categories_file}"
            )

        # Parse category definitions
        with open(categories_file, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("//"):
                    continue

                # Format: 0x00000000 false Items/Weapons/MeleeWeapons.txt Melee Weapons
                parts = line.split(maxsplit=3)
                if len(parts) < 4:
                    continue

                category_hex = parts[0]
                # parts[1] is show_ids (ignored for now)
                rel_path = parts[2].replace("Items/", "")  # Remove Items/ prefix
                category_name = parts[3]

                category = int(category_hex, 16)

                # Load items from the specified file
                item_file = base_path / rel_path
                if item_file.exists():
                    self._load_items_from_file(item_file, category, category_name)
                    self.categories.append((category_name, ItemCategory(category)))

        self._loaded = True

    def _load_items_from_file(self, filepath: Path, category: int, category_name: str):
        """Load items from a single file"""
        with open(filepath, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("//"):
                    continue

                # Format: "item_id item_name"
                parts = line.split(maxsplit=1)
                if len(parts) != 2:
                    continue

                try:
                    item_id = int(parts[0])
                    item_name = parts[1].strip()

                    item = Item(
                        id=item_id,
                        name=item_name,
                        category=ItemCategory(category),
                        category_name=category_name,
                    )

                    self.items.append(item)
                    self.items_by_id[item.full_id] = item

                    if category_name not in self.items_by_category:
                        self.items_by_category[category_name] = []
                    self.items_by_category[category_name].append(item)

                except ValueError:
                    continue

    def get_item_by_id(self, full_item_id: int) -> Item | None:
        """Get item by full ID (with category bits)"""
        return self.items_by_id.get(full_item_id)

    def get_item_by_base_id(self, base_id: int, category: ItemCategory) -> Item | None:
        """Get item by base ID and category"""
        full_id = category | base_id
        return self.items_by_id.get(full_id)

    def get_items_by_category(self, category_name: str) -> list[Item]:
        """Get all items in a category"""
        return self.items_by_category.get(category_name, [])

    def get_all_categories(self) -> list[str]:
        """Get list of all category names"""
        return list(self.items_by_category.keys())

    def search_items(self, query: str) -> list[Item]:
        """Search for items by name (case-insensitive)"""
        query_lower = query.lower()
        return [item for item in self.items if query_lower in item.name.lower()]

    def get_weapon_with_upgrade(self, base_id: int, upgrade_level: int) -> str:
        """Get weapon name with upgrade level"""
        # For weapons, base_id might include upgrade level in last 2 digits
        # Extract actual base
        actual_base = (base_id // 100) * 100

        item = self.get_item_by_base_id(actual_base, ItemCategory.WEAPON)
        if item:
            if upgrade_level > 0:
                return f"{item.name} +{upgrade_level}"
            return item.name

        return f"Unknown Weapon ({base_id})"

    def decode_item_id(self, full_id: int) -> tuple[int, ItemCategory]:
        """Decode full item ID into base ID and category"""
        category = ItemCategory(full_id & 0xF0000000)
        base_id = full_id & 0x0FFFFFFF
        return base_id, category


# Global instance
_item_db = ItemDatabase()


def get_item_database() -> ItemDatabase:
    """Get the global item database instance"""
    if not _item_db._loaded:
        _item_db.load()
    return _item_db


# Convenience functions
def get_item_name(full_item_id: int, upgrade_level: int = 0) -> str:
    """Get item name from full ID, with optional upgrade level for weapons"""
    db = get_item_database()
    base_id, category = db.decode_item_id(full_item_id)

    if category == ItemCategory.WEAPON and upgrade_level > 0:
        return db.get_weapon_with_upgrade(base_id, upgrade_level)

    item = db.get_item_by_id(full_item_id)
    if item:
        return item.name

    return f"Unknown Item (0x{full_item_id:08X})"


def search_items(query: str) -> list[Item]:
    """Search for items by name"""
    db = get_item_database()
    return db.search_items(query)


def get_categories() -> list[str]:
    """Get all item category names"""
    db = get_item_database()
    return db.get_all_categories()
