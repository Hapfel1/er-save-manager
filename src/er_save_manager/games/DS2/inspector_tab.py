"""
DS2 save inspector tab: slot overview and basic integrity checks.
"""

from __future__ import annotations

import customtkinter as ctk

from er_save_manager.games.DS2.save import CHARACTER_SELECT_ENTRY, DS2Save
from er_save_manager.i18n import t
from er_save_manager.ui.utils import bind_mousewheel


class DS2InspectorTab:
    """
    Args:
        parent: parent widget the tab content is built into.
        get_save: callable returning the current DS2Save, or None if unloaded.
        on_slot_selected: callable(slot_index) invoked by the Edit Character button.
    """

    def __init__(self, parent, get_save, on_slot_selected) -> None:
        self.parent = parent
        self.get_save = get_save
        self.on_slot_selected = on_slot_selected

        self.selected_slot: int | None = None
        self.rows: list[tuple[int, ctk.CTkFrame, ctk.CTkLabel]] = []

    def setup_ui(self) -> None:
        char_frame = ctk.CTkFrame(self.parent, corner_radius=12)
        char_frame.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(char_frame, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            header, text=t("Save Inspector"), font=("Segoe UI", 16, "bold")
        ).pack(side="left")
        ctk.CTkButton(
            header, text=t("Edit Character"), command=self._edit_selected, width=160
        ).pack(side="right")

        ctk.CTkLabel(
            char_frame,
            text=t(
                "Select a character slot, then click Edit Character to open it in Character Editor."
            ),
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=10, pady=(0, 10))

        self.list_frame = ctk.CTkScrollableFrame(char_frame, corner_radius=10)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        bind_mousewheel(self.list_frame)

        self.refresh()

    def refresh(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        self.rows.clear()
        self.selected_slot = None

        save: DS2Save | None = self.get_save()
        if save is None:
            ctk.CTkLabel(self.list_frame, text=t("No save file loaded")).pack(
                anchor="w", padx=6, pady=6
            )
            return

        select_data = save.container.get_entry(CHARACTER_SELECT_ENTRY)

        def select_slot(slot_index: int):
            self.selected_slot = slot_index
            for val, frame, label in self.rows:
                if val == slot_index:
                    frame.configure(fg_color=("#c9a0dc", "#3b2f5c"))
                    label.configure(text_color=("#1f1f28", "#f0f0f0"))
                else:
                    frame.configure(fg_color=("#f5f5f5", "#2a2a3e"))
                    label.configure(text_color=("#333333", "#cccccc"))

        for i, character in enumerate(save.characters):
            name = character.name
            display_name = name if name else "(empty)"
            status = "Ready" if save.is_slot_initialized(i) else "Never created in-game"
            check = self._check_slot(i, name, select_data)

            display_text = (
                f"Slot {i} | {display_name:16s} | Lv.{character.get_stat('level'):>3d} "
                f"| Souls: {character.souls:<10d} | {status:24s} | {check}"
            )

            row = ctk.CTkFrame(
                self.list_frame, fg_color=("#f5f5f5", "#2a2a3e"), corner_radius=6
            )
            row.pack(fill="x", padx=4, pady=4)

            label = ctk.CTkLabel(
                row, text=display_text, anchor="w", padx=8, pady=8, font=("Courier", 13)
            )
            label.pack(fill="x")

            row.bind("<Button-1>", lambda e, v=i: select_slot(v))
            label.bind("<Button-1>", lambda e, v=i: select_slot(v))
            row.bind("<Double-Button-1>", lambda e, v=i: self._edit_slot(v))
            label.bind("<Double-Button-1>", lambda e, v=i: self._edit_slot(v))

            self.rows.append((i, row, label))

        if self.rows:
            select_slot(self.rows[0][0])

    def _check_slot(self, index: int, profile_name: str, select_data) -> str:
        from er_save_manager.games.DS2.save import (
            _OCC_STRIDE,
            _SELECT_NAME_OFFSET,
            _SELECT_NAME_SIZE,
        )

        if not profile_name:
            return "OK"

        off = _SELECT_NAME_OFFSET + _OCC_STRIDE * index
        cached = (
            select_data[off : off + _SELECT_NAME_SIZE]
            .decode("utf-16-le", errors="ignore")
            .rstrip("\x00")
        )
        if cached and cached != profile_name:
            return f"Name mismatch (select screen shows '{cached}')"
        return "OK"

    def _edit_slot(self, slot_index: int) -> None:
        self.selected_slot = slot_index
        if self.on_slot_selected:
            self.on_slot_selected(slot_index)

    def _edit_selected(self) -> None:
        if self.selected_slot is None:
            return
        self._edit_slot(self.selected_slot)
