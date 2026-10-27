"""
DS2 boss panel: shows each boss's state, repairs invalid records and returns
defeated bosses to their arenas.
"""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from er_save_manager.games.DS2.bonfire_database import BONFIRES
from er_save_manager.games.DS2.save import (
    BOSS_MAX_DEFEATS,
    BossState,
    BossStatus,
    DS2Save,
    SlotState,
)
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import save_writable, write_failed
from er_save_manager.ui.tooltip import MULTI_SELECT_TIP, add_tooltip
from er_save_manager.ui.utils import game_blocks_write
from er_save_manager.validation.numbers import parse_whole


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(parent, "darksoulsii.exe", "Dark Souls II")


def _slot_locked(parent, save: DS2Save, slot: int) -> bool:
    """Show why the slot cannot be edited and return True, if it cannot."""
    reason = save.slot_lock_reason(slot)
    if reason:
        CTkMessageBox.showerror("Slot Locked", reason, parent=parent)
    return reason is not None


def _state_text(state: BossState) -> str:
    if state.status is BossStatus.INVALID:
        return f"Invalid: {state.problem}"
    return state.status.value


class DS2BossPanel:
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
        ctk.CTkLabel(header, text="Bosses", font=("Inter", 13, "bold")).pack(
            side="left"
        )
        self._summary_label = ctk.CTkLabel(header, text="")
        self._summary_label.pack(side="left", padx=(12, 0))

        buttons = ctk.CTkFrame(self.parent, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", padx=10, pady=(6, 10))
        self._repair_button = ctk.CTkButton(
            buttons, text="Repair Selected", command=self._on_repair, height=32
        )
        self._repair_button.pack(side="left", fill="x", expand=True, padx=(0, 3))
        self._repair_all_button = ctk.CTkButton(
            buttons,
            text="Repair All Invalid",
            command=self._on_repair_all,
            height=32,
        )
        self._repair_all_button.pack(side="left", fill="x", expand=True, padx=3)
        self._respawn_button = ctk.CTkButton(
            buttons, text="Respawn Selected", command=self._on_respawn, height=32
        )
        self._respawn_button.pack(side="left", fill="x", expand=True, padx=3)
        self._kill_button = ctk.CTkButton(
            buttons, text="Kill Selected", command=self._on_kill, height=32
        )
        self._kill_button.pack(side="left", fill="x", expand=True, padx=(3, 0))

        defeats_row = ctk.CTkFrame(self.parent, fg_color="transparent")
        defeats_row.pack(side="bottom", fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(defeats_row, text="Defeats:").pack(side="left", padx=(0, 4))
        self._defeats_var = ctk.StringVar(value="1")
        self._defeats_var.trace_add("write", lambda *_: self._update_buttons())
        ctk.CTkEntry(defeats_row, textvariable=self._defeats_var, width=70).pack(
            side="left"
        )
        self._set_defeats_button = ctk.CTkButton(
            defeats_row,
            text="Set Defeats",
            command=self._on_set_defeats,
            width=110,
        )
        self._set_defeats_button.pack(side="left", padx=6)

        ctk.CTkLabel(
            self.parent,
            text=(
                "Repair completes the records of a partly credited kill, for "
                "example one made in another player's world, so the boss counts "
                "as defeated and its bonfire accepts Bonfire Ascetics. It also "
                "brings back fight enemies that stay missing while their boss is "
                "alive, which leaves health on the boss bar after everything is "
                "dead. Respawn "
                "puts a defeated boss back in its arena like a Bonfire Ascetic, "
                "without raising the bonfire's intensity. Kill records a win and "
                "removes the boss from its arena, without souls, drops or other "
                "rewards. Set Defeats changes the "
                f"kill counter (1 to {BOSS_MAX_DEFEATS}) and marks the boss as "
                "defeated without removing it from its arena."
            ),
            text_color=("gray40", "gray60"),
            font=("Inter", 11),
            wraplength=900,
            justify="left",
        ).pack(side="bottom", anchor="w", padx=10)

        box, self._tree = ds.themed_tree(
            self.parent,
            columns=("name", "state", "defeats", "bonfire"),
            show="headings",
            height=8,
            selectmode="extended",
        )
        self._tree.heading("name", text="Boss")
        self._tree.heading("state", text="State")
        self._tree.heading("defeats", text="Defeats")
        self._tree.heading("bonfire", text="Ascetic Bonfire")
        self._tree.column("name", width=260)
        self._tree.column("state", width=300)
        self._tree.column("defeats", width=70, anchor="center")
        self._tree.column("bonfire", width=200)
        box.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        add_tooltip(self._tree, MULTI_SELECT_TIP)
        self._tree.bind("<<TreeviewSelect>>", lambda _e: self._update_buttons())

        self._states: list[BossState] = []
        self._has_character = False
        self.refresh()

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        save: DS2Save | None = self.get_save()
        bosses = save.bosses(self.get_slot_index()) if save is not None else None

        self._states = []
        if bosses is None:
            self._summary_label.configure(text="No boss data in this slot")
            self._has_character = False
            self._update_buttons()
            return

        self._states = bosses.states()
        for state in self._states:
            self._tree.insert(
                "",
                "end",
                values=(
                    state.name,
                    _state_text(state),
                    state.defeats,
                    BONFIRES.get(state.fight.bonfire_id, ""),
                ),
            )
        defeated = sum(1 for s in self._states if s.defeats)
        invalid = sum(1 for s in self._states if s.status is BossStatus.INVALID)
        summary = f"{defeated} of {len(self._states)} defeated"
        if invalid:
            summary += f", {invalid} invalid"
        self._summary_label.configure(text=summary)

        slot = self.get_slot_index()
        self._has_character = (
            save.slot_state(slot) is SlotState.CHARACTER
            and save.slot_lock_reason(slot) is None
        )
        self._update_buttons()

    def _selected(self) -> list[BossState]:
        return [self._states[self._tree.index(row)] for row in self._tree.selection()]

    def _update_buttons(self) -> None:
        """Enable each button only when it would change something."""
        picked = self._selected()
        can_repair = any(s.status is BossStatus.INVALID for s in picked)
        any_invalid = any(s.status is BossStatus.INVALID for s in self._states)
        can_respawn = any(s.gone_from_arena for s in picked)
        defeats = self._defeats_value()
        can_set_defeats = defeats is not None and any(
            s.defeats != defeats or s.status is BossStatus.INVALID for s in picked
        )
        for button, enabled in (
            (self._repair_button, can_repair),
            (self._repair_all_button, any_invalid),
            (self._respawn_button, can_respawn),
            (self._kill_button, any(not s.gone_from_arena for s in picked)),
            (self._set_defeats_button, can_set_defeats),
        ):
            button.configure(
                state="normal" if enabled and self._has_character else "disabled"
            )

    def _defeats_value(self) -> int | None:
        """The entered defeat count, or None when it is not a valid count."""
        try:
            value = parse_whole(self._defeats_var.get())
        except ValueError:
            return None
        return value if 1 <= value <= BOSS_MAX_DEFEATS else None

    def _apply(self, title: str, message: str, operation: str, mutate) -> None:
        """Confirm, then run mutate(bosses) to change boss data, back up and
        write. mutate returns how many bosses it changed."""
        if _game_blocks_write(self.parent):
            return

        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return
        if _slot_locked(self.parent, save, self.get_slot_index()):
            return
        bosses = save.bosses(self.get_slot_index())
        if bosses is None:
            self.show_toast("No boss data in this slot", duration=2000)
            return
        if not CTkMessageBox.askyesno(title, message, parent=self.parent):
            return
        if not save_writable():
            return

        changed = mutate(bosses)
        save_path = self.get_save_path()
        if save_path:
            try:
                self._backup(save_path, f"before_{operation}", operation)
                save.save_to_file(save_path)
            except Exception as exc:
                write_failed(exc, self.parent)
                return
        self.refresh()
        self.show_toast(f"Changed {changed} bosses", duration=2500)

    def _repair(self, states: list[BossState]) -> None:
        row_ids = [s.fight.row_id for s in states]
        self._apply(
            "Repair Bosses",
            f"Repair {len(row_ids)} bosses?\n\n"
            "A boss with a partly recorded win is recorded as defeated. A boss "
            "still in its arena stays there, and enemies of its fight marked "
            "killed spawn again. A backup is made first.",
            "repair_bosses",
            lambda bosses: bosses.repair(row_ids),
        )

    def _on_repair(self) -> None:
        self._repair([s for s in self._selected() if s.status is BossStatus.INVALID])

    def _on_repair_all(self) -> None:
        self._repair([s for s in self._states if s.status is BossStatus.INVALID])

    def _on_kill(self) -> None:
        row_ids = [s.fight.row_id for s in self._selected() if not s.gone_from_arena]
        self._apply(
            "Kill Bosses",
            f"Kill {len(row_ids)} selected bosses?\n\nEach is recorded as defeated "
            "and removed from its arena. No souls, boss soul or other drops are "
            "given. A backup is made first.",
            "kill_bosses",
            lambda bosses: bosses.kill(row_ids),
        )

    def _on_respawn(self) -> None:
        row_ids = [s.fight.row_id for s in self._selected() if s.gone_from_arena]
        self._apply(
            "Respawn Bosses",
            f"Respawn {len(row_ids)} selected bosses?\n\n"
            "Their defeat counts are kept. A backup is made first.",
            "respawn_bosses",
            lambda bosses: bosses.respawn(row_ids),
        )

    def _on_set_defeats(self) -> None:
        defeats = self._defeats_value()
        if defeats is None:
            return
        row_ids = [s.fight.row_id for s in self._selected()]
        self._apply(
            "Set Defeats",
            f"Set the defeat count of {len(row_ids)} selected bosses to "
            f"{defeats}?\n\nEach is recorded as defeated. A boss still in its "
            "arena stays there. A backup is made first.",
            "set_boss_defeats",
            lambda bosses: bosses.set_defeats(row_ids, defeats),
        )

    def _backup(self, save_path, description: str, operation: str) -> None:
        """Raises when the backup fails, so the write does not go ahead."""
        from er_save_manager.backup.manager import BackupManager

        try:
            BackupManager(Path(save_path)).create_backup(
                description=description, operation=operation
            )
        except Exception as exc:
            raise RuntimeError(f"Backup failed: {exc}") from exc
