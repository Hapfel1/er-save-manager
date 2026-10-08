"""DS2 boss records (layout documented above BossStates in DS2/save.py)."""

from __future__ import annotations

import struct

import pytest

from er_save_manager.games.DS2.regulation import BossFight
from er_save_manager.games.DS2.save import BossStates, BossStatus

# BossBattleParam rows 1010010 and 1010000.
LAST_GIANT = BossFight(1010010, 110000081, 100971, 31, 10655)
PURSUER = BossFight(1010000, 110000086, 100968, 28, 10655)
# Map ids of the first three per-map records, m10_02, m10_04 and m10_10.
MAPS = [0x0A020000, 0x0A040000, 0x0A0A0000]
ANCHOR = 0x30000
COPY = 0x604C

# Bytes the game wrote for a Last Giant kill, relative to the first bonfire id
# array: the defeated flag bit in both flag copies, the defeat count in both
# value copies and the defeated bit of m10_10 map flag 81.
LG_FLAG = (-0x151F, 0x10)
LG_COUNT = -0x738
LG_MAP_FLAG = (-0xB94, 0x40)


def _data() -> bytearray:
    return bytearray(ANCHOR + 0x8000)


def _kill_last_giant(data: bytearray, count: int = 1) -> None:
    for copy in (0, COPY):
        data[ANCHOR + LG_FLAG[0] + copy] |= LG_FLAG[1]
        struct.pack_into("<I", data, ANCHOR + LG_COUNT + copy, count)
    data[ANCHOR + LG_MAP_FLAG[0]] |= LG_MAP_FLAG[1]


def _states(data: bytearray) -> dict[int, object]:
    view = BossStates(data, ANCHOR, (LAST_GIANT, PURSUER), MAPS)
    return {s.fight.row_id: s for s in view.states()}


def test_kill_written_by_the_game_reads_as_defeated():
    data = _data()
    _kill_last_giant(data)
    states = _states(data)
    assert states[LAST_GIANT.row_id].status is BossStatus.DEFEATED
    assert states[LAST_GIANT.row_id].defeats == 1
    assert states[PURSUER.row_id].status is BossStatus.NOT_DEFEATED


def test_ascetic_state_reads_as_respawned():
    data = _data()
    _kill_last_giant(data)
    data[ANCHOR + LG_MAP_FLAG[0]] &= ~LG_MAP_FLAG[1] & 0xFF
    assert _states(data)[LAST_GIANT.row_id].status is BossStatus.RESPAWNED


def test_partial_kill_is_invalid_and_repair_completes_it():
    data = _data()
    _kill_last_giant(data, count=0)
    state = _states(data)[LAST_GIANT.row_id]
    assert state.status is BossStatus.INVALID

    view = BossStates(data, ANCHOR, (LAST_GIANT, PURSUER), MAPS)
    assert view.repair([LAST_GIANT.row_id, PURSUER.row_id]) == 1

    expected = _data()
    _kill_last_giant(expected)
    assert data == expected


def test_repair_keeps_a_boss_in_its_arena():
    data = _data()
    data[ANCHOR + LG_FLAG[0]] |= LG_FLAG[1]
    data[ANCHOR + LG_FLAG[0] + COPY] |= LG_FLAG[1]
    view = BossStates(data, ANCHOR, (LAST_GIANT,), MAPS)
    assert view.repair([LAST_GIANT.row_id]) == 1
    assert not data[ANCHOR + LG_MAP_FLAG[0]]
    assert _states(data)[LAST_GIANT.row_id].status is BossStatus.RESPAWNED


def test_respawn_clears_only_the_map_flag():
    data = _data()
    _kill_last_giant(data, count=2)
    view = BossStates(data, ANCHOR, (LAST_GIANT, PURSUER), MAPS)
    assert view.respawn([LAST_GIANT.row_id, PURSUER.row_id]) == 1

    expected = _data()
    _kill_last_giant(expected, count=2)
    expected[ANCHOR + LG_MAP_FLAG[0]] = 0
    assert data == expected


def test_set_defeats_writes_both_copies_and_keeps_the_arena():
    data = _data()
    view = BossStates(data, ANCHOR, (LAST_GIANT,), MAPS)
    assert view.set_defeats([LAST_GIANT.row_id], 3) == 1

    expected = _data()
    _kill_last_giant(expected, count=3)
    expected[ANCHOR + LG_MAP_FLAG[0]] = 0
    assert data == expected
    assert _states(data)[LAST_GIANT.row_id].status is BossStatus.RESPAWNED


def test_set_defeats_rejects_zero():
    view = BossStates(_data(), ANCHOR, (LAST_GIANT,), MAPS)
    with pytest.raises(ValueError):
        view.set_defeats([LAST_GIANT.row_id], 0)


def test_kill_writes_what_the_game_writes():
    data = _data()
    view = BossStates(data, ANCHOR, (LAST_GIANT,), MAPS)
    assert view.kill([LAST_GIANT.row_id]) == 1

    expected = _data()
    _kill_last_giant(expected)
    assert data == expected
    assert view.kill([LAST_GIANT.row_id]) == 0


def test_kill_after_respawn_counts_a_second_defeat():
    data = _data()
    _kill_last_giant(data)
    data[ANCHOR + LG_MAP_FLAG[0]] = 0
    view = BossStates(data, ANCHOR, (LAST_GIANT,), MAPS)
    assert view.kill([LAST_GIANT.row_id]) == 1

    expected = _data()
    _kill_last_giant(expected, count=2)
    assert data == expected
