"""
Elden Ring Starting Class Base Stats

Each class has base stats that determine the starting level.
Archetype values from the game.
"""

STARTING_CLASSES = {
    0: {
        "name": "Vagabond",
        "level": 9,
        "vigor": 15,
        "mind": 10,
        "endurance": 11,
        "strength": 14,
        "dexterity": 13,
        "intelligence": 9,
        "faith": 9,
        "arcane": 7,
    },
    1: {
        "name": "Warrior",
        "level": 8,
        "vigor": 11,
        "mind": 12,
        "endurance": 11,
        "strength": 10,
        "dexterity": 16,
        "intelligence": 10,
        "faith": 8,
        "arcane": 9,
    },
    2: {
        "name": "Hero",
        "level": 7,
        "vigor": 14,
        "mind": 9,
        "endurance": 12,
        "strength": 16,
        "dexterity": 9,
        "intelligence": 7,
        "faith": 8,
        "arcane": 11,
    },
    3: {
        "name": "Bandit",
        "level": 5,
        "vigor": 10,
        "mind": 11,
        "endurance": 10,
        "strength": 9,
        "dexterity": 13,
        "intelligence": 9,
        "faith": 8,
        "arcane": 14,
    },
    4: {
        "name": "Astrologer",
        "level": 6,
        "vigor": 9,
        "mind": 15,
        "endurance": 9,
        "strength": 8,
        "dexterity": 12,
        "intelligence": 16,
        "faith": 7,
        "arcane": 9,
    },
    5: {
        "name": "Prophet",
        "level": 7,
        "vigor": 10,
        "mind": 14,
        "endurance": 8,
        "strength": 11,
        "dexterity": 10,
        "intelligence": 7,
        "faith": 16,
        "arcane": 10,
    },
    6: {
        "name": "Samurai",
        "level": 9,
        "vigor": 12,
        "mind": 11,
        "endurance": 13,
        "strength": 12,
        "dexterity": 15,
        "intelligence": 9,
        "faith": 8,
        "arcane": 8,
    },
    7: {
        "name": "Prisoner",
        "level": 9,
        "vigor": 11,
        "mind": 12,
        "endurance": 11,
        "strength": 11,
        "dexterity": 14,
        "intelligence": 14,
        "faith": 6,
        "arcane": 9,
    },
    8: {
        "name": "Confessor",
        "level": 10,
        "vigor": 10,
        "mind": 13,
        "endurance": 10,
        "strength": 12,
        "dexterity": 12,
        "intelligence": 9,
        "faith": 14,
        "arcane": 9,
    },
    9: {
        "name": "Wretch",
        "level": 1,
        "vigor": 10,
        "mind": 10,
        "endurance": 10,
        "strength": 10,
        "dexterity": 10,
        "intelligence": 10,
        "faith": 10,
        "arcane": 10,
    },
}


def get_class_data(archetype: int) -> dict:
    """Get starting class data by archetype ID"""
    return STARTING_CLASSES.get(archetype, STARTING_CLASSES[9])  # Default to Wretch


def calculate_level_from_stats(
    vigor: int,
    mind: int,
    endurance: int,
    strength: int,
    dexterity: int,
    intelligence: int,
    faith: int,
    arcane: int,
    archetype: int = 9,
) -> int:
    """Calculate character level from stats based on starting class"""
    base_class = get_class_data(archetype)

    total_points = (
        (vigor - base_class["vigor"])
        + (mind - base_class["mind"])
        + (endurance - base_class["endurance"])
        + (strength - base_class["strength"])
        + (dexterity - base_class["dexterity"])
        + (intelligence - base_class["intelligence"])
        + (faith - base_class["faith"])
        + (arcane - base_class["arcane"])
    )

    return base_class["level"] + total_points
