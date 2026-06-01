"""
DS3 World State tab - bonfire unlock and NG+ editing.

Each bonfire has a specific byte (or 2-byte) unlock value stored at a fixed
offset relative to event_flag_start - 0x12. Both individual and bulk unlock
are supported since the DS3 bit-to-bonfire mapping is documented via the
reference editor offsets.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

_DATA_DIR = Path(__file__).parent.parent / "data"
_BONFIRES: list[dict] | None = None


def _load_bonfires() -> list[dict]:
    global _BONFIRES
    if _BONFIRES is None:
        _BONFIRES = json.loads(
            (_DATA_DIR / "bonfires.json").read_text(encoding="utf-8")
        )
    return _BONFIRES


def _backup_and_save(ds3_save, save_path: Path, op: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=op, save=None)
    ds3_save.save_to_file(save_path)


class DS3WorldStateTab:
    def __init__(self, parent, get_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_save = get_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = 0
        self._bonfire_badges: list[tuple[dict, ctk.CTkLabel]] = []

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
            header, variable=self._slot_var, values=[], state="readonly", width=240
        )
        self._slot_combo.pack(side="right")
        ctk.CTkLabel(header, text="Slot:").pack(side="right", padx=(0, 6))

        scroll = ctk.CTkScrollableFrame(outer, corner_radius=10)
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        bind_mousewheel(scroll)
        self._scroll = scroll

        # NG+ section
        ng_card = ctk.CTkFrame(scroll, corner_radius=10)
        ng_card.pack(fill="x", padx=4, pady=(6, 4))
        ctk.CTkLabel(ng_card, text="New Game+", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=14, pady=(12, 4)
        )
        ng_row = ctk.CTkFrame(ng_card, fg_color="transparent")
        ng_row.pack(fill="x", padx=14, pady=(0, 4))
        ctk.CTkLabel(ng_row, text="Current:").pack(side="left", padx=(0, 6))
        self._ng_current_var = tk.StringVar(value="--")
        ctk.CTkLabel(
            ng_row, textvariable=self._ng_current_var, font=("Segoe UI", 11, "bold")
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
            text="0 = NG,  1 = NG+,  2 = NG++  etc.",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=14, pady=(0, 12))

        # Bonfires section
        bf_card = ctk.CTkFrame(scroll, corner_radius=10)
        bf_card.pack(fill="x", padx=4, pady=4)
        ctk.CTkLabel(bf_card, text="Bonfires", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=14, pady=(12, 4)
        )
        bulk_row = ctk.CTkFrame(bf_card, fg_color="transparent")
        bulk_row.pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkButton(
            bulk_row,
            text="Unlock All Bonfires",
            width=180,
            command=self._unlock_all_bonfires,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            bulk_row,
            text="Lock All Bonfires",
            width=150,
            fg_color=("gray55", "gray35"),
            command=self._lock_all_bonfires,
        ).pack(side="left")

        self._bonfire_list = ctk.CTkFrame(bf_card, fg_color="transparent")
        self._bonfire_list.pack(fill="x", padx=14, pady=(0, 12))

    # --- Refresh ------------------------------------------------------------- #

    def refresh(self) -> None:
        save = self._get_save()
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
        self._rebuild_bonfire_rows()
        self._refresh_ng()

    def load_slot(self, slot_idx: int) -> None:
        options = self._slot_combo.cget("values")
        if options and slot_idx < len(options):
            self._slot_var.set(options[slot_idx])
        self._current_slot = slot_idx
        self._rebuild_bonfire_rows()
        self._refresh_ng()

    # --- NG+ ----------------------------------------------------------------- #

    def _refresh_ng(self) -> None:
        save = self._get_save()
        char = save.characters[self._current_slot] if save else None
        if char is None:
            self._ng_current_var.set("--")
            return
        self._ng_current_var.set(f"NG+{char.ng_plus}")

    def _apply_ng(self) -> None:
        save, save_path, char = self._get_char()
        if char is None:
            return
        try:
            char.ng_plus = int(self._ng_var.get())
        except Exception as exc:
            CTkMessageBox.showerror("Error", str(exc), parent=self.parent)
            return
        try:
            _backup_and_save(
                save, save_path, f"ds3_set_ng_slot_{self._current_slot + 1}"
            )
            self._refresh_ng()
            self._show_toast(f"NG+ set to {self._ng_var.get()}. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    # --- Bonfires ------------------------------------------------------------ #

    def _rebuild_bonfire_rows(self) -> None:
        for w in self._bonfire_list.winfo_children():
            w.destroy()
        self._bonfire_badges.clear()

        save = self._get_save()
        char = save.characters[self._current_slot] if save else None
        if char is None:
            return

        for bf in _load_bonfires():
            unlock_val = int(bf["unlock_value"], 16)
            unlocked = char.get_bonfire_unlocked(bf["offset"], unlock_val)
            self._add_bonfire_row(bf, unlock_val, unlocked)

    def _add_bonfire_row(self, bf: dict, unlock_val: int, unlocked: bool) -> None:
        row = ctk.CTkFrame(
            self._bonfire_list, fg_color=("#f5f5f5", "#2a2a3e"), corner_radius=6
        )
        row.pack(fill="x", pady=2)
        row.grid_columnconfigure(1, weight=1)

        badge_color = ("#2a6e2a", "#1e7e1e") if unlocked else ("gray55", "gray45")
        badge = ctk.CTkLabel(
            row,
            text="ON" if unlocked else "OFF",
            fg_color=badge_color,
            corner_radius=4,
            width=40,
            font=("Segoe UI", 9, "bold"),
        )
        badge.grid(row=0, column=0, padx=(8, 6), pady=6)
        ctk.CTkLabel(
            row,
            text=bf["name"],
            anchor="w",
            font=("Segoe UI", 11),
        ).grid(row=0, column=1, sticky="w", padx=4)
        ctk.CTkButton(
            row,
            text="Unlock",
            width=70,
            command=lambda b=bf, uv=unlock_val, bg=badge: self._set_bonfire(
                b, uv, True, bg
            ),
        ).grid(row=0, column=2, padx=4, pady=6)
        ctk.CTkButton(
            row,
            text="Lock",
            width=60,
            fg_color=("gray55", "gray35"),
            command=lambda b=bf, uv=unlock_val, bg=badge: self._set_bonfire(
                b, uv, False, bg
            ),
        ).grid(row=0, column=3, padx=(0, 8), pady=6)

        self._bonfire_badges.append((bf, badge))

    def _set_bonfire(
        self, bf: dict, unlock_val: int, unlocked: bool, badge: ctk.CTkLabel
    ) -> None:
        save, save_path, char = self._get_char()
        if char is None:
            return
        char.set_bonfire_unlocked(bf["offset"], unlock_val, unlocked)
        try:
            action = "unlock" if unlocked else "lock"
            _backup_and_save(
                save,
                save_path,
                f"ds3_bonfire_{action}_slot_{self._current_slot + 1}",
            )
            badge_color = ("#2a6e2a", "#1e7e1e") if unlocked else ("gray55", "gray45")
            badge.configure(text="ON" if unlocked else "OFF", fg_color=badge_color)
            self._show_toast(
                f"{bf['name']} {'unlocked' if unlocked else 'locked'}. Backup created."
            )
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _unlock_all_bonfires(self) -> None:
        save, save_path, char = self._get_char()
        if char is None:
            return
        for bf in _load_bonfires():
            unlock_val = int(bf["unlock_value"], 16)
            char.set_bonfire_unlocked(bf["offset"], unlock_val, True)
        try:
            _backup_and_save(
                save,
                save_path,
                f"ds3_unlock_all_bonfires_slot_{self._current_slot + 1}",
            )
            self._rebuild_bonfire_rows()
            self._show_toast("All bonfires unlocked. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _lock_all_bonfires(self) -> None:
        save, save_path, char = self._get_char()
        if char is None:
            return
        for bf in _load_bonfires():
            unlock_val = int(bf["unlock_value"], 16)
            char.set_bonfire_unlocked(bf["offset"], unlock_val, False)
        try:
            _backup_and_save(
                save, save_path, f"ds3_lock_all_bonfires_slot_{self._current_slot + 1}"
            )
            self._rebuild_bonfire_rows()
            self._show_toast("All bonfires locked. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    # --- Helpers ------------------------------------------------------------- #

    def _load_selected(self) -> None:
        save = self._get_save()
        if save is None:
            return
        idx = self._slot_idx()
        if idx < 0 or save.characters[idx] is None:
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {idx + 1} is empty.", parent=self.parent
            )
            return
        self._current_slot = idx
        self._rebuild_bonfire_rows()
        self._refresh_ng()

    def _get_char(self):
        save = self._get_save()
        save_path = self._get_save_path()
        if save is None or save_path is None:
            CTkMessageBox.showwarning(
                "No Save", "No DS3 save loaded.", parent=self.parent
            )
            return None, None, None
        char = save.characters[self._current_slot]
        if char is None:
            CTkMessageBox.showwarning(
                "Empty Slot", "No character in this slot.", parent=self.parent
            )
            return None, None, None
        return save, save_path, char

    def _slot_idx(self) -> int:
        val = self._slot_var.get()
        if not val:
            return -1
        try:
            return int(val.split(" - ")[0].replace("Slot", "").strip()) - 1
        except (ValueError, IndexError):
            return -1
