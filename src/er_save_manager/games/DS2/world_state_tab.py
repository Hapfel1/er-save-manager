"""
DS2 world state tab: raw byte/bit browser over the candidate flag region.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from er_save_manager.games.DS2.save import FLAG_REGION_END, FLAG_REGION_START, DS2Save


class DS2WorldStateTab:
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
        self._slot_index = 0

    def setup_ui(self) -> None:
        warning = ctk.CTkLabel(
            self.parent,
            text=(
                "Experimental: individual flag IDs in this region are not "
                "mapped yet. This lists non-zero bytes for comparison and "
                "lets a byte's bits be toggled directly."
            ),
            wraplength=700,
            justify="left",
        )
        warning.pack(fill="x", padx=10, pady=(10, 5))

        top = ctk.CTkFrame(self.parent, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=5)

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

        edit_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        edit_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(edit_frame, text="Byte offset (relative to region start):").pack(
            side="left"
        )
        self.offset_var = tk.StringVar()
        ctk.CTkEntry(edit_frame, textvariable=self.offset_var, width=80).pack(
            side="left", padx=5
        )
        ctk.CTkLabel(edit_frame, text="New value (0-255):").pack(
            side="left", padx=(15, 0)
        )
        self.value_var = tk.StringVar()
        ctk.CTkEntry(edit_frame, textvariable=self.value_var, width=80).pack(
            side="left", padx=5
        )
        ctk.CTkButton(edit_frame, text="Write byte", command=self._on_write_byte).pack(
            side="left", padx=15
        )

        columns = ("offset", "hex", "binary")
        self.tree = ttk.Treeview(
            self.parent, columns=columns, show="headings", height=16
        )
        for col, width in (("offset", 100), ("hex", 80), ("binary", 120)):
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.refresh()

    def refresh(self) -> None:
        self._slot_index = int(self.slot_var.get())
        save: DS2Save | None = self.get_save()

        for row in self.tree.get_children():
            self.tree.delete(row)
        if save is None:
            return

        data = save.characters[self._slot_index].raw()
        region = data[FLAG_REGION_START:FLAG_REGION_END]
        for i, byte in enumerate(region):
            if byte != 0:
                self.tree.insert(
                    "", "end", values=(i, f"0x{byte:02X}", format(byte, "08b"))
                )

    def _on_write_byte(self) -> None:
        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return

        try:
            rel_offset = int(self.offset_var.get())
            value = int(self.value_var.get())
        except ValueError:
            self.show_toast("Offset and value must be integers", duration=2500)
            return

        if not (0 <= value <= 255):
            self.show_toast("Value must be 0-255", duration=2000)
            return

        region_size = FLAG_REGION_END - FLAG_REGION_START
        if not (0 <= rel_offset < region_size):
            self.show_toast(f"Offset must be 0-{region_size - 1}", duration=2500)
            return

        character = save.characters[self._slot_index]
        character.raw()[FLAG_REGION_START + rel_offset] = value

        save_path = self.get_save_path()
        if save_path:
            try:
                save.save_to_file(save_path)
            except Exception as e:
                self.show_toast(f"Failed to write save: {e}", duration=3000)
                return

        self.refresh()
        self.show_toast("Byte written", duration=2000)
