"""
Elden Ring Save Parser - Save File (Main Entry Point)

Handles complete save file with 10 character slots, checksums, and platform detection.
Based on ER-Save-Lib Rust implementation.
"""

from __future__ import annotations

import logging
import os
import struct
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from er_save_manager.own_writes import record_write
from er_save_manager.parser.user_data_10 import UserData10
from er_save_manager.parser.user_data_x import UserDataX

logger = logging.getLogger(__name__)


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

    magic: bytes = b""
    is_ps: bool = False

    header: bytes = b""

    character_slots: list[UserDataX] = field(default_factory=list)

    user_data_10_parsed: UserData10 | None = None

    user_data_10: bytes = b""
    user_data_11: bytes = b""

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
        if isinstance(self._raw_data, bytes) and not isinstance(
            self._raw_data, bytearray
        ):
            self._raw_data = bytearray(self._raw_data)

    def __setattr__(self, name, value):
        """Override to ensure _raw_data is always bytearray"""
        if name == "_raw_data":
            if isinstance(value, bytes) and not isinstance(value, bytearray):
                value = bytearray(value)
        super().__setattr__(name, value)

    @property
    def is_convergence(self) -> bool:
        """
        Check if this save is for the Convergence mod.

        Returns:
            True if ".cnv" appears anywhere in the save filename
            (e.g. .cnv, .cnv.co2, .cnv.co3).
        """
        if hasattr(self, "_original_filepath") and self._original_filepath:
            filepath = self._original_filepath.lower()
            return ".cnv" in filepath
        return False

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

        if len(data) < 4:
            raise ValueError(f"Save file is empty or too small: {filepath}")

        f = BytesIO(data)
        obj = cls()

        # Track original filepath for save() method
        obj._original_filepath = filepath

        if isinstance(data, bytes):
            obj._raw_data = bytearray(data)
        else:
            obj._raw_data = data

        assert isinstance(obj._raw_data, bytearray), (
            f"_raw_data is {type(obj._raw_data)}, not bytearray!"
        )

        # Verify it's mutable and non-empty
        try:
            obj._raw_data[0] = obj._raw_data[0]  # Test write
        except TypeError as e:
            raise TypeError(
                f"_raw_data is not writable! Type: {type(obj._raw_data)}"
            ) from e

        obj.magic = f.read(4)

        # PC saves start with BND4. Both Apollo and Save Wizard PS exports start with cb019c2c.
        if obj.magic in (b"BND4", b"SL2\x00"):
            obj.is_ps = False
        elif obj.magic == bytes([0xCB, 0x01, 0x9C, 0x2C]):
            obj.is_ps = True
        else:
            raise ValueError(f"Invalid save file magic: {obj.magic.hex()}")

        if obj.is_ps:
            header_size = 0x6C
        else:
            header_size = 0x2FC

        obj.header = f.read(header_size)

        for _slot_index in range(10):
            slot_start = f.tell()

            obj._slot_offsets.append(slot_start)

            # Read checksum (PC only)
            checksum = None
            if not obj.is_ps:
                checksum = f.read(16)

                if len(checksum) < 16:
                    obj.character_slots.append(UserDataX())
                    break  # No more slots

                checksum.hex()

                # Check if slot is empty (all zeros checksum)
                if checksum == bytes(16):
                    f.read(0x280000)
                    obj.character_slots.append(UserDataX())
                    continue

            char_data_start = f.tell()

            slot_data_size = 0x280000

            try:
                char = UserDataX.read(f, obj.is_ps, char_data_start, slot_data_size)
                obj.character_slots.append(char)

                if char.is_empty():
                    pass
                else:
                    if char.has_torrent_bug():
                        pass
                    if char.has_weather_corruption():
                        pass
                    if char.has_time_corruption():
                        pass

            except Exception:
                obj.character_slots.append(UserDataX())
                correct_position = slot_start + 0x280010
                f.seek(correct_position)

        obj._slot_digests = obj._digest_slots()

        user_data_10_start = f.tell()
        obj._user_data_10_offset = user_data_10_start

        try:
            obj.user_data_10_parsed = UserData10.read(f, obj.is_ps)

            # Also keep raw bytes
            user_data_10_end = f.tell()
            f.seek(user_data_10_start)
            obj.user_data_10 = f.read(user_data_10_end - user_data_10_start)
            f.seek(user_data_10_end)
        except Exception:
            f.seek(user_data_10_start)
            if not obj.is_ps:
                f.read(16)  # Skip checksum
            obj.user_data_10 = f.read(0x60000)

        if not obj.is_ps:
            f.read(16)  # Skip checksum

        if obj.is_ps:
            obj.user_data_11 = f.read(0x240010)
        else:
            obj.user_data_11 = f.read(0x240010)

        return obj

    def _digest_slots(self) -> dict[int, bytes]:
        """MD5 of each non-empty slot's data, to tell which slots were edited."""
        import hashlib

        digests = {}
        for idx, slot in enumerate(self.character_slots):
            if slot.is_empty() or not getattr(slot, "data_start", 0):
                continue
            data = self._raw_data[slot.data_start : slot.data_start + 0x280000]
            digests[idx] = hashlib.md5(data).digest()
        return digests

    def _refresh_player_data_hashes(self) -> None:
        """Recompute PlayerGameDataHash for every slot edited since load.

        Untouched slots keep the hash the game wrote. Slot MD5s are redone
        afterwards when any hash changed.
        """
        from er_save_manager.parser import player_data_hash

        if isinstance(self._raw_data, bytes):
            self._raw_data = bytearray(self._raw_data)
        before = getattr(self, "_slot_digests", None)
        current = self._digest_slots()
        changed = False
        for idx, digest in current.items():
            if before is not None and before.get(idx) == digest:
                continue
            slot = self.character_slots[idx]
            if not getattr(slot, "player_data_hash_offset", 0):
                continue
            try:
                changed |= player_data_hash.refresh(self._raw_data, slot)
            except (struct.error, IndexError):
                logger.exception("PlayerGameDataHash refresh failed for slot %d", idx)
        if changed:
            self.recalculate_checksums()
        self._slot_digests = self._digest_slots()

    def recalculate_checksums(self):
        """
        Recalculate MD5 checksums for all active slots

        This is called after making modifications to ensure
        the save file integrity is maintained
        """
        if not hasattr(self, "_raw_data"):
            raise RuntimeError("Cannot recalculate checksums: raw data not available")

        # PS saves have no per-slot or USER_DATA_10 checksums - nothing to do
        if self.is_ps:
            return

        import hashlib

        SLOT_SIZE = 0x280000
        CHECKSUM_SIZE = 0x10

        for slot_idx in range(10):
            slot = self.character_slots[slot_idx]
            if slot.is_empty():
                continue

            slot_offset = self._slot_offsets[slot_idx]
            checksum_offset = slot_offset
            data_offset = slot_offset + CHECKSUM_SIZE

            char_data = self._raw_data[data_offset : data_offset + SLOT_SIZE]
            md5_hash = hashlib.md5(char_data).digest()

            self._raw_data[checksum_offset : checksum_offset + CHECKSUM_SIZE] = md5_hash

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

        Writes to a temporary file in the same directory, then atomically
        replaces the destination. A same-path truncate and write keeps the
        file identity, so Steam Cloud sync, an antivirus scanner or the game
        can keep reading a stale or partial view. The replace gives the file
        a new identity and never leaves a half-written save behind.

        Args:
            filepath: Path where save file will be written
        """
        if not hasattr(self, "_raw_data"):
            raise RuntimeError("Cannot write save file: raw data not available")

        self._refresh_player_data_hashes()

        target = Path(filepath)
        tmp_path = target.with_name(f"{target.name}.tmp{os.getpid()}")

        try:
            with open(tmp_path, "wb") as f:
                f.write(self._raw_data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise
        record_write(target)

    def get_active_slots(self) -> list[int]:
        """
        Get list of slot indices that are marked as active in CSProfileSummary.
        This is the authoritative source - checks the active flag in USER_DATA_10,
        not just whether the slot has data.

        Returns:
            List of slot indices (0-9) that are active
        """
        # Use the active flags from CSProfileSummary if available
        if self.user_data_10_parsed and self.user_data_10_parsed.profile_summary:
            active_flags = self.user_data_10_parsed.profile_summary.active_profiles
            return [i for i in range(10) if i < len(active_flags) and active_flags[i]]

        # Fallback to checking if slot is not empty (old behavior)
        return [i for i, slot in enumerate(self.character_slots) if not slot.is_empty()]

    def slot_data_offset(self, slot_idx: int) -> int:
        """Return the absolute offset of slot data, skipping the checksum prefix on PC."""
        base = self._slot_offsets[slot_idx]
        return base if self.is_ps else base + 0x10

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
                if self.user_data_10_parsed and slot_index < len(
                    self.user_data_10_parsed.profile_summary.profiles
                ):
                    profile = self.user_data_10_parsed.profile_summary.profiles[
                        slot_index
                    ]
                    profile.seconds_played // 3600
                    (profile.seconds_played % 3600) // 60

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
                    self._raw_data[
                        slot.horse_offset : slot.horse_offset + len(horse_data)
                    ] = horse_data
                    fixes.append(f"State changed to {horse.state.name}")

        # Fix 2: SteamId corruption
        correct_steam_id = None
        if self.user_data_10_parsed and hasattr(self.user_data_10_parsed, "steam_id"):
            correct_steam_id = self.user_data_10_parsed.steam_id

        if slot.has_steamid_corruption(correct_steam_id):
            if correct_steam_id is not None:
                slot.steam_id = correct_steam_id

                if hasattr(slot, "steamid_offset") and slot.steamid_offset > 0:
                    import struct

                    steamid_bytes = struct.pack("<Q", correct_steam_id)
                    self._raw_data[slot.steamid_offset : slot.steamid_offset + 8] = (
                        steamid_bytes
                    )
                    fixes.append(f"SteamId set to {correct_steam_id}")

        # Fix 3: Time corruption
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
                if self.user_data_10_parsed and hasattr(
                    self.user_data_10_parsed, "profile_summary"
                ):
                    profile_summary = self.user_data_10_parsed.profile_summary
                    if slot_index < len(profile_summary.profiles):
                        profile = profile_summary.profiles[slot_index]
                        seconds_played = profile.seconds_played

                        hours = seconds_played // 3600
                        minutes = (seconds_played % 3600) // 60
                        seconds = seconds_played % 60

                        time.hour = hours
                        time.minute = minutes
                        time.second = seconds

                        if hasattr(slot, "time_offset") and slot.time_offset > 0:
                            time_bytes = BytesIO()
                            time.write(time_bytes)
                            time_data = time_bytes.getvalue()
                            self._raw_data[
                                slot.time_offset : slot.time_offset + len(time_data)
                            ] = time_data
                            fixes.append(
                                f"Time set to {hours:02d}:{minutes:02d}:{seconds:02d}"
                            )

        # Fix 4: Weather corruption
        if slot.has_weather_corruption():
            weather = slot.world_area_weather
            if weather and hasattr(slot, "map_id") and slot.map_id:
                # AreaId mirrors MapId[3]
                weather.area_id = slot.map_id.data[3]

                if hasattr(slot, "weather_offset") and slot.weather_offset > 0:
                    weather_bytes = BytesIO()
                    weather.write(weather_bytes)
                    weather_data = weather_bytes.getvalue()
                    self._raw_data[
                        slot.weather_offset : slot.weather_offset + len(weather_data)
                    ] = weather_data
                    fixes.append(f"AreaId set to {weather.area_id}")

        # Fix 5: Event flag corruption (Ranni quest + warp sickness)
        has_event_corruption, all_issues = slot.has_corruption()
        event_flag_issues = [
            issue for issue in all_issues if issue.startswith("eventflag:")
        ]

        if event_flag_issues:
            try:
                from .event_flags import CorruptionFixer

                issue_names = [
                    issue.replace("eventflag:", "") for issue in event_flag_issues
                ]

                event_flags_mutable = bytearray(slot.event_flags)

                fixes_count, fix_descriptions = CorruptionFixer.fix_all(
                    event_flags_mutable, issue_names
                )

                slot.event_flags = bytes(event_flags_mutable)

                if hasattr(slot, "event_flags_offset") and slot.event_flags_offset > 0:
                    self._raw_data[
                        slot.event_flags_offset : slot.event_flags_offset
                        + len(event_flags_mutable)
                    ] = event_flags_mutable
                else:
                    # Fallback: derive from the tracked slot offset.
                    # Event flags sit at 0x8F7 within character data.
                    EVENT_FLAGS_OFFSET_IN_SLOT = 0x8F7

                    event_flags_start = (
                        self.slot_data_offset(slot_index) + EVENT_FLAGS_OFFSET_IN_SLOT
                    )
                    self._raw_data[
                        event_flags_start : event_flags_start + len(event_flags_mutable)
                    ] = event_flags_mutable

                for fix_desc in fix_descriptions:
                    fixes.append(f"{fix_desc}")
            except Exception:
                # Log error but don't fail the whole fix operation
                import traceback

                traceback.print_exc()

        # Fix: invalid slot checksum
        try:
            from er_save_manager.fixes.checksum import check_slot_checksum

            valid, stored, computed = check_slot_checksum(self, slot_index)
            if not valid:
                checksum_offset = slot.data_start - 0x10
                self._raw_data[checksum_offset : checksum_offset + 0x10] = (
                    bytes.fromhex(computed)
                )
                fixes.append(
                    f"Slot checksum recalculated ({stored[:8]}... -> {computed[:8]}...)"
                )
        except Exception:
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
            with open(json_path) as f:
                data = json.load(f)

            if "presets" not in data:
                return False

            if preset_slot < 0 or preset_slot >= len(data["presets"]):
                return False

            preset_entry = data["presets"][preset_slot]
            preset_data = preset_entry.get("data", {})

            new_preset = FacePreset.from_dict(preset_data)

            dest_presets = self.get_character_presets()
            if not dest_presets:
                return False

            if dest_slot < 0 or dest_slot >= 15:
                return False

            dest_presets.presets[dest_slot] = new_preset

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

            dest_presets = self.get_character_presets()
            if not dest_presets:
                return False

            if dest_slot < 0 or dest_slot >= 15:
                return False

            dest_presets.presets[dest_slot] = new_preset

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

            empty_preset = FacePreset()

            presets.presets[slot] = empty_preset

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

        self._update_preset_in_raw_data(dest_slot, dest_presets.presets[dest_slot])
        return True

    def _update_preset_in_raw_data(self, slot_idx: int, preset) -> None:
        """Update preset in raw save data"""
        from io import BytesIO

        userdata10_start = self._user_data_10_offset + 0x10  # Skip checksum

        # MenuSystemSaveLoad offset within USER_DATA_10
        # Version(4) + SteamID(8) + Settings(0x140)
        menu_offset = userdata10_start + 4 + 8 + 0x140

        # CSMenuSystemSaveLoad header is 8 bytes, each preset is 0x130
        preset_offset = menu_offset + 8 + (slot_idx * 0x130)

        preset_stream = BytesIO()
        preset.write(preset_stream)
        preset_data = preset_stream.getvalue()

        # The first 8 bytes of Preset 0 physically overlap the global array
        # header. Preserve the existing header or the array is corrupted.
        if slot_idx == 0:
            preset_data = (
                self._raw_data[preset_offset : preset_offset + 8] + preset_data[8:]
            )

        self._raw_data[preset_offset : preset_offset + len(preset_data)] = preset_data

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


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        sys.exit(1)

    save_path = sys.argv[1]

    try:
        save = load_save(save_path)

        save.print_summary()

    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)
