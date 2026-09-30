"""
DS3 World State tab - NG+, bonfires and gestures.

Bonfires: a bonfire is lit (and a warp target) when the event flag from its
BonfireWarpParam row is set; bonfires.json lists those flags by area. A
bonfire whose map has several world states has one flag per state, and all
of them are set together.
Gestures: the character's gesture list stores an unlocked bit per gesture
id; gestures.json names the ids from the game's gesture table.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.games.DS3.tabs.style import make_tree
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import game_blocks_write


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(parent, "darksoulsiii.exe", "Dark Souls III")


_DATA_DIR = Path(__file__).parent.parent / "data"
_NG_CHOICES = [str(i) for i in range(8)]
_HINT = ("gray40", "gray60")


def _load(name: str) -> list[dict]:
    return json.loads((_DATA_DIR / name).read_text(encoding="utf-8"))


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
        self._bonfires = _load("bonfires.json")
        self._gestures = sorted(_load("gestures.json"), key=lambda g: g["order"])

    # --- Layout ------------------------------------------------------------ #

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

        self._build_ng_row(outer)

        body = ctk.CTkFrame(outer, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)
        self._build_bonfires(body)
        self._build_gestures(body)

    def _build_ng_row(self, parent) -> None:
        row = ctk.CTkFrame(parent, corner_radius=10)
        row.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkLabel(row, text="New Game+", font=("Segoe UI", 12, "bold")).pack(
            side="left", padx=(14, 12), pady=10
        )
        ctk.CTkLabel(row, text="Current:").pack(side="left", padx=(0, 6))
        self._ng_current_var = tk.StringVar(value="--")
        ctk.CTkLabel(
            row, textvariable=self._ng_current_var, font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(0, 20))
        ctk.CTkLabel(row, text="Set to:").pack(side="left", padx=(0, 6))
        self._ng_var = ctk.StringVar(value="0")
        ctk.CTkComboBox(
            row, variable=self._ng_var, values=_NG_CHOICES, state="readonly", width=80
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(row, text="Apply", command=self._apply_ng, width=80).pack(
            side="left"
        )
        ctk.CTkLabel(
            row,
            text="0 = NG, 1 = NG+. The playthrough flags scripts check are kept in step.",
            font=("Segoe UI", 10),
            text_color=_HINT,
        ).pack(side="left", padx=14)

    def _panel(self, parent, column: int, title: str, hint: str) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(parent, corner_radius=10)
        panel.grid(
            row=0, column=column, sticky="nsew", padx=(0, 5) if column == 0 else (5, 0)
        )
        ctk.CTkLabel(panel, text=title, font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        ctk.CTkLabel(
            panel, text=hint, font=("Segoe UI", 10), text_color=_HINT, justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 6))
        return panel

    def _actions(self, panel, buttons) -> ctk.CTkLabel:
        row = ctk.CTkFrame(panel, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 10))
        for text, command in buttons:
            ctk.CTkButton(row, text=text, width=110, command=command).pack(
                side="left", padx=(0, 6)
            )
        status = ctk.CTkLabel(row, text="", font=("Segoe UI", 10), text_color=_HINT)
        status.pack(side="left", padx=6)
        return status

    def _build_bonfires(self, parent) -> None:
        panel = self._panel(
            parent,
            0,
            "Bonfires",
            "Lit bonfires are warp destinations once the Firelink Shrine "
            "bonfire is lit.\nDouble-click toggles a bonfire.",
        )
        frame, self._bonfire_tree = make_tree(
            panel, [("name", "Bonfire", 260, "w"), ("state", "State", 80, "center")]
        )
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        areas: dict[str, str] = {}
        for i, bonfire in enumerate(self._bonfires):
            area = bonfire["area"]
            if area not in areas:
                areas[area] = self._bonfire_tree.insert(
                    "",
                    "end",
                    iid=f"area{len(areas)}",
                    text="",
                    values=(area, ""),
                    open=True,
                )
            self._bonfire_tree.insert(
                areas[area], "end", iid=str(i), values=(bonfire["name"], "--")
            )
        self._bonfire_tree.bind(
            "<Double-1>",
            lambda e: self._toggle(self._bonfire_tree, e, self._set_bonfires),
        )
        self._bonfire_status = self._actions(
            panel,
            (
                (
                    "Light Selected",
                    lambda: self._set_bonfires(self._selected_bonfires(), True),
                ),
                (
                    "Unlight Selected",
                    lambda: self._set_bonfires(self._selected_bonfires(), False),
                ),
                (
                    "Light All",
                    lambda: self._set_bonfires(list(range(len(self._bonfires))), True),
                ),
            ),
        )

    def _build_gestures(self, parent) -> None:
        panel = self._panel(
            parent,
            1,
            "Gestures",
            "Unlocked gestures appear in the gesture menu.\nDouble-click toggles a gesture.",
        )
        frame, self._gesture_tree = make_tree(
            panel, [("name", "Gesture", 180, "w"), ("state", "State", 80, "center")]
        )
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        for i, gesture in enumerate(self._gestures):
            self._gesture_tree.insert(
                "", "end", iid=str(i), values=(gesture["name"], "--")
            )
        self._gesture_tree.bind(
            "<Double-1>",
            lambda e: self._toggle(self._gesture_tree, e, self._set_gestures),
        )
        self._gesture_status = self._actions(
            panel,
            (
                (
                    "Unlock Selected",
                    lambda: self._set_gestures(
                        self._selected(self._gesture_tree), True
                    ),
                ),
                (
                    "Lock Selected",
                    lambda: self._set_gestures(
                        self._selected(self._gesture_tree), False
                    ),
                ),
                (
                    "Unlock All",
                    lambda: self._set_gestures(list(range(len(self._gestures))), True),
                ),
            ),
        )

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
        layout_error = char.layout_error if char else "no character loaded"
        flags_error = char.flags_error if char else "no character loaded"

        self._ng_current_var.set("--" if layout_error else f"NG+{char.ng_plus}")
        if not layout_error:
            self._ng_var.set(str(char.ng_plus))

        self._bonfire_status.configure(
            text=f"Unavailable: {flags_error}" if flags_error else ""
        )
        for i, bonfire in enumerate(self._bonfires):
            lit = (
                None if flags_error else any(char.get_flag(f) for f in bonfire["flags"])
            )
            self._bonfire_tree.set(
                str(i), "state", "--" if lit is None else ("Lit" if lit else "Unlit")
            )

        self._gesture_status.configure(
            text=f"Unavailable: {layout_error}" if layout_error else ""
        )
        for i, gesture in enumerate(self._gestures):
            unlocked = None if layout_error else char.gesture_unlocked(gesture["id"])
            self._gesture_tree.set(
                str(i),
                "state",
                "--" if unlocked is None else ("Unlocked" if unlocked else "Locked"),
            )

    # --- Selection --------------------------------------------------------- #

    @staticmethod
    def _selected(tree) -> list[int]:
        return [int(i) for i in tree.selection() if i.isdigit()]

    def _selected_bonfires(self) -> list[int]:
        """Selected bonfire rows; selecting an area row selects its bonfires."""
        picked: set[int] = set()
        for iid in self._bonfire_tree.selection():
            if iid.isdigit():
                picked.add(int(iid))
            else:
                picked.update(int(c) for c in self._bonfire_tree.get_children(iid))
        return sorted(picked)

    def _toggle(self, tree, event, setter) -> None:
        row = tree.identify_row(event.y)
        if not row.isdigit():
            return
        state = tree.set(row, "state")
        if state == "--":
            return
        setter([int(row)], state in ("Unlit", "Locked"))

    # --- Writes ------------------------------------------------------------ #

    def _apply_ng(self) -> None:
        if _game_blocks_write(self.parent):
            return
        save, save_path, char = self._get_char()
        if char is None:
            return
        if char.layout_error:
            CTkMessageBox.showerror(
                "Unavailable",
                f"NG+ cannot be edited for this character: {char.layout_error}",
                parent=self.parent,
            )
            return
        char.ng_plus = int(self._ng_var.get())
        if self._save(save, save_path, "ds3_set_ng"):
            self._show_toast(f"NG+ set to {self._ng_var.get()}. Backup created.")

    def _set_bonfires(self, rows: list[int], lit: bool) -> None:
        if not rows:
            CTkMessageBox.showwarning(
                "No Selection", "Select one or more bonfires first.", parent=self.parent
            )
            return
        if _game_blocks_write(self.parent):
            return
        save, save_path, char = self._get_char()
        if char is None:
            return
        if char.flags_error:
            CTkMessageBox.showerror(
                "Unavailable",
                f"Event flags cannot be edited for this character: {char.flags_error}",
                parent=self.parent,
            )
            return
        for i in rows:
            for flag in self._bonfires[i]["flags"]:
                char.set_flag(flag, lit)
        if self._save(save, save_path, "ds3_bonfires"):
            self._show_toast(
                f"{len(rows)} bonfire(s) {'lit' if lit else 'unlit'}. Backup created."
            )

    def _set_gestures(self, rows: list[int], unlocked: bool) -> None:
        if not rows:
            CTkMessageBox.showwarning(
                "No Selection", "Select one or more gestures first.", parent=self.parent
            )
            return
        if _game_blocks_write(self.parent):
            return
        save, save_path, char = self._get_char()
        if char is None:
            return
        if char.layout_error:
            CTkMessageBox.showerror(
                "Unavailable",
                f"Gestures cannot be edited for this character: {char.layout_error}",
                parent=self.parent,
            )
            return
        for i in rows:
            char.set_gesture_unlocked(self._gestures[i]["id"], unlocked)
        if self._save(save, save_path, "ds3_gestures"):
            self._show_toast(
                f"{len(rows)} gesture(s) {'unlocked' if unlocked else 'locked'}. Backup created."
            )

    def _save(self, save, save_path, op: str) -> bool:
        try:
            _backup_and_save(save, save_path, f"{op}_slot_{self._current_slot + 1}")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)
            return False
        self._update_states()
        return True

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
        return save, save_path, char

    def _slot_idx(self) -> int:
        val = self._slot_var.get()
        if not val:
            return -1
        try:
            return int(val.split(" - ")[0].replace("Slot", "").strip()) - 1
        except (ValueError, IndexError):
            return -1
