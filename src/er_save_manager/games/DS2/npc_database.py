"""
DS2 NPC state.

Each NPC owns two blocks of ten global event flags, numbered by the NPC's
block index b:
- hostile: HOSTILE_FLAG_FIRST + 10 * b and the nine after it. The first is
  the NPC turning hostile, the others the same per location.
- death: DEATH_FLAG_FIRST + 10 * b and the nine after it, laid out the same
  way. A death can set only a location flag.
Ten-flag blocks do not line up with bytes, so neighbouring NPCs share bytes.

Killing an NPC also raises the kill count of the generator that spawned them
in that map's record. The generators are listed by GeneratorParam row id; an
NPC uses the same ids in every map it appears in. Ids from 500 up are summon
and invader variants and are not listed.
"""

from __future__ import annotations

from dataclasses import dataclass

HOSTILE_FLAG_FIRST = 103500
DEATH_FLAG_FIRST = 104000
FLAGS_PER_NPC = 10


@dataclass(frozen=True)
class NpcEntry:
    name: str
    block: int
    generators: tuple[int, ...]

    @property
    def hostile_flags(self) -> range:
        first = HOSTILE_FLAG_FIRST + FLAGS_PER_NPC * self.block
        return range(first, first + FLAGS_PER_NPC)

    @property
    def death_flags(self) -> range:
        first = DEATH_FLAG_FIRST + FLAGS_PER_NPC * self.block
        return range(first, first + FLAGS_PER_NPC)


NPCS: tuple[NpcEntry, ...] = (
    NpcEntry("Emerald Herald", 2, (205, 207, 400, 401, 402, 405)),
    NpcEntry("Laddersmith Gilligan", 5, (45, 46, 47)),
    NpcEntry("Strowen", 6, (210, 211, 212)),
    NpcEntry("Housekeeper Milibeth", 10, (15, 16, 17)),
    NpcEntry("Darkdiver Grandahl", 12, (40, 41)),
    NpcEntry("Lonesome Gavlan", 13, (245, 246)),
    NpcEntry("Saulden, the Crestfallen Warrior", 14, (100, 101)),
    NpcEntry("Creighton the Wanderer", 15, (55, 56, 57, 58)),
    NpcEntry("Benhart of Jugo", 16, (60, 61)),
    NpcEntry("Mild Mannered Pate", 17, (65, 66)),
    NpcEntry("Lucatiel of Mirrah", 19, (90, 91)),
    NpcEntry("Belfry Guard", 20, (95, 96)),
    NpcEntry("Merchant Hag Melentia", 21, (260, 261)),
    NpcEntry("Maughlin the Armourer", 25, (105, 106, 107, 108)),
    NpcEntry("Stone Trader Chloanne", 26, (110, 111, 195, 196)),
    NpcEntry("Rosabeth of Melfia", 27, (115, 116, 117)),
    NpcEntry("Blacksmith Lenigrast", 28, (120, 121, 122)),
    NpcEntry("Steady Hand McDuff", 29, (165, 166, 167)),
    NpcEntry("Carhillion of the Fold", 30, (135, 136)),
    NpcEntry("Straid of Olaphis", 31, (145, 146, 147)),
    NpcEntry("Licia of Lindeldt", 32, (150, 151, 152)),
    NpcEntry("Felkin the Outcast", 33, (155, 156)),
    NpcEntry("Royal Sorcerer Navlaan", 34, (160, 161)),
    NpcEntry("Magerold of Lanafir", 35, (175, 176)),
    NpcEntry("Weaponsmith Ornifex", 36, (265, 266)),
    NpcEntry("Titchy Gren", 38, (275, 276)),
    NpcEntry("Cromwell the Pardoner", 39, (310, 311)),
    NpcEntry("Blue Sentinel Targray", 40, (315, 316)),
    NpcEntry("The Rat King", 42, (285, 286)),
    NpcEntry("Manscorpion Tark", 43, (325,)),
)
