"""
Save/game version mismatch fix.

Elden Ring stamps a version number in three places: the global
USER_DATA_10.version, and per-slot version + BaseVersion
(base_version_copy, base_version, is_latest_version). Loading a
save on a newer game build bumps these values immediately, even
without full gameplay on that slot, so touching the character
select screen alone is enough to raise the global stamp. An older
executable then refuses to load the file with a version-incompatible
message.

This does not fit the per-slot BaseFix interface (detect/apply take
a slot_index) since the global stamp and every active slot need to
move together. Kept as a standalone module instead.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.parser import Save

CHECKSUM_SIZE = 0x10
BASE_VERSION_SIZE = 0x10


@dataclass
class SlotVersionInfo:
    """Version stamps found in one active character slot."""

    slot_index: int
    version: int
    base_version: int
    is_latest_version: int


@dataclass
class VersionInfo:
    """Version stamps found across the whole save file."""

    user_data_10_version: int
    slots: list[SlotVersionInfo] = field(default_factory=list)

    @property
    def highest_version(self) -> int:
        """Highest version stamp found anywhere in the file."""
        values = [self.user_data_10_version] + [s.version for s in self.slots]
        return max(values) if values else 0

    @property
    def has_mismatch(self) -> bool:
        """True if any two version stamps in the file disagree."""
        values = {self.user_data_10_version}
        for s in self.slots:
            values.add(s.version)
            values.add(s.base_version)
        return len(values) > 1


@dataclass
class VersionFixResult:
    """Result of applying the version downgrade fix."""

    applied: bool = False
    description: str = ""
    details: list[str] = field(default_factory=list)


def get_version_info(save: Save) -> VersionInfo:
    """Read current version stamps from a save without modifying it."""
    info = VersionInfo(user_data_10_version=save.user_data_10_parsed.version)
    for i, slot in enumerate(save.character_slots):
        if slot.is_empty():
            continue
        info.slots.append(
            SlotVersionInfo(
                slot_index=i,
                version=slot.version,
                base_version=slot.base_version.base_version,
                is_latest_version=slot.base_version.is_latest_version,
            )
        )
    return info


def apply_version_downgrade(save: Save, target_version: int) -> VersionFixResult:
    """
    Rewrite the global and every active per-slot version stamp to
    target_version, then recalculate checksums.

    Does not write to disk - caller is responsible for save.to_file().

    Args:
        save: The save file (will be modified in place)
        target_version: Version number to stamp everywhere

    Returns:
        VersionFixResult describing what changed
    """
    if target_version <= 0:
        return VersionFixResult(
            applied=False, description="Target version must be a positive integer"
        )

    details = []

    # Global USER_DATA_10.version. PS saves have no per-section checksum.
    ud10_offset = save._user_data_10_offset
    version_offset = ud10_offset if save.is_ps else ud10_offset + CHECKSUM_SIZE
    old_global = save.user_data_10_parsed.version
    save._raw_data[version_offset : version_offset + 4] = struct.pack(
        "<I", target_version
    )
    save.user_data_10_parsed.version = target_version
    details.append(f"Global save version: {old_global} -> {target_version}")

    # Per-slot version + BaseVersion for every active slot.
    for i, slot in enumerate(save.character_slots):
        if slot.is_empty():
            continue

        old_slot_version = slot.version
        save._raw_data[slot.data_start : slot.data_start + 4] = struct.pack(
            "<I", target_version
        )
        slot.version = target_version

        old_base_version = slot.base_version.base_version
        slot.base_version.base_version_copy = target_version
        slot.base_version.base_version = target_version
        slot.base_version.is_latest_version = 1

        base_version_offset = slot.steamid_offset - BASE_VERSION_SIZE
        buf = BytesIO()
        slot.base_version.write(buf)
        save._raw_data[
            base_version_offset : base_version_offset + BASE_VERSION_SIZE
        ] = buf.getvalue()

        details.append(
            f"Slot {i + 1}: version {old_slot_version} -> {target_version}, "
            f"base_version {old_base_version} -> {target_version}"
        )

    save.recalculate_checksums()

    return VersionFixResult(
        applied=True,
        description=f"All version stamps set to {target_version}",
        details=details,
    )
