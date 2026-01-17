"""ER Save Manager Parser package."""

from er_save_manager.parser.character import PlayerGameData, SPEffect
from er_save_manager.parser.equipment import EquippedItems, EquippedSpells, Inventory
from er_save_manager.parser.er_types import (
    FloatVector3,
    FloatVector4,
    Gaitem,
    HorseState,
    MapId,
    Util,
)
from er_save_manager.parser.event_flags import (
    CorruptionDetector,
    CorruptionFixer,
    EventFlags,
    FixFlags,
)
from er_save_manager.parser.save import Save, load_save
from er_save_manager.parser.user_data_10 import Profile, ProfileSummary, UserData10
from er_save_manager.parser.user_data_x import UserDataX
from er_save_manager.parser.world import (
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
