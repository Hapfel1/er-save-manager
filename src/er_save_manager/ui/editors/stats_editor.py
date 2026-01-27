"""
Stats Editor Module
Handles character stats editing UI and logic
"""

import logging

import customtkinter as ctk

from er_save_manager.data import calculate_level_from_stats, get_class_data
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


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
            parent: Parent customtkinter widget
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

        self._logger = logging.getLogger(__name__)
        self.level_warning_label = None
        self.runes_var = None

        self.frame = None

    def setup_ui(self):
        """Setup the stats editor UI"""
        # Create scrollable frame
        self.frame = ctk.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
        )
        self.frame.pack(fill=ctk.BOTH, expand=True)

        # Bind mousewheel
        bind_mousewheel(self.frame)

        # Single row: Attributes and Resources side by side
        top_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        top_row.pack(fill=ctk.X, pady=5, padx=10)

        # Attributes on the left
        stats_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        stats_frame.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=(0, 5))

        ctk.CTkLabel(
            stats_frame,
            text="Attributes",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=ctk.W, padx=5, pady=(5, 0))

        stats_grid = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_grid.pack(fill=ctk.X, padx=5, pady=5)

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
            ctk.CTkLabel(stats_grid, text=f"{label}:").grid(
                row=i, column=0, sticky=ctk.W, padx=5, pady=5
            )

            var = ctk.IntVar(value=0)
            self.stat_vars[key] = var
            entry = ctk.CTkEntry(
                stats_grid,
                textvariable=var,
                width=120,
            )
            entry.grid(row=i, column=1, padx=5, pady=5)

            # Bind to calculate level on attribute change
            entry.bind("<KeyRelease>", lambda e: self.calculate_character_level())

        # Max HP/FP/Stamina on the right (base max values only, no active HP/FP/SP)
        resources_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        resources_frame.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=(5, 0))

        ctk.CTkLabel(
            resources_frame,
            text="Max Health/FP/Stamina",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=ctk.W, padx=5, pady=(5, 0))

        resources_grid = ctk.CTkFrame(resources_frame, fg_color="transparent")
        resources_grid.pack(fill=ctk.X, padx=5, pady=5)

        resources = [
            ("Max HP", "base_max_hp"),
            ("Max FP", "base_max_fp"),
            ("Max Stamina", "base_max_sp"),
        ]

        for i, (label, key) in enumerate(resources):
            ctk.CTkLabel(resources_grid, text=f"{label}:").grid(
                row=i, column=0, sticky=ctk.W, padx=5, pady=5
            )

            var = ctk.IntVar(value=0)
            self.stat_vars[key] = var
            ctk.CTkEntry(
                resources_grid,
                textvariable=var,
                width=120,
            ).grid(row=i, column=1, padx=5, pady=5)

        # Bottom row: Level & Runes in one compact frame
        bottom_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        bottom_row.pack(fill=ctk.X, pady=5, padx=10)

        other_frame = ctk.CTkFrame(bottom_row, fg_color=("gray86", "gray25"))
        other_frame.pack(fill=ctk.X)

        ctk.CTkLabel(
            other_frame,
            text="Level & Runes",
            font=("Segoe UI", 12, "bold"),
            text_color=("black", "white"),
        ).grid(row=0, column=0, columnspan=5, sticky=ctk.W, padx=5, pady=(5, 0))

        content_row = 1

        # Level row
        ctk.CTkLabel(other_frame, text="Level:", text_color=("black", "white")).grid(
            row=content_row, column=0, sticky=ctk.W, padx=5, pady=5
        )

        self.level_var = ctk.IntVar(value=0)
        ctk.CTkEntry(
            other_frame,
            textvariable=self.level_var,
            width=120,
            fg_color=("gray86", "gray25"),
            text_color=("black", "white"),
            border_color=("gray70", "gray40"),
            border_width=1,
        ).grid(row=content_row, column=1, padx=5, pady=5)

        ctk.CTkLabel(
            other_frame, text="Calculated Level:", text_color=("black", "white")
        ).grid(row=content_row, column=2, sticky=ctk.W, padx=(20, 5), pady=5)

        self.calculated_level_var = ctk.IntVar(value=0)
        ctk.CTkLabel(
            other_frame,
            textvariable=self.calculated_level_var,
            text_color=("black", "white"),
            font=("Segoe UI", 10, "bold"),
        ).grid(row=content_row, column=3, padx=5, pady=5)

        # Level warning
        self.level_warning_var = ctk.StringVar(value="")
        self.level_warning_label = ctk.CTkLabel(
            other_frame,
            textvariable=self.level_warning_var,
            text_color="red",
            font=("Segoe UI", 11),
        )
        self.level_warning_label.grid(
            row=content_row, column=4, padx=10, pady=5, sticky=ctk.W
        )

        # Runes row
        ctk.CTkLabel(other_frame, text="Runes:", text_color=("black", "white")).grid(
            row=content_row + 1, column=0, sticky=ctk.W, padx=5, pady=5
        )

        self.runes_var = ctk.IntVar(value=0)
        ctk.CTkEntry(
            other_frame,
            textvariable=self.runes_var,
            width=120,
            fg_color=("gray86", "gray25"),
            text_color=("black", "white"),
            border_color=("gray70", "gray40"),
            border_width=1,
        ).grid(
            row=content_row + 1, column=1, columnspan=2, sticky=ctk.W, padx=5, pady=5
        )

        # Apply button
        button_frame = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        button_frame.pack(fill=ctk.X, pady=10, padx=10)

        ctk.CTkLabel(
            button_frame,
            text="Actions",
            font=("Segoe UI", 12, "bold"),
            text_color=("black", "white"),
        ).pack(anchor=ctk.W, padx=5, pady=(5, 0))

        ctk.CTkButton(
            button_frame,
            text="Apply Changes",
            command=self.apply_changes,
            width=160,
        ).pack(side=ctk.LEFT, padx=5)

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

        # Debug: log raw values loaded from save
        try:
            self._logger.debug(
                "Loaded stats for slot %s: vig=%s mind=%s end=%s str=%s dex=%s int=%s fth=%s arc=%s lvl=%s runes=%s base_hp=%s base_fp=%s base_sp=%s",
                slot_idx,
                getattr(char, "vigor", None),
                getattr(char, "mind", None),
                getattr(char, "endurance", None),
                getattr(char, "strength", None),
                getattr(char, "dexterity", None),
                getattr(char, "intelligence", None),
                getattr(char, "faith", None),
                getattr(char, "arcane", None),
                getattr(char, "level", None),
                getattr(char, "runes", None),
                getattr(char, "base_max_hp", None),
                getattr(char, "base_max_fp", None),
                getattr(char, "base_max_sp", None),
            )
        except Exception:
            self._logger.exception("Failed logging stats for slot %s", slot_idx)

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
        self.level_var.set(str(getattr(char, "level", 0)))
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
            self.calculated_level_var.set(str(calculated_level))

            # Show class name in warning if available
            class_data = get_class_data(archetype)
            class_name = class_data.get("name", "Unknown")

            # Check if current level matches
            try:
                current_level = int(self.level_var.get())
            except (ValueError, TypeError):
                current_level = 0

            if current_level != calculated_level:
                self.level_warning_var.set(
                    f"⚠ Mismatch! Recommend {calculated_level} (based on {class_name})"
                )
            else:
                self.level_warning_var.set("")

        except Exception:
            self.calculated_level_var.set("0")
            self.level_warning_var.set("")

    def apply_changes(self):
        """Apply stat changes to save file"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save",
                "Please load a save file first!",
            )
            return

        slot_idx = self.get_char_slot()

        # Check for level mismatch
        current_level = int(self.level_var.get()) if self.level_var.get() else 0
        calculated_level = (
            int(self.calculated_level_var.get())
            if self.calculated_level_var.get()
            else 0
        )

        if current_level != calculated_level:
            response = CTkMessageBox.askyesno(
                "Level Mismatch",
                f"Current level ({current_level}) does not match calculated level ({calculated_level}) based on attributes.\n\n"
                f"It's recommended to set level to {calculated_level}.\n\n"
                f"Yes - Update level to {calculated_level}\n"
                f"No - Keep current level {current_level}",
            )

            if response:
                self.level_var.set(str(calculated_level))
            else:
                return

        response = CTkMessageBox.askyesno(
            "Confirm",
            f"Apply stat changes to Slot {slot_idx + 1}?\n\nA backup will be created.",
        )

        if not response:
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

                char.level = int(self.level_var.get()) if self.level_var.get() else 0
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

                    CTkMessageBox.showinfo(
                        "Success",
                        "Stats updated successfully!\n\nBackup saved to backup manager.",
                    )
                else:
                    CTkMessageBox.showwarning(
                        "Error",
                        "Offset not tracked - cannot save changes.",
                    )
            else:
                CTkMessageBox.showwarning(
                    "Error",
                    "Character has no game data",
                )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error",
                f"Failed to apply stat changes:\n{e}",
            )
