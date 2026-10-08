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


def test_set_intensity_lights_and_writes_the_ascetic_array():
    data = _data()
    bonfires = Bonfires(data)
    assert bonfires.set_intensity([CARDINAL_TOWER], 4) == 1
    assert _byte(data, 0x200, CARDINAL_TOWER) == 1
    assert _byte(data, 0x300, CARDINAL_TOWER) == 3
    assert bonfires.set_intensity([CARDINAL_TOWER], 4) == 0


def test_set_intensity_resets_an_old_editor_level():
    data = _data()
    data[ARRAY + 0x200 + IDS.index(CARDINAL_TOWER)] = 3
    bonfires = Bonfires(data)
    assert bonfires.lit()[CARDINAL_TOWER] is True
    assert bonfires.set_intensity([CARDINAL_TOWER], 1) == 1
    assert _byte(data, 0x200, CARDINAL_TOWER) == 1


def test_unlighting_keeps_intensity():
    data = _data()
    bonfires = Bonfires(data)
    bonfires.set_intensity([CARDINAL_TOWER], 3)
    assert bonfires.set_lit([CARDINAL_TOWER], False) == 1
    assert bonfires.intensities()[CARDINAL_TOWER] == 3


def test_set_intensity_rejects_out_of_range():
    with pytest.raises(ValueError):
        Bonfires(_data()).set_intensity([CARDINAL_TOWER], 9)
