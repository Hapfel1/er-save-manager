"""
DSR NPCs & Bosses tab.

Bosses: the global defeat flags in dsr_named_flags.json (boss_kills). They
are per playthrough, so bosses read as alive again after starting NG+.

NPCs: data/npcs.json lists each NPC's state range and its dead and hostile
flags, taken from the game's NPC death and hostility events. Kill and revive
do what those events do: clear the range, then set the dead flag or the
first state (alive). Quest progress outside the range is left alone.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import game_blocks_write


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(
        parent, "darksoulsremastered.exe", "Dark Souls: Remastered"
    )


_DATA_DIR = Path(__file__).parent / "data"
_HINT = ("gray40", "gray60")


def _load_bosses() -> list[dict]:
    bosses = json.loads(
        (_DATA_DIR / "dsr_named_flags.json").read_text(encoding="utf-8")
    )["boss_kills"]
    return [b for b in bosses if b.get("accessible", True)]


def _load_npcs() -> list[dict]:
    return json.loads((_DATA_DIR / "npcs.json").read_text(encoding="utf-8"))


def _backup_and_save(dsr_save, save_path: Path, op: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=op, save=None)
    dsr_save.save_to_file(save_path)


def _style() -> None:
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "DSR.Treeview",
        background="#2b2b2b",
        foreground="white",
        fieldbackground="#2b2b2b",
        rowheight=22,
        borderwidth=0,
    )
    style.configure("DSR.Treeview.Heading", background="#3b3b3b", foreground="white")
    style.map("DSR.Treeview", background=[("selected", "#5a4a7a")])


class DSRNPCTab:
    def __init__(self, parent, get_dsr_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = 0
        self._bosses = _load_bosses()
        self._npcs = _load_npcs()

    # --- Layout ------------------------------------------------------------ #

    def setup_ui(self) -> None:
        _style()
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(header, text="NPCs & Bosses", font=("Segoe UI", 16, "bold")).pack(
            side="left"
        )
        ctk.CTkButton(header, text="Load", command=self._load_selected, width=70).pack(
            side="right", padx=(6, 0)
        )
        self._slot_var = ctk.StringVar()
        self._slot_combo = ctk.CTkComboBox(
            header, variable=self._slot_var, values=[], state="readonly", width=220
        )
        self._slot_combo.pack(side="right")
        ctk.CTkLabel(header, text="Slot:").pack(side="right", padx=(0, 6))

        body = ctk.CTkFrame(outer, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        body.grid_columnconfigure((0, 1), weight=1)
        body.grid_rowconfigure(0, weight=1)

        self._boss_tree = self._panel(
            body,
            0,
            "Bosses",
            "Defeat flags are per playthrough; NG+ starts them alive again.",
            [("name", "Boss", 200, "w"), ("area", "Area", 170, "w")],
            (("Respawn Selected", False), ("Kill Selected", True)),
            self._set_bosses,
        )
        for i, boss in enumerate(self._bosses):
            self._boss_tree.insert(
                "", "end", iid=str(i), values=(boss["name"], boss.get("area", ""), "--")
            )

        self._npc_tree = self._panel(
            body,
            1,
            "NPCs",
            "Kill or revive. Quest progress outside the NPC's state is kept.",
            [("name", "NPC", 260, "w")],
            (("Revive Selected", False), ("Kill Selected", True)),
            self._set_npcs,
        )
        for i, npc in enumerate(self._npcs):
            self._npc_tree.insert("", "end", iid=str(i), values=(npc["name"], "--"))

    def _panel(self, parent, column, title, hint, columns, actions, setter):
        panel = ctk.CTkFrame(parent, corner_radius=10)
        panel.grid(
            row=0, column=column, sticky="nsew", padx=(0, 5) if column == 0 else (5, 0)
        )
        ctk.CTkLabel(panel, text=title, font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        ctk.CTkLabel(
            panel,
            text=hint + " Ctrl/Shift click selects several, double-click toggles.",
            font=("Segoe UI", 10),
            text_color=_HINT,
            wraplength=420,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 6))
        row = ctk.CTkFrame(panel, fg_color="transparent")
        # Packed before the list so a short window shrinks the list, not this.
        row.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        frame = tk.Frame(panel, bg="#2b2b2b")
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        cols = [*columns, ("state", "State", 80, "center")]
        tree = ttk.Treeview(
            frame,
            columns=[c[0] for c in cols],
            show="headings",
            style="DSR.Treeview",
            height=8,
            selectmode="extended",
        )
        for col, text, width, anchor in cols:
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor=anchor, stretch=col == "name")
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for col, (text, kill) in enumerate(actions):
            row.grid_columnconfigure(col, weight=1, uniform="a")
            ctk.CTkButton(
                row,
                text=text,
                command=lambda t=tree, k=kill: self._apply(t, setter, k),
            ).grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 4, 0))
        tree.bind("<Double-1>", lambda e, t=tree: self._toggle(t, e, setter))
        return tree

    # --- Refresh ----------------------------------------------------------- #

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
        if not (
            0 <= self._current_slot < len(options)
            and save.characters[self._current_slot]
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
        save = self._get_dsr_save()
        if save is None or not 0 <= self._current_slot < len(save.characters):
            return None
        return save.characters[self._current_slot]

    def _update_states(self) -> None:
        char = self._char()
        try:
            for i, boss in enumerate(self._bosses):
                state = (
                    "--"
                    if char is None
                    else ("Killed" if char.get_flag(boss["id"]) else "Alive")
                )
                self._boss_tree.set(str(i), "state", state)
            for i, npc in enumerate(self._npcs):
                self._npc_tree.set(
                    str(i), "state", "--" if char is None else char.npc_state(npc)
                )
        except ValueError:
            for tree in (self._boss_tree, self._npc_tree):
                for iid in tree.get_children():
                    tree.set(iid, "state", "--")

    # --- Writes ------------------------------------------------------------ #

    def _toggle(self, tree, event, setter) -> None:
        row = tree.identify_row(event.y)
        if not row:
            return
        state = tree.set(row, "state")
        if state in ("Alive", "Killed", "Dead", "Hostile"):
            setter([int(row)], state == "Alive")

    def _apply(self, tree, setter, kill: bool) -> None:
        rows = [int(i) for i in tree.selection()]
        if not rows:
            CTkMessageBox.showwarning(
                "No Selection", "Select one or more entries first.", parent=self.parent
            )
            return
        setter(rows, kill)

    def _set_bosses(self, rows: list[int], killed: bool) -> None:
        self._write(
            lambda char: [char.set_flag(self._bosses[i]["id"], killed) for i in rows],
            "bosses_killed" if killed else "bosses_respawned",
            self._bosses[rows[0]]["name"] if len(rows) == 1 else f"{len(rows)} bosses",
            "killed" if killed else "respawned",
        )

    def _set_npcs(self, rows: list[int], killed: bool) -> None:
        self._write(
            lambda char: [char.set_npc_state(self._npcs[i], not killed) for i in rows],
            "npcs_killed" if killed else "npcs_revived",
            self._npcs[rows[0]]["name"] if len(rows) == 1 else f"{len(rows)} NPCs",
            "killed" if killed else "revived",
        )

    def _write(self, change, op: str, what: str, verb: str) -> None:
        if _game_blocks_write(self.parent):
            return
        save = self._get_dsr_save()
        save_path = self._get_save_path()
        char = self._char()
        if char is None or save_path is None:
            CTkMessageBox.showwarning(
                "No Character", "Load a character first.", parent=self.parent
            )
            return
        try:
            change(char)
        except ValueError as exc:
            CTkMessageBox.showerror("Unavailable", str(exc), parent=self.parent)
            return
        try:
            _backup_and_save(save, save_path, f"{op}_slot_{self._current_slot + 1}")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)
            return
        self._update_states()
        self._show_toast(f"{what} {verb}. Backup created.")

    def _load_selected(self) -> None:
        save = self._get_dsr_save()
        if save is None:
            return
        try:
            idx = int(self._slot_var.get().split(" - ")[0].replace("Slot", "")) - 1
        except (ValueError, IndexError):
            return
        if save.characters[idx] is None:
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {idx + 1} is empty.", parent=self.parent
            )
            return
        self._current_slot = idx
        self._update_states()
