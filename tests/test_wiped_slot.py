"""Wiped character slot detection and recovery sources."""

import shutil
import sys
from datetime import datetime

from er_save_manager.fixes.wiped_slot import (
    SLOT_SIZE,
    RecoverySource,
    extract_copy,
    find_game_backups,
    find_shadow_copies,
    is_wiped_slot,
)
from er_save_manager.parser import Save


def test_zeroed_slot_is_wiped_only_while_active(sanitized_save):
    assert not any(is_wiped_slot(sanitized_save, i) for i in range(10))
    off = sanitized_save.slot_data_offset(0)
    sanitized_save._raw_data[off : off + SLOT_SIZE] = bytes(SLOT_SIZE)
    assert is_wiped_slot(sanitized_save, 0)
    sanitized_save.user_data_10_parsed.profile_summary.active_profiles[0] = False
    assert not is_wiped_slot(sanitized_save, 0)


def test_game_backup_reports_the_character(sanitized_save_path, tmp_path, monkeypatch):
    save_path = tmp_path / sanitized_save_path.name
    shutil.copy(sanitized_save_path, save_path)
    shutil.copy(sanitized_save_path, tmp_path / (save_path.name + ".bak"))
    pgd = Save.from_file(str(save_path)).character_slots[0].player_game_data

    (source,) = find_game_backups(save_path, 0)
    assert source.path.name == save_path.name + ".bak"
    assert source.character == (pgd.character_name, pgd.level)

    monkeypatch.setattr(sys, "platform", "linux")
    assert find_shadow_copies(save_path, 0) == []


def test_extract_copy_writes_next_to_save(tmp_path):
    save_path = tmp_path / "ER0000.sl2"
    save_path.write_bytes(b"current")
    source = RecoverySource(
        "shadow", ("Tarnished", 10), datetime(2026, 10, 1, 9, 5), b"old"
    )
    target = extract_copy(source, save_path)
    assert target == tmp_path / "ER0000 (Previous Version 2026-10-01 09-05).sl2"
    assert target.read_bytes() == b"old"
    assert save_path.read_bytes() == b"current"
