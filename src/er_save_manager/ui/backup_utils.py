"""Backup utilities for safe backup creation with warnings."""

from pathlib import Path
from tkinter import messagebox

from er_save_manager.backup.manager import BackupManager, BackupMetadata
from er_save_manager.parser import Save
from er_save_manager.ui.settings import get_settings


def create_backup_with_warning(
    save_path: str | Path,
    description: str = "",
    operation: str = "",
    save: Save | None = None,
) -> tuple[Path | None, list[BackupMetadata]]:
    """
    Create a backup and show warning if backups will be pruned.

    Args:
        save_path: Path to the save file
        description: Optional description of the backup
        operation: Operation being performed
        save: Optional Save object to extract character info from

    Returns:
        Tuple of (Path to backup or None if failed, List of pruned backups)
    """
    try:
        manager = BackupManager(Path(save_path))
        backup_path, pruned_backups = manager.create_backup(
            description=description,
            operation=operation,
            save=save,
        )

        # Show warning if backups were pruned and setting is enabled
        if pruned_backups:
            settings = get_settings()
            if settings.get("show_backup_pruning_warning", True):
                max_backups = settings.get("max_backups", 50)

                # Format the list of deleted backups
                deleted_list = "\n".join(
                    f"  • {backup.filename}" for backup in pruned_backups
                )

                message = (
                    f"Backup limit of {max_backups} reached.\n\n"
                    f"The following old backups were deleted:\n\n{deleted_list}"
                )

                # Show messagebox with don't show again option
                result = messagebox.showwarning(
                    "Backups Pruned",
                    message,
                    default=messagebox.OK,
                )

                # If user wants to disable this warning in the future
                # They can do it in settings
                if result == messagebox.OK:
                    pass

        return backup_path, pruned_backups
    except Exception as e:
        print(f"Failed to create backup: {e}")
        return None, []
