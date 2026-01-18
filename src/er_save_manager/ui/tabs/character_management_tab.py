"""
Character Management Tab
Handles copy, transfer, swap, export, import, and delete operations
"""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


class CharacterManagementTab:
    """Tab for character management operations"""
    
    def __init__(self, parent, get_save_file_callback, get_save_path_callback, reload_callback):
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
        ttk.Label(
            self.parent,
            text="Character Management",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=10)
        
        info_text = ttk.Label(
            self.parent,
            text="Transfer characters between save files, copy slots, and manage your character roster",
            font=("Segoe UI", 10),
            foreground="gray",
        )
        info_text.pack(pady=5)
        
        # Operation selector
        selector_frame = ttk.LabelFrame(
            self.parent, text="Select Operation", padding=15
        )
        selector_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.char_operation_var = tk.StringVar(value="copy")
        
        operations = [
            ("Copy Character", "copy"),
            ("Transfer to Another Save", "transfer"),
            ("Swap Slots", "swap"),
            ("Export Character", "export"),
            ("Import Character", "import"),
            ("Delete Character", "delete"),
        ]
        
        # Dropdown selector
        ttk.Label(selector_frame, text="Operation:").pack(side=tk.LEFT, padx=(0, 10))
        operation_combo = ttk.Combobox(
            selector_frame,
            textvariable=self.char_operation_var,
            values=[op[0] for op in operations],
            state="readonly",
            width=30,
        )
        operation_combo.pack(side=tk.LEFT, padx=5)
        
        # Map display names to internal values
        self.operation_map = {op[0]: op[1] for op in operations}
        self.operation_map_reverse = {op[1]: op[0] for op in operations}
        
        # Set initial display value
        operation_combo.set("Copy Character")
        
        # Bind change event
        operation_combo.bind("<<ComboboxSelected>>", lambda e: self.update_operation_panel())
        
        # Operation panel frame
        self.char_ops_panel = ttk.LabelFrame(
            self.parent, text="Operation Details", padding=15
        )
        self.char_ops_panel.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Initialize with copy operation
        self.update_operation_panel()
    
    def update_operation_panel(self):
        """Update the operation panel based on selected operation"""
        # Clear existing widgets
        for widget in self.char_ops_panel.winfo_children():
            widget.destroy()
        
        # Get internal operation value from display name
        display_name = self.char_operation_var.get()
        operation = self.operation_map.get(display_name, "copy")
        
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
    
    def _setup_copy_panel(self):
        """Setup copy operation panel"""
        ttk.Label(
            self.char_ops_panel,
            text="Copy a character from one slot to another in the same save file",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=10)
        
        controls = ttk.Frame(self.char_ops_panel)
        controls.pack(fill=tk.X, pady=10)
        
        ttk.Label(controls, text="From Slot:").pack(side=tk.LEFT, padx=5)
        self.copy_from_var = tk.IntVar(value=1)
        ttk.Combobox(
            controls,
            textvariable=self.copy_from_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(controls, text="To Slot:").pack(side=tk.LEFT, padx=15)
        self.copy_to_var = tk.IntVar(value=2)
        ttk.Combobox(
            controls,
            textvariable=self.copy_to_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            controls,
            text="Copy Character",
            command=self.copy_character,
            width=20,
        ).pack(side=tk.LEFT, padx=20)
    
    def _setup_transfer_panel(self):
        """Setup transfer operation panel"""
        ttk.Label(
            self.char_ops_panel,
            text="Transfer a character to a different save file",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=10)
        
        controls = ttk.Frame(self.char_ops_panel)
        controls.pack(fill=tk.X, pady=10)
        
        ttk.Label(controls, text="From Slot:").pack(side=tk.LEFT, padx=5)
        self.transfer_from_var = tk.IntVar(value=1)
        ttk.Combobox(
            controls,
            textvariable=self.transfer_from_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            controls,
            text="Select Target Save...",
            command=self.transfer_character,
            width=25,
        ).pack(side=tk.LEFT, padx=20)
    
    def _setup_swap_panel(self):
        """Setup swap operation panel"""
        ttk.Label(
            self.char_ops_panel,
            text="Exchange two character slots",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=10)
        
        controls = ttk.Frame(self.char_ops_panel)
        controls.pack(fill=tk.X, pady=10)
        
        ttk.Label(controls, text="Slot A:").pack(side=tk.LEFT, padx=5)
        self.swap_a_var = tk.IntVar(value=1)
        ttk.Combobox(
            controls,
            textvariable=self.swap_a_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(controls, text="Slot B:").pack(side=tk.LEFT, padx=15)
        self.swap_b_var = tk.IntVar(value=2)
        ttk.Combobox(
            controls,
            textvariable=self.swap_b_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            controls,
            text="Swap Slots",
            command=self.swap_characters,
            width=20,
        ).pack(side=tk.LEFT, padx=20)
    
    def _setup_export_panel(self):
        """Setup export operation panel"""
        ttk.Label(
            self.char_ops_panel,
            text="Save character to a standalone .erc file for backup or sharing",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=10)
        
        controls = ttk.Frame(self.char_ops_panel)
        controls.pack(fill=tk.X, pady=10)
        
        ttk.Label(controls, text="Slot:").pack(side=tk.LEFT, padx=5)
        self.export_slot_var = tk.IntVar(value=1)
        ttk.Combobox(
            controls,
            textvariable=self.export_slot_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            controls,
            text="Export Character...",
            command=self.export_character,
            width=25,
        ).pack(side=tk.LEFT, padx=20)
    
    def _setup_import_panel(self):
        """Setup import operation panel"""
        ttk.Label(
            self.char_ops_panel,
            text="Load a character from a .erc file into a slot",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=10)
        
        controls = ttk.Frame(self.char_ops_panel)
        controls.pack(fill=tk.X, pady=10)
        
        ttk.Label(controls, text="To Slot:").pack(side=tk.LEFT, padx=5)
        self.import_slot_var = tk.IntVar(value=1)
        ttk.Combobox(
            controls,
            textvariable=self.import_slot_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            controls,
            text="Import Character...",
            command=self.import_character,
            width=25,
        ).pack(side=tk.LEFT, padx=20)
    
    def _setup_delete_panel(self):
        """Setup delete operation panel"""
        ttk.Label(
            self.char_ops_panel,
            text="Clear a character slot (creates backup)",
            font=("Segoe UI", 10),
            foreground="red",
        ).pack(anchor=tk.W, pady=10)
        
        controls = ttk.Frame(self.char_ops_panel)
        controls.pack(fill=tk.X, pady=10)
        
        ttk.Label(controls, text="Slot:").pack(side=tk.LEFT, padx=5)
        self.delete_slot_var = tk.IntVar(value=1)
        ttk.Combobox(
            controls,
            textvariable=self.delete_slot_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            controls,
            text="Delete Character",
            command=self.delete_character,
            width=20,
        ).pack(side=tk.LEFT, padx=20)
    
    # ========== Operations ==========
    
    def copy_character(self):
        """Copy character from one slot to another"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        from_slot = self.copy_from_var.get() - 1
        to_slot = self.copy_to_var.get() - 1
        
        if from_slot == to_slot:
            messagebox.showerror("Error", "Source and destination slots must be different!")
            return
        
        from_char = save_file.characters[from_slot]
        to_char = save_file.characters[to_slot]
        
        if from_char.is_empty():
            messagebox.showerror("Error", f"Slot {from_slot + 1} is empty!")
            return
        
        from_name = from_char.get_character_name()
        
        if not to_char.is_empty():
            to_name = to_char.get_character_name()
            if not messagebox.askyesno(
                "Overwrite?",
                f"Slot {to_slot + 1} contains '{to_name}'.\n\nOverwrite with '{from_name}'?",
            ):
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
            
            messagebox.showinfo(
                "Success",
                f"Character '{from_name}' copied from Slot {from_slot + 1} to Slot {to_slot + 1}!\n\n"
                f"Backup created in backup manager.",
            )
        
        except Exception as e:
            messagebox.showerror("Error", f"Copy failed:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def transfer_character(self):
        """Transfer character to another save file"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        from_slot = self.transfer_from_var.get() - 1
        from_char = save_file.characters[from_slot]
        
        if from_char.is_empty():
            messagebox.showerror("Error", f"Slot {from_slot + 1} is empty!")
            return
        
        # Select target save file
        target_path = filedialog.askopenfilename(
            title="Select target save file",
            filetypes=[("Save files", "*.sl2 *.co2"), ("All files", "*.*")]
        )
        
        if not target_path:
            return
        
        try:
            from er_save_manager.parser import Save
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.transfer.character_ops import CharacterOperations
            
            # Load target save
            target_save = Save(target_path)
            
            # Ask which slot in target
            slot_dialog = tk.Toplevel(self.parent)
            slot_dialog.title("Select Target Slot")
            slot_dialog.geometry("300x150")
            slot_dialog.grab_set()
            
            ttk.Label(
                slot_dialog,
                text="Select destination slot in target save:",
                padding=10
            ).pack()
            
            to_slot_var = tk.IntVar(value=1)
            ttk.Combobox(
                slot_dialog,
                textvariable=to_slot_var,
                values=list(range(1, 11)),
                state="readonly",
                width=10
            ).pack(pady=10)
            
            result = [None]
            
            def confirm():
                result[0] = to_slot_var.get() - 1
                slot_dialog.destroy()
            
            ttk.Button(slot_dialog, text="Transfer", command=confirm).pack(pady=10)
            
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
            CharacterOperations.transfer_slot(save_file, from_slot, target_save, to_slot)
            
            # Save both files
            save_file.recalculate_checksums()
            target_save.recalculate_checksums()
            
            if save_path:
                save_file.to_file(Path(save_path))
            target_save.to_file(Path(target_path))
            
            # Reload
            if self.reload_save:
                self.reload_save()
            
            messagebox.showinfo(
                "Success",
                f"Character transferred from Slot {from_slot + 1} to target save Slot {to_slot + 1}!\n\n"
                f"Both saves backed up.",
            )
        
        except Exception as e:
            messagebox.showerror("Error", f"Transfer failed:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def swap_characters(self):
        """Swap two character slots"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        slot_a = self.swap_a_var.get() - 1
        slot_b = self.swap_b_var.get() - 1
        
        if slot_a == slot_b:
            messagebox.showerror("Error", "Slots must be different!")
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
            
            messagebox.showinfo(
                "Success",
                f"Swapped Slot {slot_a + 1} and Slot {slot_b + 1}!",
            )
        
        except Exception as e:
            messagebox.showerror("Error", f"Swap failed:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def export_character(self):
        """Export character to .erc file"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        slot = self.export_slot_var.get() - 1
        char = save_file.characters[slot]
        
        if char.is_empty():
            messagebox.showerror("Error", f"Slot {slot + 1} is empty!")
            return
        
        # Get character name for default filename
        char_name = char.get_character_name() or f"Character_{slot + 1}"
        default_name = f"{char_name}.erc"
        
        output_path = filedialog.asksaveasfilename(
            title="Export Character",
            defaultextension=".erc",
            initialfile=default_name,
            filetypes=[("ER Character", "*.erc"), ("All files", "*.*")]
        )
        
        if not output_path:
            return
        
        try:
            from er_save_manager.transfer.character_ops import CharacterOperations
            
            CharacterOperations.export_character(save_file, slot, Path(output_path))
            
            messagebox.showinfo(
                "Success",
                f"Character '{char_name}' exported to:\n{output_path}",
            )
        
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def import_character(self):
        """Import character from .erc file"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        import_path = filedialog.askopenfilename(
            title="Import Character",
            filetypes=[("ER Character", "*.erc"), ("All files", "*.*")]
        )
        
        if not import_path:
            return
        
        to_slot = self.import_slot_var.get() - 1
        to_char = save_file.characters[to_slot]
        
        if not to_char.is_empty():
            to_name = to_char.get_character_name()
            if not messagebox.askyesno(
                "Overwrite?",
                f"Slot {to_slot + 1} contains '{to_name}'.\n\nOverwrite?",
            ):
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
            
            messagebox.showinfo(
                "Success",
                f"Character imported to Slot {to_slot + 1}!",
            )
        
        except Exception as e:
            messagebox.showerror("Error", f"Import failed:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def delete_character(self):
        """Delete character from slot"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        slot = self.delete_slot_var.get() - 1
        char = save_file.characters[slot]
        
        if char.is_empty():
            messagebox.showinfo("Info", f"Slot {slot + 1} is already empty.")
            return
        
        char_name = char.get_character_name()
        
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete character '{char_name}' from Slot {slot + 1}?\n\n"
            f"This will create a backup first.",
        ):
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
            
            messagebox.showinfo(
                "Success",
                f"Character '{char_name}' deleted from Slot {slot + 1}.\n\nBackup created.",
            )
        
        except Exception as e:
            messagebox.showerror("Error", f"Delete failed:\n{str(e)}")
            import traceback
            traceback.print_exc()
