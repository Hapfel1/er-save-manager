"""
Tests for er_save_manager.fixes.inventory_counters.InventoryCountersFix.
"""

from __future__ import annotations

import os
import tempfile

from er_save_manager.fixes.inventory_counters import InventoryCountersFix


def _first_active_slot(save):
    for i, slot in enumerate(save.character_slots):
        if not slot.is_empty():
            return i
    raise AssertionError("fixture save has no active character slots")


def test_no_false_positive_on_healthy_save(sanitized_save):
    fix = InventoryCountersFix()
    for i, slot in enumerate(sanitized_save.character_slots):
        if slot.is_empty():
            continue
        assert fix.detect(sanitized_save, i) is False, f"slot {i} unexpectedly flagged"


def test_detects_inflated_common_item_count(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    slot.inventory_held.common_item_count += 50

    assert InventoryCountersFix().detect(sanitized_save, i) is True


def test_detects_deflated_key_item_count(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    slot.inventory_held.key_item_count = max(0, slot.inventory_held.key_item_count - 1)

    assert InventoryCountersFix().detect(sanitized_save, i) is True


def test_apply_corrects_both_counters_independently(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    inv = slot.inventory_held
    actual_common = sum(1 for it in inv.common_items if it.gaitem_handle != 0)
    actual_key = sum(1 for it in inv.key_items if it.gaitem_handle != 0)

    inv.common_item_count = actual_common + 100
    inv.key_item_count = actual_key + 1

    result = InventoryCountersFix().apply(sanitized_save, i)

    assert result.applied is True
    assert inv.common_item_count == actual_common
    assert inv.key_item_count == actual_key
    assert len(result.details) == 2


def test_apply_persists_to_raw_data(sanitized_save):
    from er_save_manager.parser import load_save

    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    inv = slot.inventory_held
    actual_common = sum(1 for it in inv.common_items if it.gaitem_handle != 0)
    inv.common_item_count = actual_common + 7

    InventoryCountersFix().apply(sanitized_save, i)

    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "out.co2")
        sanitized_save.recalculate_checksums()
        sanitized_save.to_file(p)
        reloaded = load_save(p)
        assert reloaded.character_slots[i].inventory_held.common_item_count == (
            actual_common
        )


def test_apply_is_no_op_when_counters_already_correct(sanitized_save):
    i = _first_active_slot(sanitized_save)
    result = InventoryCountersFix().apply(sanitized_save, i)
    assert result.applied is False


def test_does_not_touch_storage_box_counters(sanitized_save):
    i = _first_active_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    slot.inventory_held.common_item_count += 10
    slot.inventory_storage_box.common_item_count += 999  # deliberately wrong too

    InventoryCountersFix().apply(sanitized_save, i)

    assert slot.inventory_storage_box.common_item_count != sum(
        1 for it in slot.inventory_storage_box.common_items if it.gaitem_handle != 0
    )
