"""
Relic spawn and removal operations for Nightreign save slots.

Spawn algorithm
---------------
The slot's state section is consumed by a fixed 5120-state loop. Each state
occupies a variable number of bytes (8 for empty/goods, 16 for armor, 80 for
relic, 88 for weapon). The loop reads exactly 5120 states; everything after
the loop (player name, currencies, item entries) sits at a fixed position
relative to the loop's final cursor.

Turning one 8-byte empty state into an 80-byte relic state keeps the state
count at 5120 but makes the section 72 bytes longer, so everything after it
(player data, item entries, acquisition counter, loadout chunk) moves 72 bytes
later. The decrypted entry has a fixed size, so the same 72 bytes are taken
from the unused slack at the end of the slot.

Every item's handle carries its state index in the low 16 bits and a
generation byte in bits 16-23 (0x80-0xFF ring). The game allocates indices
upward from the last one it used and wraps to 0 with the generation + 1,
skipping used indices, so the newest generation's highest index is the
cursor.

Concretely:
  1. Take the first empty state after the cursor (wrapping to 0 with the next
     generation); the handle is the relic type, generation and that index.
  2. Insert 72 null bytes at that offset and trim 72 bytes of trailing slack
     before the checksum tail, so the entry keeps its fixed size.
  3. Write the 80-byte relic block at that offset (overwriting the 72 nulls +
     the original 8-byte slot = 80 bytes total).
  4. Write the ItemEntry into the first free entry (now 72 bytes later).
  5. Increment entry_count and advance the acquisition counter.
  6. Re-parse the slot so every cached offset reflects the shift.

Removal is the inverse: clear the relic from vessels and presets, collapse the
80-byte state back to an empty 8-byte one, return 72 bytes to the slack,
clear the ItemEntry and decrement entry_count.
"""

from __future__ import annotations

import struct
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from er_save_manager.games.NR.parser import _ACQ_COUNTER_REL, ENTRY_SLOT_COUNT

if TYPE_CHECKING:
    from er_save_manager.games.NR.parser import NightreignSlot, RelicState

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


_CHECKSUM_TAIL = 28  # MD5(16) + padding(12) at the end of each decrypted entry


def _trim_slack(dec: bytearray, n: int) -> None:
    """Remove n bytes of unused slack directly before the checksum tail.

    The serialized slot payload is followed by unused filler (zeros or stale
    bytes) up to the fixed entry size. Its start moves with the state array
    while the payload length after the state array stays constant, so the
    filler absorbs growth of the variable-size state array.
    """
    tail_pos = len(dec) - _CHECKSUM_TAIL
    del dec[tail_pos - n : tail_pos]


def _restore_slack(dec: bytearray, n: int) -> None:
    """Re-insert n zero bytes of slack directly before the checksum tail."""
    tail_pos = len(dec) - _CHECKSUM_TAIL
    dec[tail_pos:tail_pos] = b"\x00" * n


def _reparse(slot: NightreignSlot) -> None:
    """Re-derive every cached offset after the state array shifted.

    item_states, relic_states, item_entries and the loadout offsets all move
    by the inserted/removed bytes; stale item_states would place a second
    spawn inside the previous relic's 80-byte block.
    """
    from er_save_manager.games.NR.parser import _parse_slot

    fresh = _parse_slot(slot.decrypted, slot.slot_index)
    slot.__dict__.update(fresh.__dict__)


@contextmanager
def rollback_on_error(slot: NightreignSlot) -> Iterator[None]:
    """Restore the slot's bytes and parse when the body raises, so a failed
    operation leaves no partial change in memory."""
    snapshot = bytes(slot.decrypted)
    try:
        yield
    except BaseException:
        slot.decrypted[:] = snapshot
        _reparse(slot)
        raise


def _u32_problem(value, field: str) -> str | None:
    """Message naming field unless value is an int in 0..0xFFFFFFFF."""
    if isinstance(value, bool) or not isinstance(value, int):
        return f"{field} must be a whole number, not {value!r}."
    if not 0 <= value <= 0xFFFFFFFF:
        return f"{field} {value} is outside 0 to 4294967295."
    return None


def ids_problem(real_item_id, effects: list, curses: list) -> str | None:
    """First relic id, effect or curse value that cannot be stored."""
    for value, field in (
        (real_item_id, "Relic ID"),
        *((e, f"Effect {i}") for i, e in enumerate(effects, 1)),
        *((c, f"Curse {i}") for i, c in enumerate(curses, 1)),
    ):
        problem = _u32_problem(value, field)
        if problem:
            return problem
    if real_item_id > 0x00FFFFFF:
        return f"Relic ID {real_item_id} is outside 0 to {0x00FFFFFF}."
    return None


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


def _next_acquisition_id(slot: NightreignSlot) -> int:
    """Next acquisition_id: the stored counter, or past the highest in use."""
    scanned = max(
        (
            e.acquisition_id
            for e in slot.item_entries
            if not e.is_empty and e.acquisition_id < 0x7FFFFFFF
        ),
        default=0,
    )
    return max(slot.next_acquisition_id, scanned + 1)


def _allocate_state(slot: NightreignSlot) -> tuple[int, int] | None:
    """(absolute offset, ga_handle) of the state the game would use next for
    a relic, or None when every state is in use."""
    used = [(i, ga) for i, (ga, _size, _off) in enumerate(slot.item_states) if ga]
    if used:
        generation = max((ga >> 16) & 0xFF for _i, ga in used)
        cursor = max(i for i, ga in used if (ga >> 16) & 0xFF == generation)
    else:
        generation, cursor = 0x80, -1
    next_generation = generation + 1 if generation < 0xFF else 0x80
    order = [(i, generation) for i in range(cursor + 1, len(slot.item_states))]
    order += [(i, next_generation) for i in range(cursor + 1)]
    for i, gen in order:
        ga, _size, off = slot.item_states[i]
        if ga == 0:
            return off, ITEM_TYPE_RELIC | (gen << 16) | i
    return None


def validate_relic(real_item_id: int, effects: list[int], curses: list[int]) -> None:
    """Raise ValueError unless the game can roll this relic (relic_rules.check).

    No duplicate check across relics: game-written saves hold many relics
    sharing one real_item_id.
    """
    from er_save_manager.games.NR.relic_rules import check

    issues = check(real_item_id, effects, curses)
    if issues:
        raise ValueError(" ".join(i.message for i in issues))


def prepare_relic(
    real_item_id: int, effects: list[int], curses: list[int]
) -> tuple[list[int], list[int]]:
    """Effects and curses as the game stores them. A fixed relic given no
    effects gets its fixed ones."""
    from er_save_manager.games.NR.relic_rules import canonical, fixed_effects

    if all(e == 0xFFFFFFFF for e in effects):
        effects = fixed_effects(real_item_id) or effects
    return canonical(effects, curses)


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
    Raises ValueError on IDs that do not fit their fields, and on IDs the
    game cannot roll when validate=True.
    Raises RuntimeError if there is no free space.
    The slot is unchanged when it raises.
    """
    problem = ids_problem(
        real_item_id, [effect_1, effect_2, effect_3], [curse_1, curse_2, curse_3]
    )
    if problem:
        raise ValueError(problem)
    (effect_1, effect_2, effect_3), (curse_1, curse_2, curse_3) = prepare_relic(
        real_item_id,
        [effect_1, effect_2, effect_3],
        [curse_1, curse_2, curse_3],
    )
    if validate:
        validate_relic(
            real_item_id,
            [effect_1, effect_2, effect_3],
            [curse_1, curse_2, curse_3],
        )
    with rollback_on_error(slot):
        return _spawn(
            slot,
            real_item_id,
            [effect_1, effect_2, effect_3],
            [curse_1, curse_2, curse_3],
        )


def _spawn(
    slot: NightreignSlot, real_item_id: int, effects: list[int], curses: list[int]
) -> int:
    effect_1, effect_2, effect_3 = effects
    curse_1, curse_2, curse_3 = curses
    allocated = _allocate_state(slot)
    if allocated is None:
        raise RuntimeError("No free state slot: all 5120 item states are in use")
    spawn_offset, ga_handle = allocated

    free_entries = [e for e in slot.item_entries if e.is_empty]
    if not free_entries:
        raise RuntimeError("No free item entry slots")

    # Read entry_count before expanding the buffer
    old_count = struct.unpack_from("<I", slot.decrypted, slot.entry_count_offset)[0]
    acq_id = _next_acquisition_id(slot)
    item_id = 0x80000000 | (real_item_id & 0x00FFFFFF)

    # Insert 72 null bytes at spawn_offset to compensate for the state-loop delta,
    # then trim the same amount from the slot's trailing slack so the entry keeps
    # its fixed size (the BND4 header size and downstream offsets are not updated).
    slot.decrypted[spawn_offset:spawn_offset] = b"\x00" * 72
    _trim_slack(slot.decrypted, 72)

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
        _restore_slack(slot.decrypted, 72)
        raise RuntimeError("No free item entry slots after spawn")

    struct.pack_into("<3I", dec, free_entry_off, ga_handle, 1, acq_id)
    dec[free_entry_off + 12] = 0  # is_favorite
    dec[free_entry_off + 13] = 1  # is_new

    # Write incremented entry_count and advance the acquisition counter
    struct.pack_into("<I", dec, ec_offset, old_count + 1)
    acq_counter_off = entry_base + ENTRY_SLOT_COUNT * 14 + _ACQ_COUNTER_REL
    struct.pack_into("<I", dec, acq_counter_off, acq_id + 1)

    _reparse(slot)
    return ga_handle


def remove_relic(slot: NightreignSlot, ga_handle: int) -> int:
    """
    Remove a relic. Reverses the 72-byte insert made during spawn.
    Returns the number of vessel/preset slots the relic was cleared from.
    Raises KeyError if ga_handle is not found.
    """
    rs = slot.relic_states.get(ga_handle)
    if rs is None:
        raise KeyError(f"Relic 0x{ga_handle:08X} not in slot")

    dec = slot.decrypted
    # Loadout offsets lie past the state array, so clear references before
    # the removal shifts them.
    cleared = clear_loadout_refs(slot, ga_handle)
    spawn_off = rs.abs_offset
    old_count = struct.unpack_from("<I", dec, slot.entry_count_offset)[0]

    # Zero the 80-byte relic state, remove the 72 compensating null bytes, and
    # return them to the trailing slack so the entry size is unchanged.
    dec[spawn_off : spawn_off + 80] = b"\x00" * 80
    del dec[spawn_off : spawn_off + 72]
    _restore_slack(dec, 72)
    # Empty 8-byte states carry item_id 0xFFFFFFFF, not 0
    struct.pack_into("<I", dec, spawn_off + 4, 0xFFFFFFFF)

    # Zero the ItemEntry (its offset has shifted back by 72 bytes)
    ec_offset = _entry_count_offset(dec)
    entry_base = ec_offset + 4
    for i in range(ENTRY_SLOT_COUNT):
        off = entry_base + i * 14
        ga_e = struct.unpack_from("<I", dec, off)[0]
        if ga_e == ga_handle:
            dec[off : off + 14] = b"\x00" * 14
            break

    if old_count > 0:
        struct.pack_into("<I", dec, ec_offset, old_count - 1)

    _reparse(slot)
    return cleared


def clear_loadout_refs(slot: NightreignSlot, ga_handle: int) -> int:
    """Set every vessel and preset relic slot holding ga_handle to empty (0).

    Returns the number of slots cleared.
    """
    cleared = 0
    for v in slot.all_vessels():
        if ga_handle in v.relics:
            cleared += v.relics.count(ga_handle)
            v.relics = [0 if r == ga_handle else r for r in v.relics]
            v.write_to(slot.decrypted)
    for p in slot.all_presets():
        if ga_handle in p.relics:
            cleared += p.relics.count(ga_handle)
            p.relics = [0 if r == ga_handle else r for r in p.relics]
            struct.pack_into("<6I", slot.decrypted, p.abs_offset + 48, *p.relics)
    return cleared


# ---------------------------------------------------------------------------
# Bulk import/export
# ---------------------------------------------------------------------------


def relic_to_dict(rs: RelicState) -> dict:
    """Serializable form of a relic, as used by export/import."""
    from er_save_manager.games.NR.item_db import relic_name

    return {
        "id": rs.real_item_id,
        "name": relic_name(rs.real_item_id),
        "effects": [rs.effect_1, rs.effect_2, rs.effect_3],
        "curses": [rs.curse_1, rs.curse_2, rs.curse_3],
    }


_ImportRelic = tuple[int, list[int], list[int]]


def _id_list(row: dict, key: str, field: str) -> list:
    values = row.get(key, [])
    if not isinstance(values, list):
        raise ValueError(f"{key} must be a list, not {values!r}.")
    if len(values) > 3:
        raise ValueError(f"{key} holds {len(values)} entries, at most 3 fit.")
    for i, value in enumerate(values, 1):
        problem = _u32_problem(value, f"{field} {i}")
        if problem:
            raise ValueError(problem)
    return values + [0xFFFFFFFF] * (3 - len(values))


def _row_to_args(row) -> _ImportRelic:
    """(relic id, effects, curses) of an import row; ValueError naming the
    field when a value is missing or cannot be stored."""
    if not isinstance(row, dict):
        raise ValueError(f"expected an object with an id, not {row!r}.")
    if "id" not in row:
        raise ValueError("no relic id.")
    effects = _id_list(row, "effects", "Effect")
    curses = _id_list(row, "curses", "Curse")
    problem = ids_problem(row["id"], effects, curses)
    if problem:
        raise ValueError(problem)
    return row["id"], effects, curses


def sort_import_rows(rows: list) -> tuple[list[_ImportRelic], list[str], list[str]]:
    """(relics to spawn, skipped rows, warnings), one message per problem.

    A row is skipped when a value does not fit its field, the relic id is
    unknown or the game cannot roll the relic. Unknown effects (mod data)
    and pool issues an older game version can cause only warn, since
    exported relics come from a save.
    """
    from er_save_manager.games.NR.relic_rules import (
        VERSION_SENSITIVE,
        check,
        relic_kind,
    )

    relics, skipped, warnings = [], [], []
    for i, row in enumerate(rows, 1):
        try:
            real_id, effects, curses = _row_to_args(row)
        except ValueError as e:
            skipped.append(f"Row {i}: {e}")
            continue
        if relic_kind(real_id) == "unknown":
            skipped.append(f"Row {i}: Unknown relic ID {real_id}.")
            continue
        effects, curses = prepare_relic(real_id, effects, curses)
        issues = check(real_id, effects, curses)
        # With a known relic id, "unknown" means an effect missing from the
        # game data
        hard = [
            issue
            for issue in issues
            if issue.code != "unknown" and issue.code not in VERSION_SENSITIVE
        ]
        if hard:
            skipped.append(f"Row {i}: " + " ".join(x.message for x in hard))
            continue
        warnings.extend(f"Row {i}: {issue.message}" for issue in issues)
        relics.append((real_id, effects, curses))
    return relics, skipped, warnings


def import_relics(slot: NightreignSlot, relics: list[_ImportRelic]) -> list[int]:
    """Spawn relics from sort_import_rows. Returns the new ga_handles.

    Nothing is spawned if the slot lacks room for all of them or a spawn
    fails, so a failure never leaves a partial import behind.
    """
    free_states = _count_spawnable_states(slot)
    free_entries = sum(1 for e in slot.item_entries if e.is_empty)
    if len(relics) > min(free_states, free_entries):
        raise RuntimeError(
            f"Not enough room: {len(relics)} relics requested, "
            f"{min(free_states, free_entries)} free"
        )

    handles = []
    with rollback_on_error(slot):
        for real_id, effects, curses in relics:
            handles.append(
                spawn_relic(slot, real_id, *effects, *curses, validate=False)
            )
    return handles


def _count_spawnable_states(slot: NightreignSlot) -> int:
    """Empty states, where spawns are placed."""
    return sum(1 for ga, _size, _off in slot.item_states if ga == 0)
