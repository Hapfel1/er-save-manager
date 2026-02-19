#!/usr/bin/env python3
"""
Test script to check NPC flag states in a save file
Usage: uv run python test_npc_flags.py <save_file_path> <slot_number>
"""

import sys

from er_save_manager.data.npc_data import NPC_FLAGS, get_npc_flags
from er_save_manager.parser import Save
from er_save_manager.parser.event_flags import EventFlags


def test_npc_flags(save_path: str, slot: int):
    """Test NPC flag states"""
    print(f"Loading save: {save_path}")
    save = Save.from_file(save_path)

    print(f"Number of character slots: {len(save.character_slots)}")

    slot_idx = slot - 1

    if slot_idx >= len(save.character_slots):
        print(
            f"Error: Slot {slot} doesn't exist! Only {len(save.character_slots)} slots available."
        )
        return

    character = save.character_slots[slot_idx]
    if character.is_empty():
        print(f"Slot {slot} is empty!")
        return

    print(f"Testing NPC flags for Slot {slot}")
    print("=" * 80)

    # Test a few key NPCs
    test_npcs = ["Patches", "Kalé", "White Mask Varré", "Melina", "Ranni the Witch"]

    for npc_name in test_npcs:
        if npc_name not in NPC_FLAGS:
            continue

        flags = get_npc_flags(npc_name)
        if not flags:
            continue

        alive_flag, aggro1, aggro2, dead_flag = flags

        # Read flags directly
        alive = EventFlags.get_flag(character.event_flags, alive_flag)
        aggro_abs = EventFlags.get_flag(character.event_flags, aggro1)
        aggro_perm = EventFlags.get_flag(character.event_flags, aggro2)
        dead = EventFlags.get_flag(character.event_flags, dead_flag)

        print(f"\n{npc_name} (base flag: {alive_flag}):")
        print(f"  {alive_flag} Alive:          {alive}")
        print(f"  {aggro1} Aggro (abs):     {aggro_abs}")
        print(f"  {aggro2} Aggro (perm):    {aggro_perm}")
        print(f"  {dead_flag} Dead:           {dead}")

        # Determine state
        if dead:
            status = "DEAD"
        elif aggro_perm or aggro_abs:
            status = "HOSTILE"
        elif alive:
            status = "ALIVE"
        else:
            status = "NOT SPAWNED"

        print(f"  → Status: {status}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: uv run python test_npc_flags.py <save_file_path> <slot_number>")
        sys.exit(1)

    test_npc_flags(sys.argv[1], int(sys.argv[2]))
