"""
DSR World State Tab - bonfires and NG+. All writes backup then save
immediately.

Bonfires (data/bonfires.json, named by their map's place names) are lit by
their record in the visited maps' object data (see save.BONFIRE_RECORD_TYPE);
bonfires in maps the character has not visited have no record yet.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import FieldTracker, PendingPage, StageError, var_state
from er_save_manager.ui.tooltip import MULTI_SELECT_TIP, add_tooltip
from er_save_manager.ui.utils import bind_mousewheel, game_blocks_write


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(
        parent, "darksoulsremastered.exe", "Dark Souls: Remastered"
    )


if TYPE_CHECKING:
    pass


def _backup_and_save(dsr_save, save_path: Path, operation: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=operation, save=None)
    dsr_save.save_to_file(save_path)


_NOT_VISITED = (
    "This bonfire's map has not been visited yet. The game only stores a "
    "bonfire's state once the character has entered its map, so there is no "
    "record to light. Visit the area once in game, then it can be lit here."
)


class DSRWorldStateTab:
    def __init__(
        self, parent, get_dsr_save, get_save_path, show_toast, register_pending=None
    ) -> None:
        self._register_pending = register_pending
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = -1
        self._bonfires = json.loads(
            (Path(__file__).parent / "data" / "bonfires.json").read_text(
                encoding="utf-8"
            )
        )

    def setup_ui(self) -> None:
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(header, text="World State", font=("Inter", 16, "bold")).pack(
            side="left"
        )

        scroll = ctk.CTkScrollableFrame(outer, corner_radius=10)
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        bind_mousewheel(scroll)

        # --- Bonfires section ---
        bonfire_card = ctk.CTkFrame(scroll, corner_radius=10)
        bonfire_card.pack(fill="x", padx=4, pady=(6, 4))

        ctk.CTkLabel(bonfire_card, text="Bonfires", font=("Inter", 12, "bold")).pack(
            anchor="w", padx=14, pady=(12, 4)
        )

        ctk.CTkLabel(
            bonfire_card,
            text=(
                "Lit bonfires are warp destinations once warping is unlocked. "
                "Bonfires in maps not visited yet cannot be lit here. "
                "Double-click toggles."
            ),
            wraplength=680,
            justify="left",
            font=("Inter", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=14, pady=(0, 6))
        tree_frame, self._bonfire_tree = ds.themed_tree(
            bonfire_card,
            columns=("name", "state"),
            show="headings",
            height=12,
            selectmode="extended",
        )
        tree_frame.pack(fill="x", padx=14, pady=(0, 6))
        add_tooltip(self._bonfire_tree, MULTI_SELECT_TIP)
        self._bonfire_tree.heading("name", text="Bonfire")
        self._bonfire_tree.heading("state", text="State")
        self._bonfire_tree.column("name", width=360, anchor="w")
        self._bonfire_tree.column("state", width=110, anchor="center", stretch=False)
        for i, bonfire in enumerate(self._bonfires):
            self._bonfire_tree.insert(
                "", "end", iid=str(i), values=(bonfire["name"], "--")
            )
        self._bonfire_tree.bind("<Double-1>", self._on_bonfire_double_click)
        actions = ctk.CTkFrame(bonfire_card, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(0, 12))
        for text, rows, lit in (
            ("Light Selected", None, True),
            ("Unlight Selected", None, False),
            ("Light All Visited", "all", True),
        ):
            ctk.CTkButton(
                actions,
                text=text,
                width=140,
                command=lambda r=rows, v=lit: self._set_bonfires(
                    list(range(len(self._bonfires)))
                    if r == "all"
                    else [int(i) for i in self._bonfire_tree.selection()],
                    v,
                ),
            ).pack(side="left", padx=(0, 6))

        # --- NG+ section ---
        ng_card = ctk.CTkFrame(scroll, corner_radius=10)
        ng_card.pack(fill="x", padx=4, pady=4)

        ctk.CTkLabel(
            ng_card, text="New Game+ counter", font=("Inter", 12, "bold")
        ).pack(anchor="w", padx=14, pady=(12, 4))

        ng_row = ctk.CTkFrame(ng_card, fg_color="transparent")
        ng_row.pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkLabel(ng_row, text="Current:").pack(side="left", padx=(0, 6))
        self._ng_current_var = tk.StringVar(value="--")
        ctk.CTkLabel(
            ng_row,
            textvariable=self._ng_current_var,
            font=("Inter", 11, "bold"),
        ).pack(side="left", padx=(0, 20))
        ctk.CTkLabel(ng_row, text="Set to:").pack(side="left", padx=(0, 6))
        self._ng_var = ctk.StringVar(value="0")
        self._ng_tracker = FieldTracker(var_state({"ng": self._ng_var}), {"ng": "NG+"})
        ctk.CTkComboBox(
            ng_row,
            variable=self._ng_var,
            values=[str(i) for i in range(8)],
            state="readonly",
            width=80,
        ).pack(side="left", padx=(0, 10))
        if self._register_pending is not None:
            self._register_pending(
                PendingPage(
                    "New Game+",
                    self._ng_tracker.changes,
                    self._prepare_ng,
                    lambda: self.load_slot(self._current_slot),
                    details=self._ng_tracker.details,
                )
            )

        ctk.CTkLabel(
            ng_card,
            text="0 = NG, 1 = NG+, 2 = NG++, etc.",
            font=("Inter", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=14, pady=(0, 12))

    # --- Refresh -------------------------------------------------------------- #

    def refresh(self) -> None:
        self.load_slot(self._current_slot)

    def load_slot(self, slot_idx: int) -> None:
        """Show the character in slot_idx; -1 or an empty slot clears the tab."""
        save = self._get_dsr_save()
        if save is None or not (
            0 <= slot_idx < len(save.characters) and save.characters[slot_idx]
        ):
            slot_idx = -1
        self._current_slot = slot_idx
        self._ng_tracker.clear()
        self._refresh_display()

    # --- Internal helpers ----------------------------------------------------- #

    def _refresh_display(self) -> None:
        save = self._get_dsr_save()
        char = (
            save.characters[self._current_slot]
            if save and self._current_slot >= 0
            else None
        )
        for i, bonfire in enumerate(self._bonfires):
            level = None if char is None else char.bonfire_level(bonfire["entity"])
            state = (
                "--"
                if char is None
                else "Not visited"
                if level is None
                else "Unlit"
                if level == 0
                else "Lit"
                if level <= 10
                else f"Kindled {level}"
            )
            self._bonfire_tree.set(str(i), "state", state)
        if char is None:
            self._ng_current_var.set("--")
            self._ng_tracker.clear()
            return
        self._ng_current_var.set(f"NG+{char.ng_plus}")
        # Bonfire writes refresh the tab; an unapplied NG+ choice stays.
        if not self._ng_tracker.changes():
            self._ng_var.set(str(char.ng_plus))
            self._ng_tracker.mark_clean()

    def _on_bonfire_double_click(self, event) -> None:
        row = self._bonfire_tree.identify_row(event.y)
        if not row:
            return
        state = self._bonfire_tree.set(row, "state")
        if state == "Not visited":
            CTkMessageBox.showinfo(
                "Bonfire Not Visited", _NOT_VISITED, parent=self.parent
            )
        elif state != "--":
            self._set_bonfires([int(row)], state == "Unlit")

    def _set_bonfires(self, rows: list[int], lit: bool) -> None:
        if not rows:
            CTkMessageBox.showwarning(
                "No Selection", "Select one or more bonfires first.", parent=self.parent
            )
            return
        if _game_blocks_write(self.parent):
            return
        save = self._get_dsr_save()
        save_path = self._get_save_path()
        char = (
            save.characters[self._current_slot]
            if save and self._current_slot >= 0
            else None
        )
        if char is None or save_path is None:
            CTkMessageBox.showwarning(
                "No Save", "No character loaded.", parent=self.parent
            )
            return
        changed = [
            i
            for i in rows
            if char.bonfire_level(self._bonfires[i]["entity"]) is not None
            and bool(char.bonfire_level(self._bonfires[i]["entity"])) != lit
        ]
        unvisited = sum(
            1 for i in rows if char.bonfire_level(self._bonfires[i]["entity"]) is None
        )
        for i in changed:
            char.set_bonfire_lit(self._bonfires[i]["entity"], lit)
        if not changed:
            if unvisited:
                CTkMessageBox.showinfo(
                    "Bonfire Not Visited", _NOT_VISITED, parent=self.parent
                )
            else:
                self._show_toast("Nothing to change, already set.")
            return
        try:
            _backup_and_save(save, save_path, f"bonfires_slot_{self._current_slot + 1}")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)
            return
        self._refresh_display()
        skipped = (
            f" {unvisited} in maps not visited yet were skipped." if unvisited else ""
        )
        self._show_toast(
            f"{len(changed)} bonfire(s) {'lit' if lit else 'unlit'}. Backup created."
            + skipped
        )

    def _prepare_ng(self):
        save = self._get_dsr_save()
        if save is None or self._current_slot < 0:
            raise StageError("No character loaded.")
        char = save.characters[self._current_slot]
        if char is None:
            raise StageError("No character loaded.")
        ng = int(self._ng_var.get())

        def commit() -> None:
            char.ng_plus = ng

        return commit
