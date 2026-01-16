"""ER Save Manager - Corruption Fixes Module."""

from .base import BaseFix, FixResult
from .dlc import DLCFlagFix, InvalidDLCFix
from .event_flags import EventFlagsFix, RanniSoftlockFix
from .steamid import SteamIdFix
from .teleport import TELEPORT_LOCATIONS, DLCEscapeFix, TeleportFix, TeleportLocation
from .time_sync import TimeFix
from .torrent import TorrentFix
from .weather import WeatherFix

# All available fixes in recommended application order
ALL_FIXES = [
    TorrentFix,
    SteamIdFix,
    TimeFix,
    WeatherFix,
    EventFlagsFix,
    DLCFlagFix,
    InvalidDLCFix,
]

__all__ = [
    # Base
    "BaseFix",
    "FixResult",
    # Individual fixes
    "TorrentFix",
    "SteamIdFix",
    "TimeFix",
    "WeatherFix",
    "EventFlagsFix",
    "RanniSoftlockFix",
    "DLCFlagFix",
    "InvalidDLCFix",
    "TeleportFix",
    "DLCEscapeFix",
    # Teleport locations
    "TeleportLocation",
    "TELEPORT_LOCATIONS",
    # All fixes list
    "ALL_FIXES",
]
