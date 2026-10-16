"""
DS2 save inspector tab: slot overview and basic integrity checks.
"""

from __future__ import annotations

import customtkinter as ctk

from er_save_manager.games.DS2.save import CHARACTER_SELECT_ENTRY, DS2Save, SlotState
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


class DS2InspectorTab:
    """
    Args:
        parent: parent widget the tab content is built into.
        get_save: callable returning the current DS2Save, or None if unloaded.
        on_slot_selected: callable(slot_index) invoked by the Edit Character button.
    """

    def __init__(self, parent, get_save, on_slot_selected, check_save=None) -> None:
        self.parent = parent
        self._check_save = check_save
        self.get_save = get_save
        self.on_slot_selected = on_slot_selected

        self.selected_slot: int | None = None
        self.rows: list[tuple[int, ctk.CTkFrame]] = []

    def setup_ui(self) -> None:
        char_frame = ctk.CTkFrame(self.parent, corner_radius=12)
        char_frame.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(char_frame, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(header, text="Save Inspector", font=("Segoe UI", 16, "bold")).pack(
            side="left"
        )
        ctk.CTkButton(
            header, text="Edit Character", command=self._edit_selected, width=160
        ).pack(side="right")
        if self._check_save is not None:
            ctk.CTkButton(
                header, text="View All Issues", command=self._view_issues, width=180
            ).pack(side="right", padx=(0, 8))

        ctk.CTkLabel(
            char_frame,
            text="Select a character slot, then click Edit Character to open it in Character Editor.",
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
            ctk.CTkLabel(self.list_frame, text="No save file loaded").pack(
                anchor="w", padx=6, pady=6
            )
            return

        select_data = save.container.get_entry(CHARACTER_SELECT_ENTRY)

        def select_slot(slot_index: int):
            self.selected_slot = slot_index
            for val, frame in self.rows:
                ds.select_card_row(frame, val == slot_index)

        for i, character in enumerate(save.characters):
            if save.slot_state(i) is SlotState.NEVER_CREATED:
                continue

            name = save.slot_display_name(i)
            display_name = name if name else f"({save.slot_state(i).value})"
            status = "Ready"
            check = self._check_slot(i, name, select_data)

            row = ds.card_row(
                self.list_frame,
                display_name,
                f"Slot {i}  ·  Level {character.get_stat('level')}  ·  "
                f"Souls {character.souls:,}  ·  {status}  ·  {check}",
                on_click=lambda v=i: select_slot(v),
                on_double=lambda v=i: self._edit_slot(v),
            )
            self.rows.append((i, row))

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

    def _view_issues(self) -> None:
        if self.selected_slot is None:
            CTkMessageBox.showwarning(
                "No Selection", "Select a character first.", parent=self.parent
            )
            return
        self._check_save(self.selected_slot)

    def _edit_selected(self) -> None:
        if self.selected_slot is None:
            return
        self._edit_slot(self.selected_slot)
