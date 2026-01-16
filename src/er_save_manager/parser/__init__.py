"""ER Save Manager Parser package."""

from .character import PlayerGameData, SPEffect
from .equipment import EquippedItems, EquippedSpells, Inventory
from .er_types import FloatVector3, FloatVector4, Gaitem, HorseState, MapId, Util
from .event_flags import CorruptionDetector, CorruptionFixer, EventFlags, FixFlags
from .save import Save, load_save
from .user_data_10 import Profile, ProfileSummary, UserData10
from .user_data_x import UserDataX
from .world import (
    DLC,
    FaceData,
    PlayerCoordinates,
    RideGameData,
    WorldAreaTime,
    WorldAreaWeather,
)

__all__ = [
    # Main classes
    "Save",
    "load_save",
    "UserDataX",
    "UserData10",
    "Profile",
    "ProfileSummary",
    # Character data
    "PlayerGameData",
    "SPEffect",
    # Equipment
    "Inventory",
    "EquippedSpells",
    "EquippedItems",
    # World data
    "RideGameData",
    "WorldAreaWeather",
    "WorldAreaTime",
    "PlayerCoordinates",
    "FaceData",
    "DLC",
    # Event flags
    "EventFlags",
    "FixFlags",
    "CorruptionDetector",
    "CorruptionFixer",
    # Types
    "MapId",
    "HorseState",
    "FloatVector3",
    "FloatVector4",
    "Gaitem",
    "Util",
]
