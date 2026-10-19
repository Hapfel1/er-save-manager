"""Shared character selection and unapplied-edit tracking for the main window.

Form pages (stats, identity, equipment, appearance, flags...) no longer write
the save themselves. Each one registers a PendingPage; the window-wide
PendingBar lists the pages with unapplied edits and writes all of them with
one backup and one save.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette

_POLL_MS = 400


class StageError(Exception):
    """Input of a page is invalid; raised before the page changes the save."""


class StageCancelled(StageError):
    """The user declined a page's confirmation; Apply All stops silently."""


@dataclass
class PendingPage:
    """A form page whose edits wait for Apply All.

    changes: number of changed fields, 0 when the page matches the save.
    prepare: validates the input and returns a function that writes it into
        the in-memory save (no backup, no file write) and returns notes for
        the user. Raises StageError for invalid input without touching the
        save.
    discard: reloads the page from the save.
    show: brings the page to the front (top-level tab and sub-tab).
    """

    name: str
    changes: Callable[[], int]
    prepare: Callable[[], Callable[[], list[str] | None]]
    discard: Callable[[], None]
    show: Callable[[], None] | None = None


class FieldTracker:
    """Counts fields that differ from the state recorded by mark_clean()."""

    def __init__(self, get_state: Callable[[], dict]) -> None:
        self._get_state = get_state
        self._clean: dict | None = None

    def mark_clean(self) -> None:
        self._clean = self._safe_state()

    def clear(self) -> None:
        """Nothing loaded: no changes until the next mark_clean()."""
        self._clean = None

    def changes(self) -> int:
        if self._clean is None:
            return 0
        now = self._safe_state()
        keys = self._clean.keys() | now.keys()
        return sum(1 for k in keys if self._clean.get(k) != now.get(k))

    def _safe_state(self) -> dict:
        try:
            return dict(self._get_state())
        except (tk.TclError, ValueError, AttributeError):
            return {}


def var_state(variables: dict) -> Callable[[], dict]:
    """State function over a dict of tk variables (read as strings)."""

    def state() -> dict:
        out = {}
        for key, var in variables.items():
            try:
                out[key] = str(var.get())
            except tk.TclError:
                out[key] = None
        return out

    return state


class CharacterBar(ctk.CTkFrame):
    """Character selector shared by every tab that works on one character."""

    def __init__(self, parent, on_select: Callable[[int], bool]) -> None:
        super().__init__(parent, corner_radius=12)
        self._on_select = on_select
        # (slot index, label) per entry, in list order
        self._entries: list[tuple[int, str]] = []
        self._index = -1
        ctk.CTkLabel(self, text="Character", font=ds.BOLD).pack(
            side=tk.LEFT, padx=(14, 8), pady=8
        )
        self._var = tk.StringVar(value="")
        self._combo = ctk.CTkComboBox(
            self,
            variable=self._var,
            values=[],
            state="readonly",
            width=260,
            command=self._picked,
        )
        self._combo.pack(side=tk.LEFT, pady=8)
        from er_save_manager.ui.utils import patch_combo_scroll

        patch_combo_scroll(self._combo)
        self._detail = ctk.CTkLabel(self, text="", font=ds.SMALL, text_color=ds.MUTED)
        self._detail.pack(side=tk.LEFT, padx=14)
        self._note = ctk.CTkLabel(self, text="", font=ds.SMALL, text_color=ds.MUTED)
        self._note.pack(side=tk.RIGHT, padx=14)
        # Feature links of the shown tab, right aligned before the note
        # 1 x 1 while empty; CTkFrame's default size is 200 x 200
        self._links = ctk.CTkFrame(self, fg_color="transparent", width=1, height=1)
        self._links.pack(side=tk.RIGHT)
        self._link_buttons: list[ctk.CTkButton] = []
        self.bind("<Configure>", lambda _e: self._fit_links(), add="+")

    @property
    def index(self) -> int:
        """Slot index of the selected character, -1 when none."""
        return self._index

    @property
    def labels(self) -> list[str]:
        return [label for _slot, label in self._entries]

    def set_slots(self, entries: list[tuple[int, str]], index: int) -> None:
        """Replace the (slot index, label) list and select slot index without
        loading it."""
        self._entries = list(entries)
        self._combo.configure(values=self.labels)
        self.select(index)

    def select(self, index: int) -> None:
        self._index = index
        label = next((text for slot, text in self._entries if slot == index), "")
        self._var.set(label)

    def set_detail(self, text: str) -> None:
        self._detail.configure(text=text)

    def set_links(self, links: list[tuple[str, Callable[[], None]]]) -> None:
        """Purple text buttons for features of the shown tab that are easy to
        miss (community browsers, visual pickers)."""
        for child in self._link_buttons:
            child.destroy()
        self._link_buttons = [
            ctk.CTkButton(
                self._links,
                text=text,
                command=command,
                font=ds.BOLD,
                fg_color="transparent",
                hover_color=palette.PURPLE_TINT,
                text_color=ds.INFO,
                width=0,
                height=28,
            )
            for text, command in links
        ]
        self._fit_links()

    def _fit_links(self) -> None:
        """Show the links in order while they fit; the rest stay hidden
        instead of being clipped."""
        for button in self._link_buttons:
            button.pack_forget()
        self.update_idletasks()
        used = sum(
            w.winfo_reqwidth() + 28
            for w in (self.winfo_children())
            if w is not self._links and w.winfo_manager()
        )
        free = self.winfo_width() - used
        for button in self._link_buttons:
            need = button.winfo_reqwidth() + 4
            if need > free:
                break
            button.pack(side=tk.LEFT, padx=(0, 4))
            free -= need

    def set_active(self, active: bool) -> None:
        """Dimmed on tabs that do not use a character."""
        self._combo.configure(state="readonly" if active else "disabled")
        self._note.configure(text="" if active else "Not used by this tab")

    def _picked(self, value: str) -> None:
        index = next((slot for slot, text in self._entries if text == value), None)
        if index is None or index == self._index:
            return
        if self._on_select(index):
            self._index = index
        else:
            self.select(self._index)


class PendingBar(ctk.CTkFrame):
    """Lists pages with unapplied edits; Apply All writes them in one save.

    backup(slot) backs up the save file on disk; write() writes the
    in-memory save to it.
    blocks_write() returns True (after telling the user) when the game runs.
    after_apply() reloads the character into every tab.
    reload_from_disk() restores the in-memory save after a failed apply.
    """

    def __init__(
        self,
        parent,
        *,
        get_slot: Callable[[], int],
        backup: Callable[[int], None],
        write: Callable[[], None],
        blocks_write: Callable[[], bool],
        after_apply: Callable[[], None],
        reload_from_disk: Callable[[], None],
        show_toast: Callable[..., None],
        on_visibility: Callable[[bool], None],
    ) -> None:
        super().__init__(parent, corner_radius=12, fg_color=palette.PURPLE_TINT)
        self._pages: list[PendingPage] = []
        self._get_slot = get_slot
        self._backup = backup
        self._write = write
        self._blocks_write = blocks_write
        self._after_apply = after_apply
        self._reload_from_disk = reload_from_disk
        self._show_toast = show_toast
        self._on_visibility = on_visibility
        self._shown = False
        self._busy = False
        self._label = ctk.CTkLabel(self, text="", font=ds.BOLD, anchor="w")
        self._label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=14, pady=8)
        ctk.CTkButton(self, text="Apply All", width=120, command=self.apply_all).pack(
            side=tk.RIGHT, padx=(6, 12), pady=8
        )
        ctk.CTkButton(
            self,
            text="Discard",
            width=100,
            fg_color=ds.SECONDARY,
            text_color=("gray10", "gray90"),
            command=self._discard_clicked,
        ).pack(side=tk.RIGHT, pady=8)
        self._poll_job = self.after(_POLL_MS, self._poll)

    def register(self, page: PendingPage) -> None:
        self._pages.append(page)

    def clear_pages(self) -> None:
        self._pages.clear()
        self._update()

    def destroy(self) -> None:
        if self._poll_job is not None:
            self.after_cancel(self._poll_job)
            self._poll_job = None
        super().destroy()

    # ------------------------------------------------------------------

    def dirty(self) -> list[tuple[PendingPage, int]]:
        out = []
        for page in self._pages:
            try:
                n = page.changes()
            except Exception:
                n = 0
            if n:
                out.append((page, n))
        return out

    def summary(self) -> str:
        return ", ".join(f"{p.name} ({n})" for p, n in self.dirty())

    def _poll(self) -> None:
        self._poll_job = None
        if not self._busy:
            self._update()
        self._poll_job = self.after(_POLL_MS, self._poll)

    def _update(self) -> None:
        text = self.summary()
        if text:
            self._label.configure(text=f"Unapplied changes:  {text}")
        if bool(text) != self._shown:
            self._shown = bool(text)
            self._on_visibility(self._shown)

    # ------------------------------------------------------------------

    def apply_all(self) -> bool:
        """Write every page with unapplied edits; True when nothing is left."""
        dirty = [p for p, _n in self.dirty()]
        if not dirty:
            return True
        if self._busy:
            return False
        from er_save_manager.ui.messagebox import CTkMessageBox

        if self._blocks_write():
            return False
        self._busy = True
        try:
            commits = []
            for page in dirty:
                try:
                    commits.append(page.prepare())
                except StageCancelled:
                    return False
                except StageError as exc:
                    if page.show:
                        page.show()
                    CTkMessageBox.showerror(
                        "Invalid Value", f"{page.name}:\n{exc}", parent=self
                    )
                    return False
            slot = self._get_slot()
            notes: list[str] = []
            try:
                self._backup(slot)
            except Exception as exc:
                CTkMessageBox.showerror(
                    "Backup Failed",
                    f"Nothing was written, the backup failed:\n{exc}",
                    parent=self,
                )
                return False
            try:
                for commit in commits:
                    notes += commit() or []
                self._write()
            except Exception as exc:
                CTkMessageBox.showerror(
                    "Apply Failed",
                    f"The save was not written:\n{exc}\n\nIt is reloaded from disk.",
                    parent=self,
                )
                self._reload_from_disk()
                return False
            self._after_apply()
            self._update()
            self._show_toast(
                f"Changes applied to slot {slot + 1}. Backup created.", duration=3000
            )
            if notes:
                CTkMessageBox.showwarning(
                    "Applied With Notes", "\n\n".join(notes), parent=self
                )
            return True
        finally:
            self._busy = False

    def discard_all(self) -> None:
        for page, _n in self.dirty():
            try:
                page.discard()
            except Exception:
                pass
        self._update()

    def _discard_clicked(self) -> None:
        from er_save_manager.ui.messagebox import CTkMessageBox

        if CTkMessageBox.askyesno(
            "Discard Changes",
            f"Discard the unapplied changes?\n\n{self.summary()}",
            parent=self,
        ):
            self.discard_all()

    def guard(self, action: str) -> bool:
        """Ask before an action that would drop unapplied edits.

        Returns True when the action may go ahead (applied, discarded or
        nothing pending), False when the user cancelled or applying failed.
        """
        if not self.dirty():
            return True
        from er_save_manager.ui.messagebox import CTkMessageBox

        choice = CTkMessageBox._create_dialog(
            self.winfo_toplevel(),
            "Unapplied Changes",
            f"Slot {self._get_slot() + 1} has unapplied changes:\n"
            f"{self.summary()}\n\nApply them before you {action}?",
            icon_type="question",
            buttons=[("Apply", "apply"), ("Discard", "discard"), ("Cancel", None)],
        )
        if choice == "apply":
            return self.apply_all()
        if choice == "discard":
            self.discard_all()
            return True
        return False
