"""Wiped character slot detection (Elden Ring).

A wiped slot has every byte zero (version 0, checksum of zeros valid) while
CSProfileSummary still marks it active with a full load screen summary. The
game loads it as a new character. The data is gone from the file, so the
only fix is restoring the character from an older copy of the save.
"""

from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.parser import Save

SLOT_SIZE = 0x280000
_ZERO_SLOT = bytes(SLOT_SIZE)


def is_wiped_slot(save: Save, slot_index: int) -> bool:
    """True if the profile marks the slot active but its data is all zero."""
    ud10 = save.user_data_10_parsed
    if not ud10 or not ud10.profile_summary:
        return False
    active = ud10.profile_summary.active_profiles
    if slot_index >= len(active) or not active[slot_index]:
        return False
    off = save.slot_data_offset(slot_index)
    return bytes(save._raw_data[off : off + SLOT_SIZE]) == _ZERO_SLOT


@dataclass
class RecoverySource:
    # str for shadow copy device paths, which pathlib would alter
    path: Path | str
    # Character name and level in that copy, None if the slot is empty
    # there too or the file could not be read.
    character: tuple[str, int] | None
    # Modification time of the copy, set for Windows shadow copies
    modified: datetime | None = None
    # File content, kept for shadow copies so they can be extracted
    data: bytes | None = None


def _slot_character(save: Save, slot_index: int) -> tuple[str, int] | None:
    if is_wiped_slot(save, slot_index):
        return None
    slot = save.characters[slot_index]
    if not slot or slot.is_empty():
        return None
    pgd = slot.player_game_data
    return (pgd.character_name, pgd.level)


def find_game_backups(save_path: str | Path, slot_index: int) -> list[RecoverySource]:
    """The game's own .bak copies next to the save, with the slot's content."""
    from er_save_manager.parser import Save

    save_path = Path(save_path)
    sources = []
    for bak in sorted(save_path.parent.glob(save_path.name + "*.bak")):
        character = None
        try:
            character = _slot_character(Save.from_file(str(bak)), slot_index)
        except Exception:
            pass
        sources.append(RecoverySource(bak, character))
    return sources


def manager_backup_count(save_path: str | Path) -> int:
    """Number of save manager backups recorded for this save."""
    from er_save_manager.backup.manager import BackupManager

    try:
        return len(BackupManager(Path(save_path)).history.backups)
    except Exception:
        return 0


# Shadow copy devices are numbered from 1 and never reused; numbers of
# deleted copies leave gaps, so every index up to the limit is probed.
_SHADOW_COPY_LIMIT = 512


def windows_sources_available() -> bool:
    """Previous Versions (shadow copies) exist only on Windows."""
    return sys.platform == "win32"


def find_shadow_copies(save_path: str | Path, slot_index: int) -> list[RecoverySource]:
    """Copies of the save in Windows Volume Shadow Copies (the "Previous
    Versions" of System Restore points), newest first, one per distinct file
    content.

    Enumerating shadow copies needs admin rights, opening a file inside one
    does not, so the device paths are probed directly. Paths are passed as
    strings: pathlib does not keep the GLOBALROOT prefix intact.
    """
    if not windows_sources_available():
        return []
    from er_save_manager.parser import Save

    path = Path(save_path).resolve()
    drive = path.drive
    if len(drive) != 2 or drive[1] != ":":
        return []
    rel = str(path)[len(drive) :]

    seen: set[bytes] = set()
    sources = []
    for n in range(1, _SHADOW_COPY_LIMIT + 1):
        candidate = rf"\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy{n}{rel}"
        try:
            with open(candidate, "rb") as f:
                data = f.read()
            modified = datetime.fromtimestamp(os.stat(candidate).st_mtime)
        except OSError:
            continue
        digest = hashlib.md5(data).digest()
        if digest in seen:
            continue
        seen.add(digest)
        character = None
        try:
            character = _slot_character(Save.from_file(candidate), slot_index)
        except Exception:
            pass
        sources.append(RecoverySource(candidate, character, modified, data))
    sources.sort(key=lambda s: s.modified, reverse=True)
    return sources


def extract_copy(source: RecoverySource, save_path: str | Path) -> Path:
    """Write a shadow copy next to the save under a name the game ignores."""
    save_path = Path(save_path)
    stamp = source.modified.strftime("%Y-%m-%d %H-%M")
    target = save_path.with_name(
        f"{save_path.stem} (Previous Version {stamp}){save_path.suffix}"
    )
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_bytes(source.data)
    tmp.replace(target)
    return target
