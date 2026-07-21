"""
Tests for er_save_manager.parser.event_flags and fixes.event_flags.
"""

from __future__ import annotations

from er_save_manager.fixes.event_flags import EventFlagsFix, RanniSoftlockFix
from er_save_manager.parser.event_flags import (
    CorruptionDetector,
    CorruptionFixer,
    EventFlags,
    FixFlags,
)


def _first_active_slot(save):
    for i, slot in enumerate(save.character_slots):
        if not slot.is_empty():
            return i
    raise AssertionError("fixture save has no active character slots")


def _write_event_flags(save, slot) -> None:
    save._raw_data[
        slot.event_flags_offset : slot.event_flags_offset + len(slot.event_flags)
    ] = slot.event_flags


def _flag_exists_in_bst(event_id: int) -> bool:
    block = event_id // EventFlags.FLAG_DIVISOR
    return block in EventFlags._load_bst_map()


# ---------------------------------------------------------------------------
# EventFlags - pure bit math, no save needed
# ---------------------------------------------------------------------------


def test_get_flag_defaults_to_false_on_empty_buffer():
    ef = bytes(EventFlags.EVENT_FLAGS_SIZE)
    assert EventFlags.get_flag(ef, FixFlags.RANNI_BLOCKING_FLAG) is False


def test_set_flag_true_then_false_round_trips():
    ef = bytearray(EventFlags.EVENT_FLAGS_SIZE)
    EventFlags.set_flag(ef, FixFlags.RANNI_BLOCKING_FLAG, True)
    assert EventFlags.get_flag(bytes(ef), FixFlags.RANNI_BLOCKING_FLAG) is True

    EventFlags.set_flag(ef, FixFlags.RANNI_BLOCKING_FLAG, False)
    assert EventFlags.get_flag(bytes(ef), FixFlags.RANNI_BLOCKING_FLAG) is False


def test_set_flag_does_not_affect_neighboring_flags():
    """Setting one flag must only touch its own bit, not neighboring
    bits in the same byte or block.
    """
    ef = bytearray(EventFlags.EVENT_FLAGS_SIZE)
    settable_flags = []
    for flag_id in FixFlags.RANNI_FLAGS_TO_ENABLE:
        try:
            EventFlags.set_flag(ef, flag_id, True)
            settable_flags.append(flag_id)
        except ValueError:
            continue
    assert settable_flags  # sanity: at least some flags in this BST

    EventFlags.set_flag(ef, FixFlags.RANNI_BLOCKING_FLAG, True)

    for flag_id in settable_flags:
        assert EventFlags.get_flag(bytes(ef), flag_id) is True
    assert EventFlags.get_flag(bytes(ef), FixFlags.RANNI_BLOCKING_FLAG) is True


def test_get_flag_rejects_wrong_size_buffer():
    import pytest

    with pytest.raises(ValueError):
        EventFlags.get_flag(b"\x00" * 10, FixFlags.RANNI_BLOCKING_FLAG)


def test_set_flag_requires_bytearray():
    import pytest

    with pytest.raises(TypeError):
        EventFlags.set_flag(
            bytes(EventFlags.EVENT_FLAGS_SIZE), FixFlags.RANNI_BLOCKING_FLAG, True
        )


def test_unknown_block_raises():
    import pytest

    ef = bytes(EventFlags.EVENT_FLAGS_SIZE)
    # A deliberately absurd event ID whose block is very unlikely to be
    # a real quest block in the BST map.
    with pytest.raises(ValueError):
        EventFlags.get_flag(ef, 999_999_999_999)


# ---------------------------------------------------------------------------
# CorruptionDetector - no false positives on a real, healthy save
# ---------------------------------------------------------------------------


def test_no_false_positive_on_healthy_save(sanitized_save):
    for i, slot in enumerate(sanitized_save.character_slots):
        if slot.is_empty():
            continue
        issues = CorruptionDetector.detect_all(slot.event_flags)
        assert issues == [], f"slot {i} unexpectedly flagged: {issues}"


def test_detects_ranni_softlock_when_blocking_flag_set(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    ef = bytearray(slot.event_flags)

    EventFlags.set_flag(ef, FixFlags.RANNI_BLOCKING_FLAG, True)
    slot.event_flags = bytes(ef)

    assert CorruptionDetector.check_ranni_softlock(slot.event_flags) is True
    assert "ranni_softlock" in CorruptionDetector.detect_all(slot.event_flags)


def test_detects_radahn_alive_warp(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    ef = bytearray(slot.event_flags)

    EventFlags.set_flag(ef, FixFlags.METEORITE_GREEN, True)
    EventFlags.set_flag(ef, FixFlags.DEFEATED_RADAHN, False)
    slot.event_flags = bytes(ef)

    assert CorruptionDetector.check_radahn_alive_warp(slot.event_flags) is True


def test_detects_radahn_dead_warp(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    ef = bytearray(slot.event_flags)

    EventFlags.set_flag(ef, FixFlags.METEORITE_GREEN, True)
    EventFlags.set_flag(ef, FixFlags.DEFEATED_RADAHN, True)
    EventFlags.set_flag(ef, FixFlags.GRACE_RADAHN, False)
    EventFlags.set_flag(ef, FixFlags.GRACE_WAR_DEAD_CATACOMBS, False)
    slot.event_flags = bytes(ef)

    assert CorruptionDetector.check_radahn_dead_warp(slot.event_flags) is True


def test_morgott_warp_not_triggered_once_thorns_and_fog_cleared(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    ef = bytearray(slot.event_flags)

    EventFlags.set_flag(ef, FixFlags.MORGOTT_DEFEATED, True)
    EventFlags.set_flag(ef, FixFlags.MORGOTT_THORNS_TOUCHED, False)
    EventFlags.set_flag(ef, FixFlags.MORGOTT_FOG_WALL, False)
    slot.event_flags = bytes(ef)
    assert CorruptionDetector.check_morgott_warp(slot.event_flags) is True

    EventFlags.set_flag(ef, FixFlags.MORGOTT_THORNS_TOUCHED, True)
    EventFlags.set_flag(ef, FixFlags.MORGOTT_FOG_WALL, True)
    slot.event_flags = bytes(ef)
    assert CorruptionDetector.check_morgott_warp(slot.event_flags) is False


# ---------------------------------------------------------------------------
# CorruptionFixer
# ---------------------------------------------------------------------------


def test_fix_ranni_softlock_clears_blocking_flag_and_enables_progression(
    sanitized_save,
):
    """fix_ranni_softlock silently skips any listed flag ID not present
    in this BST resource (see its own except ValueError: continue), so
    this only asserts on flags actually settable here.
    """
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    ef = bytearray(slot.event_flags)
    EventFlags.set_flag(ef, FixFlags.RANNI_BLOCKING_FLAG, True)

    assert CorruptionFixer.fix_ranni_softlock(ef) is True
    assert EventFlags.get_flag(bytes(ef), FixFlags.RANNI_BLOCKING_FLAG) is False

    settable_flags = [
        flag_id
        for flag_id in FixFlags.RANNI_FLAGS_TO_ENABLE
        if _flag_exists_in_bst(flag_id)
    ]
    assert settable_flags  # sanity: at least some flags in this BST
    for flag_id in settable_flags:
        assert EventFlags.get_flag(bytes(ef), flag_id) is True


def test_fix_radahn_alive_warp_closes_crater_and_marker(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    ef = bytearray(slot.event_flags)
    EventFlags.set_flag(ef, FixFlags.METEORITE_GREEN, True)
    EventFlags.set_flag(ef, FixFlags.RADAHN_MAP_MARKER, True)

    assert CorruptionFixer.fix_radahn_alive_warp(ef) is True
    assert EventFlags.get_flag(bytes(ef), FixFlags.METEORITE_GREEN) is False
    assert EventFlags.get_flag(bytes(ef), FixFlags.RADAHN_MAP_MARKER) is False


def test_fix_all_applies_every_detected_issue(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    ef = bytearray(slot.event_flags)
    EventFlags.set_flag(ef, FixFlags.RANNI_BLOCKING_FLAG, True)
    EventFlags.set_flag(ef, FixFlags.METEORITE_GREEN, True)
    EventFlags.set_flag(ef, FixFlags.DEFEATED_RADAHN, False)
    slot.event_flags = bytes(ef)

    issues = CorruptionDetector.detect_all(slot.event_flags)
    assert set(issues) == {"ranni_softlock", "radahn_alive_warp"}

    ef2 = bytearray(slot.event_flags)
    fixes_count, descriptions = CorruptionFixer.fix_all(ef2, issues)

    assert fixes_count == 2
    assert CorruptionDetector.detect_all(bytes(ef2)) == []


# ---------------------------------------------------------------------------
# EventFlagsFix / RanniSoftlockFix (BaseFix wrappers)
# ---------------------------------------------------------------------------


def test_event_flags_fix_no_op_on_healthy_save(sanitized_save):
    i = _first_active_slot(sanitized_save)
    result = EventFlagsFix().apply(sanitized_save, i)
    assert result.applied is False


def test_event_flags_fix_detects_and_fixes_ranni_softlock(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    ef = bytearray(slot.event_flags)
    EventFlags.set_flag(ef, FixFlags.RANNI_BLOCKING_FLAG, True)
    slot.event_flags = bytes(ef)
    _write_event_flags(sanitized_save, slot)

    fix = EventFlagsFix()
    assert fix.detect(sanitized_save, i) is True

    result = fix.apply(sanitized_save, i)
    assert result.applied is True
    assert CorruptionDetector.check_ranni_softlock(slot.event_flags) is False


def test_event_flags_fix_persists_to_raw_data(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    ef = bytearray(slot.event_flags)
    EventFlags.set_flag(ef, FixFlags.RANNI_BLOCKING_FLAG, True)
    slot.event_flags = bytes(ef)
    _write_event_flags(sanitized_save, slot)

    EventFlagsFix().apply(sanitized_save, i)

    raw_event_flags = bytes(
        sanitized_save._raw_data[
            slot.event_flags_offset : slot.event_flags_offset
            + EventFlags.EVENT_FLAGS_SIZE
        ]
    )
    assert EventFlags.get_flag(raw_event_flags, FixFlags.RANNI_BLOCKING_FLAG) is False


def test_ranni_softlock_fix_is_independent_of_other_fixes(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    ef = bytearray(slot.event_flags)
    EventFlags.set_flag(ef, FixFlags.RANNI_BLOCKING_FLAG, True)
    slot.event_flags = bytes(ef)
    _write_event_flags(sanitized_save, slot)

    fix = RanniSoftlockFix()
    assert fix.detect(sanitized_save, i) is True
    result = fix.apply(sanitized_save, i)
    assert result.applied is True
    assert fix.detect(sanitized_save, i) is False


def test_ranni_softlock_fix_no_op_when_not_present(sanitized_save):
    i = _first_active_slot(sanitized_save)
    result = RanniSoftlockFix().apply(sanitized_save, i)
    assert result.applied is False
