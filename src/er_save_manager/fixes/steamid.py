"""SteamID sync fix - fixes mismatch between character and save SteamID."""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

from er_save_manager.fixes.base import BaseFix, FixResult

if TYPE_CHECKING:
    from er_save_manager.parser import Save


class SteamIdFix(BaseFix):
    """
    Fix for SteamID mismatch.

    The character slot's SteamID should match the save file's SteamID
    stored in USER_DATA_10. A mismatch can cause loading issues.
    """

    name = "SteamID Mismatch"
    description = "Syncs character SteamID with save file SteamID"

    def detect(self, save: Save, slot_index: int) -> bool:
        """Check if SteamID is mismatched."""
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return False

        correct_steam_id = self._get_save_steam_id(save)
        return slot.has_steamid_corruption(correct_steam_id)

    def apply(self, save: Save, slot_index: int) -> FixResult:
        """Sync character SteamID to save SteamID."""
        slot = self.get_slot(save, slot_index)

        if slot.is_empty():
            return FixResult(applied=False, description="Slot is empty")

        correct_steam_id = self._get_save_steam_id(save)
        if correct_steam_id is None:
            return FixResult(
                applied=False,
                description="Could not read save SteamID from USER_DATA_10",
            )

        if not slot.has_steamid_corruption(correct_steam_id):
            return FixResult(applied=False, description="SteamID already matches")

        # Store original for logging
        original_steam_id = slot.steam_id

        # Update in memory
        slot.steam_id = correct_steam_id

        # Write to raw data
        if hasattr(slot, "steamid_offset") and slot.steamid_offset > 0:
            steamid_bytes = struct.pack("<Q", correct_steam_id)
            save._raw_data[slot.steamid_offset : slot.steamid_offset + 8] = (
                steamid_bytes
            )

            return FixResult(
                applied=True,
                description=f"SteamID synced to {correct_steam_id}",
                details=[
                    f"Original: {original_steam_id}",
                    f"New: {correct_steam_id}",
                ],
            )

        return FixResult(applied=False, description="Could not write SteamID")

    def _get_save_steam_id(self, save: Save) -> int | None:
        """Get the correct SteamID from USER_DATA_10."""
        if save.user_data_10_parsed and hasattr(save.user_data_10_parsed, "steam_id"):
            return save.user_data_10_parsed.steam_id
        return None
