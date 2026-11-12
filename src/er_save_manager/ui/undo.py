"""Undo for the last edit of a save file.

BackupManager.create_backup notes the backup made before an edit
(note_backup), own_writes.atomic_write notes the write that follows
(note_write). The success toast shown right after that write offers Undo
(offer): it restores the backup and reloads the save, while the file is
still the one the edit wrote, so a later edit or outside change is never
dropped.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from er_save_manager import own_writes

# Backups that are not made before an edit
_NOT_EDITS = ("manual_backup", "auto_backup", "")
_NOT_EDIT_PREFIXES = ("restore_",)
# A write older than this is not offered by a toast any more
_OFFER_SECONDS = 15.0


@dataclass
class _Pending:
    save_path: Path
    backup_path: Path
    written: tuple[int, int] | None = None
    written_at: float = 0.0
    offered: bool = False


_pending: dict[str, _Pending] = {}
# Set by the main window: reload(path) reloads the save if it is loaded,
# game() returns (process name, game name) of the active game
# ready() asks about unapplied edits a reload would drop, False cancels
_reload: Callable[[str], None] | None = None
_game: Callable[[], tuple[str, str]] | None = None
_ready: Callable[[], bool] | None = None


def configure(
    reload: Callable[[str], None],
    game: Callable[[], tuple[str, str]],
    ready: Callable[[], bool],
) -> None:
    global _reload, _game, _ready
    _reload, _game, _ready = reload, game, ready


def _key(path: str | Path) -> str:
    return str(Path(path).resolve())


def note_backup(save_path: str | Path, backup_path: Path, operation: str) -> None:
    """Remember the backup made before an edit of save_path."""
    if operation in _NOT_EDITS or operation.startswith(_NOT_EDIT_PREFIXES):
        return
    _pending[_key(save_path)] = _Pending(Path(save_path), backup_path)


def note_write(path: str | Path) -> None:
    """Mark the noted backup of path as undoable: the edit is on disk."""
    entry = _pending.get(_key(path))
    if entry is None:
        return
    entry.written = own_writes.file_signature(path)
    entry.written_at = time.monotonic()
    entry.offered = False


def offer(parent) -> tuple[str, Callable[[], None]] | None:
    """("Undo", callback) for the edit written just now, None when there is
    none. Each edit is offered once."""
    if _reload is None:
        return None
    now = time.monotonic()
    for entry in sorted(_pending.values(), key=lambda e: -e.written_at):
        if (
            entry.written is None
            or entry.offered
            or now - entry.written_at > _OFFER_SECONDS
            or own_writes.file_signature(entry.save_path) != entry.written
        ):
            continue
        entry.offered = True
        return ("Undo", lambda e=entry: _undo(parent, e))
    return None


def _undo(parent, entry: _Pending) -> None:
    from er_save_manager.backup.manager import BackupManager
    from er_save_manager.ui.messagebox import CTkMessageBox
    from er_save_manager.ui.toast import notify
    from er_save_manager.ui.utils import game_blocks_write

    if own_writes.file_signature(entry.save_path) != entry.written:
        notify(
            parent,
            "The save changed after this edit. Restore an older state in the "
            "Backup Manager.",
            "warning",
            5000,
        )
        return
    if _ready is not None and not _ready():
        return
    if _game is not None:
        process_name, game_name = _game()
        if process_name and game_blocks_write(parent, process_name, game_name):
            return
    try:
        BackupManager(entry.save_path).restore_backup(entry.backup_path.name)
    except Exception as e:
        CTkMessageBox.showerror(
            "Undo Failed", f"Could not restore the backup:\n{e}", parent=parent
        )
        return
    own_writes.record_write(entry.save_path)
    _pending.pop(_key(entry.save_path), None)
    if _reload is not None:
        _reload(str(entry.save_path))
    notify(parent, "Edit undone", "info")
