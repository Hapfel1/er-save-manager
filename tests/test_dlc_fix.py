"""
Tests for er_save_manager.fixes.dlc.
"""

from __future__ import annotations

from io import BytesIO

from er_save_manager.fixes.dlc import DLCFlagFix, InvalidDLCFix


def _first_active_slot(save):
    for i, slot in enumerate(save.character_slots):
        if not slot.is_empty():
            return i
    raise AssertionError("fixture save has no active character slots")


def _write_dlc(save, slot) -> None:
    buf = BytesIO()
    slot.dlc.write(buf)
    data = buf.getvalue()
    save._raw_data[slot.dlc_offset : slot.dlc_offset + len(data)] = data


# ---------------------------------------------------------------------------
# DLCFlagFix
# ---------------------------------------------------------------------------


def test_dlc_flag_is_set_on_real_save(sanitized_save):
    """Documents actual fixture state: this character has entered the
    DLC on every active slot, so DLCFlagFix legitimately flags all of
    them. Not a corruption signal by itself.
    """
    fix = DLCFlagFix()
    for i, slot in enumerate(sanitized_save.character_slots):
        if slot.is_empty():
            continue
        assert fix.detect(sanitized_save, i) is True


def test_apply_clears_the_flag(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    assert slot.has_dlc_flag() is True  # fixture precondition

    result = DLCFlagFix().apply(sanitized_save, i)

    assert result.applied is True
    assert slot.dlc.shadow_of_erdtree == 0
    assert slot.has_dlc_flag() is False


def test_apply_is_no_op_when_flag_already_clear(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    slot.dlc.shadow_of_erdtree = 0
    _write_dlc(sanitized_save, slot)

    result = DLCFlagFix().apply(sanitized_save, i)
    assert result.applied is False


def test_apply_preserves_preorder_gesture_flags(sanitized_save):
    """Only shadow_of_erdtree should change; the two preorder gesture
    flags must survive untouched.
    """
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    slot.dlc.preorder_the_ring = 1
    slot.dlc.preorder_ring_of_miquella = 1
    _write_dlc(sanitized_save, slot)

    DLCFlagFix().apply(sanitized_save, i)

    assert slot.dlc.preorder_the_ring == 1
    assert slot.dlc.preorder_ring_of_miquella == 1


# ---------------------------------------------------------------------------
# InvalidDLCFix
# ---------------------------------------------------------------------------


def test_no_false_positive_on_healthy_save(sanitized_save):
    fix = InvalidDLCFix()
    for i, slot in enumerate(sanitized_save.character_slots):
        if slot.is_empty():
            continue
        assert fix.detect(sanitized_save, i) is False, f"slot {i} unexpectedly flagged"


def test_detects_garbage_in_unused_bytes(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]

    slot.dlc.unused = b"\xff" * 47
    _write_dlc(sanitized_save, slot)

    assert InvalidDLCFix().detect(sanitized_save, i) is True


def test_apply_zeroes_unused_bytes_only(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    slot.dlc.shadow_of_erdtree = 1  # keep for post-fix assertion below
    slot.dlc.unused = b"\xff" * 47
    _write_dlc(sanitized_save, slot)

    result = InvalidDLCFix().apply(sanitized_save, i)

    assert result.applied is True
    assert slot.dlc.unused == b"\x00" * 47
    assert slot.dlc.shadow_of_erdtree == 1  # untouched by this fix


def test_apply_is_no_op_when_no_invalid_data(sanitized_save):
    i = _first_active_slot(sanitized_save)
    result = InvalidDLCFix().apply(sanitized_save, i)
    assert result.applied is False
