"""Backup manager for Elden Ring save files."""

from __future__ import annotations

import contextlib
import gzip
import json
import os
import re
import shutil
import threading
import zipfile
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from er_save_manager.own_writes import atomic_write

if TYPE_CHECKING:
    from er_save_manager.parser import Save


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """
    Write bytes to path via a temp file + atomic replace.
    """
    atomic_write(path, data)


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
    compressed: bool = False
    favorite: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> BackupMetadata:
        # Drop unknown keys so a metadata.json written by a newer build
        # does not raise TypeError and wipe the whole history on load.
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


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


# Suffixes of backup files, checked in order (".bak.zip" before ".zip").
_BACKUP_EXTENSIONS = (".bak.zip", ".bak.gz", ".bak", ".zip", ".gz")
# "<stem>_<YYYY-mm-dd_HH-MM-SS>[_<operation and description>]"
_NAME_STAMP = re.compile(r"_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})(?:_(.*))?$")
# Temporary name of an unfinished write: "<target name>.tmp<writer pid>".
_TMP_NAME = re.compile(r"^(.+)\.tmp(\d+)$")


def _pid_running(pid: int) -> bool:
    """True when a process with this id exists (or its state is unknown)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        kernel32.GetExitCodeProcess.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ulong),
        )
        # PROCESS_QUERY_LIMITED_INFORMATION; os.kill on Windows terminates.
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            # ERROR_ACCESS_DENIED: the process exists under another user.
            return kernel32.GetLastError() == 5
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def _metadata_from_entry(entry) -> BackupMetadata | None:
    """BackupMetadata from one metadata.json entry, None when a required
    field is missing or a known field has the wrong type."""
    if not isinstance(entry, dict):
        return None
    try:
        meta = BackupMetadata.from_dict(entry)
    except TypeError:
        return None
    for f in fields(BackupMetadata):
        value = getattr(meta, f.name)
        expected = _FIELD_TYPES[f.name]
        if not isinstance(value, expected) or (
            expected is int and isinstance(value, bool)
        ):
            return None
    if not meta.filename or Path(meta.filename).name != meta.filename:
        return None
    return meta


_FIELD_TYPES = {
    "filename": str,
    "original_file": str,
    "timestamp": str,
    "description": str,
    "operation": str,
    "character_summary": list,
    "file_size": int,
    "compressed": bool,
    "favorite": bool,
}


def _log_problem(exc: BaseException, where: str) -> None:
    """Append exc to errors.log without showing a dialog."""
    try:
        from er_save_manager.ui.error_report import log_exception

        log_exception(type(exc), exc, exc.__traceback__, where)
    except Exception:
        pass


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
            save_path: Path to the save file
        """
        from er_save_manager.games.DS3.parser import is_ps_userdata

        self.save_path = Path(save_path).resolve()
        # A DS3 PS4 save is a folder of userdata files; one backup holds all
        # of them, whichever file was opened.
        self._ps_folder = is_ps_userdata(self.save_path)
        stem = "userdata" if self._ps_folder else self.save_path.name
        self.backup_folder = self.save_path.parent / (stem + self.BACKUP_FOLDER_SUFFIX)
        self._history: BackupHistory | None = None

    def _save_files(self) -> list[Path]:
        """Files one backup of this save contains."""
        if not self._ps_folder:
            return [self.save_path]
        from er_save_manager.games.DS3.parser import ps_folder_files

        files = ps_folder_files(self.save_path)
        return [files[i] for i in sorted(files)] or [self.save_path]

    def _write_members(self, zipf: zipfile.ZipFile, target: Path) -> None:
        """Write the zip's save files: a single member to target, several
        members by name into target's folder."""
        names = zipf.namelist()
        if not names:
            raise ValueError(f"Backup zip is empty: {zipf.filename}")
        if len(names) == 1:
            _atomic_write_bytes(target, zipf.read(names[0]))
            return
        for name in names:
            _atomic_write_bytes(target.parent / Path(name).name, zipf.read(name))

    @property
    def history(self) -> BackupHistory:
        """Get backup history, loading from disk if needed."""
        if self._history is None:
            self._history = self._load_history()
        return self._history

    def _load_history(self) -> BackupHistory:
        """Load backup history from metadata file.

        An unreadable metadata.json is replaced by a list built from the
        backup files on disk, and entries with missing or mistyped fields
        are dropped; backup files no entry names are added from disk. Both
        cases are logged to errors.log.
        """
        history = BackupHistory(save_file=str(self.save_path))
        metadata_path = self.backup_folder / self.METADATA_FILE
        if not metadata_path.exists():
            return history
        try:
            with open(metadata_path, encoding="utf-8") as f:
                data = json.load(f)
            entries = data["backups"] if isinstance(data, dict) else None
            if not isinstance(entries, list):
                raise ValueError("metadata.json has no backup list")
        except (OSError, ValueError, KeyError) as e:
            _log_problem(
                e, f"Backup list {metadata_path} unreadable, rebuilt from files"
            )
            history.backups = self._backups_from_disk(set())
            return history

        skipped = []
        for entry in entries:
            meta = _metadata_from_entry(entry)
            if meta is None:
                skipped.append(entry)
            else:
                history.backups.append(meta)
        if skipped:
            _log_problem(
                ValueError(f"{len(skipped)} bad entries skipped: {skipped!r}"[:2000]),
                f"Backup list {metadata_path}",
            )
            known = {b.filename for b in history.backups}
            history.backups.extend(self._backups_from_disk(known))
            history.backups.sort(key=lambda b: b.timestamp, reverse=True)
        return history

    def _backups_from_disk(self, known: set[str]) -> list[BackupMetadata]:
        """Metadata for the backup files in the folder that are not in known,
        newest first. Timestamp and description come from the file name
        when it has the generated layout, else the timestamp is the mtime."""
        found = []
        try:
            paths = list(self.backup_folder.iterdir())
        except OSError:
            return found
        for path in paths:
            name = path.name
            if name in known or not path.is_file():
                continue
            ext = next((e for e in _BACKUP_EXTENSIONS if name.endswith(e)), None)
            if ext is None:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            timestamp = datetime.fromtimestamp(stat.st_mtime).isoformat()
            description = ""
            match = _NAME_STAMP.search(name[: -len(ext)])
            if match:
                with contextlib.suppress(ValueError):
                    timestamp = datetime.strptime(
                        match.group(1), "%Y-%m-%d_%H-%M-%S"
                    ).isoformat()
                description = match.group(2) or ""
            found.append(
                BackupMetadata(
                    filename=name,
                    original_file=self.save_path.name,
                    timestamp=timestamp,
                    description=description,
                    file_size=stat.st_size,
                    compressed=ext != ".bak",
                )
            )
        found.sort(key=lambda b: b.timestamp, reverse=True)
        return found

    def _remove_stale_temps(self) -> None:
        """Delete temporary backup and metadata files left by a write whose
        process ended before the rename (crash, kill, power loss). Files of
        this process or of a running process belong to a live write."""
        try:
            paths = list(self.backup_folder.iterdir())
        except OSError:
            return
        own = os.getpid()
        for path in paths:
            match = _TMP_NAME.match(path.name)
            if match is None:
                continue
            target, pid = match.group(1), int(match.group(2))
            if target != self.METADATA_FILE and not target.endswith(_BACKUP_EXTENSIONS):
                continue
            if pid == own or _pid_running(pid) or not path.is_file():
                continue
            with contextlib.suppress(OSError):
                path.unlink()

    def _save_history(self) -> None:
        """Save backup history to metadata file."""
        self.backup_folder.mkdir(parents=True, exist_ok=True)
        metadata_path = self.backup_folder / self.METADATA_FILE
        text = json.dumps(self.history.to_dict(), indent=2)
        atomic_write(metadata_path, text.encode("utf-8"))

    def _sanitize_filename_part(self, text: str) -> str:
        """Sanitize a string for safe use in filenames."""
        if not text:
            return ""
        # Remove null bytes and control characters
        text = re.sub(r"[\x00-\x1f\x7f]", "", text)
        # Replace invalid filename characters with underscores
        text = re.sub(r'[<>:"/\\|?*]', "_", text)
        text = text.replace(" ", "_")
        # Collapse multiple underscores
        text = re.sub(r"_+", "_", text)
        text = text.strip("_")
        return text

    def _generate_backup_name(
        self, description: str = "", operation: str = "", compressed: bool = False
    ) -> str:
        """
        Generate a unique backup filename.

        Two backups with the same operation and description in the same
        second would get the same name and the second would overwrite the
        first, so a numeric suffix is appended until the name is free on
        disk.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_name = self.save_path.stem

        parts = [base_name, timestamp]
        if operation:
            parts.append(self._sanitize_filename_part(operation).lower())
        if description:
            short = re.sub(r"[(),]", "", description)
            parts.append(self._sanitize_filename_part(short).lower()[:30].rstrip("_"))

        extension = ".bak.zip" if compressed else ".bak"
        stem = "_".join(parts)

        candidate = f"{stem}{extension}"
        suffix = 2
        while (self.backup_folder / candidate).exists():
            candidate = f"{stem}_{suffix}{extension}"
            suffix += 1
        return candidate

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
        keep: tuple[str, ...] = (),
    ) -> tuple[Path, list[BackupMetadata]]:
        from er_save_manager.ui.settings import (
            get_settings,  # lazy to avoid circular import
        )

        """
        Create a backup of the current save file.

        Args:
            description: Optional description of the backup
            operation: Operation being performed (e.g., "fix_torrent")
            save: Optional Save object to extract character info from
            compress: Whether to compress the backup (None = use settings)
            keep: Backup file names pruning leaves in place

        Pruning past the max_backups setting, and its warning dialog, run
        on the Tk main loop once the current event handler returns, so a
        caller that writes the save right after this call finishes the
        write first. Without a Tk root it prunes before returning.

        Returns:
            Tuple of (Path to created backup, List of BackupMetadata that will be pruned)
        """
        sources = self._save_files()
        if not any(p.exists() for p in sources):
            raise FileNotFoundError(f"Save file not found: {self.save_path}")
        self.backup_folder.mkdir(parents=True, exist_ok=True)
        self._remove_stale_temps()

        if self._ps_folder:
            compress = True
        elif compress is None:
            try:
                settings = get_settings()
                compress = settings.get("compress_backups", False)
            except Exception:
                compress = False

        backup_name = self._generate_backup_name(description, operation, compress)
        backup_path = self.backup_folder / backup_name

        # Written under a temporary name so a failed copy (disk full) never
        # leaves a truncated file with a backup name.
        tmp_path = backup_path.with_name(f"{backup_name}.tmp{os.getpid()}")
        try:
            if compress:
                with zipfile.ZipFile(
                    tmp_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6
                ) as zipf:
                    for file in sources:
                        zipf.write(file, arcname=file.name)
            else:
                shutil.copy2(self.save_path, tmp_path)
            os.replace(tmp_path, backup_path)
        except BaseException:
            with contextlib.suppress(OSError):
                tmp_path.unlink()
            raise

        metadata = BackupMetadata(
            filename=backup_name,
            original_file=self.save_path.name,
            timestamp=datetime.now().isoformat(),
            description=description,
            operation=operation,
            file_size=backup_path.stat().st_size,
            compressed=compress,
        )

        if save:
            metadata.character_summary = self._get_character_summary(save)

        self.history.backups.insert(0, metadata)
        self._save_history()

        pruned_backups = []
        try:
            max_backups = get_settings().get("max_backups", 50)
            if max_backups and max_backups > 0:
                pruned_backups = self.get_backups_to_prune(
                    keep_count=max_backups, keep=keep
                )
        except Exception as e:
            _log_problem(e, f"Backup pruning of {self.backup_folder}")
        if pruned_backups:
            self._schedule_prune(keep)

        return backup_path, pruned_backups

    def _schedule_prune(self, keep: tuple[str, ...]) -> None:
        """Run _prune_to_limit on the Tk main loop, or now without a root."""
        import tkinter as _tk

        root = _tk._default_root
        try:
            alive = root is not None and root.winfo_exists()
        except Exception:
            alive = False
        if not alive:
            self._prune_to_limit(keep)
            return
        if threading.current_thread() is threading.main_thread():
            root.after_idle(self._prune_to_limit, keep)
        else:
            root.after(0, self._prune_to_limit, keep)

    def _prune_to_limit(self, keep: tuple[str, ...]) -> None:
        """Prune past max_backups, asking first when the warning is on."""
        from er_save_manager.ui.settings import get_settings

        try:
            # Re-read: other BackupManager instances may have added backups
            # since this one loaded the list.
            self._history = None
            settings = get_settings()
            max_backups = settings.get("max_backups", 50)
            if not max_backups or max_backups <= 0:
                return
            pruned_backups = self.get_backups_to_prune(
                keep_count=max_backups, keep=keep
            )
            if not pruned_backups:
                return
            if settings.get("show_backup_pruning_warning", True):
                result = self._show_pruning_warning(max_backups, pruned_backups)
                # User raised the limit - re-read setting and skip prune
                if result == "raised":
                    max_backups = get_settings().get("max_backups", max_backups)
            self.prune_backups(keep_count=max_backups, keep=keep)
        except Exception as e:
            _log_problem(e, f"Backup pruning of {self.backup_folder}")

    def _show_pruning_warning(
        self, max_backups: int, pruned_backups: list[BackupMetadata]
    ) -> str:
        """Show the pruning warning dialog before deleting. Returns dialog result."""
        try:
            import tkinter as _tk

            from er_save_manager.ui.dialogs.backup_pruning_warning import (
                BackupPruningWarningDialog,
            )

            # Walk all Tk/CTk top-level windows to find a live root.
            root = _tk._default_root
            if root is None or not root.winfo_exists():
                return "delete"

            if threading.current_thread() is threading.main_thread():
                dialog = BackupPruningWarningDialog(
                    root, pruned_backups[0], max_backups
                )
                return dialog.show()

            # Called from a background thread (e.g. auto-backup process
            # monitor). CTk widgets are not thread-safe, so the dialog
            # must be created on the main thread. Marshal it via root.after
            # and block this thread until the user closes it.
            result_holder: list[str] = []
            done = threading.Event()

            def _create_and_show():
                dialog = BackupPruningWarningDialog(
                    root, pruned_backups[0], max_backups
                )
                result_holder.append(dialog.show())
                done.set()

            root.after(0, _create_and_show)
            done.wait()
            return result_holder[0] if result_holder else "delete"
        except Exception as e:
            print(f"Backup pruning warning failed: {e}")
            return "delete"

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
        Automatically handles compressed backups (both .zip and legacy .gz).

        Args:
            backup_name: Name of the backup file to restore

        Returns:
            True if successful
        """
        backup_path = self.backup_folder / backup_name
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_name}")

        # Back up the current state before restoring, unless the save is
        # gone. The backup being restored is kept out of pruning.
        if any(p.exists() for p in self._save_files()):
            self.create_backup(
                description="before_restore",
                operation=f"restore_{backup_name}",
                keep=(backup_name,),
            )

        is_zip = backup_name.endswith(".zip")
        is_gzip = backup_name.endswith(".gz")

        if is_zip:
            with zipfile.ZipFile(backup_path, "r") as zipf:
                self._write_members(zipf, self.save_path)
        elif is_gzip:
            # Legacy gzip support
            with gzip.open(backup_path, "rb") as f_in:
                data = f_in.read()
            _atomic_write_bytes(self.save_path, data)
        else:
            data = backup_path.read_bytes()
            _atomic_write_bytes(self.save_path, data)

        return True

    def restore_to_new_file(self, backup_name: str, target_path: str | Path) -> bool:
        """
        Restore a backup to a new file (doesn't overwrite current save).
        Automatically handles compressed backups (both .zip and legacy .gz).

        A backup of several files (DS3 PS4 userdata folder) is written by
        file name into target_path's folder.

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
        is_zip = backup_name.endswith(".zip")
        is_gzip = backup_name.endswith(".gz")

        if is_zip:
            with zipfile.ZipFile(backup_path, "r") as zipf:
                self._write_members(zipf, target)
        elif is_gzip:
            # Legacy gzip support
            with gzip.open(backup_path, "rb") as f_in:
                data = f_in.read()
            _atomic_write_bytes(target, data)
        else:
            data = backup_path.read_bytes()
            _atomic_write_bytes(target, data)

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

        self.history.backups = [
            b for b in self.history.backups if b.filename != backup_name
        ]
        self._save_history()
        return True

    def get_backups_to_prune(
        self, keep_count: int = 10, keep: tuple[str, ...] = ()
    ) -> list[BackupMetadata]:
        """
        Get list of backups that would be deleted by pruning.

        Favorites are excluded entirely: they are never returned as
        prune candidates and do not consume a slot in keep_count, so
        marking a backup as a favorite pins it regardless of the limit.

        Args:
            keep_count: Number of non-favorite backups to keep
            keep: Backup file names treated like favorites

        Returns:
            List of BackupMetadata that would be deleted
        """
        prunable = [
            b for b in self.history.backups if not b.favorite and b.filename not in keep
        ]
        if len(prunable) <= keep_count:
            return []

        return prunable[keep_count:]

    def prune_backups(self, keep_count: int = 10, keep: tuple[str, ...] = ()) -> int:
        """
        Delete old backups, keeping only the most recent ones.

        Favorites are skipped and stay on disk.

        Args:
            keep_count: Number of non-favorite backups to keep
            keep: Backup file names treated like favorites

        Returns:
            Number of backups deleted
        """
        to_delete = self.get_backups_to_prune(keep_count=keep_count, keep=keep)
        if not to_delete:
            return 0

        doomed = {b.filename for b in to_delete}
        deleted = 0

        for backup in to_delete:
            backup_path = self.backup_folder / backup.filename
            if backup_path.exists():
                backup_path.unlink()
                deleted += 1

        # Filter by filename instead of slicing, since favorites can sit
        # anywhere in the list and must survive the rewrite.
        self.history.backups = [
            b for b in self.history.backups if b.filename not in doomed
        ]
        self._save_history()

        return deleted

    def set_favorite(self, backup_name: str, favorite: bool = True) -> bool:
        """
        Mark or unmark a backup as a favorite.

        Args:
            backup_name: Name of the backup file
            favorite: True to pin the backup, False to release it

        Returns:
            True if the backup was found and updated
        """
        for backup in self.history.backups:
            if backup.filename == backup_name:
                backup.favorite = favorite
                self._save_history()
                return True
        return False

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
