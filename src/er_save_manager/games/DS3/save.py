"""
DS3 save file - top-level access.

DS3 uses BND4 with AES-CBC encrypted entries (see parser.py).
10 character slots (entries 0-9) + 1 global slot (entry 10).
"""

from __future__ import annotations

from pathlib import Path

from .parser import DS3Parser
from .slot import DS3Slot


class DS3Save:
    """
    Complete DS3 save file.

    Provides access to all 10 character slots.
    Modifications write through to the slot's bytearray; call save_to_file to persist.
    """

    CHARACTER_SLOTS = 10

    def __init__(self, parser: DS3Parser, slots: list[DS3Slot | None]) -> None:
        self._parser = parser
        self.characters: list[DS3Slot | None] = slots

    @classmethod
    def from_file(cls, path: str | Path) -> DS3Save:
        parser = DS3Parser.from_file(path)
        slots: list[DS3Slot | None] = []
        for i in range(cls.CHARACTER_SLOTS):
            data = bytearray(parser.get_slot(i))
            slot = DS3Slot(i, data)
            slots.append(None if slot.is_empty else slot)
        return cls(parser, slots)

    def save_to_file(self, path: str | Path) -> None:
        """Re-encrypt all modified slots and write."""
        for i, slot in enumerate(self.characters):
            if slot is not None:
                self._parser.set_slot(i, slot.get_raw())
        self._parser.save_to_file(path)

    def get_character(self, slot: int) -> DS3Slot | None:
        if not 0 <= slot < self.CHARACTER_SLOTS:
            raise IndexError(f"Slot {slot} out of range (0-9)")
        return self.characters[slot]
