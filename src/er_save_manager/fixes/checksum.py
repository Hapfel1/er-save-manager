"""
Slot checksum integrity check and fix.

Each character slot has a 16-byte MD5 checksum stored immediately before
the slot data. The game will not load a slot with an invalid checksum.
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

from .base import BaseFix, FixResult

if TYPE_CHECKING:
    from ..parser import Save

log = logging.getLogger(__name__)

CHECKSUM_SIZE = 0x10
SLOT_SIZE = 0x280000


def check_slot_checksum(save: Save, slot_index: int) -> tuple[bool, str, str]:
    """
    Verify the MD5 checksum for a slot.

    Returns:
        (valid, stored_hex, computed_hex)
    """
    slot = save.character_slots[slot_index]
    if slot.is_empty():
        return (True, "", "")

    slot_data_start = slot.data_start
    checksum_offset = slot_data_start - CHECKSUM_SIZE

    stored = bytes(save._raw_data[checksum_offset : checksum_offset + CHECKSUM_SIZE])
    slot_data = save._raw_data[slot_data_start : slot_data_start + SLOT_SIZE]
    computed = hashlib.md5(slot_data).digest()

    return (stored == computed, stored.hex(), computed.hex())


class SlotChecksumFix(BaseFix):
    """Detects and repairs an invalid slot MD5 checksum."""

    name = "Slot Checksum"
    description = "Recalculates the MD5 checksum for a character slot"

    def detect(self, save: Save, slot_index: int) -> bool:
        valid, _, _ = check_slot_checksum(save, slot_index)
        return not valid

    def apply(self, save: Save, slot_index: int) -> FixResult:
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        valid, stored, computed = check_slot_checksum(save, slot_index)
        if valid:
            return FixResult(applied=False, description="Checksum already valid")

        slot_data_start = slot.data_start
        checksum_offset = slot_data_start - CHECKSUM_SIZE
        new_checksum = bytes.fromhex(computed)
        save._raw_data[checksum_offset : checksum_offset + CHECKSUM_SIZE] = new_checksum

        log.info(
            "[checksum] slot %d: %s -> %s (written to file[0x%x])",
            slot_index,
            stored,
            computed,
            checksum_offset,
        )

        return FixResult(
            applied=True,
            description="Slot checksum recalculated",
            details=[
                f"Stored:   {stored}",
                f"Computed: {computed}",
            ],
        )
