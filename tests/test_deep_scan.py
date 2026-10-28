"""Tests for er_save_manager.fixes.deep_scan.DeepScanFix."""

from __future__ import annotations

from er_save_manager.fixes.deep_scan import DeepScanFix
from er_save_manager.fixes.netman import netman_problems

# Byte/bit positions of two boss anchor pairs from _EF_ANCHOR_PAIRS, for a
# synthetic tear on slot 0 (slot 1 holds a real one)
_ROMINA = ((0x465 + 20, 7), (0xD3EA + 100, 7))
_LION = ((0x465 + 17, 3), (0x1748F + 100, 3))
ROMINA_NAME = "Romina, Saint Of The Bud"
LION_NAME = "Divine Beast Dancing Lion"

_SLOT_SIZE = 0x280000
_EF_SIZE = 0x1BF99F
_NETMAN_BLOB_SIZE = 0x20004
_TEST_STEAM_ID = 0x0110000100000001


def _set_anchor(save, anchor, global_bit: bool, map_bit: bool) -> None:
    slot = save.character_slots[0]
    ef = bytearray(slot.event_flags)
    for (pos, bit), value in zip(anchor, (global_bit, map_bit), strict=True):
        if value:
            ef[pos] |= 1 << bit
        else:
            ef[pos] &= ~(1 << bit)
    slot.event_flags = bytes(ef)


def _with_steam_id(save, slot_index: int) -> None:
    """Restore a SteamID the sanitized fixture zeroed, in USER_DATA_10 and the slot."""
    save.user_data_10_parsed.steam_id = _TEST_STEAM_ID
    slot = save.character_slots[slot_index]
    save._raw_data[slot.steamid_offset : slot.steamid_offset + 8] = (
        _TEST_STEAM_ID.to_bytes(8, "little")
    )


def test_zeroed_steamid_short_circuits_the_scan(sanitized_save):
    fix = DeepScanFix()
    for i in range(10):
        result = fix.scan_only(sanitized_save, i)
        assert result.steamid_found is False and result.confidence == "none"
        assert fix.detect(sanitized_save, i) is False
    assert fix.apply(sanitized_save, 0).applied is False


def test_ef_scan(sanitized_save):
    fix = DeepScanFix()
    clean = fix.ef_scan_only(sanitized_save, 0)
    assert clean.torn is False and clean.confident is False
    # A never-fought boss (both flags 0) is reported neither way
    assert ROMINA_NAME not in clean.agreeing + clean.disagreeing

    real = fix.ef_scan_only(sanitized_save, 1)
    assert real.torn and real.confident and real.agreeing
    assert {LION_NAME, "Royal Knight Loretta"} <= set(real.disagreeing)

    # One disagreeing anchor and none agreeing: torn, not confident
    _set_anchor(sanitized_save, _ROMINA, True, False)
    result = fix.ef_scan_only(sanitized_save, 0)
    assert result.torn and not result.confident
    assert result.agreeing == [] and ROMINA_NAME in result.disagreeing

    _set_anchor(sanitized_save, _ROMINA, True, True)
    _set_anchor(sanitized_save, _LION, True, False)
    result = fix.ef_scan_only(sanitized_save, 0)
    assert result.torn and result.confident
    assert ROMINA_NAME in result.agreeing and LION_NAME in result.disagreeing
    assert result.tear_lo < result.tear_hi


def _longest_inner_zero_run(ef: bytes) -> tuple[int, int]:
    """(start, length) of the longest zero run between the first and last set byte."""
    nonzero = [i for i, b in enumerate(ef) if b]
    best = (0, 0)
    for prev, nxt in zip(nonzero, nonzero[1:], strict=False):
        if nxt - prev - 1 > best[1]:
            best = (prev + 1, nxt - prev - 1)
    return best


def test_ef_splice_fallback_ignores_healthy_slots(sanitized_save):
    fix = DeepScanFix()
    for i in range(10):
        _with_steam_id(sanitized_save, i)
        assert fix._scan_ef_splice(sanitized_save, i) is None
        assert fix.detect(sanitized_save, i) is False
        assert fix.scan_only(sanitized_save, i).tear_location != "event_flags_splice"


def test_ef_splice_fallback_repairs_removed_flags_and_oversized_netman(sanitized_save):
    """Zero bytes removed inside the event flags and NetMan grown, like a torn write."""
    _with_steam_id(sanitized_save, 0)
    slot = sanitized_save.character_slots[0]
    start, steamid_offset = slot.data_start, slot.steamid_offset
    original = bytes(sanitized_save._raw_data[start : start + _SLOT_SIZE])
    ef_rel = slot.event_flags_offset - start
    run_start, run_len = _longest_inner_zero_run(original[ef_rel : ef_rel + _EF_SIZE])
    assert run_len > 2 * 178
    cut = ef_rel + run_start + run_len // 2
    # net_man_offset points past the blob's 4-byte prefix (see NetMan docstring)
    netman_rel = slot.net_man_offset - start - 4
    netman_mid = netman_rel + _NETMAN_BLOB_SIZE // 2
    sanitized_save._raw_data[start : start + _SLOT_SIZE] = (
        original[:cut]
        + original[cut + 178 : netman_mid]
        + b"\xab" * 534
        + original[netman_mid:]
    )[:_SLOT_SIZE]
    # Everything the parser reads ends where the stale rest buffer begins
    parsed_end = _SLOT_SIZE - len(slot.rest)

    fix = DeepScanFix()
    scan = fix.scan_only(sanitized_save, 0)
    assert (scan.tear_location, scan.delta) == ("event_flags_splice", -178)
    assert fix.detect(sanitized_save, 0) is True
    result = fix.apply(sanitized_save, 0)
    assert result.applied and result.flags_relocated
    # The junk lands in NetMan's zero padding, so every chunk is kept
    assert result.netman_reset is False

    repaired = bytes(sanitized_save._raw_data[start : start + _SLOT_SIZE])
    netman_end = netman_rel + _NETMAN_BLOB_SIZE
    assert repaired[:netman_end] == original[:netman_end]
    assert not netman_problems(repaired[netman_rel + 4 : netman_end + 4])
    assert repaired[netman_end:parsed_end] == original[netman_end:parsed_end]
    assert sanitized_save.character_slots[0].steamid_offset == steamid_offset
    assert fix.detect(sanitized_save, 0) is False


def test_netman_tear_repair_reparses_slot(sanitized_save):
    """After a shift repair the parsed slot must describe the repaired bytes,
    otherwise to_file() refreshes PlayerGameDataHash at pre-repair offsets."""
    _with_steam_id(sanitized_save, 0)
    slot = sanitized_save.character_slots[0]
    start = slot.data_start
    original = bytes(sanitized_save._raw_data[start : start + _SLOT_SIZE])
    cut = slot.net_man_offset - start + _NETMAN_BLOB_SIZE // 2
    sanitized_save._raw_data[start : start + _SLOT_SIZE] = (
        original[:cut] + original[cut + 13 :] + bytes(13)
    )[:_SLOT_SIZE]

    fix = DeepScanFix()
    scan = fix.scan_only(sanitized_save, 0)
    assert (scan.tear_location, scan.delta) == ("netman", -13)
    result = fix.apply(sanitized_save, 0)
    assert result.applied and result.netman_reset and not result.flags_relocated
    reparsed = sanitized_save.character_slots[0]
    assert reparsed is not slot
    assert reparsed.steamid_offset == slot.steamid_offset
    assert reparsed.player_data_hash_offset == slot.player_data_hash_offset
