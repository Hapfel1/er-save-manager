"""World State tab - Optimized two-column layout with 1041 locations."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from er_save_manager.backup.manager import BackupManager
from er_save_manager.data.locations import get_all_locations_sorted
from er_save_manager.editors.world_state import WorldStateEditor
from er_save_manager.parser.er_types import FloatVector3, MapId

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
        self.teleport_mode = tk.StringVar(value="known")

        # Slot selection
        self.slot_var = tk.IntVar(value=0)

    def setup_ui(self):
        """Create two-column layout."""
        # Main container with two columns
        main_container = ttk.Frame(self.parent)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure grid weights
        main_container.columnconfigure(0, weight=1, minsize=300)
        main_container.columnconfigure(1, weight=2, minsize=500)
        main_container.rowconfigure(0, weight=1)

        # === LEFT COLUMN: Character Info ===
        left_frame = ttk.Frame(main_container)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Character Slot Selector
        slot_frame = ttk.LabelFrame(left_frame, text="Character Slot", padding="10")
        slot_frame.pack(fill=tk.X, pady=(0, 10))

        slot_select = ttk.Frame(slot_frame)
        slot_select.pack(fill=tk.X)

        ttk.Label(slot_select, text="Slot:").pack(side=tk.LEFT, padx=(0, 5))

        slot_combo = ttk.Combobox(
            slot_select,
            textvariable=self.slot_var,
            values=list(range(1, 11)),
            state="readonly",
            width=8,
        )
        slot_combo.pack(side=tk.LEFT, padx=(0, 10))
        slot_combo.current(0)

        ttk.Button(
            slot_select, text="Load", command=self._load_character, width=10
        ).pack(side=tk.LEFT)

        # Current Location Display
        location_frame = ttk.LabelFrame(
            left_frame, text="Current Location", padding="10"
        )
        location_frame.pack(fill=tk.BOTH, expand=True)

        # Map
        map_frame = ttk.Frame(location_frame)
        map_frame.pack(fill=tk.X, pady=5)
        ttk.Label(
            map_frame,
            text="Map:",
            width=10,
            anchor="w",
            font=("TkDefaultFont", 9, "bold"),
        ).pack(anchor="w")
        self.map_name_var = tk.StringVar(value="No character loaded")
        map_label = ttk.Label(
            map_frame, textvariable=self.map_name_var, wraplength=250, justify="left"
        )
        map_label.pack(fill=tk.X, pady=(2, 0))

        ttk.Separator(location_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Coordinates
        coords_frame = ttk.Frame(location_frame)
        coords_frame.pack(fill=tk.X, pady=5)
        ttk.Label(
            coords_frame,
            text="Coordinates:",
            anchor="w",
            font=("TkDefaultFont", 9, "bold"),
        ).pack(anchor="w")
        self.coords_var = tk.StringVar(value="N/A")
        ttk.Label(coords_frame, textvariable=self.coords_var, wraplength=250).pack(
            fill=tk.X, pady=(2, 0)
        )

        ttk.Separator(location_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Bloodstain
        bloodstain_frame = ttk.Frame(location_frame)
        bloodstain_frame.pack(fill=tk.X, pady=5)
        ttk.Label(
            bloodstain_frame,
            text="Bloodstain:",
            anchor="w",
            font=("TkDefaultFont", 9, "bold"),
        ).pack(anchor="w")
        self.bloodstain_var = tk.StringVar(value="N/A")
        ttk.Label(
            bloodstain_frame, textvariable=self.bloodstain_var, wraplength=250
        ).pack(fill=tk.X, pady=(2, 0))

        # === RIGHT COLUMN: Teleportation ===
        right_frame = ttk.LabelFrame(main_container, text="Teleportation", padding="10")
        right_frame.grid(row=0, column=1, sticky="nsew")

        # Mode Selection
        mode_frame = ttk.Frame(right_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Radiobutton(
            mode_frame,
            text="Known Locations",
            variable=self.teleport_mode,
            value="known",
            command=self._on_mode_changed,
        ).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Radiobutton(
            mode_frame,
            text="Custom Map ID + Coordinates",
            variable=self.teleport_mode,
            value="custom",
            command=self._on_mode_changed,
        ).pack(side=tk.LEFT)

        # Content container for mode-specific UI
        self.content_frame = ttk.Frame(right_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Build initial UI
        self._on_mode_changed()

    def _load_character(self):
        """Load selected character and refresh display."""
        save = self.get_save_file()
        if not save:
            messagebox.showwarning("No Save", "Please load a save file first")
            return

        slot_idx = self.slot_var.get() - 1  # Convert 1-10 to 0-9

        # Check if slot is valid
        if slot_idx < 0 or slot_idx >= 10:
            messagebox.showerror(
                "Invalid Slot", "Please select a valid character slot (1-10)"
            )
            return

        # Check if slot is empty
        slot = save.character_slots[slot_idx]
        if slot.is_empty():
            messagebox.showwarning(
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

        messagebox.showinfo(
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
        search_frame = ttk.Frame(self.content_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(search_frame, text="Search:", font=("TkDefaultFont", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search_changed)
        search_entry = ttk.Entry(
            search_frame, textvariable=self.search_var, font=("TkDefaultFont", 10)
        )
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # Count label
        self.count_label = ttk.Label(
            search_frame,
            text=f"{len(self.filtered_locations)} / {len(self.all_locations_sorted)}",
            font=("TkDefaultFont", 9),
        )
        self.count_label.pack(side=tk.LEFT)

        # Listbox with scrollbar - larger height for right column
        listbox_frame = ttk.Frame(self.content_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.location_listbox = tk.Listbox(
            listbox_frame,
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
            font=("Consolas", 9),
            height=20,
        )
        self.location_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.location_listbox.yview)

        self._update_location_list()

        # Teleport button - closer to list
        ttk.Button(
            self.content_frame,
            text="Teleport to Selected Location",
            command=self._teleport_to_known,
        ).pack(pady=8)

    def _build_custom_teleport_ui(self):
        """Build custom teleport UI."""
        # Warning
        ttk.Label(
            self.content_frame,
            text="⚠ Advanced: Invalid coordinates may corrupt your save!",
            foreground="red",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(pady=(0, 20))

        # Map ID
        map_frame = ttk.LabelFrame(self.content_frame, text="Map ID", padding="10")
        map_frame.pack(fill=tk.X, pady=(0, 15))

        id_entry_frame = ttk.Frame(map_frame)
        id_entry_frame.pack(fill=tk.X)

        self.map_id_var = tk.StringVar()
        ttk.Entry(
            id_entry_frame,
            textvariable=self.map_id_var,
            font=("TkDefaultFont", 11),
            width=30,
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(
            id_entry_frame,
            text="Format: m60_42_36_00 or 60 42 36 00 (decimal)",
            font=("TkDefaultFont", 9),
        ).pack(side=tk.LEFT)

        # Coordinates
        coords_frame = ttk.LabelFrame(
            self.content_frame, text="Coordinates (Optional)", padding="10"
        )
        coords_frame.pack(fill=tk.X, pady=(0, 15))

        # Info label
        ttk.Label(
            coords_frame,
            text="Leave empty to keep current position, or specify X/Y/Z to teleport to exact coordinates",
            font=("TkDefaultFont", 8),
            foreground="gray",
        ).pack(pady=(0, 5))

        coords_grid = ttk.Frame(coords_frame)
        coords_grid.pack()

        # X
        ttk.Label(coords_grid, text="X:", font=("TkDefaultFont", 10)).grid(
            row=0, column=0, padx=(0, 5), sticky="e"
        )
        self.custom_x_var = tk.StringVar(value="0.0")
        ttk.Entry(
            coords_grid,
            textvariable=self.custom_x_var,
            width=15,
            font=("TkDefaultFont", 10),
        ).grid(row=0, column=1, padx=5)

        # Y
        ttk.Label(coords_grid, text="Y:", font=("TkDefaultFont", 10)).grid(
            row=0, column=2, padx=(20, 5), sticky="e"
        )
        self.custom_y_var = tk.StringVar(value="0.0")
        ttk.Entry(
            coords_grid,
            textvariable=self.custom_y_var,
            width=15,
            font=("TkDefaultFont", 10),
        ).grid(row=0, column=3, padx=5)

        # Z
        ttk.Label(coords_grid, text="Z:", font=("TkDefaultFont", 10)).grid(
            row=0, column=4, padx=(20, 5), sticky="e"
        )
        self.custom_z_var = tk.StringVar(value="0.0")
        ttk.Entry(
            coords_grid,
            textvariable=self.custom_z_var,
            width=15,
            font=("TkDefaultFont", 10),
        ).grid(row=0, column=5, padx=5)

        # Teleport button
        ttk.Button(
            self.content_frame,
            text="Teleport to Custom Location",
            command=self._teleport_to_custom,
        ).pack(pady=30)

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
        self.count_label.config(
            text=f"{len(self.filtered_locations)} / {len(self.all_locations_sorted)}"
        )

    def _update_location_list(self):
        """Update listbox with filtered locations."""
        self.location_listbox.delete(0, tk.END)
        for _key, location in self.filtered_locations:
            dlc_tag = " (DLC)" if location.is_dlc else ""
            self.location_listbox.insert(tk.END, f"{location.display_name}{dlc_tag}")

    def _teleport_to_known(self):
        """Teleport to selected known location."""
        if not self.editor:
            messagebox.showerror(
                "Error", "Please load a character first (select slot and click Load)"
            )
            return

        selection_idx = self.location_listbox.curselection()
        if not selection_idx:
            messagebox.showerror("Error", "Please select a location from the list")
            return

        location_key, location = self.filtered_locations[selection_idx[0]]

        # DLC warning
        if location.is_dlc:
            save = self.get_save_file()
            slot_idx = self.slot_var.get() - 1
            slot = save.character_slots[slot_idx]

            if not slot.has_dlc_flag():
                if not messagebox.askyesno(
                    "DLC Location Warning",
                    f"{location.short_display_name}\n\nThis is a DLC location.\n"
                    "Your character has not entered the DLC yet.\n\n"
                    "Teleporting may cause issues.\n\n"
                    "Continue anyway?",
                    icon="warning",
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
                messagebox.showinfo("Success", f"✓ {message}")
                self.reload_save()
                self.refresh()
        else:
            messagebox.showerror("Error", message)

    def _teleport_to_custom(self):
        """Teleport to custom map ID + coordinates."""
        if not self.editor:
            messagebox.showerror("Error", "Please load a character first")
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
            messagebox.showerror(
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
            messagebox.showerror(
                "Error", "Invalid coordinates - must be numeric values"
            )
            return

        # DLC warning
        dlc_warning = ""
        if map_id.is_dlc():
            save = self.get_save_file()
            slot_idx = self.slot_var.get() - 1
            slot = save.character_slots[slot_idx]

            if not slot.has_dlc_flag():
                dlc_warning = "\n\n⚠ WARNING: This is a DLC map!\nYour character has not entered the DLC.\nIf you don't own the dlc you will get stuck in an infinite loading screen!"

        # Confirm
        coords_text = f"Coordinates: X={coords.x}, Y={coords.y}, Z={coords.z}"
        if coords.x == 0.0 and coords.y == 0.0 and coords.z == 0.0:
            coords_text += " ⚠ (World origin - likely not a valid location!)"

        if not messagebox.askyesno(
            "Confirm Custom Teleport",
            f"Custom teleportation can corrupt your save if:\n"
            f"• Map ID is invalid\n"
            f"• Coordinates are out of bounds{dlc_warning}\n\n"
            f"{coords_text}\n\n"
            f"Have you created a backup?\n\n"
            f"Continue with teleport?",
            icon="warning",
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
                messagebox.showinfo("Success", f"✓ {message}")
                self.reload_save()
                self.refresh()
        else:
            messagebox.showerror("Error", message)

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
