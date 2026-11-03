from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import struct
from pathlib import Path

TITLE_ID = "0400f5802371e000"
SIZES = (0x280000,) * 10 + (0x60000, 0x240010)
PROFILE_FLAGS = 0x1954
PROFILE_BASE = PROFILE_FLAGS + 10
PROFILE_SIZE = 0x24C
MAX_PC_SIZE = 64 * 1024 * 1024

SPACES = {
    0: "System",
    1: "User",
    2: "SdSystem",
    3: "Temporary",
    4: "SdUser",
    100: "ProperSystem",
    101: "SafeMode",
    102: "ProperUser",
}
TYPES = {
    0: "System",
    1: "Account",
    2: "Bcat",
    3: "Device",
    4: "Temporary",
    5: "Cache",
    6: "SystemBcat",
    7: "StreamPlay",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _name(index: int) -> str:
    return f"ER_____0000_userdata{index:04d}"


def _regular_file(path: Path, size: int | None = None) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ValueError(f"Missing save file: {path.name}") from exc
    _require(stat.S_ISREG(metadata.st_mode), f"Not a regular save file: {path.name}")
    if size is not None:
        _require(metadata.st_size == size, f"Unexpected save file size: {path.name}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pc_entries(data: bytes, selected_slot: int) -> list[bytes]:
    _require(
        0x300 <= len(data) <= MAX_PC_SIZE
        and data[:4] == b"BND4"
        and struct.unpack_from("<I", data, 0xC)[0] == 12,
        "This is not a complete Elden Ring PC .sl2 save.",
    )
    entries = []
    ranges = []
    for index, expected_size in enumerate(SIZES):
        record = 0x40 + index * 0x20
        size = struct.unpack_from("<Q", data, record + 8)[0]
        offset = struct.unpack_from("<I", data, record + 0x10)[0]
        _require(
            size == expected_size + 16 and 0x300 <= offset <= len(data) - size,
            "The PC save has an unexpected Elden Ring entry.",
        )
        digest = data[offset : offset + 16]
        payload = data[offset + 16 : offset + size]
        empty = index < 10 and digest == bytes(16)
        _require(
            (not empty or index != selected_slot)
            and (
                empty or hashlib.md5(payload, usedforsecurity=False).digest() == digest
            ),
            f"PC character data {index + 1} failed its checksum.",
        )
        entries.append(payload)
        ranges.append((offset, offset + size))
    ranges.sort()
    _require(
        all(
            previous[1] <= current[0]
            for previous, current in zip(ranges, ranges[1:], strict=False)
        ),
        "The PC save has overlapping entries.",
    )
    return entries


def _verify_backup(backup: Path) -> None:
    _require(
        backup.is_dir() and not backup.is_symlink(), "Choose a SaveKit backup folder."
    )
    manifest_path = backup / "manifest.json"
    _regular_file(manifest_path)
    _require(
        manifest_path.stat().st_size <= 1024 * 1024,
        "The SaveKit manifest is too large.",
    )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("The SaveKit manifest could not be read.") from exc
    _require(isinstance(manifest, dict), "The SaveKit manifest is invalid.")
    _require(
        manifest.get("titleId") == TITLE_ID,
        "The backup is not for Elden Ring on Switch 2.",
    )
    selection = manifest.get("selection")
    _require(isinstance(selection, dict), "The backup has no archive identity.")
    for field in ("space", "type", "rank", "index", "staticId"):
        _require(
            type(selection.get(field)) is int,
            "The backup has an invalid archive identity.",
        )
    uid = selection.get("uid")
    _require(
        isinstance(uid, str) and re.fullmatch(r"[a-f0-9]{32}", uid) is not None,
        "The backup has an invalid account ID.",
    )
    space = SPACES.get(selection["space"], selection["space"])
    archive_type = TYPES.get(selection["type"], selection["type"])
    label = (
        f"space={space} type={archive_type} rank={selection['rank']} "
        f"index={selection['index']} uid={uid[:16]}"
    )
    _require(
        manifest.get("archive") == label, "The backup archive identity does not match."
    )
    entries = manifest.get("entries")
    _require(
        manifest.get("partial") is not True
        and manifest.get("failed") in (None, [])
        and type(manifest.get("files")) is int
        and manifest["files"] == 12
        and isinstance(entries, list)
        and len(entries) == 12,
        "Choose a complete Elden Ring SaveKit backup with 12 files.",
    )
    expected = {_name(index): size for index, size in enumerate(SIZES)}
    _require(
        {entry.name for entry in backup.iterdir()} == set(expected) | {"manifest.json"},
        "The backup has files missing from its manifest or unexpected files.",
    )
    seen = set()
    total = 0
    for entry in entries:
        _require(isinstance(entry, dict), "The SaveKit manifest has an invalid entry.")
        entry_path = entry.get("path")
        _require(
            isinstance(entry_path, str)
            and entry_path.startswith("/")
            and entry_path[1:] in expected
            and entry_path[1:] not in seen,
            "The SaveKit manifest has a missing or repeated file.",
        )
        name = entry_path[1:]
        seen.add(name)
        _require(
            type(entry.get("size")) is int and entry["size"] == expected[name],
            f"The SaveKit manifest has an invalid size for {name}.",
        )
        digest = entry.get("sha256")
        _require(
            isinstance(digest, str)
            and re.fullmatch(r"[a-f0-9]{64}", digest) is not None,
            f"The SaveKit manifest has no SHA-256 for {name}.",
        )
        file = backup / name
        _regular_file(file, expected[name])
        _require(
            _sha256(file) == digest,
            f"The SaveKit backup failed SHA-256 verification: {name}.",
        )
        total += expected[name]
    _require(seen == set(expected), "The SaveKit backup is missing a file.")
    _require(
        type(manifest.get("bytes")) is int and manifest["bytes"] == total,
        "The SaveKit backup byte count differs from its manifest.",
    )


def _patch_account(slot: bytearray, source: bytes, target: bytes, version: int) -> None:
    _require(source != bytes(8), "The PC save has no usable account ID.")
    offsets = []
    position = slot.find(source)
    while position != -1:
        offsets.append(position)
        position = slot.find(source, position + 1)
    _require(
        len(offsets) == 1 and offsets[0] >= 16,
        "Could not identify exactly one account ID in the selected PC character.",
    )
    offset = offsets[0]
    _require(
        struct.unpack_from("<II", slot, offset - 16) == (version, version),
        "The selected PC character has an unrecognized account record.",
    )
    slot[offset : offset + 8] = target


def convert_pc_character(
    pc_save: Path,
    switch_backup: Path,
    output_dir: Path,
    pc_slot: int,
    switch_slot: int,
) -> Path:
    pc_save = Path(pc_save)
    switch_backup = Path(switch_backup)
    output_dir = Path(output_dir)
    _require(
        type(pc_slot) is int
        and 0 <= pc_slot < 10
        and type(switch_slot) is int
        and 0 <= switch_slot < 10,
        "Choose character slots from 1 to 10.",
    )
    _require(pc_save.suffix.lower() == ".sl2", "Choose a PC .sl2 save.")
    _regular_file(pc_save)
    _require(
        0x300 <= pc_save.stat().st_size <= MAX_PC_SIZE,
        "Choose a complete PC .sl2 save.",
    )
    pc = _pc_entries(pc_save.read_bytes(), pc_slot)
    _verify_backup(switch_backup)

    pc_global = pc[10]
    source = pc[pc_slot]
    switch_global = (switch_backup / _name(10)).read_bytes()
    source_version = struct.unpack_from("<I", source)[0]
    pc_version = struct.unpack_from("<I", pc_global)[0]
    switch_version = struct.unpack_from("<I", switch_global)[0]
    _require(
        source_version > 0
        and source_version == pc_version
        and switch_version > 0
        and source_version <= switch_version,
        "The PC character version is incompatible with this Switch backup.",
    )
    _require(
        pc_global[PROFILE_FLAGS + pc_slot] == 1,
        "The selected PC character slot is empty.",
    )
    _require(
        switch_global[PROFILE_FLAGS + switch_slot] <= 1,
        "The Switch backup has an unrecognized character profile.",
    )
    source_profile = PROFILE_BASE + pc_slot * PROFILE_SIZE
    target_profile = PROFILE_BASE + switch_slot * PROFILE_SIZE
    _require(
        source_profile + PROFILE_SIZE <= len(pc_global)
        and target_profile + PROFILE_SIZE <= len(switch_global),
        "The Elden Ring profile summary is incomplete.",
    )

    converted_slot = bytearray(source)
    _patch_account(converted_slot, pc_global[4:12], switch_global[4:12], source_version)
    converted_global = bytearray(switch_global)
    converted_global[target_profile : target_profile + PROFILE_SIZE] = pc_global[
        source_profile : source_profile + PROFILE_SIZE
    ]
    converted_global[PROFILE_FLAGS + switch_slot] = 1

    _require(
        output_dir.is_dir()
        and not output_dir.is_symlink()
        and not any(output_dir.iterdir()),
        "Choose an existing, empty output folder.",
    )
    save_folder = output_dir / "save-files"
    save_folder.mkdir(mode=0o700)
    try:
        for name, data in (
            (_name(switch_slot), converted_slot),
            (_name(10), converted_global),
        ):
            target = save_folder / name
            with target.open("xb") as stream:
                stream.write(data)
            target.chmod(0o600)
            _require(
                target.read_bytes() == data,
                f"Could not verify the converted file: {name}.",
            )
    except Exception:
        shutil.rmtree(save_folder)
        raise
    return save_folder


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a PC Elden Ring character for a Switch 2 SaveKit backup."
    )
    parser.add_argument("--pc", type=Path, required=True, help="PC .sl2 save")
    parser.add_argument(
        "--switch",
        type=Path,
        required=True,
        help="complete Switch 2 SaveKit backup folder",
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="existing empty output folder"
    )
    parser.add_argument(
        "--pc-slot", type=int, required=True, help="PC character slot, 0 to 9"
    )
    parser.add_argument(
        "--switch-slot", type=int, required=True, help="Switch character slot, 0 to 9"
    )
    args = parser.parse_args()
    try:
        save_folder = convert_pc_character(
            args.pc, args.switch, args.output, args.pc_slot, args.switch_slot
        )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
    print(save_folder)


if __name__ == "__main__":
    main()
