"""rebuild_slot re-serializes a whole character slot from the parsed
UserDataX and must reproduce an unmodified slot exactly."""

from __future__ import annotations

from er_save_manager.parser.slot_rebuild import rebuild_slot, rebuild_slot_with_map

SLOT_SIZE = 0x280000


def test_rebuild_slot_is_byte_identical_for_unmodified_slots(sanitized_save_readonly):
    save = sanitized_save_readonly
    for i, slot in enumerate(save.character_slots):
        original = bytes(save._raw_data[slot.data_start : slot.data_start + SLOT_SIZE])
        assert rebuild_slot(slot) == original, f"slot {i}"


def test_padding_after_player_coordinates_is_written_back(sanitized_save):
    """game_man_0x5be/0x5bf are read and written back, not zeroed."""
    slot = sanitized_save.character_slots[0]
    slot.game_man_0x5be, slot.game_man_0x5bf = 0xAB, 0xCD
    rebuilt, sections = rebuild_slot_with_map(slot)
    s = next(s for s in sections if s["name"] == "padding_after_player_coordinates")
    assert rebuilt[s["start"] : s["end"]] == bytes([0xAB, 0xCD])


def test_empty_rest_is_padded_to_slot_size(sanitized_save):
    slot = sanitized_save.character_slots[0]
    slot.rest = b""
    rebuilt = rebuild_slot(slot)
    assert len(rebuilt) == SLOT_SIZE
    assert rebuilt[-10:] == bytes(10)
