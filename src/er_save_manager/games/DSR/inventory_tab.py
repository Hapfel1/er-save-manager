"""
DSR Inventory Editor Tab

Left panel: current inventory with:
- Search box + category filter
- Sortable column headers (click to toggle asc/desc, arrow shown)
- Combined edit row: Quantity | Upgrade | Infusion | Apply Changes (one button)

Right panel: item spawner with full labels and validation.
All mutations backup then write immediately.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox

if TYPE_CHECKING:
    pass

_DATA_DIR = Path(__file__).parent / "data"
_DB: dict | None = None
_LOOKUP: dict[tuple[int, int], dict] | None = None


def _ensure_db() -> tuple[dict, dict]:
    global _DB, _LOOKUP
    if _DB is None:
        _DB = json.loads((_DATA_DIR / "items.json").read_text(encoding="utf-8"))
        _LOOKUP = {}
        for cat_key, cat_items in _DB.items():
            for item in cat_items:
                item["_cat"] = cat_key
                _LOOKUP[(int(item["Type"], 16) // 0x10000000, int(item["Id"], 16))] = (
                    item
                )
    return _DB, _LOOKUP  # type: ignore[return-value]


_CAT_LABELS: dict[str, str] = {
    "weapon_items": "Weapons",
    "ring_items": "Rings",
    "armor_items": "Armor",
    "key_items": "Key Items",
    "usable_items": "Usables",
    "ammunition_items": "Ammo",
    "material_items": "Materials",
    "magic_items": "Spells",
    "specials": "Special",
}
_INFUSION_NAMES = [
    "Standard",
    "Crystal",
    "Lightning",
    "Raw",
    "Magic",
    "Enchanted",
    "Divine",
    "Occult",
    "Fire",
    "Chaos",
]
# (header label, index in _all_items tuple, is_numeric)
_COL_META: dict[str, tuple[str, int, bool]] = {
    "name": ("Item", 1, False),
    "cat": ("Type", 2, False),
    "qty": ("Qty", 3, True),
    "slot": ("Slot", 4, True),
}


def _resolve_name(type_num: int, base_id: int, item_id: int) -> str:
    _, lookup = _ensure_db()
    entry = lookup.get((type_num, base_id))
    if entry is None:
        return f"Unknown (type={type_num:#x} id={item_id:#x})"
    name = entry["Name"]
    if type_num == 0:
        ul = item_id % 100
        inf_idx = ((item_id - ul) % 1000) // 100
        if ul > 0:
            name += f" +{ul}"
        if inf_idx > 0:
            name += f" ({_INFUSION_NAMES[inf_idx]})"
    return name


def _backup_and_save(dsr_save, save_path: Path, op: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=op, save=None)
    dsr_save.save_to_file(save_path)


def _validate_add(db_item: dict, qty: int, upg: int, inf: int) -> str | None:
    type_num = int(db_item["Type"], 16) // 0x10000000
    max_stack = int(db_item.get("MaxStackCount") or 1)
    if qty < 1 or qty > max_stack:
        return f"Quantity must be 1-{max_stack}."
    if upg > 0:
        max_up = db_item.get("MaxUpgrade") or 0
        if not max_up:
            return f"{db_item['Name']} cannot be upgraded."
        if upg > max_up:
            return f"Max upgrade for {db_item['Name']} is +{max_up}."
    if inf > 0:
        if type_num != 0:
            return "Only weapons can be infused."
        if not db_item.get("CanInfuse"):
            return f"{db_item['Name']} cannot be infused."
    return None


def _apply_treeview_style() -> None:
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "DSR.Treeview",
        background="#2b2b2b",
        foreground="white",
        fieldbackground="#2b2b2b",
        rowheight=22,
        borderwidth=0,
    )
    style.configure("DSR.Treeview.Heading", background="#3b3b3b", foreground="white")
    style.map("DSR.Treeview", background=[("selected", "#5a4a7a")])


class DSRInventoryTab:
    def __init__(self, parent, get_dsr_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = -1
        self._selected_slot_idx = -1
        self._selected_db_item: dict | None = None
        self._spawn_items: dict[str, dict] = {}
        self._all_items: list[tuple] = []  # (iid, name, cat_label, qty, slot_idx)
        self._sort_col: str | None = None
        self._sort_reverse: bool = False

    def setup_ui(self) -> None:
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(
            header, text="Inventory Editor", font=("Segoe UI", 16, "bold")
        ).pack(side="left")
        self._count_label = ctk.CTkLabel(
            header, text="", font=("Segoe UI", 10), text_color=("gray40", "gray70")
        )
        self._count_label.pack(side="right", padx=8)
        ctk.CTkButton(header, text="Load", command=self._load_selected, width=70).pack(
            side="right", padx=(6, 0)
        )
        self._slot_var = tk.StringVar()
        self._slot_combo = ctk.CTkComboBox(
            header, variable=self._slot_var, values=[], state="readonly", width=220
        )
        self._slot_combo.pack(side="right")
        ctk.CTkLabel(header, text="Slot:").pack(side="right", padx=(0, 6))

        main = ctk.CTkFrame(outer, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=2)

        _apply_treeview_style()
        self._build_inventory_panel(main)
        self._build_spawner_panel(main)

    # --- Left panel ----------------------------------------------------------- #

    def _build_inventory_panel(self, parent) -> None:
        frame = ctk.CTkFrame(parent, corner_radius=10)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text="Current Inventory", font=("Segoe UI", 12, "bold")
        ).grid(row=0, column=0, pady=(10, 4), padx=12, sticky="w")

        # Search + category filter
        frow = ctk.CTkFrame(frame, fg_color="transparent")
        frow.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
        frow.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(frow, text="Filter:").grid(row=0, column=0, padx=(0, 4))
        self._inv_search_var = tk.StringVar()
        self._inv_search_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(
            frow,
            textvariable=self._inv_search_var,
            placeholder_text="Search items...",
            width=150,
        ).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self._inv_cat_var = tk.StringVar(value="All")
        ctk.CTkComboBox(
            frow,
            variable=self._inv_cat_var,
            values=["All"] + list(_CAT_LABELS.values()),
            state="readonly",
            width=100,
            command=lambda _: self._apply_filter(),
        ).grid(row=0, column=2)

        # Treeview
        tf = tk.Frame(frame, bg="#2b2b2b")
        tf.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)
        self._inv_tree = ttk.Treeview(
            tf,
            columns=("name", "cat", "qty", "slot"),
            show="headings",
            style="DSR.Treeview",
            selectmode="browse",
        )
        for col, (label, _, _) in _COL_META.items():
            self._inv_tree.heading(
                col, text=label, command=lambda c=col: self._on_header_click(c)
            )
        self._inv_tree.column("name", width=200, minwidth=130)
        self._inv_tree.column("cat", width=80, minwidth=55)
        self._inv_tree.column("qty", width=45, minwidth=38, anchor="center")
        self._inv_tree.column("slot", width=45, minwidth=38, anchor="center")
        self._inv_tree.grid(row=0, column=0, sticky="nsew")
        self._inv_tree.bind("<<TreeviewSelect>>", self._on_inv_select)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self._inv_tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._inv_tree.configure(yscrollcommand=sb.set)

        # Combined edit row: Quantity | Upgrade | Infusion | [Apply Changes]
        edit_row = ctk.CTkFrame(frame, fg_color="transparent")
        edit_row.grid(row=3, column=0, sticky="ew", padx=8, pady=(2, 2))

        ctk.CTkLabel(edit_row, text="Quantity:").pack(side="left", padx=(0, 4))
        self._edit_qty_var = tk.StringVar(value="")
        self._edit_qty_entry = ctk.CTkEntry(
            edit_row,
            textvariable=self._edit_qty_var,
            width=55,
            justify="center",
            state="disabled",
        )
        self._edit_qty_entry.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(edit_row, text="Upgrade:").pack(side="left", padx=(0, 4))
        self._inv_upg_var = tk.StringVar(value="")
        self._inv_upg_entry = ctk.CTkEntry(
            edit_row,
            textvariable=self._inv_upg_var,
            width=45,
            justify="center",
            state="disabled",
        )
        self._inv_upg_entry.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(edit_row, text="Infusion:").pack(side="left", padx=(0, 4))
        self._inv_inf_var = tk.StringVar(value="Standard")
        self._inv_inf_combo = ctk.CTkComboBox(
            edit_row,
            variable=self._inv_inf_var,
            values=_INFUSION_NAMES,
            state="disabled",
            width=110,
        )
        self._inv_inf_combo.pack(side="left", padx=(0, 12))

        self._apply_edit_btn = ctk.CTkButton(
            edit_row,
            text="Apply Changes",
            command=self._apply_changes,
            width=120,
            state="disabled",
        )
        self._apply_edit_btn.pack(side="left")

        self._edit_hint = ctk.CTkLabel(
            edit_row, text="", font=("Segoe UI", 9), text_color=("gray50", "gray60")
        )
        self._edit_hint.pack(side="left", padx=(8, 0))

        # Action buttons
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew", padx=8, pady=(2, 10))
        ctk.CTkButton(
            btn_row,
            text="Remove Selected",
            command=self._remove_selected,
            width=130,
            fg_color=("#a03030", "#802020"),
            hover_color=("#c03030", "#a02020"),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_row, text="Repair All Items", command=self._repair_all, width=120
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_row, text="Refresh", command=self._refresh_inventory, width=80
        ).pack(side="left", padx=4)

    # --- Right panel ---------------------------------------------------------- #

    def _build_spawner_panel(self, parent) -> None:
        frame = ctk.CTkFrame(parent, corner_radius=10)
        frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Add Item", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, pady=(10, 6), padx=12, sticky="w"
        )

        frow = ctk.CTkFrame(frame, fg_color="transparent")
        frow.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
        frow.grid_columnconfigure(1, weight=1)
        db, _ = _ensure_db()
        self._spawn_cat_var = tk.StringVar(value="All")
        ctk.CTkComboBox(
            frow,
            variable=self._spawn_cat_var,
            values=["All"] + [_CAT_LABELS.get(k, k) for k in db.keys()],
            state="readonly",
            width=110,
            command=lambda _: self._rebuild_item_list(),
        ).grid(row=0, column=0, padx=(0, 6))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._rebuild_item_list())
        ctk.CTkEntry(
            frow, textvariable=self._search_var, placeholder_text="Search...", width=130
        ).grid(row=0, column=1, sticky="ew")

        tf2 = tk.Frame(frame, bg="#2b2b2b")
        tf2.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        tf2.grid_rowconfigure(0, weight=1)
        tf2.grid_columnconfigure(0, weight=1)
        self._spawn_tree = ttk.Treeview(
            tf2,
            columns=("name",),
            show="headings",
            style="DSR.Treeview",
            selectmode="browse",
        )
        self._spawn_tree.heading("name", text="Item Name")
        self._spawn_tree.column("name", width=220)
        self._spawn_tree.grid(row=0, column=0, sticky="nsew")
        self._spawn_tree.bind("<<TreeviewSelect>>", self._on_spawn_select)
        sb2 = ttk.Scrollbar(tf2, orient="vertical", command=self._spawn_tree.yview)
        sb2.grid(row=0, column=1, sticky="ns")
        self._spawn_tree.configure(yscrollcommand=sb2.set)

        # Spawner controls - spelled out
        cfg = ctk.CTkFrame(frame, fg_color="transparent")
        cfg.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 4))

        ctk.CTkLabel(cfg, text="Quantity:").pack(side="left", padx=(0, 4))
        self._qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(cfg, textvariable=self._qty_var, width=50, justify="center").pack(
            side="left", padx=(0, 10)
        )

        ctk.CTkLabel(cfg, text="Upgrade:").pack(side="left", padx=(0, 4))
        self._upg_var = tk.StringVar(value="0")
        self._upg_entry = ctk.CTkEntry(
            cfg, textvariable=self._upg_var, width=40, justify="center"
        )
        self._upg_entry.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(cfg, text="Infusion:").pack(side="left", padx=(0, 4))
        self._inf_var = tk.StringVar(value="Standard")
        self._inf_combo = ctk.CTkComboBox(
            cfg,
            variable=self._inf_var,
            values=_INFUSION_NAMES,
            state="readonly",
            width=100,
        )
        self._inf_combo.pack(side="left")

        # Add to Inventory - bottom left
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=4, column=0, sticky="ew", padx=8, pady=(2, 10))
        ctk.CTkButton(
            btn_frame, text="Add to Inventory", command=self._add_item, width=180
        ).pack(side="left")

        self._rebuild_item_list()

    # --- Sorting ------------------------------------------------------------- #

    def _on_header_click(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False
        self._sort_in_place()
        self._update_header_arrows()

    def _sort_in_place(self) -> None:
        if not self._sort_col:
            return
        _, _, numeric = _COL_META[self._sort_col]
        col = self._sort_col
        data = [
            (self._inv_tree.set(k, col), k) for k in self._inv_tree.get_children("")
        ]
        data.sort(
            key=lambda x: int(x[0])
            if (numeric and str(x[0]).lstrip("-").isdigit())
            else str(x[0]).lower(),
            reverse=self._sort_reverse,
        )
        for i, (_, k) in enumerate(data):
            self._inv_tree.move(k, "", i)

    def _update_header_arrows(self) -> None:
        for col, (label, _, _) in _COL_META.items():
            arrow = ""
            if col == self._sort_col:
                arrow = " ↓" if self._sort_reverse else " ↑"
            self._inv_tree.heading(col, text=label + arrow)

    # --- Filtering ----------------------------------------------------------- #

    def _apply_filter(self) -> None:
        query = self._inv_search_var.get().lower()
        cat_filter = self._inv_cat_var.get()

        filtered = [
            row
            for row in self._all_items
            if (not query or query in row[1].lower())
            and (cat_filter == "All" or row[2] == cat_filter)
        ]

        if self._sort_col:
            _, tuple_idx, numeric = _COL_META[self._sort_col]
            filtered.sort(
                key=lambda x: x[tuple_idx] if numeric else str(x[tuple_idx]).lower(),
                reverse=self._sort_reverse,
            )

        self._inv_tree.delete(*self._inv_tree.get_children())
        for iid, name, cat_label, qty, slot_idx in filtered:
            self._inv_tree.insert(
                "", "end", iid=iid, values=(name, cat_label, qty, slot_idx)
            )

        total = len(self._all_items)
        shown = len(filtered)
        self._count_label.configure(
            text=f"{shown} / {total} items" if shown < total else f"{total} items"
        )
        self._update_header_arrows()
        self._selected_slot_idx = -1
        self._reset_edit_controls()

    # --- Refresh / load ------------------------------------------------------ #

    def refresh(self) -> None:
        save = self._get_dsr_save()
        if save is None:
            self._slot_combo.configure(values=[])
            return
        options = [
            f"Slot {i + 1} - {c.name}" if c else f"Slot {i + 1} - Empty"
            for i, c in enumerate(save.characters)
        ]
        self._slot_combo.configure(values=options)
        self._slot_var.set(options[0] if options else "")

    def load_slot(self, slot_idx: int) -> None:
        options = self._slot_combo.cget("values")
        if options and slot_idx < len(options):
            self._slot_var.set(options[slot_idx])
        self._current_slot = slot_idx
        self._refresh_inventory()

    def _load_selected(self) -> None:
        idx = self._slot_idx()
        if idx < 0:
            return
        save = self._get_dsr_save()
        if save is None:
            CTkMessageBox.showwarning(
                "No Save", "No DSR save loaded.", parent=self.parent
            )
            return
        if save.characters[idx] is None:
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {idx + 1} is empty.", parent=self.parent
            )
            return
        self._current_slot = idx
        self._refresh_inventory()

    def _refresh_inventory(self) -> None:
        if self._current_slot < 0:
            return
        save = self._get_dsr_save()
        char = save.characters[self._current_slot] if save else None
        if char is None:
            return
        _, lookup = _ensure_db()
        self._all_items.clear()
        for item in char.iter_items():
            name = _resolve_name(item.category, item.base_item_id, item.item_id)
            entry = lookup.get((item.category, item.base_item_id))
            cat_label = _CAT_LABELS.get(entry.get("_cat", ""), "?") if entry else "?"
            self._all_items.append(
                (str(item.slot_index), name, cat_label, item.quantity, item.slot_index)
            )
        self._apply_filter()

    def _rebuild_item_list(self) -> None:
        db, _ = _ensure_db()
        query = self._search_var.get().lower()
        cat_label = self._spawn_cat_var.get()
        cat_key = next((k for k, v in _CAT_LABELS.items() if v == cat_label), None)
        self._spawn_tree.delete(*self._spawn_tree.get_children())
        self._spawn_items.clear()
        for db_cat, cat_items in db.items():
            if cat_key and db_cat != cat_key:
                continue
            for item in cat_items:
                if query and query not in item["Name"].lower():
                    continue
                iid = f"{db_cat}:{item['Id']}"
                self._spawn_items[iid] = item
                self._spawn_tree.insert("", "end", iid=iid, values=(item["Name"],))
        self._selected_db_item = None

    # --- Selection ----------------------------------------------------------- #

    def _on_inv_select(self, _event=None) -> None:
        sel = self._inv_tree.selection()
        if not sel:
            self._selected_slot_idx = -1
            self._reset_edit_controls()
            return
        self._selected_slot_idx = int(sel[0])
        save = self._get_dsr_save()
        char = save.characters[self._current_slot] if save else None
        if char is None:
            return
        item = char.read_item(self._selected_slot_idx)
        _, lookup = _ensure_db()
        entry = lookup.get((item.category, item.base_item_id))
        max_stack = int(entry.get("MaxStackCount") or 1) if entry else 1
        is_weapon = item.category == 0

        # Quantity - enabled for stackable items
        if max_stack > 1:
            self._edit_qty_var.set(str(item.quantity))
            self._edit_qty_entry.configure(state="normal")
            self._edit_hint.configure(text=f"max qty: {max_stack}")
        else:
            self._edit_qty_entry.configure(state="disabled")
            self._edit_hint.configure(text="")

        # Upgrade + Infusion - enabled for weapons
        if is_weapon and entry:
            max_up = entry.get("MaxUpgrade") or 0
            can_inf = bool(entry.get("CanInfuse"))
            self._inv_upg_var.set(str(item.upgrade_level))
            self._inv_upg_entry.configure(state="normal" if max_up else "disabled")
            self._inv_inf_var.set(
                _INFUSION_NAMES[item.infusion]
                if item.infusion < len(_INFUSION_NAMES)
                else "Standard"
            )
            self._inv_inf_combo.configure(state="readonly" if can_inf else "disabled")
        else:
            self._inv_upg_entry.configure(state="disabled")
            self._inv_inf_combo.configure(state="disabled")

        # Apply Changes button enabled whenever any control is active
        any_active = (max_stack > 1) or (
            is_weapon and entry and entry.get("MaxUpgrade")
        )
        self._apply_edit_btn.configure(state="normal" if any_active else "disabled")

    def _reset_edit_controls(self) -> None:
        self._edit_qty_var.set("")
        self._edit_qty_entry.configure(state="disabled")
        self._inv_upg_var.set("")
        self._inv_upg_entry.configure(state="disabled")
        self._inv_inf_var.set("Standard")
        self._inv_inf_combo.configure(state="disabled")
        self._apply_edit_btn.configure(state="disabled")
        self._edit_hint.configure(text="")

    def _on_spawn_select(self, _event=None) -> None:
        sel = self._spawn_tree.selection()
        if not sel:
            self._selected_db_item = None
            return
        item = self._spawn_items.get(sel[0])
        self._selected_db_item = item
        if item is None:
            return
        type_num = int(item["Type"], 16) // 0x10000000
        is_weapon = type_num == 0
        max_up = item.get("MaxUpgrade")
        can_infuse = bool(item.get("CanInfuse")) and is_weapon
        self._upg_entry.configure(
            state="normal" if (is_weapon and max_up) else "disabled"
        )
        self._inf_combo.configure(state="readonly" if can_infuse else "disabled")
        if not can_infuse:
            self._inf_var.set("Standard")
        if not (is_weapon and max_up):
            self._upg_var.set("0")

    # --- Apply changes ------------------------------------------------------- #

    def _apply_changes(self) -> None:
        """Single Apply button covers quantity, upgrade, and infusion editing."""
        if self._selected_slot_idx < 0:
            return
        save, save_path, char = self._get_char()
        if char is None:
            return
        item = char.read_item(self._selected_slot_idx)
        _, lookup = _ensure_db()
        entry = lookup.get((item.category, item.base_item_id))
        changed = False

        # Quantity (only if entry is enabled = stackable)
        if str(self._edit_qty_entry.cget("state")) == "normal":
            try:
                new_qty = int(self._edit_qty_var.get())
            except ValueError:
                CTkMessageBox.showerror(
                    "Invalid", "Enter a valid quantity.", parent=self.parent
                )
                return
            max_stack = int(entry.get("MaxStackCount") or 1) if entry else 1
            if not 1 <= new_qty <= max_stack:
                CTkMessageBox.showerror(
                    "Out of Range",
                    f"Quantity must be 1-{max_stack}.",
                    parent=self.parent,
                )
                return
            item.quantity = new_qty
            changed = True

        # Upgrade + infusion (only if weapon controls are active)
        upg_active = str(self._inv_upg_entry.cget("state")) == "normal"
        inf_active = str(self._inv_inf_combo.cget("state")) == "readonly"
        if upg_active or inf_active:
            try:
                new_upg = (
                    int(self._inv_upg_var.get()) if upg_active else item.upgrade_level
                )
            except ValueError:
                CTkMessageBox.showerror(
                    "Invalid", "Enter a valid upgrade level.", parent=self.parent
                )
                return
            inf_name = (
                self._inv_inf_var.get()
                if inf_active
                else _INFUSION_NAMES[item.infusion]
            )
            new_inf = (
                _INFUSION_NAMES.index(inf_name) if inf_name in _INFUSION_NAMES else 0
            )

            max_up = (entry.get("MaxUpgrade") or 0) if entry else 0
            if upg_active and (new_upg < 0 or new_upg > max_up):
                CTkMessageBox.showerror(
                    "Invalid Upgrade", f"Range is 0-{max_up}.", parent=self.parent
                )
                return
            if inf_active and new_inf > 0 and entry and not entry.get("CanInfuse"):
                CTkMessageBox.showerror(
                    "Cannot Infuse",
                    f"{entry['Name']} cannot be infused.",
                    parent=self.parent,
                )
                return

            item.item_id = item.base_item_id + new_inf * 100 + new_upg
            if entry and entry.get("Durability"):
                base_dur = int(entry["Durability"])
                item.durability = base_dur // 10 if new_inf == 1 else base_dur
            changed = True

        if not changed:
            return

        char.write_item(self._selected_slot_idx, item)
        if item.category == 0:
            char.calibrate_weapon_level()

        try:
            _backup_and_save(
                save, save_path, f"edit_item_slot_{self._current_slot + 1}"
            )
            self._refresh_inventory()
            self._show_toast("Item updated.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    # --- Add / remove / repair ----------------------------------------------- #

    def _remove_selected(self) -> None:
        if self._selected_slot_idx < 0:
            CTkMessageBox.showwarning(
                "No Selection", "Select an item to remove.", parent=self.parent
            )
            return
        save, save_path, char = self._get_char()
        if char is None:
            return
        item = char.read_item(self._selected_slot_idx)
        _, lookup = _ensure_db()
        entry = lookup.get((item.category, item.base_item_id))
        name = entry["Name"] if entry else f"slot {self._selected_slot_idx}"
        if not CTkMessageBox.askyesno(
            "Confirm Remove", f"Remove {name}?", parent=self.parent
        ):
            return
        char.remove_item(self._selected_slot_idx)
        try:
            _backup_and_save(
                save, save_path, f"inventory_remove_slot_{self._current_slot + 1}"
            )
            self._refresh_inventory()
            self._show_toast(f"Removed {name}.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _add_item(self) -> None:
        db_item = self._selected_db_item
        if db_item is None:
            CTkMessageBox.showwarning(
                "No Item", "Select an item from the list.", parent=self.parent
            )
            return
        if self._current_slot < 0:
            CTkMessageBox.showwarning(
                "No Slot", "Load a character slot first.", parent=self.parent
            )
            return
        save, save_path, char = self._get_char()
        if char is None:
            return
        try:
            qty = int(self._qty_var.get())
            upg = int(self._upg_var.get())
            inf_name = self._inf_var.get()
            inf = _INFUSION_NAMES.index(inf_name) if inf_name in _INFUSION_NAMES else 0
        except ValueError as exc:
            CTkMessageBox.showerror("Invalid Value", str(exc), parent=self.parent)
            return
        err = _validate_add(db_item, qty, upg, inf)
        if err:
            CTkMessageBox.showerror("Invalid Item", err, parent=self.parent)
            return
        type_num = int(db_item["Type"], 16) // 0x10000000
        max_stack = int(db_item.get("MaxStackCount") or 1)
        base_id = int(db_item["Id"], 16)
        if max_stack == 1 and type_num != 0:
            for inv_item in char.iter_items():
                if inv_item.item_id == base_id and inv_item.category == type_num:
                    if not CTkMessageBox.askyesno(
                        "Already Owned",
                        f"Already have {db_item['Name']}. Add duplicate?",
                        parent=self.parent,
                    ):
                        return
                    break
        slot = char.add_item(db_item, quantity=qty, upgrade=upg, infusion=inf)
        if slot < 0:
            CTkMessageBox.showerror(
                "Inventory Full", "No empty slots available.", parent=self.parent
            )
            return
        try:
            _backup_and_save(
                save, save_path, f"inventory_add_slot_{self._current_slot + 1}"
            )
            self._refresh_inventory()
            self._show_toast(f"Added {db_item['Name']}.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _repair_all(self) -> None:
        if self._current_slot < 0:
            CTkMessageBox.showwarning(
                "No Slot", "Load a character slot first.", parent=self.parent
            )
            return
        save, save_path, char = self._get_char()
        if char is None:
            return
        if not CTkMessageBox.askyesno(
            "Repair All",
            "Restore durability on all items?\n\nA backup will be created.",
            parent=self.parent,
        ):
            return
        _, lookup = _ensure_db()
        repaired = 0
        for item in char.iter_items():
            if item.durability == 0:
                continue
            entry = lookup.get((item.category, item.base_item_id))
            if entry and entry.get("Durability"):
                max_dur = int(entry["Durability"])
                if item.infusion == 1:
                    max_dur //= 10
                if item.durability < max_dur:
                    item.durability = max_dur
                    char.write_item(item.slot_index, item)
                    repaired += 1
        if repaired == 0:
            self._show_toast("All items already at full durability.")
            return
        try:
            _backup_and_save(
                save, save_path, f"repair_all_slot_{self._current_slot + 1}"
            )
            self._refresh_inventory()
            self._show_toast(f"Repaired {repaired} items.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    # --- Helpers ------------------------------------------------------------- #

    def _get_char(self):
        save = self._get_dsr_save()
        save_path = self._get_save_path()
        if save is None or save_path is None:
            return None, None, None
        char = (
            save.characters[self._current_slot]
            if 0 <= self._current_slot < len(save.characters)
            else None
        )
        return save, save_path, char

    def _slot_idx(self) -> int:
        val = self._slot_var.get()
        if not val:
            return -1
        try:
            return int(val.split(" - ")[0].replace("Slot", "").strip()) - 1
        except (ValueError, IndexError):
            return -1
