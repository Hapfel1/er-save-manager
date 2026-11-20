"""
Unequip items in the form the game writes for an empty equipment slot.

Equipment slots name items by gaitem handle (plus item id and the item's
position in the held inventory). Removing an equipped item without this
leaves the slot pointing at a handle that no longer exists.

Empty slot as the game writes it, per slot kind:

  arms 1-3 (both hands)  Unarmed (weapon 110000): the handle of an Unarmed
                         entry in the held inventory; several slots may
                         share one
  head/chest/arms/legs   the character's bare placeholder (armor 10000,
                         10100, 10200, 10300) from the held inventory; the
                         armaments mirror stores it with the armor category
  talismans, ammo        item id 0xFFFFFFFF, handle 0, equip index 0xFFFFFFFF
  quick items, pouch     handle 0, equip index 0xFFFFFFFF, mirror 0xFFFFFFFF
  Great Rune             handle 0, equip index 0xFFFFFFFF

The caller must call save.recalculate_checksums() and save.to_file().
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save

EMPTY = 0xFFFFFFFF
UNARMED_ID = 110000
_ARMOR_CATEGORY = 0x10000000
_PREFIX_WEAPON = 0x80000000

WEAPON_SLOTS = (
    "left_hand_armament1",
    "right_hand_armament1",
    "left_hand_armament2",
    "right_hand_armament2",
    "left_hand_armament3",
    "right_hand_armament3",
)
AMMO_SLOTS = ("arrows1", "bolts1", "arrows2", "bolts2", "arrows3", "bolts3")
ARMOR_PLACEHOLDERS = {"head": 10000, "chest": 10100, "arms": 10200, "legs": 10300}
TALISMAN_SLOTS = ("talisman1", "talisman2", "talisman3", "talisman4", "talisman5")


def _held_index(slot, handle: int) -> int:
    """Equip index of a held entry: its key item position, or the key item
    capacity plus its common item position. EMPTY when not held."""
    held = slot.inventory_held
    for i, entry in enumerate(held.key_items):
        if entry.gaitem_handle == handle:
            return i
    for i, entry in enumerate(held.common_items):
        if entry.gaitem_handle == handle:
            return len(held.key_items) + i
    return EMPTY


def _held_placeholder(slot, item_id: int, prefix: int | None, avoid: set[int]):
    """Handle of a held common item whose gaitem has item_id (and handle
    prefix), skipping avoid; None when the character has none."""
    by_handle = {g.gaitem_handle: g for g in slot.gaitem_map if g.gaitem_handle}
    for entry in slot.inventory_held.common_items:
        handle = entry.gaitem_handle
        g = by_handle.get(handle)
        if (
            g is not None
            and handle not in avoid
            and g.item_id == item_id
            and (prefix is None or (handle & 0xF0000000) == prefix)
        ):
            return handle
    return None


def empty_form(slot, key: str, current: int = 0) -> tuple[int, int, int]:
    """(item id, armaments mirror value, handle) the game writes for an empty
    weapon, ammo, armor or talisman slot. current is kept when it already is
    a held placeholder entry for the slot. Weapon and armor slots fall back to
    the EMPTY form when the character holds no placeholder."""
    if key in WEAPON_SLOTS:
        item_id = mirror_id = gaitem_id = UNARMED_ID
        prefix = _PREFIX_WEAPON
    elif key in ARMOR_PLACEHOLDERS:
        item_id = ARMOR_PLACEHOLDERS[key]
        mirror_id = gaitem_id = _ARMOR_CATEGORY | item_id
        prefix = None
    else:
        return EMPTY, EMPTY, 0
    if current and _held_index(slot, current) != EMPTY:
        for g in slot.gaitem_map:
            if g.gaitem_handle == current:
                if g.item_id == gaitem_id:
                    return item_id, mirror_id, current
                break
    handle = _held_placeholder(slot, gaitem_id, prefix, set())
    if handle is None:
        return EMPTY, EMPTY, 0
    return item_id, mirror_id, handle


def blocked(slot, handles: set[int]) -> set[int]:
    """Handles among handles that unequip() would leave equipped: a weapon
    when the character holds no Unarmed entry, armor when it holds no bare
    placeholder for that slot. Changes nothing."""
    equip_handles = slot.equipped_items_gaitem_handle
    out: set[int] = set()
    for key in WEAPON_SLOTS:
        handle = getattr(equip_handles, key)
        if handle in handles and (
            _held_placeholder(slot, UNARMED_ID, _PREFIX_WEAPON, handles) is None
        ):
            out.add(handle)
    for key, bare_id in ARMOR_PLACEHOLDERS.items():
        handle = getattr(equip_handles, key)
        if handle in handles and (
            _held_placeholder(slot, _ARMOR_CATEGORY | bare_id, None, handles) is None
        ):
            out.add(handle)
    return out


def unequip(save: Save, slot_idx: int, handles: set[int]) -> tuple[set, set]:
    """
    Empty every equipment slot that holds one of handles and write the
    equipment structs to the save.

    Returns (handles no slot holds any more, handles still equipped because
    the character has no Unarmed or bare placeholder entry to fall back to).
    """
    slot = save.character_slots[slot_idx]
    ids = slot.equipped_items_item_id
    mirror = slot.equipped_armaments_and_items
    equip_handles = slot.equipped_items_gaitem_handle
    index = slot.equipped_items_equip_index
    items = slot.equipped_items
    kept: set[int] = set()

    def empty(key: str) -> None:
        setattr(ids, key, EMPTY)
        setattr(mirror, key, EMPTY)
        setattr(equip_handles, key, 0)
        setattr(index, key, EMPTY)

    for key in WEAPON_SLOTS:
        handle = getattr(equip_handles, key)
        if handle not in handles:
            continue
        unarmed = _held_placeholder(slot, UNARMED_ID, _PREFIX_WEAPON, handles)
        if unarmed is None:
            kept.add(handle)
            continue
        setattr(ids, key, UNARMED_ID)
        setattr(mirror, key, UNARMED_ID)
        setattr(equip_handles, key, unarmed)
        setattr(index, key, _held_index(slot, unarmed))

    for key, bare_id in ARMOR_PLACEHOLDERS.items():
        handle = getattr(equip_handles, key)
        if handle not in handles:
            continue
        bare = _held_placeholder(slot, _ARMOR_CATEGORY | bare_id, None, handles)
        if bare is None:
            kept.add(handle)
            continue
        setattr(ids, key, bare_id)
        setattr(mirror, key, _ARMOR_CATEGORY | bare_id)
        setattr(equip_handles, key, bare)
        setattr(index, key, _held_index(slot, bare))

    for key in AMMO_SLOTS + TALISMAN_SLOTS:
        if hasattr(equip_handles, key) and getattr(equip_handles, key) in handles:
            empty(key)

    for prefix, entries in (
        ("quickitem", items.quick_items),
        ("pouch", items.pouch_items),
    ):
        for i, entry in enumerate(entries, 1):
            if entry.gaitem_handle in handles:
                entry.gaitem_handle = 0
                entry.equip_index = EMPTY
                if hasattr(mirror, f"{prefix}{i}"):
                    setattr(mirror, f"{prefix}{i}", EMPTY)

    if items.great_rune in handles:
        items.great_rune = 0
        items.great_rune_equip_index = EMPTY

    _patch_equipment(save, slot_idx, slot)
    return set(handles) - kept, kept


def _patch_equipment(save: Save, slot_idx: int, slot) -> None:
    """Write the equipment structs back at their tracked offsets."""
    base = save.slot_data_offset(slot_idx)
    for obj, offset in (
        (slot.equipped_items_equip_index, slot.equipped_items_equip_index_offset),
        (slot.equipped_items_item_id, slot.equipped_items_item_id_offset),
        (slot.equipped_items_gaitem_handle, slot.equipped_items_gaitem_handle_offset),
        (slot.equipped_items, slot.equipped_items_offset),
        (slot.equipped_armaments_and_items, slot.equipped_armaments_and_items_offset),
    ):
        if not offset:
            continue
        buf = BytesIO()
        obj.write(buf)
        data = buf.getvalue()
        save._raw_data[base + offset : base + offset + len(data)] = data
