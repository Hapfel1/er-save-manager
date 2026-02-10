"""
Convergence mod item ID mapping and detection.

Handles parsing Convergence item IDs from bundled HEX ID files and detecting
Convergence saves (.cnv and .cnv.co2 formats).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save


# Cache for Convergence item IDs
_CONVERGENCE_ITEMS_CACHE: dict[str, dict[str, int]] = {}


def _get_bundled_hex_dir() -> Path:
    """Get path to bundled Convergence HEX ID files."""
    # Get the data directory where this module is located
    data_dir = Path(__file__).parent
    hex_dir = data_dir / "items" / "Convergence"
    return hex_dir


def parse_convergence_hex_files(
    hex_dir: str | Path | None = None,
) -> dict[str, dict[str, int]]:
    """
    Parse Convergence bundled item list files and extract item mappings.

    Args:
        hex_dir: Path to Convergence items directory. If None, uses bundled files.

    Returns:
        Dict mapping category name to dict of item_name -> item_id
        Example: {"weapons": {"Underworld Dagger": 100590, ...}, ...}
    """
    if hex_dir is None:
        hex_dir = _get_bundled_hex_dir()

    items_by_category: dict[str, dict[str, int]] = {}
    hex_dir = Path(hex_dir)

    if not hex_dir.exists():
        return {}

    item_files = [
        ("weapons", hex_dir / "Weapons" / "ConvergenceMeleeWeapons.txt"),
        ("armor", hex_dir / "Armor" / "ConvergenceArmor.txt"),
        ("spell tools", hex_dir / "Spelltools" / "ConvergenceSpellTools.txt"),
        (
            "keystones and remnants",
            hex_dir / "Goods" / "ConvergenceKeystonesRemnants.txt",
        ),
        ("stones", hex_dir / "Goods" / "ConvergenceStones.txt"),
        ("runes", hex_dir / "Goods" / "ConvergenceRunes.txt"),
        ("notes", hex_dir / "Goods" / "ConvergenceNotes.txt"),
        ("remembrances", hex_dir / "Goods" / "ConvergenceRemembrances.txt"),
    ]

    for category, item_file in item_files:
        if not item_file.exists():
            continue

        items: dict[str, int] = {}
        try:
            with open(item_file, encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line or line.startswith("//"):
                        continue

                    parts = line.split(maxsplit=1)
                    if len(parts) != 2:
                        continue

                    item_id_str, item_name = parts
                    try:
                        item_id = int(item_id_str, 0)
                    except ValueError:
                        continue

                    items[item_name.strip()] = item_id
        except Exception:
            continue

        if items:
            items_by_category[category] = items

    return items_by_category


def parse_convergence_hex_all(hex_dir: str | Path | None = None) -> dict[int, str]:
    """
    Build a lookup of Convergence item IDs to item names from bundled lists.

    Args:
        hex_dir: Path to Convergence items directory. If None, uses bundled files.

    Returns:
        Dict mapping item_id to item name
    """
    items_by_category = parse_convergence_hex_files(hex_dir)
    id_to_name: dict[int, str] = {}
    for items in items_by_category.values():
        for item_name, item_id in items.items():
            id_to_name[item_id] = item_name
    return id_to_name


def is_convergence_save(save_path: str | Path) -> bool:
    """
    Check if a save file is a Convergence mod save.

    Convergence saves use .cnv or .cnv.co2 extensions.

    Args:
        save_path: Path to save file

    Returns:
        True if save is Convergence format
    """
    import logging

    logger = logging.getLogger(__name__)

    path = Path(save_path)
    suffix = path.suffix.lower()
    suffixes = [s.lower() for s in path.suffixes]

    # Check for .cnv or .cnv.co2 extensions
    # .cnv alone = Convergence save
    # .cnv.co2 = Convergence save with encryption
    # .co2 alone = NOT Convergence (these are encrypted vanilla saves)
    is_cnv = suffix == ".cnv"
    is_cnv_co2 = len(suffixes) >= 2 and suffixes[-2:] == [".cnv", ".co2"]
    result = is_cnv or is_cnv_co2

    logger.debug(
        f"[is_convergence_save] path={path.name}, suffix={suffix}, "
        f"suffixes={suffixes}, is_cnv={is_cnv}, is_cnv_co2={is_cnv_co2}, result={result}"
    )

    return result


def detect_convergence_items(
    save: Save, convergence_items: dict[str, dict[str, int]]
) -> dict[str, list[str]]:
    """
    Detect which Convergence custom items are present in the character's inventory.

    Checks all inventory slots for custom item IDs from the Convergence mod.

    Args:
        save: Save instance
        convergence_items: Dict of category -> item_name -> hex_id from parse_convergence_hex_files

    Returns:
        Dict mapping category to list of found item names
    """
    found_items: dict[str, list[str]] = {cat: [] for cat in convergence_items.keys()}

    def collect_item_ids(slot) -> set[int]:
        item_ids: set[int] = set()

        gaitem_map = {}
        if hasattr(slot, "gaitem_map"):
            for gaitem in slot.gaitem_map:
                if getattr(gaitem, "gaitem_handle", 0) != 0xFFFFFFFF:
                    gaitem_map[gaitem.gaitem_handle] = gaitem

        def add_from_inventory(inv) -> None:
            if not inv:
                return

            for inv_item in inv.common_items:
                if inv_item.gaitem_handle != 0 and inv_item.quantity > 0:
                    gaitem = gaitem_map.get(inv_item.gaitem_handle)
                    if gaitem:
                        item_ids.add(gaitem.item_id)

            for inv_item in inv.key_items:
                if inv_item.gaitem_handle != 0 and inv_item.quantity > 0:
                    gaitem = gaitem_map.get(inv_item.gaitem_handle)
                    if gaitem:
                        item_ids.add(gaitem.item_id)

        if hasattr(slot, "inventory_held"):
            add_from_inventory(slot.inventory_held)

        if hasattr(slot, "inventory_storage_box"):
            add_from_inventory(slot.inventory_storage_box)

        equipped = getattr(slot, "equipped_items", None)
        if equipped:
            for weapon in [
                equipped.right_hand_armament1,
                equipped.right_hand_armament2,
                equipped.right_hand_armament3,
                equipped.left_hand_armament1,
                equipped.left_hand_armament2,
                equipped.left_hand_armament3,
            ]:
                if weapon:
                    item_ids.add(weapon)

            for armor in [
                equipped.head_armor,
                equipped.chest_armor,
                equipped.arms_armor,
                equipped.legs_armor,
            ]:
                if armor:
                    item_ids.add(armor)

            for talisman in [
                equipped.talisman_1,
                equipped.talisman_2,
                equipped.talisman_3,
                equipped.talisman_4,
            ]:
                if talisman:
                    item_ids.add(talisman)

        return item_ids

    def iter_match_ids(item_id: int) -> list[int]:
        candidates = [item_id]

        category = item_id & 0xF0000000
        base_id = item_id & 0x0FFFFFFF

        # Try base ID for non-weapon categories stored without category bits
        if category != 0x00000000 and base_id not in candidates:
            candidates.append(base_id)

        # For weapons/catalysts (category 0x0), try stripping variant suffixes
        if category == 0x00000000:
            rounded_base_100 = (base_id // 100) * 100
            rounded_id_100 = category | rounded_base_100
            if rounded_id_100 not in candidates:
                candidates.append(rounded_id_100)

            rounded_base_10 = (base_id // 10) * 10
            rounded_id_10 = category | rounded_base_10
            if rounded_id_10 not in candidates:
                candidates.append(rounded_id_10)

        return candidates

    try:
        # Reverse mapping for quick lookup: hex_id -> (category, item_name)
        id_to_item = {}
        for category, items in convergence_items.items():
            for item_name, item_id in items.items():
                id_to_item[item_id] = (category, item_name)

        # Check all character slots for Convergence items
        for character in save.character_slots:
            if character.is_empty():
                continue

            for item_id in collect_item_ids(character):
                for match_id in iter_match_ids(item_id):
                    if match_id in id_to_item:
                        category, item_name = id_to_item[match_id]
                        if item_name not in found_items[category]:
                            found_items[category].append(item_name)
                        break

    except Exception:
        pass

    # Return only categories with found items
    return {cat: items for cat, items in found_items.items() if items}


def get_convergence_items_for_submission(
    save: Save, save_path: str | Path
) -> dict | None:
    """
    Extract Convergence custom items for character submission.

    If the save is a Convergence save, returns detected custom items using
    bundled Convergence item list files.

    Args:
        save: Save instance
        save_path: Path to save file

    Returns:
        Dict with convergence_detected and custom_items, or None if not Convergence
    """
    import logging

    logger = logging.getLogger(__name__)

    if not save_path:
        logger.debug(
            "[get_convergence_items_for_submission] save_path is None, returning None"
        )
        return None

    logger.debug(
        f"[get_convergence_items_for_submission] Checking save_path: {save_path}"
    )

    if not is_convergence_save(save_path):
        logger.debug(
            "[get_convergence_items_for_submission] Not a Convergence save, returning None"
        )
        return None

    logger.info(
        f"[get_convergence_items_for_submission] Detected Convergence save: {save_path}"
    )

    convergence_data = {
        "convergence_detected": True,
        "custom_items": {},
    }

    # Load bundled Convergence item mappings
    convergence_items = parse_convergence_hex_files()
    if convergence_items:
        found_items = detect_convergence_items(save, convergence_items)
        convergence_data["custom_items"] = found_items
        logger.debug(
            f"[get_convergence_items_for_submission] Found items: {found_items}"
        )

    return convergence_data
