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


def test_global_flags_and_their_copy():
    data, flags = _flags()
    flags.set_flag(102460, True)
    offset = GLOBALS + (102460 - 100000) // 8
    assert data[offset] == data[offset + COPY_DISTANCE] == 0x08

    # The copy covers 428 bytes; flags past it are written once
    data, flags = _flags()
    flags.set_flag(100000 + 428 * 8 - 1, True)
    flags.set_flag(100000 + 428 * 8, True)
    assert data[GLOBALS + 427 + COPY_DISTANCE] == 0x01
    assert data[GLOBALS + 428 + COPY_DISTANCE] == 0

    data, flags = _flags()
    flags.set_flag(113416, True)
    offset = GLOBALS + (113416 - 100000) // 8
    assert (data[offset], data[offset + COPY_DISTANCE]) == (0x80, 0)
    assert flags.get_flag(113416)
    flags.set_flag(113416, False)
    assert not any(data)


def test_map_flags():
    data, flags = _flags()
    flags.set_flag(110000170, True)
    # m10_10 is the second record, so the second 25-byte block
    assert data[MAP_BLOCKS + 25 + 170 // 8] == 0x80 >> (170 % 8)
    assert flags.get_flag(110000170)
    # m10_00 has no record
    assert not flags.is_stored(104000050)


def test_ids_the_save_does_not_hold():
    _data, flags = _flags()
    for flag in (
        99999,
        120000,
        200001,
        110000200,
        110030001,
        104010100,
        10020200,
        2030100,
    ):
        assert not flags.is_stored(flag)
        with pytest.raises(ValueError):
            flags.get_flag(flag)
        with pytest.raises(ValueError):
            flags.set_flag(flag, True)
