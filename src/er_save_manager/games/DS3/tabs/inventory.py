"""
DS3 Inventory Editor tab.

Left panel: current inventory with search, category filter, sortable columns.
  Edit row: Quantity | Upgrade (weapons only) | Apply / Remove buttons.

Right panel: item spawner with category filter, search, quantity + upgrade inputs.

Weapons and armor use INSERT+TRIM (see slot.py). Goods and rings write directly
into an empty inventory slot. All mutations backup then save immediately.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox

_DATA_DIR = Path(__file__).parent.parent / "data"
_DB: dict | None = None
_LOOKUP: dict[tuple[int, int], dict] | None = None

_CAT_LABELS: dict[str, str] = {
    "weapon_items": "Weapons",
    "ammo_items": "Ammo",
    "armor_items": "Armor",
    "ring_items": "Rings",
    "goods_items": "Goods",
}

# gaitem_handle type nibble values
_TYPE_WEAPON = 0x8
_TYPE_ARMOR = 0x9
_TYPE_RING = 0xA
_TYPE_GOOD = 0xB


def _ensure_db() -> tuple[dict, dict]:
    global _DB, _LOOKUP
    if _DB is None:
        _DB = json.loads((_DATA_DIR / "items.json").read_text(encoding="utf-8"))
        _LOOKUP = {}
        for cat_key, cat_items in _DB.items():
            for item in cat_items:
                item["_cat"] = cat_key
                type_nibble = int(item["Type"], 16) >> 28
                _LOOKUP[(type_nibble, int(item["Id"], 16))] = item
    return _DB, _LOOKUP  # type: ignore[return-value]


def _resolve_name(type_nibble: int, item_id: int) -> str:
    _, lookup = _ensure_db()
    entry = lookup.get((type_nibble, item_id))
    if entry is None:
        return f"Unknown (type={type_nibble:#x} id={item_id:#010x})"
    return entry["Name"]


def _backup_and_save(ds3_save, save_path: Path, op: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=op, save=None)
    ds3_save.save_to_file(save_path)


def _apply_treeview_style() -> None:
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "DS3.Treeview",
        background="#2b2b2b",
        foreground="white",
        fieldbackground="#2b2b2b",
        rowheight=22,
        borderwidth=0,
    )
    style.configure("DS3.Treeview.Heading", background="#3b3b3b", foreground="white")
    style.map("DS3.Treeview", background=[("selected", "#5a4a7a")])


class DS3InventoryTab:
    def __init__(self, parent, get_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_save = get_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = -1
        self._selected_inv_offset = -1
        self._selected_db_item: dict | None = None
        self._spawn_row_map: dict[str, dict] = {}
        self._all_items: list[
            tuple
        ] = []  # (offset, name, cat, qty, type_nibble, item_id)
        self._sort_col: str | None = None
        self._sort_asc = True

    def setup_ui(self) -> None:
        _apply_treeview_style()

        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        # Slot selector header
        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(
            header, text="Inventory Editor", font=("Segoe UI", 16, "bold")
        ).pack(side="left")
        ctk.CTkButton(header, text="Load", command=self._load_selected, width=70).pack(
            side="right", padx=(6, 0)
        )
        self._slot_var = tk.StringVar()
        self._slot_combo = ctk.CTkComboBox(
            header,
            variable=self._slot_var,
            values=[],
            state="readonly",
            width=240,
        )
        self._slot_combo.pack(side="right")
        ctk.CTkLabel(header, text="Slot:").pack(side="right", padx=(0, 6))

        # Two-column layout
        body = ctk.CTkFrame(outer, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self._build_inventory_panel(body)
        self._build_spawner_panel(body)

    # --- Inventory panel (left) ---------------------------------------------- #

    def _build_inventory_panel(self, parent) -> None:
        left = ctk.CTkFrame(parent, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Filter row
        frow = ctk.CTkFrame(left, fg_color="transparent")
        frow.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ctk.CTkLabel(frow, text="Filter:").pack(side="left", padx=(0, 4))
        self._inv_search_var = tk.StringVar()
        self._inv_search_var.trace_add(
            "write", lambda *_: self._refresh_inventory_tree()
        )
        ctk.CTkEntry(frow, textvariable=self._inv_search_var, width=160).pack(
            side="left", padx=(0, 6)
        )
        self._inv_cat_var = tk.StringVar(value="All")
        ctk.CTkComboBox(
            frow,
            variable=self._inv_cat_var,
            values=["All"] + list(_CAT_LABELS.values()),
            state="readonly",
            width=110,
            command=lambda _: self._refresh_inventory_tree(),
        ).pack(side="left")

        # Inventory treeview
        cols = ("name", "type", "qty")
        self._inv_tree = ttk.Treeview(
            left, columns=cols, show="headings", style="DS3.Treeview", height=16
        )
        for col, heading, width in [
            ("name", "Item", 220),
            ("type", "Type", 80),
            ("qty", "Qty", 55),
        ]:
            self._inv_tree.heading(
                col,
                text=heading,
                command=lambda c=col: self._sort_by(c),
            )
            self._inv_tree.column(
                col, width=width, anchor="w" if col == "name" else "center"
            )
        self._inv_tree.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))

        vsb = ttk.Scrollbar(left, orient="vertical", command=self._inv_tree.yview)
        vsb.grid(row=1, column=1, sticky="ns", pady=(0, 4))
        self._inv_tree.configure(yscrollcommand=vsb.set)
        self._inv_tree.bind("<<TreeviewSelect>>", self._on_inv_select)

        # Edit controls
        edit_row = ctk.CTkFrame(left, fg_color="transparent")
        edit_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))

        ctk.CTkLabel(edit_row, text="Qty:").pack(side="left", padx=(0, 2))
        self._edit_qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(edit_row, textvariable=self._edit_qty_var, width=55).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkLabel(edit_row, text="Upgrade:").pack(side="left", padx=(0, 2))
        self._edit_upg_var = tk.StringVar(value="0")
        self._edit_upg_entry = ctk.CTkEntry(
            edit_row, textvariable=self._edit_upg_var, width=45
        )
        self._edit_upg_entry.pack(side="left", padx=(0, 8))
        ctk.CTkButton(edit_row, text="Apply", command=self._apply_edit, width=70).pack(
            side="left", padx=(0, 4)
        )
        ctk.CTkButton(
            edit_row,
            text="Remove",
            command=self._remove_item,
            width=70,
            fg_color=("gray60", "gray35"),
            hover_color=("gray50", "gray25"),
        ).pack(side="left")

    # --- Spawner panel (right) ----------------------------------------------- #

    def _build_spawner_panel(self, parent) -> None:
        right = ctk.CTkFrame(parent, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="Spawn Item", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 4)
        )

        # Category + search
        frow = ctk.CTkFrame(right, fg_color="transparent")
        frow.grid(row=0, column=0, sticky="ew", padx=8, pady=(28, 2))
        self._spawn_cat_var = tk.StringVar(value="All")
        ctk.CTkComboBox(
            frow,
            variable=self._spawn_cat_var,
            values=["All"] + list(_CAT_LABELS.values()),
            state="readonly",
            width=110,
            command=lambda _: self._refresh_spawn_tree(),
        ).pack(side="left", padx=(0, 6))
        self._spawn_search_var = tk.StringVar()
        self._spawn_search_var.trace_add("write", lambda *_: self._refresh_spawn_tree())
        ctk.CTkEntry(
            frow,
            textvariable=self._spawn_search_var,
            width=140,
            placeholder_text="Search...",
        ).pack(side="left")

        # Spawn treeview
        self._spawn_tree = ttk.Treeview(
            right, columns=("name",), show="headings", style="DS3.Treeview", height=18
        )
        self._spawn_tree.heading("name", text="Item")
        self._spawn_tree.column("name", width=200, anchor="w")
        self._spawn_tree.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))
        ssb = ttk.Scrollbar(right, orient="vertical", command=self._spawn_tree.yview)
        ssb.grid(row=1, column=1, sticky="ns", pady=(0, 4))
        self._spawn_tree.configure(yscrollcommand=ssb.set)
        self._spawn_tree.bind("<<TreeviewSelect>>", self._on_spawn_select)
        # Maps auto-generated treeview IID -> item dict
        self._spawn_row_map: dict[str, dict] = {}

        # Spawn controls
        ctrl = ctk.CTkFrame(right, fg_color="transparent")
        ctrl.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        ctk.CTkLabel(ctrl, text="Qty:").grid(row=0, column=0, padx=(0, 2), pady=4)
        self._spawn_qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(ctrl, textvariable=self._spawn_qty_var, width=50).grid(
            row=0, column=1, padx=(0, 8), pady=4
        )
        ctk.CTkLabel(ctrl, text="Upgrade:").grid(row=0, column=2, padx=(0, 2), pady=4)
        self._spawn_upg_var = tk.StringVar(value="0")
        self._spawn_upg_entry = ctk.CTkEntry(
            ctrl, textvariable=self._spawn_upg_var, width=40
        )
        self._spawn_upg_entry.grid(row=0, column=3, padx=(0, 8), pady=4)
        ctk.CTkButton(ctrl, text="Spawn", command=self._spawn_item, width=80).grid(
            row=0, column=4, pady=4
        )

        self._spawn_info = ctk.CTkLabel(
            ctrl, text="", font=("Segoe UI", 9), text_color=("gray40", "gray60")
        )
        self._spawn_info.grid(row=1, column=0, columnspan=5, sticky="w", pady=(0, 4))

    # --- Refresh ------------------------------------------------------------- #

    def refresh(self) -> None:
        save = self._get_save()
        if save is None:
            self._slot_combo.configure(values=[])
            return
        options = [
            f"Slot {i + 1} - {c.name}" if c else f"Slot {i + 1} - Empty"
            for i, c in enumerate(save.characters)
        ]
        self._slot_combo.configure(values=options)
        self._slot_var.set(options[0] if options else "")
        self._refresh_spawn_tree()

    def load_slot(self, slot_idx: int) -> None:
        options = self._slot_combo.cget("values")
        if options and slot_idx < len(options):
            self._slot_var.set(options[slot_idx])
        self._current_slot = slot_idx
        self._reload_inventory()

    def _load_selected(self) -> None:
        idx = self._slot_idx()
        if idx < 0:
            return
        save = self._get_save()
        if save is None or save.characters[idx] is None:
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {idx + 1} is empty.", parent=self.parent
            )
            return
        self._current_slot = idx
        self._reload_inventory()

    # --- Inventory tree population ------------------------------------------- #

    def _reload_inventory(self) -> None:
        save = self._get_save()
        if save is None or self._current_slot < 0:
            return
        char = save.characters[self._current_slot]
        if char is None:
            return

        _, lookup = _ensure_db()
        self._all_items = []
        for entry in char.iter_inventory():
            if entry.is_empty:
                continue
            type_nibble = entry.type_bits >> 28
            name = _resolve_name(type_nibble, entry.item_id)
            cat = _CAT_LABELS.get(_nibble_to_cat(type_nibble), "?")
            self._all_items.append(
                (entry.offset, name, cat, entry.quantity, type_nibble, entry.item_id)
            )

        self._refresh_inventory_tree()

    def _refresh_inventory_tree(self) -> None:
        self._inv_tree.delete(*self._inv_tree.get_children())
        query = self._inv_search_var.get().strip().lower()
        cat_filter_label = self._inv_cat_var.get()
        if cat_filter_label != "All":
            next((k for k, v in _CAT_LABELS.items() if v == cat_filter_label), None)
            cat_filter_label_resolved = cat_filter_label
        else:
            cat_filter_label_resolved = None

        items = self._all_items
        if query:
            items = [r for r in items if query in r[1].lower()]
        if cat_filter_label_resolved:
            items = [r for r in items if r[2] == cat_filter_label_resolved]

        if self._sort_col == "name":
            items = sorted(items, key=lambda r: r[1], reverse=not self._sort_asc)
        elif self._sort_col == "type":
            items = sorted(items, key=lambda r: r[2], reverse=not self._sort_asc)
        elif self._sort_col == "qty":
            items = sorted(items, key=lambda r: r[3], reverse=not self._sort_asc)

        for offset, name, cat, qty, *_ in items:
            iid = str(offset)
            self._inv_tree.insert("", "end", iid=iid, values=(name, cat, qty))

    def _refresh_spawn_tree(self) -> None:
        self._spawn_tree.delete(*self._spawn_tree.get_children())
        self._spawn_row_map.clear()
        db, _ = _ensure_db()
        query = self._spawn_search_var.get().strip().lower()
        cat_label = self._spawn_cat_var.get()
        cat_key = None
        if cat_label != "All":
            cat_key = next((k for k, v in _CAT_LABELS.items() if v == cat_label), None)

        for db_cat, cat_items in db.items():
            if cat_key and db_cat != cat_key:
                continue
            for item in cat_items:
                if query and query not in item["Name"].lower():
                    continue
                row_iid = self._spawn_tree.insert("", "end", values=(item["Name"],))
                self._spawn_row_map[row_iid] = item

    # --- Selection handlers -------------------------------------------------- #

    def _on_inv_select(self, _event) -> None:
        sel = self._inv_tree.selection()
        if not sel:
            self._selected_inv_offset = -1
            return
        try:
            offset = int(sel[0])
        except ValueError:
            self._selected_inv_offset = -1
            return
        self._selected_inv_offset = offset
        # Pre-fill qty from current entry
        for row in self._all_items:
            if row[0] == offset:
                self._edit_qty_var.set(str(row[3]))
                break

    def _on_spawn_select(self, _event) -> None:
        sel = self._spawn_tree.selection()
        if not sel:
            self._selected_db_item = None
            self._spawn_info.configure(text="")
            return
        entry = self._spawn_row_map.get(sel[0])
        self._selected_db_item = entry
        if entry:
            max_up = entry.get("MaxUpgrade") or 0
            max_stk = entry.get("MaxStackCount") or 1
            info = f"Max stack: {max_stk}"
            if max_up:
                info += f"  Max upgrade: +{max_up}"
            self._spawn_info.configure(text=info)
            if max_up == 0:
                self._spawn_upg_var.set("0")
                self._spawn_upg_entry.configure(state="disabled")
            else:
                self._spawn_upg_entry.configure(state="normal")

    # --- Sort ---------------------------------------------------------------- #

    def _sort_by(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True
        arrow = " ^" if self._sort_asc else " v"
        for c, heading, _ in [
            ("name", "Item", 220),
            ("type", "Type", 80),
            ("qty", "Qty", 55),
        ]:
            self._inv_tree.heading(c, text=heading + (arrow if c == col else ""))
        self._refresh_inventory_tree()

    # --- Inventory operations ------------------------------------------------ #

    def _apply_edit(self) -> None:
        if self._selected_inv_offset < 0:
            CTkMessageBox.showwarning(
                "No Selection",
                "Select an item from the inventory first.",
                parent=self.parent,
            )
            return
        save = self._get_save()
        save_path = self._get_save_path()
        if save is None or save_path is None or self._current_slot < 0:
            return
        char = save.characters[self._current_slot]
        if char is None:
            return

        try:
            qty = int(self._edit_qty_var.get())
            upg = int(self._edit_upg_var.get())
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Value", "Enter valid integers.", parent=self.parent
            )
            return

        # Find entry in inventory
        for entry in char.iter_inventory():
            if entry.offset == self._selected_inv_offset:
                # Overwrite quantity
                from er_save_manager.games.DS3.slot import _write_u32

                _write_u32(char._data, entry.offset + 8, max(1, qty))
                # Upgrade: only for weapons in gaitem table
                type_nibble = entry.type_bits >> 28
                if type_nibble in (_TYPE_WEAPON, _TYPE_ARMOR) and upg >= 0:
                    # Find gaitem entry with matching handle
                    for ge in char.iter_gaitem():
                        if ge.handle == entry.handle and ge.size == 60:
                            _write_u32(char._data, ge.offset + 12, upg)
                            break
                break

        try:
            _backup_and_save(
                save, save_path, f"ds3_edit_item_slot_{self._current_slot + 1}"
            )
            self._reload_inventory()
            self._show_toast("Item updated. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _remove_item(self) -> None:
        if self._selected_inv_offset < 0:
            CTkMessageBox.showwarning(
                "No Selection",
                "Select an item from the inventory first.",
                parent=self.parent,
            )
            return
        save = self._get_save()
        save_path = self._get_save_path()
        if save is None or save_path is None or self._current_slot < 0:
            return
        char = save.characters[self._current_slot]
        if char is None:
            return
        if not CTkMessageBox.askyesno(
            "Confirm Remove",
            "Remove the selected item from inventory?",
            parent=self.parent,
        ):
            return
        char.remove_item(self._selected_inv_offset)
        try:
            _backup_and_save(
                save, save_path, f"ds3_remove_item_slot_{self._current_slot + 1}"
            )
            self._selected_inv_offset = -1
            self._reload_inventory()
            self._show_toast("Item removed. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _spawn_item(self) -> None:
        entry = self._selected_db_item
        if entry is None:
            CTkMessageBox.showwarning(
                "No Item",
                "Select an item from the spawner list first.",
                parent=self.parent,
            )
            return
        save = self._get_save()
        save_path = self._get_save_path()
        if save is None or save_path is None or self._current_slot < 0:
            CTkMessageBox.showwarning(
                "No Character", "Load a character first.", parent=self.parent
            )
            return
        char = save.characters[self._current_slot]
        if char is None:
            return

        try:
            qty = int(self._spawn_qty_var.get())
            upg = int(self._spawn_upg_var.get())
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Value", "Enter valid integers.", parent=self.parent
            )
            return

        max_stk = int(entry.get("MaxStackCount") or 1)
        max_up = int(entry.get("MaxUpgrade") or 0)
        qty = max(1, min(qty, max_stk))
        upg = max(0, min(upg, max_up))

        from er_save_manager.games.DS3.slot import (
            ITEM_TYPE_ARMOR,
            ITEM_TYPE_GOOD,
            ITEM_TYPE_RING,
            ITEM_TYPE_WEAPON,
        )

        item_id = int(entry["Id"], 16)
        type_nibble = int(entry["Type"], 16) >> 28

        type_map = {
            0x8: ITEM_TYPE_WEAPON,
            0x9: ITEM_TYPE_ARMOR,
            0xA: ITEM_TYPE_RING,
            0xB: ITEM_TYPE_GOOD,
        }
        item_type = type_map.get(type_nibble)
        if item_type is None:
            CTkMessageBox.showerror(
                "Unknown Type",
                f"Item type {type_nibble:#x} not handled.",
                parent=self.parent,
            )
            return

        if type_nibble in (_TYPE_WEAPON, _TYPE_ARMOR):
            ok = char.add_weapon_armor(item_id, item_type, upg)
        else:
            ok = char.add_goods_rings(item_id, item_type, qty)

        if not ok:
            CTkMessageBox.showerror(
                "Full",
                "Inventory and storage box are both full, or gaitem table has no empty slots.",
                parent=self.parent,
            )
            return

        try:
            _backup_and_save(
                save, save_path, f"ds3_spawn_item_slot_{self._current_slot + 1}"
            )
            self._reload_inventory()
            self._show_toast(f"Spawned: {entry['Name']}. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    # --- Helpers ------------------------------------------------------------- #

    def _slot_idx(self) -> int:
        val = self._slot_var.get()
        if not val:
            return -1
        try:
            return int(val.split(" - ")[0].replace("Slot", "").strip()) - 1
        except (ValueError, IndexError):
            return -1


def _nibble_to_cat(nibble: int) -> str:
    return {
        0x8: "weapon_items",
        0x9: "armor_items",
        0xA: "ring_items",
        0xB: "goods_items",
    }.get(nibble, "")
