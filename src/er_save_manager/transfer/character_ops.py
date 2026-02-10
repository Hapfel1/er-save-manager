"""
Character operations for copying, transferring, and deleting characters.

Handles raw byte-level manipulation of character slots in save files.
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save

import logging

# Module logger — write detailed transfer logs to project log file for debugging
logger = logging.getLogger(__name__)
# Ensure there is a dedicated file handler writing to er_save_manager.log
found = False
for h in logger.handlers:
    if isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "").endswith(
        "er_save_manager.log"
    ):
        found = True
        break
if not found:
    try:
        fh = logging.FileHandler("er_save_manager.log", encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception:
        pass


class CharacterOperations:
    CHECKSUM_SIZE = 0x10  # Match parser/save.py CHECKSUM_SIZE
    SLOT_SIZE = 0x280000  # Match parser/save.py SLOT_SIZE
    SLOT_DATA_SIZE = 0x280000  # Match parser/save.py slot_data_size

    @staticmethod
    def get_slot_offset(save, slot_index: int) -> int:
        """Return the byte offset of the start of the given slot in the save file."""
        return save._slot_offsets[slot_index]

    @staticmethod
    def _update_profile_summary_from_slot(save: Save, slot_index: int) -> None:
        """Update profile summary for a slot using the character data in that slot, including appearance and equipment."""
        char = save.character_slots[slot_index]
        if char.is_empty():
            return

        # Get offsets for profile summary
        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save)
        profile_size = 0x24C
        profile_offset = profiles_base + slot_index * profile_size

        import struct
        from io import BytesIO

        player = char.player_game_data
        buf = BytesIO()

        # Character name (16 wide chars, UTF-16LE, padded)
        name = getattr(player, "character_name", "")[:16]
        name_bytes = name.encode("utf-16le")
        name_bytes = name_bytes + b"\x00" * (32 - len(name_bytes))
        buf.write(name_bytes)
        buf.write(b"\x00" * 2)  # Terminator

        # Level, seconds played, runes_memory, map_id, unk0x34
        buf.write(struct.pack("<I", getattr(player, "level", 1)))
        buf.write(struct.pack("<I", getattr(player, "seconds_played", 0)))
        buf.write(struct.pack("<I", getattr(player, "runes_memory", 0)))
        buf.write(getattr(player, "map_id", b"\x00\x00\x00\x00"))
        buf.write(struct.pack("<I", getattr(player, "unk0x34", 0)))

        # Face data (0x124 bytes) - use FaceData from slot, convert to profile summary size (0x120 if needed)
        face_data = getattr(player, "face_data", None)
        if face_data is not None and hasattr(face_data, "raw_data"):
            face_bytes = face_data.raw_data
            if len(face_bytes) > 0x124:
                face_bytes = face_bytes[:0x124]
            elif len(face_bytes) < 0x124:
                face_bytes = face_bytes + b"\x00" * (0x124 - len(face_bytes))
        else:
            face_bytes = b"\x00" * 0x124
        buf.write(face_bytes)

        # Equipment (0xE8 bytes) - use equipment from slot if available
        equipment = getattr(player, "profile_equipment", None)
        if equipment is not None:
            if hasattr(equipment, "raw_data"):
                equip_bytes = equipment.raw_data
            else:
                equip_bytes = equipment
            if len(equip_bytes) > 0xE8:
                equip_bytes = equip_bytes[:0xE8]
            elif len(equip_bytes) < 0xE8:
                equip_bytes = equip_bytes + b"\x00" * (0xE8 - len(equip_bytes))
        else:
            equip_bytes = b"\x00" * 0xE8
        buf.write(equip_bytes)

        # Body type, archetype, starting gift
        buf.write(struct.pack("<B", getattr(player, "body_type", 0)))
        buf.write(struct.pack("<B", getattr(player, "archetype", 0)))
        buf.write(struct.pack("<B", getattr(player, "starting_gift", 0)))

        # Unknown fields (3 bytes + 4 bytes = 7 bytes)
        buf.write(b"\x00" * 7)

        # Pad to 0x24C bytes
        data = buf.getvalue()
        if len(data) < profile_size:
            data += b"\x00" * (profile_size - len(data))
        elif len(data) > profile_size:
            data = data[:profile_size]

        # Write to raw_data
        save._raw_data[profile_offset : profile_offset + profile_size] = data

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

        # Log copy intent
        try:
            path = getattr(save, "_original_filepath", "<unknown>")
            logger.info("copy_slot: %s %d -> %d", path, from_slot, to_slot)
        except Exception:
            logger.exception("Failed to log copy_slot intent")

        if not hasattr(save, "_raw_data"):
            raise RuntimeError("Save does not have raw data")

        # Ensure _raw_data is bytearray
        if isinstance(save._raw_data, bytes):
            save._raw_data = bytearray(save._raw_data)

        from_offset = CharacterOperations.get_slot_offset(save, from_slot)
        to_offset = CharacterOperations.get_slot_offset(save, to_slot)

        logger.debug(
            "copy_slot offsets: from_offset=%s to_offset=%s",
            hex(from_offset),
            hex(to_offset),
        )

        # Copy entire slot (checksum + data)
        save._raw_data[to_offset : to_offset + CharacterOperations.SLOT_SIZE] = (
            save._raw_data[from_offset : from_offset + CharacterOperations.SLOT_SIZE]
        )

        logger.debug(
            "Copied %d bytes from %s to %s",
            CharacterOperations.SLOT_SIZE,
            hex(from_offset),
            hex(to_offset),
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

        # Log transfer intent and context
        try:
            s_path = getattr(source_save, "_original_filepath", "<unknown>")
            t_path = getattr(target_save, "_original_filepath", "<unknown>")
            logger.info(
                "transfer_slot: %s slot %d -> %s slot %d",
                s_path,
                from_slot,
                t_path,
                to_slot,
            )
            logger.debug(
                "source raw len=%d target raw len=%d",
                len(source_save._raw_data),
                len(target_save._raw_data),
            )
        except Exception:
            logger.exception("Failed to log transfer context")

        # Ensure both are bytearray
        if isinstance(source_save._raw_data, bytes):
            source_save._raw_data = bytearray(source_save._raw_data)
        if isinstance(target_save._raw_data, bytes):
            target_save._raw_data = bytearray(target_save._raw_data)

        from_offset = CharacterOperations.get_slot_offset(source_save, from_slot)
        to_offset = CharacterOperations.get_slot_offset(target_save, to_slot)

        logger.debug(
            "slot offsets: from_offset=%s to_offset=%s",
            hex(from_offset),
            hex(to_offset),
        )

        # Copy entire slot
        target_save._raw_data[to_offset : to_offset + CharacterOperations.SLOT_SIZE] = (
            source_save._raw_data[
                from_offset : from_offset + CharacterOperations.SLOT_SIZE
            ]
        )

        # Re-parse the modified slot first so we have an accurate UserDataX
        from io import BytesIO

        from er_save_manager.parser.user_data_x import UserDataX

        f = BytesIO(target_save._raw_data)
        f.seek(to_offset + CharacterOperations.CHECKSUM_SIZE)
        try:
            target_save.character_slots[to_slot] = UserDataX.read(
                f,
                target_save.is_ps,
                to_offset + CharacterOperations.CHECKSUM_SIZE,
                CharacterOperations.SLOT_DATA_SIZE,
            )
        except Exception:
            logger.exception(
                "Failed to parse UserDataX for target slot %d after transfer", to_slot
            )
            raise

        # Patch SteamID to match target save using the freshly parsed slot info
        try:
            CharacterOperations._patch_steamid_in_slot(target_save, to_slot)
        except Exception:
            logger.exception("_patch_steamid_in_slot failed")

        # Update profile summary from the transferred slot
        try:
            CharacterOperations._update_profile_summary_from_slot(target_save, to_slot)
        except Exception:
            logger.exception("_update_profile_summary_from_slot failed")

        # Mark slot as active
        try:
            CharacterOperations._set_slot_active(target_save, to_slot, True)
        except Exception:
            logger.exception("_set_slot_active failed")

        # Re-parse USER_DATA_10 to update parsed profile data
        try:
            CharacterOperations._reparse_user_data_10(target_save)
        except Exception:
            logger.exception("_reparse_user_data_10 failed")

        # Re-parse the modified slot again in case SteamID patching altered parsed fields
        f = BytesIO(target_save._raw_data)
        f.seek(to_offset + CharacterOperations.CHECKSUM_SIZE)
        try:
            target_save.character_slots[to_slot] = UserDataX.read(
                f,
                target_save.is_ps,
                to_offset + CharacterOperations.CHECKSUM_SIZE,
                CharacterOperations.SLOT_DATA_SIZE,
            )
        except Exception:
            logger.exception(
                "Failed to re-parse UserDataX for target slot %d after steamid patch",
                to_slot,
            )
            # not fatal

        # Log resulting character info
        try:
            slot_obj = target_save.character_slots[to_slot]
            name = (
                slot_obj.get_character_name()
                if hasattr(slot_obj, "get_character_name")
                else "<unknown>"
            )
            active = CharacterOperations._is_slot_active(target_save, to_slot)
            logger.info(
                "Transfer result: target_slot=%d name=%s active=%s empty=%s",
                to_slot,
                name,
                active,
                slot_obj.is_empty() if hasattr(slot_obj, "is_empty") else False,
            )
        except Exception:
            logger.exception("Failed to log transfer result for slot %d", to_slot)

        # Recalculate checksums for the modified target save to ensure integrity
        try:
            if hasattr(target_save, "recalculate_checksums"):
                target_save.recalculate_checksums()
                logger.debug("Recalculated checksums for target save")
        except Exception:
            logger.exception("Failed to recalculate checksums for target save")

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
        """Update profile summary for a slot using the character data in that slot."""
        # Defensive: ensure slot is not empty
        char = save.character_slots[slot_index]
        if char.is_empty():
            return

        # Get offsets for profile summary
        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save)
        profile_size = 0x24C
        profile_offset = profiles_base + slot_index * profile_size

        # Build a new Profile entry from the slot's player_game_data
        import struct
        from io import BytesIO

        player = char.player_game_data
        buf = BytesIO()

        # Character name (16 wide chars, UTF-16LE, padded)
        name = getattr(player, "character_name", "")[:16]
        name_bytes = name.encode("utf-16le")
        name_bytes = name_bytes + b"\x00" * (32 - len(name_bytes))
        buf.write(name_bytes)
        buf.write(b"\x00" * 2)  # Terminator

        # Level, seconds played, runes, map id, unk0x34
        buf.write(struct.pack("<I", getattr(player, "level", 1)))
        buf.write(struct.pack("<I", getattr(player, "seconds_played", 0)))
        buf.write(struct.pack("<I", getattr(player, "runes", 0)))
        buf.write(getattr(player, "map_id", b"\x00\x00\x00\x00"))
        buf.write(struct.pack("<I", getattr(player, "unk0x34", 0)))

        # Face data (0x124 bytes)
        buf.write(getattr(player, "face_data", b"\x00" * 0x124))

        # Equipment (0xE8 bytes)
        buf.write(getattr(player, "profile_equipment", b"\x00" * 0xE8))

        # Body type, archetype, starting gift
        buf.write(struct.pack("<B", getattr(player, "body_type", 0)))
        buf.write(struct.pack("<B", getattr(player, "archetype", 0)))
        buf.write(struct.pack("<B", getattr(player, "starting_gift", 0)))

        # Unknown fields (3 bytes + 4 bytes = 7 bytes)
        buf.write(b"\x00" * 7)

        # Pad to 0x24C bytes
        data = buf.getvalue()
        if len(data) < profile_size:
            data += b"\x00" * (profile_size - len(data))
        elif len(data) > profile_size:
            data = data[:profile_size]

        # Write to raw_data
        save._raw_data[profile_offset : profile_offset + profile_size] = data

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

        # Get profile summary using calculated offsets, but re-generate from slot for full fidelity
        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save)
        profile_size = 0x24C
        # Use the same logic as _update_profile_summary_from_slot to build profile_data
        import struct
        from io import BytesIO

        player = char.player_game_data
        buf = BytesIO()
        name = getattr(player, "character_name", "")[:16]
        name_bytes = name.encode("utf-16le")
        name_bytes = name_bytes + b"\x00" * (32 - len(name_bytes))
        buf.write(name_bytes)
        buf.write(b"\x00" * 2)
        buf.write(struct.pack("<I", getattr(player, "level", 1)))
        buf.write(struct.pack("<I", getattr(player, "seconds_played", 0)))
        buf.write(struct.pack("<I", getattr(player, "runes_memory", 0)))
        buf.write(getattr(player, "map_id", b"\x00\x00\x00\x00"))
        buf.write(struct.pack("<I", getattr(player, "unk0x34", 0)))
        face_data = getattr(player, "face_data", None)
        if face_data is not None and hasattr(face_data, "raw_data"):
            face_bytes = face_data.raw_data
            if len(face_bytes) > 0x124:
                face_bytes = face_bytes[:0x124]
            elif len(face_bytes) < 0x124:
                face_bytes = face_bytes + b"\x00" * (0x124 - len(face_bytes))
        else:
            face_bytes = b"\x00" * 0x124
        buf.write(face_bytes)
        equipment = getattr(player, "profile_equipment", None)
        if equipment is not None:
            if hasattr(equipment, "raw_data"):
                equip_bytes = equipment.raw_data
            else:
                equip_bytes = equipment
            if len(equip_bytes) > 0xE8:
                equip_bytes = equip_bytes[:0xE8]
            elif len(equip_bytes) < 0xE8:
                equip_bytes = equip_bytes + b"\x00" * (0xE8 - len(equip_bytes))
        else:
            equip_bytes = b"\x00" * 0xE8
        buf.write(equip_bytes)
        buf.write(struct.pack("<B", getattr(player, "body_type", 0)))
        buf.write(struct.pack("<B", getattr(player, "archetype", 0)))
        buf.write(struct.pack("<B", getattr(player, "starting_gift", 0)))
        buf.write(b"\x00" * 7)
        profile_data = buf.getvalue()
        if len(profile_data) < profile_size:
            profile_data += b"\x00" * (profile_size - len(profile_data))
        elif len(profile_data) > profile_size:
            profile_data = profile_data[:profile_size]

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

        # Write new profile data (always full 0x24C bytes)
        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save)
        profile_offset = profiles_base + slot_index * profile_size
        save._raw_data[profile_offset : profile_offset + profile_size] = profile_data

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
        from er_save_manager.data.starting_classes import get_class_data

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

        # Use Convergence classes if applicable
        is_convergence = (
            save.is_convergence if hasattr(save, "is_convergence") else False
        )
        class_data = get_class_data(archetype_id, is_convergence)
        char_class = class_data.get("name", "Unknown")

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
            # Max resources
            "max_hp": getattr(player_data, "base_max_hp", 0),
            "max_fp": getattr(player_data, "base_max_fp", 0),
            "max_stamina": getattr(player_data, "base_max_sp", 0),
            "runes": player_data.runes,
            # Playtime (from USER_DATA_10 ProfileSummary)
            "playtime_seconds": playtime_seconds,
            "playtime": playtime_formatted,
            # Progression info
            "ng_level": CharacterOperations._get_ng_level(save, slot_index),
            "bosses_defeated": CharacterOperations._count_bosses_defeated(
                save, slot_index
            ),
            "graces_unlocked": CharacterOperations._count_graces_unlocked(
                save, slot_index
            ),
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
            from er_save_manager.parser.event_flags import EventFlags

            # Get event flags for character
            event_flags = save.character_slots[slot_index].event_flags
            if not event_flags:
                return 0

            # Check NG+ progression flags
            for ng_cycle in range(7, 0, -1):  # Check NG+7 down to NG+1
                flag_id = 10000799 + (ng_cycle * 1000)
                if EventFlags.get_flag(event_flags, flag_id):
                    return ng_cycle

            return 0
        except Exception:
            return 0

    @staticmethod
    def _get_ng_level(save: Save, slot_index: int) -> str:
        """Get descriptive NG level (NG, NG+1, NG+2, etc.)."""
        ng_plus = CharacterOperations._detect_ng_plus(save, slot_index)
        if ng_plus == 0:
            return "NG"
        else:
            return f"NG+{ng_plus}"

    @staticmethod
    def _count_bosses_defeated(save: Save, slot_index: int) -> int:
        """Count number of bosses defeated."""
        try:
            from er_save_manager.data.event_flags_db import EVENT_FLAGS
            from er_save_manager.parser.event_flags import EventFlags

            event_flags = save.character_slots[slot_index].event_flags
            if not event_flags:
                return 0

            # Count all flags in "Bosses" category that are set
            boss_count = 0
            for flag_id, flag_data in EVENT_FLAGS.items():
                if flag_data.get("category") == "Bosses" and EventFlags.get_flag(
                    event_flags, flag_id
                ):
                    boss_count += 1

            return boss_count
        except Exception:
            return 0

    @staticmethod
    def _count_graces_unlocked(save: Save, slot_index: int) -> int:
        """Count number of graces unlocked."""
        try:
            from er_save_manager.data.event_flags_db import EVENT_FLAGS
            from er_save_manager.parser.event_flags import EventFlags

            event_flags = save.character_slots[slot_index].event_flags
            if not event_flags:
                return 0

            # Count all flags in "Grace" category that are set
            grace_count = 0
            for flag_id, flag_data in EVENT_FLAGS.items():
                if flag_data.get("category") == "Grace" and EventFlags.get_flag(
                    event_flags, flag_id
                ):
                    grace_count += 1

            return grace_count
        except Exception:
            return 0

    @staticmethod
    def _extract_equipment_summary(char) -> dict:
        """
        Extract equipped items summary for character metadata.

        Returns:
            Dictionary with equipment info (currently returns empty dict as placeholder)
        """
        try:
            from er_save_manager.data.convergence_items import (
                parse_convergence_hex_all,
                parse_convergence_hex_files,
            )
            from er_save_manager.data.item_database import get_item_name

            equip = getattr(char, "equipped_items_item_id", None)
            if not equip:
                return {}

            convergence_items = parse_convergence_hex_files()
            id_to_name = {}
            for items in convergence_items.values():
                for item_name, item_id in items.items():
                    id_to_name[item_id] = item_name

            id_to_name.update(parse_convergence_hex_all())

            empty_item_ids = {0x00000000, 0xFFFFFFFF, 0x0001ADB0}

            def resolve_name(item_id: int, category_bits: int | None) -> str:
                if item_id in empty_item_ids:
                    return ""

                full_id = item_id
                if category_bits and (item_id & 0xF0000000) == 0:
                    full_id = category_bits | item_id

                name = get_item_name(full_id)
                if name and not name.startswith("Unknown "):
                    return name

                # Try Convergence lookup
                if full_id in id_to_name:
                    return id_to_name[full_id]
                if item_id in id_to_name:
                    return id_to_name[item_id]
                base_id = full_id & 0x0FFFFFFF
                if base_id in id_to_name:
                    return id_to_name[base_id]

                # Try rounding for weapon-like variants (category 0x0)
                category = full_id & 0xF0000000
                base_id = full_id & 0x0FFFFFFF
                if category == 0x00000000:
                    rounded_100 = category | ((base_id // 100) * 100)
                    rounded_10 = category | ((base_id // 10) * 10)
                    if rounded_100 in id_to_name:
                        return id_to_name[rounded_100]
                    if rounded_10 in id_to_name:
                        return id_to_name[rounded_10]

                return name

            slots = {
                "right_hand_1": (equip.right_hand_armament1, 0x00000000),
                "right_hand_2": (equip.right_hand_armament2, 0x00000000),
                "right_hand_3": (equip.right_hand_armament3, 0x00000000),
                "left_hand_1": (equip.left_hand_armament1, 0x00000000),
                "left_hand_2": (equip.left_hand_armament2, 0x00000000),
                "left_hand_3": (equip.left_hand_armament3, 0x00000000),
                "head": (equip.head, 0x10000000),
                "chest": (equip.chest, 0x10000000),
                "arms": (equip.arms, 0x10000000),
                "legs": (equip.legs, 0x10000000),
                "talisman_1": (equip.talisman1, 0x20000000),
                "talisman_2": (equip.talisman2, 0x20000000),
                "talisman_3": (equip.talisman3, 0x20000000),
                "talisman_4": (equip.talisman4, 0x20000000),
            }

            equipment: dict[str, dict[str, int | str]] = {}
            for slot_name, (item_id, category_bits) in slots.items():
                item_name = resolve_name(item_id, category_bits)
                if item_name:
                    equipment[slot_name] = {"id": item_id, "name": item_name}

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

        except Exception:
            return False
