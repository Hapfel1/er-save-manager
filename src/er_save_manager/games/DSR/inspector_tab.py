"""
DSR Save Inspector Tab

Clicking a row highlights it. Only the "Edit Character" button navigates
to the Character Editor. Row clicks do not trigger tab switching.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

if TYPE_CHECKING:
    pass

_CLASS_NAMES = [
    "Warrior",
    "Knight",
    "Wanderer",
    "Thief",
    "Bandit",
    "Hunter",
    "Sorcerer",
    "Pyromancer",
    "Cleric",
    "Deprived",
]


class DSRInspectorTab:
    def __init__(self, parent, get_dsr_save, on_slot_selected=None) -> None:
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        self._on_slot_selected = on_slot_selected
        self.selected_slot: int | None = None
        self._rows: list[tuple[int, ctk.CTkFrame, ctk.CTkLabel]] = []

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

        ctk.CTkLabel(
            ctk.CTkFrame(char_frame, fg_color="transparent"),
            text="Select a character and click 'Edit Character' to open the editor tabs.",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(side="left", anchor="w")

        self.list_frame = ctk.CTkScrollableFrame(
            char_frame, width=900, height=320, corner_radius=10
        )
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        bind_mousewheel(self.list_frame)

    def refresh(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._rows.clear()
        self.selected_slot = None

        save = self._get_dsr_save()
        if save is None:
            ctk.CTkLabel(
                self.list_frame,
                text="No save file loaded.",
                text_color=("gray50", "gray60"),
            ).pack(anchor="w", padx=6, pady=6)
            return

        occupied = [(i, c) for i, c in enumerate(save.characters) if c is not None]
        if not occupied:
            ctk.CTkLabel(self.list_frame, text="No active characters found.").pack(
                anchor="w", padx=6, pady=6
            )
            return

        def select(slot_idx: int) -> None:
            # Highlight only - does NOT navigate to another tab
            self.selected_slot = slot_idx
            for val, frame, label in self._rows:
                if val == slot_idx:
                    frame.configure(fg_color=("#c9a0dc", "#3b2f5c"))
                    label.configure(text_color=("#1f1f28", "#f0f0f0"))
                else:
                    frame.configure(fg_color=("#f5f5f5", "#2a2a3e"))
                    label.configure(text_color=("#333333", "#cccccc"))

        for slot_idx, char in occupied:
            cls = int(char.player_class)
            class_name = _CLASS_NAMES[cls] if cls < len(_CLASS_NAMES) else str(cls)
            display = (
                f"Slot {slot_idx + 1:2d} | {char.name:16s} | "
                f"Lv.{char.level:>3d} | {class_name:<14s} | "
                f"Souls: {char.souls:>8,} | NG+{char.ng_plus}"
            )
            row = ctk.CTkFrame(
                self.list_frame, fg_color=("#f5f5f5", "#2a2a3e"), corner_radius=6
            )
            row.pack(fill="x", padx=4, pady=4)
            label = ctk.CTkLabel(
                row, text=display, anchor="w", padx=8, pady=8, font=("Courier", 13)
            )
            label.pack(fill="x")

            row.bind("<Button-1>", lambda _e, v=slot_idx: select(v))
            label.bind("<Button-1>", lambda _e, v=slot_idx: select(v))

            self._rows.append((slot_idx, row, label))

        if self._rows:
            select(self._rows[0][0])

    def _edit_selected(self) -> None:
        if self.selected_slot is None:
            CTkMessageBox.showwarning(
                "No Selection", "Please select a character first.", parent=self.parent
            )
            return
        if self._on_slot_selected:
            self._on_slot_selected(self.selected_slot)
