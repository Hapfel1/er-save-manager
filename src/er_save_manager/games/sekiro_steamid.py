"""
SteamID patcher for Sekiro: Shadows Die Twice save files (S0000.sl2).

Sekiro saves are unencrypted BND4 files with MD5 checksums. SteamID is stored
as Steam64 (uint64 LE) at fixed offsets in each slot and the settings block.
Recalculating MD5 checksums after patching is sufficient - no RAM injection needed.

All offsets and constants from uberhalit/SimpleSekiroSavegameHelper (MIT license).
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

_BND4_MAGIC = b"BND4\x00\x00\x00\x00"
_MINIMAL_LENGTH = 0x00A603B0

# Slot layout: each slot block is (0x100000 + 16) bytes
_SLOT_BLOCK = 0x100000 + 16
_SLOT_COUNT = 10

# Offsets in the raw file
_FIRST_SLOT_CHECKSUM = 0x00000300  # MD5 of data[offset+16 : offset+16+0x100000]
_SLOT_STEAM_ID = 0x00034164  # Steam64 uint64, 8 bytes
_SETTINGS_CHECKSUM = 0x00A003A0  # MD5 of data[offset+16 : offset+16+0x60000]
_SETTINGS_STEAM_ID = 0x00A003D4  # Steam64 uint64, 8 bytes
_SETTINGS_CHECK_LEN = 0x00060000
_SLOT_CHECK_LEN = 0x00100000


def _md5_range(data: bytes | bytearray, offset: int, length: int) -> bytes:
    return hashlib.md5(data[offset : offset + length]).digest()


def detect_steamid_sekiro(save_path: Path) -> int | None:
    """Read Steam64 from the settings block at fixed offset 0xA003D4."""
    try:
        data = save_path.read_bytes()
        if len(data) < _MINIMAL_LENGTH or data[:8] != _BND4_MAGIC:
            return None
        steamid = struct.unpack_from("<Q", data, _SETTINGS_STEAM_ID)[0]
        if 0x0110000100000000 <= steamid <= 0x01100001FFFFFFFF:
            return steamid
        return None
    except Exception:
        return None


def patch_steamid_sekiro(save_path: Path, new_steam64: int) -> tuple[bool, str]:
    """
    Patch SteamID in all used save slots and the settings block.
    Recalculates MD5 checksums. Writes in-place.
    Returns (success, message).
    """
    try:
        data = bytearray(save_path.read_bytes())
    except OSError as e:
        return False, f"Could not read file: {e}"

    if len(data) < _MINIMAL_LENGTH or data[:8] != _BND4_MAGIC:
        return False, "Not a valid Sekiro SL2 file"

    old_steam64 = struct.unpack_from("<Q", data, _SETTINGS_STEAM_ID)[0]
    if old_steam64 == new_steam64:
        return False, "New SteamID is the same as the current one"

    new_bytes = struct.pack("<Q", new_steam64)
    slots_patched = 0

    for i in range(_SLOT_COUNT):
        steam_off = _SLOT_STEAM_ID + i * _SLOT_BLOCK
        checksum_off = _FIRST_SLOT_CHECKSUM + i * _SLOT_BLOCK

        # Only patch slots that are in use (SteamID != 0)
        current = struct.unpack_from("<Q", data, steam_off)[0]
        if current == 0:
            continue

        # Patch SteamID
        data[steam_off : steam_off + 8] = new_bytes

        # Recalculate slot checksum: MD5 of data[checksum_off+16 : checksum_off+16+slot_len]
        new_checksum = _md5_range(data, checksum_off + 16, _SLOT_CHECK_LEN)
        data[checksum_off : checksum_off + 16] = new_checksum
        slots_patched += 1

    # Patch settings block SteamID
    data[_SETTINGS_STEAM_ID : _SETTINGS_STEAM_ID + 8] = new_bytes

    # Recalculate settings checksum
    new_settings_checksum = _md5_range(
        data, _SETTINGS_CHECKSUM + 16, _SETTINGS_CHECK_LEN
    )
    data[_SETTINGS_CHECKSUM : _SETTINGS_CHECKSUM + 16] = new_settings_checksum

    save_path.write_bytes(bytes(data))
    return True, (
        f"Patched {slots_patched} save slot(s) + settings block\n"
        f"Old SteamID: {old_steam64}\n"
        f"New SteamID: {new_steam64}"
    )
