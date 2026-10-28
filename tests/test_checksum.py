"""Tests for er_save_manager.fixes.checksum against a real save file."""

from __future__ import annotations

from er_save_manager.fixes.checksum import (
    CHECKSUM_SIZE,
    SlotChecksumFix,
    check_slot_checksum,
)


def test_all_slots_valid_on_unmodified_save(sanitized_save_readonly):
    for i in range(10):
        valid, stored, computed = check_slot_checksum(sanitized_save_readonly, i)
        assert valid, f"slot {i}: stored={stored} computed={computed}"


def test_fix_repairs_corrupted_checksum(sanitized_save):
    offset = sanitized_save.character_slots[0].data_start - CHECKSUM_SIZE
    sanitized_save._raw_data[offset : offset + CHECKSUM_SIZE] = bytes(CHECKSUM_SIZE)

    fix = SlotChecksumFix()
    assert fix.detect(sanitized_save, 0) is True
    assert fix.apply(sanitized_save, 0).applied is True
    assert check_slot_checksum(sanitized_save, 0)[0]
