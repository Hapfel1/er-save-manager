"""Tests for er_save_manager.fixes.torrent.TorrentFix."""

from __future__ import annotations

from io import BytesIO

from er_save_manager.fixes.torrent import TorrentFix
from er_save_manager.parser.world import HorseState


def _set_horse(save, hp, state):
    slot = save.character_slots[0]
    slot.horse.hp, slot.horse.state = hp, state
    buf = BytesIO()
    slot.horse.write(buf)
    data = buf.getvalue()
    save._raw_data[slot.horse_offset : slot.horse_offset + len(data)] = data
    return slot.horse


def test_hp_zero_active_state_is_set_dead_and_rest_kept(sanitized_save):
    horse = _set_horse(sanitized_save, 0, HorseState.ACTIVE)
    coords = (horse.coordinates.x, horse.coordinates.y, horse.coordinates.z)
    fix = TorrentFix()
    assert fix.detect(sanitized_save, 0) is True
    assert fix.apply(sanitized_save, 0).applied is True
    assert horse.state == HorseState.DEAD and horse.hp == 0
    assert (horse.coordinates.x, horse.coordinates.y, horse.coordinates.z) == coords
    assert fix.detect(sanitized_save, 0) is False


def test_consistent_states_are_not_flagged(sanitized_save):
    for hp, state in ((0, HorseState.DEAD), (100, HorseState.ACTIVE)):
        _set_horse(sanitized_save, hp, state)
        assert TorrentFix().detect(sanitized_save, 0) is False
