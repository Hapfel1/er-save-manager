"""
PlayStation 4 userdata exports of the FromSoftware games.

A decrypted PS4 save folder holds one file per save entry, named
userdata0000, userdata0001, ... (the console's backupNNNN files next to
them are the game's own previous copies and are never opened). The name
is the same in every game; the entry sizes tell the games apart:

  Game                    Entries  Sizes
  Dark Souls III          0-10     0-9 0xC0000, 10 0x60000
  Dark Souls Remastered   0-10     0-9 0x60030, 10 0x160040
  Dark Souls II SotFS     0-22     0 0x176C, 1-10 0x1B2BC, 11-20 0x7A8A8,
                                   21 0x200000, 22 0x33B0
"""

from __future__ import annotations

import re
from pathlib import Path

_NAME = re.compile(r"userdata(\d{4})", re.IGNORECASE)

ENTRY_SIZES: dict[str, tuple[int, ...]] = {
    "dark_souls_3": (0xC0000,) * 10 + (0x60000,),
    "dark_souls_remastered": (0x60030,) * 10 + (0x160040,),
    "dark_souls_2": (0x176C,) + (0x1B2BC,) * 10 + (0x7A8A8,) * 10 + (0x200000, 0x33B0),
}


def entry_index(path: str | Path) -> int | None:
    """Entry index encoded in a userdataNNNN file name, or None."""
    m = _NAME.fullmatch(Path(path).name)
    return int(m.group(1)) if m else None


def _size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def userdata_game(path: str | Path) -> str | None:
    """Game key of a PS4 userdata file whose size matches its index, or None."""
    path = Path(path)
    index = entry_index(path)
    if index is None:
        return None
    size = _size(path)
    for game, sizes in ENTRY_SIZES.items():
        if index < len(sizes) and sizes[index] == size:
            return game
    return None


def is_ps_userdata(path: str | Path, game: str | None = None) -> bool:
    """True for a PS4 userdata file of game (any supported game when None)."""
    found = userdata_game(path)
    return found is not None and (game is None or found == game)


def folder_files(path: str | Path, game: str | None = None) -> dict[int, Path]:
    """Entry index -> file for every userdata file of the same game next to
    path. game defaults to the game of path itself."""
    path = Path(path)
    game = game or userdata_game(path)
    files: dict[int, Path] = {}
    if game is None:
        return files
    try:
        children = list(path.parent.iterdir())
    except OSError:
        return files
    for child in children:
        index = entry_index(child)
        if index is not None and index not in files and is_ps_userdata(child, game):
            files[index] = child
    return files


class IncompleteFolderError(ValueError):
    """A PS4 save folder lacks userdata files the game's parser needs."""


def require_folder(path: str | Path, game: str) -> list[Path]:
    """Every entry file of game in path's folder, in index order. Raises
    IncompleteFolderError naming the files that are missing or have a size
    the entry cannot have."""
    files = folder_files(path, game)
    sizes = ENTRY_SIZES[game]
    present = {c.name.lower() for c in _children(Path(path).parent)}
    missing, wrong = [], []
    for i in range(len(sizes)):
        if i in files:
            continue
        name = f"userdata{i:04d}"
        (wrong if name in present else missing).append(name)
    if not missing and not wrong:
        return [files[i] for i in range(len(sizes))]
    lines = ["The PS4 save folder is incomplete. All files are needed:"]
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
    """Path that identifies the save a file belongs to: the folder for a PS4
    userdata file, the file itself otherwise."""
    path = Path(path).resolve()
    return path.parent if is_ps_userdata(path) else path
