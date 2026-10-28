"""
Appearance Tab
Manages character appearance presets (15 slots)
"""

import json
import os
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.editors import face_overrides
from er_save_manager.ui import palette
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import (
    FieldTracker,
    StageError,
    guard_before_write,
    save_writable,
    var_state,
    write_failed,
)
from er_save_manager.ui.toast import notify
from er_save_manager.ui.utils import bind_mousewheel, patch_combo_scroll, pick_file

_EYE_CARD_WIDTH = 270

# Slot 0 eye override choices, in event 1800 priority order
_EYE_CHOICES = {
    "None": face_overrides.NONE,
    "Frenzied Flame": face_overrides.FRENZIED_FLAME_EYES,
    "Bloody Finger (White Mask Varre)": face_overrides.BLOODY_FINGER_EYES,
    "Dragon Communion": face_overrides.DRAGON_COMMUNION_EYES,
}


class AppearanceTab:
    """Tab for character appearance preset management"""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_save_path_callback,
        reload_callback,
        show_toast_callback,
    ):
        """
        Initialize appearance tab

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_save_path_callback: Function that returns save file path
            reload_callback: Function to reload save file
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback
        self.show_toast = show_toast_callback
        self.preset_frames = []
        self.selected_slot = None
        self._warped_face_btn = None
        self.current_slot = None
        self._eye_names = dict(_EYE_CHOICES)
        self._eyes_var = tk.StringVar(value="")
        self._mark_var = tk.BooleanVar(value=False)
        self._eye_alterations_var = tk.BooleanVar(value=True)
        self._eye_widgets = []
        self._eye_combo = None
        self._eye_note = None
        self._eye_tracker = FieldTracker(
            var_state(
                {
                    "eyes": self._eyes_var,
                    "mark": self._mark_var,
                    "eye_alterations": self._eye_alterations_var,
                }
            ),
            {
                "mark": "Frenzied Flame mark",
                "eye_alterations": "Eye alterations shown",
            },
        )

    def setup_ui(self):
        """Setup the appearance tab UI"""
        scroll_frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(scroll_frame)

        header_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        header_frame.pack(fill=tk.X, padx=15, pady=(15, 10))

        ctk.CTkLabel(
            header_frame,
            text="Character Appearance & Presets",
            font=("Inter", 16, "bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_frame,
            text="Manage character appearance presets (15 slots)",
            font=("Inter", 11),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", pady=(2, 0))

        row = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        row.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        row.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew")
        list_container = ctk.CTkFrame(left, corner_radius=10)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        eye_card = self._build_eye_card(row)
        self._eye_side = None

        ctk.CTkLabel(
            list_container,
            text="Presets",
            font=("Inter", 12, "bold"),
        ).pack(pady=(12, 6), padx=12, anchor="w")

        self.list_frame = ctk.CTkScrollableFrame(
            list_container, corner_radius=8, height=280
        )
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        bind_mousewheel(self.list_frame)

        action_frame = ctk.CTkFrame(left, fg_color="transparent")
        action_frame.pack(fill=tk.X, pady=(0, 5))

        btn_row = ctk.CTkFrame(action_frame, fg_color="transparent")
        btn_row.pack(fill=tk.X, pady=(0, 4))

        ctk.CTkButton(
            btn_row,
            text="View Details",
            command=self.view_preset_details,
            width=130,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            btn_row,
            text="Delete Preset",
            command=self.delete_preset,
            width=130,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            btn_row,
            text="Copy to Another Save",
            command=self.copy_preset_to_save,
            width=170,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            btn_row,
            text="Browse Community Presets",
            command=self.open_preset_browser,
            width=200,
        ).pack(side=tk.LEFT)

        from er_save_manager.ui.settings import get_settings

        if get_settings().get("debug_warped_face_sliders", False):
            self._warped_face_btn = ctk.CTkButton(
                btn_row,
                text="Warped Face Sliders",
                command=self.open_warped_face_sliders,
                width=180,
                fg_color=("gray70", "gray30"),
            )
            self._warped_face_btn.pack(side=tk.LEFT, padx=(6, 0))

        io_row = ctk.CTkFrame(action_frame, fg_color="transparent")
        io_row.pack(fill=tk.X, pady=(0, 4))

        ctk.CTkButton(
            io_row,
            text="Export to JSON",
            command=self.export_presets,
            width=130,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            io_row,
            text="Import from JSON",
            command=self.import_preset_from_json,
            width=130,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            io_row,
            text="Export to Code",
            command=self.export_preset_to_code,
            width=130,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            io_row,
            text="Import from Code",
            command=self.import_preset_from_code,
            width=130,
        ).pack(side=tk.LEFT, padx=(0, 6))

        def place_eye_card(event=None):
            # Next to the presets when their buttons still fit beside it,
            # else below the buttons
            side = (
                row.winfo_width()
                >= action_frame.winfo_reqwidth() + eye_card.winfo_reqwidth() + 10
            )
            if side == self._eye_side:
                return
            self._eye_side = side
            if side:
                eye_card.grid(row=0, column=1, sticky="n", padx=(10, 0), pady=0)
            else:
                eye_card.grid(row=1, column=0, sticky="ew", padx=0, pady=(10, 0))

        place_eye_card()
        row.bind("<Configure>", place_eye_card, add="+")

    def _build_eye_card(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=10, width=_EYE_CARD_WIDTH)
        ctk.CTkLabel(
            card,
            text="Eye overrides",
            font=("Inter", 12, "bold"),
        ).pack(pady=(12, 2), padx=12, anchor="w")
        ctk.CTkLabel(
            card,
            text=(
                "Eyes and marks the game puts over the selected character's face. "
                "The load screen shows the change after the next in-game save."
            ),
            font=("Inter", 11),
            text_color=("#808080", "#a0a0a0"),
            wraplength=_EYE_CARD_WIDTH - 24,
            justify="left",
        ).pack(pady=(0, 8), padx=12, anchor="w")

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill=tk.X, padx=12)
        ctk.CTkLabel(grid, text="Eyes:").grid(row=0, column=0, sticky="w")
        self._eye_combo = ctk.CTkComboBox(
            grid,
            variable=self._eyes_var,
            values=list(self._eye_names),
            state="readonly",
            width=_EYE_CARD_WIDTH - 24,
        )
        self._eye_combo.grid(row=1, column=0, sticky="w", pady=(0, 4))
        patch_combo_scroll(self._eye_combo)
        mark = ctk.CTkCheckBox(
            grid, text="Frenzied Flame mark", variable=self._mark_var
        )
        mark.grid(row=2, column=0, sticky="w", pady=4)
        alterations = ctk.CTkCheckBox(
            grid,
            text="Eye alterations shown",
            variable=self._eye_alterations_var,
        )
        alterations.grid(row=3, column=0, sticky="w", pady=4)
        self._eye_widgets = [self._eye_combo, mark, alterations]

        self._eye_note = ctk.CTkLabel(
            card,
            text="",
            font=("Inter", 11),
            text_color=palette.WARNING_TEXT,
            wraplength=_EYE_CARD_WIDTH - 24,
            justify="left",
        )
        self._eye_note.pack(pady=(4, 0), padx=12, anchor="w")
        ctk.CTkFrame(card, fg_color="transparent", height=6).pack()
        self._set_eye_card_enabled(False)
        return card

    def _set_eye_card_enabled(self, enabled: bool) -> None:
        for widget in self._eye_widgets:
            if not enabled:
                state = "disabled"
            elif widget is self._eye_combo:
                state = "readonly"
            else:
                state = "normal"
            widget.configure(state=state)

    def _eye_label(self, eye_id: int) -> str:
        for name, value in _EYE_CHOICES.items():
            if value == eye_id:
                return name
        return f"Other ({eye_id})"

    def load_slot(self, slot_idx: int) -> None:
        """Show the eye overrides of the character in slot_idx; -1 or an
        empty slot clears the card."""
        if self._eye_combo is None:
            return
        save_file = self.get_save_file()
        if (
            save_file is None
            or not 0 <= slot_idx < 10
            or slot_idx not in save_file.get_active_slots()
        ):
            self.current_slot = None
            self._eye_tracker.clear()
            self._eyes_var.set("")
            self._mark_var.set(False)
            self._eye_alterations_var.set(True)
            self._eye_note.configure(text="")
            self._set_eye_card_enabled(False)
            return
        self.current_slot = slot_idx
        state = face_overrides.read(save_file, slot_idx)
        self._eye_names = dict(_EYE_CHOICES)
        label = self._eye_label(state.eyes)
        # An id the game never sets stays selectable so it is kept as is
        self._eye_names[label] = state.eyes
        self._eye_combo.configure(values=list(self._eye_names))
        self._eyes_var.set(label)
        self._mark_var.set(state.mark)
        self._eye_alterations_var.set(state.eye_alterations)
        self._eye_note.configure(
            text=(
                "Flag 9434 is set: the game removes Bloody Finger and Dragon "
                "Communion eyes the next time an eye flag changes."
                if state.eyes_blocked
                else ""
            )
        )
        self._set_eye_card_enabled(True)
        self._eye_tracker.mark_clean()

    def eye_changes(self) -> int:
        return self._eye_tracker.changes()

    def eye_details(self):
        return self._eye_tracker.details()

    def discard_eyes(self) -> None:
        if self.current_slot is not None:
            self.load_slot(self.current_slot)

    def prepare_eyes(self):
        """Validate and return the function that writes the eye overrides
        into the in-memory save (Apply All in the main window)."""
        save_file = self.get_save_file()
        if not save_file or self.current_slot is None:
            raise StageError("Load a character slot first.")
        slot_idx = self.current_slot
        try:
            eyes = self._eye_names[self._eyes_var.get()]
        except KeyError:
            raise StageError("Pick the eyes for the character.") from None
        state = face_overrides.FaceOverrides(
            eyes=eyes,
            mark=self._mark_var.get(),
            eye_alterations=self._eye_alterations_var.get(),
        )

        def commit() -> None:
            face_overrides.write(save_file, slot_idx, state)

        return commit

    # Byte indices within unk0x6c and their labels, grouped by face region.
    # Indices with no observable effect are omitted.
    _WARPED_FACE_SLIDERS = [
        # Eyes / chin area
        ("Eyes/Chin A", 43),
        ("Eyes/Chin B", 44),
        ("Eyes/Chin C", 45),
        # Upper face (forehead/brow)
        ("Upper Face A", 47),
        ("Upper Face B", 48),
        ("Upper Face C", 49),
        # Mouth
        ("Mouth A", 50),
        ("Mouth B", 51),
        ("Mouth C", 52),
        # Chin
        ("Chin A", 53),
        ("Chin B", 54),
        ("Chin C", 55),
        ("Chin D", 56),
        ("Chin E", 57),
        ("Chin F", 58),
        # Nose
        ("Nose A", 59),
        ("Nose B", 60),
        ("Nose C", 61),
        ("Nose D", 62),
    ]

    def open_warped_face_sliders(self):
        """Open the warped face deformation slider dialog for the selected preset."""
        from er_save_manager.ui.messagebox import CTkMessageBox

        if self.selected_slot is None:
            notify(self.parent, "Select a preset first.", "warning")
            return

        save_file = self.get_save_file()
        if not save_file:
            notify(self.parent, "Load a save file first.", "warning")
            return

        try:
            presets = save_file.get_character_presets()
            preset = presets.presets[self.selected_slot]

            if preset.is_empty():
                notify(self.parent, "Selected preset slot is empty.", "warning")
                return
        except Exception as e:
            CTkMessageBox.showerror(
                "Preset Unavailable", f"Failed to read preset:\n{e}", parent=self.parent
            )
            return

        from er_save_manager.ui import dialog_style as ds

        dialog = ds.create(
            self.parent, f"Warped Face Sliders - Preset {self.selected_slot + 1}"
        )
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        btn_row = ctk.CTkFrame(main, fg_color="transparent")
        btn_row.pack(side=tk.BOTTOM, fill=tk.X, pady=(14, 0))
        ds.header(
            main,
            f"Warped Face Sliders, Preset {self.selected_slot + 1}",
            font=ds.TITLE_LARGE,
        )

        unk = list(preset.unk0x6c)

        slider_vars = {}
        value_labels = {}
        for _label, idx in self._WARPED_FACE_SLIDERS:
            slider_vars[idx] = tk.IntVar(value=unk[idx])

        def build(body):
            groups: dict[str, list] = {}
            for label, idx in self._WARPED_FACE_SLIDERS:
                groups.setdefault(label.rsplit(" ", 1)[0], []).append((label, idx))
            for group, sliders in groups.items():
                ctk.CTkLabel(body, text=group, font=ds.BOLD).pack(
                    anchor="w", pady=(10, 0)
                )
                box = ds.box(body, pady=(4, 0))
                for i, (label, idx) in enumerate(sliders):
                    pady = (8 if i == 0 else 2, 8 if i == len(sliders) - 1 else 2)
                    ctk.CTkLabel(
                        box, text=label, font=ds.FONT, width=110, anchor="w"
                    ).grid(row=i, column=0, sticky="w", padx=(12, 8), pady=pady)
                    val_label = ctk.CTkLabel(
                        box, text=str(slider_vars[idx].get()), font=ds.FONT, width=36
                    )
                    value_labels[idx] = val_label
                    ctk.CTkSlider(
                        box,
                        from_=0,
                        to=255,
                        number_of_steps=255,
                        variable=slider_vars[idx],
                        width=200,
                        command=lambda v, lbl=val_label, var=slider_vars[idx]: (
                            var.set(int(v)),
                            lbl.configure(text=str(int(v))),
                        ),
                    ).grid(row=i, column=1, pady=pady)
                    val_label.grid(row=i, column=2, padx=(4, 12), pady=pady)

        ds.content(main, build, max_height=480, width=400, pady=(4, 0))

        def apply_full_warp():
            for idx, var in slider_vars.items():
                var.set(0)
                value_labels[idx].configure(text="0")

        def do_confirm():
            if not guard_before_write("change the preset"):
                return
            try:
                new_unk = list(preset.unk0x6c)
                for idx, var in slider_vars.items():
                    new_unk[idx] = var.get()

                preset.unk0x6c = bytes(new_unk)
                preset.unk0xb1 = bytes(len(preset.unk0xb1))
                preset.face_data_marker = 0

                save_path = self.get_save_path()
                if save_path:
                    from er_save_manager.backup.manager import BackupManager

                    manager = BackupManager(Path(save_path))
                    manager.create_backup(
                        description=f"before_warped_face_sliders_slot_{self.selected_slot + 1}",
                        operation="warped_face_sliders",
                        save=save_file,
                    )

                save_file.import_preset(preset, self.selected_slot)
                save_file.recalculate_checksums()
                if save_path:
                    save_file.to_file(Path(save_path))

                if self.reload_save:
                    self.reload_save()

                dialog.destroy()
                self.show_toast(
                    f"Warped face sliders saved to Preset {self.selected_slot + 1}",
                    duration=2500,
                )

            except Exception as e:
                CTkMessageBox.showerror(
                    "Save Failed", f"Failed to save:\n{e}", parent=dialog
                )
                import traceback

                traceback.print_exc()

        ds.button(btn_row, "Full Warp", apply_full_warp, primary=False).pack(
            side=tk.LEFT
        )
        ds.button(btn_row, "Cancel", dialog.destroy, primary=False).pack(side=tk.RIGHT)
        ds.button(btn_row, "Confirm", do_confirm).pack(side=tk.RIGHT, padx=(0, 8))
        ds.finish(dialog, self.parent)

    def open_preset_browser(self):
        """Open the preset browser dialog."""
        from er_save_manager.ui.dialogs.preset_browser import EnhancedPresetBrowser

        browser = EnhancedPresetBrowser(self.parent, self)
        browser.show()

    def select_preset(self, slot_idx, frame):
        """Handle preset selection"""
        from er_save_manager.ui import dialog_style as ds

        self.selected_slot = slot_idx

        for i, f in enumerate(self.preset_frames):
            ds.select_card_row(f, i == slot_idx)

    def load_presets(self):
        """Load character presets"""
        from er_save_manager.ui import dialog_style as ds

        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.preset_frames = []
        self.selected_slot = None

        save_file = self.get_save_file()
        if not save_file:
            return

        try:
            presets = save_file.get_character_presets()
            if not presets:
                ctk.CTkLabel(
                    self.list_frame, text="No presets found", text_color="gray"
                ).pack(pady=10)
                return

            for i in range(15):
                try:
                    preset = presets.presets[i]
                    if preset.is_empty():
                        detail = "Empty"
                    else:
                        body_type_value = (
                            preset.get_body_type()
                            if hasattr(preset, "get_body_type")
                            else 0
                        )
                        detail = "Type A" if body_type_value == 1 else "Type B"
                except Exception:
                    detail = "Error"

                frame = ds.card_row(
                    self.list_frame,
                    f"Preset {i + 1}",
                    detail,
                    on_click=lambda idx=i: self.select_preset(idx, None),
                )
                self.preset_frames.append(frame)

        except Exception as e:
            ctk.CTkLabel(
                self.list_frame,
                text="Error loading presets",
                text_color=("red", "lightcoral"),
            ).pack(pady=10)
            print(f"Error loading presets: {e}")
            import traceback

            traceback.print_exc()

    def view_preset_details(self):
        """View detailed preset information"""
        save_file = self.get_save_file()
        if not save_file:
            notify(self.parent, "Load a save file first.", "warning")
            return

        if self.selected_slot is None:
            notify(self.parent, "Select a preset to view.", "warning")
            return

        preset_idx = self.selected_slot

        try:
            presets = save_file.get_character_presets()
            if not presets or preset_idx >= len(presets.presets):
                CTkMessageBox.showerror(
                    "Preset Unavailable",
                    "Could not load preset data",
                    parent=self.parent,
                )
                return

            preset = presets.presets[preset_idx]

            if preset.is_empty():
                notify(self.parent, f"Preset {preset_idx + 1} is empty", "info")
                return

            body_type_value = preset.get_body_type()
            body_type = "Type A" if body_type_value == 1 else "Type B"

            def get_attr(obj, name, default=0):
                """Safely get attribute with default"""
                return getattr(obj, name, default)

            def get_rgb(obj, prefix):
                """Get RGB values for a color"""
                r = get_attr(obj, f"{prefix}_r")
                g = get_attr(obj, f"{prefix}_g")
                b = get_attr(obj, f"{prefix}_b")
                return f"RGB({r}, {g}, {b})"

            info = []
            info.append("BASIC INFORMATION")
            info.append("=" * 50)
            info.append(f"Body Type: {body_type}")
            info.append(f"Face Model: {preset.face_model}")
            info.append(f"Hair Model: {preset.hair_model}")
            info.append(f"Eyebrow Model: {preset.eyebrow_model}")
            info.append(f"Beard Model: {preset.beard_model}")
            info.append(f"Eyepatch Model: {get_attr(preset, 'eyepatch_model')}")
            info.append("")

            info.append("BODY PROPORTIONS")
            info.append("=" * 50)
            info.append(f"Head Size: {preset.head_size}")
            info.append(f"Chest Size: {preset.chest_size}")
            info.append(f"Abdomen Size: {preset.abdomen_size}")
            info.append(f"Arms Size: {preset.arms_size}")
            info.append(f"Legs Size: {preset.legs_size}")
            if hasattr(preset, "body_hair"):
                info.append(f"Body Hair: {preset.body_hair}")
            info.append("")

            info.append("FACE - GENERAL")
            info.append("=" * 50)
            info.append(f"Apparent Age: {preset.apparent_age}")
            info.append(f"Facial Aesthetic: {preset.facial_aesthetic}")
            info.append(f"Form Emphasis: {get_attr(preset, 'form_emphasis')}")
            info.append(f"Face Protrusion: {get_attr(preset, 'face_protrusion')}")
            info.append(
                f"Vertical Face Ratio: {get_attr(preset, 'vertical_face_ratio')}"
            )
            info.append(
                f"Horizontal Face Ratio: {get_attr(preset, 'horizontal_face_ratio')}"
            )
            info.append(
                f"Facial Feature Slant: {get_attr(preset, 'facial_feature_slant')}"
            )
            info.append("")

            info.append("FOREHEAD & BROW")
            info.append("=" * 50)
            info.append(f"Brow Ridge Height: {get_attr(preset, 'brow_ridge_height')}")
            info.append(f"Inner Brow Ridge: {get_attr(preset, 'inner_brow_ridge')}")
            info.append(f"Outer Brow Ridge: {get_attr(preset, 'outer_brow_ridge')}")
            info.append(f"Forehead Depth: {get_attr(preset, 'forehead_depth')}")
            info.append(
                f"Forehead Protrusion: {get_attr(preset, 'forehead_protrusion')}"
            )
            info.append("")

            info.append("EYES")
            info.append("=" * 50)
            info.append(f"Eye Position: {preset.eye_position}")
            info.append(f"Eye Size: {preset.eye_size}")
            info.append(f"Eye Slant: {get_attr(preset, 'eye_slant')}")
            info.append(f"Eye Spacing: {get_attr(preset, 'eye_spacing')}")
            if hasattr(preset, "right_eye_position"):
                info.append(f"Right Eye Position: {preset.right_eye_position}")
            if hasattr(preset, "left_eye_position"):
                info.append(
                    f"Left Eye Position: {get_attr(preset, 'left_eye_position')}"
                )
            info.append("")

            info.append("NOSE")
            info.append("=" * 50)
            info.append(f"Nose Size: {preset.nose_size}")
            info.append(
                f"Nose Forehead Ratio: {get_attr(preset, 'nose_forehead_ratio')}"
            )
            info.append(f"Nose Ridge Depth: {get_attr(preset, 'nose_ridge_depth')}")
            info.append(f"Nose Ridge Length: {get_attr(preset, 'nose_ridge_length')}")
            info.append(f"Nose Position: {get_attr(preset, 'nose_position')}")
            info.append(f"Nose Tip Height: {get_attr(preset, 'nose_tip_height')}")
            info.append(f"Nose Protrusion: {get_attr(preset, 'nose_protrusion')}")
            info.append(f"Nose Bridge Height: {get_attr(preset, 'nose_bridge_height')}")
            info.append(f"Nostril Slant: {get_attr(preset, 'nostril_slant')}")
            info.append(f"Nostril Size: {get_attr(preset, 'nostril_size')}")
            info.append(f"Nostril Width: {get_attr(preset, 'nostril_width')}")
            info.append("")

            info.append("MOUTH & LIPS")
            info.append("=" * 50)
            info.append(f"Mouth Width: {preset.mouth_width}")
            info.append(f"Mouth Position: {get_attr(preset, 'mouth_position')}")
            info.append(f"Mouth Protrusion: {get_attr(preset, 'mouth_protrusion')}")
            info.append(f"Mouth Slant: {get_attr(preset, 'mouth_slant')}")
            info.append(f"Mouth Expression: {get_attr(preset, 'mouth_expression')}")
            info.append(
                f"Mouth-Chin Distance: {get_attr(preset, 'mouth_chin_distance')}"
            )
            info.append(f"Lip Shape: {get_attr(preset, 'lip_shape')}")
            info.append(f"Lip Size: {get_attr(preset, 'lip_size')}")
            info.append(f"Lip Fullness: {get_attr(preset, 'lip_fullness')}")
            info.append(f"Lip Protrusion: {get_attr(preset, 'lip_protrusion')}")
            info.append(f"Lip Thickness: {get_attr(preset, 'lip_thickness')}")
            info.append(f"Occlusion: {get_attr(preset, 'occlusion')}")
            info.append("")

            info.append("CHEEKS & JAW")
            info.append("=" * 50)
            info.append(f"Cheekbone Height: {get_attr(preset, 'cheekbone_height')}")
            info.append(f"Cheekbone Depth: {get_attr(preset, 'cheekbone_depth')}")
            info.append(f"Cheekbone Width: {get_attr(preset, 'cheekbone_width')}")
            info.append(
                f"Cheekbone Protrusion: {get_attr(preset, 'cheekbone_protrusion')}"
            )
            info.append(f"Cheeks: {get_attr(preset, 'cheeks')}")
            if hasattr(preset, "cheeks_color_intensity"):
                info.append(f"Cheeks Color Intensity: {preset.cheeks_color_intensity}")
            info.append(f"Jaw Protrusion: {get_attr(preset, 'jaw_protrusion')}")
            info.append(f"Jaw Width: {get_attr(preset, 'jaw_width')}")
            info.append(f"Lower Jaw: {get_attr(preset, 'lower_jaw')}")
            info.append(f"Jaw Contour: {get_attr(preset, 'jaw_contour')}")
            info.append("")

            info.append("CHIN")
            info.append("=" * 50)
            info.append(f"Chin Tip Position: {get_attr(preset, 'chin_tip_position')}")
            info.append(f"Chin Length: {get_attr(preset, 'chin_length')}")
            info.append(f"Chin Protrusion: {get_attr(preset, 'chin_protrusion')}")
            info.append(f"Chin Depth: {get_attr(preset, 'chin_depth')}")
            info.append(f"Chin Size: {get_attr(preset, 'chin_size')}")
            info.append(f"Chin Height: {get_attr(preset, 'chin_height')}")
            info.append(f"Chin Width: {get_attr(preset, 'chin_width')}")
            info.append("")

            info.append("COLORS - SKIN & HAIR")
            info.append("=" * 50)
            info.append(f"Skin Color: {get_rgb(preset, 'skin_color')}")
            info.append(f"Skin Luster: {preset.skin_luster}")
            info.append(f"Dark Circles: {get_attr(preset, 'dark_circles')}")
            info.append(f"Dark Circle Color: {get_rgb(preset, 'dark_circle_color')}")
            if hasattr(preset, "cheek_color_r"):
                info.append(f"Cheek Color: {get_rgb(preset, 'cheek_color')}")
            info.append(f"Stubble: {get_attr(preset, 'stubble')}")
            if hasattr(preset, "body_hair_color_r"):
                info.append(f"Body Hair Color: {get_rgb(preset, 'body_hair_color')}")
            if hasattr(preset, "beard_color_r"):
                info.append(f"Beard Color: {get_rgb(preset, 'beard_color')}")
            info.append("")

            info.append("COLORS - EYES")
            info.append("=" * 50)
            if hasattr(preset, "left_iris_color_r"):
                info.append(f"Left Iris Color: {get_rgb(preset, 'left_iris_color')}")
            elif hasattr(preset, "left_eye_color_r"):
                info.append(f"Left Eye Color: {get_rgb(preset, 'left_eye_color')}")
            if hasattr(preset, "right_iris_color_r"):
                info.append(f"Right Iris Color: {get_rgb(preset, 'right_iris_color')}")
            elif hasattr(preset, "right_eye_color_r"):
                info.append(f"Right Eye Color: {get_rgb(preset, 'right_eye_color')}")
            if hasattr(preset, "left_eye_clouding"):
                info.append(f"Left Eye Clouding: {preset.left_eye_clouding}")
                info.append(
                    f"Left Eye Clouding Color: {get_rgb(preset, 'left_eye_clouding_color')}"
                )
            if hasattr(preset, "right_eye_clouding"):
                info.append(f"Right Eye Clouding: {preset.right_eye_clouding}")
                info.append(
                    f"Right Eye Clouding Color: {get_rgb(preset, 'right_eye_clouding_color')}"
                )
            if hasattr(preset, "left_eye_white_color_r"):
                info.append(
                    f"Left Eye White: {get_rgb(preset, 'left_eye_white_color')}"
                )
            if hasattr(preset, "right_eye_white_color_r"):
                info.append(
                    f"Right Eye White: {get_rgb(preset, 'right_eye_white_color')}"
                )
            if hasattr(preset, "eyebrow_color_r"):
                info.append(f"Eyebrow Color: {get_rgb(preset, 'eyebrow_color')}")
            if hasattr(preset, "eyelash_color_r"):
                info.append(f"Eyelash Color: {get_rgb(preset, 'eyelash_color')}")
            info.append("")

            info.append("MAKEUP & DECORATIVE")
            info.append("=" * 50)
            if hasattr(preset, "eye_liner"):
                info.append(f"Eye Liner: {preset.eye_liner}")
                info.append(f"Eye Liner Color: {get_rgb(preset, 'eye_liner_color')}")
            if hasattr(preset, "eye_shadow_upper"):
                info.append(f"Eye Shadow Upper: {preset.eye_shadow_upper}")
                info.append(
                    f"Eye Shadow Upper Color: {get_rgb(preset, 'eye_shadow_upper_color')}"
                )
            if hasattr(preset, "eye_shadow_lower"):
                info.append(f"Eye Shadow Lower: {preset.eye_shadow_lower}")
                info.append(
                    f"Eye Shadow Lower Color: {get_rgb(preset, 'eye_shadow_lower_color')}"
                )
            if hasattr(preset, "lip_stick"):
                info.append(f"Lip Stick: {preset.lip_stick}")
                info.append(f"Lip Stick Color: {get_rgb(preset, 'lip_stick_color')}")
            if hasattr(preset, "tattoo_mark_type"):
                info.append(f"Tattoo Mark Type: {preset.tattoo_mark_type}")
                info.append(
                    f"Tattoo Mark Color: {get_rgb(preset, 'tattoo_mark_color')}"
                )
                info.append(
                    f"Tattoo Position Vertical: {get_attr(preset, 'tattoo_mark_position_vertical')}"
                )
                info.append(
                    f"Tattoo Position Horizontal: {get_attr(preset, 'tattoo_mark_position_horizontal')}"
                )
                info.append(f"Tattoo Angle: {get_attr(preset, 'tattoo_mark_angle')}")
                info.append(
                    f"Tattoo Expansion: {get_attr(preset, 'tattoo_mark_expansion')}"
                )
                info.append(f"Tattoo Flip: {get_attr(preset, 'tattoo_mark_flip')}")
            if hasattr(preset, "tattoo_mark_shininess"):
                info.append(f"Tattoo Shininess: {preset.tattoo_mark_shininess}")
            if hasattr(preset, "tattoo_glow_color_r"):
                info.append(
                    f"Tattoo Glow Color: {get_rgb(preset, 'tattoo_glow_color')}"
                )

            self._show_preset_details(preset_idx, info)

        except Exception as e:
            CTkMessageBox.showerror(
                "Preset View Failed", f"Failed to view preset:\n{str(e)}"
            )
            import traceback

            traceback.print_exc()

    def _show_preset_details(self, preset_idx, info: list[str]) -> None:
        """Show the "Key: value" lines of info as boxed sections in two columns.

        A section starts with its title line followed by a line of "=".
        """
        from er_save_manager.ui import dialog_style as ds

        sections: list[tuple[str, list[tuple[str, str]]]] = []
        for i, line in enumerate(info):
            if line.startswith("="):
                continue
            if i + 1 < len(info) and info[i + 1].startswith("="):
                sections.append((line.title(), []))
            elif line and sections:
                key, _, value = line.partition(": ")
                sections[-1][1].append((key, value))

        dialog = ds.create(self.parent, f"Preset {preset_idx + 1} Details")
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        ds.button_row(main, [{"text": "Close", "command": dialog.destroy}])
        ds.header(
            main, f"Preset {preset_idx + 1}: Character Appearance", font=ds.TITLE_LARGE
        )

        def build(body):
            body.grid_columnconfigure((0, 1), weight=1, uniform="col")
            # Fill the shorter column first so both end at about the same height
            heights = [0, 0]
            for title, rows in sections:
                col = 0 if heights[0] <= heights[1] else 1
                heights[col] += len(rows) + 2
                cell = ctk.CTkFrame(body, fg_color="transparent")
                cell.grid(
                    row=len(cell.master.grid_slaves(column=col)),
                    column=col,
                    sticky="new",
                    padx=(0, 10) if col == 0 else (10, 0),
                )
                ctk.CTkLabel(cell, text=title, font=ds.BOLD).pack(
                    anchor="w", pady=(10, 0)
                )
                box = ds.box(cell, pady=(4, 0))
                box.grid_columnconfigure(1, weight=1)
                for r, (key, value) in enumerate(rows):
                    pady = (6 if r == 0 else 1, 6 if r == len(rows) - 1 else 1)
                    ctk.CTkLabel(
                        box, text=key, font=ds.SMALL, text_color=ds.MUTED
                    ).grid(row=r, column=0, sticky="w", padx=(12, 12), pady=pady)
                    ctk.CTkLabel(box, text=value, font=ds.SMALL).grid(
                        row=r, column=1, sticky="w", padx=(0, 12), pady=pady
                    )

        ds.content(main, build, max_height=560, width=700, pady=(4, 0))
        ds.finish(dialog, self.parent)

    def _build_preset_export_dialog(
        self, presets_data, title, subtitle, action_label, on_export
    ):
        """Build a preset checkbox selection dialog. on_export(selected_indices, dialog) does the export work."""
        available_presets = []
        for i in range(15):
            try:
                preset = presets_data.presets[i]
                if not preset.is_empty():
                    body_type_value = (
                        preset.get_body_type()
                        if hasattr(preset, "get_body_type")
                        else 0
                    )
                    body_type = "Type A" if body_type_value == 1 else "Type B"
                    available_presets.append((i, f"Preset {i + 1}: {body_type}"))
                else:
                    available_presets.append((i, f"Preset {i + 1}: Empty"))
            except Exception:
                available_presets.append((i, f"Preset {i + 1}: Error"))

        if not any(
            label
            for idx, label in available_presets
            if "Empty" not in label and "Error" not in label
        ):
            notify(self.parent, "No presets available to export", "warning")
            return

        from er_save_manager.ui import dialog_style as ds

        dialog = ds.create(self.parent, title)
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        checkbox_data = []

        def select_all():
            for var, _idx, label in checkbox_data:
                if "Empty" not in label and "Error" not in label:
                    var.set(True)

        def select_none():
            for var, _idx, _label in checkbox_data:
                var.set(False)

        def do_export():
            selected_indices = [idx for var, idx, label in checkbox_data if var.get()]

            if not selected_indices:
                notify(dialog, "Select at least one preset to export", "warning")
                return

            on_export(selected_indices, dialog)

        ds.button_row(
            main,
            [
                {"text": action_label, "command": do_export, "width": 140},
                {"text": "Cancel", "command": dialog.destroy, "primary": False},
            ],
        )
        ds.header(main, title, font=ds.TITLE_LARGE)
        ctk.CTkLabel(main, text=subtitle, font=ds.SMALL, text_color=ds.MUTED).pack(
            anchor=tk.W, pady=(2, 10)
        )

        controls = ctk.CTkFrame(main, fg_color="transparent")
        controls.pack(fill=tk.X)
        ctk.CTkLabel(controls, text="Presets", font=ds.BOLD).pack(side=tk.LEFT)
        ds.button(
            controls, "None", select_none, primary=False, width=70, height=26
        ).pack(side=tk.RIGHT)
        ds.button(controls, "All", select_all, primary=False, width=70, height=26).pack(
            side=tk.RIGHT, padx=(0, 6)
        )

        box = ds.box(main, pady=(6, 0))
        rows = (len(available_presets) + 1) // 2
        for n, (idx, label) in enumerate(available_presets):
            usable = "Empty" not in label and "Error" not in label
            var = tk.BooleanVar(value=usable)
            cb = ctk.CTkCheckBox(box, text=label, variable=var, font=ds.FONT)
            row, col = n % rows, n // rows
            cb.grid(
                row=row,
                column=col,
                sticky="w",
                padx=(12, 24),
                pady=(8 if row == 0 else 3, 8 if row == rows - 1 else 3),
            )
            if not usable:
                cb.configure(state="disabled")
            checkbox_data.append((var, idx, label))

        ds.finish(dialog, self.parent, min_width=420)

    def _preset_export_payload(self, presets_data, selected_indices):
        """Build the {"presets": [...]} payload dict for the given preset indices."""
        export_data = {"presets": []}
        for idx in selected_indices:
            preset = presets_data.presets[idx]
            preset_dict = preset.to_dict() if hasattr(preset, "to_dict") else {}
            export_data["presets"].append(preset_dict)
        return export_data

    def _show_share_code(self, code, description):
        """Show a dialog with a generated share code and a copy button."""
        from er_save_manager.ui import dialog_style as ds

        ds.show_code(
            self.parent,
            "Share Code",
            f"Shared {description}",
            code,
            lambda: self.show_toast("Code copied to clipboard", duration=2000),
            font=ds.TITLE_LARGE,
        )

    def _ask_code(self, title, text):
        """Single-line input dialog for a share code; None when cancelled."""
        from er_save_manager.ui import dialog_style as ds

        code = ds.ask_string(self.parent, title, text, font=ds.TITLE_LARGE)
        return code.strip() if code is not None else None

    def export_presets(self):
        """Export selected presets to JSON"""
        save_file = self.get_save_file()
        if not save_file:
            notify(self.parent, "Load a save file first.", "warning")
            return

        try:
            presets_data = save_file.get_character_presets()
            if not presets_data:
                CTkMessageBox.showerror(
                    "Preset Unavailable",
                    "Could not load preset data",
                    parent=self.parent,
                )
                return

            def on_export(selected_indices, dialog):
                output_path = pick_file(
                    title="Export Presets",
                    save=True,
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                )
                if not output_path:
                    return

                try:
                    export_data = self._preset_export_payload(
                        presets_data, selected_indices
                    )
                    with open(output_path, "w") as f:
                        json.dump(export_data, f, indent=2)

                    notify(
                        dialog,
                        f"Exported {len(selected_indices)} preset(s) to:\n{os.path.basename(output_path)}",
                        "success",
                    )
                    dialog.destroy()
                except Exception as e:
                    CTkMessageBox.showerror(
                        "Export Failed", f"Export failed:\n{str(e)}", parent=dialog
                    )
                    import traceback

                    traceback.print_exc()

            self._build_preset_export_dialog(
                presets_data,
                "Select Presets to Export",
                "Choose which presets to include in the JSON file",
                "Export Selected",
                on_export,
            )

        except Exception as e:
            CTkMessageBox.showerror(
                "Export Failed",
                f"Failed to prepare export:\n{str(e)}",
                parent=self.parent,
            )
            import traceback

            traceback.print_exc()

    def export_preset_to_code(self):
        """Export selected presets to a shareable code via Supabase."""
        save_file = self.get_save_file()
        if not save_file:
            notify(self.parent, "Load a save file first.", "warning")
            return

        try:
            presets_data = save_file.get_character_presets()
            if not presets_data:
                CTkMessageBox.showerror(
                    "Preset Unavailable",
                    "Could not load preset data",
                    parent=self.parent,
                )
                return

            def on_export(selected_indices, dialog):
                from er_save_manager.data.appearance_sharing import share_preset

                export_data = self._preset_export_payload(
                    presets_data, selected_indices
                )
                code = share_preset(export_data)
                if not code:
                    CTkMessageBox.showerror(
                        "Upload Failed",
                        "Failed to upload preset. Check your connection.",
                        parent=dialog,
                    )
                    return

                dialog.destroy()
                self._show_share_code(code, f"{len(selected_indices)} preset(s)")

            self._build_preset_export_dialog(
                presets_data,
                "Select Presets to Share",
                "Choose which presets to include in the share code",
                "Get Share Code",
                on_export,
            )

        except Exception as e:
            CTkMessageBox.showerror(
                "Export Failed",
                f"Failed to prepare export:\n{str(e)}",
                parent=self.parent,
            )
            import traceback

            traceback.print_exc()

    def occupied_slots(self, save_file, slots) -> list[int]:
        """0-based slots among slots that hold a preset in save_file."""
        presets = save_file.get_character_presets()
        if not presets:
            return []
        return [s for s in slots if not presets.presets[s].is_empty()]

    def _confirm_overwrite(self, save_file, slots, parent) -> bool:
        """Ask before replacing presets; True when none of slots is occupied."""
        occupied = self.occupied_slots(save_file, slots)
        if not occupied:
            return True
        if len(occupied) == 1:
            text = f"Preset slot {occupied[0] + 1} already holds a preset. Replace it?"
        else:
            names = ", ".join(str(s + 1) for s in occupied)
            text = f"Preset slots {names} already hold presets. Replace them?"
        return CTkMessageBox.askyesno("Replace Presets", text, parent=parent)

    def write_presets(self, save_file, change, description, operation, parent):
        """Back up the loaded save, run change, write the save and reload it.

        change returns False when it could not change the presets; the save
        is then reloaded from disk without writing. Returns True on success.
        """
        if not save_writable():
            return False
        save_path = self.get_save_path()
        if save_path:
            BackupManager(Path(save_path)).create_backup(
                description=description, operation=operation, save=save_file
            )
        if not change():
            if self.reload_save:
                self.reload_save()
            CTkMessageBox.showerror(
                "Preset Not Written",
                "The preset could not be written to the save. Nothing was changed.",
                parent=parent,
            )
            return False
        try:
            save_file.recalculate_checksums()
            if save_path:
                save_file.to_file(Path(save_path))
        except Exception as exc:
            write_failed(exc, parent)
            return False
        if self.reload_save:
            self.reload_save()
        return True

    def import_preset_from_json(self):
        """Import preset from external JSON file"""
        save_file = self.get_save_file()
        if not save_file:
            notify(self.parent, "Load a save file first.", "warning")
            return

        json_path = pick_file(
            title="Select Preset JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if not json_path:
            return

        try:
            with open(json_path) as f:
                data = json.load(f)
        except Exception as e:
            CTkMessageBox.showerror(
                "JSON Load Failed",
                f"Failed to load JSON:\n{str(e)}",
                parent=self.parent,
            )
            import traceback

            traceback.print_exc()
            return

        self._import_preset_data(data, os.path.basename(json_path))

    def import_preset_from_code(self):
        """Import preset(s) from a share code."""
        save_file = self.get_save_file()
        if not save_file:
            notify(self.parent, "Load a save file first.", "warning")
            return

        code = self._ask_code("Import from Code", "Enter share code:")
        if not code:
            return

        from er_save_manager.data.appearance_sharing import fetch_preset

        data = fetch_preset(code)
        if data is None:
            CTkMessageBox.showerror(
                "Code Not Found",
                "Code not found, or failed to fetch. Check your connection.",
                parent=self.parent,
            )
            return

        self._import_preset_data(data, f"code {code}")

    def _import_preset_data(self, data, source_label):
        """Parse preset data (from JSON file or share code) and show the import dialog."""
        save_file = self.get_save_file()
        if not save_file:
            notify(self.parent, "Load a save file first.", "warning")
            return

        try:
            # Support formats:
            #   {"presets": [...]}           - UI export (raw appearance dicts)
            #   {"presets": [{"slot","data"}]} - save.py export
            #   {"description","appearance"} - single NPC preset
            #   {"base": {...}, "skin_color": {...}, ...} - Elden Bling Auto Sliders
            #   [...]                        - bare list
            if isinstance(data, dict) and "base" in data and "skin_color" in data:
                from er_save_manager.parser.character_presets import FacePreset

                presets = [FacePreset.from_elden_bling(data).to_dict()]
            elif isinstance(data, dict) and "appearance" in data:
                presets = [data["appearance"]]
            elif isinstance(data, dict) and "presets" in data:
                presets = data["presets"]
            elif isinstance(data, list):
                presets = data
            else:
                CTkMessageBox.showerror(
                    "Preset Unavailable",
                    "Invalid preset data format",
                    parent=self.parent,
                )
                return

            if not isinstance(presets, list) or not presets:
                CTkMessageBox.showerror(
                    "No Presets Found",
                    "No presets found in the data",
                    parent=self.parent,
                )
                return

            from er_save_manager.parser.character_presets import FacePreset

            # Entries that cannot be written are dropped and listed
            valid = []
            skipped = []
            for i, entry in enumerate(presets):
                body = entry.get("data", entry) if isinstance(entry, dict) else entry
                problem = FacePreset.dict_problem(body)
                if problem:
                    skipped.append(f"Preset {i + 1}: {problem}")
                else:
                    valid.append((f"Preset {i + 1}", body))

            skipped_text = "\n".join(skipped[:10])
            if len(skipped) > 10:
                skipped_text += f"\n... and {len(skipped) - 10} more"

            if not valid:
                CTkMessageBox.showerror(
                    "Preset Not Imported",
                    f"No preset in {source_label} can be imported:\n\n{skipped_text}",
                    parent=self.parent,
                )
                return

            from er_save_manager.ui import dialog_style as ds
            from er_save_manager.ui.utils import patch_combo_scroll

            dialog = ds.create(self.parent, "Import Presets")
            main = ctk.CTkFrame(dialog, fg_color="transparent")
            main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
            button_frame = ctk.CTkFrame(main, fg_color="transparent")
            button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(16, 0))

            ds.header(main, "Import Presets", font=ds.TITLE_LARGE)
            ctk.CTkLabel(
                main, text=f"From {source_label}", font=ds.SMALL, text_color=ds.MUTED
            ).pack(anchor=tk.W, pady=(2, 10))
            if skipped:
                ctk.CTkLabel(
                    main,
                    text=f"Skipped, cannot be imported:\n{skipped_text}",
                    font=ds.SMALL,
                    text_color=ds.WARNING,
                    justify=tk.LEFT,
                ).pack(anchor=tk.W, pady=(0, 10))

            frame = ds.box(main, pady=(0, 0))
            preset_names = [label for label, _ in valid]
            combos = []
            for row, (label, values) in enumerate(
                (
                    ("Preset to import", preset_names),
                    ("Into slot", [str(i) for i in range(1, 16)]),
                )
            ):
                pady = (10, 3) if row == 0 else (3, 10)
                ctk.CTkLabel(frame, text=label, font=ds.FONT).grid(
                    row=row, column=0, sticky=tk.W, padx=(12, 20), pady=pady
                )
                combo = ctk.CTkComboBox(
                    frame,
                    values=values,
                    state="readonly",
                    width=180,
                    font=ds.FONT,
                    dropdown_font=ds.FONT,
                )
                combo.grid(row=row, column=1, padx=(0, 12), pady=pady)
                combo.set(values[0])
                patch_combo_scroll(combo)
                combos.append(combo)
            preset_combo, slot_combo = combos

            def do_import():
                if not guard_before_write("import the preset"):
                    return
                # Applying pending edits reloads the save
                target_save = self.get_save_file()
                if not target_save:
                    return
                body = valid[preset_names.index(preset_combo.get())][1]
                target_slot = int(slot_combo.get()) - 1
                if not self._confirm_overwrite(target_save, [target_slot], dialog):
                    return
                try:
                    written = self.write_presets(
                        target_save,
                        lambda: target_save.import_preset(body, target_slot),
                        f"before_import_preset_to_slot_{target_slot + 1}",
                        "import_preset",
                        self.parent,
                    )
                except Exception as e:
                    CTkMessageBox.showerror(
                        "Import Failed", f"Import failed:\n{str(e)}", parent=self.parent
                    )
                    import traceback

                    traceback.print_exc()
                    return
                if not written:
                    return
                dialog.destroy()
                self.show_toast(
                    f"Preset imported to Slot {target_slot + 1}", duration=2500
                )

            def do_import_all():
                if not guard_before_write("import the presets"):
                    return
                target_save = self.get_save_file()
                if not target_save:
                    return
                count = min(len(valid), 15)
                if not self._confirm_overwrite(target_save, range(count), dialog):
                    return

                def change():
                    return all(
                        target_save.import_preset(valid[i][1], i) for i in range(count)
                    )

                try:
                    written = self.write_presets(
                        target_save,
                        change,
                        "before_import_all_presets",
                        "import_preset",
                        self.parent,
                    )
                except Exception as e:
                    CTkMessageBox.showerror(
                        "Import Failed",
                        f"Import all failed:\n{str(e)}",
                        parent=self.parent,
                    )
                    import traceback

                    traceback.print_exc()
                    return
                if not written:
                    return
                dialog.destroy()
                self.show_toast(
                    f"Imported {count} preset(s) to slots 1-{count}", duration=2500
                )

            ds.button(
                button_frame,
                "Import All to Slots",
                do_import_all,
                primary=False,
                width=150,
            ).pack(side=tk.LEFT)
            ds.button(button_frame, "Cancel", dialog.destroy, primary=False).pack(
                side=tk.RIGHT
            )
            ds.button(button_frame, "Import", do_import).pack(
                side=tk.RIGHT, padx=(0, 8)
            )
            ds.finish(dialog, self.parent, min_width=420)

        except Exception as e:
            CTkMessageBox.showerror(
                "Import Failed",
                f"Failed to import preset data:\n{str(e)}",
                parent=self.parent,
            )
            import traceback

            traceback.print_exc()

    def copy_preset_to_save(self):
        """Copy selected preset to another save file"""
        if self.selected_slot is None:
            notify(self.parent, "Select a preset to copy", "warning")
            return

        save_file = self.get_save_file()
        if not save_file:
            notify(self.parent, "Load a save file first", "warning")
            return

        presets_data = save_file.get_character_presets()
        if not presets_data or self.selected_slot >= 15:
            CTkMessageBox.showerror(
                "Preset Unavailable", "Invalid preset selection", parent=self.parent
            )
            return

        source_preset = presets_data.presets[self.selected_slot]
        if not source_preset or source_preset.is_empty():
            notify(self.parent, "Selected slot is empty", "warning")
            return
        # Capture the slot before the dialog can change selected_slot
        source_slot = self.selected_slot

        from er_save_manager.ui import dialog_style as ds
        from er_save_manager.ui.utils import patch_combo_scroll

        dialog = ds.create(self.parent, "Copy Preset to Another Save")
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        button_frame = ctk.CTkFrame(main, fg_color="transparent")
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(16, 0))
        ds.header(
            main, f"Copy Preset {source_slot + 1} to Another Save", font=ds.TITLE_LARGE
        )

        frame = ds.box(main, pady=(12, 0))
        frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(frame, text="Save file", font=ds.FONT).grid(
            row=0, column=0, sticky="w", padx=(12, 16), pady=(10, 3)
        )
        dest_path_var = tk.StringVar(value="")
        ctk.CTkEntry(
            frame, textvariable=dest_path_var, width=320, height=32, font=ds.FONT
        ).grid(row=0, column=1, sticky="ew", pady=(10, 3))

        def browse_dest():
            filename = pick_file(
                title="Select Destination Save File",
                filetypes=[("Elden Ring Saves", "*.sl2 *.co2"), ("All Files", "*.*")],
            )
            if filename:
                dest_path_var.set(filename)

        ds.button(frame, "Browse", browse_dest, primary=False, width=90).grid(
            row=0, column=2, padx=(8, 12), pady=(10, 3)
        )

        ctk.CTkLabel(frame, text="Into slot", font=ds.FONT).grid(
            row=1, column=0, sticky="w", padx=(12, 16), pady=(3, 10)
        )
        dest_slot_var = tk.StringVar(value="1")
        slot_combo = ctk.CTkComboBox(
            frame,
            variable=dest_slot_var,
            values=[str(i) for i in range(1, 16)],
            state="readonly",
            width=90,
            font=ds.FONT,
            dropdown_font=ds.FONT,
        )
        slot_combo.grid(row=1, column=1, sticky="w", pady=(3, 10))
        patch_combo_scroll(slot_combo)

        def do_copy():
            if not guard_before_write("copy the preset"):
                return
            dest_path = dest_path_var.get()
            if not dest_path or not Path(dest_path).exists():
                notify(self.parent, "Select a valid destination save file", "warning")
                return

            try:
                dest_slot = int(dest_slot_var.get())
                if dest_slot < 1 or dest_slot > 15:
                    CTkMessageBox.showerror(
                        "Invalid Slot",
                        "Slot must be between 1 and 15",
                        parent=self.parent,
                    )
                    return

                # Applying pending edits reloads the save
                source_save = self.get_save_file()
                if not source_save:
                    return
                open_path = self.get_save_path()
                if open_path and _same_file(dest_path, open_path):
                    self._copy_within_open_save(
                        source_save, source_slot, dest_slot - 1, dialog
                    )
                    return

                from er_save_manager.parser import Save

                dest_save = Save.from_file(dest_path)
                if not dest_save.get_character_presets():
                    CTkMessageBox.showerror(
                        "Copy Failed",
                        "The destination save has no preset data.",
                        parent=self.parent,
                    )
                    return
                if not self._confirm_overwrite(dest_save, [dest_slot - 1], dialog):
                    return

                manager = BackupManager(Path(dest_path))
                manager.create_backup(
                    description=f"before_preset_copy_to_slot_{dest_slot}",
                    operation="copy_preset",
                    save=dest_save,
                )

                success = dest_save.copy_preset_to_save(
                    source_save, source_slot, dest_slot - 1
                )

                if not success:
                    CTkMessageBox.showerror(
                        "Copy Failed", "Failed to copy preset", parent=self.parent
                    )
                    return

                dest_save.recalculate_checksums()
                dest_save.to_file(dest_path)

                notify(
                    self.parent,
                    f"Preset copied to {Path(dest_path).name}, Slot {dest_slot}.",
                    "success",
                )
                dialog.destroy()

            except Exception as e:
                CTkMessageBox.showerror(
                    "Copy Failed", f"Copy failed:\n{str(e)}", parent=self.parent
                )
                import traceback

                traceback.print_exc()

        ds.button(button_frame, "Cancel", dialog.destroy, primary=False).pack(
            side=tk.RIGHT
        )
        ds.button(button_frame, "Copy", do_copy).pack(side=tk.RIGHT, padx=(0, 8))
        ds.finish(dialog, self.parent)

    def _copy_within_open_save(self, save_file, source_slot, dest_slot, dialog):
        """Copy a preset between slots of the loaded save in memory.

        Writing the file on disk directly would leave the loaded save stale,
        and the next Apply All would write the old presets back.
        """
        if dest_slot == source_slot:
            notify(
                dialog,
                f"Preset {source_slot + 1} is the preset being copied. "
                "Pick another slot.",
                "warning",
            )
            return
        if not self._confirm_overwrite(save_file, [dest_slot], dialog):
            return
        if self.write_presets(
            save_file,
            lambda: save_file.copy_preset_to_save(save_file, source_slot, dest_slot),
            f"before_preset_copy_to_slot_{dest_slot + 1}",
            "copy_preset",
            self.parent,
        ):
            dialog.destroy()
            self.show_toast(
                f"Preset {source_slot + 1} copied to Slot {dest_slot + 1}",
                duration=2500,
            )

    def delete_preset(self):
        """Delete selected preset"""
        if self.selected_slot is None:
            notify(self.parent, "Select a preset to delete", "warning")
            return

        save_file = self.get_save_file()
        if not save_file:
            notify(self.parent, "Load a save file first", "warning")
            return

        slot = self.selected_slot
        if not self.occupied_slots(save_file, [slot]):
            notify(self.parent, f"Preset slot {slot + 1} is already empty", "info")
            return

        if not CTkMessageBox.askyesno(
            "Confirm Delete",
            f"Delete preset in Slot {slot + 1}?\n\nThis will clear the slot.",
            parent=self.parent,
        ):
            return
        if not guard_before_write("delete the preset"):
            return
        # Applying pending edits reloads the save
        save_file = self.get_save_file()
        if not save_file:
            return

        try:
            deleted = self.write_presets(
                save_file,
                lambda: save_file.delete_preset(slot),
                f"before_delete_preset_slot_{slot + 1}",
                "delete_preset",
                self.parent,
            )
        except Exception as e:
            CTkMessageBox.showerror(
                "Delete Failed", f"Delete failed:\n{str(e)}", parent=self.parent
            )
            import traceback

            traceback.print_exc()
            return
        if not deleted:
            return

        self.load_presets()
        self.show_toast(f"Preset in Slot {slot + 1} deleted", duration=2500)


def _same_file(a, b) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False
