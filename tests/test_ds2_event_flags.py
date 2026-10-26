"""DS2 event flag storage: global flags, their partial second copy and the
per-map flag blocks."""

from __future__ import annotations

import pytest

from er_save_manager.games.DS2.save import EventFlags

ANCHOR = 0x30000
GLOBALS = ANCHOR - 0x15A0 + 8
COPY_DISTANCE = 0x604C
MAP_BLOCKS = ANCHOR - 0xBD0
M10_02, M10_10 = 0x0A020000, 0x0A0A0000


def _flags() -> tuple[bytearray, EventFlags]:
    data = bytearray(ANCHOR + 0x8000)
    return data, EventFlags(data, ANCHOR, [M10_02, M10_10])


def test_copied_global_flag_writes_both_copies():
    data, flags = _flags()
    flags.set_flag(102460, True)
    offset = GLOBALS + (102460 - 100000) // 8
    assert data[offset] == 0x08
    assert data[offset + COPY_DISTANCE] == 0x08


def test_global_flag_past_the_copy_writes_first_copy_only():
    data, flags = _flags()
    flags.set_flag(113416, True)
    offset = GLOBALS + (113416 - 100000) // 8
    assert data[offset] == 0x80
    assert data[offset + COPY_DISTANCE] == 0
    assert flags.get_flag(113416)
    flags.set_flag(113416, False)
    assert not any(data)


def test_last_copied_byte():
    data, flags = _flags()
    flags.set_flag(100000 + 428 * 8 - 1, True)
    flags.set_flag(100000 + 428 * 8, True)
    assert data[GLOBALS + 427 + COPY_DISTANCE] == 0x01
    assert data[GLOBALS + 428 + COPY_DISTANCE] == 0


def test_map_flag_uses_the_map_block_in_record_order():
    data, flags = _flags()
    flags.set_flag(110000170, True)
    assert data[MAP_BLOCKS + 25 + 170 // 8] == 0x80 >> (170 % 8)
    assert flags.get_flag(110000170)


@pytest.mark.parametrize(
    "flag",
    [99999, 120000, 200001, 110000200, 110030001, 104010100, 10020200, 2030100],
)
def test_ids_the_save_does_not_hold(flag):
    _data, flags = _flags()
    assert not flags.is_stored(flag)
    with pytest.raises(ValueError):
        flags.get_flag(flag)
    with pytest.raises(ValueError):
        flags.set_flag(flag, True)


def test_map_without_a_record_is_not_stored():
    _data, flags = _flags()
    assert not flags.is_stored(104000050)
