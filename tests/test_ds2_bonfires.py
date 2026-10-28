"""DS2 bonfire lit states and intensities (layout documented above Bonfires in
DS2/save.py)."""

from __future__ import annotations

import struct

import pytest

from er_save_manager.games.DS2.bonfire_database import BONFIRES
from er_save_manager.games.DS2.save import Bonfires

IDS = list(BONFIRES)
ARRAY = 0x100
CARDINAL_TOWER = 10655


def _data() -> bytearray:
    data = bytearray(ARRAY + 0x600)
    struct.pack_into(f"<{len(IDS)}H", data, ARRAY, *IDS)
    return data


def _byte(data: bytearray, offset: int, bonfire_id: int) -> int:
    return data[ARRAY + offset + IDS.index(bonfire_id)]


def test_intensity_is_ascetic_count_plus_one():
    data = _data()
    data[ARRAY + 0x200 + IDS.index(CARDINAL_TOWER)] = 1
    data[ARRAY + 0x300 + IDS.index(CARDINAL_TOWER)] = 1
    bonfires = Bonfires(data)
    assert bonfires.lit()[CARDINAL_TOWER] is True
    assert bonfires.intensities()[CARDINAL_TOWER] == 2


def test_set_intensity():
    data = _data()
    bonfires = Bonfires(data)
    assert bonfires.set_intensity([CARDINAL_TOWER], 4) == 1
    assert _byte(data, 0x200, CARDINAL_TOWER) == 1
    assert _byte(data, 0x300, CARDINAL_TOWER) == 3
    assert bonfires.set_intensity([CARDINAL_TOWER], 4) == 0
    # Unlighting keeps the intensity
    assert bonfires.set_lit([CARDINAL_TOWER], False) == 1
    assert bonfires.intensities()[CARDINAL_TOWER] == 4
    with pytest.raises(ValueError):
        bonfires.set_intensity([CARDINAL_TOWER], 9)

    # An old editor wrote the level into the lit byte
    data = _data()
    data[ARRAY + 0x200 + IDS.index(CARDINAL_TOWER)] = 3
    bonfires = Bonfires(data)
    assert bonfires.lit()[CARDINAL_TOWER] is True
    assert bonfires.set_intensity([CARDINAL_TOWER], 1) == 1
    assert _byte(data, 0x200, CARDINAL_TOWER) == 1


def test_ng_plus_cycle_adds_to_intensity():
    data = _data()
    data[ARRAY + 0x300 + IDS.index(CARDINAL_TOWER)] = 1
    bonfires = Bonfires(data, cycle=1)
    assert bonfires.min_intensity == 2
    assert bonfires.intensities()[CARDINAL_TOWER] == 3
    assert bonfires.set_intensity([CARDINAL_TOWER], 5) == 1
    assert _byte(data, 0x300, CARDINAL_TOWER) == 3
    with pytest.raises(ValueError):
        bonfires.set_intensity([CARDINAL_TOWER], 1)
    # Intensity stops at eight
    assert Bonfires(data, cycle=6).intensities()[CARDINAL_TOWER] == 8


MAJULA = 4650
MAPS = {CARDINAL_TOWER: 0x0A0A0000, MAJULA: 0x0A040000}


def _rested_data() -> bytearray:
    """A slot that last rested at Cardinal Tower, as the game writes it."""
    data = bytearray(ARRAY + 0x1000)
    struct.pack_into(f"<{len(IDS)}H", data, ARRAY, *IDS)
    data[ARRAY + 0x200 + IDS.index(CARDINAL_TOWER)] = 1
    struct.pack_into("<3I", data, ARRAY + 0xC00, 0x0A0A0000, CARDINAL_TOWER, 0)
    return data


def test_last_rested():
    data = _rested_data()
    bonfires = Bonfires(data, bonfire_maps=MAPS)
    assert bonfires.last_rested == CARDINAL_TOWER
    assert bonfires.set_last_rested(MAJULA)
    assert struct.unpack_from("<3I", data, ARRAY + 0xC00) == (0x0A040000, MAJULA, 0)
    assert bonfires.last_rested == MAJULA
    assert bonfires.lit()[MAJULA] is True
    assert not bonfires.set_last_rested(MAJULA)
    # A bonfire without a known map cannot be set
    assert not bonfires.can_set_last_rested(2650)
    with pytest.raises(ValueError):
        bonfires.set_last_rested(2650)
