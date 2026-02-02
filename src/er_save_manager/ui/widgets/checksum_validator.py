"""
Checksum Validator Widget for Hex Editor

Validates and recalculates MD5 checksums for Elden Ring save files.
PC saves have MD5 checksums (16 bytes) before each character slot.
"""

import hashlib
from dataclasses import dataclass


@dataclass
class ChecksumInfo:
    """Information about a checksum in the save file."""

    slot_index: int  # 0-9 for character slots
    checksum_offset: int  # Where the MD5 checksum is stored
    data_offset: int  # Where the character data starts
    data_size: int  # Size of character data to hash
    expected_checksum: bytes  # Current checksum in file
    calculated_checksum: bytes | None = None  # Recalculated checksum
    is_valid: bool | None = None  # Whether checksums match


class ChecksumValidator:
    """Validates and manages checksums for Elden Ring save files."""

    # PC save file constants
    SLOT_SIZE = 0x280000  # Total size per slot (2,621,440 bytes)
    CHECKSUM_SIZE = 0x10  # MD5 checksum size (16 bytes)
    DATA_SIZE = 0x27FFF0  # Character data size (2,621,424 bytes)
    FIRST_SLOT_OFFSET = 0x300  # First slot starts at offset 0x300
    NUM_SLOTS = 10  # 10 character slots

    def __init__(self, save_data: bytes):
        """
        Initialize validator with save file data.

        Args:
            save_data: Complete save file binary data
        """
        self.save_data = save_data
        self.checksums: list[ChecksumInfo] = []
        self._detect_checksums()

    def _detect_checksums(self):
        """Detect all character slot checksums in the save file."""
        self.checksums = []

        for slot_index in range(self.NUM_SLOTS):
            checksum_offset = self.FIRST_SLOT_OFFSET + (slot_index * self.SLOT_SIZE)
            data_offset = checksum_offset + self.CHECKSUM_SIZE

            # Check if offsets are within file bounds
            if data_offset + self.DATA_SIZE > len(
                self.save_data
            ) or checksum_offset + self.CHECKSUM_SIZE > len(self.save_data):
                break

            # Extract checksum from file
            expected_checksum = self.save_data[
                checksum_offset : checksum_offset + self.CHECKSUM_SIZE
            ]

            checksum_info = ChecksumInfo(
                slot_index=slot_index,
                checksum_offset=checksum_offset,
                data_offset=data_offset,
                data_size=self.DATA_SIZE,
                expected_checksum=expected_checksum,
            )

            self.checksums.append(checksum_info)

    def validate_all(self) -> list[ChecksumInfo]:
        """
        Validate all checksums in the save file.

        Returns:
            List of checksum info with validation results
        """
        for checksum_info in self.checksums:
            self._validate_checksum(checksum_info)

        return self.checksums

    def _validate_checksum(self, checksum_info: ChecksumInfo):
        """
        Validate a single checksum.

        Args:
            checksum_info: Checksum information to validate
        """
        # Calculate MD5 hash of character data
        data_start = checksum_info.data_offset
        data_end = data_start + checksum_info.data_size
        character_data = self.save_data[data_start:data_end]

        calculated = hashlib.md5(character_data).digest()

        checksum_info.calculated_checksum = calculated
        checksum_info.is_valid = calculated == checksum_info.expected_checksum

    def calculate_checksum(self, slot_index: int) -> bytes:
        """
        Calculate the MD5 checksum for a specific character slot.

        Args:
            slot_index: Character slot index (0-9)

        Returns:
            16-byte MD5 checksum
        """
        if slot_index < 0 or slot_index >= len(self.checksums):
            raise ValueError(f"Invalid slot index: {slot_index}")

        checksum_info = self.checksums[slot_index]
        data_start = checksum_info.data_offset
        data_end = data_start + checksum_info.data_size
        character_data = self.save_data[data_start:data_end]

        return hashlib.md5(character_data).digest()

    def get_slot_for_offset(self, offset: int) -> int | None:
        """
        Get the character slot index for a given offset.

        Args:
            offset: Byte offset in the save file

        Returns:
            Slot index (0-9) or None if offset is not in a character slot
        """
        for checksum_info in self.checksums:
            slot_start = checksum_info.checksum_offset
            slot_end = slot_start + self.SLOT_SIZE

            if slot_start <= offset < slot_end:
                return checksum_info.slot_index

        return None

    def get_checksum_info(self, slot_index: int) -> ChecksumInfo | None:
        """
        Get checksum information for a specific slot.

        Args:
            slot_index: Character slot index (0-9)

        Returns:
            ChecksumInfo or None if slot doesn't exist
        """
        if slot_index < 0 or slot_index >= len(self.checksums):
            return None

        return self.checksums[slot_index]

    def update_save_data(self, new_data: bytes):
        """
        Update the save data and re-detect checksums.

        Args:
            new_data: New save file binary data
        """
        self.save_data = new_data
        self._detect_checksums()

    def get_invalid_checksums(self) -> list[ChecksumInfo]:
        """
        Get list of all invalid checksums.

        Returns:
            List of ChecksumInfo for slots with invalid checksums
        """
        return [info for info in self.checksums if info.is_valid is False]

    def get_modified_slots(self, original_data: bytes) -> list[int]:
        """
        Compare current save data with original to find modified slots.

        Args:
            original_data: Original save file binary data

        Returns:
            List of modified slot indices
        """
        modified = []

        for checksum_info in self.checksums:
            data_start = checksum_info.data_offset
            data_end = data_start + checksum_info.data_size

            if len(original_data) >= data_end:
                current_data = self.save_data[data_start:data_end]
                orig_data = original_data[data_start:data_end]

                if current_data != orig_data:
                    modified.append(checksum_info.slot_index)

        return modified
