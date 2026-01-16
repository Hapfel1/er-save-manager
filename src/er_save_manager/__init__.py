"""Elden Ring Save Manager - Editor, Backup Manager, and Corruption Fixer."""

from .parser import (
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
]

__version__ = "1.0.0"
