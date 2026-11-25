"""
DSR Event Flags sub-pages: doors, shortcuts and item pickups.
"""

from __future__ import annotations

import customtkinter as ctk

from er_save_manager.games.DSR.world_flags import (
    AREAS,
    DOORS,
    PICKUPS,
    SHORTCUTS,
    FlagState,
    flag_state,
    set_flags,
)
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import save_writable, write_failed
from er_save_manager.ui.tooltip import MULTI_SELECT_TIP, add_tooltip
from er_save_manager.ui.utils import game_blocks_write, patch_combo_scroll

_ALL_AREAS = "All areas"


def _counted(n: int, noun: str) -> str:
    return f"{n} {noun if n == 1 else noun + 's'}"


class _FlagPage:
    """Header with area filter and search, a multi-select list and a button
    row. Subclasses list their rows and write through _apply.

    Args:
        parent: frame the page is built into.
        get_char: callable returning (save, save_path, character), with None
            parts when nothing is loaded.
        backup_and_save: callable(save, save_path, operation) that backs up
            and writes the file.
        show_toast: callable(message) for status messages.
    """

    def __init__(self, parent, get_char, backup_and_save, show_toast) -> None:
        self.parent = parent
        self._get_char = get_char
        self._backup_and_save = backup_and_save
        self._show_toast = show_toast
        self._rows: list = []
        self._built = False

    def build(self) -> None:
        self._built = True
        for w in self.parent.winfo_children():
            w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 4))
        self._summary = ctk.CTkLabel(header, text="", font=ds.BOLD)
        self._summary.pack(side="left")

        self._area_var = ctk.StringVar(value=_ALL_AREAS)
        combo = ctk.CTkComboBox(
            header,
            values=[_ALL_AREAS, *AREAS.values()],
            variable=self._area_var,
            state="readonly",
            width=280,
            command=lambda _v: self.refresh(),
        )
        combo.pack(side="right")
        patch_combo_scroll(combo)
        ctk.CTkLabel(header, text="Area:").pack(side="right", padx=(12, 6))

        self._search_var = ctk.StringVar()
        ctk.CTkEntry(header, textvariable=self._search_var, width=200).pack(
            side="right"
        )
        ctk.CTkLabel(header, text="Search:").pack(side="right", padx=(0, 6))
        self._search_var.trace_add("write", lambda *_: self.refresh())

        buttons = ctk.CTkFrame(self.parent, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", padx=10, pady=(4, 10))
        self._buttons = self._make_buttons(buttons)
        ctk.CTkLabel(
            self.parent,
            text=self.note,
            text_color=("gray40", "gray60"),
            font=("Inter", 11),
            wraplength=900,
            justify="left",
        ).pack(side="bottom", anchor="w", padx=10)

        box, self._tree = ds.themed_tree(
            self.parent,
            columns=tuple(self.columns),
            show="headings",
            height=12,
            selectmode="extended",
        )
        for key, (heading, width) in self.columns.items():
            self._tree.heading(key, text=heading)
            self._tree.column(key, width=width)
        box.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        add_tooltip(self._tree, MULTI_SELECT_TIP)
        self._tree.bind("<<TreeviewSelect>>", lambda _e: self._update_buttons())

    def _button(self, row, text: str, command, first: bool = False):
        button = ctk.CTkButton(row, text=text, command=command, height=32)
        button.pack(side="left", fill="x", expand=True, padx=(0, 3) if first else 3)
        return button

    def _matches(self, area: str, text: str) -> bool:
        picked = self._area_var.get()
        if picked != _ALL_AREAS and area != picked:
            return False
        query = self._search_var.get().strip().lower()
        return not query or query in text.lower()

    def refresh(self) -> None:
        if not self._built:
            return
        tree = self._tree
        tree.delete(*tree.get_children())
        self._rows = []
        self._states: dict = {}
        _, _, char = self._get_char()
        if char is None:
            self._summary.configure(text="No character loaded")
            self._update_buttons()
            return
        done = 0
        entries = self.entries()
        for entry in entries:
            state = flag_state(char, entry.flags)
            self._states[entry] = state
            done += state is FlagState.SET
            if not self._matches(entry.area, self.search_text(entry)):
                continue
            self._rows.append(entry)
            tree.insert("", "end", values=self.values(entry, state))
        self._summary.configure(text=self.summary(done, len(entries)))
        self._update_buttons()

    def _selected(self) -> list:
        return [self._rows[self._tree.index(row)] for row in self._tree.selection()]

    def _enable(self, *pairs) -> None:
        _, _, char = self._get_char()
        for button, enabled in pairs:
            button.configure(
                state="normal" if enabled and char is not None else "disabled"
            )

    def _apply(self, title: str, message: str, operation: str, groups, value: bool):
        """Confirm, set or clear the flags of groups, back up and write."""
        if game_blocks_write(
            self.parent, "darksoulsremastered.exe", "Dark Souls: Remastered"
        ):
            return
        save, save_path, char = self._get_char()
        if char is None:
            return
        if not CTkMessageBox.askyesno(title, message, parent=self.parent):
            return
        if not save_writable():
            return
        changed = set_flags(char, groups, value)
        if changed:
            try:
                self._backup_and_save(save, save_path, operation)
            except Exception as exc:
                write_failed(exc, self.parent)
                return
        self.refresh()
        return changed


class DSRDoorsPage(_FlagPage):
    columns = {
        "area": ("Area", 230),
        "door": ("Door", 280),
        "key": ("Key", 260),
        "state": ("State", 100),
    }
    note = (
        "Opening a door sets every flag the game sets when it is unlocked; "
        "the key is not used up. Closing clears them. Partly open: some of "
        "the flags are set but not the one that holds the door open, for "
        "example a door that stays shut with no prompt after co-op. Close "
        "Selected brings the prompt back so the door can be unlocked in the "
        "game again; Open Selected sets the rest."
    )
    _STATE_TEXT = {
        FlagState.SET: "Open",
        FlagState.CLEAR: "Closed",
        FlagState.PARTLY: "Partly open",
    }

    def entries(self):
        return DOORS

    def search_text(self, entry) -> str:
        return f"{entry.label} {' '.join(entry.keys)}"

    def values(self, entry, state):
        return (
            entry.area,
            entry.label,
            " or ".join(entry.keys),
            self._STATE_TEXT[state],
        )

    def summary(self, done: int, total: int) -> str:
        return f"{done} of {total} doors open"

    def _make_buttons(self, row):
        self._open = self._button(row, "Open Selected", lambda: self._set(True), True)
        self._close = self._button(row, "Close Selected", lambda: self._set(False))
        return (self._open, self._close)

    def _update_buttons(self) -> None:
        picked = self._selected()
        states = getattr(self, "_states", {})
        self._enable(
            (self._open, any(states.get(d) is not FlagState.SET for d in picked)),
            (self._close, any(states.get(d) is not FlagState.CLEAR for d in picked)),
        )

    def _set(self, opened: bool) -> None:
        doors = self._selected()
        verb = "Open" if opened else "Close"
        changed = self._apply(
            f"{verb} Doors",
            f"{verb} {_counted(len(doors), 'selected door')}?\n\nA backup is made first.",
            f"{verb.lower()}_doors",
            doors,
            opened,
        )
        if changed is not None:
            past = "Opened" if opened else "Closed"
            self._show_toast(f"{past} {_counted(changed, 'door')}.")


class DSRShortcutsPage(_FlagPage):
    columns = {
        "area": ("Area", 230),
        "shortcut": ("Lever or Shortcut", 320),
        "state": ("State", 100),
    }
    note = (
        "Levers, ladders and handles whose state the game keeps once used. "
        "Elevator call levers reset on their own and are not listed."
    )
    _STATE_TEXT = {
        FlagState.SET: "Used",
        FlagState.CLEAR: "Not used",
        FlagState.PARTLY: "Partly used",
    }

    def entries(self):
        return SHORTCUTS

    def search_text(self, entry) -> str:
        return entry.label

    def values(self, entry, state):
        return (entry.area, entry.label, self._STATE_TEXT[state])

    def summary(self, done: int, total: int) -> str:
        return f"{done} of {total} used"

    def _make_buttons(self, row):
        self._use = self._button(row, "Mark Used", lambda: self._set(True), True)
        self._reset = self._button(row, "Reset Selected", lambda: self._set(False))
        return (self._use, self._reset)

    def _update_buttons(self) -> None:
        picked = self._selected()
        states = getattr(self, "_states", {})
        self._enable(
            (self._use, any(states.get(s) is not FlagState.SET for s in picked)),
            (self._reset, any(states.get(s) is not FlagState.CLEAR for s in picked)),
        )

    def _set(self, used: bool) -> None:
        picked = self._selected()
        title = "Mark Shortcuts Used" if used else "Reset Shortcuts"
        verb = "Mark" if used else "Reset"
        tail = " as used" if used else ""
        changed = self._apply(
            title,
            f"{verb} {_counted(len(picked), 'selected shortcut')}{tail}?\n\n"
            "A backup is made first.",
            "mark_shortcuts" if used else "reset_shortcuts",
            picked,
            used,
        )
        if changed is not None:
            done = "Marked" if used else "Reset"
            self._show_toast(f"{done} {_counted(changed, 'shortcut')}.")


class DSRPickupsPage(_FlagPage):
    columns = {
        "area": ("Area", 230),
        "items": ("Items", 340),
        "flag": ("Flag", 100),
        "state": ("State", 100),
    }
    note = (
        "Item pickups and chest contents placed in the maps. Respawn clears "
        "the pickup flag (and closes its chest), so the item lies there again "
        "the next time the area loads. Enemy drops are not included."
    )
    _STATE_TEXT = {
        FlagState.SET: "Taken",
        FlagState.CLEAR: "Available",
        FlagState.PARTLY: "Available",
    }

    def entries(self):
        return PICKUPS

    def search_text(self, entry) -> str:
        return f"{entry.items} {entry.flag}"

    def values(self, entry, state):
        return (entry.area, entry.items, entry.flag, self._STATE_TEXT[state])

    def summary(self, done: int, total: int) -> str:
        return f"{done} of {total} taken"

    def _make_buttons(self, row):
        self._respawn = self._button(row, "Respawn Selected", self._on_selected, True)
        self._respawn_area = self._button(row, "Respawn All in Area", self._on_area)
        return (self._respawn, self._respawn_area)

    def _update_buttons(self) -> None:
        picked = self._selected()
        states = getattr(self, "_states", {})
        self._enable(
            (self._respawn, any(states.get(p) is not FlagState.CLEAR for p in picked)),
            (self._respawn_area, bool(self._taken_in_area())),
        )

    def _taken_in_area(self) -> list:
        """Taken pickups of the picked area, ignoring the search text."""
        area = self._area_var.get()
        if area == _ALL_AREAS:
            return []
        states = getattr(self, "_states", {})
        return [
            p
            for p in PICKUPS
            if p.area == area and states.get(p) is not FlagState.CLEAR
        ]

    def _respawn_list(self, pickups: list) -> None:
        changed = self._apply(
            "Respawn Items",
            f"Respawn {_counted(len(pickups), 'item pickup')}?\n\n"
            "A backup is made first.",
            "respawn_items",
            pickups,
            False,
        )
        if changed is not None:
            self._show_toast(f"Respawned {_counted(changed, 'item pickup')}.")

    def _on_selected(self) -> None:
        self._respawn_list(self._selected())

    def _on_area(self) -> None:
        self._respawn_list(self._taken_in_area())
