"""
Elden Ring matchmaking weapon level utilities.

matchmaking_weapon_level is stored on the 0-25 standard upgrade scale.
Somber weapons must be mapped to their standard equivalent before storing:

  Somber +1=3, +2=5, +3=7, +4=9, +5=12, +6=15, +7=18, +8=20, +9=22, +10=25

The floor is the highest mapped upgrade level found across all weapons in
held and storage inventory. The stored value may not be set lower than this.

Weapon gaitem_handle prefix: 0x80000000
Somber detection: materialSetId == 2200 in params, but we detect via
  upgrade range: item_id % 100 <= 10 with the weapon having a known somber
  base ID. Since we don't have params at runtime, we use the heuristic that
  any weapon whose item_id % 100 is in 1-10 AND whose base_id is in the somber
  set is somber - but that requires DB access.

Simpler runtime approach: map upgrade=N using the somber table if N <= 10,
otherwise treat as standard. This is safe because standard upgrades in the
1-10 range always map to themselves on the standard scale anyway (standard +5
= mm level 5, somber +5 = mm level 12). We must use the higher of the two
interpretations to avoid under-reporting, so we use the somber mapping for
any weapon with upgrade <= 10 whose somber-mapped value > raw value.

Actually the correct approach: check the gaitem's item_id base against the
item database to get reinforcement type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.parser.user_data_x import UserDataX

_HANDLE_MASK = 0xF0000000
_WEAPON_HANDLE = 0x80000000

# Somber upgrade level -> standard matchmaking scale
_SOMBER_TO_MM = {
    0: 0,
    1: 3,
    2: 5,
    3: 7,
    4: 9,
    5: 12,
    6: 15,
    7: 18,
    8: 20,
    9: 22,
    10: 25,
}


def somber_to_mm(upgrade: int) -> int:
    """Map a somber upgrade level (0-10) to the matchmaking scale (0-25)."""
    return _SOMBER_TO_MM.get(upgrade, upgrade)


def _is_somber_weapon(base_id: int) -> bool:
    """
    Check whether a weapon base ID is somber using the item database.
    Falls back to False if the DB is unavailable.
    """
    try:
        from er_save_manager.data.item_database import get_item_database

        db = get_item_database()
        item = db.get_item_by_id(base_id)
        if item is None:
            # Try stripping affinity code
            stripped = (base_id & 0x0FFFFFFF) // 10000 * 10000
            item = db.get_item_by_id(stripped)
        return (
            item is not None and getattr(item, "reinforcement", "standard") == "somber"
        )
    except Exception:
        return False


def weapon_mm_level(item_id: int) -> int:
    """
    Return the matchmaking level for a weapon given its stored item_id.

    Standard weapons: mm_level = item_id % 100
    Somber weapons:   mm_level = somber_to_mm(item_id % 100)
    """
    upgrade = item_id % 100
    if upgrade == 0:
        return 0
    base_id = (item_id // 100) * 100
    if _is_somber_weapon(base_id):
        return somber_to_mm(upgrade)
    return upgrade


def get_max_weapon_upgrade(slot: UserDataX) -> int:
    """
    Return the highest matchmaking weapon level found across all weapons
    in held and storage inventory.

    Somber weapons are mapped to their standard-scale equivalent so the
    returned value is always on the 0-25 standard scale.
    """
    gaitem_map_raw = getattr(slot, "gaitem_map", None)
    if not gaitem_map_raw:
        return 0

    # Build handle -> mm_level for weapon gaitems only.
    weapon_mm: dict[int, int] = {}
    for g in gaitem_map_raw:
        handle = getattr(g, "gaitem_handle", 0)
        if handle == 0 or handle == 0xFFFFFFFF:
            continue
        if (handle & _HANDLE_MASK) != _WEAPON_HANDLE:
            continue
        item_id = getattr(g, "item_id", 0)
        upgrade = item_id % 100
        if upgrade > 0:
            weapon_mm[handle] = weapon_mm_level(item_id)

    if not weapon_mm:
        return 0

    max_mm = 0

    def _scan(inventory) -> None:
        nonlocal max_mm
        if inventory is None:
            return
        for inv_item in getattr(inventory, "common_items", []):
            handle = getattr(inv_item, "gaitem_handle", 0)
            if handle == 0 or getattr(inv_item, "quantity", 0) == 0:
                continue
            mm = weapon_mm.get(handle)
            if mm is None:
                continue
            if mm > max_mm:
                max_mm = mm
            if max_mm == 25:
                return

    _scan(getattr(slot, "inventory_held", None))
    if max_mm < 25:
        _scan(getattr(slot, "inventory_storage_box", None))

    return max_mm
