"""
Deep scan fix for torn write corruption.

Torn writes insert or remove bytes mid-slot, shifting everything after
the insertion point. Standard fixes fail because offsets tracked by the
parser are wrong.

Strategy:
  1. Search raw slot bytes for the known SteamID64 (from USER_DATA_10).
  2. Walk backward from SteamID64 using fixed-size trailing structs to
     locate where NetMan must start (NetMan is 0x20004 bytes, fixed).
  3. Compare that against the expected NetMan start (event_flags_end +
     variable-sized structs). The sized structs are opaque but their
     size fields are intact, so we can sum them up from event_flags_end.
  4. The delta between expected and actual is the shift amount. Cut or
     pad at the boundary right after event flags end.
  5. Re-parse the corrected slot to validate.

NetMan anchor math (backward from steam_id):
  steam_id        8 bytes
  BaseVersion    16 bytes
  WorldAreaTime  12 bytes
  WorldAreaWeather 12 bytes
  NetMan        0x20004 bytes
  => NetMan start = steam_id_offset - 8 - 16 - 12 - 12 - 0x20004
                  = steam_id_offset - 0x20030
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .base import BaseFix, FixResult

if TYPE_CHECKING:
    from ..parser import Save

log = logging.getLogger(__name__)

# Fixed size of trailing structs between NetMan end and steam_id
# NetMan(0x20004) + unk4(4) + WorldAreaWeather(12) + WorldAreaTime(12) + BaseVersion(16)
_NETMAN_SIZE = 0x20004
_TAIL_AFTER_NETMAN = 4 + 12 + 12 + 16  # unk4 + weather + time + base_version = 0x2c
_STEAM_ID_TO_NETMAN_START = _NETMAN_SIZE + _TAIL_AFTER_NETMAN  # 0x20030

# Version-specific extras between sized structs and NetMan
# PlayerCoordinates(57) + 2pad + spawn(4) + game_man(4) = 67 bytes minimum
# version>=65 adds 4, version>=66 adds 1
_PRE_NETMAN_FIXED_BASE = 57 + 2 + 4 + 4  # 67 bytes
_PRE_NETMAN_V65_EXTRA = 4
_PRE_NETMAN_V66_EXTRA = 1

# Event flags size is fixed
_EVENT_FLAGS_SIZE = 0x1BF99F
_EVENT_FLAGS_TERMINATOR = 1

# How many bytes to sample for post-fix validation
_VALIDATION_SAMPLE = 64


@dataclass
class DeepScanResult:
    """Result of deep scan with shift details."""

    steamid_found: bool = False
    steamid_offset_in_slot: int = 0  # relative to slot data start
    expected_steamid_offset: int = 0  # what parser tracked
    delta: int = 0  # actual - expected (positive = bytes inserted)
    shift_point: int = 0  # relative offset where cut/pad should happen (for insertion)
    netman_start: int = 0  # NetMan start derived from SteamID pivot (for removal)
    confidence: str = "none"  # "high", "medium", "low", "none"
    details: list[str] = field(default_factory=list)


class DeepScanFix(BaseFix):
    """
    Deep scan fix for torn write corruption.

    Use when standard fixes fail to resolve SteamID mismatch.
    Searches for SteamID64 in raw slot data, computes byte shift,
    and corrects the slot by cutting or padding at the shift point.
    """

    name = "Deep Scan (Torn Write)"
    description = "Detects and repairs byte-shift corruption from torn writes"

    def detect(self, save: Save, slot_index: int) -> bool:
        """Run deep scan to check if a repairable shift exists."""
        result = self._scan(save, slot_index)
        return (
            result.steamid_found
            and result.delta != 0
            and result.confidence in ("high", "medium")
        )

    def apply(self, save: Save, slot_index: int) -> FixResult:
        """Apply the shift correction."""
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            log.debug("[deep_scan] slot %d is empty, skipping", slot_index)
            return FixResult(applied=False, description="Slot is empty")

        correct_steam_id = self._get_save_steam_id(save)
        if correct_steam_id is None:
            log.debug("[deep_scan] no SteamID in USER_DATA_10")
            return FixResult(
                applied=False, description="Cannot read SteamID from USER_DATA_10"
            )

        result = self._scan(save, slot_index)

        if not result.steamid_found:
            log.warning(
                "[deep_scan] SteamID64 not found in slot %d raw data", slot_index
            )
            return FixResult(
                applied=False, description="SteamID64 not found in slot data"
            )

        if result.delta == 0:
            log.debug("[deep_scan] no shift detected for slot %d", slot_index)
            return FixResult(applied=False, description="No shift detected")

        if result.confidence not in ("high", "medium"):
            log.warning(
                "[deep_scan] confidence too low (%s) to auto-repair slot %d",
                result.confidence,
                slot_index,
            )
            return FixResult(
                applied=False,
                description=f"Confidence too low to auto-repair: {result.confidence}",
                details=result.details,
            )

        slot_data_start = slot.data_start  # absolute file offset (after checksum)
        slot_size = 0x280000
        delta = result.delta

        # Splice point: found_steamid_rel - 0x28.
        # Derived from reference fix: the splice falls 0x28 bytes before the misplaced
        # SteamID, inside the NetMan data region. Inserting |delta| zeros here (or
        # removing delta bytes) shifts the SteamID and everything after it to the
        # correct position without disturbing the struct zone size fields.
        _SPLICE_BEFORE_STEAMID = 0x28
        shift_point = result.steamid_offset_in_slot - _SPLICE_BEFORE_STEAMID

        log.info(
            "[deep_scan] slot %d: delta=%+d (0x%x), shift_point=slot+0x%x, confidence=%s",
            slot_index,
            delta,
            abs(delta),
            shift_point,
            result.confidence,
        )

        slot_raw = bytearray(
            save._raw_data[slot_data_start : slot_data_start + slot_size]
        )

        if shift_point <= 0 or shift_point >= slot_size:
            log.error("[deep_scan] invalid shift_point 0x%x", shift_point)
            return FixResult(
                applied=False, description=f"Invalid shift point 0x{shift_point:x}"
            )

        log.debug(
            "[deep_scan] bytes at found SteamID (slot+0x%x): %s",
            result.steamid_offset_in_slot,
            slot_raw[
                result.steamid_offset_in_slot : result.steamid_offset_in_slot + 16
            ].hex(),
        )

        if delta > 0:
            if shift_point + delta > slot_size:
                return FixResult(applied=False, description="Shift exceeds slot bounds")
            log.info(
                "[deep_scan] removing %d (0x%x) bytes at slot+0x%x",
                delta,
                delta,
                shift_point,
            )
            corrected = bytearray(slot_raw[:shift_point])
            corrected += slot_raw[shift_point + delta :]
            corrected += b"\x00" * delta
        else:
            pad = abs(delta)
            log.info(
                "[deep_scan] inserting %d (0x%x) zero bytes at slot+0x%x",
                pad,
                pad,
                shift_point,
            )
            corrected = bytearray(slot_raw[:shift_point])
            corrected += b"\x00" * pad
            corrected += slot_raw[shift_point:]
            corrected = corrected[:slot_size]

        if len(corrected) != slot_size:
            log.error(
                "[deep_scan] corrected slot size mismatch: %d != %d",
                len(corrected),
                slot_size,
            )
            return FixResult(
                applied=False,
                description=f"Corrected slot size mismatch: {len(corrected)} != {slot_size}",
            )

        # Validate: SteamID should now be at expected offset
        corrected_steamid_bytes = corrected[
            result.expected_steamid_offset : result.expected_steamid_offset + 8
        ]
        corrected_steamid = (
            struct.unpack_from("<Q", corrected_steamid_bytes)[0]
            if len(corrected_steamid_bytes) == 8
            else None
        )
        steamid_ok = corrected_steamid == correct_steam_id

        log.info(
            "[deep_scan] post-fix SteamID at slot+0x%x: %s (expected %d, got %s)",
            result.expected_steamid_offset,
            "OK" if steamid_ok else "MISMATCH",
            correct_steam_id,
            corrected_steamid,
        )

        # Check for zeroed-out data around the SteamID — indicates the fix
        # landed in padding rather than real data
        check_start = max(0, result.expected_steamid_offset - 64)
        check_end = min(len(corrected), result.expected_steamid_offset + 64)
        neighbourhood = corrected[check_start:check_end]
        zero_ratio = (
            neighbourhood.count(0) / len(neighbourhood) if neighbourhood else 1.0
        )

        log.debug(
            "[deep_scan] post-fix neighbourhood [slot+0x%x..0x%x]: %s",
            check_start,
            check_end,
            neighbourhood.hex(),
        )
        log.info(
            "[deep_scan] post-fix zero ratio in SteamID neighbourhood: %.1f%%",
            zero_ratio * 100,
        )

        if zero_ratio > 0.9:
            log.warning(
                "[deep_scan] post-fix data around SteamID is >90%% zeros — fix may have landed in padding"
            )

        # Validate NetMan region post-fix: after fix, NetMan should be at expected_netman
        netman_start = result.expected_steamid_offset - _STEAM_ID_TO_NETMAN_START
        if 0 <= netman_start < len(corrected) - _VALIDATION_SAMPLE:
            netman_sample = corrected[netman_start : netman_start + _VALIDATION_SAMPLE]
            netman_zero_ratio = netman_sample.count(0) / _VALIDATION_SAMPLE
            log.debug(
                "[deep_scan] post-fix NetMan region [slot+0x%x]: %s",
                netman_start,
                netman_sample.hex(),
            )
            log.info(
                "[deep_scan] post-fix NetMan zero ratio: %.1f%%",
                netman_zero_ratio * 100,
            )
            if netman_zero_ratio > 0.9:
                log.warning(
                    "[deep_scan] post-fix NetMan region looks zeroed — may indicate wrong shift point"
                )

        # Write corrected data back
        save._raw_data[slot_data_start : slot_data_start + slot_size] = corrected
        log.info("[deep_scan] wrote corrected slot data back to file buffer")

        # Recalculate checksum for this slot
        _recalculate_slot_checksum(save, slot_index, slot_data_start)

        validation_note = (
            "SteamID verified at correct offset"
            if steamid_ok
            else "WARNING: SteamID not at expected offset after fix"
        )
        zero_note = f"Neighbourhood zero ratio: {zero_ratio:.0%}" + (
            " (suspicious)" if zero_ratio > 0.9 else " (ok)"
        )

        return FixResult(
            applied=True,
            description=f"Torn write corrected: {'+' if delta > 0 else ''}{delta} bytes at offset 0x{shift_point:x}",
            details=result.details
            + [
                f"SteamID found at slot+0x{result.steamid_offset_in_slot:x}",
                f"Expected at slot+0x{result.expected_steamid_offset:x}",
                f"Confidence: {result.confidence}",
                validation_note,
                zero_note,
                "Checksum recalculated",
            ],
        )

    def scan_only(self, save: Save, slot_index: int) -> DeepScanResult:
        """Public method to run scan and return details without modifying."""
        return self._scan(save, slot_index)

    # ------------------------------------------------------------------
    # Internal

    def _scan(self, save: Save, slot_index: int) -> DeepScanResult:
        result = DeepScanResult()

        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            log.debug("[deep_scan] _scan: slot %d is empty", slot_index)
            return result

        correct_steam_id = self._get_save_steam_id(save)
        if not correct_steam_id:
            log.debug("[deep_scan] _scan: no SteamID in USER_DATA_10")
            result.details.append("No SteamID in USER_DATA_10")
            return result

        log.debug(
            "[deep_scan] _scan slot %d: correct_steam_id=%d, slot.steam_id=%s",
            slot_index,
            correct_steam_id,
            getattr(slot, "steam_id", "N/A"),
        )

        slot_data_start = slot.data_start
        slot_size = 0x280000
        slot_raw = save._raw_data[slot_data_start : slot_data_start + slot_size]

        log.debug(
            "[deep_scan] _scan: slot.data_start=0x%x, slot.steamid_offset=0x%x, slot.event_flags_offset=0x%x",
            slot_data_start,
            getattr(slot, "steamid_offset", -1),
            getattr(slot, "event_flags_offset", -1),
        )

        steamid_bytes = struct.pack("<Q", correct_steam_id)
        found_offsets = _find_all(slot_raw, steamid_bytes)

        log.info(
            "[deep_scan] _scan: searched slot for SteamID %d — found at offsets: %s",
            correct_steam_id,
            [hex(o) for o in found_offsets],
        )

        if not found_offsets:
            log.warning("[deep_scan] _scan: SteamID not found in slot %d", slot_index)
            result.details.append(f"SteamID64 {correct_steam_id} not found in slot")
            return result

        # Use a single SteamID occurrence — if multiple, take the one that gives a
        # netman_start consistent with event_flags_end (i.e. netman_start > ef_end).
        # event_flags_offset is an absolute file offset (f.tell() on the full file stream).
        # Convert to slot-relative by subtracting slot_data_start.
        if (
            hasattr(slot, "event_flags_offset")
            and slot.event_flags_offset > slot_data_start
        ):
            ef_rel = slot.event_flags_offset - slot_data_start
            ef_end_rel = ef_rel + _EVENT_FLAGS_SIZE + _EVENT_FLAGS_TERMINATOR
            log.debug(
                "[deep_scan] event_flags_offset abs=0x%x -> rel=0x%x, ef_end_rel=0x%x",
                slot.event_flags_offset,
                ef_rel,
                ef_end_rel,
            )
        else:
            ef_end_rel = 0

        best = None
        netman_start_from_steamid = 0
        for candidate in found_offsets:
            ns = candidate - _STEAM_ID_TO_NETMAN_START
            if ns > ef_end_rel:
                best = candidate
                netman_start_from_steamid = ns
                break
        if best is None:
            # Fallback: closest to any reasonable netman position
            best = found_offsets[0]
            netman_start_from_steamid = best - _STEAM_ID_TO_NETMAN_START

        result.steamid_found = True
        result.steamid_offset_in_slot = best
        result.netman_start = netman_start_from_steamid

        # Early-out: if SteamID is already at the parser's tracked position, no shift.
        if hasattr(slot, "steamid_offset") and slot.steamid_offset > slot_data_start:
            expected_sid_rel = slot.steamid_offset - slot_data_start
            if best == expected_sid_rel:
                log.debug(
                    "[deep_scan] _scan: SteamID already at correct offset slot+0x%x, delta=0",
                    best,
                )
                result.delta = 0
                return result

        if len(found_offsets) > 1:
            log.debug("[deep_scan] _scan: multiple SteamID hits, using best candidate")
            result.details.append(
                f"Multiple SteamID occurrences: {[hex(o) for o in found_offsets]}"
            )

        log.info(
            "[deep_scan] _scan: SteamID at slot+0x%x, NetMan start from pivot = slot+0x%x",
            best,
            netman_start_from_steamid,
        )
        result.details.append(
            f"NetMan start (from pivot): slot+0x{netman_start_from_steamid:x}"
        )

        # Walk sized structs from ef_end in raw data to find expected_netman.
        # Size fields are intact even in a torn write — only content is shifted.
        # Layout after event_flags_end:
        #   FieldArea:      4 + size
        #   WorldArea:      4 + size
        #   WorldGeomMan:   4 + size
        #   WorldGeomMan2:  4 + size
        #   RendMan:        4 + size
        #   PlayerCoords:   57
        #   pad:             2
        #   spawn:           4
        #   game_man:        4
        #   (version>=65):   4
        #   (version>=66):   1
        # Walk 5 sized structs forward from ef_end to find expected_netman.
        # The struct size fields encode the CORRUPTED sizes (torn write inflated them),
        # so the walk lands at the wrong var_zone_end relative to found_netman.
        # That divergence IS the delta.
        #
        # walk_netman = walk_end + fixed_tail
        # delta = found_netman - walk_netman
        # (negative = bytes removed from slot, walk overshoots found_netman)

        version = getattr(slot, "version", 0)
        fixed_tail = 57 + 2 + 4 + 4  # PlayerCoords + pad + spawn + game_man
        if version >= 65:
            fixed_tail += 4
        if version >= 66:
            fixed_tail += 1

        if ef_end_rel <= 0 or ef_end_rel >= len(slot_raw):
            log.warning("[deep_scan] _scan: ef_end_rel=0x%x out of bounds", ef_end_rel)
            result.details.append("event_flags_offset out of bounds")
            return result

        pos = ef_end_rel
        log.debug(
            "[deep_scan] version=%d, fixed_tail=%d, ef_end_rel=0x%x",
            version,
            fixed_tail,
            ef_end_rel,
        )
        for sname in (
            "FieldArea",
            "WorldArea",
            "WorldGeomMan",
            "WorldGeomMan2",
            "RendMan",
        ):
            if pos + 4 > len(slot_raw):
                log.warning(
                    "[deep_scan] struct walk: %s size field out of bounds at slot+0x%x",
                    sname,
                    pos,
                )
                result.details.append(f"Struct walk OOB at {sname}")
                return result
            sz = struct.unpack_from("<i", slot_raw, pos)[0]
            if sz < 0 or sz > 0x200000:
                log.warning(
                    "[deep_scan] struct walk: %s size=0x%x out of range at slot+0x%x",
                    sname,
                    sz,
                    pos,
                )
                result.details.append(f"Struct walk invalid size at {sname}: 0x{sz:x}")
                return result
            log.debug(
                "[deep_scan] %s at slot+0x%x: size=0x%x -> end=slot+0x%x",
                sname,
                pos,
                sz,
                pos + 4 + sz,
            )
            if sz == 0 and sname in (
                "WorldArea",
                "WorldGeomMan",
                "WorldGeomMan2",
                "RendMan",
            ):
                # Zero size for a struct that should have content.
                # Struct zone was likely patched already (zeroed region wiped a size field).
                # Use pivot position as authoritative: if netman_start_from_steamid is in a
                # plausible range, treat as clean.
                if netman_start_from_steamid > ef_end_rel + fixed_tail:
                    log.debug(
                        "[deep_scan] walk: zero size for %s, pivot looks valid — "
                        "struct zone appears post-fix, delta=0",
                        sname,
                    )
                    result.delta = 0
                    return result
            pos += 4 + sz

        walk_netman = pos + fixed_tail
        expected_netman = walk_netman
        log.debug(
            "[deep_scan] walk_end=slot+0x%x, fixed_tail=%d, expected_netman=slot+0x%x",
            pos,
            fixed_tail,
            expected_netman,
        )

        delta = netman_start_from_steamid - expected_netman
        log.debug(
            "[deep_scan] _scan: expected_netman=0x%x (struct walk), found_netman=0x%x (pivot), delta=%+d",
            expected_netman,
            netman_start_from_steamid,
            delta,
        )

        result.delta = delta
        result.expected_steamid_offset = expected_netman + _STEAM_ID_TO_NETMAN_START

        # Locate the splice point: walk structs to find which one straddles found_netman.
        # The torn write removed bytes from inside that struct — splice there.
        splice_point = ef_end_rel  # fallback
        pos = ef_end_rel
        for sname in (
            "FieldArea",
            "WorldArea",
            "WorldGeomMan",
            "WorldGeomMan2",
            "RendMan",
        ):
            sz = struct.unpack_from("<i", slot_raw, pos)[0]
            end = pos + 4 + sz
            if pos <= netman_start_from_steamid < end:
                splice_point = netman_start_from_steamid
                log.debug(
                    "[deep_scan] splice inside %s at slot+0x%x", sname, splice_point
                )
                break
            pos = end
        else:
            log.debug(
                "[deep_scan] splice point fallback to ef_end_rel=0x%x", ef_end_rel
            )

        result.shift_point = splice_point
        log.info(
            "[deep_scan] _scan: delta=%+d (0x%x), splice_point=slot+0x%x",
            delta,
            abs(delta),
            splice_point,
        )
        result.details.append(f"Shift point: slot+0x{splice_point:x}")

        if delta == 0:
            result.details.append("NetMan at expected position: no shift")
            return result

        result.details.append(
            f"NetMan shift: {'+' if delta > 0 else ''}{delta} (0x{abs(delta):x}) bytes"
        )

        confidence = _assess_confidence(slot_raw, expected_netman, delta, found_offsets)
        result.confidence = confidence
        log.info("[deep_scan] _scan: confidence=%s", confidence)
        result.details.append(f"Confidence: {confidence}")

        return result

    def _get_save_steam_id(self, save: Save) -> int | None:
        if save.user_data_10_parsed and hasattr(save.user_data_10_parsed, "steam_id"):
            return save.user_data_10_parsed.steam_id
        return None


# ------------------------------------------------------------------
# Helpers


def _find_all(data: bytes | bytearray, pattern: bytes) -> list[int]:
    """Find all non-overlapping occurrences of pattern in data."""
    offsets = []
    start = 0
    while True:
        idx = data.find(pattern, start)
        if idx == -1:
            break
        offsets.append(idx)
        start = idx + len(pattern)
    return offsets


def _assess_confidence(
    slot_raw: bytes | bytearray,
    netman_start: int,
    delta: int,
    all_found: list[int],
) -> str:
    """
    Assess confidence in the scan result.

    High:   NetMan region looks valid, only one SteamID occurrence.
    Medium: Plausible but multiple SteamID hits or weak NetMan validation.
    Low:    Cannot validate NetMan region.
    """
    if netman_start < 0 or netman_start + _NETMAN_SIZE > len(slot_raw):
        log.debug(
            "[deep_scan] confidence=low: netman_start=0x%x out of bounds (slot len=0x%x)",
            netman_start,
            len(slot_raw),
        )
        return "low"

    unk0x0 = struct.unpack_from("<I", slot_raw, netman_start)[0]
    log.debug("[deep_scan] NetMan unk0x0 at slot+0x%x = 0x%x", netman_start, unk0x0)
    if unk0x0 > 0x10000000:
        log.debug("[deep_scan] confidence=low: unk0x0 looks like a pointer")
        return "low"

    netman_data_sample = slot_raw[netman_start + 4 : netman_start + 64]
    zero_ratio = (
        netman_data_sample.count(0) / len(netman_data_sample)
        if netman_data_sample
        else 1.0
    )
    log.debug(
        "[deep_scan] NetMan data sample [+4:+64]: %s (zero ratio=%.1f%%)",
        netman_data_sample.hex(),
        zero_ratio * 100,
    )

    if netman_data_sample == b"\x00" * 60 or netman_data_sample == b"\xff" * 60:
        log.debug(
            "[deep_scan] confidence=medium: NetMan sample is all zeros or all 0xFF"
        )
        return "medium"

    if len(all_found) == 1:
        return "high"

    return "medium"


def _recalculate_slot_checksum(
    save: Save, slot_index: int, slot_data_start: int
) -> None:
    """Recalculate and write the MD5 checksum for a single slot."""
    import hashlib

    CHECKSUM_SIZE = 0x10
    slot_size = 0x280000

    # Checksum covers the slot data (0x280000 bytes after the checksum itself)
    slot_data = save._raw_data[slot_data_start : slot_data_start + slot_size]
    md5_hash = hashlib.md5(slot_data).digest()

    # Checksum is stored immediately before the slot data
    checksum_offset = slot_data_start - CHECKSUM_SIZE
    save._raw_data[checksum_offset : checksum_offset + CHECKSUM_SIZE] = md5_hash

    log.info(
        "[deep_scan] checksum for slot %d recalculated: %s (written to file[0x%x])",
        slot_index,
        md5_hash.hex(),
        checksum_offset,
    )
