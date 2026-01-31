"""
Appearance Tab
Manages character appearance presets (15 slots)
"""

import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


class AppearanceTab:
    """Tab for character appearance preset management"""

    def __init__(
        self, parent, get_save_file_callback, get_save_path_callback, reload_callback
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

        self.preset_frames = []
        self.selected_slot = None  # Track selected preset slot

    def setup_ui(self):
        """Setup the appearance tab UI"""
        # Main scrollable container
        scroll_frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(scroll_frame)

        # Header
        header_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        header_frame.pack(fill=tk.X, padx=15, pady=(15, 10))

        ctk.CTkLabel(
            header_frame,
            text="Character Appearance & Presets",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_frame,
            text="Manage character appearance presets (15 slots)",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", pady=(2, 0))

        # Preset list container
        list_container = ctk.CTkFrame(scroll_frame, corner_radius=10)
        list_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        ctk.CTkLabel(
            list_container,
            text="Presets",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(12, 6), padx=12, anchor="w")

        # Scrollable list
        self.list_frame = ctk.CTkScrollableFrame(
            list_container, corner_radius=8, height=280
        )
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        bind_mousewheel(self.list_frame)

        # Action buttons
        action_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        action_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

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
            text="Export to JSON",
            command=self.export_presets,
            width=130,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            btn_row,
            text="Import from JSON",
            command=self.import_preset_from_json,
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

    def open_preset_browser(self):
        """Open enhanced preset browser dialog."""
        from er_save_manager.ui.dialogs.preset_browser import (
            EnhancedPresetBrowser,
            PresetBrowserDialog,
        )

        browser = EnhancedPresetBrowser(self.parent, self)

        try:
            index = browser.manager.fetch_index()
            presets = index.get("presets", [])

            if presets:
                browser.show()
            else:
                PresetBrowserDialog.show_coming_soon(self.parent)
        except Exception as e:
            print(f"Failed to fetch presets: {e}")
            PresetBrowserDialog.show_coming_soon(self.parent)

    def select_preset(self, slot_idx, frame):
        """Handle preset selection"""
        self.selected_slot = slot_idx

        # Get appearance mode for colors
        mode = ctk.get_appearance_mode().lower()
        selected_color = "#c9a0dc" if mode == "light" else "#3b2f5c"
        unselected_color = "#f5f5f5" if mode == "light" else "#2a2a3e"

        # Update all frames
        for i, f in enumerate(self.preset_frames):
            if i == slot_idx:
                f.configure(fg_color=selected_color)
            else:
                f.configure(fg_color=unselected_color)

    def load_presets(self):
        """Load character presets"""
        # Clear existing frames
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

            mode = ctk.get_appearance_mode().lower()
            unselected_color = "#f5f5f5" if mode == "light" else "#2a2a3e"

            for i in range(15):
                frame = ctk.CTkFrame(
                    self.list_frame, corner_radius=8, fg_color=unselected_color
                )
                frame.pack(fill=tk.X, pady=4, padx=4)
                self.preset_frames.append(frame)

                # Make frame clickable
                frame.bind(
                    "<Button-1>", lambda e, idx=i, f=frame: self.select_preset(idx, f)
                )

                try:
                    preset = presets.presets[i]
                    if preset.is_empty():
                        label_text = f"Preset {i + 1:2d}: Empty"
                    else:
                        body_type_value = (
                            preset.get_body_type()
                            if hasattr(preset, "get_body_type")
                            else 0
                        )
                        body_type = "Type A" if body_type_value == 0 else "Type B"
                        label_text = f"Preset {i + 1:2d}: {body_type}"
                except Exception:
                    label_text = f"Preset {i + 1:2d}: Error"

                label = ctk.CTkLabel(
                    frame,
                    text=label_text,
                    font=("Consolas", 11),
                    anchor="w",
                )
                label.pack(fill=tk.X, padx=12, pady=8)
                label.bind(
                    "<Button-1>", lambda e, idx=i, f=frame: self.select_preset(idx, f)
                )

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
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", self.parent
            )
            return

        if self.selected_slot is None:
            CTkMessageBox.showwarning(
                "No Selection", "Please select a preset to view!", self.parent
            )
            return

        preset_idx = self.selected_slot

        try:
            presets = save_file.get_character_presets()
            if not presets or preset_idx >= len(presets.presets):
                CTkMessageBox.showerror(
                    "Error", "Could not load preset data", self.parent
                )
                return

            preset = presets.presets[preset_idx]

            if preset.is_empty():
                CTkMessageBox.showinfo(
                    "Empty Preset", f"Preset {preset_idx + 1} is empty", self.parent
                )
                return

            # Create dialog
            from er_save_manager.ui.utils import force_render_dialog

            dialog = ctk.CTkToplevel(self.parent)
            dialog.title(f"Preset {preset_idx + 1} Details")
            width, height = 700, 600
            dialog.resizable(True, True)
            dialog.transient(self.parent)
            dialog.update_idletasks()
            # Center over parent window
            self.parent.update_idletasks()
            parent_x = self.parent.winfo_rootx()
            parent_y = self.parent.winfo_rooty()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            x = parent_x + (parent_width // 2) - (width // 2)
            y = parent_y + (parent_height // 2) - (height // 2)
            dialog.geometry(f"{width}x{height}+{x}+{y}")
            # Force rendering on Linux before grab_set
            force_render_dialog(dialog)
            dialog.grab_set()

            ctk.CTkLabel(
                dialog,
                text=f"Preset {preset_idx + 1} - Character Appearance",
                font=("Segoe UI", 14, "bold"),
            ).pack(pady=(15, 10), padx=15)

            # Create scrollable text display
            text_container = ctk.CTkFrame(dialog, corner_radius=8)
            text_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

            text = ctk.CTkTextbox(
                text_container,
                font=("Consolas", 11),
                wrap="word",
            )
            text.pack(fill=tk.BOTH, expand=True)

            # Build comprehensive info text - use getattr for safety
            body_type_value = preset.get_body_type()
            body_type = "Type A" if body_type_value == 0 else "Type B"

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

            text.insert("1.0", "\n".join(info))
            text.configure(state="disabled")

            # Close button
            ctk.CTkButton(dialog, text="Close", command=dialog.destroy, width=15).pack(
                pady=10
            )

            # Auto-shown
            dialog.lift()
            dialog.focus_set()

        except Exception as e:
            CTkMessageBox.showerror("Error", f"Failed to view preset:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def export_presets(self):
        """Export presets to JSON"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        output_path = filedialog.asksaveasfilename(
            title="Export Presets",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if output_path:
            try:
                count = save_file.export_presets(output_path)
                CTkMessageBox.showinfo("Success", f"Exported {count} preset(s) to JSON")
            except Exception as e:
                CTkMessageBox.showerror("Error", f"Export failed:\n{str(e)}")

    def import_preset_from_json(self):
        """Import preset from external JSON file"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        json_path = filedialog.askopenfilename(
            title="Select Preset JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if not json_path:
            return

        try:
            with open(json_path) as f:
                data = json.load(f)

            # Support both formats: direct list or {'presets': [...]}
            if isinstance(data, dict) and "presets" in data:
                presets = data["presets"]
            elif isinstance(data, list):
                presets = data
            else:
                CTkMessageBox.showerror("Error", "Invalid JSON file format")
                return

            if not presets:
                CTkMessageBox.showerror("Error", "No presets found in JSON file")
                return

            # Create import dialog
            dialog = tk.Toplevel(self.parent)
            dialog.title("Import from JSON")
            dialog.geometry("550x250")
            dialog.grab_set()

            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"550x250+{x}+{y}")

            frame = ctk.CTkFrame(dialog)
            frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            ctk.CTkLabel(
                frame,
                text=f"Import from: {os.path.basename(json_path)}",
                font=("Segoe UI", 11, "bold"),
            ).grid(row=0, column=0, columnspan=3, pady=(0, 15))

            ctk.CTkLabel(frame, text="Select Preset from JSON:").grid(
                row=1, column=0, sticky=tk.W, pady=5
            )

            preset_names = [f"Preset {i + 1}" for i in range(len(presets))]
            preset_combo = ctk.CTkComboBox(
                frame,
                values=preset_names,
                state="readonly",
                width=15,
                font=("Segoe UI", 11),
            )
            preset_combo.grid(row=1, column=1, padx=10, pady=5)
            preset_combo.set(preset_names[0])

            ctk.CTkLabel(frame, text="Import to Slot:").grid(
                row=2, column=0, sticky=tk.W, pady=5
            )

            slot_combo = ctk.CTkComboBox(
                frame,
                values=[str(i) for i in range(1, 16)],
                state="readonly",
                width=15,
                font=("Segoe UI", 11),
            )
            slot_combo.grid(row=2, column=1, padx=10, pady=5)
            slot_combo.set("1")

            def do_import():
                try:
                    from er_save_manager.backup.manager import BackupManager

                    source_idx = preset_combo.cget("values").index(preset_combo.get())
                    target_slot = int(slot_combo.get()) - 1

                    if source_idx < 0 or target_slot < 0:
                        CTkMessageBox.showwarning(
                            "Invalid", "Please select valid source and target"
                        )
                        return

                    # Create backup
                    save_path = self.get_save_path()
                    if save_path:
                        manager = BackupManager(Path(save_path))
                        manager.create_backup(
                            description=f"before_import_preset_to_slot_{target_slot + 1}",
                            operation="import_preset",
                            save=save_file,
                        )

                    # Import
                    save_file.import_preset(presets[source_idx], target_slot)

                    # Save
                    save_file.recalculate_checksums()
                    if save_path:
                        save_file.to_file(Path(save_path))

                    # Reload
                    if self.reload_save:
                        self.reload_save()

                    CTkMessageBox.showinfo(
                        "Success", f"Preset imported to Slot {target_slot + 1}!"
                    )
                    dialog.destroy()

                except Exception as e:
                    CTkMessageBox.showerror("Error", f"Import failed:\n{str(e)}")
                    import traceback

                    traceback.print_exc()

            button_frame = ctk.CTkFrame(frame)
            button_frame.grid(row=3, column=0, columnspan=3, pady=20)

            ctk.CTkButton(
                button_frame, text="Import", command=do_import, width=15
            ).pack(side=tk.LEFT, padx=5)
            ctk.CTkButton(
                button_frame, text="Cancel", command=dialog.destroy, width=15
            ).pack(side=tk.LEFT, padx=5)

        except Exception as e:
            CTkMessageBox.showerror("Error", f"Failed to load JSON:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def copy_preset_to_save(self):
        """Copy selected preset to another save file"""
        if self.selected_slot is None:
            CTkMessageBox.showwarning("No Selection", "Please select a preset to copy")
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first")
            return

        # Get preset info
        presets_data = save_file.get_character_presets()
        if not presets_data or self.selected_slot >= 15:
            CTkMessageBox.showerror("Error", "Invalid preset selection")
            return

        source_preset = presets_data.presets[self.selected_slot]
        if not source_preset or source_preset.is_empty():
            CTkMessageBox.showwarning("Empty Slot", "Selected slot is empty")
            return
        # CRITICAL: Capture the slot value NOW to avoid closure issues
        source_slot = self.selected_slot

        # Show copy dialog
        dialog = tk.Toplevel(self.parent)
        dialog.title("Copy Preset to Another Save")
        dialog.geometry("600x250")
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            frame,
            text=f"Copy preset from Slot {source_slot + 1}",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, columnspan=3, pady=(0, 15))

        ctk.CTkLabel(frame, text="Destination Save File:").grid(
            row=1, column=0, sticky="w", pady=5
        )

        dest_path_var = tk.StringVar(value="")
        ctk.CTkEntry(frame, textvariable=dest_path_var, width=45).grid(
            row=1, column=1, padx=5
        )

        def browse_dest():
            from tkinter import filedialog

            filename = filedialog.askopenfilename(
                title="Select Destination Save File",
                filetypes=[("Elden Ring Saves", "*.sl2 *.co2"), ("All Files", "*.*")],
            )
            if filename:
                dest_path_var.set(filename)

        ctk.CTkButton(frame, text="Browse", command=browse_dest).grid(
            row=1, column=2, padx=5
        )

        ctk.CTkLabel(frame, text="Destination Slot (1-15):").grid(
            row=2, column=0, sticky="w", pady=5
        )

        dest_slot_var = tk.StringVar(value="1")
        ctk.CTkEntry(frame, textvariable=dest_slot_var, width=10).grid(
            row=2, column=1, sticky="w", padx=5
        )

        def do_copy():
            dest_path = dest_path_var.get()
            if not dest_path or not Path(dest_path).exists():
                CTkMessageBox.showerror(
                    "Error", "Please select a valid destination save file"
                )
                return

            try:
                dest_slot = int(dest_slot_var.get())
                if dest_slot < 1 or dest_slot > 15:
                    CTkMessageBox.showerror("Error", "Slot must be between 1 and 15")
                    return

                # Load destination save
                from er_save_manager.parser import Save

                dest_save = Save.from_file(dest_path)

                # Create backup of destination
                manager = BackupManager(Path(dest_path))
                manager.create_backup(
                    description=f"before_preset_copy_to_slot_{dest_slot}",
                    operation="copy_preset",
                    save=dest_save,
                )

                # Copy preset
                success = dest_save.copy_preset_to_save(
                    save_file, self.selected_slot, dest_slot - 1
                )

                if not success:
                    CTkMessageBox.showerror("Error", "Failed to copy preset")
                    return

                # Save destination
                dest_save.recalculate_checksums()
                dest_save.to_file(dest_path)

                CTkMessageBox.showinfo(
                    "Success",
                    f"Preset copied to {Path(dest_path).name}, Slot {dest_slot}!",
                )
                dialog.destroy()

            except Exception as e:
                CTkMessageBox.showerror("Error", f"Copy failed:\n{str(e)}")
                import traceback

                traceback.print_exc()

        button_frame = ctk.CTkFrame(frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)

        ctk.CTkButton(button_frame, text="Copy", command=do_copy, width=15).pack(
            side=tk.LEFT, padx=5
        )
        ctk.CTkButton(
            button_frame, text="Cancel", command=dialog.destroy, width=15
        ).pack(side=tk.LEFT, padx=5)

    def delete_preset(self):
        """Delete selected preset"""
        if self.selected_slot is None:
            CTkMessageBox.showwarning(
                "No Selection", "Please select a preset to delete"
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first")
            return

        # Confirm deletion
        if not CTkMessageBox.askyesno(
            "Confirm Delete",
            f"Delete preset in Slot {self.selected_slot + 1}?\n\nThis will clear the slot.",
        ):
            return

        try:
            # Create backup
            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_delete_preset_slot_{self.selected_slot + 1}",
                    operation="delete_preset",
                    save=save_file,
                )

            # Delete preset
            success = save_file.delete_preset(self.selected_slot)

            if not success:
                CTkMessageBox.showerror("Error", "Failed to delete preset")
                return

            # Save
            save_file.recalculate_checksums()
            if save_path:
                save_file.to_file(Path(save_path))

            # Reload
            if self.reload_save:
                self.reload_save()

            # Refresh preset list so UI matches new state
            self.load_presets()

            CTkMessageBox.showinfo(
                "Success", f"Preset in Slot {self.selected_slot + 1} deleted!"
            )

        except Exception as e:
            CTkMessageBox.showerror("Error", f"Delete failed:\n{str(e)}")
            import traceback

            traceback.print_exc()
