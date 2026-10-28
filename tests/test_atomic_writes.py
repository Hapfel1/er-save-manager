"""
Tests for atomic save-file writes.

Save.to_file and BackupManager.restore_backup/restore_to_new_file write
via a temp file + os.replace instead of a direct in-place open(path, "wb").
A direct overwrite can leave a file-watcher (Steam Cloud sync, antivirus,
the game's own save detection) holding a stale cached view of the file,
since the file's identity never changes for a same-path truncate+write.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def _no_tmp_files_left(directory: Path) -> bool:
    return not any(".tmp" in p.name for p in directory.iterdir())


def test_to_file_leaves_no_leftover_temp_file(sanitized_save, tmp_path):
    out = tmp_path / "ER0000_out.co2"
    sanitized_save.to_file(str(out))

    assert _no_tmp_files_left(tmp_path)


def test_to_file_overwrites_existing_file_atomically(sanitized_save, tmp_path):
    out = tmp_path / "ER0000_out.co2"
    out.write_bytes(b"stale placeholder content")

    sanitized_save.to_file(str(out))

    assert out.read_bytes() == bytes(sanitized_save._raw_data)
    assert _no_tmp_files_left(tmp_path)


def test_restore_backup_is_byte_identical_and_leaves_no_temp_files(
    tmp_path, sanitized_save_path
):
    from er_save_manager.backup.manager import BackupManager

    live_save = tmp_path / "ER0000.co2"
    shutil.copyfile(sanitized_save_path, live_save)
    original_bytes = live_save.read_bytes()

    manager = BackupManager(live_save)
    backup_path, _ = manager.create_backup(description="test", operation="test")

    # Corrupt the live save in place to prove restore actually overwrites it.
    with open(live_save, "r+b") as f:
        f.write(b"CORRUPTED")

    assert manager.restore_backup(backup_path.name) is True
    assert live_save.read_bytes() == original_bytes
    assert _no_tmp_files_left(tmp_path)


def test_restore_to_new_file_is_byte_identical_and_leaves_no_temp_files(
    tmp_path, sanitized_save_path
):
    from er_save_manager.backup.manager import BackupManager

    live_save = tmp_path / "ER0000.co2"
    shutil.copyfile(sanitized_save_path, live_save)
    original_bytes = live_save.read_bytes()

    manager = BackupManager(live_save)
    backup_path, _ = manager.create_backup(description="test", operation="test")

    target = tmp_path / "restored_elsewhere.co2"
    assert manager.restore_to_new_file(backup_path.name, str(target)) is True
    assert target.read_bytes() == original_bytes
    assert _no_tmp_files_left(tmp_path)


def test_same_second_same_operation_backups_get_distinct_filenames(
    tmp_path, sanitized_save_path
):
    """Two create_backup() calls with the same operation string, in the
    same wall-clock second, must not collide on filename - a collision
    would silently overwrite the earlier backup with no warning.
    """
    from er_save_manager.backup.manager import BackupManager

    live_save = tmp_path / "ER0000.co2"
    shutil.copyfile(sanitized_save_path, live_save)

    manager = BackupManager(live_save)

    first_path, _ = manager.create_backup(description="", operation="add_item")
    first_content = first_path.read_bytes()

    # Mutate the live save in place so the second backup would capture
    # different content if it were allowed to overwrite the first.
    with open(live_save, "r+b") as f:
        f.write(b"DIFFERENT_STATE")

    second_path, _ = manager.create_backup(description="", operation="add_item")

    assert first_path != second_path
    assert first_path.exists()
    assert second_path.exists()
    assert first_path.read_bytes() == first_content


def test_create_backup_removes_temp_files_of_ended_writes(
    tmp_path, sanitized_save_path
):
    """A crash between the temp write and the rename leaves
    <name>.tmp<pid>; the next backup in the folder deletes it unless the
    writing process still runs."""
    import os

    from er_save_manager.backup.manager import BackupManager

    live_save = tmp_path / "ER0000.co2"
    shutil.copyfile(sanitized_save_path, live_save)
    manager = BackupManager(live_save)
    folder = manager.backup_folder
    folder.mkdir()

    # Above the Linux pid_max limit (2**22), so no process has this id.
    dead = 2**22 + 1
    stale = [
        folder / f"ER0000.co2_2026-01-01_00-00-00_x.bak.tmp{dead}",
        folder / f"ER0000.co2_2026-01-01_00-00-00_x.bak.zip.tmp{dead}",
        folder / f"metadata.json.tmp{dead}",
    ]
    live = [
        folder / f"ER0000.co2_2026-01-01_00-00-00_y.bak.tmp{os.getpid()}",
        folder / f"unrelated.txt.tmp{dead}",
    ]
    for path in stale + live:
        path.write_bytes(b"partial")

    manager.create_backup(operation="add_item")

    assert not any(p.exists() for p in stale)
    assert all(p.exists() for p in live)
