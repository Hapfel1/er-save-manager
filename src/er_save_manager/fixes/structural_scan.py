"""
Structural integrity checks for character slot data.

Independent of deep_scan.py's NetMan/SteamID torn-write detector and of
InventoryCountersFix (which already covers held common_item_count /
key_item_count). These look at internal consistency that neither of
those checks: gaitem_map handle uniqueness, dangling inventory rows,
storage counters, and the size of the world-state struct chain.

RebuildRoundtripFix, DuplicateGaitemHandleFix, and WorldStructSizeFix
are report-only. Each has a detect() but apply() always returns
applied=False with an explanation, there is no correction that is safe
to make without knowing what the correct content should have been.

DanglingInventoryHandleFix and StorageInventoryCountersFix have a
well-defined, reversible correction and behave like any other fix in
this package.

Two checks that were here (duplicate acquisition_index, and
acquisition_index_counter vs actual max) were removed after testing
against real saves. Both assumed acquisition_index and
acquisition_index_counter are directly comparable, they are not: real
saves show acquisition_index running roughly double the counter value,
and legitimate items can share an acquisition_index (simultaneous
pickups). Revisit only with a confirmed model of that relationship.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from er_save_manager.parser.inventory_ops import _patch_slot, _select_inventory
from er_save_manager.parser.slot_rebuild import rebuild_slot_with_map

from .base import BaseFix, FixResult

if TYPE_CHECKING:
    from er_save_manager.parser import Save

# Handle prefixes that identify a real gaitem_map entry. Talisman and
# goods items use a direct handle computed from the item id instead and
# are expected to repeat across stacks, they are excluded everywhere in
# this module that compares against gaitem_map.
_GAITEM_PREFIXES = (0x80000000, 0x90000000, 0xC0000000)

# Observed real-save sizes for the five variable structs between
# event_flags and coordinates stay in the low thousands of bytes at
# most. Absolute sanity bound, not a precise expected value.
_WORLD_STRUCT_SIZE_WARN = 20000

_WORLD_STRUCT_NAMES = (
    "field_area",
    "world_area",
    "world_geom_man",
    "world_geom_man2",
    "rend_man",
)


# Sections rebuild_slot() cannot round-trip faithfully. The parser reads
# these bytes but never stores them anywhere on the slot object, so
# rebuild_slot() has to guess a fixed value (zero) instead of writing
# back what was actually there. A real save can have non-zero content
# here without anything being wrong.
_UNRELIABLE_SECTIONS = {"padding_after_player_coordinates"}


class RebuildRoundtripFix(BaseFix):
    """
    Re-serializes the slot from its parsed fields and compares against
    the raw bytes on disk, up through the end of player_data_hash,
    excluding sections rebuild_slot() is known to guess rather than
    faithfully reproduce (see _UNRELIABLE_SECTIONS). A mismatch outside
    those means some size-prefixed struct's declared size no longer
    matches its actual content, or a tracked offset is stale.

    slot.rest (whatever follows player_data_hash) is excluded on
    purpose, rebuild_slot() itself never writes it, treating it as
    discardable padding, and real saves often have non-zero content
    there that is not corruption.
    """

    name = "Rebuild Round-trip"
    description = (
        "Checks that the slot re-serializes byte-for-byte up through player_data_hash"
    )

    def _compare(self, save: Save, slot) -> tuple[bytes, bytes, int]:
        data_start = slot.data_start
        rebuilt, sections = rebuild_slot_with_map(slot)
        end = sections[-1]["end"] if sections else len(rebuilt)
        raw = bytearray(save._raw_data[data_start : data_start + end])
        rebuilt = bytearray(rebuilt[:end])

        # Mask out unreliable sections identically in both buffers so
        # they can never contribute a difference.
        for section in sections:
            if section["name"] in _UNRELIABLE_SECTIONS:
                s, e = section["start"], section["end"]
                raw[s:e] = b"\x00" * (e - s)
                rebuilt[s:e] = b"\x00" * (e - s)

        return bytes(raw), bytes(rebuilt), end

    def detect(self, save: Save, slot_index: int) -> bool:
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False
        raw, rebuilt, _ = self._compare(save, slot)
        return raw != rebuilt

    def apply(self, save: Save, slot_index: int) -> FixResult:
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        raw, rebuilt, end = self._compare(save, slot)

        if raw == rebuilt:
            return FixResult(applied=False, description="Rebuild matches raw data")

        first_diff = next(
            (i for i in range(len(raw)) if raw[i] != rebuilt[i]), len(raw)
        )
        return FixResult(
            applied=False,
            description="Rebuild mismatch detected, no automatic correction available",
            details=[
                f"First difference at slot offset 0x{first_diff:x}",
                f"Compared 0x{end:x} bytes, excluding the slot.rest tail and known-unreliable sections",
            ],
        )


class DuplicateGaitemHandleFix(BaseFix):
    """
    Checks gaitem_map only for a handle used by more than one entry.
    Talisman and goods rows are not part of gaitem_map and are not
    checked here, they use a direct handle and duplicate by design.
    Report-only, reassigning a handle would also require finding and
    updating whichever inventory row points at it, which needs manual
    review to do safely.
    """

    name = "Duplicate Gaitem Handle"
    description = "Checks gaitem_map for a handle used by more than one entry"

    def _find_duplicates(self, slot) -> list[str]:
        seen: dict[int, int] = {}
        details = []
        for idx, g in enumerate(slot.gaitem_map):
            if g.gaitem_handle == 0:
                continue
            if g.gaitem_handle in seen:
                details.append(
                    f"handle 0x{g.gaitem_handle:08X} used by gaitem_map "
                    f"entries {seen[g.gaitem_handle]} and {idx}"
                )
            else:
                seen[g.gaitem_handle] = idx
        return details

    def detect(self, save: Save, slot_index: int) -> bool:
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False
        return bool(self._find_duplicates(slot))

    def apply(self, save: Save, slot_index: int) -> FixResult:
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        details = self._find_duplicates(slot)
        if not details:
            return FixResult(applied=False, description="No duplicate gaitem handles")

        return FixResult(
            applied=False,
            description="Duplicate gaitem handles found, no automatic correction available",
            details=details,
        )


class WorldStructSizeFix(BaseFix):
    """
    Absolute-bound sanity check on the five variable-size structs between
    event_flags and coordinates (field_area, world_area, world_geom_man,
    world_geom_man2, rend_man). Does not know the correct size, only
    flags sizes far outside what has been observed in real saves.
    Independent of deep_scan.py's NetMan anchor, so this can flag an
    oversized struct even when NetMan/SteamID still line up. Report-only,
    the correct content cannot be reconstructed from the size alone.
    """

    name = "World Struct Size"
    description = "Checks field_area/world_area/world_geom_man/world_geom_man2/rend_man for implausible sizes"

    def _oversized(self, slot) -> list[str]:
        details = []
        for name in _WORLD_STRUCT_NAMES:
            struct_obj = getattr(slot, name, None)
            if struct_obj is None:
                continue
            size = struct_obj.size
            if size < 0 or size > _WORLD_STRUCT_SIZE_WARN:
                details.append(
                    f"{name}.size is {size}, outside expected range "
                    f"(0-{_WORLD_STRUCT_SIZE_WARN})"
                )
        return details

    def detect(self, save: Save, slot_index: int) -> bool:
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False
        return bool(self._oversized(slot))

    def apply(self, save: Save, slot_index: int) -> FixResult:
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        details = self._oversized(slot)
        if not details:
            return FixResult(
                applied=False, description="World struct sizes look plausible"
            )

        return FixResult(
            applied=False,
            description="World struct size out of range, no automatic correction available",
            details=details,
        )


class DanglingInventoryHandleFix(BaseFix):
    """
    Inventory rows carrying a gaitem-style handle (weapon, armor, or gem
    prefix) with no matching gaitem_map entry. The item this row pointed
    to no longer exists, so clearing the row loses nothing recoverable.
    Checks held and storage, common and key items.
    """

    name = "Dangling Inventory Handle"
    description = (
        "Clears inventory rows referencing a gaitem handle that no longer exists"
    )

    def _find(self, slot) -> list[tuple[str, str, int]]:
        gaitem_handles = {
            g.gaitem_handle for g in slot.gaitem_map if g.gaitem_handle != 0
        }
        found = []
        for location in ("held", "storage"):
            inv = _select_inventory(slot, location)
            for kind, items in (("common", inv.common_items), ("key", inv.key_items)):
                for i, it in enumerate(items):
                    h = it.gaitem_handle
                    if (
                        h != 0
                        and (h & 0xF0000000) in _GAITEM_PREFIXES
                        and h not in gaitem_handles
                    ):
                        found.append((location, kind, i))
        return found

    def detect(self, save: Save, slot_index: int) -> bool:
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False
        return bool(self._find(slot))

    def apply(self, save: Save, slot_index: int) -> FixResult:
        from er_save_manager.parser.equipment import InventoryItem

        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        found = self._find(slot)
        if not found:
            return FixResult(applied=False, description="No dangling inventory handles")

        details = []
        for location, kind, i in found:
            inv = _select_inventory(slot, location)
            items = inv.common_items if kind == "common" else inv.key_items
            h = items[i].gaitem_handle
            items[i] = InventoryItem()
            if kind == "common":
                inv.common_item_count = max(0, inv.common_item_count - 1)
            else:
                inv.key_item_count = max(0, inv.key_item_count - 1)
            details.append(f"{location} {kind}_items[{i}]: cleared handle 0x{h:08X}")

        _patch_slot(save, slot_index, slot)

        return FixResult(
            applied=True,
            description=f"Cleared {len(found)} dangling inventory row(s)",
            details=details,
        )


class StorageInventoryCountersFix(BaseFix):
    """
    Same check as InventoryCountersFix, for storage instead of held.
    InventoryCountersFix only covers slot.inventory_held, storage box
    counters are not checked anywhere else.
    """

    name = "Storage Inventory Counters"
    description = "Repairs corrupted storage box item counters"

    def detect(self, save: Save, slot_index: int) -> bool:
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False
        inv = slot.inventory_storage_box
        actual_common = sum(1 for it in inv.common_items if it.gaitem_handle != 0)
        actual_key = sum(1 for it in inv.key_items if it.gaitem_handle != 0)
        return (
            inv.common_item_count != actual_common or inv.key_item_count != actual_key
        )

    def apply(self, save: Save, slot_index: int) -> FixResult:
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        inv = slot.inventory_storage_box
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
            return FixResult(applied=False, description="Storage counters are correct")

        _patch_slot(save, slot_index, slot)

        return FixResult(
            applied=True,
            description="Storage counters repaired",
            details=details,
        )
