"""
DS2 NPC invaders (black phantoms) and Forlorn.

Each invasion is an event script that waits for the player in a region and
then spawns the invader's generator. The scripts store no flag of their own:
the only saved state is the generator's kill count in its map record (0 before
the kill, 1 after). Forlorn have no event script, but their generators keep
the same kill count.

Generators are GeneratorParam row ids of the invader's map. An entry lists
every generator of one invader in one map (some invaders switch generators by
condition) and any global flag their death also sets.
"""

from __future__ import annotations

from dataclasses import dataclass


def _map(area: int, block: int) -> int:
    return area << 24 | block << 16


FOREST_OF_FALLEN_GIANTS = _map(10, 10)
TSELDORA = _map(10, 14)
ALDIAS_KEEP = _map(10, 15)
LOST_BASTILLE = _map(10, 16)
HARVEST_VALLEY = _map(10, 17)
NO_MANS_WHARF = _map(10, 18)
IRON_KEEP = _map(10, 19)
HUNTSMANS_COPSE = _map(10, 23)
THE_GUTTER = _map(10, 25)
DRAGON_AERIE = _map(10, 27)
SHADED_WOODS = _map(10, 32)
DOORS_OF_PHARROS = _map(10, 33)
GRAVE_OF_SAINTS = _map(10, 34)
SHRINE_OF_AMANA = _map(20, 11)
DRANGLEIC_CASTLE = _map(20, 21)
UNDEAD_CRYPT = _map(20, 24)
SHULVA = _map(50, 35)
BRUME_TOWER = _map(50, 36)
ELEUM_LOYCE = _map(50, 37)

# Set by Melinda's death script; hides her summon sign in Dragon Aerie.
MELINDA_DEATH_FLAG = 104470


@dataclass(frozen=True)
class Invader:
    name: str
    map_id: int
    generators: tuple[int, ...]
    condition: str = ""
    flags: tuple[int, ...] = ()


_NAVLAAN = "After Navlaan is freed, until he dies"
_LICIA = "While Licia is alive"

INVADERS: tuple[Invader, ...] = (
    Invader("Armorer Dennis", FOREST_OF_FALLEN_GIANTS, (521,)),
    Invader("Royal Sorcerer Navlaan", FOREST_OF_FALLEN_GIANTS, (520,), _NAVLAAN),
    Invader("Bowman Guthry", TSELDORA, (520,)),
    Invader("Royal Sorcerer Navlaan", TSELDORA, (521,), _NAVLAAN),
    Invader("Aslatiel of Mirrah", ALDIAS_KEEP, (531,)),
    Invader("Royal Sorcerer Navlaan", ALDIAS_KEEP, (530,), _NAVLAAN),
    Invader("Vorgel the Sinner", LOST_BASTILLE, (540,)),
    Invader("Bell Keeper", LOST_BASTILLE, (541,)),
    Invader("Bell Keeper", IRON_KEEP, (570,)),
    Invader("Oliver the Collector", IRON_KEEP, (571,)),
    Invader("Fencer Sharron", IRON_KEEP, (572,)),
    Invader("Armorer Dennis", IRON_KEEP, (573,)),
    Invader("Merciless Roenna", HUNTSMANS_COPSE, (580,)),
    Invader("Melinda the Butcher", THE_GUTTER, (590,), flags=(MELINDA_DEATH_FLAG,)),
    Invader("Royal Sorcerer Navlaan", THE_GUTTER, (591,), _NAVLAAN),
    Invader("Woodland Child Victor", THE_GUTTER, (592,)),
    Invader("Woodland Child Gully", THE_GUTTER, (593,)),
    Invader("Gutter Denizen", THE_GUTTER, (594,)),
    Invader("Royal Sorcerer Navlaan", DRAGON_AERIE, (600,), _NAVLAAN),
    Invader("Dragonfang Villard", DRAGON_AERIE, (601,)),
    Invader("Transcendent Edde", DRAGON_AERIE, (608,)),
    Invader("Fencer Sharron", DRAGON_AERIE, (609,)),
    Invader("Bowman Guthry", DOORS_OF_PHARROS, (630, 631)),
    Invader("Rhoy the Explorer", GRAVE_OF_SAINTS, (640, 641)),
    Invader("Peculiar Kindalur", SHRINE_OF_AMANA, (660,)),
    Invader("Royal Sorcerer Navlaan", DRANGLEIC_CASTLE, (670,), _NAVLAAN),
    Invader("Nameless Usurper", DRANGLEIC_CASTLE, (671,), _LICIA),
    Invader("Nameless Usurper", UNDEAD_CRYPT, (680,), _LICIA),
    Invader("Jester Thomas", SHULVA, (700,)),
    Invader("Rockshield Baldyr", SHULVA, (720,)),
    Invader("Quicksword Rachel", BRUME_TOWER, (730,)),
    Invader("Maldron the Assassin", BRUME_TOWER, (731,)),
    Invader("Castaway Witch Donna", ELEUM_LOYCE, (760,)),
    Invader("Hexer Nicholai", ELEUM_LOYCE, (761,)),
    Invader("Holy Knight Aurheim", ELEUM_LOYCE, (762,)),
    Invader("Forlorn", FOREST_OF_FALLEN_GIANTS, (923,)),
    Invader("Forlorn", TSELDORA, (926,)),
    Invader("Forlorn", LOST_BASTILLE, (932,)),
    Invader("Forlorn", HARVEST_VALLEY, (935,)),
    Invader("Forlorn", NO_MANS_WHARF, (938,)),
    Invader("Forlorn", IRON_KEEP, (941,)),
    Invader("Forlorn", HUNTSMANS_COPSE, (944,)),
    Invader("Forlorn", THE_GUTTER, (947,)),
    Invader("Forlorn", SHADED_WOODS, (956,)),
    Invader("Forlorn", SHRINE_OF_AMANA, (965,)),
    Invader("Forlorn", DRANGLEIC_CASTLE, (968,)),
    Invader("Forlorn", UNDEAD_CRYPT, (971,)),
    Invader("Forlorn", SHULVA, (974,)),
    Invader("Forlorn", BRUME_TOWER, (977,)),
    Invader("Forlorn", ELEUM_LOYCE, (980,)),
)
