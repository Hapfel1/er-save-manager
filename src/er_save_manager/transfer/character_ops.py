"""
Character operations for copying, transferring, and deleting characters.

Handles raw byte-level manipulation of character slots in save files.
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

from er_save_manager.parser.profile_sync import profile_from_slot

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save

import logging

# Module logger - write detailed transfer logs to project log file for debugging
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
    @staticmethod
    def get_user_data_10_offset(save) -> int:
        """
        Return the offset of USER_DATA_10 section in the save file.
        """
        return getattr(save, "_user_data_10_offset", 0)

    SLOT_SIZE = 0x280000
    SLOT_DATA_SIZE = 0x280000
    CHECKSUM_SIZE = 0x10

    @staticmethod
    def get_slot_offset(save, slot_index: int) -> int:
        """Return the byte offset of slot data, skipping the checksum prefix on PC."""
        return save.slot_data_offset(slot_index)

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

        f = BytesIO(save._raw_data)
        f.seek(CharacterOperations.get_user_data_10_offset(save))

        if not save.is_ps:
            f.read(16)

        # Version (4 bytes)
        f.read(4)

        # SteamID (8 bytes)
        f.read(8)

        settings_start = f.tell()
        # Settings expected to take 0x140 bytes total (with padding)
        f.seek(settings_start + 0x140)

        # MenuSystemSaveLoad (0x1808 bytes)
        f.read(0x1808)

        profile_summary_start = f.tell()

        # IsProfileActive[10] - 10 bytes
        active_slots_offset = profile_summary_start

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

        try:
            path = getattr(save, "_original_filepath", "<unknown>")
            logger.info("copy_slot: %s %d -> %d", path, from_slot, to_slot)
        except Exception:
            logger.exception("Failed to log copy_slot intent")

        if not hasattr(save, "_raw_data"):
            raise RuntimeError("Save does not have raw data")

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

        CharacterOperations._update_profile_summary(save, from_slot, to_slot)

        CharacterOperations._set_slot_active(save, to_slot, True)

        CharacterOperations._reparse_user_data_10(save)

        from io import BytesIO

        from er_save_manager.parser.user_data_x import UserDataX

        f = BytesIO(save._raw_data)
        f.seek(to_offset)
        save.character_slots[to_slot] = UserDataX.read(
            f,
            save.is_ps,
            to_offset,
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

        target_save._raw_data[to_offset : to_offset + CharacterOperations.SLOT_SIZE] = (
            source_save._raw_data[
                from_offset : from_offset + CharacterOperations.SLOT_SIZE
            ]
        )

        # Copy the profile summary across, preserving seconds_played and the
        # equipment preview
        _, source_profiles_base = CharacterOperations.get_profile_summary_offsets(
            source_save
        )
        _, target_profiles_base = CharacterOperations.get_profile_summary_offsets(
            target_save
        )
        profile_size = 0x24C

        source_profile_offset = source_profiles_base + from_slot * profile_size
        target_profile_offset = target_profiles_base + to_slot * profile_size

        target_save._raw_data[
            target_profile_offset : target_profile_offset + profile_size
        ] = source_save._raw_data[
            source_profile_offset : source_profile_offset + profile_size
        ]

        logger.debug(
            "Copied profile summary from source slot %d to target slot %d",
            from_slot,
            to_slot,
        )

        # Re-parse the modified slot first for an accurate UserDataX
        from io import BytesIO

        from er_save_manager.parser.user_data_x import UserDataX

        f = BytesIO(target_save._raw_data)
        f.seek(to_offset)
        try:
            target_save.character_slots[to_slot] = UserDataX.read(
                f,
                target_save.is_ps,
                to_offset,
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

        try:
            CharacterOperations._set_slot_active(target_save, to_slot, True)
        except Exception:
            logger.exception("_set_slot_active failed")

        try:
            CharacterOperations._reparse_user_data_10(target_save)
        except Exception:
            logger.exception("_reparse_user_data_10 failed")

        # Re-parse the modified slot again in case SteamID patching altered parsed fields
        f = BytesIO(target_save._raw_data)
        f.seek(to_offset)
        try:
            target_save.character_slots[to_slot] = UserDataX.read(
                f,
                target_save.is_ps,
                to_offset,
                CharacterOperations.SLOT_DATA_SIZE,
            )
        except Exception:
            logger.exception(
                "Failed to re-parse UserDataX for target slot %d after steamid patch",
                to_slot,
            )
            # not fatal

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

        if isinstance(save._raw_data, bytes):
            save._raw_data = bytearray(save._raw_data)

        slot_offset = CharacterOperations.get_slot_offset(save, slot_index)

        # Zero out the entire slot (checksum + data)
        save._raw_data[slot_offset : slot_offset + CharacterOperations.SLOT_SIZE] = (
            bytes(CharacterOperations.SLOT_SIZE)
        )

        CharacterOperations._clear_profile_summary(save, slot_index)

        CharacterOperations._set_slot_active(save, slot_index, False)

        CharacterOperations._reparse_user_data_10(save)

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

        if isinstance(save._raw_data, bytes):
            save._raw_data = bytearray(save._raw_data)

        offset_a = CharacterOperations.get_slot_offset(save, slot_a)
        offset_b = CharacterOperations.get_slot_offset(save, slot_b)

        temp = bytes(
            save._raw_data[offset_a : offset_a + CharacterOperations.SLOT_SIZE]
        )
        save._raw_data[offset_a : offset_a + CharacterOperations.SLOT_SIZE] = (
            save._raw_data[offset_b : offset_b + CharacterOperations.SLOT_SIZE]
        )
        save._raw_data[offset_b : offset_b + CharacterOperations.SLOT_SIZE] = temp

        CharacterOperations._swap_profile_summaries(save, slot_a, slot_b)

        active_a = CharacterOperations._is_slot_active(save, slot_a)
        active_b = CharacterOperations._is_slot_active(save, slot_b)
        CharacterOperations._set_slot_active(save, slot_a, active_b)
        CharacterOperations._set_slot_active(save, slot_b, active_a)

        CharacterOperations._reparse_user_data_10(save)

        from io import BytesIO

        from er_save_manager.parser.user_data_x import UserDataX

        f = BytesIO(save._raw_data)

        # get_slot_offset already points past the PC checksum prefix
        for slot_idx, offset in [(slot_a, offset_a), (slot_b, offset_b)]:
            f.seek(offset)
            save.character_slots[slot_idx] = UserDataX.read(
                f,
                save.is_ps,
                offset,
                CharacterOperations.SLOT_DATA_SIZE,
            )

    @staticmethod
    def _update_profile_summary(save: Save, from_slot: int, to_slot: int) -> None:
        """Copy profile summary from one slot to another."""
        if not save.user_data_10_parsed or not save.user_data_10_parsed.profile_summary:
            return

        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save)
        profile_size = 0x24C

        from_profile_offset = profiles_base + from_slot * profile_size
        to_profile_offset = profiles_base + to_slot * profile_size

        save._raw_data[to_profile_offset : to_profile_offset + profile_size] = (
            save._raw_data[from_profile_offset : from_profile_offset + profile_size]
        )

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

        PlayStation slots store 0 here, regardless of the USER_DATA_10 value.
        """
        if isinstance(save._raw_data, bytes):
            save._raw_data = bytearray(save._raw_data)

        if save.is_ps:
            target_steamid = 0
        else:
            if not save.user_data_10_parsed:
                return
            target_steamid = save.user_data_10_parsed.steam_id
            if target_steamid == 0:
                return

        # SteamID is near the end of character data (in the slot, not profile summary)
        slot_char = save.character_slots[slot_index]
        if not slot_char.is_empty() and hasattr(slot_char, "steamid_offset"):
            # steamid_offset is an absolute file offset from f.tell() at parse time
            struct.pack_into(
                "<Q", save._raw_data, slot_char.steamid_offset, target_steamid
            )

    @staticmethod
    def _reparse_user_data_10(save: Save) -> None:
        """
        Re-parse USER_DATA_10 to update the parsed profile summary.

        This is critical after modifying profile data in raw bytes -
        otherwise the Save object's parsed data won't match the file.
        """
        from io import BytesIO

        from er_save_manager.parser.user_data_10 import UserData10

        f = BytesIO(save._raw_data)
        f.seek(CharacterOperations.get_user_data_10_offset(save))

        try:
            save.user_data_10_parsed = UserData10.read(f, save.is_ps)
        except Exception as e:
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

        if isinstance(save._raw_data, bytes):
            save._raw_data = bytearray(save._raw_data)

        char = save.character_slots[slot_index]
        if char.is_empty():
            raise ValueError(f"Slot {slot_index} is empty")

        slot_offset = CharacterOperations.get_slot_offset(save, slot_index)

        raw_slot_start = save._slot_offsets[slot_index]
        slot_data = bytes(
            save._raw_data[slot_offset : raw_slot_start + CharacterOperations.SLOT_SIZE]
        )

        # The game-written profile is the base: its place name and face are
        # not rebuilt from the slot.
        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save)
        profile_size = 0x24C
        profile_offset = profiles_base + slot_index * profile_size
        profile_data = profile_from_slot(
            save._raw_data,
            char,
            bytes(save._raw_data[profile_offset : profile_offset + profile_size]),
        )

        is_active = CharacterOperations._is_slot_active(save, slot_index)

        import hashlib

        with open(output_path, "wb") as f:
            f.write(b"ERC\x00")
            f.write(struct.pack("<I", 1))
            # Active flag (1 byte)
            f.write(struct.pack("<B", 1 if is_active else 0))
            f.write(struct.pack("<I", len(slot_data)))
            f.write(slot_data)
            f.write(struct.pack("<I", len(profile_data)))
            f.write(profile_data)

        with open(output_path, "rb") as f:
            data = f.read()

        checksum = hashlib.md5(data).digest()

        with open(output_path, "ab") as f:
            f.write(checksum)

    @staticmethod
    def read_erc(input_path) -> tuple[bytes, bytes]:
        """Slot data and profile data of an .erc file.

        Raises ValueError with a plain message for a file that is not an
        .erc export, is cut short or fails its checksum.
        """
        import hashlib

        with open(input_path, "rb") as f:
            data = f.read()
        truncated = ValueError(
            "The .erc file is incomplete (cut short). Export the character again."
        )
        if data[:4] != b"ERC\x00":
            raise ValueError("Not a character export (.erc) file.")
        pos = 4

        def take(size: int) -> bytes:
            nonlocal pos
            if pos + size > len(data):
                raise truncated
            chunk = data[pos : pos + size]
            pos += size
            return chunk

        version = struct.unpack("<I", take(4))[0]
        if version != 1:
            raise ValueError(f"Unsupported .erc version: {version}")
        take(1)  # active flag
        slot_size = struct.unpack("<I", take(4))[0]
        if slot_size > CharacterOperations.SLOT_SIZE:
            raise ValueError(
                f"The .erc slot data is {slot_size:#x} bytes, larger than a "
                f"character slot ({CharacterOperations.SLOT_SIZE:#x})."
            )
        slot_data = take(slot_size)
        profile_size = struct.unpack("<I", take(4))[0]
        if profile_size != 0x24C:
            raise ValueError(
                f"Profile size mismatch in .erc file: expected 0x24C bytes, got "
                f"{profile_size:#x}. The .erc file may be corrupted."
            )
        profile_data = take(profile_size)
        checksum_expected = take(16)
        if hashlib.md5(data[:-16]).digest() != checksum_expected:
            raise ValueError("Checksum mismatch - file may be corrupted")
        return slot_data, profile_data

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

        if isinstance(save._raw_data, bytes):
            save._raw_data = bytearray(save._raw_data)

        slot_data, profile_data = CharacterOperations.read_erc(input_path)
        profile_size = len(profile_data)

        slot_offset = CharacterOperations.get_slot_offset(save, slot_index)

        # Zero the whole slot first, or bytes from the previous character
        # survive wherever the new one writes less data
        save._raw_data[slot_offset : slot_offset + CharacterOperations.SLOT_SIZE] = (
            bytes(CharacterOperations.SLOT_SIZE)
        )

        # Write slot data (checksum prefix already zeroed by the clear above, recalculated later)
        save._raw_data[slot_offset : slot_offset + len(slot_data)] = slot_data

        # Write new profile data (always full 0x24C bytes). Files from older
        # versions carry a profile rebuilt with zeroed fields, so every field
        # the slot also holds is taken from the slot.
        from io import BytesIO

        from er_save_manager.parser.user_data_x import UserDataX

        reader = BytesIO(save._raw_data)
        reader.seek(slot_offset)
        imported = UserDataX.read(
            reader, save.is_ps, slot_offset, CharacterOperations.SLOT_DATA_SIZE
        )
        profile_data = profile_from_slot(save._raw_data, imported, profile_data)
        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save)
        profile_offset = profiles_base + slot_index * profile_size
        save._raw_data[profile_offset : profile_offset + profile_size] = profile_data

        # Set slot as active (imported characters should be active by default)
        CharacterOperations._set_slot_active(save, slot_index, True)

        # Re-parse the slot before patching SteamID so steamid_offset reflects the
        # imported data, not the previous occupant of the slot.
        from io import BytesIO

        from er_save_manager.parser.user_data_x import UserDataX

        f = BytesIO(save._raw_data)
        f.seek(slot_offset)
        save.character_slots[slot_index] = UserDataX.read(
            f,
            save.is_ps,
            slot_offset,
            CharacterOperations.SLOT_DATA_SIZE,
        )

        CharacterOperations._patch_steamid_in_slot(save, slot_index)

        # Re-parse USER_DATA_10 so CSProfileSummary reflects the written profile data
        # and the steamid-patched slot bytes.
        CharacterOperations._reparse_user_data_10(save)

        # Re-parse slot again to pick up any changes made by the steamid patch.
        f = BytesIO(save._raw_data)
        f.seek(slot_offset)
        save.character_slots[slot_index] = UserDataX.read(
            f,
            save.is_ps,
            slot_offset,
            CharacterOperations.SLOT_DATA_SIZE,
        )

        # The slot and USER_DATA_10 checksums must match the new contents
        # or the game rejects the save as corrupt
        save.recalculate_checksums()

        return save.character_slots[slot_index].get_character_name()

    @staticmethod
    def extract_character_metadata(save: Save, slot_index: int) -> dict:
        """
        Extract metadata from a character for community sharing.

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

        is_convergence = (
            save.is_convergence if hasattr(save, "is_convergence") else False
        )
        class_data = get_class_data(archetype_id, is_convergence)
        char_class = class_data.get("name", "Unknown")

        playtime_seconds = profile.seconds_played if profile else 0
        playtime_formatted = CharacterOperations._format_playtime(playtime_seconds)

        body_type = None
        if profile and profile.body_type is not None:
            body_type = "Type A" if profile.body_type == 1 else "Type B"

        metadata = {
            "name": player_data.character_name,
            "level": player_data.level,
            "class": char_class,
            "body_type": body_type,
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
            "max_hp": getattr(player_data, "base_max_hp", 0),
            "max_fp": getattr(player_data, "base_max_fp", 0),
            "max_stamina": getattr(player_data, "base_max_sp", 0),
            "runes": player_data.runes,
            # Playtime (from USER_DATA_10 ProfileSummary)
            "playtime_seconds": playtime_seconds,
            "playtime": playtime_formatted,
            "ng_level": CharacterOperations._get_ng_level(save, slot_index),
            "bosses_defeated": CharacterOperations._count_bosses_defeated(
                save, slot_index
            ),
            "graces_unlocked": CharacterOperations._count_graces_unlocked(
                save, slot_index
            ),
            "ng_plus": CharacterOperations._detect_ng_plus(save, slot_index),
            "equipment": CharacterOperations._extract_equipment_summary(char),
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

            event_flags = save.character_slots[slot_index].event_flags
            if not event_flags:
                return 0

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
            from er_save_manager.data.item_database import get_item_name

            equip = getattr(char, "equipped_items_item_id", None)
            if not equip:
                return {}

            empty_item_ids = {0x00000000, 0xFFFFFFFF, 0x0001ADB0}

            def resolve_name(item_id: int, category_bits: int | None) -> str:
                if item_id in empty_item_ids:
                    return ""

                full_id = item_id
                if category_bits and (item_id & 0xF0000000) == 0:
                    full_id = category_bits | item_id

                return get_item_name(full_id)

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
