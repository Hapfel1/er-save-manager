"""
Console userdata exports of the FromSoftware games: one file per save entry.

A decrypted PS4 save folder holds files named userdata0000, userdata0001,
... (the console's backupNNNN files next to them are the game's own previous
copies and are never opened). The name is the same in every game; the entry
sizes tell the games apart:

  Game                    Entries  Sizes
  Dark Souls III          0-10     0-9 0xC0000, 10 0x60000
  Dark Souls Remastered   0-10     0-9 0x60030, 10 0x160040
  Dark Souls II SotFS     0-22     0 0x176C, 1-10 0x1B2BC, 11-20 0x7A8A8,
                                   21 0x200000, 22 0x33B0

An Elden Ring Switch 2 save is the game's own files ER_____0000_userdata0000
to 0011: the entries of a PlayStation memory.dat (no header, no checksums),
one per file.

  Elden Ring (Switch 2)   0-11     0-9 0x280000, 10 0x60000, 11 0x240010
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

PS4 = "ps4"
SWITCH2 = "switch2"

_NAMES: dict[str, re.Pattern[str]] = {
    PS4: re.compile(r"userdata(\d{4})", re.IGNORECASE),
    SWITCH2: re.compile(r"ER_____0000_userdata(\d{4})", re.IGNORECASE),
}
_FILE_NAME = {PS4: "userdata{:04d}", SWITCH2: "ER_____0000_userdata{:04d}"}
_FOLDER_LABEL = {PS4: "PS4", SWITCH2: "Switch 2"}

ENTRY_SIZES: dict[str, tuple[int, ...]] = {
    "dark_souls_3": (0xC0000,) * 10 + (0x60000,),
    "dark_souls_remastered": (0x60030,) * 10 + (0x160040,),
    "dark_souls_2": (0x176C,) + (0x1B2BC,) * 10 + (0x7A8A8,) * 10 + (0x200000, 0x33B0),
}

SWITCH2_ENTRY_SIZES: dict[str, tuple[int, ...]] = {
    "elden_ring": (0x280000,) * 10 + (0x60000, 0x240010),
}

_SIZES = {PS4: ENTRY_SIZES, SWITCH2: SWITCH2_ENTRY_SIZES}


def entry_sizes(game: str, platform: str = PS4) -> tuple[int, ...]:
    return _SIZES[platform][game]


def entry_file_name(index: int, platform: str = PS4) -> str:
    return _FILE_NAME[platform].format(index)


def entry_index(path: str | Path, platform: str = PS4) -> int | None:
    """Entry index encoded in a userdata file name of platform, or None."""
    m = _NAMES[platform].fullmatch(Path(path).name)
    return int(m.group(1)) if m else None


def _size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def userdata_kind(path: str | Path) -> tuple[str, str] | None:
    """(game key, platform) of a userdata file whose size matches its index,
    or None."""
    path = Path(path)
    size = None
    for platform, names in _NAMES.items():
        m = names.fullmatch(path.name)
        if not m:
            continue
        index = int(m.group(1))
        if size is None:
            size = _size(path)
        for game, sizes in _SIZES[platform].items():
            if index < len(sizes) and sizes[index] == size:
                return game, platform
    return None


def userdata_game(path: str | Path) -> str | None:
    """Game key of a console userdata file (PS4 or Switch 2), or None."""
    kind = userdata_kind(path)
    return kind[0] if kind else None


def is_ps_userdata(path: str | Path, game: str | None = None) -> bool:
    """True for a PS4 userdata file of game (any supported game when None)."""
    kind = userdata_kind(path)
    return kind is not None and kind[1] == PS4 and (game is None or kind[0] == game)


def is_switch2_userdata(path: str | Path) -> bool:
    """True for a file of an Elden Ring Switch 2 save."""
    kind = userdata_kind(path)
    return kind is not None and kind[1] == SWITCH2


def is_userdata_file(path: str | Path) -> bool:
    """True for any console userdata file (PS4 or Switch 2)."""
    return userdata_kind(path) is not None


def folder_files(
    path: str | Path, game: str | None = None, platform: str | None = None
) -> dict[int, Path]:
    """Entry index -> file for every userdata file of the same game and
    platform next to path. game and platform default to those of path."""
    path = Path(path)
    kind = userdata_kind(path)
    game = game or (kind[0] if kind else None)
    platform = platform or (kind[1] if kind else PS4)
    files: dict[int, Path] = {}
    if game is None or game not in _SIZES[platform]:
        return files
    sizes = _SIZES[platform][game]
    for child in _children(path.parent):
        index = entry_index(child, platform)
        if (
            index is not None
            and index not in files
            and index < len(sizes)
            and _size(child) == sizes[index]
        ):
            files[index] = child
    return files


class IncompleteFolderError(ValueError):
    """A console save folder lacks userdata files the game's parser needs."""


def require_folder(path: str | Path, game: str, platform: str = PS4) -> list[Path]:
    """Every entry file of game in path's folder, in index order. Raises
    IncompleteFolderError naming the files that are missing or have a size
    the entry cannot have."""
    files = folder_files(path, game, platform)
    sizes = _SIZES[platform][game]
    present = {c.name.lower() for c in _children(Path(path).parent)}
    missing, wrong = [], []
    for i in range(len(sizes)):
        if i in files:
            continue
        name = entry_file_name(i, platform)
        (wrong if name.lower() in present else missing).append(name)
    if not missing and not wrong:
        return [files[i] for i in range(len(sizes))]
    lines = [
        f"The {_FOLDER_LABEL[platform]} save folder is incomplete. "
        "All files are needed:"
    ]
    if missing:
        lines.append(f"Missing: {', '.join(missing)}")
    if wrong:
        lines.append(
            f"Wrong size (cut off, damaged or from another game): {', '.join(wrong)}"
        )
    raise IncompleteFolderError("\n".join(lines))


def _children(folder: Path) -> list[Path]:
    try:
        return list(folder.iterdir())
    except OSError:
        return []


def save_identity(path: str | Path) -> Path:
    """Path that identifies the save a file belongs to: the folder for a
    console userdata file, the file itself otherwise."""
    path = Path(path).resolve()
    return path.parent if is_userdata_file(path) else path


def memory_dat_header(magic: bytes, entry_count: int) -> bytes:
    """Header of a PlayStation memory.dat (Elden Ring, Nightreign): magic,
    u32 0, 0x7F7F7F7F, u32 0, then (u32 n, 0x7F7F7F7F) for n = 7 to
    6 + entry_count. The entries follow it back to back."""
    pad = b"\x7f" * 4
    return (
        magic
        + struct.pack("<I4sI", 0, pad, 0)
        + b"".join(struct.pack("<I4s", n, pad) for n in range(7, 7 + entry_count))
    )
