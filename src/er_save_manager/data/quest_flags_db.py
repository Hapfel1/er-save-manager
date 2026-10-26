"""
Quest progress flag database for Elden Ring NPCs.
Derived from community-translated event flag spreadsheet.

Structure:
    QUEST_FLAGS: dict[str, list[dict]]
    Each NPC maps to a list of quest steps.
    Each step: {description, location, flags: [{id, value}]}
    flags[].value is the target state (0 or 1) for that step to be considered complete.

Data lives in quest_flags.json as rows of [description, location, [[id, value], ...]].
The DS3, DSR and DS2 quest_steps.json tables use the same row format.
"""

import json
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "quest_flags.json"


def load_quest_table(path: Path) -> dict[str, list[dict]]:
    """NPC -> steps from a quest table file in the row format above."""
    return {
        npc: [
            {
                "description": description,
                "location": location,
                "flags": [{"id": flag_id, "value": value} for flag_id, value in flags],
            }
            for description, location, flags in steps
        ]
        for npc, steps in json.loads(path.read_text(encoding="utf-8")).items()
    }


QUEST_FLAGS: dict[str, list[dict]] = load_quest_table(_DATA_FILE)
