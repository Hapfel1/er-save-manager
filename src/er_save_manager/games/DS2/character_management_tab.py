"""
DS2 character management tab.

Copy, transfer, swap, export, import, and delete character slots.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.games.DS2.character_ops import DS2CharacterOperations
from er_save_manager.games.DS2.save import DS2Save
from er_save_manager.games.game_profiles import PROFILES_BY_KEY, find_save_paths
from er_save_manager.i18n import t
from er_save_manager.ui.dialogs.save_selector import SaveSelectorDialog
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel, force_render_dialog, pick_file

# Shown after any operation that writes a character into a slot that
# already had cached load-screen info (copy, swap, transfer, import).
# DS2's character-select screen reads its own cached summary (see
# save.py: entry 0 / entry 22) which this tool keeps in sync for the
# name, but the game itself only fully refreshes that summary the next
# time it actually loads the save, same as the DS1R/DS3 first-load
# quirk documented in DS2Save.is_slot_initialized().
STALE_SUMMARY_NOTE = (
    "In-game, this slot may still show the old character until you load it once."
)

_DS2_FILETYPES = [("DS2 Character", "*.ds2c"), ("All files", "*.*")]
_SAVE_FILETYPES = [("DS2 save files", "*.sl2"), ("All files", "*.*")]


class DS2CharacterManagementTab:
    """
    Args:
        parent: parent widget the tab content is built into.
        get_save: callable returning the current DS2Save, or None if unloaded.
        get_save_path: callable returning the current save file path.
        reload_save: callable to reload the save file after a write.
        show_toast: callable(message, duration) for transient status messages.
        is_game_running: optional callable() -> bool.
    """

    def __init__(
        self,
        parent,
        get_save,
        get_save_path,
        reload_save,
        show_toast,
        is_game_running=None,
    ) -> None:
        self.parent = parent
        self.get_save = get_save
        self.get_save_path = get_save_path
        self.reload_save = reload_save
        self.show_toast = show_toast
        self.is_game_running = is_game_running

        self.operation_var = None
        self.operation_map: dict[str, str] = {}
        self.ops_scrollable = None

        self.copy_from_var = None
        self.copy_to_var = None
        self.transfer_from_var = None
        self.swap_a_var = None
        self.swap_b_var = None
        self.export_slot_var = None
        self.import_slot_var = None
        self.delete_slot_var = None

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        scroll_frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)
        bind_mousewheel(scroll_frame)

        ctk.CTkLabel(
            scroll_frame, text=t("Character Management"), font=("Segoe UI", 16, "bold")
        ).pack(pady=10)

        selector_frame = ctk.CTkFrame(scroll_frame, corner_radius=10)
        selector_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(
            selector_frame, text=t("Select Operation"), font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        selector_controls = ctk.CTkFrame(selector_frame, fg_color="transparent")
        selector_controls.pack(fill="x", padx=15, pady=(5, 15))

        operations = [
            ("Copy Character", "copy"),
            ("Transfer to Another Save", "transfer"),
            ("Swap Slots", "swap"),
            ("Export Character", "export"),
            ("Import Character", "import"),
            ("Delete Character", "delete"),
        ]
        self.operation_map = dict(operations)
        self.operation_var = tk.StringVar(value=operations[0][0])

        ctk.CTkComboBox(
            selector_controls,
            variable=self.operation_var,
            values=[label for label, _ in operations],
            state="readonly",
            width=280,
            command=lambda _v: self._update_panel(),
        ).pack(side="left")

        self.ops_panel = ctk.CTkFrame(scroll_frame, corner_radius=10)
        self.ops_panel.pack(fill="both", expand=True, padx=20, pady=10)
        self.ops_scrollable = ctk.CTkScrollableFrame(
            self.ops_panel, fg_color="transparent"
        )
        self.ops_scrollable.pack(fill="both", expand=True, padx=15, pady=15)
        bind_mousewheel(self.ops_scrollable)

        self._update_panel()

    def refresh(self) -> None:
        """Rebuild the current operation panel so slot dropdowns reflect
        the just-loaded save. Called after loading or reloading a save."""
        if self.ops_scrollable is not None:
            self._update_panel()

    def _update_panel(self) -> None:
        for widget in self.ops_scrollable.winfo_children():
            widget.destroy()

        operation = self.operation_map.get(self.operation_var.get(), "copy")
        {
            "copy": self._setup_copy_panel,
            "transfer": self._setup_transfer_panel,
            "swap": self._setup_swap_panel,
            "export": self._setup_export_panel,
            "import": self._setup_import_panel,
            "delete": self._setup_delete_panel,
        }[operation]()

    def _slot_display_names(self, save: DS2Save | None = None) -> list[str]:
        save = save or self.get_save()
        if save is None:
            return [f"{i} - (no save loaded)" for i in range(10)]

        occupied = save.slot_occupancy()
        names = []
        for i in range(10):
            if i in occupied:
                names.append(f"{i} - {occupied[i]}")
            elif save.is_slot_initialized(i):
                names.append(f"{i} - (empty)")
            else:
                names.append(f"{i} - (never created in-game)")
        return names

    @staticmethod
    def _slot_index_from_display(value: str) -> int:
        return int(value.split(" - ")[0])

    # ------------------------------------------------------------------
    # Panels
    # ------------------------------------------------------------------

    def _labeled_slot_combo(self, parent, label_text, values, initial_index=0):
        ctk.CTkLabel(parent, text=label_text).pack(side="left", padx=(0, 5))
        var = tk.StringVar(value=values[initial_index])
        ctk.CTkComboBox(
            parent, variable=var, values=values, state="readonly", width=220
        ).pack(side="left", padx=5)
        return var

    def _setup_copy_panel(self) -> None:
        ctk.CTkLabel(
            self.ops_scrollable,
            text=t("Copy a character from one slot to another in the same save file."),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", pady=(0, 10))

        row = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        row.pack(fill="x", pady=5)

        names = self._slot_display_names()
        self.copy_from_var = self._labeled_slot_combo(row, "From:", names, 0)
        self.copy_to_var = self._labeled_slot_combo(row, "To:", names, 1)
        ctk.CTkButton(row, text=t("Copy Character"), command=self._copy_character).pack(
            side="left", padx=15
        )

    def _setup_transfer_panel(self) -> None:
        ctk.CTkLabel(
            self.ops_scrollable,
            text=t("Transfer a character to a slot in a different save file."),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", pady=(0, 10))

        row = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        row.pack(fill="x", pady=5)

        names = self._slot_display_names()
        self.transfer_from_var = self._labeled_slot_combo(row, "From:", names, 0)
        ctk.CTkButton(
            row, text=t("Select Target Save..."), command=self._transfer_character
        ).pack(side="left", padx=15)

    def _setup_swap_panel(self) -> None:
        ctk.CTkLabel(
            self.ops_scrollable,
            text=t("Exchange two character slots in the same save file."),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", pady=(0, 10))

        row = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        row.pack(fill="x", pady=5)

        names = self._slot_display_names()
        self.swap_a_var = self._labeled_slot_combo(row, "Slot A:", names, 0)
        self.swap_b_var = self._labeled_slot_combo(row, "Slot B:", names, 1)
        ctk.CTkButton(row, text=t("Swap Slots"), command=self._swap_characters).pack(
            side="left", padx=15
        )

    def _setup_export_panel(self) -> None:
        ctk.CTkLabel(
            self.ops_scrollable,
            text=t(
                "Save a character to a standalone .ds2c file for backup or sharing."
            ),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", pady=(0, 10))

        row = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        row.pack(fill="x", pady=5)

        names = self._slot_display_names()
        self.export_slot_var = self._labeled_slot_combo(row, "Slot:", names, 0)
        ctk.CTkButton(
            row, text=t("Export Character..."), command=self._export_character
        ).pack(side="left", padx=15)

    def _setup_import_panel(self) -> None:
        ctk.CTkLabel(
            self.ops_scrollable,
            text=t("Load a character from a .ds2c file into a slot."),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", pady=(0, 10))

        row = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        row.pack(fill="x", pady=5)

        names = self._slot_display_names()
        self.import_slot_var = self._labeled_slot_combo(row, "To Slot:", names, 0)
        ctk.CTkButton(
            row, text=t("Import Character..."), command=self._import_character
        ).pack(side="left", padx=15)

    def _setup_delete_panel(self) -> None:
        ctk.CTkLabel(
            self.ops_scrollable,
            text=t("Clear a character slot (creates a backup first)."),
            text_color=("red", "red"),
        ).pack(anchor="w", pady=(0, 10))

        row = ctk.CTkFrame(self.ops_scrollable, fg_color="transparent")
        row.pack(fill="x", pady=5)

        names = self._slot_display_names()
        self.delete_slot_var = self._labeled_slot_combo(row, "Slot:", names, 0)
        ctk.CTkButton(
            row,
            text=t("Delete Character"),
            command=self._delete_character,
            fg_color=("red", "darkred"),
            hover_color=("darkred", "red"),
        ).pack(side="left", padx=15)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _check_game_not_running(self) -> bool:
        if self.is_game_running and self.is_game_running():
            CTkMessageBox.showerror(
                t("Game is running"),
                t("Please close Dark Souls II before modifying save files."),
                parent=self.parent,
            )
            return False
        return True

    def _require_save(self) -> DS2Save | None:
        save = self.get_save()
        if save is None:
            CTkMessageBox.showwarning(
                t("No Save"), t("Please load a save file first."), parent=self.parent
            )
        return save

    def _backup(self, save_path, description: str, operation: str) -> None:
        if not save_path:
            return
        try:
            from er_save_manager.backup.manager import BackupManager

            BackupManager(Path(save_path)).create_backup(
                description=description, operation=operation
            )
        except Exception:
            pass

    def _confirm_uninitialized_override(self, message: str) -> bool:
        """Show the uninitialized-slot warning and ask whether to proceed
        anyway."""
        return CTkMessageBox.askyesno(
            t("Slot never created in-game"),
            message + "\n\nWrite anyway?",
            parent=self.parent,
        )

    def _write_and_reload(self, save: DS2Save, toast_message: str) -> None:
        save_path = self.get_save_path()
        if save_path:
            save.save_to_file(save_path)
        if self.reload_save:
            self.reload_save()
        self.show_toast(f"{toast_message} {STALE_SUMMARY_NOTE}", duration=4000)

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def _copy_character(self) -> None:
        if not self._check_game_not_running():
            return
        save = self._require_save()
        if save is None:
            return

        from_slot = self._slot_index_from_display(self.copy_from_var.get())
        to_slot = self._slot_index_from_display(self.copy_to_var.get())
        if from_slot == to_slot:
            CTkMessageBox.showerror(
                t("Error"),
                t("Source and destination slots must differ."),
                parent=self.parent,
            )
            return

        from_name = save.characters[from_slot].name
        if not from_name:
            CTkMessageBox.showerror(
                t("Error"),
                t("Slot {from_slot} is empty.").format(from_slot=from_slot),
                parent=self.parent,
            )
            return

        to_name = save.characters[to_slot].name
        if to_name and not CTkMessageBox.askyesno(
            t("Overwrite?"),
            t(
                "Slot {to_slot} contains '{to_name}'.\n\nOverwrite with '{from_name}'?"
            ).format(to_slot=to_slot, to_name=to_name, from_name=from_name),
            parent=self.parent,
        ):
            return

        try:
            self._backup(
                self.get_save_path(),
                f"before_copy_{from_name}_slot{from_slot}_to_slot{to_slot}",
                "copy_character",
            )
            DS2CharacterOperations.copy_slot(save, from_slot, to_slot)
        except RuntimeError as warning:
            if not self._confirm_uninitialized_override(str(warning)):
                return
            DS2CharacterOperations.copy_slot(save, from_slot, to_slot, force=True)
        except Exception as e:
            CTkMessageBox.showerror(
                t("Error"), t("Copy failed:\n{e}").format(e=e), parent=self.parent
            )
            return

        self._write_and_reload(
            save, f"Character '{from_name}' copied to Slot {to_slot}."
        )

    def _swap_characters(self) -> None:
        if not self._check_game_not_running():
            return
        save = self._require_save()
        if save is None:
            return

        slot_a = self._slot_index_from_display(self.swap_a_var.get())
        slot_b = self._slot_index_from_display(self.swap_b_var.get())
        if slot_a == slot_b:
            CTkMessageBox.showerror(
                t("Error"), t("Slots must differ."), parent=self.parent
            )
            return

        try:
            self._backup(
                self.get_save_path(),
                f"before_swap_{slot_a}_and_{slot_b}",
                "swap_characters",
            )
            DS2CharacterOperations.swap_slots(save, slot_a, slot_b)
        except RuntimeError as warning:
            if not self._confirm_uninitialized_override(str(warning)):
                return
            DS2CharacterOperations.swap_slots(save, slot_a, slot_b, force=True)
        except Exception as e:
            CTkMessageBox.showerror(
                t("Error"), t("Swap failed:\n{e}").format(e=e), parent=self.parent
            )
            return

        self._write_and_reload(save, f"Swapped Slot {slot_a} and Slot {slot_b}.")

    def _export_character(self) -> None:
        save = self._require_save()
        if save is None:
            return

        slot = self._slot_index_from_display(self.export_slot_var.get())
        character = save.characters[slot]
        if not character.name:
            CTkMessageBox.showerror(
                t("Error"),
                t("Slot {slot} is empty.").format(slot=slot),
                parent=self.parent,
            )
            return

        save_path = self.get_save_path()
        initialdir = str(Path(save_path).parent) if save_path else None
        output_path = pick_file(
            title=t("Export Character"),
            initialdir=initialdir,
            filetypes=_DS2_FILETYPES,
            save=True,
            defaultextension=".ds2c",
            initialfile=f"{character.name}.ds2c",
        )
        if not output_path:
            return

        try:
            DS2CharacterOperations.export_character(save, slot, output_path)
        except Exception as e:
            CTkMessageBox.showerror(
                t("Error"), t("Export failed:\n{e}").format(e=e), parent=self.parent
            )
            return

        CTkMessageBox.showinfo(
            t("Success"),
            t("Character '{name}' exported to:\n{output_path}").format(
                name=character.name, output_path=output_path
            ),
            parent=self.parent,
        )

    def _import_character(self) -> None:
        if not self._check_game_not_running():
            return
        save = self._require_save()
        if save is None:
            return

        save_path = self.get_save_path()
        initialdir = str(Path(save_path).parent) if save_path else None
        input_path = pick_file(
            title=t("Import Character"), initialdir=initialdir, filetypes=_DS2_FILETYPES
        )
        if not input_path:
            return

        to_slot = self._slot_index_from_display(self.import_slot_var.get())
        to_name = save.characters[to_slot].name
        if to_name and not CTkMessageBox.askyesno(
            t("Overwrite?"),
            t("Slot {to_slot} contains '{to_name}'.\n\nOverwrite?").format(
                to_slot=to_slot, to_name=to_name
            ),
            parent=self.parent,
        ):
            return

        try:
            self._backup(
                save_path, f"before_import_to_slot_{to_slot}", "import_character"
            )
            name = DS2CharacterOperations.import_character(save, to_slot, input_path)
        except RuntimeError as warning:
            if not self._confirm_uninitialized_override(str(warning)):
                return
            name = DS2CharacterOperations.import_character(
                save, to_slot, input_path, force=True
            )
        except Exception as e:
            CTkMessageBox.showerror(
                t("Error"), t("Import failed:\n{e}").format(e=e), parent=self.parent
            )
            return

        self._write_and_reload(save, f"Character '{name}' imported to Slot {to_slot}.")

    def _delete_character(self) -> None:
        if not self._check_game_not_running():
            return
        save = self._require_save()
        if save is None:
            return

        slot = self._slot_index_from_display(self.delete_slot_var.get())
        character = save.characters[slot]
        if not character.name:
            CTkMessageBox.showinfo(
                t("Info"),
                t("Slot {slot} is already empty.").format(slot=slot),
                parent=self.parent,
            )
            return

        name = character.name
        if not CTkMessageBox.askyesno(
            t("Confirm Delete"),
            t(
                "Delete character '{name}' from Slot {slot}?\n\nThis will create a backup first."
            ).format(name=name, slot=slot),
            parent=self.parent,
        ):
            return

        try:
            self._backup(
                self.get_save_path(),
                f"before_delete_{name}_slot_{slot}",
                "delete_character",
            )
            DS2CharacterOperations.delete_slot(save, slot)
        except Exception as e:
            CTkMessageBox.showerror(
                t("Error"), t("Delete failed:\n{e}").format(e=e), parent=self.parent
            )
            return

        save_path = self.get_save_path()
        if save_path:
            save.save_to_file(save_path)
        if self.reload_save:
            self.reload_save()
        self.show_toast(
            t("Character deleted from Slot {slot}.").format(slot=slot), duration=2500
        )

    # ------------------------------------------------------------------
    # Transfer (cross-save, with auto-find)
    # ------------------------------------------------------------------

    def _browse_target_save_manually(self) -> str | None:
        save_path = self.get_save_path()
        initialdir = str(Path(save_path).parent) if save_path else None
        return pick_file(
            title=t("Select target save file"),
            initialdir=initialdir,
            filetypes=_SAVE_FILETYPES,
        )

    def _select_target_save_file(self) -> str | None:
        """Auto-find DS2 saves in common locations, offer a picker with a
        manual browse fallback, same pattern as the ER management tab."""
        profile = PROFILES_BY_KEY["dark_souls_2"]
        found_saves = find_save_paths(profile)

        current_path = self.get_save_path()
        if current_path:
            current_resolved = Path(current_path).resolve()
            found_saves = [p for p in found_saves if p.resolve() != current_resolved]

        if found_saves:
            return SaveSelectorDialog.show(
                self.parent,
                found_saves,
                lambda path: None,
                browse_callback=self._browse_target_save_manually,
                browse_button_text="Browse Manually",
            )
        return self._browse_target_save_manually()

    def _select_target_slot(self, target_save: DS2Save, target_path: str) -> int | None:
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Select Target Slot")
        dialog.geometry("520x220")
        force_render_dialog(dialog)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=t("Select destination slot in target save:"),
            font=("Segoe UI", 12),
        ).pack(padx=10, pady=(12, 6))
        ctk.CTkLabel(
            dialog,
            text=str(target_path),
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
            wraplength=480,
        ).pack(padx=10, pady=(0, 10))

        names = self._slot_display_names(target_save)
        slot_var = tk.StringVar(value=names[0])
        ctk.CTkComboBox(
            dialog, variable=slot_var, values=names, state="readonly", width=360
        ).pack(pady=(0, 12))

        result = {"value": None}

        def confirm():
            result["value"] = self._slot_index_from_display(slot_var.get())
            dialog.destroy()

        ctk.CTkButton(dialog, text=t("Transfer"), command=confirm, width=140).pack(
            pady=(0, 12)
        )
        dialog.bind("<Return>", lambda _e: confirm())
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        dialog.wait_window()
        return result["value"]

    def _transfer_character(self) -> None:
        if not self._check_game_not_running():
            return
        save = self._require_save()
        if save is None:
            return

        from_slot = self._slot_index_from_display(self.transfer_from_var.get())
        from_character = save.characters[from_slot]
        if not from_character.name:
            CTkMessageBox.showerror(
                t("Error"),
                t("Slot {from_slot} is empty.").format(from_slot=from_slot),
                parent=self.parent,
            )
            return

        target_path = self._select_target_save_file()
        if not target_path:
            return

        current_path = self.get_save_path()
        if current_path and Path(target_path).resolve() == Path(current_path).resolve():
            CTkMessageBox.showerror(
                t("Error"),
                t("Select a different target save file."),
                parent=self.parent,
            )
            return

        try:
            target_save = DS2Save.from_file(target_path)
        except Exception as e:
            CTkMessageBox.showerror(
                t("Error"),
                t("Failed to load target save:\n{e}").format(e=e),
                parent=self.parent,
            )
            return

        to_slot = self._select_target_slot(target_save, target_path)
        if to_slot is None:
            return

        try:
            self._backup(
                current_path,
                f"before_transfer_slot_{from_slot}_to_other_save",
                "transfer_character",
            )
            self._backup(
                target_path,
                f"before_receive_character_to_slot_{to_slot}",
                "receive_character",
            )
            DS2CharacterOperations.transfer_slot(save, from_slot, target_save, to_slot)
        except RuntimeError as warning:
            if not self._confirm_uninitialized_override(str(warning)):
                return
            DS2CharacterOperations.transfer_slot(
                save, from_slot, target_save, to_slot, force=True
            )
        except Exception as e:
            CTkMessageBox.showerror(
                t("Error"), t("Transfer failed:\n{e}").format(e=e), parent=self.parent
            )
            return

        target_save.save_to_file(target_path)
        if self.reload_save:
            self.reload_save()
        self.show_toast(
            t(
                "Character transferred to Slot {to_slot} in target save. {stale_summary_note}"
            ).format(to_slot=to_slot, stale_summary_note=STALE_SUMMARY_NOTE),
            duration=4000,
        )
