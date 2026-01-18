"""
Event Flags Tab
View and manage event flags for quest progression
"""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


class EventFlagsTab:
    """Tab for event flag viewing and management"""
    
    def __init__(self, parent, get_save_file_callback, get_save_path_callback, reload_callback):
        """
        Initialize event flags tab
        
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
        
        self.eventflag_slot_var = None
        self.eventflag_text = None
    
    def setup_ui(self):
        """Setup the event flags tab UI"""
        ttk.Label(
            self.parent,
            text="Event Flags",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=10)
        
        info_text = ttk.Label(
            self.parent,
            text="View and edit event flags that control game progression",
            font=("Segoe UI", 10),
            foreground="gray",
        )
        info_text.pack(pady=5)
        
        # Slot selector
        slot_frame = ttk.Frame(self.parent)
        slot_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(slot_frame, text="Character Slot:", font=("Segoe UI", 10)).pack(
            side=tk.LEFT, padx=5
        )
        
        self.eventflag_slot_var = tk.IntVar(value=1)
        slot_combo = ttk.Combobox(
            slot_frame,
            textvariable=self.eventflag_slot_var,
            values=list(range(1, 11)),
            state="readonly",
            width=5,
        )
        slot_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            slot_frame,
            text="Load Event Flags",
            command=self.load_event_flags,
            width=20,
        ).pack(side=tk.LEFT, padx=10)
        
        # Quick fixes
        fixes_frame = ttk.LabelFrame(
            self.parent, text="Quick Fixes", padding=15
        )
        fixes_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(
            fixes_frame,
            text="Fix common event flag issues:",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=5)
        
        button_grid = ttk.Frame(fixes_frame)
        button_grid.pack(fill=tk.X)
        
        ttk.Button(
            button_grid,
            text="Fix Ranni Quest",
            command=lambda: self.fix_event_flag_issue("ranni"),
            width=18,
        ).grid(row=0, column=0, padx=5, pady=5)
        
        ttk.Button(
            button_grid,
            text="Fix Warp Sickness",
            command=lambda: self.fix_event_flag_issue("warp"),
            width=18,
        ).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(
            button_grid,
            text="Clear Softlock Flags",
            command=lambda: self.fix_event_flag_issue("softlock"),
            width=18,
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Event flag viewer
        viewer_frame = ttk.LabelFrame(
            self.parent, text="Event Flags", padding=10
        )
        viewer_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Add scrollable text area for flags
        text_frame = ttk.Frame(viewer_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.eventflag_text = tk.Text(
            text_frame,
            height=15,
            font=("Consolas", 9),
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
        )
        self.eventflag_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.eventflag_text.yview)
        
        self.eventflag_text.insert("1.0", "Load a character to view event flags")
        self.eventflag_text.config(state="disabled")
    
    def load_event_flags(self):
        """Load event flags for selected character"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        slot_idx = self.eventflag_slot_var.get() - 1
        slot = save_file.characters[slot_idx]
        
        if slot.is_empty():
            messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
            return
        
        try:
            self.eventflag_text.config(state="normal")
            self.eventflag_text.delete("1.0", tk.END)
            
            char_name = slot.get_character_name()
            self.eventflag_text.insert(
                "1.0",
                f"Event Flags for {char_name} (Slot {slot_idx + 1})\n\n",
            )
            
            # Get event flag data if available
            if hasattr(slot, 'event_flags') and slot.event_flags:
                self.eventflag_text.insert(tk.END, "Event Flags Summary:\n")
                self.eventflag_text.insert(tk.END, "=" * 50 + "\n\n")
                
                # Count set flags
                total_flags = len(slot.event_flags.flags)
                set_flags = sum(1 for flag in slot.event_flags.flags if flag)
                
                self.eventflag_text.insert(tk.END, f"Total Flags: {total_flags}\n")
                self.eventflag_text.insert(tk.END, f"Set Flags: {set_flags}\n")
                self.eventflag_text.insert(tk.END, f"Percentage: {(set_flags/total_flags*100):.1f}%\n\n")
                
                self.eventflag_text.insert(tk.END, "Note: Detailed flag viewing coming soon...\n\n")
                self.eventflag_text.insert(tk.END, "This feature will display:\n")
                self.eventflag_text.insert(tk.END, "• Boss defeats\n")
                self.eventflag_text.insert(tk.END, "• Grace sites unlocked\n")
                self.eventflag_text.insert(tk.END, "• Quest progression\n")
                self.eventflag_text.insert(tk.END, "• NPC states\n")
            else:
                self.eventflag_text.insert(tk.END, "Event flag data not available for this character.\n")
            
            self.eventflag_text.config(state="disabled")
        
        except Exception as e:
            self.eventflag_text.config(state="normal")
            self.eventflag_text.delete("1.0", tk.END)
            self.eventflag_text.insert("1.0", f"Error loading event flags:\n{str(e)}")
            self.eventflag_text.config(state="disabled")
            
            import traceback
            traceback.print_exc()
    
    def fix_event_flag_issue(self, issue_type):
        """Fix specific event flag issues"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        slot_idx = self.eventflag_slot_var.get() - 1
        
        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.fixes.event_flags import EventFlagFix
            
            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_fix_{issue_type}_flags_slot_{slot_idx + 1}",
                    operation=f"fix_event_flags_{issue_type}",
                    save=save_file,
                )
            
            fix = EventFlagFix()
            result = fix.apply(save_file, slot_idx)
            
            if result.applied:
                save_file.recalculate_checksums()
                if save_path:
                    save_file.to_file(Path(save_path))
                
                if self.reload_save:
                    self.reload_save()
                
                messagebox.showinfo(
                    "Success",
                    f"{result.description}\n\nBackup saved to backup manager.",
                )
            else:
                messagebox.showinfo("No Changes", "No issues were detected or fixed")
        
        except Exception as e:
            messagebox.showerror("Error", f"Fix failed:\n{str(e)}")
            import traceback
            traceback.print_exc()
