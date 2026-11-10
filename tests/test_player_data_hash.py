import struct

from er_save_manager.parser.player_data_hash import _FIELDS, compute


def test_compute_matches_game_written_hashes(sanitized_save):
    raw = bytes(sanitized_save._raw_data)
    slots = [s for s in sanitized_save.character_slots if s and not s.is_empty()]
    for index, slot in enumerate(slots):
        stored = struct.unpack_from("<11I", raw, slot.player_data_hash_offset)
        values = compute(raw, slot)
        assert values["equipped_items"] == stored[9]
        if index == 0:
            for entry, attr in _FIELDS.items():
                assert values[attr] == stored[entry], attr
