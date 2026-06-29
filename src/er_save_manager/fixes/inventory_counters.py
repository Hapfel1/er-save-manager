"""Fix for corrupted inventory item counters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from er_save_manager.fixes.base import BaseFix, FixResult
from er_save_manager.parser.inventory_ops import _patch_slot

if TYPE_CHECKING:
    from er_save_manager.parser import Save


class InventoryCountersFix(BaseFix):
    """
    Fix for corrupted common_item_count and key_item_count.

    The game uses these counters to gate new item pickups, so an
    inflated or negative count causes the "no space" message even when
    the inventory arrays have free slots, and in severe cases causes crashes
    on load.

    The fix counts actual occupied slots in the arrays and writes the
    correct values back.
    """

    name = "Inventory Counters"
    description = "Repairs corrupted held inventory item counters"

    def detect(self, save: Save, slot_index: int) -> bool:
        slot = self.get_slot(save, slot_index)
        if slot is None or slot.is_empty():
            return False
        inv = slot.inventory_held
        actual_common = sum(1 for it in inv.common_items if it.gaitem_handle != 0)
        actual_key = sum(1 for it in inv.key_items if it.gaitem_handle != 0)
        return (
            inv.common_item_count != actual_common or inv.key_item_count != actual_key
        )

    def apply(self, save: Save, slot_index: int) -> FixResult:
        slot = self.get_slot(save, slot_index)
        if slot is None or slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        inv = slot.inventory_held
        actual_common = sum(1 for it in inv.common_items if it.gaitem_handle != 0)
        actual_key = sum(1 for it in inv.key_items if it.gaitem_handle != 0)

        details = []
        changed = False

        if inv.common_item_count != actual_common:
            details.append(
                f"common_item_count: {inv.common_item_count} -> {actual_common}"
            )
            inv.common_item_count = actual_common
            changed = True

        if inv.key_item_count != actual_key:
            details.append(f"key_item_count: {inv.key_item_count} -> {actual_key}")
            inv.key_item_count = actual_key
            changed = True

        if not changed:
            return FixResult(
                applied=False, description="Inventory counters are correct"
            )

        _patch_slot(save, slot_index, slot)

        return FixResult(
            applied=True,
            description="Inventory counters repaired",
            details=details,
        )
