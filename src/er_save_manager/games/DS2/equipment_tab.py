"""DS2 equipment sub-tab: the shared equipment panel over a DS2 character,
plus the attunement list."""

from __future__ import annotations

from collections.abc import Hashable

from er_save_manager.games.DS2.icon_manager import get_icon
from er_save_manager.games.DS2.item_database import build_item_db
from er_save_manager.games.DS2.regulation import INFUSION_NAMES
from er_save_manager.games.DS2.save import (
    AMMO_BOLT_SLOTS,
    INVENTORY_END,
    INVENTORY_START,
    KEEP_SLOT,
    Character,
    DS2Save,
    InventoryItem,
)
from er_save_manager.ui.editors.ds_equipment import (
    AttunementSection,
    EquipChoice,
    EquipmentPanel,
    EquipSlot,
    check_attunement,
)
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import game_blocks_write

_ARMOR_PIECES = ("Head", "Chest", "Hands", "Legs")
# Armor item ids end in the piece: head 0, chest 1, hands 2, legs 3.
_ARMOR_PIECE_MOD = 10
_SPELL_SLOTS = 14

# (group, index, label) in display order. Weapons follow equip()'s order,
# L1 R1 L2 R2 L3 R3; right hand is listed first as in game.
_SLOTS = (
    *(("weapons", k, f"Right hand {k // 2 + 1}") for k in (1, 3, 5)),
    *(("weapons", k, f"Left hand {k // 2 + 1}") for k in (0, 2, 4)),
    *(("armor", k, _ARMOR_PIECES[k]) for k in range(4)),
    *(("rings", k, f"Ring {k + 1}") for k in range(4)),
    ("ammo", 0, "Arrows 1"),
    ("ammo", 1, "Arrows 2"),
    ("ammo", 2, "Bolts 1"),
    ("ammo", 3, "Bolts 2"),
    *(("belt", k, f"Item {k + 1}") for k in range(10)),
)
_GROUP_TITLES = {
    "weapons": "Weapons",
    "armor": "Armor",
    "rings": "Rings",
    "ammo": "Ammo",
    "belt": "Belt items",
}
_GROUP_CATEGORY = {
    "weapons": "weapons",
    "armor": "armors",
    "rings": "rings",
    "ammo": "bolts",
    "belt": "goods",
}
_CATEGORY_LABELS = {
    "weapons": "Weapons",
    "armors": "Armor",
    "rings": "Rings",
    "goods": "Goods",
    "spells": "Spells",
    "bolts": "Ammo",
}


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(parent, "darksoulsii.exe", "Dark Souls II")


class DS2EquipAdapter:
    def __init__(self, character: Character) -> None:
        self.character = character
        self._db = build_item_db()
        self._carried = [
            e
            for e in character.inventory()
            if e.item_id
            and not e.in_box
            and INVENTORY_START <= e.offset < INVENTORY_END
        ]
        self._by_key = {self._key(e): e for e in self._carried}
        self._current = character.equipped_entries()
        seen: dict[str, int] = {}
        self._names: dict[Hashable, str] = {}
        for entry in self._carried:
            name = self._base_name(entry)
            seen[name] = seen.get(name, 0) + 1
            self._names[self._key(entry)] = (
                name if seen[name] == 1 else f"{name} ({seen[name]})"
            )
        self.loaded_spells = [self._key(e) for e in character.attuned_spells()]
        # Staged attunement list; the panel's Apply writes it with the slots.
        self.spells: list[Hashable] = list(self.loaded_spells)

    @staticmethod
    def _key(entry: InventoryItem) -> Hashable:
        return (entry.offset, entry.item_id)

    def category(self, item_id: int) -> str | None:
        info = self._db.get(item_id)
        return info[1] if info else None

    def _base_name(self, entry: InventoryItem) -> str:
        info = self._db.get(entry.item_id)
        name = info[0] if info else f"Unknown ({entry.item_id})"
        category = info[1] if info else None
        if category == "weapons" and 0 < entry.infusion < len(INFUSION_NAMES):
            name = f"{INFUSION_NAMES[entry.infusion]} {name}"
        if category in ("weapons", "armors") and entry.upgrade:
            name = f"{name} +{entry.upgrade}"
        return name

    def choice(self, entry: InventoryItem) -> EquipChoice:
        category = self.category(entry.item_id)
        item_id = entry.item_id
        return EquipChoice(
            self._key(entry),
            self._names[self._key(entry)],
            _CATEGORY_LABELS.get(category, "Other"),
            lambda: get_icon(item_id, category),
        )

    def entry(self, key: Hashable) -> InventoryItem | None:
        return self._by_key.get(key)

    def _accepts(self, slot_key: tuple[str, int], entry: InventoryItem) -> bool:
        group, k = slot_key
        if self.category(entry.item_id) != _GROUP_CATEGORY.get(group):
            return False
        if group == "ammo":
            return self.character.is_bolt(entry.item_id) == (k in AMMO_BOLT_SLOTS)
        return group != "armor" or entry.item_id % _ARMOR_PIECE_MOD == k

    # ---- EquipAdapter ----------------------------------------------------------

    def slots(self) -> list[EquipSlot]:
        return [
            EquipSlot((group, k), label, _GROUP_TITLES[group])
            for group, k, label in _SLOTS
        ]

    def current(self, slot_key: Hashable) -> EquipChoice | None:
        group, k = slot_key
        entry = self._current[group][k]
        if entry is None or self._key(entry) not in self._by_key:
            return None
        return self.choice(entry)

    def choices(self, slot_key: Hashable) -> list[EquipChoice]:
        return [self.choice(e) for e in self._carried if self._accepts(slot_key, e)]

    def clear_choice(self, slot_key: Hashable) -> EquipChoice | None:
        return None

    def shared(self, choice_key: Hashable) -> bool:
        return False

    # ---- attunement --------------------------------------------------------------

    def spell_choices(self) -> list[EquipChoice]:
        """Carried spells not in the staged attunement list."""
        return [
            self.choice(e)
            for e in self._carried
            if self.category(e.item_id) == "spells" and self._key(e) not in self.spells
        ]

    def spell_name(self, key: Hashable) -> str:
        entry = self._by_key.get(key)
        return self.choice(entry).name if entry else str(key)

    def spell_cost(self, key: Hashable) -> int | None:
        entry = self._by_key.get(key)
        return self.character.spell_slots(entry.item_id) if entry else None

    def attunement_budget(self, staged: dict) -> int | None:
        """Attunement slots with the staged equipment, None when unknown."""
        ids: set[int] = set()
        for group in _GROUP_CATEGORY:
            for k, entry in enumerate(self._current[group]):
                if (group, k) in staged:
                    choice = staged[(group, k)]
                    entry = None if choice is None else self._by_key.get(choice.key)
                if entry is not None:
                    ids.add(entry.item_id)
        return self.character.attunement_slots(ids)

    @property
    def spells_changed(self) -> bool:
        return self.spells != self.loaded_spells

    # ---- writing -----------------------------------------------------------------

    def apply(self, staged: dict) -> None:
        """Write staged slots and the attunement list. Raises ValueError,
        before writing anything, when a pick changed since loading or the
        spells take more slots than the staged equipment allows."""
        groups: dict[str, list] = {
            group: [KEEP_SLOT] * len(self._current[group]) for group in _GROUP_CATEGORY
        }
        for (group, k), choice in staged.items():
            groups[group][k] = None if choice is None else self._fresh(choice.key)
        spells = [self._fresh(key) for key in self.spells]
        check_attunement(
            sum(self.spell_cost(key) or 0 for key in self.spells),
            self.attunement_budget(staged),
            self.character.attunement_slots(),
            self.spells_changed,
        )
        self.character.equip(
            weapons=groups["weapons"],
            armor=groups["armor"],
            rings=groups["rings"],
            belt=groups["belt"],
            ammo=groups["ammo"],
        )
        if self.spells_changed:
            self.character.attune(spells)

    def _fresh(self, key: Hashable) -> InventoryItem:
        offset, item_id = key
        current = {e.offset: e for e in self.character.inventory()}.get(offset)
        if current is None or current.item_id != item_id or current.in_box:
            name = self._names.get(key, str(item_id))
            raise ValueError(
                f"{name} moved in the inventory. Reload the character and pick it "
                "again."
            )
        return current


class DS2EquipmentPanel:
    """Equipment sub-tab of the DS2 character editor."""

    def __init__(self, parent, get_save, get_slot_index, get_save_path, show_toast):
        self.parent = parent
        self.get_save = get_save
        self.get_slot_index = get_slot_index
        self.get_save_path = get_save_path
        self.show_toast = show_toast
        self.panel: EquipmentPanel | None = None
        self.attunement = AttunementSection(_SPELL_SLOTS)

    def setup_ui(self) -> None:
        self.panel = EquipmentPanel(self.parent, self._apply, self.attunement.build)
        self.attunement.attach(self.panel)

    def _adapter(self) -> DS2EquipAdapter | None:
        return self.panel.adapter if self.panel is not None else None

    # ---- loading and applying ---------------------------------------------------

    def reload_if_unchanged(self) -> None:
        """Reload from the save unless picks are staged."""
        if not (self.panel.staged or self.attunement.changed()):
            self.refresh()

    def refresh(self) -> None:
        if self.panel is None:
            return
        save: DS2Save | None = self.get_save()
        if save is None:
            self.panel.load(None)
        else:
            character = save.characters[self.get_slot_index()]
            if character.has_equipment_block():
                self.panel.load(DS2EquipAdapter(character))
            else:
                self.panel.load(
                    None,
                    "This character's equipment block has an unknown layout, so "
                    "its equipment cannot be edited.",
                )

    def _apply(self, adapter: DS2EquipAdapter, staged: dict) -> None:
        if not staged and not adapter.spells_changed:
            self.show_toast("No equipment changes to apply", duration=2000)
            return
        if _game_blocks_write(self.parent):
            return
        save: DS2Save | None = self.get_save()
        save_path = self.get_save_path()
        if save is None or not save_path:
            return
        slot_index = self.get_slot_index()
        if not CTkMessageBox.askyesno(
            "Apply Equipment",
            f"Apply equipment changes to slot {slot_index + 1}?\n\n"
            "A backup will be created.",
            parent=self.parent,
        ):
            return
        try:
            adapter.apply(staged)
        except ValueError as exc:
            CTkMessageBox.showerror(
                "Equipment Not Applied", str(exc), parent=self.parent
            )
            self.refresh()
            return
        save.sync_equipment_cache(slot_index)
        try:
            from pathlib import Path

            from er_save_manager.backup.manager import BackupManager

            BackupManager(Path(save_path)).create_backup(
                description=f"before_equipment_edit_slot_{slot_index}",
                operation="edit_equipment",
            )
            save.save_to_file(save_path)
            self.show_toast("Equipment applied. Backup created.", duration=3000)
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)
        self.refresh()
