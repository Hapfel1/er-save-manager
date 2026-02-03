"""
Gestures Tab
View and unlock gestures
"""

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.data.gestures import (
    get_all_unlockable_gestures,
    get_gesture_name,
    is_cut_content,
    is_dlc_gesture,
)
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


class GesturesRegionsTab:
    """Tab for viewing and unlocking gestures"""

    def __init__(
        self, parent, get_save_file_callback, get_save_path_callback, reload_callback
    ):
        """
        Initialize gestures tab

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_save_path_callback: Function that returns save file path
            reload_callback: Function to reload save file
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback

        self.gesture_slot_var = None
        self.current_slot = None
        self.gesture_states = {}
        self._initial_unlocked: set[int] = set()
        self.gestures_inner_frame = None

    def setup_ui(self):
        """Setup the gestures tab UI"""
        # Main scrollable container
        main_frame = ctk.CTkScrollableFrame(self.parent, corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(main_frame)

        # Header
        ctk.CTkLabel(
            main_frame,
            text="Gestures",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(15, 5), padx=15, anchor="w")

        ctk.CTkLabel(
            main_frame,
            text="View and manage unlocked gestures",
            font=("Segoe UI", 11),
            text_color=("#808080", "#a0a0a0"),
        ).pack(pady=(0, 15), padx=15, anchor="w")

        # Slot selector frame
        slot_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        slot_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        ctk.CTkLabel(slot_frame, text="Character Slot:", font=("Segoe UI", 11)).pack(
            side=tk.LEFT, padx=(12, 8), pady=12
        )

        self.gesture_slot_var = tk.IntVar(value=1)
        slot_combo = ctk.CTkComboBox(
            slot_frame,
            variable=self.gesture_slot_var,
            values=list(map(str, range(1, 11))),
            width=80,
            state="readonly",
        )
        slot_combo.pack(side=tk.LEFT, padx=(0, 10), pady=12)

        ctk.CTkButton(
            slot_frame,
            text="Load",
            command=self.load_gestures,
            width=90,
        ).pack(side=tk.LEFT, pady=12, padx=(0, 12))

        # Gestures frame
        gestures_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        gestures_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        ctk.CTkLabel(
            gestures_frame,
            text="Gestures",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(12, 8), padx=12, anchor="w")

        # Scrollable gestures list
        self.gestures_inner_frame = ctk.CTkScrollableFrame(
            gestures_frame, corner_radius=8, fg_color=("#f5f5f5", "#2a2a3e")
        )
        self.gestures_inner_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        bind_mousewheel(self.gestures_inner_frame)

        # Gesture action buttons
        gesture_buttons = ctk.CTkFrame(gestures_frame, fg_color="transparent")
        gesture_buttons.pack(fill=tk.X, pady=(0, 12), padx=12)

        ctk.CTkButton(
            gesture_buttons,
            text="Apply Changes",
            command=self.apply_gesture_changes,
            width=140,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            gesture_buttons,
            text="Select All Base",
            command=lambda: self.select_all_gestures("base"),
            width=140,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            gesture_buttons,
            text="Select All + DLC",
            command=lambda: self.select_all_gestures("all"),
            width=140,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            gesture_buttons,
            text="Deselect All",
            command=self.deselect_all_gestures,
            width=120,
        ).pack(side=tk.LEFT)

    def load_gestures(self):
        """Load gestures for selected character"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        try:
            slot_idx = int(self.gesture_slot_var.get()) - 1
        except (ValueError, AttributeError):
            CTkMessageBox.showwarning(
                "Invalid Slot", "Please select a valid slot!", parent=self.parent
            )
            return

        if slot_idx < 0 or slot_idx >= 10:
            CTkMessageBox.showwarning(
                "Invalid Slot", "Slot must be between 1 and 10!", parent=self.parent
            )
            return

        slot = save_file.characters[slot_idx]

        if slot.is_empty():
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {slot_idx + 1} is empty!", parent=self.parent
            )
            return

        self.current_slot = slot_idx

        # Clear previous gesture checkboxes
        for widget in self.gestures_inner_frame.winfo_children():
            widget.destroy()
        self.gesture_states.clear()

        # Get all possible gestures
        all_gestures = get_all_unlockable_gestures(include_cut_content=False)
        unlocked_gesture_ids = set()

        if hasattr(slot, "gestures") and slot.gestures:
            unlocked_gesture_ids = {
                g for g in slot.gestures.gesture_ids if g != 0 and g != 0xFFFFFFFF
            }

        # Create checkboxes for all gestures
        for gesture_id in sorted(all_gestures):
            name = get_gesture_name(gesture_id)
            dlc = " [DLC]" if is_dlc_gesture(gesture_id) else ""
            cut = " [CUT]" if is_cut_content(gesture_id) else ""

            var = tk.BooleanVar(value=(gesture_id in unlocked_gesture_ids))
            self.gesture_states[gesture_id] = var

            checkbox = ctk.CTkCheckBox(
                self.gestures_inner_frame,
                text=f"{name}{dlc}{cut}",
                variable=var,
                onvalue=True,
                offvalue=False,
            )
            checkbox.pack(anchor="w", pady=4, padx=8)

        # Remember initial unlocked set for delta calculation on apply
        self._initial_unlocked = set(unlocked_gesture_ids)

        CTkMessageBox.showinfo(
            "Loaded",
            f"Loaded {len(self.gesture_states, parent=self.parent)} gestures for Slot {slot_idx + 1}.",
        )

    def apply_gesture_changes(self):
        """Apply individual gesture changes"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        if self.current_slot is None:
            CTkMessageBox.showwarning(
                "No Slot", "Please load a character slot first!", parent=self.parent
            )
            return

        slot_idx = self.current_slot
        slot = save_file.characters[slot_idx]

        if slot.is_empty():
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {slot_idx + 1} is empty!", parent=self.parent
            )
            return

        selected_set = {gid for gid, var in self.gesture_states.items() if var.get()}
        # Compute intended changes vs original state
        to_unlock = selected_set - self._initial_unlocked
        to_lock = self._initial_unlocked - selected_set
        selected_gestures = sorted(selected_set)

        if not CTkMessageBox.askyesno(
            "Apply Changes",
            (
                f"Apply gesture changes to Slot {slot_idx + 1}?\n"
                f"{len(to_unlock, parent=self.parent)} gesture(s) will be unlocked"
                + (f" and {len(to_lock)} locked" if to_lock else "")
                + ".\n\nA backup will be created."
            ),
        ):
            return

        try:
            if isinstance(save_file._raw_data, bytes):
                save_file._raw_data = bytearray(save_file._raw_data)

            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_gesture_changes_slot_{slot_idx + 1}",
                    operation=f"gesture_changes_slot_{slot_idx + 1}",
                    save=save_file,
                )

            selected_gestures_sorted = sorted(selected_gestures)
            new_gesture_ids = selected_gestures_sorted + [0] * (
                64 - len(selected_gestures_sorted)
            )
            new_gesture_ids = new_gesture_ids[:64]

            if len(new_gesture_ids) != 64:
                CTkMessageBox.showerror(
                    "Error",
                    f"Invalid gesture count: {len(new_gesture_ids, parent=self.parent)} (expected 64)",
                )
                return

            slot.gestures.gesture_ids = new_gesture_ids

            if not hasattr(slot, "gestures_offset") or slot.gestures_offset < 0:
                CTkMessageBox.showerror(
                    "Error",
                    "Gesture offset not tracked. Cannot write changes.",
                    parent=self.parent,
                )
                return

            from io import BytesIO

            gesture_bytes = BytesIO()
            slot.gestures.write(gesture_bytes)
            gesture_data = gesture_bytes.getvalue()

            if len(gesture_data) != 256:
                CTkMessageBox.showerror(
                    "Error",
                    f"Invalid gesture data size: {len(gesture_data, parent=self.parent)} bytes (expected 256)",
                )
                return

            slot_offset = save_file._slot_offsets[slot_idx]
            CHECKSUM_SIZE = 0x10
            abs_offset = slot_offset + CHECKSUM_SIZE + slot.gestures_offset

            save_file._raw_data[abs_offset : abs_offset + len(gesture_data)] = (
                gesture_data
            )

            save_file.recalculate_checksums()
            save_file.to_file(save_path)

            CTkMessageBox.showinfo(
                "Success",
                (
                    f"Applied changes to Slot {slot_idx + 1}:\n"
                    f"Unlocked {len(to_unlock)}"
                    + (f", locked {len(to_lock)}" if to_lock else "")
                    + "."
                ),
                parent=self.parent,
            )

            if self.reload_save:
                self.reload_save()
            self.load_gestures()

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to apply changes:\n{str(e, parent=self.parent)}"
            )

    def select_all_gestures(self, select_type: str):
        """
        Select all gestures by checking all boxes

        Args:
            select_type: "base" for base game only, "all" for base + DLC
        """
        if self.current_slot is None:
            CTkMessageBox.showwarning(
                "No Slot", "Please load a character slot first!", parent=self.parent
            )
            return

        include_dlc = select_type == "all"

        for gesture_id, var in self.gesture_states.items():
            if include_dlc or not is_dlc_gesture(gesture_id):
                var.set(True)

        CTkMessageBox.showinfo(
            "Gestures Selected",
            f"All {'base game + DLC' if include_dlc else 'base game'} gestures selected.\n"
            f"Click 'Apply Changes' to save.",
            parent=self.parent,
        )

    def deselect_all_gestures(self):
        """Deselect all gestures"""
        if self.current_slot is None:
            CTkMessageBox.showwarning(
                "No Slot", "Please load a character slot first!", parent=self.parent
            )
            return

        for var in self.gesture_states.values():
            var.set(False)

        CTkMessageBox.showinfo(
            "Gestures Deselected", "All gestures deselected.", parent=self.parent
        )
