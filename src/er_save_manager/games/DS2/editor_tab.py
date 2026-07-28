"""DS2 character editor tab: slot select, stats/souls/hp/ng, inventory list."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from er_save_manager.games.DS2.item_database import build_item_db
from er_save_manager.games.DS2.save import STAT_OFFSETS, DS2Save


class DS2EditorTab:
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
        self._stat_vars: dict[str, tk.StringVar] = {}

    def setup_ui(self) -> None:
        top = ctk.CTkFrame(self.parent, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Character slot:").pack(side="left")
        self.slot_var = tk.StringVar(value="0")
        self.slot_menu = ctk.CTkOptionMenu(
            top,
            variable=self.slot_var,
            values=[str(i) for i in range(10)],
            command=self._on_slot_changed,
        )
        self.slot_menu.pack(side="left", padx=(5, 15))

        ctk.CTkButton(top, text="Refresh", command=self.refresh).pack(
            side="left", padx=5
        )
        ctk.CTkButton(top, text="Save changes", command=self._apply_changes).pack(
            side="left", padx=5
        )

        self.slot_status_label = ctk.CTkLabel(top, text="")
        self.slot_status_label.pack(side="left", padx=(15, 0))

        fields = ctk.CTkFrame(self.parent, fg_color="transparent")
        fields.pack(fill="x", padx=10, pady=5)

        self.name_var = tk.StringVar()
        self.souls_var = tk.StringVar()
        self.hp_var = tk.StringVar()
        self.ng_var = tk.StringVar()

        self._add_field(fields, "Name", self.name_var, row=0)
        self._add_field(fields, "Souls", self.souls_var, row=1)
        self._add_field(fields, "HP", self.hp_var, row=2)
        self._add_field(fields, "NG+", self.ng_var, row=3)

        stats_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        stats_frame.pack(fill="x", padx=10, pady=5)
        for i, stat_name in enumerate(STAT_OFFSETS):
            var = tk.StringVar()
            self._stat_vars[stat_name] = var
            self._add_field(
                stats_frame, stat_name.capitalize(), var, row=i // 3, col=(i % 3) * 2
            )

        inv_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        inv_frame.pack(fill="both", expand=True, padx=10, pady=(10, 10))
        ctk.CTkLabel(inv_frame, text="Inventory (read-only)").pack(anchor="w")

        columns = ("name", "category", "item_id")
        self.inv_tree = ttk.Treeview(
            inv_frame, columns=columns, show="headings", height=12
        )
        for col, width in (("name", 260), ("category", 100), ("item_id", 100)):
            self.inv_tree.heading(col, text=col.replace("_", " ").title())
            self.inv_tree.column(col, width=width)
        self.inv_tree.pack(fill="both", expand=True)

        self.refresh()

    def _add_field(self, parent, label, var, row, col=0):
        ctk.CTkLabel(parent, text=f"{label}:").grid(
            row=row, column=col, sticky="w", padx=5, pady=3
        )
        ctk.CTkEntry(parent, textvariable=var, width=140).grid(
            row=row, column=col + 1, sticky="w", padx=5, pady=3
        )

    def _on_slot_changed(self, value: str) -> None:
        self._slot_index = int(value)
        self.refresh()

    def refresh(self) -> None:
        self._slot_index = int(self.slot_var.get())
        save: DS2Save | None = self.get_save()
        if save is None:
            return

        if not save.is_slot_initialized(self._slot_index):
            self.slot_status_label.configure(
                text="Never created in-game - edits here will not appear at the load screen",
                text_color="orange",
            )
        else:
            self.slot_status_label.configure(text="")

        character = save.characters[self._slot_index]
        self.name_var.set(character.name)
        self.souls_var.set(str(character.souls))
        self.hp_var.set(str(character.hp))
        self.ng_var.set(str(character.new_game_plus))
        for stat_name, var in self._stat_vars.items():
            var.set(str(character.get_stat(stat_name)))

        for row in self.inv_tree.get_children():
            self.inv_tree.delete(row)
        for item in character.inventory():
            if item.item_id == 0:
                continue
            info = self._item_db.get(item.item_id)
            name, category = info if info else (f"Unknown ({item.item_id})", "?")
            self.inv_tree.insert("", "end", values=(name, category, item.item_id))

    def _apply_changes(self) -> None:
        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return

        character = save.characters[self._slot_index]
        try:
            character.name = self.name_var.get()
            character.souls = int(self.souls_var.get())
            character.hp = int(self.hp_var.get())
            character.new_game_plus = int(self.ng_var.get())
            for stat_name, var in self._stat_vars.items():
                character.set_stat(stat_name, int(var.get()))
        except ValueError:
            self.show_toast("Invalid numeric value, changes not applied", duration=2500)
            return

        save_path = self.get_save_path()
        if not save_path:
            self.show_toast("No save path to write to", duration=2000)
            return

        try:
            save.save_to_file(save_path)
        except Exception as e:
            self.show_toast(f"Failed to write save: {e}", duration=3000)
            return

        self.show_toast("Changes saved to disk", duration=2500)
