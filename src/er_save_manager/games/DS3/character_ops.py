"""
Character operations for DS3: copy, transfer, swap, delete, export, import.

Each DS3 slot is an independently AES-CBC encrypted BND4 entry, so operations
work on plaintext bytearrays directly rather than splicing a shared raw
buffer. SteamID lives inside each character slot at a dynamic offset
(pointer at 0x58, +0x6F), separate from the slot's own gaitem-based offset
tracking, and mirrors the offset used by ds3_steamid.py.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from .save import DS3Save
from .slot import DS3Slot

_ERC_MAGIC = b"DS3C"
_ERC_VERSION = 1

# --- Character-select directory (in global entry 10) ------------------------
#
# The load-screen character list is a separate 10-entry directory stored in
# the global entry, not derived from the character slots themselves. Each
# entry mirrors the name and level of its character slot. Confirmed
# empirically against a real save (DS30000): copying a character into a
# previously-empty slot left its directory entry blank, and the copy was
# invisible on the in-game load screen despite the character slot itself
# being correct. character_ops must keep this directory in sync on every
# slot mutation.
#
# Layout per entry (554 bytes), offsets relative to entry start:
#   +0x00  34   Character name (UTF-16LE)
#   +0x22   4   Level (u32 LE)
#   remaining bytes: portrait thumbnail, appearance color cache, and other
#   load-screen display data not required for the character to load correctly.
#
# Entry 0 starts at DIR_BASE; entries are contiguous, DIR_STRIDE apart.
DIR_BASE = 4258
DIR_STRIDE = 554
DIR_NAME_OFFSET = 0x00
DIR_LEVEL_OFFSET = 0x22

# Canonical "unused slot" directory entry, captured from an untouched slot
# (identical across the never-used slots in the reference save, aside from a
# 4-byte scratch field at +0x21A that carries no meaning and is zeroed here).
# Used to restore a slot's directory entry to its proper empty state on delete.
_DIR_EMPTY_TEMPLATE = bytes.fromhex(
    "0000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000ffffffff00000000ffffffff464143450300"
    "0000f40000000000000000000000000000000000000000000000000000000000"
    "00000000000000000000808080ff808080ff808080ff808080ff808080ff8080"
    "80ff808080ff808080ff808080ff000000008080808080808000000000000000"
    "0000000000000000000000008080808080808080808080808080808080808080"
    "8080808080808080808080808080808080808080808080808080808080808080"
    "8080808080808080808080808080808080808080808080808080808080808080"
    "8080808080808080808080808080808080808080808080808080808080808080"
    "8080808080808080808080800000c0b684420100000001000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "00000000000000000000ffffffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffff00000000000000000000000000000000000000000100"
    "00000000000000000000"
)


def _dir_entry_offset(slot_index: int) -> int:
    return DIR_BASE + slot_index * DIR_STRIDE


def _read_dir_entry(save: DS3Save, slot_index: int) -> bytearray:
    dec = save._parser.get_slot(10)
    off = _dir_entry_offset(slot_index)
    return bytearray(dec[off : off + DIR_STRIDE])


def _write_dir_entry(save: DS3Save, slot_index: int, entry: bytes) -> None:
    if len(entry) != DIR_STRIDE:
        raise ValueError(
            f"Directory entry must be {DIR_STRIDE} bytes, got {len(entry)}"
        )
    dec = save._parser.get_slot(10)
    off = _dir_entry_offset(slot_index)
    dec[off : off + DIR_STRIDE] = entry


def _sync_dir_name_level(save: DS3Save, slot_index: int, name: str, level: int) -> None:
    """Patch just the name and level fields of a slot's directory entry.

    Used when the source character has no directory entry of its own to copy
    from (import from a standalone .ds3c file). Everything else in the entry
    (portrait thumbnail, appearance cache) is left as-is; the game regenerates
    those from the character slot itself the next time it is loaded in-game.
    """
    existing = _read_dir_entry(save, slot_index)
    if bytes(existing) == _DIR_EMPTY_TEMPLATE:
        entry = bytearray(_DIR_EMPTY_TEMPLATE)
    else:
        entry = existing
    name_bytes = name.encode("utf-16-le").ljust(34, b"\x00")[:34]
    entry[DIR_NAME_OFFSET : DIR_NAME_OFFSET + 34] = name_bytes
    struct.pack_into("<I", entry, DIR_LEVEL_OFFSET, level & 0xFFFFFFFF)
    _write_dir_entry(save, slot_index, entry)


def _check_bounds(slot_index: int) -> None:
    if not 0 <= slot_index < DS3Save.CHARACTER_SLOTS:
        raise IndexError(
            f"Slot {slot_index} out of range (0-{DS3Save.CHARACTER_SLOTS - 1})"
        )


def _get_global_steam32(save: DS3Save) -> int | None:
    """Read the Steam32 account ID from the global entry (index 10)."""
    dec = save._parser.get_slot(10)
    if len(dec) < 0xC:
        return None
    steam32 = struct.unpack_from("<i", dec, 0x8)[0]
    return steam32 if steam32 > 0 else None


def _patch_slot_steamid(data: bytearray, new_steam32: int) -> None:
    """Patch the SteamID embedded in a character slot, if the pointer resolves in bounds."""
    if len(data) < 0x5C:
        return
    ptr = struct.unpack_from("<i", data, 0x58)[0]
    steam_off = ptr + 0x6F
    if steam_off < 0 or steam_off + 4 > len(data):
        return
    struct.pack_into("<i", data, steam_off, new_steam32)


def copy_slot(save: DS3Save, from_slot: int, to_slot: int) -> None:
    """Copy a character from one slot to another in the same save."""
    _check_bounds(from_slot)
    _check_bounds(to_slot)
    if from_slot == to_slot:
        raise ValueError("Source and destination slots cannot be the same")

    src = save.characters[from_slot]
    if src is None:
        raise ValueError(f"Slot {from_slot} is empty")

    save.characters[to_slot] = DS3Slot(to_slot, bytearray(src.get_raw()))
    _write_dir_entry(save, to_slot, _read_dir_entry(save, from_slot))


def delete_slot(save: DS3Save, slot_index: int) -> None:
    """Clear a character slot, zeroing the underlying encrypted entry."""
    _check_bounds(slot_index)
    size = save._parser.get_slot_plaintext_size(slot_index)
    save._parser.set_slot(slot_index, bytearray(size))
    save.characters[slot_index] = None
    _write_dir_entry(save, slot_index, _DIR_EMPTY_TEMPLATE)


def swap_slots(save: DS3Save, slot_a: int, slot_b: int) -> None:
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
    source_save: DS3Save, from_slot: int, target_save: DS3Save, to_slot: int
) -> None:
    """Transfer a character to another save file, patching the embedded SteamID."""
    _check_bounds(from_slot)
    _check_bounds(to_slot)

    src = source_save.characters[from_slot]
    if src is None:
        raise ValueError(f"Slot {from_slot} is empty")

    data = bytearray(src.get_raw())

    new_steam32 = _get_global_steam32(target_save)
    if new_steam32 is not None:
        _patch_slot_steamid(data, new_steam32)

    target_save.characters[to_slot] = DS3Slot(to_slot, data)
    _write_dir_entry(target_save, to_slot, _read_dir_entry(source_save, from_slot))


def export_character(save: DS3Save, slot_index: int, output_path: str | Path) -> None:
    """Export a character slot to a standalone .ds3c file."""
    _check_bounds(slot_index)
    char = save.characters[slot_index]
    if char is None:
        raise ValueError(f"Slot {slot_index} is empty")

    data = bytes(char.get_raw())

    with open(output_path, "wb") as f:
        f.write(_ERC_MAGIC)
        f.write(struct.pack("<I", _ERC_VERSION))
        f.write(struct.pack("<I", len(data)))
        f.write(data)

    with open(output_path, "rb") as f:
        checksum = hashlib.md5(f.read()).digest()

    with open(output_path, "ab") as f:
        f.write(checksum)


def import_character(save: DS3Save, slot_index: int, input_path: str | Path) -> str:
    """Import a character from a .ds3c file into a slot. Returns the character name."""
    _check_bounds(slot_index)

    with open(input_path, "rb") as f:
        magic = f.read(4)
        if magic != _ERC_MAGIC:
            raise ValueError("Invalid .ds3c file: bad magic")

        version = struct.unpack("<I", f.read(4))[0]
        if version != _ERC_VERSION:
            raise ValueError(f"Unsupported .ds3c version: {version}")

        size = struct.unpack("<I", f.read(4))[0]
        data = f.read(size)
        checksum_expected = f.read(16)

    with open(input_path, "rb") as f:
        checksum_actual = hashlib.md5(f.read()[:-16]).digest()

    if checksum_actual != checksum_expected:
        raise ValueError("Checksum mismatch - file may be corrupted")

    expected_size = save._parser.get_slot_plaintext_size(slot_index)
    if len(data) != expected_size:
        raise ValueError(
            f"Slot data size mismatch: expected {expected_size} bytes, got {len(data)}"
        )

    data = bytearray(data)
    new_steam32 = _get_global_steam32(save)
    if new_steam32 is not None:
        _patch_slot_steamid(data, new_steam32)

    char = DS3Slot(slot_index, data)
    save.characters[slot_index] = char
    _sync_dir_name_level(save, slot_index, char.name, char.level)
    return char.name
