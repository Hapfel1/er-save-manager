"""DS2 container load checks: cut-off files and entries whose MD5 does not
match (layout documented at the top of DS2/save.py)."""

from __future__ import annotations

import struct

import pytest

from er_save_manager.games.DS2 import save as ds2
from er_save_manager.games.DS2.character_ops import DS2CharacterOperations
from er_save_manager.games.DS2.save import DS2Container, DS2Save
from er_save_manager.validation.numbers import parse_whole

_ENTRY_PLAIN = 0x4000


def _build(tmp_path, damage: tuple[int, ...] = ()) -> tuple:
    """A 23-entry DS2 file of zeroed entries; entries in damage get one
    ciphertext byte flipped after the checksum is computed."""
    count = ds2.TOTAL_ENTRIES
    table = 0x40 + count * 32
    raw = bytearray(table)
    raw[:4] = b"BND4"
    struct.pack_into("<I", raw, 0x0C, count)
    for i in range(count):
        iv = bytes([i]) * 16
        ciphertext = ds2._encrypt(iv, bytearray(_ENTRY_PLAIN))
        blob = bytearray(ds2._md5(iv + ciphertext) + iv + ciphertext)
        if i in damage:
            blob[-20] ^= 0xFF
        struct.pack_into("<I", raw, 0x40 + i * 32 + 8, len(blob))
        struct.pack_into("<I", raw, 0x40 + i * 32 + 16, len(raw))
        raw += blob
    path = tmp_path / "DS2SOFS0000.sl2"
    path.write_bytes(raw)
    return path, bytes(raw)


def _entry_bytes(raw: bytes, index: int) -> bytes:
    size = struct.unpack_from("<I", raw, 0x40 + index * 32 + 8)[0]
    offset = struct.unpack_from("<I", raw, 0x40 + index * 32 + 16)[0]
    return raw[offset : offset + size]


def test_cut_off_file_is_rejected(tmp_path):
    path, raw = _build(tmp_path)
    save = DS2Save.from_file(path)
    assert save.container.damaged_entries() == [] and save.damaged_slots() == []
    for cut in (1, 16, 100):
        path.write_bytes(raw[:-cut])
        with pytest.raises(ValueError, match="cut off"):
            DS2Container.from_file(path)


def test_damaged_entries_lock_their_slot_only(tmp_path):
    path, _ = _build(
        tmp_path, damage=(ds2.PROFILE_ENTRY_START + 1, ds2.BIG_ENTRY_START + 3, 21)
    )
    save = DS2Save.from_file(path)
    assert save.damaged_slots() == [1, 3]
    assert save.slot_lock_reason(1)
    assert save.slot_lock_reason(0) is None
    assert save.damaged_shared_entries() == [21]


def test_write_keeps_untouched_damaged_entry(tmp_path):
    index = ds2.PROFILE_ENTRY_START + 1
    path, raw = _build(tmp_path, damage=(index,))
    save = DS2Save.from_file(path)
    save.characters[0].raw()[0x10] = 1
    save.save_to_file(path)
    written = path.read_bytes()
    assert _entry_bytes(written, index) == _entry_bytes(raw, index)
    assert DS2Save.from_file(path).damaged_slots() == [1]


def test_replaced_damaged_slot_is_written_with_a_valid_checksum(tmp_path):
    path, _ = _build(tmp_path, damage=(ds2.PROFILE_ENTRY_START + 1,))
    save = DS2Save.from_file(path)
    DS2CharacterOperations.delete_slot(save, 1)
    save.characters[1].raw()[0x10] = 1
    assert save.damaged_slots() == []
    save.save_to_file(path)
    assert DS2Save.from_file(path).container.damaged_entries() == []


def test_damaged_slot_cannot_be_copied_or_swapped(tmp_path):
    path, _ = _build(tmp_path, damage=(ds2.PROFILE_ENTRY_START + 1,))
    save = DS2Save.from_file(path)
    with pytest.raises(ValueError, match="damaged"):
        DS2CharacterOperations.copy_slot(save, 1, 2, force=True)
    with pytest.raises(ValueError, match="damaged"):
        DS2CharacterOperations.swap_slots(save, 0, 1, force=True)


def test_parse_whole_accepts_only_ascii_digits():
    for text, value in (("0", 0), (" 42 ", 42), ("007", 7)):
        assert parse_whole(text) == value
    for text in ("", " ", "1_000", "-1", "+3", "1.5", "٣", "１"):
        with pytest.raises(ValueError):
            parse_whole(text)
