"""
Gestures Tab
View and unlock gestures
"""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.data.gestures import (
    get_all_unlockable_gestures,
    get_gesture_name,
    is_cut_content,
    is_dlc_gesture,
)


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
        self.gesture_states = {}  # Track checkbox states {gesture_id: BooleanVar}

    def setup_ui(self):
        """Setup the gestures tab UI"""
        ttk.Label(
            self.parent,
            text="Gestures",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=10)

        info_text = ttk.Label(
            self.parent,
            text="View and manage unlocked gestures",
            font=("Segoe UI", 10),
            foreground="gray",
        )
        info_text.pack(pady=5)

        # Slot selector
        slot_frame = ttk.Frame(self.parent)
        slot_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(slot_frame, text="Character Slot:", font=("Segoe UI", 10)).pack(
            side=tk.LEFT, padx=5
        )

        self.gesture_slot_var = tk.IntVar(value=1)
        slot_combo = ttk.Combobox(
            slot_frame,
            textvariable=self.gesture_slot_var,
            values=list(range(1, 11)),
            state="readonly",
            width=5,
        )
        slot_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            slot_frame,
            text="Load",
            command=self.load_gestures,
            width=15,
        ).pack(side=tk.LEFT, padx=10)

        # Gestures frame
        gestures_frame = ttk.LabelFrame(self.parent, text="Gestures", padding=10)
        gestures_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Gestures canvas with scrollbar for checkboxes
        gestures_canvas = tk.Canvas(gestures_frame, highlightthickness=0)
        gestures_scrollbar = ttk.Scrollbar(
            gestures_frame, orient="vertical", command=gestures_canvas.yview
        )
        self.gestures_inner_frame = ttk.Frame(gestures_canvas)

        self.gestures_inner_frame.bind(
            "<Configure>",
            lambda e: gestures_canvas.configure(
                scrollregion=gestures_canvas.bbox("all")
            ),
        )

        gestures_canvas.create_window(
            (0, 0), window=self.gestures_inner_frame, anchor="nw"
        )
        gestures_canvas.configure(yscrollcommand=gestures_scrollbar.set)

        gestures_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        gestures_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mousewheel
        def on_mousewheel(event):
            gestures_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        gestures_canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Gesture action buttons
        gesture_buttons = ttk.Frame(gestures_frame)
        gesture_buttons.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            gesture_buttons,
            text="Apply Changes",
            command=self.apply_gesture_changes,
            width=18,
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            gesture_buttons,
            text="Select All Base",
            command=lambda: self.select_all_gestures("base"),
            width=18,
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            gesture_buttons,
            text="Select All + DLC",
            command=lambda: self.select_all_gestures("all"),
            width=18,
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            gesture_buttons,
            text="Deselect All",
            command=self.deselect_all_gestures,
            width=18,
        ).pack(side=tk.LEFT, padx=2)

    def load_gestures(self):
        """Load gestures for selected character"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.gesture_slot_var.get() - 1
        slot = save_file.characters[slot_idx]

        if slot.is_empty():
            messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
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
            # Filter out 0 and 0xFFFFFFFF which are empty slots
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

            cb = ttk.Checkbutton(
                self.gestures_inner_frame,
                text=f"{name}{dlc}{cut}",
                variable=var,
            )
            cb.pack(anchor=tk.W, pady=2, padx=5)

    def apply_gesture_changes(self):
        """Apply individual gesture changes"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        if self.current_slot is None:
            messagebox.showwarning("No Slot", "Please load a character slot first!")
            return

        slot_idx = self.current_slot
        slot = save_file.characters[slot_idx]

        if slot.is_empty():
            messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
            return

        # Get selected gestures and sort them
        selected_gestures = sorted(
            [gesture_id for gesture_id, var in self.gesture_states.items() if var.get()]
        )

        if not messagebox.askyesno(
            "Apply Changes",
            f"Apply gesture changes to Slot {slot_idx + 1}?\n"
            f"{len(selected_gestures)} gestures will be unlocked.\n\n"
            f"A backup will be created.",
        ):
            return

        try:
            # Ensure raw_data is mutable
            if isinstance(save_file._raw_data, bytes):
                save_file._raw_data = bytearray(save_file._raw_data)

            # Create backup
            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_gesture_changes_slot_{slot_idx + 1}",
                    operation=f"gesture_changes_slot_{slot_idx + 1}",
                    save=save_file,
                )

            # Update gesture IDs - must be exactly 64 slots, sorted
            selected_gestures_sorted = sorted(selected_gestures)
            new_gesture_ids = selected_gestures_sorted + [0] * (
                64 - len(selected_gestures_sorted)
            )
            new_gesture_ids = new_gesture_ids[:64]  # Ensure exactly 64 slots

            # Validate we have exactly 64 entries
            if len(new_gesture_ids) != 64:
                messagebox.showerror(
                    "Error",
                    f"Invalid gesture count: {len(new_gesture_ids)} (expected 64)",
                )
                return

            slot.gestures.gesture_ids = new_gesture_ids

            # Find gesture offset in save file
            if not hasattr(slot, "gestures_offset") or slot.gestures_offset < 0:
                messagebox.showerror(
                    "Error",
                    "Gesture offset not tracked. Cannot write changes.",
                )
                return

            # Write gestures back to raw data
            from io import BytesIO

            gesture_bytes = BytesIO()
            slot.gestures.write(gesture_bytes)
            gesture_data = gesture_bytes.getvalue()

            # Validate gesture data size (should be exactly 256 bytes = 64 * 4)
            if len(gesture_data) != 256:
                messagebox.showerror(
                    "Error",
                    f"Invalid gesture data size: {len(gesture_data)} bytes (expected 256)",
                )
                return

            # Calculate absolute offset
            slot_offset = save_file._slot_offsets[slot_idx]
            CHECKSUM_SIZE = 0x10
            abs_offset = slot_offset + CHECKSUM_SIZE + slot.gestures_offset

            # Write to raw data
            save_file._raw_data[abs_offset : abs_offset + len(gesture_data)] = (
                gesture_data
            )

            # Recalculate checksums and save
            save_file.recalculate_checksums()
            save_file.to_file(save_path)

            messagebox.showinfo(
                "Success",
                f"Applied changes: {len(selected_gestures)} gestures unlocked for Slot {slot_idx + 1}!",
            )

            # Reload display
            self.reload_save()
            self.load_gestures()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply changes:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def select_all_gestures(self, select_type: str):
        """
        Select all gestures by checking all boxes

        Args:
            select_type: "base" for base game only, "all" for base + DLC
        """
        if self.current_slot is None:
            messagebox.showwarning("No Slot", "Please load a character slot first!")
            return

        include_dlc = select_type == "all"

        # Check all appropriate boxes
        for gesture_id, var in self.gesture_states.items():
            if include_dlc or not is_dlc_gesture(gesture_id):
                var.set(True)

        messagebox.showinfo(
            "Gestures Selected",
            f"All {'base game + DLC' if include_dlc else 'base game'} gestures selected.\n"
            f"Click 'Apply Changes' to save.",
        )

    def deselect_all_gestures(self):
        """Deselect all gestures"""
        if self.current_slot is None:
            messagebox.showwarning("No Slot", "Please load a character slot first!")
            return

        for var in self.gesture_states.values():
            var.set(False)

        messagebox.showinfo("Gestures Deselected", "All gestures deselected.")
