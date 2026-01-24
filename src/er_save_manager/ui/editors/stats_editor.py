"""
Stats Editor Module
Handles character stats editing UI and logic
"""

import tkinter as tk
from tkinter import messagebox, ttk

from er_save_manager.data import calculate_level_from_stats, get_class_data


class StatsEditor:
    """Stats editor for character attributes, level, and runes"""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_char_slot_callback,
        get_save_path_callback,
    ):
        """
        Initialize stats editor

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

        self.stat_vars = {}
        self.level_var = None
        self.calculated_level_var = None
        self.level_warning_var = None
        self.level_warning_label = None
        self.runes_var = None

        self.frame = None

    def setup_ui(self):
        """Setup the stats editor UI"""
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

        # Single row: Attributes and Resources side by side
        top_row = ttk.Frame(self.frame)
        top_row.pack(fill=tk.X, pady=5)

        # Attributes on the left
        stats_frame = ttk.LabelFrame(top_row, text="Attributes", padding=10)
        stats_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        attributes = [
            ("Vigor", "vigor"),
            ("Mind", "mind"),
            ("Endurance", "endurance"),
            ("Strength", "strength"),
            ("Dexterity", "dexterity"),
            ("Intelligence", "intelligence"),
            ("Faith", "faith"),
            ("Arcane", "arcane"),
        ]

        for i, (label, key) in enumerate(attributes):
            ttk.Label(stats_frame, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=5
            )

            var = tk.IntVar(value=0)
            self.stat_vars[key] = var
            entry = ttk.Entry(stats_frame, textvariable=var, width=10)
            entry.grid(row=i, column=1, padx=5, pady=5)

            # Bind to calculate level on attribute change
            entry.bind("<KeyRelease>", lambda e: self.calculate_character_level())

        # Max HP/FP/Stamina on the right (base max values only, no active HP/FP/SP)
        resources_frame = ttk.LabelFrame(
            top_row, text="Max Health/FP/Stamina", padding=10
        )
        resources_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        resources = [
            ("Max HP", "base_max_hp"),
            ("Max FP", "base_max_fp"),
            ("Max Stamina", "base_max_sp"),
        ]

        for i, (label, key) in enumerate(resources):
            ttk.Label(resources_frame, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=5
            )

            var = tk.IntVar(value=0)
            self.stat_vars[key] = var
            ttk.Entry(resources_frame, textvariable=var, width=10).grid(
                row=i, column=1, padx=5, pady=5
            )

        # Bottom row: Level & Runes in one compact frame
        bottom_row = ttk.Frame(self.frame)
        bottom_row.pack(fill=tk.X, pady=5)

        other_frame = ttk.LabelFrame(bottom_row, text="Level & Runes", padding=10)
        other_frame.pack(fill=tk.X)

        # Level row
        ttk.Label(other_frame, text="Level:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.level_var = tk.IntVar(value=0)
        ttk.Entry(other_frame, textvariable=self.level_var, width=10).grid(
            row=0, column=1, padx=5, pady=5
        )

        ttk.Label(other_frame, text="Calculated Level:").grid(
            row=0, column=2, sticky=tk.W, padx=(20, 5), pady=5
        )
        self.calculated_level_var = tk.IntVar(value=0)
        ttk.Label(
            other_frame,
            textvariable=self.calculated_level_var,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=3, padx=5, pady=5)

        # Level warning
        self.level_warning_var = tk.StringVar(value="")
        self.level_warning_label = ttk.Label(
            other_frame,
            textvariable=self.level_warning_var,
            foreground="red",
            font=("Segoe UI", 9),
        )
        self.level_warning_label.grid(row=0, column=4, padx=10, pady=5, sticky=tk.W)

        # Runes row
        ttk.Label(other_frame, text="Runes:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.runes_var = tk.IntVar(value=0)
        ttk.Entry(other_frame, textvariable=self.runes_var, width=15).grid(
            row=1, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5
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

    def load_stats(self):
        """Load stats from current character slot"""
        save_file = self.get_save_file()
        if not save_file:
            return

        slot_idx = self.get_char_slot()
        if slot_idx < 0 or slot_idx >= len(save_file.characters):
            return

        slot = save_file.characters[slot_idx]
        if not hasattr(slot, "player_game_data") or not slot.player_game_data:
            return

        char = slot.player_game_data

        # Load attributes
        self.stat_vars["vigor"].set(getattr(char, "vigor", 0))
        self.stat_vars["mind"].set(getattr(char, "mind", 0))
        self.stat_vars["endurance"].set(getattr(char, "endurance", 0))
        self.stat_vars["strength"].set(getattr(char, "strength", 0))
        self.stat_vars["dexterity"].set(getattr(char, "dexterity", 0))
        self.stat_vars["intelligence"].set(getattr(char, "intelligence", 0))
        self.stat_vars["faith"].set(getattr(char, "faith", 0))
        self.stat_vars["arcane"].set(getattr(char, "arcane", 0))

        # Load base max resources only
        self.stat_vars["base_max_hp"].set(getattr(char, "base_max_hp", 0))
        self.stat_vars["base_max_fp"].set(getattr(char, "base_max_fp", 0))
        self.stat_vars["base_max_sp"].set(getattr(char, "base_max_sp", 0))

        # Load level and runes
        self.level_var.set(getattr(char, "level", 0))
        self.runes_var.set(getattr(char, "runes", 0))

        # Calculate level
        self.calculate_character_level()

    def calculate_character_level(self):
        """Calculate expected character level from attributes based on starting class"""
        try:
            # Get archetype from currently loaded character
            archetype = 9  # Default to Wretch

            save_file = self.get_save_file()
            if save_file:
                slot_idx = self.get_char_slot()
                try:
                    slot = save_file.characters[slot_idx]
                    if (
                        slot
                        and hasattr(slot, "player_game_data")
                        and slot.player_game_data
                    ):
                        archetype = slot.player_game_data.archetype
                except Exception:
                    pass

            # Get current attributes
            vigor = self.stat_vars["vigor"].get()
            mind = self.stat_vars["mind"].get()
            endurance = self.stat_vars["endurance"].get()
            strength = self.stat_vars["strength"].get()
            dexterity = self.stat_vars["dexterity"].get()
            intelligence = self.stat_vars["intelligence"].get()
            faith = self.stat_vars["faith"].get()
            arcane = self.stat_vars["arcane"].get()

            # Calculate level using actual class data
            calculated_level = calculate_level_from_stats(
                vigor,
                mind,
                endurance,
                strength,
                dexterity,
                intelligence,
                faith,
                arcane,
                archetype,
            )

            # Update calculated level display
            self.calculated_level_var.set(calculated_level)

            # Show class name in warning if available
            class_data = get_class_data(archetype)
            class_name = class_data.get("name", "Unknown")

            # Check if current level matches
            current_level = self.level_var.get()
            if current_level != calculated_level:
                self.level_warning_var.set(
                    f"⚠ Mismatch! Recommend {calculated_level} (based on {class_name})"
                )
            else:
                self.level_warning_var.set("")

        except Exception:
            self.calculated_level_var.set(0)
            self.level_warning_var.set("")

    def apply_changes(self):
        """Apply stat changes to save file"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.get_char_slot()

        # Check for level mismatch
        current_level = self.level_var.get()
        calculated_level = self.calculated_level_var.get()

        if current_level != calculated_level:
            response = messagebox.askyesnocancel(
                "Level Mismatch",
                f"Current level ({current_level}) does not match calculated level ({calculated_level}) based on attributes.\n\n"
                f"It's recommended to set level to {calculated_level}.\n\n"
                f"Yes - Update level to {calculated_level}\n"
                f"No - Keep current level {current_level}\n"
                f"Cancel - Abort changes",
            )

            if response is None:  # Cancel
                return
            elif response:  # Yes - update to calculated level
                self.level_var.set(calculated_level)

        if not messagebox.askyesno(
            "Confirm",
            f"Apply stat changes to Slot {slot_idx + 1}?\n\nA backup will be created.",
        ):
            return

        try:
            # Ensure raw_data is mutable
            if isinstance(save_file._raw_data, bytes):
                save_file._raw_data = bytearray(save_file._raw_data)

            # Create backup
            from pathlib import Path

            from er_save_manager.backup.manager import BackupManager

            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_edit_stats_slot_{slot_idx + 1}",
                    operation=f"edit_stats_slot_{slot_idx + 1}",
                    save=save_file,
                )

            # Modify stats
            slot = save_file.characters[slot_idx]
            if hasattr(slot, "player_game_data") and slot.player_game_data:
                char = slot.player_game_data

                # Update stats in memory
                char.vigor = self.stat_vars["vigor"].get()
                char.mind = self.stat_vars["mind"].get()
                char.endurance = self.stat_vars["endurance"].get()
                char.strength = self.stat_vars["strength"].get()
                char.dexterity = self.stat_vars["dexterity"].get()
                char.intelligence = self.stat_vars["intelligence"].get()
                char.faith = self.stat_vars["faith"].get()
                char.arcane = self.stat_vars["arcane"].get()

                char.level = self.level_var.get()
                char.runes = self.runes_var.get()

                char.base_max_hp = self.stat_vars["base_max_hp"].get()
                char.base_max_fp = self.stat_vars["base_max_fp"].get()
                char.base_max_sp = self.stat_vars["base_max_sp"].get()

                # Write back to raw data using tracked offset
                if (
                    hasattr(slot, "player_game_data_offset")
                    and slot.player_game_data_offset >= 0
                ):
                    from io import BytesIO

                    # Serialize character data
                    char_bytes = BytesIO()
                    char.write(char_bytes)
                    char_data = char_bytes.getvalue()

                    # Verify size
                    if len(char_data) != 432:  # PlayerGameData is exactly 432 bytes
                        raise RuntimeError(
                            f"PlayerGameData serialization error: expected 432 bytes, got {len(char_data)}"
                        )

                    # Calculate absolute offset in save file using tracked offset
                    slot_offset = save_file._slot_offsets[slot_idx]
                    CHECKSUM_SIZE = 0x10

                    abs_offset = (
                        slot_offset + CHECKSUM_SIZE + slot.player_game_data_offset
                    )

                    # Write to raw data
                    save_file._raw_data[abs_offset : abs_offset + len(char_data)] = (
                        char_data
                    )

                    # Recalculate checksums and save
                    save_file.recalculate_checksums()
                    save_path = self.get_save_path()
                    if save_path:
                        save_file.to_file(Path(save_path))

                    messagebox.showinfo(
                        "Success",
                        "Stats updated successfully!\n\nBackup saved to backup manager.",
                    )
                else:
                    messagebox.showerror(
                        "Error",
                        "Offset not tracked - cannot save changes.",
                    )
            else:
                messagebox.showerror("Error", "Character has no game data")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply stat changes:\n{e}")
