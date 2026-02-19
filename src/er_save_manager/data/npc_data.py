"""
NPC Revival Data for Elden Ring
Extracted from Translated_Event_Flags.xlsx

Each NPC has 4 sequential flags:
- base+0: Alive (spawn flag)
- base+1: Hostile/Aggro (can be absolved)
- base+2: Hostile/Aggro (permanent, cannot be absolved)
- base+3: Dead

To revive an NPC:
- Set Alive flag to ON (base+0 = True)
- Clear Aggro flags (base+1 = False, base+2 = False)
- Set Dead flag to OFF (base+3 = False)
"""

# Format: "NPC Name": (base_flag_id, "First encounter location")
# Locations extracted from individual NPC sheets in Translated_Event_Flags.xlsx
NPC_FLAGS = {
    # Roundtable Hold NPCs
    "Fia": (4120, "Roundtable Hold"),
    "Gideon Ofnir": (3960, "Roundtable Hold (main grace room)"),
    "Brother Corhyn": (4200, "Roundtable Hold"),
    "Dung Eater": (4240, "Roundtable Hold"),
    "Diallos": (3440, "Roundtable Hold"),
    "Nepheli Loux": (4220, "Stormveil Castle"),
    "D, Hunter of the Dead": (4040, "Roundtable Hold"),
    "Knight Bernahl": (3880, "Warmaster's Shack (Limgrave)"),
    "Ensha": (4280, "Roundtable Hold"),
    "Master Hewg": (3220, "Roundtable Hold"),
    "Roderika": (3700, "Stormhill Shack (Limgrave)"),
    "Enia": (3480, "Roundtable Hold"),
    # Limgrave NPCs
    "Kalé": (4700, "Church of Elleh (Limgrave)"),
    "White Mask Varré": (3180, "First Step (Limgrave)"),
    "Melina": (3160, "Chapel of Anticipation (Limgrave)"),
    "Ranni the Witch": (3740, "Church of Elleh (Limgrave, as Renna)"),
    "Gatekeeper Gostoc": (3260, "Stormveil Castle Gate (Limgrave)"),
    "Sorcerer Rogier": (3900, "Stormveil Castle (Limgrave)"),
    "Patches": (3680, "Murkwater Cave (Limgrave)"),
    "Kenneth Haight": (4260, "Mistwood Outskirts (Limgrave)"),
    "Iron Fist Alexander": (3660, "Saintsbridge (Limgrave)"),
    "Irina": (3380, "Bridge of Sacrifice (Limgrave)"),
    "Edgar": (3400, "Castle Morne (Limgrave)"),
    "Sorceress Sellen": (3460, "Waypoint Ruins Cellar (Limgrave)"),
    # Liurnia NPCs
    "Miriel, Pastor of Vows": (3720, "Church of Vows (Liurnia)"),
    "Iji": (3760, "Road to Manor (Liurnia)"),
    "Seluvis": (3560, "Ranni's Rise (Liurnia)"),
    "Blaidd": (3600, "Mistwood (Limgrave) / Siofra River"),
    "Albus": (3540, "Village of the Albinaurics (Liurnia)"),
    "Latenna": (4100, "Slumbering Wolf's Shack (Liurnia)"),
    "Blackguard Big Boggart": (4140, "Boilprawn Shack (Liurnia)"),
    "Boc the Seamster": (3940, "Coastal Cave (Limgrave)"),
    "Thops": (3800, "Church of Irith (Liurnia)"),
    "Jar-Bairn": (3820, "Jarburg (Liurnia)"),
    "Rya/Zoraya": (3420, "Telescope near Boilprawn Shack (Liurnia)"),
    "Hyetta": (3380, "Lake-Facing Cliffs (Liurnia)"),
    "Pidia": (4300, "Caria Manor (Liurnia)"),
    # Caelid NPCs
    "Gowry": (4160, "Gowry's Shack (Caelid)"),
    "Millicent": (4180, "Aeonia Swamp (Caelid)"),
    "Gurranq, Beast Clergyman": (3640, "Bestial Sanctum (Caelid)"),
    "Jerren": (3360, "Festival Plaza (Caelid)"),
    # Volcano Manor NPCs
    "Tanith": (3100, "Volcano Manor"),
    "Ghost in Volcano Manor": (3780, "Volcano Manor"),
    # Special NPCs
    "Yura/Shabriri": (3620, "Murkwater Coast (Limgrave)"),
    "D's Brother": (4060, "Siofra Aqueduct"),
    "Finger Reader Crone": (3500, "Near Stormveil Castle (Limgrave)"),
    "Jellyfish Spirit Sister": (3840, "Stargazer's Ruins (Mountaintops)"),
    # Boss NPCs (have status flags but can be "revived" to reset aggro)
    "Godrick the Grafted": (3200, "Stormveil Castle"),
    "Margit, the Fell Omen": (3140, "Stormhill"),
    "Mohg, Lord of Blood": (3340, "Mohgwyn Palace"),
    "Morgott, the Omen King": (3320, "Leyndell, Royal Capital"),
}


def get_npc_flags(npc_name: str) -> tuple[int, int, int, int] | None:
    """
    Get 4 sequential flags for NPC: (alive, aggro_absolvable, aggro_permanent, dead)

    Args:
        npc_name: Name of the NPC

    Returns:
        Tuple of (alive_flag, aggro1_flag, aggro2_flag, dead_flag) or None if NPC not found
    """
    if npc_name not in NPC_FLAGS:
        return None
    base_flag, _location = NPC_FLAGS[npc_name]
    return (base_flag, base_flag + 1, base_flag + 2, base_flag + 3)


def get_npc_state(event_flags_accessor, npc_name: str) -> dict | None:
    """
    Get current state of an NPC

    Args:
        event_flags_accessor: EventFlagAccessor instance with get_flag method
        npc_name: Name of the NPC

    Returns:
        Dict with keys: alive, aggro_absolvable, aggro_permanent, dead
        Or None if NPC not found
    """
    flags = get_npc_flags(npc_name)
    if not flags:
        return None

    alive_flag, aggro1_flag, aggro2_flag, dead_flag = flags

    return {
        "alive": event_flags_accessor.get_flag(alive_flag),
        "aggro_absolvable": event_flags_accessor.get_flag(aggro1_flag),
        "aggro_permanent": event_flags_accessor.get_flag(aggro2_flag),
        "dead": event_flags_accessor.get_flag(dead_flag),
    }


def revive_npc(event_flags_accessor, npc_name: str) -> bool:
    """
    Revive an NPC by resetting their status flags

    Sets:
    - Alive flag to ON
    - Both aggro flags to OFF
    - Dead flag to OFF

    Args:
        event_flags_accessor: EventFlagAccessor instance with set_flag method
        npc_name: Name of the NPC to revive

    Returns:
        True if successful, False if NPC not found
    """
    flags = get_npc_flags(npc_name)
    if not flags:
        return False

    alive_flag, aggro1_flag, aggro2_flag, dead_flag = flags

    # Revive: set alive, clear aggro, clear dead
    event_flags_accessor.set_flag(alive_flag, True)  # Spawn NPC
    event_flags_accessor.set_flag(aggro1_flag, False)  # Clear absolvable aggro
    event_flags_accessor.set_flag(aggro2_flag, False)  # Clear permanent aggro
    event_flags_accessor.set_flag(dead_flag, False)  # Mark as alive

    return True


def calm_npc(event_flags_accessor, npc_name: str) -> bool:
    """
    Calm a hostile NPC (clear aggro flags only, doesn't affect alive/dead state)

    Args:
        event_flags_accessor: EventFlagAccessor instance with set_flag method
        npc_name: Name of the NPC to calm

    Returns:
        True if successful, False if NPC not found
    """
    flags = get_npc_flags(npc_name)
    if not flags:
        return False

    _alive_flag, aggro1_flag, aggro2_flag, _dead_flag = flags

    # Clear both aggro flags
    event_flags_accessor.set_flag(aggro1_flag, False)
    event_flags_accessor.set_flag(aggro2_flag, False)

    return True


def get_npc_location(npc_name: str) -> str | None:
    """Get location string for an NPC"""
    if npc_name not in NPC_FLAGS:
        return None
    return NPC_FLAGS[npc_name][1]


def get_all_npcs() -> list[str]:
    """Get list of all NPC names"""
    return sorted(NPC_FLAGS.keys())
