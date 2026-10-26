"""
DS3 PS4 userdata saves: one unencrypted file per entry, each the PC
plaintext without its leading u32 size field.

The folders are built from the decrypted PC slot fixture, so they carry
the same character as test_ds3_slot.py.
"""

from __future__ import annotations

import struct
import zipfile
from pathlib import Path

import pytest

from er_save_manager.backup.manager import BackupManager
from er_save_manager.games.DS3 import character_ops
from er_save_manager.games.DS3.parser import is_ps_userdata, save_identity
from er_save_manager.games.DS3.save import DS3Save
from er_save_manager.games.save_identify import identify_game

FIXTURE = Path(__file__).parent / "fixtures" / "DS3_slot0_sanitized.bin.zip"
SLOT_SIZE = 0xC0000
GLOBAL_SIZE = 0x60000


@pytest.fixture(scope="module")
def slot_body() -> bytes:
    with zipfile.ZipFile(FIXTURE) as zf:
        plaintext = zf.read("DS3_slot0_sanitized.bin")
    assert struct.unpack_from("<I", plaintext, 0)[0] == SLOT_SIZE
    return plaintext[4:]


def _write_folder(folder: Path, body: bytes, slots: range, with_global: bool) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for i in slots:
        data = body if i == 0 else bytes(SLOT_SIZE)
        (folder / f"userdata{i:04d}").write_bytes(data)
    if with_global:
        (folder / "userdata0010").write_bytes(bytes(GLOBAL_SIZE))


@pytest.fixture
def ps_folder(tmp_path, slot_body) -> Path:
    folder = tmp_path / "ps4"
    _write_folder(folder, slot_body, range(10), with_global=True)
    return folder


@pytest.fixture
def ps_single(tmp_path, slot_body) -> Path:
    folder = tmp_path / "single"
    _write_folder(folder, slot_body, range(1), with_global=False)
    return folder


def _steam_field(data: bytes) -> bytes:
    ptr = struct.unpack_from("<i", data, 0x58)[0]
    return bytes(data[ptr + 0x6F : ptr + 0x77])


def test_identifies_userdata_files(ps_folder, tmp_path):
    assert is_ps_userdata(ps_folder / "userdata0003")
    assert is_ps_userdata(ps_folder / "userdata0010")
    assert identify_game(ps_folder / "userdata0000") == "dark_souls_3"
    wrong = tmp_path / "userdata0011"
    wrong.write_bytes(bytes(SLOT_SIZE))
    assert not is_ps_userdata(wrong)
    short = tmp_path / "userdata0001"
    short.write_bytes(bytes(SLOT_SIZE - 1))
    assert not is_ps_userdata(short)
    assert identify_game(short) is None


def test_folder_loads_every_file(ps_folder):
    save = DS3Save.from_file(ps_folder / "userdata0004")
    assert save.is_ps
    assert save.has_directory
    assert all(save.slot_available(i) for i in range(10))
    char = save.characters[0]
    assert char is not None and char.layout_error is None
    assert char.name == "invtest"
    assert all(c is None for c in save.characters[1:])


def test_unchanged_save_writes_nothing(ps_folder):
    before = {p.name: p.stat().st_mtime_ns for p in ps_folder.iterdir()}
    DS3Save.from_file(ps_folder / "userdata0000").save_to_file(
        ps_folder / "userdata0000"
    )
    assert {p.name: p.stat().st_mtime_ns for p in ps_folder.iterdir()} == before


def test_edit_writes_only_changed_files(ps_folder, slot_body):
    save = DS3Save.from_file(ps_folder / "userdata0000")
    save.characters[0].name = "Renamed"
    character_ops._sync_dir_name_level(save, 0, "Renamed", save.characters[0].level)
    before = (ps_folder / "userdata0001").stat().st_mtime_ns
    save.save_to_file(ps_folder / "userdata0000")

    body = (ps_folder / "userdata0000").read_bytes()
    assert len(body) == SLOT_SIZE and body != slot_body
    assert (ps_folder / "userdata0001").stat().st_mtime_ns == before
    reloaded = DS3Save.from_file(ps_folder / "userdata0000")
    assert reloaded.characters[0].name == "Renamed"
    entry = character_ops._read_dir_entry(reloaded, 0)
    assert entry[:14] == "Renamed".encode("utf-16-le")


def test_copy_and_delete_in_folder(ps_folder):
    save = DS3Save.from_file(ps_folder / "userdata0000")
    character_ops.copy_slot(save, 0, 5)
    save.save_to_file(ps_folder / "userdata0000")
    assert (ps_folder / "userdata0005").read_bytes() == (
        ps_folder / "userdata0000"
    ).read_bytes()

    save = DS3Save.from_file(ps_folder / "userdata0000")
    character_ops.delete_slot(save, 5)
    save.save_to_file(ps_folder / "userdata0000")
    assert (ps_folder / "userdata0005").read_bytes() == bytes(SLOT_SIZE)


def test_single_file_limits_to_its_slot(ps_single):
    save = DS3Save.from_file(ps_single / "userdata0000")
    assert save.is_ps and not save.has_directory
    assert save.slot_available(0) and not save.slot_available(1)
    with pytest.raises(ValueError, match="userdata0001"):
        character_ops.copy_slot(save, 0, 1)
    save.characters[0].name = "Alone"
    character_ops._sync_dir_name_level(save, 0, "Alone", save.characters[0].level)
    save.save_to_file(ps_single / "userdata0000")
    assert sorted(p.name for p in ps_single.iterdir()) == ["userdata0000"]
    assert DS3Save.from_file(ps_single / "userdata0000").characters[0].name == "Alone"


def test_transfer_to_ps_clears_steamid(ps_folder, ps_single, slot_body):
    assert _steam_field(b"\0\0\0\0" + slot_body) != bytes(8)
    source = DS3Save.from_file(ps_single / "userdata0000")
    target = DS3Save.from_file(ps_folder / "userdata0000")
    character_ops.transfer_slot(source, 0, target, 3)
    target.save_to_file(ps_folder / "userdata0000")
    moved = struct.pack("<I", SLOT_SIZE) + (ps_folder / "userdata0003").read_bytes()
    assert _steam_field(moved) == bytes(8)


def test_save_identity_is_the_folder(ps_folder):
    assert save_identity(ps_folder / "userdata0000") == save_identity(
        ps_folder / "userdata0007"
    )


def test_backup_holds_and_restores_every_file(ps_folder, slot_body):
    manager = BackupManager(ps_folder / "userdata0002")
    backup_path, _ = manager.create_backup(operation="test", compress=False)
    assert backup_path.suffix == ".zip"
    with zipfile.ZipFile(backup_path) as zf:
        assert len(zf.namelist()) == 11

    save = DS3Save.from_file(ps_folder / "userdata0000")
    character_ops.copy_slot(save, 0, 1)
    save.save_to_file(ps_folder / "userdata0000")
    assert (ps_folder / "userdata0001").read_bytes() == slot_body

    BackupManager(ps_folder / "userdata0000").restore_backup(backup_path.name)
    assert (ps_folder / "userdata0001").read_bytes() == bytes(SLOT_SIZE)
    assert (ps_folder / "userdata0000").read_bytes() == slot_body


def test_equipment_sync_reaches_the_directory(ps_folder):
    save = DS3Save.from_file(ps_folder / "userdata0000")
    ids = save.characters[0].equipped_ids()
    character_ops.sync_dir_equipment(save, 0)
    save.save_to_file(ps_folder / "userdata0000")
    entry = character_ops._read_dir_entry(
        DS3Save.from_file(ps_folder / "userdata0000"), 0
    )
    at = character_ops.DIR_EQUIP_OFFSET
    assert list(struct.unpack_from(f"<{len(ids)}I", entry, at)) == list(ids)


def test_userdata_gets_the_ps4_ban_warning(ps_folder, tmp_path):
    from er_save_manager.ui.dialogs.vanilla_save_warning import (
        _GAME_TEXT,
        is_vanilla_save,
        warning_key,
    )

    path = str(ps_folder / "userdata0000")
    assert is_vanilla_save(path)
    assert warning_key("dark_souls_3", path) == "dark_souls_3_ps4"
    assert "PlayStation Network" in _GAME_TEXT["dark_souls_3_ps4"][0]
    pc = tmp_path / "DS30000.co2"
    pc.write_bytes(b"BND4")
    assert not is_vanilla_save(str(pc))
    assert warning_key("dark_souls_3", str(pc)) == "dark_souls_3"
