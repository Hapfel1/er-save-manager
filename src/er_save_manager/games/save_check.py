"""
Save integrity check and repair for DS3, DSR, DS2 and Nightreign.

check() reads the file and reports problems; repair() fixes the ones marked
fixable and writes the file in place. Callers make the backup.

Checked per game:
  all       entry checksums (the game rejects a save with a bad one)
  DS3, DSR  load screen directory name and level match the character slot
  DS3       slot layout resolves (inventory, gestures, NG+ offsets)
  DS2       load screen caches (entries 0 and 22) match name, level, class
  NR        no bytes past the last BND4 entry (left by old relic spawns)
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Issue:
    text: str
    fixable: bool
    # Character slot the issue belongs to; None for save-wide issues.
    slot: int | None = None


def _md5(data: bytes) -> bytes:
    return hashlib.md5(data).digest()


def _utf16(data: bytes) -> str:
    end = 0
    while end + 1 < len(data) and data[end : end + 2] != b"\x00\x00":
        end += 2
    return data[:end].decode("utf-16-le", errors="replace")


# --- Dark Souls III ----------------------------------------------------------


def _ds3_dir_mismatches(save) -> list[tuple[int, str]]:
    from er_save_manager.games.DS3 import character_ops as ops

    out = []
    for i, char in enumerate(save.characters):
        if char is None:
            continue
        entry = ops._read_dir_entry(save, i)
        name = _utf16(bytes(entry[ops.DIR_NAME_OFFSET : ops.DIR_NAME_OFFSET + 34]))
        level = struct.unpack_from("<I", entry, ops.DIR_LEVEL_OFFSET)[0]
        if name != char.name or level != char.level:
            out.append(
                (
                    i,
                    f"Load screen shows '{name}' level {level}, "
                    f"the character is '{char.name}' level {char.level}",
                )
            )
    return out


def _check_ds3(path: Path) -> list[Issue]:
    from er_save_manager.games.DS3.parser import DS3Parser, _read_entry_header
    from er_save_manager.games.DS3.save import DS3Save

    raw = path.read_bytes()
    issues = []
    for i in range(DS3Parser.TOTAL_SLOTS):
        size, offset = _read_entry_header(raw, i)
        blob = raw[offset : offset + size]
        if _md5(blob[16:]) != blob[:16]:
            if i < 10:
                issues.append(Issue("Invalid slot checksum", True, i))
            else:
                issues.append(Issue("Invalid global data checksum", True))
    save = DS3Save.from_file(path)
    for i, char in enumerate(save.characters):
        if char is not None and char.layout_error:
            issues.append(Issue(char.layout_error, False, i))
    issues += [Issue(text, True, i) for i, text in _ds3_dir_mismatches(save)]
    return issues


def _repair_ds3(path: Path) -> None:
    from er_save_manager.games.DS3.character_ops import _sync_dir_name_level
    from er_save_manager.games.DS3.save import DS3Save

    save = DS3Save.from_file(path)
    for i, _ in _ds3_dir_mismatches(save):
        char = save.characters[i]
        _sync_dir_name_level(save, i, char.name, char.level)
    save.save_to_file(path)


# --- Dark Souls Remastered ---------------------------------------------------


def _dsr_dir_mismatches(save) -> list[tuple[int, str]]:
    from er_save_manager.games.DSR import character_ops as ops

    out = []
    for i, char in enumerate(save.characters):
        if char is None:
            continue
        entry = ops._read_dir_entry(save, i)
        name = _utf16(bytes(entry[ops.DIR_NAME_OFFSET : ops.DIR_NAME_OFFSET + 34]))
        level = struct.unpack_from("<I", entry, ops.DIR_LEVEL_OFFSET)[0]
        if name != char.name or level != char.level:
            out.append(
                (
                    i,
                    f"Load screen shows '{name}' level {level}, "
                    f"the character is '{char.name}' level {char.level}",
                )
            )
    return out


def _check_dsr(path: Path) -> list[Issue]:
    from er_save_manager.games.DSR.save import DSRSave

    save = DSRSave.from_file(path)
    issues = [
        Issue("Invalid slot checksum", True, i)
        if i < 10
        else Issue("Invalid profile data checksum", True)
        for i, ok in save.verify_checksums()
        if not ok
    ]
    issues += [Issue(text, True, i) for i, text in _dsr_dir_mismatches(save)]
    return issues


def _repair_dsr(path: Path) -> None:
    from er_save_manager.games.DSR.character_ops import _sync_dir_name_level
    from er_save_manager.games.DSR.save import DSRSave

    save = DSRSave.from_file(path)
    for i, _ in _dsr_dir_mismatches(save):
        char = save.characters[i]
        _sync_dir_name_level(save, i, char.name, char.level)
    save.save_to_file(path)


# --- Dark Souls II -----------------------------------------------------------


def _ds2_cache_mismatches(save) -> list[tuple[int, str]]:
    from er_save_manager.games.DS2 import save as ds2

    out = []
    for entry, name_offset, label in (
        (ds2.OCCUPANCY_ENTRY, ds2._OCC_NAME_OFFSET, "slot summary"),
        (ds2.CHARACTER_SELECT_ENTRY, ds2._SELECT_NAME_OFFSET, "load screen"),
    ):
        data = save.container.get_entry(entry)
        for i, char in enumerate(save.characters):
            if not ds2._is_valid_name(char.name):
                continue
            off = name_offset + ds2._OCC_STRIDE * i
            if off + ds2._CACHE_CLASS_FROM_NAME + 2 > len(data):
                continue
            name = ds2._decode_name(bytes(data[off : off + ds2._OCC_NAME_SIZE]))
            level = struct.unpack_from("<H", data, off + ds2._CACHE_LEVEL_FROM_NAME)[0]
            cls = struct.unpack_from("<H", data, off + ds2._CACHE_CLASS_FROM_NAME)[0]
            expected_name = char.name[: ds2._OCC_NAME_SIZE // 2]
            if (name, level, cls) != (
                expected_name,
                char.get_stat("level"),
                char.starting_class,
            ):
                out.append(
                    (
                        i,
                        f"{label.capitalize()} shows '{name}' level {level}, "
                        f"the character is '{char.name}' level "
                        f"{char.get_stat('level')}",
                    )
                )
    return out


def _check_ds2(path: Path) -> list[Issue]:
    from er_save_manager.games.DS2 import save as ds2

    raw = path.read_bytes()
    issues = []
    for i in range(ds2.TOTAL_ENTRIES):
        size, offset = ds2._read_entry_header(raw, i)
        blob = raw[offset : offset + size]
        if _md5(blob[16:]) != blob[:16]:
            slot = i - ds2.PROFILE_ENTRY_START
            if 0 <= slot < ds2.CHARACTER_SLOTS:
                issues.append(Issue("Invalid character data checksum", True, slot))
            else:
                issues.append(Issue(f"Invalid checksum in save entry {i}", True))
    save = ds2.DS2Save.from_file(path)
    issues += [Issue(text, True, i) for i, text in _ds2_cache_mismatches(save)]
    return issues


def _repair_ds2(path: Path) -> None:
    from er_save_manager.games.DS2 import save as ds2

    save = ds2.DS2Save.from_file(path)
    # The container only rewrites entries that were opened, so open them all
    # to have every checksum recomputed.
    for i in range(ds2.TOTAL_ENTRIES):
        save.container.get_entry(i)
    for i, char in enumerate(save.characters):
        if ds2._is_valid_name(char.name):
            save.sync_class_cache(i)
    save.save_to_file(path)


# --- Nightreign --------------------------------------------------------------


def _check_nr(path: Path) -> list[Issue]:
    from er_save_manager.games.NR.parser import _CHECKSUM_TAIL, NightreignSave

    save = NightreignSave.from_file(path)
    issues = []
    for entry in save.entries:
        dec = entry.decrypted
        end = len(dec) - _CHECKSUM_TAIL
        if _md5(bytes(dec[4:end])) != bytes(dec[end : end + 16]):
            if entry.index < 10:
                issues.append(Issue("Invalid slot checksum", True, entry.index))
            else:
                issues.append(
                    Issue(f"Invalid checksum in save entry {entry.index}", True)
                )
    if save.trailing_bytes:
        issues.append(
            Issue(f"{save.trailing_bytes} stray bytes after the last entry", True)
        )
    return issues


def _repair_nr(path: Path) -> None:
    from er_save_manager.games.NR.parser import NightreignSave

    NightreignSave.from_file(path).write_file(path)


_GAMES = {
    "dark_souls_3": (_check_ds3, _repair_ds3),
    "dark_souls_remastered": (_check_dsr, _repair_dsr),
    "dark_souls_2": (_check_ds2, _repair_ds2),
    "nightreign": (_check_nr, _repair_nr),
}


def supported(game_key: str) -> bool:
    return game_key in _GAMES


def check(game_key: str, path: str | Path) -> list[Issue]:
    """Problems found in the save. A file that cannot be read at all is
    reported as one unfixable issue."""
    try:
        return _GAMES[game_key][0](Path(path))
    except Exception as exc:
        return [Issue(f"The save could not be read: {exc}", False)]


def repair(game_key: str, path: str | Path) -> None:
    """Fix every fixable issue and write the save in place."""
    _GAMES[game_key][1](Path(path))
