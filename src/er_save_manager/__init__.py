"""Elden Ring Save Manager - Editor, Backup Manager, and Corruption Fixer."""

from er_save_manager.parser import (
    CorruptionDetector,
    CorruptionFixer,
    EventFlags,
    HorseState,
    MapId,
    RideGameData,
    Save,
    UserDataX,
    load_save,
)
from er_save_manager.version_checker import VersionChecker

__all__ = [
    "Save",
    "load_save",
    "UserDataX",
    "MapId",
    "HorseState",
    "RideGameData",
    "EventFlags",
    "CorruptionDetector",
    "CorruptionFixer",
    "VersionChecker",
]

__version__ = "0.8.0"
