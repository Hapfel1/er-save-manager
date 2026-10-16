"""Copy-and-share card of the DS2 / DS3 / DSR appearance tabs.

Loads another character's appearance into the tab: from a slot of the open
save, from a character in another save file of the same game, or from a
JSON export. Nothing is written until the tab's Apply Changes.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import patch_combo_scroll


@dataclass(frozen=True)
class ShareSource:
    """What the card needs from a game.

    characters(save) lists (slot index, name, character) of occupied slots;
    load_save(path) opens a save file of the game; save_filetypes feeds the
    file dialog.
    """

    characters: Callable[[Any], list[tuple[int, str, Any]]]
    load_save: Callable[[str], Any]
    save_filetypes: list[tuple[str, str]]


def pick_character(parent, title: str, entries: list[tuple[int, str]]) -> int | None:
    """Card list of characters; returns the chosen slot index or None."""
    result: list[int | None] = [None]
    selected: list[int | None] = [entries[0][0] if entries else None]
    dialog = ds.create(parent, title)
    rows: dict[int, ctk.CTkFrame] = {}

    def choose(idx: int) -> None:
        selected[0] = idx
        for key, row in rows.items():
            ds.select_card_row(row, key == idx)

    def accept() -> None:
        result[0] = selected[0]
        dialog.destroy()

    def build(frame) -> None:
        for idx, name in entries:
            rows[idx] = ds.card_row(
                frame,
                name or "(no name)",
                f"Slot {idx + 1}",
                on_click=lambda i=idx: choose(i),
                on_double=lambda i=idx: (choose(i), accept()),
            )

    outer = ctk.CTkFrame(dialog, fg_color="transparent")
    outer.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    ds.header(outer, "Choose a character")
    ds.button_row(
        outer,
        [
            {"text": "Cancel", "command": dialog.destroy, "primary": False},
            {"text": "Load", "command": accept},
        ],
    )
    ds.content(outer, build, max_height=360, width=340, pady=(12, 0))
    if entries:
        choose(entries[0][0])
    ds.finish(dialog, parent, min_width=380)
    dialog.wait_window()
    return result[0]


class AppearanceShareCard:
    """Copy from slot / another save, export and import, packed into body."""

    def __init__(
        self,
        body,
        *,
        source: ShareSource,
        get_save: Callable[[], Any],
        on_character: Callable[[Any], bool],
        on_export: Callable[[], None],
        on_import: Callable[[], None],
        show_toast: Callable[[str], None],
    ) -> None:
        self._body = body
        self._source = source
        self._get_save = get_save
        self._on_character = on_character
        self._show_toast = show_toast
        self._var = tk.StringVar()

        row = ds.FlowRow(body, gap=8)
        row.pack(fill="x")
        label = ctk.CTkLabel(row, text="Copy from")
        self._combo = ctk.CTkComboBox(
            row, values=[], variable=self._var, state="readonly", width=240
        )
        patch_combo_scroll(self._combo)
        copy = ds.button(row, "Copy Appearance", self._copy_slot, width=150)
        other = ds.button(
            row,
            "From Another Save...",
            self._copy_other_save,
            primary=False,
            width=170,
        )
        row.add(label, self._combo, copy, other)

        io = ctk.CTkFrame(body, fg_color="transparent")
        io.pack(fill="x", pady=(8, 0))
        ds.button(io, "Export to JSON", on_export, primary=False, width=140).pack(
            side="left", padx=(0, 8)
        )
        ds.button(io, "Import from JSON", on_import, primary=False, width=140).pack(
            side="left"
        )

    def refresh(self) -> None:
        save = self._get_save()
        chars = self._source.characters(save) if save is not None else []
        options = [f"Slot {i + 1} - {name}" for i, name, _c in chars]
        self._combo.configure(values=options)
        self._var.set(options[0] if options else "")

    def _copy_slot(self) -> None:
        save = self._get_save()
        choice = self._var.get()
        if save is None or not choice.startswith("Slot "):
            return
        idx = int(choice.split()[1]) - 1
        char = next((c for i, _n, c in self._source.characters(save) if i == idx), None)
        if char is not None and self._on_character(char):
            self._show_toast(f"Appearance of slot {idx + 1} loaded. Apply to save it.")

    def _copy_other_save(self) -> None:
        path = filedialog.askopenfilename(
            parent=self._body,
            title="Choose a Save File",
            filetypes=self._source.save_filetypes,
        )
        if not path:
            return
        try:
            save = self._source.load_save(path)
            chars = self._source.characters(save)
        except Exception as exc:
            CTkMessageBox.showerror(
                "Save Not Loaded",
                f"{Path(path).name} could not be read: {exc}",
                parent=self._body,
            )
            return
        if not chars:
            CTkMessageBox.showinfo(
                "No Characters",
                f"{Path(path).name} holds no characters.",
                parent=self._body,
            )
            return
        idx = pick_character(
            self._body, "Copy Appearance", [(i, name) for i, name, _c in chars]
        )
        if idx is None:
            return
        char = next(c for i, _n, c in chars if i == idx)
        if self._on_character(char):
            self._show_toast(
                f"Appearance from {Path(path).name}, slot {idx + 1} loaded. "
                "Apply to save it."
            )
