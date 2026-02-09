"""Backup manager for Elden Ring save files."""

from __future__ import annotations

import gzip
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.parser import Save

from er_save_manager.ui.settings import get_settings


@dataclass
class BackupMetadata:
    """Metadata for a single backup."""

    filename: str
    original_file: str
    timestamp: str
    description: str = ""
    operation: str = ""
    character_summary: list[dict] = field(default_factory=list)
    file_size: int = 0
    compressed: bool = False  # Whether backup is gzip compressed

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> BackupMetadata:
        return cls(**data)


@dataclass
class BackupHistory:
    """History of all backups for a save file."""

    save_file: str
    backups: list[BackupMetadata] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "save_file": self.save_file,
            "backups": [b.to_dict() for b in self.backups],
        }

    @classmethod
    def from_dict(cls, data: dict) -> BackupHistory:
        return cls(
            save_file=data["save_file"],
            backups=[BackupMetadata.from_dict(b) for b in data.get("backups", [])],
        )


class BackupManager:
    """
    Manages backups for Elden Ring save files.

    Backups are stored in a dedicated folder next to the save file:
        {save_name}.sl2.backups/
            {save_name}_{timestamp}_{description}.bak
            metadata.json

    All write operations automatically create a backup first.
    """

    BACKUP_FOLDER_SUFFIX = ".backups"
    METADATA_FILE = "metadata.json"

    def __init__(self, save_path: str | Path):
        """
        Initialize backup manager for a save file.

        Args:
            save_path: Path to the save file (.sl2 or .co2)
        """
        self.save_path = Path(save_path).resolve()
        self.backup_folder = self.save_path.parent / (
            self.save_path.name + self.BACKUP_FOLDER_SUFFIX
        )
        self._history: BackupHistory | None = None

    @property
    def history(self) -> BackupHistory:
        """Get backup history, loading from disk if needed."""
        if self._history is None:
            self._history = self._load_history()
        return self._history

    def _load_history(self) -> BackupHistory:
        """Load backup history from metadata file."""
        metadata_path = self.backup_folder / self.METADATA_FILE
        if metadata_path.exists():
            try:
                with open(metadata_path) as f:
                    data = json.load(f)
                return BackupHistory.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        return BackupHistory(save_file=str(self.save_path))

    def _save_history(self) -> None:
        """Save backup history to metadata file."""
        self.backup_folder.mkdir(parents=True, exist_ok=True)
        metadata_path = self.backup_folder / self.METADATA_FILE
        with open(metadata_path, "w") as f:
            json.dump(self.history.to_dict(), f, indent=2)

    def _sanitize_filename_part(self, text: str) -> str:
        """Sanitize a string for safe use in filenames."""
        if not text:
            return ""
        # Remove null bytes and control characters
        text = re.sub(r'[\x00-\x1f\x7f]', '', text)
        # Replace invalid filename characters with underscores
        text = re.sub(r'[<>:"/\\|?*]', '_', text)
        # Replace spaces with underscores
        text = text.replace(' ', '_')
        # Collapse multiple underscores
        text = re.sub(r'_+', '_', text)
        # Remove leading/trailing underscores
        text = text.strip('_')
        return text

    def _generate_backup_name(
        self, description: str = "", operation: str = "", compressed: bool = False
    ) -> str:
        """Generate a unique backup filename."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_name = self.save_path.stem

        parts = [base_name, timestamp]
        if operation:
            parts.append(self._sanitize_filename_part(operation).lower())
        if description:
            parts.append(self._sanitize_filename_part(description).lower()[:30])

        extension = ".bak.gz" if compressed else ".bak"
        return "_".join(parts) + extension

    def _get_character_summary(self, save: Save) -> list[dict]:
        """Extract character summary from save for metadata."""
        summary = []
        for i, slot in enumerate(save.character_slots):
            if slot.is_empty():
                continue
            char_info = {
                "slot": i + 1,
                "name": slot.get_character_name(),
                "level": slot.get_level(),
            }
            summary.append(char_info)
        return summary

    def create_backup(
        self,
        description: str = "",
        operation: str = "",
        save: Save | None = None,
        compress: bool | None = None,
    ) -> tuple[Path, list[BackupMetadata]]:
        """
        Create a backup of the current save file.

        Args:
            description: Optional description of the backup
            operation: Operation being performed (e.g., "fix_torrent")
            save: Optional Save object to extract character info from
            compress: Whether to compress the backup (None = use settings)

        Returns:
            Tuple of (Path to created backup, List of BackupMetadata that will be pruned)
        """
        self.backup_folder.mkdir(parents=True, exist_ok=True)

        # Check compression setting
        if compress is None:
            try:
                settings = get_settings()
                compress = settings.get("compress_backups", False)
            except Exception:
                compress = False

        # Generate backup filename
        backup_name = self._generate_backup_name(description, operation, compress)
        backup_path = self.backup_folder / backup_name

        # Copy and optionally compress the save file
        if compress:
            with open(self.save_path, "rb") as f_in:
                with gzip.open(backup_path, "wb", compresslevel=6) as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy2(self.save_path, backup_path)

        # Create metadata
        metadata = BackupMetadata(
            filename=backup_name,
            original_file=self.save_path.name,
            timestamp=datetime.now().isoformat(),
            description=description,
            operation=operation,
            file_size=backup_path.stat().st_size,
            compressed=compress,
        )

        # Add character summary if save provided
        if save:
            metadata.character_summary = self._get_character_summary(save)

        # Update history
        self.history.backups.insert(0, metadata)
        self._save_history()

        # Prune old backups if max_backups setting is configured
        pruned_backups = []
        try:
            settings = get_settings()
            max_backups = settings.get("max_backups", 50)
            if max_backups and max_backups > 0:
                pruned_backups = self.get_backups_to_prune(keep_count=max_backups)
                if pruned_backups:
                    self.prune_backups(keep_count=max_backups)

                    # Show warning if setting is enabled
                    if settings.get("show_backup_pruning_warning", True):
                        self._show_pruning_warning(max_backups, pruned_backups)
        except Exception:
            # Silently fail if settings can't be accessed
            pass

        return backup_path, pruned_backups

    def _show_pruning_warning(
        self, max_backups: int, pruned_backups: list[BackupMetadata]
    ):
        """Show warning about pruned backups using messagebox."""
        try:
            from tkinter import messagebox

            # Format the list of deleted backups
            deleted_list = "\n".join(
                f"  • {backup.filename}" for backup in pruned_backups
            )

            message = (
                f"Backup limit of {max_backups} reached.\n\n"
                f"The following old backups were permanently deleted:\n\n{deleted_list}\n\n"
                f"You can disable this warning in Settings > Backups > "
                f"'Show warning when backups are automatically deleted'"
            )

            messagebox.showwarning(
                "Backups Pruned",
                message,
            )
        except Exception:
            # Silently fail if messagebox can't be shown (headless mode, etc)
            pass

    def create_pre_write_backup(self, save: Save, operation: str) -> Path:
        """
        Create mandatory backup before any write operation.

        This is called automatically before modifications.

        Args:
            save: The save object being modified
            operation: Description of the operation

        Returns:
            Path to the backup file
        """
        return self.create_backup(
            description="before_modification",
            operation=operation,
            save=save,
        )

    def list_backups(self) -> list[BackupMetadata]:
        """
        List all backups for this save file.

        Returns:
            List of BackupMetadata sorted by timestamp (newest first)
        """
        return self.history.backups

    def restore_backup(self, backup_name: str) -> bool:
        """
        Restore a backup to the current save file.

        Creates a backup of the current state before restoring.
        Automatically handles compressed backups.

        Args:
            backup_name: Name of the backup file to restore

        Returns:
            True if successful
        """
        backup_path = self.backup_folder / backup_name
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_name}")

        # Create backup of current state before restoring
        self.create_backup(
            description="before_restore",
            operation=f"restore_{backup_name}",
        )

        # Check if backup is compressed
        is_compressed = backup_name.endswith(".gz")

        # Restore the backup
        if is_compressed:
            with gzip.open(backup_path, "rb") as f_in:
                with open(self.save_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy2(backup_path, self.save_path)

        return True

    def restore_to_new_file(self, backup_name: str, target_path: str | Path) -> bool:
        """
        Restore a backup to a new file (doesn't overwrite current save).
        Automatically handles compressed backups.

        Args:
            backup_name: Name of the backup file to restore
            target_path: Path where the backup should be restored

        Returns:
            True if successful
        """
        backup_path = self.backup_folder / backup_name
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_name}")

        target = Path(target_path)
        is_compressed = backup_name.endswith(".gz")

        if is_compressed:
            with gzip.open(backup_path, "rb") as f_in:
                with open(target, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy2(backup_path, target)

        return True

    def delete_backup(self, backup_name: str) -> bool:
        """
        Delete a specific backup.

        Args:
            backup_name: Name of the backup file to delete

        Returns:
            True if successful
        """
        backup_path = self.backup_folder / backup_name
        if backup_path.exists():
            backup_path.unlink()

        # Update history
        self.history.backups = [
            b for b in self.history.backups if b.filename != backup_name
        ]
        self._save_history()
        return True

    def get_backups_to_prune(self, keep_count: int = 10) -> list[BackupMetadata]:
        """
        Get list of backups that would be deleted by pruning.

        Args:
            keep_count: Number of backups to keep

        Returns:
            List of BackupMetadata that would be deleted
        """
        if len(self.history.backups) <= keep_count:
            return []

        return self.history.backups[keep_count:]

    def prune_backups(self, keep_count: int = 10) -> int:
        """
        Delete old backups, keeping only the most recent ones.

        Args:
            keep_count: Number of backups to keep

        Returns:
            Number of backups deleted
        """
        if len(self.history.backups) <= keep_count:
            return 0

        to_delete = self.history.backups[keep_count:]
        deleted = 0

        for backup in to_delete:
            backup_path = self.backup_folder / backup.filename
            if backup_path.exists():
                backup_path.unlink()
                deleted += 1

        self.history.backups = self.history.backups[:keep_count]
        self._save_history()

        return deleted

    def verify_backup(self, backup_name: str) -> bool:
        """
        Verify a backup file is valid.

        Args:
            backup_name: Name of the backup file to verify

        Returns:
            True if backup is valid
        """
        backup_path = self.backup_folder / backup_name
        if not backup_path.exists():
            return False

        # Check file size
        if backup_path.stat().st_size < 1000:
            return False

        # Check magic bytes
        with open(backup_path, "rb") as f:
            magic = f.read(4)
            return magic in (b"BND4", b"SL2\x00")

    def get_backup_info(self, backup_name: str) -> BackupMetadata | None:
        """
        Get metadata for a specific backup.

        Args:
            backup_name: Name of the backup file

        Returns:
            BackupMetadata or None if not found
        """
        for backup in self.history.backups:
            if backup.filename == backup_name:
                return backup
        return None
