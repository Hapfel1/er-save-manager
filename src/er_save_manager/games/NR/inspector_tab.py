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
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

if TYPE_CHECKING:
    pass


class NRInspectorTab:
    def __init__(
        self,
        parent,
        get_nr_save: Callable,
        on_slot_selected: Callable | None = None,
        check_save: Callable | None = None,
    ) -> None:
        self.parent = parent
        self._check_save = check_save
        self._get_nr_save = get_nr_save
        self._on_slot_selected = on_slot_selected
        self.selected_slot: int | None = None
        self._rows: list[tuple[int, ctk.CTkFrame, ctk.CTkLabel]] = []

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

        hint_frame = ctk.CTkFrame(outer, fg_color="transparent")
        hint_frame.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(
            hint_frame,
            text="Select a character and click 'Edit Character' to open the editor tabs.",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(side="left", anchor="w")

        self.list_frame = ctk.CTkScrollableFrame(
            outer, width=900, height=320, corner_radius=10
        )
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        bind_mousewheel(self.list_frame)

    def refresh(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._rows.clear()
        self.selected_slot = None

        save = self._get_nr_save()
        if save is None:
            ctk.CTkLabel(
                self.list_frame,
                text="No save file loaded.",
                text_color=("gray50", "gray60"),
            ).pack(anchor="w", padx=6, pady=6)
            return

        if save.trailing_bytes:
            ctk.CTkLabel(
                self.list_frame,
                text=(
                    f"This file has {save.trailing_bytes} junk bytes past its last "
                    "entry. They are removed the next time the editor saves this file."
                ),
                text_color=palette.PURPLE_TEXT,
                font=("Segoe UI", 11),
                wraplength=640,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=6, pady=(2, 4))

        occupied = [
            (i, slot)
            for i, slot in enumerate(save.slots)
            if slot.entry_count > 0 or slot.player_name
        ]
        if not occupied:
            ctk.CTkLabel(self.list_frame, text="No active characters found.").pack(
                anchor="w", padx=6, pady=6
            )
            return

        for slot_idx, slot in occupied:
            display = (
                f"Slot {slot_idx + 1:2d} | {slot.player_name:16s} | "
                f"Murk: {slot.murk:>11,} | Sigils: {slot.marks_of_night:>6,} | "
                f"Relics: {len(slot.relic_states):>4d}"
            )
            row = ctk.CTkFrame(
                self.list_frame, fg_color=("#f5f5f5", "#2a2a3e"), corner_radius=6
            )
            row.pack(fill="x", padx=4, pady=4)
            label = ctk.CTkLabel(
                row, text=display, anchor="w", padx=8, pady=8, font=("Courier", 13)
            )
            label.pack(fill="x")
            row.bind("<Button-1>", lambda _e, v=slot_idx: self._select_row(v))
            label.bind("<Button-1>", lambda _e, v=slot_idx: self._select_row(v))
            self._rows.append((slot_idx, row, label))

        if self._rows:
            self._select_row(self._rows[0][0])

    def _select_row(self, idx: int) -> None:
        self.selected_slot = idx
        for val, frame, label in self._rows:
            if val == idx:
                frame.configure(fg_color=palette.PURPLE_TINT)
                label.configure(text_color=("#1f1f28", "#f0f0f0"))
            else:
                frame.configure(fg_color=("#f5f5f5", "#2a2a3e"))
                label.configure(text_color=("#333333", "#cccccc"))

    def _view_issues(self) -> None:
        if self.selected_slot is None:
            CTkMessageBox.showwarning(
                "No Selection", "Please select a character first!", parent=self.parent
            )
            return
        self._check_save(self.selected_slot)

    def _edit_selected(self) -> None:
        if self.selected_slot is None:
            CTkMessageBox.showwarning(
                "No Selection", "Please select a character first.", parent=self.parent
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
