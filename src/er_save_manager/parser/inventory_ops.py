"""
Inventory operations for Elden Ring save files.

Supported categories and their storage mechanism:

  0x00000000  Weapons       gaitem prefix 0x8, size 21 (has gem_gaitem_handle)
  0x10000000  Armor         gaitem prefix 0x9, size 16
  0x20000000  Talismans     A0 direct handle, no gaitem entry
  0x40000000  Goods/Spells  B0 direct handle, no gaitem entry
  0x80000000  Gems/AoW      gaitem prefix 0xC, size 8 - gaitem entry only, no inventory entry

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

_PREFIX_WEAPON = 0x80000000  # gaitem handle prefix, size 21
_PREFIX_ARMOR = 0x90000000  # gaitem handle prefix, size 16
_PREFIX_TALISMAN = 0xA0000000  # direct handle, no gaitem entry
_PREFIX_DIRECT = 0xB0000000  # goods and spells direct handle
_PREFIX_GEM = 0xC0000000  # gaitem handle prefix, size 8

SLOT_DATA_SIZE = 0x280000
CHECKSUM_SIZE = 0x10

# Upgrade caps by reinforcement type
UPGRADE_CAP_STANDARD = 25
UPGRADE_CAP_SOMBER = 10
UPGRADE_CAP_ASH = 10


# ---- category helpers -------------------------------------------------------


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
    """Direct inventory handle for goods, spells, and talismans."""
    base = full_item_id & 0x00FFFFFF
    if _category(full_item_id) == _CAT_TALISMAN:
        return (_PREFIX_TALISMAN | base) & 0xFFFFFFFF
    return (_PREFIX_DIRECT | base) & 0xFFFFFFFF


def validate_upgrade(upgrade: int, reinforcement: str = "standard") -> int:
    """
    Clamp and validate upgrade level for the given reinforcement type.

    Args:
        upgrade: Requested upgrade level.
        reinforcement: "standard" (max 25), "somber" (max 10), or "ash" (max 10).

    Returns:
        Clamped upgrade level.

    Raises:
        ValueError: Unknown reinforcement type.
    """
    caps = {
        "standard": UPGRADE_CAP_STANDARD,
        "somber": UPGRADE_CAP_SOMBER,
        "ash": UPGRADE_CAP_ASH,
    }
    if reinforcement not in caps:
        raise ValueError(f"unknown reinforcement type {reinforcement!r}")
    cap = caps[reinforcement]
    if upgrade < 0 or upgrade > cap:
        raise ValueError(f"{reinforcement} upgrade must be 0-{cap}, got {upgrade}")
    return upgrade


# ---- gaitem map helpers -----------------------------------------------------


def _next_gaitem_handle(slot, prefix: int) -> int:
    """
    Generate the next available gaitem handle for weapons, armor, or gems.

    Upper 16 bits encode category (0x8080 weapon, 0x9080 armor, 0xC080 gem).
    Lower 16 bits are a sequential counter shared across all categories so
    handles from different categories never collide.
    """
    max_lower16 = 0
    for g in slot.gaitem_map:
        if g.gaitem_handle == 0:
            continue
        g_prefix = g.gaitem_handle & 0xF0000000
        if g_prefix in (_PREFIX_WEAPON, _PREFIX_ARMOR, _PREFIX_GEM):
            lower16 = g.gaitem_handle & 0x0000FFFF
            if lower16 > max_lower16:
                max_lower16 = lower16

    next_lower16 = (max_lower16 + 1) & 0xFFFF
    upper16 = {
        _PREFIX_WEAPON: 0x8080,
        _PREFIX_ARMOR: 0x9080,
        _PREFIX_GEM: 0xC080,
    }[prefix]
    return (upper16 << 16) | next_lower16


def _find_empty_gaitem_slot(slot, prefix: int) -> int:
    """
    Return index of the first suitable empty gaitem slot for the given prefix.

    Gems go before the first weapon entry (AoW region).
    Weapons and armor go after the first weapon entry.
    Returns -1 if no suitable slot exists.
    """
    first_weapon_idx = -1
    for i, g in enumerate(slot.gaitem_map):
        if g.gaitem_handle != 0 and (g.gaitem_handle & 0xF0000000) == _PREFIX_WEAPON:
            first_weapon_idx = i
            break

    if prefix == _PREFIX_GEM:
        for i, g in enumerate(slot.gaitem_map):
            if first_weapon_idx != -1 and i >= first_weapon_idx:
                break
            if g.gaitem_handle == 0:
                return i
        return -1

    start = (first_weapon_idx + 1) if first_weapon_idx != -1 else 0
    for i in range(start, len(slot.gaitem_map)):
        if slot.gaitem_map[i].gaitem_handle == 0:
            return i
    return -1


def _find_gaitem_by_item(slot, full_item_id: int):
    """
    Find a gaitem entry matching full_item_id.

    For weapons, matches on base_id (ignores upgrade suffix and infusion code).
    For armor and gems, matches on exact item_id.

    Returns (gaitem_index, gaitem_entry) or (-1, None).
    """
    cat_bits = _category(full_item_id)
    for i, g in enumerate(slot.gaitem_map):
        if g.gaitem_handle == 0:
            continue
        if _category(g.item_id) != cat_bits and cat_bits != _CAT_WEAPON:
            continue
        if cat_bits == _CAT_WEAPON:
            stored_base = (g.item_id & 0x0FFFFFFF) // 10000 * 10000
            want_base = (full_item_id & 0x0FFFFFFF) // 10000 * 10000
            if stored_base == want_base:
                return i, g
        else:
            if g.item_id == full_item_id:
                return i, g
    return -1, None


def _gaitem_last_empty(slot, slot_data_base: int) -> int | None:
    """Return absolute buffer offset of the last empty gaitem entry, or None."""
    result = None
    for i, g in enumerate(slot.gaitem_map):
        if g.gaitem_handle == 0:
            result = slot_data_base + slot.gaitem_offsets[i]
    return result


# ---- inventory helpers ------------------------------------------------------


def _global_next_acq_index(slot) -> int:
    """Return next globally unique acquisition index (max across all inventories + 2)."""
    max_seen = 0
    for inv in (slot.inventory_held, slot.inventory_storage_box):
        for it in inv.common_items:
            if it.gaitem_handle != 0 and it.acquisition_index > max_seen:
                max_seen = it.acquisition_index
        for it in inv.key_items:
            if it.gaitem_handle != 0 and it.acquisition_index > max_seen:
                max_seen = it.acquisition_index
    return min(max_seen + 2, 0xFFFFFFFF)


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


# ---- binary patch helpers ---------------------------------------------------


def _patch_slot(save: Save, slot_idx: int, slot) -> None:
    """
    Write modified inventory bytes directly into save._raw_data.

    Serializes only the affected Inventory structs and patches their exact byte
    ranges, leaving all other slot data untouched.
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


def _patch_slot_with_gaitem_insert(
    save: Save,
    slot_idx: int,
    slot,
    gaitem_idx: int,
    new_gaitem_bytes: bytes,
    old_gaitem_size: int,
) -> int:
    """
    Insert/replace a gaitem entry in the binary slot data.

    Returns the net byte shift applied to everything after the gaitem region
    (inventory, event flags, etc.) so the caller can update in-memory offsets.

    delta == 0: direct overwrite. Net shift = 0.

    delta > 0 (expand, e.g. empty 8 -> armor 16 or weapon 21):
        1. INSERT new entry at entry_abs.
        2. Delete 8 bytes at last_ga_empty (shifted position after step 1).
        3. Trim (new_size - 8) bytes from slot end.
        Net shift = new_size - 8.

    delta < 0 (shrink, e.g. weapon 21 -> empty 8):
        1. INSERT small entry at entry_abs.
        2. Delete old large entry.
        3. Append abs(delta) zeros at slot end.
        Net shift = -(old_size - new_size).
    """
    slot_data_base = save._slot_offsets[slot_idx] + CHECKSUM_SIZE
    entry_abs_off = slot_data_base + slot.gaitem_offsets[gaitem_idx]
    new_size = len(new_gaitem_bytes)
    delta = new_size - old_gaitem_size

    if delta == 0:
        save._raw_data[entry_abs_off : entry_abs_off + new_size] = new_gaitem_bytes
        return 0

    if delta > 0:
        last_empty_abs = _gaitem_last_empty(slot, slot_data_base)

        save._raw_data[entry_abs_off:entry_abs_off] = new_gaitem_bytes

        if last_empty_abs is not None:
            shifted = last_empty_abs + new_size
            del save._raw_data[shifted : shifted + 8]
        else:
            inv_shifted = slot_data_base + slot.inventory_held_offset + new_size
            del save._raw_data[inv_shifted - 8 : inv_shifted]

        trim = new_size - 8
        if trim > 0:
            current_end = slot_data_base + SLOT_DATA_SIZE + new_size - 8
            del save._raw_data[current_end - trim : current_end]

        return new_size - 8

    else:
        abs_delta = -delta
        save._raw_data[entry_abs_off:entry_abs_off] = new_gaitem_bytes
        del save._raw_data[
            entry_abs_off + new_size : entry_abs_off + new_size + old_gaitem_size
        ]
        slot_end = slot_data_base + SLOT_DATA_SIZE - abs_delta
        save._raw_data[slot_end:slot_end] = bytes(abs_delta)
        return -abs_delta


# ---- gaitem construction ----------------------------------------------------


def _make_gaitem(full_item_id: int, handle: int, upgrade: int = 0):
    """
    Create a Gaitem struct for weapons, armor, or gems.

    Weapons: item_id = base_id + upgrade (no category bits, cat = 0x00).
    Armor:   item_id = full_item_id (0x10000000 | base, fits in int32).
    Gems:    item_id = base_id only (0x80000000 bit NOT stored; derived from 0xC0 handle).
    """
    from er_save_manager.parser.er_types import Gaitem

    cat = _category(full_item_id)
    base_id = full_item_id & 0x0FFFFFFF
    g = Gaitem()
    g.gaitem_handle = handle

    if cat == _CAT_WEAPON:
        g.item_id = base_id + upgrade
    elif cat == _CAT_GEM:
        g.item_id = base_id
    else:
        g.item_id = full_item_id  # armor

    if cat in (_CAT_WEAPON, _CAT_ARMOR):
        g.unk0x10 = 0
        g.unk0x14 = 0
        if cat == _CAT_WEAPON:
            g.gem_gaitem_handle = 0
            g.unk0x1c = 0

    return g


# ---- core gaitem operations -------------------------------------------------


def insert_gaitem(
    save: Save,
    slot_idx: int,
    full_item_id: int,
    upgrade: int = 0,
    gem_handle: int = 0,
) -> tuple[int, int]:
    """
    Insert a gaitem entry into the slot's gaitem map without touching inventory.

    Used for AoW gems (which exist only in the gaitem map) and as the first
    step of add_item for weapons and armor.

    Args:
        save: Parsed Save instance.
        slot_idx: Character slot index 0-9.
        full_item_id: Full item id with category bits.
        upgrade: Upgrade level for weapons (0 for others).
        gem_handle: Ash of War handle to link to a weapon gaitem.

    Returns:
        (gaitem_handle, net_shift) - handle assigned to the new entry, and the
        net byte shift applied to everything after the gaitem region.

    Raises:
        ValueError: Category has no gaitem, map is full.
    """
    from io import BytesIO

    if not _needs_gaitem(full_item_id):
        raise ValueError(f"item 0x{full_item_id:08X} does not use a gaitem entry")

    slot = save.character_slots[slot_idx]
    if slot.is_empty():
        raise ValueError(f"slot {slot_idx} is empty")

    prefix = _gaitem_prefix(full_item_id)
    handle = _next_gaitem_handle(slot, prefix)

    empty_g = _find_empty_gaitem_slot(slot, prefix)
    if empty_g == -1:
        raise ValueError("gaitem map is full")

    new_gaitem = _make_gaitem(full_item_id, handle, upgrade)

    if _category(full_item_id) == _CAT_WEAPON and gem_handle:
        new_gaitem.gem_gaitem_handle = (
            gem_handle - 0x100000000 if gem_handle >= 0x80000000 else gem_handle
        )

    buf = BytesIO()
    new_gaitem.write(buf)
    new_gaitem_bytes = buf.getvalue()
    gaitem_size = len(new_gaitem_bytes)
    size_delta = gaitem_size - 8

    slot.gaitem_map[empty_g] = new_gaitem

    net_shift = _patch_slot_with_gaitem_insert(
        save, slot_idx, slot, empty_g, new_gaitem_bytes, old_gaitem_size=8
    )

    entry_rel = slot.gaitem_offsets[empty_g]
    for i, off in enumerate(slot.gaitem_offsets):
        if off > entry_rel:
            slot.gaitem_offsets[i] += size_delta

    if net_shift != 0:
        slot.inventory_held_offset += net_shift
        slot.inventory_storage_offset += net_shift

    return handle, net_shift


def _remove_gaitem(save: Save, slot_idx: int, slot, gaitem_idx: int) -> int:
    """
    Remove a gaitem entry from the slot, replacing it with an empty 8-byte slot.

    Returns the net byte shift (negative = gaitem region shrank).
    """
    from io import BytesIO

    from er_save_manager.parser.er_types import Gaitem

    old_gaitem_size = slot.gaitem_map[gaitem_idx].get_size()
    gaitem_size_delta = 8 - old_gaitem_size

    empty_gaitem = Gaitem()
    buf = BytesIO()
    empty_gaitem.write(buf)
    empty_bytes = buf.getvalue()

    slot.gaitem_map[gaitem_idx] = empty_gaitem

    net_shift = _patch_slot_with_gaitem_insert(
        save,
        slot_idx,
        slot,
        gaitem_idx,
        empty_bytes,
        old_gaitem_size=old_gaitem_size,
    )

    if gaitem_size_delta != 0:
        for i in range(gaitem_idx + 1, len(slot.gaitem_offsets)):
            slot.gaitem_offsets[i] += gaitem_size_delta
        slot.inventory_held_offset += net_shift
        slot.inventory_storage_offset += net_shift

    return net_shift


def _update_inv_counters(slot, inventory, location: str, acq_idx: int) -> None:
    """Update acquisition and equip index counters after adding an inventory entry."""
    slot.inventory_held.acquisition_index_counter = acq_idx
    if location == "storage":
        inv_s = slot.inventory_storage_box
        inv_s.equip_index_counter = (
            0x80 if inv_s.equip_index_counter == 0 else inv_s.equip_index_counter + 1
        )
        inv_s.acquisition_index_counter = acq_idx
    else:
        slot.inventory_held.equip_index_counter += 1


# ---- public API -------------------------------------------------------------


def add_item(
    save: Save,
    slot_idx: int,
    full_item_id: int,
    quantity: int,
    location: str = "held",
    upgrade: int = 0,
    gem_full_id: int = 0,
    reinforcement: str = "standard",
) -> dict:
    """
    Add an item to the character's inventory.

    Args:
        save: Parsed Save instance.
        slot_idx: Character slot index 0-9.
        full_item_id: Full item id including category bits.
        quantity: Stack size (use 1 for weapons/armor/talismans/gems).
        location: "held" or "storage".
        upgrade: Upgrade level. Validated against reinforcement type.
        gem_full_id: Full id of an Ash of War to attach to a weapon. The gem
                     is added to the gaitem map only (no inventory entry).
        reinforcement: "standard", "somber", or "ash" - determines upgrade cap.

    Returns:
        Dict with keys: gaitem_handle, full_item_id, quantity, acquisition_index,
        inventory_slot, location, new_common_item_count.

    Raises:
        ValueError: Unknown category, invalid upgrade, item already present,
                    gaitem map full, or inventory full.
    """
    from er_save_manager.parser.equipment import InventoryItem

    cat = _category(full_item_id)
    if cat not in (_CAT_WEAPON, _CAT_ARMOR, _CAT_TALISMAN, _CAT_GOODS, _CAT_GEM):
        raise ValueError(
            f"unknown item category 0x{cat:08X} for item 0x{full_item_id:08X}"
        )

    if cat == _CAT_WEAPON and upgrade:
        upgrade = validate_upgrade(upgrade, reinforcement)

    # AoW: insert gem into gaitem map only (no inventory entry needed).
    gem_handle = 0
    if cat == _CAT_WEAPON and gem_full_id and _category(gem_full_id) == _CAT_GEM:
        try:
            gem_handle, _ = insert_gaitem(save, slot_idx, gem_full_id)
        except Exception:
            gem_handle = 0  # continue without AoW on failure

    slot = save.character_slots[slot_idx]
    if slot.is_empty():
        raise ValueError(f"slot {slot_idx} is empty")

    inventory = _select_inventory(slot, location)

    handle = None
    gaitem_slot = None

    if _needs_gaitem(full_item_id):
        handle, _ = insert_gaitem(save, slot_idx, full_item_id, upgrade, gem_handle)
        # Re-read slot after insert_gaitem updated offsets
        slot = save.character_slots[slot_idx]
        inventory = _select_inventory(slot, location)
        # Find the gaitem slot we just inserted
        gaitem_slot, _ = _find_gaitem_by_item(slot, full_item_id)
    else:
        handle = _direct_handle(full_item_id)

    # Reject if already in inventory
    for it in inventory.common_items:
        if it.gaitem_handle == handle and it.quantity > 0:
            raise ValueError(
                f"item 0x{full_item_id:08X} already present (handle 0x{handle:08X})"
            )

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
    _update_inv_counters(slot, inventory, location, acq_idx)

    _patch_slot(save, slot_idx, slot)

    return {
        "gaitem_handle": handle,
        "full_item_id": full_item_id,
        "quantity": quantity,
        "acquisition_index": acq_idx,
        "inventory_slot": inv_slot,
        "location": location,
        "new_common_item_count": inventory.common_item_count,
        **({"gaitem_slot": gaitem_slot} if gaitem_slot is not None else {}),
    }


def remove_item(
    save: Save,
    slot_idx: int,
    full_item_id: int,
    location: str = "held",
) -> dict:
    """
    Remove an item from the inventory.

    Zeros the inventory slot, decrements common_item_count, and for gaitem
    items also removes the gaitem map entry.

    Returns:
        Dict with keys: gaitem_handle, full_item_id, inventory_slot, location,
        old_quantity, new_common_item_count.
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

    if _needs_gaitem(full_item_id):
        gaitem_idx, g = _find_gaitem_by_item(slot, full_item_id)
        if gaitem_idx == -1:
            raise ValueError(f"item 0x{full_item_id:08X} not found in gaitem map")
        handle = g.gaitem_handle
    else:
        handle = _direct_handle(full_item_id)
        gaitem_idx = -1

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

    if gaitem_idx != -1:
        _remove_gaitem(save, slot_idx, slot, gaitem_idx)
        # Re-read slot after _remove_gaitem updated offsets
        slot = save.character_slots[slot_idx]
        inventory = _select_inventory(slot, location)

    _patch_slot(save, slot_idx, slot)

    return {
        "gaitem_handle": handle,
        "full_item_id": full_item_id,
        "inventory_slot": inv_slot,
        "location": location,
        "old_quantity": old_qty,
        "new_common_item_count": inventory.common_item_count,
    }


def set_quantity(
    save: Save,
    slot_idx: int,
    full_item_id: int,
    quantity: int,
    location: str = "held",
) -> dict:
    """
    Set the stack quantity of an existing inventory entry.

    Only meaningful for stackable items (goods/spells).

    Returns:
        Dict with keys: gaitem_handle, full_item_id, inventory_slot, location,
        old_quantity, new_quantity.
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
        _, g = _find_gaitem_by_item(slot, full_item_id)
        if g is None:
            raise ValueError(f"item 0x{full_item_id:08X} not found in gaitem map")
        handle = g.gaitem_handle
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
    _patch_slot(save, slot_idx, slot)

    return {
        "gaitem_handle": handle,
        "full_item_id": full_item_id,
        "inventory_slot": inv_slot,
        "location": location,
        "old_quantity": old_qty,
        "new_quantity": quantity,
    }
