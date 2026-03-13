"""World State tab."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.data.locations import MapLocation, get_all_locations
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
        show_toast_callback,
    ):
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.show_toast = show_toast_callback
        self.reload_save = reload_callback
        self.get_selected_slot = selected_slot_callback
        self.editor: WorldStateEditor | None = None

        self.all_locations: list[MapLocation] = get_all_locations()
        self.filtered_locations: list[MapLocation] = self.all_locations.copy()

        self.teleport_mode = tk.StringVar(value="known")
        self.slot_var = tk.IntVar(value=1)

    def _get_slot_display_names(self) -> list[str]:
        save_file = self.get_save_file()
        if not save_file:
            return [f"{i}" for i in range(1, 11)]

        profiles = None
        try:
            if save_file.user_data_10_parsed:
                profiles = save_file.user_data_10_parsed.profile_summary.profiles
        except Exception:
            pass

        slot_names = []
        for i in range(10):
            char = save_file.characters[i]
            if char.is_empty():
                slot_names.append(f"{i + 1} - Empty")
                continue
            char_name = "Unknown"
            if profiles and i < len(profiles):
                try:
                    char_name = profiles[i].character_name or "Unknown"
                except Exception:
                    pass
            slot_names.append(f"{i + 1} - {char_name}")

        return slot_names

    def refresh_slot_names(self):
        slot_names = self._get_slot_display_names()
        if hasattr(self, "slot_combo"):
            current = self.slot_combo.get()
            self.slot_combo.configure(values=slot_names)
            if current in slot_names:
                self.slot_combo.set(current)
            else:
                self.slot_combo.set(slot_names[0])

    def setup_ui(self):
        scroll_frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(scroll_frame)

        main_container = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        main_container.grid_columnconfigure(0, weight=1, minsize=300)
        main_container.grid_columnconfigure(1, weight=2, minsize=500)
        main_container.grid_rowconfigure(0, weight=1)

        # Left column: character info
        left_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        slot_frame = ctk.CTkFrame(left_frame, corner_radius=12)
        slot_frame.pack(fill=tk.X, padx=10, pady=10)

        ctk.CTkLabel(
            slot_frame, text="Character Slot", font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        slot_select = ctk.CTkFrame(slot_frame, fg_color="transparent")
        slot_select.pack(fill=tk.X, padx=10, pady=(5, 10))

        ctk.CTkLabel(slot_select, text="Slot:").pack(side=tk.LEFT, padx=(0, 5))

        slot_names = self._get_slot_display_names()
        self.slot_combo = ctk.CTkComboBox(
            slot_select,
            values=slot_names,
            width=200,
            state="readonly",
            command=lambda v: self.slot_var.set(int(v.split(" - ")[0])),
        )
        self.slot_combo.set(slot_names[0])
        self.slot_combo.pack(side=tk.LEFT, padx=(0, 10))

        ctk.CTkButton(
            slot_select, text="Load", command=self._load_character, width=80
        ).pack(side=tk.LEFT)

        location_frame = ctk.CTkFrame(left_frame, corner_radius=12)
        location_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        ctk.CTkLabel(
            location_frame, text="Current Location", font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        map_frame = ctk.CTkFrame(location_frame, fg_color="transparent")
        map_frame.pack(fill=tk.X, padx=10, pady=5)
        ctk.CTkLabel(map_frame, text="Map:", font=("Segoe UI", 9, "bold")).pack(
            anchor="w"
        )
        self.map_name_var = tk.StringVar(value="No character loaded")
        ctk.CTkLabel(
            map_frame, textvariable=self.map_name_var, wraplength=250, justify="left"
        ).pack(fill=tk.X, pady=(2, 10))

        coords_frame = ctk.CTkFrame(location_frame, fg_color="transparent")
        coords_frame.pack(fill=tk.X, padx=10, pady=5)
        ctk.CTkLabel(
            coords_frame, text="Coordinates:", font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")
        self.coords_var = tk.StringVar(value="N/A")
        ctk.CTkLabel(coords_frame, textvariable=self.coords_var, wraplength=250).pack(
            fill=tk.X, pady=(2, 10)
        )

        bloodstain_frame = ctk.CTkFrame(location_frame, fg_color="transparent")
        bloodstain_frame.pack(fill=tk.X, padx=10, pady=5)
        ctk.CTkLabel(
            bloodstain_frame, text="Bloodstain:", font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")
        self.bloodstain_var = tk.StringVar(value="N/A")
        ctk.CTkLabel(
            bloodstain_frame, textvariable=self.bloodstain_var, wraplength=250
        ).pack(fill=tk.X, pady=(2, 0))

        # Right column: teleportation
        right_frame = ctk.CTkFrame(main_container, corner_radius=12)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(
            right_frame, text="Teleportation", font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        mode_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        mode_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        ctk.CTkRadioButton(
            mode_frame,
            text="Map Locations",
            variable=self.teleport_mode,
            value="known",
            command=self._on_mode_changed,
        ).pack(side=tk.LEFT, padx=(0, 20))

        ctk.CTkRadioButton(
            mode_frame,
            text="Custom Map ID + Coordinates",
            variable=self.teleport_mode,
            value="custom",
            command=self._on_mode_changed,
        ).pack(side=tk.LEFT)

        self.content_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._on_mode_changed()

    def _load_character(self):
        save = self.get_save_file()
        if not save:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first.", parent=self.parent
            )
            return

        try:
            slot_idx = int(self.slot_var.get()) - 1
        except (ValueError, AttributeError):
            slot_idx = 0

        if not (0 <= slot_idx < 10):
            CTkMessageBox.showerror(
                "Invalid Slot", "Select a slot between 1 and 10.", parent=self.parent
            )
            return

        slot = save.character_slots[slot_idx]
        if slot.is_empty():
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {slot_idx + 1} is empty.", parent=self.parent
            )
            self.map_name_var.set("Empty slot")
            self.coords_var.set("N/A")
            self.bloodstain_var.set("N/A")
            self.editor = None
            return

        self.editor = WorldStateEditor(save, slot_idx)
        self.refresh()
        self.show_toast(f"Slot {slot_idx + 1} loaded.", duration=2500)

    def _reload_editor(self):
        """Recreate editor from the reloaded save so it points to the fresh object."""
        save = self.get_save_file()
        if save is None or self.editor is None:
            return
        # Preserve slot selection across reload
        slot_idx = self.slot_var.get() - 1
        current_combo = self.slot_combo.get() if hasattr(self, "slot_combo") else None
        self.editor = WorldStateEditor(save, slot_idx)
        if current_combo and hasattr(self, "slot_combo"):
            self.slot_combo.set(current_combo)

    def _on_mode_changed(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        if self.teleport_mode.get() == "known":
            self._build_known_locations_ui()
        else:
            self._build_custom_teleport_ui()

    def _build_known_locations_ui(self):
        # Search bar
        search_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        search_frame.pack(fill=tk.X, pady=(0, 5))

        ctk.CTkLabel(search_frame, text="Search:", font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 5)
        )

        self.search_var = tk.StringVar(value="")
        self.search_var.trace_add("write", self._on_search_changed)
        ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Filter locations...",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.count_label = ctk.CTkLabel(
            search_frame,
            text=f"{len(self.filtered_locations)} / {len(self.all_locations)}",
        )
        self.count_label.pack(side=tk.LEFT)

        ctk.CTkButton(
            self.content_frame,
            text="Teleport to Selected Location",
            command=self._teleport_to_known,
            height=40,
        ).pack(pady=(5, 8), fill=tk.X, padx=5)

        listbox_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        scrollbar = ctk.CTkScrollbar(listbox_frame, orientation="vertical")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.location_listbox = tk.Listbox(
            listbox_frame,
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
            font=("Consolas", 11),
            height=20,
            highlightthickness=0,
        )
        self.location_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.configure(command=self.location_listbox.yview)

        try:
            if ctk.get_appearance_mode() == "Dark":
                self.location_listbox.config(
                    bg="#1f1f28",
                    fg="#e5e5f5",
                    selectbackground="#c9a0dc",
                    selectforeground="#1f1f28",
                )
            else:
                self.location_listbox.config(
                    bg="#f5f5f5",
                    fg="#1f1f28",
                    selectbackground="#c9a0dc",
                    selectforeground="#1f1f28",
                )
        except Exception:
            pass

        bind_mousewheel(self.location_listbox)
        self._update_location_list()

    def _on_search_changed(self, *_):
        term = self.search_var.get().lower()
        if term:
            self.filtered_locations = [
                loc
                for loc in self.all_locations
                if term in loc.name.lower() or term in loc.map_id_str
            ]
        else:
            self.filtered_locations = self.all_locations.copy()
        self._update_location_list()
        self.count_label.configure(
            text=f"{len(self.filtered_locations)} / {len(self.all_locations)}"
        )

    def _update_location_list(self):
        self.location_listbox.delete(0, tk.END)
        for loc in self.filtered_locations:
            dlc_tag = " [DLC]" if loc.is_dlc else ""
            self.location_listbox.insert(
                tk.END, f"{loc.map_id_str}  {loc.name}{dlc_tag}"
            )

    def _teleport_to_known(self):
        if not self.editor:
            CTkMessageBox.showerror(
                "Error", "Load a character first.", parent=self.parent
            )
            return

        sel = self.location_listbox.curselection()
        if not sel:
            CTkMessageBox.showerror(
                "Error", "Select a location from the list.", parent=self.parent
            )
            return

        loc = self.filtered_locations[sel[0]]

        if loc.is_dlc:
            save = self.get_save_file()
            slot_idx = self.slot_var.get() - 1
            slot = save.character_slots[slot_idx]
            has_dlc = False
            try:
                if hasattr(slot, "dlc_data"):
                    from er_save_manager.parser.world import DLC

                    has_dlc = DLC.from_bytes(slot.dlc_data).has_dlc_access()
            except Exception:
                pass

            if not has_dlc:
                if not CTkMessageBox.askyesno(
                    "DLC Warning",
                    f"{loc.name}\n\nThis is a DLC location. Teleporting without owning the DLC will cause an infinite loading screen.\n\nContinue?",
                    parent=self.parent,
                ):
                    return

        save_path = self.get_save_path()
        if save_path:
            BackupManager(Path(save_path)).create_backup(
                description=f"before_teleport_{loc.map_id_str}",
                operation="world_state_teleport",
                save=self.get_save_file(),
            )

        success, message = self.editor.teleport_to_map_id(loc.map_id_str)
        if success:
            if save_path:
                self.get_save_file().recalculate_checksums()
                self.get_save_file().to_file(save_path)
                self.reload_save()
                self._reload_editor()
                self.refresh()
            self.show_toast(f"Teleported to {loc.name}", duration=2500)
        else:
            CTkMessageBox.showerror("Error", message, parent=self.parent)

    def _build_custom_teleport_ui(self):
        ctk.CTkLabel(
            self.content_frame,
            text="Advanced: invalid coordinates may corrupt your save!",
            text_color="#ff6b6b",
            font=("Segoe UI", 10, "bold"),
        ).pack(pady=(0, 20))

        map_frame = ctk.CTkFrame(self.content_frame, corner_radius=12)
        map_frame.pack(fill=tk.X, pady=(0, 15))
        ctk.CTkLabel(map_frame, text="Map ID", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", padx=10, pady=(10, 5)
        )
        id_row = ctk.CTkFrame(map_frame, fg_color="transparent")
        id_row.pack(fill=tk.X, padx=10, pady=(5, 10))
        self.map_id_var = tk.StringVar(value="")
        ctk.CTkEntry(
            id_row,
            textvariable=self.map_id_var,
            placeholder_text="e.g. m60_42_36_00",
            width=250,
        ).pack(side=tk.LEFT, padx=(0, 10))
        ctk.CTkLabel(
            id_row,
            text="Format: m60_42_36_00 or 60 42 36 00",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(side=tk.LEFT)

        coords_frame = ctk.CTkFrame(self.content_frame, corner_radius=12)
        coords_frame.pack(fill=tk.X, pady=(0, 15))
        ctk.CTkLabel(
            coords_frame, text="Coordinates (optional)", font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        ctk.CTkLabel(
            coords_frame,
            text="Leave 0.0 to use current coordinates",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(padx=10, pady=(0, 10))

        grid = ctk.CTkFrame(coords_frame, fg_color="transparent")
        grid.pack(padx=10, pady=(0, 10))

        self.custom_x_var = tk.StringVar(value="0.0")
        self.custom_y_var = tk.StringVar(value="0.0")
        self.custom_z_var = tk.StringVar(value="0.0")

        for col, (label, var) in enumerate(
            [
                ("X:", self.custom_x_var),
                ("Y:", self.custom_y_var),
                ("Z:", self.custom_z_var),
            ]
        ):
            ctk.CTkLabel(grid, text=label).grid(
                row=0, column=col * 2, padx=(10 if col else 0, 5), sticky="e"
            )
            ctk.CTkEntry(
                grid, textvariable=var, width=100, placeholder_text="0.0"
            ).grid(row=0, column=col * 2 + 1, padx=5)

        ctk.CTkButton(
            self.content_frame,
            text="Teleport to Custom Location",
            command=self._teleport_to_custom,
            height=40,
        ).pack(pady=30, fill=tk.X, padx=5)

    def _teleport_to_custom(self):
        if not self.editor:
            CTkMessageBox.showerror(
                "Error", "Load a character first.", parent=self.parent
            )
            return

        try:
            raw = self.map_id_var.get().strip()
            if not raw:
                raise ValueError("Map ID cannot be empty")

            if raw.startswith("m"):
                parts = raw[1:].split("_")
                if len(parts) != 4:
                    raise ValueError("Format must be m##_##_##_##")
                vals = [int(p) for p in parts]
                map_bytes = bytes([vals[3], vals[2], vals[1], vals[0]])
            elif " " in raw:
                parts = raw.split()
                if len(parts) != 4:
                    raise ValueError("Space format must be ## ## ## ##")
                vals = [int(p) for p in parts]
                map_bytes = bytes([vals[3], vals[2], vals[1], vals[0]])
            else:
                clean = raw.replace("-", "").replace("_", "")
                if len(clean) != 8:
                    raise ValueError("Hex format must be 8 digits")
                map_bytes = bytes.fromhex(clean)

            map_id = MapId(map_bytes)
        except ValueError as e:
            CTkMessageBox.showerror(
                "Invalid Map ID",
                f"{e}\n\nValid formats:\n  m60_42_36_00\n  60 42 36 00\n  00362A3C (hex)",
                parent=self.parent,
            )
            return

        try:
            x = float(self.custom_x_var.get() or "0")
            y = float(self.custom_y_var.get() or "0")
            z = float(self.custom_z_var.get() or "0")
            if x == 0.0 and y == 0.0 and z == 0.0:
                info = self.editor.get_current_location()
                coords = info["coordinates"] or FloatVector3(0.0, 0.0, 0.0)
            else:
                coords = FloatVector3(x, y, z)
        except ValueError:
            CTkMessageBox.showerror(
                "Error", "Coordinates must be numeric.", parent=self.parent
            )
            return

        dlc_warning = ""
        if map_id.is_dlc():
            dlc_warning = "\n\nThis is a DLC map. Without owning the DLC you will get an infinite loading screen."

        if not CTkMessageBox.askyesno(
            "Confirm Custom Teleport",
            f"Custom teleportation can corrupt your save if the Map ID or coordinates are invalid.{dlc_warning}\n\n"
            f"Coords: X={coords.x}, Y={coords.y}, Z={coords.z}\n\nContinue?",
            parent=self.parent,
        ):
            return

        save_path = self.get_save_path()
        if save_path:
            BackupManager(Path(save_path)).create_backup(
                description="before_custom_teleport",
                operation="world_state_custom_teleport",
                save=self.get_save_file(),
            )

        success, message = self.editor.teleport_to_custom(map_id, coords)
        if success:
            if save_path:
                self.get_save_file().recalculate_checksums()
                self.get_save_file().to_file(save_path)
                self.reload_save()
                self._reload_editor()
                self.refresh()
            self.show_toast(message, duration=2500)
        else:
            CTkMessageBox.showerror("Error", message, parent=self.parent)

    def refresh(self):
        if not self.editor:
            self.map_name_var.set("No character loaded")
            self.coords_var.set("N/A")
            self.bloodstain_var.set("N/A")
            return

        info = self.editor.get_current_location()

        if info["map_name"] == "Empty Slot":
            self.map_name_var.set("Empty slot")
            self.coords_var.set("N/A")
            self.bloodstain_var.set("N/A")
            return

        self.map_name_var.set(info["map_name"])

        if info["coordinates"]:
            c = info["coordinates"]
            self.coords_var.set(f"X: {c.x:.1f}\nY: {c.y:.1f}\nZ: {c.z:.1f}")
        else:
            self.coords_var.set("N/A")

        blood = self.editor.get_bloodstain_location()
        if blood:
            self.bloodstain_var.set(f"{blood['map_name']}\n{blood['runes']:,} runes")
        else:
            self.bloodstain_var.set("No bloodstain")
