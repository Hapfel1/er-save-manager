"""Tests for er_save_manager.parser.Save against a real save file."""

from __future__ import annotations

import pytest

from er_save_manager.parser import Save, load_save

SLOT_COUNT = 10
CHECKSUM_SIZE = 0x10


def test_load_save_reads_all_slots(sanitized_save):
    assert len(sanitized_save.character_slots) == SLOT_COUNT
    assert sanitized_save.magic == b"BND4"
    assert sanitized_save.is_ps is False


def test_all_ten_slots_are_active_in_fixture(sanitized_save):
    active = sanitized_save.get_active_slots()
    assert len(active) == SLOT_COUNT


def test_slot_offsets_are_tracked_and_increasing(sanitized_save):
    offsets = sanitized_save._slot_offsets
    assert len(offsets) == SLOT_COUNT
    assert offsets == sorted(offsets)


def test_slot_data_offset_skips_checksum_on_pc(sanitized_save):
    for slot_index in range(SLOT_COUNT):
        base = sanitized_save._slot_offsets[slot_index]
        assert sanitized_save.slot_data_offset(slot_index) == base + CHECKSUM_SIZE


def test_load_save_matches_direct_from_file_call(sanitized_save_path):
    a = load_save(str(sanitized_save_path))
    b = Save.from_file(str(sanitized_save_path))
    assert bytes(a._raw_data) == bytes(b._raw_data)


def test_round_trip_write_is_byte_identical(sanitized_save_path, sanitized_save_copy):
    original_bytes = sanitized_save_path.read_bytes()

    save = load_save(str(sanitized_save_copy))
    save.to_file(str(sanitized_save_copy))

    assert sanitized_save_copy.read_bytes() == original_bytes


def test_get_slot_rejects_out_of_range_index(sanitized_save):
    with pytest.raises(IndexError):
        sanitized_save.get_slot(10)

    with pytest.raises(IndexError):
        sanitized_save.get_slot(-1)
