"""
Inventory operations for Elden Ring save files.

Supported categories and their storage mechanism:

  0x00000000  Weapons       gaitem prefix 0x8, size 21 (has gem_gaitem_handle)
  0x10000000  Armor         gaitem prefix 0x9, size 16
  0x20000000  Talismans     B0 direct handle, no gaitem entry
  0x40000000  Goods/Spells  B0 direct handle, no gaitem entry
  0x80000000  Gems/AoW      gaitem prefix 0xC, size 8

Talismans share the 0xB0 handle prefix with goods. The game distinguishes them
by base_id context (equip slots vs consumables tab). Avoid talisman base_ids
that also appear in goods files to prevent ambiguous handles.

Acquisition indices are globally unique across held and storage. The held
inventory's acquisition_index_counter is the authoritative global counter.
When adding to storage, indices are drawn from and written back to the held
inventory counter.

All public functions mutate the Save object in place. The caller must call
save.recalculate_checksums() and save.to_file() after all operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save

_CAT_WEAPON = 0x00000000
_CAT_ARMOR = 0x10000000
_CAT_TALISMAN = 0x20000000
_CAT_GOODS = 0x40000000
_CAT_GEM = 0x80000000

_PREFIX_WEAPON = 0x80000000  # size 21
_PREFIX_ARMOR = 0x90000000  # size 16
_PREFIX_DIRECT = 0xB0000000  # goods and talismans, no gaitem entry
_PREFIX_GEM = 0xC0000000  # size 8

# Weapons, armor, and gems share a sequential index space starting here.
_HANDLE_INDEX_FLOOR = 0x80008C

SLOT_DATA_SIZE = 0x280000
CHECKSUM_SIZE = 0x10


def _category(full_item_id: int) -> int:
    return full_item_id & 0xF0000000


def _needs_gaitem(full_item_id: int) -> bool:
    return _category(full_item_id) in (_CAT_WEAPON, _CAT_ARMOR, _CAT_GEM)


def _gaitem_prefix(full_item_id: int) -> int:
    cat = _category(full_item_id)
    if cat == _CAT_WEAPON:
        return _PREFIX_WEAPON
    if cat == _CAT_ARMOR:
        return _PREFIX_ARMOR
    if cat == _CAT_GEM:
        return _PREFIX_GEM
    raise ValueError(f"no gaitem prefix for item 0x{full_item_id:08X}")


def _direct_handle(full_item_id: int) -> int:
    """
    B0-prefix direct inventory handle for goods, spells, and talismans.

    Encodes the lower 24 bits of the base item id with a 0xB0 prefix.
    For talismans, choose base_ids that don't overlap with any goods base_ids
    to avoid the game misidentifying the item.
    """
    return (_PREFIX_DIRECT | (full_item_id & 0x00FFFFFF)) & 0xFFFFFFFF


def _next_sequential_handle_index(slot) -> int:
    """
    Find the first unused index in the shared weapon/armor/gem handle space.

    Occupancy is determined by gaitem_handle != 0. Using item_id as the
    occupancy check is wrong because some valid entries can have item_id=0.
    """
    used = set()
    for g in slot.gaitem_map:
        if g.gaitem_handle == 0:
            continue
        prefix = g.gaitem_handle & 0xF0000000
        if prefix in (_PREFIX_WEAPON, _PREFIX_ARMOR, _PREFIX_GEM):
            used.add(g.gaitem_handle & 0x00FFFFFF)

    if not used:
        return _HANDLE_INDEX_FLOOR

    # Use max+512 rather than max+1. The game expands the gaitem map on every
    # load (adding NPC/world entities with sequential handle indices). A gap of
    # 512 ensures the game's expansion won't consume our assigned index before
    # the player has a chance to load the character.
    return max(sorted(used)[-1] + 512, _HANDLE_INDEX_FLOOR)


def _find_empty_gaitem_slot(slot) -> int:
    """Return index of first gaitem slot with handle == 0, or -1."""
    for i, g in enumerate(slot.gaitem_map):
        if g.gaitem_handle == 0:
            return i
    return -1


def _global_next_acq_index(slot) -> int:
    """
    Return the next globally unique acquisition index.

    The held inventory's acquisition_index_counter is the authoritative global
    counter. Storage items must also draw from this counter so all items across
    both inventories have unique acquisition indices.
    """
    held = slot.inventory_held
    storage = slot.inventory_storage_box

    max_seen = 0
    for inv in (held, storage):
        for it in inv.common_items:
            if it.gaitem_handle != 0 and it.acquisition_index > max_seen:
                max_seen = it.acquisition_index
        for it in inv.key_items:
            if it.gaitem_handle != 0 and it.acquisition_index > max_seen:
                max_seen = it.acquisition_index

    return max(max_seen, held.acquisition_index_counter) + 1


def _first_empty_inv_slot(inventory) -> int:
    """Return index of first common_items slot with gaitem_handle == 0, or -1."""
    for i, it in enumerate(inventory.common_items):
        if it.gaitem_handle == 0:
            return i
    return -1


def _select_inventory(slot, location: str):
    if location == "held":
        return slot.inventory_held
    if location == "storage":
        return slot.inventory_storage_box
    raise ValueError(f"location must be 'held' or 'storage', got {location!r}")


def _patch_slot(save: Save, slot_idx: int, slot) -> None:
    """
    Write modified inventory bytes directly into save._raw_data.

    Serializes only the affected Inventory object and patches its exact byte
    range in the raw file, leaving all other slot data untouched. This avoids
    rebuild_slot which corrupts world structure data when oversized field guards
    clamp sizes to 0.

    Requires inventory_held_offset and inventory_storage_offset to be set on
    the slot object (tracked during parsing in user_data_x.py).
    """
    from io import BytesIO

    slot_data_base = save._slot_offsets[slot_idx] + CHECKSUM_SIZE

    if slot.inventory_held_offset:
        buf = BytesIO()
        slot.inventory_held.write(buf)
        data = buf.getvalue()
        abs_off = slot_data_base + slot.inventory_held_offset
        save._raw_data[abs_off : abs_off + len(data)] = data

    if slot.inventory_storage_offset:
        buf = BytesIO()
        slot.inventory_storage_box.write(buf)
        data = buf.getvalue()
        abs_off = slot_data_base + slot.inventory_storage_offset
        save._raw_data[abs_off : abs_off + len(data)] = data


def _patch_slot_with_rebuild(
    save: Save, slot_idx: int, slot, gaitem_size_delta: int = 0
) -> None:
    """
    Rebuild gaitem section then preserve original world structure bytes.

    rebuild_slot corrupts world structure data when oversized FieldArea/WorldArea
    size fields are clamped to 0. Fix: use the rebuild output for gaitem_map and
    inventory sections, then copy the original bytes back for everything from
    field_area onward.

    gaitem_size_delta is the change in serialized gaitem_map size caused by this
    operation (e.g. +8 for armor add, +13 for weapon add, -8 for remove).
    Everything after gaitem_map shifts by this delta, so the original bytes must
    be sourced from (rebuilt_field_area_start - delta) in the original raw data.
    """
    from er_save_manager.parser.slot_rebuild import rebuild_slot_with_map

    slot_bytes_list, sections = rebuild_slot_with_map(slot)
    slot_bytes = bytearray(slot_bytes_list)

    if len(slot_bytes) != SLOT_DATA_SIZE:
        raise ValueError(
            f"rebuild produced {len(slot_bytes)} bytes, expected {SLOT_DATA_SIZE}"
        )

    # Find where field_area starts in the rebuilt output
    field_area_rebuilt = None
    for sec in sections:
        if sec["name"] == "field_area":
            field_area_rebuilt = sec["start"]
            break

    if field_area_rebuilt is not None and gaitem_size_delta != 0:
        # Source offset in original raw data (before the gaitem size change)
        slot_data_base = save._slot_offsets[slot_idx] + CHECKSUM_SIZE
        original_field_area = field_area_rebuilt - gaitem_size_delta
        original_tail = bytes(
            save._raw_data[
                slot_data_base + original_field_area : slot_data_base + SLOT_DATA_SIZE
            ]
        )
        tail_len = min(len(original_tail), SLOT_DATA_SIZE - field_area_rebuilt)
        slot_bytes[field_area_rebuilt : field_area_rebuilt + tail_len] = original_tail[
            :tail_len
        ]

    offset = save._slot_offsets[slot_idx] + CHECKSUM_SIZE
    save._raw_data[offset : offset + SLOT_DATA_SIZE] = slot_bytes


def _make_gaitem(full_item_id: int, handle: int, upgrade: int = 0):
    """
    Create a Gaitem entry for weapons, armor, or gems.

    Upgrade level is encoded in the item_id suffix (base_id + upgrade), not in
    unk0x10. The Claymore +1 from a real save has item_id = base + 1, unk0x10 = 0,
    which confirms this. unk0x10 purpose is unknown; 0 is safe for all categories.

    unk0x14 must always be 0 - non-zero values corrupt equipped armor slots.
    gem_gaitem_handle is 0 (no ash of war attached by default).
    """
    from er_save_manager.parser.er_types import Gaitem

    cat = _category(full_item_id)
    g = Gaitem()
    # Embed upgrade level in item_id for weapons; armor and gems use base id as-is.
    g.gaitem_handle = handle
    g.item_id = full_item_id + (upgrade if cat == _CAT_WEAPON else 0)

    if cat in (_CAT_WEAPON, _CAT_ARMOR):
        g.unk0x10 = 0
        g.unk0x14 = 0
        if cat == _CAT_WEAPON:
            g.gem_gaitem_handle = 0
            g.unk0x1c = 0

    return g


def add_item(
    save: Save,
    slot_idx: int,
    full_item_id: int,
    quantity: int,
    location: str = "held",
    upgrade: int = 0,
) -> dict:
    """
    Add an item to the inventory.

    Handles all categories:
    - Goods, spells, talismans: B0 direct handle, no gaitem entry.
    - Weapons: 0x8 gaitem entry (size 21), sequential handle index.
    - Armor: 0x9 gaitem entry (size 16), sequential handle index.
    - Gems/AoW: 0xC gaitem entry (size 8), sequential handle index.

    Acquisition indices are globally unique. When adding to storage the held
    inventory's counter is used and updated so subsequent adds remain unique.

    Args:
        save: Parsed Save instance.
        slot_idx: Character slot index 0-9.
        full_item_id: Full item id including category bits.
        quantity: Stack size (use 1 for weapons/armor/talismans/gems).
        location: "held" or "storage".
        upgrade: Upgrade level for weapons. Encoded as item_id = base_id + upgrade.
                 Standard weapons support 0-25, somber weapons 0-10. Ignored for
                 other categories.

    Returns:
        Dict with keys: gaitem_handle, full_item_id, quantity, acquisition_index,
        inventory_slot, location, new_common_item_count. For gaitem items also:
        gaitem_slot, gaitem_size.

    Raises:
        ValueError: Unknown category, empty slot, item already present, or full.
    """
    from er_save_manager.parser.equipment import InventoryItem

    cat = _category(full_item_id)
    if cat not in (_CAT_WEAPON, _CAT_ARMOR, _CAT_TALISMAN, _CAT_GOODS, _CAT_GEM):
        raise ValueError(
            f"unknown item category 0x{cat:08X} for item 0x{full_item_id:08X}"
        )

    slot = save.character_slots[slot_idx]
    if slot.is_empty():
        raise ValueError(f"slot {slot_idx} is empty")

    inventory = _select_inventory(slot, location)

    gaitem_slot = None
    gaitem_size = None

    if _needs_gaitem(full_item_id):
        prefix = _gaitem_prefix(full_item_id)
        idx = _next_sequential_handle_index(slot)
        handle = (prefix | idx) & 0xFFFFFFFF

        # Reject if handle already occupied
        for g in slot.gaitem_map:
            if g.gaitem_handle == handle:
                raise ValueError(
                    f"gaitem handle 0x{handle:08X} already in use "
                    f"(item 0x{g.item_id:08X})"
                )

        empty_g = _find_empty_gaitem_slot(slot)
        if empty_g == -1:
            raise ValueError("gaitem map is full")

        new_gaitem = _make_gaitem(full_item_id, handle, upgrade)
        slot.gaitem_map[empty_g] = new_gaitem
        gaitem_slot = empty_g
        gaitem_size = new_gaitem.get_size()
        # Empty slot was 8 bytes; delta is the expansion
        gaitem_size_delta = gaitem_size - 8
    else:
        handle = _direct_handle(full_item_id)
        gaitem_size_delta = 0

    # Reject if already in inventory
    for it in inventory.common_items:
        if it.gaitem_handle == handle and it.quantity > 0:
            raise ValueError(
                f"item 0x{full_item_id:08X} already present "
                f"(handle 0x{handle:08X} qty={it.quantity})"
            )

    # Acquisition index is globally unique; counter lives in held inventory
    acq_idx = _global_next_acq_index(slot)
    inv_slot = _first_empty_inv_slot(inventory)
    if inv_slot == -1:
        raise ValueError(f"inventory {location!r} is full")

    entry = InventoryItem()
    entry.gaitem_handle = handle
    entry.quantity = quantity
    entry.acquisition_index = acq_idx

    inventory.common_items[inv_slot] = entry
    inventory.common_item_count += 1

    # Always update the held inventory counter regardless of target location
    slot.inventory_held.acquisition_index_counter = acq_idx + 1

    if gaitem_slot is not None:
        _patch_slot_with_rebuild(save, slot_idx, slot, gaitem_size_delta)
    else:
        _patch_slot(save, slot_idx, slot)

    result = {
        "gaitem_handle": handle,
        "full_item_id": full_item_id,
        "quantity": quantity,
        "acquisition_index": acq_idx,
        "inventory_slot": inv_slot,
        "location": location,
        "new_common_item_count": inventory.common_item_count,
    }
    if gaitem_slot is not None:
        result["gaitem_slot"] = gaitem_slot
        result["gaitem_size"] = gaitem_size
    return result


def remove_item(
    save: Save,
    slot_idx: int,
    full_item_id: int,
    location: str = "held",
) -> dict:
    """
    Remove an item from the inventory.

    Zeros the inventory slot and decrements common_item_count. For gaitem items
    (weapons/armor/gems) also zeros the gaitem map entry.

    Args:
        save: Parsed Save instance.
        slot_idx: Character slot index 0-9.
        full_item_id: Full item id including category bits.
        location: "held" or "storage".

    Returns:
        Dict with keys: gaitem_handle, full_item_id, inventory_slot, location,
        old_quantity, new_common_item_count. For gaitem items also: gaitem_slot.

    Raises:
        ValueError: Unknown category, empty slot, or item not found.
    """
    from er_save_manager.parser.equipment import InventoryItem
    from er_save_manager.parser.er_types import Gaitem

    cat = _category(full_item_id)
    if cat not in (_CAT_WEAPON, _CAT_ARMOR, _CAT_TALISMAN, _CAT_GOODS, _CAT_GEM):
        raise ValueError(
            f"unknown item category 0x{cat:08X} for item 0x{full_item_id:08X}"
        )

    slot = save.character_slots[slot_idx]
    if slot.is_empty():
        raise ValueError(f"slot {slot_idx} is empty")

    inventory = _select_inventory(slot, location)

    if _needs_gaitem(full_item_id):
        # The stored gaitem item_id = base_id + upgrade, so exact matching on
        # full_item_id only works for unupgraded items. Match on category bits
        # and the full lower 28 bits with upgrade stripped (base_id <= full_item_id).
        # The simplest correct approach: scan the inventory for a handle whose
        # gaitem entry has the same category bits and whose item_id has the same
        # base (item_id with last two decimal digits zeroed for standard weapons).
        # For exact-match cases (upgrade=0, gems, armor) g.item_id == full_item_id.
        handle = None
        cat_bits = _category(full_item_id)
        for g in slot.gaitem_map:
            if g.gaitem_handle == 0:
                continue
            if _category(g.item_id) != cat_bits:
                continue
            # For weapons: base = (item_id // 100) * 100 (infusion step is 100)
            # Upgrade is the remainder after stripping infusion: item_id % 100
            # So base without upgrade = (item_id // 100) * 100
            # full_item_id passed in should be the base (no upgrade suffix) for lookup
            if cat_bits == _CAT_WEAPON:
                stored_base = (g.item_id & 0x0FFFFFFF) // 100 * 100
                want_base = (full_item_id & 0x0FFFFFFF) // 100 * 100
                if stored_base == want_base:
                    handle = g.gaitem_handle
                    break
            else:
                # Armor and gems: item_id stored as-is, no upgrade suffix
                if g.item_id == full_item_id:
                    handle = g.gaitem_handle
                    break
        if handle is None:
            raise ValueError(f"item 0x{full_item_id:08X} not found in gaitem map")
    else:
        handle = _direct_handle(full_item_id)

    inv_slot = -1
    old_qty = 0
    for i, it in enumerate(inventory.common_items):
        if it.gaitem_handle == handle:
            inv_slot = i
            old_qty = it.quantity
            break

    if inv_slot == -1:
        raise ValueError(
            f"item 0x{full_item_id:08X} not found in {location!r} inventory "
            f"(handle 0x{handle:08X})"
        )

    inventory.common_items[inv_slot] = InventoryItem()
    inventory.common_item_count = max(0, inventory.common_item_count - 1)

    gaitem_slot = None
    gaitem_size_delta = 0
    if _needs_gaitem(full_item_id):
        cat_bits = _category(full_item_id)
        for i, g in enumerate(slot.gaitem_map):
            if g.gaitem_handle == 0:
                continue
            # Match by item_id rather than handle: after game loads, the game
            # renumbers gaitem handles so the handle we wrote may have changed.
            # item_id (which encodes the item type + upgrade) does not change.
            if _category(g.item_id) != cat_bits:
                continue
            id_match = False
            if cat_bits == _CAT_WEAPON:
                id_match = (g.item_id & 0x0FFFFFFF) // 100 * 100 == (
                    full_item_id & 0x0FFFFFFF
                ) // 100 * 100
            else:
                id_match = g.item_id == full_item_id
            if id_match:
                old_gaitem_size = g.get_size()
                # Update handle to match what the game renumbered it to
                handle = g.gaitem_handle
                slot.gaitem_map[i] = Gaitem()
                gaitem_slot = i
                gaitem_size_delta = 8 - old_gaitem_size
                break

    if gaitem_slot is not None:
        _patch_slot_with_rebuild(save, slot_idx, slot, gaitem_size_delta)
    else:
        _patch_slot(save, slot_idx, slot)

    result = {
        "gaitem_handle": handle,
        "full_item_id": full_item_id,
        "inventory_slot": inv_slot,
        "location": location,
        "old_quantity": old_qty,
        "new_common_item_count": inventory.common_item_count,
    }
    if gaitem_slot is not None:
        result["gaitem_slot"] = gaitem_slot
    return result


def set_quantity(
    save: Save,
    slot_idx: int,
    full_item_id: int,
    quantity: int,
    location: str = "held",
) -> dict:
    """
    Set the stack quantity of an existing inventory entry.

    Only meaningful for stackable items (goods/spells). Weapons, armor,
    talismans, and gems always show qty=1 in-game regardless of this value.

    Args:
        save: Parsed Save instance.
        slot_idx: Character slot index 0-9.
        full_item_id: Full item id including category bits.
        quantity: New stack size. Must be >= 1.
        location: "held" or "storage".

    Returns:
        Dict with keys: gaitem_handle, full_item_id, inventory_slot, location,
        old_quantity, new_quantity.

    Raises:
        ValueError: quantity < 1, empty slot, or item not found.
    """
    if quantity < 1:
        raise ValueError(f"quantity must be >= 1, got {quantity}")

    cat = _category(full_item_id)
    if cat not in (_CAT_WEAPON, _CAT_ARMOR, _CAT_TALISMAN, _CAT_GOODS, _CAT_GEM):
        raise ValueError(
            f"unknown item category 0x{cat:08X} for item 0x{full_item_id:08X}"
        )

    slot = save.character_slots[slot_idx]
    if slot.is_empty():
        raise ValueError(f"slot {slot_idx} is empty")

    inventory = _select_inventory(slot, location)

    if _needs_gaitem(full_item_id):
        handle = None
        cat_bits = _category(full_item_id)
        for g in slot.gaitem_map:
            if g.gaitem_handle == 0:
                continue
            if _category(g.item_id) != cat_bits:
                continue
            if cat_bits == _CAT_WEAPON:
                stored_base = (g.item_id & 0x0FFFFFFF) // 100 * 100
                want_base = (full_item_id & 0x0FFFFFFF) // 100 * 100
                if stored_base == want_base:
                    handle = g.gaitem_handle
                    break
            else:
                if g.item_id == full_item_id:
                    handle = g.gaitem_handle
                    break
        if handle is None:
            raise ValueError(f"item 0x{full_item_id:08X} not found in gaitem map")
    else:
        handle = _direct_handle(full_item_id)

    inv_slot = -1
    old_qty = 0
    for i, it in enumerate(inventory.common_items):
        if it.gaitem_handle == handle:
            inv_slot = i
            old_qty = it.quantity
            break

    if inv_slot == -1:
        raise ValueError(
            f"item 0x{full_item_id:08X} not found in {location!r} inventory "
            f"(handle 0x{handle:08X})"
        )

    inventory.common_items[inv_slot].quantity = quantity
    _patch_slot(save, slot_idx, slot)  # quantity-only change, no gaitem modification

    return {
        "gaitem_handle": handle,
        "full_item_id": full_item_id,
        "inventory_slot": inv_slot,
        "location": location,
        "old_quantity": old_qty,
        "new_quantity": quantity,
    }
