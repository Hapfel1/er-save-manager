"""Quest step tables (quest_steps.json per game, ER quest_flags.json) and the
DS2 quest flag accessor."""

from __future__ import annotations

from pathlib import Path

import pytest

from er_save_manager.data.quest_flags_db import QUEST_FLAGS, load_quest_table
from er_save_manager.games.DS2.save import QuestFlags

GAMES = Path(__file__).parent.parent / "src" / "er_save_manager" / "games"
TABLES = {
    "DS3": GAMES / "DS3" / "data" / "quest_steps.json",
    "DSR": GAMES / "DSR" / "data" / "quest_steps.json",
    "DS2": GAMES / "DS2" / "data" / "quest_steps.json",
}


@pytest.mark.parametrize("game", TABLES)
def test_tables_load_with_labels_and_flags(game):
    table = load_quest_table(TABLES[game])
    assert table
    for steps in table.values():
        for step in steps:
            assert step["description"].strip()
            assert any(f["value"] == 1 for f in step["flags"])


# DS3 NPCs freed through common_func 20006003: earlier states may stay set,
# so their steps only clear later states.
CUMULATIVE = {
    "Greirat of the Undead Settlement",
    "Orbeck of Vinheim",
    "Cornyx of the Great Swamp",
    "Irina of Carim",
    "Karla",
}


@pytest.mark.parametrize("game", ["DS3", "DSR"])
def test_steps_cover_the_whole_range(game):
    """A step sets its state and clears the rest of the NPC's range, the way
    the game's events move a quest on."""
    for npc, steps in load_quest_table(TABLES[game]).items():
        ranges = set()
        for step in steps:
            on = [f["id"] for f in step["flags"] if f["value"] == 1]
            assert len(on) == 1
            if npc in CUMULATIVE:
                assert all(f["id"] > on[0] for f in step["flags"] if not f["value"])
                continue
            ids = sorted(f["id"] for f in step["flags"])
            assert ids == list(range(ids[0], ids[-1] + 1))
            ranges.add((ids[0], ids[-1]))
        assert len(ranges) <= 1


def test_ds3_ranges_sit_below_the_alive_flag():
    """Quest range = alive_flag - 15 .. alive_flag - 1, alive_flag at x15 or x35
    (Old Woman of Londor 1575, range 1560-1574)."""
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
    flags = QuestFlags(data, ANCHOR)
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
