"""
SteamID patcher for Dark Souls II: SotFS and Dark Souls: Remastered save files.

Both use the same BND4 entry format:
  [16 bytes MD5 of (IV + encrypted payload)]
  [16 bytes IV]
  [AES-128-CBC encrypted payload]

SteamID is stored as Steam64 (uint64 LE) and found by byte-scanning the
decrypted entries - it is not at a fixed offset.

Keys:
  DS2 SotFS: 59 9F 9B 69 96 40 A5 52 36 EE 2D 70 83 5E C7 44
  DSR:       01 23 45 67 89 AB CD EF FE DC BA 98 76 54 32 10

"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

_KEYS = {
    "dark_souls_2": bytes.fromhex("599f9b699640a55236ee2d70835ec744"),
}

_IV_SIZE = 16
_MD5_SIZE = 16
_STEAM64_BASE = 0x0110000100000000
_STEAM64_MAX = 0x01100001FFFFFFFF
_BND4_MAGIC = b"BND4"
_ENTRY_STRIDE = 32
_ENTRIES_START = 64


def _key_for(game_key: str) -> bytes:
    k = _KEYS.get(game_key)
    if k is None:
        raise ValueError(f"No key for game: {game_key}")
    return k


def _decrypt(raw_entry: bytes, key: bytes) -> tuple[bytes, bytes, bytearray]:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    md5 = raw_entry[:_MD5_SIZE]
    iv = raw_entry[_MD5_SIZE : _MD5_SIZE + _IV_SIZE]
    payload = raw_entry[_MD5_SIZE + _IV_SIZE :]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    dec = cipher.decryptor()
    return md5, iv, bytearray(dec.update(payload) + dec.finalize())


def _encrypt(iv: bytes, decrypted: bytearray, key: bytes) -> bytes:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    enc = cipher.encryptor()
    encrypted = enc.update(bytes(decrypted)) + enc.finalize()
    md5 = hashlib.md5(iv + encrypted).digest()
    return md5 + iv + encrypted


def _read_entry(raw: bytes, index: int) -> tuple[int, int]:
    pos = _ENTRIES_START + index * _ENTRY_STRIDE
    size = struct.unpack_from("<I", raw, pos + 8)[0]
    offset = struct.unpack_from("<I", raw, pos + 16)[0]
    return size, offset


def _scan_steam64(dec: bytearray) -> list[int]:
    """Return list of offsets where a valid Steam64 is stored."""
    offsets = []
    i = 0
    end = len(dec) - 8
    while i <= end:
        val = struct.unpack_from("<Q", dec, i)[0]
        if _STEAM64_BASE <= val <= _STEAM64_MAX:
            offsets.append(i)
            i += 8
        else:
            i += 1
    return offsets


def detect_steamid(save_path: Path, game_key: str) -> int | None:
    """Decrypt all entries and return the first Steam64 found, or None."""
    try:
        key = _key_for(game_key)
        raw = save_path.read_bytes()
        if raw[:4] != _BND4_MAGIC:
            return None
        file_count = struct.unpack_from("<I", raw, 0x0C)[0]
        for i in range(file_count):
            size, offset = _read_entry(raw, i)
            _, _, dec = _decrypt(raw[offset : offset + size], key)
            hits = _scan_steam64(dec)
            if hits:
                return struct.unpack_from("<Q", dec, hits[0])[0]
    except Exception:
        pass
    return None


def patch_steamid(save_path: Path, new_steam64: int, game_key: str) -> tuple[bool, str]:
    """
    Patch all Steam64 occurrences in all decrypted entries.
    Recalculates checksums and re-encrypts. Writes in-place.
    """
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher  # noqa: F401
    except ImportError:
        return False, "cryptography package required. Run: uv add cryptography"

    try:
        key = _key_for(game_key)
    except ValueError as e:
        return False, str(e)

    try:
        raw = bytearray(save_path.read_bytes())
    except OSError as e:
        return False, f"Could not read file: {e}"

    if raw[:4] != _BND4_MAGIC:
        return False, "Not a valid BND4/SL2 file"

    file_count = struct.unpack_from("<I", raw, 0x0C)[0]
    new_bytes = struct.pack("<Q", new_steam64)
    old_steam64 = None
    entries_patched = 0
    total_replacements = 0

    for i in range(file_count):
        size, offset = _read_entry(raw, i)
        _, iv, dec = _decrypt(bytes(raw[offset : offset + size]), key)
        hits = _scan_steam64(dec)
        if not hits:
            continue
        if old_steam64 is None:
            old_steam64 = struct.unpack_from("<Q", dec, hits[0])[0]
        if old_steam64 == new_steam64:
            return False, "New SteamID is the same as the current one"
        for h in hits:
            dec[h : h + 8] = new_bytes
        total_replacements += len(hits)
        re_enc = _encrypt(iv, dec, key)
        raw[offset : offset + size] = re_enc
        entries_patched += 1

    if entries_patched == 0:
        return (
            False,
            "No Steam64 ID found in any entry. The save file may be empty or use an unexpected format.",
        )

    save_path.write_bytes(bytes(raw))
    return True, (
        f"Patched {total_replacements} occurrence(s) across {entries_patched} entry/entries\n"
        f"Old SteamID: {old_steam64}\n"
        f"New SteamID: {new_steam64}"
    )
