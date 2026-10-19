"""Tests for er_save_manager.parser.Save against a real save file."""

from __future__ import annotations

import struct
from io import BytesIO

import pytest

from er_save_manager.parser import load_save
from er_save_manager.parser.equipment import AcquiredProjectiles

SLOT_COUNT = 10
CHECKSUM_SIZE = 0x10


def test_load_save_reads_all_slots(sanitized_save_readonly):
    assert len(sanitized_save_readonly.character_slots) == SLOT_COUNT
    assert sanitized_save_readonly.magic == b"BND4"
    assert sanitized_save_readonly.is_ps is False


def test_all_ten_slots_are_active_in_fixture(sanitized_save_readonly):
    active = sanitized_save_readonly.get_active_slots()
    assert len(active) == SLOT_COUNT


def test_slot_offsets_are_tracked_and_increasing(sanitized_save_readonly):
    offsets = sanitized_save_readonly._slot_offsets
    assert len(offsets) == SLOT_COUNT
    assert offsets == sorted(offsets)


def test_slot_data_offset_skips_checksum_on_pc(sanitized_save_readonly):
    for slot_index in range(SLOT_COUNT):
        base = sanitized_save_readonly._slot_offsets[slot_index]
        assert (
            sanitized_save_readonly.slot_data_offset(slot_index) == base + CHECKSUM_SIZE
        )


def test_round_trip_write_is_byte_identical(sanitized_save_path, sanitized_save_copy):
    original_bytes = sanitized_save_path.read_bytes()

    save = load_save(str(sanitized_save_copy))
    save.to_file(str(sanitized_save_copy))

    assert sanitized_save_copy.read_bytes() == original_bytes


def test_get_slot_rejects_out_of_range_index(sanitized_save_readonly):
    with pytest.raises(IndexError):
        sanitized_save_readonly.get_slot(10)

    with pytest.raises(IndexError):
        sanitized_save_readonly.get_slot(-1)


def test_garbage_record_count_fails_before_reading_records():
    """A count from a misparsed slot fails at once instead of reading to EOF."""
    f = BytesIO(struct.pack("<I", 0xFFFFFF00) + bytes(0x100000))
    with pytest.raises(ValueError):
        AcquiredProjectiles.read(f)
