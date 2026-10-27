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

AES-128-CBC key:
  FD 46 4D 69 5E 69 A3 9A 10 E3 19 A7 AC E8 B7 FA
Published in DS3SaveUnpacker by tremwil.

PlayStation 4 (decrypted export): one unencrypted file per entry, named
userdata0000-userdata0009 for the character slots and userdata0010 for the
global entry. Each file is the PC plaintext without its leading u32 size
field, so DS3PSParser rebuilds that field and serves entries in the PC
layout. Entries whose file is missing are unavailable (get_slot returns
None), which allows opening a single slot file on its own.
"""

from __future__ import annotations

import hashlib
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

from er_save_manager import aes_cbc
from er_save_manager.own_writes import atomic_write

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
    padded = bytearray(aes_cbc.decrypt(_DS3_KEY, iv, ciphertext))
    # Strip PKCS7 padding
    pad_len = padded[-1]
    if 1 <= pad_len <= 16:
        return padded[:-pad_len]
    return padded


def _encrypt(iv: bytes, plaintext: bytearray) -> bytes:
    # Add PKCS7 padding to next 16-byte boundary
    pad_len = 16 - (len(plaintext) % 16)
    padded = bytes(plaintext) + bytes([pad_len] * pad_len)
    return aes_cbc.encrypt(_DS3_KEY, iv, padded)


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
    is_ps = False

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

    def has_slot(self, index: int) -> bool:
        return 0 <= index < self.TOTAL_SLOTS

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
        atomic_write(path, out)

    def get_slot_plaintext_size(self, index: int) -> int:
        return len(self._entries[index].plaintext)


# --- PlayStation 4 -----------------------------------------------------------

_PS_NAME = re.compile(r"userdata(\d{4})", re.IGNORECASE)
_PS_SLOT_SIZE = 0xC0000
_PS_GLOBAL_SIZE = 0x60000


def _ps_index(path: Path) -> int | None:
    """Entry index encoded in a PS userdata file name, or None."""
    m = _PS_NAME.fullmatch(path.name)
    if m is None:
        return None
    index = int(m.group(1))
    return index if index < DS3Parser.TOTAL_SLOTS else None


def _ps_expected_size(index: int) -> int:
    return _PS_GLOBAL_SIZE if index == DS3Parser.CHARACTER_SLOTS else _PS_SLOT_SIZE


def is_ps_userdata(path: str | Path) -> bool:
    """True for a DS3 PS4 userdataNNNN file of the size its index requires."""
    path = Path(path)
    index = _ps_index(path)
    if index is None:
        return False
    try:
        return path.stat().st_size == _ps_expected_size(index)
    except OSError:
        return False


def ps_folder_files(path: str | Path) -> dict[int, Path]:
    """Entry index -> file for every valid userdata file next to path."""
    folder = Path(path).parent
    files = {}
    try:
        children = list(folder.iterdir())
    except OSError:
        return files
    for child in children:
        index = _ps_index(child)
        if index is not None and index not in files and is_ps_userdata(child):
            files[index] = child
    return files


def save_identity(path: str | Path) -> Path:
    """Path that identifies the save a file belongs to: the folder for a PS
    userdata file, the file itself otherwise."""
    path = Path(path).resolve()
    return path.parent if is_ps_userdata(path) else path


class DS3PSParser:
    """
    PS4 userdata folder for a DS3 save, entries in the PC plaintext layout.

    Only files whose content changed are written back.
    """

    CHARACTER_SLOTS = DS3Parser.CHARACTER_SLOTS
    TOTAL_SLOTS = DS3Parser.TOTAL_SLOTS
    is_ps = True

    def __init__(self, entries: list[bytearray | None], names: list[str]) -> None:
        self._entries = entries
        self._names = names
        self._written = [bytes(e) if e is not None else None for e in entries]

    @classmethod
    def from_file(cls, path: str | Path) -> DS3PSParser:
        path = Path(path)
        if not is_ps_userdata(path):
            raise ValueError(f"{path.name} is not a DS3 PS4 userdata file")
        files = ps_folder_files(path)
        entries: list[bytearray | None] = []
        names: list[str] = []
        for i in range(cls.TOTAL_SLOTS):
            file = files.get(i)
            if file is None:
                entries.append(None)
                names.append(f"userdata{i:04d}")
                continue
            body = file.read_bytes()
            entries.append(bytearray(struct.pack("<I", len(body)) + body))
            names.append(file.name)
        return cls(entries, names)

    def has_slot(self, index: int) -> bool:
        return 0 <= index < self.TOTAL_SLOTS and self._entries[index] is not None

    def file_name(self, index: int) -> str:
        return self._names[index]

    def get_slot(self, index: int) -> bytearray | None:
        """Return the PC-layout plaintext for the given slot (0-10), or None
        when its file was not loaded."""
        return self._entries[index]

    def set_slot(self, index: int, data: bytearray) -> None:
        if self._entries[index] is None:
            raise ValueError(f"No {self._names[index]} file was loaded")
        self._entries[index] = data

    def get_slot_plaintext_size(self, index: int) -> int:
        entry = self._entries[index]
        return len(entry) if entry is not None else _ps_expected_size(index) + 4

    def save_to_file(self, path: str | Path) -> None:
        """Write every changed entry to its userdata file in path's folder."""
        folder = Path(path).parent
        for i, entry in enumerate(self._entries):
            if entry is None or bytes(entry) == self._written[i]:
                continue
            expected = _ps_expected_size(i)
            if len(entry) != expected + 4:
                raise RuntimeError(
                    f"{self._names[i]}: entry size changed. Plaintext must not "
                    "change in length."
                )
            atomic_write(folder / self._names[i], entry[4:])
            self._written[i] = bytes(entry)


def load_parser(path: str | Path) -> DS3Parser | DS3PSParser:
    """Open a PC .sl2/.co2 or a PS4 userdata file."""
    if is_ps_userdata(path):
        return DS3PSParser.from_file(path)
    return DS3Parser.from_file(path)
