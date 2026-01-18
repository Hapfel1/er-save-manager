"""
Save Inspector Tab
Displays character list with quick fix functionality
"""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


class SaveInspectorTab:
    """Tab for viewing save file contents and quick fixes"""
    
    def __init__(self, parent, get_save_file_callback, get_save_path_callback, reload_callback, show_details_callback):
        """
        Initialize save inspector tab
        
        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_save_path_callback: Function that returns save file path
            reload_callback: Function to reload save file
            show_details_callback: Function to show character details dialog (slot_idx)
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback
        self.show_details = show_details_callback
        
        self.char_listbox = None
        self.selected_slot = None
    
    def setup_ui(self):
        """Setup the save inspector tab UI"""
        # Character selection frame
        char_frame = ttk.LabelFrame(
            self.parent, text="Select Character", padding="10"
        )
        char_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Character listbox
        list_frame = ttk.Frame(char_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.char_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            height=10,
            selectmode=tk.SINGLE,
        )
        self.char_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.char_listbox.yview)
        
        self.char_listbox.bind("<ButtonRelease-1>", self.on_character_select)
        self.char_listbox.bind("<Double-Button-1>", self.on_character_double_click)
        
        # Actions frame
        action_frame = ttk.LabelFrame(self.parent, text="Actions", padding="10")
        action_frame.pack(fill=tk.X)
        
        ttk.Button(
            action_frame,
            text="View Details & Issues",
            command=self.show_character_details,
            width=25,
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            action_frame,
            text="Quick Fix All Issues",
            command=self.quick_fix_all,
            width=25,
        ).pack(side=tk.LEFT, padx=5)
    
    def populate_character_list(self):
        """Populate character listbox"""
        self.char_listbox.delete(0, tk.END)
        
        save_file = self.get_save_file()
        if not save_file:
            return
        
        try:
            active_slots = save_file.get_active_slots()
            
            if not active_slots:
                self.char_listbox.insert(tk.END, "No active characters found")
                return
            
            # Get profiles safely
            profiles = None
            try:
                if save_file.user_data_10_parsed:
                    profiles = save_file.user_data_10_parsed.profile_summary.profiles
            except Exception as e:
                print(f"Warning: Could not load profiles: {e}")
            
            for slot_idx in active_slots:
                try:
                    slot = save_file.characters[slot_idx]
                    if not slot:
                        continue
                    
                    # Get character info safely
                    name = "Unknown"
                    level = "?"
                    
                    if profiles and slot_idx < len(profiles):
                        try:
                            profile = profiles[slot_idx]
                            name = profile.character_name or "Unknown"
                            level = str(profile.level) if profile.level else "?"
                        except Exception as e:
                            print(f"Warning: Could not load profile for slot {slot_idx}: {e}")
                    
                    # Get map location safely
                    map_str = "Unknown"
                    try:
                        if hasattr(slot, "map_id") and slot.map_id:
                            map_str = slot.map_id.to_string_decimal()
                    except Exception as e:
                        print(f"Warning: Could not get map for slot {slot_idx}: {e}")
                    
                    display_text = f"Slot {slot_idx + 1:2d} | {name:16s} | Lv.{level:>3s} | Map: {map_str}"
                    self.char_listbox.insert(tk.END, display_text)
                
                except Exception as e:
                    # If individual character fails, show error but continue
                    self.char_listbox.insert(
                        tk.END, f"Slot {slot_idx + 1:2d} | Error loading data"
                    )
                    print(f"Error loading slot {slot_idx}: {e}")
        
        except Exception as e:
            self.char_listbox.insert(tk.END, "Error loading characters")
            messagebox.showerror("Error", f"Failed to load character list:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def on_character_select(self, event):
        """Handle character selection"""
        save_file = self.get_save_file()
        if not save_file:
            return
        
        selection = self.char_listbox.curselection()
        if selection:
            active_slots = save_file.get_active_slots()
            if selection[0] < len(active_slots):
                self.selected_slot = active_slots[selection[0]]
    
    def on_character_double_click(self, event):
        """Handle double-click to show details"""
        self.show_character_details()
    
    def show_character_details(self):
        """Show character details dialog"""
        if self.selected_slot is None:
            messagebox.showwarning("No Selection", "Please select a character first!")
            return
        
        if self.show_details:
            self.show_details(self.selected_slot)
    
    def quick_fix_all(self):
        """Apply all fixes to selected character"""
        save_file = self.get_save_file()
        if not save_file or self.selected_slot is None:
            messagebox.showwarning("No Selection", "Please select a character first!")
            return
        
        if not messagebox.askyesno(
            "Confirm",
            f"Fix all issues in Slot {self.selected_slot + 1}?\n\nA backup will be created.",
        ):
            return
        
        try:
            from er_save_manager.backup.manager import BackupManager
            
            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description="before_fix",
                    operation="fix_corruption",
                    save=save_file,
                )
            
            # Apply fix
            was_fixed, fixes = save_file.fix_character_corruption(self.selected_slot)
            
            if was_fixed:
                # Save
                save_file.recalculate_checksums()
                if save_path:
                    save_file.to_file(Path(save_path))
                
                # Reload
                if self.reload_save:
                    self.reload_save()
                
                fix_summary = "\n".join(fixes[:5])
                if len(fixes) > 5:
                    fix_summary += f"\n...and {len(fixes) - 5} more"
                
                messagebox.showinfo(
                    "Success",
                    f"Fixed {len(fixes)} issue(s):\n\n{fix_summary}\n\nBackup saved to backup manager.",
                )
            else:
                messagebox.showinfo("No Issues", "No corruption detected")
        
        except Exception as e:
            messagebox.showerror("Error", f"Fix failed:\n{str(e)}")
            import traceback
            traceback.print_exc()
