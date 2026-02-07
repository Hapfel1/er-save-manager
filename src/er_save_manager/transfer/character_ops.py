"""
Character operations for copying, transferring, and deleting characters.

Handles raw byte-level manipulation of character slots in save files.
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save


class CharacterOperations:
    """
    Character slot operations.

    Uses dynamically tracked offsets from Save instance instead of hardcoded values
    to ensure compatibility across different save file formats and versions.
    """

    SLOT_SIZE = 0x280010
    SLOT_DATA_SIZE = 0x280000
    CHECKSUM_SIZE = 16

    @staticmethod
    def get_slot_offset(save: Save, slot_index: int) -> int:
        """
        Get file offset for a character slot from tracked offsets.

        Args:
            save: Save instance with tracked offsets
            slot_index: Slot index (0-9)

        Returns:
            Absolute file offset for the slot
        """
        if not 0 <= slot_index <= 9:
            raise ValueError(f"Slot index must be 0-9, got {slot_index}")

        if not hasattr(save, "_slot_offsets") or not save._slot_offsets:
            raise RuntimeError("Save does not have tracked slot offsets")

        if slot_index >= len(save._slot_offsets):
            raise IndexError(f"Slot {slot_index} offset not tracked")

        return save._slot_offsets[slot_index]

    @staticmethod
    def get_user_data_10_offset(save: Save) -> int:
        """
        Get USER_DATA_10 offset from tracked offset.

        Args:
            save: Save instance with tracked offset

        Returns:
            Absolute file offset for USER_DATA_10
        """
        if not hasattr(save, "_user_data_10_offset"):
            raise RuntimeError("Save does not have tracked USER_DATA_10 offset")

        return save._user_data_10_offset

    @staticmethod
    def get_profile_summary_offsets(save: Save) -> tuple[int, int]:
        """
        Calculate ProfileSummary offsets based on parsed USER_DATA_10.

        Returns:
            Tuple of (active_slots_offset, profiles_base_offset)
        """
        if not save.user_data_10_parsed:
            raise RuntimeError("USER_DATA_10 not parsed")

        # Use actual parsed structure to find ProfileSummary location
        from io import BytesIO

        # Simulate reading up to ProfileSummary to get offset
        f = BytesIO(save._raw_data)
        f.seek(CharacterOperations.get_user_data_10_offset(save))

        # Skip checksum if PC
        if not save.is_ps:
            f.read(16)

        # Version (4 bytes)
        f.read(4)

        # SteamID (8 bytes)
        f.read(8)

        # Settings - read until size matched
        settings_start = f.tell()
        # Settings expected to take 0x140 bytes total (with padding)
        f.seek(settings_start + 0x140)

        # MenuSystemSaveLoad (0x1808 bytes)
        f.read(0x1808)

        profile_summary_start = f.tell()

        # IsProfileActive[10] - 10 bytes
        active_slots_offset = profile_summary_start

        # Profiles start after active slots
        profiles_base = profile_summary_start + 0xA

        return (active_slots_offset, profiles_base)

    @staticmethod
    def copy_slot(save: Save, from_slot: int, to_slot: int) -> None:
        """
        Copy character from one slot to another in the same save.

        Args:
            save: Save instance
            from_slot: Source slot index (0-9)
            to_slot: Destination slot index (0-9)
        """
        if from_slot == to_slot:
            raise ValueError("Source and destination slots cannot be the same")

        if not hasattr(save, "_raw_data"):
            raise RuntimeError("Save does not have raw data")

        # Ensure _raw_data is bytearray
        if isinstance(save._raw_data, bytes):
            save._raw_data = bytearray(save._raw_data)

        from_offset = CharacterOperations.get_slot_offset(save, from_slot)
        to_offset = CharacterOperations.get_slot_offset(save, to_slot)

        # Copy entire slot (checksum + data)
        save._raw_data[to_offset : to_offset + CharacterOperations.SLOT_SIZE] = (
            save._raw_data[from_offset : from_offset + CharacterOperations.SLOT_SIZE]
        )

        # Update profile summary in USER_DATA_10
        CharacterOperations._update_profile_summary(save, from_slot, to_slot)

        # Mark slot as active
        CharacterOperations._set_slot_active(save, to_slot, True)

        # Re-parse USER_DATA_10 to update parsed profile data
        CharacterOperations._reparse_user_data_10(save)

        # Re-parse the modified slot
        from io import BytesIO

        from er_save_manager.parser.user_data_x import UserDataX

        f = BytesIO(save._raw_data)
        f.seek(to_offset + CharacterOperations.CHECKSUM_SIZE)
        save.character_slots[to_slot] = UserDataX.read(
            f,
            save.is_ps,
            to_offset + CharacterOperations.CHECKSUM_SIZE,
            CharacterOperations.SLOT_DATA_SIZE,
        )

    @staticmethod
    def transfer_slot(
        source_save: Save, from_slot: int, target_save: Save, to_slot: int
    ) -> None:
        """
        Transfer character from one save file to another.

        Args:
            source_save: Source save instance
            from_slot: Source slot index (0-9)
            target_save: Target save instance
            to_slot: Destination slot index (0-9)
        """
        if not hasattr(source_save, "_raw_data") or not hasattr(
            target_save, "_raw_data"
        ):
            raise RuntimeError("Both saves must have raw data")

        # Ensure both are bytearray
        if isinstance(source_save._raw_data, bytes):
            source_save._raw_data = bytearray(source_save._raw_data)
        if isinstance(target_save._raw_data, bytes):
            target_save._raw_data = bytearray(target_save._raw_data)

        from_offset = CharacterOperations.get_slot_offset(source_save, from_slot)
        to_offset = CharacterOperations.get_slot_offset(target_save, to_slot)

        # Copy entire slot
        target_save._raw_data[to_offset : to_offset + CharacterOperations.SLOT_SIZE] = (
            source_save._raw_data[
                from_offset : from_offset + CharacterOperations.SLOT_SIZE
            ]
        )

        # Patch SteamID to match target save
        CharacterOperations._patch_steamid_in_slot(target_save, to_slot)

        # Update profile summary
        CharacterOperations._update_profile_summary_from_slot(target_save, to_slot)

        # Mark slot as active
        CharacterOperations._set_slot_active(target_save, to_slot, True)

        # Re-parse USER_DATA_10 to update parsed profile data
        CharacterOperations._reparse_user_data_10(target_save)

        # Re-parse the modified slot
        from io import BytesIO

        from er_save_manager.parser.user_data_x import UserDataX

        f = BytesIO(target_save._raw_data)
        f.seek(to_offset + CharacterOperations.CHECKSUM_SIZE)
        target_save.character_slots[to_slot] = UserDataX.read(
            f,
            target_save.is_ps,
            to_offset + CharacterOperations.CHECKSUM_SIZE,
            CharacterOperations.SLOT_DATA_SIZE,
        )

    @staticmethod
    def delete_slot(save: Save, slot_index: int) -> None:
        """
        Delete character from a slot.

        Args:
            save: Save instance
            slot_index: Slot index to delete (0-9)
        """
        if not hasattr(save, "_raw_data"):
            raise RuntimeError("Save does not have raw data")

        # Ensure _raw_data is bytearray
        if isinstance(save._raw_data, bytes):
            save._raw_data = bytearray(save._raw_data)

        slot_offset = CharacterOperations.get_slot_offset(save, slot_index)

        # Zero out the entire slot (checksum + data)
        save._raw_data[slot_offset : slot_offset + CharacterOperations.SLOT_SIZE] = (
            bytes(CharacterOperations.SLOT_SIZE)
        )

        # Clear profile summary
        CharacterOperations._clear_profile_summary(save, slot_index)

        # Mark slot as inactive
        CharacterOperations._set_slot_active(save, slot_index, False)

        # Re-parse USER_DATA_10 to update parsed profile data
        CharacterOperations._reparse_user_data_10(save)

        # Replace with empty slot object
        from er_save_manager.parser.user_data_x import UserDataX

        save.character_slots[slot_index] = UserDataX()

    @staticmethod
    def swap_slots(save: Save, slot_a: int, slot_b: int) -> None:
        """
        Swap two character slots.

        Args:
            save: Save instance
            slot_a: First slot index (0-9)
            slot_b: Second slot index (0-9)
        """
        if slot_a == slot_b:
            raise ValueError("Cannot swap a slot with itself")

        if not hasattr(save, "_raw_data"):
            raise RuntimeError("Save does not have raw data")

        # Ensure _raw_data is bytearray
        if isinstance(save._raw_data, bytes):
            save._raw_data = bytearray(save._raw_data)

        offset_a = CharacterOperations.get_slot_offset(save, slot_a)
        offset_b = CharacterOperations.get_slot_offset(save, slot_b)

        # Swap entire slots using temp buffer
        temp = bytes(
            save._raw_data[offset_a : offset_a + CharacterOperations.SLOT_SIZE]
        )
        save._raw_data[offset_a : offset_a + CharacterOperations.SLOT_SIZE] = (
            save._raw_data[offset_b : offset_b + CharacterOperations.SLOT_SIZE]
        )
        save._raw_data[offset_b : offset_b + CharacterOperations.SLOT_SIZE] = temp

        # Swap profile summaries
        CharacterOperations._swap_profile_summaries(save, slot_a, slot_b)

        # Swap active flags
        active_a = CharacterOperations._is_slot_active(save, slot_a)
        active_b = CharacterOperations._is_slot_active(save, slot_b)
        CharacterOperations._set_slot_active(save, slot_a, active_b)
        CharacterOperations._set_slot_active(save, slot_b, active_a)

        # Re-parse USER_DATA_10 to update parsed profile data
        CharacterOperations._reparse_user_data_10(save)

        # Re-parse both slots
        from io import BytesIO

        from er_save_manager.parser.user_data_x import UserDataX

        f = BytesIO(save._raw_data)

        for slot_idx, offset in [(slot_a, offset_a), (slot_b, offset_b)]:
            f.seek(offset + CharacterOperations.CHECKSUM_SIZE)
            save.character_slots[slot_idx] = UserDataX.read(
                f,
                save.is_ps,
                offset + CharacterOperations.CHECKSUM_SIZE,
                CharacterOperations.SLOT_DATA_SIZE,
            )

    @staticmethod
    def _update_profile_summary(save: Save, from_slot: int, to_slot: int) -> None:
        """Copy profile summary from one slot to another."""
        if not save.user_data_10_parsed or not save.user_data_10_parsed.profile_summary:
            return

        # Get actual ProfileSummary offsets from parsed structure
        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save)
        profile_size = 0x24C

        from_profile_offset = profiles_base + from_slot * profile_size
        to_profile_offset = profiles_base + to_slot * profile_size

        save._raw_data[to_profile_offset : to_profile_offset + profile_size] = (
            save._raw_data[from_profile_offset : from_profile_offset + profile_size]
        )

    @staticmethod
    def _update_profile_summary_from_slot(save: Save, slot_index: int) -> None:
        """Update profile summary from the character data in the slot."""
        # This reads name/level from the slot and updates the summary
        pass

    @staticmethod
    def _clear_profile_summary(save: Save, slot_index: int) -> None:
        """Clear profile summary for a slot."""
        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save)
        profile_size = 0x24C
        profile_offset = profiles_base + slot_index * profile_size

        save._raw_data[profile_offset : profile_offset + profile_size] = bytes(
            profile_size
        )

    @staticmethod
    def _swap_profile_summaries(save: Save, slot_a: int, slot_b: int) -> None:
        """Swap profile summaries between two slots."""
        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save)
        profile_size = 0x24C

        offset_a = profiles_base + slot_a * profile_size
        offset_b = profiles_base + slot_b * profile_size

        temp = bytes(save._raw_data[offset_a : offset_a + profile_size])
        save._raw_data[offset_a : offset_a + profile_size] = save._raw_data[
            offset_b : offset_b + profile_size
        ]
        save._raw_data[offset_b : offset_b + profile_size] = temp

    @staticmethod
    def _set_slot_active(save: Save, slot_index: int, active: bool) -> None:
        """Set slot active flag in USER_DATA_10."""
        active_slots_offset, _ = CharacterOperations.get_profile_summary_offsets(save)
        flag_offset = active_slots_offset + slot_index

        save._raw_data[flag_offset] = 1 if active else 0

    @staticmethod
    def _is_slot_active(save: Save, slot_index: int) -> bool:
        """Check if slot is active in USER_DATA_10."""
        active_slots_offset, _ = CharacterOperations.get_profile_summary_offsets(save)
        flag_offset = active_slots_offset + slot_index

        return save._raw_data[flag_offset] != 0

    @staticmethod
    def _patch_steamid_in_slot(save: Save, slot_index: int) -> None:
        """
        Patch SteamID in character slot to match USER_DATA_10.

        IMPORTANT: SteamID is ONLY in the character slot data, NOT in the
        profile summary. The profile summary contains character name, level,
        playtime, and other profile info, but NOT SteamID.
        """
        if not save.user_data_10_parsed:
            return

        # Ensure _raw_data is bytearray
        if isinstance(save._raw_data, bytes):
            save._raw_data = bytearray(save._raw_data)

        # Get SteamID from USER_DATA_10
        target_steamid = save.user_data_10_parsed.steam_id
        if target_steamid == 0:
            return

        # SteamID is near the end of character data (in the slot, not profile summary)
        slot_char = save.character_slots[slot_index]
        if not slot_char.is_empty() and hasattr(slot_char, "steamid_offset"):
            slot_offset = CharacterOperations.get_slot_offset(save, slot_index)
            steamid_offset = (
                slot_offset
                + CharacterOperations.CHECKSUM_SIZE
                + slot_char.steamid_offset
            )

            # Write SteamID as uint64 little-endian
            struct.pack_into("<Q", save._raw_data, steamid_offset, target_steamid)

    @staticmethod
    def _reparse_user_data_10(save: Save) -> None:
        """
        Re-parse USER_DATA_10 to update the parsed profile summary.

        This is critical after modifying profile data in raw bytes -
        otherwise the Save object's parsed data won't match the file.
        """
        from io import BytesIO

        from er_save_manager.parser.user_data_10 import UserData10

        # Re-parse USER_DATA_10 from updated raw data
        f = BytesIO(save._raw_data)
        f.seek(CharacterOperations.get_user_data_10_offset(save))

        try:
            save.user_data_10_parsed = UserData10.read(f, save.is_ps)
        except Exception as e:
            # If parsing fails, clear the old parsed data
            save.user_data_10_parsed = None
            print(f"Warning: Failed to re-parse USER_DATA_10: {e}")

    @staticmethod
    def export_character(save: Save, slot_index: int, output_path: str) -> None:
        """
        Export character to standalone .erc file.

        File format:
        - Magic: "ERC\0" (4 bytes)
        - Version: uint32 (1)
        - Active flag: uint8 (1 byte) - whether slot was active
        - Slot size: uint32
        - Character data: full slot data
        - Profile size: uint32
        - Profile data: 0x24C bytes (CSProfileSummary entry)
        - Checksum: MD5 of all above data (16 bytes)

        Args:
            save: Save instance
            slot_index: Slot to export (0-9)
            output_path: Output file path
        """
        if not hasattr(save, "_raw_data"):
            raise RuntimeError("Save does not have raw data")

        # Ensure _raw_data is bytearray
        if isinstance(save._raw_data, bytes):
            save._raw_data = bytearray(save._raw_data)

        char = save.character_slots[slot_index]
        if char.is_empty():
            raise ValueError(f"Slot {slot_index} is empty")

        slot_offset = CharacterOperations.get_slot_offset(save, slot_index)

        # Get slot data (without checksum)
        slot_data = bytes(
            save._raw_data[
                slot_offset + CharacterOperations.CHECKSUM_SIZE : slot_offset
                + CharacterOperations.SLOT_SIZE
            ]
        )

        # Get profile summary using calculated offsets
        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save)
        profile_size = 0x24C
        profile_offset = profiles_base + slot_index * profile_size
        profile_data = bytes(
            save._raw_data[profile_offset : profile_offset + profile_size]
        )

        # Validate profile data size
        if len(profile_data) != profile_size:
            raise ValueError(
                f"Failed to extract full profile data during export: "
                f"expected {profile_size} bytes, got {len(profile_data)} bytes. "
                f"Save may be corrupted."
            )

        # Get active flag
        is_active = CharacterOperations._is_slot_active(save, slot_index)

        # Build file
        import hashlib

        with open(output_path, "wb") as f:
            # Magic
            f.write(b"ERC\x00")
            # Version
            f.write(struct.pack("<I", 1))
            # Active flag (1 byte)
            f.write(struct.pack("<B", 1 if is_active else 0))
            # Slot data size
            f.write(struct.pack("<I", len(slot_data)))
            # Slot data
            f.write(slot_data)
            # Profile size
            f.write(struct.pack("<I", len(profile_data)))
            # Profile data
            f.write(profile_data)

        # Calculate and append checksum
        with open(output_path, "rb") as f:
            data = f.read()

        checksum = hashlib.md5(data).digest()

        with open(output_path, "ab") as f:
            f.write(checksum)

    @staticmethod
    def import_character(save: Save, slot_index: int, input_path: str) -> str:
        """
        Import character from .erc file.

        Args:
            save: Save instance
            slot_index: Target slot (0-9)
            input_path: Input .erc file path

        Returns:
            Name of imported character
        """
        if not hasattr(save, "_raw_data"):
            raise RuntimeError("Save does not have raw data")

        # Ensure _raw_data is bytearray
        if isinstance(save._raw_data, bytes):
            save._raw_data = bytearray(save._raw_data)

        with open(input_path, "rb") as f:
            # Verify magic
            magic = f.read(4)
            if magic != b"ERC\x00":
                raise ValueError("Invalid .erc file: bad magic")

            # Read version
            version = struct.unpack("<I", f.read(4))[0]
            if version != 1:
                raise ValueError(f"Unsupported .erc version: {version}")

            # Read active flag (added in version 1)
            active_flag = struct.unpack("<B", f.read(1))[0]
            bool(active_flag)

            # Read slot data
            slot_size = struct.unpack("<I", f.read(4))[0]
            slot_data = f.read(slot_size)

            # Read profile data
            profile_size = struct.unpack("<I", f.read(4))[0]
            if profile_size != 0x24C:
                raise ValueError(
                    f"Profile size mismatch in .erc file: expected 0x24C ({0x24C}) bytes, "
                    f"got {profile_size} ({hex(profile_size)}). The .erc file may be corrupted."
                )
            profile_data = f.read(profile_size)

            if len(profile_data) != profile_size:
                raise ValueError(
                    f"Failed to read full profile data from .erc file: "
                    f"expected {profile_size} bytes, got {len(profile_data)} bytes. "
                    f"The .erc file may be truncated."
                )

            print(
                f"[CharacterOps] Read .erc file: slot_data={len(slot_data)} bytes, "
                f"profile_data={len(profile_data)} bytes"
            )

            # Read checksum
            checksum_expected = f.read(16)

        # Verify checksum
        with open(input_path, "rb") as f:
            # Read everything except last 16 bytes (checksum)
            f.seek(0)
            data_to_hash = f.read()
            data_to_hash = data_to_hash[:-16]  # Remove checksum from end

            import hashlib

            checksum_actual = hashlib.md5(data_to_hash).digest()

            if checksum_actual != checksum_expected:
                raise ValueError("Checksum mismatch - file may be corrupted")

        # Write to slot
        slot_offset = CharacterOperations.get_slot_offset(save, slot_index)

        # IMPORTANT: Clear the ENTIRE slot first to avoid residual data from previous character
        # This prevents issues when overwriting a character with a different one
        save._raw_data[slot_offset : slot_offset + CharacterOperations.SLOT_SIZE] = (
            bytes(CharacterOperations.SLOT_SIZE)
        )

        # Write slot data (checksum remains zeroed, will recalculate later)
        save._raw_data[
            slot_offset + CharacterOperations.CHECKSUM_SIZE : slot_offset
            + CharacterOperations.CHECKSUM_SIZE
            + len(slot_data)
        ] = slot_data

        # Clear and write profile data using calculated offsets
        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save)
        profile_size = 0x24C
        profile_offset = profiles_base + slot_index * profile_size

        # Validate profile data size
        if len(profile_data) != profile_size:
            raise ValueError(
                f"Profile data size mismatch: expected {profile_size} bytes, "
                f"got {len(profile_data)} bytes. The .erc file may be corrupted."
            )

        print(
            f"[CharacterOps] Writing profile data to slot {slot_index} at offset {hex(profile_offset)}"
        )

        # Clear the profile entry first to avoid residual data
        save._raw_data[profile_offset : profile_offset + profile_size] = bytes(
            profile_size
        )

        # Write new profile data (always full 0x24C bytes)
        save._raw_data[profile_offset : profile_offset + profile_size] = profile_data

        print("[CharacterOps] Profile data written successfully")

        # Set slot as active (imported characters should be active by default)
        CharacterOperations._set_slot_active(save, slot_index, True)

        # Patch SteamID
        CharacterOperations._patch_steamid_in_slot(save, slot_index)

        # Re-parse USER_DATA_10 to update parsed profile data
        CharacterOperations._reparse_user_data_10(save)

        # Re-parse slot
        from io import BytesIO

        from er_save_manager.parser.user_data_x import UserDataX

        f = BytesIO(save._raw_data)
        f.seek(slot_offset + CharacterOperations.CHECKSUM_SIZE)
        save.character_slots[slot_index] = UserDataX.read(
            f,
            save.is_ps,
            slot_offset + CharacterOperations.CHECKSUM_SIZE,
            CharacterOperations.SLOT_DATA_SIZE,
        )

        # CRITICAL: Recalculate checksums for the modified slot and USER_DATA_10
        # Without this, the save file will be corrupted and the game won't load it
        save.recalculate_checksums()

        return save.character_slots[slot_index].get_character_name()

    @staticmethod
    def extract_character_metadata(save: Save, slot_index: int) -> dict:
        """
        Extract comprehensive metadata from a character for community sharing.

        Args:
            save: Save instance
            slot_index: Slot index (0-9)

        Returns:
            Dictionary with character metadata including:
            - Basic info (name, level, class, gender)
            - Stats (vigor, mind, endurance, etc.)
            - Playtime and NG+ cycle
            - Equipment and inventory summary
            - DLC item detection
        """
        char = save.character_slots[slot_index]
        if char.is_empty():
            raise ValueError(f"Slot {slot_index} is empty")

        player_data = char.player_game_data

        # Basic character info
        from er_save_manager.data.starting_classes import STARTING_CLASSES

        profile = None
        try:
            if save.user_data_10_parsed and save.user_data_10_parsed.profile_summary:
                profiles = save.user_data_10_parsed.profile_summary.profiles
                if profiles and slot_index < len(profiles):
                    profile = profiles[slot_index]
        except Exception:
            profile = None

        archetype_id = None
        if profile and profile.archetype is not None:
            archetype_id = profile.archetype
        else:
            archetype_id = player_data.archetype

        class_data = STARTING_CLASSES.get(archetype_id, None)
        char_class = class_data["name"] if class_data else "Unknown"

        playtime_seconds = profile.seconds_played if profile else 0
        playtime_formatted = CharacterOperations._format_playtime(playtime_seconds)

        body_type = None
        if profile and profile.body_type is not None:
            body_type = "Type A" if profile.body_type == 0 else "Type B"

        metadata = {
            "name": player_data.character_name,
            "level": player_data.level,
            "class": char_class,
            "body_type": body_type,
            # Stats
            "stats": {
                "vigor": player_data.vigor,
                "mind": player_data.mind,
                "endurance": player_data.endurance,
                "strength": player_data.strength,
                "dexterity": player_data.dexterity,
                "intelligence": player_data.intelligence,
                "faith": player_data.faith,
                "arcane": player_data.arcane,
            },
            "runes": player_data.runes,
            # Playtime (from USER_DATA_10 ProfileSummary)
            "playtime_seconds": playtime_seconds,
            "playtime": playtime_formatted,
            # NG+ detection - check if any NG+1 flags are set
            "ng_plus": CharacterOperations._detect_ng_plus(save, slot_index),
            # Equipment
            "equipment": CharacterOperations._extract_equipment_summary(char),
            # DLC access detection (checks if character has Shadow of the Erdtree flag)
            "has_dlc": CharacterOperations._has_dlc_access(char),
        }

        return metadata

    @staticmethod
    def _detect_ng_plus(save: Save, slot_index: int) -> int:
        """
        Detect NG+ cycle by checking event flags.

        Returns:
            NG+ cycle number (0 for first playthrough, 1 for NG+1, etc.)
        """
        # NG+ cycles are tracked via event flags
        # Flag 10000799 = Beat final boss (NG)
        # Flag 10001799 = Beat final boss (NG+1)
        # Flag 10002799 = Beat final boss (NG+2)
        # etc.

        try:
            from er_save_manager.parser.event_flags import EventFlagManager

            # Get event flags for character
            event_flags = save.character_slots[slot_index].gaitem
            if not event_flags:
                return 0

            # Check NG+ progression flags
            for ng_cycle in range(7, 0, -1):  # Check NG+7 down to NG+1
                flag_id = 10000799 + (ng_cycle * 1000)
                if EventFlagManager.get_flag_state(event_flags, flag_id):
                    return ng_cycle

            return 0
        except Exception:
            return 0

    @staticmethod
    def _extract_equipment_summary(char) -> dict:
        """Extract summary of equipped items with names resolved."""
        try:
            from er_save_manager.data.item_database import ItemCategory, get_item_name

            equipped = None
            if hasattr(char, "equipped_items_item_id"):
                equipped = char.equipped_items_item_id
            if not equipped and hasattr(char, "equipped_items"):
                equipped = char.equipped_items
            if not equipped:
                return {}

            def resolve_item(item_id: int, category: ItemCategory) -> dict | None:
                """Resolve item ID to name and ID with proper category bits."""
                # Filter out empty/placeholder slots
                if item_id == 0 or item_id == 0xFFFFFFFF or item_id == 110000:
                    return None
                # Add category bits to the base ID
                full_id = category | item_id
                return {"id": item_id, "name": get_item_name(full_id)}

            equipment = {}

            # Weapons (right and left hand)
            for hand in ["right_hand", "left_hand"]:
                for i in [1, 2, 3]:
                    item_id = getattr(equipped, f"{hand}_armament{i}", 0)
                    item = resolve_item(item_id, ItemCategory.WEAPON)
                    if item:
                        equipment[f"{hand}_{i}"] = item

            # Armor (skip if 0 or 0xFFFFFFFF)
            for slot in ["head", "chest", "arms", "legs"]:
                item_id = getattr(equipped, slot, 0)
                item = resolve_item(item_id, ItemCategory.ARMOR)
                if item:
                    equipment[slot] = item

            # Talismans (skip if 0 or 0xFFFFFFFF)
            talismans = []
            for i in range(1, 5):
                item_id = getattr(equipped, f"talisman{i}", 0)
                item = resolve_item(item_id, ItemCategory.TALISMAN)
                if item:
                    talismans.append(item)
            if talismans:
                equipment["talismans"] = talismans

            return equipment
        except Exception:
            return {}

    @staticmethod
    def _format_playtime(seconds: int) -> str:
        """Format playtime seconds as Hh Mm Ss."""
        if not seconds or seconds < 0:
            return "0h 0m 0s"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs}s"

    @staticmethod
    def _has_dlc_access(char) -> bool:
        """Check if character has Shadow of the Erdtree DLC access (via DLC flag)."""
        try:
            if hasattr(char, "has_dlc_flag"):
                return bool(char.has_dlc_flag())
        except Exception:
            return False
        return False

    @staticmethod
    def _detect_dlc_items(char) -> bool:
        """
        Detect if character has any DLC (Shadow of the Erdtree) items.

        DLC items have IDs in specific ranges:
        - Weapons: 41000000-42000000
        - Armor: 43000000-44000000
        - Talismans: 2100-2200
        - Ashes of War: 850000-860000
        """
        try:
            # Check equipped items
            equipped = char.equipped_items
            if equipped:
                # Check weapons
                for weapon in [
                    equipped.right_hand_armament_1,
                    equipped.right_hand_armament_2,
                    equipped.right_hand_armament_3,
                    equipped.left_hand_armament_1,
                    equipped.left_hand_armament_2,
                    equipped.left_hand_armament_3,
                ]:
                    if weapon and 41000000 <= weapon < 42000000:
                        return True

                # Check armor
                for armor in [
                    equipped.head_armor,
                    equipped.chest_armor,
                    equipped.arms_armor,
                    equipped.legs_armor,
                ]:
                    if armor and 43000000 <= armor < 44000000:
                        return True

                # Check talismans
                for talisman in [
                    equipped.talisman_1,
                    equipped.talisman_2,
                    equipped.talisman_3,
                    equipped.talisman_4,
                ]:
                    if talisman and 2100 <= talisman < 2200:
                        return True

            # TODO: Check inventory items when inventory parsing is implemented

            return False
        except Exception:
            return False
