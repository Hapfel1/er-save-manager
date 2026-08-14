"""
DSR Character Management Tab

Copy, transfer, swap, delete, export, and import character slots.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.games.game_profiles import PROFILES_BY_KEY
from er_save_manager.platform import PlatformUtils
from er_save_manager.ui.dialogs.save_selector import SaveSelectorDialog
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel, pick_file

from . import character_ops
from .save import CHARACTER_SLOTS, DSRSave


class DSRCharacterManagementTab:
    def __init__(
        self,
        parent,
        get_dsr_save,
        get_save_path,
        reload_callback,
        show_toast,
        is_game_running=None,
    ) -> None:
        self.parent = parent
        self._get_save = get_dsr_save
        self._get_save_path = get_save_path
        self._reload = reload_callback
        self._show_toast = show_toast
        self.is_game_running = is_game_running

        self._operation_var = None
        self._operation_map: dict[str, str] = {}
        self._ops_panel = None
        self._ops_scrollable = None

        self._copy_from_var = tk.StringVar()
        self._copy_to_var = tk.StringVar()
        self._transfer_from_var = tk.StringVar()
        self._swap_a_var = tk.StringVar()
        self._swap_b_var = tk.StringVar()
        self._export_slot_var = tk.StringVar()
        self._import_slot_var = tk.StringVar()
        self._delete_slot_var = tk.StringVar()

    def setup_ui(self) -> None:
        scroll = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(scroll)

        ctk.CTkLabel(
            scroll, text="Character Management", font=("Segoe UI", 16, "bold")
        ).pack(pady=10)
        ctk.CTkLabel(
            scroll,
            text="Copy, transfer, swap, export, import, or delete character slots",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(pady=5)

        selector = ctk.CTkFrame(scroll, corner_radius=10)
        selector.pack(fill=tk.X, padx=20, pady=10)
        ctk.CTkLabel(
            selector, text="Select Operation", font=("Segoe UI", 12, "bold")
        ).pack(anchor=tk.W, padx=15, pady=(10, 5))

        controls = ctk.CTkFrame(selector, fg_color="transparent")
        controls.pack(fill=tk.X, padx=15, pady=(5, 15))

        operations = [
            ("Copy Character", "copy"),
            ("Transfer to Another Save", "transfer"),
            ("Swap Slots", "swap"),
            ("Export Character", "export"),
            ("Import Character", "import"),
            ("Delete Character", "delete"),
        ]
        self._operation_map = {op[0]: op[1] for op in operations}
        self._operation_var = tk.StringVar(value=operations[0][0])

        ctk.CTkLabel(controls, text="Operation:").pack(side=tk.LEFT, padx=(0, 10))
        combo = ctk.CTkComboBox(
            controls,
            variable=self._operation_var,
            values=[op[0] for op in operations],
            state="readonly",
            width=300,
            command=self._update_panel,
        )
        combo.pack(side=tk.LEFT, padx=5)

        self._ops_panel = ctk.CTkFrame(scroll, corner_radius=10)
        self._ops_panel.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        ctk.CTkLabel(
            self._ops_panel, text="Operation Details", font=("Segoe UI", 12, "bold")
        ).pack(anchor=tk.W, padx=15, pady=(10, 5))

        self._ops_scrollable = ctk.CTkScrollableFrame(
            self._ops_panel, fg_color="transparent"
        )
        self._ops_scrollable.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 15))
        bind_mousewheel(self._ops_scrollable)

        self._update_panel()

    def refresh(self) -> None:
        self._update_panel()

    def _update_panel(self, _value=None) -> None:
        for widget in self._ops_scrollable.winfo_children():
            widget.destroy()

        operation = self._operation_map.get(self._operation_var.get(), "copy")
        setup = {
            "copy": self._setup_copy_panel,
            "transfer": self._setup_transfer_panel,
            "swap": self._setup_swap_panel,
            "export": self._setup_export_panel,
            "import": self._setup_import_panel,
            "delete": self._setup_delete_panel,
        }[operation]
        setup()

    def _slot_names(self, save=None) -> list[str]:
        save = save or self._get_save()
        if not save:
            return [f"Slot {i + 1} - Empty" for i in range(CHARACTER_SLOTS)]
        names = []
        for i, char in enumerate(save.characters):
            names.append(
                f"Slot {i + 1} - {char.name}" if char else f"Slot {i + 1} - Empty"
            )
        return names

    @staticmethod
    def _slot_index(display_name: str) -> int:
        return int(display_name.split(" - ")[0].replace("Slot ", "")) - 1

    def _slot_picker(
        self, controls, label: str, var: tk.StringVar, index: int = 0
    ) -> None:
        ctk.CTkLabel(controls, text=label).pack(side=tk.LEFT, padx=5)
        names = self._slot_names()
        combo = ctk.CTkComboBox(
            controls, variable=var, values=names, state="readonly", width=220
        )
        combo.set(names[index] if index < len(names) else (names[0] if names else ""))
        combo.pack(side=tk.LEFT, padx=5)

    def _setup_copy_panel(self) -> None:
        ctk.CTkLabel(
            self._ops_scrollable,
            text="Copy a character from one slot to another in the same save file",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(anchor=tk.W, pady=10)
        ctk.CTkLabel(
            self._ops_scrollable,
            text=(
                "Note: if the target slot has never had a character created "
                "in it in-game, the copy will not appear on the in-game load "
                "screen. Create a throwaway character there first, then copy."
            ),
            font=("Segoe UI", 10),
            text_color=("darkorange", "orange"),
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 5))
        controls = ctk.CTkFrame(self._ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)
        self._slot_picker(controls, "From Slot:", self._copy_from_var, 0)
        self._slot_picker(controls, "To Slot:", self._copy_to_var, 1)
        ctk.CTkButton(
            controls, text="Copy Character", command=self._copy_character, width=150
        ).pack(side=tk.LEFT, padx=20)

    def _setup_transfer_panel(self) -> None:
        ctk.CTkLabel(
            self._ops_scrollable,
            text="Transfer a character to a different save file",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(anchor=tk.W, pady=10)
        ctk.CTkLabel(
            self._ops_scrollable,
            text=(
                "Note: if the target slot has never had a character created "
                "in it in-game, the transfer will not appear on the in-game "
                "load screen. Create a throwaway character there first."
            ),
            font=("Segoe UI", 10),
            text_color=("darkorange", "orange"),
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 5))
        controls = ctk.CTkFrame(self._ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)
        self._slot_picker(controls, "From Slot:", self._transfer_from_var, 0)
        ctk.CTkButton(
            controls,
            text="Select Target Save...",
            command=self._transfer_character,
            width=180,
        ).pack(side=tk.LEFT, padx=20)

    def _setup_swap_panel(self) -> None:
        ctk.CTkLabel(
            self._ops_scrollable,
            text="Exchange two character slots",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(anchor=tk.W, pady=10)
        controls = ctk.CTkFrame(self._ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)
        self._slot_picker(controls, "Slot A:", self._swap_a_var, 0)
        self._slot_picker(controls, "Slot B:", self._swap_b_var, 1)
        ctk.CTkButton(
            controls, text="Swap Slots", command=self._swap_characters, width=150
        ).pack(side=tk.LEFT, padx=20)

    def _setup_export_panel(self) -> None:
        ctk.CTkLabel(
            self._ops_scrollable,
            text="Save character to a standalone .dsrc file for backup or sharing",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(anchor=tk.W, pady=10)
        controls = ctk.CTkFrame(self._ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)
        self._slot_picker(controls, "Slot:", self._export_slot_var, 0)
        ctk.CTkButton(
            controls,
            text="Export Character...",
            command=self._export_character,
            width=180,
        ).pack(side=tk.LEFT, padx=20)

    def _setup_import_panel(self) -> None:
        ctk.CTkLabel(
            self._ops_scrollable,
            text="Load a character from a .dsrc file into a slot",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(anchor=tk.W, pady=10)
        ctk.CTkLabel(
            self._ops_scrollable,
            text=(
                "Note: if the target slot has never had a character created "
                "in it in-game, the import will not appear on the in-game "
                "load screen. Create a throwaway character there first."
            ),
            font=("Segoe UI", 10),
            text_color=("darkorange", "orange"),
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 5))
        controls = ctk.CTkFrame(self._ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)
        self._slot_picker(controls, "To Slot:", self._import_slot_var, 0)
        ctk.CTkButton(
            controls,
            text="Import Character...",
            command=self._import_character,
            width=180,
        ).pack(side=tk.LEFT, padx=20)

    def _setup_delete_panel(self) -> None:
        ctk.CTkLabel(
            self._ops_scrollable,
            text="Clear a character slot (creates backup)",
            font=("Segoe UI", 11),
            text_color=("red", "red"),
        ).pack(anchor=tk.W, pady=10)
        controls = ctk.CTkFrame(self._ops_scrollable, fg_color="transparent")
        controls.pack(fill=tk.X, pady=10)
        self._slot_picker(controls, "Slot:", self._delete_slot_var, 0)
        ctk.CTkButton(
            controls,
            text="Delete Character",
            command=self._delete_character,
            width=150,
            fg_color=("red", "darkred"),
            hover_color=("darkred", "red"),
        ).pack(side=tk.LEFT, padx=20)

    def _backup(self, path: Path, description: str, operation: str) -> None:
        from er_save_manager.backup.manager import BackupManager

        BackupManager(path).create_backup(
            description=description, operation=operation, save=None
        )

    def _confirm_empty_target(self, to_slot: int) -> bool:
        """Warn before writing a character into a currently-empty slot.

        Dark Souls Remastered will not display a character written directly
        into a slot that has never been created in-game. The save file looks
        correct and the manager will show it, but the in-game load screen
        stays blank for that slot.
        """
        return CTkMessageBox.askyesno(
            "Empty Slot",
            f"Slot {to_slot + 1} is currently empty.\n\n"
            "Dark Souls Remastered will not show a character written "
            "directly into a slot that has never been created in-game, "
            "even though the save file and this manager will look correct.\n\n"
            f"If Slot {to_slot + 1} has never had a character created in it "
            "before, go create a quick throwaway character there first (any "
            "name, skip the intro, save and quit), then run this again.\n\n"
            "Already created a character in this slot? Continue.",
            parent=self.parent,
        )

    def _check_game_not_running(self) -> bool:
        if self.is_game_running and self.is_game_running():
            CTkMessageBox.showerror(
                "Game is running",
                "Please close Dark Souls: Remastered before modifying save files.",
                parent=self.parent,
            )
            return False
        return True

    def _copy_character(self) -> None:
        if not self._check_game_not_running():
            return

        save = self._get_save()
        if not save:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        from_slot = self._slot_index(self._copy_from_var.get())
        to_slot = self._slot_index(self._copy_to_var.get())
        if from_slot == to_slot:
            CTkMessageBox.showerror(
                "Error",
                "Source and destination slots must be different!",
                parent=self.parent,
            )
            return

        from_char = save.characters[from_slot]
        if from_char is None:
            CTkMessageBox.showerror(
                "Error", f"Slot {from_slot + 1} is empty!", parent=self.parent
            )
            return

        to_char = save.characters[to_slot]
        if to_char is not None:
            response = CTkMessageBox.askyesno(
                "Overwrite?",
                f"Slot {to_slot + 1} contains '{to_char.name}'.\n\nOverwrite with '{from_char.name}'?",
                parent=self.parent,
            )
            if not response:
                return
        else:
            if not self._confirm_empty_target(to_slot):
                return

        save_path = self._get_save_path()
        try:
            if save_path:
                self._backup(
                    Path(save_path),
                    f"before_copy_slot{from_slot + 1}_to_slot{to_slot + 1}",
                    "copy_character",
                )

            character_ops.copy_slot(save, from_slot, to_slot)

            if save_path:
                save.save_to_file(Path(save_path))
            if self._reload:
                self._reload()
            self._show_toast(
                f"Character '{from_char.name}' copied to Slot {to_slot + 1}! "
                "In-game, this slot may still show the old character until "
                "you load it once.",
                duration=4500,
            )
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Copy failed:\n{str(e)}", parent=self.parent
            )

    def _swap_characters(self) -> None:
        if not self._check_game_not_running():
            return

        save = self._get_save()
        if not save:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        slot_a = self._slot_index(self._swap_a_var.get())
        slot_b = self._slot_index(self._swap_b_var.get())
        if slot_a == slot_b:
            CTkMessageBox.showerror(
                "Error", "Slots must be different!", parent=self.parent
            )
            return

        char_a = save.characters[slot_a]
        char_b = save.characters[slot_b]
        if char_a is None and char_b is not None:
            if not self._confirm_empty_target(slot_a):
                return
        elif char_b is None and char_a is not None:
            if not self._confirm_empty_target(slot_b):
                return

        save_path = self._get_save_path()
        try:
            if save_path:
                self._backup(
                    Path(save_path),
                    f"before_swap_slot{slot_a + 1}_slot{slot_b + 1}",
                    "swap_characters",
                )

            character_ops.swap_slots(save, slot_a, slot_b)

            if save_path:
                save.save_to_file(Path(save_path))
            if self._reload:
                self._reload()
            self._show_toast(
                f"Swapped Slot {slot_a + 1} and Slot {slot_b + 1}!", duration=2500
            )
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Swap failed:\n{str(e)}", parent=self.parent
            )

    def _delete_character(self) -> None:
        if not self._check_game_not_running():
            return

        save = self._get_save()
        if not save:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        slot = self._slot_index(self._delete_slot_var.get())
        char = save.characters[slot]
        if char is None:
            CTkMessageBox.showinfo(
                "Info", f"Slot {slot + 1} is already empty.", parent=self.parent
            )
            return

        name = char.name
        response = CTkMessageBox.askyesno(
            "Confirm Delete",
            f"Delete character '{name}' from Slot {slot + 1}?\n\nThis will create a backup first.",
            parent=self.parent,
        )
        if not response:
            return

        save_path = self._get_save_path()
        try:
            if save_path:
                self._backup(
                    Path(save_path),
                    f"before_delete_{name}_slot_{slot + 1}",
                    "delete_character",
                )

            character_ops.delete_slot(save, slot)

            if save_path:
                save.save_to_file(Path(save_path))
            if self._reload:
                self._reload()
            self._show_toast(f"Character deleted from Slot {slot + 1}", duration=2500)
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Delete failed:\n{str(e)}", parent=self.parent
            )

    def _export_character(self) -> None:
        save = self._get_save()
        if not save:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        slot = self._slot_index(self._export_slot_var.get())
        char = save.characters[slot]
        if char is None:
            CTkMessageBox.showerror(
                "Error", f"Slot {slot + 1} is empty!", parent=self.parent
            )
            return

        default_name = f"{char.name or f'Character_{slot + 1}'}.dsrc"
        output_path = pick_file(
            title="Export Character",
            save=True,
            defaultextension=".dsrc",
            initialfile=default_name,
            filetypes=[("DSR Character", "*.dsrc"), ("All files", "*.*")],
        )
        if not output_path:
            return

        try:
            character_ops.export_character(save, slot, Path(output_path))
            CTkMessageBox.showinfo(
                "Success",
                f"Character '{char.name}' exported to:\n{output_path}",
                parent=self.parent,
            )
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Export failed:\n{str(e)}", parent=self.parent
            )

    def _import_character(self) -> None:
        if not self._check_game_not_running():
            return

        save = self._get_save()
        if not save:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        import_path = pick_file(
            title="Import Character",
            filetypes=[("DSR Character", "*.dsrc"), ("All files", "*.*")],
        )
        if not import_path:
            return

        to_slot = self._slot_index(self._import_slot_var.get())
        to_char = save.characters[to_slot]
        if to_char is not None:
            response = CTkMessageBox.askyesno(
                "Overwrite?",
                f"Slot {to_slot + 1} contains '{to_char.name}'.\n\nOverwrite?",
                parent=self.parent,
            )
            if not response:
                return
        else:
            if not self._confirm_empty_target(to_slot):
                return

        save_path = self._get_save_path()
        try:
            if save_path:
                self._backup(
                    Path(save_path),
                    f"before_import_to_slot_{to_slot + 1}",
                    "import_character",
                )

            character_ops.import_character(save, to_slot, Path(import_path))

            if save_path:
                save.save_to_file(Path(save_path))
            if self._reload:
                self._reload()
            self._show_toast(
                f"Character imported to Slot {to_slot + 1}!", duration=2500
            )
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Import failed:\n{str(e)}", parent=self.parent
            )

    def _transfer_character(self) -> None:
        if not self._check_game_not_running():
            return

        save = self._get_save()
        if not save:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        from_slot = self._slot_index(self._transfer_from_var.get())
        from_char = save.characters[from_slot]
        if from_char is None:
            CTkMessageBox.showerror(
                "Error", f"Slot {from_slot + 1} is empty!", parent=self.parent
            )
            return

        current_path = self._get_save_path()
        target_path = self._select_target_save_file()
        if not target_path:
            return
        if current_path and Path(target_path).resolve() == Path(current_path).resolve():
            CTkMessageBox.showerror(
                "Error",
                "Select a different target save file for transfer.",
                parent=self.parent,
            )
            return

        try:
            target_save = DSRSave.from_file(target_path)
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Could not load target save:\n{str(e)}", parent=self.parent
            )
            return

        to_slot = self._pick_target_slot(target_save, target_path)
        if to_slot is None:
            return

        if target_save.characters[to_slot] is None:
            if not self._confirm_empty_target(to_slot):
                return

        try:
            if current_path:
                self._backup(
                    Path(current_path),
                    f"before_transfer_slot_{from_slot + 1}_to_other_save",
                    "transfer_character",
                )
            self._backup(
                Path(target_path),
                f"before_receive_character_to_slot_{to_slot + 1}",
                "receive_character",
            )

            character_ops.transfer_slot(save, from_slot, target_save, to_slot)

            if current_path:
                save.save_to_file(Path(current_path))
            target_save.save_to_file(Path(target_path))

            if self._reload:
                self._reload()
            self._show_toast(
                f"Character transferred to target Slot {to_slot + 1}! "
                "In-game, this slot may still show the old character until "
                "you load it once.",
                duration=4500,
            )
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Transfer failed:\n{str(e)}", parent=self.parent
            )

    def _browse_target_save_manually(self) -> str | None:
        """Open a manual file picker for the target save file."""
        current_path = self._get_save_path()
        initialdir = str(Path(current_path).parent) if current_path else None
        return pick_file(
            title="Select target save file",
            initialdir=initialdir,
            filetypes=[("DSR save files", "*.sl2"), ("All files", "*.*")],
        )

    def _select_target_save_file(self) -> str | None:
        """Show a picker for the target save file with auto-detected saves."""
        profile = PROFILES_BY_KEY["dark_souls_remastered"]
        found_saves = PlatformUtils.find_all_save_files(profile)
        current_path = self._get_save_path()
        if current_path:
            current_resolved = Path(current_path).resolve()
            found_saves = [
                save_path
                for save_path in found_saves
                if save_path.resolve() != current_resolved
            ]

        if found_saves:
            return SaveSelectorDialog.show(
                self.parent,
                found_saves,
                lambda path: None,
                browse_callback=self._browse_target_save_manually,
                browse_button_text="Browse Manually",
            )
        return self._browse_target_save_manually()

    def _pick_target_slot(self, target_save: DSRSave, target_path: str) -> int | None:
        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Select Target Slot")
        dialog.geometry("520x220")
        force_render_dialog(dialog)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Select destination slot in target save:",
            font=("Segoe UI", 12),
        ).pack(padx=10, pady=(12, 6))
        ctk.CTkLabel(
            dialog,
            text=str(target_path),
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
            wraplength=480,
        ).pack(padx=10, pady=(0, 10))

        names = self._slot_names(target_save)
        slot_var = tk.StringVar(value=names[0] if names else "")
        ctk.CTkComboBox(
            dialog, variable=slot_var, values=names, state="readonly", width=360
        ).pack(pady=(0, 12))

        result = {"value": None}

        def confirm():
            try:
                result["value"] = self._slot_index(slot_var.get())
            except Exception:
                result["value"] = 0
            dialog.destroy()

        ctk.CTkButton(dialog, text="Transfer", command=confirm, width=140).pack(
            pady=(0, 12)
        )
        dialog.bind("<Return>", lambda _e: confirm())
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        dialog.wait_window()
        return result["value"]
