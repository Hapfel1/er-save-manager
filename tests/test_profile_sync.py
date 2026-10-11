"""Load screen profile (CSProfileSummary entry) kept in step with the slot."""

import struct

from er_save_manager.parser import Save
from er_save_manager.parser.profile_sync import PROFILE_SIZE, profile_from_slot
from er_save_manager.transfer.character_ops import CharacterOperations

_LEVEL = 0x22
_SECONDS = 0x26
_PLACE_NAME = 0x32


def _profile(save, idx):
    _, base = CharacterOperations.get_profile_summary_offsets(save)
    start = base + idx * PROFILE_SIZE
    return bytes(save._raw_data[start : start + PROFILE_SIZE])


def _active_slots(save):
    return [i for i, slot in enumerate(save.character_slots) if not slot.is_empty()]


def test_rebuild_keeps_fields_the_slot_does_not_hold(sanitized_save):
    for idx in _active_slots(sanitized_save):
        profile = _profile(sanitized_save, idx)
        rebuilt = profile_from_slot(
            sanitized_save._raw_data, sanitized_save.character_slots[idx], profile
        )
        assert len(rebuilt) == PROFILE_SIZE
        assert (
            rebuilt[_PLACE_NAME : _PLACE_NAME + 4]
            == profile[_PLACE_NAME : _PLACE_NAME + 4]
        )
        slot = sanitized_save.character_slots[idx]
        assert (
            struct.unpack_from("<I", rebuilt, _LEVEL)[0] == slot.player_game_data.level
        )
        assert (
            struct.unpack_from("<I", rebuilt, _SECONDS)[0] == slot.play_time_ms // 1000
        )


def test_write_syncs_only_edited_slots(sanitized_save, tmp_path):
    slots = _active_slots(sanitized_save)
    edited, others = slots[0], slots[1:]
    before = {i: _profile(sanitized_save, i) for i in others}

    slot = sanitized_save.character_slots[edited]
    level_offset = slot.player_game_data_offset + 0x60
    struct.pack_into("<I", sanitized_save._raw_data, level_offset, 321)

    out = tmp_path / "ER0000.co2"
    sanitized_save.to_file(str(out))
    written = Save.from_file(str(out))

    assert struct.unpack_from("<I", _profile(written, edited), _LEVEL)[0] == 321
    assert written.user_data_10_parsed.profile_summary.profiles[edited].level == 321
    for i in others:
        assert _profile(written, i) == before[i]
