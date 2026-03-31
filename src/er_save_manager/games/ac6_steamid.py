"""
SteamID patcher for Armored Core VI save files (AC60000.sl2).

AC6 uses the same AES-128-CBC BND4 encryption pattern as Nightreign but:
- Different AES key
- SteamID is not at a fixed offset; it is located by scanning each decrypted
  entry for a section header containing the ASCII string "Steam", where the
  section's data field is exactly 8 bytes (uint64 SteamID LE).

Reference: Nordgaren/ArmoredCore6SaveTransferTool
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

_AC6_KEY = bytes(
    [
        0xB1,
        0x56,
        0x87,
        0x9F,
        0x13,
        0x48,
        0x97,
        0x98,
        0x70,
        0x05,
        0xC4,
        0x87,
        0x00,
        0xAE,
        0xF8,
        0x79,
    ]
)

_IV_SIZE = 16
_SECTION_STRING_SIZE = 16  # section name is a null-padded 16-byte field
_SECTION_HEADER_SIZE = 32  # 16-byte name + 16 bytes of header metadata
_CHECKSUM_TAIL = 28  # MD5 (16) + padding (12) at end of decrypted data
_BND4_MAGIC = b"BND4"
_ENTRY_STRIDE = 32
_ENTRIES_START = 64


def _decrypt(raw_entry: bytes) -> tuple[bytes, bytearray]:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    iv = raw_entry[:_IV_SIZE]
    payload = raw_entry[_IV_SIZE:]
    cipher = Cipher(algorithms.AES(_AC6_KEY), modes.CBC(iv), backend=default_backend())
    dec = cipher.decryptor()
    return iv, bytearray(dec.update(payload) + dec.finalize())


def _encrypt(iv: bytes, decrypted: bytearray) -> bytes:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    cipher = Cipher(algorithms.AES(_AC6_KEY), modes.CBC(iv), backend=default_backend())
    enc = cipher.encryptor()
    return iv + enc.update(bytes(decrypted)) + enc.finalize()


def _patch_checksum(dec: bytearray) -> None:
    offset = len(dec) - _CHECKSUM_TAIL
    digest = hashlib.md5(dec[4:offset]).digest()
    dec[offset : offset + 16] = digest


def _find_steam_section(dec: bytearray) -> list[int]:
    """Return list of offsets where 'Steam' section with 8-byte data is found."""
    offsets = []
    i = 0
    while i < len(dec) - _SECTION_STRING_SIZE:
        # Section name must start with ASCII letter
        if not (0x41 <= dec[i] <= 0x5A or 0x61 <= dec[i] <= 0x7A):
            i += 1
            continue
        chunk = dec[i : i + _SECTION_STRING_SIZE]
        # Decode null-terminated name
        null = chunk.find(0)
        name = (
            chunk[:null].decode("utf-8", errors="ignore")
            if null != -1
            else chunk.decode("utf-8", errors="ignore")
        )
        if "Steam" in name:
            # Read data size at offset +16 within the section header
            size_offset = i + 16
            if size_offset + 4 <= len(dec):
                data_size = struct.unpack_from("<I", dec, size_offset)[0]
                if data_size == 8:
                    offsets.append(i)
                    i += _SECTION_HEADER_SIZE + data_size
                    continue
        i += 1
    return offsets


def detect_steamid_ac6(save_path: Path) -> int | None:
    """
    Detect SteamID from an AC6 save by decrypting entries and scanning for
    the 'Steam' section header. Returns None on failure.
    """
    try:
        raw = save_path.read_bytes()
        if raw[:4] != _BND4_MAGIC:
            return None
        file_count = struct.unpack_from("<I", raw, 0x0C)[0]
        for i in range(file_count):
            pos = _ENTRIES_START + i * _ENTRY_STRIDE
            size = struct.unpack_from("<I", raw, pos + 8)[0]
            data_offset = struct.unpack_from("<I", raw, pos + 16)[0]
            _, dec = _decrypt(raw[data_offset : data_offset + size])
            steam_offsets = _find_steam_section(dec)
            for off in steam_offsets:
                steamid = struct.unpack_from("<Q", dec, off + _SECTION_HEADER_SIZE)[0]
                STEAM64_BASE = 0x0110000100000000
                STEAM64_MAX = 0x01100001FFFFFFFF
                if STEAM64_BASE <= steamid <= STEAM64_MAX:
                    return steamid
    except Exception:
        pass
    return None


def patch_steamid_ac6(save_path: Path, new_steamid: int) -> tuple[bool, str]:
    """
    Patch the SteamID in an AC6 save. Writes in-place.
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
    new_bytes = struct.pack("<Q", new_steamid)
    entries_patched = 0
    old_steamid = None

    for i in range(file_count):
        pos = _ENTRIES_START + i * _ENTRY_STRIDE
        size = struct.unpack_from("<I", raw, pos + 8)[0]
        data_offset = struct.unpack_from("<I", raw, pos + 16)[0]

        iv, dec = _decrypt(bytes(raw[data_offset : data_offset + size]))
        steam_offsets = _find_steam_section(dec)
        if not steam_offsets:
            continue

        for off in steam_offsets:
            steam_data_offset = off + _SECTION_HEADER_SIZE
            if old_steamid is None:
                old_steamid = struct.unpack_from("<Q", dec, steam_data_offset)[0]
            dec[steam_data_offset : steam_data_offset + 8] = new_bytes

        _patch_checksum(dec)
        re_enc = _encrypt(iv, dec)
        raw[data_offset : data_offset + size] = re_enc
        entries_patched += 1

    if entries_patched == 0:
        return (
            False,
            "No 'Steam' section found in any entry. File may not be a valid AC6 save.",
        )

    save_path.write_bytes(bytes(raw))
    return True, (
        f"Patched {entries_patched} entry/entries\n"
        f"Old SteamID: {old_steamid}\n"
        f"New SteamID: {new_steamid}"
    )
