"""
DS3 NPCs tab - revive or kill NPCs.

Every NPC has a five-flag state range (npcs.json alive_flag to last_flag)
driven by the game's common NPC events (common_func 20006000-20006002):
  alive_flag      alive and friendly
  alive_flag + 1  hostile
  alive_flag + 2  hostile (the variant some NPCs use when provoked)
  dead_flag       dead (alive_flag + 3)
The events clear the whole range before setting one flag, so exactly one is
on at a time. Revive and Kill do the same; quest progress flags outside the
range are left alone, except for an NPC whose own events read its quest
state for alive/dead (npcs.json quest = [lo, hi, alive state, dead state]):
Revive and Kill set that range the way the game's revive and kill events do.

A killed NPC also has its death bit set in the map's character state
(npcs.json chr_bits, see DS3Slot.character_dead). The game spawns it dead
from that bit and its death event sets the dead flag again, so Revive clears
the bits too. Kill leaves them: the dead flag alone makes the events remove
the NPC.
"""

from __future__ import annotations

import json
from pathlib import Path

import customtkinter as ctk

from er_save_manager.games.DS3.slot import LayoutError
from er_save_manager.games.DS3.tabs.style import make_tree
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import game_blocks_write


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(parent, "darksoulsiii.exe", "Dark Souls III")


_DATA_DIR = Path(__file__).parent.parent / "data"

# Offsets of the two hostile states from alive_flag.
_HOSTILE_OFFSETS = (1, 2)


def _backup_and_save(ds3_save, save_path: Path, op: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=op, save=None)
    ds3_save.save_to_file(save_path)


def _npc_state(char, npc: dict) -> str:
    if char.get_flag(npc["dead_flag"]):
        return "Dead"
    if any(char.get_flag(npc["alive_flag"] + off) for off in _HOSTILE_OFFSETS):
        return "Hostile"
    if char.get_flag(npc["alive_flag"]):
        return "Alive"
    # Nothing set yet: the NPC's area has not been loaded on this character.
    return "Not met"


def _clear_death_bits(char, npc: dict) -> None:
    for part in npc.get("chr_bits", []):
        char.set_character_dead(part["map"], part["bit"], False)


def _set_state(char, npc: dict, revive: bool) -> None:
    flag = npc["alive_flag"] if revive else npc["dead_flag"]
    for f in range(npc["alive_flag"], npc["last_flag"] + 1):
        char.set_flag(f, f == flag)
    if "quest" in npc:
        lo, hi, alive, dead = npc["quest"]
        state = alive if revive else dead
        for f in range(lo, hi + 1):
            char.set_flag(f, f == state)


class DS3NpcsTab:
    def __init__(self, parent, get_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_save = get_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = 0
        self._npcs = json.loads((_DATA_DIR / "npcs.json").read_text(encoding="utf-8"))

    def setup_ui(self) -> None:
        outer = ctk.CTkFrame(self.parent, fg_color="transparent")
        outer.pack(fill="both", expand=True)

        ctk.CTkLabel(
            outer,
            text=(
                "Revive makes a dead or hostile NPC alive and friendly again; "
                "Kill marks them dead. Quest progress is not changed, so an NPC "
                "whose questline already moved on stays where it left them."
            ),
            font=("Inter", 10),
            text_color=("gray40", "gray70"),
            wraplength=850,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 6))

        actions = ctk.CTkFrame(outer, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkButton(
            actions,
            text="Revive Selected",
            width=130,
            command=lambda: self._apply(True),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Kill Selected",
            width=130,
            fg_color=("gray55", "gray35"),
            command=lambda: self._apply(False),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Quest Progress",
            width=130,
            command=self._open_quests,
        ).pack(side="left", padx=(0, 8))
        self._status = ctk.CTkLabel(
            actions, text="", font=("Inter", 10), text_color=("gray40", "gray60")
        )
        self._status.pack(side="left", padx=8)

        frame, self._tree = make_tree(
            outer, [("name", "NPC", 360, "w"), ("state", "State", 100, "center")]
        )
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for i, npc in enumerate(self._npcs):
            self._tree.insert("", "end", iid=str(i), values=(npc["name"], "--"))

    # --- Refresh ----------------------------------------------------------- #

    def refresh(self) -> None:
        self.load_slot(self._current_slot)

    def load_slot(self, slot_idx: int) -> None:
        """Show the character in slot_idx; -1 or an empty slot clears the tab."""
        save = self._get_save()
        if save is None or not (
            0 <= slot_idx < len(save.characters) and save.characters[slot_idx]
        ):
            slot_idx = -1
        self._current_slot = slot_idx
        self._update_states()

    def _update_states(self) -> None:
        save = self._get_save()
        char = (
            save.characters[self._current_slot]
            if save and self._current_slot >= 0
            else None
        )
        error = char.flags_error if char is not None else "no character loaded"
        self._status.configure(text=f"Unavailable: {error}" if error else "")
        for i, npc in enumerate(self._npcs):
            self._tree.set(str(i), "state", "--" if error else _npc_state(char, npc))

    # --- Writes ------------------------------------------------------------ #

    def _open_quests(self) -> None:
        from er_save_manager.data.quest_flags_db import load_quest_table
        from er_save_manager.ui.quest_progress_dialog import QuestProgressDialog

        save = self._get_save()
        save_path = self._get_save_path()
        char = (
            save.characters[self._current_slot]
            if save and self._current_slot >= 0
            else None
        )
        if char is None or save_path is None:
            CTkMessageBox.showwarning(
                "No Character", "Load a character first.", parent=self.parent
            )
            return
        if char.flags_error:
            CTkMessageBox.showerror(
                "Unavailable",
                f"Event flags cannot be edited for this character: {char.flags_error}",
                parent=self.parent,
            )
            return
        if _game_blocks_write(self.parent):
            return
        slot = self._current_slot

        def commit(_description: str) -> None:
            _backup_and_save(save, save_path, f"ds3_quest_progress_slot_{slot + 1}")
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
            apply_steps_between=True,
            apply_all=False,
        )

    def _apply(self, revive: bool) -> None:
        npcs = [self._npcs[int(i)] for i in self._tree.selection()]
        if not npcs:
            CTkMessageBox.showwarning(
                "No Selection", "Select one or more NPCs first.", parent=self.parent
            )
            return
        if _game_blocks_write(self.parent):
            return
        save = self._get_save()
        save_path = self._get_save_path()
        char = (
            save.characters[self._current_slot]
            if save and self._current_slot >= 0
            else None
        )
        if char is None or save_path is None:
            CTkMessageBox.showwarning(
                "No Character", "Load a character first.", parent=self.parent
            )
            return
        if char.flags_error:
            CTkMessageBox.showerror(
                "Unavailable",
                f"Event flags cannot be edited for this character: {char.flags_error}",
                parent=self.parent,
            )
            return
        if revive:
            try:
                for npc in npcs:
                    _clear_death_bits(char, npc)
            except LayoutError as exc:
                # Every NPC reads the same block, so this fails on the first
                # one, before anything is written.
                CTkMessageBox.showerror("Unavailable", str(exc), parent=self.parent)
                return
        for npc in npcs:
            _set_state(char, npc, revive)
        verb = "revived" if revive else "killed"
        try:
            _backup_and_save(
                save, save_path, f"ds3_npc_{verb}_slot_{self._current_slot + 1}"
            )
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)
            return
        self._update_states()
        what = npcs[0]["name"] if len(npcs) == 1 else f"{len(npcs)} NPCs"
        self._show_toast(f"{what} {verb}. Backup created.")
