"""Quest step tables (quest_steps.json per game, ER quest_flags.json) and the
DS2 quest flag accessor."""

from __future__ import annotations

from pathlib import Path

import pytest

from er_save_manager.data.quest_flags_db import QUEST_FLAGS, load_quest_table
from er_save_manager.games.DS2.save import EventFlags
from er_save_manager.ui.quest_progress_dialog import is_tracked, steps_up_to

GAMES = Path(__file__).parent.parent / "src" / "er_save_manager" / "games"
TABLES = {
    "DS3": GAMES / "DS3" / "data" / "quest_steps.json",
    "DSR": GAMES / "DSR" / "data" / "quest_steps.json",
    "DS2": GAMES / "DS2" / "data" / "quest_steps.json",
}


def test_tables_load_with_labels_and_flags():
    for path in TABLES.values():
        table = load_quest_table(path)
        assert table, path
        for steps in table.values():
            for step in steps:
                assert step["description"].strip()
                assert any(f["value"] == 1 for f in step["flags"])


# DS3 NPCs freed through common_func 20006003: states up to these stay set
# together, so their steps only clear later states; later steps clear the
# whole range.
CUMULATIVE = {
    "Greirat of the Undead Settlement": 1203,
    "Orbeck of Vinheim": 1221,
    "Cornyx of the Great Swamp": 1241,
    "Irina of Carim": 1282,
    "Karla": 1261,
}


def test_steps_cover_the_whole_range():
    """A step sets its state and clears the rest of the NPC's range, the way
    the game's events move a quest on."""
    for game in ("DS3", "DSR"):
        for npc, steps in load_quest_table(TABLES[game]).items():
            ranges = set()
            for step in steps:
                on = [f["id"] for f in step["flags"] if f["value"] == 1]
                assert len(on) == 1
                if on[0] <= CUMULATIVE.get(npc, -1):
                    assert all(f["id"] > on[0] for f in step["flags"] if not f["value"])
                    continue
                ids = sorted(f["id"] for f in step["flags"])
                assert ids == list(range(ids[0], ids[-1] + 1))
                ranges.add((ids[0], ids[-1]))
            assert len(ranges) <= 1, npc
    # DS3 range = alive_flag - 15 .. alive_flag - 1, alive_flag at x15 or x35
    # (Old Woman of Londor 1575, range 1560-1574)
    for steps in load_quest_table(TABLES["DS3"]).values():
        ids = [f["id"] for step in steps for f in step["flags"]]
        assert min(ids) % 20 in (0, 15) and max(ids) - min(ids) < 15


def test_er_block_states_have_steps_for_dlc_npcs():
    """NPC block states (base+5..base+17) added for NPCs the community table
    did not cover, Shadow of the Erdtree ones included."""
    for npc in ("Thiollier", "Sir Ansbach", "Boc the Seamster"):
        assert QUEST_FLAGS[npc]


ANCHOR = 0x30000
COPY_DISTANCE = 0x604C


def test_ds2_quest_flags_write_both_copies():
    data = bytearray(ANCHOR + 0x8000)
    flags = EventFlags(data, ANCHOR, [])
    flags.set_flag(102480, True)
    first = ANCHOR - 0x15A0 + 8 + (102480 - 100000) // 8
    mask = 0x80 >> ((102480 - 100000) % 8)
    assert data[first] == mask
    assert data[first + COPY_DISTANCE] == mask
    assert flags.get_flag(102480)
    flags.set_flag(102480, False)
    assert not any(data)
    with pytest.raises(ValueError):
        flags.get_flag(99999)


def _step(*flags):
    return {"flags": [{"id": i, "value": v} for i, v in flags]}


# Greirat-style steps: each sets its state and clears only later ones.
RESCUE_STEPS = [
    _step((1201, 1), (1202, 0), (1203, 0)),
    _step((1202, 1), (1203, 0)),
    _step((1203, 1)),
]


def _is_complete(state):
    return lambda s: all(state.get(f["id"], 0) == f["value"] for f in s["flags"])


def test_steps_up_to_applies_the_steps_in_between():
    chain = steps_up_to(RESCUE_STEPS, 2, _is_complete({1201: 1}))
    assert chain == RESCUE_STEPS[1:]
    assert steps_up_to(RESCUE_STEPS, 0, _is_complete({})) == RESCUE_STEPS[:1]
    # Steps that only clear flags are not tracked
    assert not is_tracked(_step((10, 0), (11, 0)))
    assert is_tracked(_step((10, 0), (11, 1)))
