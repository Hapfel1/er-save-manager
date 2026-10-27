"""Tests for the loaded-save check in own_writes.atomic_write."""

from __future__ import annotations

import os

import pytest

from er_save_manager import own_writes


@pytest.fixture(autouse=True)
def _forget_loaded():
    yield
    own_writes.record_load(None, None)


def _load(path):
    own_writes.record_load(path, own_writes.file_signature(path))


def test_loaded_write_after_own_write(tmp_path):
    save = tmp_path / "ER0000.sl2"
    save.write_bytes(b"a")
    _load(save)
    own_writes.atomic_write(save, b"bb", loaded=True)
    own_writes.atomic_write(save, b"ccc", loaded=True)
    assert save.read_bytes() == b"ccc"


def test_loaded_write_refused_after_external_change(tmp_path):
    save = tmp_path / "ER0000.sl2"
    save.write_bytes(b"a")
    _load(save)
    save.write_bytes(b"changed")
    with pytest.raises(own_writes.SaveChangedError):
        own_writes.atomic_write(save, b"x", loaded=True)
    assert save.read_bytes() == b"changed"
    assert isinstance(own_writes.write_problem(save), own_writes.SaveChangedError)


def test_unchecked_write_ignores_loaded_state(tmp_path):
    save = tmp_path / "ER0000.sl2"
    save.write_bytes(b"a")
    _load(save)
    own_writes.atomic_write(save, b"patched")
    with pytest.raises(own_writes.SaveChangedError):
        own_writes.atomic_write(save, b"x", loaded=True)


def test_other_path_not_checked(tmp_path):
    save = tmp_path / "ER0000.sl2"
    save.write_bytes(b"a")
    _load(save)
    other = tmp_path / "ER0000.co2"
    own_writes.atomic_write(other, b"x", loaded=True)
    assert other.read_bytes() == b"x"


def test_deleted_save(tmp_path):
    save = tmp_path / "ER0000.sl2"
    save.write_bytes(b"a")
    _load(save)
    save.unlink()
    problem = own_writes.write_problem(save)
    assert isinstance(problem, own_writes.SaveWriteError)
    assert not isinstance(problem, own_writes.SaveChangedError)


@pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0, reason="POSIX mode bits")
def test_read_only_save(tmp_path):
    save = tmp_path / "ER0000.sl2"
    save.write_bytes(b"a")
    save.chmod(0o444)
    with pytest.raises(own_writes.SaveReadOnlyError):
        own_writes.atomic_write(save, b"x")
    assert save.read_bytes() == b"a"
