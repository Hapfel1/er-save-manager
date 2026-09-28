"""
DS2 NPC panel: shows which NPCs are hostile or dead and can revive or calm them.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import ttk

import customtkinter as ctk

from er_save_manager.games.DS2.save import DS2Save, NpcState, SlotState
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import game_blocks_write


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(parent, "darksoulsii.exe", "Dark Souls II")


def _state_text(state: NpcState) -> str:
    if state.dead:
        return "Dead"
    return "Hostile" if state.hostile else "Alive"


class DS2NpcPanel:
    """
    Args:
        parent: parent widget the panel is built into.
        get_save: callable returning the current DS2Save, or None if unloaded.
        get_slot_index: callable returning the currently selected slot index.
        get_save_path: callable returning the current save file path.
        show_toast: callable(message, duration) for transient status messages.
    """

    def __init__(
        self, parent, get_save, get_slot_index, get_save_path, show_toast
    ) -> None:
        self.parent = parent
        self.get_save = get_save
        self.get_slot_index = get_slot_index
        self.get_save_path = get_save_path
        self.show_toast = show_toast

    def setup_ui(self) -> None:
        header = ctk.CTkFrame(self.parent, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(header, text="NPCs", font=("Segoe UI", 13, "bold")).pack(
            side="left"
        )
        self._summary_label = ctk.CTkLabel(header, text="")
        self._summary_label.pack(side="left", padx=(12, 0))

        buttons = ctk.CTkFrame(self.parent, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", padx=10, pady=(6, 10))
        self._revive_button = ctk.CTkButton(
            buttons, text="Revive Selected", command=self._on_revive, height=32
        )
        self._revive_button.pack(side="left", fill="x", expand=True, padx=(0, 3))
        self._calm_button = ctk.CTkButton(
            buttons, text="Calm Selected", command=self._on_calm, height=32
        )
        self._calm_button.pack(side="left", fill="x", expand=True, padx=3)
        self._record_button = ctk.CTkButton(
            buttons,
            text="Clear Kill Record",
            command=self._on_clear_record,
            height=32,
        )
        self._record_button.pack(side="left", fill="x", expand=True, padx=(3, 0))

        ctk.CTkLabel(
            self.parent,
            text=(
                "Revive clears the dead and hostile flags and the kill record. "
                "Calm clears the hostile flag only. A kill leaves a record that "
                "keeps an NPC dead even with his flags cleared. Ctrl or "
                "Shift+click selects several."
            ),
            text_color=("gray40", "gray60"),
            font=("Segoe UI", 11),
        ).pack(side="bottom", anchor="w", padx=10)

        self._tree = ttk.Treeview(
            self.parent,
            columns=("name", "state"),
            show="headings",
            height=8,
            selectmode="extended",
        )
        self._tree.heading("name", text="NPC")
        self._tree.heading("state", text="State")
        self._tree.column("name", width=300)
        self._tree.column("state", width=110)
        self._tree.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._tree.bind("<<TreeviewSelect>>", lambda _e: self._update_buttons())

        self._states: list[NpcState] = []
        self._record_present = False
        self._has_character = False
        self.refresh()

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        save: DS2Save | None = self.get_save()
        npcs = save.npcs(self.get_slot_index()) if save is not None else None

        self._states = []
        self._record_present = False
        if npcs is None:
            self._summary_label.configure(text="No NPC data in this slot")
            self._update_buttons()
            return

        self._states = npcs.states()
        for state in self._states:
            self._tree.insert("", "end", values=(state.entry.name, _state_text(state)))
        self._record_present = npcs.kill_record_present
        gone = sum(1 for s in self._states if s.dead or s.hostile)
        text = f"{gone} hostile or dead"
        if self._record_present:
            text += ", kill record present"
        self._summary_label.configure(text=text)

        self._has_character = (
            save.slot_state(self.get_slot_index()) is SlotState.CHARACTER
        )
        self._update_buttons()

    def _selected(self) -> list[NpcState]:
        return [self._states[self._tree.index(row)] for row in self._tree.selection()]

    def _update_buttons(self) -> None:
        """Enable each button only when it would change something."""
        picked = self._selected()
        can_revive = any(s.dead or s.hostile for s in picked)
        can_calm = any(s.hostile for s in picked)
        for button, enabled in (
            (self._revive_button, can_revive),
            (self._calm_button, can_calm),
            (self._record_button, self._record_present),
        ):
            button.configure(
                state="normal" if enabled and self._has_character else "disabled"
            )

    def _apply(self, title: str, message: str, operation: str, mutate) -> None:
        """Confirm, then run mutate(npcs) to change NPC data, back up and write.
        mutate returns how many NPCs it changed."""
        if _game_blocks_write(self.parent):
            return

        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return
        npcs = save.npcs(self.get_slot_index())
        if npcs is None:
            self.show_toast("No NPC data in this slot", duration=2000)
            return
        if not CTkMessageBox.askyesno(title, message, parent=self.parent):
            return

        changed = mutate(npcs)
        save_path = self.get_save_path()
        if save_path:
            self._backup(save_path, f"before_{operation}", operation)
            try:
                save.save_to_file(save_path)
            except Exception as e:
                self.show_toast(f"Failed to write save: {e}", duration=3000)
                return
        self.refresh()
        self.show_toast(f"Changed {changed} NPCs", duration=2500)

    def _on_revive(self) -> None:
        names = [s.entry.name for s in self._selected() if s.dead or s.hostile]
        self._apply(
            "Revive NPCs",
            f"Revive {len(names)} selected NPCs?\n\n"
            "This also clears the kill record. A backup is made first.",
            "revive_npcs",
            lambda npcs: npcs.revive(names),
        )

    def _on_calm(self) -> None:
        names = [s.entry.name for s in self._selected() if s.hostile]
        self._apply(
            "Calm NPCs",
            f"Calm {len(names)} selected NPCs?\n\nA backup is made first.",
            "calm_npcs",
            lambda npcs: npcs.calm(names),
        )

    def _on_clear_record(self) -> None:
        def clear(npcs) -> int:
            npcs.clear_kill_record()
            return 0

        self._apply(
            "Clear kill record",
            "Clear the kill record in this slot?\n\n"
            "An NPC killed earlier whose flags were already cleared should come "
            "back. A backup is made first.",
            "clear_kill_record",
            clear,
        )

    def _backup(self, save_path, description: str, operation: str) -> None:
        try:
            from er_save_manager.backup.manager import BackupManager

            BackupManager(Path(save_path)).create_backup(
                description=description, operation=operation
            )
        except Exception:
            pass
