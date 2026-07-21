"""
Tests for er_save_manager.parser.slot_rebuild.rebuild_slot.

rebuild_slot re-serializes an entire character slot from the parsed
UserDataX structure, and is used as a full-slot rewrite path by
TeleportFix, the inventory_ops gaitem-insert fallback, and
structural_scan. It must reproduce the original slot bytes exactly for
an unmodified slot - any drift here is silent save corruption for every
caller.

Regression coverage for two real bugs found via round-trip testing
against a real save (see git history for slot_rebuild.py /
user_data_x.py): a 2-byte gap after PlayerCoordinates that was read and
discarded instead of captured (game_man_0x5be/game_man_0x5bf), and a
~400KB trailing region after PlayerGameDataHash that was assumed to be
always-safe-to-zero padding but is real character data on most real
saves (already correctly captured into slot.rest on read; rebuild just
never wrote it back).
"""

from __future__ import annotations

from er_save_manager.parser.slot_rebuild import rebuild_slot

SLOT_SIZE = 0x280000


def _active_slots(save):
    return [i for i, slot in enumerate(save.character_slots) if not slot.is_empty()]


def test_rebuild_slot_is_byte_identical_for_unmodified_slots(sanitized_save):
    """The core regression test: every active slot in a real save must
    round-trip through rebuild_slot with zero byte drift.
    """
    for i in _active_slots(sanitized_save):
        slot = sanitized_save.character_slots[i]
        original = bytes(
            sanitized_save._raw_data[slot.data_start : slot.data_start + SLOT_SIZE]
        )
        rebuilt = rebuild_slot(slot)
        assert rebuilt == original, f"slot {i} did not round-trip byte-identical"


def test_rebuild_slot_output_is_exactly_slot_size(sanitized_save):
    for i in _active_slots(sanitized_save):
        slot = sanitized_save.character_slots[i]
        assert len(rebuild_slot(slot)) == SLOT_SIZE


def test_padding_after_player_coordinates_is_preserved(sanitized_save):
    """Regression test for the specific game_man_0x5be/0x5bf bug: these
    two bytes must be captured on read and written back verbatim, not
    hardcoded to zero.
    """
    i = _active_slots(sanitized_save)[0]
    slot = sanitized_save.character_slots[i]

    # Force a nonzero value to prove it survives the round trip, rather
    # than relying on this particular fixture slot happening to have a
    # nonzero value here.
    slot.game_man_0x5be = 0xAB
    slot.game_man_0x5bf = 0xCD

    rebuilt = rebuild_slot(slot)

    # Recompute this section's absolute position the same way
    # rebuild_slot does: everything up to and including
    # player_coordinates, before this 2-byte gap.
    from er_save_manager.parser.slot_rebuild import rebuild_slot_with_map

    _, sections = rebuild_slot_with_map(slot)
    section = next(
        s for s in sections if s["name"] == "padding_after_player_coordinates"
    )

    assert rebuilt[section["start"] : section["end"]] == bytes([0xAB, 0xCD])


def test_rest_bytes_are_preserved(sanitized_save):
    """Regression test for the trailing-region bug: slot.rest must be
    written back verbatim, not replaced with zero padding.
    """
    i = _active_slots(sanitized_save)[0]
    slot = sanitized_save.character_slots[i]

    original_rest = bytes(slot.rest)
    rebuilt = rebuild_slot(slot)

    assert rebuilt[SLOT_SIZE - len(original_rest) :] == original_rest


def test_rest_survives_even_when_all_zero(sanitized_save):
    """An empty/all-zero slot.rest must still produce a full slot_size
    output (padded), not a short buffer.
    """
    i = _active_slots(sanitized_save)[0]
    slot = sanitized_save.character_slots[i]
    slot.rest = b""

    rebuilt = rebuild_slot(slot)

    assert len(rebuilt) == SLOT_SIZE
    assert rebuilt[SLOT_SIZE - 10 :] == b"\x00" * 10
