"""
Identify which game a save file belongs to from its header alone.

PC saves of every supported game are BND4 containers whose entry count and
first entry size are fixed per game:

  game                  entries  entry 0 size
  Elden Ring            12       0x280010
  Dark Souls III        12       0xC0030
  Nightreign            14       0x100030
  Dark Souls II SOTFS   23       0x1AB0
  Dark Souls Remastered 11       0x60030
  Armored Core VI       11       0xC0030
  Sekiro                12       0x100010

PlayStation exports are matched by magic (ER), exact length (NR, same
rule as the NR parser) or userdataNNNN name plus size (DS3, DSR, DS2).
Anything else returns None, so callers only reject a file that positively
matches a different game.

incomplete_reason() tells a cut-off or empty file from a whole one by the
container layout alone, before any game parser runs.
"""

from __future__ import annotations

import struct
from pathlib import Path

_BND4_SIGNATURES: dict[tuple[int, int], str] = {
    (12, 0x280010): "elden_ring",
    (12, 0xC0030): "dark_souls_3",
    (14, 0x100030): "nightreign",
    (23, 0x1AB0): "dark_souls_2",
    (11, 0x60030): "dark_souls_remastered",
    (11, 0xC0030): "armored_core_6",
    (12, 0x100010): "sekiro",
}

_ER_PS_MAGIC = bytes.fromhex("cb019c2c")
_NR_PS_SIZE = 0x12A00A0

# BND4 header: u32 entry count at 0xC, entry table at 0x40 with 0x20-byte
# records: entry size u64 at +0x8, data offset u32 at +0x10.
_ENTRY_COUNT_OFFSET = 0xC
_ENTRY_TABLE = 0x40
_ENTRY_STRIDE = 0x20
_ENTRY_SIZE_FIELD = 0x8
_ENTRY_DATA_OFFSET_FIELD = 0x10
_FIRST_ENTRY_SIZE_OFFSET = _ENTRY_TABLE + _ENTRY_SIZE_FIELD
# Larger than any supported game's entry count; a count above it is not a save.
_MAX_ENTRIES = 64

# ER PS export: 0x70-byte header, 10 slots of 0x280000, USER_DATA_10
# (0x60000) and USER_DATA_11 (0x240010), no checksums.
ER_PS_SIZE = 0x70 + 10 * 0x280000 + 0x60000 + 0x240010


# Games whose own saves are always recognized; checks against any other game
# (unknown signature) cannot tell a mismatch from its own file.
KNOWN_GAMES = frozenset(_BND4_SIGNATURES.values())


def bnd4_game(head: bytes) -> str | None:
    """Game key for a BND4 header (at least 0x48 bytes), None if unknown."""
    if head[:4] != b"BND4" or len(head) < _FIRST_ENTRY_SIZE_OFFSET + 8:
        return None
    count = struct.unpack_from("<I", head, _ENTRY_COUNT_OFFSET)[0]
    first = struct.unpack_from("<Q", head, _FIRST_ENTRY_SIZE_OFFSET)[0]
    return _BND4_SIGNATURES.get((count, first))


def _cut_entries(data: bytes, size: int) -> list[int]:
    """Indices of the BND4 entries that end past size. data holds the
    header and the whole entry table."""
    count = struct.unpack_from("<I", data, _ENTRY_COUNT_OFFSET)[0]
    cut = []
    for i in range(count):
        rec = _ENTRY_TABLE + i * _ENTRY_STRIDE
        entry_size = struct.unpack_from("<Q", data, rec + _ENTRY_SIZE_FIELD)[0]
        offset = struct.unpack_from("<I", data, rec + _ENTRY_DATA_OFFSET_FIELD)[0]
        if offset + entry_size > size:
            cut.append(i)
    return cut


def er_tail_cut(data: bytes, size: int) -> bool:
    """True for an Elden Ring BND4 where only the last entry (USER_DATA_11,
    regulation data) ends past the file end and starts inside it: every
    character slot and USER_DATA_10 are whole."""
    if bnd4_game(data) != "elden_ring" or len(data) < _ENTRY_TABLE:
        return False
    count = struct.unpack_from("<I", data, _ENTRY_COUNT_OFFSET)[0]
    if (
        not 0 < count <= _MAX_ENTRIES
        or len(data) < _ENTRY_TABLE + count * _ENTRY_STRIDE
    ):
        return False
    last = count - 1
    start = struct.unpack_from(
        "<I", data, _ENTRY_TABLE + last * _ENTRY_STRIDE + _ENTRY_DATA_OFFSET_FIELD
    )[0]
    return _cut_entries(data, size) == [last] and start < size


def bnd4_problem(data: bytes, size: int) -> str | None:
    """Why a BND4 file of the given size is cut off, None when every entry
    lies inside it or only an Elden Ring save's regulation entry is cut
    (er_tail_cut). data holds at least the header and entry table."""
    if len(data) < _ENTRY_TABLE:
        return f"BND4 header cut off at {size:#x} bytes"
    count = struct.unpack_from("<I", data, _ENTRY_COUNT_OFFSET)[0]
    if not 0 < count <= _MAX_ENTRIES:
        return f"BND4 entry count {count}"
    table_end = _ENTRY_TABLE + count * _ENTRY_STRIDE
    if len(data) < table_end:
        return f"BND4 entry table ends at {table_end:#x}, file is {size:#x} bytes"
    cut = _cut_entries(data, size)
    if not cut or er_tail_cut(data, size):
        return None
    rec = _ENTRY_TABLE + cut[0] * _ENTRY_STRIDE
    end = (
        struct.unpack_from("<I", data, rec + _ENTRY_DATA_OFFSET_FIELD)[0]
        + struct.unpack_from("<Q", data, rec + _ENTRY_SIZE_FIELD)[0]
    )
    return f"BND4 entry {cut[0]} ends at {end:#x}, file is {size:#x} bytes"


def incomplete_reason(path: str | Path) -> str | None:
    """Why the file is empty or cut off, None when it looks whole or its
    format is unknown (left to the game parser)."""
    path = Path(path)
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            head = f.read(_ENTRY_TABLE + _MAX_ENTRIES * _ENTRY_STRIDE)
    except OSError as exc:
        return f"cannot read: {exc}"
    if size == 0:
        return "empty file"
    if head[:4] == b"BND4":
        return bnd4_problem(head, size)
    if head[:4] == _ER_PS_MAGIC and size < ER_PS_SIZE:
        return f"PS save is {size:#x} bytes, needs {ER_PS_SIZE:#x}"
    return None


def tail_cut_reason(path: str | Path) -> str | None:
    """Description of a cut regulation entry (er_tail_cut), None otherwise."""
    path = Path(path)
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            head = f.read(_ENTRY_TABLE + _MAX_ENTRIES * _ENTRY_STRIDE)
    except OSError:
        return None
    if head[:4] != b"BND4" or not er_tail_cut(head, size):
        return None
    count = struct.unpack_from("<I", head, _ENTRY_COUNT_OFFSET)[0]
    rec = _ENTRY_TABLE + (count - 1) * _ENTRY_STRIDE
    end = (
        struct.unpack_from("<I", head, rec + _ENTRY_DATA_OFFSET_FIELD)[0]
        + struct.unpack_from("<Q", head, rec + _ENTRY_SIZE_FIELD)[0]
    )
    return f"{end - size:#x} bytes of the regulation data are missing"


def identify_game(path: str | Path) -> str | None:
    """Return the GameProfile key of the game that wrote path, or None if unknown."""
    path = Path(path)
    try:
        with path.open("rb") as f:
            head = f.read(_FIRST_ENTRY_SIZE_OFFSET + 8)
        size = path.stat().st_size
    except OSError:
        return None

    from er_save_manager.games.ps_userdata import userdata_game

    magic = head[:4]
    if magic == b"BND4" and len(head) >= _FIRST_ENTRY_SIZE_OFFSET + 8:
        return bnd4_game(head)
    if magic == _ER_PS_MAGIC:
        return "elden_ring"
    if size == _NR_PS_SIZE:
        return "nightreign"
    return userdata_game(path)
