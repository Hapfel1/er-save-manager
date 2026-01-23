"""
Appearance Tab
Manages character appearance presets (15 slots)
"""

import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.ui.dialogs.preset_browser import PresetBrowserDialog


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

        self.preset_listbox = None
        self.selected_slot = None  # Track selected preset slot

    def setup_ui(self):
        """Setup the appearance tab UI"""
        ttk.Label(
            self.parent,
            text="Character Appearance & Presets",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        # Preset list
        preset_frame = ttk.LabelFrame(
            self.parent, text="Character Presets (15 slots)", padding=10
        )
        preset_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        list_frame = ttk.Frame(preset_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.preset_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            height=12,
        )
        self.preset_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.preset_listbox.yview)

        # Bind selection event
        self.preset_listbox.bind("<<ListboxSelect>>", self._on_preset_select)

        # Preset actions
        action_frame = ttk.Frame(self.parent)
        action_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            action_frame,
            text="View Details",
            command=self.view_preset_details,
            width=18,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            action_frame,
            text="Export to JSON",
            command=self.export_presets,
            width=18,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            action_frame,
            text="Import from JSON",
            command=self.import_preset_from_json,
            width=18,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            action_frame,
            text="Copy to Another Save",
            command=self.copy_preset_to_save,
            width=18,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            action_frame,
            text="Delete Preset",
            command=self.delete_preset,
            width=18,
        ).pack(side=tk.LEFT, padx=5)

        # Community presets button
        ttk.Button(
            action_frame,
            text="Browse Community Presets (Coming Soon)",
            command=self.open_preset_browser,
            width=45,
        ).pack(pady=5)

    def open_preset_browser(self):
        """Open community preset browser dialog."""
        from er_save_manager.ui.dialogs.preset_browser import PresetBrowserDialog
        
        print("\n" + "="*60)
        print("DEBUG: Opening preset browser...")
        
        # Create browser instance
        browser = PresetBrowserDialog(self.parent, self)
        print(f"DEBUG: Created browser instance")
        print(f"DEBUG: Base URL: {browser.manager.base_url}")
        print(f"DEBUG: Index URL: {browser.manager.index_url}")
        
        # Check if presets exist
        try:
            print("DEBUG: Fetching index from GitHub...")
            index = browser.manager.fetch_index()
            
            print(f"DEBUG: Index fetched successfully")
            print(f"DEBUG: Index keys: {list(index.keys())}")
            print(f"DEBUG: Index version: {index.get('version', 'N/A')}")
            
            presets = index.get('presets', [])
            print(f"DEBUG: Number of presets: {len(presets)}")
            
            if presets:
                print(f"DEBUG: Presets found! Showing full browser...")
                print(f"DEBUG: First preset: {presets[0].get('name', 'Unknown')}")
                browser.show()  # Full browser!
            else:
                print(f"DEBUG: No presets in index - showing Coming Soon")
                PresetBrowserDialog.show_coming_soon(self.parent)  # Coming soon
                
        except Exception as e:
            print(f"DEBUG: ERROR fetching index: {e}")
            import traceback
            traceback.print_exc()
            print(f"DEBUG: Showing Coming Soon due to error")
            PresetBrowserDialog.show_coming_soon(self.parent)  # Coming soon
        
        print("="*60 + "\n")

    def _on_preset_select(self, event=None):
        """Handle preset selection"""
        selection = self.preset_listbox.curselection()
        if selection:
            self.selected_slot = selection[0]
        else:
            self.selected_slot = None

    def load_presets(self):
        """Load character presets"""
        self.preset_listbox.delete(0, tk.END)

        save_file = self.get_save_file()
        if not save_file:
            return

        try:
            presets = save_file.get_character_presets()
            if not presets:
                self.preset_listbox.insert(tk.END, "No presets found")
                return

            for i in range(15):
                try:
                    preset = presets.presets[i]
                    if preset.is_empty():
                        self.preset_listbox.insert(tk.END, f"Preset {i + 1:2d}: Empty")
                    else:
                        body_type_value = (
                            preset.get_body_type()
                            if hasattr(preset, "get_body_type")
                            else 0
                        )
                        body_type = "Type A" if body_type_value == 0 else "Type B"
                        self.preset_listbox.insert(
                            tk.END, f"Preset {i + 1:2d}: {body_type}"
                        )
                except Exception:
                    self.preset_listbox.insert(tk.END, f"Preset {i + 1:2d}: Error")

        except Exception as e:
            self.preset_listbox.insert(tk.END, "Error loading presets")
            print(f"Error loading presets: {e}")
            import traceback

            traceback.print_exc()

    def view_preset_details(self):
        """View detailed preset information"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        selection = self.preset_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a preset to view!")
            return

        preset_idx = selection[0]

        try:
            presets = save_file.get_character_presets()
            if not presets or preset_idx >= len(presets.presets):
                messagebox.showerror("Error", "Could not load preset data")
                return

            preset = presets.presets[preset_idx]

            if preset.is_empty():
                messagebox.showinfo("Empty Preset", f"Preset {preset_idx + 1} is empty")
                return

            # Create dialog
            dialog = tk.Toplevel(self.parent)
            dialog.withdraw()
            dialog.title(f"Preset {preset_idx + 1} Details")

            width, height = 700, 600
            screen_w = dialog.winfo_screenwidth()
            screen_h = dialog.winfo_screenheight()
            x = (screen_w // 2) - (width // 2)
            y = (screen_h // 2) - (height // 2)
            dialog.geometry(f"{width}x{height}+{x}+{y}")

            ttk.Label(
                dialog,
                text=f"Preset {preset_idx + 1} - Character Appearance",
                font=("Segoe UI", 14, "bold"),
                padding=10,
            ).pack()

            # Create scrollable text display
            text_frame = ttk.Frame(dialog)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            scrollbar = ttk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            text = tk.Text(
                text_frame,
                font=("Consolas", 9),
                wrap=tk.WORD,
                yscrollcommand=scrollbar.set,
            )
            text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=text.yview)

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
            text.config(state="disabled")

            # Close button
            ttk.Button(dialog, text="Close", command=dialog.destroy, width=15).pack(
                pady=10
            )

            dialog.deiconify()
            dialog.lift()
            dialog.focus_force()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to view preset:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def export_presets(self):
        """Export presets to JSON"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        output_path = filedialog.asksaveasfilename(
            title="Export Presets",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if output_path:
            try:
                count = save_file.export_presets(output_path)
                messagebox.showinfo("Success", f"Exported {count} preset(s) to JSON")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed:\n{str(e)}")

    def import_preset_from_json(self):
        """Import preset from external JSON file"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
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
                messagebox.showerror("Error", "Invalid JSON file format")
                return

            if not presets:
                messagebox.showerror("Error", "No presets found in JSON file")
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

            frame = ttk.Frame(dialog, padding=20)
            frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(
                frame,
                text=f"Import from: {os.path.basename(json_path)}",
                font=("Segoe UI", 11, "bold"),
            ).grid(row=0, column=0, columnspan=3, pady=(0, 15))

            ttk.Label(frame, text="Select Preset from JSON:").grid(
                row=1, column=0, sticky=tk.W, pady=5
            )

            preset_var = tk.StringVar()
            preset_names = [f"Preset {i + 1}" for i in range(len(presets))]
            preset_combo = ttk.Combobox(
                frame,
                textvariable=preset_var,
                values=preset_names,
                state="readonly",
                width=15,
            )
            preset_combo.grid(row=1, column=1, padx=10, pady=5)
            preset_combo.current(0)

            ttk.Label(frame, text="Import to Slot:").grid(
                row=2, column=0, sticky=tk.W, pady=5
            )

            slot_var = tk.IntVar(value=1)
            slot_combo = ttk.Combobox(
                frame,
                textvariable=slot_var,
                values=list(range(1, 16)),
                state="readonly",
                width=15,
            )
            slot_combo.grid(row=2, column=1, padx=10, pady=5)

            def do_import():
                try:
                    from er_save_manager.backup.manager import BackupManager

                    source_idx = preset_combo.current()
                    target_slot = slot_var.get() - 1

                    if source_idx < 0 or target_slot < 0:
                        messagebox.showwarning(
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

                    messagebox.showinfo(
                        "Success", f"Preset imported to Slot {target_slot + 1}!"
                    )
                    dialog.destroy()

                except Exception as e:
                    messagebox.showerror("Error", f"Import failed:\n{str(e)}")
                    import traceback

                    traceback.print_exc()

            button_frame = ttk.Frame(frame)
            button_frame.grid(row=3, column=0, columnspan=3, pady=20)

            ttk.Button(button_frame, text="Import", command=do_import, width=15).pack(
                side=tk.LEFT, padx=5
            )
            ttk.Button(
                button_frame, text="Cancel", command=dialog.destroy, width=15
            ).pack(side=tk.LEFT, padx=5)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def copy_preset_to_save(self):
        """Copy selected preset to another save file"""
        if self.selected_slot is None:
            messagebox.showwarning("No Selection", "Please select a preset to copy")
            return

        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first")
            return

        # Get preset info
        presets_data = save_file.get_character_presets()
        if not presets_data or self.selected_slot >= 15:
            messagebox.showerror("Error", "Invalid preset selection")
            return

        source_preset = presets_data.presets[self.selected_slot]
        if not source_preset or source_preset.is_empty():
            messagebox.showwarning("Empty Slot", "Selected slot is empty")
            return

        # Show copy dialog
        dialog = tk.Toplevel(self.parent)
        dialog.title("Copy Preset to Another Save")
        dialog.geometry("600x250")
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text=f"Copy preset from Slot {self.selected_slot + 1}",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, columnspan=3, pady=(0, 15))

        ttk.Label(frame, text="Destination Save File:").grid(
            row=1, column=0, sticky="w", pady=5
        )

        dest_path_var = tk.StringVar()
        ttk.Entry(frame, textvariable=dest_path_var, width=45).grid(
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

        ttk.Button(frame, text="Browse", command=browse_dest).grid(
            row=1, column=2, padx=5
        )

        ttk.Label(frame, text="Destination Slot (1-15):").grid(
            row=2, column=0, sticky="w", pady=5
        )

        dest_slot_var = tk.StringVar(value="1")
        ttk.Entry(frame, textvariable=dest_slot_var, width=10).grid(
            row=2, column=1, sticky="w", padx=5
        )

        def do_copy():
            dest_path = dest_path_var.get()
            if not dest_path or not Path(dest_path).exists():
                messagebox.showerror(
                    "Error", "Please select a valid destination save file"
                )
                return

            try:
                dest_slot = int(dest_slot_var.get())
                if dest_slot < 1 or dest_slot > 15:
                    messagebox.showerror("Error", "Slot must be between 1 and 15")
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
                    messagebox.showerror("Error", "Failed to copy preset")
                    return

                # Save destination
                dest_save.recalculate_checksums()
                dest_save.to_file(dest_path)

                messagebox.showinfo(
                    "Success",
                    f"Preset copied to {Path(dest_path).name}, Slot {dest_slot}!",
                )
                dialog.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"Copy failed:\n{str(e)}")
                import traceback

                traceback.print_exc()

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)

        ttk.Button(button_frame, text="Copy", command=do_copy, width=15).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy, width=15).pack(
            side=tk.LEFT, padx=5
        )

    def delete_preset(self):
        """Delete selected preset"""
        if self.selected_slot is None:
            messagebox.showwarning("No Selection", "Please select a preset to delete")
            return

        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first")
            return

        # Confirm deletion
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete preset in Slot {self.selected_slot + 1}?\n\nThis will clear the slot.",
            icon="warning",
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
                messagebox.showerror("Error", "Failed to delete preset")
                return

            # Save
            save_file.recalculate_checksums()
            if save_path:
                save_file.to_file(Path(save_path))

            # Reload
            if self.reload_save:
                self.reload_save()

            messagebox.showinfo(
                "Success", f"Preset in Slot {self.selected_slot + 1} deleted!"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Delete failed:\n{str(e)}")
            import traceback

            traceback.print_exc()
