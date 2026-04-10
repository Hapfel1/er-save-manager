"""
Elden Ring matchmaking weapon level utilities.

matchmaking_weapon_level stores a raw upgrade level (0-25 on the regular
scale, 0-10 on the somber scale). The game uses this value directly to
determine the matchmaking range -- it is NOT a pre-mapped tier (0-9).

The floor is the highest upgrade level (item_id % 100) found across all
weapons in held and storage inventory. The stored value may not be set
lower than this without misrepresenting the character's upgrade state.

Weapon gaitem_handle upper nibble: 0x80000000
Upgrade level: item_id % 100
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.parser.user_data_x import UserDataX

_HANDLE_MASK = 0xF0000000
_WEAPON_HANDLE_BITS = 0x80000000


def get_max_weapon_upgrade(slot: UserDataX) -> int:
    """
    Return the highest weapon upgrade level (item_id % 100) found in
    held and storage inventory.

    Returns 0 if no upgraded weapons are present.
    """
    gaitem_map_raw = getattr(slot, "gaitem_map", None)
    if not gaitem_map_raw:
        return 0

    # Build handle -> upgrade level for weapon gaitems only.
    weapon_upgrades: dict[int, int] = {}
    for g in gaitem_map_raw:
        handle = getattr(g, "gaitem_handle", 0)
        if handle == 0 or handle == 0xFFFFFFFF:
            continue
        if (handle & _HANDLE_MASK) != _WEAPON_HANDLE_BITS:
            continue
        upgrade = getattr(g, "item_id", 0) % 100
        if upgrade > 0:
            weapon_upgrades[handle] = upgrade

    if not weapon_upgrades:
        return 0

    max_upgrade = 0

    def _scan_inventory(inventory) -> None:
        nonlocal max_upgrade
        if inventory is None:
            return
        for inv_item in getattr(inventory, "common_items", []):
            handle = getattr(inv_item, "gaitem_handle", 0)
            if handle == 0 or getattr(inv_item, "quantity", 0) == 0:
                continue
            upgrade = weapon_upgrades.get(handle)
            if upgrade is None:
                continue
            if upgrade > max_upgrade:
                max_upgrade = upgrade
            if max_upgrade == 25:
                return

    _scan_inventory(getattr(slot, "inventory_held", None))
    if max_upgrade < 25:
        _scan_inventory(getattr(slot, "inventory_storage_box", None))

    return max_upgrade
