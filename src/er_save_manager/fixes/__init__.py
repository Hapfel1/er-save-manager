"""ER Save Manager - Corruption Fixes Module."""

from er_save_manager.fixes.base import BaseFix, FixResult
from er_save_manager.fixes.checksum import SlotChecksumFix, check_slot_checksum
from er_save_manager.fixes.deep_scan import (
    DeepScanFix,
    DeepScanResult,
    EFTornScanResult,
)
from er_save_manager.fixes.dlc import DLCFlagFix, InvalidDLCFix
from er_save_manager.fixes.event_flags import EventFlagsFix, RanniSoftlockFix
from er_save_manager.fixes.steamid import SteamIdFix
from er_save_manager.fixes.teleport import (
    TELEPORT_LOCATIONS,
    DLCEscapeFix,
    TeleportFix,
    TeleportLocation,
)
from er_save_manager.fixes.torrent import TorrentFix
from er_save_manager.fixes.weather import WeatherFix

# All available fixes in recommended application order
ALL_FIXES = [
    TorrentFix,
    SteamIdFix,
    WeatherFix,
    EventFlagsFix,
    DLCFlagFix,
    InvalidDLCFix,
    SlotChecksumFix,
    DeepScanFix,
]

__all__ = [
    "BaseFix",
    "FixResult",
    "TorrentFix",
    "SteamIdFix",
    "WeatherFix",
    "EventFlagsFix",
    "RanniSoftlockFix",
    "DLCFlagFix",
    "InvalidDLCFix",
    "SlotChecksumFix",
    "check_slot_checksum",
    "TeleportFix",
    "DLCEscapeFix",
    "TeleportLocation",
    "TELEPORT_LOCATIONS",
    "ALL_FIXES",
    "DeepScanFix",
    "DeepScanResult",
    "EFTornScanResult",
]
