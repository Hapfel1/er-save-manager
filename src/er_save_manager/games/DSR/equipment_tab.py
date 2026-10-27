"""DSR equipment: EquipAdapter over a DSRCharacter for the shared equipment
panel."""

from __future__ import annotations

from collections.abc import Hashable

from er_save_manager.games.DSR import attunement, catalog
from er_save_manager.games.DSR.icon_manager import get_icon
from er_save_manager.games.DSR.save import (
    ARMOR_PIECE_STEP,
    ATTUNE_SLOTS,
    BARE_ARMOR_BASE,
    BARE_HAND_ID,
    EQUIP_AMMO,
    EQUIP_ARMOR,
    EQUIP_BOLT_SLOTS,
    EQUIP_HANDS,
    EQUIP_QUICK,
    EQUIP_RINGS,
    KEY_ITEM_SLOTS,
    MAX_INVENTORY_SLOTS,
    DSRCharacter,
    DSRItem,
)
from er_save_manager.ui.editors.ds_equipment import (
    EquipChoice,
    EquipSlot,
    check_attunement,
)

_ARMOR_PIECES = ("Head", "Chest", "Hands", "Legs")
_QUICK_CATEGORIES = frozenset({"consumables"})
# Choice key of a bare armor entry that Clear Slot creates on Apply, as the
# game does on the first unequip of that piece.
_NEW_BARE = "new bare armor"

# (slot number, label, group) in display order.
_SLOTS = (
    (1, "Right hand 1", "Weapons"),
    (3, "Right hand 2", "Weapons"),
    (0, "Left hand 1", "Weapons"),
    (2, "Left hand 2", "Weapons"),
    *((k, _ARMOR_PIECES[i], "Armor") for i, k in enumerate(EQUIP_ARMOR)),
    *((k, f"Ring {i + 1}", "Rings") for i, k in enumerate(EQUIP_RINGS)),
    (EQUIP_AMMO[0], "Arrows 1", "Ammo"),
    (EQUIP_AMMO[2], "Arrows 2", "Ammo"),
    (EQUIP_AMMO[1], "Bolts 1", "Ammo"),
    (EQUIP_AMMO[3], "Bolts 2", "Ammo"),
    *((k, f"Item {i + 1}", "Quick items") for i, k in enumerate(EQUIP_QUICK)),
)


def _placeholder_id(k: int) -> tuple[int, int] | None:
    """(item type, id) of the entry an empty hand or armor slot points at."""
    if k in EQUIP_HANDS:
        return catalog.TYPE_WEAPON, BARE_HAND_ID
    if k in EQUIP_ARMOR:
        return (
            catalog.TYPE_ARMOR,
            BARE_ARMOR_BASE + (k - EQUIP_ARMOR.start) * ARMOR_PIECE_STEP,
        )
    return None


def equip_slots() -> list[EquipSlot]:
    return [EquipSlot(k, label, group) for k, label, group in _SLOTS]


class DSREquipAdapter:
    def __init__(self, char: DSRCharacter) -> None:
        self.char = char
        self._held = [
            char.read_item(i)
            for i in range(KEY_ITEM_SLOTS, MAX_INVENTORY_SLOTS)
            if not char.read_item(i).is_empty
        ]
        self._by_key = {self._key(item): item for item in self._held}
        seen: dict[str, int] = {}
        self._names: dict[Hashable, str] = {}
        for item in self._held:
            placeholder = self._placeholder_name(item)
            if placeholder is not None:
                self._names[self._key(item)] = placeholder
                continue
            name = catalog.display_name(item.category, item.item_id)
            seen[name] = seen.get(name, 0) + 1
            self._names[self._key(item)] = (
                name if seen[name] == 1 else f"{name} ({seen[name]})"
            )
        # Attunement records hold spell ids, so the spell keys are ids.
        self.loaded_spells: list[int] = char.attuned_spells()
        self.spells: list[int] = list(self.loaded_spells)

    @staticmethod
    def _key(item: DSRItem) -> Hashable:
        return (item.slot_index, item.item_id)

    @staticmethod
    def _category(item: DSRItem) -> str:
        hit = catalog.lookup(item.category, item.item_id)
        return hit[0]["category"] if hit else ""

    def _choice(self, item: DSRItem) -> EquipChoice:
        hit = catalog.lookup(item.category, item.item_id)
        icon_id = hit[0]["icon_id"] if hit else None
        return EquipChoice(
            self._key(item),
            self._names[self._key(item)],
            catalog.CATEGORY_LABELS.get(self._category(item), "Other"),
            lambda: get_icon(icon_id),
        )

    @staticmethod
    def _placeholder_name(item: DSRItem) -> str | None:
        """Name for a bare hand or bare armor entry, which have no catalog
        row."""
        if (item.category, item.item_id) not in catalog.PLACEHOLDERS:
            return None
        if item.category == catalog.TYPE_WEAPON:
            return "Bare hand"
        piece = (item.item_id - BARE_ARMOR_BASE) // ARMOR_PIECE_STEP
        return f"Bare {_ARMOR_PIECES[piece].lower()}"

    @staticmethod
    def _is_placeholder(item: DSRItem) -> bool:
        return (item.category, item.item_id) in catalog.PLACEHOLDERS

    def accepts(self, k: int, item: DSRItem) -> bool:
        if self._is_placeholder(item):
            return False
        category = self._category(item)
        if k in EQUIP_HANDS:
            return item.category == catalog.TYPE_WEAPON and category == "weapons"
        if k in EQUIP_ARMOR:
            return (
                item.category == catalog.TYPE_ARMOR
                and item.item_id // ARMOR_PIECE_STEP % 10 == k - EQUIP_ARMOR.start
            )
        if k in EQUIP_RINGS:
            return item.category == catalog.TYPE_RING
        if k in EQUIP_AMMO:
            return (
                item.category == catalog.TYPE_WEAPON
                and category == "ammo"
                and self.char.is_bolt(item.item_id) == (k in EQUIP_BOLT_SLOTS)
            )
        if k in EQUIP_QUICK:
            return item.category == catalog.TYPE_GOODS and category in _QUICK_CATEGORIES
        return False

    # ---- EquipAdapter ----------------------------------------------------------

    def slots(self) -> list[EquipSlot]:
        return equip_slots()

    def current(self, slot_key: Hashable) -> EquipChoice | None:
        slot, _cached_id = self.char.equip_slot(slot_key)
        if not KEY_ITEM_SLOTS <= slot < MAX_INVENTORY_SLOTS:
            return None
        item = self.char.read_item(slot)
        if item.is_empty:
            return None
        return self._choice(item)

    def choices(self, slot_key: Hashable) -> list[EquipChoice]:
        return [self._choice(i) for i in self._held if self.accepts(slot_key, i)]

    def clear_choice(self, slot_key: Hashable) -> EquipChoice | None:
        wanted = _placeholder_id(slot_key)
        if wanted is None:
            return None
        candidates = [i for i in self._held if (i.category, i.item_id) == wanted]
        if candidates:
            return self._choice(candidates[0])
        if slot_key in EQUIP_ARMOR:
            piece = _ARMOR_PIECES[slot_key - EQUIP_ARMOR.start]
            return EquipChoice(
                (_NEW_BARE, wanted[1]), f"Bare {piece.lower()}", "Armor", lambda: None
            )
        raise ValueError(
            "The character has no bare hand entry in its inventory, so this "
            "slot cannot be emptied here. Unequip it in game instead."
        )

    def shared(self, choice_key: Hashable) -> bool:
        item = self._by_key.get(choice_key)
        return item is not None and self._is_placeholder(item)

    # ---- attunement --------------------------------------------------------------

    def spell_choices(self) -> list[EquipChoice]:
        """Held spells not in the staged attunement list, one per id."""
        out: dict[int, EquipChoice] = {}
        for item in self._held:
            if (
                item.category == catalog.TYPE_GOODS
                and attunement.spell(item.item_id) is not None
                and item.item_id not in self.spells
                and item.item_id not in out
            ):
                choice = self._choice(item)
                out[item.item_id] = EquipChoice(
                    item.item_id, choice.name, choice.category, choice.icon
                )
        return list(out.values())

    def spell_name(self, key: Hashable) -> str:
        return catalog.display_name(catalog.TYPE_GOODS, key)

    def spell_cost(self, key: Hashable) -> int | None:
        info = attunement.spell(key)
        return info[0] if info else None

    def attunement_budget(self, staged: dict) -> int | None:
        rings = []
        for k in EQUIP_RINGS:
            if k in staged:
                choice = staged[k]
                if choice is not None:
                    rings.append(choice.key[1])
            else:
                slot, item_id = self.char.equip_slot(k)
                if slot != 0xFFFFFFFF:
                    rings.append(item_id)
        return attunement.slots(self.char.get_stat("atn"), rings)

    @property
    def spells_changed(self) -> bool:
        return self.spells != self.loaded_spells

    # ---- writing -----------------------------------------------------------------

    def apply(self, staged: dict) -> None:
        """Write staged picks into the character data. Raises ValueError,
        before writing anything, when a picked entry changed since the panel
        loaded."""
        resolved = []
        for slot_key, choice in staged.items():
            slot = None
            if choice is not None and choice.key[0] == _NEW_BARE:
                resolved.append((slot_key, choice.key))
                continue
            if choice is not None:
                slot, item_id = choice.key
                item = self.char.read_item(slot)
                if item.is_empty or item.item_id != item_id:
                    raise ValueError(
                        f"{choice.name} moved in the inventory. Reload the "
                        "character and pick it again."
                    )
                if not (self.accepts(slot_key, item) or self._is_placeholder(item)):
                    raise ValueError(f"{choice.name} does not fit this slot.")
            resolved.append((slot_key, slot))
        spells = []
        for spell_id in self.spells if self.spells_changed else ():
            info = attunement.spell(spell_id)
            if info is None:
                raise ValueError(f"Spell {spell_id} has no Magic param row.")
            spells.append((spell_id, info[1]))
        if len(self.spells) > ATTUNE_SLOTS:
            raise ValueError(f"At most {ATTUNE_SLOTS} spells can be attuned.")
        check_attunement(
            sum(self.spell_cost(k) or 0 for k in self.spells),
            self.attunement_budget(staged),
            self.attunement_budget({}),
            self.spells_changed,
        )
        new_entries = sum(1 for _k, slot in resolved if isinstance(slot, tuple))
        free = sum(
            1
            for i in range(KEY_ITEM_SLOTS, MAX_INVENTORY_SLOTS)
            if self.char.read_item(i).is_empty
        )
        if new_entries > free:
            raise ValueError("The inventory is full; no room for a bare armor entry.")
        for slot_key, slot in resolved:
            if isinstance(slot, tuple):
                slot = self._create_bare_armor(slot[1])
            self.char.set_equip(slot_key, slot)
        if self.spells_changed:
            self.char.attune(spells)

    def _create_bare_armor(self, item_id: int) -> int:
        """Add the bare armor entry the game creates on the first unequip of
        a piece: quantity 1, sort key 0, durability 0."""
        return self.char.add_item(catalog.TYPE_ARMOR, item_id, 1)
