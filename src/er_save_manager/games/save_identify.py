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

PlayStation exports are matched by magic (ER), exact length (NR, same
rule as the NR parser) or userdataNNNN name plus size (DS3).
Anything else returns None, so callers only reject a file that positively
matches a different game.
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
}

_ER_PS_MAGIC = bytes.fromhex("cb019c2c")
_NR_PS_SIZE = 0x12A00A0

# BND4 header: u32 entry count at 0xC, entry table at 0x40, entry size u64 at +0x8.
_ENTRY_COUNT_OFFSET = 0xC
_FIRST_ENTRY_SIZE_OFFSET = 0x40 + 0x8


# Games whose own saves are always recognized; checks against any other game
# (Sekiro, unknown signature) cannot tell a mismatch from its own file.
KNOWN_GAMES = frozenset(_BND4_SIGNATURES.values())


def identify_game(path: str | Path) -> str | None:
    """Return the GameProfile key of the game that wrote path, or None if unknown."""
    path = Path(path)
    try:
        with path.open("rb") as f:
            head = f.read(_FIRST_ENTRY_SIZE_OFFSET + 8)
        size = path.stat().st_size
    except OSError:
        return None

    from er_save_manager.games.DS3.parser import is_ps_userdata

    magic = head[:4]
    if magic == b"BND4" and len(head) >= _FIRST_ENTRY_SIZE_OFFSET + 8:
        count = struct.unpack_from("<I", head, _ENTRY_COUNT_OFFSET)[0]
        first = struct.unpack_from("<Q", head, _FIRST_ENTRY_SIZE_OFFSET)[0]
        return _BND4_SIGNATURES.get((count, first))
    if magic == _ER_PS_MAGIC:
        return "elden_ring"
    if size == _NR_PS_SIZE:
        return "nightreign"
    if is_ps_userdata(path):
        return "dark_souls_3"
    return None
