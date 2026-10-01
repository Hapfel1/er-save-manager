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
from tkinter import ttk
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.games.DSR.npc_tab import _style as _apply_tree_style
from er_save_manager.ui.messagebox import CTkMessageBox
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


class DSRWorldStateTab:
    def __init__(self, parent, get_dsr_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = 0
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

        ctk.CTkLabel(header, text="World State", font=("Segoe UI", 16, "bold")).pack(
            side="left"
        )
        ctk.CTkButton(header, text="Load", command=self._load_selected, width=70).pack(
            side="right", padx=(6, 0)
        )
        self._slot_var = ctk.StringVar()
        self._slot_combo = ctk.CTkComboBox(
            header,
            variable=self._slot_var,
            values=[],
            state="readonly",
            width=220,
        )
        self._slot_combo.pack(side="right")
        ctk.CTkLabel(header, text="Slot:").pack(side="right", padx=(0, 6))

        scroll = ctk.CTkScrollableFrame(outer, corner_radius=10)
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        bind_mousewheel(scroll)

        # --- Bonfires section ---
        bonfire_card = ctk.CTkFrame(scroll, corner_radius=10)
        bonfire_card.pack(fill="x", padx=4, pady=(6, 4))

        ctk.CTkLabel(bonfire_card, text="Bonfires", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=14, pady=(12, 4)
        )

        ctk.CTkLabel(
            bonfire_card,
            text=(
                "Lit bonfires are warp destinations once warping is unlocked. "
                "Bonfires in maps not visited yet cannot be lit here. "
                "Ctrl/Shift click selects several, double-click toggles."
            ),
            wraplength=680,
            justify="left",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=14, pady=(0, 6))
        _apply_tree_style()
        tree_frame = tk.Frame(bonfire_card, bg="#2b2b2b")
        tree_frame.pack(fill="x", padx=14, pady=(0, 6))
        self._bonfire_tree = ttk.Treeview(
            tree_frame,
            columns=("name", "state"),
            show="headings",
            style="DSR.Treeview",
            height=12,
            selectmode="extended",
        )
        self._bonfire_tree.heading("name", text="Bonfire")
        self._bonfire_tree.heading("state", text="State")
        self._bonfire_tree.column("name", width=360, anchor="w")
        self._bonfire_tree.column("state", width=110, anchor="center", stretch=False)
        sb = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self._bonfire_tree.yview
        )
        self._bonfire_tree.configure(yscrollcommand=sb.set)
        self._bonfire_tree.pack(side="left", fill="x", expand=True)
        sb.pack(side="right", fill="y")
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
            ng_card, text="New Game+ Counter", font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=14, pady=(12, 4))

        ng_row = ctk.CTkFrame(ng_card, fg_color="transparent")
        ng_row.pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkLabel(ng_row, text="Current:").pack(side="left", padx=(0, 6))
        self._ng_current_var = tk.StringVar(value="--")
        ctk.CTkLabel(
            ng_row,
            textvariable=self._ng_current_var,
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left", padx=(0, 20))
        ctk.CTkLabel(ng_row, text="Set to:").pack(side="left", padx=(0, 6))
        self._ng_var = ctk.StringVar(value="0")
        ctk.CTkComboBox(
            ng_row,
            variable=self._ng_var,
            values=[str(i) for i in range(8)],
            state="readonly",
            width=80,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(ng_row, text="Apply", command=self._apply_ng, width=80).pack(
            side="left"
        )

        ctk.CTkLabel(
            ng_card,
            text="0 = NG, 1 = NG+, 2 = NG++, etc.",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=14, pady=(0, 12))

    # --- Refresh -------------------------------------------------------------- #

    def refresh(self) -> None:
        save = self._get_dsr_save()
        if save is None:
            self._slot_combo.configure(values=[])
            return
        options = [
            f"Slot {i + 1} - {c.name}" if c else f"Slot {i + 1} - Empty"
            for i, c in enumerate(save.characters)
        ]
        self._slot_combo.configure(values=options)
        self._slot_var.set(options[0] if options else "")
        self._current_slot = 0
        self._refresh_display()

    def load_slot(self, slot_idx: int) -> None:
        options = self._slot_combo.cget("values")
        if options and slot_idx < len(options):
            self._slot_var.set(options[slot_idx])
        self._current_slot = slot_idx
        self._refresh_display()

    # --- Internal helpers ----------------------------------------------------- #

    def _load_selected(self) -> None:
        save = self._get_dsr_save()
        if save is None:
            CTkMessageBox.showwarning(
                "No Save", "No DSR save loaded.", parent=self.parent
            )
            return
        idx = self._slot_idx()
        if idx < 0:
            return
        if save.characters[idx] is None:
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {idx + 1} is empty.", parent=self.parent
            )
            return
        self._current_slot = idx
        self._refresh_display()

    def _refresh_display(self) -> None:
        save = self._get_dsr_save()
        char = save.characters[self._current_slot] if save else None
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
            return
        self._ng_current_var.set(f"NG+{char.ng_plus}")

    def _on_bonfire_double_click(self, event) -> None:
        row = self._bonfire_tree.identify_row(event.y)
        if not row:
            return
        state = self._bonfire_tree.set(row, "state")
        if state not in ("--", "Not visited"):
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
        char = save.characters[self._current_slot] if save else None
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
        for i in changed:
            char.set_bonfire_lit(self._bonfires[i]["entity"], lit)
        if not changed:
            self._show_toast("Nothing to change (already set or map not visited).")
            return
        try:
            _backup_and_save(save, save_path, f"bonfires_slot_{self._current_slot + 1}")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)
            return
        self._refresh_display()
        self._show_toast(
            f"{len(changed)} bonfire(s) {'lit' if lit else 'unlit'}. Backup created."
        )

    def _apply_ng(self) -> None:
        if _game_blocks_write(self.parent):
            return

        save = self._get_dsr_save()
        save_path = self._get_save_path()
        if save is None or save_path is None or self._current_slot < 0:
            CTkMessageBox.showwarning(
                "No Save", "No character loaded.", parent=self.parent
            )
            return
        char = save.characters[self._current_slot]
        if char is None:
            return
        try:
            char.ng_plus = int(self._ng_var.get())
        except Exception as exc:
            CTkMessageBox.showerror("Error", str(exc), parent=self.parent)
            return
        try:
            _backup_and_save(save, save_path, f"set_ng_slot_{self._current_slot + 1}")
            self._refresh_display()
            self._show_toast(f"NG+ set to {self._ng_var.get()}. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _slot_idx(self) -> int:
        val = self._slot_var.get()
        if not val:
            return -1
        try:
            return int(val.split(" - ")[0].replace("Slot", "").strip()) - 1
        except (ValueError, IndexError):
            return -1
