"""Base interface for corruption fixes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..parser import Save, UserDataX


@dataclass
class FixResult:
    """Result of applying a fix."""

    applied: bool = False
    description: str = ""
    details: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.applied


class BaseFix(ABC):
    """
    Base class for all corruption fixes.

    Each fix should:
    1. Detect if the issue is present
    2. Apply the fix if needed
    3. Return a FixResult with details
    """

    name: str = "Base Fix"
    description: str = "Base fix class"

    @abstractmethod
    def detect(self, save: Save, slot_index: int) -> bool:
        """
        Check if this fix is needed for the given slot.

        Args:
            save: The save file
            slot_index: Character slot index (0-9)

        Returns:
            True if the fix is needed
        """
        ...

    @abstractmethod
    def apply(self, save: Save, slot_index: int) -> FixResult:
        """
        Apply the fix to the given slot.

        Args:
            save: The save file (will be modified)
            slot_index: Character slot index (0-9)

        Returns:
            FixResult with details of what was changed
        """
        ...

    def get_slot(self, save: Save, slot_index: int) -> UserDataX:
        """Get a character slot with validation."""
        if slot_index < 0 or slot_index >= 10:
            raise IndexError(f"Slot index must be 0-9, got {slot_index}")
        return save.character_slots[slot_index]
