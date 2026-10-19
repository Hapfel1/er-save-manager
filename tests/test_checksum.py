"""Tests for er_save_manager.fixes.checksum against a real save file."""

from __future__ import annotations

from er_save_manager.fixes.checksum import (
    CHECKSUM_SIZE,
    SlotChecksumFix,
    check_slot_checksum,
)

ACTIVE_SLOT_COUNT = 10


def test_all_slots_valid_on_unmodified_save(sanitized_save_readonly):
    for slot_index in range(ACTIVE_SLOT_COUNT):
        slot = sanitized_save_readonly.character_slots[slot_index]
        if slot.is_empty():
            continue
        valid, stored, computed = check_slot_checksum(
            sanitized_save_readonly, slot_index
        )
        assert valid, f"slot {slot_index}: stored={stored} computed={computed}"


def test_fix_repairs_corrupted_checksum(sanitized_save):
    slot_index = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[slot_index]
    checksum_offset = slot.data_start - CHECKSUM_SIZE

    # Corrupt the stored checksum in place.
    sanitized_save._raw_data[checksum_offset : checksum_offset + CHECKSUM_SIZE] = (
        b"\x00" * CHECKSUM_SIZE
    )

    fix = SlotChecksumFix()
    assert fix.detect(sanitized_save, slot_index) is True

    result = fix.apply(sanitized_save, slot_index)
    assert result.applied is True

    valid, _, _ = check_slot_checksum(sanitized_save, slot_index)
    assert valid


def _first_active_slot(save) -> int:
    for i, slot in enumerate(save.character_slots):
        if not slot.is_empty():
            return i
    raise AssertionError("fixture save has no active character slots")
