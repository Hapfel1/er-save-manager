"""
DS2 Appearance tab: copy a look between characters, body type, the creation
menu selections (build, physique, hairstyle, eyebrow, beard, tattoo) and
colors.

Edits stay in the tab until the main window's Apply All writes them. Copying
from another character or importing JSON only loads values into the tab.
Only created characters are written: a slot before character creation gets
its look from the creation menu.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from er_save_manager.games.DS2 import appearance as app_data
from er_save_manager.games.DS2.appearance import Appearance
from er_save_manager.games.DS2.save import DS2Save, SlotState
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.appearance_share import AppearanceShareCard, ShareSource
from er_save_manager.ui.color_sliders import ColorSliders
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import FieldTracker, StageError
from er_save_manager.ui.utils import bind_mousewheel, patch_combo_scroll

_SAVE_FILETYPES = [("DS2 save files", "*.sl2 *.co2"), ("All files", "*")]


def _created(save: DS2Save) -> list[tuple[int, str, object]]:
    return [
        (i, save.slot_display_name(i), c)
        for i, c in enumerate(save.characters)
        if save.slot_state(i) is SlotState.CHARACTER
    ]


class DS2AppearanceTab:
    def __init__(
        self,
        parent,
        get_save,
        show_toast,
    ) -> None:
        self.parent = parent
        self._get_save = get_save
        # Slot of the character shown, -1 when none
        self._slot = -1
        self._show_toast = show_toast
        # The appearance block being edited; None until a character is loaded.
        self.block: bytes | None = None
        self._tracker = FieldTracker(self._state)
        self._body_var = tk.StringVar(value=app_data.BODY_TYPES[0])
        # One (part, variable, combo box) per creation menu selection.
        self._parts: list[tuple[app_data.Part, tk.StringVar, object]] = []
        self._colors: list[tuple[ColorSliders, int]] = []

    # --- Building ------------------------------------------------------------ #

    def setup_ui(self) -> None:
        frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        bind_mousewheel(frame)

        body = self._card(
            frame,
            "Copy and share",
            "Load the look of another character, from this save or another "
            "DS2 save, or from a JSON file. Copies include the face, hair "
            "and all colors. Nothing is written until Apply All.",
        )
        self._share = AppearanceShareCard(
            body,
            source=ShareSource(
                characters=_created,
                load_save=DS2Save.from_file,
                save_filetypes=_SAVE_FILETYPES,
            ),
            get_save=self._get_save,
            on_character=lambda char: self.load_character(char, copy=True),
            on_export=self._export_json,
            on_import=self._import_json,
            show_toast=self._show_toast,
        )

        body = self._card(
            frame,
            "Body and face",
            "Builds and hairstyles differ between body types; changing the "
            "body type keeps their place in the list. Options are numbered in "
            "the creation menu's order.",
        )
        self._combo(
            body,
            0,
            "Body type",
            self._body_var,
            list(app_data.BODY_TYPES),
            self._on_body_type,
        )
        for row, part in enumerate(app_data.PARTS, start=1):
            var = tk.StringVar()
            combo = self._combo(
                body,
                row,
                part.label,
                var,
                [],
                lambda _value, p=part, v=var: self._on_part(p, v),
            )
            self._parts.append((part, var, combo))

        body = self._card(frame, "Colors")
        for i, (title, offset) in enumerate(app_data.COLORS):
            sliders = ColorSliders(body, title)
            sliders.frame.grid(
                row=i // 2, column=i % 2, sticky="nw", padx=(0, 30), pady=(0, 10)
            )
            self._colors.append((sliders, offset))

    def _card(self, parent, title: str, hint: str | None = None) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", padx=10, pady=(6, 4))
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=12, pady=(10, 0)
        )
        if hint:
            ctk.CTkLabel(
                card,
                text=hint,
                font=("Segoe UI", 10),
                text_color=ds.MUTED,
                justify="left",
                wraplength=700,
            ).pack(anchor="w", padx=12)
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=12, pady=(4, 10))
        return body

    def _combo(self, parent, row: int, label: str, var, values, command=None):
        ctk.CTkLabel(parent, text=label).grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=4
        )
        combo = ctk.CTkComboBox(
            parent,
            values=values,
            variable=var,
            state="readonly",
            width=260,
            command=command,
        )
        combo.grid(row=row, column=1, sticky="w", pady=4)
        patch_combo_scroll(combo)
        return combo

    # --- State --------------------------------------------------------------- #

    def _options(self, part: app_data.Part) -> list[tuple[str, int]]:
        options = list(part.choices(self.block[app_data.GENDER]))
        current = part.get(self.block)
        if current not in [v for _label, v in options]:
            options.append((f"Value {current}", current))
        return options

    def _on_body_type(self, _value=None) -> None:
        if self.block is None:
            return
        body = app_data.BODY_TYPES.index(self._body_var.get())
        self.block = app_data.set_gender(self._pull_colors(self.block), body)
        self._show_values()

    def _on_part(self, part: app_data.Part, var: tk.StringVar) -> None:
        if self.block is None:
            return
        value = dict(self._options(part)).get(var.get())
        if value is not None:
            self.block = part.set(self.block, value)

    def _pull_colors(self, block: bytes) -> bytes:
        for sliders, offset in self._colors:
            block = app_data.set_rgb(block, offset, sliders.rgb())
        return block

    def _show_values(self) -> None:
        if self.block is None:
            return
        body = self.block[app_data.GENDER]
        if body < len(app_data.BODY_TYPES):
            self._body_var.set(app_data.BODY_TYPES[body])
        for part, var, combo in self._parts:
            options = self._options(part)
            combo.configure(values=[label for label, _v in options])
            current = part.get(self.block)
            var.set(next(label for label, v in options if v == current))
        for sliders, offset in self._colors:
            sliders.set_rgb(app_data.get_rgb(self.block, offset))

    def _current(self) -> Appearance:
        if self.block is None:
            raise ValueError("No character loaded")
        return Appearance(self._pull_colors(self.block))

    # --- Public -------------------------------------------------------------- #

    def load_slot(self, slot: int) -> None:
        """Show the character in slot; -1 clears the tab."""
        self._slot = slot
        self.refresh()

    def refresh(self) -> None:
        """Reload the share list and the selected slot's appearance."""
        self._share.refresh()
        save = self._get_save()
        slot = self._slot
        if save is None or slot < 0:
            self.block = None
            self._tracker.clear()
            return
        self.load_character(save.characters[slot])

    def load_character(self, char, *, copy: bool = False) -> bool:
        """Show char's appearance. A failed copy keeps the loaded one; a
        failed load clears it, so Apply All cannot write another
        character's."""
        try:
            app = Appearance.from_character(char)
            app.validate()
        except ValueError as exc:
            if not copy:
                self.block = None
                self._tracker.clear()
            CTkMessageBox.showwarning(
                "Appearance Not Loaded",
                f"This character's appearance could not be read: {exc}",
                parent=self.parent,
            )
            return False
        self.block = app.block
        self._show_values()
        if not copy:
            self._tracker.mark_clean()
        return True

    def changes(self) -> int:
        return self._tracker.changes()

    def _state(self) -> dict:
        """The appearance block byte by byte, as Apply All writes it."""
        return dict(enumerate(self._current().block))

    def discard(self) -> None:
        save = self._get_save()
        if save is not None and self._slot >= 0:
            self.load_character(save.characters[self._slot])

    def prepare(self):
        save = self._get_save()
        slot = self._slot
        if save is None or slot < 0:
            raise StageError("No character loaded.")
        if save.slot_state(slot) is not SlotState.CHARACTER or self.block is None:
            raise StageError(
                "This slot holds no created character. Create the character "
                "in game first; its look comes from the creation menu."
            )
        try:
            app = self._current()
            app.validate()
        except ValueError as exc:
            raise StageError(str(exc)) from None

        def commit() -> None:
            app.apply_to(save.characters[slot])
            save.sync_appearance_cache(slot)

        return commit

    # --- Actions ------------------------------------------------------------- #

    def _export_json(self) -> None:
        try:
            data = self._current().to_json()
        except ValueError as exc:
            CTkMessageBox.showwarning("Nothing to Export", str(exc), parent=self.parent)
            return
        save = self._get_save()
        name = save.slot_display_name(self._slot) if save is not None else ""
        path = filedialog.asksaveasfilename(
            parent=self.parent,
            title="Export Appearance",
            defaultextension=".json",
            initialfile=f"{name or 'appearance'}_ds2_appearance.json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as exc:
            CTkMessageBox.showerror("Export Failed", str(exc), parent=self.parent)
            return
        self._show_toast("Appearance exported.")

    def _import_json(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.parent,
            title="Import Appearance",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        try:
            app = Appearance.from_json(
                json.loads(Path(path).read_text(encoding="utf-8"))
            )
        except (OSError, ValueError) as exc:
            CTkMessageBox.showerror("Import Failed", str(exc), parent=self.parent)
            return
        self.block = app.block
        self._show_values()
        self._show_toast("Appearance loaded. Apply All to save it.")
