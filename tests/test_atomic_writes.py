"""Save.to_file and BackupManager restores write via a temp file and
os.replace, so file watchers (Steam Cloud, antivirus, the game) see a new
file instead of a same-path truncate and write."""

from __future__ import annotations

import shutil
from pathlib import Path

from er_save_manager.backup.manager import BackupManager


def _no_tmp_files_left(directory: Path) -> bool:
    return not any(".tmp" in p.name for p in directory.iterdir())


def test_to_file_replaces_existing_file(sanitized_save, tmp_path):
    out = tmp_path / "ER0000_out.co2"
    out.write_bytes(b"stale placeholder content")
    sanitized_save.to_file(str(out))
    assert out.read_bytes() == bytes(sanitized_save._raw_data)
    assert _no_tmp_files_left(tmp_path)


def test_restores_are_byte_identical(tmp_path, sanitized_save_path):
    live_save = tmp_path / "ER0000.co2"
    shutil.copyfile(sanitized_save_path, live_save)
    original = live_save.read_bytes()
    manager = BackupManager(live_save)
    backup_path, _ = manager.create_backup(description="test", operation="test")

    with open(live_save, "r+b") as f:
        f.write(b"CORRUPTED")
    assert manager.restore_backup(backup_path.name) is True
    assert live_save.read_bytes() == original

    target = tmp_path / "restored_elsewhere.co2"
    assert manager.restore_to_new_file(backup_path.name, str(target)) is True
    assert target.read_bytes() == original
    assert _no_tmp_files_left(tmp_path)


def test_same_second_same_operation_backups_get_distinct_filenames(
    tmp_path, sanitized_save_path
):
    """A filename collision would silently overwrite the earlier backup."""
    live_save = tmp_path / "ER0000.co2"
    shutil.copyfile(sanitized_save_path, live_save)
    manager = BackupManager(live_save)

    first_path, _ = manager.create_backup(description="", operation="add_item")
    first_content = first_path.read_bytes()
    with open(live_save, "r+b") as f:
        f.write(b"DIFFERENT_STATE")
    second_path, _ = manager.create_backup(description="", operation="add_item")

    assert first_path != second_path
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
