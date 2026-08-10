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
_STEAM64_BASE = 0x0110000100000000
_STEAM64_MAX = 0x01100001FFFFFFFF

# --- Character-select directory (in system_data / slot 10) -----------------
#
# The load-screen character list is a separate 10-entry directory stored in
# slot 10, not derived from the character slots themselves. Each entry mirrors
# the name and level of its character slot. Copying a character into a previously-empty slot left
# its directory entry blank, and the copy was invisible on the in-game load
# screen despite the character slot itself being correct. character_ops must
# keep this directory in sync on every slot mutation.
#
# Layout per entry (400 bytes), offsets relative to entry start:
#   +0x28  34   Character name (UTF-16LE, mirrors OFF_NAME_PRIMARY)
#   +0x4C   4   Level (u32 LE)
#   remaining bytes: portrait thumbnail, appearance color cache, and other
#   load-screen display data not required for the character to load correctly.
#
# Entry 0 starts at DIR_BASE; entries are contiguous, DIR_STRIDE apart.
DIR_BASE = 172
DIR_STRIDE = 400
DIR_NAME_OFFSET = 0x28
DIR_LEVEL_OFFSET = 0x4C

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
    save.system_data[off : off + DIR_STRIDE] = entry


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


def delete_slot(save: DSRSave, slot_index: int) -> None:
    """Clear a character slot."""
    _check_bounds(slot_index)
    save.characters[slot_index] = None
    _write_dir_entry(save, slot_index, _DIR_EMPTY_TEMPLATE)


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


def import_character(save: DSRSave, slot_index: int, input_path: str | Path) -> str:
    """Import a character from a .dsrc file into a slot. Returns the character name."""
    _check_bounds(slot_index)

    with open(input_path, "rb") as f:
        magic = f.read(4)
        if magic != _ERC_MAGIC:
            raise ValueError("Invalid .dsrc file: bad magic")

        version = struct.unpack("<I", f.read(4))[0]
        if version != _ERC_VERSION:
            raise ValueError(f"Unsupported .dsrc version: {version}")

        size = struct.unpack("<I", f.read(4))[0]
        data = f.read(size)
        checksum_expected = f.read(16)

    with open(input_path, "rb") as f:
        checksum_actual = hashlib.md5(f.read()[:-16]).digest()

    if checksum_actual != checksum_expected:
        raise ValueError("Checksum mismatch - file may be corrupted")

    if len(data) != SLOT_DATA_SIZE:
        raise ValueError(
            f"Slot data size mismatch: expected {SLOT_DATA_SIZE} bytes, got {len(data)}"
        )

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
    return char.name
