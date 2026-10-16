"""DS3 Save Inspector tab - shows all characters, click to edit."""

from __future__ import annotations

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


class DS3InspectorTab:
    def __init__(
        self, parent, get_save, on_slot_selected=None, check_save=None
    ) -> None:
        self.parent = parent
        self._check_save = check_save
        self._get_save = get_save
        self._on_slot_selected = on_slot_selected
        self.selected_slot: int | None = None
        self._rows: list[tuple[int, ctk.CTkFrame]] = []

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

        save = self._get_save()
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
            self.selected_slot = slot_idx
            for val, frame in self._rows:
                ds.select_card_row(frame, val == slot_idx)

        for slot_idx, char in occupied:
            ng = "NG+?" if char.layout_error else f"NG+{char.ng_plus}"
            row = ds.card_row(
                self.list_frame,
                char.name,
                f"Slot {slot_idx + 1}  ·  Level {char.level}  ·  "
                f"Souls {char.souls:,}  ·  {ng}",
                on_click=lambda v=slot_idx: select(v),
            )
            self._rows.append((slot_idx, row))

        if self._rows:
            select(self._rows[0][0])

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
