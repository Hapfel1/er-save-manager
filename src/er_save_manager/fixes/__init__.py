"""ER Save Manager - Corruption Fixes Module."""

from er_save_manager.fixes.base import BaseFix, FixResult
from er_save_manager.fixes.dlc import DLCFlagFix, InvalidDLCFix
from er_save_manager.fixes.event_flags import EventFlagsFix, RanniSoftlockFix
from er_save_manager.fixes.steamid import SteamIdFix
from er_save_manager.fixes.teleport import (
    TELEPORT_LOCATIONS,
    DLCEscapeFix,
    TeleportFix,
    TeleportLocation,
)
from er_save_manager.fixes.time_sync import TimeFix
from er_save_manager.fixes.torrent import TorrentFix
from er_save_manager.fixes.weather import WeatherFix

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
