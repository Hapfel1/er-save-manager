import hashlib
import json
import shutil
import struct

import pytest

from er_save_manager.transfer.switch2 import convert_pc_character

TITLE_ID = "0400f5802371e000"
SLOT_SIZE = 0x280000
SIZES = [SLOT_SIZE] * 10 + [0x60000, 0x240010]
PROFILE_FLAGS = 0x1954
PROFILE_BASE = PROFILE_FLAGS + 10
PROFILE_SIZE = 0x24C
ACCOUNT_OFFSET = 0x217E09
PC_ACCOUNT = bytes.fromhex("1122334455667788")


def save_name(index):
    return f"ER_____0000_userdata{index:04d}"


@pytest.fixture(scope="module")
def saves(tmp_path_factory):
    root = tmp_path_factory.mktemp("switch2-conversion")
    pc_path = root / "ER0000.sl2"
    backup = root / "switch-backup"
    backup.mkdir()
    header = bytearray(0x300)
    header[:4] = b"BND4"
    struct.pack_into("<I", header, 0xC, 12)
    pc_parts = []
    entries = []
    offset = len(header)

    for index, size in enumerate(SIZES):
        source = bytearray(size)
        target = bytearray(size)
        if index == 0:
            struct.pack_into("<I", source, 0, 252)
            struct.pack_into("<II", source, ACCOUNT_OFFSET - 16, 252, 252)
            source[ACCOUNT_OFFSET : ACCOUNT_OFFSET + 8] = PC_ACCOUNT
            struct.pack_into("<I", target, 0, 260)
            target[0x100:0x110] = b"SWITCH CHARACTER"
        elif index == 10:
            struct.pack_into("<I", source, 0, 252)
            source[4:12] = PC_ACCOUNT
            source[PROFILE_FLAGS] = 1
            source[PROFILE_BASE + 0x20 : PROFILE_BASE + 0x2A] = b"PC PROFILE"
            struct.pack_into("<I", target, 0, 260)
            target[PROFILE_FLAGS] = 1
            target[PROFILE_BASE + 0x20 : PROFILE_BASE + 0x2E] = b"SWITCH PROFILE"

        digest = (
            bytes(16)
            if 0 < index < 10
            else hashlib.md5(source, usedforsecurity=False).digest()
        )
        part = digest + source
        record = 0x40 + index * 0x20
        struct.pack_into("<Q", header, record + 8, len(part))
        struct.pack_into("<I", header, record + 0x10, offset)
        offset += len(part)
        pc_parts.append(part)

        file = backup / save_name(index)
        file.write_bytes(target)
        entries.append(
            {
                "path": "/" + file.name,
                "size": len(target),
                "sha256": hashlib.sha256(target).hexdigest(),
            }
        )

    pc_path.write_bytes(header + b"".join(pc_parts))
    manifest = {
        "titleId": TITLE_ID,
        "archive": "space=User type=Account rank=0 index=0 uid=" + "a" * 16,
        "selection": {
            "space": 1,
            "type": 1,
            "rank": 0,
            "index": 0,
            "staticId": 0,
            "uid": "a" * 32,
        },
        "files": len(entries),
        "bytes": sum(entry["size"] for entry in entries),
        "partial": False,
        "failed": [],
        "entries": entries,
    }
    (backup / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pc_path, backup


def _convert(pc_path, backup, tmp_path, *, pc_slot=0, switch_slot=0):
    output = tmp_path / "output"
    output.mkdir()
    return convert_pc_character(pc_path, backup, output, pc_slot, switch_slot)


def test_converts_one_character_without_changing_inputs(saves, tmp_path):
    pc_path, backup = saves
    original_global = (backup / save_name(10)).read_bytes()
    result = _convert(pc_path, backup, tmp_path)

    assert result == tmp_path / "output" / "save-files"
    assert {file.name for file in result.iterdir()} == {save_name(0), save_name(10)}
    slot = (result / save_name(0)).read_bytes()
    global_data = (result / save_name(10)).read_bytes()
    assert struct.unpack_from("<I", slot)[0] == 252
    assert slot[ACCOUNT_OFFSET : ACCOUNT_OFFSET + 8] == bytes(8)
    assert struct.unpack_from("<I", global_data)[0] == 260
    assert global_data[4:12] == bytes(8)
    assert global_data[PROFILE_FLAGS] == 1
    assert global_data[PROFILE_BASE + 0x20 : PROFILE_BASE + 0x2A] == b"PC PROFILE"
    assert (backup / save_name(10)).read_bytes() == original_global


def test_accepts_standalone_ns2_savekit_backup(saves, tmp_path):
    pc_path, backup = saves
    standalone = tmp_path / "standalone-backup"
    shutil.copytree(backup, standalone)
    manifest_file = standalone / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    selection = manifest.pop("selection")
    manifest["programId"] = manifest.pop("titleId")
    manifest.update(
        {key: selection[key] for key in ("uid", "space", "type", "rank", "index")}
    )
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    result = _convert(pc_path, standalone, tmp_path)
    assert {file.name for file in result.iterdir()} == {save_name(0), save_name(10)}


@pytest.mark.parametrize("field,value", [("uid", "b" * 32), ("space", 4)])
def test_rejects_conflicting_combined_manifest_identity(saves, tmp_path, field, value):
    pc_path, backup = saves
    combined = tmp_path / "combined-backup"
    shutil.copytree(backup, combined)
    manifest_file = combined / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["programId"] = manifest["titleId"]
    manifest.update(
        {
            key: manifest["selection"][key]
            for key in ("uid", "space", "type", "rank", "index")
        }
    )
    manifest[field] = value
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="conflicting archive identity"):
        _convert(pc_path, combined, tmp_path)


@pytest.mark.parametrize(
    "field,value", [("programId", "0000000000000000"), ("uid", "b" * 32)]
)
def test_rejects_standalone_backup_with_mismatched_identity(
    saves, tmp_path, field, value
):
    pc_path, backup = saves
    standalone = tmp_path / "standalone-backup"
    shutil.copytree(backup, standalone)
    manifest_file = standalone / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    selection = manifest.pop("selection")
    manifest["programId"] = manifest.pop("titleId")
    manifest.update(
        {key: selection[key] for key in ("uid", "space", "type", "rank", "index")}
    )
    manifest[field] = value
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="Elden Ring|identity"):
        _convert(pc_path, standalone, tmp_path)


def test_target_slot_is_selected_independently(saves, tmp_path):
    pc_path, backup = saves
    result = _convert(pc_path, backup, tmp_path, switch_slot=2)
    assert {file.name for file in result.iterdir()} == {save_name(2), save_name(10)}
    global_data = (result / save_name(10)).read_bytes()
    assert global_data[PROFILE_FLAGS + 2] == 1
    start = PROFILE_BASE + 2 * PROFILE_SIZE + 0x20
    assert global_data[start : start + 10] == b"PC PROFILE"
    assert (backup / save_name(10)).read_bytes()[PROFILE_FLAGS + 2] == 0


def test_rejects_bad_pc_checksum(saves, tmp_path):
    pc_path, backup = saves
    changed = bytearray(pc_path.read_bytes())
    changed[0x300] ^= 0xFF
    altered = tmp_path / "bad-checksum.sl2"
    altered.write_bytes(changed)
    with pytest.raises(ValueError, match="checksum|digest|MD5"):
        _convert(altered, backup, tmp_path)


def test_rejects_changed_switch_backup(saves, tmp_path):
    pc_path, backup = saves
    changed_backup = tmp_path / "changed-backup"
    shutil.copytree(backup, changed_backup)
    file = changed_backup / save_name(0)
    data = bytearray(file.read_bytes())
    data[0x100] ^= 1
    file.write_bytes(data)
    with pytest.raises(ValueError, match="SHA|manifest|backup|checksum"):
        _convert(pc_path, changed_backup, tmp_path)


def test_rejects_newer_pc_version(saves, tmp_path):
    pc_path, backup = saves
    changed = bytearray(pc_path.read_bytes())
    struct.pack_into("<I", changed, 0x300 + 16, 300)
    changed[0x300 : 0x300 + 16] = hashlib.md5(
        changed[0x300 + 16 : 0x300 + 16 + SLOT_SIZE], usedforsecurity=False
    ).digest()
    altered = tmp_path / "newer.sl2"
    altered.write_bytes(changed)
    with pytest.raises(ValueError, match="version|newer|format"):
        _convert(altered, backup, tmp_path)


def test_rejects_empty_source_slot(saves, tmp_path):
    pc_path, backup = saves
    with pytest.raises(ValueError, match="empty|checksum|character"):
        _convert(pc_path, backup, tmp_path, pc_slot=1)


def test_rejects_unlisted_backup_file(saves, tmp_path):
    pc_path, backup = saves
    changed_backup = tmp_path / "extra-backup"
    shutil.copytree(backup, changed_backup)
    (changed_backup / "unlisted.dat").write_bytes(b"extra")
    with pytest.raises(ValueError, match="manifest|extra|unlisted|unexpected"):
        _convert(pc_path, changed_backup, tmp_path)


def test_rejects_backup_symlink(saves, tmp_path):
    pc_path, backup = saves
    changed_backup = tmp_path / "linked-backup"
    shutil.copytree(backup, changed_backup)
    file = changed_backup / save_name(0)
    file.unlink()
    file.symlink_to(backup / save_name(0))
    with pytest.raises(ValueError, match="link|file|backup"):
        _convert(pc_path, changed_backup, tmp_path)
