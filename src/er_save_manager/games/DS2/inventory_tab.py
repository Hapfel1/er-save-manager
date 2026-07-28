"""
DS2 inventory editor panel.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

import customtkinter as ctk

from er_save_manager.games.DS2.item_database import (
    CATEGORIES,
    _hex_id_to_int,
    build_item_db,
)
from er_save_manager.games.DS2.save import DS2Save

STACKABLE_CATEGORIES = ("goods", "bolts", "spells", "upgrade")

# Internal category key -> display label. Kept separate so backend calls
# (item_database lookups, Character.add_item/delete_item) always use the
# lowercase key, while the UI only ever shows the capitalized label.
CATEGORY_LABELS = {
    "goods": "Goods",
    "weapons": "Weapons",
    "armors": "Armor",
    "rings": "Rings",
    "keys": "Key Items",
    "bolts": "Bolts",
    "spells": "Spells",
    "upgrade": "Upgrade Materials",
}
_DISPLAY_CATEGORIES = list(CATEGORY_LABELS.keys())


class DS2InventoryPanel:
    """
    Args:
        parent: parent widget the panel is built into.
        get_save: callable returning the current DS2Save, or None if unloaded.
        get_slot_index: callable returning the currently selected slot index.
        get_save_path: callable returning the current save file path.
        show_toast: callable(message, duration) for transient status messages.
    """

    def __init__(
        self,
        parent,
        get_save,
        get_slot_index: Callable[[], int],
        get_save_path,
        show_toast,
    ) -> None:
        self.parent = parent
        self.get_save = get_save
        self.get_slot_index = get_slot_index
        self.get_save_path = get_save_path
        self.show_toast = show_toast
        self._item_db = build_item_db()
        self._current_items: list[tuple] = []  # (item, name, category)
        self._search_results: list[str] = []
        self._visible_items: list[tuple] = []
        self._sort_column: str = "name"
        self._sort_reverse: bool = False

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        self.frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True)

        pane = tk.PanedWindow(
            self.frame, orient=tk.HORIZONTAL, sashwidth=6, sashrelief=tk.FLAT, bg="#2b2b2b"
        )
        pane.pack(fill="both", expand=True, padx=4, pady=4)

        left = ctk.CTkFrame(pane, fg_color=("gray88", "gray18"), corner_radius=8)
        right = ctk.CTkFrame(pane, fg_color=("gray88", "gray18"), corner_radius=8)
        pane.add(left, minsize=320, width=380)
        pane.add(right, minsize=360)

        self._build_browser_panel(left)
        self._build_inventory_panel(right)

        self.refresh()

    def _build_browser_panel(self, parent) -> None:
        ctk.CTkLabel(parent, text="Add Item", font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=10, pady=(10, 4)
        )

        cat_row = ctk.CTkFrame(parent, fg_color="transparent")
        cat_row.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(cat_row, text="Category:", width=70).pack(side="left")
        self.add_category_var = tk.StringVar(value=CATEGORY_LABELS[_DISPLAY_CATEGORIES[0]])
        ctk.CTkComboBox(
            cat_row,
            variable=self.add_category_var,
            values=list(CATEGORY_LABELS.values()),
            state="readonly",
            width=160,
            command=lambda _v: self._search_items(),
        ).pack(side="left", padx=(0, 6))

        search_row = ctk.CTkFrame(parent, fg_color="transparent")
        search_row.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(search_row, text="Search:", width=70).pack(side="left")
        self.add_search_var = tk.StringVar()
        self.add_search_var.trace_add("write", lambda *_: self._search_items())
        ctk.CTkEntry(search_row, textvariable=self.add_search_var, width=200).pack(
            side="left", padx=(0, 6)
        )

        self._results_tree = ttk.Treeview(
            parent, columns=("name",), show="headings", height=14
        )
        self._results_tree.heading("name", text="Item")
        self._results_tree.column("name", width=260)
        self._results_tree.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        qty_row = ctk.CTkFrame(parent, fg_color="transparent")
        qty_row.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(qty_row, text="Quantity:", width=70).pack(side="left")
        self.add_qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(qty_row, textvariable=self.add_qty_var, width=70).pack(side="left")

        ctk.CTkButton(parent, text="Add Item", command=self._on_add, height=32).pack(
            fill="x", padx=10, pady=(0, 10)
        )

        self._search_items()

    def _build_inventory_panel(self, parent) -> None:
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(header, text="Current Inventory", font=("Segoe UI", 13, "bold")).pack(
            side="left"
        )

        filter_row = ctk.CTkFrame(parent, fg_color="transparent")
        filter_row.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(filter_row, text="Category:", width=70).pack(side="left")
        self.filter_category_var = tk.StringVar(value="All")
        ctk.CTkComboBox(
            filter_row,
            variable=self.filter_category_var,
            values=["All"] + list(CATEGORY_LABELS.values()),
            state="readonly",
            width=160,
            command=lambda _v: self._apply_filter(),
        ).pack(side="left", padx=(0, 6))

        search_row = ctk.CTkFrame(parent, fg_color="transparent")
        search_row.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(search_row, text="Filter:", width=70).pack(side="left")
        self.filter_search_var = tk.StringVar()
        self.filter_search_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(search_row, textvariable=self.filter_search_var, width=200).pack(
            side="left", padx=(0, 6)
        )

        columns = ("name", "category", "quantity")
        self._inventory_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=14
        )
        self._column_labels = {"name": "Name", "category": "Category", "quantity": "Qty"}
        for col, label, width in (
            ("name", "Name", 240),
            ("category", "Category", 130),
            ("quantity", "Qty", 60),
        ):
            self._inventory_tree.heading(
                col, text=label, command=lambda c=col: self._sort_by(c)
            )
            self._inventory_tree.column(col, width=width)
        self._inventory_tree.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(actions, text="Remove Selected", command=self._on_remove, width=130).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkLabel(actions, text="New qty:").pack(side="left", padx=(10, 4))
        self.set_qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(actions, textvariable=self.set_qty_var, width=60).pack(side="left")
        ctk.CTkButton(actions, text="Set Quantity", command=self._on_set_quantity, width=110).pack(
            side="left", padx=6
        )

    # ------------------------------------------------------------------
    # Left panel: item browser
    # ------------------------------------------------------------------

    def _selected_add_category(self) -> str:
        label = self.add_category_var.get()
        for key, value in CATEGORY_LABELS.items():
            if value == label:
                return key
        return _DISPLAY_CATEGORIES[0]

    def _search_items(self) -> None:
        category = self._selected_add_category()
        query = self.add_search_var.get().strip().lower()
        names = sorted(CATEGORIES.get(category, {}).keys())
        if query:
            names = [n for n in names if query in n.lower()]

        self._results_tree.delete(*self._results_tree.get_children())
        self._search_results = names
        for name in names:
            self._results_tree.insert("", "end", values=(name,))

    def _on_add(self) -> None:
        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return

        selection = self._results_tree.selection()
        if not selection:
            self.show_toast("Select an item to add", duration=2000)
            return

        item_name = self._results_tree.item(selection[0], "values")[0]
        category = self._selected_add_category()
        hex_id = CATEGORIES.get(category, {}).get(item_name)
        if hex_id is None:
            self.show_toast("Item not found in database", duration=2000)
            return

        try:
            quantity = int(self.add_qty_var.get())
        except ValueError:
            self.show_toast("Quantity must be a number", duration=2000)
            return
        if quantity < 1:
            self.show_toast("Quantity must be at least 1", duration=2000)
            return

        item_id = _hex_id_to_int(hex_id)
        character = save.characters[self.get_slot_index()]
        added = character.add_item(item_id, category, quantity=quantity)
        if not added:
            self.show_toast("No empty inventory slot available", duration=2500)
            return

        self._write_and_refresh(save, operation="add_item")
        self.show_toast(f"Added {item_name}", duration=2000)

    # ------------------------------------------------------------------
    # Right panel: current inventory
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        save: DS2Save | None = self.get_save()
        self._current_items = []
        if save is not None:
            character = save.characters[self.get_slot_index()]
            for item in character.inventory() + character.key_items():
                if item.item_id == 0:
                    continue
                info = self._item_db.get(item.item_id)
                name, category = info if info else (f"Unknown ({item.item_id})", None)
                self._current_items.append((item, name, category))
        self._apply_filter()

    def _sort_by(self, column: str) -> None:
        if self._sort_column == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column
            self._sort_reverse = False

        for col, label in self._column_labels.items():
            if col == self._sort_column:
                arrow = " \u25bc" if self._sort_reverse else " \u25b2"
                self._inventory_tree.heading(col, text=label + arrow)
            else:
                self._inventory_tree.heading(col, text=label)

        self._apply_filter()

    def _apply_filter(self) -> None:
        category_label = self.filter_category_var.get()
        query = self.filter_search_var.get().strip().lower()

        rows = []
        for item, name, item_category in self._current_items:
            display_category = CATEGORY_LABELS.get(item_category, "Unknown")
            if category_label != "All" and display_category != category_label:
                continue
            if query and query not in name.lower():
                continue
            qty = item.quantity if item_category in STACKABLE_CATEGORIES else -1
            rows.append((item, name, item_category, display_category, qty))

        sort_key = {
            "name": lambda r: r[1].lower(),
            "category": lambda r: r[3].lower(),
            "quantity": lambda r: r[4],
        }.get(self._sort_column, lambda r: r[1].lower())
        rows.sort(key=sort_key, reverse=self._sort_reverse)

        self._inventory_tree.delete(*self._inventory_tree.get_children())
        self._visible_items = []
        for item, name, item_category, display_category, qty in rows:
            self._visible_items.append((item, name, item_category))
            qty_str = str(qty) if qty >= 0 else ""
            self._inventory_tree.insert(
                "", "end", values=(name, display_category, qty_str)
            )

    def _on_remove(self) -> None:
        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return

        selection = self._inventory_tree.selection()
        if not selection:
            self.show_toast("No item selected", duration=2000)
            return

        index = self._inventory_tree.index(selection[0])
        item, name, category = self._visible_items[index]
        character = save.characters[self.get_slot_index()]
        deleted = character.delete_item(item.item_id, category)
        if not deleted:
            self.show_toast("Item not found in inventory", duration=2000)
            return

        self._write_and_refresh(save, operation="remove_item")
        self.show_toast(f"Removed {name}", duration=2000)

    def _on_set_quantity(self) -> None:
        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return

        selection = self._inventory_tree.selection()
        if not selection:
            self.show_toast("No item selected", duration=2000)
            return

        index = self._inventory_tree.index(selection[0])
        item, name, category = self._visible_items[index]
        if category not in STACKABLE_CATEGORIES:
            self.show_toast(
                "Quantity only applies to goods, bolts, spells, and upgrade materials",
                duration=3000,
            )
            return

        try:
            quantity = int(self.set_qty_var.get())
        except ValueError:
            self.show_toast("Quantity must be a number", duration=2000)
            return
        if not (1 <= quantity <= 99):
            self.show_toast("Quantity must be between 1 and 99", duration=2500)
            return

        character = save.characters[self.get_slot_index()]
        character.add_item(item.item_id, category, quantity=quantity, stack=True)
        self._write_and_refresh(save, operation="set_item_quantity")
        self.show_toast(f"Set {name} to x{quantity}", duration=2000)

    def _write_and_refresh(self, save: DS2Save, operation: str = "inventory_edit") -> None:
        save_path = self.get_save_path()
        if save_path:
            self._backup(save_path, f"before_{operation}", operation)
            try:
                save.save_to_file(save_path)
            except Exception as e:
                self.show_toast(f"Failed to write save: {e}", duration=3000)
        self.refresh()

    def _backup(self, save_path, description: str, operation: str) -> None:
        if not save_path:
            return
        try:
            from pathlib import Path

            from er_save_manager.backup.manager import BackupManager

            BackupManager(Path(save_path)).create_backup(
                description=description, operation=operation
            )
        except Exception:
            pass
