"""
DS3 Bosses tab - boss defeat state editing.

Each boss has a "dead" event flag (the one the game's boss scripts check),
and the main-story bosses also have a "Defeated X" progression flag that
Firelink Shrine and NPC scripts read. Kill sets both, Respawn clears both;
no other flag in the block is touched. Flag ids come from bosses.json,
generated from the game's event scripts.
"""

from __future__ import annotations

import json
from pathlib import Path

import customtkinter as ctk

from er_save_manager.games.DS3.tabs.style import make_tree
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import game_blocks_write


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(parent, "darksoulsiii.exe", "Dark Souls III")


_DATA_DIR = Path(__file__).parent.parent / "data"


def _backup_and_save(ds3_save, save_path: Path, op: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=op, save=None)
    ds3_save.save_to_file(save_path)


def _set_boss(char, boss: dict, defeated: bool) -> None:
    char.set_flag(boss["dead_flag"], defeated)
    if boss.get("progress_flag"):
        char.set_flag(boss["progress_flag"], defeated)


class DS3BossesTab:
    def __init__(self, parent, get_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_save = get_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = 0
        self._bosses = json.loads(
            (_DATA_DIR / "bosses.json").read_text(encoding="utf-8")
        )

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

        actions = ctk.CTkFrame(outer, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(0, 6))
        for text, command, primary in (
            ("Kill Selected", lambda: self._apply(True, selected=True), False),
            ("Respawn Selected", lambda: self._apply(False, selected=True), True),
            ("Kill All", lambda: self._apply(True, selected=False), False),
            ("Respawn All", lambda: self._apply(False, selected=False), True),
        ):
            ctk.CTkButton(
                actions,
                text=text,
                width=130,
                command=command,
                fg_color=None if primary else ("gray55", "gray35"),
            ).pack(side="left", padx=(0, 8))
        self._status = ctk.CTkLabel(
            actions, text="", font=("Segoe UI", 10), text_color=("gray40", "gray60")
        )
        self._status.pack(side="left", padx=8)

        frame, self._tree = make_tree(
            outer,
            [
                ("name", "Boss", 300, "w"),
                ("area", "Area", 280, "w"),
                ("state", "State", 90, "center"),
            ],
        )
        for i, boss in enumerate(self._bosses):
            area = boss["area"] + (" (DLC)" if boss.get("dlc") else "")
            self._tree.insert("", "end", iid=str(i), values=(boss["name"], area, "--"))
        self._tree.bind("<Double-1>", self._on_double_click)
        ctk.CTkLabel(
            outer,
            text="Select one or more bosses (Ctrl/Shift click). Double-click toggles a boss.",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray60"),
        ).pack(side="bottom", anchor="w", padx=12, pady=(0, 10))
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))

    # --- Refresh ----------------------------------------------------------- #

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
        if (
            not (0 <= self._current_slot < len(options))
            or save.characters[self._current_slot] is None
        ):
            self._current_slot = next(
                (i for i, c in enumerate(save.characters) if c is not None), 0
            )
        self._slot_var.set(options[self._current_slot] if options else "")
        self._update_states()

    def load_slot(self, slot_idx: int) -> None:
        options = self._slot_combo.cget("values")
        if options and slot_idx < len(options):
            self._slot_var.set(options[slot_idx])
        self._current_slot = slot_idx
        self._update_states()

    def _char(self):
        save = self._get_save()
        return save.characters[self._current_slot] if save else None

    def _update_states(self) -> None:
        char = self._char()
        error = char.flags_error if char is not None else "no character loaded"
        self._status.configure(text=f"Unavailable: {error}" if error else "")
        for i, boss in enumerate(self._bosses):
            if error:
                state = "--"
            else:
                state = "Killed" if char.get_flag(boss["dead_flag"]) else "Alive"
            self._tree.set(str(i), "state", state)

    # --- Writes ------------------------------------------------------------ #

    def _on_double_click(self, event) -> None:
        row = self._tree.identify_row(event.y)
        char = self._char()
        if not row or char is None or char.flags_error:
            return
        boss = self._bosses[int(row)]
        self._write([boss], not char.get_flag(boss["dead_flag"]))

    def _apply(self, defeated: bool, selected: bool) -> None:
        if selected:
            bosses = [self._bosses[int(i)] for i in self._tree.selection()]
            if not bosses:
                CTkMessageBox.showwarning(
                    "No Selection",
                    "Select one or more bosses first.",
                    parent=self.parent,
                )
                return
        else:
            bosses = self._bosses
            if not CTkMessageBox.askyesno(
                "Confirm",
                f"{'Kill' if defeated else 'Respawn'} all bosses in Slot "
                f"{self._current_slot + 1}?",
                parent=self.parent,
            ):
                return
        self._write(bosses, defeated)

    def _write(self, bosses: list[dict], defeated: bool) -> None:
        if _game_blocks_write(self.parent):
            return
        save, save_path, char = self._get_char()
        if char is None:
            return
        for boss in bosses:
            _set_boss(char, boss, defeated)
        action = "kill" if defeated else "respawn"
        try:
            _backup_and_save(
                save, save_path, f"ds3_boss_{action}_slot_{self._current_slot + 1}"
            )
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)
            return
        self._update_states()
        what = bosses[0]["name"] if len(bosses) == 1 else f"{len(bosses)} bosses"
        self._show_toast(
            f"{what} {'killed' if defeated else 'respawned'}. Backup created."
        )

    # --- Helpers ----------------------------------------------------------- #

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
        self._update_states()

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
        if char.flags_error:
            CTkMessageBox.showerror(
                "Unavailable",
                f"Event flags cannot be edited for this character: {char.flags_error}",
                parent=self.parent,
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
