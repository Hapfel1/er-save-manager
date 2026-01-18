"""
Character Info Editor Module
Handles character information editing (name, body type, class, etc.)
"""

import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path


class CharacterInfoEditor:
    """Editor for character information and progression"""
    
    def __init__(self, parent, get_save_file_callback, get_char_slot_callback, get_save_path_callback):
        """
        Initialize character info editor
        
        Args:
            parent: Parent tkinter widget
            get_save_file_callback: Function that returns current save file
            get_char_slot_callback: Function that returns current character slot index
            get_save_path_callback: Function that returns save file path
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_char_slot = get_char_slot_callback
        self.get_save_path = get_save_path_callback
        
        # Character info variables
        self.char_name_var = None
        self.char_name_count_label = None
        self.char_body_type_var = None
        self.char_archetype_var = None
        self.char_voice_var = None
        self.char_gift_var = None
        self.char_talisman_slots_var = None
        self.char_spirit_level_var = None
        self.char_crimson_flask_var = None
        self.char_cerulean_flask_var = None
        
        self.frame = None
    
    def setup_ui(self):
        """Setup the character info editor UI"""
        # Create scrollable frame
        canvas = tk.Canvas(self.parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.parent, orient=tk.VERTICAL, command=canvas.yview)
        self.frame = ttk.Frame(canvas)
        
        self.frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mousewheel
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Character creation info
        creation_frame = ttk.LabelFrame(self.frame, text="Character Creation", padding=10)
        creation_frame.pack(fill=tk.X, pady=5)
        
        # Name
        ttk.Label(creation_frame, text="Name:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_name_var = tk.StringVar(value="")
        
        # Add validation for max 16 characters
        def validate_name(new_value):
            return len(new_value) <= 16
        
        name_vcmd = (creation_frame.register(validate_name), "%P")
        name_entry = ttk.Entry(
            creation_frame,
            textvariable=self.char_name_var,
            width=30,
            validate="key",
            validatecommand=name_vcmd,
        )
        name_entry.grid(row=0, column=1, columnspan=3, padx=5, pady=5)
        
        # Add label showing character count
        self.char_name_count_label = ttk.Label(
            creation_frame, text="0/16", font=("Segoe UI", 8), foreground="gray"
        )
        self.char_name_count_label.grid(row=0, column=4, padx=5, pady=5)
        
        # Update counter on change
        def update_name_count(*args):
            count = len(self.char_name_var.get())
            self.char_name_count_label.config(text=f"{count}/16")
        
        self.char_name_var.trace("w", update_name_count)
        
        # Body Type
        ttk.Label(creation_frame, text="Body Type:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_body_type_var = tk.IntVar(value=0)
        body_type_combo = ttk.Combobox(
            creation_frame,
            textvariable=self.char_body_type_var,
            values=["Type A (0)", "Type B (1)"],
            state="readonly",
            width=15,
        )
        body_type_combo.grid(row=1, column=1, padx=5, pady=5)
        
        # Archetype (starting class)
        ttk.Label(creation_frame, text="Archetype:").grid(
            row=1, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.char_archetype_var = tk.IntVar(value=0)
        ttk.Entry(creation_frame, textvariable=self.char_archetype_var, width=10).grid(
            row=1, column=3, padx=5, pady=5
        )
        
        # Voice type
        ttk.Label(creation_frame, text="Voice Type:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_voice_var = tk.IntVar(value=0)
        voice_combo = ttk.Combobox(
            creation_frame,
            textvariable=self.char_voice_var,
            values=["Young (0)", "Mature (1)", "Aged (2)"],
            state="readonly",
            width=15,
        )
        voice_combo.grid(row=2, column=1, padx=5, pady=5)
        
        # Keepsake gift
        ttk.Label(creation_frame, text="Keepsake:").grid(
            row=2, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.char_gift_var = tk.IntVar(value=0)
        ttk.Entry(creation_frame, textvariable=self.char_gift_var, width=10).grid(
            row=2, column=3, padx=5, pady=5
        )
        
        # Game progression info
        progression_frame = ttk.LabelFrame(self.frame, text="Game Progression", padding=10)
        progression_frame.pack(fill=tk.X, pady=5)
        
        # Additional talisman slots
        ttk.Label(progression_frame, text="Extra Talisman Slots:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_talisman_slots_var = tk.IntVar(value=0)
        ttk.Entry(
            progression_frame, textvariable=self.char_talisman_slots_var, width=10
        ).grid(row=0, column=1, padx=5, pady=5)
        
        # Spirit summon level
        ttk.Label(progression_frame, text="Spirit Summon Level:").grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.char_spirit_level_var = tk.IntVar(value=0)
        ttk.Entry(
            progression_frame, textvariable=self.char_spirit_level_var, width=10
        ).grid(row=0, column=3, padx=5, pady=5)
        
        # Flask info
        flask_frame = ttk.LabelFrame(self.frame, text="Flasks", padding=10)
        flask_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(flask_frame, text="Max Crimson Flasks:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_crimson_flask_var = tk.IntVar(value=0)
        ttk.Entry(flask_frame, textvariable=self.char_crimson_flask_var, width=10).grid(
            row=0, column=1, padx=5, pady=5
        )
        
        ttk.Label(flask_frame, text="Max Cerulean Flasks:").grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.char_cerulean_flask_var = tk.IntVar(value=0)
        ttk.Entry(flask_frame, textvariable=self.char_cerulean_flask_var, width=10).grid(
            row=0, column=3, padx=5, pady=5
        )
        
        # Apply button
        button_frame = ttk.LabelFrame(self.frame, text="Actions", padding=10)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            button_frame,
            text="Apply Changes",
            command=self.apply_changes,
            width=20,
        ).pack(side=tk.LEFT, padx=5)
    
    def load_character_info(self):
        """Load character info from current character slot"""
        save_file = self.get_save_file()
        if not save_file:
            return
        
        slot_idx = self.get_char_slot()
        if slot_idx < 0 or slot_idx >= len(save_file.characters):
            return
        
        slot = save_file.characters[slot_idx]
        
        if not slot or slot.is_empty():
            return
        
        if hasattr(slot, "player_game_data") and slot.player_game_data:
            char = slot.player_game_data
            
            self.char_name_var.set(getattr(char, "character_name", ""))
            self.char_body_type_var.set(getattr(char, "gender", 0))
            self.char_archetype_var.set(getattr(char, "archetype", 0))
            self.char_voice_var.set(getattr(char, "voice_type", 0))
            self.char_gift_var.set(getattr(char, "gift", 0))
            self.char_talisman_slots_var.set(
                getattr(char, "additional_talisman_slot_count", 0)
            )
            self.char_spirit_level_var.set(getattr(char, "summon_spirit_level", 0))
            self.char_crimson_flask_var.set(getattr(char, "max_crimson_flask_count", 0))
            self.char_cerulean_flask_var.set(getattr(char, "max_cerulean_flask_count", 0))
    
    def apply_changes(self):
        """Apply character info changes to save file"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        slot_idx = self.get_char_slot()
        
        if not messagebox.askyesno(
            "Confirm",
            f"Apply character info changes to Slot {slot_idx + 1}?\n\nA backup will be created.",
        ):
            return
        
        try:
            # Ensure raw_data is mutable
            if isinstance(save_file._raw_data, bytes):
                save_file._raw_data = bytearray(save_file._raw_data)
            
            # Create backup
            from er_save_manager.backup.manager import BackupManager
            
            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_edit_character_info_slot_{slot_idx + 1}",
                    operation=f"edit_character_info_slot_{slot_idx + 1}",
                    save=save_file,
                )
            
            # Modify character info
            slot = save_file.characters[slot_idx]
            if hasattr(slot, "player_game_data") and slot.player_game_data:
                char = slot.player_game_data
                
                char.character_name = self.char_name_var.get()
                char.gender = self.char_body_type_var.get()
                char.archetype = self.char_archetype_var.get()
                char.voice_type = self.char_voice_var.get()
                char.gift = self.char_gift_var.get()
                char.additional_talisman_slot_count = self.char_talisman_slots_var.get()
                char.summon_spirit_level = self.char_spirit_level_var.get()
                char.max_crimson_flask_count = self.char_crimson_flask_var.get()
                char.max_cerulean_flask_count = self.char_cerulean_flask_var.get()
                
                # Write back using offset
                if hasattr(slot, "player_game_data_offset"):
                    from io import BytesIO
                    
                    char_bytes = BytesIO()
                    char.write(char_bytes)
                    char_data = char_bytes.getvalue()
                    
                    # Calculate absolute offset
                    slot_offset = save_file._slot_offsets[slot_idx]
                    CHECKSUM_SIZE = 0x10
                    abs_offset = slot_offset + CHECKSUM_SIZE + slot.player_game_data_offset
                    
                    # Write to raw data
                    save_file._raw_data[abs_offset : abs_offset + len(char_data)] = char_data
                    
                    # Recalculate checksums and save
                    save_file.recalculate_checksums()
                    save_path = self.get_save_path()
                    if save_path:
                        save_file.to_file(Path(save_path))
                    
                    messagebox.showinfo(
                        "Success",
                        "Character info updated successfully!\n\nBackup saved to backup manager.",
                    )
                else:
                    messagebox.showerror("Error", "Offset not tracked")
            else:
                messagebox.showerror("Error", "Could not access character data")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply changes:\n{str(e)}")