"""
DS2 save inspector tab: slot overview and basic integrity checks.
"""

from __future__ import annotations

import customtkinter as ctk

from er_save_manager.games.DS2.save import DS2Save, SlotState
from er_save_manager.ui.character_list import (
    CharacterList,
    CharacterRow,
    columns,
    format_playtime,
    slot_issues,
)
from er_save_manager.ui.messagebox import CTkMessageBox


class DS2InspectorTab:
    """
    Args:
        parent: parent widget the tab content is built into.
        get_save: callable returning the current DS2Save, or None if unloaded.
        on_slot_selected: callable(slot_index) invoked by the Edit Character button.
    """

    def __init__(
        self, parent, get_save, on_slot_selected, check_save=None, get_issues=None
    ) -> None:
        self.parent = parent
        self._check_save = check_save
        self._get_issues = get_issues
        self.get_save = get_save
        self.on_slot_selected = on_slot_selected

        self.selected_slot: int | None = None

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

        self.list = CharacterList(
            char_frame, on_select=self._select, on_double=self._edit_slot
        )
        self.list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.refresh()

    def _select(self, slot_index: int) -> None:
        self.selected_slot = slot_index

    def refresh(self) -> None:
        self.selected_slot = None
        save: DS2Save | None = self.get_save()
        if save is None:
            self.list.message("No save file loaded.")
            return

        issues = self._get_issues() if self._get_issues else None
        rows = []
        for i, character in enumerate(save.characters):
            if save.slot_state(i) is SlotState.NEVER_CREATED:
                continue
            name = save.slot_display_name(i)
            values = {
                "level": str(character.get_stat("level")),
                "class": character.starting_class_name or "",
                "currency": f"{character.souls:,}",
                "ng": f"NG+{character.new_game_plus}",
                "playtime": format_playtime(save.slot_play_seconds(i)),
            }
            rows.append(
                CharacterRow(
                    i,
                    name or f"({save.slot_state(i).value})",
                    values,
                    slot_issues(issues, i),
                )
            )
        self.list.show(columns("Souls"), rows)

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
