"""
Tests for er_save_manager.own_writes, which lets the external-modification
watcher ignore saves written by the tool itself.
"""

from __future__ import annotations

import os

from er_save_manager.backup.manager import _atomic_write_bytes
from er_save_manager.own_writes import is_own_write


def test_untouched_file_is_not_own_write(sanitized_save_copy):
    assert is_own_write(sanitized_save_copy) is False


def test_save_to_file_is_own_write(sanitized_save, sanitized_save_copy):
    sanitized_save.to_file(sanitized_save_copy)
    assert is_own_write(sanitized_save_copy) is True


def test_backup_restore_write_is_own_write(sanitized_save_copy):
    data = sanitized_save_copy.read_bytes()
    _atomic_write_bytes(sanitized_save_copy, data)
    assert is_own_write(sanitized_save_copy) is True


def test_external_write_after_own_write_is_detected(
    sanitized_save, sanitized_save_copy
):
    sanitized_save.to_file(sanitized_save_copy)
    st = os.stat(sanitized_save_copy)
    with open(sanitized_save_copy, "r+b") as f:
        f.write(b"\x01")
    os.utime(sanitized_save_copy, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
    assert is_own_write(sanitized_save_copy) is False
