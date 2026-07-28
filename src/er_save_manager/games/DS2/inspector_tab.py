"""DS2 save inspector tab: slot overview and basic integrity checks."""

from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

from er_save_manager.games.DS2.save import CHARACTER_SELECT_ENTRY, DS2Save


class DS2InspectorTab:
    """
    Args:
        parent: parent widget the tab content is built into.
        get_save: callable returning the current DS2Save, or None if unloaded.
        on_slot_selected: callable(slot_index) invoked when a row is picked.
    """

    def __init__(self, parent, get_save, on_slot_selected) -> None:
        self.parent = parent
        self.get_save = get_save
        self.on_slot_selected = on_slot_selected

    def setup_ui(self) -> None:
        top = ctk.CTkFrame(self.parent, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkButton(top, text="Refresh", command=self.refresh).pack(side="left")

        columns = ("slot", "name", "level", "souls", "status", "check")
        self.tree = ttk.Treeview(
            self.parent, columns=columns, show="headings", height=12
        )
        headings = {
            "slot": ("Slot", 50),
            "name": ("Name", 200),
            "level": ("Level", 60),
            "souls": ("Souls", 100),
            "status": ("Status", 160),
            "check": ("Integrity", 200),
        }
        for col, (label, width) in headings.items():
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree.bind("<Double-1>", self._on_row_activated)

        self.refresh()

    def refresh(self) -> None:
        save: DS2Save | None = self.get_save()
        for row in self.tree.get_children():
            self.tree.delete(row)
        if save is None:
            return

        save.slot_occupancy()
        select_data = save.container.get_entry(CHARACTER_SELECT_ENTRY)

        for i, character in enumerate(save.characters):
            name = character.name
            display_name = name if name else "(empty)"
            status = "Ready" if save.is_slot_initialized(i) else "Never created in-game"
            check = self._check_slot(save, i, name, select_data)
            self.tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    i,
                    display_name,
                    character.get_stat("level"),
                    character.souls,
                    status,
                    check,
                ),
            )

    def _check_slot(
        self, save: DS2Save, index: int, profile_name: str, select_data
    ) -> str:
        from er_save_manager.games.DS2.save import (
            _OCC_STRIDE,
            _SELECT_NAME_OFFSET,
            _SELECT_NAME_SIZE,
        )

        if not profile_name:
            return "OK (empty)"

        off = _SELECT_NAME_OFFSET + _OCC_STRIDE * index
        cached = (
            select_data[off : off + _SELECT_NAME_SIZE]
            .decode("utf-16-le", errors="ignore")
            .rstrip("\x00")
        )
        if cached and cached != profile_name:
            return f"Name mismatch (select screen shows '{cached}')"
        return "OK"

    def _on_row_activated(self, event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        slot_index = int(selection[0])
        self.on_slot_selected(slot_index)
