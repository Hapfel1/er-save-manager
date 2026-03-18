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
     size fields are intact, so they can be summed up from event_flags_end.
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
from pathlib import Path
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

# Boss defeat flag pairs for event flag torn write detection.
# (map_block_byte, glob_block_byte, map_flag_id, glob_flag_id,
#  map_byte_off, map_bit, glob_byte_off, glob_bit, name)
# map_block_byte = bst[map_flag // 1000] * 125  (position in event_flags array)
# glob_block_byte = bst[glob_flag // 1000] * 125 (always in block 9, ~0x465)
# Sorted ascending by map_block_byte for binary search.
# Global flags (block 9) are always before any realistic torn-write region.
_EF_ANCHOR_PAIRS: list[tuple[int, int, int, int, int, int, int, int, str]] = [
    (
        0x0000D3EA,
        0x00000465,
        2044450800,
        9160,
        100,
        7,
        20,
        7,
        "Romina, Saint Of The Bud",
    ),
    (
        0x0001748F,
        0x00000465,
        2046460800,
        9140,
        100,
        7,
        17,
        3,
        "Divine Beast Dancing Lion",
    ),
    (
        0x00020AF3,
        0x00000465,
        2048440800,
        9190,
        100,
        7,
        23,
        1,
        "Rellana, Twin Moon Knight",
    ),
    (0x000263D1, 0x00000465, 2049480800, 9164, 100, 7, 20, 3, "Commander Gaius"),
    (0x0002AF03, 0x00000465, 2050480800, 9162, 100, 7, 20, 5, "Scadutree Avatar"),
    (0x000679B7, 0x00000465, 1035500800, 9119, 100, 7, 14, 0, "Royal Knight Loretta"),
    (0x0008AA43, 0x00000465, 1039540800, 9182, 100, 7, 22, 1, "Elemer Of The Briar"),
    (0x000F1D24, 0x00000465, 1051570800, 9184, 100, 7, 23, 7, "Commander Niall"),
    (0x00151BCF, 0x00000465, 10000800, 9100, 100, 7, 12, 3, "Godrick The Grafted"),
    (0x00151BCF, 0x00000465, 10000850, 9101, 106, 5, 12, 2, "Margit, The Fell Omen"),
    (0x00152034, 0x00000465, 10010800, 9103, 100, 7, 12, 0, "Grafted Scion"),
    (0x00152D63, 0x00000465, 11000800, 9104, 100, 7, 13, 7, "Morgott, The Omen King"),
    (
        0x00152D63,
        0x00000465,
        11000850,
        9105,
        106,
        5,
        13,
        6,
        "Godfrey, First Elden Lord",
    ),
    (0x001531C8, 0x00000465, 11050850, 9106, 106, 5, 13, 5, "Sir Gideon Ofnir"),
    (
        0x00154C26,
        0x00000465,
        12010800,
        9109,
        100,
        7,
        13,
        2,
        "Dragonkin Soldier Of Nokstella",
    ),
    (0x001554F0, 0x00000465, 12030850, 9111, 106, 5, 13, 0, "Lichdragon Fortissax"),
    (
        0x00155955,
        0x00000465,
        12040800,
        9108,
        100,
        7,
        13,
        3,
        "Astel, Naturalborn Of The Void",
    ),
    (0x00155DBA, 0x00000465, 12050800, 9112, 100, 7, 14, 7, "Mohg, Lord Of Blood"),
    (0x00156F4E, 0x00000465, 12090800, 9133, 100, 7, 16, 2, "Regal Ancestor Spirit"),
    (
        0x001573B3,
        0x00000465,
        13000800,
        9116,
        100,
        7,
        14,
        3,
        "Maliketh, The Black Blade",
    ),
    (0x001573B3, 0x00000465, 13000830, 9115, 103, 1, 14, 4, "Dragonlord Placidusax"),
    (
        0x001580E2,
        0x00000465,
        14000800,
        9118,
        100,
        7,
        14,
        1,
        "Rennala, Queen Of The Full Moon",
    ),
    (
        0x00158E11,
        0x00000465,
        15000800,
        9120,
        100,
        7,
        15,
        7,
        "Malenia, Blade Of Miquella",
    ),
    (
        0x00159B40,
        0x00000465,
        16000800,
        9122,
        100,
        7,
        15,
        5,
        "Rykard, Lord Of Blasphemy",
    ),
    (
        0x0017AEFD,
        0x00000465,
        20000800,
        9140,
        100,
        7,
        17,
        3,
        "Divine Beast Dancing Lion (DLC map)",
    ),
    (0x0017C4F6, 0x00000465, 21010800, 9146, 100, 7, 18, 5, "Messmer The Impaler"),
    (0x0017D225, 0x00000465, 22000800, 9148, 100, 7, 18, 3, "Putrescent Knight"),
    (0x0017DAEF, 0x00000465, 25000800, 9155, 100, 7, 19, 4, "Metyr, Mother Of Fingers"),
    (
        0x0017F54D,
        0x00000465,
        28000800,
        9156,
        100,
        7,
        19,
        3,
        "Midra, Lord Of Frenzied Flame",
    ),
    (0x001A1A9E, 0x00000465, 1252380800, 9130, 100, 7, 16, 5, "Starscourge Radahn"),
    (0x001AABA3, 0x00000465, 1252520800, 9131, 100, 7, 16, 4, "Fire Giant"),
]


@dataclass
class EFTornScanResult:
    """Result of event flag torn write scan."""

    torn: bool = False
    tear_lo: int = 0  # map_block_byte of last agreeing anchor (0 if none)
    tear_hi: int = 0  # map_block_byte of first disagreeing anchor
    agreeing: list[str] = field(default_factory=list)
    disagreeing: list[str] = field(default_factory=list)
    confident: bool = False  # True when at least one pair agrees and one disagrees


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
    tear_location: str = "netman"  # "netman" or "event_flags"
    ef_splice_point: int = (
        0  # slot-relative splice point when tear_location=="event_flags"
    )
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

        if result.delta == 0 and result.tear_location != "event_flags":
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

        if result.tear_location == "event_flags":
            # Splice inside event flags at the start of the first disagreeing block.
            shift_point = result.ef_splice_point
            log.info(
                "[deep_scan] slot %d: EF tear, delta=%+d (0x%x), splice=slot+0x%x, confidence=%s",
                slot_index,
                delta,
                abs(delta),
                shift_point,
                result.confidence,
            )
        else:
            # NetMan tear: splice at expected_netman + TAIL_AFTER_NETMAN.
            # = expected_steamid_offset - _NETMAN_SIZE
            # Verified by byte-diff against manual fix: the tear removes bytes from
            # inside the NetMan block; splicing here restores correct NetMan content
            # and leaves weather/time/SteamID intact at their expected positions.
            shift_point = result.expected_steamid_offset - _NETMAN_SIZE
            log.info(
                "[deep_scan] slot %d: NetMan tear, delta=%+d (0x%x), "
                "splice=slot+0x%x (expected_sid-NetMan_size), confidence=%s",
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

        # Check for zeroed-out data around the SteamID - indicates the fix
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
                "[deep_scan] post-fix data around SteamID is >90%% zeros - fix may have landed in padding"
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
                    "[deep_scan] post-fix NetMan region looks zeroed - may indicate wrong shift point"
                )

        # Write corrected data back
        save._raw_data[slot_data_start : slot_data_start + slot_size] = corrected
        log.info("[deep_scan] wrote corrected slot data back to file buffer")

        # For NetMan-region tears: after reshifting, NetMan may contain invalid data.
        # Check if NetMan is non-empty and replace with known-clean binary if so.
        netman_note = None
        if result.tear_location == "netman":
            netman_abs = (
                slot_data_start
                + result.expected_steamid_offset
                - _STEAM_ID_TO_NETMAN_START
            )
            netman_region = save._raw_data[netman_abs : netman_abs + _NETMAN_SIZE]
            if any(b != 0 for b in netman_region):
                clean = _load_clean_netman()
                if clean is not None:
                    save._raw_data[netman_abs : netman_abs + _NETMAN_SIZE] = clean
                    netman_note = "NetMan replaced with clean template"
                    log.info(
                        "[deep_scan] NetMan had data after reshift - replaced with clean template"
                    )
                else:
                    netman_note = "WARNING: clean NetMan template not found - NetMan may be invalid"
                    log.warning(
                        "[deep_scan] CSNetMan.bin not found, cannot wipe invalid NetMan"
                    )
            else:
                netman_note = "NetMan empty - no wipe needed"
                log.info("[deep_scan] NetMan is empty after reshift, no wipe needed")

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
            description=f"Torn write corrected ({result.tear_location}): {'+' if delta > 0 else ''}{delta} bytes at slot+0x{shift_point:x}",
            details=result.details
            + [
                f"SteamID found at slot+0x{result.steamid_offset_in_slot:x}",
                f"Expected at slot+0x{result.expected_steamid_offset:x}",
                f"Confidence: {result.confidence}",
                validation_note,
                zero_note,
            ]
            + ([netman_note] if netman_note else [])
            + ["Checksum recalculated"],
        )

    def scan_only(self, save: Save, slot_index: int) -> DeepScanResult:
        """Public method to run scan and return details without modifying."""
        return self._scan(save, slot_index)

    def ef_scan_only(self, save: Save, slot_index: int) -> EFTornScanResult:
        """Public method to run event flag torn write scan without modifying."""
        return self._scan_event_flags(save, slot_index)

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
            "[deep_scan] _scan: searched slot for SteamID %d - found at offsets: %s",
            correct_steam_id,
            [hex(o) for o in found_offsets],
        )

        if not found_offsets:
            log.warning("[deep_scan] _scan: SteamID not found in slot %d", slot_index)
            result.details.append(f"SteamID64 {correct_steam_id} not found in slot")
            return result

        # Use a single SteamID occurrence - if multiple, take the one that gives a
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

        # Check for EF tear unconditionally, trying all SteamID candidates.
        # EF tears can produce false SteamID hits (duplicate values in shifted data)
        # and the parser may store a wrong steamid_offset due to zeroed structs.
        # Iterate all candidates and pick the one where a struct scan from
        # ef_end_rel+d lands exactly on the candidate - that gives the true delta.
        # Anchor pairs are used only to locate the splice point, NOT to detect the tear
        # (anchors can disagree legitimately due to boss flags set in non-standard ways).
        if (
            hasattr(slot, "event_flags_offset")
            and slot.event_flags_offset > slot_data_start
        ):
            ef_rel = slot.event_flags_offset - slot_data_start
            ef_end_rel_early = ef_rel + _EVENT_FLAGS_SIZE + _EVENT_FLAGS_TERMINATOR
            version_early = getattr(slot, "version", 0)
            ft = _PRE_NETMAN_FIXED_BASE
            if version_early >= 65:
                ft += _PRE_NETMAN_V65_EXTRA
            if version_early >= 66:
                ft += _PRE_NETMAN_V66_EXTRA
            # First check d=0: if struct walk from ef_end_rel already lands on a SteamID,
            # the file is clean - skip EF tear detection entirely.
            pos0 = ef_end_rel_early
            ok0 = True
            for _ in range(5):
                if pos0 + 4 > len(slot_raw):
                    ok0 = False
                    break
                sz = struct.unpack_from("<i", slot_raw, pos0)[0]
                if sz < 0 or sz > 0x8000:
                    ok0 = False
                    break
                pos0 += 4 + sz
            ef_delta = 0
            ef_best = best
            if ok0 and pos0 + ft + _NETMAN_SIZE + _TAIL_AFTER_NETMAN in found_offsets:
                # Verify the d=0 walk used at least one non-zero struct size.
                # All-zero sizes = EF overflow garbage, not a real clean match.
                pos_check = ef_end_rel_early
                any_nonzero = False
                for _ in range(5):
                    if pos_check + 4 > len(slot_raw):
                        break
                    sz = struct.unpack_from("<i", slot_raw, pos_check)[0]
                    if sz > 0:
                        any_nonzero = True
                        break
                    pos_check += 4 + sz
                if any_nonzero:
                    pass  # d=0 is a genuine clean match - no EF tear
                    ef_delta = 0  # ensure delta scan below is skipped
                else:
                    # All-zero structs: EF overflow, remove false hit and scan for real delta
                    found_offsets = [
                        f
                        for f in found_offsets
                        if f != pos0 + ft + _NETMAN_SIZE + _TAIL_AFTER_NETMAN
                    ]
                    ok0 = False
            if (
                not ok0
                or pos0 + ft + _NETMAN_SIZE + _TAIL_AFTER_NETMAN not in found_offsets
            ):
                for candidate in found_offsets:
                    for d in range(1, 0x400):
                        pos = ef_end_rel_early + d
                        ok = True
                        for _ in range(5):
                            if pos + 4 > len(slot_raw):
                                ok = False
                                break
                            sz = struct.unpack_from("<i", slot_raw, pos)[0]
                            if sz < 0 or sz > 0x8000:
                                ok = False
                                break
                            pos += 4 + sz
                        if not ok:
                            continue
                        if pos + ft + _NETMAN_SIZE + _TAIL_AFTER_NETMAN == candidate:
                            ef_delta = d
                            ef_best = candidate
                            break
                    if ef_delta > 0:
                        break
            if ef_delta > 0:
                # Delta confirmed by struct scan - now run anchor scan to locate splice.
                ef_early = self._scan_event_flags(save, slot_index)
                # Find the exact splice point by scanning for the zero-run of length ef_delta
                # that marks where the extra bytes were inserted.
                # Search range: within the torn block region (tear_lo..tear_hi+125).
                # If no agreeing pairs (tear_lo unknown), search only within tear_hi block.
                ef_slot_raw = slot_raw[ef_rel : ef_rel + _EVENT_FLAGS_SIZE]
                tear_lo = max(ef_early.tear_lo, 0)
                tear_hi = ef_early.tear_hi
                if ef_early.confident and tear_lo > 0:
                    search_start = tear_lo
                else:
                    search_start = tear_hi
                search_end = min(tear_hi + 125, _EVENT_FLAGS_SIZE - ef_delta)
                splice_in_ef = tear_hi  # default: torn block start
                for i in range(search_start, search_end):
                    if all(ef_slot_raw[i + j] == 0 for j in range(ef_delta)):
                        splice_in_ef = i
                        break

                result.delta = ef_delta
                result.tear_location = "event_flags"
                result.ef_splice_point = ef_rel + splice_in_ef
                result.steamid_offset_in_slot = ef_best
                result.expected_steamid_offset = ef_best - ef_delta
                result.confidence = "high" if ef_early.confident else "medium"
                result.details.append(f"EF shift: +{ef_delta} (0x{ef_delta:x}) bytes")
                result.details.append(
                    f"Tear location: event_flags (ef+0x{splice_in_ef:x})"
                )
                if ef_early.disagreeing:
                    result.details.append(
                        f"Disagreeing bosses: {', '.join(ef_early.disagreeing)}"
                    )
                log.info(
                    "[deep_scan] _scan: EF tear, delta=+0x%x, splice=slot+0x%x, bosses=%s",
                    ef_delta,
                    result.ef_splice_point,
                    ef_early.disagreeing,
                )
                return result

        # Early-out: if SteamID is already at the parser's tracked position, no NetMan shift.
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
        # Size fields are intact even in a torn write - only content is shifted.
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
                        "[deep_scan] walk: zero size for %s, pivot looks valid - "
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
        # The torn write removed bytes from inside that struct - splice there.
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

        # Check if the tear is actually in event flags rather than NetMan.
        # If EF scan finds disagreeing anchor pairs, the tear is in event flags -
        # the SteamID shift is a downstream effect, and the splice point differs.
        ef_result = self._scan_event_flags(save, slot_index)
        if ef_result.torn and ef_result.confident:
            result.tear_location = "event_flags"
            # Splice at the start of the first disagreeing block in ef
            # ef_start_rel = event_flags_offset - slot_data_start (already computed above)
            result.ef_splice_point = (
                ef_end_rel
                - _EVENT_FLAGS_SIZE
                - _EVENT_FLAGS_TERMINATOR
                + ef_result.tear_hi
            )
            log.info(
                "[deep_scan] _scan: tear in event_flags, splice at slot+0x%x (ef+0x%x)",
                result.ef_splice_point,
                ef_result.tear_hi,
            )
            result.details.append(
                f"Tear location: event_flags (ef+0x{ef_result.tear_hi:x})"
            )
            result.details.append(
                f"Disagreeing bosses: {', '.join(ef_result.disagreeing)}"
            )
        elif ef_result.torn and not ef_result.confident:
            result.tear_location = "event_flags"
            # No agreeing pairs - tear before all anchors; use first anchor as upper bound
            result.ef_splice_point = (
                ef_end_rel
                - _EVENT_FLAGS_SIZE
                - _EVENT_FLAGS_TERMINATOR
                + ef_result.tear_hi
            )
            log.info(
                "[deep_scan] _scan: tear likely in event_flags (no agreeing pairs), splice at slot+0x%x",
                result.ef_splice_point,
            )
            result.details.append(
                f"Tear location: event_flags (before ef+0x{ef_result.tear_hi:x}, low confidence)"
            )
        else:
            result.tear_location = "netman"
            result.details.append("Tear location: NetMan region")

        return result

    def _scan_event_flags(self, save: Save, slot_index: int) -> EFTornScanResult:
        """
        Detect a torn write inside the event flags region.

        Strategy: each boss has two flags that must always agree -
        a global flag (block 9, always early in the array) and a map-local
        flag scattered across the array. A tear at byte position X shifts all
        map flags with block_byte > X, causing them to disagree with their
        global counterpart. Binary search on sorted anchor pairs brackets the tear.
        """
        result = EFTornScanResult()
        slot = self.get_slot(save, slot_index)
        if slot.is_empty():
            return result

        ef = getattr(slot, "event_flags", None)
        if ef is None or len(ef) != _EVENT_FLAGS_SIZE:
            log.debug(
                "[deep_scan] ef_scan: slot %d missing or wrong-size event_flags",
                slot_index,
            )
            return result

        ef = bytes(ef)

        def read_bit(block_byte: int, byte_off: int, bit: int) -> bool | None:
            pos = block_byte + byte_off
            if pos >= len(ef):
                return None
            return bool((ef[pos] >> bit) & 1)

        agreeing: list[tuple[int, str]] = []
        disagreeing: list[tuple[int, str]] = []

        for (
            map_bb,
            glob_bb,
            _map_id,
            _glob_id,
            map_bo,
            map_bit,
            glob_bo,
            glob_bit,
            name,
        ) in _EF_ANCHOR_PAIRS:
            glob_val = read_bit(glob_bb, glob_bo, glob_bit)
            map_val = read_bit(map_bb, map_bo, map_bit)
            if glob_val is None or map_val is None:
                continue
            # Skip undefeated bosses - both flags being 0 is consistent but not informative.
            if not glob_val:
                continue
            if map_val == glob_val:
                agreeing.append((map_bb, name))
            else:
                disagreeing.append((map_bb, name))

        result.agreeing = [n for _, n in agreeing]
        result.disagreeing = [n for _, n in disagreeing]
        log.debug(
            "[deep_scan] ef_scan slot %d: %d agreeing, %d disagreeing",
            slot_index,
            len(agreeing),
            len(disagreeing),
        )

        if not disagreeing:
            return result

        result.torn = True

        if not agreeing:
            # All defeated bosses' map flags disagree - tear is before the first anchor.
            result.confident = False
            result.tear_lo = 0
            result.tear_hi = _EF_ANCHOR_PAIRS[0][0]
            log.info(
                "[deep_scan] ef_scan slot %d: all pairs disagree, tear before ef+0x%x",
                slot_index,
                result.tear_hi,
            )
            return result

        result.confident = True
        result.tear_lo = max(p for p, _ in agreeing)
        result.tear_hi = min(p for p, _ in disagreeing)
        log.info(
            "[deep_scan] ef_scan slot %d: tear between ef+0x%x and ef+0x%x",
            slot_index,
            result.tear_lo,
            result.tear_hi,
        )
        return result

    def _get_save_steam_id(self, save: Save) -> int | None:
        if save.user_data_10_parsed and hasattr(save.user_data_10_parsed, "steam_id"):
            return save.user_data_10_parsed.steam_id
        return None


# ------------------------------------------------------------------
# Helpers


def _load_clean_netman() -> bytes | None:
    """
    Load the clean NetMan template from CSNetMan.bin.

    The file is expected to live alongside this module. Returns None if not found
    or if the size does not match _NETMAN_SIZE.
    """
    candidate = Path(__file__).parent / "CSNetMan.bin"
    if not candidate.is_file():
        log.debug("[deep_scan] CSNetMan.bin not found at %s", candidate)
        return None
    data = candidate.read_bytes()
    if len(data) != _NETMAN_SIZE:
        log.warning(
            "[deep_scan] CSNetMan.bin size mismatch: expected 0x%x, got 0x%x",
            _NETMAN_SIZE,
            len(data),
        )
        return None
    unk0x0 = struct.unpack_from("<I", data, 0)[0]
    if unk0x0 != 0:
        log.warning(
            "[deep_scan] CSNetMan.bin unk0x0=0x%x (non-zero) - template is invalid, ignoring",
            unk0x0,
        )
        return None
    return data


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
