"""
SteamID patcher for Dark Souls III save files (DS30000.sl2).

DS3 saves use BND4 with AES-128-CBC encrypted entries. Each entry has:
  [16 bytes MD5 checksum of (IV + encrypted payload)]
  [16 bytes IV]
  [AES-CBC encrypted payload]

Key found by Atvaark, published in DS3SaveUnpacker by tremwil.

SteamID storage (all values are Steam32 / account ID, i.e. Steam64 - 0x0110000100000000):
  USER_DATA_010 (global menu): int32 at offset 0x8 of decrypted data
  USER_DATA_000..009 (char slots): int32 at SlotData[int32@0x58 + 0x6F]

Reference: JKAnderson/SaveMerge (MIT license)
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

_DS3_KEY = bytes.fromhex("FD464D695E69A39A10E319A7ACE8B7FA")
_IV_SIZE = 16
_MD5_SIZE = 16
_STEAM64_BASE = 0x0110000100000000
_BND4_MAGIC = b"BND4"
_ENTRY_STRIDE = 32
_ENTRIES_START = 64


def _steam64_to_32(steam64: int) -> int:
    return steam64 - _STEAM64_BASE


def _steam32_to_64(steam32: int) -> int:
    return steam32 + _STEAM64_BASE


def _decrypt_entry(raw_entry: bytes) -> tuple[bytes, bytes, bytearray]:
    """Returns (md5, iv, decrypted)."""
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    md5 = raw_entry[:_MD5_SIZE]
    iv = raw_entry[_MD5_SIZE : _MD5_SIZE + _IV_SIZE]
    payload = raw_entry[_MD5_SIZE + _IV_SIZE :]
    cipher = Cipher(algorithms.AES(_DS3_KEY), modes.CBC(iv), backend=default_backend())
    dec = cipher.decryptor()
    return md5, iv, bytearray(dec.update(payload) + dec.finalize())


def _encrypt_entry(iv: bytes, decrypted: bytearray) -> bytes:
    """Returns [MD5][IV][encrypted]."""
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    cipher = Cipher(algorithms.AES(_DS3_KEY), modes.CBC(iv), backend=default_backend())
    enc = cipher.encryptor()
    encrypted = enc.update(bytes(decrypted)) + enc.finalize()
    md5 = hashlib.md5(iv + encrypted).digest()
    return md5 + iv + encrypted


def _read_entry(raw: bytes, index: int) -> tuple[int, int]:
    """Returns (size, data_offset) for entry at index."""
    pos = _ENTRIES_START + index * _ENTRY_STRIDE
    size = struct.unpack_from("<I", raw, pos + 8)[0]
    data_offset = struct.unpack_from("<I", raw, pos + 16)[0]
    return size, data_offset


def detect_steamid_ds3(save_path: Path) -> int | None:
    """
    Read SteamID from DS3 save. Returns Steam64 or None.
    Reads the int32 Steam32 from USER_DATA_010 at offset 0x8 and converts.
    """
    try:
        raw = save_path.read_bytes()
        if raw[:4] != _BND4_MAGIC:
            return None
        file_count = struct.unpack_from("<I", raw, 0x0C)[0]
        if file_count < 11:
            return None
        size, offset = _read_entry(raw, 10)
        _, _, dec = _decrypt_entry(raw[offset : offset + size])
        steam32 = struct.unpack_from("<i", dec, 0x8)[0]  # signed int32
        if steam32 <= 0:
            return None
        return _steam32_to_64(steam32)
    except Exception:
        return None


def patch_steamid_ds3(save_path: Path, new_steam64: int) -> tuple[bool, str]:
    """
    Patch the SteamID in a DS3 save. Writes in-place.
    Accepts Steam64 and converts to Steam32 internally.
    Returns (success, message).
    """
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher  # noqa: F401
    except ImportError:
        return False, "cryptography package required. Run: uv add cryptography"

    try:
        raw = bytearray(save_path.read_bytes())
    except OSError as e:
        return False, f"Could not read file: {e}"

    if raw[:4] != _BND4_MAGIC:
        return False, "Not a valid BND4/SL2 file"

    file_count = struct.unpack_from("<I", raw, 0x0C)[0]
    if file_count < 11:
        return False, f"Expected at least 11 entries, found {file_count}"

    new_steam32 = _steam64_to_32(new_steam64)
    new_steam32_bytes = struct.pack("<i", new_steam32)

    # Detect old ID from entry 10
    size10, off10 = _read_entry(raw, 10)
    _, iv10, dec10 = _decrypt_entry(bytes(raw[off10 : off10 + size10]))
    old_steam32 = struct.unpack_from("<i", dec10, 0x8)[0]
    old_steam64 = _steam32_to_64(old_steam32) if old_steam32 > 0 else None

    if old_steam32 == new_steam32:
        return False, "New SteamID is the same as the current one"

    # Patch entry 10: write Steam32 at offset 0x8
    dec10[0x8:0xC] = new_steam32_bytes
    raw[off10 : off10 + size10] = _encrypt_entry(iv10, dec10)

    # Patch character slots (entries 0-9)
    slots_patched = 0
    for i in range(min(10, file_count)):
        size, offset = _read_entry(raw, i)
        _, iv, dec = _decrypt_entry(bytes(raw[offset : offset + size]))
        # Read the offset pointer at 0x58
        if len(dec) < 0x5C:
            continue
        ptr = struct.unpack_from("<i", dec, 0x58)[0]
        steam_off = ptr + 0x6F
        if steam_off + 4 > len(dec):
            continue
        current = struct.unpack_from("<i", dec, steam_off)[0]
        if current == old_steam32:
            dec[steam_off : steam_off + 4] = new_steam32_bytes
            raw[offset : offset + size] = _encrypt_entry(iv, dec)
            slots_patched += 1

    save_path.write_bytes(bytes(raw))
    return True, (
        f"Patched USER_DATA_010 + {slots_patched} character slot(s)\n"
        f"Old SteamID: {old_steam64} (Steam32: {old_steam32})\n"
        f"New SteamID: {new_steam64} (Steam32: {new_steam32})"
    )
