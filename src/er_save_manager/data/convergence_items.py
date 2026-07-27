"""
Convergence mod save detection and item detection.

Detects Convergence saves (.cnv and .cnv.co2 formats) and reports which
Convergence-exclusive items a character has equipped or carries, using the
item database (item_database.py) as the source of truth for item names and
categories.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from er_save_manager.data.item_database import get_item_database

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save


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
    is_cnv = suffix == ".cnv"
    is_cnv_co2 = len(suffixes) >= 2 and suffixes[-2:] == [".cnv", ".co2"]
    result = is_cnv or is_cnv_co2

    logger.debug(
        f"[is_convergence_save] path={path.name}, suffix={suffix}, "
        f"suffixes={suffixes}, is_cnv={is_cnv}, is_cnv_co2={is_cnv_co2}, result={result}"
    )

    return result


def _resolve_convergence_item(full_id: int):
    """
    Look up an item ID against the Convergence entries in the item database.

    Tries the exact ID first, then the base ID with category bits stripped,
    then rounds down to the nearest 100/10 for weapon variant suffixes
    (upgrade level, affinity). Returns None if no Convergence item matches.
    """
    db = get_item_database()

    category = full_id & 0xF0000000
    base_id = full_id & 0x0FFFFFFF

    candidates = [full_id, category | base_id]

    if category == 0x00000000:
        candidates.append(category | ((base_id // 100) * 100))
        candidates.append(category | ((base_id // 10) * 10))

    for candidate in candidates:
        item = db.get_item_by_id(candidate, is_convergence=True)
        if item and item.category_name.startswith("Convergence"):
            return item

    return None


def detect_convergence_items(save: Save) -> dict[str, list[str]]:
    """
    Detect which Convergence-exclusive items are present in each character's
    inventory, equipped slots, and storage box.

    Args:
        save: Save instance

    Returns:
        Dict mapping category name to list of found item names
    """
    found_items: dict[str, list[str]] = {}

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

    try:
        for character in save.character_slots:
            if character.is_empty():
                continue

            for item_id in collect_item_ids(character):
                item = _resolve_convergence_item(item_id)
                if not item:
                    continue

                category = item.category_name
                found_items.setdefault(category, [])
                if item.name not in found_items[category]:
                    found_items[category].append(item.name)

    except Exception:
        pass

    return found_items


def get_convergence_items_for_submission(
    save: Save, save_path: str | Path
) -> dict | None:
    """
    Extract Convergence custom items for character submission.

    If the save is a Convergence save, returns detected custom items using
    the item database's Convergence categories.

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

    found_items = detect_convergence_items(save)
    logger.debug(f"[get_convergence_items_for_submission] Found items: {found_items}")

    return {
        "convergence_detected": True,
        "custom_items": found_items,
    }
