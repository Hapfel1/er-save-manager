"""
Elden Ring Save Parser - Save File (Main Entry Point)

Handles complete save file with 10 character slots, checksums, and platform detection.
Based on ER-Save-Lib Rust implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO

from er_save_manager.parser.user_data_10 import UserData10
from er_save_manager.parser.user_data_x import UserDataX


@dataclass
class Save:
    """
    Complete Elden Ring save file

    Structure:
    - Magic (4 bytes)
    - Header (0x2FC for PC, 0x6C for PS)
    - 10 Character slots (UserDataX)
    - USER_DATA_10 (Common section with SteamID and ProfileSummary)
    - USER_DATA_11 (Regulation data)

    Each character slot on PC has:
    - MD5 checksum (16 bytes)
    - Character data (~2.6MB)
    """

    # File identification
    magic: bytes = b""
    is_ps: bool = False

    # Header
    header: bytes = b""

    # Character slots (10 total)
    character_slots: list[UserDataX] = field(default_factory=list)

    # Common section (parsed)
    user_data_10_parsed: UserData10 | None = None

    # Additional data sections (raw)
    user_data_10: bytes = b""
    user_data_11: bytes = b""

    # Offset tracking for modifications
    _user_data_10_offset: int = 0
    _slot_offsets: list[int] = field(default_factory=list)

    # Note: _raw_data and _original_filepath are set dynamically in from_file()
    # They are not dataclass fields to avoid type conversion issues

    def __post_init__(self):
        """Initialize dynamic attributes if not already set."""
        if not hasattr(self, "_raw_data"):
            self._raw_data = bytearray()
        if not hasattr(self, "_original_filepath"):
            self._original_filepath = ""
        # Ensure _raw_data is always bytearray
        if isinstance(self._raw_data, bytes) and not isinstance(
            self._raw_data, bytearray
        ):
            self._raw_data = bytearray(self._raw_data)

    def __setattr__(self, name, value):
        """Override to ensure _raw_data is always bytearray"""
        if name == "_raw_data":
            # Force conversion to bytearray
            if isinstance(value, bytes) and not isinstance(value, bytearray):
                value = bytearray(value)
        super().__setattr__(name, value)

    @classmethod
    def from_file(cls, filepath: str) -> Save:
        """
        Load and parse save file from disk.

        Args:
            filepath: Path to save file

        Returns:
            Save instance with all data parsed
        """

        with open(filepath, "rb") as file:
            data = file.read()

        f = BytesIO(data)
        obj = cls()

        # Track original filepath for save() method
        obj._original_filepath = filepath

        # Force bytearray, not bytes
        if isinstance(data, bytes):
            obj._raw_data = bytearray(data)
        else:
            obj._raw_data = data

        # Double-check it's actually bytearray
        assert isinstance(obj._raw_data, bytearray), (
            f"_raw_data is {type(obj._raw_data)}, not bytearray!"
        )

        # Verify it's mutable
        try:
            obj._raw_data[0] = obj._raw_data[0]  # Test write
        except TypeError as e:
            raise TypeError(
                f"_raw_data is not writable! Type: {type(obj._raw_data)}"
            ) from e

        # Read magic (4 bytes)
        obj.magic = f.read(4)

        # Detect platform
        if obj.magic == b"BND4":
            obj.is_ps = False
        elif obj.magic == b"SL2\x00":
            obj.is_ps = False
        elif obj.magic == bytes([0xCB, 0x01, 0x9C, 0x2C]):
            obj.is_ps = True
        else:
            raise ValueError(f"Invalid save file magic: {obj.magic.hex()}")

        # Read header
        if obj.is_ps:
            header_size = 0x6C
        else:
            header_size = 0x2FC

        obj.header = f.read(header_size)

        # Parse 10 character slots

        for _slot_index in range(10):
            # Mark the start position of this slot's data
            slot_start = f.tell()

            # Store slot offset
            obj._slot_offsets.append(slot_start)

            # Read checksum (PC only)
            checksum = None
            if not obj.is_ps:
                checksum = f.read(16)

                # Check if full checksum
                if len(checksum) < 16:
                    obj.character_slots.append(UserDataX())
                    break  # No more slots

                # Display checksum
                checksum.hex()

                # Check if slot is empty (all zeros checksum)
                if checksum == bytes(16):
                    # Skip the character data for this slot
                    f.read(0x280000)  # Skip empty slot data
                    obj.character_slots.append(UserDataX())  # Add empty slot
                    continue

            # Mark where character data starts (after checksum)
            char_data_start = f.tell()

            # Calculate slot size (data portion only, without checksum)
            slot_data_size = 0x280000

            # Parse character data
            try:
                char = UserDataX.read(f, obj.is_ps, char_data_start, slot_data_size)
                obj.character_slots.append(char)

                if char.is_empty():
                    pass
                else:
                    # Check for issues
                    if char.has_torrent_bug():
                        pass
                    if char.has_weather_corruption():
                        pass
                    if char.has_time_corruption():
                        pass

            except Exception:
                obj.character_slots.append(UserDataX())
                # Skip to next slot boundary
                correct_position = slot_start + 0x280010
                f.seek(correct_position)

        # Read and parse USER_DATA_10

        user_data_10_start = f.tell()
        obj._user_data_10_offset = user_data_10_start

        try:
            # Parse USER_DATA_10
            obj.user_data_10_parsed = UserData10.read(f, obj.is_ps)

            # Also keep raw bytes
            user_data_10_end = f.tell()
            f.seek(user_data_10_start)
            obj.user_data_10 = f.read(user_data_10_end - user_data_10_start)
            f.seek(user_data_10_end)
        except Exception:
            # Fall back to reading raw bytes
            f.seek(user_data_10_start)
            if not obj.is_ps:
                f.read(16)  # Skip checksum
            obj.user_data_10 = f.read(0x60000)

        # Read USER_DATA_11
        if not obj.is_ps:
            f.read(16)  # Skip checksum

        if obj.is_ps:
            obj.user_data_11 = f.read(0x240010)
        else:
            obj.user_data_11 = f.read(0x240010)

        return obj

    def recalculate_checksums(self):
        """
        Recalculate MD5 checksums for all active slots

        This is called after making modifications to ensure
        the save file integrity is maintained
        """
        if not hasattr(self, "_raw_data"):
            raise RuntimeError("Cannot recalculate checksums: raw data not available")

        import hashlib

        SLOT_SIZE = 0x280000
        CHECKSUM_SIZE = 0x10

        # Recalculate for each active slot using tracked offsets
        for slot_idx in range(10):
            slot = self.character_slots[slot_idx]
            if slot.is_empty():
                continue

            # Use tracked offset for this slot
            slot_offset = self._slot_offsets[slot_idx]
            checksum_offset = slot_offset
            data_offset = slot_offset + CHECKSUM_SIZE

            # Calculate MD5 of character data
            char_data = self._raw_data[data_offset : data_offset + SLOT_SIZE]
            md5_hash = hashlib.md5(char_data).digest()

            # Write checksum
            self._raw_data[checksum_offset : checksum_offset + CHECKSUM_SIZE] = md5_hash

        # Recalculate USER_DATA_10 checksum using tracked offset
        userdata10_offset = self._user_data_10_offset
        userdata10_checksum_offset = userdata10_offset
        userdata10_data_offset = userdata10_offset + CHECKSUM_SIZE

        userdata10_data = self._raw_data[
            userdata10_data_offset : userdata10_data_offset + 0x60000
        ]
        md5_hash = hashlib.md5(userdata10_data).digest()
        self._raw_data[
            userdata10_checksum_offset : userdata10_checksum_offset + CHECKSUM_SIZE
        ] = md5_hash

    def to_file(self, filepath: str):
        """
        Write save file to disk.

        Args:
            filepath: Path where save file will be written
        """
        if not hasattr(self, "_raw_data"):
            raise RuntimeError("Cannot write save file: raw data not available")

        with open(filepath, "wb") as f:
            f.write(self._raw_data)

    def get_active_slots(self) -> list[int]:
        """
        Get list of slot indices that contain characters.

        Returns:
            List of slot indices (0-9) that are not empty
        """
        return [i for i, slot in enumerate(self.character_slots) if not slot.is_empty()]

    def get_slot(self, index: int) -> UserDataX:
        """
        Get character slot by index.

        Args:
            index: Slot index (0-9)

        Returns:
            UserDataX for that slot
        """
        if index < 0 or index >= 10:
            raise IndexError(f"Slot index must be 0-9, got {index}")
        return self.character_slots[index]

    def print_summary(self):
        """Print a summary of all character slots"""

        if self.user_data_10_parsed:
            pass

        self.get_active_slots()

        for slot_index in range(10):
            char = self.character_slots[slot_index]

            if char.is_empty():
                pass
            else:
                # Show profile summary time played if available
                if self.user_data_10_parsed and slot_index < len(
                    self.user_data_10_parsed.profile_summary.profiles
                ):
                    profile = self.user_data_10_parsed.profile_summary.profiles[
                        slot_index
                    ]
                    profile.seconds_played // 3600
                    (profile.seconds_played % 3600) // 60

                # Show issues
                issues = []
                if char.has_torrent_bug():
                    issues.append("Torrent bug")
                if char.has_weather_corruption():
                    issues.append("Weather corruption")
                if char.has_time_corruption():
                    issues.append("Time corruption")

                if issues:
                    pass

    @property
    def characters(self):
        """Compatibility alias for character_slots"""
        return self.character_slots

    def save(self, filepath: str = None):
        """
        Compatibility wrapper for to_file()

        If no filepath provided, saves to the original file path
        (must be tracked during load)
        """
        if filepath is None:
            if not hasattr(self, "_original_filepath"):
                raise ValueError("No filepath specified and original path not tracked")
            filepath = self._original_filepath

        self.to_file(filepath)

    @property
    def data(self):
        """Compatibility alias for _raw_data - always returns bytearray"""
        if hasattr(self, "_raw_data"):
            # Force conversion if it's somehow bytes
            if isinstance(self._raw_data, bytes) and not isinstance(
                self._raw_data, bytearray
            ):
                self._raw_data = bytearray(self._raw_data)
            return self._raw_data
        return bytearray()

    def fix_character_corruption(self, slot_index: int) -> tuple[bool, list[str]]:
        """
        Fix corruption issues in a character slot.

        Fixes:
        1. Torrent bug: HP=0, State=ACTIVE, State=DEAD
        2. SteamId: 0 or not matching the one in USER_DATA_10, Copy from USER_DATA_10
        3. Time: 00:00:00, Calculate from seconds_played
        4. Weather: AreaId=0, Sync with MapId[3]

        Returns:
            (was_fixed, list_of_fixes)
        """
        if slot_index < 0 or slot_index >= 10:
            raise IndexError(f"Slot index must be 0-9, got {slot_index}")

        slot = self.character_slots[slot_index]
        if slot.is_empty():
            return (False, [])

        fixes = []
        from io import BytesIO

        # Fix 1: Torrent bug
        if slot.has_torrent_bug():
            horse = slot.horse
            if horse and horse.has_bug():
                horse.fix_bug()

                if hasattr(slot, "horse_offset") and slot.horse_offset > 0:
                    horse_bytes = BytesIO()
                    horse.write(horse_bytes)
                    horse_data = horse_bytes.getvalue()
                    # Calculate absolute offset
                    absolute_horse_offset = slot.data_start + slot.horse_offset
                    self._raw_data[
                        absolute_horse_offset : absolute_horse_offset + len(horse_data)
                    ] = horse_data
                    fixes.append(f"State changed to {horse.state.name}")

        # Fix 2: SteamId corruption
        # Get correct SteamId from USER_DATA_10
        correct_steam_id = None
        if self.user_data_10_parsed and hasattr(self.user_data_10_parsed, "steam_id"):
            correct_steam_id = self.user_data_10_parsed.steam_id

        if slot.has_steamid_corruption(correct_steam_id):
            if correct_steam_id is not None:
                # Update in memory
                slot.steam_id = correct_steam_id

                # Write to file
                if hasattr(slot, "steamid_offset") and slot.steamid_offset > 0:
                    import struct

                    # Calculate absolute offset (steamid_offset is relative to data_start)
                    absolute_offset = slot.data_start + slot.steamid_offset
                    steamid_bytes = struct.pack("<Q", correct_steam_id)
                    self._raw_data[absolute_offset : absolute_offset + 8] = (
                        steamid_bytes
                    )
                    fixes.append(f"SteamId set to {correct_steam_id}")

        # Fix 3: Time corruption
        # Get seconds_played from ProfileSummary
        seconds_played = None
        if self.user_data_10_parsed and hasattr(
            self.user_data_10_parsed, "profile_summary"
        ):
            profile_summary = self.user_data_10_parsed.profile_summary
            if slot_index < len(profile_summary.profiles):
                seconds_played = profile_summary.profiles[slot_index].seconds_played

        if slot.has_time_corruption(seconds_played):
            time = slot.world_area_time
            if time:
                # Get seconds_played from ProfileSummary
                if self.user_data_10_parsed and hasattr(
                    self.user_data_10_parsed, "profile_summary"
                ):
                    profile_summary = self.user_data_10_parsed.profile_summary
                    if slot_index < len(profile_summary.profiles):
                        profile = profile_summary.profiles[slot_index]
                        seconds_played = profile.seconds_played

                        # Calculate hours:minutes:seconds
                        hours = seconds_played // 3600
                        minutes = (seconds_played % 3600) // 60
                        seconds = seconds_played % 60

                        # Update in memory
                        time.hour = hours
                        time.minute = minutes
                        time.second = seconds

                        # Write to file
                        if hasattr(slot, "time_offset") and slot.time_offset > 0:
                            time_bytes = BytesIO()
                            time.write(time_bytes)
                            time_data = time_bytes.getvalue()
                            # Calculate absolute offset
                            absolute_time_offset = slot.data_start + slot.time_offset
                            self._raw_data[
                                absolute_time_offset : absolute_time_offset
                                + len(time_data)
                            ] = time_data
                            fixes.append(
                                f"Time set to {hours:02d}:{minutes:02d}:{seconds:02d}"
                            )

        # Fix 4: Weather corruption
        if slot.has_weather_corruption():
            weather = slot.world_area_weather
            if weather and hasattr(slot, "map_id") and slot.map_id:
                # Update in memory - AreaId = MapId[3]
                weather.area_id = slot.map_id.data[3]

                # Write to file
                if hasattr(slot, "weather_offset") and slot.weather_offset > 0:
                    weather_bytes = BytesIO()
                    weather.write(weather_bytes)
                    weather_data = weather_bytes.getvalue()
                    # Calculate absolute offset
                    absolute_weather_offset = slot.data_start + slot.weather_offset
                    self._raw_data[
                        absolute_weather_offset : absolute_weather_offset
                        + len(weather_data)
                    ] = weather_data
                    fixes.append(f"AreaId set to {weather.area_id}")

        # Fix 5: Event flag corruption (Ranni quest + warp sickness)
        # Check if slot has event flag issues
        has_event_corruption, all_issues = slot.has_corruption()
        event_flag_issues = [
            issue for issue in all_issues if issue.startswith("eventflag:")
        ]

        if event_flag_issues:
            try:
                from .event_flags import CorruptionFixer

                # Extract issue names (remove 'eventflag:' prefix)
                issue_names = [
                    issue.replace("eventflag:", "") for issue in event_flag_issues
                ]

                # Make event_flags mutable
                event_flags_mutable = bytearray(slot.event_flags)

                # Apply fixes
                fixes_count, fix_descriptions = CorruptionFixer.fix_all(
                    event_flags_mutable, issue_names
                )

                # Update character's event flags in memory
                slot.event_flags = bytes(event_flags_mutable)

                # Write back to raw data using the tracked offset
                if hasattr(slot, "event_flags_offset") and slot.event_flags_offset > 0:
                    # Calculate absolute offset
                    absolute_event_flags_offset = (
                        slot.data_start + slot.event_flags_offset
                    )
                    self._raw_data[
                        absolute_event_flags_offset : absolute_event_flags_offset
                        + len(event_flags_mutable)
                    ] = event_flags_mutable
                else:
                    # Fallback: calculate using tracked slot offset
                    slot_offset = self._slot_offsets[slot_index]
                    CHECKSUM_SIZE = 0x10

                    # Use the offset we found: 0x8F7 within character data
                    EVENT_FLAGS_OFFSET_IN_SLOT = 0x8F7

                    event_flags_start = (
                        slot_offset + CHECKSUM_SIZE + EVENT_FLAGS_OFFSET_IN_SLOT
                    )
                    self._raw_data[
                        event_flags_start : event_flags_start + len(event_flags_mutable)
                    ] = event_flags_mutable

                # Add fix descriptions
                for fix_desc in fix_descriptions:
                    fixes.append(f"{fix_desc}")
            except Exception:
                # Log error but don't fail the whole fix operation
                import traceback

                traceback.print_exc()

        was_fixed = len(fixes) > 0
        return (was_fixed, fixes)

    def get_character_presets(self):
        """Get character preset data from USER_DATA_10"""
        if self.user_data_10_parsed and self.user_data_10_parsed.menu_system_save_load:
            return self.user_data_10_parsed.menu_system_save_load.parsed
        return None

    def export_presets(self, output_path: str) -> int:
        """Export all active presets to JSON file"""
        import json

        presets = self.get_character_presets()
        if not presets:
            return 0

        active = presets.get_active_presets()
        data = {
            "version": 1,
            "preset_count": len(active),
            "presets": [
                {"slot": idx, "data": preset.to_dict()} for idx, preset in active
            ],
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        return len(active)

    def import_preset_from_json(
        self, json_path: str, preset_slot: int, dest_slot: int
    ) -> bool:
        """
        Import a preset from JSON file into a specific slot

        Args:
            json_path: Path to JSON file exported by export_presets()
            preset_slot: Which preset in the JSON to import (0-based index in JSON)
            dest_slot: Destination slot in save file (0-14)

        Returns:
            True if successful
        """
        import json

        from .character_presets import FacePreset

        try:
            # Load JSON
            with open(json_path) as f:
                data = json.load(f)

            # Validate JSON structure
            if "presets" not in data:
                return False

            if preset_slot < 0 or preset_slot >= len(data["presets"]):
                return False

            # Get preset data
            preset_entry = data["presets"][preset_slot]
            preset_data = preset_entry.get("data", {})

            # Create FacePreset from dict
            new_preset = FacePreset.from_dict(preset_data)

            # Get destination presets container
            dest_presets = self.get_character_presets()
            if not dest_presets:
                return False

            if dest_slot < 0 or dest_slot >= 15:
                return False

            # Set the preset
            dest_presets.presets[dest_slot] = new_preset

            # Update in raw data
            self._update_preset_in_raw_data(dest_slot, new_preset)

            return True

        except Exception:
            import traceback

            traceback.print_exc()
            return False

    def import_preset(self, preset, dest_slot: int) -> bool:
        """
        Import a FacePreset object into a specific slot

        Args:
            preset: FacePreset object or dict with preset data
            dest_slot: Destination slot in save file (0-14)

        Returns:
            True if successful
        """
        from .character_presets import FacePreset

        try:
            # Handle dict input (from JSON presets list)
            if isinstance(preset, dict):
                if "data" in preset:
                    # Format: {"original_slot": N, "data": {...}}
                    preset_data = preset["data"]
                else:
                    # Format: raw preset dict
                    preset_data = preset
                new_preset = FacePreset.from_dict(preset_data)
            else:
                # Already a FacePreset object
                new_preset = preset

            # Get destination presets container
            dest_presets = self.get_character_presets()
            if not dest_presets:
                return False

            if dest_slot < 0 or dest_slot >= 15:
                return False

            # Set the preset
            dest_presets.presets[dest_slot] = new_preset

            # Update in raw data
            self._update_preset_in_raw_data(dest_slot, new_preset)

            return True

        except Exception:
            import traceback

            traceback.print_exc()
            return False

    def delete_preset(self, slot: int) -> bool:
        """
        Delete a preset from a specific slot

        Args:
            slot: Preset slot to delete (0-14)

        Returns:
            True if successful
        """
        from .character_presets import FacePreset

        try:
            presets = self.get_character_presets()
            if not presets:
                return False

            if slot < 0 or slot >= 15:
                return False

            # Create empty preset
            empty_preset = FacePreset()

            # Set the preset
            presets.presets[slot] = empty_preset

            # Update in raw data
            self._update_preset_in_raw_data(slot, empty_preset)

            return True

        except Exception:
            import traceback

            traceback.print_exc()
            return False

    def copy_preset_to_save(
        self, source_save, source_slot: int, dest_slot: int
    ) -> bool:
        """Copy preset from another save file"""
        source_presets = source_save.get_character_presets()
        dest_presets = self.get_character_presets()

        if not source_presets or not dest_presets:
            return False

        if source_slot < 0 or source_slot >= 15 or dest_slot < 0 or dest_slot >= 15:
            return False

        source_preset = source_presets.presets[source_slot]
        if source_preset.is_empty():
            return False

        # Deep copy the preset
        from io import BytesIO

        preset_bytes = BytesIO()
        source_preset.write(preset_bytes)
        preset_bytes.seek(0)

        from .character_presets import FacePreset

        dest_presets.presets[dest_slot] = FacePreset.read(preset_bytes)

        # Update in raw data
        self._update_preset_in_raw_data(dest_slot, dest_presets.presets[dest_slot])
        return True

    def _update_preset_in_raw_data(self, slot_idx: int, preset) -> None:
        """Update preset in raw save data"""
        from io import BytesIO

        # Calculate offset in save file using tracked offsets
        userdata10_start = self._user_data_10_offset + 0x10  # Skip checksum

        # MenuSystemSaveLoad offset within USER_DATA_10
        # Version(4) + SteamID(8) + Settings(0x140)
        menu_offset = userdata10_start + 4 + 8 + 0x140

        # CSMenuSystemSaveLoad header is 8 bytes, each preset is 0x130
        preset_offset = menu_offset + 8 + (slot_idx * 0x130)

        # Write preset data
        preset_stream = BytesIO()
        preset.write(preset_stream)
        preset_data = preset_stream.getvalue()

        self._raw_data[preset_offset : preset_offset + len(preset_data)] = preset_data

        # Recalculate USER_DATA_10 checksum
        self._recalculate_userdata10_checksum()

    def _recalculate_userdata10_checksum(self) -> None:
        """Recalculate USER_DATA_10 MD5 checksum after preset modification"""
        import hashlib

        CHECKSUM_SIZE = 0x10

        userdata10_offset = self._user_data_10_offset
        userdata10_checksum_offset = userdata10_offset
        userdata10_data_offset = userdata10_offset + CHECKSUM_SIZE

        userdata10_data = self._raw_data[
            userdata10_data_offset : userdata10_data_offset + 0x60000
        ]
        md5_hash = hashlib.md5(userdata10_data).digest()
        self._raw_data[
            userdata10_checksum_offset : userdata10_checksum_offset + CHECKSUM_SIZE
        ] = md5_hash


def load_save(filepath: str) -> Save:
    """
    Convenience function to load a save file.

    Args:
        filepath: Path to file

    Returns:
        Parsed Save object
    """
    return Save.from_file(filepath)


# Main entry point for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        sys.exit(1)

    save_path = sys.argv[1]

    try:
        # Load and parse save file
        save = load_save(save_path)

        # Print summary
        save.print_summary()

    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)
