"""
Character operations for DSR: copy, transfer, swap, delete, export, import.

Each DSR slot is decrypted independently (own IV per slot), so operations
work on plaintext bytearrays directly. DSR has no fixed SteamID offset in
character slots; it is found by byte-scanning for a valid Steam64 range,
matching the approach in ds2_dsr_steamid.py.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from .save import (
    CHARACTER_SLOTS,
    SLOT_DATA_SIZE,
    SLOT_SIZE,
    SLOTS_OFFSET,
    DSRCharacter,
    DSRSave,
    _decrypt,
)

_ERC_MAGIC = b"DSRC"
_ERC_VERSION = 1
_ERC_HEADER = 12  # magic, version, data size
_ERC_CHECKSUM = 16  # MD5 of everything before it
_STEAM64_BASE = 0x0110000100000000
_STEAM64_MAX = 0x01100001FFFFFFFF

# --- Slot state in system_data (slot 10) ----------------------------------
#
# One u8 per character slot at ACTIVE_FLAGS_OFFSET: 1 when the slot holds a
# character. Deleting a character in game clears it and zeroes the slot's
# character data; the directory entry below is left as it was.
ACTIVE_FLAGS_OFFSET = 0xC4

# Decrypted slot: u32 length of the character data at +0x10, the data from
# +0x14, then PKCS7 padding.
_DATA_LENGTH_OFFSET = 0x10
_DATA_START = 0x14

# --- Character-select directory (in system_data / slot 10) -----------------
#
# The load-screen character list is a separate 10-entry directory stored in
# slot 10, not derived from the character slots themselves. Each entry mirrors
# the name and level of its character slot. character_ops keeps the name and
# level in sync on every slot mutation.
#
# The first 0x28 bytes of entry 0 overlap the slot header that holds the
# active flags, so entry writes keep those flags.
#
# Layout per entry (400 bytes), offsets relative to entry start:
#   +0x28  34   Character name (UTF-16LE, mirrors OFF_NAME_PRIMARY)
#   +0x4C   4   Level (u32 LE)
#   +0x88  16   Hair color RGBA (mirrors OFF_HAIR_RGBA)
#   +0x98  16   Eye color RGBA (mirrors OFF_EYE_RGBA)
#   +0xA8 100   Face data (mirrors OFF_FACE_DATA)
#   +0x14C 80   Item ids of the 20 equip slots (copy of the slot's id cache);
#               runs 12 bytes past DIR_STRIDE into the next entry's range
#   remaining bytes: other load-screen display data not required for the
#   character to load correctly.
#
# Entry 0 starts at DIR_BASE; entries are contiguous, DIR_STRIDE apart.
DIR_BASE = 172
DIR_STRIDE = 400
DIR_NAME_OFFSET = 0x28
DIR_LEVEL_OFFSET = 0x4C
DIR_HAIR_RGBA_OFFSET = 0x88
DIR_EYE_RGBA_OFFSET = 0x98
DIR_FACE_DATA_OFFSET = 0xA8
DIR_HAIR_ITEM_OFFSET = 0x17C  # copy of the slot's equipped hair id
DIR_EQUIP_OFFSET = 0x14C

_DIR_EMPTY_TEMPLATE = bytes.fromhex(
    "ffffffffffffffffffffffffffffffffffffffff000000000100000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "000000000000000000000000000000000000000000000000ffffffff00000000"
    "000000000000000058bc3d41010000000000000000000000ffffffff00000000"
    "00000000000000000000003f0000003f0000003f0000803f0000003f6666263f"
    "3333333f0000803f808080808080808080808080808080808080808080808080"
    "8080808080808080808080808080808080808080808080808080808080808080"
    "8080808080808080808080808080808080808080808080808080808080808080"
    "8080808080808080808080800000000000000000000000000000000000000000"
    "000000000000000070d731410100000001000000000000000000000000000000"
    "000000000000000000000000ffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffffffffffffffff"
)


def _dir_entry_offset(slot_index: int) -> int:
    return DIR_BASE + slot_index * DIR_STRIDE


def _read_dir_entry(save: DSRSave, slot_index: int) -> bytearray:
    off = _dir_entry_offset(slot_index)
    return bytearray(save.system_data[off : off + DIR_STRIDE])


def _write_dir_entry(save: DSRSave, slot_index: int, entry: bytes) -> None:
    if len(entry) != DIR_STRIDE:
        raise ValueError(
            f"Directory entry must be {DIR_STRIDE} bytes, got {len(entry)}"
        )
    off = _dir_entry_offset(slot_index)
    flags = bytes(
        save.system_data[ACTIVE_FLAGS_OFFSET : ACTIVE_FLAGS_OFFSET + CHARACTER_SLOTS]
    )
    save.system_data[off : off + DIR_STRIDE] = entry
    save.system_data[ACTIVE_FLAGS_OFFSET : ACTIVE_FLAGS_OFFSET + CHARACTER_SLOTS] = (
        flags
    )


def _set_active(save: DSRSave, slot_index: int, active: bool) -> None:
    save.system_data[ACTIVE_FLAGS_OFFSET + slot_index] = 1 if active else 0


def _clear_slot_data(save: DSRSave, slot_index: int) -> None:
    """Zero the character data of a slot, keeping the plaintext header and
    padding, as the game does on delete."""
    data = save.slot_plaintext(slot_index)
    length = struct.unpack_from("<I", data, _DATA_LENGTH_OFFSET)[0]
    data[_DATA_START : _DATA_START + length] = bytes(length)
    save.set_slot_plaintext(slot_index, data)


def _sync_dir_name_level(save: DSRSave, slot_index: int, name: str, level: int) -> None:
    """Patch just the name and level fields of a slot's directory entry.

    Used when the source character has no directory entry of its own to copy
    from (import from a standalone .dsrc file). Everything else in the entry
    (portrait thumbnail, appearance cache) is left as-is; the game regenerates
    those from the character slot itself the next time it is loaded in-game.
    """
    off = _dir_entry_offset(slot_index)
    existing = save.system_data[off : off + DIR_STRIDE]
    if bytes(existing) == _DIR_EMPTY_TEMPLATE:
        entry = bytearray(_DIR_EMPTY_TEMPLATE)
    else:
        entry = bytearray(existing)
    name_bytes = name.encode("utf-16-le").ljust(34, b"\x00")[:34]
    entry[DIR_NAME_OFFSET : DIR_NAME_OFFSET + 34] = name_bytes
    struct.pack_into("<I", entry, DIR_LEVEL_OFFSET, level & 0xFFFFFFFF)
    _write_dir_entry(save, slot_index, entry)


def sync_dir_equipment(save: DSRSave, slot_index: int) -> None:
    """Copy a character's equip slot item ids into its directory entry, which
    the load screen reads."""
    char = save.characters[slot_index]
    if char is None:
        return
    ids = char.equipped_ids()
    struct.pack_into(
        f"<{len(ids)}I",
        save.system_data,
        _dir_entry_offset(slot_index) + DIR_EQUIP_OFFSET,
        *ids,
    )


def _sync_dir_appearance(save: DSRSave, slot_index: int, char: DSRCharacter) -> None:
    """Patch the hair color, eye color, face data and hair id of a slot's
    directory entry from the character. An empty-template entry is left
    alone."""
    off = _dir_entry_offset(slot_index)
    entry = bytearray(save.system_data[off : off + DIR_STRIDE])
    if bytes(entry) == _DIR_EMPTY_TEMPLATE:
        return
    struct.pack_into("<4f", entry, DIR_HAIR_RGBA_OFFSET, *char.hair_rgba)
    struct.pack_into("<4f", entry, DIR_EYE_RGBA_OFFSET, *char.eye_rgba)
    face = char.face_data
    entry[DIR_FACE_DATA_OFFSET : DIR_FACE_DATA_OFFSET + len(face)] = face
    struct.pack_into("<I", entry, DIR_HAIR_ITEM_OFFSET, char.hair_item_id)
    _write_dir_entry(save, slot_index, entry)


def _check_bounds(slot_index: int) -> None:
    if not 0 <= slot_index < CHARACTER_SLOTS:
        raise IndexError(f"Slot {slot_index} out of range (0-{CHARACTER_SLOTS - 1})")


def _scan_steam64(data: bytearray) -> int | None:
    """Return the first Steam64 value found in decrypted data, or None."""
    i = 0
    end = len(data) - 8
    while i <= end:
        val = struct.unpack_from("<Q", data, i)[0]
        if _STEAM64_BASE <= val <= _STEAM64_MAX:
            return val
        i += 1
    return None


def _get_system_steam64(save: DSRSave) -> int | None:
    """Decrypt slot 10 (system data) and return the embedded Steam64, if any."""
    if save.is_ps:
        return None
    off = SLOTS_OFFSET + 10 * SLOT_SIZE
    iv = bytes(save._raw[off : off + 16])
    ciphertext = bytes(save._raw[off + 16 : off + 16 + SLOT_DATA_SIZE])
    plaintext = bytearray(_decrypt(iv, ciphertext))
    return _scan_steam64(plaintext)


def copy_slot(save: DSRSave, from_slot: int, to_slot: int) -> None:
    """Copy a character from one slot to another in the same save."""
    _check_bounds(from_slot)
    _check_bounds(to_slot)
    if from_slot == to_slot:
        raise ValueError("Source and destination slots cannot be the same")

    src = save.characters[from_slot]
    if src is None:
        raise ValueError(f"Slot {from_slot} is empty")

    save.characters[to_slot] = DSRCharacter(
        slot_index=to_slot, _data=bytearray(src.get_raw())
    )
    _write_dir_entry(save, to_slot, _read_dir_entry(save, from_slot))
    _set_active(save, to_slot, True)


def delete_slot(save: DSRSave, slot_index: int) -> None:
    """Clear a character slot the way the game does: zero its character data
    and clear its active flag."""
    _check_bounds(slot_index)
    _clear_slot_data(save, slot_index)
    save.characters[slot_index] = None
    _set_active(save, slot_index, False)


def swap_slots(save: DSRSave, slot_a: int, slot_b: int) -> None:
    """Swap two character slots."""
    _check_bounds(slot_a)
    _check_bounds(slot_b)
    if slot_a == slot_b:
        raise ValueError("Cannot swap a slot with itself")

    char_a = save.characters[slot_a]
    char_b = save.characters[slot_b]

    if char_a is not None:
        char_a.slot_index = slot_b
    if char_b is not None:
        char_b.slot_index = slot_a

    save.characters[slot_a], save.characters[slot_b] = char_b, char_a

    entry_a = _read_dir_entry(save, slot_a)
    entry_b = _read_dir_entry(save, slot_b)
    _write_dir_entry(save, slot_a, entry_b)
    _write_dir_entry(save, slot_b, entry_a)
    _set_active(save, slot_a, char_b is not None)
    _set_active(save, slot_b, char_a is not None)


def transfer_slot(
    source_save: DSRSave, from_slot: int, target_save: DSRSave, to_slot: int
) -> None:
    """Transfer a character to another save file, patching the embedded SteamID."""
    _check_bounds(from_slot)
    _check_bounds(to_slot)

    src = source_save.characters[from_slot]
    if src is None:
        raise ValueError(f"Slot {from_slot} is empty")

    data = bytearray(src.get_raw())

    old_steamid = _get_system_steam64(source_save)
    new_steamid = _get_system_steam64(target_save)
    if (
        old_steamid is not None
        and new_steamid is not None
        and old_steamid != new_steamid
    ):
        old_bytes = struct.pack("<Q", old_steamid)
        new_bytes = struct.pack("<Q", new_steamid)
        i = 0
        end = len(data) - 8
        while i <= end:
            if data[i : i + 8] == old_bytes:
                data[i : i + 8] = new_bytes
                i += 8
            else:
                i += 1

    target_save.characters[to_slot] = DSRCharacter(slot_index=to_slot, _data=data)
    _write_dir_entry(target_save, to_slot, _read_dir_entry(source_save, from_slot))
    _set_active(target_save, to_slot, True)


def export_character(save: DSRSave, slot_index: int, output_path: str | Path) -> None:
    """Export a character slot to a standalone .dsrc file."""
    _check_bounds(slot_index)
    char = save.characters[slot_index]
    if char is None:
        raise ValueError(f"Slot {slot_index} is empty")

    data = char.get_raw()

    with open(output_path, "wb") as f:
        f.write(_ERC_MAGIC)
        f.write(struct.pack("<I", _ERC_VERSION))
        f.write(struct.pack("<I", len(data)))
        f.write(data)

    with open(output_path, "rb") as f:
        checksum = hashlib.md5(f.read()).digest()

    with open(output_path, "ab") as f:
        f.write(checksum)


def read_character_file(input_path: str | Path) -> bytes:
    """Character data of a .dsrc file. Raises ValueError with a message for
    the user when the file is not a readable DSR character file, OSError when
    it cannot be read."""
    raw = Path(input_path).read_bytes()
    if raw[:4] != _ERC_MAGIC:
        raise ValueError("Not a DSR character file.")
    if len(raw) < _ERC_HEADER:
        raise ValueError("Not a DSR character file (too short).")
    version, size = struct.unpack_from("<II", raw, 4)
    if version != _ERC_VERSION:
        raise ValueError(
            f"Not a DSR character file this version can read (format {version})."
        )
    if size != SLOT_DATA_SIZE or len(raw) != _ERC_HEADER + size + _ERC_CHECKSUM:
        raise ValueError("Not a DSR character file (wrong size).")
    if hashlib.md5(raw[:-_ERC_CHECKSUM]).digest() != raw[-_ERC_CHECKSUM:]:
        raise ValueError("The DSR character file is damaged (checksum mismatch).")
    return raw[_ERC_HEADER:-_ERC_CHECKSUM]


def import_character(save: DSRSave, slot_index: int, input_path: str | Path) -> str:
    """Import a character from a .dsrc file into a slot. Returns the character name."""
    return import_character_data(save, slot_index, read_character_file(input_path))


def import_character_data(save: DSRSave, slot_index: int, data: bytes) -> str:
    """Write character data from read_character_file into a slot and its
    directory entry. Returns the character name."""
    _check_bounds(slot_index)

    data = bytearray(data)
    new_steamid = _get_system_steam64(save)
    if new_steamid is not None:
        old_steamid = _scan_steam64(data)
        if old_steamid is not None and old_steamid != new_steamid:
            old_bytes = struct.pack("<Q", old_steamid)
            new_bytes = struct.pack("<Q", new_steamid)
            i = 0
            end = len(data) - 8
            while i <= end:
                if data[i : i + 8] == old_bytes:
                    data[i : i + 8] = new_bytes
                    i += 8
                else:
                    i += 1

    char = DSRCharacter(slot_index=slot_index, _data=data)
    save.characters[slot_index] = char
    _sync_dir_name_level(save, slot_index, char.name, char.level)
    sync_dir_equipment(save, slot_index)
    _sync_dir_appearance(save, slot_index, char)
    _set_active(save, slot_index, True)
    return char.name
