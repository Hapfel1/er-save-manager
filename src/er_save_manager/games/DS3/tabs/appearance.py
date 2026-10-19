"""
DS3 Appearance tab: body type and build, base templates, face sliders, hair,
brow, beard, eyelashes, pupils, tattoo/mark and their colors.

The sliders are the character creation menu's own, with its captions. Edits
stay in the tab until the main window's Apply All writes them. Copying from
another character or importing JSON only loads values into the tab.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from er_save_manager.games.DS3 import appearance as app_data
from er_save_manager.games.DS3.appearance import Appearance, Part, Slider
from er_save_manager.games.DS3.character_ops import _sync_dir_face
from er_save_manager.games.DS3.save import DS3Save
from er_save_manager.games.DS3.slot import LayoutError
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.appearance_share import AppearanceShareCard, ShareSource
from er_save_manager.ui.color_sliders import ColorSliders
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import FieldTracker, StageError
from er_save_manager.ui.utils import (
    bind_mousewheel,
    center_window,
    patch_combo_scroll,
    style_window_frame,
)
from er_save_manager.ui.virtual_grid import GridEntry, VirtualIconGrid

_LABEL_WIDTH = 190
_CAPTION_WIDTH = 86
_PART_ICON = 56
_BUILD_GROUP = "Build Detail"
_TATTOO_GROUP = "Tweak Tattoo/Mark"
_SKIN_GROUPS = ("Skin Color", "Cosmetics")
_SKIN_COLOR_OFFSET = 0x30
_TATTOO_PART = "Tattoo/Mark"
_SAVE_FILETYPES = [("DS3 save files", "*.sl2 *.co2"), ("All files", "*")]


class PartPickerDialog(ctk.CTkToplevel):
    """Icon grid of a part's options, as in the character creation menu."""

    def __init__(self, parent, part: Part, current: int, on_pick) -> None:
        super().__init__(parent)
        self._part = part
        self._on_pick = on_pick
        self._picked: int | None = None
        self.title(f"Choose {part.name}")
        w, h = 560, 560
        self.geometry(f"{w}x{h}")
        self.minsize(420, 360)
        self.transient(parent)
        style_window_frame(self)

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(side="bottom", fill="x", padx=10, pady=(4, 10))
        ds.button(bar, "Select", self._select, width=120).pack(side="right")
        ds.button(bar, "Cancel", self.destroy, primary=False, width=100).pack(
            side="right", padx=(0, 8)
        )

        self._grid = VirtualIconGrid(
            self,
            self._on_select,
            on_activate=lambda key: self._finish(key),
            cell_w=96,
            cell_h=104,
            icon_size=64,
        )
        self._grid.pack(fill="both", expand=True, padx=6, pady=(10, 4))
        entries = [
            GridEntry(
                opt.value,
                f"{part.name} {i + 1}",
                f"{part.name} {i + 1}".lower(),
                lambda icon=opt.icon: app_data.icon_image(icon),
            )
            for i, opt in enumerate(part.options)
        ]
        self._grid.set_entries(entries)
        if any(opt.value == current for opt in part.options):
            self._grid.set_selection([current], notify=False)
            self._picked = current
        center_window(self, w, h, parent=parent)
        self.lift()
        self.focus_force()

    def _on_select(self, keys: list) -> None:
        self._picked = keys[0] if keys else None

    def _select(self) -> None:
        if self._picked is not None:
            self._finish(self._picked)

    def _finish(self, value: int) -> None:
        self._on_pick(value)
        self.destroy()


class _PartRow:
    """Icon, option number, Change button and color sliders of one part."""

    def __init__(self, tab: DS3AppearanceTab, parent, part: Part) -> None:
        self.part = part
        self._tab = tab
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        left = ctk.CTkFrame(self.frame, fg_color="transparent", width=220)
        left.pack(side="left", anchor="n", padx=(0, 20))
        ctk.CTkLabel(left, text=part.name, font=ds.BOLD).pack(anchor="w")
        row = ctk.CTkFrame(left, fg_color="transparent")
        row.pack(anchor="w", pady=(4, 0))
        self._icon = ctk.CTkLabel(row, text="", width=_PART_ICON, height=_PART_ICON)
        self._icon.pack(side="left")
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", padx=(8, 0))
        self._value_label = ctk.CTkLabel(info, text="", anchor="w")
        self._value_label.pack(anchor="w")
        ds.button(info, "Change", self._pick, primary=False, width=90).pack(
            anchor="w", pady=(2, 0)
        )
        self.color = ColorSliders(self.frame, f"{part.name} color")
        self.color.frame.pack(side="left", anchor="n")

    def _pick(self) -> None:
        current = app_data.get_part(self._tab.face, self.part)
        PartPickerDialog(self._tab.parent, self.part, current, self._set)

    def _set(self, value: int) -> None:
        self._tab.face = app_data.set_part(self._tab.face, self.part, value)
        self.show()

    def show(self) -> None:
        value = app_data.get_part(self._tab.face, self.part)
        index = next(
            (i for i, o in enumerate(self.part.options) if o.value == value), None
        )
        if index is None:
            self._value_label.configure(text=f"Value {value}")
            self._icon.configure(image=None)
            return
        self._value_label.configure(text=f"{self.part.name} {index + 1}")
        img = app_data.icon_image(self.part.options[index].icon)
        self._icon_image = ctk.CTkImage(img, img, size=(_PART_ICON, _PART_ICON))
        self._icon.configure(image=self._icon_image)


class DS3AppearanceTab:
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
        # The FACE block being edited; None until a character is loaded.
        self.face: bytes | None = None
        self._tracker = FieldTracker(self._state)
        self._sliders: list[tuple[Slider, tk.IntVar]] = []
        self._part_rows: list[_PartRow] = []
        self._skin_built = False
        self._body_var = tk.StringVar(value=app_data.BODY_TYPES[1])
        self._template_var = tk.StringVar()

    # --- Building ------------------------------------------------------------ #

    def setup_steps(self):
        frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        bind_mousewheel(frame)

        self._build_actions(frame)
        self._build_body(frame)
        yield
        self._build_face(frame)
        yield
        self._build_parts(frame)

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

    def _combo(self, parent, label: str, var, values, command=None):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, width=120, anchor="w").pack(side="left")
        combo = ctk.CTkComboBox(
            row,
            values=values,
            variable=var,
            state="readonly",
            width=260,
            command=command,
        )
        combo.pack(side="left")
        patch_combo_scroll(combo)
        return combo

    def _build_body(self, parent) -> None:
        body = self._card(parent, "Body")
        self._combo(
            body,
            "Body type",
            self._body_var,
            list(app_data.BODY_TYPES),
            self._on_body_change,
        )
        self._fill_group(body, app_data.group(_BUILD_GROUP), heading=False)

    def _build_face(self, parent) -> None:
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", padx=10, pady=(6, 4))
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(10, 0))
        ctk.CTkLabel(head, text="Face", font=("Segoe UI", 12, "bold")).pack(side="left")
        self._face_mode = ctk.CTkSegmentedButton(
            head, values=["Shape", "Skin"], command=self._show_face_page
        )
        self._face_mode.pack(side="right")
        self._face_mode.set("Shape")
        ctk.CTkLabel(
            card,
            text="Picking a base template replaces the face sliders and the "
            "base skin color, as in character creation.",
            font=("Segoe UI", 10),
            text_color=ds.MUTED,
            justify="left",
            wraplength=700,
        ).pack(anchor="w", padx=12)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(4, 0))
        self._template_combo = self._combo(
            top, "Base template", self._template_var, [], self._on_template
        )
        self._set_template_names(1)

        self._shape_page = ctk.CTkFrame(card, fg_color="transparent")
        self._skin_page = ctk.CTkFrame(card, fg_color="transparent")
        skip = {_BUILD_GROUP, _TATTOO_GROUP, *_SKIN_GROUPS}
        for grp in app_data.slider_groups():
            if grp.name not in skip:
                self._fill_group(self._shape_page, grp)
        self._shape_page.pack(fill="x", padx=12, pady=(4, 10))

    def _build_skin_page(self) -> None:
        self._skin_color = ColorSliders(self._skin_page, "Base skin color")
        self._skin_color.frame.pack(anchor="w", pady=(8, 0))
        for name in _SKIN_GROUPS:
            self._fill_group(self._skin_page, app_data.group(name))
        self._skin_built = True

    def _show_face_page(self, mode: str) -> None:
        if mode == "Skin" and not self._skin_built:
            self._build_skin_page()
            self._show_values()
        shown, hidden = (
            (self._skin_page, self._shape_page)
            if mode == "Skin"
            else (self._shape_page, self._skin_page)
        )
        hidden.pack_forget()
        shown.pack(fill="x", padx=12, pady=(4, 10))

    def _build_parts(self, parent) -> None:
        body = self._card(
            parent,
            "Hair, eyes and tattoo",
            "Options are numbered in the order the character creation menu shows them.",
        )
        for part in app_data.parts():
            row = _PartRow(self, body, part)
            row.frame.pack(fill="x", pady=(6, 6))
            self._part_rows.append(row)
            if part.name == _TATTOO_PART:
                self._fill_group(body, app_data.group(_TATTOO_GROUP))

    def _build_actions(self, parent) -> None:
        body = self._card(
            parent,
            "Copy and share",
            "Load the look of another character, from this save or another "
            "DS3 save, or from a JSON file. Nothing is written until Apply All.",
        )
        self._share = AppearanceShareCard(
            body,
            source=ShareSource(
                characters=lambda save: [
                    (i, c.name, c) for i, c in enumerate(save.characters) if c
                ],
                load_save=DS3Save.from_file,
                save_filetypes=_SAVE_FILETYPES,
            ),
            get_save=self._get_save,
            on_character=lambda char: self.load_character(char, copy=True),
            on_export=self._export_json,
            on_import=self._import_json,
            show_toast=self._show_toast,
        )

    def _fill_group(self, page, grp, heading: bool = True) -> None:
        if heading:
            ctk.CTkLabel(page, text=grp.name, font=ds.BOLD).pack(
                anchor="w", pady=(8, 0)
            )
        for slider in grp.sliders:
            row = ctk.CTkFrame(page, fg_color="transparent")
            row.pack(fill="x")
            ctk.CTkLabel(row, text=slider.label, width=_LABEL_WIDTH, anchor="w").pack(
                side="left"
            )
            ctk.CTkLabel(
                row,
                text=slider.min_caption,
                width=_CAPTION_WIDTH,
                anchor="e",
                text_color=ds.MUTED,
            ).pack(side="left")
            var = tk.IntVar(value=0)
            ctk.CTkSlider(
                row,
                from_=0,
                to=255,
                number_of_steps=255,
                variable=var,
                width=240,
                command=lambda v, s=slider: self._on_slider(s, v),
            ).pack(side="left", padx=6)
            ctk.CTkLabel(
                row,
                text=slider.max_caption,
                width=_CAPTION_WIDTH,
                anchor="w",
                text_color=ds.MUTED,
            ).pack(side="left")
            ctk.CTkLabel(row, textvariable=var, width=36, anchor="e").pack(side="left")
            self._sliders.append((slider, var))

    # --- State --------------------------------------------------------------- #

    def _body_type(self) -> int:
        return app_data.BODY_TYPES.index(self._body_var.get())

    def _set_template_names(self, body_type: int) -> None:
        names = app_data.template_names(body_type)
        self._template_combo.configure(values=names)
        if self._template_var.get() not in names:
            self._template_var.set("")

    def _on_body_change(self, _value=None) -> None:
        self._set_template_names(self._body_type())

    def _on_template(self, _value=None) -> None:
        if self.face is None:
            return
        names = app_data.template_names(self._body_type())
        self.face = app_data.apply_template(
            self._pull_colors(self.face),
            self._body_type(),
            names.index(self._template_var.get()),
        )
        self._show_values()

    def _on_slider(self, slider: Slider, value: float) -> None:
        if self.face is not None:
            self.face = app_data.set_u8(self.face, slider.offsets, round(value))

    def _color_rows(self):
        rows = [(row.color, row.part.color_offset) for row in self._part_rows]
        if self._skin_built:
            rows.append((self._skin_color, _SKIN_COLOR_OFFSET))
        return rows

    def _pull_colors(self, face: bytes) -> bytes:
        for sliders, offset in self._color_rows():
            face = app_data.set_rgb(face, offset, sliders.rgb())
        return face

    def _show_values(self) -> None:
        if self.face is None:
            return
        for slider, var in self._sliders:
            var.set(self.face[slider.offsets[0]])
        for sliders, offset in self._color_rows():
            sliders.set_rgb(app_data.get_rgb(self.face, offset))
        for row in self._part_rows:
            row.show()

    def _current(self) -> Appearance:
        if self.face is None:
            raise ValueError("No character loaded")
        return Appearance(self._body_type(), self._pull_colors(self.face))

    def _show(self, app: Appearance) -> None:
        self._body_var.set(app_data.BODY_TYPES[app.body_type])
        self._set_template_names(app.body_type)
        self._template_var.set("")
        self.face = app.face
        self._show_values()

    # --- Public -------------------------------------------------------------- #

    def refresh(self) -> None:
        self._share.refresh()

    def load_slot(self, slot_idx: int) -> None:
        """Show the character in slot_idx; -1 or an empty slot clears the tab."""
        self.refresh()
        save = self._get_save()
        if save is None or not (
            0 <= slot_idx < len(save.characters) and save.characters[slot_idx]
        ):
            self._slot = -1
            self.clear()
            return
        self._slot = slot_idx
        self.load_character(save.characters[slot_idx])

    def load_character(self, char, *, copy: bool = False) -> bool:
        """Show char's appearance. A failed copy keeps the loaded one; a
        failed load clears it, so Apply cannot write another character's."""
        try:
            app = Appearance.from_character(char)
            app.validate()
        except (LayoutError, ValueError) as exc:
            if not copy:
                self.face = None
                self._tracker.clear()
            CTkMessageBox.showwarning(
                "Appearance Not Loaded",
                f"This character's appearance could not be read: {exc}",
                parent=self.parent,
            )
            return False
        self._show(app)
        if not copy:
            self._tracker.mark_clean()
        return True

    def clear(self) -> None:
        self.face = None
        self._tracker.clear()

    def changes(self) -> int:
        return self._tracker.changes()

    def _state(self) -> dict:
        """Body type and the FACE block byte by byte, as Apply All writes them."""
        app = self._current()
        return {"body": app.body_type} | dict(enumerate(app.face))

    def discard(self) -> None:
        save = self._get_save()
        slot = self._slot
        if save is None or slot < 0 or save.characters[slot] is None:
            return
        self.load_character(save.characters[slot])

    def prepare(self):
        save = self._get_save()
        slot = self._slot
        if save is None or slot < 0 or save.characters[slot] is None:
            raise StageError("No character loaded.")
        try:
            app = self._current()
            app.validate()
            char = save.characters[slot]
            if len(char.face_block) != len(app.face):
                raise ValueError(
                    f"Appearance block is {len(app.face)} bytes, the character's "
                    f"is {len(char.face_block)}"
                )
        except (LayoutError, ValueError) as exc:
            raise StageError(str(exc)) from None

        def commit() -> None:
            app.apply_to(char)
            _sync_dir_face(save, slot, char.face_block)

        return commit

    # --- Actions ------------------------------------------------------------- #

    def _export_json(self) -> None:
        try:
            data = self._current().to_json()
        except ValueError as exc:
            CTkMessageBox.showwarning("Nothing to Export", str(exc), parent=self.parent)
            return
        save = self._get_save()
        slot = self._slot
        name = (
            save.characters[slot].name
            if save is not None and slot >= 0 and save.characters[slot]
            else "appearance"
        )
        path = filedialog.asksaveasfilename(
            parent=self.parent,
            title="Export Appearance",
            defaultextension=".json",
            initialfile=f"{name or 'appearance'}_ds3_appearance.json",
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
        self._show(app)
        self._show_toast("Appearance loaded. Apply All to save it.")
