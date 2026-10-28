"""Tests for er_save_manager.parser.Save against a real save file."""

from __future__ import annotations

import struct
from io import BytesIO

import pytest

from er_save_manager.parser import load_save
from er_save_manager.parser.equipment import AcquiredProjectiles

CHECKSUM_SIZE = 0x10


def test_load_save_reads_all_slots(sanitized_save_readonly):
    save = sanitized_save_readonly
    assert save.magic == b"BND4" and save.is_ps is False
    # Other tests use slot 0 knowing every fixture slot holds a character
    assert len(save.get_active_slots()) == len(save.character_slots) == 10
    assert save._slot_offsets == sorted(save._slot_offsets)
    for i, base in enumerate(save._slot_offsets):
        assert save.slot_data_offset(i) == base + CHECKSUM_SIZE
    for index in (10, -1):
        with pytest.raises(IndexError):
            save.get_slot(index)


def test_round_trip_write_is_byte_identical(sanitized_save_path, sanitized_save_copy):
    save = load_save(str(sanitized_save_copy))
    save.to_file(str(sanitized_save_copy))
    assert sanitized_save_copy.read_bytes() == sanitized_save_path.read_bytes()


def test_garbage_record_count_fails_before_reading_records():
    """A count from a misparsed slot fails at once instead of reading to EOF."""
    f = BytesIO(struct.pack("<I", 0xFFFFFF00) + bytes(0x100000))
    with pytest.raises(ValueError):
        AcquiredProjectiles.read(f)
