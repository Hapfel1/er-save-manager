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
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.tooltip import MULTI_SELECT_TIP, add_tooltip
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
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(header, text="NPCs & Bosses", font=("Inter", 16, "bold")).pack(
            side="left"
        )
        ctk.CTkButton(
            header, text="Quest Progress", width=130, command=self._open_quests
        ).pack(side="right")

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
        ctk.CTkLabel(panel, text=title, font=("Inter", 12, "bold")).pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        ctk.CTkLabel(
            panel,
            text=hint + " Double-click toggles.",
            font=("Inter", 10),
            text_color=_HINT,
            wraplength=420,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 6))
        row = ctk.CTkFrame(panel, fg_color="transparent")
        # Packed before the list so a short window shrinks the list, not this.
        row.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        cols = [*columns, ("state", "State", 80, "center")]
        frame, tree = ds.themed_tree(
            panel,
            columns=[c[0] for c in cols],
            show="headings",
            height=8,
            selectmode="extended",
        )
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        for col, text, width, anchor in cols:
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor=anchor, stretch=col == "name")
        for col, (text, kill) in enumerate(actions):
            row.grid_columnconfigure(col, weight=1, uniform="a")
            ctk.CTkButton(
                row,
                text=text,
                command=lambda t=tree, k=kill: self._apply(t, setter, k),
            ).grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 4, 0))
        tree.bind("<Double-1>", lambda e, t=tree: self._toggle(t, e, setter))
        add_tooltip(tree, MULTI_SELECT_TIP)
        return tree

    # --- Refresh ----------------------------------------------------------- #

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

    def _open_quests(self) -> None:
        from er_save_manager.data.quest_flags_db import load_quest_table
        from er_save_manager.ui.quest_progress_dialog import QuestProgressDialog

        save = self._get_dsr_save()
        save_path = self._get_save_path()
        char = self._char()
        if char is None or save_path is None:
            CTkMessageBox.showwarning(
                "No Character", "Load a character first.", parent=self.parent
            )
            return
        if _game_blocks_write(self.parent):
            return
        slot = self._current_slot

        def commit(_description: str) -> None:
            _backup_and_save(save, save_path, f"quest_progress_slot_{slot + 1}")
            self._update_states()

        QuestProgressDialog.open(
            self.parent,
            char,
            save,
            save_path,
            slot,
            None,
            self._show_toast,
            quest_flags=load_quest_table(_DATA_DIR / "quest_steps.json"),
            commit=commit,
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
