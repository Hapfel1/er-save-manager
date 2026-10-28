"""
DS3 save file - top-level access.

PC saves are BND4 with AES-CBC encrypted entries, PS4 saves a folder of
userdata files (see parser.py).
10 character slots (entries 0-9) + 1 global slot (entry 10).
"""

from __future__ import annotations

from pathlib import Path

from .parser import DS3Parser, DS3PSParser, load_parser
from .slot import DS3Slot


class DS3Save:
    """
    Complete DS3 save file.

    Provides access to all 10 character slots.
    Modifications write through to the slot's bytearray; call save_to_file to persist.
    """

    CHARACTER_SLOTS = 10

    def __init__(
        self, parser: DS3Parser | DS3PSParser, slots: list[DS3Slot | None]
    ) -> None:
        self._parser = parser
        self.characters: list[DS3Slot | None] = slots

    @classmethod
    def from_file(cls, path: str | Path) -> DS3Save:
        parser = load_parser(path)
        slots: list[DS3Slot | None] = []
        for i in range(cls.CHARACTER_SLOTS):
            plaintext = parser.get_slot(i)
            if plaintext is None:
                slots.append(None)
                continue
            data = bytearray(plaintext)
            slot = DS3Slot(i, data)
            slots.append(None if slot.is_empty else slot)
        return cls(parser, slots)

    @classmethod
    def open_checked(cls, path: str | Path) -> DS3Save:
        """from_file for a file picked as a source or target. Raises
        ValueError with a reason for the user when the file is cut off,
        belongs to another game or does not parse."""
        from er_save_manager.games.game_profiles import PROFILES_BY_KEY
        from er_save_manager.games.save_identify import (
            identify_game,
            incomplete_reason,
        )

        if incomplete_reason(path):
            raise ValueError("the file is empty or cut off.")
        owner = identify_game(path)
        if owner is not None and owner != "dark_souls_3":
            profile = PROFILES_BY_KEY.get(owner)
            raise ValueError(
                f"not a Dark Souls III save ({profile.name if profile else owner} "
                "save)."
            )
        try:
            return cls.from_file(path)
        except Exception as exc:
            raise ValueError("not a Dark Souls III save, or it is damaged.") from exc

    @property
    def is_ps(self) -> bool:
        return self._parser.is_ps

    @property
    def has_directory(self) -> bool:
        """True when the global entry (character-select directory) is loaded."""
        return self._parser.has_slot(self.CHARACTER_SLOTS)

    def slot_available(self, slot: int) -> bool:
        """False for a PS4 slot whose userdata file was not loaded."""
        return self._parser.has_slot(slot)

    def missing_slot_message(self, slot: int) -> str:
        return (
            f"Slot {slot + 1} has no {self._parser.file_name(slot)} file "
            "next to the loaded save."
        )

    def save_to_file(self, path: str | Path) -> None:
        """Re-encrypt all modified slots and write."""
        for i, slot in enumerate(self.characters):
            if slot is not None:
                self._parser.set_slot(i, slot.get_raw())
        self._parser.save_to_file(path)
