"""
Equipment Editor Module
Handles equipment editing UI and logic
"""

import tkinter as tk
from tkinter import messagebox, ttk

from er_save_manager.data.item_database import get_item_name


class EquipmentEditor:
    """Equipment editor for character equipment slots"""
    
    def __init__(self, parent, get_save_file_callback, get_char_slot_callback):
        """
        Initialize equipment editor
        
        Args:
            parent: Parent tkinter widget
            get_save_file_callback: Function that returns current save file
            get_char_slot_callback: Function that returns current character slot index
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_char_slot = get_char_slot_callback
        
        self.equipment_vars = {}
        self.equipment_name_labels = {}
        
        self.frame = None
        
    def setup_ui(self):
        """Setup the equipment editor UI"""
        # Main scrollable frame
        canvas = tk.Canvas(self.parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=canvas.yview)
        self.frame = ttk.Frame(canvas)
        
        self.frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mousewheel
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Top row: Weapons and Armor
        top_row = ttk.Frame(self.frame)
        top_row.pack(fill=tk.X, pady=5)
        
        # Weapons frame (left)
        weapons_frame = ttk.LabelFrame(top_row, text="Weapons", padding=10)
        weapons_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        weapons = [
            ("Right Hand 1", "right_hand_armament1"),
            ("Right Hand 2", "right_hand_armament2"),
            ("Right Hand 3", "right_hand_armament3"),
            ("Left Hand 1", "left_hand_armament1"),
            ("Left Hand 2", "left_hand_armament2"),
            ("Left Hand 3", "left_hand_armament3"),
        ]
        
        for i, (label, key) in enumerate(weapons):
            ttk.Label(weapons_frame, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=3
            )
            var = tk.IntVar(value=0)
            self.equipment_vars[key] = var
            entry = ttk.Entry(weapons_frame, textvariable=var, width=12)
            entry.grid(row=i, column=1, padx=5, pady=3)
            
            # Item name label
            name_label = ttk.Label(weapons_frame, text="", foreground="blue", width=28, anchor="w")
            name_label.grid(row=i, column=2, sticky=tk.W, padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            var.trace('w', lambda *args, k=key: self.update_equipment_name(k))
        
        # Armor frame (right)
        armor_frame = ttk.LabelFrame(top_row, text="Armor", padding=10)
        armor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        armor = [
            ("Head", "head"),
            ("Chest", "chest"),
            ("Arms", "arms"),
            ("Legs", "legs"),
        ]
        
        for i, (label, key) in enumerate(armor):
            ttk.Label(armor_frame, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=3
            )
            var = tk.IntVar(value=0)
            self.equipment_vars[key] = var
            entry = ttk.Entry(armor_frame, textvariable=var, width=12)
            entry.grid(row=i, column=1, padx=5, pady=3)
            
            # Item name label
            name_label = ttk.Label(armor_frame, text="", foreground="blue", width=28, anchor="w")
            name_label.grid(row=i, column=2, sticky=tk.W, padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            var.trace('w', lambda *args, k=key: self.update_equipment_name(k))
        
        # Middle row: Talismans and Arrows/Bolts
        middle_row = ttk.Frame(self.frame)
        middle_row.pack(fill=tk.X, pady=5)
        
        # Talismans frame (left)
        talisman_frame = ttk.LabelFrame(middle_row, text="Talismans", padding=10)
        talisman_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        talismans = [
            ("Talisman 1", "talisman1"),
            ("Talisman 2", "talisman2"),
            ("Talisman 3", "talisman3"),
            ("Talisman 4", "talisman4"),
        ]
        
        for i, (label, key) in enumerate(talismans):
            ttk.Label(talisman_frame, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=3
            )
            var = tk.IntVar(value=0)
            self.equipment_vars[key] = var
            entry = ttk.Entry(talisman_frame, textvariable=var, width=12)
            entry.grid(row=i, column=1, padx=5, pady=3)
            
            # Item name label
            name_label = ttk.Label(talisman_frame, text="", foreground="blue", width=28, anchor="w")
            name_label.grid(row=i, column=2, sticky=tk.W, padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            var.trace('w', lambda *args, k=key: self.update_equipment_name(k))
        
        # Arrows/Bolts frame (right)
        ammo_frame = ttk.LabelFrame(middle_row, text="Arrows & Bolts", padding=10)
        ammo_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        ammo = [
            ("Arrows 1", "arrows1"),
            ("Arrows 2", "arrows2"),
            ("Bolts 1", "bolts1"),
            ("Bolts 2", "bolts2"),
        ]
        
        for i, (label, key) in enumerate(ammo):
            ttk.Label(ammo_frame, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=3
            )
            var = tk.IntVar(value=0)
            self.equipment_vars[key] = var
            entry = ttk.Entry(ammo_frame, textvariable=var, width=12)
            entry.grid(row=i, column=1, padx=5, pady=3)
            
            # Item name label
            name_label = ttk.Label(ammo_frame, text="", foreground="blue", width=28, anchor="w")
            name_label.grid(row=i, column=2, sticky=tk.W, padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            var.trace('w', lambda *args, k=key: self.update_equipment_name(k))
        
        # Bottom: Spells (12 slots in 2 columns)
        spells_frame = ttk.LabelFrame(self.frame, text="Spells (Memory Slots)", padding=10)
        spells_frame.pack(fill=tk.X, pady=5)
        
        for i in range(12):
            row = i // 2
            col = (i % 2) * 3  # Changed to 3 to make room for name labels
            
            ttk.Label(spells_frame, text=f"Spell {i + 1}:").grid(
                row=row, column=col, sticky=tk.W, padx=5, pady=3
            )
            var = tk.IntVar(value=0)
            key = f"spell{i + 1}"
            self.equipment_vars[key] = var
            entry = ttk.Entry(spells_frame, textvariable=var, width=12)
            entry.grid(row=row, column=col + 1, padx=5, pady=3)
            
            # Item name label
            name_label = ttk.Label(spells_frame, text="", foreground="blue", width=20, anchor="w")
            name_label.grid(row=row, column=col + 2, sticky=tk.W, padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            var.trace('w', lambda *args, k=key: self.update_equipment_name(k))
        
        # Apply button
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            button_frame,
            text="Apply Equipment Changes",
            command=self.apply_changes,
            width=30
        ).pack()
    
    def load_equipment(self):
        """Load equipment from current character slot"""
        save_file = self.get_save_file()
        if not save_file:
            return
        
        slot_idx = self.get_char_slot()
        if slot_idx < 0 or slot_idx >= len(save_file.characters):
            return
        
        slot = save_file.characters[slot_idx]
        if not hasattr(slot, "equipped_items_item_id") or not slot.equipped_items_item_id:
            return
        
        equip = slot.equipped_items_item_id
        
        # Load all equipment IDs
        self.equipment_vars["right_hand_armament1"].set(getattr(equip, "right_hand_armament1", 0))
        self.equipment_vars["right_hand_armament2"].set(getattr(equip, "right_hand_armament2", 0))
        self.equipment_vars["right_hand_armament3"].set(getattr(equip, "right_hand_armament3", 0))
        self.equipment_vars["left_hand_armament1"].set(getattr(equip, "left_hand_armament1", 0))
        self.equipment_vars["left_hand_armament2"].set(getattr(equip, "left_hand_armament2", 0))
        self.equipment_vars["left_hand_armament3"].set(getattr(equip, "left_hand_armament3", 0))
        
        self.equipment_vars["head"].set(getattr(equip, "head", 0))
        self.equipment_vars["chest"].set(getattr(equip, "chest", 0))
        self.equipment_vars["arms"].set(getattr(equip, "arms", 0))
        self.equipment_vars["legs"].set(getattr(equip, "legs", 0))
        
        self.equipment_vars["talisman1"].set(getattr(equip, "talisman1", 0))
        self.equipment_vars["talisman2"].set(getattr(equip, "talisman2", 0))
        self.equipment_vars["talisman3"].set(getattr(equip, "talisman3", 0))
        self.equipment_vars["talisman4"].set(getattr(equip, "talisman4", 0))
        
        self.equipment_vars["arrows1"].set(getattr(equip, "arrows1", 0))
        self.equipment_vars["arrows2"].set(getattr(equip, "arrows2", 0))
        self.equipment_vars["bolts1"].set(getattr(equip, "bolts1", 0))
        self.equipment_vars["bolts2"].set(getattr(equip, "bolts2", 0))
        
        # Load spells if they exist
        for i in range(1, 13):
            key = f"spell{i}"
            if hasattr(equip, key):
                self.equipment_vars[key].set(getattr(equip, key, 0))
        
        # Update all name labels
        for key in self.equipment_vars.keys():
            if key in self.equipment_name_labels:
                self.update_equipment_name(key)
    
    def apply_changes(self):
        """Apply equipment changes to save file"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        slot_idx = self.get_char_slot()
        
        if not messagebox.askyesno(
            "Confirm",
            f"Apply equipment changes to Slot {slot_idx + 1}?\n\nA backup will be created.",
        ):
            return
        
        try:
            # Ensure raw_data is mutable
            if isinstance(save_file._raw_data, bytes):
                save_file._raw_data = bytearray(save_file._raw_data)
            
            # Create backup
            from er_save_manager.backup.manager import BackupManager
            from pathlib import Path
            
            save_path = getattr(save_file, '_save_path', None)
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_edit_equipment_slot_{slot_idx + 1}",
                    operation=f"edit_equipment_slot_{slot_idx + 1}",
                    save=save_file,
                )
            
            # Modify equipment
            slot = save_file.characters[slot_idx]
            if hasattr(slot, "equipped_items_item_id") and slot.equipped_items_item_id:
                equip = slot.equipped_items_item_id
                
                # Update all equipment
                equip.right_hand_armament1 = self.equipment_vars["right_hand_armament1"].get()
                equip.right_hand_armament2 = self.equipment_vars["right_hand_armament2"].get()
                equip.right_hand_armament3 = self.equipment_vars["right_hand_armament3"].get()
                equip.left_hand_armament1 = self.equipment_vars["left_hand_armament1"].get()
                equip.left_hand_armament2 = self.equipment_vars["left_hand_armament2"].get()
                equip.left_hand_armament3 = self.equipment_vars["left_hand_armament3"].get()
                
                equip.head = self.equipment_vars["head"].get()
                equip.chest = self.equipment_vars["chest"].get()
                equip.arms = self.equipment_vars["arms"].get()
                equip.legs = self.equipment_vars["legs"].get()
                
                equip.talisman1 = self.equipment_vars["talisman1"].get()
                equip.talisman2 = self.equipment_vars["talisman2"].get()
                equip.talisman3 = self.equipment_vars["talisman3"].get()
                equip.talisman4 = self.equipment_vars["talisman4"].get()
                
                equip.arrows1 = self.equipment_vars["arrows1"].get()
                equip.arrows2 = self.equipment_vars["arrows2"].get()
                equip.bolts1 = self.equipment_vars["bolts1"].get()
                equip.bolts2 = self.equipment_vars["bolts2"].get()
                
                # Update spells
                for i in range(1, 13):
                    key = f"spell{i}"
                    if hasattr(equip, key):
                        setattr(equip, key, self.equipment_vars[key].get())
                
                messagebox.showinfo("Success", "Equipment updated successfully!")
            else:
                messagebox.showerror("Error", "Character has no equipment data")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply equipment changes:\n{e}")
    
    def update_equipment_name(self, equipment_key):
        """Update equipment name label when ID changes"""
        if equipment_key not in self.equipment_name_labels:
            return
        
        try:
            item_id = self.equipment_vars[equipment_key].get()
            if item_id == 0 or item_id == -1:
                self.equipment_name_labels[equipment_key].config(text="")
                return
            
            # Get name from item database
            item_name = get_item_name(item_id)
            
            # Truncate if too long
            if len(item_name) > 28:
                item_name = item_name[:25] + "..."
            
            self.equipment_name_labels[equipment_key].config(text=item_name)
        except Exception:
            self.equipment_name_labels[equipment_key].config(text="(Unknown)")
