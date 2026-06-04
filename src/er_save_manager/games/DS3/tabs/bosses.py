"""
DS3 Bosses tab - boss defeat state editing.

Boss state is stored as a specific byte value at a fixed offset relative to
event_flag_start - 0x12. The 'defeat_value' from bosses.json is the byte
that must be present for the boss to be considered defeated.
"""

from __future__ import annotations

import json
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

_DATA_DIR = Path(__file__).parent.parent / "data"
_BOSSES: list[dict] | None = None


def _load_bosses() -> list[dict]:
    global _BOSSES
    if _BOSSES is None:
        _BOSSES = json.loads((_DATA_DIR / "bosses.json").read_text(encoding="utf-8"))
    return _BOSSES


def _backup_and_save(ds3_save, save_path: Path, op: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=op, save=None)
    ds3_save.save_to_file(save_path)


class DS3BossesTab:
    def __init__(self, parent, get_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_save = get_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = 0
        self._row_widgets: list[tuple[dict, ctk.CTkLabel]] = []

    def setup_ui(self) -> None:
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(header, text="Bosses", font=("Segoe UI", 16, "bold")).pack(
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

        bulk = ctk.CTkFrame(outer, fg_color="transparent")
        bulk.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkButton(
            bulk,
            text="Kill All Bosses",
            width=130,
            fg_color=("gray55", "gray35"),
            command=lambda: self._bulk(True),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            bulk,
            text="Respawn All Bosses",
            width=160,
            command=lambda: self._bulk(False),
        ).pack(side="left")

        self._scroll = ctk.CTkScrollableFrame(outer, corner_radius=10)
        self._scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        bind_mousewheel(self._scroll)

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
        self._rebuild_rows()

    def load_slot(self, slot_idx: int) -> None:
        options = self._slot_combo.cget("values")
        if options and slot_idx < len(options):
            self._slot_var.set(options[slot_idx])
        self._current_slot = slot_idx
        self._rebuild_rows()

    # --- Row building -------------------------------------------------------- #

    def _rebuild_rows(self) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()
        self._row_widgets.clear()

        save = self._get_save()
        char = save.characters[self._current_slot] if save else None
        if char is None:
            ctk.CTkLabel(
                self._scroll,
                text="Empty slot or no save loaded.",
                text_color=("gray50", "gray60"),
            ).pack(anchor="w", padx=6, pady=40)
            return

        for boss in _load_bosses():
            defeat_val = int(boss["defeat_value"], 16)
            defeated = char.get_boss_defeated(boss["offset"], defeat_val)
            self._add_boss_row(char, boss, defeat_val, defeated)

    def _add_boss_row(self, char, boss: dict, defeat_val: int, defeated: bool) -> None:
        row = ctk.CTkFrame(
            self._scroll, fg_color=("#f5f5f5", "#2a2a3e"), corner_radius=6
        )
        row.pack(fill="x", padx=4, pady=3)
        row.grid_columnconfigure(1, weight=1)

        badge_color = ("gray55", "gray45") if defeated else ("#2a6e2a", "#1e7e1e")
        badge_text = "KILLED" if defeated else "ALIVE"
        badge = ctk.CTkLabel(
            row,
            text=badge_text,
            fg_color=badge_color,
            corner_radius=4,
            width=58,
            font=("Segoe UI", 9, "bold"),
        )
        badge.grid(row=0, column=0, padx=(8, 6), pady=6)

        ctk.CTkLabel(
            row,
            text=boss["name"],
            anchor="w",
            font=("Segoe UI", 11),
            text_color=("#333333", "#cccccc"),
        ).grid(row=0, column=1, sticky="w", padx=4, pady=(6, 2))
        ctk.CTkLabel(
            row,
            text=boss["area"],
            anchor="w",
            font=("Segoe UI", 9),
            text_color=("gray50", "gray60"),
        ).grid(row=1, column=1, sticky="w", padx=4, pady=(0, 4))

        ctk.CTkButton(
            row,
            text="Kill",
            width=65,
            fg_color=("gray55", "gray35"),
            command=lambda b=boss, dv=defeat_val, bg=badge: self._set_boss(
                b, dv, True, bg
            ),
        ).grid(row=0, column=2, rowspan=2, padx=4, pady=6)
        ctk.CTkButton(
            row,
            text="Respawn",
            width=80,
            fg_color=("#2a5a9a", "#1e4a8a"),
            command=lambda b=boss, dv=defeat_val, bg=badge: self._set_boss(
                b, dv, False, bg
            ),
        ).grid(row=0, column=3, rowspan=2, padx=(0, 8), pady=6)

        self._row_widgets.append((boss, badge))

    # --- Toggle -------------------------------------------------------------- #

    def _set_boss(
        self, boss: dict, defeat_val: int, defeated: bool, badge: ctk.CTkLabel
    ) -> None:
        save, save_path, char = self._get_char()
        if char is None:
            return
        char.set_boss_defeated(boss["offset"], defeat_val, defeated)
        try:
            action = "kill" if defeated else "respawn"
            _backup_and_save(
                save,
                save_path,
                f"ds3_boss_{action}_{boss['name'].split()[0].lower()}_slot_{self._current_slot + 1}",
            )
            badge_color = ("gray55", "gray45") if defeated else ("#2a6e2a", "#1e7e1e")
            badge.configure(
                text="KILLED" if defeated else "ALIVE", fg_color=badge_color
            )
            self._show_toast(
                f"{boss['name']} {'killed' if defeated else 'respawned'}. Backup created."
            )
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _bulk(self, defeated: bool) -> None:
        save, save_path, char = self._get_char()
        if char is None:
            return
        if not CTkMessageBox.askyesno(
            "Confirm",
            f"{'Kill' if defeated else 'Respawn'} all bosses in Slot {self._current_slot + 1}?",
            parent=self.parent,
        ):
            return
        for boss in _load_bosses():
            defeat_val = int(boss["defeat_value"], 16)
            char.set_boss_defeated(boss["offset"], defeat_val, defeated)
        try:
            action = "kill_all" if defeated else "respawn_all"
            _backup_and_save(
                save, save_path, f"ds3_bosses_{action}_slot_{self._current_slot + 1}"
            )
            self._rebuild_rows()
            self._show_toast(
                f"All bosses {'killed' if defeated else 'respawned'}. Backup created."
            )
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
        self._rebuild_rows()

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
