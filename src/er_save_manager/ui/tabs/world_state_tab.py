"""
World State Tab
Manages world state, teleportation, and location info
"""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


class WorldStateTab:
    """Tab for world state management and teleportation"""
    
    def __init__(self, parent, get_save_file_callback, get_save_path_callback, reload_callback):
        """
        Initialize world state tab
        
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
        
        self.world_slot_var = None
        self.location_text = None
    
    def setup_ui(self):
        """Setup the world state tab UI"""
        ttk.Label(
            self.parent,
            text="World State Editor",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)
        
        # Slot selector
        select_frame = ttk.Frame(self.parent)
        select_frame.pack(fill=tk.X, pady=10, padx=20)
        
        ttk.Label(select_frame, text="Character Slot:").pack(side=tk.LEFT, padx=5)
        
        self.world_slot_var = tk.IntVar(value=1)
        ttk.Combobox(
            select_frame,
            textvariable=self.world_slot_var,
            values=list(range(1, 11)),
            state="readonly",
            width=5,
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            select_frame,
            text="Load World State",
            command=self.load_world_state,
        ).pack(side=tk.LEFT, padx=5)
        
        # Location info
        location_frame = ttk.LabelFrame(
            self.parent, text="Current Location", padding=10
        )
        location_frame.pack(fill=tk.X, pady=10, padx=20)
        
        self.location_text = tk.Text(
            location_frame,
            height=6,
            font=("Consolas", 9),
            state="disabled",
            wrap=tk.WORD,
        )
        self.location_text.pack(fill=tk.X)
        
        # Teleport
        teleport_frame = ttk.LabelFrame(
            self.parent, text="Teleportation", padding=10
        )
        teleport_frame.pack(fill=tk.X, pady=10, padx=20)
        
        ttk.Label(teleport_frame, text="Teleport to safe location:").pack(
            anchor=tk.W, pady=5
        )
        
        teleport_buttons = ttk.Frame(teleport_frame)
        teleport_buttons.pack(fill=tk.X)
        
        locations = [
            ("Church of Elleh", "limgrave"),
            ("Roundtable Hold", "roundtable"),
            ("Lake-Facing Cliffs", "liurnia"),
            ("Altus Plateau", "altus"),
            ("Smoldering Wall", "caelid"),
            ("Leyndell Outskirts", "leyndell"),
        ]
        
        for i, (name, key) in enumerate(locations):
            ttk.Button(
                teleport_buttons,
                text=name,
                command=lambda k=key: self.teleport_character(k),
                width=20,
            ).grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky=tk.W)
    
    def load_world_state(self):
        """Load and display world state for selected character"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        slot_idx = self.world_slot_var.get() - 1
        
        try:
            slot = save_file.characters[slot_idx]
            
            if slot.is_empty():
                messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
                return
            
            # Get location info
            location_info = []
            location_info.append(f"Character Slot: {slot_idx + 1}")
            location_info.append("")
            
            if hasattr(slot, "map_id") and slot.map_id:
                location_info.append(f"Map ID: {slot.map_id.to_string_decimal()}")
                location_info.append(f"Area: {slot.map_id.get_area_name()}")
                if slot.map_id.is_dlc():
                    location_info.append("Location: DLC Area")
            else:
                location_info.append("Map ID: Unknown")
            
            location_info.append("")
            
            # Check if in DLC area
            if hasattr(slot, "dlc_data"):
                from er_save_manager.parser.world import DLC
                try:
                    dlc = DLC.from_bytes(slot.dlc_data)
                    if dlc.has_dlc_access():
                        location_info.append("DLC Access: Yes")
                    else:
                        location_info.append("DLC Access: No")
                except Exception:
                    location_info.append("DLC Access: Unknown")
            
            # Display in text widget
            self.location_text.config(state="normal")
            self.location_text.delete("1.0", tk.END)
            self.location_text.insert("1.0", "\n".join(location_info))
            self.location_text.config(state="disabled")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load world state:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def teleport_character(self, location):
        """Teleport character to a safe location"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        slot_idx = self.world_slot_var.get() - 1
        
        if not messagebox.askyesno(
            "Confirm Teleport",
            f"Teleport character in Slot {slot_idx + 1} to {location.replace('_', ' ').title()}?\n\nA backup will be created.",
        ):
            return
        
        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.fixes.teleport import TeleportFix
            
            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_teleport_to_{location}_slot_{slot_idx + 1}",
                    operation=f"teleport_to_{location}",
                    save=save_file,
                )
            
            teleport = TeleportFix(location)
            result = teleport.apply(save_file, slot_idx)
            
            if result.applied:
                save_file.recalculate_checksums()
                if save_path:
                    save_file.to_file(Path(save_path))
                
                if self.reload_save:
                    self.reload_save()
                
                details = "\n".join(result.details) if result.details else ""
                messagebox.showinfo(
                    "Success",
                    f"{result.description}\n\n{details}\n\nBackup saved to backup manager.",
                )
            else:
                messagebox.showwarning("Not Applied", result.description)
        
        except Exception as e:
            messagebox.showerror("Error", f"Teleport failed:\n{str(e)}")
            import traceback
            traceback.print_exc()
