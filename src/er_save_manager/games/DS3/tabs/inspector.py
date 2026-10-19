"""DS3 Save Inspector tab - shows all characters, click to edit."""

from __future__ import annotations

import customtkinter as ctk

from er_save_manager.games.DS3 import catalog
from er_save_manager.ui.character_list import (
    CharacterList,
    CharacterRow,
    columns,
    format_playtime,
    slot_issues,
)
from er_save_manager.ui.messagebox import CTkMessageBox


class DS3InspectorTab:
    def __init__(
        self, parent, get_save, on_slot_selected=None, check_save=None, get_issues=None
    ) -> None:
        self.parent = parent
        self._check_save = check_save
        self._get_issues = get_issues
        self._get_save = get_save
        self._on_slot_selected = on_slot_selected
        self.selected_slot: int | None = None

    def setup_ui(self) -> None:
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(header, text="Save Inspector", font=("Inter", 16, "bold")).pack(
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
            font=("Inter", 11),
            text_color=("gray40", "gray70"),
        ).pack(side="left", anchor="w")

        self.list = CharacterList(outer, on_select=self._select)
        self.list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _select(self, slot_idx: int) -> None:
        self.selected_slot = slot_idx

    def refresh(self) -> None:
        self.selected_slot = None
        save = self._get_save()
        if save is None:
            self.list.message("No save file loaded.")
            return

        issues = self._get_issues() if self._get_issues else None
        # The Inspector has no Game data selector; vanilla names the classes
        classes = catalog.starting_classes("vanilla")
        rows = []
        for slot_idx, char in enumerate(save.characters):
            if char is None:
                continue
            cls = char.starting_class
            values = {
                "level": str(char.level),
                "class": classes[cls].name if cls < len(classes) else f"Class {cls}",
                "currency": f"{char.souls:,}",
                "ng": "NG+?" if char.layout_error else f"NG+{char.ng_plus}",
                "playtime": format_playtime(char.play_time_ms / 1000),
            }
            rows.append(
                CharacterRow(slot_idx, char.name, values, slot_issues(issues, slot_idx))
            )
        self.list.show(columns("Souls"), rows)

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
        if self._on_slot_selected:
            self._on_slot_selected(self.selected_slot)
