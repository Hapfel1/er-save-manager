"""Tests for er_save_manager.fixes.version_mismatch."""

from __future__ import annotations

from er_save_manager.fixes.version_mismatch import (
    ITEM_HISTORY_OLD_LAYOUT_MAX_VERSION,
    slots_with_item_history_mismatch,
)


def test_item_history_mismatch_follows_the_layout_boundary(sanitized_save):
    slot = sanitized_save.character_slots[0]
    assert slot.gaitem_game_data.count > 0
    old, new = (
        ITEM_HISTORY_OLD_LAYOUT_MAX_VERSION,
        ITEM_HISTORY_OLD_LAYOUT_MAX_VERSION + 1,
    )
    same, other = (new, old) if slot.gaitem_game_data.record_size == 8 else (old, new)
    assert 0 not in slots_with_item_history_mismatch(sanitized_save, same)
    assert 0 in slots_with_item_history_mismatch(sanitized_save, other)
