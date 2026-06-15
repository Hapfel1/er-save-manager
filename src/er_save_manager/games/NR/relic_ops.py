"""
Relic spawn and removal operations for Nightreign save slots.

Spawn algorithm
---------------
The slot's state section is consumed by a fixed 5120-state loop. Each state
occupies a variable number of bytes (8 for empty/goods, 16 for armor, 80 for
relic, 88 for weapon). The loop reads exactly 5120 states; everything after
the loop (player name, currencies, item entries) sits at a fixed position
relative to the loop's final cursor.

Adding an 80-byte relic in place of ten 8-byte empty states would reduce the
number of loop iterations that reach the post-state data by 9 (9 * 8 = 72 bytes
"missing"). To compensate, we insert 72 null bytes at the spawn position before
writing the relic. Those 72 bytes are parsed as 9 additional empty 8-byte
states, so the loop's cursor still lands at the same position relative to the
player-data block.

Concretely:
  1. Find the first 8-byte empty state slot at or after the last existing relic.
  2. Insert 72 null bytes at that offset (expanding the bytearray by 72 bytes).
  3. Write the 80-byte relic block at that offset (overwriting the 72 nulls +
     the original 8-byte slot = 80 bytes total).
  4. Find and update the ItemEntry slot (also shifted by 72 bytes).
  5. Increment entry_count at its shifted offset.

Removal is the inverse: zero the 80-byte relic state, then remove the 72
compensating null bytes, restoring the original layout.
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.games.NR.parser import NightreignSlot

ITEM_TYPE_RELIC = 0xC0000000
STATE_KEEP_START = 84
_STATE_SLOT_COUNT = 5120

_STATE_SIZE = {
    0x00000000: 8,
    0x80000000: 88,
    0x90000000: 16,
    0xB0000000: 8,
    0xC0000000: 80,
}

# Fixed padding bytes within a relic state at offsets +0x1C-0x37
_RELIC_PAD_1C = bytes.fromhex(
    "ffffffffffffffff000000ff0000000000000000ffffffffffffffff"
)


def _walk_states_cursor(dec: bytearray) -> int:
    """Return the cursor position after the 5120-state loop."""
    cursor = 0x14
    for _ in range(_STATE_SLOT_COUNT):
        ga = struct.unpack_from("<I", dec, cursor)[0]
        type_bits = ga & 0xF0000000
        cursor += _STATE_SIZE.get(type_bits, 8)
    return cursor


def _entry_count_offset(dec: bytearray) -> int:
    """Recompute the entry_count field offset from the current state layout."""
    return _walk_states_cursor(dec) + 0x94 + 0x5B8


def _next_relic_handle(slot: NightreignSlot) -> int:
    if not slot.relic_states:
        return ITEM_TYPE_RELIC | 0x800001
    return ITEM_TYPE_RELIC | (max(h & 0x00FFFFFF for h in slot.relic_states) + 1)


def _find_spawn_offset(slot: NightreignSlot) -> int | None:
    """
    Return the absolute offset of the first 8-byte empty state slot at or after
    the last existing relic state. Returns None if no suitable slot exists.
    """
    last_relic_off = -1
    for _ga, rs in slot.relic_states.items():
        if rs.abs_offset > last_relic_off:
            last_relic_off = rs.abs_offset

    for ga, size, off in slot.item_states:
        if off <= last_relic_off:
            continue
        if ga == 0 and size == 8:
            return off
    return None


def spawn_relic(
    slot: NightreignSlot,
    real_item_id: int,
    effect_1: int = 0xFFFFFFFF,
    effect_2: int = 0xFFFFFFFF,
    effect_3: int = 0xFFFFFFFF,
    curse_1: int = 0xFFFFFFFF,
    curse_2: int = 0xFFFFFFFF,
    curse_3: int = 0xFFFFFFFF,
    validate: bool = True,
) -> int:
    """
    Spawn a relic. Returns the new ga_handle.
    Raises ValueError on invalid IDs (when validate=True).
    Raises RuntimeError if there is no free space.
    """
    if validate:
        from er_save_manager.games.NR.item_db import (
            get_relic,
            validate_curse,
            validate_effect,
        )

        relic_row = get_relic(real_item_id)
        if relic_row is None:
            raise ValueError(f"Unknown relic ID {real_item_id}")
        is_deep = relic_row["deep"]

        # Warn on duplicate
        existing = [
            rs for rs in slot.relic_states.values() if rs.real_item_id == real_item_id
        ]
        if existing:
            raise ValueError(
                f"This save already contains a '{relic_row['name']}' (ID {real_item_id}). "
                f"The game will remove duplicates on load."
            )

        for slot_num, ef in enumerate([effect_1, effect_2, effect_3], 1):
            err = validate_effect(ef, is_deep)
            if err:
                raise ValueError(f"Effect slot {slot_num}: {err}")
        for slot_num, ef in enumerate([curse_1, curse_2, curse_3], 1):
            err = validate_curse(ef)
            if err:
                raise ValueError(f"Curse slot {slot_num}: {err}")

    # Special relics (real_item_id < 100000) have effect_1 == real_item_id by game convention.
    if real_item_id < 100000:
        effect_1 = real_item_id

    spawn_offset = _find_spawn_offset(slot)
    if spawn_offset is None:
        raise RuntimeError("No free state slot found after existing relics")

    free_entries = [e for e in slot.item_entries if e.is_empty]
    if not free_entries:
        raise RuntimeError("No free item entry slots")

    # Read entry_count before expanding the buffer
    old_count = struct.unpack_from("<I", slot.decrypted, slot.entry_count_offset)[0]
    ga_handle = _next_relic_handle(slot)
    item_id = 0x80000000 | (real_item_id & 0x00FFFFFF)

    # Insert 72 null bytes at spawn_offset to compensate for the state-loop delta.
    # Insert 8 null bytes before the 28-byte checksum tail so total expansion = 80
    # bytes (multiple of AES-128 block size = 16).
    slot.decrypted[spawn_offset:spawn_offset] = b"\x00" * 72
    tail_pos = len(slot.decrypted) - 28
    slot.decrypted[tail_pos:tail_pos] = b"\x00" * 8

    # Write the 80-byte relic state at spawn_offset
    dec = slot.decrypted
    struct.pack_into(
        "<4I", dec, spawn_offset, ga_handle, item_id, item_id, 0xFFFFFFFF
    )  # +0x00
    struct.pack_into(
        "<3I", dec, spawn_offset + 0x10, effect_1, effect_2, effect_3
    )  # +0x10
    dec[spawn_offset + 0x1C : spawn_offset + 0x38] = _RELIC_PAD_1C  # +0x1C
    struct.pack_into(
        "<3I", dec, spawn_offset + 0x38, curse_1, curse_2, curse_3
    )  # +0x38
    struct.pack_into("<I", dec, spawn_offset + 0x44, 0xFFFFFFFF)  # +0x44
    struct.pack_into("<Q", dec, spawn_offset + 0x48, 0)  # +0x48

    # All offsets after spawn_offset are now 72 bytes later in the buffer.
    # The entry slots are in the item-entries section (past the state array).
    # Recalculate the entry offset and find a free entry there.
    ec_offset = _entry_count_offset(dec)
    entry_base = ec_offset + 4

    # Find the first empty entry in the shifted data
    ENTRY_SLOT_COUNT = 3065
    free_entry_off = None
    for i in range(ENTRY_SLOT_COUNT):
        off = entry_base + i * 14
        ga_e = struct.unpack_from("<I", dec, off)[0]
        if ga_e == 0:
            free_entry_off = off
            break

    if free_entry_off is None:
        # Roll back the insert
        del slot.decrypted[spawn_offset : spawn_offset + 72]
        raise RuntimeError("No free item entry slots after spawn")

    # Write ItemEntry
    struct.pack_into("<3I", dec, free_entry_off, ga_handle, 1, 0)
    dec[free_entry_off + 12] = 0  # is_favorite
    dec[free_entry_off + 13] = 1  # is_new

    # Write incremented entry_count
    struct.pack_into("<I", dec, ec_offset, old_count + 1)

    # Update slot's cached offsets
    slot.entry_count_offset = ec_offset
    slot.entry_offset = entry_base

    # Register in in-memory state (abs_offset is the physical position in the expanded buffer)
    from er_save_manager.games.NR.parser import RelicState

    rs = RelicState.from_bytes(dec, spawn_offset, -1)
    slot.relic_states[ga_handle] = rs

    return ga_handle


def remove_relic(slot: NightreignSlot, ga_handle: int) -> None:
    """
    Remove a relic. Reverses the 72-byte insert made during spawn.
    Raises KeyError if ga_handle is not found.
    """
    rs = slot.relic_states.get(ga_handle)
    if rs is None:
        raise KeyError(f"Relic 0x{ga_handle:08X} not in slot")

    dec = slot.decrypted
    spawn_off = rs.abs_offset
    old_count = struct.unpack_from("<I", dec, slot.entry_count_offset)[0]

    # Zero the 80-byte relic state, then remove the 72 compensating null bytes
    # and the 8 tail bytes that were added for AES alignment.
    dec[spawn_off : spawn_off + 80] = b"\x00" * 80
    del dec[spawn_off : spawn_off + 72]
    tail_pos = len(dec) - 28
    del dec[tail_pos : tail_pos + 8]

    # Zero the ItemEntry (its offset has shifted back by 72 bytes)
    ec_offset = _entry_count_offset(dec)
    entry_base = ec_offset + 4
    ENTRY_SLOT_COUNT = 3065
    for i in range(ENTRY_SLOT_COUNT):
        off = entry_base + i * 14
        ga_e = struct.unpack_from("<I", dec, off)[0]
        if ga_e == ga_handle:
            dec[off : off + 14] = b"\x00" * 14
            break

    # Decrement entry_count
    if old_count > 0:
        struct.pack_into("<I", dec, ec_offset, old_count - 1)

    slot.entry_count_offset = ec_offset
    slot.entry_offset = entry_base

    del slot.relic_states[ga_handle]
    slot.relics.pop(ga_handle, None)
