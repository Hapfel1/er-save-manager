"""
DSR Appearance tab: body, face and hair types, colors and FaceGen face sliders.

Edits stay in the tab until the main window's Apply All writes them. Copying
from another character or importing JSON only loads values into the tab.
"""

from __future__ import annotations

import json
import tkinter as tk
from collections import Counter
from pathlib import Path

import customtkinter as ctk

from er_save_manager.games.DSR import appearance as app_data
from er_save_manager.games.DSR.appearance import Appearance, FaceControl
from er_save_manager.games.DSR.character_ops import _sync_dir_appearance
from er_save_manager.games.DSR.save import DSRSave
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.appearance_share import AppearanceShareCard, ShareSource
from er_save_manager.ui.color_sliders import ColorSliders
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import FieldTracker, StageError
from er_save_manager.ui.utils import bind_mousewheel, patch_combo_scroll, pick_file

_BODY_TYPES = ["Type B", "Type A"]  # index = stored body type
_SAVE_FILETYPES = [("DSR save files", "*.sl2 *.co2"), ("All files", "*")]
_LABEL_WIDTH = 230
# Slider rows built per event loop turn while the tab builds in the background.
_ROWS_PER_STAGE = 6
# Slider readout: control value as a share of its slider half-range.
_READOUT_SCALE = 100
_REFRESH_MS = 120


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


class DSRAppearanceTab:
    def __init__(
        self,
        parent,
        get_dsr_save,
        show_toast,
    ) -> None:
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        # Slot of the character shown, -1 when none
        self._slot = -1
        self._show_toast = show_toast
        self._tracker = FieldTracker(self._state)
        self._coeffs: list[float] = [0.0] * 100
        self._sliders: list[tuple[FaceControl, ctk.CTkSlider, tk.StringVar]] = []
        self._ranges: dict[FaceControl, float] = {}
        self._refresh_job = None
        self._skin_built = False

        self._body_var = tk.StringVar(value=_BODY_TYPES[1])
        self._physique_var = tk.StringVar()
        self._face_var = tk.StringVar()
        self._hair_var = tk.StringVar()
        self._color_var = tk.StringVar()

    # --- Building ------------------------------------------------------------ #

    def setup_steps(self):
        frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        bind_mousewheel(frame)
        self._frame = frame

        self._build_actions(frame)
        yield
        self._build_types(frame)
        yield
        self._build_colors(frame)
        yield
        yield from self._build_face(frame)

    def _card(self, parent, title: str, hint: str | None = None) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", padx=10, pady=(6, 4))
        ctk.CTkLabel(card, text=title, font=("Inter", 12, "bold")).pack(
            anchor="w", padx=12, pady=(10, 0)
        )
        if hint:
            ctk.CTkLabel(
                card,
                text=hint,
                font=("Inter", 10),
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

    def _build_types(self, parent) -> None:
        body = self._card(
            parent,
            "Body and hair",
            "Face types and hairstyles differ between body types. Picking a "
            "face type replaces the face sliders with that face, as in the "
            "character creation menu.",
        )
        self._combo(
            body, 0, "Body type", self._body_var, _BODY_TYPES, self._on_body_change
        )
        self._combo(body, 1, "Physique", self._physique_var, app_data.physique_names())
        self._face_combo = self._combo(
            body, 2, "Face type", self._face_var, [], self._on_face_type
        )
        self._hair_combo = self._combo(body, 3, "Hairstyle", self._hair_var, [])
        self._set_type_names(1)

    def _build_colors(self, parent) -> None:
        body = self._card(
            parent,
            "Colors",
            "A preset sets hair and eye color together, as in the game. The "
            "sliders change each color afterwards.",
        )
        top = ctk.CTkFrame(body, fg_color="transparent")
        top.pack(fill="x")
        self._combo(
            top,
            0,
            "Color preset",
            self._color_var,
            app_data.color_names(),
            self._on_color_preset,
        )
        rows = ctk.CTkFrame(body, fg_color="transparent")
        rows.pack(fill="x", pady=(6, 0))
        self._hair_color = ColorSliders(rows, "Hair color")
        self._hair_color.frame.pack(side="left", anchor="n", padx=(0, 30))
        self._eye_color = ColorSliders(rows, "Eye color")
        self._eye_color.frame.pack(side="left", anchor="n")

    def _build_actions(self, parent) -> None:
        body = self._card(
            parent,
            "Copy and share",
            "Load the look of another character, from this save or another "
            "DSR save, or from a JSON file. Nothing is written until Apply "
            "Changes.",
        )
        self._share = AppearanceShareCard(
            body,
            source=ShareSource(
                characters=lambda save: [
                    (i, c.name, c) for i, c in enumerate(save.characters) if c
                ],
                load_save=DSRSave.from_file,
                save_filetypes=_SAVE_FILETYPES,
            ),
            get_save=self._get_dsr_save,
            on_character=lambda char: self.load_character(char, copy=True),
            on_export=self._export_json,
            on_import=self._import_json,
            show_toast=self._show_toast,
        )

    def _build_face(self, parent):
        """Build the face card, a few slider rows per stage."""
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", padx=10, pady=(6, 4))
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(10, 0))
        ctk.CTkLabel(head, text="Face", font=("Inter", 12, "bold")).pack(side="left")
        self._face_mode = ctk.CTkSegmentedButton(
            head, values=["Shape", "Skin"], command=self._show_face_page
        )
        self._face_mode.pack(side="right")
        self._face_mode.set("Shape")
        ctk.CTkLabel(
            card,
            text="The game's FaceGen controls. Moving one slider can move "
            "related ones. Values are relative: 0 is the average face.",
            font=("Inter", 10),
            text_color=ds.MUTED,
            justify="left",
            wraplength=700,
        ).pack(anchor="w", padx=12)
        self._shape_page = ctk.CTkFrame(card, fg_color="transparent")
        self._skin_page = ctk.CTkFrame(card, fg_color="transparent")
        yield from self._fill_sliders(self._shape_page, app_data.shape_controls())
        self._shape_page.pack(fill="x", padx=12, pady=(4, 10))

    def _show_face_page(self, mode: str) -> None:
        if mode == "Skin" and not self._skin_built:
            for _ in self._fill_sliders(self._skin_page, app_data.skin_controls()):
                pass
            self._skin_built = True
            self._refresh_sliders(reset_ranges=True)
        shown, hidden = (
            (self._skin_page, self._shape_page)
            if mode == "Skin"
            else (self._shape_page, self._skin_page)
        )
        hidden.pack_forget()
        shown.pack(fill="x", padx=12, pady=(4, 10))

    def _fill_sliders(self, page, controls):
        """Add slider rows, yielding every _ROWS_PER_STAGE rows."""
        sizes = Counter(ctl.group for ctl in controls)
        # One-slider groups share a final "Other" heading: "Temples: thin / wide".
        rows = [
            (_cap(ctl.group.lower()), _cap(ctl.label), ctl)
            for ctl in controls
            if sizes[ctl.group] > 1
        ] + [
            ("Other", f"{_cap(ctl.group.lower())}: {ctl.label}", ctl)
            for ctl in controls
            if sizes[ctl.group] == 1
        ]
        # si.ctl has two different controls with the same name; number them.
        names = Counter((g, t) for g, t, _ in rows)
        seen: Counter = Counter()
        group = None
        for heading, text, ctl in rows:
            if names[(heading, text)] > 1:
                seen[(heading, text)] += 1
                text = f"{text} {seen[(heading, text)]}"
            if heading != group:
                group = heading
                ctk.CTkLabel(page, text=heading, font=ds.BOLD).pack(
                    anchor="w", pady=(8, 0)
                )
            row = ctk.CTkFrame(page, fg_color="transparent")
            row.pack(fill="x")
            ctk.CTkLabel(row, text=text, width=_LABEL_WIDTH, anchor="w").pack(
                side="left"
            )
            readout = tk.StringVar(value="0")
            slider = ctk.CTkSlider(
                row,
                from_=-1.0,
                to=1.0,
                width=280,
                command=lambda v, c=ctl: self._on_slider(c, v),
            )
            slider.pack(side="left", padx=6)
            ctk.CTkLabel(row, textvariable=readout, width=44, anchor="e").pack(
                side="left"
            )
            self._sliders.append((ctl, slider, readout))
            if len(self._sliders) % _ROWS_PER_STAGE == 0:
                yield

    # --- State ------------------------------------------------------------------ #

    def _set_type_names(self, body_type: int) -> None:
        faces = app_data.face_names(body_type)
        hairs = app_data.hair_names(body_type)
        face_idx = self._index(self._face_combo, self._face_var)
        hair_idx = self._index(self._hair_combo, self._hair_var)
        self._face_combo.configure(values=faces)
        self._hair_combo.configure(values=hairs)
        self._face_var.set(faces[face_idx])
        self._hair_var.set(hairs[hair_idx])

    @staticmethod
    def _index(combo, var) -> int:
        values = list(combo.cget("values"))
        return values.index(var.get()) if var.get() in values else 0

    def _body_type(self) -> int:
        return _BODY_TYPES.index(self._body_var.get())

    def _on_body_change(self, _value=None) -> None:
        self._set_type_names(self._body_type())

    def _on_face_type(self, _value=None) -> None:
        face = app_data.face_preset(
            self._body_type(), self._index(self._face_combo, self._face_var)
        )
        self._coeffs = app_data.face_to_coeffs(face)
        self._refresh_sliders(reset_ranges=True)

    def _on_color_preset(self, _value=None) -> None:
        rgb = app_data.color_preset_rgb(
            app_data.color_names().index(self._color_var.get())
        )
        self._hair_color.set_rgb(rgb)
        self._eye_color.set_rgb(rgb)

    def _on_slider(self, ctl: FaceControl, position: float) -> None:
        self._coeffs = ctl.apply(self._coeffs, position * self._ranges[ctl])
        if self._refresh_job is not None:
            self.parent.after_cancel(self._refresh_job)
        self._refresh_job = self.parent.after(_REFRESH_MS, self._refresh_sliders)

    def _refresh_sliders(self, reset_ranges: bool = False) -> None:
        self._refresh_job = None
        for ctl, slider, readout in self._sliders:
            if reset_ranges or ctl not in self._ranges:
                self._ranges[ctl] = ctl.slider_range(self._coeffs)
            position = ctl.value(self._coeffs) / self._ranges[ctl]
            position = max(-1.0, min(1.0, position))
            slider.set(position)
            readout.set(str(round(position * _READOUT_SCALE)))

    def _current(self) -> Appearance:
        return Appearance(
            body_type=self._body_type(),
            physique=app_data.physique_names().index(self._physique_var.get()),
            face_type=self._index(self._face_combo, self._face_var),
            hair_type=self._index(self._hair_combo, self._hair_var),
            color_preset=app_data.color_names().index(self._color_var.get()),
            hair_rgba=self._hair_color.rgba(),
            eye_rgba=self._eye_color.rgba(),
            face_data=app_data.coeffs_to_face(self._coeffs),
        )

    def _show(self, app: Appearance) -> None:
        self._body_var.set(_BODY_TYPES[app.body_type])
        self._set_type_names(app.body_type)
        self._physique_var.set(app_data.physique_names()[app.physique])
        self._face_var.set(app_data.face_names(app.body_type)[app.face_type])
        self._hair_var.set(app_data.hair_names(app.body_type)[app.hair_type])
        self._color_var.set(app_data.color_names()[app.color_preset])
        self._hair_color.set_rgba(app.hair_rgba)
        self._eye_color.set_rgba(app.eye_rgba)
        self._coeffs = app_data.face_to_coeffs(app.face_data)
        self._refresh_sliders(reset_ranges=True)

    # --- Public ------------------------------------------------------------------ #

    def refresh(self) -> None:
        self._share.refresh()

    def load_slot(self, slot_idx: int) -> None:
        """Show the character in slot_idx; -1 or an empty slot clears the tab."""
        self.refresh()
        save = self._get_dsr_save()
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
        failed load clears it, so Apply All cannot write another
        character's."""
        try:
            app = Appearance.from_character(char)
            app.validate()
        except ValueError as exc:
            if not copy:
                self._tracker.clear()
            CTkMessageBox.showwarning(
                "Appearance Not Loaded",
                f"This character's appearance values are out of range: {exc}",
                parent=self.parent,
            )
            return False
        self._show(app)
        if not copy:
            self._tracker.mark_clean()
        return True

    def clear(self) -> None:
        self._tracker.clear()

    def changes(self) -> int:
        return self._tracker.changes()

    def discard(self) -> None:
        save = self._get_dsr_save()
        slot = self._slot
        if save is None or slot < 0 or save.characters[slot] is None:
            return
        self.load_character(save.characters[slot])

    def prepare(self):
        save = self._get_dsr_save()
        slot = self._slot
        if save is None or slot < 0 or save.characters[slot] is None:
            raise StageError("No character loaded.")
        try:
            app = self._current()
            app.validate()
        except ValueError as exc:
            raise StageError(str(exc)) from None
        char = save.characters[slot]

        def commit() -> None:
            app.apply_to(char)
            _sync_dir_appearance(save, slot, char)

        return commit

    def _state(self) -> dict:
        """Every value Apply All writes, FACE bytes one by one."""
        app = self._current()
        state = {
            "body": app.body_type,
            "physique": app.physique,
            "face_type": app.face_type,
            "hair_type": app.hair_type,
            "color_preset": app.color_preset,
            "hair_rgba": tuple(app.hair_rgba),
            "eye_rgba": tuple(app.eye_rgba),
        }
        state.update({f"face{i}": b for i, b in enumerate(app.face_data)})
        return state

    # --- Actions ----------------------------------------------------------------- #

    def _export_json(self) -> None:
        save = self._get_dsr_save()
        slot = self._slot
        name = (
            save.characters[slot].name
            if save is not None and slot >= 0 and save.characters[slot]
            else "appearance"
        )
        path = pick_file(
            save=True,
            title="Export Appearance",
            defaultextension=".json",
            initialfile=f"{name or 'appearance'}_dsr_appearance.json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        try:
            data = self._current().to_json()
            Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        except (OSError, ValueError) as exc:
            CTkMessageBox.showerror("Export Failed", str(exc), parent=self.parent)
            return
        self._show_toast("Appearance exported.")

    def _import_json(self) -> None:
        path = pick_file(
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
