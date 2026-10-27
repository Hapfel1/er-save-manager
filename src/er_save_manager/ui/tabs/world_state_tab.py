"""World State tab."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.data.locations import (
    MapLocation,
    get_all_locations,
    get_grace_locations,
)
from er_save_manager.data.world_map import MAP_NAMES, location_map_point
from er_save_manager.editors.map_markers import (
    BEACON,
    MARKER,
    MapMarkerEditor,
    copy_markers,
)
from er_save_manager.editors.map_unlock import unlock
from er_save_manager.editors.world_state import WorldStateEditor
from er_save_manager.parser.er_types import FloatVector3, MapId
from er_save_manager.parser.event_flags import EventFlags
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette
from er_save_manager.ui.boss_gate import closed_gate, confirm_teleport, filter_unlock
from er_save_manager.ui.dialogs.message_manager import MessageManagerDialog
from er_save_manager.ui.dialogs.pin_teleport_warning import confirm_pin_teleport
from er_save_manager.ui.map_view import (
    count_phrase,
    current_window,
    open_map_window,
)
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import StageError
from er_save_manager.ui.popups import reopenable
from er_save_manager.ui.utils import bind_mousewheel, patch_combo_scroll, pick_file

if TYPE_CHECKING:
    pass

# Interval at which the UI thread checks for the decoded map thumbnail.
_THUMB_POLL_MS = 50


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
        self.marker_editor: MapMarkerEditor | None = None
        self.marker_editor_slot = 0
        self._maps_dir: Path | None = None  # set via set_maps_dir()

        self._convergence = False
        self.all_locations: list[MapLocation] = (
            get_all_locations() + get_grace_locations()
        )
        self.filtered_locations: list[MapLocation] = self.all_locations.copy()

        self.teleport_mode = tk.StringVar(value="known")
        # 1-based slot of the character picked in the main window's bar
        self.slot_var = tk.IntVar(value=0)
        # Character bar labels and the bar's select function, for the map
        # window's own character picker
        self._slot_labels: list[str] = []
        self.select_character = None
        # Main window's Apply All, for the map window's Apply button
        self.apply_all = None
        # Marker records as loaded, to count the staged changes
        self._marker_snapshot: set[tuple] = set()

    def set_slot_labels(self, labels: list[str]) -> None:
        """Character bar labels, listed in the map window's picker."""
        self._slot_labels = list(labels)
        self._update_map_window()

    def _sync_flavor(self):
        """Use the Convergence locations and map for Convergence saves."""
        save = self.get_save_file()
        convergence = bool(save is not None and save.is_convergence)
        if convergence == self._convergence:
            return
        self._convergence = convergence
        self.all_locations = get_all_locations(convergence) + get_grace_locations(
            convergence
        )
        if getattr(self, "count_label", None) is not None and (
            self.count_label.winfo_exists()
        ):
            self._on_search_changed()
        else:
            self.filtered_locations = self.all_locations.copy()
        window = current_window()
        if window is not None:
            window.set_locations(self.all_locations, convergence)

    def load_slot(self, slot_idx: int) -> None:
        """Load the character in slot_idx; -1 or an empty slot clears the
        tab."""
        self.slot_var.set(slot_idx + 1)
        self._sync_flavor()
        if not hasattr(self, "map_name_var"):
            return
        if slot_idx < 0:
            self.editor = None
            self.marker_editor = None
            self._snapshot_markers()
            self.refresh()
            self._update_map_window()
            return
        self._load_character(quiet=True)

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

        tools_frame = ctk.CTkFrame(left_frame, corner_radius=12)
        tools_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        ctk.CTkLabel(
            tools_frame,
            text="Map markers and item history",
            font=("Inter", 12, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 2))
        self.markers_var = tk.StringVar(value="N/A")
        ds.wrap_to_width(
            ctk.CTkLabel(tools_frame, textvariable=self.markers_var, font=ds.FONT)
        ).pack(fill=tk.X, padx=10, pady=(0, 6))
        buttons = ctk.CTkFrame(tools_frame, fg_color="transparent")
        buttons.pack(fill=tk.X, padx=10, pady=(0, 10))
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            buttons,
            text="Edit Markers on Map",
            command=self._open_map_window,
            height=30,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(
            buttons, text="Item History", command=self._open_item_history, height=30
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        location_frame = ctk.CTkFrame(left_frame, corner_radius=12)
        location_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        ctk.CTkLabel(
            location_frame, text="Current location", font=("Inter", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        map_frame = ctk.CTkFrame(location_frame, fg_color="transparent")
        map_frame.pack(fill=tk.X, padx=10, pady=5)
        ctk.CTkLabel(map_frame, text="Map:", font=ds.BOLD).pack(anchor="w")
        self.map_name_var = tk.StringVar(value="No character loaded")
        ds.wrap_to_width(
            ctk.CTkLabel(map_frame, textvariable=self.map_name_var, font=ds.FONT)
        ).pack(fill=tk.X, pady=(2, 10))

        coords_frame = ctk.CTkFrame(location_frame, fg_color="transparent")
        coords_frame.pack(fill=tk.X, padx=10, pady=5)
        ctk.CTkLabel(coords_frame, text="Coordinates:", font=ds.BOLD).pack(anchor="w")
        self.coords_var = tk.StringVar(value="N/A")
        ds.wrap_to_width(
            ctk.CTkLabel(coords_frame, textvariable=self.coords_var, font=ds.FONT)
        ).pack(fill=tk.X, pady=(2, 10))

        bloodstain_frame = ctk.CTkFrame(location_frame, fg_color="transparent")
        bloodstain_frame.pack(fill=tk.X, padx=10, pady=5)
        ctk.CTkLabel(bloodstain_frame, text="Bloodstain:", font=ds.BOLD).pack(
            anchor="w"
        )
        self.bloodstain_var = tk.StringVar(value="N/A")
        ds.wrap_to_width(
            ctk.CTkLabel(
                bloodstain_frame, textvariable=self.bloodstain_var, font=ds.FONT
            )
        ).pack(fill=tk.X, pady=(2, 4))
        self.bloodstain_btn = ctk.CTkButton(
            bloodstain_frame,
            text="Move Bloodstain to Player",
            command=self._sync_bloodstain_to_player,
            height=30,
        )
        self.bloodstain_btn.pack(fill=tk.X, pady=(0, 2))

        messages_frame = ctk.CTkFrame(left_frame, corner_radius=12)
        messages_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        ctk.CTkLabel(messages_frame, text="Messages", font=("Inter", 12, "bold")).pack(
            anchor="w", padx=10, pady=(10, 5)
        )
        self.messages_var = tk.StringVar(value="N/A")
        ctk.CTkLabel(messages_frame, textvariable=self.messages_var).pack(
            anchor="w", padx=10, pady=(0, 4)
        )
        ctk.CTkButton(
            messages_frame,
            text="Manage Messages...",
            command=self._open_message_manager,
            height=30,
        ).pack(fill=tk.X, padx=10, pady=(0, 10))

        # Right column: teleportation
        right_frame = ctk.CTkFrame(main_container, corner_radius=12)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        def place_columns(event) -> None:
            # Side by side needs both column minimums (300 + 500) plus the
            # paddings; narrower, the teleport column moves below
            stacked = event.width < round(840 * main_container._get_widget_scaling())
            if stacked == (int(right_frame.grid_info()["row"]) == 1):
                return
            main_container.grid_columnconfigure(1, minsize=0 if stacked else 500)
            left_frame.grid_configure(columnspan=2 if stacked else 1)
            right_frame.grid_configure(
                row=1 if stacked else 0,
                column=0 if stacked else 1,
                columnspan=2 if stacked else 1,
            )

        main_container.bind("<Configure>", place_columns, add="+")

        ctk.CTkLabel(
            right_frame, text="Teleportation", font=("Inter", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self._build_map_card(right_frame)

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
        ).pack(side=tk.LEFT, padx=(0, 20))

        self.content_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._on_mode_changed()
        if self.slot_var.get() > 0:
            self._load_character(quiet=True)

    def _build_map_card(self, parent):
        """Card advertising the World Map window, with a map thumbnail."""
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color=ds.BOX,
            border_width=1,
            border_color=palette.PURPLE_TEXT,
        )
        card.pack(fill=tk.X, padx=10, pady=(5, 10))
        map_path = self._maps_dir / "lands_between.jpg" if self._maps_dir else None
        if map_path is not None and map_path.exists():
            image_label = ctk.CTkLabel(
                card, text="", width=300, height=186, cursor="hand2"
            )
            image_label.pack(side=tk.LEFT, padx=8, pady=8)
            image_label.bind("<Button-1>", lambda e: self._open_map_window())
            self._load_map_thumb(image_label, map_path)
        text = ctk.CTkFrame(card, fg_color="transparent")
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 12), pady=10)
        ctk.CTkLabel(text, text="World map", font=ds.TITLE_LARGE, anchor="w").pack(
            fill=tk.X
        )
        ctk.CTkLabel(
            text,
            text="Teleport by clicking graces, dungeons or tiles on the game's map, "
            "lock or unlock graces, and place, move or copy map markers. "
            "Lands Between, Underground and Realm of Shadow.",
            font=ds.FONT,
            anchor="w",
            justify="left",
            wraplength=380,
        ).pack(fill=tk.X, pady=(4, 10))
        ctk.CTkButton(
            text,
            text="Open World Map",
            font=("Inter", 15),
            height=40,
            width=200,
            command=self._open_map_window,
        ).pack(anchor="w")

    @staticmethod
    def _load_map_thumb(label, path: Path) -> None:
        """Show the map thumbnail in label once a worker thread has decoded
        it; decoding the full-size progressive JPEG would block the window."""
        result = []

        def decode():
            from PIL import Image

            with Image.open(path) as img:
                # Overworld land area, scaled down
                result.append(
                    img.crop((400, 600, 4400, 4300)).resize((300, 186), Image.LANCZOS)
                )

        def poll():
            if not label.winfo_exists():
                return
            if worker.is_alive():
                label.after(_THUMB_POLL_MS, poll)
            elif result:
                label.configure(image=ctk.CTkImage(result[0], size=(300, 186)))

        worker = threading.Thread(target=decode, daemon=True)
        worker.start()
        label.after(_THUMB_POLL_MS, poll)

    def _load_character(self, quiet: bool = False):
        save = self.get_save_file()
        if not save:
            if quiet:
                return
            CTkMessageBox.showwarning(
                "No Save",
                "Load a save file first.",
                parent=self._dialog_parent(),
            )
            return

        try:
            slot_idx = int(self.slot_var.get()) - 1
        except (ValueError, AttributeError):
            slot_idx = 0

        if not (0 <= slot_idx < 10):
            CTkMessageBox.showerror(
                "Invalid Slot",
                "Select a slot between 1 and 10.",
                parent=self._dialog_parent(),
            )
            return

        slot = save.character_slots[slot_idx]
        if slot.is_empty() or slot_idx not in save.get_active_slots():
            if not quiet:
                CTkMessageBox.showwarning(
                    "Empty Slot",
                    f"Slot {slot_idx + 1} is empty.",
                    parent=self._dialog_parent(),
                )
            self.map_name_var.set("Empty slot")
            self.coords_var.set("N/A")
            self.bloodstain_var.set("N/A")
            self.messages_var.set("N/A")
            self.editor = None
            self.marker_editor = None
            self.refresh()
            self._update_map_window()
            return

        self.editor = WorldStateEditor(save, slot_idx)
        self.marker_editor = MapMarkerEditor(save, slot_idx)
        self.marker_editor_slot = slot_idx
        self._snapshot_markers()
        self.refresh()
        self._update_map_window()

    def _reload_editor(self):
        """Recreate editor from the reloaded save so it points to the fresh object."""
        save = self.get_save_file()
        if save is None or self.editor is None:
            return
        # Preserve slot selection across reload
        slot_idx = self.slot_var.get() - 1
        self.editor = WorldStateEditor(save, slot_idx)
        old_markers = self.marker_editor
        old_slot = self.marker_editor_slot
        self.marker_editor = MapMarkerEditor(save, slot_idx)
        self.marker_editor_slot = slot_idx
        if (
            old_markers is not None
            and old_markers.dirty
            and old_slot == slot_idx
            and self.marker_editor.supported
        ):
            # Saves made elsewhere in the tab do not touch the marker records,
            # so staged markers keep their record positions.
            self.marker_editor.markers = old_markers.markers
            self.marker_editor.dirty = True
        else:
            self._snapshot_markers()
        self._update_map_window()

    @reopenable
    def _open_message_manager(self):
        if not self.editor:
            CTkMessageBox.showerror(
                "No Character Loaded", "Load a character first.", parent=self.parent
            )
            return

        def reload():
            self.reload_save()
            self._reload_editor()
            self.refresh()

        MessageManagerDialog(
            self.parent,
            self.slot_var.get() - 1,
            self.get_save_file,
            self.get_save_path,
            reload,
            self.show_toast,
        )

    def _sync_bloodstain_to_player(self):
        if not self.editor:
            CTkMessageBox.showerror(
                "No Character Loaded",
                "Load a character first.",
                parent=self._dialog_parent(),
            )
            return

        if not CTkMessageBox.askyesno(
            "Move Bloodstain",
            "Move the bloodstain to the player's current position?\n\nThis will overwrite the existing bloodstain location.",
            parent=self._dialog_parent(),
        ):
            return

        save_path = self.get_save_path()
        if save_path:
            BackupManager(Path(save_path)).create_backup(
                description="before_bloodstain_sync",
                operation="world_state_bloodstain_sync",
                save=self.get_save_file(),
            )

        success, message = self.editor.sync_bloodstain_to_player()
        if success:
            if save_path:
                self.get_save_file().recalculate_checksums()
                self.get_save_file().to_file(save_path)
                self.reload_save()
                self._reload_editor()
                self.refresh()
            self.show_toast(message, duration=2500)
        else:
            CTkMessageBox.showerror(
                "Bloodstain Not Moved", message, parent=self._dialog_parent()
            )

    def set_maps_dir(self, path: Path):
        self._maps_dir = path

    def _player_map_point(self) -> tuple[int, float, float] | None:
        if not self.editor:
            return None
        info = self.editor.get_current_location()
        coords = info.get("coordinates")
        if not info.get("map_id_str") or coords is None:
            return None
        return location_map_point(
            info["map_id_str"], coords.x, coords.z, self._convergence
        )

    def _bloodstain_map_point(self) -> tuple[int, float, float, str, int] | None:
        """Map position and label of the character's bloodstain, None when
        there is none (BloodStain 0x30 is 0 while one exists)."""
        if not self.editor:
            return None
        save = self.get_save_file()
        bs = getattr(save.character_slots[self.slot_var.get() - 1], "blood_stain", None)
        if bs is None or bs.unk0x30 != 0:
            return None
        d = bs.map_id.data
        map_id = f"m{d[3]:02d}_{d[2]:02d}_{d[1]:02d}_{d[0]:02d}"
        point = location_map_point(
            map_id, bs.coordinates.x, bs.coordinates.z, self._convergence
        )
        if point is None:
            return None
        blood = self.editor.get_bloodstain_location() or {}
        runes = max(bs.runes, 0)
        label = f"{blood.get('map_name', map_id)}, {runes:,} runes"
        return (*point, label, runes)

    def _map_slot_selected(self, value: str):
        """Character picked in the map window: switch the main window's
        character bar, which loads it here."""
        if value in self._slot_labels and self.select_character is not None:
            self.select_character(self._slot_labels.index(value))
        self._update_map_window()

    def _update_map_window(self):
        window = current_window()
        if window is not None:
            index = self.slot_var.get() - 1
            window.set_character(
                self._slot_labels,
                self._slot_labels[index]
                if 0 <= index < len(self._slot_labels)
                else None,
            )
            window.set_bloodstain(self._bloodstain_map_point())
            window.set_player(self._player_map_point())
            window.set_marker_editor(self.marker_editor)
            loaded = self.editor is not None
            window.set_grace_callbacks(
                self._grace_state if loaded else None,
                self._set_grace if loaded else None,
                self._unlock_on_map if loaded else None,
            )
            window.set_pickup_callback(self._set_pickup if loaded else None)
            window.set_flag_callback(self._set_flags if loaded else None)
            save = self.get_save_file()
            path = (getattr(save, "_original_filepath", "") or "").lower()
            # Seamless Co-op (.co2) and Convergence have no summoning pools
            window.set_pools_available(
                save is not None and path.endswith(".sl2") and not save.is_convergence
            )

    def _grace_state(self, flag_id: int) -> bool | None:
        save = self.get_save_file()
        if save is None or self.editor is None:
            return None
        slot = save.character_slots[self.slot_var.get() - 1]
        try:
            return EventFlags.get_flag(slot.event_flags, flag_id)
        except (ValueError, KeyError):
            return None

    def _set_grace(self, flag_id: int, state: bool):
        self._set_graces([flag_id], state)

    def _unlock_on_map(self, grace_flags: list[int], piece_flags: list[int]):
        """Reveal map pieces and unlock graces with their play regions."""
        save = self.get_save_file()
        if save is None or self.editor is None:
            return
        names = {loc.flag_id: loc.name for loc in self.all_locations if loc.flag_id}
        grace_flags = filter_unlock(
            grace_flags,
            names,
            self._convergence,
            self._grace_state,
            self._dialog_parent(),
        )
        if grace_flags is None:
            return
        try:
            result = unlock(
                save,
                self.slot_var.get() - 1,
                grace_flags,
                piece_flags,
                self._convergence,
            )
        except (ValueError, KeyError) as e:
            CTkMessageBox.showerror(
                "Unlock Failed", f"Could not unlock:\n{e}", parent=self._dialog_parent()
            )
            self.reload_save()
            return
        if self._persist("before_map_unlock", "map_unlock"):
            parts = [
                count_phrase(n, word)
                for n, word in (
                    (result.graces, "grace"),
                    (result.pieces, "map piece"),
                    (result.regions, "play region"),
                    (result.fog_cells, "fog cell"),
                )
                if n
            ]
            self.show_toast(
                f"Unlocked {', '.join(parts)}" if parts else "Nothing new to unlock",
                duration=3000,
            )

    def _set_graces(self, flag_ids: list[int], state: bool):
        """Lock or unlock graces: write their event flags and save the file."""
        save = self.get_save_file()
        if save is None or self.editor is None:
            return
        slot = save.character_slots[self.slot_var.get() - 1]
        flags = bytearray(slot.event_flags)
        try:
            for flag_id in flag_ids:
                EventFlags.set_flag(flags, flag_id, state)
        except (ValueError, KeyError) as e:
            CTkMessageBox.showerror(
                "Grace", f"Could not write the flag:\n{e}", parent=self._dialog_parent()
            )
            return
        slot.event_flags = bytes(flags)
        off = slot.event_flags_offset
        save._raw_data[off : off + len(flags)] = flags
        if self._persist("before_grace_edit", "grace_edit"):
            what = "Grace" if len(flag_ids) == 1 else f"{len(flag_ids)} graces"
            self.show_toast(
                f"{what} {'unlocked' if state else 'locked'}.", duration=2500
            )

    def _set_pickup(self, flag_id: int, collected: bool):
        """Mark a world item pickup collected, or clear its flag so the item
        is placed again, and save the file."""
        save = self.get_save_file()
        if save is None or self.editor is None:
            return
        slot = save.character_slots[self.slot_var.get() - 1]
        flags = bytearray(slot.event_flags)
        try:
            EventFlags.set_flag(flags, flag_id, collected)
        except (ValueError, KeyError) as e:
            CTkMessageBox.showerror(
                "Item Pickup",
                f"Could not write the flag:\n{e}",
                parent=self._dialog_parent(),
            )
            return
        slot.event_flags = bytes(flags)
        off = slot.event_flags_offset
        save._raw_data[off : off + len(flags)] = flags
        if self._persist("before_pickup_edit", "pickup_edit", reload=False):
            self.show_toast(
                "Pickup marked collected."
                if collected
                else "Pickup respawns after the area reloads.",
                duration=2500,
            )

    def _set_flags(
        self,
        changes: dict[int, bool],
        operation: str,
        message: str,
        to_roundtable: bool,
    ):
        """Write NPC or boss flags from the map and save the file;
        to_roundtable also teleports the character to Roundtable Hold."""
        save = self.get_save_file()
        if save is None or self.editor is None:
            return
        index = self.slot_var.get() - 1
        slot = save.character_slots[index]
        flags = bytearray(slot.event_flags)
        try:
            for flag_id, state in changes.items():
                EventFlags.set_flag(flags, flag_id, state)
        except (ValueError, KeyError) as e:
            CTkMessageBox.showerror(
                "Flags Not Written",
                f"Could not write the flag:\n{e}",
                parent=self._dialog_parent(),
            )
            return
        slot.event_flags = bytes(flags)
        off = slot.event_flags_offset
        save._raw_data[off : off + len(flags)] = flags
        if to_roundtable:
            from er_save_manager.fixes.teleport import TELEPORT_LOCATIONS
            from er_save_manager.parser.er_types import FloatVector3

            dest = TELEPORT_LOCATIONS["roundtable"]
            ok, msg = self.editor.teleport_to_custom(
                dest.map_id, FloatVector3(*dest.coordinates)
            )
            if not ok:
                CTkMessageBox.showwarning(
                    "Teleport Failed",
                    f"Could not move the character to Roundtable Hold:\n{msg}",
                    parent=self._dialog_parent(),
                )
        # The Roundtable Hold move goes through the editor; reload after it
        if self._persist(f"before_{operation}", operation, reload=to_roundtable):
            self.show_toast(message, duration=2500)

    def _open_map_window(self):
        if not self._maps_dir:
            CTkMessageBox.showwarning(
                "Map Unavailable", "Map images not found.", parent=self.parent
            )
            return
        open_map_window(
            self.parent,
            self._maps_dir,
            self.all_locations,
            on_teleport=self._teleport_to_known_loc,
            player=self._player_map_point(),
            marker_editor=self.marker_editor,
            on_apply_markers=self._apply_markers,
            on_copy_markers=self._copy_markers,
            on_import_markers=self._import_markers,
            on_export_markers=self._export_markers,
            grace_state=self._grace_state if self.editor else None,
            on_set_grace=self._set_grace if self.editor else None,
            on_unlock=self._unlock_on_map if self.editor else None,
            on_select_slot=self._map_slot_selected,
            on_move_bloodstain=self._sync_bloodstain_to_player,
            convergence=self._convergence,
        )
        self._update_map_window()

    # ------------------------------------------------------------------
    # Map markers
    # ------------------------------------------------------------------

    def _persist(self, description: str, operation: str, reload: bool = True) -> bool:
        """Back up the file on disk, write the edited save and reload it.
        reload=False keeps the loaded save: for event flag writes, which
        change no offsets, the loaded save already holds the new state and
        a full reload only re-parses and refreshes every tab."""
        save_path = self.get_save_path()
        if not save_path:
            return False
        save = self.get_save_file()
        BackupManager(Path(save_path)).create_backup(
            description=description, operation=operation, save=save
        )
        save.recalculate_checksums()
        save.to_file(save_path)
        if reload:
            self.reload_save()
            self._reload_editor()
        self.refresh()
        return True

    def _apply_markers(self, editor: MapMarkerEditor) -> MapMarkerEditor | None:
        """Map window's Apply: the main window's Apply All."""
        if self.apply_all is not None:
            self.apply_all()
        return self.marker_editor

    def _snapshot_markers(self) -> None:
        m = self.marker_editor
        self._marker_snapshot = (
            {self._marker_key(x) for x in m.markers} if m is not None else set()
        )

    @staticmethod
    def _marker_key(marker) -> tuple:
        return (
            marker.kind,
            marker.id,
            marker.x,
            marker.y,
            marker.map,
            marker.icon,
            marker.flags,
        )

    def marker_changes(self) -> int:
        """Markers and beacons added, removed or changed since loading."""
        m = self.marker_editor
        if m is None or not m.dirty:
            return 0
        now = {self._marker_key(x) for x in m.markers}
        return max(1, len(now ^ self._marker_snapshot))

    def marker_details(self):
        """One row per marker or beacon added, removed, moved or given
        another icon. Keys are _marker_key tuples."""
        m = self.marker_editor
        if m is None or not m.dirty:
            return []
        before = {key[1]: key for key in self._marker_snapshot}
        after = {x.id: self._marker_key(x) for x in m.markers}
        rows = []
        for marker_id in sorted(before.keys() | after.keys()):
            old, new = before.get(marker_id), after.get(marker_id)
            if old == new:
                continue
            kind, _id, _x, _y, map_id, icon, _flags = new or old
            field = f"{kind.capitalize()} ({MAP_NAMES.get(map_id, f'Map {map_id}')})"
            if old is None:
                rows.append((field, "", "Added"))
            elif new is None:
                rows.append((field, "", "Removed"))
            elif old[5] != icon:
                rows.append((field, f"Icon {old[5]}", f"Icon {icon}"))
            else:
                rows.append((field, "", "Moved"))
        return rows

    def discard_markers(self) -> None:
        if self.marker_editor is not None:
            self.marker_editor.revert()
        self._refresh_marker_summary()
        self._update_map_window()

    def prepare_markers(self):
        editor = self.marker_editor
        if editor is None:
            raise StageError("No character loaded.")
        if not editor.supported:
            raise StageError("This character uses the older marker layout.")

        def commit() -> None:
            if isinstance(editor._save._raw_data, bytes):
                editor._save._raw_data = bytearray(editor._save._raw_data)
            editor.apply()

        return commit

    def _export_markers(self, editor: MapMarkerEditor):
        path = pick_file(
            save=True,
            title="Export Map Markers",
            defaultextension=".json",
            filetypes=[("Map markers", "*.json"), ("All files", "*.*")],
            initialfile="map_markers.json",
        )
        if not path:
            return
        editor.export_file(path)
        self.show_toast(f"Exported {len(editor.markers)} markers.", duration=2500)

    def _ask_replace(self, parent, title: str, message: str) -> bool | None:
        """True to replace, False to append, None when cancelled."""
        dialog = ds.create(parent, title)
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        ds.header(main, title, font=ds.TITLE_LARGE)
        ctk.CTkLabel(
            main, text=message, font=ds.FONT, justify="left", anchor="w", wraplength=420
        ).pack(fill=tk.X, pady=(10, 0))
        result: dict[str, bool | None] = {"value": None}

        def choose(value):
            result["value"] = value
            dialog.destroy()

        ds.button_row(
            main,
            [
                {"text": "Cancel", "command": dialog.destroy, "primary": False},
                {"text": "Append", "command": lambda: choose(False)},
                {"text": "Replace", "command": lambda: choose(True)},
            ],
        )
        ds.finish(dialog, parent, min_width=460)
        dialog.wait_window()
        return result["value"]

    def _import_markers(self, editor: MapMarkerEditor) -> bool:
        parent = self._dialog_parent()
        path = pick_file(
            title="Import Map Markers",
            filetypes=[("Map markers", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return False
        replace = self._ask_replace(
            parent,
            "Import Map Markers",
            "Replace this character's markers and beacons with the imported "
            "ones, or append them to the existing ones?",
        )
        if replace is None:
            return False
        try:
            added, skipped = editor.import_file(path, replace)
        except (OSError, ValueError, KeyError) as e:
            CTkMessageBox.showerror(
                "Import Failed", f"Not a map marker file:\n{e}", parent=parent
            )
            return False
        note = f" {skipped} did not fit." if skipped else ""
        self.show_toast(
            f"Imported {added} markers. Apply All to save.{note}", duration=3500
        )
        return True

    def _copy_markers(self, markers: dict):
        parent = self._dialog_parent()
        save = self.get_save_file()
        if save is None or not self.editor:
            return
        source = self.slot_var.get() - 1
        # Character bar label -> slot index; ER bar labels list all 10 slots
        targets = {
            label: i
            for i, label in enumerate(self._slot_labels)
            if i != source and not label.endswith(" - Empty")
        }
        names = list(targets)
        if not names:
            CTkMessageBox.showinfo(
                "Copy Markers",
                "There is no other character in this save.",
                parent=parent,
            )
            return

        dialog = ds.create(parent, "Copy Markers To")
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        ds.header(main, "Copy Markers To", font=ds.TITLE_LARGE)
        ctk.CTkLabel(
            main,
            text="Copies this character's markers and beacons as shown on the map, "
            "unsaved changes included.",
            font=ds.FONT,
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill=tk.X, pady=(10, 8))
        target_var = tk.StringVar(value=names[0])
        combo = ctk.CTkComboBox(
            main, values=names, variable=target_var, state="readonly", width=280
        )
        combo.pack(anchor="w")
        patch_combo_scroll(combo)
        result: dict[str, int | None] = {"value": None}

        def confirm():
            result["value"] = targets[target_var.get()]
            dialog.destroy()

        ds.button_row(
            main,
            [
                {"text": "Cancel", "command": dialog.destroy, "primary": False},
                {"text": "Next", "command": confirm},
            ],
        )
        ds.finish(dialog, parent, min_width=460)
        dialog.wait_window()
        target = result["value"]
        if target is None:
            return

        target_editor = MapMarkerEditor(save, target)
        if not target_editor.supported:
            CTkMessageBox.showwarning(
                "Copy Markers",
                "The target character uses the older marker layout. Load it in "
                "game and save once, then copy again.",
                parent=parent,
            )
            return
        replace = self._ask_replace(
            parent,
            "Copy Markers",
            f"Replace the markers and beacons of slot {target + 1}, or append "
            "to the ones it has?",
        )
        if replace is None:
            return
        added, skipped = copy_markers(save, markers, target, replace)
        if not self._persist("before_copy_map_markers", "world_state_copy_markers"):
            return
        note = f" {skipped} did not fit." if skipped else ""
        self.show_toast(
            f"Copied {added} markers to slot {target + 1}.{note}", duration=3500
        )

    # ------------------------------------------------------------------
    # Item history
    # ------------------------------------------------------------------

    @reopenable
    def _open_item_history(self):
        if not self.editor:
            CTkMessageBox.showwarning(
                "No Character", "Load a character first.", parent=self.parent
            )
            return
        from er_save_manager.ui.dialogs.item_history import show_item_history

        save = self.get_save_file()
        show_item_history(self.parent, save, self.slot_var.get() - 1)

    def _on_mode_changed(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        if self.teleport_mode.get() == "known":
            self._build_known_locations_ui()
        else:
            self._build_custom_teleport_ui()

    def _build_known_locations_ui(self):
        search_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        search_frame.pack(fill=tk.X, pady=(0, 5))

        ctk.CTkLabel(search_frame, text="Search:", font=ds.BOLD).pack(
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

        listbox_frame, self.location_listbox = ds.themed_listbox(
            self.content_frame,
            selectmode=tk.SINGLE,
            height=20,
        )
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)
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
            grace_tag = " [Grace]" if loc.tile_type == "grace" else ""
            dlc_tag = " [DLC]" if loc.is_dlc else ""
            boss_tag = (
                " [Boss Alive]"
                if self.editor
                and closed_gate(loc, self._convergence, self._grace_state)
                else ""
            )
            self.location_listbox.insert(
                tk.END, f"{loc.map_id_str}  {loc.name}{grace_tag}{dlc_tag}{boss_tag}"
            )

    def _teleport_to_known(self):
        if not self.editor:
            CTkMessageBox.showerror(
                "No Character Loaded", "Load a character first.", parent=self.parent
            )
            return

        sel = self.location_listbox.curselection()
        if not sel:
            CTkMessageBox.showerror(
                "No Location Selected",
                "Select a location from the list.",
                parent=self.parent,
            )
            return

        self._teleport_to_known_loc(self.filtered_locations[sel[0]])

    def _dialog_parent(self):
        """The map window while it is open, so dialogs do not open behind it."""
        window = current_window()
        return window._win if window else self.parent

    def _teleport_to_known_loc(self, loc: MapLocation):
        if not self.editor:
            CTkMessageBox.showerror(
                "No Character Loaded",
                "Load a character first.",
                parent=self._dialog_parent(),
            )
            return

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
                    parent=self._dialog_parent(),
                ):
                    return

        if loc.tile_type == "pin" and not confirm_pin_teleport(self._dialog_parent()):
            return

        if not confirm_teleport(
            loc, self._convergence, self._grace_state, self._dialog_parent()
        ):
            return

        save_path = self.get_save_path()
        if save_path:
            BackupManager(Path(save_path)).create_backup(
                description=f"before_teleport_{loc.map_id_str}",
                operation="world_state_teleport",
                save=self.get_save_file(),
            )

        success, message = self.editor.teleport_to_location(loc)
        if success:
            if save_path:
                self.get_save_file().recalculate_checksums()
                self.get_save_file().to_file(save_path)
                self.reload_save()
                self._reload_editor()
                self.refresh()
            self.show_toast(f"Teleported to {loc.name}", duration=2500)
        else:
            CTkMessageBox.showerror(
                "Teleport Failed", message, parent=self._dialog_parent()
            )

    def _build_custom_teleport_ui(self):
        ctk.CTkLabel(
            self.content_frame,
            text="Advanced: invalid coordinates may corrupt your save.",
            text_color="#ff6b6b",
            font=("Inter", 10, "bold"),
        ).pack(pady=(0, 20))

        map_frame = ctk.CTkFrame(self.content_frame, corner_radius=12)
        map_frame.pack(fill=tk.X, pady=(0, 15))
        ctk.CTkLabel(map_frame, text="Map ID", font=("Inter", 11, "bold")).pack(
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
            font=("Inter", 10),
            text_color=("gray40", "gray70"),
        ).pack(side=tk.LEFT)

        coords_frame = ctk.CTkFrame(self.content_frame, corner_radius=12)
        coords_frame.pack(fill=tk.X, pady=(0, 15))
        ctk.CTkLabel(
            coords_frame, text="Coordinates (optional)", font=("Inter", 11, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        ctk.CTkLabel(
            coords_frame,
            text="Leave 0.0 to use current coordinates",
            font=("Inter", 10),
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
                "No Character Loaded", "Load a character first.", parent=self.parent
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
                "Invalid Coordinates",
                "Coordinates must be numeric.",
                parent=self.parent,
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
            CTkMessageBox.showerror("Teleport Failed", message, parent=self.parent)

    def _refresh_marker_summary(self):
        if not hasattr(self, "markers_var"):
            return
        m = self.marker_editor
        if m is None:
            self.markers_var.set("N/A")
        elif not m.supported:
            self.markers_var.set("Older marker layout (not editable)")
        else:
            changed = "\nUnapplied changes" if m.dirty else ""
            self.markers_var.set(
                f"{m.count(MARKER)} markers, {m.count(BEACON)} beacons{changed}"
            )

    def _bloodstain_has_runes(self) -> bool:
        """A bloodstain exists (BloodStain 0x30 is 0) and holds runes."""
        save = self.get_save_file()
        if not self.editor or save is None:
            return False
        bs = getattr(save.character_slots[self.slot_var.get() - 1], "blood_stain", None)
        return bs is not None and bs.unk0x30 == 0 and bs.runes > 0

    def refresh(self):
        self._refresh_marker_summary()
        listbox = getattr(self, "location_listbox", None)
        if listbox is not None and listbox.winfo_exists():
            self._update_location_list()
        if hasattr(self, "bloodstain_btn"):
            self.bloodstain_btn.configure(
                state="normal" if self._bloodstain_has_runes() else "disabled"
            )
        if not self.editor:
            self.map_name_var.set("No character loaded")
            self.coords_var.set("N/A")
            self.bloodstain_var.set("N/A")
            self.messages_var.set("N/A")
            return

        info = self.editor.get_current_location()

        if info["map_name"] == "Empty Slot":
            self.map_name_var.set("Empty slot")
            self.coords_var.set("N/A")
            self.bloodstain_var.set("N/A")
            self.messages_var.set("N/A")
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

        messages = self.editor.get_message_counts()
        if messages is None:
            self.messages_var.set("Message data unreadable")
        else:
            own, cached = messages
            self.messages_var.set(f"{own} own, {cached} cached")
