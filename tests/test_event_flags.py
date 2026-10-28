"""Tests for er_save_manager.parser.event_flags and fixes.event_flags."""

from __future__ import annotations

import pytest

from er_save_manager.fixes.event_flags import EventFlagsFix, RanniSoftlockFix
from er_save_manager.parser.event_flags import (
    CorruptionDetector,
    CorruptionFixer,
    EventFlags,
    FixFlags,
)

RANNI = FixFlags.RANNI_BLOCKING_FLAG


def _get(ef, flag_id):
    return EventFlags.get_flag(bytes(ef), flag_id)


def _with(save, **flags) -> bytearray:
    """Slot 0's event flags with the named FixFlags set, written to raw data."""
    slot = save.character_slots[0]
    ef = bytearray(slot.event_flags)
    for name, value in flags.items():
        EventFlags.set_flag(ef, getattr(FixFlags, name), value)
    slot.event_flags = bytes(ef)
    save._raw_data[slot.event_flags_offset : slot.event_flags_offset + len(ef)] = ef
    return ef


def test_flag_bits():
    ef = bytearray(EventFlags.EVENT_FLAGS_SIZE)
    assert _get(ef, RANNI) is False
    settable = []
    for flag_id in FixFlags.RANNI_FLAGS_TO_ENABLE:
        try:
            EventFlags.set_flag(ef, flag_id, True)
            settable.append(flag_id)
        except ValueError:
            continue
    assert settable
    EventFlags.set_flag(ef, RANNI, True)
    assert _get(ef, RANNI) is True
    EventFlags.set_flag(ef, RANNI, False)
    assert _get(ef, RANNI) is False
    # Neighbouring bits are untouched
    assert all(_get(ef, f) for f in settable)


def test_flag_arguments_are_checked():
    with pytest.raises(ValueError):
        EventFlags.get_flag(bytes(10), RANNI)
    with pytest.raises(TypeError):
        EventFlags.set_flag(bytes(EventFlags.EVENT_FLAGS_SIZE), RANNI, True)
    with pytest.raises(ValueError):
        EventFlags.get_flag(bytes(EventFlags.EVENT_FLAGS_SIZE), 999_999_999_999)


def test_detectors(sanitized_save):
    ef = _with(sanitized_save, RANNI_BLOCKING_FLAG=True)
    assert CorruptionDetector.check_ranni_softlock(bytes(ef)) is True

    ef = _with(sanitized_save, METEORITE_GREEN=True, DEFEATED_RADAHN=False)
    assert CorruptionDetector.check_radahn_alive_warp(bytes(ef)) is True
    ef = _with(
        sanitized_save,
        DEFEATED_RADAHN=True,
        GRACE_RADAHN=False,
        GRACE_WAR_DEAD_CATACOMBS=False,
    )
    assert CorruptionDetector.check_radahn_dead_warp(bytes(ef)) is True

    ef = _with(
        sanitized_save,
        MORGOTT_DEFEATED=True,
        MORGOTT_THORNS_TOUCHED=False,
        MORGOTT_FOG_WALL=False,
    )
    assert CorruptionDetector.check_morgott_warp(bytes(ef)) is True
    ef = _with(sanitized_save, MORGOTT_THORNS_TOUCHED=True, MORGOTT_FOG_WALL=True)
    assert CorruptionDetector.check_morgott_warp(bytes(ef)) is False


def test_fixers(sanitized_save):
    ef = _with(sanitized_save, RANNI_BLOCKING_FLAG=True, RADAHN_MAP_MARKER=True)
    EventFlags.set_flag(ef, FixFlags.METEORITE_GREEN, True)
    EventFlags.set_flag(ef, FixFlags.DEFEATED_RADAHN, False)
    issues = CorruptionDetector.detect_all(bytes(ef))
    assert set(issues) == {"ranni_softlock", "radahn_alive_warp"}

    assert CorruptionFixer.fix_all(ef, issues)[0] == 2
    assert CorruptionDetector.detect_all(bytes(ef)) == []
    assert _get(ef, RANNI) is False
    assert _get(ef, FixFlags.RADAHN_MAP_MARKER) is False
    # Listed flags absent from this BST are skipped by fix_ranni_softlock
    stored = [
        f
        for f in FixFlags.RANNI_FLAGS_TO_ENABLE
        if f // EventFlags.FLAG_DIVISOR in EventFlags._load_bst_map()
    ]
    assert stored and all(_get(ef, f) for f in stored)


def test_fix_wrappers_persist_to_raw_data(sanitized_save):
    for fix_cls in (EventFlagsFix, RanniSoftlockFix):
        assert fix_cls().apply(sanitized_save, 0).applied is False
        _with(sanitized_save, RANNI_BLOCKING_FLAG=True)
        fix = fix_cls()
        assert fix.detect(sanitized_save, 0) is True
        assert fix.apply(sanitized_save, 0).applied is True
        assert fix.detect(sanitized_save, 0) is False
        slot = sanitized_save.character_slots[0]
        start = slot.event_flags_offset
        raw = sanitized_save._raw_data[start : start + EventFlags.EVENT_FLAGS_SIZE]
        assert _get(raw, RANNI) is False
