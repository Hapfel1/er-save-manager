"""
Character operations for Nightreign: copy, transfer, swap, delete, export, import.

Each slot is an independently AES-CBC encrypted BND4 entry (entries 0-9).
NightreignSlot.decrypted is the same bytearray object as the corresponding
BND4Entry.decrypted, so all writes go through in-place slice assignment on
the entry buffer, then the slot is re-parsed so its cached offsets match the
new content. SteamID is only stored in the global entry (index 10), not in
character slots, so no per-slot SteamID patch is needed on transfer.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from .parser import NightreignSave, _parse_slot

_ERC_MAGIC = b"NRC\x00"
_ERC_VERSION = 1
CHARACTER_SLOTS = 10


def _check_bounds(slot_index: int) -> None:
    if not 0 <= slot_index < CHARACTER_SLOTS:
        raise IndexError(f"Slot {slot_index} out of range (0-{CHARACTER_SLOTS - 1})")


def copy_slot(save: NightreignSave, from_slot: int, to_slot: int) -> None:
    """Copy a character from one slot to another in the same save."""
    _check_bounds(from_slot)
    _check_bounds(to_slot)
    if from_slot == to_slot:
        raise ValueError("Source and destination slots cannot be the same")

    if save.slots[from_slot].is_empty():
        raise ValueError(f"Slot {from_slot} is empty")

    src_entry = save.entries[from_slot]
    dst_entry = save.entries[to_slot]
    data = bytes(src_entry.decrypted)
    if len(data) != len(dst_entry.decrypted):
        raise ValueError("Slot size mismatch between source and destination")

    dst_entry.decrypted[:] = data
    save.slots[to_slot] = _parse_slot(dst_entry.decrypted, to_slot)


def delete_slot(save: NightreignSave, slot_index: int) -> None:
    """Clear a character slot."""
    _check_bounds(slot_index)
    entry = save.entries[slot_index]
    entry.decrypted[:] = bytes(len(entry.decrypted))
    save.slots[slot_index] = _parse_slot(entry.decrypted, slot_index)


def swap_slots(save: NightreignSave, slot_a: int, slot_b: int) -> None:
    """Swap two character slots."""
    _check_bounds(slot_a)
    _check_bounds(slot_b)
    if slot_a == slot_b:
        raise ValueError("Cannot swap a slot with itself")

    entry_a = save.entries[slot_a]
    entry_b = save.entries[slot_b]
    if len(entry_a.decrypted) != len(entry_b.decrypted):
        raise ValueError("Slot size mismatch between the two slots")

    data_a = bytes(entry_a.decrypted)
    data_b = bytes(entry_b.decrypted)
    entry_a.decrypted[:] = data_b
    entry_b.decrypted[:] = data_a

    save.slots[slot_a] = _parse_slot(entry_a.decrypted, slot_a)
    save.slots[slot_b] = _parse_slot(entry_b.decrypted, slot_b)


def transfer_slot(
    source_save: NightreignSave,
    from_slot: int,
    target_save: NightreignSave,
    to_slot: int,
) -> None:
    """Transfer a character to another save file."""
    _check_bounds(from_slot)
    _check_bounds(to_slot)

    if source_save.slots[from_slot].is_empty():
        raise ValueError(f"Slot {from_slot} is empty")

    src_entry = source_save.entries[from_slot]
    dst_entry = target_save.entries[to_slot]
    data = bytes(src_entry.decrypted)
    if len(data) != len(dst_entry.decrypted):
        raise ValueError("Slot size mismatch between source and target saves")

    dst_entry.decrypted[:] = data
    target_save.slots[to_slot] = _parse_slot(dst_entry.decrypted, to_slot)


def export_character(
    save: NightreignSave, slot_index: int, output_path: str | Path
) -> None:
    """Export a character slot to a standalone .nrc file."""
    _check_bounds(slot_index)
    if save.slots[slot_index].is_empty():
        raise ValueError(f"Slot {slot_index} is empty")

    data = bytes(save.entries[slot_index].decrypted)

    with open(output_path, "wb") as f:
        f.write(_ERC_MAGIC)
        f.write(struct.pack("<I", _ERC_VERSION))
        f.write(struct.pack("<I", len(data)))
        f.write(data)

    with open(output_path, "rb") as f:
        checksum = hashlib.md5(f.read()).digest()

    with open(output_path, "ab") as f:
        f.write(checksum)


def import_character(
    save: NightreignSave, slot_index: int, input_path: str | Path
) -> str:
    """Import a character from a .nrc file into a slot. Returns the player name."""
    _check_bounds(slot_index)

    with open(input_path, "rb") as f:
        magic = f.read(4)
        if magic != _ERC_MAGIC:
            raise ValueError("Invalid .nrc file: bad magic")

        version = struct.unpack("<I", f.read(4))[0]
        if version != _ERC_VERSION:
            raise ValueError(f"Unsupported .nrc version: {version}")

        size = struct.unpack("<I", f.read(4))[0]
        data = f.read(size)
        checksum_expected = f.read(16)

    with open(input_path, "rb") as f:
        checksum_actual = hashlib.md5(f.read()[:-16]).digest()

    if checksum_actual != checksum_expected:
        raise ValueError("Checksum mismatch - file may be corrupted")

    entry = save.entries[slot_index]
    if len(data) != len(entry.decrypted):
        raise ValueError(
            f"Slot data size mismatch: expected {len(entry.decrypted)} bytes, got {len(data)}"
        )

    entry.decrypted[:] = data
    save.slots[slot_index] = _parse_slot(entry.decrypted, slot_index)
    return save.slots[slot_index].player_name
