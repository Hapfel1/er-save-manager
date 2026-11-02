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


def test_revive_keeps_the_neighbour_sharing_a_flag_byte():
    data = _data()
    _kill_rosabeth(data)
    states = _states(data)
    assert states["Rosabeth of Melfia"].dead
    assert not states["Stone Trader Chloanne"].dead
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


def test_kill_count_or_location_flag_alone_reads_as_dead():
    data = _data()
    data[RECORDS[SHADED_WOODS] + KILL_COUNTS_IN_RECORD + 4] = 1
    assert _states(data)["Rosabeth of Melfia"].dead
    assert NpcStates(data, ANCHOR, RECORDS).revive(["Rosabeth of Melfia"]) == 1
    assert not any(data)
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


# Invaders: the record lists generator ids from offset 0x10, in row order.
IRON_KEEP = 0x0A130000
THE_GUTTER = 0x0A190000
INVADER_RECORDS = {IRON_KEEP: 0x3000, THE_GUTTER: 0x4000}


def _list_generators(data: bytearray, record: int, generators: list[int]) -> None:
    data[record + 4 : record + 8] = len(generators).to_bytes(4, "little")
    for i, g in enumerate(generators):
        data[record + 0x10 + 2 * i : record + 0x12 + 2 * i] = g.to_bytes(2, "little")


def _invaders(data: bytearray) -> dict[tuple[str, int], object]:
    view = NpcStates(data, ANCHOR, INVADER_RECORDS)
    return {(s.invader.name, s.invader.map_id): s for s in view.invader_states()}


def test_invader_reset_clears_only_the_selected_row():
    data = _data()
    record = INVADER_RECORDS[IRON_KEEP]
    _list_generators(data, record, [10, 570, 571, 572, 573, 941])
    data[record + KILL_COUNTS_IN_RECORD + 3] = 1  # Fencer Sharron (572)
    data[record + KILL_COUNTS_IN_RECORD + 4] = 1  # Armorer Dennis (573)
    data[record + 0x310 + 4 * 3 : record + 0x314 + 4 * 3] = b"\x01\x02\x03\x04"
    data[record + 0x710 + 4 * 3] = 2
    states = _invaders(data)
    sharron = states[("Fencer Sharron", IRON_KEEP)]
    assert sharron.killed
    assert states[("Oliver the Collector", IRON_KEEP)].killed is False
    assert states[("Forlorn", IRON_KEEP)].killed is False
    assert states[("Melinda the Butcher", THE_GUTTER)].killed is None

    view = NpcStates(data, ANCHOR, INVADER_RECORDS)
    assert view.reset_invaders([sharron.invader]) == 1
    assert data[record + KILL_COUNTS_IN_RECORD + 3] == 0
    assert not any(data[record + 0x310 + 12 : record + 0x314 + 12])
    assert not any(data[record + 0x710 + 12 : record + 0x714 + 12])
    assert data[record + KILL_COUNTS_IN_RECORD + 4] == 1
    assert view.reset_invaders([sharron.invader]) == 0


def test_melinda_reset_clears_her_death_flag():
    data = _data()
    record = INVADER_RECORDS[THE_GUTTER]
    _list_generators(data, record, [590, 591])
    data[record + KILL_COUNTS_IN_RECORD] = 1
    _set_flag(data, 104470)
    _set_flag(data, 104471)
    melinda = _invaders(data)[("Melinda the Butcher", THE_GUTTER)]
    assert melinda.killed
    NpcStates(data, ANCHOR, INVADER_RECORDS).reset_invaders([melinda.invader])
    assert data[record + KILL_COUNTS_IN_RECORD] == 0
    assert not _flag(data, 104470)
    assert _flag(data, 104471)
