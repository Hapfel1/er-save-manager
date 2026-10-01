"""
Quest progress flag database for Elden Ring NPCs.
Derived from community-translated event flag spreadsheet.

Structure:
    QUEST_FLAGS: dict[str, list[dict]]
    Each NPC maps to a list of quest steps.
    Each step: {description, location, flags: [{id, value}]}
    flags[].value is the target state (0 or 1) for that step to be considered complete.

Data lives in quest_flags.json as rows of [description, location, [[id, value], ...]].
"""

import json
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "quest_flags.json"

QUEST_FLAGS: dict[str, list[dict]] = {
    npc: [
        {
            "description": description,
            "location": location,
            "flags": [{"id": flag_id, "value": value} for flag_id, value in flags],
        }
        for description, location, flags in steps
    ]
    for npc, steps in json.loads(_DATA_FILE.read_text(encoding="utf-8")).items()
}
