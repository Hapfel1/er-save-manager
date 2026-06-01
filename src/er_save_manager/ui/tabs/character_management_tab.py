"""
Character Management Tab (CustomTkinter)
Handles copy, transfer, swap, export, import, and delete operations
"""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox


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
        """Setup the Manage Slots screen with operation cards and an inline detail panel."""
        # Palette
        _PANEL = "#181825"
        _PANEL2 = "#313244"
        _FG = "#cdd6f4"
        _FG_ALT = "#a6adc8"
        _FAINT = "#7f849c"
        _ACCENT = "#cba6f7"
        _BORDER = "#313244"
        _RED = "#f38ba8"
        _RED_BG = "#3a1e2e"
        _RED_BDR = "#7a2e3e"
        _GOOD = "#a6e3a1"
        _GOOD_BG = "#1e3a2e"

        outer = ctk.CTkScrollableFrame(
            self.parent, fg_color="transparent", corner_radius=0
        )
        outer.pack(fill=tk.BOTH, expand=True, padx=22, pady=16)

        # Header row
        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill=tk.X, pady=(0, 16))

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side=tk.LEFT, fill=tk.Y)
        ctk.CTkLabel(
            title_col,
            text="Manage Slots",
            font=("Segoe UI", 20, "bold"),
            text_color=_FG,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_col,
            text="Pick an action - every option is visible up front, no hidden menus.",
            font=("Segoe UI", 12),
            text_color=_FG_ALT,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        ctk.CTkButton(
            header,
            text="Character Library",
            command=self.open_character_browser,
            width=150,
            height=34,
            font=("Segoe UI", 12),
            fg_color=_PANEL2,
            text_color=_FG,
            hover_color="#45475a",
        ).pack(side=tk.RIGHT, pady=(0, 0))

        # Operation cards grid (3 columns)
        OPERATIONS = [
            ("Copy", "Duplicate a slot within this save", False),
            ("Move", "Reorder characters between slots", False),
            ("Export", "Save a character to an .erc file", False),
            ("Import", "Load a character from .erc", False),
            ("Transfer", "Copy to a different save file", False),
            ("Delete", "Permanently remove a character", True),
        ]

        cards_frame = ctk.CTkFrame(outer, fg_color="transparent")
        cards_frame.pack(fill=tk.X, pady=(0, 14))
        for col in range(3):
            cards_frame.grid_columnconfigure(col, weight=1, uniform="op_col")

        self._active_op: str | None = None
        self._op_card_widgets: dict[str, ctk.CTkFrame] = {}

        def _select_op(name: str):
            # Deselect previous
            for op_name, card in self._op_card_widgets.items():
                danger = op_name == "Delete"
                card.configure(
                    fg_color=_PANEL,
                    border_color=_BORDER,
                    border_width=1,
                )
            # Select new
            self._active_op = name
            danger = name == "Delete"
            self._op_card_widgets[name].configure(
                fg_color=_RED_BG if danger else _PANEL,
                border_color=_RED_BDR if danger else _ACCENT,
                border_width=1,
            )
            _rebuild_detail()

        for i, (name, desc, danger) in enumerate(OPERATIONS):
            row = i // 3
            col = i % 3
            cards_frame.grid_rowconfigure(row, minsize=80)

            card = ctk.CTkFrame(
                cards_frame,
                fg_color=_PANEL,
                corner_radius=10,
                border_width=1,
                border_color=_BORDER,
                cursor="hand2",
            )
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            self._op_card_widgets[name] = card

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

            ctk.CTkLabel(
                inner,
                text=name,
                font=("Segoe UI", 13, "bold"),
                text_color=_RED if danger else _FG,
                anchor="w",
            ).pack(anchor="w")
            ctk.CTkLabel(
                inner,
                text=desc,
                font=("Segoe UI", 11),
                text_color=_FAINT,
                anchor="w",
            ).pack(anchor="w", pady=(3, 0))

            def cmd(n=name):
                return _select_op(n)

            card.bind("<Button-1>", lambda e, c=cmd: c())
            inner.bind("<Button-1>", lambda e, c=cmd: c())
            for child in inner.winfo_children():
                child.bind("<Button-1>", lambda e, c=cmd: c())

        # Detail panel (rebuilt when an op card is selected)
        self._detail_frame = ctk.CTkFrame(outer, fg_color=_PANEL, corner_radius=10)
        self._detail_frame.pack(fill=tk.X)
        self._detail_frame.pack_forget()

        def _rebuild_detail():
            for w in self._detail_frame.winfo_children():
                w.destroy()
            op = self._active_op
            if op is None:
                self._detail_frame.pack_forget()
                return
            self._detail_frame.pack(fill=tk.X, pady=(0, 8))
            self._build_detail_panel(
                op,
                self._detail_frame,
                _select_op,
                _PANEL2,
                _FG,
                _FG_ALT,
                _FAINT,
                _ACCENT,
                _BORDER,
                _RED,
                _RED_BG,
                _RED_BDR,
                _GOOD,
                _GOOD_BG,
            )

        # Select Copy by default
        _select_op("Copy")

    def _build_detail_panel(
        self,
        op: str,
        parent,
        _select_op,
        _PANEL2,
        _FG,
        _FG_ALT,
        _FAINT,
        _ACCENT,
        _BORDER,
        _RED,
        _RED_BG,
        _RED_BDR,
        _GOOD,
        _GOOD_BG,
    ) -> None:
        """Build the inline detail/controls panel for the selected operation."""
        slot_names = self._get_slot_display_names()

        inner = ctk.CTkFrame(parent, fg_color="transparent")
        inner.pack(fill=tk.X, padx=18, pady=16)

        if op == "Copy":
            ctk.CTkLabel(
                inner, text="From Slot:", font=("Segoe UI", 12), text_color=_FG_ALT
            ).pack(side=tk.LEFT, padx=(0, 6))
            self.copy_from_var = tk.IntVar(value=1)
            fc = ctk.CTkComboBox(
                inner,
                values=slot_names,
                state="readonly",
                width=180,
                command=lambda v: self.copy_from_var.set(int(v.split(" - ")[0])),
            )
            fc.set(slot_names[0])
            fc.pack(side=tk.LEFT, padx=(0, 14))

            ctk.CTkLabel(
                inner, text="To Slot:", font=("Segoe UI", 12), text_color=_FG_ALT
            ).pack(side=tk.LEFT, padx=(0, 6))
            self.copy_to_var = tk.IntVar(value=2)
            tc = ctk.CTkComboBox(
                inner,
                values=slot_names,
                state="readonly",
                width=180,
                command=lambda v: self.copy_to_var.set(int(v.split(" - ")[0])),
            )
            tc.set(slot_names[1] if len(slot_names) > 1 else slot_names[0])
            tc.pack(side=tk.LEFT, padx=(0, 14))
            ctk.CTkButton(
                inner,
                text="Copy character",
                command=self.copy_character,
                width=140,
                height=34,
            ).pack(side=tk.LEFT)

        elif op == "Move":
            ctk.CTkLabel(
                inner, text="Slot A:", font=("Segoe UI", 12), text_color=_FG_ALT
            ).pack(side=tk.LEFT, padx=(0, 6))
            self.swap_a_var = tk.IntVar(value=1)
            ac = ctk.CTkComboBox(
                inner,
                values=slot_names,
                state="readonly",
                width=180,
                command=lambda v: self.swap_a_var.set(int(v.split(" - ")[0])),
            )
            ac.set(slot_names[0])
            ac.pack(side=tk.LEFT, padx=(0, 14))

            ctk.CTkLabel(
                inner, text="Slot B:", font=("Segoe UI", 12), text_color=_FG_ALT
            ).pack(side=tk.LEFT, padx=(0, 6))
            self.swap_b_var = tk.IntVar(value=2)
            bc = ctk.CTkComboBox(
                inner,
                values=slot_names,
                state="readonly",
                width=180,
                command=lambda v: self.swap_b_var.set(int(v.split(" - ")[0])),
            )
            bc.set(slot_names[1] if len(slot_names) > 1 else slot_names[0])
            bc.pack(side=tk.LEFT, padx=(0, 14))
            ctk.CTkButton(
                inner,
                text="Swap slots",
                command=self.swap_characters,
                width=120,
                height=34,
            ).pack(side=tk.LEFT)

        elif op == "Export":
            ctk.CTkLabel(
                inner, text="Slot:", font=("Segoe UI", 12), text_color=_FG_ALT
            ).pack(side=tk.LEFT, padx=(0, 6))
            self.export_slot_var = tk.IntVar(value=1)
            ec = ctk.CTkComboBox(
                inner,
                values=slot_names,
                state="readonly",
                width=200,
                command=lambda v: self.export_slot_var.set(int(v.split(" - ")[0])),
            )
            ec.set(slot_names[0])
            ec.pack(side=tk.LEFT, padx=(0, 14))
            ctk.CTkButton(
                inner,
                text="Export to .erc...",
                command=self.export_character,
                width=150,
                height=34,
            ).pack(side=tk.LEFT)

        elif op == "Import":
            ctk.CTkLabel(
                inner, text="To Slot:", font=("Segoe UI", 12), text_color=_FG_ALT
            ).pack(side=tk.LEFT, padx=(0, 6))
            self.import_slot_var = tk.IntVar(value=1)
            ic = ctk.CTkComboBox(
                inner,
                values=slot_names,
                state="readonly",
                width=200,
                command=lambda v: self.import_slot_var.set(int(v.split(" - ")[0])),
            )
            ic.set(slot_names[0])
            ic.pack(side=tk.LEFT, padx=(0, 14))
            ctk.CTkButton(
                inner,
                text="Import from .erc...",
                command=self.import_character,
                width=160,
                height=34,
            ).pack(side=tk.LEFT)

        elif op == "Transfer":
            ctk.CTkLabel(
                inner, text="From Slot:", font=("Segoe UI", 12), text_color=_FG_ALT
            ).pack(side=tk.LEFT, padx=(0, 6))
            self.transfer_from_var = tk.IntVar(value=1)
            tfc = ctk.CTkComboBox(
                inner,
                values=slot_names,
                state="readonly",
                width=200,
                command=lambda v: self.transfer_from_var.set(int(v.split(" - ")[0])),
            )
            tfc.set(slot_names[0])
            tfc.pack(side=tk.LEFT, padx=(0, 14))
            ctk.CTkButton(
                inner,
                text="Select target save...",
                command=self.transfer_character,
                width=170,
                height=34,
            ).pack(side=tk.LEFT)

        elif op == "Delete":
            # Inline typed confirmation matching the mockup
            top_row = ctk.CTkFrame(inner, fg_color="transparent")
            top_row.pack(fill=tk.X, pady=(0, 12))

            title_col = ctk.CTkFrame(top_row, fg_color="transparent")
            title_col.pack(side=tk.LEFT, fill=tk.Y)
            ctk.CTkLabel(
                title_col,
                text="Delete a character",
                font=("Segoe UI", 14, "bold"),
                text_color=_FG,
                anchor="w",
            ).pack(anchor="w")

            ctk.CTkLabel(
                top_row,
                text="IRREVERSIBLE",
                font=("Segoe UI", 10, "bold"),
                text_color=_RED,
                anchor="e",
            ).pack(side=tk.RIGHT)

            # Slot selector row
            slot_row = ctk.CTkFrame(inner, fg_color="transparent")
            slot_row.pack(fill=tk.X, pady=(0, 10))

            ctk.CTkLabel(
                slot_row, text="Slot:", font=("Segoe UI", 12), text_color=_FG_ALT
            ).pack(side=tk.LEFT, padx=(0, 8))
            self.delete_slot_var = tk.IntVar(value=1)
            dc = ctk.CTkComboBox(
                slot_row,
                values=slot_names,
                state="readonly",
                width=220,
                command=lambda v: self.delete_slot_var.set(int(v.split(" - ")[0])),
            )
            dc.set(slot_names[0])
            dc.pack(side=tk.LEFT)

            # Description
            slot_display = slot_names[0] if slot_names else "Slot 1"
            desc_var = tk.StringVar(
                value=f"This permanently removes {slot_display}. To continue, type the slot number."
            )

            def _update_desc(*_):
                v = dc.get()
                desc_var.set(
                    f"This permanently removes {v}. To continue, type the slot number."
                )
                confirm_entry.delete(0, tk.END)

            dc.configure(
                command=lambda v: (
                    self.delete_slot_var.set(int(v.split(" - ")[0])),
                    _update_desc(),
                )
            )

            ctk.CTkLabel(
                inner,
                textvariable=desc_var,
                font=("Segoe UI", 12),
                text_color=_FG_ALT,
                anchor="w",
                wraplength=600,
            ).pack(anchor="w", pady=(0, 12))

            # Confirm row
            confirm_row = ctk.CTkFrame(inner, fg_color="transparent")
            confirm_row.pack(fill=tk.X)

            confirm_entry = ctk.CTkEntry(
                confirm_row,
                placeholder_text=f'type "{slot_names[0].split(" - ")[0]}"',
                width=120,
                height=34,
                fg_color=_PANEL2,
                border_color=_BORDER,
                text_color=_FG,
            )
            confirm_entry.pack(side=tk.LEFT, padx=(0, 8))

            def _do_delete():
                # Validate typed slot number matches selection
                try:
                    typed = int(confirm_entry.get().strip())
                except ValueError:
                    return
                selected_slot = int(dc.get().split(" - ")[0])
                if typed != selected_slot:
                    confirm_entry.configure(border_color=_RED)
                    return
                confirm_entry.configure(border_color=_BORDER)
                self.delete_character()

            del_btn = ctk.CTkButton(
                confirm_row,
                text="Delete character",
                command=_do_delete,
                width=140,
                height=34,
                font=("Segoe UI", 12, "bold"),
                fg_color=_RED,
                text_color="#1e1e2e",
                hover_color="#d4637f",
            )
            del_btn.pack(side=tk.LEFT, padx=(0, 8))

            ctk.CTkButton(
                confirm_row,
                text="Cancel",
                command=lambda: _select_op("Copy"),
                width=80,
                height=34,
                fg_color="transparent",
                text_color=_FG_ALT,
                border_width=1,
                border_color=_BORDER,
                hover_color=_PANEL2,
            ).pack(side=tk.LEFT, padx=(0, 14))

            # Backup assurance
            ctk.CTkLabel(
                confirm_row,
                text="A backup will be taken first",
                font=("Segoe UI", 11),
                text_color=_GOOD,
            ).pack(side=tk.LEFT)

    def refresh_slot_names(self):
        """Rebuild the detail panel to pick up new slot names after a save reload."""
        if not hasattr(self, "_active_op") or self._active_op is None:
            return
        if not hasattr(self, "_detail_frame"):
            return
        # Retrieve the color constants stored on the parent frame isn't possible,
        # so trigger a full UI rebuild by calling setup_ui again.
        # The scrollable frame is recreated; existing refs in ops go stale but
        # setup_ui() recreates everything cleanly.
        for w in self.parent.winfo_children():
            w.destroy()
        self.setup_ui()

    def _get_slot_display_names(self):
        """Get display names for all slots."""
        save_file = self.get_save_file()
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

    # ========== Operations ==========

    def copy_character(self):
        """Copy character from one slot to another"""
        # Check if game is running
        if self.is_game_running and self.is_game_running():
            CTkMessageBox.showerror(
                "Elden Ring is Running!",
                "Please close Elden Ring before modifying save files.",
                parent=self.parent,
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        from_slot = int(self.copy_from_var.get()) - 1
        to_slot = int(self.copy_to_var.get()) - 1

        if from_slot == to_slot:
            CTkMessageBox.showerror(
                "Error",
                "Source and destination slots must be different!",
                parent=self.parent,
            )
            return

        from_char = save_file.characters[from_slot]
        to_char = save_file.characters[to_slot]

        if from_char.is_empty():
            CTkMessageBox.showerror(
                "Error", f"Slot {from_slot + 1} is empty!", parent=self.parent
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
                "Overwrite?",
                f"Slot {to_slot + 1} contains '{to_name}'.\n\nOverwrite with '{from_name}'?",
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
                    f"Character '{from_name}' copied to Slot {to_slot + 1}!",
                    duration=2500,
                ),
            )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Copy failed:\n{str(e)}", parent=self.parent
            )
            import traceback

            traceback.print_exc()

    def transfer_character(self):
        """Transfer character to another save file"""
        # Check if game is running
        if self.is_game_running and self.is_game_running():
            CTkMessageBox.showerror(
                "Elden Ring is Running!",
                "Please close Elden Ring before modifying save files.",
                parent=self.parent,
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        from_slot = int(self.transfer_from_var.get()) - 1
        from_char = save_file.characters[from_slot]

        if from_char.is_empty():
            CTkMessageBox.showerror(
                "Error", f"Slot {from_slot + 1} is empty!", parent=self.parent
            )
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
            target_save = Save.from_file(target_path)

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
                result[0] = int(to_slot_var.get()) - 1
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

            # Delay message to ensure it appears on top after reload
            self.show_toast(
                f"Character transferred to target Slot {to_slot + 1}!", duration=2500
            )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Transfer failed:\n{str(e)}", parent=self.parent
            )
            import traceback

            traceback.print_exc()

    def swap_characters(self):
        """Swap two character slots"""
        # Check if game is running
        if self.is_game_running and self.is_game_running():
            CTkMessageBox.showerror(
                "Elden Ring is Running!",
                "Please close Elden Ring before modifying save files.",
                parent=self.parent,
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        slot_a = int(self.swap_a_var.get()) - 1
        slot_b = int(self.swap_b_var.get()) - 1

        if slot_a == slot_b:
            CTkMessageBox.showerror(
                "Error", "Slots must be different!", parent=self.parent
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
                f"Swapped Slot {slot_a + 1} and Slot {slot_b + 1}!", duration=2500
            )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Swap failed:\n{str(e)}", parent=self.parent
            )
            import traceback

            traceback.print_exc()

    def export_character(self):
        """Export character to .erc file"""
        # Check if game is running
        if self.is_game_running and self.is_game_running():
            CTkMessageBox.showerror(
                "Elden Ring is Running!",
                "Please close Elden Ring before modifying save files.",
                parent=self.parent,
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        slot = int(self.export_slot_var.get()) - 1
        char = save_file.characters[slot]

        if char.is_empty():
            CTkMessageBox.showerror(
                "Error", f"Slot {slot + 1} is empty!", parent=self.parent
            )
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
                "Success",
                f"Character '{char_name}' exported to:\n{output_path}",
                parent=self.parent,
            )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Export failed:\n{str(e)}", parent=self.parent
            )
            import traceback

            traceback.print_exc()

    def import_character(self):
        """Import character from .erc file"""
        # Check if game is running
        if self.is_game_running and self.is_game_running():
            CTkMessageBox.showerror(
                "Elden Ring is Running!",
                "Please close Elden Ring before modifying save files.",
                parent=self.parent,
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        import_path = filedialog.askopenfilename(
            title="Import Character",
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
                "Overwrite?",
                f"Slot {to_slot + 1} contains '{to_name}'.\n\nOverwrite?",
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
            self.show_toast(f"Character imported to Slot {to_slot + 1}!", duration=2500)

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Import failed:\n{str(e)}", parent=self.parent
            )
            import traceback

            traceback.print_exc()

    def open_character_browser(self):
        """Open the character browser dialog."""
        from er_save_manager.ui.dialogs.character_browser import CharacterBrowser

        save = self.get_save_file()
        if not save:
            CTkMessageBox.showwarning(
                "No Save File",
                "Please load a save file first",
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
                "Elden Ring is Running!",
                "Please close Elden Ring before modifying save files.",
                parent=self.parent,
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        slot = int(self.delete_slot_var.get()) - 1
        char = save_file.characters[slot]

        if char.is_empty():
            CTkMessageBox.showinfo(
                "Info", f"Slot {slot + 1} is already empty.", parent=self.parent
            )
            return

        char_name = char.get_character_name()

        response = CTkMessageBox.askyesno(
            "Confirm Delete",
            f"Delete character '{char_name}' from Slot {slot + 1}?\n\nThis will create a backup first.",
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
            self.show_toast(f"Character deleted from Slot {slot + 1}", duration=2500)

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Delete failed:\n{str(e)}", parent=self.parent
            )
            import traceback

            traceback.print_exc()
