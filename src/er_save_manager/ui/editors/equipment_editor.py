"""
Equipment Editor - view and edit equipped items per slot.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel, trace_variable

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
]
_ARMOR_CATS = ["Armor", "DLC Armor"]
_TALISMAN_CATS = ["Talismans", "DLC Talismans"]
_AMMO_CATS = ["Ammo", "DLC Ammo"]

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


def _resolve_name(key: str, raw_id: int) -> str:
    if raw_id in _EMPTY_IDS:
        return ""

    from er_save_manager.data.item_database import get_item_name

    if key in _WEAPON_KEYS:
        upgrade = raw_id % 100
        name = get_item_name(raw_id, upgrade_level=upgrade)
        if name.startswith("Unknown"):
            return ""
        affinity_code = (raw_id // 100) % 100
        if affinity_code != 0:
            aff = _AFFINITY_BY_CODE.get(affinity_code, str(affinity_code))
            name = f"{name} [{aff}]"
        return name

    if key in _ARMOR_KEYS:
        name = get_item_name(0x10000000 | raw_id)
        return "" if name.startswith("Unknown") else name

    if key in _TALISMAN_KEYS:
        name = get_item_name(0x20000000 | raw_id)
        if name.startswith("Unknown"):
            name = get_item_name(0x20000000 | (raw_id & 0x00FFFFFF))
        return "" if name.startswith("Unknown") else name

    return ""


# ---- item picker dialog -----------------------------------------------------


class _ItemPickerDialog(ctk.CTkToplevel):
    """Small searchable item picker for a single equipment slot."""

    _AFFINITY_NAMES = [
        "Standard",
        "Heavy",
        "Keen",
        "Quality",
        "Fire",
        "Flame Art",
        "Lightning",
        "Sacred",
        "Magic",
        "Cold",
        "Poison",
        "Blood",
        "Occult",
    ]
    _AFFINITY_CODES = {n: i for i, n in enumerate(_AFFINITY_NAMES)}

    def __init__(self, parent, slot_key: str, on_select):
        super().__init__(parent)
        self.title("Select Item")
        self.resizable(False, True)
        self.transient(parent)
        self.attributes("-alpha", 0)

        self._on_select = on_select
        self._items: list = []
        self._visible: list = []
        self._is_weapon = slot_key in _WEAPON_KEYS

        # Taller if weapon (extra controls)
        self.geometry("420x520" if self._is_weapon else "420x460")

        self.update_idletasks()
        self.attributes("-alpha", 1)
        self.grab_set()

        cats = _SLOT_CATS.get(slot_key, [])

        # Search row
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill=ctk.X, padx=10, pady=(10, 4))
        ctk.CTkLabel(top, text="Search:").pack(side=ctk.LEFT, padx=(0, 6))
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter())
        ctk.CTkEntry(top, textvariable=self._search_var, width=320).pack(side=ctk.LEFT)

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

        # Upgrade + affinity (weapons only)
        if self._is_weapon:
            opts = ctk.CTkFrame(self, fg_color="transparent")
            opts.pack(fill=ctk.X, padx=10, pady=(2, 0))

            ctk.CTkLabel(opts, text="Upgrade:").pack(side=ctk.LEFT, padx=(0, 4))
            self._upgrade_var = ctk.IntVar(value=0)
            ctk.CTkEntry(opts, textvariable=self._upgrade_var, width=50).pack(
                side=ctk.LEFT, padx=(0, 14)
            )

            ctk.CTkLabel(opts, text="Affinity:").pack(side=ctk.LEFT, padx=(0, 4))
            self._affinity_var = ctk.StringVar(value="Standard")
            ctk.CTkComboBox(
                opts,
                variable=self._affinity_var,
                values=self._AFFINITY_NAMES,
                width=130,
            ).pack(side=ctk.LEFT)

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

        self._load_items(cats)

    def _load_items(self, cats: list[str]):
        try:
            from er_save_manager.data.item_database import get_item_database

            db = get_item_database()
            self._items = []
            for cat in cats:
                self._items.extend(db.get_items_by_category(cat))
        except Exception:
            pass
        self._filter()

    def _filter(self):
        query = self._search_var.get().lower().strip()
        self._visible = (
            [i for i in self._items if query in i.name.lower()]
            if query
            else list(self._items)
        )
        self._lb.delete(0, tk.END)
        for item in self._visible[:300]:
            self._lb.insert(tk.END, item.name)

    def _confirm(self):
        sel = self._lb.curselection()
        if not sel or sel[0] >= len(self._visible):
            return
        item = self._visible[sel[0]]
        item_id = item.id

        if self._is_weapon:
            try:
                upgrade = max(0, min(25, int(self._upgrade_var.get())))
            except (ValueError, tk.TclError):
                upgrade = 0
            affinity_code = self._AFFINITY_CODES.get(self._affinity_var.get(), 0)
            item_id = item_id + affinity_code * 100 + upgrade

        self._on_select(item_id)
        self.destroy()

    def _clear(self):
        self._on_select(0)
        self.destroy()


# ---- editor -----------------------------------------------------------------


class EquipmentEditor:
    """Equipment editor: view and select equipped items per slot."""

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
        # Parallel to equipment_vars: stores the gaitem handle for each slot.
        # item_id goes to equipped_items_item_id and equipped_armaments_and_items.
        # gaitem_handle goes to equipped_items_gaitem_handle.
        self._gaitem_handles: dict[str, int] = {}

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

        btn_frame = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(
            btn_frame,
            text="Apply Equipment Changes",
            command=self.apply_changes,
            width=240,
        ).pack(pady=6)

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
            ctk.CTkButton(
                grid,
                text="...",
                width=28,
                height=24,
                command=lambda k=key: self._open_picker(k),
            ).grid(row=i, column=2, padx=(0, 4), pady=3)

            trace_variable(var, "w", lambda *_a, k=key: self.update_equipment_name(k))

    # ---- picker -------------------------------------------------------------

    def _gaitem_handle_for_item(self, key: str, item_id: int) -> int:
        """
        Find the gaitem handle for item_id in the current character's gaitem_map.
        Returns 0 if not found (item not in inventory / talisman direct handle).
        """
        save_file = self.get_save_file()
        if not save_file or item_id == 0:
            return 0

        slot_idx = self.get_char_slot()
        try:
            slot = save_file.characters[slot_idx]
        except Exception:
            return 0

        if key in _TALISMAN_KEYS:
            # Talismans use direct 0xA0 handles, no gaitem entry
            return 0xA0000000 | (item_id & 0x00FFFFFF)

        # For weapons/armor/ammo: find matching gaitem entry
        for g in getattr(slot, "gaitem_map", []):
            if g.gaitem_handle == 0 or g.gaitem_handle == 0xFFFFFFFF:
                continue
            prefix = g.gaitem_handle & 0xF0000000
            if key in _WEAPON_KEYS and prefix == 0x80000000:
                if g.item_id == item_id:
                    return g.gaitem_handle
            elif key in _ARMOR_KEYS and prefix == 0x90000000:
                if g.item_id == item_id or g.item_id == (item_id & 0x0FFFFFFF):
                    return g.gaitem_handle

        return 0

    def _open_picker(self, key: str):
        def on_select(item_id: int):
            self.equipment_vars[key].set(str(item_id))
            self._gaitem_handles[key] = self._gaitem_handle_for_item(key, item_id)

        _ItemPickerDialog(self.parent, key, on_select)

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

        for key in self.equipment_vars:
            raw = getattr(equip_ids, key, 0) or 0
            self.equipment_vars[key].set(str(raw))
            # Load existing gaitem handle so apply preserves it when unchanged
            handle = getattr(equip_handles, key, 0) if equip_handles else 0
            self._gaitem_handles[key] = handle or 0

        for key in self.equipment_vars:
            self.update_equipment_name(key)

    def update_equipment_name(self, key: str):
        label = self.equipment_name_labels.get(key)
        if label is None:
            return
        try:
            raw = self._get_raw(key)
            name = _resolve_name(key, raw)
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

            # Write item_id to both structs that store item IDs
            equip_ids = slot.equipped_items_item_id
            equip_armaments = getattr(slot, "equipped_armaments_and_items", None)
            equip_handles = getattr(slot, "equipped_items_gaitem_handle", None)

            for key in self.equipment_vars:
                item_id = self._get_raw(key)
                gaitem_handle = self._gaitem_handles.get(key, 0)

                if hasattr(equip_ids, key):
                    setattr(equip_ids, key, item_id)
                if equip_armaments and hasattr(equip_armaments, key):
                    setattr(equip_armaments, key, item_id)
                if equip_handles and hasattr(equip_handles, key):
                    setattr(equip_handles, key, gaitem_handle)

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
