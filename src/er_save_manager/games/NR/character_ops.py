"""
Character operations for Nightreign: copy, transfer, swap, delete, export, import.

Each slot is an independently AES-CBC encrypted BND4 entry (entries 0-9).
NightreignSlot.decrypted is the same bytearray object as the corresponding
BND4Entry.decrypted, so all writes go through in-place slice assignment on
the entry buffer, then the slot is re-parsed so its cached offsets match the
new content. Each character slot carries its own copy of the owner SteamID
(the global entry 10 holds the other); PC stores the account SteamID, PS
stores 0. Transfer and import rewrite it to match the target save.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from .parser import NightreignSave, _parse_slot

_ERC_MAGIC = b"NRC\x00"
_ERC_VERSION = 1
CHARACTER_SLOTS = 10

# Global entry (entry 10): one u8 per slot, 1 while the game lists the slot,
# then one load-screen summary per slot starting with the UTF-16LE name.
_E10_SLOT_IN_USE = 0x1958
_E10_SUMMARY = _E10_SLOT_IN_USE + CHARACTER_SLOTS
_E10_SUMMARY_STRIDE = 0x290
_SUMMARY_NAME_SIZE = 0x22  # 16 UTF-16 units and a terminator
# Every slot entry starts with this header, empty or not; the rest of an
# empty slot is zero.
_SLOT_HEADER_SIZE = 4


def _check_bounds(slot_index: int) -> None:
    if not 0 <= slot_index < CHARACTER_SLOTS:
        raise IndexError(f"Slot {slot_index} out of range (0-{CHARACTER_SLOTS - 1})")


def _sync_slot_steam_id(save: NightreignSave, slot_index: int) -> None:
    """Set the slot SteamID to the target save's owner (0 on PlayStation)."""
    slot = save.slots[slot_index]
    if slot.steam_id_offset < 0:
        return
    if save.is_ps:
        slot.steam_id = 0
    elif save.profile is not None and save.profile.steam_id:
        slot.steam_id = save.profile.steam_id


def _global(save: NightreignSave) -> bytearray:
    return save.entries[CHARACTER_SLOTS].decrypted


def _summary_span(slot_index: int) -> slice:
    start = _E10_SUMMARY + slot_index * _E10_SUMMARY_STRIDE
    return slice(start, start + _E10_SUMMARY_STRIDE)


def _set_in_use(save: NightreignSave, slot_index: int, in_use: bool) -> None:
    _global(save)[_E10_SLOT_IN_USE + slot_index] = 1 if in_use else 0


def _sync_summary_name(save: NightreignSave, slot_index: int) -> None:
    """Write the slot's player name into its load-screen summary."""
    name = save.slots[slot_index].player_name.encode("utf-16-le")
    start = _summary_span(slot_index).start
    _global(save)[start : start + _SUMMARY_NAME_SIZE] = name[
        : _SUMMARY_NAME_SIZE - 2
    ].ljust(_SUMMARY_NAME_SIZE, b"\x00")


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
    g = _global(save)
    g[_summary_span(to_slot)] = g[_summary_span(from_slot)]
    _set_in_use(save, to_slot, True)


def delete_slot(save: NightreignSave, slot_index: int) -> None:
    """Clear a character slot the way the game leaves an empty one: header
    kept, rest zero, in-use flag off, empty summary."""
    _check_bounds(slot_index)
    entry = save.entries[slot_index]
    size = len(entry.decrypted)
    entry.decrypted[_SLOT_HEADER_SIZE:] = bytes(size - _SLOT_HEADER_SIZE)
    save.slots[slot_index] = _parse_slot(entry.decrypted, slot_index)
    _set_in_use(save, slot_index, False)
    # Empty slots carry the same summary template; reuse another empty
    # slot's when the save has one.
    g = _global(save)
    for other in range(CHARACTER_SLOTS):
        if other != slot_index and not g[_E10_SLOT_IN_USE + other]:
            g[_summary_span(slot_index)] = g[_summary_span(other)]
            break


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
    g = _global(save)
    span_a, span_b = _summary_span(slot_a), _summary_span(slot_b)
    g[span_a], g[span_b] = bytes(g[span_b]), bytes(g[span_a])
    in_a, in_b = g[_E10_SLOT_IN_USE + slot_a], g[_E10_SLOT_IN_USE + slot_b]
    g[_E10_SLOT_IN_USE + slot_a], g[_E10_SLOT_IN_USE + slot_b] = in_b, in_a


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
    _sync_slot_steam_id(target_save, to_slot)
    _global(target_save)[_summary_span(to_slot)] = _global(source_save)[
        _summary_span(from_slot)
    ]
    _set_in_use(target_save, to_slot, True)


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


def read_character_file(input_path: str | Path, slot_size: int) -> bytes:
    """Slot data of a .nrc file. ValueError with a plain message when the
    file cannot be read, is not a character file, is damaged or holds a slot
    of another size than slot_size."""
    try:
        raw = Path(input_path).read_bytes()
    except OSError as e:
        raise ValueError(f"The file cannot be read: {e.strerror or e}") from None
    header = len(_ERC_MAGIC) + 8
    if raw[: len(_ERC_MAGIC)] != _ERC_MAGIC:
        raise ValueError("The file is not a Nightreign character file (.nrc).")
    if len(raw) < header:
        raise ValueError("The character file is cut off.")
    version, size = struct.unpack_from("<II", raw, len(_ERC_MAGIC))
    if version != _ERC_VERSION:
        raise ValueError(
            f"The character file has format version {version}; this version "
            f"of the save manager reads version {_ERC_VERSION}."
        )
    if len(raw) < header + size + 16:
        raise ValueError("The character file is cut off.")
    if (
        hashlib.md5(raw[: header + size]).digest()
        != raw[header + size : header + size + 16]
    ):
        raise ValueError("The character file is damaged (checksum mismatch).")
    if size != slot_size:
        raise ValueError(
            f"The character file holds {size} bytes of slot data; slots in "
            f"this save hold {slot_size}."
        )
    data = raw[header : header + size]
    try:
        slot = _parse_slot(bytearray(data), 0)
    except Exception:
        raise ValueError("The character in the file cannot be read.") from None
    if slot.is_empty():
        raise ValueError("The character file holds an empty slot.")
    if slot.is_unreadable:
        raise ValueError("The character in the file cannot be read.")
    return data


def import_character(
    save: NightreignSave, slot_index: int, input_path: str | Path
) -> str:
    """Import a character from a .nrc file into a slot. Returns the player name."""
    _check_bounds(slot_index)
    entry = save.entries[slot_index]
    data = read_character_file(input_path, len(entry.decrypted))
    entry.decrypted[:] = data
    save.slots[slot_index] = _parse_slot(entry.decrypted, slot_index)
    _sync_slot_steam_id(save, slot_index)
    _sync_summary_name(save, slot_index)
    _set_in_use(save, slot_index, True)
    return save.slots[slot_index].player_name
