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


class SaveReadOnlyError(SaveWriteError):
    """The save or its folder is read-only."""


class SaveChangedError(SaveWriteError):
    """The loaded save changed on disk after it was read; writing the
    in-memory save back would drop that change."""


# (path key, signature when read) of the save the editor holds in memory
_loaded: tuple[str, tuple[int, int]] | None = None


def file_signature(path: str | Path) -> tuple[int, int] | None:
    """(mtime_ns, size) of path, None when it cannot be read."""
    try:
        return _signature(path)
    except OSError:
        return None


def record_load(path: str | Path | None, signature: tuple[int, int] | None) -> None:
    """Remember path as the loaded save, with the signature taken before it
    was read. None for either forgets the loaded save."""
    global _loaded
    if path is None or signature is None:
        _loaded = None
    else:
        _loaded = (_key(path), signature)


def check_loaded(path: str | Path) -> None:
    """Raise SaveChangedError when path is the loaded save and changed on
    disk since it was read, SaveWriteError when it no longer exists."""
    if _loaded is None or _loaded[0] != _key(path):
        return
    target = Path(path)
    current = file_signature(target)
    if current is None:
        raise SaveWriteError(
            f"{target.name} was deleted or moved after it was loaded:\n{target}"
        )
    if current != _loaded[1]:
        raise SaveChangedError(
            f"{target.name} changed on disk after it was loaded. Writing "
            "now would overwrite that change."
        )


def write_problem(path: str | Path) -> SaveWriteError | None:
    """The error a write of the loaded save to path would raise, or None."""
    try:
        check_loaded(path)
        check_writable(path)
    except SaveWriteError as exc:
        return exc
    return None


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
        raise SaveReadOnlyError(
            f"{target.name} is read-only. Clear the read-only flag and try again."
        )
    if not os.access(folder, os.W_OK):
        raise SaveReadOnlyError(
            f"The folder of {target.name} is read-only, so the save cannot be "
            f"replaced:\n{folder}"
        )


def atomic_write(
    path: str | Path, data: bytes | bytearray, *, loaded: bool = False
) -> None:
    """Write data to path through a temporary file in the same folder.

    The temporary file is flushed to disk and then replaces path, so path
    holds either the old or the new contents. The temporary file is removed
    when anything fails. Records the write for the external-change watcher.

    loaded marks a write of a parsed save object back to its file: it is
    refused with SaveChangedError when path is the loaded save and changed
    on disk since it was read, and the write becomes the new loaded state.
    Read-modify-write tools (SteamID patchers, restore) leave it False.
    """
    global _loaded
    target = Path(path)
    if loaded:
        check_loaded(target)
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
    if loaded and _loaded is not None and _loaded[0] == _key(target):
        signature = file_signature(target)
        _loaded = (_loaded[0], signature) if signature is not None else None
