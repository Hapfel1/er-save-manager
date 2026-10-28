"""Tests for er_save_manager.fixes.dlc."""

from __future__ import annotations

from io import BytesIO

from er_save_manager.fixes.dlc import DLCFlagFix, InvalidDLCFix, TarnishedPackFlagFix

_FLAGS = (
    "shadow_of_erdtree",
    "preorder_the_ring",
    "preorder_ring_of_miquella",
    "tarnished_pack",
)


def _set_dlc(save, **values):
    slot = save.character_slots[0]
    for name, value in values.items():
        setattr(slot.dlc, name, value)
    buf = BytesIO()
    slot.dlc.write(buf)
    data = buf.getvalue()
    save._raw_data[slot.dlc_offset : slot.dlc_offset + len(data)] = data
    return slot


def test_dlc_flag_fix_clears_only_the_entry_flag(sanitized_save):
    # The fixture has the DLC entry flag set on every slot
    for i in range(10):
        assert DLCFlagFix().detect(sanitized_save, i) is True
    slot = _set_dlc(sanitized_save, **dict.fromkeys(_FLAGS[1:], 1))
    assert DLCFlagFix().apply(sanitized_save, 0).applied is True
    assert slot.has_dlc_flag() is False
    assert [getattr(slot.dlc, f) for f in _FLAGS] == [0, 1, 1, 1]
    assert DLCFlagFix().apply(sanitized_save, 0).applied is False


def test_tarnished_pack_fix_clears_only_its_flag(sanitized_save):
    slot = _set_dlc(sanitized_save, **dict.fromkeys(_FLAGS, 1))
    assert TarnishedPackFlagFix().apply(sanitized_save, 0).applied is True
    assert slot.has_tarnished_pack_flag() is False
    assert [getattr(slot.dlc, f) for f in _FLAGS] == [1, 1, 1, 0]
    assert TarnishedPackFlagFix().apply(sanitized_save, 0).applied is False


def test_invalid_dlc_fix_zeroes_unused_bytes_only(sanitized_save):
    # The Tarnished pack flag lies outside the unused range
    slot = _set_dlc(sanitized_save, shadow_of_erdtree=1, tarnished_pack=1)
    assert InvalidDLCFix().detect(sanitized_save, 0) is False

    _set_dlc(sanitized_save, unused=b"\xff" * 46)
    assert InvalidDLCFix().detect(sanitized_save, 0) is True
    assert InvalidDLCFix().apply(sanitized_save, 0).applied is True
    assert slot.dlc.unused == bytes(46)
    assert slot.dlc.shadow_of_erdtree == 1 and slot.dlc.tarnished_pack == 1
