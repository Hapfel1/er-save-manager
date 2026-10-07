"""
Generic SteamID patcher for unencrypted BND4/SL2 save files (Elden Ring).

DS3, Nightreign and AC6 saves are encrypted, so the SteamID is not visible
in the raw file and they have their own patchers. DS2 needs no patch, and
Sekiro and DSR are handled separately in the SteamID patcher tab.

Strategy: scan the file for all 8-byte occurrences of the old SteamID
(little-endian uint64) and replace them with the new SteamID. This is
safe because a 64-bit Steam ID in the range 0x01100001_00000000 to
0x01100001_FFFFFFFF is effectively unique in a save file - accidental
collision with game data is negligible, and all known games store the
ID as a plain LE uint64.

If the old SteamID is unknown (e.g. loading a file from a different
account), callers can pass old_steamid=None to replace ALL occurrences
of any valid Steam64 ID range value matching a single candidate found
by scanning. The scan returns an error if multiple distinct IDs are
found and no explicit old_steamid is given.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

from er_save_manager.own_writes import record_write

# Steam64 ID base constant - all valid IDs are above this
_STEAM64_BASE = 0x0110000100000000
_STEAM64_MAX = 0x01100001FFFFFFFF

BND4_MAGIC = b"BND4"


@dataclass
class PatchResult:
    success: bool
    replacements: int = 0
    old_steamid: int = 0
    new_steamid: int = 0
    error: str = ""
    offsets: list[int] = field(default_factory=list)


def _is_valid_steam64(value: int) -> bool:
    return _STEAM64_BASE <= value <= _STEAM64_MAX


# Every valid Steam64 value has this 4-byte little-endian upper half, so the
# scan only needs a C-speed byte search instead of unpacking every offset.
_STEAM64_HIGH = struct.pack("<I", _STEAM64_BASE >> 32)


def find_steamids_in_file(data: bytes | bytearray) -> dict[int, list[int]]:
    """
    Scan file bytes for all occurrences of valid Steam64 IDs.

    Returns a dict mapping steamid -> list[offset]. Offsets are unaligned
    and matches do not overlap.
    """
    found: dict[int, list[int]] = {}
    search = bytes(data)
    next_free = 0
    pos = search.find(_STEAM64_HIGH, 4)
    while pos != -1:
        start = pos - 4
        if start >= next_free:
            val = struct.unpack_from("<Q", search, start)[0]
            found.setdefault(val, []).append(start)
            next_free = start + 8
        pos = search.find(_STEAM64_HIGH, pos + 1)
    return found


def patch_steamid_generic(
    save_path: Path,
    new_steamid: int,
    old_steamid: int | None = None,
) -> PatchResult:
    """
    Patch all occurrences of old_steamid with new_steamid in an SL2 file.

    If old_steamid is None, scans the file to detect the existing ID.
    Fails if the file doesn't start with BND4 magic.
    Fails if old_steamid is None and multiple distinct IDs are found.

    Writes the patched file in-place.
    """
    data = bytearray(save_path.read_bytes())

    if data[:4] != BND4_MAGIC:
        return PatchResult(
            success=False,
            error=f"Not a valid BND4/SL2 file (magic: {data[:4].hex()})",
        )

    if not _is_valid_steam64(new_steamid):
        return PatchResult(
            success=False,
            error=f"Invalid Steam64 ID: {new_steamid}",
        )

    if old_steamid is None:
        found = find_steamids_in_file(data)
        if not found:
            return PatchResult(success=False, error="No Steam64 ID found in file")
        if len(found) > 1:
            ids_str = ", ".join(str(k) for k in sorted(found))
            return PatchResult(
                success=False,
                error=(
                    f"Multiple distinct Steam64 IDs found: {ids_str}. "
                    "Please specify old_steamid explicitly."
                ),
            )
        old_steamid = next(iter(found))

    if old_steamid == new_steamid:
        return PatchResult(
            success=True,
            replacements=0,
            old_steamid=old_steamid,
            new_steamid=new_steamid,
        )

    old_bytes = struct.pack("<Q", old_steamid)
    new_bytes = struct.pack("<Q", new_steamid)

    offsets = []
    i = 0
    end = len(data) - 7
    while i <= end:
        if data[i : i + 8] == old_bytes:
            data[i : i + 8] = new_bytes
            offsets.append(i)
            i += 8
        else:
            i += 1

    if not offsets:
        return PatchResult(
            success=False,
            old_steamid=old_steamid,
            new_steamid=new_steamid,
            error=f"SteamID {old_steamid} not found in file",
        )

    tmp_path = save_path.with_suffix(save_path.suffix + ".tmp")
    tmp_path.write_bytes(data)
    tmp_path.replace(save_path)
    record_write(save_path)

    return PatchResult(
        success=True,
        replacements=len(offsets),
        old_steamid=old_steamid,
        new_steamid=new_steamid,
        offsets=offsets,
    )


def detect_steamid_in_file(save_path: Path) -> int | None:
    """
    Return the SteamID found in the save file, or None on error.

    For unencrypted BND4 saves (ER, DS3, DS2, DSR): finds the most
    frequently occurring valid Steam64 value via byte scan.

    For Nightreign (AES-CBC encrypted entries): decrypts entry 10 and
    reads the Steam64 at offset 0x8.

    Returns None if no ID can be determined.
    """
    try:
        data = save_path.read_bytes()
    except OSError:
        return None

    if data[:4] != BND4_MAGIC:
        return None

    found = find_steamids_in_file(data)
    if found:
        return max(found, key=lambda k: len(found[k]))

    # No plaintext Steam64 found - try encrypted-entry detection (NR / AC6)
    try:
        from er_save_manager.games.nightreign_steamid import detect_steamid_nr

        sid = detect_steamid_nr(save_path)
        if sid:
            return sid
    except Exception:
        pass

    try:
        from er_save_manager.games.ac6_steamid import detect_steamid_ac6

        sid = detect_steamid_ac6(save_path)
        if sid:
            return sid
    except Exception:
        pass

    try:
        from er_save_manager.games.ds3_steamid import detect_steamid_ds3

        sid = detect_steamid_ds3(save_path)
        if sid:
            return sid
    except Exception:
        pass

    try:
        from er_save_manager.games.sekiro_steamid import detect_steamid_sekiro

        sid = detect_steamid_sekiro(save_path)
        if sid:
            return sid
    except Exception:
        pass

    # DS2: AES-encrypted, byte-scan after decrypt
    try:
        from er_save_manager.games.ds2_dsr_steamid import detect_steamid

        name = save_path.name.lower()
        if name.startswith("ds2") or name.startswith("darksii"):
            return detect_steamid(save_path, "dark_souls_2")
    except Exception:
        pass

    return None
