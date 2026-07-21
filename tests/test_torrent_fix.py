"""Tests for er_save_manager.fixes.torrent.TorrentFix."""

from __future__ import annotations

from io import BytesIO

from er_save_manager.fixes.torrent import TorrentFix
from er_save_manager.parser.world import HorseState


def _first_active_slot(save):
    for i, slot in enumerate(save.character_slots):
        if not slot.is_empty():
            return i
    raise AssertionError("fixture save has no active character slots")


def test_no_false_positive_on_healthy_save(sanitized_save):
    fix = TorrentFix()
    for i, slot in enumerate(sanitized_save.character_slots):
        if slot.is_empty():
            continue
        assert fix.detect(sanitized_save, i) is False, f"slot {i} unexpectedly flagged"


def test_apply_is_no_op_when_bug_not_present(sanitized_save):
    i = _first_active_slot(sanitized_save)
    fix = TorrentFix()
    result = fix.apply(sanitized_save, i)
    assert result.applied is False


def test_detects_and_fixes_hp_zero_active_state(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    slot.horse.hp = 0
    slot.horse.state = HorseState.ACTIVE
    _write_horse(sanitized_save, slot)

    fix = TorrentFix()
    assert fix.detect(sanitized_save, i) is True

    result = fix.apply(sanitized_save, i)
    assert result.applied is True
    assert slot.horse.state == HorseState.DEAD
    assert fix.detect(sanitized_save, i) is False


def test_fix_preserves_horse_position_and_hp(sanitized_save):
    """Only state should change; coordinates, map_id, and hp must survive
    the fix untouched.
    """
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    slot.horse.hp = 0
    slot.horse.state = HorseState.ACTIVE
    original_coords = (
        slot.horse.coordinates.x,
        slot.horse.coordinates.y,
        slot.horse.coordinates.z,
    )
    _write_horse(sanitized_save, slot)

    TorrentFix().apply(sanitized_save, i)

    assert slot.horse.hp == 0
    assert (
        slot.horse.coordinates.x,
        slot.horse.coordinates.y,
        slot.horse.coordinates.z,
    ) == original_coords


def test_hp_zero_with_dead_state_is_not_a_bug(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    slot.horse.hp = 0
    slot.horse.state = HorseState.DEAD
    _write_horse(sanitized_save, slot)

    assert TorrentFix().detect(sanitized_save, i) is False


def test_nonzero_hp_with_active_state_is_not_a_bug(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    slot.horse.hp = 100
    slot.horse.state = HorseState.ACTIVE
    _write_horse(sanitized_save, slot)

    assert TorrentFix().detect(sanitized_save, i) is False


def _write_horse(save, slot) -> None:
    """Mirror what TorrentFix.apply does to persist an in-memory horse
    edit into raw_data, so detect() (which reads from the parsed object,
    not raw_data) sees a consistent state either way.
    """
    buf = BytesIO()
    slot.horse.write(buf)
    data = buf.getvalue()
    save._raw_data[slot.horse_offset : slot.horse_offset + len(data)] = data
