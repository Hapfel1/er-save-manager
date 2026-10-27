"""Registry of save files written by this process.

The external-modification watcher compares a file's current stat against the
stat recorded right after this process last wrote it. A match means the file
still holds this process's own write; anything else (the game saving, another
tool) changes mtime or size and is reported.
"""

from __future__ import annotations

import contextlib
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
    with contextlib.suppress(OSError):
        _last_write[_key(path)] = _signature(path)


def is_own_write(path: str | Path) -> bool:
    """True when the file is unchanged since this process last wrote it."""
    try:
        return _last_write.get(_key(path)) == _signature(path)
    except OSError:
        return False


class SaveWriteError(OSError):
    """A save write was refused before anything was written; the message is
    shown to the user."""


def check_writable(path: str | Path) -> None:
    """Raise SaveWriteError when path or its folder cannot be written.

    os.replace swaps a read-only file out on Linux and fails on Windows, so a
    read-only save is refused here on every platform.
    """
    target = Path(path)
    folder = target.parent
    if not folder.is_dir():
        raise SaveWriteError(f"The folder of {target.name} no longer exists:\n{folder}")
    if target.exists() and not os.access(target, os.W_OK):
        raise SaveWriteError(
            f"{target.name} is read-only. Clear the read-only flag and try again."
        )
    if not os.access(folder, os.W_OK):
        raise SaveWriteError(
            f"The folder of {target.name} is read-only, so the save cannot be "
            f"replaced:\n{folder}"
        )


def atomic_write(path: str | Path, data: bytes | bytearray) -> None:
    """Write data to path through a temporary file in the same folder.

    The temporary file is flushed to disk and then replaces path, so path
    holds either the old or the new contents. The temporary file is removed
    when anything fails. Records the write for the external-change watcher.
    """
    target = Path(path)
    check_writable(target)
    tmp_path = target.with_name(f"{target.name}.tmp{os.getpid()}")
    try:
        with open(tmp_path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp_path.unlink()
        raise
    record_write(target)
