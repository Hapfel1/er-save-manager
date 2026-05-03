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

import logging
from typing import TYPE_CHECKING

_log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save

_CAT_WEAPON = 0x00000000
_CAT_ARMOR = 0x10000000
_CAT_TALISMAN = 0x20000000
_CAT_GOODS = 0x40000000
_CAT_GEM = 0x80000000

_PREFIX_WEAPON = 0x80000000  # size 21
_PREFIX_ARMOR = 0x90000000  # size 16
_PREFIX_TALISMAN = 0xA0000000  # direct handle, no gaitem entry
_PREFIX_DIRECT = 0xB0000000  # goods and spells direct handle, no gaitem entry
_PREFIX_GEM = 0xC0000000  # size 8

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
    Direct inventory handle (no gaitem entry) for goods, spells, and talismans.

    Talismans use the game-native 0xA0 prefix.
    Goods and spells use 0xB0.
    """
    base = full_item_id & 0x00FFFFFF
    if _category(full_item_id) == _CAT_TALISMAN:
        return (_PREFIX_TALISMAN | base) & 0xFFFFFFFF
    return (_PREFIX_DIRECT | base) & 0xFFFFFFFF


def _next_gaitem_handle(slot, prefix: int) -> int:
    """
    Generate the next available gaitem handle for weapons, armor, or gems.

    Matches the game's own handle format: upper 16 bits encode category
    (0x8080 weapon, 0x9080 armor, 0xC080 gem), lower 16 bits are a sequential
    counter shared across all three categories.

    Uses max_lower16 + 1 across ALL occupied gaitem entries so handles from
    different categories don't collide in the lower-16 counter space.
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
    # Upper 16 bits: weapon=0x8080, armor=0x9080, gem=0xC080
    upper16 = {
        _PREFIX_WEAPON: 0x8080,
        _PREFIX_ARMOR: 0x9080,
        _PREFIX_GEM: 0xC080,
    }[prefix]
    return (upper16 << 16) | next_lower16


def _find_empty_gaitem_slot(slot, prefix: int) -> int:
    """
    Return the gaitem map index of the first suitable empty slot for the given prefix.

    Gems (0xC0) go in the AoW region before the first weapon entry.
    Weapons and armor go after the first weapon entry.
    Returns -1 if no suitable empty slot exists.
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


def _global_next_acq_index(slot) -> int:
    """
    Return the next globally unique acquisition index.

    Scans all occupied slots in both inventories and returns max + 2.
    The +2 step matches the game's own spacing and avoids colliding with
    indices the game assigns between player-added items.
    """
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


def _gaitem_last_empty(slot, slot_data_base: int) -> int | None:
    """
    Return the absolute buffer offset of the last empty (00000000 FFFFFFFF)
    gaitem entry, or None.
    """
    _EMPTY_PATTERN = b"\x00\x00\x00\x00\xff\xff\xff\xff"
    result = None
    for i, g in enumerate(slot.gaitem_map):
        if g.gaitem_handle == 0:
            result = slot_data_base + slot.gaitem_offsets[i]
    return result


def _patch_slot_with_gaitem_insert(
    save: Save,
    slot_idx: int,
    slot,
    gaitem_idx: int,
    new_gaitem_bytes: bytes,
    old_gaitem_size: int,
) -> int:
    """
    Insert/replace a gaitem entry, matching the proven approach from Final.py.

    Returns the net shift applied to all data after the gaitem region (inventory,
    EF, etc.) so the caller can update in-memory offset fields.

    delta == 0 (AoW 8->8):
        Direct overwrite. Net shift = 0.

    delta > 0 (armor 8->16, weapon 8->21):
        1. Pure INSERT new entry at entry_abs.
        2. Delete 8 bytes at last_ga_empty (shifts to last_ga_empty + new_size
           after step 1; we delete from the shifted position).
        3. Trim (new_size - 8) bytes from slot end (guaranteed zero padding).
        Net shift to inventory/EF = new_size - 8 = size_delta.

    delta < 0 (shrink: weapon 21->8 or armor 16->8):
        1. Pure INSERT small entry at entry_abs.
        2. Delete old large entry.
        3. Append abs(delta) zeros at slot end.
        Net shift = size_delta (negative).
    """
    slot_data_base = save._slot_offsets[slot_idx] + CHECKSUM_SIZE
    entry_abs_off = slot_data_base + slot.gaitem_offsets[gaitem_idx]
    new_size = len(new_gaitem_bytes)
    delta = new_size - old_gaitem_size

    _log.debug(
        "gaitem_insert: slot=%d idx=%d entry_rel=0x%X new_size=%d delta=%d inv_rel=0x%X",
        slot_idx,
        gaitem_idx,
        slot.gaitem_offsets[gaitem_idx],
        new_size,
        delta,
        slot.inventory_held_offset,
    )

    if delta == 0:
        save._raw_data[entry_abs_off : entry_abs_off + new_size] = new_gaitem_bytes
        return 0

    if delta > 0:
        # Capture last empty BEFORE insert (its position shifts after step 1)
        last_empty_abs = _gaitem_last_empty(slot, slot_data_base)

        # Step 1: pure INSERT - does not replace old empty, grows buffer by new_size
        save._raw_data[entry_abs_off:entry_abs_off] = new_gaitem_bytes

        # Step 2: delete the last empty (now at last_empty_abs + new_size after insert)
        if last_empty_abs is not None:
            shifted_last_empty = last_empty_abs + new_size
            del save._raw_data[shifted_last_empty : shifted_last_empty + 8]
        else:
            # No empty found - delete from just before the shifted inventory
            inv_abs_shifted = slot_data_base + slot.inventory_held_offset + new_size
            del save._raw_data[inv_abs_shifted - 8 : inv_abs_shifted]

        # Step 3: trim (new_size - 8) bytes from slot end (zero padding after all data)
        trim = new_size - 8
        if trim > 0:
            slot_end = slot_data_base + SLOT_DATA_SIZE
            # After step 1 (+new_size) and step 2 (-8), slot_end shifted by (new_size - 8)
            current_slot_end = slot_end + new_size - 8
            del save._raw_data[current_slot_end - trim : current_slot_end]

        # Net shift to everything after gaitem region = new_size - 8 = delta - (8-8+new_size-8)
        # insert +new_size, delete -8 (before inv), trim -trim (after inv) -> net = new_size-8
        return new_size - 8

    else:
        abs_delta = -delta
        # Step 1: pure INSERT small new entry
        save._raw_data[entry_abs_off:entry_abs_off] = new_gaitem_bytes
        # Step 2: delete the old large entry (now at entry_abs + new_size after insert)
        del save._raw_data[
            entry_abs_off + new_size : entry_abs_off + new_size + old_gaitem_size
        ]
        # Step 3: restore zero padding at slot end
        slot_end = slot_data_base + SLOT_DATA_SIZE - abs_delta
        save._raw_data[slot_end:slot_end] = bytes(abs_delta)
        return -abs_delta


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
    base_id = full_item_id & 0x0FFFFFFF
    g = Gaitem()
    g.gaitem_handle = handle
    # Weapons: no category bits (cat=0x00), embed upgrade in item_id.
    # Armor: category bits (0x10000000) are part of item_id as stored in gaitem.
    # Gems: category bits (0x80000000) are NOT stored - game derives from 0xC0 handle prefix.
    if cat == _CAT_WEAPON:
        g.item_id = base_id + upgrade
    elif cat == _CAT_GEM:
        g.item_id = base_id
    else:
        g.item_id = full_item_id  # armor: 0x10000000 | base fits in int32

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
    gem_full_id: int = 0,
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
        gem_full_id: Full item id of an Ash of War gem to attach to a weapon.
                     0 means no AoW (Standard). Ignored for non-weapon categories.

    Returns:
        Dict with keys: gaitem_handle, full_item_id, quantity, acquisition_index,
        inventory_slot, location, new_common_item_count. For gaitem items also:
        gaitem_slot, gaitem_size.

    Raises:
        ValueError: Unknown category, empty slot, item already present, or full.
    """
    from er_save_manager.parser.equipment import InventoryItem

    # For weapons with AoW: spawn the gem first as a complete add_item so it gets
    # both a gaitem entry and an inventory item. Gem gaitem is delta=0 (size 8),
    # so no offset shifting occurs and the weapon add can continue unchanged.
    gem_handle_for_weapon = 0
    if (
        _category(full_item_id) == _CAT_WEAPON
        and gem_full_id
        and _category(gem_full_id) == _CAT_GEM
    ):
        try:
            gem_result = add_item(save, slot_idx, gem_full_id, 1, location)
            gem_handle_for_weapon = gem_result["gaitem_handle"]
        except Exception as e:
            _log.warning("add_item: gem spawn failed (%s), continuing without AoW", e)

    cat = _category(full_item_id)
    if cat not in (_CAT_WEAPON, _CAT_ARMOR, _CAT_TALISMAN, _CAT_GOODS, _CAT_GEM):
        raise ValueError(
            f"unknown item category 0x{cat:08X} for item 0x{full_item_id:08X}"
        )

    _log.debug(
        "add_item: full_id=0x%08X cat=0x%08X qty=%d location=%s upgrade=%d",
        full_item_id,
        cat,
        quantity,
        location,
        upgrade,
    )

    # Re-read slot: gem add_item may have updated gaitem_map and counters.
    slot = save.character_slots[slot_idx]
    if slot.is_empty():
        raise ValueError(f"slot {slot_idx} is empty")

    inventory = _select_inventory(slot, location)

    gaitem_slot = None
    gaitem_size = None

    if _needs_gaitem(full_item_id):
        from io import BytesIO as _BytesIO

        prefix = _gaitem_prefix(full_item_id)
        handle = _next_gaitem_handle(slot, prefix)

        _log.debug(
            "add_item gaitem: prefix=0x%08X handle=0x%08X",
            prefix,
            handle,
        )

        # Reject if handle already occupied
        for g in slot.gaitem_map:
            if g.gaitem_handle == handle:
                raise ValueError(
                    f"gaitem handle 0x{handle:08X} already in use "
                    f"(item 0x{g.item_id:08X})"
                )

        empty_g = _find_empty_gaitem_slot(slot, prefix)
        if empty_g == -1:
            raise ValueError("gaitem map is full")

        new_gaitem = _make_gaitem(full_item_id, handle, upgrade)

        # Attach AoW handle from the pre-spawned gem gaitem.
        if cat == _CAT_WEAPON and gem_handle_for_weapon:
            new_gaitem.gem_gaitem_handle = (
                gem_handle_for_weapon - 0x100000000
                if gem_handle_for_weapon >= 0x80000000
                else gem_handle_for_weapon
            )
            _log.debug(
                "add_item: linked gem_gaitem_handle=0x%08X", gem_handle_for_weapon
            )

        gaitem_slot = empty_g
        gaitem_size = new_size = new_gaitem.get_size()
        size_delta = new_size - 8

        # Serialize new gaitem entry
        buf = _BytesIO()
        new_gaitem.write(buf)
        new_gaitem_bytes = buf.getvalue()

        slot.gaitem_map[empty_g] = new_gaitem

        _log.debug(
            "add_item gaitem: slot_idx=%d gaitem_slot=%d gaitem_size=%d "
            "bytes=%s inv_held_off=0x%X inv_storage_off=0x%X",
            slot_idx,
            empty_g,
            gaitem_size,
            new_gaitem_bytes.hex(),
            slot.inventory_held_offset,
            slot.inventory_storage_offset,
        )
    else:
        handle = _direct_handle(full_item_id)
        size_delta = 0

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
    # Held counter tracks the globally-last assigned index.
    slot.inventory_held.acquisition_index_counter = acq_idx
    # equip_index_counter must be incremented on every add (spawner: inventory_counters /
    # increment_storage_counter). Storage initialises to 0x80 on first use.
    if location == "storage":
        inv_s = slot.inventory_storage_box
        inv_s.equip_index_counter = (
            0x80 if inv_s.equip_index_counter == 0 else inv_s.equip_index_counter + 1
        )
        inv_s.acquisition_index_counter = acq_idx
    else:
        slot.inventory_held.equip_index_counter += 1

    # Write inventory FIRST (at current offsets, before gaitem insert shifts them)
    _patch_slot(save, slot_idx, slot)

    if gaitem_slot is not None:
        net_shift = _patch_slot_with_gaitem_insert(
            save, slot_idx, slot, gaitem_slot, new_gaitem_bytes, old_gaitem_size=8
        )
        # Update in-memory gaitem offsets: pure insert at entry_rel shifts all
        # subsequent entries by +new_size, then delete last_empty (-8) shifts
        # entries after last_empty by -8. Simplify: entries after entry_rel shift
        # by net_shift (the net effect on inventory/EF = new_size - 8 for expand).
        entry_rel = slot.gaitem_offsets[gaitem_slot]
        for i, off in enumerate(slot.gaitem_offsets):
            if off > entry_rel:
                slot.gaitem_offsets[i] += size_delta
        # Inventory and all post-gaitem data shifted by net_shift in the binary.
        if net_shift != 0:
            slot.inventory_held_offset += net_shift
            slot.inventory_storage_offset += net_shift

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
        from io import BytesIO as _BytesIO

        # Write zeroed 8-byte entry back (empty slot)
        empty_gaitem = Gaitem()
        buf = _BytesIO()
        empty_gaitem.write(buf)
        empty_bytes = buf.getvalue()  # 8 bytes
        _patch_slot_with_gaitem_insert(
            save,
            slot_idx,
            slot,
            gaitem_slot,
            empty_bytes,
            old_gaitem_size=8 - gaitem_size_delta,  # original size before zeroing
        )
        # Update in-memory offsets for gaitem entries after the removed entry
        if gaitem_size_delta != 0:
            for i in range(gaitem_slot + 1, len(slot.gaitem_offsets)):
                slot.gaitem_offsets[i] += gaitem_size_delta
            # Inventory offsets do NOT change: the shrink path pads the slot end
            # to maintain net-zero size change for the gaitem region.

    # Always patch inventory to disk
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
