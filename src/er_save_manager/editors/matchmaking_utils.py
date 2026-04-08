"""
Elden Ring matchmaking weapon level utilities.

Computes the minimum allowed matchmaking_weapon_level value based on
the highest-tier weapon present in the character's inventory (held +
storage).

Weapon gaitem_handle: 0x80000000 | index
Upgrade level: item_id % 100
Somber vs regular: item_id % 100 > 10 guarantees regular (+25 max);
  <= 10 could be either -- the somber table is used (more restrictive).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.parser.user_data_x import UserDataX

# Matchmaking tier tables indexed by upgrade level.
_REGULAR_TABLE: tuple[int, ...] = (
    0,
    1,
    2,
    3,
    3,
    4,
    4,
    5,
    5,
    5,
    6,
    6,
    7,
    7,
    7,
    7,
    8,
    8,
    8,
    8,
    8,
    9,
    9,
    9,
    9,
    9,
)
_SOMBER_TABLE: tuple[int, ...] = (
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    9,
)

_HANDLE_MASK = 0xF0000000
_WEAPON_HANDLE_BITS = 0x80000000


def _matchmaking_tier(upgrade: int) -> int:
    """
    Return the matchmaking tier for a weapon upgrade level.

    upgrade > 10 is unambiguously a regular weapon; use _REGULAR_TABLE.
    upgrade <= 10 could be somber or regular -- use the more restrictive
    value (somber table gives higher tiers for low upgrade levels).
    """
    if upgrade > 10:
        return _REGULAR_TABLE[upgrade] if upgrade < len(_REGULAR_TABLE) else 9
    regular = _REGULAR_TABLE[upgrade]
    somber = _SOMBER_TABLE[upgrade]
    return max(regular, somber)


def get_max_matchmaking_level(slot: UserDataX) -> int:
    """
    Scan held and storage inventory for weapons and return the highest
    matchmaking tier present.

    Upgrade level is derived from item_id % 100.
    Returns 0 if no upgraded weapons are found.
    """
    gaitem_map_raw = getattr(slot, "gaitem_map", None)
    if not gaitem_map_raw:
        return 0

    # Build handle -> item_id lookup for weapon gaitems only.
    weapon_item_ids: dict[int, int] = {}
    for g in gaitem_map_raw:
        handle = getattr(g, "gaitem_handle", 0)
        if handle == 0 or handle == 0xFFFFFFFF:
            continue
        if (handle & _HANDLE_MASK) != _WEAPON_HANDLE_BITS:
            continue
        weapon_item_ids[handle] = getattr(g, "item_id", 0)

    max_tier = 0

    def _scan_inventory(inventory) -> None:
        nonlocal max_tier
        if inventory is None:
            return
        for inv_item in getattr(inventory, "common_items", []):
            handle = getattr(inv_item, "gaitem_handle", 0)
            if handle == 0 or getattr(inv_item, "quantity", 0) == 0:
                continue
            item_id = weapon_item_ids.get(handle)
            if item_id is None:
                continue
            upgrade = item_id % 100
            if upgrade == 0:
                continue
            tier = _matchmaking_tier(upgrade)
            if tier > max_tier:
                max_tier = tier
            if max_tier == 9:
                return

    _scan_inventory(getattr(slot, "inventory_held", None))
    if max_tier < 9:
        _scan_inventory(getattr(slot, "inventory_storage_box", None))

    return max_tier
