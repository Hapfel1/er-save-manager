"""
DS2 NPC state flags.

An NPC's state lives in two byte arrays of the game's flag object, one for
hostility and one for death. Offsets are relative to the start of that object.
A byte is 0 while the flag is clear and holds bits once it is set, for example
0x08 hostile and 0x80 dead for a killed NPC.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NpcEntry:
    name: str
    hostile: int | None
    dead: int | None


NPCS: tuple[NpcEntry, ...] = (
    NpcEntry("Emerald Herald", 0x1C0, 0x1FE),
    NpcEntry("Laddersmith Gilligan", 0x1C4, 0x202),
    NpcEntry("Strowen", None, 0x204),
    NpcEntry("Housekeeper Milibeth", None, 0x208),
    NpcEntry("Darkdiver Grandahl", 0x1CC, 0x20B),
    NpcEntry("Lonesome Gavlan", 0x1CD, 0x20C),
    NpcEntry("Saulden, the Crestfallen Warrior", 0x1CF, 0x20D),
    NpcEntry("Creighton the Wanderer", 0x1D0, 0x20E),
    NpcEntry("Benhart of Jugo", 0x1D1, 0x210),
    NpcEntry("Mild Mannered Pate", 0x1D2, 0x211),
    NpcEntry("Lucatiel of Mirrah", 0x1D5, 0x214),
    NpcEntry("Belfry Guard", 0x1D6, 0x215),
    NpcEntry("Merchant Hag Melentia", 0x1D7, 0x216),
    NpcEntry("Maughlin the Armourer", 0x1DC, 0x21B),
    NpcEntry("Stone Trader Chloanne", 0x1DE, 0x21C),
    NpcEntry("Rosabeth of Melfia", 0x1DF, 0x21D),
    NpcEntry("Blacksmith Lenigrast", 0x1E0, 0x21F),
    NpcEntry("Steady Hand McDuff", 0x1E1, 0x220),
    NpcEntry("Carhillion of the Fold", 0x1E3, 0x221),
    NpcEntry("Straid of Olaphis", 0x1E4, 0x222),
    NpcEntry("Licia of Lindeldt", 0x1E5, 0x224),
    NpcEntry("Felkin the Outcast", 0x1E6, 0x225),
    NpcEntry("Royal Sorcerer Navlaan", 0x1E8, 0x226),
    NpcEntry("Magerold of Lanafir", 0x1E9, 0x227),
    NpcEntry("Weaponsmith Ornifex", 0x1EA, 0x229),
    NpcEntry("Titchy Gren", 0x1ED, 0x22B),
    NpcEntry("Cromwell the Pardoner", 0x1EE, 0x22C),
    NpcEntry("Blue Sentinel Targray", 0x1EF, 0x22E),
    NpcEntry("The Rat King", 0x1F2, 0x230),
    NpcEntry("Manscorpion Tark", 0x1F3, 0x231),
)
