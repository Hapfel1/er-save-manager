"""Wiped character slot detection."""

import shutil

from er_save_manager.fixes.wiped_slot import (
    SLOT_SIZE,
    find_game_backups,
    is_wiped_slot,
)
from er_save_manager.parser import Save


def _used_slot(save):
    return next(i for i, s in enumerate(save.character_slots) if not s.is_empty())


def _wipe(save, slot_index):
    off = save.slot_data_offset(slot_index)
    save._raw_data[off : off + SLOT_SIZE] = bytes(SLOT_SIZE)


def test_intact_slots_are_not_wiped(sanitized_save):
    assert not any(is_wiped_slot(sanitized_save, i) for i in range(10))


def test_zeroed_active_slot_is_wiped(sanitized_save):
    i = _used_slot(sanitized_save)
    _wipe(sanitized_save, i)
    assert is_wiped_slot(sanitized_save, i)


def test_zeroed_inactive_slot_is_not_wiped(sanitized_save):
    i = _used_slot(sanitized_save)
    _wipe(sanitized_save, i)
    sanitized_save.user_data_10_parsed.profile_summary.active_profiles[i] = False
    assert not is_wiped_slot(sanitized_save, i)


def test_game_backup_reports_the_character(sanitized_save_path, tmp_path):
    save_path = tmp_path / sanitized_save_path.name
    shutil.copy(sanitized_save_path, save_path)
    shutil.copy(sanitized_save_path, tmp_path / (save_path.name + ".bak"))
    save = Save.from_file(str(save_path))
    i = _used_slot(save)
    pgd = save.character_slots[i].player_game_data

    (source,) = find_game_backups(save_path, i)
    assert source.path.name == save_path.name + ".bak"
    assert source.character == (pgd.character_name, pgd.level)
