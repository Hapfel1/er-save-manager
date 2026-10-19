"""
Nightreign Save Inspector Tab

Lists the occupied slots with name, murk, Sovereign Sigils and relic count.
Clicking a row selects it. "Edit Character" navigates to the editor tab.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.ui import palette
from er_save_manager.ui.character_list import (
    CharacterList,
    CharacterRow,
    columns,
    format_playtime,
    slot_issues,
)
from er_save_manager.ui.messagebox import CTkMessageBox

if TYPE_CHECKING:
    pass


class NRInspectorTab:
    def __init__(
        self,
        parent,
        get_nr_save: Callable,
        on_slot_selected: Callable | None = None,
        check_save: Callable | None = None,
        get_issues: Callable | None = None,
    ) -> None:
        self.parent = parent
        self._check_save = check_save
        self._get_issues = get_issues
        self._get_nr_save = get_nr_save
        self._on_slot_selected = on_slot_selected
        self.selected_slot: int | None = None

    def setup_ui(self) -> None:
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
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

        self._hint_frame = ctk.CTkFrame(outer, fg_color="transparent")
        self._hint_frame.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(
            self._hint_frame,
            text="Select a character and click 'Edit Character' to open the editor tabs.",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(side="left", anchor="w")

        # Packed above the list only while the file has junk bytes
        self._junk_note = ctk.CTkLabel(
            outer,
            text="",
            text_color=palette.PURPLE_TEXT,
            font=("Segoe UI", 11),
            wraplength=640,
            justify="left",
            anchor="w",
        )
        self.list = CharacterList(outer, on_select=self._select_row)
        self.list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def refresh(self) -> None:
        self.selected_slot = None
        self._junk_note.pack_forget()
        save = self._get_nr_save()
        if save is None:
            self.list.message("No save file loaded.")
            return

        if save.trailing_bytes:
            self._junk_note.configure(
                text=(
                    f"This file has {save.trailing_bytes} junk bytes past its last "
                    "entry. They are removed the next time the editor saves this file."
                )
            )
            self._junk_note.pack(fill="x", padx=16, pady=(0, 4), after=self._hint_frame)

        issues = self._get_issues() if self._get_issues else None
        rows = [
            CharacterRow(
                slot_idx,
                slot.player_name,
                {
                    "currency": f"{slot.murk:,}",
                    "playtime": format_playtime(slot.play_time_ms / 1000),
                    "sigils": f"{slot.marks_of_night:,}",
                    "relics": str(len(slot.relic_states)),
                },
                slot_issues(issues, slot_idx),
            )
            for slot_idx, slot in enumerate(save.slots)
            if slot.entry_count > 0 or slot.player_name
        ]
        cols = columns(
            "Murk",
            level=False,
            char_class=False,
            ng_plus=False,
            extras=(("sigils", "Sigils", 90), ("relics", "Relics", 60)),
        )
        self.list.show(cols, rows)

    def _select_row(self, idx: int) -> None:
        self.selected_slot = idx

    def _view_issues(self) -> None:
        if self.selected_slot is None:
            CTkMessageBox.showwarning(
                "No Selection", "Select a character first.", parent=self.parent
            )
            return
        self._check_save(self.selected_slot)

    def _edit_selected(self) -> None:
        if self.selected_slot is None:
            CTkMessageBox.showwarning(
                "No Selection", "Select a character first.", parent=self.parent
            )
            return
        save = self._get_nr_save()
        if save is None:
            return
        slot = save.slots[self.selected_slot]
        if slot.entry_count == 0 and not slot.player_name:
            CTkMessageBox.showinfo(
                "Empty Slot", "That slot has no character data.", parent=self.parent
            )
            return
        if self._on_slot_selected:
            self._on_slot_selected(self.selected_slot)
