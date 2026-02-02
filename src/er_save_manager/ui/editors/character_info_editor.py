"""
Character Info Editor Module (customtkinter)
Handles character information editing (name, body type, class, etc.)
"""

from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel, trace_variable


class CharacterInfoEditor:
    """Editor for character information and progression"""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_char_slot_callback,
        get_save_path_callback,
    ):
        """
        Initialize character info editor

        Args:
            parent: Parent widget
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
        self.char_ng_level_var = None

        self.frame = None

    def setup_ui(self):
        """Setup the character info editor UI"""
        self.frame = ctk.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
        )
        self.frame.pack(fill=ctk.BOTH, expand=True)
        bind_mousewheel(self.frame)

        # Character creation info
        creation_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        creation_frame.pack(fill=ctk.X, pady=5, padx=10)
        ctk.CTkLabel(
            creation_frame,
            text="Character Creation",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, columnspan=5, sticky=ctk.W, padx=5, pady=(5, 0))

        # Name
        ctk.CTkLabel(creation_frame, text="Name:").grid(
            row=1, column=0, sticky=ctk.W, padx=5, pady=5
        )
        self.char_name_var = ctk.StringVar(value="")

        # Add validation for max 16 characters
        def validate_name(new_value):
            return len(new_value) <= 16

        name_vcmd = (creation_frame.register(validate_name), "%P")
        name_entry = ctk.CTkEntry(
            creation_frame,
            textvariable=self.char_name_var,
            width=200,
            validate="key",
            validatecommand=name_vcmd,
        )
        name_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5)

        # Add label showing character count
        self.char_name_count_label = ctk.CTkLabel(
            creation_frame,
            text="0/16",
            font=("Segoe UI", 8),
        )
        self.char_name_count_label.grid(row=1, column=4, padx=5, pady=5)

        # Update counter on change
        def update_name_count(*args):
            count = len(self.char_name_var.get())
            self.char_name_count_label.configure(text=f"{count}/16")

        trace_variable(self.char_name_var, "w", update_name_count)

        # Body Type
        ctk.CTkLabel(creation_frame, text="Body Type:").grid(
            row=2, column=0, sticky=ctk.W, padx=5, pady=5
        )
        self.char_body_type_var = ctk.IntVar(value=0)
        body_type_combo = ctk.CTkComboBox(
            creation_frame,
            variable=self.char_body_type_var,
            values=["Type A (0)", "Type B (1)"],
            width=140,
        )
        body_type_combo.grid(row=2, column=1, padx=5, pady=5)

        # Archetype (starting class)
        ctk.CTkLabel(creation_frame, text="Archetype:").grid(
            row=2, column=2, sticky=ctk.W, padx=5, pady=5
        )
        self.char_archetype_var = ctk.IntVar(value=0)
        ctk.CTkEntry(
            creation_frame,
            textvariable=self.char_archetype_var,
            width=100,
        ).grid(row=2, column=3, padx=5, pady=5)

        # Voice type
        ctk.CTkLabel(creation_frame, text="Voice Type:").grid(
            row=3, column=0, sticky=ctk.W, padx=5, pady=5
        )
        self.char_voice_var = ctk.IntVar(value=0)
        voice_combo = ctk.CTkComboBox(
            creation_frame,
            variable=self.char_voice_var,
            values=["Young (0)", "Mature (1)", "Aged (2)"],
            width=140,
        )
        voice_combo.grid(row=3, column=1, padx=5, pady=5)

        # Keepsake gift
        ctk.CTkLabel(creation_frame, text="Keepsake:").grid(
            row=3, column=2, sticky=ctk.W, padx=5, pady=5
        )
        self.char_gift_var = ctk.IntVar(value=0)
        ctk.CTkEntry(
            creation_frame,
            textvariable=self.char_gift_var,
            width=100,
        ).grid(row=3, column=3, padx=5, pady=5)

        # Game progression info
        progression_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        progression_frame.pack(fill=ctk.X, pady=5, padx=10)
        ctk.CTkLabel(
            progression_frame,
            text="Game Progression",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, columnspan=6, sticky=ctk.W, padx=5, pady=(5, 0))

        # Additional talisman slots
        ctk.CTkLabel(
            progression_frame,
            text="Extra Talisman Slots:",
        ).grid(row=1, column=0, sticky=ctk.W, padx=5, pady=5)
        self.char_talisman_slots_var = ctk.IntVar(value=0)
        ctk.CTkEntry(
            progression_frame,
            textvariable=self.char_talisman_slots_var,
            width=100,
        ).grid(row=1, column=1, padx=5, pady=5)

        # Spirit summon level
        ctk.CTkLabel(
            progression_frame,
            text="Spirit Summon Level:",
        ).grid(row=1, column=2, sticky=ctk.W, padx=5, pady=5)
        self.char_spirit_level_var = ctk.IntVar(value=0)
        ctk.CTkEntry(
            progression_frame,
            textvariable=self.char_spirit_level_var,
            width=100,
        ).grid(row=1, column=3, padx=5, pady=5)

        # NG+ Level (event flag and ClearCount)
        ctk.CTkLabel(
            progression_frame,
            text="NG+ Level:",
        ).grid(row=1, column=4, sticky=ctk.W, padx=5, pady=5)
        self.char_ng_level_var = ctk.StringVar(value="NG (0)")
        ng_combo = ctk.CTkComboBox(
            progression_frame,
            variable=self.char_ng_level_var,
            values=[
                "NG (0)",
                "NG+ (1)",
                "NG+2 (2)",
                "NG+3 (3)",
                "NG+4 (4)",
                "NG+5 (5)",
                "NG+6 (6)",
                "NG+7+ (7+)",
            ],
            width=140,
        )
        ng_combo.grid(row=1, column=5, padx=5, pady=5)

        # Flask info
        flask_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        flask_frame.pack(fill=ctk.X, pady=5, padx=10)
        ctk.CTkLabel(
            flask_frame,
            text="Flasks",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky=ctk.W, padx=5, pady=(5, 0))

        ctk.CTkLabel(flask_frame, text="Max Crimson Flasks:").grid(
            row=1, column=0, sticky=ctk.W, padx=5, pady=5
        )
        self.char_crimson_flask_var = ctk.IntVar(value=0)
        ctk.CTkEntry(
            flask_frame,
            textvariable=self.char_crimson_flask_var,
            width=100,
        ).grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(flask_frame, text="Max Cerulean Flasks:").grid(
            row=1, column=2, sticky=ctk.W, padx=5, pady=5
        )
        self.char_cerulean_flask_var = ctk.IntVar(value=0)
        ctk.CTkEntry(
            flask_frame,
            textvariable=self.char_cerulean_flask_var,
            width=100,
        ).grid(row=1, column=3, padx=5, pady=5)

        # Apply button
        button_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        button_frame.pack(fill=ctk.X, pady=10, padx=10)
        ctk.CTkLabel(
            button_frame,
            text="Actions",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=ctk.W, padx=5, pady=(5, 0))

        ctk.CTkButton(
            button_frame,
            text="Apply Changes",
            command=self.apply_changes,
            width=180,
        ).pack(side=ctk.LEFT, padx=5, pady=5)

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
            self.char_cerulean_flask_var.set(
                getattr(char, "max_cerulean_flask_count", 0)
            )

        # Load NG+ level from ClearCount if possible, else from event flags
        clearcount = None
        if hasattr(slot, "unk_gamedataman_0x120_or_gamedataman_0x130"):
            clearcount = getattr(
                slot, "unk_gamedataman_0x120_or_gamedataman_0x130", None
            )
        if clearcount is not None and 0 <= clearcount <= 7:
            ng_label = [
                "NG (0)",
                "NG+ (1)",
                "NG+2 (2)",
                "NG+3 (3)",
                "NG+4 (4)",
                "NG+5 (5)",
                "NG+6 (6)",
                "NG+7+ (7+)",
            ][clearcount]
            self.char_ng_level_var.set(ng_label)
        else:
            self._load_ng_level(save_file, slot_idx)

    def apply_changes(self):
        """Apply character info changes to save file"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        slot_idx = self.get_char_slot()

        if not CTkMessageBox.askyesno(
            "Confirm",
            f"Apply character info changes to Slot {slot_idx + 1}?\n\nA backup will be created.",
            parent=self.parent,
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

                # Set ClearCount (NG+ playthroughs, raw field) from dropdown
                if hasattr(slot, "unk_gamedataman_0x120_or_gamedataman_0x130"):
                    ng_string = self.char_ng_level_var.get()
                    target_level = int(ng_string.split("(")[1].rstrip(")"))
                    slot.unk_gamedataman_0x120_or_gamedataman_0x130 = target_level

                # Write back using offset
                if hasattr(slot, "player_game_data_offset"):
                    from io import BytesIO

                    char_bytes = BytesIO()
                    char.write(char_bytes)
                    char_data = char_bytes.getvalue()

                    # Calculate absolute offset
                    slot_offset = save_file._slot_offsets[slot_idx]
                    CHECKSUM_SIZE = 0x10
                    abs_offset = (
                        slot_offset + CHECKSUM_SIZE + slot.player_game_data_offset
                    )

                    # Write to raw data
                    save_file._raw_data[abs_offset : abs_offset + len(char_data)] = (
                        char_data
                    )

                    # Apply NG+ level changes (event flag and ClearCount sync)
                    self._apply_ng_level(
                        save_file,
                        slot_idx,
                        force_clearcount=target_level,
                    )

                    # Rebuild slot bytes and write to _raw_data before saving
                    from er_save_manager.parser.slot_rebuild import rebuild_slot

                    rebuilt_bytes = rebuild_slot(slot)
                    slot_offset = save_file._slot_offsets[slot_idx]
                    CHECKSUM_SIZE = 0x10
                    abs_offset = slot_offset + CHECKSUM_SIZE
                    save_file._raw_data[
                        abs_offset : abs_offset + len(rebuilt_bytes)
                    ] = rebuilt_bytes

                    # Recalculate checksums and save
                    save_file.recalculate_checksums()
                    save_path = self.get_save_path()
                    if save_path:
                        save_file.to_file(Path(save_path))

                    # Reload character info to reflect changes
                    self.load_character_info()

                    CTkMessageBox.showinfo(
                        "Success",
                        "Character info updated successfully!\n\nBackup saved to backup manager.",
                        parent=self.parent,
                    )
                else:
                    CTkMessageBox.showerror(
                        "Error", "Offset not tracked", parent=self.parent
                    )
            else:
                CTkMessageBox.showerror(
                    "Error", "Could not access character data", parent=self.parent
                )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to apply changes:\n{str(e)}", parent=self.parent
            )

    def _load_ng_level(self, save_file, slot_idx):
        """Load NG+ level from event flags using EventFlags.get_flag (matches event flag tab)"""
        try:
            from er_save_manager.parser.event_flags import EventFlags

            ng_flag_ids = [50, 51, 52, 53, 54, 55, 56, 57]
            slot = save_file.characters[slot_idx]
            flags = slot.event_flags

            ng_bits = []
            for flag_id in ng_flag_ids:
                try:
                    is_set = EventFlags.get_flag(flags, flag_id)
                except Exception:
                    is_set = 0
                ng_bits.append(1 if is_set else 0)

            # Strict logic:
            # - If only flag 50 is set, show NG (0)
            # - If only one of 51-57 is set, show that NG+
            # - Otherwise, default to NG (0)
            if ng_bits[0] == 1 and sum(ng_bits[1:]) == 0:
                self.char_ng_level_var.set("NG (0)")
            elif sum(ng_bits[1:]) == 1 and ng_bits[0] == 0:
                idx = ng_bits[1:].index(1) + 1
                ng_label = [
                    "NG (0)",
                    "NG+ (1)",
                    "NG+2 (2)",
                    "NG+3 (3)",
                    "NG+4 (4)",
                    "NG+5 (5)",
                    "NG+6 (6)",
                    "NG+7+ (7+)",
                ][idx]
                self.char_ng_level_var.set(ng_label)
            else:
                self.char_ng_level_var.set("NG (0)")
        except Exception:
            self.char_ng_level_var.set("NG (0)")

    def _apply_ng_level(self, save_file, slot_idx, force_clearcount=None):
        """Apply NG+ level changes to save file using EventFlags.set_flag (matches event flag tab). Optionally force ClearCount."""
        try:
            from er_save_manager.parser.event_flags import EventFlags

            # Get the string value from combo box and extract the number
            ng_string = self.char_ng_level_var.get()
            target_level = int(ng_string.split("(")[1].rstrip(")"))

            ng_flag_ids = [50, 51, 52, 53, 54, 55, 56, 57]
            slot = save_file.characters[slot_idx]
            # Always operate on a mutable buffer
            flags = (
                bytearray(slot.event_flags)
                if not isinstance(slot.event_flags, bytearray)
                else slot.event_flags
            )

            # Clear all NG+ level flags first
            for flag_id in ng_flag_ids:
                try:
                    EventFlags.set_flag(flags, flag_id, False)
                except Exception:
                    pass

            # Set the target NG+ level flag
            target_flag_id = ng_flag_ids[target_level]
            try:
                EventFlags.set_flag(flags, target_flag_id, True)
            except Exception:
                pass

            # Write back as bytes
            slot.event_flags = bytes(flags)

            # Update ClearCount (the actual playthrough counter)
            # If force_clearcount is provided, use it, else set to target_level
            if hasattr(slot, "unk_gamedataman_0x120_or_gamedataman_0x130"):
                cc_val = (
                    force_clearcount if force_clearcount is not None else target_level
                )
                slot.unk_gamedataman_0x120_or_gamedataman_0x130 = cc_val

        except Exception:
            raise
