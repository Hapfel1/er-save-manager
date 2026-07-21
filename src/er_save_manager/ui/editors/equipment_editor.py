"""
Equipment Editor - view and edit equipped items per slot.

Pickers only ever list items the character actually owns (resolved from
gaitem_map for weapons/armor, from held inventory direct handles for
talismans/spells/physick tears/quick items/pouch). This is the validation
mechanism: whatever is selectable is guaranteed equippable.

Armor gaitem_map.item_id encoding note: inventory_ops.py's _find_gaitem_by_item
compares it against a full_item_id (category bit included) while this module's
_resolve_name has always expected a bare base id. Lookups here mask the value
before OR-ing the category bit back in, and storage always uses the masked
base id, so either encoding resolves correctly.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel, pick_file, trace_variable

# ---- constants --------------------------------------------------------------

# Item DB category names that belong to each slot type
_WEAPON_CATS = [
    "Melee Weapons",
    "Ranged Weapons",
    "Spell Tools",
    "Shields",
    "DLC Melee Weapons",
    "DLC Ranged Weapons",
    "DLC Spell Tools",
    "DLC Shields",
    "Convergence Melee Weapons",
    "Convergence Reworked Weapons",
    "Convergence Ranged Weapons",
    "Convergence Shields",
    "Convergence Spell Tools",
]
_ARMOR_CATS = ["Armor", "DLC Armor", "Convergence Armor"]
_TALISMAN_CATS = ["Talismans", "DLC Talismans", "Convergence Talismans"]
_AMMO_CATS = ["Ammo", "DLC Ammo", "Convergence Ammo"]
_SPELL_CATS = ["Magic", "DLC Magic", "Convergence Magic"]
_PHYSICK_CATS = ["Crystal Tears", "DLC Crystal Tears", "Convergence Crystal Tears"]
_QUICKITEM_CATS = [
    "Consumables",
    "DLC Consumables",
    "Convergence Consumables",
    "Tools",
    "DLC Tools",
    "Ashes",
    "DLC Ashes",
    "Convergence Ashes",
    "Seamless Co-op Items",
    "Convergence Remembrances",
    "Convergence Runes",
]
# Flasks are deliberately excluded: equipping them via the tool duplicates
# them rather than moving them, so they are never offered here and are
# skipped on apply even if present in an old/shared loadout.
_FLASK_CATS = {"Flasks"}
# Pouch shares the same usable-goods categories as quick items.

# Category name prefixes/sets gated by save type, mirroring inventory_editor.py
_SEAMLESS_CATS = {"Seamless Co-op Items"}


def _cat_allowed(cat: str, is_cnv: bool, is_co2: bool) -> bool:
    if cat.startswith("Convergence ") and not is_cnv:
        return False
    if cat in _SEAMLESS_CATS and not is_co2:
        return False
    return True


_SLOT_CATS: dict[str, list[str]] = {
    "right_hand_armament1": _WEAPON_CATS,
    "right_hand_armament2": _WEAPON_CATS,
    "right_hand_armament3": _WEAPON_CATS,
    "left_hand_armament1": _WEAPON_CATS,
    "left_hand_armament2": _WEAPON_CATS,
    "left_hand_armament3": _WEAPON_CATS,
    "head": _ARMOR_CATS,
    "chest": _ARMOR_CATS,
    "arms": _ARMOR_CATS,
    "legs": _ARMOR_CATS,
    "talisman1": _TALISMAN_CATS,
    "talisman2": _TALISMAN_CATS,
    "talisman3": _TALISMAN_CATS,
    "talisman4": _TALISMAN_CATS,
    "arrows1": _AMMO_CATS,
    "arrows2": _AMMO_CATS,
    "bolts1": _AMMO_CATS,
    "bolts2": _AMMO_CATS,
}
for _i in range(1, 15):
    _SLOT_CATS[f"spell{_i}"] = _SPELL_CATS
for _i in range(1, 3):
    _SLOT_CATS[f"physick{_i}"] = _PHYSICK_CATS
for _i in range(1, 11):
    _SLOT_CATS[f"quickitem{_i}"] = _QUICKITEM_CATS
for _i in range(1, 7):
    _SLOT_CATS[f"pouch{_i}"] = _QUICKITEM_CATS

# Raw IDs that mean "empty slot"
_EMPTY_IDS = {0, 0xFFFFFFFF, 110000}

_AFFINITY_BY_CODE: dict[int, str] = {
    0: "Standard",
    1: "Heavy",
    2: "Keen",
    3: "Quality",
    4: "Fire",
    5: "Flame Art",
    6: "Lightning",
    7: "Sacred",
    8: "Magic",
    9: "Cold",
    10: "Poison",
    11: "Blood",
    12: "Occult",
}


# ---- name resolution --------------------------------------------------------

_WEAPON_KEYS = {
    "right_hand_armament1",
    "right_hand_armament2",
    "right_hand_armament3",
    "left_hand_armament1",
    "left_hand_armament2",
    "left_hand_armament3",
    "arrows1",
    "arrows2",
    "bolts1",
    "bolts2",
}
_ARMOR_KEYS = {"head", "chest", "arms", "legs"}
_TALISMAN_KEYS = {"talisman1", "talisman2", "talisman3", "talisman4"}
_SPELL_KEYS = {f"spell{i}" for i in range(1, 15)}
_PHYSICK_KEYS = {"physick1", "physick2"}
_QUICKITEM_KEYS = {f"quickitem{i}" for i in range(1, 11)}
_POUCH_KEYS = {f"pouch{i}" for i in range(1, 7)}
_GOODS_KEYS = _SPELL_KEYS | _PHYSICK_KEYS | _QUICKITEM_KEYS | _POUCH_KEYS


def _resolve_name(key: str, raw_id: int, is_cnv: bool = False) -> str:
    if raw_id in _EMPTY_IDS:
        return ""

    from er_save_manager.data.item_database import get_item_name

    if key in _WEAPON_KEYS:
        upgrade = raw_id % 100
        name = get_item_name(raw_id, upgrade_level=upgrade, is_convergence=is_cnv)
        if name.startswith("Unknown"):
            return ""
        affinity_code = (raw_id // 100) % 100
        if affinity_code != 0:
            aff = _AFFINITY_BY_CODE.get(affinity_code, str(affinity_code))
            name = f"{name} [{aff}]"
        return name

    if key in _ARMOR_KEYS:
        name = get_item_name(0x10000000 | raw_id, is_convergence=is_cnv)
        return "" if name.startswith("Unknown") else name

    if key in _TALISMAN_KEYS:
        name = get_item_name(0x20000000 | raw_id, is_convergence=is_cnv)
        if name.startswith("Unknown"):
            name = get_item_name(
                0x20000000 | (raw_id & 0x00FFFFFF), is_convergence=is_cnv
            )
        return "" if name.startswith("Unknown") else name

    if key in _GOODS_KEYS:
        name = get_item_name(0x40000000 | raw_id, is_convergence=is_cnv)
        return "" if name.startswith("Unknown") else name

    return ""


def _decode_slot_value(raw: int, category_bit: int = 0) -> int:
    """Convert an on-disk item-id-type field to the editor's internal value.

    On-disk empty sentinel for item-id-type fields is 0xFFFFFFFF (confirmed
    against real save data - never 0). Internally the editor uses 0 for empty.
    category_bit strips the item database category bit (e.g. 0x40000000 for
    goods) that physick/quickitem/pouch fields carry but weapon/armor/talisman/
    spell fields do not.
    """
    if raw in (0, 0xFFFFFFFF):
        return 0
    return (raw & 0x00FFFFFF) if category_bit else raw


def _encode_slot_value(raw: int, category_bit: int = 0) -> int:
    """Convert the editor's internal value (0 = empty) back to on-disk form."""
    if raw == 0:
        return 0xFFFFFFFF
    return (category_bit | raw) if category_bit else raw


def _is_flask(raw: int) -> bool:
    """True if raw (goods base id, no category bit) is a Flask item."""
    if raw == 0:
        return False
    from er_save_manager.data.item_database import get_item_database

    item = get_item_database().items_by_id.get(0x40000000 | raw)
    return item is not None and item.category_name in _FLASK_CATS


# ---- armor per-slot gating ---------------------------------------------------

_ARMOR_KEY_TO_SLOT = {"head": "head", "chest": "chest", "arms": "arms", "legs": "legs"}
_armor_slot_types: dict[int, str] | None = None


def _load_armor_slot_types() -> dict[int, str]:
    """Load ID -> head/chest/arms/legs from armor_slot_types.csv.

    Derived from EquipParamProtector's headEquip/bodyEquip/armEquip/legEquip
    columns (Armor.csv itself has no slot-type column).
    """
    global _armor_slot_types
    if _armor_slot_types is not None:
        return _armor_slot_types

    import csv as _csv

    mapping: dict[int, str] = {}
    try:
        from er_save_manager.data import item_database as _idb

        path = Path(_idb.__file__).parent / "items" / "armor_slot_types.csv"
        with open(path, newline="") as f:
            for row in _csv.DictReader(f):
                mapping[int(row["ID"])] = row["Slot"]
    except Exception:
        pass
    _armor_slot_types = mapping
    return mapping


# ---- owned-item resolution ---------------------------------------------------


def _owned_gaitem_items(
    slot, prefix: int, cat_names: set[str], key: str, is_cnv: bool, is_co2: bool
) -> list[tuple[int, int, str, str]]:
    """Return (raw_value, gaitem_handle, name, category_name) for owned
    weapon/armor entries.

    raw_value matches the encoding expected by EquippedItemsItemIds fields
    (no category bit). Every physical instance is listed separately (not
    deduplicated by raw_value) so owning multiple copies of the same item
    shows every copy and lets each be assigned to a different slot.
    """
    from er_save_manager.data.item_database import get_item_database

    db = get_item_database()
    armor_slot = _ARMOR_KEY_TO_SLOT.get(key)
    slot_types = _load_armor_slot_types() if armor_slot else None
    out = []
    seen_handles = set()
    for g in getattr(slot, "gaitem_map", []):
        if g.gaitem_handle in (0, 0xFFFFFFFF) or g.gaitem_handle in seen_handles:
            continue
        if (g.gaitem_handle & 0xF0000000) != prefix:
            continue
        raw = g.item_id & 0x0FFFFFFF
        if prefix == 0x80000000:
            true_base = (raw // 10000) * 10000
            item = db.items_by_id.get(true_base)
        else:
            item = db.items_by_id.get(0x10000000 | raw)
            if armor_slot and slot_types and slot_types.get(raw) != armor_slot:
                continue
        if item is None or item.category_name not in cat_names:
            continue
        if not _cat_allowed(item.category_name, is_cnv, is_co2):
            continue
        name = _resolve_name(key, raw, is_cnv)
        if not name:
            continue
        seen_handles.add(g.gaitem_handle)
        out.append((raw, g.gaitem_handle, name, item.category_name))
    out = _suffix_duplicate_names(out)
    out.sort(key=lambda t: t[2])
    return out


def _suffix_duplicate_names(
    items: list[tuple[int, int, str, str]],
) -> list[tuple[int, int, str, str]]:
    """Append (2), (3), ... to display names that occur more than once."""
    counts: dict[str, int] = {}
    for _raw, _handle, name, _cat in items:
        counts[name] = counts.get(name, 0) + 1
    seen: dict[str, int] = {}
    out = []
    for raw, handle, name, cat in items:
        if counts[name] > 1:
            seen[name] = seen.get(name, 0) + 1
            out.append((raw, handle, f"{name} ({seen[name]})", cat))
        else:
            out.append((raw, handle, name, cat))
    return out


def _owned_direct_items(
    slot, cat_names: set[str], category_bit: int, is_cnv: bool, is_co2: bool
) -> list[tuple[int, int, str, str]]:
    """Return (base_id, direct_handle, name, category_name) for owned
    talisman/goods entries.

    category_bit is the item database category (0x20000000 talisman,
    0x40000000 goods). base_id is the 24-bit masked value stored directly
    in equipped_items and equipped_armaments_and_items. Talismans/goods are
    stacked by quantity on a single inventory entry (unlike weapons/armor,
    there is no separate physical instance per copy), so one row per type.
    """
    from er_save_manager.data.item_database import get_item_database

    db = get_item_database()
    prefix = 0xA0000000 if category_bit == 0x20000000 else 0xB0000000
    out = []
    seen = set()
    entries = list(slot.inventory_held.common_items) + list(
        slot.inventory_held.key_items
    )
    for entry in entries:
        h = entry.gaitem_handle
        if h in (0, 0xFFFFFFFF) or (h & 0xF0000000) != prefix:
            continue
        base_id = h & 0x00FFFFFF
        if base_id in seen:
            continue
        item = db.items_by_id.get(category_bit | base_id)
        if item is None or item.category_name not in cat_names:
            continue
        if not _cat_allowed(item.category_name, is_cnv, is_co2):
            continue
        seen.add(base_id)
        out.append((base_id, h, item.name, item.category_name))
    out.sort(key=lambda t: t[2])
    return out


# ---- item picker dialog -----------------------------------------------------


class _ItemPickerDialog(ctk.CTkToplevel):
    """Searchable picker limited to items the character actually owns."""

    def __init__(
        self,
        parent,
        owned_items: list[tuple[int, int, str, str]],
        on_select,
    ):
        super().__init__(parent)
        self.title("Select Item")
        self.resizable(False, True)
        self.transient(parent)
        self.attributes("-alpha", 0)

        self._on_select = on_select
        self._items = owned_items
        self._visible: list[tuple[int, int, str, str]] = []

        self.geometry("440x500")

        self.update_idletasks()
        self.attributes("-alpha", 1)
        self.grab_set()

        # Search row
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill=ctk.X, padx=10, pady=(10, 4))
        ctk.CTkLabel(top, text="Search:").pack(side=ctk.LEFT, padx=(0, 6))
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter())
        ctk.CTkEntry(top, textvariable=self._search_var, width=250).pack(side=ctk.LEFT)

        # Category + sort row
        filt_row = ctk.CTkFrame(self, fg_color="transparent")
        filt_row.pack(fill=ctk.X, padx=10, pady=(0, 4))
        ctk.CTkLabel(filt_row, text="Category:").pack(side=ctk.LEFT, padx=(0, 6))
        categories = ["All"] + sorted({i[3] for i in owned_items})
        self._cat_var = ctk.StringVar(value="All")
        ctk.CTkComboBox(
            filt_row,
            values=categories,
            variable=self._cat_var,
            width=150,
            command=lambda _v: self._filter(),
        ).pack(side=ctk.LEFT, padx=(0, 12))
        ctk.CTkLabel(filt_row, text="Sort:").pack(side=ctk.LEFT, padx=(0, 6))
        self._sort_var = ctk.StringVar(value="Name (A-Z)")
        ctk.CTkComboBox(
            filt_row,
            values=["Name (A-Z)", "Name (Z-A)", "Category"],
            variable=self._sort_var,
            width=140,
            command=lambda _v: self._filter(),
        ).pack(side=ctk.LEFT)

        # Listbox
        lb_frame = ctk.CTkFrame(self, fg_color=("gray82", "gray14"), corner_radius=6)
        lb_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=4)

        mode = ctk.get_appearance_mode()
        lb_bg = "#1a1a24" if mode == "Dark" else "#f0f0f0"
        lb_fg = "#d4d4e8" if mode == "Dark" else "#111111"
        lb_sel = "#7c4dac" if mode == "Dark" else "#b8a0d0"

        sb = tk.Scrollbar(lb_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._lb = tk.Listbox(
            lb_frame,
            yscrollcommand=sb.set,
            font=("Consolas", 10),
            bg=lb_bg,
            fg=lb_fg,
            selectbackground=lb_sel,
            relief=tk.FLAT,
            borderwidth=0,
            activestyle="none",
        )
        self._lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        sb.config(command=self._lb.yview)
        self._lb.bind("<Double-Button-1>", lambda _e: self._confirm())
        bind_mousewheel(self._lb)

        if not owned_items:
            ctk.CTkLabel(
                self,
                text="No owned items found in inventory for this slot.",
                text_color=("gray40", "gray60"),
                wraplength=380,
            ).pack(padx=10, pady=(0, 4))

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill=ctk.X, padx=10, pady=(6, 10))
        ctk.CTkButton(btn_row, text="Select", command=self._confirm, width=120).pack(
            side=ctk.LEFT, padx=(0, 6)
        )
        ctk.CTkButton(
            btn_row,
            text="Clear Slot",
            command=self._clear,
            width=100,
            fg_color=("gray70", "gray35"),
        ).pack(side=ctk.LEFT, padx=(0, 6))
        ctk.CTkButton(btn_row, text="Cancel", command=self.destroy, width=80).pack(
            side=ctk.RIGHT
        )

        self._filter()

    def _filter(self):
        query = self._search_var.get().lower().strip()
        cat = self._cat_var.get()
        items = [i for i in self._items if query in i[2].lower()]
        if cat != "All":
            items = [i for i in items if i[3] == cat]

        sort_mode = self._sort_var.get()
        if sort_mode == "Name (Z-A)":
            items.sort(key=lambda t: t[2], reverse=True)
        elif sort_mode == "Category":
            items.sort(key=lambda t: (t[3], t[2]))
        else:
            items.sort(key=lambda t: t[2])

        self._visible = items
        self._lb.delete(0, tk.END)
        for _raw, _handle, name, _cat in self._visible:
            self._lb.insert(tk.END, name)

    def _confirm(self):
        sel = self._lb.curselection()
        if not sel or sel[0] >= len(self._visible):
            return
        raw_value, handle, _name, _cat = self._visible[sel[0]]
        self._on_select(raw_value, handle)
        self.destroy()

    def _clear(self):
        self._on_select(0, 0)
        self.destroy()


# ---- binary patch --------------------------------------------------------


def _patch_equipment(save_file, slot_idx: int, slot) -> None:
    """Write modified equipment structs directly into save_file._raw_data.

    to_file() only ever dumps _raw_data verbatim - it does not re-serialize
    the parsed dataclass tree. Mutating slot.equipped_* attributes alone has
    no effect on disk; each struct must be patched into _raw_data at its
    tracked offset, same pattern as inventory_ops.py's _patch_slot.
    """
    from io import BytesIO

    base = save_file.slot_data_offset(slot_idx)

    def patch(obj, offset: int) -> None:
        if not offset:
            return
        buf = BytesIO()
        obj.write(buf)
        data = buf.getvalue()
        abs_off = base + offset
        save_file._raw_data[abs_off : abs_off + len(data)] = data

    patch(slot.equipped_items_equip_index, slot.equipped_items_equip_index_offset)
    patch(slot.equipped_items_item_id, slot.equipped_items_item_id_offset)
    patch(slot.equipped_items_gaitem_handle, slot.equipped_items_gaitem_handle_offset)
    patch(slot.inventory_held, slot.inventory_held_offset)
    patch(slot.equipped_spells, slot.equipped_spells_offset)
    patch(slot.equipped_items, slot.equipped_items_offset)
    patch(slot.equipped_armaments_and_items, slot.equipped_armaments_and_items_offset)
    patch(slot.equipped_physics, slot.equipped_physics_offset)


def _find_equip_index(slot, handle: int) -> int:
    """Compute the equip_index value the game's menu expects for a handle.

    Confirmed empirically against real save data (see equipment editor
    module docstring context): position in key_items as-is, or held key
    capacity (0x180) plus position in common_items. 0xFFFFFFFF if empty or
    not found.
    """
    if handle in (0, 0xFFFFFFFF):
        return 0xFFFFFFFF
    held_key_capacity = 0x180
    for i, entry in enumerate(slot.inventory_held.key_items):
        if entry.gaitem_handle == handle:
            return i
    for i, entry in enumerate(slot.inventory_held.common_items):
        if entry.gaitem_handle == handle:
            return held_key_capacity + i
    return 0xFFFFFFFF


# ---- loadout browser dialog --------------------------------------------------


class _LoadoutBrowserDialog(ctk.CTkToplevel):
    """List locally saved loadouts with Load/Delete actions."""

    def __init__(self, parent, store: dict, on_choice):
        super().__init__(parent)
        self.title("Load Loadout")
        self.resizable(False, True)
        self.transient(parent)
        self.attributes("-alpha", 0)

        self._store = store
        self._on_choice = on_choice
        self._names = sorted(store.keys())

        self.geometry("360x420")
        self.update_idletasks()
        self.attributes("-alpha", 1)
        self.grab_set()

        lb_frame = ctk.CTkFrame(self, fg_color=("gray82", "gray14"), corner_radius=6)
        lb_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

        mode = ctk.get_appearance_mode()
        lb_bg = "#1a1a24" if mode == "Dark" else "#f0f0f0"
        lb_fg = "#d4d4e8" if mode == "Dark" else "#111111"
        lb_sel = "#7c4dac" if mode == "Dark" else "#b8a0d0"

        sb = tk.Scrollbar(lb_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._lb = tk.Listbox(
            lb_frame,
            yscrollcommand=sb.set,
            font=("Consolas", 10),
            bg=lb_bg,
            fg=lb_fg,
            selectbackground=lb_sel,
            relief=tk.FLAT,
            borderwidth=0,
            activestyle="none",
        )
        self._lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        sb.config(command=self._lb.yview)
        self._lb.bind("<Double-Button-1>", lambda _e: self._load())
        bind_mousewheel(self._lb)
        for name in self._names:
            self._lb.insert(tk.END, name)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill=ctk.X, padx=10, pady=(0, 10))
        ctk.CTkButton(btn_row, text="Load", command=self._load, width=100).pack(
            side=ctk.LEFT, padx=(0, 6)
        )
        ctk.CTkButton(
            btn_row,
            text="Delete",
            command=self._delete,
            width=100,
            fg_color=("gray70", "gray35"),
        ).pack(side=ctk.LEFT, padx=(0, 6))
        ctk.CTkButton(btn_row, text="Cancel", command=self.destroy, width=80).pack(
            side=ctk.RIGHT
        )

    def _selected_name(self) -> str | None:
        sel = self._lb.curselection()
        if not sel:
            return None
        return self._names[sel[0]]

    def _load(self):
        name = self._selected_name()
        if not name:
            return
        self._on_choice(name, "load", self._store)
        self.destroy()

    def _delete(self):
        name = self._selected_name()
        if not name:
            return
        if not CTkMessageBox.askyesno(
            "Delete Loadout", f"Delete loadout '{name}'?", parent=self
        ):
            return
        self._on_choice(name, "delete", self._store)
        self._names.remove(name)
        self._lb.delete(0, tk.END)
        for n in self._names:
            self._lb.insert(tk.END, n)


_MEMORY_STONE_HANDLE = 0xB0000000 | 10030


def _max_spell_slots(slot) -> int:
    """Best-effort spell slot cap: base 3 plus owned Memory Stones (held key
    items - Memory Stones are stored there, not in common_items).

    This is a heuristic, not verified ground truth (no persisted "unlocked
    slots" counter exists anywhere in the save the way there is for
    talisman slots). It is floored by the highest slot index that already
    has a real spell, so a wrong guess can only ever block adding something
    new to an empty slot - it can never hide or overwrite existing data.
    """
    base = 3
    stone_qty = 0
    for e in slot.inventory_held.key_items:
        if e.gaitem_handle == _MEMORY_STONE_HANDLE:
            stone_qty = getattr(e, "quantity", 0)
            break
    computed = base + stone_qty

    highest_filled = 0
    for i, s in enumerate(slot.equipped_spells.spell_slots, start=1):
        if s.spell_id not in (0, 0xFFFFFFFF):
            highest_filled = i
    return max(computed, highest_filled)


def _resolve_icon(key: str, raw: int, is_cnv: bool = False):
    """Return a PIL image for a slot's current item, or None."""
    if raw in _EMPTY_IDS:
        return None
    from er_save_manager.data.icon_manager import get_icon
    from er_save_manager.data.item_database import get_item_database

    db = get_item_database()
    if key in _WEAPON_KEYS:
        true_base = (raw // 10000) * 10000
        item = db.get_item_by_id(true_base, is_cnv)
    elif key in _ARMOR_KEYS:
        item = db.get_item_by_id(0x10000000 | raw, is_cnv)
    elif key in _TALISMAN_KEYS:
        item = db.get_item_by_id(0x20000000 | raw, is_cnv)
    elif key in _GOODS_KEYS:
        item = db.get_item_by_id(0x40000000 | raw, is_cnv)
    else:
        return None
    if item is None:
        return None
    try:
        return get_icon(item.name, getattr(item, "category_name", ""))
    except Exception:
        return None


# ---- visual grid browser -----------------------------------------------------

_ICON_SIZE = 64
_CELL_W = 96


def _resolve_icon_by_name(display_name: str):
    """Icon lookup for owned-item picker rows, which may have suffixes like

    ' (2)' (duplicate instance) or ' [Affinity]' (weapon affinity) appended.
    """
    import re

    from er_save_manager.data.icon_manager import get_icon

    name = re.sub(r"\s*\(\d+\)$", "", display_name)
    name = re.sub(r"\s*\[[^\]]+\]$", "", name)
    try:
        return get_icon(name)
    except Exception:
        return None


class _VisualItemPickerDialog(ctk.CTkToplevel):
    """Icon-grid picker limited to items the character actually owns.

    Canvas-based (not one CTkButton/CTkFrame per item) - a weapon slot can
    have hundreds of owned instances, and creating that many widgets at once
    triggers X11 BadAlloc. Icons are drawn as raw PhotoImages onto a single
    Canvas and loaded in small batches via after(), same approach already
    used for the gem picker in icon_browser.py.
    """

    _CELL = 108
    _COLS = 5
    _MAX_VISIBLE = 300

    def __init__(self, parent, owned_items: list[tuple[int, int, str, str]], on_select):
        super().__init__(parent)
        self.title("Select Item")
        self.resizable(True, True)
        self.transient(parent)
        self.attributes("-alpha", 0)

        self._on_select = on_select
        self._items = owned_items
        self._visible: list[tuple[int, int, str, str]] = []
        self._photos: list = []
        self._sel: int | None = None
        self._job = None

        self.geometry("640x680")
        self.update_idletasks()
        self.attributes("-alpha", 1)
        self.grab_set()

        mode = ctk.get_appearance_mode()
        self._bg = "#1a1a24" if mode == "Dark" else "#f0f0f0"
        self._fg = "#d4d4e8" if mode == "Dark" else "#111111"
        self._sel_color = "#7c4dac" if mode == "Dark" else "#b8a0d0"

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill=ctk.X, padx=10, pady=(10, 4))
        ctk.CTkLabel(top, text="Search:").pack(side=ctk.LEFT, padx=(0, 6))
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter())
        ctk.CTkEntry(top, textvariable=self._search_var, width=250).pack(side=ctk.LEFT)

        filt_row = ctk.CTkFrame(self, fg_color="transparent")
        filt_row.pack(fill=ctk.X, padx=10, pady=(0, 4))
        ctk.CTkLabel(filt_row, text="Category:").pack(side=ctk.LEFT, padx=(0, 6))
        categories = ["All"] + sorted({i[3] for i in owned_items})
        self._cat_var = ctk.StringVar(value="All")
        ctk.CTkComboBox(
            filt_row,
            values=categories,
            variable=self._cat_var,
            width=150,
            command=lambda _v: self._filter(),
        ).pack(side=ctk.LEFT, padx=(0, 12))
        ctk.CTkLabel(filt_row, text="Sort:").pack(side=ctk.LEFT, padx=(0, 6))
        self._sort_var = ctk.StringVar(value="Name (A-Z)")
        ctk.CTkComboBox(
            filt_row,
            values=["Name (A-Z)", "Name (Z-A)", "Category"],
            variable=self._sort_var,
            width=140,
            command=lambda _v: self._filter(),
        ).pack(side=ctk.LEFT)

        cv_frame = ctk.CTkFrame(self, fg_color=("gray82", "gray14"), corner_radius=6)
        cv_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=4)

        self._cv = tk.Canvas(cv_frame, bg=self._bg, highlightthickness=0, bd=0)
        sb = tk.Scrollbar(cv_frame, orient="vertical", command=self._cv.yview)
        self._cv.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._cv.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self._cv.bind("<Button-1>", self._on_click)
        self._cv.bind(
            "<Double-Button-1>", lambda e: (self._on_click(e), self._confirm())
        )
        self._cv.bind(
            "<MouseWheel>",
            lambda e: self._cv.yview_scroll(int(-e.delta / 120), "units"),
        )
        self._cv.bind("<Button-4>", lambda _e: self._cv.yview_scroll(-1, "units"))
        self._cv.bind("<Button-5>", lambda _e: self._cv.yview_scroll(1, "units"))

        if not owned_items:
            ctk.CTkLabel(
                self,
                text="No owned items found in inventory for this slot.",
                text_color=("gray40", "gray60"),
            ).pack(padx=10, pady=(0, 4))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill=ctk.X, padx=10, pady=(6, 10))
        ctk.CTkButton(
            btn_row,
            text="Clear Slot",
            command=self._clear,
            width=100,
            fg_color=("gray70", "gray35"),
        ).pack(side=ctk.LEFT)
        ctk.CTkButton(btn_row, text="Cancel", command=self.destroy, width=80).pack(
            side=ctk.RIGHT
        )

        self._filter()

    def _filter(self):
        query = self._search_var.get().lower().strip()
        cat = self._cat_var.get()
        items = [i for i in self._items if query in i[2].lower()]
        if cat != "All":
            items = [i for i in items if i[3] == cat]

        sort_mode = self._sort_var.get()
        if sort_mode == "Name (Z-A)":
            items.sort(key=lambda t: t[2], reverse=True)
        elif sort_mode == "Category":
            items.sort(key=lambda t: (t[3], t[2]))
        else:
            items.sort(key=lambda t: t[2])

        self._draw(items[: self._MAX_VISIBLE])

    def _draw(self, items: list[tuple[int, int, str, str]]):
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        self._cv.delete("all")
        self._photos.clear()
        self._visible = items
        self._sel = None

        cw = max(self._cv.winfo_width(), self._CELL * self._COLS)
        for idx, (_raw, _handle, name, _cat) in enumerate(items):
            row, col = divmod(idx, self._COLS)
            x0, y0 = col * self._CELL, row * self._CELL
            self._cv.create_rectangle(
                x0,
                y0,
                x0 + self._CELL,
                y0 + self._CELL,
                fill=self._bg,
                outline="",
                tags=(f"cell_{idx}", f"bg_{idx}"),
            )
            label = name if len(name) <= 28 else name[:25] + "..."
            self._cv.create_text(
                x0 + self._CELL / 2,
                y0 + self._CELL - 26,
                text=label,
                fill=self._fg,
                font=("Segoe UI", 9),
                width=self._CELL - 6,
                anchor="n",
                justify="center",
                tags=f"cell_{idx}",
            )
        rows = (len(items) + self._COLS - 1) // self._COLS
        self._cv.configure(scrollregion=(0, 0, cw, rows * self._CELL))
        self._job = self.after(60, lambda: self._load_icons(0))

    def _load_icons(self, start: int, batch: int = 24):
        try:
            from PIL import Image, ImageTk
        except Exception:
            return
        end = min(start + batch, len(self._visible))
        for idx in range(start, end):
            _raw, _handle, name, _cat = self._visible[idx]
            try:
                pil = _resolve_icon_by_name(name)
                if pil:
                    pil = pil.convert("RGBA").resize((72, 72), Image.LANCZOS)
                    ph = ImageTk.PhotoImage(pil)
                    self._photos.append(ph)
                    row, col = divmod(idx, self._COLS)
                    x0, y0 = col * self._CELL, row * self._CELL
                    self._cv.create_image(
                        x0 + self._CELL / 2,
                        y0 + self._CELL / 2 - 12,
                        image=ph,
                        tags=f"cell_{idx}",
                    )
            except Exception:
                pass
        if end < len(self._visible):
            self._job = self.after(20, lambda: self._load_icons(end, batch))
        else:
            self._job = None
            self._cv._photo_refs = self._photos  # prevent GC

    def _on_click(self, event):
        x, y = self._cv.canvasx(event.x), self._cv.canvasy(event.y)
        col = int(x // self._CELL)
        row = int(y // self._CELL)
        if col < 0 or col >= self._COLS:
            return
        idx = row * self._COLS + col
        if not (0 <= idx < len(self._visible)):
            return
        prev = self._sel
        self._sel = idx
        for i in (prev, idx):
            if i is not None:
                self._cv.itemconfigure(
                    f"bg_{i}",
                    fill=self._sel_color if i == self._sel else self._bg,
                )

    def _confirm(self):
        if self._sel is None or self._sel >= len(self._visible):
            return
        raw, handle, _name, _cat = self._visible[self._sel]
        self._on_select(raw, handle)
        self.destroy()

    def _clear(self):
        self._on_select(0, 0)
        self.destroy()


class _VisualEquipmentBrowser(ctk.CTkToplevel):
    """Icon-grid overview of all equipped slots. Click a slot to pick a new item."""

    def __init__(self, parent, editor: EquipmentEditor):
        super().__init__(parent)
        self.title("Visual Equipment Picker")
        self.resizable(True, True)
        self.transient(parent)
        self.attributes("-alpha", 0)

        self._editor = editor
        self._ctk_images: list[ctk.CTkImage] = []
        self._cells: dict[str, ctk.CTkButton] = {}
        self._captions: dict[str, ctk.CTkLabel] = {}

        self.geometry("900x760")
        self.update_idletasks()
        self.attributes("-alpha", 1)

        outer = ctk.CTkScrollableFrame(self, fg_color="transparent")
        outer.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)
        bind_mousewheel(outer)

        def row(items: list[tuple[str, str]], enabled: bool = True):
            f = ctk.CTkFrame(outer, fg_color="transparent")
            f.pack(fill=ctk.X, pady=3)
            for label, key in items:
                self._build_cell(f, label, key, enabled=enabled)

        row(
            [
                ("RH1", "right_hand_armament1"),
                ("RH2", "right_hand_armament2"),
                ("RH3", "right_hand_armament3"),
                ("Arrow1", "arrows1"),
                ("Arrow2", "arrows2"),
            ]
        )
        row(
            [
                ("LH1", "left_hand_armament1"),
                ("LH2", "left_hand_armament2"),
                ("LH3", "left_hand_armament3"),
                ("Bolt1", "bolts1"),
                ("Bolt2", "bolts2"),
            ]
        )
        row(
            [
                ("Head", "head"),
                ("Chest", "chest"),
                ("Arms", "arms"),
                ("Legs", "legs"),
            ]
        )
        row([(f"Tal{i}", f"talisman{i}") for i in range(1, 5)])
        row([(f"Item{i}", f"quickitem{i}") for i in range(1, 6)])
        row([(f"Item{i}", f"quickitem{i}") for i in range(6, 11)])
        row([(f"Pouch{i}", f"pouch{i}") for i in range(1, 7)])
        row([("Tear1", "physick1"), ("Tear2", "physick2")])
        for lo, hi in ((1, 6), (6, 11), (11, 15)):
            row([(f"Sp{i}", f"spell{i}") for i in range(lo, hi)])

        slot = None
        save_file = editor.get_save_file()
        if save_file:
            try:
                slot = save_file.characters[editor.get_char_slot()]
            except Exception:
                slot = None
        if slot:
            max_spells = _max_spell_slots(slot)
            for i in range(1, 15):
                key = f"spell{i}"
                if i > max_spells and editor._get_raw(key) == 0:
                    btn = self._cells.get(key)
                    if btn:
                        btn.configure(state="disabled")
                        self._captions[key].configure(text="locked")

        self.refresh_all()

        btn_row = ctk.CTkFrame(self, fg_color=("gray86", "gray25"))
        btn_row.pack(fill=ctk.X, padx=10, pady=(0, 10))
        ctk.CTkButton(
            btn_row,
            text="Apply Equipment Changes",
            command=editor.apply_changes,
            width=240,
        ).pack(pady=6)

    def _build_cell(self, parent, label: str, key: str, enabled: bool = True):
        col = ctk.CTkFrame(parent, fg_color="transparent", width=_CELL_W)
        col.pack(side=ctk.LEFT, padx=3)
        ctk.CTkLabel(
            col,
            text=label,
            font=("Segoe UI", 9, "bold"),
            text_color=("gray40", "gray65"),
        ).pack()
        btn = ctk.CTkButton(
            col,
            text="",
            width=_ICON_SIZE + 8,
            height=_ICON_SIZE + 8,
            fg_color=("gray80", "gray20"),
            command=lambda k=key: self._pick(k),
        )
        btn.pack()
        cap = ctk.CTkLabel(
            col, text="(empty)", font=("Segoe UI", 8), wraplength=_CELL_W - 4
        )
        cap.pack()
        self._cells[key] = btn
        self._captions[key] = cap

    def _pick(self, key: str):
        owned = self._editor._owned_items_for_key(key)

        def on_select(raw_value: int, handle: int):
            self._editor.equipment_vars[key].set(str(raw_value))
            self._editor._handles[key] = handle
            # Deferred: let the picker dialog finish destroying itself first,
            # otherwise the button's image update can be lost.
            self.after(50, lambda: self.refresh_cell(key))

        _VisualItemPickerDialog(self, owned, on_select)

    def refresh_cell(self, key: str):
        btn = self._cells.get(key)
        cap = self._captions.get(key)
        if btn is None:
            return
        # A locked (disabled) empty slot keeps its "locked" caption - never
        # overwritten by a name/empty refresh.
        if str(btn.cget("state")) == "disabled":
            return
        raw = self._editor._get_raw(key)
        is_cnv = self._editor._is_cnv_save()
        img = _resolve_icon(key, raw, is_cnv)
        if img:
            ctk_img = ctk.CTkImage(
                light_image=img, dark_image=img, size=(_ICON_SIZE, _ICON_SIZE)
            )
            self._ctk_images.append(ctk_img)
            btn.configure(image=ctk_img, text="")
        else:
            btn.configure(image=None, text="empty")
        btn.update_idletasks()
        if cap is not None:
            name = _resolve_name(key, raw, is_cnv)
            if not name:
                cap.configure(text="(empty)")
            else:
                cap.configure(text=name if len(name) <= 40 else name[:37] + "...")

    def refresh_all(self):
        for key in self._cells:
            self.refresh_cell(key)


# ---- editor -----------------------------------------------------------------


class EquipmentEditor:
    """Equipment editor: view and select equipped items per slot, plus loadouts."""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_char_slot_callback,
        get_save_path_callback,
    ):
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_char_slot = get_char_slot_callback
        self.get_save_path = get_save_path_callback

        self.equipment_vars: dict[str, ctk.StringVar] = {}
        self.equipment_name_labels: dict[str, ctk.CTkLabel] = {}
        self._pick_buttons: dict[str, ctk.CTkButton] = {}
        # Parallel to equipment_vars. For weapon/armor: gaitem_handle.
        # For talisman/quickitem/pouch: direct handle (0xA0/0xB0 | base_id).
        # For spell/physick: unused (0), those fields store the raw id only.
        self._handles: dict[str, int] = {}

        self.frame = None

    # ---- UI -----------------------------------------------------------------

    def setup_ui(self):
        self.frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True)
        bind_mousewheel(self.frame)

        top_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        top_row.pack(fill="x", pady=5)

        self._build_section(
            top_row,
            "Weapons",
            "left",
            [
                ("Right Hand 1", "right_hand_armament1"),
                ("Right Hand 2", "right_hand_armament2"),
                ("Right Hand 3", "right_hand_armament3"),
                ("Left Hand 1", "left_hand_armament1"),
                ("Left Hand 2", "left_hand_armament2"),
                ("Left Hand 3", "left_hand_armament3"),
            ],
        )
        self._build_section(
            top_row,
            "Armor",
            "left",
            [
                ("Head", "head"),
                ("Chest", "chest"),
                ("Arms", "arms"),
                ("Legs", "legs"),
            ],
        )

        mid_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        mid_row.pack(fill="x", pady=5)

        self._build_section(
            mid_row,
            "Talismans",
            "left",
            [
                ("Talisman 1", "talisman1"),
                ("Talisman 2", "talisman2"),
                ("Talisman 3", "talisman3"),
                ("Talisman 4", "talisman4"),
            ],
        )
        self._build_section(
            mid_row,
            "Arrows & Bolts",
            "left",
            [
                ("Arrows 1", "arrows1"),
                ("Arrows 2", "arrows2"),
                ("Bolts 1", "bolts1"),
                ("Bolts 2", "bolts2"),
            ],
        )

        spell_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        spell_row.pack(fill="x", pady=5)

        self._build_section(
            spell_row,
            "Spells (1-7)",
            "left",
            [(f"Spell {i}", f"spell{i}") for i in range(1, 8)],
        )
        self._build_section(
            spell_row,
            "Spells (8-14)",
            "left",
            [(f"Spell {i}", f"spell{i}") for i in range(8, 15)],
        )

        misc_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        misc_row.pack(fill="x", pady=5)

        self._build_section(
            misc_row,
            "Physick Tears",
            "left",
            [("Tear 1", "physick1"), ("Tear 2", "physick2")],
        )
        self._build_section(
            misc_row,
            "Pouch",
            "left",
            [(f"Pouch {i}", f"pouch{i}") for i in range(1, 7)],
        )

        quick_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        quick_row.pack(fill="x", pady=5)

        self._build_section(
            quick_row,
            "Quick Items (1-5)",
            "left",
            [(f"Quick Item {i}", f"quickitem{i}") for i in range(1, 6)],
        )
        self._build_section(
            quick_row,
            "Quick Items (6-10)",
            "left",
            [(f"Quick Item {i}", f"quickitem{i}") for i in range(6, 11)],
        )

        loadout_frame = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        loadout_frame.pack(fill="x", pady=(5, 0))
        ctk.CTkLabel(
            loadout_frame, text="Loadouts", font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=8, pady=(6, 0))
        loadout_btns = ctk.CTkFrame(loadout_frame, fg_color="transparent")
        loadout_btns.pack(fill="x", padx=6, pady=(2, 8))
        ctk.CTkButton(
            loadout_btns,
            text="Save Loadout",
            command=self.save_loadout,
            width=150,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            loadout_btns,
            text="Load Loadout",
            command=self.load_loadout,
            width=150,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            loadout_btns,
            text="Export to File...",
            command=self.export_loadout_file,
            width=150,
            fg_color=("gray70", "gray35"),
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            loadout_btns,
            text="Import from File...",
            command=self.import_loadout_file,
            width=150,
            fg_color=("gray70", "gray35"),
        ).pack(side="left")

        loadout_btns2 = ctk.CTkFrame(loadout_frame, fg_color="transparent")
        loadout_btns2.pack(fill="x", padx=6, pady=(0, 8))
        ctk.CTkButton(
            loadout_btns2,
            text="Share via Code...",
            command=self.share_loadout_code,
            width=150,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            loadout_btns2,
            text="Import via Code...",
            command=self.import_loadout_code,
            width=150,
        ).pack(side="left")

        btn_frame = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(
            btn_frame,
            text="Visual Picker...",
            command=self.open_visual_picker,
            width=180,
            fg_color=("gray70", "gray35"),
        ).pack(side="left", padx=(6, 6), pady=6)
        ctk.CTkButton(
            btn_frame,
            text="Apply Equipment Changes",
            command=self.apply_changes,
            width=240,
        ).pack(side="left", pady=6)

    def _build_section(
        self, parent, title: str, side: str, slots: list[tuple[str, str]]
    ):
        frame = ctk.CTkFrame(parent, fg_color=("gray86", "gray25"))
        frame.pack(side=side, fill="both", expand=True, padx=4)

        ctk.CTkLabel(frame, text=title, font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=8, pady=(6, 0)
        )

        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=6, pady=4)

        for i, (label, key) in enumerate(slots):
            ctk.CTkLabel(grid, text=f"{label}:").grid(
                row=i, column=0, sticky="w", padx=4, pady=3
            )

            var = ctk.StringVar(value="0")
            self.equipment_vars[key] = var
            self._handles.setdefault(key, 0)

            # Read-only display showing the resolved item name; click to pick
            name_label = ctk.CTkLabel(
                grid,
                text="(empty)",
                text_color="#60a5fa",
                width=220,
                anchor="w",
                cursor="hand2",
            )
            name_label.grid(row=i, column=1, sticky="w", padx=4, pady=3)
            self.equipment_name_labels[key] = name_label
            name_label.bind("<Button-1>", lambda _e, k=key: self._open_picker(k))

            # Small pick button
            pick_btn = ctk.CTkButton(
                grid,
                text="...",
                width=28,
                height=24,
                command=lambda k=key: self._open_picker(k),
            )
            pick_btn.grid(row=i, column=2, padx=(0, 4), pady=3)
            self._pick_buttons[key] = pick_btn

            trace_variable(var, "w", lambda *_a, k=key: self.update_equipment_name(k))

    # ---- picker -------------------------------------------------------------

    def _is_cnv_save(self) -> bool:
        sf = self.get_save_file()
        if sf and hasattr(sf, "is_convergence"):
            return bool(sf.is_convergence)
        return ".cnv" in str(self.get_save_path() or "").lower()

    def _is_co2_save(self) -> bool:
        return ".co2" in str(self.get_save_path() or "").lower()

    def _owned_items_for_key(self, key: str) -> list[tuple[int, int, str, str]]:
        save_file = self.get_save_file()
        if not save_file:
            return []
        slot_idx = self.get_char_slot()
        try:
            slot = save_file.characters[slot_idx]
        except Exception:
            return []

        cats = set(_SLOT_CATS.get(key, []))
        is_cnv = self._is_cnv_save()
        is_co2 = self._is_co2_save()
        if key in _WEAPON_KEYS:
            owned = _owned_gaitem_items(slot, 0x80000000, cats, key, is_cnv, is_co2)
        elif key in _ARMOR_KEYS:
            owned = _owned_gaitem_items(slot, 0x90000000, cats, key, is_cnv, is_co2)
        elif key in _TALISMAN_KEYS:
            owned = _owned_direct_items(slot, cats, 0x20000000, is_cnv, is_co2)
        elif key in _GOODS_KEYS:
            owned = _owned_direct_items(slot, cats, 0x40000000, is_cnv, is_co2)
        else:
            return []

        # An item already assigned to another slot cannot be assigned again -
        # exclude handles currently in use elsewhere (not this slot itself).
        used_elsewhere = {
            h for k, h in self._handles.items() if k != key and h not in (0,)
        }
        return [item for item in owned if item[1] not in used_elsewhere]

    def _open_picker(self, key: str):
        owned = self._owned_items_for_key(key)

        def on_select(raw_value: int, handle: int):
            self.equipment_vars[key].set(str(raw_value))
            self._handles[key] = handle

        _ItemPickerDialog(self.parent, owned, on_select)

    def open_visual_picker(self):
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first.", parent=self.parent
            )
            return
        _VisualEquipmentBrowser(self.parent, self)

    # ---- data ---------------------------------------------------------------

    def load_equipment(self):
        save_file = self.get_save_file()
        if not save_file:
            return

        slot_idx = self.get_char_slot()
        if slot_idx < 0 or slot_idx >= len(save_file.characters):
            return

        slot = save_file.characters[slot_idx]
        if (
            not hasattr(slot, "equipped_items_item_id")
            or not slot.equipped_items_item_id
        ):
            return

        equip_ids = slot.equipped_items_item_id
        equip_handles = getattr(slot, "equipped_items_gaitem_handle", None)
        getattr(slot, "equipped_armaments_and_items", None)

        for key in _WEAPON_KEYS | _ARMOR_KEYS | _TALISMAN_KEYS:
            raw = _decode_slot_value(getattr(equip_ids, key, 0))
            if key in _WEAPON_KEYS and raw == 110000:
                raw = 0  # unarmed/fists - not a real gaitem, treat as empty
            self.equipment_vars[key].set(str(raw))
            handle = getattr(equip_handles, key, 0) if equip_handles else 0
            self._handles[key] = 0 if handle == 0xFFFFFFFF else handle

        spells = getattr(slot, "equipped_spells", None)
        if spells and spells.spell_slots:
            for i in range(1, 15):
                key = f"spell{i}"
                raw = _decode_slot_value(spells.spell_slots[i - 1].spell_id)
                self.equipment_vars[key].set(str(raw))
                self._handles[key] = 0

        physics = getattr(slot, "equipped_physics", None)
        if physics:
            self.equipment_vars["physick1"].set(
                str(_decode_slot_value(physics.slot1, 0x40000000))
            )
            self.equipment_vars["physick2"].set(
                str(_decode_slot_value(physics.slot2, 0x40000000))
            )
            self._handles["physick1"] = 0
            self._handles["physick2"] = 0

        # Quick items and pouch: the gaitem handle is the ground truth for
        # what is actually equipped. The equipped_armaments_and_items mirror
        # field can drift from it, so it is only used as a write target,
        # never read from here. A handle whose prefix isn't the goods direct-
        # handle format (0xB0......) is not a valid goods reference - treat
        # as empty rather than masking out a misleading raw value.
        equipped_items = getattr(slot, "equipped_items", None)
        for i in range(1, 11):
            key = f"quickitem{i}"
            handle = (
                equipped_items.quick_items[i - 1].gaitem_handle
                if equipped_items and equipped_items.quick_items
                else 0
            )
            if handle == 0xFFFFFFFF or (handle & 0xF0000000) != 0xB0000000:
                handle = 0
            raw = 0 if handle == 0 else (handle & 0x00FFFFFF)
            self.equipment_vars[key].set(str(raw))
            self._handles[key] = handle
        for i in range(1, 7):
            key = f"pouch{i}"
            handle = (
                equipped_items.pouch_items[i - 1].gaitem_handle
                if equipped_items and equipped_items.pouch_items
                else 0
            )
            if handle == 0xFFFFFFFF or (handle & 0xF0000000) != 0xB0000000:
                handle = 0
            raw = 0 if handle == 0 else (handle & 0x00FFFFFF)
            self.equipment_vars[key].set(str(raw))
            self._handles[key] = handle

        for key in self.equipment_vars:
            self.update_equipment_name(key)

        self._apply_spell_lock(slot)

    def _apply_spell_lock(self, slot):
        """Disable pick buttons for empty spell slots beyond the estimated cap.

        Never touches a slot that already has a real spell in it - see
        _max_spell_slots' docstring for why this must stay non-destructive.
        """
        max_spells = _max_spell_slots(slot)
        for i in range(1, 15):
            key = f"spell{i}"
            btn = self._pick_buttons.get(key)
            label = self.equipment_name_labels.get(key)
            locked = i > max_spells and self._get_raw(key) == 0
            if btn:
                btn.configure(state="disabled" if locked else "normal")
            if label:
                if locked:
                    label.unbind("<Button-1>")
                    label.configure(text="locked", cursor="arrow")
                else:
                    label.bind("<Button-1>", lambda _e, k=key: self._open_picker(k))
                    label.configure(cursor="hand2")

    def update_equipment_name(self, key: str):
        label = self.equipment_name_labels.get(key)
        if label is None:
            return
        try:
            raw = self._get_raw(key)
            name = _resolve_name(key, raw, self._is_cnv_save())
            if not name:
                label.configure(text="(empty)", text_color=("gray50", "gray55"))
                return
            if len(name) > 32:
                name = name[:29] + "..."
            label.configure(text=name, text_color="#60a5fa")
        except Exception:
            label.configure(text="(empty)", text_color=("gray50", "gray55"))

    # ---- apply --------------------------------------------------------------

    def apply_changes(self):
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first.", parent=self.parent
            )
            return

        slot_idx = self.get_char_slot()

        if not CTkMessageBox.askyesno(
            "Confirm",
            f"Apply equipment changes to Slot {slot_idx + 1}?\n\nA backup will be created.",
            parent=self.parent,
        ):
            return

        try:
            if isinstance(save_file._raw_data, bytes):
                save_file._raw_data = bytearray(save_file._raw_data)

            save_path = self.get_save_path()
            if save_path:
                from er_save_manager.backup.manager import BackupManager

                BackupManager(Path(save_path)).create_backup(
                    description=f"before_edit_equipment_slot_{slot_idx + 1}",
                    operation=f"edit_equipment_slot_{slot_idx + 1}",
                    save=save_file,
                )

            slot = save_file.characters[slot_idx]
            if (
                not hasattr(slot, "equipped_items_item_id")
                or not slot.equipped_items_item_id
            ):
                CTkMessageBox.showerror(
                    "Error", "Character has no equipment data.", parent=self.parent
                )
                return

            # Write item_id to both structs that store item IDs, and handle
            # to the gaitem handle struct, for weapon/armor/talisman/ammo.
            equip_ids = slot.equipped_items_item_id
            equip_armaments = getattr(slot, "equipped_armaments_and_items", None)
            equip_handles = getattr(slot, "equipped_items_gaitem_handle", None)

            for key in _WEAPON_KEYS | _ARMOR_KEYS | _TALISMAN_KEYS:
                item_id = _encode_slot_value(self._get_raw(key))
                handle = self._handles.get(key, 0)

                if hasattr(equip_ids, key):
                    setattr(equip_ids, key, item_id)
                if equip_armaments and hasattr(equip_armaments, key):
                    setattr(equip_armaments, key, item_id)
                if equip_handles and hasattr(equip_handles, key):
                    setattr(equip_handles, key, handle)

            # equipped_items_equip_index is a separate identity field the
            # game's inventory/equipment menu reads, distinct from item_id/
            # gaitem_handle which drive the in-hand model. Confirmed against
            # real save data (before/after diffs of normal in-game equip
            # changes): it is a position in a conceptual [key_items,
            # common_items] concatenation - key_items position used as-is,
            # common_items position offset by the held key capacity (0x180).
            equip_index = getattr(slot, "equipped_items_equip_index", None)
            if equip_index is not None:
                for key in _WEAPON_KEYS | _ARMOR_KEYS | _TALISMAN_KEYS:
                    setattr(
                        equip_index,
                        key,
                        _find_equip_index(slot, self._handles.get(key, 0)),
                    )

            # Spells: raw id only, no handle concept for this struct.
            spells = getattr(slot, "equipped_spells", None)
            if spells and spells.spell_slots:
                for i in range(1, 15):
                    spells.spell_slots[i - 1].spell_id = _encode_slot_value(
                        self._get_raw(f"spell{i}")
                    )

            # Wondrous Physick tears: goods category bit included on disk.
            physics = getattr(slot, "equipped_physics", None)
            if physics:
                physics.slot1 = _encode_slot_value(
                    self._get_raw("physick1"), 0x40000000
                )
                physics.slot2 = _encode_slot_value(
                    self._get_raw("physick2"), 0x40000000
                )

            # Quick items and pouch: goods-category mirror id plus the
            # direct gaitem handle (handle's own empty value is 0, not
            # 0xFFFFFFFF, so it is written as-is). Flasks are skipped
            # entirely - equipping them here duplicates them in-game.
            equipped_items = getattr(slot, "equipped_items", None)
            for i in range(1, 11):
                key = f"quickitem{i}"
                raw = self._get_raw(key)
                if _is_flask(raw):
                    continue
                handle = self._handles.get(key, 0)
                if equip_armaments and hasattr(equip_armaments, key):
                    setattr(equip_armaments, key, _encode_slot_value(raw, 0x40000000))
                if equipped_items and equipped_items.quick_items:
                    equipped_items.quick_items[i - 1].gaitem_handle = handle
                    equipped_items.quick_items[i - 1].equip_index = _find_equip_index(
                        slot, handle
                    )
            for i in range(1, 7):
                key = f"pouch{i}"
                raw = self._get_raw(key)
                if _is_flask(raw):
                    continue
                handle = self._handles.get(key, 0)
                if equip_armaments and hasattr(equip_armaments, key):
                    setattr(equip_armaments, key, _encode_slot_value(raw, 0x40000000))
                if equipped_items and equipped_items.pouch_items:
                    equipped_items.pouch_items[i - 1].gaitem_handle = handle
                    equipped_items.pouch_items[i - 1].equip_index = _find_equip_index(
                        slot, handle
                    )

            _patch_equipment(save_file, slot_idx, slot)
            save_file.recalculate_checksums()
            if save_path:
                save_file.to_file(Path(save_path))

            CTkMessageBox.showinfo(
                "Done", "Equipment changes applied.", parent=self.parent
            )
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to apply equipment changes:\n{e}", parent=self.parent
            )

    def _get_raw(self, key: str) -> int:
        try:
            raw = self.equipment_vars[key].get()
            return int(raw) if raw not in ("", None) else 0
        except (ValueError, KeyError):
            return 0

    # ---- loadouts -------------------------------------------------------------

    def _collect_state(self) -> dict[str, int]:
        return {key: self._get_raw(key) for key in self.equipment_vars}

    def _apply_state(self, data: dict) -> tuple[list[str], list[tuple[str, int]]]:
        """Apply a loadout dict to the current vars, validating ownership.

        Returns (skipped_keys, unresolved) where unresolved is a list of
        (key, raw) pairs not currently owned - candidates for spawning.
        Handles already claimed earlier in this same pass are excluded too,
        so a loadout cannot assign one physical item to two slots.
        """
        skipped: list[str] = []
        unresolved: list[tuple[str, int]] = []
        claimed: set[int] = set()
        for key, raw in data.items():
            if key not in self.equipment_vars:
                continue
            try:
                raw = int(raw)
            except (TypeError, ValueError):
                continue
            if raw in _EMPTY_IDS:
                self.equipment_vars[key].set("0")
                self._handles[key] = 0
                continue
            if key in (_QUICKITEM_KEYS | _POUCH_KEYS) and _is_flask(raw):
                continue  # never touched - equipping via the tool duplicates flasks
            owned = [o for o in self._owned_items_for_key(key) if o[1] not in claimed]
            match = next((o for o in owned if o[0] == raw), None)
            if match is None:
                skipped.append(key)
                unresolved.append((key, raw))
                continue
            self.equipment_vars[key].set(str(raw))
            self._handles[key] = match[1]
            claimed.add(match[1])

        for key in self.equipment_vars:
            self.update_equipment_name(key)
        return skipped, unresolved

    def _spawn_unresolved(self, unresolved: list[tuple[str, int]]) -> int:
        """Spawn unowned loadout items into inventory via inventory_ops.add_item.

        Returns the number successfully spawned. Caller should re-run
        _apply_state for the same data afterward to pick them up.
        """
        save_file = self.get_save_file()
        slot_idx = self.get_char_slot()
        from er_save_manager.data.item_database import get_item_database
        from er_save_manager.parser.inventory_ops import add_item

        db = get_item_database()
        slot = save_file.characters[slot_idx]
        spawned = 0
        for key, raw in unresolved:
            try:
                if key in _WEAPON_KEYS:
                    full_id = raw
                    true_base = (raw & 0x0FFFFFFF) // 10000 * 10000
                    item = db.items_by_id.get(true_base)
                    upgrade = raw % 100
                    reinf = (
                        getattr(item, "reinforcement", "standard")
                        if item
                        else "standard"
                    )
                elif key in _ARMOR_KEYS:
                    full_id = 0x10000000 | raw
                    upgrade, reinf = 0, "standard"
                elif key in _TALISMAN_KEYS:
                    full_id = 0x20000000 | raw
                    upgrade, reinf = 0, "standard"
                elif key in _GOODS_KEYS:
                    full_id = 0x40000000 | raw
                    upgrade, reinf = 0, "standard"
                else:
                    continue

                loc = (
                    "storage"
                    if all(
                        it.gaitem_handle != 0 for it in slot.inventory_held.common_items
                    )
                    else "held"
                )
                add_item(
                    save_file,
                    slot_idx,
                    full_id,
                    1,
                    loc,
                    upgrade=upgrade,
                    gem_full_id=0,
                    reinforcement=reinf,
                )
                spawned += 1
            except Exception:
                continue
        return spawned

    def _loadout_store_path(self) -> Path:
        from er_save_manager.ui.settings import Settings

        return Settings._get_default_settings_path().parent / "equipment_loadouts.json"

    def _read_loadout_store(self) -> dict:
        path = self._loadout_store_path()
        if not path.exists():
            return {}
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_loadout_store(self, store: dict) -> None:
        path = self._loadout_store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(store, f, indent=2)

    def save_loadout(self):
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first.", parent=self.parent
            )
            return

        name = self._ask_code("Save Loadout", "Loadout name:")
        if not name:
            return

        store = self._read_loadout_store()
        store[name] = self._collect_state()
        try:
            self._write_loadout_store(store)
            CTkMessageBox.showinfo(
                "Saved", f"Loadout '{name}' saved.", parent=self.parent
            )
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to save loadout:\n{e}", parent=self.parent
            )

    def load_loadout(self):
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first.", parent=self.parent
            )
            return

        store = self._read_loadout_store()
        if not store:
            CTkMessageBox.showinfo(
                "No Loadouts", "No saved loadouts yet.", parent=self.parent
            )
            return

        _LoadoutBrowserDialog(self.parent, store, self._on_loadout_chosen)

    def _on_loadout_chosen(self, name: str, action: str, store: dict) -> None:
        if action == "delete":
            store.pop(name, None)
            self._write_loadout_store(store)
            return
        slots = store.get(name, {})
        self._apply_loadout_data(slots)

    def _apply_loadout_data(self, slots: dict) -> None:
        skipped, unresolved = self._apply_state(slots)
        if not unresolved:
            CTkMessageBox.showinfo(
                "Loadout Applied",
                "Loadout applied. Click Apply Equipment Changes to save.",
                parent=self.parent,
            )
            return

        if CTkMessageBox.askyesno(
            "Items Not Owned",
            f"{len(unresolved)} item(s) in this loadout are not in your "
            "inventory:\n"
            + ", ".join(k for k, _ in unresolved)
            + "\n\nSpawn them into inventory now, then equip them?",
            parent=self.parent,
        ):
            spawned = self._spawn_unresolved(unresolved)
            skipped, unresolved = self._apply_state(slots)
            CTkMessageBox.showinfo(
                "Loadout Applied",
                f"Spawned {spawned} item(s). "
                + (
                    f"{len(unresolved)} slot(s) still could not be resolved: "
                    + ", ".join(k for k, _ in unresolved)
                    if unresolved
                    else "All slots resolved."
                )
                + "\n\nClick Apply Equipment Changes to save.",
                parent=self.parent,
            )
        else:
            CTkMessageBox.showwarning(
                "Loadout Applied",
                "Applied, skipping items not owned:\n"
                + ", ".join(skipped)
                + "\n\nClick Apply Equipment Changes to save the rest.",
                parent=self.parent,
            )

    def export_loadout_file(self):
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first.", parent=self.parent
            )
            return

        path = pick_file(
            title="Export Equipment Loadout",
            save=True,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        data = {
            "format": "er-save-manager-equipment-loadout",
            "version": 1,
            "slots": self._collect_state(),
        }

        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            CTkMessageBox.showinfo(
                "Exported",
                f"Loadout exported to:\n{Path(path).name}",
                parent=self.parent,
            )
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to export loadout:\n{e}", parent=self.parent
            )

    def import_loadout_file(self):
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first.", parent=self.parent
            )
            return

        path = pick_file(
            title="Import Equipment Loadout",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path) as f:
                data = json.load(f)
            slots = data.get("slots", data) if isinstance(data, dict) else {}
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to import loadout:\n{e}", parent=self.parent
            )
            return

        self._apply_loadout_data(slots)

    def _show_share_code(self, code: str, description: str = "loadout"):
        """Show a dialog with a generated share code and a copy button.

        Mirrors appearance_tab.py's _show_share_code - a readonly CTkEntry
        the user can select/copy manually, plus a Copy Code button.
        """
        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Share Code")
        dialog.resizable(False, False)
        dialog.transient(self.parent)

        dialog.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        width, height = 420, 190
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        force_render_dialog(dialog)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text=f"Shared {description}", font=("Segoe UI", 13, "bold")
        ).pack(pady=(15, 5))
        ctk.CTkLabel(
            dialog,
            text="Send this code to share it:",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(pady=(0, 10))

        code_entry = ctk.CTkEntry(
            dialog, width=300, justify="center", font=("Consolas", 12)
        )
        code_entry.pack(pady=(0, 15))
        code_entry.insert(0, code)
        code_entry.configure(state="readonly")

        def copy_code():
            dialog.clipboard_clear()
            dialog.clipboard_append(code)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack()
        ctk.CTkButton(btn_frame, text="Copy Code", command=copy_code, width=120).pack(
            side=tk.LEFT, padx=5
        )
        ctk.CTkButton(btn_frame, text="Close", command=dialog.destroy, width=100).pack(
            side=tk.LEFT, padx=5
        )

    def _ask_code(self, title: str, text: str) -> str | None:
        """Centered modal single-line input dialog, mirrors appearance_tab.py's _ask_code."""
        from er_save_manager.ui.utils import force_render_dialog

        result = [None]
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.transient(self.parent)

        dialog.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        width, height = 380, 150
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        force_render_dialog(dialog)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=text, font=("Segoe UI", 11)).pack(pady=(15, 6))
        var = ctk.StringVar()
        entry = ctk.CTkEntry(dialog, textvariable=var, width=280, justify="center")
        entry.pack(pady=(0, 12))
        entry.focus_set()

        def confirm(_event=None):
            result[0] = var.get().strip()
            dialog.destroy()

        entry.bind("<Return>", confirm)
        entry.bind("<Escape>", lambda _e: dialog.destroy())

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack()
        ctk.CTkButton(btn_frame, text="OK", command=confirm, width=100).pack(
            side=tk.LEFT, padx=5
        )
        ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy, width=100).pack(
            side=tk.LEFT, padx=5
        )

        self.parent.wait_window(dialog)
        return result[0]

    def share_loadout_code(self):
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first.", parent=self.parent
            )
            return

        from er_save_manager.data.equipment_sharing import share_loadout

        save_type = (
            "cnv"
            if self._is_cnv_save()
            else ("co2" if self._is_co2_save() else "vanilla")
        )
        code = share_loadout(self._collect_state(), save_type=save_type)
        if not code:
            CTkMessageBox.showerror(
                "Error",
                "Failed to share loadout. Check your internet connection.",
                parent=self.parent,
            )
            return

        self._show_share_code(code, "equipment loadout")

    def import_loadout_code(self):
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first.", parent=self.parent
            )
            return

        code = self._ask_code("Import via Code", "Paste share code:")
        if not code:
            return

        from er_save_manager.data.equipment_sharing import fetch_loadout

        slots = fetch_loadout(code)
        if slots is None:
            CTkMessageBox.showerror(
                "Not Found",
                "No loadout found for that code, or the connection failed.",
                parent=self.parent,
            )
            return

        self._apply_loadout_data(slots)
