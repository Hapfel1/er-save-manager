"""
Nightreign Save Inspector Tab

Shows all 10 slots with name, hero usage, relic count, murk, and Marks of Night.
Clicking a row selects it. "Edit Slot" navigates to the editor tab.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import customtkinter as ctk

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
    ) -> None:
        self.parent = parent
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
            header, text="Edit Slot", command=self._edit_selected, width=130
        ).pack(side="right", padx=(6, 0))

        ctk.CTkLabel(
            outer,
            text="Select a slot then click 'Edit Slot' to open the editor.",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=12, pady=(0, 4))

        self.list_frame = ctk.CTkScrollableFrame(outer, corner_radius=10)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        bind_mousewheel(self.list_frame)

        # Column header row
        hdr = ctk.CTkFrame(
            self.list_frame, fg_color=("gray75", "gray28"), corner_radius=6
        )
        hdr.pack(fill="x", padx=4, pady=(4, 2))
        for text, w in [
            ("Slot", 50),
            ("Name", 160),
            ("Murk", 90),
            ("Sovereign Sigils", 110),
            ("Relics", 70),
            ("Entries", 70),
        ]:
            ctk.CTkLabel(
                hdr, text=text, font=("Segoe UI", 11, "bold"), width=w, anchor="w"
            ).pack(side="left", padx=6)

    def refresh(self) -> None:
        for child in self.list_frame.winfo_children():
            # Keep the header row (first child)
            if (
                child == self.list_frame.winfo_children()[0]
                if self.list_frame.winfo_children()
                else None
            ):
                continue
            child.destroy()
        # Destroy all except header
        children = self.list_frame.winfo_children()
        for child in children[1:]:
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

        for i, slot in enumerate(save.slots):
            is_active = slot.entry_count > 0 or bool(slot.player_name)
            name = slot.player_name if slot.player_name else "(empty)"
            murk = str(slot.murk) if is_active else "-"
            mon = str(slot.marks_of_night) if is_active else "-"
            relics = str(len(slot.relic_states)) if is_active else "-"
            entries = str(slot.entry_count) if is_active else "-"

            row = ctk.CTkFrame(
                self.list_frame,
                corner_radius=6,
                fg_color=("gray88", "gray20"),
            )
            row.pack(fill="x", padx=4, pady=2)

            lbl_slot = ctk.CTkLabel(
                row,
                text=str(i + 1),
                width=50,
                anchor="w",
                font=("Segoe UI", 12, "bold" if is_active else "normal"),
            )
            lbl_slot.pack(side="left", padx=6)

            lbl_name = ctk.CTkLabel(
                row,
                text=name,
                width=160,
                anchor="w",
                font=("Segoe UI", 12),
                text_color=("gray20", "gray90") if is_active else ("gray50", "gray55"),
            )
            lbl_name.pack(side="left", padx=6)

            for val, w in [(murk, 90), (mon, 110), (relics, 70), (entries, 70)]:
                ctk.CTkLabel(
                    row, text=val, width=w, anchor="w", font=("Segoe UI", 11)
                ).pack(side="left", padx=6)

            self._rows.append((i, row, lbl_name))

            # Bind click to select
            for widget in [row, lbl_slot, lbl_name]:
                widget.bind("<Button-1>", lambda e, idx=i: self._select_row(idx))

    def _select_row(self, idx: int) -> None:
        self.selected_slot = idx
        for i, row, _ in self._rows:
            color = ("gray78", "gray35") if i == idx else ("gray88", "gray20")
            row.configure(fg_color=color)

    def _edit_selected(self) -> None:
        if self.selected_slot is None:
            CTkMessageBox.showinfo(
                "No Selection", "Select a slot first.", parent=self.parent
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
