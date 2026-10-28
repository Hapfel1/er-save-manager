"""
Character operations for DS3: copy, transfer, swap, delete, export, import.

Each DS3 slot is an independently stored entry (AES-CBC BND4 entry on PC,
one userdata file on PS4), so operations work on plaintext bytearrays
directly rather than splicing a shared raw buffer. The Steam64 ID lives
inside each character slot as a u64 0x6F bytes into the last section of the
slot's section directory (offset stored at 0x58, see slot.py), the same
location ds3_steamid.py patches. PC slots hold the global entry's Steam64 ID,
PS4 slots hold 0.

A PS4 save opened without its userdata0010 file has no character-select
directory; directory reads then return the empty entry and writes are
skipped.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from .save import DS3Save
from .slot import DS3Slot, LayoutError

_ERC_MAGIC = b"DS3C"
_ERC_VERSION = 1

# --- Character-select directory (in global entry 10) ------------------------
#
# The load-screen character list is a separate 10-entry directory stored in
# the global entry, not derived from the character slots themselves. Each
# entry mirrors the name and level of its character slot.
#
# Layout per entry (554 bytes), offsets relative to entry start:
#   +0x00  34   Character name (UTF-16LE)
#   +0x22   4   Level (u32 LE)
#   +0x3A       Appearance block (mirrors the slot's FACE block)
#   +0x1AA 88   Item ids of the 22 equip slots (copy of the slot's id block)
#   remaining bytes: other load-screen display data not required for the
#   character to load correctly.
#
# Entry 0 starts at DIR_BASE; entries are contiguous, DIR_STRIDE apart.
DIR_BASE = 4258
DIR_STRIDE = 554
DIR_NAME_OFFSET = 0x00
DIR_LEVEL_OFFSET = 0x22
DIR_FACE_OFFSET = 0x3A
DIR_EQUIP_OFFSET = 0x1AA

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
    if not save.has_directory:
        return bytearray(_DIR_EMPTY_TEMPLATE)
    dec = save._parser.get_slot(10)
    off = _dir_entry_offset(slot_index)
    return bytearray(dec[off : off + DIR_STRIDE])


def _write_dir_entry(save: DS3Save, slot_index: int, entry: bytes) -> None:
    if len(entry) != DIR_STRIDE:
        raise ValueError(
            f"Directory entry must be {DIR_STRIDE} bytes, got {len(entry)}"
        )
    if not save.has_directory:
        return
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


def sync_dir_equipment(save: DS3Save, slot_index: int) -> None:
    """Copy a character's equip slot item ids into its directory entry, which
    the load screen reads."""
    char = save.characters[slot_index]
    if char is None:
        return
    entry = _read_dir_entry(save, slot_index)
    ids = char.equipped_ids()
    struct.pack_into(f"<{len(ids)}I", entry, DIR_EQUIP_OFFSET, *ids)
    _write_dir_entry(save, slot_index, entry)


def _sync_dir_face(save: DS3Save, slot_index: int, block: bytes) -> None:
    """Copy the slot's appearance block into its directory entry. An entry
    without a block header of the same size is left alone."""
    entry = _read_dir_entry(save, slot_index)
    end = DIR_FACE_OFFSET + len(block)
    if end > DIR_STRIDE or entry[DIR_FACE_OFFSET : DIR_FACE_OFFSET + 12] != block[:12]:
        return
    entry[DIR_FACE_OFFSET:end] = block
    _write_dir_entry(save, slot_index, entry)


def _sync_dir_from_slot(save: DS3Save, slot_index: int) -> None:
    """Fill a slot's directory entry from the character slot alone: name,
    level, appearance block and equipped item ids. Fields whose offsets do
    not resolve on this slot are left as they are."""
    char = save.characters[slot_index]
    _sync_dir_name_level(save, slot_index, char.name, char.level)
    try:
        _sync_dir_face(save, slot_index, char.face_block)
    except LayoutError:
        pass
    try:
        sync_dir_equipment(save, slot_index)
    except LayoutError:
        pass


def _check_bounds(slot_index: int) -> None:
    if not 0 <= slot_index < DS3Save.CHARACTER_SLOTS:
        raise IndexError(
            f"Slot {slot_index} out of range (0-{DS3Save.CHARACTER_SLOTS - 1})"
        )


def _check_available(save: DS3Save, slot_index: int) -> None:
    if not save.slot_available(slot_index):
        raise ValueError(save.missing_slot_message(slot_index))


def _target_steam64(save: DS3Save) -> int | None:
    """Steam64 ID a character slot written into save must carry: 0 on PS4,
    the global entry's u64 at 0x8 on PC, None when it cannot be read."""
    if save.is_ps:
        return 0
    dec = save._parser.get_slot(10)
    if len(dec) < 0x10:
        return None
    steam32 = struct.unpack_from("<i", dec, 0x8)[0]
    if steam32 <= 0:
        return None
    return struct.unpack_from("<Q", dec, 0x8)[0]


def _patch_slot_steamid(data: bytearray, new_steam64: int) -> None:
    """Patch the Steam64 ID embedded in a character slot, if the pointer resolves in bounds."""
    if len(data) < 0x5C:
        return
    ptr = struct.unpack_from("<i", data, 0x58)[0]
    steam_off = ptr + 0x6F
    if steam_off < 0 or steam_off + 8 > len(data):
        return
    struct.pack_into("<Q", data, steam_off, new_steam64)


def copy_slot(save: DS3Save, from_slot: int, to_slot: int) -> None:
    """Copy a character from one slot to another in the same save."""
    _check_bounds(from_slot)
    _check_bounds(to_slot)
    if from_slot == to_slot:
        raise ValueError("Source and destination slots cannot be the same")
    _check_available(save, to_slot)

    src = save.characters[from_slot]
    if src is None:
        raise ValueError(f"Slot {from_slot} is empty")

    save.characters[to_slot] = DS3Slot(to_slot, bytearray(src.get_raw()))
    _write_dir_entry(save, to_slot, _read_dir_entry(save, from_slot))


def delete_slot(save: DS3Save, slot_index: int) -> None:
    """Clear a character slot, zeroing the underlying encrypted entry."""
    _check_bounds(slot_index)
    _check_available(save, slot_index)
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
    _check_available(save, slot_a)
    _check_available(save, slot_b)

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
    _check_available(target_save, to_slot)

    src = source_save.characters[from_slot]
    if src is None:
        raise ValueError(f"Slot {from_slot} is empty")

    data = bytearray(src.get_raw())

    new_steam64 = _target_steam64(target_save)
    if new_steam64 is not None:
        _patch_slot_steamid(data, new_steam64)

    target_save.characters[to_slot] = DS3Slot(to_slot, data)
    if source_save.has_directory:
        _write_dir_entry(target_save, to_slot, _read_dir_entry(source_save, from_slot))
    else:
        _sync_dir_from_slot(target_save, to_slot)


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


_ERC_HEADER = struct.Struct("<4sII")
_ERC_CHECKSUM_SIZE = 16


def read_character_file(
    save: DS3Save, slot_index: int, input_path: str | Path
) -> bytearray:
    """Slot data of a .ds3c file, checked against the file's checksum and the
    plaintext size of slot_index in save. Raises ValueError with a message
    for the user."""
    _check_bounds(slot_index)
    _check_available(save, slot_index)
    raw = Path(input_path).read_bytes()
    if raw[:4] != _ERC_MAGIC:
        raise ValueError("Not a Dark Souls III character file (.ds3c).")
    if len(raw) < _ERC_HEADER.size:
        raise ValueError("The character file is cut off.")
    _, version, size = _ERC_HEADER.unpack_from(raw)
    if version != _ERC_VERSION:
        raise ValueError(f"Unsupported .ds3c version {version}.")
    end = _ERC_HEADER.size + size
    if len(raw) < end + _ERC_CHECKSUM_SIZE:
        raise ValueError("The character file is cut off.")
    if hashlib.md5(raw[:end]).digest() != raw[end : end + _ERC_CHECKSUM_SIZE]:
        raise ValueError("The character file is damaged (checksum mismatch).")
    expected_size = save._parser.get_slot_plaintext_size(slot_index)
    if size != expected_size:
        raise ValueError(
            f"The character data is {size:,} bytes, a slot in this save holds "
            f"{expected_size:,}."
        )
    return bytearray(raw[_ERC_HEADER.size : end])


def import_character(save: DS3Save, slot_index: int, input_path: str | Path) -> str:
    """Import a character from a .ds3c file into a slot. Returns the character name."""
    _check_bounds(slot_index)
    _check_available(save, slot_index)
    return place_character(
        save, slot_index, read_character_file(save, slot_index, input_path)
    )


def place_character(save: DS3Save, slot_index: int, data: bytearray) -> str:
    """Write slot data from read_character_file() into a slot. Returns the
    character name."""
    _check_bounds(slot_index)
    _check_available(save, slot_index)
    new_steam64 = _target_steam64(save)
    if new_steam64 is not None:
        _patch_slot_steamid(data, new_steam64)

    save.characters[slot_index] = DS3Slot(slot_index, data)
    _sync_dir_from_slot(save, slot_index)
    return save.characters[slot_index].name
