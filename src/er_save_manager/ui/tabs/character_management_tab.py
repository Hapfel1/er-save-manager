"""
Character Management Tab (CustomTkinter)
Handles copy, transfer, swap, export, import, and delete operations
"""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


class CharacterManagementTab:
    """Tab for character management operations"""

    def __init__(
        self, parent, get_save_file_callback, get_save_path_callback, reload_callback
    ):
        """
        Initialize character management tab

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_save_path_callback: Function that returns save file path
            reload_callback: Function to reload save file after operations
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback

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
        # Title
        title_label = ctk.CTkLabel(
            self.parent,
            text="Character Management",
            font=("Segoe UI", 16, "bold"),
        )
        title_label.pack(pady=10)

        # Info label
        info_text = ctk.CTkLabel(
            self.parent,
            text="Transfer characters between save files, copy slots, and manage your character roster",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        )
        info_text.pack(pady=5)

        # Operation selector frame
        selector_frame = ctk.CTkFrame(
            self.parent,
            corner_radius=10,
        )
        selector_frame.pack(fill=tk.X, padx=20, pady=10)

        # Add label to selector frame
        selector_label = ctk.CTkLabel(
            selector_frame,
            text="Select Operation",
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
        op_label = ctk.CTkLabel(selector_controls, text="Operation:")
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
            self.parent,
            corner_radius=10,
        )
        self.char_ops_panel.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Add label to operation panel
        panel_label = ctk.CTkLabel(
            self.char_ops_panel,
            text="Operation Details",
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

        # Force layout update to avoid rendering delays
        self.ops_scrollable.update_idletasks()

    def _setup_copy_panel(self):
        """Setup copy operation panel"""
        desc_label = ctk.CTkLabel(
            self.ops_scrollable,
            text="Copy a character from one slot to another in the same save file",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        )
        desc_label.pack(anchor=tk.W, pady=10)

        controls = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)

        from_label = ctk.CTkLabel(controls, text="From Slot:")
        from_label.pack(side=tk.LEFT, padx=5)

        self.copy_from_var = tk.IntVar(value=1)
        from_combo = ctk.CTkComboBox(
            controls,
            variable=self.copy_from_var,
            values=[str(i) for i in range(1, 11)],
            state="readonly",
            width=80,
        )
        from_combo.pack(side=tk.LEFT, padx=5)

        to_label = ctk.CTkLabel(controls, text="To Slot:")
        to_label.pack(side=tk.LEFT, padx=15)

        self.copy_to_var = tk.IntVar(value=2)
        to_combo = ctk.CTkComboBox(
            controls,
            variable=self.copy_to_var,
            values=[str(i) for i in range(1, 11)],
            state="readonly",
            width=80,
        )
        to_combo.pack(side=tk.LEFT, padx=5)

        copy_button = ctk.CTkButton(
            controls,
            text="Copy Character",
            command=self.copy_character,
            width=150,
        )
        copy_button.pack(side=tk.LEFT, padx=20)

    def _setup_transfer_panel(self):
        """Setup transfer operation panel"""
        desc_label = ctk.CTkLabel(
            self.ops_scrollable,
            text="Transfer a character to a different save file",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        )
        desc_label.pack(anchor=tk.W, pady=10)

        controls = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)

        from_label = ctk.CTkLabel(controls, text="From Slot:")
        from_label.pack(side=tk.LEFT, padx=5)

        self.transfer_from_var = tk.IntVar(value=1)
        from_combo = ctk.CTkComboBox(
            controls,
            variable=self.transfer_from_var,
            values=[str(i) for i in range(1, 11)],
            state="readonly",
            width=80,
        )
        from_combo.pack(side=tk.LEFT, padx=5)

        transfer_button = ctk.CTkButton(
            controls,
            text="Select Target Save...",
            command=self.transfer_character,
            width=180,
        )
        transfer_button.pack(side=tk.LEFT, padx=20)

    def _setup_swap_panel(self):
        """Setup swap operation panel"""
        desc_label = ctk.CTkLabel(
            self.ops_scrollable,
            text="Exchange two character slots",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        )
        desc_label.pack(anchor=tk.W, pady=10)

        controls = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)

        slot_a_label = ctk.CTkLabel(controls, text="Slot A:")
        slot_a_label.pack(side=tk.LEFT, padx=5)

        self.swap_a_var = tk.IntVar(value=1)
        slot_a_combo = ctk.CTkComboBox(
            controls,
            variable=self.swap_a_var,
            values=[str(i) for i in range(1, 11)],
            state="readonly",
            width=80,
        )
        slot_a_combo.pack(side=tk.LEFT, padx=5)

        slot_b_label = ctk.CTkLabel(controls, text="Slot B:")
        slot_b_label.pack(side=tk.LEFT, padx=15)

        self.swap_b_var = tk.IntVar(value=2)
        slot_b_combo = ctk.CTkComboBox(
            controls,
            variable=self.swap_b_var,
            values=[str(i) for i in range(1, 11)],
            state="readonly",
            width=80,
        )
        slot_b_combo.pack(side=tk.LEFT, padx=5)

        swap_button = ctk.CTkButton(
            controls,
            text="Swap Slots",
            command=self.swap_characters,
            width=150,
        )
        swap_button.pack(side=tk.LEFT, padx=20)

    def _setup_export_panel(self):
        """Setup export operation panel"""
        desc_label = ctk.CTkLabel(
            self.ops_scrollable,
            text="Save character to a standalone .erc file for backup or sharing",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        )
        desc_label.pack(anchor=tk.W, pady=10)

        controls = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)

        slot_label = ctk.CTkLabel(controls, text="Slot:")
        slot_label.pack(side=tk.LEFT, padx=5)

        self.export_slot_var = tk.IntVar(value=1)
        slot_combo = ctk.CTkComboBox(
            controls,
            variable=self.export_slot_var,
            values=[str(i) for i in range(1, 11)],
            state="readonly",
            width=80,
        )
        slot_combo.pack(side=tk.LEFT, padx=5)

        export_button = ctk.CTkButton(
            controls,
            text="Export Character...",
            command=self.export_character,
            width=180,
        )
        export_button.pack(side=tk.LEFT, padx=20)

    def _setup_import_panel(self):
        """Setup import operation panel"""
        desc_label = ctk.CTkLabel(
            self.ops_scrollable,
            text="Load a character from a .erc file into a slot",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        )
        desc_label.pack(anchor=tk.W, pady=10)

        controls = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)

        slot_label = ctk.CTkLabel(controls, text="To Slot:")
        slot_label.pack(side=tk.LEFT, padx=5)

        self.import_slot_var = tk.IntVar(value=1)
        slot_combo = ctk.CTkComboBox(
            controls,
            variable=self.import_slot_var,
            values=[str(i) for i in range(1, 11)],
            state="readonly",
            width=80,
        )
        slot_combo.pack(side=tk.LEFT, padx=5)

        import_button = ctk.CTkButton(
            controls,
            text="Import Character...",
            command=self.import_character,
            width=180,
        )
        import_button.pack(side=tk.LEFT, padx=20)

    def _setup_delete_panel(self):
        """Setup delete operation panel"""
        desc_label = ctk.CTkLabel(
            self.ops_scrollable,
            text="Clear a character slot (creates backup)",
            font=("Segoe UI", 11),
            text_color=("red",),
        )
        desc_label.pack(anchor=tk.W, pady=10)

        controls = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)

        slot_label = ctk.CTkLabel(controls, text="Slot:")
        slot_label.pack(side=tk.LEFT, padx=5)

        self.delete_slot_var = tk.IntVar(value=1)
        slot_combo = ctk.CTkComboBox(
            controls,
            variable=self.delete_slot_var,
            values=[str(i) for i in range(1, 11)],
            state="readonly",
            width=80,
        )
        slot_combo.pack(side=tk.LEFT, padx=5)

        delete_button = ctk.CTkButton(
            controls,
            text="Delete Character",
            command=self.delete_character,
            width=150,
            fg_color=("red", "darkred"),
            hover_color=("darkred", "red"),
        )
        delete_button.pack(side=tk.LEFT, padx=20)

    # ========== Operations ==========

    def copy_character(self):
        """Copy character from one slot to another"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        from_slot = self.copy_from_var.get() - 1
        to_slot = self.copy_to_var.get() - 1

        if from_slot == to_slot:
            CTkMessageBox.showerror(
                "Error", "Source and destination slots must be different!"
            )
            return

        from_char = save_file.characters[from_slot]
        to_char = save_file.characters[to_slot]

        if from_char.is_empty():
            CTkMessageBox.showerror("Error", f"Slot {from_slot + 1} is empty!")
            return

        from_name = from_char.get_character_name()

        if not to_char.is_empty():
            to_name = to_char.get_character_name()
            response = CTkMessageBox.askyesno(
                "Overwrite?",
                f"Slot {to_slot + 1} contains '{to_name}'.\n\nOverwrite with '{from_name}'?",
            )
            if response != "Yes":
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

            CTkMessageBox.showinfo(
                "Success",
                f"Character '{from_name}' copied from Slot {from_slot + 1} to Slot {to_slot + 1}!\n\nBackup created in backup manager.",
            )

        except Exception as e:
            CTkMessageBox.showerror("Error", f"Copy failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def transfer_character(self):
        """Transfer character to another save file"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        from_slot = self.transfer_from_var.get() - 1
        from_char = save_file.characters[from_slot]

        if from_char.is_empty():
            CTkMessageBox.showerror("Error", f"Slot {from_slot + 1} is empty!")
            return

        # Select target save file
        target_path = filedialog.askopenfilename(
            title="Select target save file",
            filetypes=[("Save files", "*.sl2 *.co2"), ("All files", "*.*")],
        )

        if not target_path:
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.parser import Save
            from er_save_manager.transfer.character_ops import CharacterOperations
            from er_save_manager.ui.utils import force_render_dialog

            # Load target save
            target_save = Save(target_path)

            # Ask which slot in target
            slot_dialog = ctk.CTkToplevel(self.parent)
            slot_dialog.title("Select Target Slot")
            slot_dialog.geometry("300x150")

            # Force rendering on Linux before grab_set
            force_render_dialog(slot_dialog)
            slot_dialog.grab_set()

            dialog_label = ctk.CTkLabel(
                slot_dialog,
                text="Select destination slot in target save:",
                font=("Segoe UI", 12),
            )
            dialog_label.pack(padx=10, pady=10)

            to_slot_var = tk.IntVar(value=1)
            slot_combo = ctk.CTkComboBox(
                slot_dialog,
                variable=to_slot_var,
                values=[str(i) for i in range(1, 11)],
                state="readonly",
                width=150,
            )
            slot_combo.pack(pady=10)

            result = [None]

            def confirm():
                result[0] = to_slot_var.get() - 1
                slot_dialog.destroy()

            confirm_button = ctk.CTkButton(
                slot_dialog,
                text="Transfer",
                command=confirm,
            )
            confirm_button.pack(pady=10)

            slot_dialog.wait_window()

            if result[0] is None:
                return

            to_slot = result[0]

            # Create backups
            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
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

            if save_path:
                save_file.to_file(Path(save_path))
            target_save.to_file(Path(target_path))

            # Reload
            if self.reload_save:
                self.reload_save()

            CTkMessageBox.showinfo(
                "Success",
                f"Character transferred from Slot {from_slot + 1} to target save Slot {to_slot + 1}!\n\nBoth saves backed up.",
            )

        except Exception as e:
            CTkMessageBox.showerror("Error", f"Transfer failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def swap_characters(self):
        """Swap two character slots"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        slot_a = self.swap_a_var.get() - 1
        slot_b = self.swap_b_var.get() - 1

        if slot_a == slot_b:
            CTkMessageBox.showerror("Error", "Slots must be different!")
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

            CTkMessageBox.showinfo(
                "Success", f"Swapped Slot {slot_a + 1} and Slot {slot_b + 1}!"
            )

        except Exception as e:
            CTkMessageBox.showerror("Error", f"Swap failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def export_character(self):
        """Export character to .erc file"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        slot = self.export_slot_var.get() - 1
        char = save_file.characters[slot]

        if char.is_empty():
            CTkMessageBox.showerror("Error", f"Slot {slot + 1} is empty!")
            return

        # Get character name for default filename
        char_name = char.get_character_name() or f"Character_{slot + 1}"
        default_name = f"{char_name}.erc"

        output_path = filedialog.asksaveasfilename(
            title="Export Character",
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
                "Success", f"Character '{char_name}' exported to:\n{output_path}"
            )

        except Exception as e:
            CTkMessageBox.showerror("Error", f"Export failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def import_character(self):
        """Import character from .erc file"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        import_path = filedialog.askopenfilename(
            title="Import Character",
            filetypes=[("ER Character", "*.erc"), ("All files", "*.*")],
        )

        if not import_path:
            return

        to_slot = self.import_slot_var.get() - 1
        to_char = save_file.characters[to_slot]

        if not to_char.is_empty():
            to_name = to_char.get_character_name()
            response = CTkMessageBox.askyesno(
                "Overwrite?", f"Slot {to_slot + 1} contains '{to_name}'.\n\nOverwrite?"
            )
            if response != "Yes":
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

            CTkMessageBox.showinfo(
                "Success", f"Character imported to Slot {to_slot + 1}!"
            )

        except Exception as e:
            CTkMessageBox.showerror("Error", f"Import failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def delete_character(self):
        """Delete character from slot"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        slot = self.delete_slot_var.get() - 1
        char = save_file.characters[slot]

        if char.is_empty():
            CTkMessageBox.showinfo("Info", f"Slot {slot + 1} is already empty.")
            return

        char_name = char.get_character_name()

        response = CTkMessageBox.askyesno(
            "Confirm Delete",
            f"Delete character '{char_name}' from Slot {slot + 1}?\n\nThis will create a backup first.",
        )
        if response != "Yes":
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

            CTkMessageBox.showinfo(
                "Success",
                f"Character '{char_name}' deleted from Slot {slot + 1}.\n\nBackup created.",
            )

        except Exception as e:
            CTkMessageBox.showerror("Error", f"Delete failed:\n{str(e)}")
            import traceback

            traceback.print_exc()
