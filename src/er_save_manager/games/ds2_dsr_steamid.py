"""
SteamID patcher for Dark Souls II: SotFS and Dark Souls: Remastered save files.

Both use the same BND4 entry format:
  [16 bytes MD5 of (IV + encrypted payload)]
  [16 bytes IV]
  [AES-128-CBC encrypted payload]

DS2 stores the owning account in decrypted entry 0 at +0x39 as the Steam64
in 16 lowercase ASCII hex digits plus a NUL, the same string as the save
folder name. It is the only copy in the file. DSR saves hold no SteamID; the
account is identified by the save folder name.

Keys:
  DS2 SotFS: 59 9F 9B 69 96 40 A5 52 36 EE 2D 70 83 5E C7 44
  DSR:       01 23 45 67 89 AB CD EF FE DC BA 98 76 54 32 10

"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from er_save_manager.own_writes import record_write

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

_OWNER_ENTRY = 0
_OWNER_OFFSET = 0x39
_OWNER_LEN = 16


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


def _read_owner(dec: bytes) -> int | None:
    """Parse the owner SteamID string, or None if it is not a valid Steam64."""
    field = bytes(dec[_OWNER_OFFSET : _OWNER_OFFSET + _OWNER_LEN + 1])
    if len(field) != _OWNER_LEN + 1 or field[-1] != 0:
        return None
    try:
        value = int(field[:-1].decode("ascii"), 16)
    except ValueError:
        return None
    if not _STEAM64_BASE <= value <= _STEAM64_MAX:
        return None
    return value


def detect_steamid(save_path: Path, game_key: str) -> int | None:
    """Return the owner SteamID stored in entry 0, or None."""
    try:
        key = _key_for(game_key)
        raw = save_path.read_bytes()
        if raw[:4] != _BND4_MAGIC:
            return None
        size, offset = _read_entry(raw, _OWNER_ENTRY)
        _, _, dec = _decrypt(raw[offset : offset + size], key)
        return _read_owner(dec)
    except Exception:
        return None


def patch_steamid(save_path: Path, new_steam64: int, game_key: str) -> tuple[bool, str]:
    """
    Rewrite the owner SteamID in entry 0, re-encrypt it with its IV and
    recompute its MD5. Writes in-place.
    """
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher  # noqa: F401
    except ImportError:
        return False, "cryptography package required. Run: uv add cryptography"

    try:
        key = _key_for(game_key)
    except ValueError as e:
        return False, str(e)

    if not _STEAM64_BASE <= new_steam64 <= _STEAM64_MAX:
        return False, f"Not a valid Steam64 ID: {new_steam64}"

    try:
        raw = bytearray(save_path.read_bytes())
    except OSError as e:
        return False, f"Could not read file: {e}"

    if raw[:4] != _BND4_MAGIC:
        return False, "Not a valid BND4/SL2 file"

    size, offset = _read_entry(raw, _OWNER_ENTRY)
    _, iv, dec = _decrypt(bytes(raw[offset : offset + size]), key)
    old_steam64 = _read_owner(dec)
    if old_steam64 is None:
        return False, "No SteamID found in the save header. The file may be damaged."
    if old_steam64 == new_steam64:
        return False, "New SteamID is the same as the current one"

    dec[_OWNER_OFFSET : _OWNER_OFFSET + _OWNER_LEN] = f"{new_steam64:016x}".encode(
        "ascii"
    )
    raw[offset : offset + size] = _encrypt(iv, dec, key)

    tmp_path = save_path.with_suffix(save_path.suffix + ".tmp")
    tmp_path.write_bytes(bytes(raw))
    tmp_path.replace(save_path)
    record_write(save_path)
    return True, f"Old SteamID: {old_steam64}\nNew SteamID: {new_steam64}"
