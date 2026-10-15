"""DS2 NPC states (layout documented in DS2/npc_database.py and above
NpcStates in DS2/save.py)."""

from __future__ import annotations

from er_save_manager.games.DS2.save import NpcStates

ANCHOR = 0x30000
FLAG_OBJECT = ANCHOR - 0x15A0 + 8
KILL_COUNTS_IN_RECORD = 0x210
# Record offsets of m10_17 (Earthen Peak) and m10_29 (Shaded Woods).
EARTHEN_PEAK = 0x0A110000
SHADED_WOODS = 0x0A1D0000
RECORDS = {EARTHEN_PEAK: 0x1000, SHADED_WOODS: 0x2000}


def _data() -> bytearray:
    return bytearray(ANCHOR + 0x8000)


def _set_flag(data: bytearray, flag: int) -> None:
    index = flag - 100000
    data[FLAG_OBJECT + index // 8] |= 0x80 >> (index % 8)


def _flag(data: bytearray, flag: int) -> bool:
    index = flag - 100000
    return bool(data[FLAG_OBJECT + index // 8] & 0x80 >> (index % 8))


def _kill_rosabeth(data: bytearray) -> None:
    """What the game wrote for Rosabeth killed in Shaded Woods: the death flag,
    its Shaded Woods flag and the kill count of generator 117 (row 4)."""
    _set_flag(data, 104270)
    _set_flag(data, 104271)
    data[RECORDS[SHADED_WOODS] + KILL_COUNTS_IN_RECORD + 4] = 1


def _kill_chloanne(data: bytearray) -> None:
    """Chloanne killed in Earthen Peak: death flags 104260/104261 and the kill
    count of generator 195 (row 7)."""
    _set_flag(data, 104260)
    _set_flag(data, 104261)
    data[RECORDS[EARTHEN_PEAK] + KILL_COUNTS_IN_RECORD + 7] = 1


def _states(data: bytearray) -> dict[str, object]:
    view = NpcStates(data, ANCHOR, RECORDS)
    return {s.entry.name: s for s in view.states()}


def test_neighbouring_npcs_read_separately():
    data = _data()
    _kill_rosabeth(data)
    states = _states(data)
    assert states["Rosabeth of Melfia"].dead
    assert not states["Stone Trader Chloanne"].dead


def test_revive_keeps_the_neighbour_sharing_a_flag_byte():
    data = _data()
    _kill_rosabeth(data)
    _kill_chloanne(data)
    NpcStates(data, ANCHOR, RECORDS).revive(["Rosabeth of Melfia"])
    states = _states(data)
    assert not states["Rosabeth of Melfia"].dead
    assert states["Stone Trader Chloanne"].dead
    # 104270 shares its byte with Chloanne's 104264-104269.
    _set_flag(data, 104265)
    NpcStates(data, ANCHOR, RECORDS).revive(["Rosabeth of Melfia"])
    assert _flag(data, 104265)
    assert data[RECORDS[EARTHEN_PEAK] + KILL_COUNTS_IN_RECORD + 7] == 1


def test_kill_count_alone_reads_as_dead_and_revive_clears_it():
    data = _data()
    data[RECORDS[SHADED_WOODS] + KILL_COUNTS_IN_RECORD + 4] = 1
    assert _states(data)["Rosabeth of Melfia"].dead
    assert NpcStates(data, ANCHOR, RECORDS).revive(["Rosabeth of Melfia"]) == 1
    assert not any(data)


def test_location_flag_alone_reads_as_dead():
    data = _data()
    _set_flag(data, 104261)
    assert _states(data)["Stone Trader Chloanne"].dead


def test_calm_clears_only_the_hostile_block():
    data = _data()
    _kill_rosabeth(data)
    _set_flag(data, 103770)
    _set_flag(data, 103771)
    view = NpcStates(data, ANCHOR, RECORDS)
    assert view.calm(["Rosabeth of Melfia"]) == 1
    state = _states(data)["Rosabeth of Melfia"]
    assert not state.hostile
    assert state.dead
