"""
DS3 BND4 container parser.

File layout:
  [0x0000:0x0004]  Magic "BND4"
  [0x0004:0x000C]  Header fields
  [0x000C:0x0010]  Entry count u32 LE (typically 11: slots 0-9 + global slot 10)
  [0x0040:0x0040+N*32]  Entry table, 32 bytes per entry (N = entry count)

Entry table row (32 bytes at ENTRIES_START + index * ENTRY_STRIDE):
  +0x00  u32  Flags: 0x50
  +0x04  u32  0xFFFFFFFF
  +0x08  u32  Total entry size in file (MD5 + IV + PKCS7-padded ciphertext)
  +0x0C  u32  Unknown
  +0x10  u32  Absolute data offset in file
  +0x14  u32  Name string offset in file
  +0x18  u32  Footer length
  +0x1C  u32  Padding

Per-entry data layout at data_offset:
  [0x00:0x10]  MD5 checksum of (IV + ciphertext)
  [0x10:0x20]  AES-CBC IV (16 bytes)
  [0x20:end]   AES-128-CBC PKCS7-padded ciphertext

On save: re-encrypt with the original IV, compute new MD5 = md5(original_iv + new_ciphertext),
write [new_md5][original_iv][new_ciphertext] at the same offset. Total size stays constant
because PKCS7 padding on same-length plaintext produces same-length ciphertext.

AES-128-CBC key (all DS3 saves, PC and Seamless Coop):
  FD 46 4D 69 5E 69 A3 9A 10 E3 19 A7 AC E8 B7 FA

Discovered by Atvaark, published in DS3SaveUnpacker by tremwil.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_DS3_KEY = bytes.fromhex("FD464D695E69A39A10E319A7ACE8B7FA")

_BND4_MAGIC = b"BND4"
_ENTRIES_START = 0x40
_ENTRY_STRIDE = 32
_MD5_SIZE = 16
_IV_SIZE = 16
_HEADER_SIZE = _MD5_SIZE + _IV_SIZE  # 32 bytes before ciphertext


@dataclass
class _BND4Entry:
    index: int
    size: int  # full entry blob size (MD5 + IV + ciphertext)
    offset: int  # absolute file offset of the entry blob
    iv: bytes = field(repr=False)
    plaintext: bytearray = field(repr=False)


def _read_entry_header(raw: bytes, index: int) -> tuple[int, int]:
    """Return (size, data_offset) for the entry at index."""
    pos = _ENTRIES_START + index * _ENTRY_STRIDE
    size = struct.unpack_from("<I", raw, pos + 8)[0]
    data_offset = struct.unpack_from("<I", raw, pos + 16)[0]
    return size, data_offset


def _decrypt(iv: bytes, ciphertext: bytes) -> bytearray:
    cipher = Cipher(algorithms.AES(_DS3_KEY), modes.CBC(iv))
    dec = cipher.decryptor()
    padded = bytearray(dec.update(ciphertext) + dec.finalize())
    # Strip PKCS7 padding
    pad_len = padded[-1]
    if 1 <= pad_len <= 16:
        return padded[:-pad_len]
    return padded


def _encrypt(iv: bytes, plaintext: bytearray) -> bytes:
    # Add PKCS7 padding to next 16-byte boundary
    pad_len = 16 - (len(plaintext) % 16)
    padded = bytes(plaintext) + bytes([pad_len] * pad_len)
    cipher = Cipher(algorithms.AES(_DS3_KEY), modes.CBC(iv))
    enc = cipher.encryptor()
    return enc.update(padded) + enc.finalize()


def _md5(data: bytes) -> bytes:
    return hashlib.md5(data).digest()


class DS3Parser:
    """
    BND4 container for a DS3 save file.

    Decrypts all entries on load; re-encrypts on save.
    Entry slots 0-9 are character slots; slot 10 is the global data entry.
    """

    CHARACTER_SLOTS = 10
    TOTAL_SLOTS = 11

    def __init__(self, raw: bytearray, entries: list[_BND4Entry]) -> None:
        self._raw = raw
        self._entries = entries

    @classmethod
    def from_file(cls, path: str | Path) -> DS3Parser:
        raw = bytearray(Path(path).read_bytes())
        if raw[:4] != _BND4_MAGIC:
            raise ValueError("Not a BND4 file")

        entry_count = struct.unpack_from("<I", raw, 0x0C)[0]
        if entry_count < cls.TOTAL_SLOTS:
            raise ValueError(
                f"Expected at least {cls.TOTAL_SLOTS} entries, found {entry_count}"
            )

        entries = []
        for i in range(cls.TOTAL_SLOTS):
            size, offset = _read_entry_header(raw, i)
            blob = bytes(raw[offset : offset + size])
            iv = blob[_MD5_SIZE : _MD5_SIZE + _IV_SIZE]
            ciphertext = blob[_HEADER_SIZE:]
            plaintext = _decrypt(iv, ciphertext)
            entries.append(_BND4Entry(i, size, offset, iv, plaintext))

        return cls(raw, entries)

    def get_slot(self, index: int) -> bytearray:
        """Return the decrypted plaintext for the given slot (0-10)."""
        return self._entries[index].plaintext

    def set_slot(self, index: int, data: bytearray) -> None:
        """Replace the decrypted plaintext for the given slot."""
        self._entries[index].plaintext = data

    def save_to_file(self, path: str | Path) -> None:
        """Re-encrypt all modified slots and write the file."""
        out = bytearray(self._raw)
        for entry in self._entries:
            ciphertext = _encrypt(entry.iv, entry.plaintext)
            new_md5 = _md5(entry.iv + ciphertext)
            blob = new_md5 + entry.iv + ciphertext
            if len(blob) != entry.size:
                raise RuntimeError(
                    f"Slot {entry.index}: re-encrypted size {len(blob)} != "
                    f"original {entry.size}. Plaintext must not change in length."
                )
            out[entry.offset : entry.offset + entry.size] = blob
        Path(path).write_bytes(out)

    def get_slot_plaintext_size(self, index: int) -> int:
        return len(self._entries[index].plaintext)
