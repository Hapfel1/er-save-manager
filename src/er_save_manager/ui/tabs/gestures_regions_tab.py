"""
Gestures Tab
View and unlock gestures
"""

import tkinter as tk
from io import BytesIO
from pathlib import Path

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.data.gestures import (
    get_all_unlockable_gestures,
    get_gesture_name,
    is_cut_content,
    is_dlc_gesture,
)
from er_save_manager.data.regions import REGIONS
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


class GesturesRegionsTab:
    """Tab for viewing and unlocking gestures"""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_save_path_callback,
        reload_callback,
        show_toast_callback,
    ):
        """
        Initialize gestures tab

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_save_path_callback: Function that returns save file path
            reload_callback: Function to reload save file
            show_toast_callback: Function to show toast notifications
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback
        self.show_toast = show_toast_callback

        self.gesture_slot_var = None
        self.current_slot = None
        self.gesture_states = {}
        self._initial_unlocked: set[int] = set()
        self.gestures_inner_frame = None

    def _get_slot_display_names(self):
        """Get display names for all slots"""
        save_file = self.get_save_file()  # or self.save_file depending on class
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
        slot_names = self._get_slot_display_names()

        if hasattr(self, "gesture_slot_combo"):
            self.gesture_slot_combo.configure(values=slot_names)
            self.gesture_slot_combo.set(slot_names[0])

    def setup_ui(self):
        """Setup the gestures tab UI"""
        # Main scrollable container
        main_frame = ctk.CTkScrollableFrame(self.parent, corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(main_frame)

        # Header
        ctk.CTkLabel(
            main_frame,
            text="Gestures & Invasion Regions",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(15, 5), padx=15, anchor="w")

        ctk.CTkLabel(
            main_frame,
            text="View and manage unlocked gestures as well as invasion regions and game settings.",
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
        slot_names = self._get_slot_display_names()
        self.gesture_slot_combo = ctk.CTkComboBox(  # Store reference with self.
            slot_frame,
            values=slot_names,
            width=200,
            state="readonly",
            command=lambda v: self.gesture_slot_var.set(int(v.split(" - ")[0])),
        )
        self.gesture_slot_combo.set(slot_names[0])
        self.gesture_slot_combo.pack(side=tk.LEFT, padx=(0, 10), pady=12)

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

        # Additional tools row
        tools_row = ctk.CTkFrame(main_frame, fg_color="transparent")
        tools_row.pack(fill=tk.X, padx=15, pady=(0, 15))

        ctk.CTkButton(
            tools_row,
            text="Invasion Regions...",
            command=self.open_invasion_regions,
            width=160,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ctk.CTkButton(
            tools_row,
            text="Game Settings...",
            command=self.open_game_settings,
            width=140,
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

        self.show_toast(
            f"Loaded {len(self.gesture_states)} gestures for Slot {slot_idx + 1}",
            duration=2500,
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
                f"{len(to_unlock)} gesture(s) will be unlocked"
                + (f" and {len(to_lock)} locked" if to_lock else "")
                + ".\n\nA backup will be created."
            ),
            parent=self.parent,
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
                    f"Invalid gesture count: {len(new_gesture_ids)} (expected 64)",
                    parent=self.parent,
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
                    f"Invalid gesture data size: {len(gesture_data)} bytes (expected 256)",
                    parent=self.parent,
                )
                return

            # gestures_offset is absolute in the raw file
            abs_offset = slot.gestures_offset

            save_file._raw_data[abs_offset : abs_offset + len(gesture_data)] = (
                gesture_data
            )

            save_file.recalculate_checksums()
            save_file.to_file(save_path)

            if self.reload_save:
                self.reload_save()

            self.show_toast(
                f"Applied changes to Slot {slot_idx + 1}: Unlocked {len(to_unlock)}"
                + (f", locked {len(to_lock)}" if to_lock else ""),
                duration=2500,
            )

            self.load_gestures()

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to apply changes:\n{str(e)}", parent=self.parent
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

        self.show_toast(
            f"All {'base game + DLC' if include_dlc else 'base game'} gestures selected. Click 'Apply Changes' to save.",
            duration=2500,
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

        self.show_toast("All gestures deselected", duration=2000)

    def open_invasion_regions(self):
        """Open invasion regions editor dialog."""
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

        slot = save_file.character_slots[self.current_slot]
        if slot.is_empty():
            CTkMessageBox.showwarning(
                "Empty Slot",
                f"Slot {self.current_slot + 1} is empty!",
                parent=self.parent,
            )
            return

        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Invasion Regions")
        dialog.geometry("640x540")
        dialog.transient(self.parent)
        dialog.update_idletasks()
        self.parent.update_idletasks()
        force_render_dialog(dialog)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Invasion Regions",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(15, 4), padx=15)

        ctk.CTkLabel(
            dialog,
            text="Unlocked map regions stored in the save. Controls which areas appear as available for invasions and blue summons.",
            font=("Segoe UI", 10),
            text_color=("gray50", "gray70"),
            wraplength=580,
        ).pack(pady=(0, 10), padx=15)

        # Current region IDs
        current_ids: list[int] = list(slot.unlocked_regions.region_ids)
        region_vars: dict[int, tk.BooleanVar] = {}

        list_frame = ctk.CTkScrollableFrame(dialog, corner_radius=8)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 8))
        bind_mousewheel(list_frame)

        # Show all known regions as checkboxes; unknown IDs shown at bottom
        known_ids = set(REGIONS.keys())
        unknown_ids = [rid for rid in current_ids if rid not in known_ids]

        for region_id, region_name in sorted(REGIONS.items(), key=lambda x: x[0]):
            var = tk.BooleanVar(value=(region_id in current_ids))
            region_vars[region_id] = var
            ctk.CTkCheckBox(
                list_frame,
                text=f"{region_id}: {region_name}",
                variable=var,
            ).pack(anchor="w", padx=8, pady=2)

        for region_id in unknown_ids:
            var = tk.BooleanVar(value=True)
            region_vars[region_id] = var
            ctk.CTkCheckBox(
                list_frame,
                text=f"{region_id}: (unknown)",
                variable=var,
            ).pack(anchor="w", padx=8, pady=2)

        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        def apply_regions():
            selected = sorted(rid for rid, var in region_vars.items() if var.get())

            save_path = self.get_save_path()
            if not save_path or not save_path.is_file():
                CTkMessageBox.showerror(
                    "Invalid Save Path", "Could not locate save file.", parent=dialog
                )
                return

            try:
                backup_mgr = BackupManager(save_path)
                backup_mgr.create_backup(
                    description=f"Before invasion region edit (Slot {self.current_slot + 1})",
                    operation="invasion_regions",
                    save=save_file,
                )
            except PermissionError:
                CTkMessageBox.showwarning(
                    "Backup Skipped",
                    "Could not create backup (permission denied). Proceeding.",
                    parent=dialog,
                )

            slot.unlocked_regions.region_ids = selected
            slot.unlocked_regions.count = len(selected)

            from er_save_manager.parser.slot_rebuild import rebuild_slot

            rebuilt = rebuild_slot(slot)
            save_file._raw_data[slot.data_start : slot.data_start + len(rebuilt)] = (
                rebuilt
            )
            save_file.recalculate_checksums()
            save_file.save(save_path)
            self.reload_save()

            self.show_toast(f"Saved {len(selected)} region IDs", duration=2500)
            dialog.destroy()

        def select_all():
            for var in region_vars.values():
                var.set(True)

        def deselect_all():
            for var in region_vars.values():
                var.set(False)

        ctk.CTkButton(btn_frame, text="Close", command=dialog.destroy, width=100).pack(
            side=tk.LEFT
        )
        ctk.CTkButton(btn_frame, text="Select All", command=select_all, width=100).pack(
            side=tk.LEFT, padx=6
        )
        ctk.CTkButton(
            btn_frame, text="Deselect All", command=deselect_all, width=110
        ).pack(side=tk.LEFT)
        ctk.CTkButton(btn_frame, text="Apply", command=apply_regions, width=100).pack(
            side=tk.RIGHT
        )

    def open_game_settings(self):
        """Open game settings editor (USER_DATA_10 Settings struct)."""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        if (
            not save_file.user_data_10_parsed
            or not save_file.user_data_10_parsed.settings
        ):
            CTkMessageBox.showerror(
                "Unavailable",
                "Game settings could not be read from this save.",
                parent=self.parent,
            )
            return

        settings = save_file.user_data_10_parsed.settings

        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Game Settings")
        dialog.geometry("520x600")
        dialog.transient(self.parent)
        dialog.update_idletasks()
        self.parent.update_idletasks()
        force_render_dialog(dialog)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Game Settings",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(15, 4), padx=15)

        ctk.CTkLabel(
            dialog,
            text="Stored in USER_DATA_10, shared across all characters.",
            font=("Segoe UI", 10),
            text_color=("gray50", "gray70"),
        ).pack(pady=(0, 10), padx=15)

        scroll = ctk.CTkScrollableFrame(dialog, corner_radius=8)
        scroll.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 8))
        bind_mousewheel(scroll)

        # (label, field_name, min, max)
        fields = [
            ("Brightness", "brightness", 0, 10),
            ("Master Volume", "master_volume", 0, 10),
            ("Music Volume", "music_volume", 0, 10),
            ("Sound Effects Volume", "sound_effects_volume", 0, 10),
            ("Voice Volume", "voice_volume", 0, 10),
            ("Camera Speed", "camera_speed", 0, 10),
            ("Camera X Axis", "camera_x_axis", 0, 1),
            ("Camera Y Axis", "camera_y_axis", 0, 1),
            ("Controller Vibration", "controller_vibration", 0, 1),
            ("Display Blood", "display_blood", 0, 1),
            ("Subtitles", "subtitles", 0, 1),
            ("HUD", "hud", 0, 1),
            ("Toggle Auto Lock-On", "toggle_auto_lockon", 0, 1),
            ("Camera Auto Wall Recovery", "camera_auto_wall_recovery", 0, 1),
            ("Reset Camera Y Axis", "reset_camera_y_axis", 0, 1),
            ("Cinematic Effects", "cinematic_effects", 0, 1),
            ("Perform Matchmaking", "perform_matchmaking", 0, 1),
            ("Manual Attack Aim", "manual_attack_aim", 0, 1),
            ("Autotarget", "autotarget", 0, 1),
            ("Send Summon Sign", "send_summon_sign", 0, 1),
            ("HDR", "hdr", 0, 1),
            ("HDR Adjust Brightness", "hdr_adjust_brightness", 0, 10),
            ("HDR Maximum Brightness", "hdr_maximum_brightness", 0, 10),
            ("HDR Adjust Saturation", "hdr_adjust_saturation", 0, 10),
            ("Ray Tracing", "is_raytracing_on", 0, 1),
            ("Mark New Items", "mark_new_items", 0, 1),
            ("Show Recent Tabs", "show_recent_tabs", 0, 1),
        ]

        vars: dict[str, tk.IntVar] = {}
        for label, field, lo, hi in fields:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill=tk.X, pady=2, padx=4)

            ctk.CTkLabel(row, text=f"{label}:", width=200, anchor="w").pack(
                side=tk.LEFT, padx=(0, 8)
            )
            var = tk.IntVar(value=getattr(settings, field, 0))
            vars[field] = var
            ctk.CTkEntry(row, textvariable=var, width=80).pack(side=tk.LEFT)
            ctk.CTkLabel(
                row,
                text=f"[{lo}–{hi}]",
                text_color=("gray50", "gray70"),
                font=("Segoe UI", 9),
            ).pack(side=tk.LEFT, padx=6)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        def apply_settings():
            save_path = self.get_save_path()
            if not save_path or not save_path.is_file():
                CTkMessageBox.showerror(
                    "Invalid Save Path", "Could not locate save file.", parent=dialog
                )
                return

            try:
                backup_mgr = BackupManager(save_path)
                backup_mgr.create_backup(
                    description="Before game settings edit",
                    operation="game_settings",
                    save=save_file,
                )
            except PermissionError:
                CTkMessageBox.showwarning(
                    "Backup Skipped",
                    "Could not create backup (permission denied). Proceeding.",
                    parent=dialog,
                )

            for field, var in vars.items():
                try:
                    setattr(settings, field, var.get())
                except Exception:
                    pass

            # Write Settings back into _raw_data at its fixed offset.
            # Layout: checksum(16) + version(4) + steam_id(8) + Settings(0x140 with padding)
            ud10_base = save_file._user_data_10_offset
            settings_offset = ud10_base + 16 + 4 + 8  # skip checksum, version, steam_id

            settings_buf = BytesIO()
            settings.write(settings_buf)
            settings_bytes = settings_buf.getvalue()

            # Pad to 0x140 to cover the full Settings region
            padded = settings_bytes + b"\x00" * (0x140 - len(settings_bytes))
            save_file._raw_data[settings_offset : settings_offset + 0x140] = padded[
                :0x140
            ]

            save_file._recalculate_userdata10_checksum()
            save_file.save(save_path)

            self.show_toast("Game settings saved", duration=2500)
            dialog.destroy()

        ctk.CTkButton(btn_frame, text="Close", command=dialog.destroy, width=100).pack(
            side=tk.LEFT
        )
        ctk.CTkButton(btn_frame, text="Apply", command=apply_settings, width=100).pack(
            side=tk.RIGHT
        )
