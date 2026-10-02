"""Registry of save files written by this process.

The external-modification watcher compares a file's current stat against the
stat recorded right after this process last wrote it. A match means the file
still holds this process's own write; anything else (the game saving, another
tool) changes mtime or size and is reported.
"""

from __future__ import annotations

import os
from pathlib import Path

_last_write: dict[str, tuple[int, int]] = {}


def _key(path: str | Path) -> str:
    return os.path.normcase(os.path.realpath(path))


def _signature(path: str | Path) -> tuple[int, int]:
    st = os.stat(path)
    return st.st_mtime_ns, st.st_size


def record_write(path: str | Path) -> None:
    """Remember the stat of a file this process just finished writing."""
    try:
        _last_write[_key(path)] = _signature(path)
    except OSError:
        pass


def is_own_write(path: str | Path) -> bool:
    """True when the file is unchanged since this process last wrote it."""
    try:
        return _last_write.get(_key(path)) == _signature(path)
    except OSError:
        return False
