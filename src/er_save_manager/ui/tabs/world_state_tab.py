"""World State tab - Optimized two-column layout with 1041 locations (customtkinter version)."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.data.locations import get_all_locations_sorted
from er_save_manager.editors.world_state import WorldStateEditor
from er_save_manager.parser.er_types import FloatVector3, MapId
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

if TYPE_CHECKING:
    pass


class WorldStateTab:
    """UI tab for world state viewing and teleportation."""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_save_path_callback,
        reload_callback,
        selected_slot_callback,
    ):
        """Initialize World State tab."""
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback
        self.get_selected_slot = selected_slot_callback
        self.editor: WorldStateEditor | None = None

        # Location data
        self.all_locations_sorted = get_all_locations_sorted()
        self.filtered_locations = self.all_locations_sorted.copy()

        # Mode selection
        self.teleport_mode = tk.StringVar(
            value="custom"
        )  # Default to custom since known is disabled

        # Slot selection
        self.slot_var = tk.IntVar(value=0)

    def setup_ui(self):
        """Create two-column layout using CTk."""
        # Main scrollable container
        scroll_frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(scroll_frame)

        # Main container with two columns
        main_container = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure grid weights
        main_container.grid_columnconfigure(0, weight=1, minsize=300)
        main_container.grid_columnconfigure(1, weight=2, minsize=500)
        main_container.grid_rowconfigure(0, weight=1)

        # === LEFT COLUMN: Character Info ===
        left_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Character Slot Selector
        slot_frame = ctk.CTkFrame(left_frame, corner_radius=12)
        slot_frame.pack(fill=tk.X, padx=10, pady=10)

        slot_label = ctk.CTkLabel(
            slot_frame,
            text="Character Slot",
            font=("Segoe UI", 12, "bold"),
        )
        slot_label.pack(anchor="w", padx=10, pady=(10, 5))

        slot_select = ctk.CTkFrame(slot_frame, fg_color="transparent")
        slot_select.pack(fill=tk.X, padx=10, pady=(5, 10))

        ctk.CTkLabel(
            slot_select,
            text="Slot:",
        ).pack(side=tk.LEFT, padx=(0, 5))

        slot_combo = ctk.CTkComboBox(
            slot_select,
            variable=self.slot_var,
            values=[str(i) for i in range(1, 11)],
            state="readonly",
            width=80,
        )
        slot_combo.pack(side=tk.LEFT, padx=(0, 10))
        slot_combo.set("1")

        ctk.CTkButton(
            slot_select,
            text="Load",
            command=self._load_character,
            width=80,
        ).pack(side=tk.LEFT)

        # Current Location Display
        location_frame = ctk.CTkFrame(left_frame, corner_radius=12)
        location_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        location_title = ctk.CTkLabel(
            location_frame,
            text="Current Location",
            font=("Segoe UI", 12, "bold"),
        )
        location_title.pack(anchor="w", padx=10, pady=(10, 5))

        # Map
        map_frame = ctk.CTkFrame(location_frame, fg_color="transparent")
        map_frame.pack(fill=tk.X, padx=10, pady=5)

        ctk.CTkLabel(
            map_frame,
            text="Map:",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        self.map_name_var = tk.StringVar(value="No character loaded")
        map_label = ctk.CTkLabel(
            map_frame,
            textvariable=self.map_name_var,
            wraplength=250,
            justify="left",
        )
        map_label.pack(fill=tk.X, pady=(2, 0))

        # Separator
        separator1 = ctk.CTkLabel(map_frame, text="", height=2)
        separator1.pack(fill=tk.X, pady=10)

        # Coordinates
        coords_frame = ctk.CTkFrame(location_frame, fg_color="transparent")
        coords_frame.pack(fill=tk.X, padx=10, pady=5)

        ctk.CTkLabel(
            coords_frame,
            text="Coordinates:",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        self.coords_var = tk.StringVar(value="N/A")
        coords_label = ctk.CTkLabel(
            coords_frame,
            textvariable=self.coords_var,
            wraplength=250,
        )
        coords_label.pack(fill=tk.X, pady=(2, 0))

        # Separator
        separator2 = ctk.CTkLabel(coords_frame, text="", height=2)
        separator2.pack(fill=tk.X, pady=10)

        # Bloodstain
        bloodstain_frame = ctk.CTkFrame(location_frame, fg_color="transparent")
        bloodstain_frame.pack(fill=tk.X, padx=10, pady=5)

        ctk.CTkLabel(
            bloodstain_frame,
            text="Bloodstain:",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        self.bloodstain_var = tk.StringVar(value="N/A")
        bloodstain_label = ctk.CTkLabel(
            bloodstain_frame,
            textvariable=self.bloodstain_var,
            wraplength=250,
        )
        bloodstain_label.pack(fill=tk.X, pady=(2, 0))

        # === RIGHT COLUMN: Teleportation ===
        right_frame = ctk.CTkFrame(main_container, corner_radius=12)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        right_title = ctk.CTkLabel(
            right_frame,
            text="Teleportation",
            font=("Segoe UI", 12, "bold"),
        )
        right_title.pack(anchor="w", padx=10, pady=(10, 5))

        # Mode Selection
        mode_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        mode_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        self.known_locations_radio = ctk.CTkRadioButton(
            mode_frame,
            text="Known Locations (WIP - Temporarily Disabled)",
            variable=self.teleport_mode,
            value="known",
            command=self._on_mode_changed,
            state="disabled",
        )
        self.known_locations_radio.pack(side=tk.LEFT, padx=(0, 20))

        ctk.CTkRadioButton(
            mode_frame,
            text="Custom Map ID + Coordinates",
            variable=self.teleport_mode,
            value="custom",
            command=self._on_mode_changed,
        ).pack(side=tk.LEFT)

        # Content container for mode-specific UI
        self.content_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Build initial UI
        self._on_mode_changed()

    def _load_character(self):
        """Load selected character and refresh display."""
        save = self.get_save_file()
        if not save:
            CTkMessageBox.showwarning("No Save", "Please load a save file first")
            return

        try:
            slot_idx = int(self.slot_var.get()) - 1  # Convert 1-10 to 0-9
        except (ValueError, AttributeError):
            slot_idx = 0

        # Check if slot is valid
        if slot_idx < 0 or slot_idx >= 10:
            CTkMessageBox.showerror(
                "Invalid Slot", "Please select a valid character slot (1-10)"
            )
            return

        # Check if slot is empty
        slot = save.character_slots[slot_idx]
        if slot.is_empty():
            CTkMessageBox.showwarning(
                "Empty Slot", f"Character slot {slot_idx + 1} is empty"
            )
            self.map_name_var.set("Empty slot")
            self.coords_var.set("N/A")
            self.bloodstain_var.set("N/A")
            self.editor = None
            return

        # Create editor
        self.editor = WorldStateEditor(save, slot_idx)

        # Refresh display
        self.refresh()

        CTkMessageBox.showinfo(
            "Loaded", f"Character slot {slot_idx + 1} loaded successfully"
        )

    def _on_mode_changed(self):
        """Switch between modes."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        if self.teleport_mode.get() == "known":
            self._build_known_locations_ui()
        else:
            self._build_custom_teleport_ui()

    def _build_known_locations_ui(self):
        """Build known locations UI - optimized for right column."""
        # Search bar
        search_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        search_frame.pack(fill=tk.X, pady=(0, 5))

        ctk.CTkLabel(
            search_frame,
            text="Search:",
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.search_var = tk.StringVar(value="")
        self.search_var.trace("w", self._on_search_changed)
        search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Type to filter...",
        )
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # Count label
        self.count_label = ctk.CTkLabel(
            search_frame,
            text=f"{len(self.filtered_locations)} / {len(self.all_locations_sorted)}",
            font=("Segoe UI", 11),
        )
        self.count_label.pack(side=tk.LEFT)

        # Teleport button - pack BEFORE listbox to ensure visibility
        ctk.CTkButton(
            self.content_frame,
            text="Teleport to Selected Location",
            command=self._teleport_to_known,
            height=40,
        ).pack(pady=(5, 8), fill=tk.X, padx=5)

        # Listbox with scrollbar - larger height for right column
        listbox_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        scrollbar = ctk.CTkScrollbar(listbox_frame, orientation="vertical")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Use tk.Listbox with theme-aware styling
        self.location_listbox = tk.Listbox(
            listbox_frame,
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
            font=("Consolas", 11),
            height=20,
            bg="#f5f5f5",
            fg="#1f1f28",
            selectbackground="#c9a0dc",
            selectforeground="#1f1f28",
            highlightthickness=0,
        )
        self.location_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.configure(command=self.location_listbox.yview)

        # Update colors based on appearance mode for better theme support
        try:
            if ctk.get_appearance_mode() == "Dark":
                self.location_listbox.config(bg="#1f1f28", fg="#e5e5f5")
            else:
                self.location_listbox.config(bg="#f5f5f5", fg="#1f1f28")
        except Exception:
            pass

        # Bind mousewheel to listbox
        bind_mousewheel(self.location_listbox)

        self._update_location_list()

    def _build_custom_teleport_ui(self):
        """Build custom teleport UI."""
        # Warning
        warning_label = ctk.CTkLabel(
            self.content_frame,
            text="⚠ Advanced: Invalid coordinates may corrupt your save!",
            text_color="#ff6b6b",
            font=("Segoe UI", 10, "bold"),
        )
        warning_label.pack(pady=(0, 20))

        # Map ID
        map_frame = ctk.CTkFrame(self.content_frame, corner_radius=12)
        map_frame.pack(fill=tk.X, padx=0, pady=(0, 15))

        map_title = ctk.CTkLabel(
            map_frame,
            text="Map ID",
            font=("Segoe UI", 11, "bold"),
        )
        map_title.pack(anchor="w", padx=10, pady=(10, 5))

        id_entry_frame = ctk.CTkFrame(map_frame, fg_color="transparent")
        id_entry_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        self.map_id_var = tk.StringVar(value="")
        map_entry = ctk.CTkEntry(
            id_entry_frame,
            textvariable=self.map_id_var,
            placeholder_text="e.g., m60_42_36_00",
            width=250,
        )
        map_entry.pack(side=tk.LEFT, padx=(0, 10))

        format_label = ctk.CTkLabel(
            id_entry_frame,
            text="Format: m60_42_36_00 or 60 42 36 00",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        )
        format_label.pack(side=tk.LEFT)

        # Coordinates
        coords_frame = ctk.CTkFrame(self.content_frame, corner_radius=12)
        coords_frame.pack(fill=tk.X, padx=0, pady=(0, 15))

        coords_title = ctk.CTkLabel(
            coords_frame,
            text="Coordinates (Optional)",
            font=("Segoe UI", 11, "bold"),
        )
        coords_title.pack(anchor="w", padx=10, pady=(10, 5))

        # Info label
        info_label = ctk.CTkLabel(
            coords_frame,
            text="Leave empty or use 0.0 to keep current position",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        )
        info_label.pack(padx=10, pady=(0, 10))

        coords_grid = ctk.CTkFrame(coords_frame, fg_color="transparent")
        coords_grid.pack(padx=10, pady=(0, 10))

        # X
        ctk.CTkLabel(coords_grid, text="X:").grid(
            row=0, column=0, padx=(0, 5), sticky="e"
        )
        self.custom_x_var = tk.StringVar(value="0.0")
        ctk.CTkEntry(
            coords_grid,
            textvariable=self.custom_x_var,
            width=100,
            placeholder_text="0.0",
        ).grid(row=0, column=1, padx=5)

        # Y
        ctk.CTkLabel(coords_grid, text="Y:").grid(
            row=0, column=2, padx=(20, 5), sticky="e"
        )
        self.custom_y_var = tk.StringVar(value="0.0")
        ctk.CTkEntry(
            coords_grid,
            textvariable=self.custom_y_var,
            width=100,
            placeholder_text="0.0",
        ).grid(row=0, column=3, padx=5)

        # Z
        ctk.CTkLabel(coords_grid, text="Z:").grid(
            row=0, column=4, padx=(20, 5), sticky="e"
        )
        self.custom_z_var = tk.StringVar(value="0.0")
        ctk.CTkEntry(
            coords_grid,
            textvariable=self.custom_z_var,
            width=100,
            placeholder_text="0.0",
        ).grid(row=0, column=5, padx=5)

        # Teleport button
        ctk.CTkButton(
            self.content_frame,
            text="Teleport to Custom Location",
            command=self._teleport_to_custom,
            height=40,
        ).pack(pady=30, fill=tk.X, padx=5)

    def _on_search_changed(self, *args):
        """Filter locations by search text."""
        search_text = self.search_var.get().lower()
        if not search_text:
            self.filtered_locations = self.all_locations_sorted.copy()
        else:
            self.filtered_locations = [
                (key, loc)
                for key, loc in self.all_locations_sorted
                if search_text in loc.display_name.lower()
                or search_text in loc.region.lower()
                or search_text in (loc.grace_name or "").lower()
            ]
        self._update_location_list()
        self.count_label.configure(
            text=f"{len(self.filtered_locations)} / {len(self.all_locations_sorted)}"
        )

    def _update_location_list(self):
        """Update listbox with filtered locations."""
        self.location_listbox.delete(0, tk.END)
        for _key, location in self.filtered_locations:
            dlc_tag = " (DLC)" if location.is_dlc else ""
            # Format: Region - Name - Grace Name - (DLC)
            # Build map code string
            map_str = f"m{location.map_id.data[3]:02d}_{location.map_id.data[2]:02d}_{location.map_id.data[1]:02d}_{location.map_id.data[0]:02d}"

            # Start with region
            display = location.region

            # Add name only if different from region
            if location.name and location.name != location.region:
                display += f" - {location.name}"

            # Add grace name if different from name and not a map code
            # Skip if it looks like a map ID (starts with 'm' followed by digits and underscores)
            is_grace_name_map_code = (
                location.grace_name
                and location.grace_name.startswith("m")
                and "_" in location.grace_name
            )
            if (
                location.grace_name
                and location.grace_name != location.name
                and location.grace_name != location.region
                and not is_grace_name_map_code
            ):
                display += f" - {location.grace_name}"

            # Add map code and DLC tag
            display += f" - {map_str}{dlc_tag}"

            self.location_listbox.insert(tk.END, display)

    def _teleport_to_known(self):
        """Teleport to selected known location."""
        if not self.editor:
            CTkMessageBox.showerror(
                "Error", "Please load a character first (select slot and click Load)"
            )
            return

        selection_idx = self.location_listbox.curselection()
        if not selection_idx:
            CTkMessageBox.showerror("Error", "Please select a location from the list")
            return

        location_key, location = self.filtered_locations[selection_idx[0]]

        # DLC warning
        if location.is_dlc:
            save = self.get_save_file()
            slot_idx = self.slot_var.get() - 1
            slot = save.character_slots[slot_idx]

            # Check if character has DLC access
            has_dlc_access = False
            try:
                if hasattr(slot, "dlc_data"):
                    from er_save_manager.parser.world import DLC

                    dlc = DLC.from_bytes(slot.dlc_data)
                    has_dlc_access = dlc.has_dlc_access()
            except Exception:
                pass

            if not has_dlc_access:
                if not CTkMessageBox.askyesno(
                    "DLC Location Warning",
                    f"{location.short_display_name}\n\nThis is a DLC location.\n"
                    "Your character has not entered the DLC yet.\n\n"
                    "Teleporting may cause issues.\n\n"
                    "Continue anyway?",
                ):
                    return

        # Create backup before teleporting
        save_path = self.get_save_path()
        if save_path:
            manager = BackupManager(Path(save_path))
            manager.create_backup(
                description=f"before_teleport_to_{location_key}",
                operation="world_state_teleport",
                save=self.get_save_file(),
            )

        success, message = self.editor.teleport_to_location(location_key)
        if success:
            save_path = self.get_save_path()
            if save_path:
                # Recalculate checksums before saving
                self.get_save_file().recalculate_checksums()
                self.get_save_file().to_file(save_path)
                CTkMessageBox.showinfo("Success", f"✓ {message}")
                self.reload_save()
                self.refresh()
        else:
            CTkMessageBox.showerror("Error", message)

    def _teleport_to_custom(self):
        """Teleport to custom map ID + coordinates."""
        if not self.editor:
            CTkMessageBox.showerror("Error", "Please load a character first")
            return

        # Parse map ID
        try:
            map_id_input = self.map_id_var.get().strip()

            if not map_id_input:
                raise ValueError("Map ID cannot be empty")

            if map_id_input.startswith("m"):
                # Format: m60_42_36_00 (decimal values separated by underscores)
                parts = map_id_input[1:].split("_")
                if len(parts) != 4:
                    raise ValueError("M-format must be: m##_##_##_##")
                # These are decimal values, parse as ints, reverse order for bytes
                vals = [int(p) for p in parts]
                map_bytes = bytes([vals[3], vals[2], vals[1], vals[0]])
            elif " " in map_id_input:
                # Format with spaces: "60 42 36 00" (decimal values)
                parts = map_id_input.split()
                if len(parts) != 4:
                    raise ValueError("Space-separated format must be: ## ## ## ##")
                # Parse as decimal, reverse order for bytes
                vals = [int(p) for p in parts]
                map_bytes = bytes([vals[3], vals[2], vals[1], vals[0]])
            else:
                # Pure hex format (no spaces): "60423600"
                map_id_hex = map_id_input.replace("-", "").replace("_", "")
                if len(map_id_hex) != 8:
                    raise ValueError(
                        "Hex format must be 8 digits (e.g., 00362A3C for m60_42_36_00)"
                    )
                map_bytes = bytes.fromhex(map_id_hex)

            map_id = MapId(map_bytes)
        except ValueError as e:
            CTkMessageBox.showerror(
                "Invalid Map ID",
                f"{e}\n\n"
                "Valid formats:\n"
                "• m60_42_36_00 (decimal with m prefix)\n"
                "• 60 42 36 00 (decimal with spaces)\n"
                "• 00362A3C (hex, no spaces)",
            )
            return

        # Parse coordinates (optional - use current location if not specified)
        try:
            x_str = self.custom_x_var.get().strip()
            y_str = self.custom_y_var.get().strip()
            z_str = self.custom_z_var.get().strip()

            # If all empty or all 0.0, use current character coordinates
            if (
                (not x_str or x_str == "0.0")
                and (not y_str or y_str == "0.0")
                and (not z_str or z_str == "0.0")
            ):
                # Get current coordinates from character
                location_info = self.editor.get_current_location()
                if location_info["coordinates"]:
                    coords = location_info["coordinates"]
                else:
                    # No current coordinates available, use 0,0,0
                    coords = FloatVector3(0.0, 0.0, 0.0)
            else:
                coords = FloatVector3(
                    float(x_str) if x_str else 0.0,
                    float(y_str) if y_str else 0.0,
                    float(z_str) if z_str else 0.0,
                )
        except ValueError:
            CTkMessageBox.showerror(
                "Error", "Invalid coordinates - must be numeric values"
            )
            return

        # DLC warning
        dlc_warning = ""
        if map_id.is_dlc():
            save = self.get_save_file()
            slot_idx = self.slot_var.get() - 1
            slot = save.character_slots[slot_idx]

            # Check if character has DLC access
            has_dlc_access = False
            try:
                if hasattr(slot, "dlc_data"):
                    from er_save_manager.parser.world import DLC

                    dlc = DLC.from_bytes(slot.dlc_data)
                    has_dlc_access = dlc.has_dlc_access()
            except Exception:
                pass

            if not has_dlc_access:
                dlc_warning = "\n\n⚠ WARNING: This is a DLC map!\nYour character has not entered the DLC.\nIf you don't own the dlc you will get stuck in an infinite loading screen!"

        # Confirm
        coords_text = f"Coordinates: X={coords.x}, Y={coords.y}, Z={coords.z}"
        if coords.x == 0.0 and coords.y == 0.0 and coords.z == 0.0:
            coords_text += " ⚠ (World origin - likely not a valid location!)"

        if not CTkMessageBox.askyesno(
            "Confirm Custom Teleport",
            f"Custom teleportation can corrupt your save if:\n"
            f"• Map ID is invalid\n"
            f"• Coordinates are out of bounds{dlc_warning}\n\n"
            f"{coords_text}\n\n"
            f"Have you created a backup?\n\n"
            f"Continue with teleport?",
        ):
            return

        # Create backup before custom teleporting
        save_path = self.get_save_path()
        if save_path:
            manager = BackupManager(Path(save_path))
            manager.create_backup(
                description="before_custom_teleport",
                operation="world_state_custom_teleport",
                save=self.get_save_file(),
            )

        success, message = self.editor.teleport_to_custom(map_id, coords)
        if success:
            save_path = self.get_save_path()
            if save_path:
                # Recalculate checksums before saving
                self.get_save_file().recalculate_checksums()
                self.get_save_file().to_file(save_path)
                CTkMessageBox.showinfo("Success", f"✓ {message}")
                self.reload_save()
                self.refresh()
        else:
            CTkMessageBox.showerror("Error", message)

    def refresh(self):
        """Refresh location display."""
        if not self.editor:
            self.map_name_var.set("No character loaded")
            self.coords_var.set("N/A")
            self.bloodstain_var.set("N/A")
            return

        location_info = self.editor.get_current_location()

        if location_info["map_name"] == "Empty Slot":
            self.map_name_var.set("Empty slot")
            self.coords_var.set("N/A")
            self.bloodstain_var.set("N/A")
            return

        self.map_name_var.set(location_info["map_name"])

        if location_info["coordinates"]:
            coords = location_info["coordinates"]
            self.coords_var.set(
                f"X: {coords.x:.1f}\nY: {coords.y:.1f}\nZ: {coords.z:.1f}"
            )
        else:
            self.coords_var.set("N/A")

        bloodstain_info = self.editor.get_bloodstain_location()
        if bloodstain_info:
            self.bloodstain_var.set(
                f"{bloodstain_info['map_name']}\n{bloodstain_info['runes']:,} runes"
            )
        else:
            self.bloodstain_var.set("No bloodstain")
