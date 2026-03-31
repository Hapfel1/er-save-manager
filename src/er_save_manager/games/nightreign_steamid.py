"""
SteamID patcher for Elden Ring: Nightreign save files (NR0000.sl2 / NR0000.co2).

Nightreign saves use the same BND4 container as DS2/DS3/ER but with AES-CBC
encryption on every entry. The AES key was found by TKGP and published in
EonaCat's NightReign Save Transfer tool (MIT license).

Patching process:
  1. Decrypt all entries (AES-128-CBC, fixed key, per-entry IV prepended to data).
  2. In decrypted entry 10 (global data): overwrite 8 bytes at offset 0x8 with new SteamID.
  3. In all other entries: scan for old SteamID LE bytes and replace every occurrence.
  4. Recalculate each entry's checksum: MD5(decrypted[4 : len-28]) written at len-28.
  5. Re-encrypt with same IV and write back.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path

# AES-128-CBC key for Nightreign save files (credit: TKGP / EonaCat)
_NR_KEY = bytes(
    [
        0x18,
        0xF6,
        0x32,
        0x66,
        0x05,
        0xBD,
        0x17,
        0x8A,
        0x55,
        0x24,
        0x52,
        0x3A,
        0xC0,
        0xA0,
        0xC6,
        0x09,
    ]
)

_IV_SIZE = 16
_CHECKSUM_TAIL = 28  # checksum occupies last 28 bytes; MD5 (16 bytes) at offset len-28
_BND4_MAGIC = b"BND4"
_ENTRY_STRIDE = 32
_ENTRIES_START = 64  # 0x40


@dataclass
class _NrEntry:
    index: int
    size: int
    data_offset: int
    iv: bytes
    decrypted: bytearray


def _decrypt_entry(raw: bytes, offset: int, size: int) -> tuple[bytes, bytearray]:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    enc = raw[offset : offset + size]
    iv = enc[:_IV_SIZE]
    payload = enc[_IV_SIZE:]
    cipher = Cipher(algorithms.AES(_NR_KEY), modes.CBC(iv), backend=default_backend())
    dec = cipher.decryptor()
    return iv, bytearray(dec.update(payload) + dec.finalize())


def _encrypt_entry(iv: bytes, decrypted: bytearray) -> bytes:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    cipher = Cipher(algorithms.AES(_NR_KEY), modes.CBC(iv), backend=default_backend())
    enc = cipher.encryptor()
    return iv + enc.update(bytes(decrypted)) + enc.finalize()


def _patch_checksum(dec: bytearray) -> None:
    """Recalculate and write the MD5 checksum in-place."""
    checksum_offset = len(dec) - _CHECKSUM_TAIL
    digest = hashlib.md5(dec[4:checksum_offset]).digest()
    dec[checksum_offset : checksum_offset + 16] = digest


def detect_steamid_nr(save_path: Path) -> int | None:
    """
    Detect the SteamID from a Nightreign save file by decrypting entry 10
    and reading the uint64 at offset 0x8.
    Returns None on failure.
    """
    try:
        raw = save_path.read_bytes()
        if raw[:4] != _BND4_MAGIC:
            return None

        file_count = struct.unpack_from("<I", raw, 0x0C)[0]
        if file_count < 11:
            return None

        pos = _ENTRIES_START + 10 * _ENTRY_STRIDE
        size = struct.unpack_from("<I", raw, pos + 8)[0]
        data_offset = struct.unpack_from("<I", raw, pos + 16)[0]

        _, dec = _decrypt_entry(raw, data_offset, size)
        steamid = struct.unpack_from("<Q", dec, 0x8)[0]

        STEAM64_BASE = 0x0110000100000000
        STEAM64_MAX = 0x01100001FFFFFFFF
        if STEAM64_BASE <= steamid <= STEAM64_MAX:
            return steamid
        return None
    except Exception:
        return None


def patch_steamid_nr(
    save_path: Path,
    new_steamid: int,
    old_steamid: int | None = None,
) -> tuple[bool, str]:
    """
    Patch the SteamID in a Nightreign save file.

    Returns (success, message).
    Writes the patched file in-place.
    """
    try:
        from cryptography.hazmat.primitives.ciphers import (
            Cipher,  # noqa: F401 - availability check
        )
    except ImportError:
        return (
            False,
            "cryptography package is required for Nightreign SteamID patching. Install it with: pip install cryptography",
        )

    try:
        raw = bytearray(save_path.read_bytes())
    except OSError as e:
        return False, f"Could not read file: {e}"

    if raw[:4] != _BND4_MAGIC:
        return False, "Not a valid BND4/SL2 file"

    file_count = struct.unpack_from("<I", raw, 0x0C)[0]
    if file_count < 11:
        return False, f"Expected at least 11 entries, found {file_count}"

    # Read entry table
    entries: list[_NrEntry] = []
    for i in range(file_count):
        pos = _ENTRIES_START + i * _ENTRY_STRIDE
        size = struct.unpack_from("<I", raw, pos + 8)[0]
        data_offset = struct.unpack_from("<I", raw, pos + 16)[0]
        iv, dec = _decrypt_entry(bytes(raw), data_offset, size)
        entries.append(
            _NrEntry(index=i, size=size, data_offset=data_offset, iv=iv, decrypted=dec)
        )

    # Detect old SteamID from entry 10 if not provided
    entry10 = entries[10]
    detected = struct.unpack_from("<Q", entry10.decrypted, 0x8)[0]
    if old_steamid is None:
        old_steamid = detected

    if old_steamid == new_steamid:
        return False, "New SteamID is the same as the current one"

    old_bytes = struct.pack("<Q", old_steamid)
    new_bytes = struct.pack("<Q", new_steamid)

    # Patch entry 10 at fixed offset 0x8
    entry10.decrypted[0x8:0x10] = new_bytes

    # Patch all other entries by scanning for old SteamID bytes
    total_replacements = 0
    for entry in entries:
        if entry.index == 10:
            continue
        dec = entry.decrypted
        i = 0
        while i <= len(dec) - 8:
            if dec[i : i + 8] == old_bytes:
                dec[i : i + 8] = new_bytes
                total_replacements += 1
                i += 8
            else:
                i += 1

    # Recalculate checksums and re-encrypt, writing back into raw
    for entry in entries:
        _patch_checksum(entry.decrypted)
        re_enc = _encrypt_entry(entry.iv, entry.decrypted)
        raw[entry.data_offset : entry.data_offset + entry.size] = re_enc

    save_path.write_bytes(bytes(raw))
    return (
        True,
        f"Patched entry 10 + {total_replacements} occurrence(s) in character slots. Old: {old_steamid}  New: {new_steamid}",
    )
