"""
DSR and DS2 PS4 userdata saves (layouts at the top of games/ps_userdata.py,
DSR/save.py "PlayStation 4" and DS2/save.py DS2PSContainer).

Folders are built from synthetic entries: DSR files as the console stores
them ([IV][AES-CBC ciphertext][md5(IV + ciphertext)]) or as Apollo's
Decrypt userdata step leaves them (plaintext in place of the ciphertext).
"""

from __future__ import annotations

import hashlib
import struct
import zipfile
from pathlib import Path

import pytest

from er_save_manager import aes_cbc
from er_save_manager.backup.manager import BackupManager
from er_save_manager.games import ps_userdata
from er_save_manager.games.DS2 import save as ds2
from er_save_manager.games.DS2.save import DS2Save
from er_save_manager.games.DSR import character_ops as dsr_ops
from er_save_manager.games.DSR.save import PS_AES_KEY, DSRCharacter, DSRSave
from er_save_manager.games.save_identify import identify_game
from er_save_manager.ui.dialogs.vanilla_save_warning import (
    is_vanilla_save,
    warning_key,
)

DSR_SIZES = ps_userdata.ENTRY_SIZES["dark_souls_remastered"]
DS2_SIZES = ps_userdata.ENTRY_SIZES["dark_souls_2"]
KEYCONFIG = b"[ORBISINPUT]\nACTION_Move_Forward = 18\n"


def _md5(data: bytes) -> bytes:
    return hashlib.md5(data).digest()


def _dsr_plaintext(file_size: int) -> bytearray:
    """[u32 size][data][PKCS7 padding] filling a file of file_size."""
    length = file_size - 32
    plain = bytearray(length)
    struct.pack_into("<I", plain, 0, length - 0x10)
    plain[-12:] = b"\x0c" * 12
    return plain


def _dsr_file(index: int, plain: bytes, encrypted: bool) -> bytes:
    iv = bytes([0xD3, 0x1E, index, 0x85]) * 4
    ciphertext = aes_cbc.encrypt(PS_AES_KEY, iv, bytes(plain))
    return iv + (ciphertext if encrypted else bytes(plain)) + _md5(iv + ciphertext)


def _write_dsr_folder(folder: Path, encrypted: bool) -> None:
    folder.mkdir(parents=True)
    for i, size in enumerate(DSR_SIZES):
        plain = _dsr_plaintext(size)
        if i == 0:
            # Character "Tester" in the PC slot layout (IV + plaintext).
            char = DSRCharacter(slot_index=0, _data=bytearray(16) + plain)
            char.name = "Tester"
            char.level = 7
            char.souls = 100
            char._data[0x74] = 1  # non-empty slot
            plain = char.get_raw()[16:]
        elif i == 10:
            plain[0x28 - 16 : 0x28 - 16 + len(KEYCONFIG)] = KEYCONFIG
            plain[-0x100:] = b"\xab" * 0x100  # undecoded tail
        (folder / f"userdata{i:04d}").write_bytes(_dsr_file(i, plain, encrypted))


def _files(folder: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()}


@pytest.fixture(params=[True, False], ids=["encrypted", "decrypted"])
def dsr_folder(request, tmp_path) -> Path:
    folder = tmp_path / "dsr"
    _write_dsr_folder(folder, request.param)
    return folder


def test_userdata_files_identify_their_game(dsr_folder, tmp_path):
    ds2_folder = _write_ds2_folder(tmp_path / "ds2")
    assert identify_game(dsr_folder / "userdata0000") == "dark_souls_remastered"
    assert identify_game(dsr_folder / "userdata0010") == "dark_souls_remastered"
    assert identify_game(ds2_folder / "userdata0000") == "dark_souls_2"
    assert identify_game(ds2_folder / "userdata0021") == "dark_souls_2"
    stray = tmp_path / "userdata0010"
    stray.write_bytes(bytes(0x1234))
    assert identify_game(stray) is None


def test_dsr_folder_loads_and_unchanged_save_writes_nothing(dsr_folder):
    before = _files(dsr_folder)
    save = DSRSave.from_file(dsr_folder / "userdata0004")
    assert save.is_ps
    assert save.characters[0].name == "Tester"
    assert save.characters[1:] == [None] * 9
    assert all(ok for _, ok in save.verify_checksums())
    save.save_to_file(dsr_folder / "userdata0004")
    assert _files(dsr_folder) == before


def test_dsr_edit_keeps_form_and_md5(dsr_folder):
    before = _files(dsr_folder)
    encrypted = _md5(before["userdata0000"][:-16]) == before["userdata0000"][-16:]
    save = DSRSave.from_file(dsr_folder / "userdata0000")
    save.characters[0].souls = 12345
    save.save_to_file(dsr_folder / "userdata0000")

    after = _files(dsr_folder)
    assert [n for n in after if after[n] != before[n]] == ["userdata0000"]
    data = after["userdata0000"]
    assert (_md5(data[:-16]) == data[-16:]) == encrypted
    reloaded = DSRSave.from_file(dsr_folder / "userdata0000")
    assert reloaded.characters[0].souls == 12345
    assert all(ok for _, ok in reloaded.verify_checksums())


def _plain(path: Path) -> bytes:
    """IV + plaintext of a DSR PS4 file in either form."""
    data = path.read_bytes()
    iv, body = data[:16], data[16:-16]
    if _md5(data[:-16]) == data[-16:]:
        body = aes_cbc.decrypt(PS_AES_KEY, iv, body)
    return iv + body


def test_dsr_directory_lands_after_the_key_config_block(dsr_folder):
    save = DSRSave.from_file(dsr_folder / "userdata0000")
    dsr_ops._sync_dir_name_level(save, 3, "Copy", 9)
    dsr_ops._set_active(save, 3, True)
    save.save_to_file(dsr_folder / "userdata0000")

    data = _plain(dsr_folder / "userdata0010")
    name_at = dsr_ops._dir_entry_offset(3) + dsr_ops.DIR_NAME_OFFSET + 0x2000
    assert data[name_at : name_at + 8].decode("utf-16-le") == "Copy"
    assert data[dsr_ops.ACTIVE_FLAGS_OFFSET + 0x2000 + 3] == 1
    assert data[0x28 : 0x28 + len(KEYCONFIG)] == KEYCONFIG
    assert data[-0x100:] == b"\xab" * 0x100
    assert struct.unpack_from("<I", data, 0x10)[0] == DSR_SIZES[10] - 0x30


def test_dsr_copy_and_delete(dsr_folder):
    save = DSRSave.from_file(dsr_folder / "userdata0000")
    dsr_ops.copy_slot(save, 0, 5)
    save.save_to_file(dsr_folder / "userdata0000")
    save = DSRSave.from_file(dsr_folder / "userdata0000")
    assert save.characters[5].name == "Tester"

    dsr_ops.delete_slot(save, 5)
    save.save_to_file(dsr_folder / "userdata0000")
    save = DSRSave.from_file(dsr_folder / "userdata0000")
    assert save.characters[5] is None
    assert save.system_data[dsr_ops.ACTIVE_FLAGS_OFFSET + 5] == 0


def test_dsr_missing_and_wrong_size_files_are_named(dsr_folder):
    (dsr_folder / "userdata0007").unlink()
    (dsr_folder / "userdata0010").write_bytes(bytes(0x100))
    with pytest.raises(ps_userdata.IncompleteFolderError) as err:
        DSRSave.from_file(dsr_folder / "userdata0000")
    assert "Missing: userdata0007" in str(err.value)
    assert "Wrong size (cut off, damaged or from another game): userdata0010" in (
        str(err.value)
    )


def test_dsr_backup_holds_and_restores_every_file(dsr_folder):
    before = _files(dsr_folder)
    manager = BackupManager(dsr_folder / "userdata0003")
    backup_path, _ = manager.create_backup(operation="test", save=None)
    with zipfile.ZipFile(backup_path) as zf:
        assert sorted(zf.namelist()) == [f"userdata{i:04d}" for i in range(11)]

    save = DSRSave.from_file(dsr_folder / "userdata0000")
    save.characters[0].souls = 1
    save.save_to_file(dsr_folder / "userdata0000")
    manager.restore_backup(backup_path.name)
    assert {k: v for k, v in _files(dsr_folder).items() if k in before} == before


# --- DS2 ---------------------------------------------------------------------

PS_SUMMARY_SIZE = 0x14


def _write_ds2_folder(folder: Path) -> Path:
    folder.mkdir(parents=True)
    for i, size in enumerate(DS2_SIZES):
        data = bytearray(size)
        if i == ds2.OCCUPANCY_ENTRY:
            struct.pack_into("<III", data, 0, 3, 0x66, PS_SUMMARY_SIZE)
            next_section = 0x20 + PS_SUMMARY_SIZE
            struct.pack_into("<III", data, next_section, 4, 0x6D, 0x1370)
        (folder / f"userdata{i:04d}").write_bytes(bytes(data))
    return folder


def test_ds2_entry_zero_is_served_in_the_pc_layout(tmp_path):
    folder = _write_ds2_folder(tmp_path / "ds2")
    save = DS2Save.from_file(folder / "userdata0012")
    assert save.is_ps
    entry = save.container.get_entry(ds2.OCCUPANCY_ENTRY)
    assert len(entry) == DS2_SIZES[0] + 0x32C - PS_SUMMARY_SIZE
    assert struct.unpack_from("<I", entry, 8)[0] == 0x32C
    assert struct.unpack_from("<I", entry, 0x34C)[0] == 4
    assert save.damaged_slots() == []


def test_ds2_unchanged_save_writes_nothing(tmp_path):
    folder = _write_ds2_folder(tmp_path / "ds2")
    before = _files(folder)
    save = DS2Save.from_file(folder / "userdata0000")
    save.save_to_file(folder / "userdata0000")
    assert _files(folder) == before


def test_ds2_name_cache_lands_at_the_ps4_offset(tmp_path):
    folder = _write_ds2_folder(tmp_path / "ds2")
    before = _files(folder)
    save = DS2Save.from_file(folder / "userdata0000")
    entry = save.container.get_entry(ds2.OCCUPANCY_ENTRY)
    off = ds2._OCC_NAME_OFFSET + ds2._OCC_STRIDE * 2
    entry[off : off + 8] = "Tess".encode("utf-16-le")
    save.container.save_to_file(folder / "userdata0000")

    after = _files(folder)
    assert [n for n in after if after[n] != before[n]] == ["userdata0000"]
    data = after["userdata0000"]
    assert len(data) == DS2_SIZES[0]
    ps_off = off - (0x32C - PS_SUMMARY_SIZE)
    assert data[ps_off : ps_off + 8].decode("utf-16-le") == "Tess"
    assert struct.unpack_from("<I", data, 8)[0] == PS_SUMMARY_SIZE


def test_ds2_missing_file_is_named(tmp_path):
    folder = _write_ds2_folder(tmp_path / "ds2")
    (folder / "userdata0021").unlink()
    with pytest.raises(ps_userdata.IncompleteFolderError, match="userdata0021"):
        DS2Save.from_file(folder / "userdata0000")


def test_ps4_userdata_gets_the_ban_warning(tmp_path, dsr_folder):
    folder = _write_ds2_folder(tmp_path / "ds2")
    path = str(folder / "userdata0001")
    assert is_vanilla_save(path)
    assert warning_key("dark_souls_2", path) == "dark_souls_2_ps4"
    assert is_vanilla_save(str(dsr_folder / "userdata0001"))
    assert (
        warning_key("dark_souls_remastered", str(dsr_folder / "userdata0001"))
        == "dark_souls_remastered_ps4"
    )
    assert warning_key("dark_souls_2", str(dsr_folder / "userdata0001")) == (
        "dark_souls_2"
    )
