"""
Quest steps of Elden Ring NPCs placed on the map.

A quest table (quest_flags_db.QUEST_FLAGS) belongs to an NPC life block
(npc_data.NPC_FLAGS) when their names share a word, accents ignored ("Kale"
is Kalé), and it uses the block's flags; several tables can match one block
(Irina and Hyetta share 3380). A block no table name matches takes the table
using the most of its flags.
A step moves the NPC when it turns on one of the block's location flags that
npc_locations places on the map.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import cache

from er_save_manager.data.npc_data import NPC_FLAGS
from er_save_manager.data.npc_locations import _placements
from er_save_manager.data.quest_flags_db import QUEST_FLAGS

# Title words that do not identify an NPC
_GENERIC = {"the", "of", "and", "master", "knight", "sir", "brother", "warrior"}
# A table matched by flags alone must use this many of the block's flags;
# tables touching one or two (Ensha's) only reset other NPCs
_MIN_FLAGS = 10


def _words(name: str) -> set[str]:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return {
        w
        for w in plain.lower().replace("/", " ").replace(",", " ").split()
        if len(w) > 2 and w not in _GENERIC
    }


@cache
def quests_for_block(base: int) -> tuple[str, ...]:
    """QUEST_FLAGS keys of the NPC with life block base, the table using
    the most of the block's flags first."""
    names = set().union(*(_words(n) for n, (b, _) in NPC_FLAGS.items() if b == base))

    def uses(key: str) -> int:
        return sum(
            base <= f["id"] < base + 20 for s in QUEST_FLAGS[key] for f in s["flags"]
        )

    counts = {k: uses(k) for k in QUEST_FLAGS}
    by_name = [k for k in QUEST_FLAGS if _words(k) & names]
    named = [k for k in by_name if counts[k]]
    if not named and by_name:
        # Kalé's table uses flags outside his life block only
        keys = by_name
    elif named:
        # A shared word alone ("Hunter" in Yura's table for D) is not
        # enough: keep tables using a fair share of the block's flags
        top = max(counts[k] for k in named)
        keys = [k for k in named if counts[k] * 4 >= top]
    else:
        # Tables named otherwise ("Finger Reader Cone" is Enia's)
        best = max(QUEST_FLAGS, key=counts.__getitem__)
        keys = [best] if counts[best] >= _MIN_FLAGS else []
    return tuple(sorted(keys, key=lambda k: -counts[k]))


@dataclass(frozen=True)
class QuestStep:
    quest: str  # QUEST_FLAGS key
    index: int  # step index in the quest table
    description: str
    location: str | None
    flags: tuple[tuple[int, int], ...]  # (flag id, target value)
    places: tuple[tuple[str, str, float, float, float], ...]  # parts it enables


@cache
def quest_steps(base: int, is_convergence: bool = False) -> tuple[QuestStep, ...]:
    """Every step of the block's quest tables, with the parts a step places
    when it turns on one of the block's location flags."""
    placements = _placements(is_convergence)
    steps = []
    for key in quests_for_block(base):
        for i, s in enumerate(QUEST_FLAGS[key]):
            flags = tuple((f["id"], f["value"]) for f in s["flags"])
            places = tuple(
                tuple(part)
                for flag_id, value in flags
                if value and base + 5 <= flag_id <= base + 17
                for part in placements.get(flag_id, ())
            )
            steps.append(
                QuestStep(key, i, s["description"], s["location"], flags, places)
            )
    return tuple(steps)
