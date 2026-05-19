"""
DSR World State Tab

Bonfire unlock and NG+ editing.
All writes immediately create a backup then save.

Note on individual bonfires:
The 3 bonfire bytes encode 20 warpable bonfires as bit flags, but no public documentation
maps which bit corresponds to which bonfire. The reference editor (ds1-save-editor) only
implements bulk unlock, and this tool follows the same approach.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

if TYPE_CHECKING:
    from er_save_manager.games.DSR.save import DSRSave


def _backup_and_save(dsr_save: DSRSave, save_path: Path, operation: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=operation, save=None)
    dsr_save.save_to_file(save_path)


class DSRWorldStateTab:
    """Bonfire unlock and NG+ editor. Matches ER editor visual style."""

    def __init__(
        self,
        parent,
        get_dsr_save: Callable[[], DSRSave | None],
        get_save_path: Callable[[], Path | None],
        show_toast: Callable[[str], None],
    ) -> None:
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = 0

    def setup_ui(self) -> None:
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self.parent, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))

        ctk.CTkLabel(header, text="World State", font=("Segoe UI", 16, "bold")).pack(
            side="left"
        )
        ctk.CTkFrame(header, fg_color="transparent").pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkLabel(header, text="Slot:").pack(side="left", padx=(0, 6))
        self._slot_var = ctk.StringVar()
        self._slot_combo = ctk.CTkComboBox(
            header,
            variable=self._slot_var,
            values=[],
            state="readonly",
            width=220,
        )
        self._slot_combo.pack(side="left", padx=(0, 8))
        ctk.CTkButton(header, text="Load", command=self._load_selected, width=70).pack(
            side="left", padx=4
        )

        # Content
        scroll = ctk.CTkScrollableFrame(self.parent, corner_radius=12)
        scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        scroll.grid_columnconfigure(0, weight=1)
        bind_mousewheel(scroll)

        # --- Bonfires card ---
        bonfire_card = ctk.CTkFrame(scroll, corner_radius=10)
        bonfire_card.pack(fill="x", padx=4, pady=(6, 4))
        bonfire_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            bonfire_card,
            text="Bonfires",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 4))

        # Status row
        status_row = ctk.CTkFrame(bonfire_card, fg_color="transparent")
        status_row.pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkLabel(status_row, text="Current state:").pack(side="left", padx=(0, 8))
        self._bonfire_status_var = tk.StringVar(value="--")
        ctk.CTkLabel(
            status_row,
            textvariable=self._bonfire_status_var,
            font=("Consolas", 11),
        ).pack(side="left")

        # Unlock button + status indicator
        unlock_row = ctk.CTkFrame(bonfire_card, fg_color="transparent")
        unlock_row.pack(fill="x", padx=14, pady=(0, 4))

        ctk.CTkButton(
            unlock_row,
            text="Unlock All Warpable Bonfires",
            command=self._unlock_bonfires,
            width=240,
        ).pack(side="left", padx=(0, 12))

        self._bonfire_unlocked_label = ctk.CTkLabel(
            unlock_row,
            text="",
            font=("Segoe UI", 11),
        )
        self._bonfire_unlocked_label.pack(side="left")

        # Info note
        ctk.CTkLabel(
            bonfire_card,
            text=(
                "Unlocks all 20 warpable bonfires (Firelink Shrine, Undead Parish, etc.).\n"
                "Individual bonfire control is not available - the bit-to-bonfire mapping is "
                "not publicly documented for DSR."
            ),
            wraplength=680,
            justify="left",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=14, pady=(0, 12))

        # --- NG+ card ---
        ng_card = ctk.CTkFrame(scroll, corner_radius=10)
        ng_card.pack(fill="x", padx=4, pady=4)

        ctk.CTkLabel(
            ng_card,
            text="New Game+ Counter",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 4))

        ng_row = ctk.CTkFrame(ng_card, fg_color="transparent")
        ng_row.pack(fill="x", padx=14, pady=(0, 12))

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
        ctk.CTkButton(
            ng_row,
            text="Apply",
            command=self._apply_ng,
            width=80,
        ).pack(side="left")

        ctk.CTkLabel(
            ng_card,
            text="0 = NG, 1 = NG+, 2 = NG++, etc. Takes effect on next load.",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=14, pady=(0, 12))

    # --- Refresh -------------------------------------------------------------- #

    def refresh(self) -> None:
        save = self._get_dsr_save()
        if save is None:
            self._slot_combo.configure(values=[])
            return
        options = []
        for i, char in enumerate(save.characters):
            label = f"Slot {i + 1} - {char.name}" if char else f"Slot {i + 1} - Empty"
            options.append(label)
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
        if char is None:
            self._bonfire_status_var.set("--")
            self._ng_current_var.set("--")
            return

        status = char.get_bonfire_status()
        if status:
            b1, b2, b3, warp = status
            self._bonfire_status_var.set(
                f"bytes [{b1:#04x}, {b2:#04x}, {b3:#04x}]  warp={warp:#04x}"
            )
            # Check if all-unlocked state
            if b1 == 0xF0 and b2 == 0xFF and b3 == 0xFF and warp == 0x22:
                self._bonfire_unlocked_label.configure(
                    text="All unlocked", text_color=("#2a8a2a", "#4caf50")
                )
            else:
                self._bonfire_unlocked_label.configure(
                    text="Not fully unlocked", text_color=("gray50", "gray60")
                )
        else:
            self._bonfire_status_var.set("(Pattern1 not found)")

        self._ng_current_var.set(f"NG+{char.ng_plus}")

    def _unlock_bonfires(self) -> None:
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
        char.unlock_all_bonfires()
        try:
            _backup_and_save(
                save, save_path, f"unlock_bonfires_slot_{self._current_slot + 1}"
            )
            self._refresh_display()
            self._show_toast("All bonfires unlocked. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _apply_ng(self) -> None:
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
