"""Shared character selection and unapplied-edit tracking for the main window.

Form pages (stats, identity, equipment, appearance, flags...) no longer write
the save themselves. Each one registers a PendingPage; the window-wide
PendingBar lists the pages with unapplied edits and writes all of them with
one backup and one save.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette

_POLL_MS = 400
# Change rows listed in a confirmation before "and N more"
_PROMPT_ROWS = 12
# Longest field name in the bar; event flag names run to 80 characters
_NAME_CHARS = 36

# (field, old value, new value) as shown to the user
Change = tuple[str, str, str]


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
    details: the changed fields with old and new values; without it the
        page is listed as its name and change count.
    """

    name: str
    changes: Callable[[], int]
    prepare: Callable[[], Callable[[], list[str] | None]]
    discard: Callable[[], None]
    show: Callable[[], None] | None = None
    details: Callable[[], list[Change]] | None = None


def show_value(value) -> str:
    """Display text of a tracked value; tk booleans read as On / Off."""
    if value is None:
        return ""
    text = str(value)
    return {"True": "On", "False": "Off"}.get(text, text)


class FieldTracker:
    """Counts fields that differ from the state recorded by mark_clean().

    labels maps state keys to field names for details(); other keys are
    shown capitalized with underscores as spaces. show turns a (key, value)
    pair into display text.
    """

    def __init__(
        self,
        get_state: Callable[[], dict],
        labels: dict | None = None,
        show: Callable[[object, object], str] | None = None,
    ) -> None:
        self._get_state = get_state
        self._clean: dict | None = None
        self._labels = labels if labels is not None else {}
        self._show = show or (lambda _key, value: show_value(value))

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

    def details(self) -> list[Change]:
        if self._clean is None:
            return []
        now = self._safe_state()
        keys = list(now) + [k for k in self._clean if k not in now]
        return [
            (
                self._label(key),
                self._show(key, self._clean.get(key)),
                self._show(key, now.get(key)),
            )
            for key in keys
            if self._clean.get(key) != now.get(key)
        ]

    def _label(self, key) -> str:
        if key in self._labels:
            return self._labels[key]
        return str(key).replace("_", " ").capitalize()

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

    backup(slot, changes) backs up the save file on disk; changes names the
    changed fields, as shown in the bar. write() writes the in-memory
    save to it.
    blocks_write() returns True (after telling the user) when the game runs.
    file_writable() returns False (after asking the user) when the save
    changed on disk since it was loaded or cannot be written.
    after_apply() reloads the character into every tab.
    reload_from_disk() restores the in-memory save after a failed apply.
    """

    def __init__(
        self,
        parent,
        *,
        get_slot: Callable[[], int],
        backup: Callable[[int, str], None],
        write: Callable[[], None],
        blocks_write: Callable[[], bool],
        file_writable: Callable[[], bool],
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
        self._file_writable = file_writable
        self._after_apply = after_apply
        self._reload_from_disk = reload_from_disk
        self._show_toast = show_toast
        self._on_visibility = on_visibility
        self._shown = False
        self._busy = False
        # Buttons first: pack gives them their width before the label.
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
        ctk.CTkButton(
            self,
            text="Review",
            width=90,
            font=ds.BOLD,
            fg_color="transparent",
            hover_color=palette.PURPLE_SELECT,
            text_color=ds.INFO,
            command=self._open_review,
        ).pack(side=tk.RIGHT, padx=(0, 6), pady=8)
        self._label = ctk.CTkLabel(self, text="", font=ds.BOLD, anchor="w")
        self._label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=14, pady=8)
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

    def rows(
        self, dirty: list[tuple[PendingPage, int]] | None = None
    ) -> list[tuple[PendingPage, Change]]:
        """One row per changed field; a page without details gives one row
        with an empty field and its change count as the new value."""
        if dirty is None:
            dirty = self.dirty()
        out = []
        for page, n in dirty:
            details = []
            if page.details is not None:
                try:
                    details = page.details()
                except Exception:
                    details = []
            if not details:
                details = [("", "", f"{n} change{'s' if n != 1 else ''}")]
            out += [(page, change) for change in details]
        return out

    @staticmethod
    def _count(
        dirty: list[tuple[PendingPage, int]], rows: list[tuple[PendingPage, Change]]
    ) -> int:
        """Changed fields; a page without details counts its change count."""
        total = 0
        for page, n in dirty:
            fields = [change[0] for p, change in rows if p is page]
            total += len(fields) if fields and fields[0] else n
        return total

    def summary(self, dirty: list[tuple[PendingPage, int]] | None = None) -> str:
        """Changed field names, the first few, then "and N more"."""
        return self._names(self.rows(dirty))

    @staticmethod
    def _names(rows: list[tuple[PendingPage, Change]]) -> str:
        names = []
        for page, (field, _old, new) in rows:
            name = field or f"{page.name} ({new})"
            if len(name) > _NAME_CHARS:
                name = name[: _NAME_CHARS - 3] + "..."
            if name not in names:
                names.append(name)
        if len(names) <= 3:
            return ", ".join(names)
        return ", ".join(names[:3]) + f" and {len(names) - 3} more"

    def _change_lines(self) -> str:
        """Changes as "Page: field old -> new" lines for a confirmation."""
        lines = []
        for page, (field, old, new) in self.rows():
            if not field:
                lines.append(f"{page.name}: {new}")
            elif old:
                lines.append(f"{page.name}: {field}  {old} \u2192 {new}")
            else:
                lines.append(f"{page.name}: {field}  {new}".rstrip())
        if len(lines) > _PROMPT_ROWS:
            more = len(lines) - _PROMPT_ROWS + 1
            lines = [*lines[: _PROMPT_ROWS - 1], f"and {more} more"]
        return "\n".join(lines)

    def _poll(self) -> None:
        self._poll_job = None
        if not self._busy:
            self._update()
        self._poll_job = self.after(_POLL_MS, self._poll)

    def _update(self) -> None:
        dirty = self.dirty()
        rows = self.rows(dirty) if dirty else []
        text = self._names(rows)
        if text:
            n = self._count(dirty, rows)
            self._label.configure(
                text=f"{n} unapplied change{'s' if n != 1 else ''}:  {text}"
            )
        if bool(text) != self._shown:
            self._shown = bool(text)
            self._on_visibility(self._shown)

    # ------------------------------------------------------------------

    def apply_all(self) -> bool:
        """Write every page with unapplied edits; True when nothing is left."""
        pending = self.dirty()
        dirty = [p for p, _n in pending]
        if not dirty:
            return True
        if self._busy:
            return False
        from er_save_manager.ui.messagebox import CTkMessageBox

        if self._blocks_write() or not self._file_writable():
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
                self._backup(slot, self.summary(pending))
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
            with contextlib.suppress(Exception):
                page.discard()
        self._update()

    def _discard_clicked(self) -> None:
        from er_save_manager.ui.messagebox import CTkMessageBox

        if CTkMessageBox.askyesno(
            "Discard Changes",
            f"Discard these unapplied changes?\n\n{self._change_lines()}",
            parent=self,
        ):
            self.discard_all()

    def guard(self, action: str, *, apply: bool = True, discard: str = "Discard") -> bool:
        """Ask before an action that would drop unapplied edits.

        Returns True when the action may go ahead (applied, discarded or
        nothing pending), False when the user cancelled or applying failed.
        apply=False offers only discard (button text discard) and Cancel, for
        actions where applying would overwrite newer data on disk.
        """
        if not self.dirty():
            return True
        from er_save_manager.ui.messagebox import CTkMessageBox

        head = (
            f"Slot {self._get_slot() + 1} has unapplied changes:\n\n"
            f"{self._change_lines()}\n\n"
        )
        if apply:
            question = f"Apply them before you {action}?"
            buttons = [("Apply", "apply"), ("Discard", "discard"), ("Cancel", None)]
        else:
            question = f"Discard them and {action}?"
            buttons = [(discard, "discard"), ("Cancel", None)]
        choice = CTkMessageBox._create_dialog(
            self.winfo_toplevel(),
            "Unapplied Changes",
            head + question,
            icon_type="question",
            buttons=buttons,
        )
        if choice == "apply":
            return self.apply_all()
        if choice == "discard":
            self.discard_all()
            return True
        return False

    def _open_review(self) -> None:
        """Every unapplied change with old and new value, a Show link per
        row that brings its page to the front."""
        rows = self.rows()
        if not rows:
            return
        parent = self.winfo_toplevel()
        dialog = ds.create(parent, "Unapplied Changes")
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        def close_then(action: Callable[[], object] | None) -> Callable[[], None]:
            def run() -> None:
                dialog.destroy()
                if action is not None:
                    action()

            return run

        ds.button_row(
            main,
            [
                {"text": "Close", "command": dialog.destroy, "primary": False},
                {"text": "Apply All", "command": close_then(self.apply_all)},
            ],
        )
        ctk.CTkLabel(
            main, text="Unapplied Changes", font=ds.TITLE_LARGE, anchor="w"
        ).pack(fill=tk.X)
        ctk.CTkLabel(
            main,
            text=f"Slot {self._get_slot() + 1}. Apply All writes these "
            "changes in one save.",
            font=ds.SMALL,
            text_color=ds.MUTED,
            anchor="w",
        ).pack(fill=tk.X, pady=(2, 10))

        def build(frame) -> None:
            grid = ctk.CTkFrame(frame, fg_color=ds.BOX, corner_radius=8)
            grid.pack(fill=tk.X)
            for r, (page, (field, old, new)) in enumerate(rows):
                pad = (8 if r == 0 else 2, 8 if r == len(rows) - 1 else 2)
                ctk.CTkLabel(
                    grid, text=page.name, font=ds.SMALL, text_color=ds.MUTED
                ).grid(row=r, column=0, sticky="w", padx=(14, 14), pady=pad)
                ctk.CTkLabel(grid, text=field, font=ds.BOLD, anchor="w").grid(
                    row=r, column=1, sticky="w", padx=(0, 14), pady=pad
                )
                ctk.CTkLabel(
                    grid,
                    text=old,
                    font=ds.FONT,
                    text_color=ds.MUTED,
                    anchor="w",
                    wraplength=260,
                    justify=tk.LEFT,
                ).grid(row=r, column=2, sticky="w", pady=pad)
                if old:
                    ctk.CTkLabel(grid, text="\u2192", font=ds.FONT).grid(
                        row=r, column=3, padx=8, pady=pad
                    )
                ctk.CTkLabel(
                    grid,
                    text=new,
                    font=ds.BOLD,
                    text_color=ds.INFO,
                    anchor="w",
                    wraplength=260,
                    justify=tk.LEFT,
                ).grid(row=r, column=4, sticky="w", pady=pad)
                if page.show is not None:
                    ctk.CTkButton(
                        grid,
                        text="Show",
                        width=0,
                        height=22,
                        font=ds.SMALL,
                        fg_color="transparent",
                        hover_color=palette.PURPLE_TINT,
                        text_color=ds.INFO,
                        command=close_then(page.show),
                    ).grid(row=r, column=5, padx=(14, 10), pady=pad)

        ds.content(main, build, max_height=420)
        ds.finish(dialog, parent, min_width=460)
