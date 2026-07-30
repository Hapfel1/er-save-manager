"""
Character operations for DS2: copy, delete, swap, export, import, metadata.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.games.DS2.save import DS2Save

from er_save_manager.games.DS2.save import (
    BIG_ENTRY_START,
    CHARACTER_SLOTS,
    PROFILE_ENTRY_START,
    Character,
)

_EXPORT_MAGIC = b"DS2C\x00"
_EXPORT_VERSION = 1

UNINITIALIZED_SLOT_WARNING = (
    "Slot {slot} has never been through the game's own character creation "
    "screen. Writing character data into it directly will not make it "
    "appear at the load screen, even though the write itself succeeds."
    "Create a throwaway character in this slot "
    "in-game first, save and quit, then run this again."
)


class DS2CharacterOperations:
    @staticmethod
    def _check_slot_index(slot_index: int) -> None:
        if not (0 <= slot_index < CHARACTER_SLOTS):
            raise ValueError(
                f"Slot index must be 0-{CHARACTER_SLOTS - 1}, got {slot_index}"
            )

    @staticmethod
    def slot_warning(save: DS2Save, slot_index: int) -> str | None:
        """Return a warning message if slot_index has never been through
        character creation in-game, or None if it is safe to write into."""
        if not save.is_slot_initialized(slot_index):
            return UNINITIALIZED_SLOT_WARNING.format(slot=slot_index)
        return None

    @staticmethod
    def copy_slot(
        save: DS2Save, from_slot: int, to_slot: int, force: bool = False
    ) -> None:
        """Copy a character (profile + big entry) from one slot to another
        in the same save. Overwrites whatever is in to_slot.

        Raises RuntimeError if to_slot has never been through character
        creation in-game, unless force=True. See UNINITIALIZED_SLOT_WARNING.
        """
        if from_slot == to_slot:
            raise ValueError("Source and destination slots cannot be the same")
        DS2CharacterOperations._check_slot_index(from_slot)
        DS2CharacterOperations._check_slot_index(to_slot)

        if not force:
            warning = DS2CharacterOperations.slot_warning(save, to_slot)
            if warning:
                raise RuntimeError(warning)

        profile_data = bytes(save.container.get_entry(PROFILE_ENTRY_START + from_slot))
        big_data = bytes(save.container.get_entry(BIG_ENTRY_START + from_slot))

        save.characters[to_slot].raw()[:] = profile_data
        save.container.get_entry(BIG_ENTRY_START + to_slot)[:] = big_data

        save.sync_name_caches()

    @staticmethod
    def transfer_slot(
        source_save: DS2Save,
        from_slot: int,
        target_save: DS2Save,
        to_slot: int,
        force: bool = False,
    ) -> None:
        """Copy a character (profile + big entry) from a slot in one save
        file into a slot in a different save file. Overwrites whatever is
        in to_slot on target_save.

        Raises RuntimeError if to_slot on target_save has never been
        through character creation in-game, unless force=True. See
        UNINITIALIZED_SLOT_WARNING.
        """
        DS2CharacterOperations._check_slot_index(from_slot)
        DS2CharacterOperations._check_slot_index(to_slot)

        if not force:
            warning = DS2CharacterOperations.slot_warning(target_save, to_slot)
            if warning:
                raise RuntimeError(warning)

        profile_data = bytes(source_save.characters[from_slot].raw())
        big_data = bytes(source_save.container.get_entry(BIG_ENTRY_START + from_slot))

        target_save.characters[to_slot].raw()[:] = profile_data
        target_save.container.get_entry(BIG_ENTRY_START + to_slot)[:] = big_data

        target_save.sync_name_caches()

    @staticmethod
    def delete_slot(save: DS2Save, slot_index: int) -> None:
        """Zero a character's profile and big entry, and clear its cached
        name in entry 0 / entry 22."""
        DS2CharacterOperations._check_slot_index(slot_index)

        profile = save.characters[slot_index].raw()
        profile[:] = bytes(len(profile))

        big_entry = save.container.get_entry(BIG_ENTRY_START + slot_index)
        big_entry[:] = bytes(len(big_entry))

        save.clear_name_cache(slot_index)

    @staticmethod
    def swap_slots(
        save: DS2Save, slot_a: int, slot_b: int, force: bool = False
    ) -> None:
        """Swap two characters (profile + big entry) in place.

        Raises RuntimeError if either slot has never been through
        character creation in-game, unless force=True. See
        UNINITIALIZED_SLOT_WARNING.
        """
        if slot_a == slot_b:
            raise ValueError("Cannot swap a slot with itself")
        DS2CharacterOperations._check_slot_index(slot_a)
        DS2CharacterOperations._check_slot_index(slot_b)

        if not force:
            for slot in (slot_a, slot_b):
                warning = DS2CharacterOperations.slot_warning(save, slot)
                if warning:
                    raise RuntimeError(warning)

        profile_a = save.characters[slot_a].raw()
        profile_b = save.characters[slot_b].raw()
        profile_a[:], profile_b[:] = bytes(profile_b), bytes(profile_a)

        big_a = save.container.get_entry(BIG_ENTRY_START + slot_a)
        big_b = save.container.get_entry(BIG_ENTRY_START + slot_b)
        big_a[:], big_b[:] = bytes(big_b), bytes(big_a)

        save.sync_name_caches()

    @staticmethod
    def export_character(save: DS2Save, slot_index: int, output_path: str) -> None:
        """
        Export a character to a standalone .ds2c file.

        File format:
          Magic: "DS2C\\0" (5 bytes)
          Version: u32 (1)
          Profile size: u32, then that many bytes of profile entry data
          Big entry size: u32, then that many bytes of big entry data
          Checksum: MD5 of everything above (16 bytes)
        """
        DS2CharacterOperations._check_slot_index(slot_index)

        character = save.characters[slot_index]
        if not character.name:
            raise ValueError(f"Slot {slot_index} is empty")

        profile_data = bytes(character.raw())
        big_data = bytes(save.container.get_entry(BIG_ENTRY_START + slot_index))

        buffer = bytearray()
        buffer += _EXPORT_MAGIC
        buffer += struct.pack("<I", _EXPORT_VERSION)
        buffer += struct.pack("<I", len(profile_data))
        buffer += profile_data
        buffer += struct.pack("<I", len(big_data))
        buffer += big_data
        buffer += hashlib.md5(buffer).digest()

        target = Path(output_path)
        tmp_path = target.with_suffix(target.suffix + ".tmp")
        tmp_path.write_bytes(bytes(buffer))
        tmp_path.replace(target)

    @staticmethod
    def import_character(
        save: DS2Save, slot_index: int, input_path: str, force: bool = False
    ) -> str:
        """
        Import a character from a .ds2c file into slot_index.

        The imported profile/big entry data must be exactly the size of
        the target slot's current entries, since BND4 entry sizes are
        fixed in the container's entry table and cannot grow or shrink.
        This holds as long as source and target save are the same game
        version. Returns the imported character's name.

        Raises RuntimeError if slot_index has never been through character
        creation in-game, unless force=True. See UNINITIALIZED_SLOT_WARNING.
        """
        DS2CharacterOperations._check_slot_index(slot_index)

        if not force:
            warning = DS2CharacterOperations.slot_warning(save, slot_index)
            if warning:
                raise RuntimeError(warning)

        with open(input_path, "rb") as f:
            magic = f.read(5)
            if magic != _EXPORT_MAGIC:
                raise ValueError("Invalid .ds2c file: bad magic")

            version = struct.unpack("<I", f.read(4))[0]
            if version != _EXPORT_VERSION:
                raise ValueError(f"Unsupported .ds2c version: {version}")

            profile_size = struct.unpack("<I", f.read(4))[0]
            profile_data = f.read(profile_size)

            big_size = struct.unpack("<I", f.read(4))[0]
            big_data = f.read(big_size)

            checksum_expected = f.read(16)

        with open(input_path, "rb") as f:
            data_to_hash = f.read()[:-16]
        if hashlib.md5(data_to_hash).digest() != checksum_expected:
            raise ValueError("Checksum mismatch - .ds2c file may be corrupted")

        target_profile = save.characters[slot_index].raw()
        target_big = save.container.get_entry(BIG_ENTRY_START + slot_index)

        if len(profile_data) != len(target_profile):
            raise ValueError(
                f"Profile size mismatch: .ds2c has {len(profile_data)} bytes, "
                f"target slot expects {len(target_profile)}. Likely a different "
                f"game version; cannot import into this save."
            )
        if len(big_data) != len(target_big):
            raise ValueError(
                f"Big entry size mismatch: .ds2c has {len(big_data)} bytes, "
                f"target slot expects {len(target_big)}. Likely a different "
                f"game version; cannot import into this save."
            )

        target_profile[:] = profile_data
        target_big[:] = big_data
        save.sync_name_caches()

        return save.characters[slot_index].name

    @staticmethod
    def extract_character_metadata(save: DS2Save, slot_index: int) -> dict:
        """
        Extract character metadata for display or community sharing.

        Boss kills, playtime, and world-state progress are not included:
        the region that likely holds them (see FLAG_REGION_* in save.py)
        is not mapped to individual flag IDs yet.
        """
        DS2CharacterOperations._check_slot_index(slot_index)

        character: Character = save.characters[slot_index]
        if not character.name:
            raise ValueError(f"Slot {slot_index} is empty")

        inventory = [i for i in character.inventory() if i.item_id != 0]
        key_items = [i for i in character.key_items() if i.item_id != 0]

        return {
            "name": character.name,
            "level": character.get_stat("level"),
            "souls": character.souls,
            "hp": character.hp,
            "ng_plus": character.new_game_plus,
            "stats": {
                "vigor": character.get_stat("vigor"),
                "attunement": character.get_stat("attunement"),
                "endurance": character.get_stat("endurance"),
                "vitality": character.get_stat("vitality"),
                "strength": character.get_stat("strength"),
                "dexterity": character.get_stat("dexterity"),
                "adaptability": character.get_stat("adaptability"),
                "intelligence": character.get_stat("intelligence"),
                "faith": character.get_stat("faith"),
            },
            "inventory_item_count": len(inventory),
            "key_item_count": len(key_items),
        }
