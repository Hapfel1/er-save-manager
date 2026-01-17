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
        # We need to calculate where ProfileSummary starts within USER_DATA_10
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

        # Settings - read until we match the size
        settings_start = f.tell()
        # Settings expected to take 0x140 bytes total (with padding)
        f.seek(settings_start + 0x140)

        # MenuSystemSaveLoad (0x1808 bytes)
        f.read(0x1808)

        # Now we're at ProfileSummary
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
        # For now, we'll keep existing summary logic from the copy
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

        The SteamID in each character slot must match the one in USER_DATA_10.
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

        # SteamID is near the end of character data
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
            # If parsing fails, at least clear the old parsed data
            save.user_data_10_parsed = None
            print(f"Warning: Failed to re-parse USER_DATA_10: {e}")

    @staticmethod
    def export_character(save: Save, slot_index: int, output_path: str) -> None:
        """
        Export character to standalone .erc file.

        File format:
        - Magic: "ERC\0" (4 bytes)
        - Version: uint32 (1)
        - Slot size: uint32
        - Character data: full slot data
        - Profile data: 0x24C bytes
        - Checksum: MD5 of data

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

        # Build file
        import hashlib

        with open(output_path, "wb") as f:
            # Magic
            f.write(b"ERC\x00")
            # Version
            f.write(struct.pack("<I", 1))
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

            # Read slot data
            slot_size = struct.unpack("<I", f.read(4))[0]
            slot_data = f.read(slot_size)

            # Read profile data
            profile_size = struct.unpack("<I", f.read(4))[0]
            profile_data = f.read(profile_size)

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

        # Clear checksum (will recalculate later)
        save._raw_data[
            slot_offset : slot_offset + CharacterOperations.CHECKSUM_SIZE
        ] = bytes(CharacterOperations.CHECKSUM_SIZE)

        # Write slot data
        save._raw_data[
            slot_offset + CharacterOperations.CHECKSUM_SIZE : slot_offset
            + CharacterOperations.CHECKSUM_SIZE
            + len(slot_data)
        ] = slot_data

        # Write profile data using calculated offsets
        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save)
        profile_offset = profiles_base + slot_index * 0x24C
        save._raw_data[profile_offset : profile_offset + len(profile_data)] = (
            profile_data
        )

        # Mark slot as active
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

        return save.character_slots[slot_index].get_character_name()
