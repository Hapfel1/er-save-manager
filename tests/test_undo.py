"""Undo of the last edit: backup before the edit, write, toast offer, restore."""

from __future__ import annotations

from er_save_manager import own_writes
from er_save_manager.backup.manager import BackupManager
from er_save_manager.ui import toast, undo


def test_undo_restores_the_edit_once(tmp_path, monkeypatch):
    save = tmp_path / "DS30000.sl2"
    save.write_bytes(b"before")
    reloaded = []
    undo.configure(reloaded.append, lambda: ("", ""), lambda: True)
    monkeypatch.setattr(toast, "notify", lambda *a, **k: None)

    BackupManager(save).create_backup(operation="manual_backup")
    own_writes.atomic_write(save, b"manual")
    assert undo.offer(None) is None  # not an edit

    BackupManager(save).create_backup(operation="kill_boss")
    own_writes.atomic_write(save, b"after")
    action = undo.offer(None)
    assert action is not None and undo.offer(None) is None  # offered once
    action[1]()
    assert save.read_bytes() == b"manual"
    assert reloaded == [str(save)]

    # A later write makes an older edit's Undo refuse
    BackupManager(save).create_backup(operation="kill_boss")
    own_writes.atomic_write(save, b"one")
    stale = undo.offer(None)
    save.write_bytes(b"outside change")
    stale[1]()
    assert save.read_bytes() == b"outside change"
