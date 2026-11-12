"""Undo link for the toast shown after an edit: restores the backup made
right before the edit and reloads the save."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from er_save_manager import own_writes


def undo_action(
    parent,
    save_path: str | Path,
    backup_path: Path | None,
    reload: Callable[[], None] | None,
    what: str,
    process_name: str = "eldenring.exe",
    game_name: str = "Elden Ring",
) -> tuple[str, Callable[[], None]] | None:
    """("Undo", callback) for show_toast, None when there is nothing to undo.

    Call right after the edit was written. The undo only runs while the
    file is still the one this edit wrote; after a later edit or an outside
    change it points to the Backup Manager instead of dropping that change.
    """
    if backup_path is None or reload is None:
        return None
    save_path = Path(save_path)
    written = own_writes.file_signature(save_path)

    def undo() -> None:
        from er_save_manager.backup.manager import BackupManager
        from er_save_manager.ui.messagebox import CTkMessageBox
        from er_save_manager.ui.toast import notify
        from er_save_manager.ui.utils import game_blocks_write

        if own_writes.file_signature(save_path) != written:
            notify(
                parent,
                "The save changed after this edit. Restore an older state in "
                "the Backup Manager.",
                "warning",
                5000,
            )
            return
        if game_blocks_write(parent, process_name, game_name):
            return
        try:
            BackupManager(save_path).restore_backup(backup_path.name)
        except Exception as e:
            CTkMessageBox.showerror(
                "Undo Failed", f"Could not restore the backup:\n{e}", parent=parent
            )
            return
        own_writes.record_write(save_path)
        reload()
        notify(parent, f"Undone: {what}", "info")

    return ("Undo", undo)
