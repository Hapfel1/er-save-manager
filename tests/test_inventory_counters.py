"""Tests for er_save_manager.fixes.inventory_counters.InventoryCountersFix."""

from __future__ import annotations

from er_save_manager.fixes.inventory_counters import InventoryCountersFix
from er_save_manager.parser import load_save


def _occupied(items):
    return sum(1 for it in items if it.gaitem_handle != 0)


def test_detects_wrong_counts(sanitized_save):
    inv = sanitized_save.character_slots[0].inventory_held
    inv.common_item_count += 50
    assert InventoryCountersFix().detect(sanitized_save, 0) is True
    inv.common_item_count -= 50
    inv.key_item_count -= 1
    assert InventoryCountersFix().detect(sanitized_save, 0) is True


def test_apply_corrects_held_counters_and_persists(sanitized_save, sanitized_save_copy):
    slot = sanitized_save.character_slots[0]
    inv, storage = slot.inventory_held, slot.inventory_storage_box
    common, key = _occupied(inv.common_items), _occupied(inv.key_items)
    inv.common_item_count = common + 100
    inv.key_item_count = key + 1
    storage.common_item_count += 999

    result = InventoryCountersFix().apply(sanitized_save, 0)
    assert result.applied is True and len(result.details) == 2
    assert (inv.common_item_count, inv.key_item_count) == (common, key)
    # The storage box counters are not this fix's business
    assert storage.common_item_count != _occupied(storage.common_items)
    assert InventoryCountersFix().apply(sanitized_save, 0).applied is False

    sanitized_save.recalculate_checksums()
    sanitized_save.to_file(str(sanitized_save_copy))
    reloaded = load_save(str(sanitized_save_copy)).character_slots[0]
    assert reloaded.inventory_held.common_item_count == common


def test_clamps_equip_index_counter_past_array_end(sanitized_save):
    slot = sanitized_save.character_slots[0]
    held, storage = slot.inventory_held, slot.inventory_storage_box
    held_top = len(held.key_items) + len(held.common_items) - 1
    storage_top = len(storage.key_items) + len(storage.common_items) - 1
    held.equip_index_counter = held_top + 90
    storage.equip_index_counter = storage_top + 1

    fix = InventoryCountersFix()
    assert fix.detect(sanitized_save, 0) is True
    assert fix.apply(sanitized_save, 0).applied is True
    assert held.equip_index_counter == held_top
    assert storage.equip_index_counter == storage_top


def test_renumbers_wrapped_acquisition_indices(sanitized_save):
    slot = sanitized_save.character_slots[0]
    held, storage = slot.inventory_held, slot.inventory_storage_box
    fix = InventoryCountersFix()
    assert fix.detect(sanitized_save, 0) is False

    live = [it for it in held.common_items if it.gaitem_handle]
    order = sorted(live, key=lambda it: it.acquisition_index)
    order[0].acquisition_index = 0xC0000000
    assert fix.detect(sanitized_save, 0) is True
    result = fix.apply(sanitized_save, 0)
    assert result.applied is True
    assert order[0].acquisition_index == max(
        it.acquisition_index
        for it in held.common_items + held.key_items
        if it.gaitem_handle
    )
    assert fix.detect(sanitized_save, 0) is False

    storage.acquisition_index_counter = 0x7FFFFC02
    assert fix.detect(sanitized_save, 0) is True
    fix.apply(sanitized_save, 0)
    assert (
        storage.acquisition_index_counter
        == _occupied(storage.common_items) + _occupied(storage.key_items) + 1
    )
