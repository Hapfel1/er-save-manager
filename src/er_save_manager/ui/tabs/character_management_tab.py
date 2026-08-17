"""
Character Management Tab (CustomTkinter)
Handles copy, transfer, swap, export, import, and delete operations
"""

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.i18n import t
from er_save_manager.platform import PlatformUtils
from er_save_manager.ui.dialogs.save_selector import SaveSelectorDialog
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel, pick_file


class CharacterManagementTab:
    """Tab for character management operations"""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_save_path_callback,
        reload_callback,
        show_toast_callback,
        is_game_running_callback=None,
    ):
        """
        Initialize character management tab

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_save_path_callback: Function that returns save file path
            reload_callback: Function to reload save file after operations
            show_toast_callback: Function to show toast notifications
            is_game_running_callback: Function to check if game is running
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback
        self.show_toast = show_toast_callback
        self.is_game_running = is_game_running_callback

        # Operation variables
        self.char_operation_var = None
        self.operation_map = {}
        self.operation_map_reverse = {}

        # Panel widgets
        self.char_ops_panel = None

        # Operation-specific variables
        self.copy_from_var = None
        self.copy_to_var = None
        self.transfer_from_var = None
        self.swap_a_var = None
        self.swap_b_var = None
        self.export_slot_var = None
        self.import_slot_var = None
        self.delete_slot_var = None

    def setup_ui(self):
        """Setup the character management tab UI"""
        # Create scrollable frame wrapper
        scroll_frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(scroll_frame)

        # Title
        title_label = ctk.CTkLabel(
            scroll_frame,
            text=t("Character Management"),
            font=("Segoe UI", 16, "bold"),
        )
        title_label.pack(pady=10)

        # Info label
        info_text = ctk.CTkLabel(
            scroll_frame,
            text=t(
                "Transfer characters between save files, copy slots, manage your character roster, share and download community builds"
            ),
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        )
        info_text.pack(pady=5)

        # Character Browser button
        browser_frame = ctk.CTkFrame(
            scroll_frame,
            corner_radius=10,
        )
        browser_frame.pack(fill=tk.X, padx=20, pady=(10, 5))

        ctk.CTkButton(
            browser_frame,
            text=t("🌐 Browse Character Library"),
            command=self.open_character_browser,
            width=250,
            height=40,
        ).pack(side=tk.LEFT, padx=15, pady=10)

        ctk.CTkLabel(
            browser_frame,
            text=t("Download complete character builds from the community"),
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(side=tk.LEFT, padx=(10, 15))

        # Operation selector frame
        selector_frame = ctk.CTkFrame(
            scroll_frame,
            corner_radius=10,
        )
        selector_frame.pack(fill=tk.X, padx=20, pady=10)

        # Add label to selector frame
        selector_label = ctk.CTkLabel(
            selector_frame,
            text=t("Select Operation"),
            font=("Segoe UI", 12, "bold"),
        )
        selector_label.pack(anchor=tk.W, padx=15, pady=(10, 5))

        # Inner frame for controls
        selector_controls = ctk.CTkFrame(selector_frame, fg_color="transparent")
        selector_controls.pack(fill=tk.X, padx=15, pady=(5, 15))

        self.char_operation_var = tk.StringVar(value="copy")

        operations = [
            ("Copy Character", "copy"),
            ("Transfer to Another Save", "transfer"),
            ("Swap Slots", "swap"),
            ("Export Character", "export"),
            ("Import Character", "import"),
            ("Delete Character", "delete"),
        ]

        # Operation label
        op_label = ctk.CTkLabel(selector_controls, text=t("Operation:"))
        op_label.pack(side=tk.LEFT, padx=(0, 10))

        # Dropdown selector
        operation_combo = ctk.CTkComboBox(
            selector_controls,
            variable=self.char_operation_var,
            values=[op[0] for op in operations],
            state="readonly",
            width=300,
            command=self.update_operation_panel,
        )
        operation_combo.pack(side=tk.LEFT, padx=5)

        # Map display names to internal values
        self.operation_map = {op[0]: op[1] for op in operations}
        self.operation_map_reverse = {op[1]: op[0] for op in operations}

        # Set initial display value
        operation_combo.set("Copy Character")

        # Operation panel frame
        self.char_ops_panel = ctk.CTkFrame(
            scroll_frame,
            corner_radius=10,
        )
        self.char_ops_panel.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Add label to operation panel
        panel_label = ctk.CTkLabel(
            self.char_ops_panel,
            text=t("Operation Details"),
            font=("Segoe UI", 12, "bold"),
        )
        panel_label.pack(anchor=tk.W, padx=15, pady=(10, 5))

        # Create scrollable frame for operation-specific content
        self.ops_scrollable = ctk.CTkScrollableFrame(
            self.char_ops_panel,
            fg_color="transparent",
        )
        self.ops_scrollable.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 15))

        # Bind mousewheel to scrollable frame
        bind_mousewheel(self.ops_scrollable)

        # Initialize with copy operation
        self.update_operation_panel()

    def update_operation_panel(self, value=None):
        """Update the operation panel based on selected operation - optimized for performance"""
        # Clear existing widgets efficiently
        for widget in self.ops_scrollable.winfo_children():
            widget.destroy()

        # Get internal operation value from display name
        display_name = self.char_operation_var.get()
        operation = self.operation_map.get(display_name, "copy")

        # Create appropriate panel based on operation
        if operation == "copy":
            self._setup_copy_panel()
        elif operation == "transfer":
            self._setup_transfer_panel()
        elif operation == "swap":
            self._setup_swap_panel()
        elif operation == "export":
            self._setup_export_panel()
        elif operation == "import":
            self._setup_import_panel()
        elif operation == "delete":
            self._setup_delete_panel()

    def _get_slot_display_names(self, save_file=None):
        """Get display names for all slots"""
        save_file = save_file or self.get_save_file()
        if not save_file:
            return [str(i) for i in range(1, 11)]

        slot_names = []
        profiles = None

        try:
            if save_file.user_data_10_parsed:
                profiles = save_file.user_data_10_parsed.profile_summary.profiles
        except Exception:
            pass

        for i in range(10):
            slot_num = i + 1
            char = save_file.characters[i]

            if char.is_empty():
                slot_names.append(f"{slot_num} - Empty")
                continue

            char_name = "Unknown"
            if profiles and i < len(profiles):
                try:
                    char_name = profiles[i].character_name or "Unknown"
                except Exception:
                    pass

            slot_names.append(f"{slot_num} - {char_name}")

        return slot_names

    def refresh_slot_names(self):
        """Refresh slot display names after save file changes"""
        # Only refresh if panel is visible
        if not hasattr(self, "char_ops_panel"):
            return

        # Re-run current panel setup to refresh names
        self.update_operation_panel()

    def _setup_copy_panel(self):
        """Setup copy operation panel"""
        desc_label = ctk.CTkLabel(
            self.ops_scrollable,
            text=t("Copy a character from one slot to another in the same save file"),
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        )
        desc_label.pack(anchor=tk.W, pady=10)

        controls = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)

        from_label = ctk.CTkLabel(controls, text=t("From Slot:"))
        from_label.pack(side=tk.LEFT, padx=5)

        self.copy_from_var = tk.IntVar(value=1)
        slot_names = self._get_slot_display_names()
        from_combo = ctk.CTkComboBox(
            controls,
            values=slot_names,
            state="readonly",
            width=200,
            command=lambda v: self.copy_from_var.set(int(v.split(" - ")[0])),
        )
        from_combo.set(slot_names[0])
        from_combo.pack(side=tk.LEFT, padx=5)

        to_label = ctk.CTkLabel(controls, text=t("To Slot:"))
        to_label.pack(side=tk.LEFT, padx=15)

        self.copy_to_var = tk.IntVar(value=2)
        to_combo = ctk.CTkComboBox(
            controls,
            variable=self.copy_to_var,
            values=slot_names,
            state="readonly",
            width=200,
            command=lambda v: self.copy_to_var.set(int(v.split(" - ")[0])),
        )
        to_combo.set(slot_names[1])
        to_combo.pack(side=tk.LEFT, padx=5)

        copy_button = ctk.CTkButton(
            controls,
            text=t("Copy Character"),
            command=self.copy_character,
            width=150,
        )
        copy_button.pack(side=tk.LEFT, padx=20)

    def _setup_transfer_panel(self):
        """Setup transfer operation panel"""
        desc_label = ctk.CTkLabel(
            self.ops_scrollable,
            text=t("Transfer a character to a different save file"),
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        )
        desc_label.pack(anchor=tk.W, pady=10)

        controls = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)

        from_label = ctk.CTkLabel(controls, text=t("From Slot:"))
        from_label.pack(side=tk.LEFT, padx=5)

        self.transfer_from_var = tk.IntVar(value=1)
        slot_names = self._get_slot_display_names()
        from_combo = ctk.CTkComboBox(
            controls,
            values=slot_names,
            state="readonly",
            width=200,
            command=lambda v: self.transfer_from_var.set(int(v.split(" - ")[0])),
        )
        from_combo.set(slot_names[0])
        from_combo.pack(side=tk.LEFT, padx=5)

        transfer_button = ctk.CTkButton(
            controls,
            text=t("Select Target Save..."),
            command=self.transfer_character,
            width=180,
        )
        transfer_button.pack(side=tk.LEFT, padx=20)

    def _setup_swap_panel(self):
        """Setup swap operation panel"""
        desc_label = ctk.CTkLabel(
            self.ops_scrollable,
            text=t("Exchange two character slots"),
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        )
        desc_label.pack(anchor=tk.W, pady=10)

        controls = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)

        slot_a_label = ctk.CTkLabel(controls, text=t("Slot A:"))
        slot_a_label.pack(side=tk.LEFT, padx=5)

        self.swap_a_var = tk.IntVar(value=1)
        slot_names = self._get_slot_display_names()
        slot_a_combo = ctk.CTkComboBox(
            controls,
            values=slot_names,
            state="readonly",
            width=200,
            command=lambda v: self.swap_a_var.set(int(v.split(" - ")[0])),
        )
        slot_a_combo.set(slot_names[0])
        slot_a_combo.pack(side=tk.LEFT, padx=5)

        slot_b_label = ctk.CTkLabel(controls, text=t("Slot B:"))
        slot_b_label.pack(side=tk.LEFT, padx=15)

        self.swap_b_var = tk.IntVar(value=2)
        slot_b_combo = ctk.CTkComboBox(
            controls,
            values=slot_names,
            state="readonly",
            width=200,
            command=lambda v: self.swap_b_var.set(int(v.split(" - ")[0])),
        )
        slot_b_combo.set(slot_names[1])
        slot_b_combo.pack(side=tk.LEFT, padx=5)

        swap_button = ctk.CTkButton(
            controls,
            text=t("Swap Slots"),
            command=self.swap_characters,
            width=150,
        )
        swap_button.pack(side=tk.LEFT, padx=20)

    def _setup_export_panel(self):
        """Setup export operation panel"""
        desc_label = ctk.CTkLabel(
            self.ops_scrollable,
            text=t("Save character to a standalone .erc file for backup or sharing"),
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        )
        desc_label.pack(anchor=tk.W, pady=10)

        controls = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)

        slot_label = ctk.CTkLabel(controls, text=t("Slot:"))
        slot_label.pack(side=tk.LEFT, padx=5)

        self.export_slot_var = tk.IntVar(value=1)
        slot_names = self._get_slot_display_names()
        slot_combo = ctk.CTkComboBox(
            controls,
            values=slot_names,
            state="readonly",
            width=200,
            command=lambda v: self.export_slot_var.set(int(v.split(" - ")[0])),
        )
        slot_combo.set(slot_names[0])
        slot_combo.pack(side=tk.LEFT, padx=5)

        export_button = ctk.CTkButton(
            controls,
            text=t("Export Character..."),
            command=self.export_character,
            width=180,
        )
        export_button.pack(side=tk.LEFT, padx=20)

    def _setup_import_panel(self):
        """Setup import operation panel"""
        desc_label = ctk.CTkLabel(
            self.ops_scrollable,
            text=t("Load a character from a .erc file into a slot"),
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        )
        desc_label.pack(anchor=tk.W, pady=10)

        controls = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)

        slot_label = ctk.CTkLabel(controls, text=t("To Slot:"))
        slot_label.pack(side=tk.LEFT, padx=5)

        self.import_slot_var = tk.IntVar(value=1)
        slot_names = self._get_slot_display_names()
        slot_combo = ctk.CTkComboBox(
            controls,
            values=slot_names,
            state="readonly",
            width=200,
            command=lambda v: self.import_slot_var.set(int(v.split(" - ")[0])),
        )
        slot_combo.set(slot_names[0])
        slot_combo.pack(side=tk.LEFT, padx=5)

        import_button = ctk.CTkButton(
            controls,
            text=t("Import Character..."),
            command=self.import_character,
            width=180,
        )
        import_button.pack(side=tk.LEFT, padx=20)

    def _setup_delete_panel(self):
        """Setup delete operation panel"""
        desc_label = ctk.CTkLabel(
            self.ops_scrollable,
            text=t("Clear a character slot (creates backup)"),
            font=("Segoe UI", 11),
            text_color=("red", "red"),
        )
        desc_label.pack(anchor=tk.W, pady=10)

        controls = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)

        slot_label = ctk.CTkLabel(controls, text=t("Slot:"))
        slot_label.pack(side=tk.LEFT, padx=5)

        self.delete_slot_var = tk.IntVar(value=1)
        slot_names = self._get_slot_display_names()
        slot_combo = ctk.CTkComboBox(
            controls,
            values=slot_names,
            state="readonly",
            width=200,
            command=lambda v: self.delete_slot_var.set(int(v.split(" - ")[0])),
        )
        slot_combo.set(slot_names[0])
        slot_combo.pack(side=tk.LEFT, padx=5)

        delete_button = ctk.CTkButton(
            controls,
            text=t("Delete Character"),
            command=self.delete_character,
            width=150,
            fg_color=("red", "darkred"),
            hover_color=("darkred", "red"),
        )
        delete_button.pack(side=tk.LEFT, padx=20)

    # ========== Operations ==========

    def copy_character(self):
        """Copy character from one slot to another"""
        # Check if game is running
        if self.is_game_running and self.is_game_running():
            CTkMessageBox.showerror(
                t("Elden Ring is Running!"),
                t("Please close Elden Ring before modifying save files."),
                parent=self.parent,
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                t("No Save"), t("Please load a save file first!"), parent=self.parent
            )
            return

        from_slot = int(self.copy_from_var.get()) - 1
        to_slot = int(self.copy_to_var.get()) - 1

        if from_slot == to_slot:
            CTkMessageBox.showerror(
                t("Error"),
                t("Source and destination slots must be different!"),
                parent=self.parent,
            )
            return

        from_char = save_file.characters[from_slot]
        to_char = save_file.characters[to_slot]

        if from_char.is_empty():
            CTkMessageBox.showerror(
                t("Error"),
                t("Slot {from_slot} is empty!").format(from_slot=from_slot + 1),
                parent=self.parent,
            )
            return

        from_name = from_char.get_character_name()

        # Check if destination slot has an ACTIVE character (not just data)
        to_is_active = False
        if (
            save_file.user_data_10_parsed
            and save_file.user_data_10_parsed.profile_summary
        ):
            active_flags = save_file.user_data_10_parsed.profile_summary.active_profiles
            if to_slot < len(active_flags):
                to_is_active = active_flags[to_slot]

        # Only prompt for overwrite if the slot is actually active AND not empty
        if not to_char.is_empty() and to_is_active:
            to_name = to_char.get_character_name()
            response = CTkMessageBox.askyesno(
                t("Overwrite?"),
                t(
                    "Slot {to_slot} contains '{to_name}'.\n\nOverwrite with '{from_name}'?"
                ).format(to_slot=to_slot + 1, to_name=to_name, from_name=from_name),
                parent=self.parent,
            )
            if not response:
                return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.transfer.character_ops import CharacterOperations

            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_copy_{from_name}_slot{from_slot + 1}_to_slot{to_slot + 1}",
                    operation="copy_character",
                    save=save_file,
                )

            # (debug logging removed)

            # Copy character data
            CharacterOperations.copy_slot(save_file, from_slot, to_slot)

            # Recalculate checksums
            save_file.recalculate_checksums()

            # Save to file
            save_path = self.get_save_path()
            if save_path:
                save_file.to_file(Path(save_path))

            # Reload
            if self.reload_save:
                self.reload_save()

            # Delay message to ensure it appears on top after reload
            (
                self.show_toast(
                    t("Character '{from_name}' copied to Slot {to_slot}!").format(
                        from_name=from_name, to_slot=to_slot + 1
                    ),
                    duration=2500,
                ),
            )

        except Exception as e:
            CTkMessageBox.showerror(
                t("Error"),
                t("Copy failed:\n{str}").format(str=str(e)),
                parent=self.parent,
            )
            import traceback

            traceback.print_exc()

    def transfer_character(self):
        """Transfer character to another save file"""
        # Check if game is running
        if self.is_game_running and self.is_game_running():
            CTkMessageBox.showerror(
                t("Elden Ring is Running!"),
                t("Please close Elden Ring before modifying save files."),
                parent=self.parent,
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                t("No Save"), t("Please load a save file first!"), parent=self.parent
            )
            return

        from_slot = int(self.transfer_from_var.get()) - 1
        from_char = save_file.characters[from_slot]

        if from_char.is_empty():
            CTkMessageBox.showerror(
                t("Error"),
                t("Slot {from_slot} is empty!").format(from_slot=from_slot + 1),
                parent=self.parent,
            )
            return

        target_path = self._select_target_save_file()

        if not target_path:
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.parser import Save
            from er_save_manager.transfer.character_ops import CharacterOperations

            # Load target save
            target_save = Save.from_file(target_path)

            to_slot = self._select_target_slot(target_save, target_path)
            if to_slot is None:
                return

            source_path = self._get_current_save_path()
            if source_path and Path(target_path).resolve() == source_path.resolve():
                CTkMessageBox.showerror(
                    t("Error"),
                    t("Select a different target save file for transfer."),
                    parent=self.parent,
                )
                return

            # Create backups
            if source_path:
                manager = BackupManager(source_path)
                manager.create_backup(
                    description=f"before_transfer_slot_{from_slot + 1}_to_other_save",
                    operation="transfer_character",
                    save=save_file,
                )

            target_manager = BackupManager(Path(target_path))
            target_manager.create_backup(
                description=f"before_receive_character_to_slot_{to_slot + 1}",
                operation="receive_character",
                save=target_save,
            )

            # Transfer
            CharacterOperations.transfer_slot(
                save_file, from_slot, target_save, to_slot
            )

            # Save both files
            save_file.recalculate_checksums()
            target_save.recalculate_checksums()

            if source_path:
                save_file.to_file(source_path)
            target_save.to_file(Path(target_path))

            # Reload
            if self.reload_save:
                self.reload_save()

            # Delay message to ensure it appears on top after reload
            self.show_toast(
                t("Character transferred to target Slot {to_slot}!").format(
                    to_slot=to_slot + 1
                ),
                duration=2500,
            )

        except Exception as e:
            CTkMessageBox.showerror(
                t("Error"),
                t("Transfer failed:\n{str}").format(str=str(e)),
                parent=self.parent,
            )
            import traceback

            traceback.print_exc()

    def _get_current_save_path(self) -> Path | None:
        """Return the current save path as a Path object when available."""
        save_path = self.get_save_path()
        if not save_path:
            return None
        return Path(save_path)

    def _browse_target_save_manually(self) -> str | None:
        """Open a manual file picker for the target save file."""
        save_path = self._get_current_save_path()
        initialdir = str(save_path.parent) if save_path else None
        return pick_file(
            title=t("Select target save file"),
            initialdir=initialdir,
            filetypes=[("Save files", "*.sl2 *.co2 *.cnv"), ("All files", "*.*")],
        )

    def _select_target_save_file(self) -> str | None:
        """Show a picker for the target save file with auto-detected saves."""
        found_saves = PlatformUtils.find_all_save_files()
        current_save_path = self._get_current_save_path()
        if current_save_path:
            found_saves = [
                save_path
                for save_path in found_saves
                if save_path.resolve() != current_save_path.resolve()
            ]

        if found_saves:
            selected_path = SaveSelectorDialog.show(
                self.parent,
                found_saves,
                lambda path: None,
                browse_callback=self._browse_target_save_manually,
                browse_button_text="Browse Manually",
            )
        else:
            selected_path = self._browse_target_save_manually()

        return selected_path

    def _select_target_slot(self, target_save, target_path: str) -> int | None:
        """Show a target-slot picker using the parsed target save data."""
        from er_save_manager.ui.utils import force_render_dialog

        slot_dialog = ctk.CTkToplevel(self.parent)
        slot_dialog.title("Select Target Slot")
        slot_dialog.geometry("520x220")

        # Force rendering on Linux before grab_set
        force_render_dialog(slot_dialog)
        slot_dialog.grab_set()

        dialog_label = ctk.CTkLabel(
            slot_dialog,
            text=t("Select destination slot in target save:"),
            font=("Segoe UI", 12),
        )
        dialog_label.pack(padx=10, pady=(12, 6))

        target_label = ctk.CTkLabel(
            slot_dialog,
            text=str(target_path),
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
            wraplength=480,
        )
        target_label.pack(padx=10, pady=(0, 10))

        slot_names = self._get_slot_display_names(target_save)
        to_slot_var = tk.StringVar(value=slot_names[0] if slot_names else "1")
        slot_combo = ctk.CTkComboBox(
            slot_dialog,
            variable=to_slot_var,
            values=slot_names,
            state="readonly",
            width=360,
        )
        slot_combo.pack(pady=(0, 12))

        result = {"value": None}

        def confirm():
            try:
                result["value"] = int(to_slot_var.get().split(" - ")[0]) - 1
            except Exception:
                result["value"] = 0
            slot_dialog.destroy()

        confirm_button = ctk.CTkButton(
            slot_dialog,
            text=t("Transfer"),
            command=confirm,
            width=140,
        )
        confirm_button.pack(pady=(0, 12))

        slot_dialog.bind("<Return>", lambda _event: confirm())
        slot_dialog.bind("<Escape>", lambda _event: slot_dialog.destroy())

        slot_dialog.wait_window()
        return result["value"]

    def swap_characters(self):
        """Swap two character slots"""
        # Check if game is running
        if self.is_game_running and self.is_game_running():
            CTkMessageBox.showerror(
                t("Elden Ring is Running!"),
                t("Please close Elden Ring before modifying save files."),
                parent=self.parent,
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                t("No Save"), t("Please load a save file first!"), parent=self.parent
            )
            return

        slot_a = int(self.swap_a_var.get()) - 1
        slot_b = int(self.swap_b_var.get()) - 1

        if slot_a == slot_b:
            CTkMessageBox.showerror(
                t("Error"), t("Slots must be different!"), parent=self.parent
            )
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.transfer.character_ops import CharacterOperations

            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_swap_slots_{slot_a + 1}_and_{slot_b + 1}",
                    operation="swap_characters",
                    save=save_file,
                )

            # Swap
            CharacterOperations.swap_slots(save_file, slot_a, slot_b)

            # Save
            save_file.recalculate_checksums()
            if save_path:
                save_file.to_file(Path(save_path))

            # Reload
            if self.reload_save:
                self.reload_save()

            # Delay message to ensure it appears on top after reload
            self.show_toast(
                t("Swapped Slot {slot_a} and Slot {slot_b}!").format(
                    slot_a=slot_a + 1, slot_b=slot_b + 1
                ),
                duration=2500,
            )

        except Exception as e:
            CTkMessageBox.showerror(
                t("Error"),
                t("Swap failed:\n{str}").format(str=str(e)),
                parent=self.parent,
            )
            import traceback

            traceback.print_exc()

    def export_character(self):
        """Export character to .erc file"""
        # Check if game is running
        if self.is_game_running and self.is_game_running():
            CTkMessageBox.showerror(
                t("Elden Ring is Running!"),
                t("Please close Elden Ring before modifying save files."),
                parent=self.parent,
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                t("No Save"), t("Please load a save file first!"), parent=self.parent
            )
            return

        slot = int(self.export_slot_var.get()) - 1
        char = save_file.characters[slot]

        if char.is_empty():
            CTkMessageBox.showerror(
                t("Error"),
                t("Slot {slot} is empty!").format(slot=slot + 1),
                parent=self.parent,
            )
            return

        # Get character name for default filename
        char_name = char.get_character_name() or f"Character_{slot + 1}"
        default_name = f"{char_name}.erc"

        output_path = pick_file(
            title=t("Export Character"),
            save=True,
            defaultextension=".erc",
            initialfile=default_name,
            filetypes=[("ER Character", "*.erc"), ("All files", "*.*")],
        )

        if not output_path:
            return

        try:
            from er_save_manager.transfer.character_ops import CharacterOperations

            CharacterOperations.export_character(save_file, slot, Path(output_path))

            CTkMessageBox.showinfo(
                t("Success"),
                t("Character '{char_name}' exported to:\n{output_path}").format(
                    char_name=char_name, output_path=output_path
                ),
                parent=self.parent,
            )

        except Exception as e:
            CTkMessageBox.showerror(
                t("Error"),
                t("Export failed:\n{str}").format(str=str(e)),
                parent=self.parent,
            )
            import traceback

            traceback.print_exc()

    def import_character(self):
        """Import character from .erc file"""
        # Check if game is running
        if self.is_game_running and self.is_game_running():
            CTkMessageBox.showerror(
                t("Elden Ring is Running!"),
                t("Please close Elden Ring before modifying save files."),
                parent=self.parent,
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                t("No Save"), t("Please load a save file first!"), parent=self.parent
            )
            return

        import_path = pick_file(
            title=t("Import Character"),
            filetypes=[("ER Character", "*.erc"), ("All files", "*.*")],
        )

        if not import_path:
            return

        to_slot = int(self.import_slot_var.get()) - 1
        to_char = save_file.characters[to_slot]

        # Check if destination slot has an ACTIVE character (not just data)
        to_is_active = False
        if (
            save_file.user_data_10_parsed
            and save_file.user_data_10_parsed.profile_summary
        ):
            active_flags = save_file.user_data_10_parsed.profile_summary.active_profiles
            if to_slot < len(active_flags):
                to_is_active = active_flags[to_slot]

        # Only prompt for overwrite if the slot is actually active AND not empty
        if not to_char.is_empty() and to_is_active:
            to_name = to_char.get_character_name()
            response = CTkMessageBox.askyesno(
                t("Overwrite?"),
                t("Slot {to_slot} contains '{to_name}'.\n\nOverwrite?").format(
                    to_slot=to_slot + 1, to_name=to_name
                ),
                parent=self.parent,
            )
            if not response:
                return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.transfer.character_ops import CharacterOperations

            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_import_to_slot_{to_slot + 1}",
                    operation="import_character",
                    save=save_file,
                )

            # Import
            CharacterOperations.import_character(save_file, to_slot, Path(import_path))

            # Save
            save_file.recalculate_checksums()
            if save_path:
                save_file.to_file(Path(save_path))

            # Reload
            if self.reload_save:
                self.reload_save()

            # Delay message to ensure it appears on top after reload
            self.show_toast(
                t("Character imported to Slot {to_slot}!").format(to_slot=to_slot + 1),
                duration=2500,
            )

        except Exception as e:
            CTkMessageBox.showerror(
                t("Error"),
                t("Import failed:\n{str}").format(str=str(e)),
                parent=self.parent,
            )
            import traceback

            traceback.print_exc()

    def open_character_browser(self):
        """Open the character browser dialog."""
        from er_save_manager.ui.dialogs.character_browser import CharacterBrowser

        save = self.get_save_file()
        if not save:
            CTkMessageBox.showwarning(
                t("No Save File"),
                t("Please load a save file first"),
                parent=self.parent,
            )
            return

        browser = CharacterBrowser(self.parent, character_tab=self, save_file=save)
        browser.show()

    def delete_character(self):
        """Delete character from slot"""
        # Check if game is running
        if self.is_game_running and self.is_game_running():
            CTkMessageBox.showerror(
                t("Elden Ring is Running!"),
                t("Please close Elden Ring before modifying save files."),
                parent=self.parent,
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                t("No Save"), t("Please load a save file first!"), parent=self.parent
            )
            return

        slot = int(self.delete_slot_var.get()) - 1
        char = save_file.characters[slot]

        if char.is_empty():
            CTkMessageBox.showinfo(
                t("Info"),
                t("Slot {slot} is already empty.").format(slot=slot + 1),
                parent=self.parent,
            )
            return

        char_name = char.get_character_name()

        response = CTkMessageBox.askyesno(
            t("Confirm Delete"),
            t(
                "Delete character '{char_name}' from Slot {slot}?\n\nThis will create a backup first."
            ).format(char_name=char_name, slot=slot + 1),
            parent=self.parent,
        )
        if not response:
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.transfer.character_ops import CharacterOperations

            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_delete_{char_name}_slot_{slot + 1}",
                    operation="delete_character",
                    save=save_file,
                )

            # Delete
            CharacterOperations.delete_slot(save_file, slot)

            # Save
            save_file.recalculate_checksums()
            if save_path:
                save_file.to_file(Path(save_path))

            # Reload
            if self.reload_save:
                self.reload_save()

            # Delay message to ensure it appears on top after reload
            self.show_toast(
                t("Character deleted from Slot {slot}").format(slot=slot + 1),
                duration=2500,
            )

        except Exception as e:
            CTkMessageBox.showerror(
                t("Error"),
                t("Delete failed:\n{str}").format(str=str(e)),
                parent=self.parent,
            )
            import traceback

            traceback.print_exc()
