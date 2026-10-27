"""
Save Inspector Tab (customtkinter version)
Displays character list with quick fix functionality
"""

import customtkinter as ctk

from er_save_manager.data.starting_classes import get_class_data
from er_save_manager.fixes.wiped_slot import is_wiped_slot
from er_save_manager.ui.character_list import (
    CharacterList,
    CharacterRow,
    columns,
    format_playtime,
)
from er_save_manager.ui.dialogs.character_details import scan_character
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.toast import notify
from er_save_manager.ui.version_mismatch_dialog import VersionMismatchDialog


class SaveInspectorTab:
    """Tab for viewing save file contents and quick fixes"""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_save_path_callback,
        reload_callback,
        show_details_callback,
        on_slot_selected_callback=None,
    ):
        """
        Initialize save inspector tab

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_save_path_callback: Function that returns save file path
            reload_callback: Function to reload save file
            show_details_callback: Function to show character details dialog (slot_idx)
            on_slot_selected_callback: Function called when slot is selected (slot_idx)
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback
        self.show_details = show_details_callback
        self.on_slot_selected = on_slot_selected_callback

        self.selected_slot = None

    def setup_ui(self):
        """Setup the save fixer tab UI"""
        char_frame = ctk.CTkFrame(self.parent, corner_radius=12)
        char_frame.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(char_frame, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            header,
            text="Save Fixer",
            font=("Inter", 16, "bold"),
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="View All Issues",
            command=self.show_character_details,
            width=180,
        ).pack(side="right")

        ctk.CTkButton(
            header,
            text="Mismatched Game/Save Version?",
            command=self.show_version_mismatch_dialog,
            fg_color=("gray70", "gray35"),
            width=220,
        ).pack(side="right", padx=(0, 8))

        instructions_frame = ctk.CTkFrame(char_frame, fg_color="transparent")
        instructions_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            instructions_frame,
            text="Select a character and click 'View All Issues' to scan for problems and apply fixes",
            font=("Inter", 11),
            text_color=("gray40", "gray70"),
        ).pack(side="left", anchor="w")

        self.list = CharacterList(char_frame, on_select=self._select_slot)
        self.list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _select_slot(self, slot_index: int) -> None:
        self.selected_slot = slot_index
        if self.on_slot_selected:
            self.on_slot_selected(slot_index)

    def populate_character_list(self):
        """Populate the character list"""
        self.list.clear()
        self.selected_slot = None

        save_file = self.get_save_file()
        if not save_file:
            return

        try:
            profiles = None
            try:
                if save_file.user_data_10_parsed:
                    profiles = save_file.user_data_10_parsed.profile_summary.profiles
            except Exception as e:
                print(f"Warning: Could not load profiles: {e}")

            rows = []
            for slot_idx in save_file.get_active_slots():
                slot = save_file.characters[slot_idx]
                if not slot:
                    continue
                try:
                    rows.append(self._character_row(save_file, slot_idx, profiles))
                except Exception as e:
                    rows.append(
                        CharacterRow(
                            slot_idx,
                            f"Character {slot_idx + 1}",
                            issues=[f"The slot could not be read: {e}"],
                        )
                    )
                    print(f"Error loading slot {slot_idx}: {e}")

            self.list.show(
                columns("Runes", extras=(("location", "Location", 110),)), rows
            )

        except Exception as e:
            self.list.message("Error loading characters")
            CTkMessageBox.showerror(
                "Load Failed",
                f"Failed to load character list:\n{str(e)}",
                parent=self.parent,
            )
            import traceback

            traceback.print_exc()

    @staticmethod
    def _character_row(save_file, slot_idx, profiles) -> CharacterRow:
        slot = save_file.characters[slot_idx]
        name = f"Character {slot_idx + 1}"
        values = {}
        if profiles and slot_idx < len(profiles):
            profile = profiles[slot_idx]
            name = profile.character_name or name
            if profile.level:
                values["level"] = str(profile.level)
            values["playtime"] = format_playtime(profile.seconds_played)

        if is_wiped_slot(save_file, slot_idx):
            values["location"] = "Data wiped"
            return CharacterRow(slot_idx, name, values, ["Character data wiped"])

        pgd = slot.player_game_data
        values["class"] = get_class_data(pgd.archetype, save_file.is_convergence)[
            "name"
        ]
        values["currency"] = f"{pgd.runes:,}"
        # Misparsed slots read garbage here
        ng = slot.get_ng_plus()
        values["ng"] = f"NG+{ng}" if ng < 100 else "NG+?"
        if getattr(slot, "map_id", None):
            values["location"] = slot.map_id.to_string_decimal()
        return CharacterRow(
            slot_idx, name, values, scan_character(save_file, slot_idx).issue_texts
        )

    def show_character_details(self):
        """Show character details dialog"""
        if self.selected_slot is None:
            notify(self.parent, "Select a character first.", "warning")
            return

        if self.show_details:
            self.show_details(self.selected_slot)

    def show_version_mismatch_dialog(self):
        """Open the save/game version mismatch fix dialog."""
        save_file = self.get_save_file()
        if not save_file:
            notify(self.parent, "Load a save file first.", "warning")
            return

        VersionMismatchDialog(
            self.parent.winfo_toplevel(),
            save_file,
            self.get_save_path(),
            self.reload_save,
        )
