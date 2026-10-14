"""Items counted by the Legendary trophies, in TrophyEquipData bit order.

Bit n of each TrophyEquipData set is the n-th item of the matching tuple
(ascending item id). Ids carry the category tag used in GaitemGameData.
"""

from __future__ import annotations

_GOODS = 0x40000000
_TALISMAN = 0x20000000

# "Legendary Armaments"
LEGENDARY_WEAPONS: tuple[int, ...] = (
    2140000,  # Sword of Night and Flame
    3090000,  # Dark Moon Greatsword
    3150000,  # Marais Executioner's Sword
    3170000,  # Golden Order Greatsword
    4080000,  # Ruins Greatsword
    4100000,  # Grafted Blade Greatsword
    7100000,  # Eclipse Shotel
    12200000,  # Devourer's Scepter
    16090000,  # Bolt of Gransax
)

# Bits 0-6 "Legendary Sorceries and Incantations", bits 7-12 "Legendary
# Ashen Remains".
LEGENDARY_GOODS: tuple[int, ...] = tuple(
    _GOODS | goods_id
    for goods_id in (
        4200,  # Comet Azur
        4210,  # Founding Rain of Stars
        4220,  # Stars of Ruin
        4361,  # Ranni's Dark Moon
        6110,  # Flame of the Fell God
        6720,  # Elden Stars
        7090,  # Greyoll's Roar
        200000,  # Black Knife Tiche
        207000,  # Mimic Tear Ashes
        223000,  # Cleanrot Knight Finlay
        256000,  # Ancient Dragon Knight Kristoff
        257000,  # Redmane Knight Ogha
        258000,  # Lhutel the Headless
    )
)
LEGENDARY_SPELL_COUNT = 7

# "Legendary Talismans"
LEGENDARY_TALISMANS: tuple[int, ...] = tuple(
    _TALISMAN | talisman_id
    for talisman_id in (
        1042,  # Erdtree's Favor +2
        1051,  # Radagon's Soreseal
        1140,  # Moon of Nokstella
        1221,  # Marika's Soreseal
        3060,  # Old Lord's Talisman
        3070,  # Radagon Icon
        3090,  # Godfrey Icon
        4003,  # Dragoncrest Greatshield Talisman
    )
)

# (trophy, TrophyEquipData field, first bit, items)
TROPHIES: tuple[tuple[str, str, int, tuple[int, ...]], ...] = (
    ("Legendary Armaments", "legendary_weapons", 0, LEGENDARY_WEAPONS),
    (
        "Legendary Sorceries and Incantations",
        "legendary_goods",
        0,
        LEGENDARY_GOODS[:LEGENDARY_SPELL_COUNT],
    ),
    (
        "Legendary Ashen Remains",
        "legendary_goods",
        LEGENDARY_SPELL_COUNT,
        LEGENDARY_GOODS[LEGENDARY_SPELL_COUNT:],
    ),
    ("Legendary Talismans", "legendary_talismans", 0, LEGENDARY_TALISMANS),
)


def trophy_progress(trophy_data) -> list[tuple[str, list[tuple[int, bool]]]]:
    """Per trophy: (name, [(item id, counted)]) from a TrophyEquipData."""
    result = []
    for name, field, first, items in TROPHIES:
        bits = int.from_bytes(getattr(trophy_data, field), "little")
        counted = [
            (item, bool(bits >> (first + n) & 1)) for n, item in enumerate(items)
        ]
        result.append((name, counted))
    return result
