"""DS3 equipment: EquipAdapter over a DS3Slot for the shared equipment panel."""

from __future__ import annotations

from collections.abc import Hashable

from er_save_manager.games.DS3 import attunement, catalog
from er_save_manager.games.DS3.icon_manager import item_icon
from er_save_manager.games.DS3.slot import (
    ATTUNE_SLOTS,
    EQUIP_AMMO,
    EQUIP_ARMOR,
    EQUIP_COVENANT,
    EQUIP_RINGS,
    ID_GOOD,
    QUICK_SLOTS,
    DS3InventoryEntry,
    DS3Slot,
    id_kind,
)
from er_save_manager.ui.editors.ds_equipment import (
    EquipChoice,
    EquipSlot,
    check_attunement,
)

_ARMOR_PIECES = ("Head", "Chest", "Hands", "Legs")

# (slot number, label, group) in display order: right hand first as in game.
_SLOTS = (
    (1, "Right hand 1", "Weapons"),
    (3, "Right hand 2", "Weapons"),
    (5, "Right hand 3", "Weapons"),
    (0, "Left hand 1", "Weapons"),
    (2, "Left hand 2", "Weapons"),
    (4, "Left hand 3", "Weapons"),
    *((k, _ARMOR_PIECES[i], "Armor") for i, k in enumerate(EQUIP_ARMOR)),
    (EQUIP_AMMO[0], "Arrows 1", "Ammo"),
    (EQUIP_AMMO[2], "Arrows 2", "Ammo"),
    (EQUIP_AMMO[1], "Bolts 1", "Ammo"),
    (EQUIP_AMMO[3], "Bolts 2", "Ammo"),
    *((k, f"Ring {i + 1}", "Rings and covenant") for i, k in enumerate(EQUIP_RINGS)),
    (EQUIP_COVENANT, "Covenant", "Rings and covenant"),
    *((("quick", k), f"Item {k + 1}", "Quick items") for k in range(QUICK_SLOTS)),
)


def equip_slots() -> list[EquipSlot]:
    return [EquipSlot(k, label, group) for k, label, group in _SLOTS]


class DS3EquipAdapter:
    def __init__(self, char: DS3Slot, source: str) -> None:
        self.char = char
        self.source = source
        self._held = [
            e for e in char.iter_inventory() if not e.is_key and char.is_real_item(e)
        ]
        self._by_key = {self._key(e): e for e in self._held}
        self._names = self._unique_names(self._held)
        # Attunement records hold spell ids, so the spell keys are ids.
        self.loaded_spells: list[int] = char.attuned_spells()
        self.spells: list[int] = list(self.loaded_spells)

    @staticmethod
    def _key(entry: DS3InventoryEntry) -> Hashable:
        return (entry.offset, entry.handle)

    def _unique_names(self, entries: list[DS3InventoryEntry]) -> dict:
        """Display name per entry key; copies of one item get (2), (3)..."""
        seen: dict[str, int] = {}
        names = {}
        for entry in entries:
            if self._is_placeholder(entry):
                names[self._key(entry)] = self._placeholder_name(entry)
                continue
            name = catalog.display_name(entry.item_id, self.source)
            seen[name] = seen.get(name, 0) + 1
            names[self._key(entry)] = (
                name if seen[name] == 1 else f"{name} ({seen[name]})"
            )
        return names

    def _choice(self, entry: DS3InventoryEntry) -> EquipChoice:
        source = self.source
        item = catalog.lookup(entry.item_id, source)
        return EquipChoice(
            self._key(entry),
            self._names[self._key(entry)],
            catalog.CATEGORY_LABELS.get(
                catalog.category_of(entry.item_id, source), "Other"
            ),
            lambda: item_icon(item, source),
        )

    @staticmethod
    def _placeholder_name(entry: DS3InventoryEntry) -> str:
        """Fists, or "Bare <piece>" for the bare armor entries (the game names
        those Head, Body, Arms and Legs, which read like items)."""
        for k in EQUIP_ARMOR:
            if entry.item_id == DS3Slot.equip_placeholder_id(k):
                return f"Bare {_ARMOR_PIECES[k - EQUIP_ARMOR.start].lower()}"
        return "Fists"

    @staticmethod
    def _is_placeholder(entry: DS3InventoryEntry) -> bool:
        return entry.item_id in catalog.PLACEHOLDER_IDS

    # ---- EquipAdapter ----------------------------------------------------------

    def slots(self) -> list[EquipSlot]:
        return equip_slots()

    def _accepts(self, slot_key: Hashable, entry: DS3InventoryEntry) -> bool:
        if self._is_placeholder(entry):
            return False
        if isinstance(slot_key, tuple):
            item = catalog.lookup(entry.item_id, self.source)
            return (
                id_kind(entry.item_id) == ID_GOOD
                and not (item is not None and catalog.is_spell(item))
                and not attunement.is_material(entry.item_id, self.source)
            )
        return self.char.equip_slot_accepts(slot_key, entry.item_id)

    def current(self, slot_key: Hashable) -> EquipChoice | None:
        if isinstance(slot_key, tuple):
            entry = self.char.quick_entry(slot_key[1])
        else:
            entry = self.char.equipped_entry(slot_key)
        if entry is None or self._key(entry) not in self._by_key:
            return None
        return self._choice(entry)

    def choices(self, slot_key: Hashable) -> list[EquipChoice]:
        return [self._choice(e) for e in self._held if self._accepts(slot_key, e)]

    def clear_choice(self, slot_key: Hashable) -> EquipChoice | None:
        if isinstance(slot_key, tuple):
            return None
        wanted = self.char.equip_placeholder_id(slot_key)
        if wanted is None:
            return None
        piece = (
            _ARMOR_PIECES[slot_key - EQUIP_ARMOR.start].lower()
            if slot_key in EQUIP_ARMOR
            else "hand"
        )
        entry = next((e for e in self._held if e.item_id == wanted), None)
        if entry is None:
            raise ValueError(
                f"The character has no bare {piece} entry in its inventory, so "
                "this slot cannot be emptied here. Unequip it in game instead."
            )
        return self._choice(entry)

    def shared(self, choice_key: Hashable) -> bool:
        entry = self._by_key.get(choice_key)
        return entry is not None and self._is_placeholder(entry)

    # ---- attunement --------------------------------------------------------------

    def spell_choices(self) -> list[EquipChoice]:
        """Held spells not in the staged attunement list, one per id."""
        out: dict[int, EquipChoice] = {}
        for entry in self._held:
            spell_id = entry.item_id & 0x0FFFFFFF
            item = catalog.lookup(entry.item_id, self.source)
            if (
                item is not None
                and catalog.is_spell(item)
                and attunement.spell_cost(spell_id, self.source) is not None
                and spell_id not in self.spells
                and spell_id not in out
            ):
                choice = self._choice(entry)
                out[spell_id] = EquipChoice(
                    spell_id, choice.name, catalog.SPELLS_LABEL, choice.icon
                )
        return list(out.values())

    def spell_name(self, key: Hashable) -> str:
        return catalog.display_name((ID_GOOD << 28) | key, self.source)

    def spell_cost(self, key: Hashable) -> int | None:
        return attunement.spell_cost(key, self.source)

    def attunement_budget(self, staged: dict) -> int | None:
        ids = []
        for k in EQUIP_RINGS:
            if k in staged:
                choice = staged[k]
                entry = None if choice is None else self._by_key.get(choice.key)
            else:
                entry = self.char.equipped_entry(k)
            if entry is not None:
                ids.append(entry.item_id)
        return attunement.slots(self.char.get_stat("atn"), ids, self.source)

    @property
    def spells_changed(self) -> bool:
        return self.spells != self.loaded_spells

    # ---- writing -----------------------------------------------------------------

    def apply(self, staged: dict) -> None:
        """Write staged picks into the slot data. Raises ValueError, before
        writing anything, when a picked entry changed since the panel
        loaded."""
        resolved = []
        for slot_key, choice in staged.items():
            entry = None
            if choice is not None:
                offset, handle = choice.key
                entry = self.char.entry_at(offset)
                if entry is None or entry.handle != handle:
                    raise ValueError(
                        f"{choice.name} moved in the inventory. Reload the "
                        "character and pick it again."
                    )
                if not self._accepts(slot_key, entry) and not (
                    self._is_placeholder(entry)
                    and entry.item_id == self.char.equip_placeholder_id(slot_key)
                ):
                    raise ValueError(f"{choice.name} does not fit this slot.")
            resolved.append((slot_key, entry))
        if len(self.spells) > ATTUNE_SLOTS:
            raise ValueError(f"At most {ATTUNE_SLOTS} spells can be attuned.")
        unknown = [s for s in self.spells if self.spell_cost(s) is None]
        if unknown and self.spells_changed:
            raise ValueError(f"Spell {unknown[0]} has no Magic param row.")
        check_attunement(
            sum(self.spell_cost(s) or 0 for s in self.spells),
            self.attunement_budget(staged),
            self.attunement_budget({}),
            self.spells_changed,
        )
        for slot_key, entry in resolved:
            if isinstance(slot_key, tuple):
                self.char.set_quick_item(slot_key[1], entry)
            else:
                self.char.set_equip(slot_key, entry)
        if self.spells_changed:
            self.char.attune(self.spells)
