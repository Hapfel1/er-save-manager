"""
Appearance Tab
Manages character appearance presets (15 slots)
"""

import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


class AppearanceTab:
    """Tab for character appearance preset management"""
    
    def __init__(self, parent, get_save_file_callback, get_save_path_callback, reload_callback):
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
                        body_type_value = preset.get_body_type() if hasattr(preset, "get_body_type") else 0
                        body_type = "Type A" if body_type_value == 0 else "Type B"
                        self.preset_listbox.insert(tk.END, f"Preset {i + 1:2d}: {body_type}")
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
            
            # Build info text
            body_type_value = preset.get_body_type()
            body_type = "Type A" if body_type_value == 0 else "Type B"
            
            info = []
            info.append("BASIC INFORMATION")
            info.append("=" * 50)
            info.append(f"Body Type: {body_type}")
            info.append(f"Face Model: {preset.face_model}")
            info.append(f"Hair Model: {preset.hair_model}")
            info.append(f"Eyebrow Model: {preset.eyebrow_model}")
            info.append(f"Beard Model: {preset.beard_model}")
            info.append("")
            info.append("BODY PROPORTIONS")
            info.append("=" * 50)
            info.append(f"Head Size: {preset.head_size}")
            info.append(f"Chest Size: {preset.chest_size}")
            info.append(f"Abdomen Size: {preset.abdomen_size}")
            info.append(f"Arms Size: {preset.arms_size}")
            info.append(f"Legs Size: {preset.legs_size}")
            info.append("")
            info.append("FACIAL FEATURES")
            info.append("=" * 50)
            info.append(f"Apparent Age: {preset.apparent_age}")
            info.append(f"Facial Aesthetic: {preset.facial_aesthetic}")
            info.append(f"Eye Position: {preset.eye_position}")
            info.append(f"Eye Size: {preset.eye_size}")
            info.append(f"Nose Size: {preset.nose_size}")
            info.append(f"Mouth Size: {preset.mouth_size}")
            
            text.insert("1.0", "\n".join(info))
            text.config(state="disabled")
            
            # Close button
            ttk.Button(dialog, text="Close", command=dialog.destroy, width=15).pack(pady=10)
            
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
            preset_names = [f"Preset {i+1}" for i in range(len(presets))]
            preset_combo = ttk.Combobox(
                frame,
                textvariable=preset_var,
                values=preset_names,
                state="readonly",
                width=15
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
                width=15
            )
            slot_combo.grid(row=2, column=1, padx=10, pady=5)
            
            def do_import():
                try:
                    from er_save_manager.backup.manager import BackupManager
                    
                    source_idx = preset_combo.current()
                    target_slot = slot_var.get() - 1
                    
                    if source_idx < 0 or target_slot < 0:
                        messagebox.showwarning("Invalid", "Please select valid source and target")
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
                        "Success",
                        f"Preset imported to Slot {target_slot + 1}!"
                    )
                    dialog.destroy()
                
                except Exception as e:
                    messagebox.showerror("Error", f"Import failed:\n{str(e)}")
                    import traceback
                    traceback.print_exc()
            
            button_frame = ttk.Frame(frame)
            button_frame.grid(row=3, column=0, columnspan=3, pady=20)
            
            ttk.Button(button_frame, text="Import", command=do_import, width=15).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON:\n{str(e)}")
            import traceback
            traceback.print_exc()
