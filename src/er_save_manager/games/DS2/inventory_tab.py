"""DS2 inventory editor tab: browse, add, and delete items."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from er_save_manager.games.DS2.item_database import (
    CATEGORIES,
    _hex_id_to_int,
    build_item_db,
)
from er_save_manager.games.DS2.save import DS2Save


class DS2InventoryTab:
    """
    Args:
        parent: parent widget the tab content is built into.
        get_save: callable returning the current DS2Save, or None if unloaded.
        get_save_path: callable returning the current save file path.
        show_toast: callable(message, duration) for transient status messages.
    """

    def __init__(self, parent, get_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self.get_save = get_save
        self.get_save_path = get_save_path
        self.show_toast = show_toast
        self._item_db = build_item_db()
        self._slot_index = 0

    def setup_ui(self) -> None:
        top = ctk.CTkFrame(self.parent, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Slot:").pack(side="left")
        self.slot_var = tk.StringVar(value="0")
        ctk.CTkOptionMenu(
            top,
            variable=self.slot_var,
            values=[str(i) for i in range(10)],
            command=lambda _v: self.refresh(),
            width=60,
        ).pack(side="left", padx=(5, 15))
        ctk.CTkButton(top, text="Refresh", command=self.refresh).pack(side="left")

        add_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        add_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(add_frame, text="Category:").grid(row=0, column=0, padx=5, pady=3)
        self.category_var = tk.StringVar(value="goods")
        ctk.CTkOptionMenu(
            add_frame,
            variable=self.category_var,
            values=list(CATEGORIES.keys()),
            command=self._on_category_changed,
        ).grid(row=0, column=1, padx=5, pady=3)

        ctk.CTkLabel(add_frame, text="Item:").grid(row=0, column=2, padx=5, pady=3)
        self.item_var = tk.StringVar()
        self.item_menu = ctk.CTkOptionMenu(
            add_frame, variable=self.item_var, values=[""]
        )
        self.item_menu.grid(row=0, column=3, padx=5, pady=3)

        ctk.CTkLabel(add_frame, text="Qty:").grid(row=0, column=4, padx=5, pady=3)
        self.qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(add_frame, textvariable=self.qty_var, width=60).grid(
            row=0, column=5, padx=5, pady=3
        )

        ctk.CTkButton(add_frame, text="Add item", command=self._on_add).grid(
            row=0, column=6, padx=10, pady=3
        )
        ctk.CTkButton(add_frame, text="Delete selected", command=self._on_delete).grid(
            row=0, column=7, padx=5, pady=3
        )

        columns = ("name", "category", "item_id", "quantity")
        self.tree = ttk.Treeview(
            self.parent, columns=columns, show="headings", height=14
        )
        for col, width in (
            ("name", 260),
            ("category", 100),
            ("item_id", 100),
            ("quantity", 100),
        ):
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self._on_category_changed(self.category_var.get())
        self.refresh()

    def _on_category_changed(self, category: str) -> None:
        names = sorted(CATEGORIES.get(category, {}).keys())
        self.item_menu.configure(values=names)
        if names:
            self.item_var.set(names[0])

    def refresh(self) -> None:
        self._slot_index = int(self.slot_var.get())
        save: DS2Save | None = self.get_save()

        for row in self.tree.get_children():
            self.tree.delete(row)
        if save is None:
            return

        character = save.characters[self._slot_index]
        for item in character.inventory() + character.key_items():
            if item.item_id == 0:
                continue
            info = self._item_db.get(item.item_id)
            name, category = info if info else (f"Unknown ({item.item_id})", "?")
            self.tree.insert(
                "", "end", values=(name, category, item.item_id, item.quantity)
            )

    def _on_add(self) -> None:
        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return

        category = self.category_var.get()
        item_name = self.item_var.get()
        hex_id = CATEGORIES.get(category, {}).get(item_name)
        if hex_id is None:
            self.show_toast("Item not found", duration=2000)
            return

        try:
            quantity = int(self.qty_var.get())
        except ValueError:
            self.show_toast("Invalid quantity", duration=2000)
            return

        item_id = _hex_id_to_int(hex_id)
        character = save.characters[self._slot_index]
        added = character.add_item(item_id, category, quantity=quantity)
        if not added:
            self.show_toast("No empty inventory slot available", duration=2500)
            return

        self._write_and_refresh(save)
        self.show_toast(f"Added {item_name}", duration=2000)

    def _on_delete(self) -> None:
        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return

        selection = self.tree.selection()
        if not selection:
            self.show_toast("No item selected", duration=2000)
            return

        values = self.tree.item(selection[0], "values")
        name, category, item_id = values[0], values[1], int(values[2])
        character = save.characters[self._slot_index]
        deleted = character.delete_item(item_id, category)
        if not deleted:
            self.show_toast("Item not found in inventory", duration=2000)
            return

        self._write_and_refresh(save)
        self.show_toast(f"Deleted {name}", duration=2000)

    def _write_and_refresh(self, save: DS2Save) -> None:
        save_path = self.get_save_path()
        if save_path:
            try:
                save.save_to_file(save_path)
            except Exception as e:
                self.show_toast(f"Failed to write save: {e}", duration=3000)
        self.refresh()
