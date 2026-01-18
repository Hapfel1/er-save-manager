"""
Advanced Tools Tab
Validation, checksum recalculation, and save information
"""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


class AdvancedToolsTab:
    """Tab for advanced save file operations"""
    
    def __init__(self, parent, get_save_file_callback, get_save_path_callback, reload_callback):
        """
        Initialize advanced tools tab
        
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
        
        self.save_info_text = None
    
    def setup_ui(self):
        """Setup the advanced tools tab UI"""
        ttk.Label(
            self.parent,
            text="Advanced Tools",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)
        
        # Save info
        info_frame = ttk.LabelFrame(
            self.parent, text="Save Information", padding=10
        )
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.save_info_text = tk.Text(
            info_frame, height=8, font=("Consolas", 9), state="disabled", wrap=tk.WORD
        )
        self.save_info_text.pack(fill=tk.X)
        
        # Tools
        tools_frame = ttk.LabelFrame(self.parent, text="Tools", padding=10)
        tools_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Button(
            tools_frame,
            text="Validate Save File",
            command=self.validate_save,
            width=25,
        ).pack(pady=5)
        
        ttk.Button(
            tools_frame,
            text="Recalculate All Checksums",
            command=self.recalculate_checksums,
            width=25,
        ).pack(pady=5)
        
        ttk.Button(
            tools_frame,
            text="Refresh Information",
            command=self.update_save_info,
            width=25,
        ).pack(pady=5)
    
    def update_save_info(self):
        """Update save information display"""
        save_file = self.get_save_file()
        if not save_file:
            self.save_info_text.config(state="normal")
            self.save_info_text.delete("1.0", tk.END)
            self.save_info_text.insert("1.0", "No save file loaded")
            self.save_info_text.config(state="disabled")
            return
        
        try:
            info = []
            info.append("SAVE FILE INFORMATION")
            info.append("=" * 40)
            info.append(f"Platform: {'PlayStation' if save_file.is_ps else 'PC'}")
            info.append(f"Magic: {save_file.magic.hex()}")
            
            if save_file.user_data_10_parsed:
                ud10 = save_file.user_data_10_parsed
                info.append(f"SteamID: {ud10.steam_id}")
            
            active_slots = save_file.get_active_slots()
            info.append(f"Active Characters: {len(active_slots)}")
            
            # File size
            save_path = self.get_save_path()
            if save_path:
                file_size = Path(save_path).stat().st_size
                info.append(f"File Size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
            
            self.save_info_text.config(state="normal")
            self.save_info_text.delete("1.0", tk.END)
            self.save_info_text.insert("1.0", "\n".join(info))
            self.save_info_text.config(state="disabled")
        
        except Exception as e:
            self.save_info_text.config(state="normal")
            self.save_info_text.delete("1.0", tk.END)
            self.save_info_text.insert("1.0", f"Error loading save info:\n{str(e)}")
            self.save_info_text.config(state="disabled")
    
    def validate_save(self):
        """Validate save file integrity"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        try:
            # Basic validation
            issues = []
            
            # Check magic bytes
            if save_file.magic not in [b'BND4', b'SL2\x00']:
                issues.append("Invalid magic bytes")
            
            # Check active characters
            active_slots = save_file.get_active_slots()
            if not active_slots:
                issues.append("No active characters found")
            
            # Check for corruption in active slots
            for slot_idx in active_slots:
                slot = save_file.characters[slot_idx]
                has_corruption, corruption_issues = slot.has_corruption()
                if has_corruption:
                    issues.append(f"Slot {slot_idx + 1}: {', '.join(corruption_issues)}")
            
            if issues:
                messagebox.showwarning(
                    "Validation Issues",
                    f"Found {len(issues)} issue(s):\n\n" + "\n".join(f"• {issue}" for issue in issues)
                )
            else:
                messagebox.showinfo(
                    "Validation Success",
                    "Save file appears to be valid!\n\nNo corruption detected."
                )
        
        except Exception as e:
            messagebox.showerror("Validation Error", f"Failed to validate:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def recalculate_checksums(self):
        """Recalculate all save file checksums"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        if not messagebox.askyesno(
            "Confirm", "Recalculate all checksums?\n\nA backup will be created."
        ):
            return
        
        try:
            from er_save_manager.backup.manager import BackupManager
            
            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description="before_checksum_recalc",
                    operation="recalculate_checksums",
                    save=save_file,
                )
            
            save_file.recalculate_checksums()
            if save_path:
                save_file.to_file(Path(save_path))
            
            if self.reload_save:
                self.reload_save()
            
            messagebox.showinfo(
                "Success",
                "Checksums recalculated!\n\nBackup saved to backup manager.",
            )
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to recalculate:\n{str(e)}")
            import traceback
            traceback.print_exc()
