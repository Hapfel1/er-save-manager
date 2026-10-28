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
    # Bonfire Ascetic state: map flag cleared
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

    # A boss still in its arena stays there
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

    # A kill after a respawn counts a second defeat
    data[ANCHOR + LG_MAP_FLAG[0]] = 0
    assert view.kill([LAST_GIANT.row_id]) == 1

    expected = _data()
    _kill_last_giant(expected, count=2)
    assert data == expected


# BossBattleParam row 1014010, whose spawn-once enemies include Undead Laborer
# generators 2530 and 2533 in m10_14.
MAGUS = BossFight(1014010, 114000096, 101000, 41, 14655)
M10_14 = 0x0A0E0000
RECORD = 0x1000
# Kill counts start after the 16-byte header and 256 u16 generator ids.
KILLS = RECORD + 0x10 + 2 * 256
# Generator ids in the record: 55 (an NPC), then two Laborers.
GENERATORS = (55, 2530, 2533)


def _magus_data() -> bytearray:
    data = _data()
    struct.pack_into("<II", data, RECORD, M10_14, len(GENERATORS))
    struct.pack_into(f"<{len(GENERATORS)}H", data, RECORD + 0x10, *GENERATORS)
    return data


def _magus_view(data: bytearray) -> BossStates:
    return BossStates(data, ANCHOR, (MAGUS,), MAPS + [M10_14], {M10_14: RECORD})


def _magus_map_flag(data: bytearray) -> tuple[int, int]:
    # Local flag 96 in the fourth map's 25-byte block.
    return ANCHOR - 0xBD0 + 3 * 25 + 96 // 8, 0x80 >> 96 % 8


def test_arena_enemy_kill_counts():
    data = _magus_data()
    data[KILLS + 1] = 1
    data[KILLS + 2] = 1
    state = _magus_view(data).states()[0]
    assert state.status is BossStatus.INVALID
    assert state.problem == "2 arena enemies marked killed"

    # Repair clears only the arena enemies' counts
    data[KILLS] = 3
    data[KILLS + 1] = 0
    view = _magus_view(data)
    assert view.repair([MAGUS.row_id]) == 1

    expected = _magus_data()
    expected[KILLS] = 3
    assert data == expected
    assert view.states()[0].status is BossStatus.NOT_DEFEATED

    # The same counts after a win are valid
    data = _magus_data()
    data[KILLS + 1] = data[KILLS + 2] = 1
    offset, mask = _magus_map_flag(data)
    data[offset] |= mask
    view = _magus_view(data)
    view.set_defeats([MAGUS.row_id], 1)
    assert view.states()[0].status is BossStatus.DEFEATED


def test_respawn_resets_the_arena_kill_counts():
    data = _magus_data()
    data[KILLS] = 3
    data[KILLS + 1] = data[KILLS + 2] = 1
    offset, mask = _magus_map_flag(data)
    data[offset] |= mask
    view = _magus_view(data)
    assert view.respawn([MAGUS.row_id]) == 1

    expected = _magus_data()
    expected[KILLS] = 3
    assert data == expected
