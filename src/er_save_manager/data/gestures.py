"""
Gesture database for Elden Ring
Maps gesture IDs to names and categories
Based on Cheat Engine script gesture_ids
"""

# Base game gestures - using actual gesture slot IDs from CE script
GESTURES_BASE = {
    1: {"name": "Bow", "category": "Greetings", "item_id": 0x40002328},
    3: {"name": "Polite Bow", "category": "Greetings", "item_id": 0x40002329},
    5: {"name": "My Thanks", "category": "Greetings", "item_id": 0x4000232A},
    7: {"name": "Curtsy", "category": "Greetings", "item_id": 0x4000232B},
    9: {"name": "Reverential Bow", "category": "Greetings", "item_id": 0x4000232C},
    11: {"name": "My Lord", "category": "Greetings", "item_id": 0x4000232D},
    13: {"name": "Warm Welcome", "category": "Greetings", "item_id": 0x4000232E},
    15: {"name": "Wave", "category": "Greetings", "item_id": 0x4000232F},
    17: {"name": "Casual Greeting", "category": "Greetings", "item_id": 0x40002330},
    19: {"name": "Strength!", "category": "Greetings", "item_id": 0x40002331},
    21: {"name": "As You Wish", "category": "Greetings", "item_id": 0x40002332},
    41: {"name": "Point Forwards", "category": "Gesturing", "item_id": 0x40002333},
    43: {"name": "Point Upwards", "category": "Gesturing", "item_id": 0x40002334},
    45: {"name": "Point Downwards", "category": "Gesturing", "item_id": 0x40002335},
    47: {"name": "Beckon", "category": "Gesturing", "item_id": 0x40002336},
    49: {"name": "Wait!", "category": "Gesturing", "item_id": 0x40002337},
    51: {"name": "Calm Down!", "category": "Gesturing", "item_id": 0x40002338},
    61: {"name": "Nod In Thought", "category": "Gesturing", "item_id": 0x40002339},
    81: {"name": "Extreme Repentance", "category": "Submissive", "item_id": 0x4000233A},
    83: {"name": "Grovel For Mercy", "category": "Submissive", "item_id": 0x4000233B},
    101: {"name": "Rallying Cry", "category": "Battle", "item_id": 0x4000233C},
    103: {"name": "Heartening Cry", "category": "Battle", "item_id": 0x4000233D},
    105: {"name": "By My Sword", "category": "Battle", "item_id": 0x4000233E},
    107: {"name": "Hoslow's Oath", "category": "Battle", "item_id": 0x4000233F},
    109: {"name": "Fire Spur Me", "category": "Battle", "item_id": 0x40002340},
    111: {
        "name": "The Carian Oath",
        "category": "Battle",
        "item_id": 0x40002341,
        "cut_content": True,
    },
    121: {"name": "Bravo!", "category": "Celebration", "item_id": 0x40002342},
    141: {"name": "Jump for Joy", "category": "Celebration", "item_id": 0x40002343},
    143: {
        "name": "Triumphant Delight",
        "category": "Celebration",
        "item_id": 0x40002344,
    },
    145: {"name": "Fancy Spin", "category": "Celebration", "item_id": 0x40002345},
    147: {"name": "Finger Snap", "category": "Celebration", "item_id": 0x40002346},
    161: {"name": "Dejection", "category": "Emotion", "item_id": 0x40002347},
    181: {"name": "Patches' Crouch", "category": "Resting", "item_id": 0x40002348},
    183: {"name": "Crossed Legs", "category": "Resting", "item_id": 0x40002349},
    185: {"name": "Rest", "category": "Resting", "item_id": 0x4000234A},
    187: {"name": "Sitting Sideways", "category": "Resting", "item_id": 0x4000234B},
    189: {"name": "Dozing Cross-Legged", "category": "Resting", "item_id": 0x4000234C},
    191: {"name": "Spread Out", "category": "Resting", "item_id": 0x4000234D},
    193: {
        "name": "Fetal Position",
        "category": "Resting",
        "item_id": 0x4000234E,
        "cut_content": True,
    },
    195: {"name": "Balled Up", "category": "Resting", "item_id": 0x4000234F},
    197: {"name": "What Do You Want?", "category": "Emotion", "item_id": 0x40002350},
    201: {"name": "Prayer", "category": "Prayer", "item_id": 0x40002351},
    203: {"name": "Desperate Prayer", "category": "Prayer", "item_id": 0x40002352},
    205: {"name": "Rapture", "category": "Prayer", "item_id": 0x40002353},
    207: {"name": "Erudition", "category": "Prayer", "item_id": 0x40002355},
    209: {"name": "Outer Order", "category": "Prayer", "item_id": 0x40002356},
    211: {"name": "Inner Order", "category": "Prayer", "item_id": 0x40002357},
    213: {"name": "Golden Order Totality", "category": "Prayer", "item_id": 0x40002358},
    217: {
        "name": "The Ring (Pre-Order)",
        "category": "Special",
        "item_id": 0x40002359,
        "preorder": True,
    },
    219: {"name": "The Ring (Co-op)", "category": "Special", "item_id": 0x4000235A},
    221: {
        "name": "?GoodsName?",
        "category": "Special",
        "item_id": 0x40002354,
        "cut_content": True,
    },
}

# DLC gestures
GESTURES_DLC = {
    223: {
        "name": "May the Best Win",
        "category": "Battle",
        "item_id": 0x401EA7A9,
        "dlc": True,
    },
    225: {
        "name": "The Two Fingers",
        "category": "Gesturing",
        "item_id": 0x401EA7AA,
        "dlc": True,
    },
    227: {
        "name": "Ring of Miquella (Pre-Order)",
        "category": "Special",
        "item_id": 0x401EA7A8,
        "dlc": True,
        "preorder": True,
    },
    229: {
        "name": "Let Us Go Together",
        "category": "Greetings",
        "item_id": 0x401EA7AB,
        "dlc": True,
    },
    231: {"name": "O Mother", "category": "Prayer", "item_id": 0x401EA7AC, "dlc": True},
    233: {
        "name": "Ring of Miquella",
        "category": "Special",
        "item_id": 0x401EA7A8,
        "dlc": True,
    },
}

# Combine all gestures
GESTURES_ALL = {**GESTURES_BASE, **GESTURES_DLC}

# Categories
GESTURE_CATEGORIES = {
    "Greetings": [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 229],
    "Gesturing": [41, 43, 45, 47, 49, 51, 61, 225],
    "Battle": [101, 103, 105, 107, 109, 111, 223],
    "Celebration": [121, 141, 143, 145, 147],
    "Emotion": [161, 197],
    "Resting": [181, 183, 185, 187, 189, 191, 193, 195],
    "Prayer": [201, 203, 205, 207, 209, 211, 213, 231],
    "Submissive": [81, 83],
    "Special": [217, 219, 221, 227, 233],
}


def get_gesture_name(gesture_id: int) -> str:
    """Get gesture name from ID"""
    gesture = GESTURES_ALL.get(gesture_id)
    if gesture:
        return gesture["name"]
    return f"Unknown ({gesture_id})"


def get_gesture_category(gesture_id: int) -> str:
    """Get gesture category from ID"""
    gesture = GESTURES_ALL.get(gesture_id)
    if gesture:
        return gesture["category"]
    return "Unknown"


def is_cut_content(gesture_id: int) -> bool:
    """Check if gesture is cut content"""
    gesture = GESTURES_ALL.get(gesture_id)
    return gesture.get("cut_content", False) if gesture else False


def is_dlc_gesture(gesture_id: int) -> bool:
    """Check if gesture is DLC"""
    gesture = GESTURES_ALL.get(gesture_id)
    return gesture.get("dlc", False) if gesture else False


def get_all_unlockable_gestures(include_cut_content: bool = False) -> list[int]:
    """
    Get list of all unlockable gesture IDs

    Args:
        include_cut_content: Whether to include cut content gestures

    Returns:
        List of gesture IDs
    """
    gestures = []
    for gesture_id, data in GESTURES_ALL.items():
        # Skip cut content unless requested
        if data.get("cut_content", False) and not include_cut_content:
            continue
        gestures.append(gesture_id)
    return sorted(gestures)


def get_gestures_by_category(category: str) -> list[int]:
    """Get all gesture IDs in a category"""
    return GESTURE_CATEGORIES.get(category, [])
