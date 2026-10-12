"""Wiped character slot detection (Elden Ring).

A wiped slot has every byte zero (version 0, checksum of zeros valid) while
CSProfileSummary still marks it active with a full load screen summary. The
game loads it as a new character. The data is gone from the file, so the
only fix is restoring the character from an older copy of the save.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    path: Path
    # Character name and level in that copy, None if the slot is empty
    # there too or the file could not be read.
    character: tuple[str, int] | None


def find_game_backups(save_path: str | Path, slot_index: int) -> list[RecoverySource]:
    """The game's own .bak copies next to the save, with the slot's content."""
    from er_save_manager.parser import Save

    save_path = Path(save_path)
    sources = []
    for bak in sorted(save_path.parent.glob(save_path.name + "*.bak")):
        character = None
        try:
            copy = Save.from_file(str(bak))
            if not is_wiped_slot(copy, slot_index):
                slot = copy.characters[slot_index]
                if slot and not slot.is_empty():
                    pgd = slot.player_game_data
                    character = (pgd.character_name, pgd.level)
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
