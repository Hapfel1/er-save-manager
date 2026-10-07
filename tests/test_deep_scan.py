"""
Tests for er_save_manager.fixes.deep_scan.DeepScanFix.
"""

from __future__ import annotations

from er_save_manager.fixes.deep_scan import DeepScanFix

# Byte/bit positions for two boss anchor pairs from _EF_ANCHOR_PAIRS,
# used to construct a controlled synthetic tear independent of the
# fixture's own real corruption (which lives on slot 1).
_ROMINA_GLOB_POS = 0x465 + 20
_ROMINA_GLOB_BIT = 7
_ROMINA_MAP_POS = 0xD3EA + 100
_ROMINA_MAP_BIT = 7

_LION_GLOB_POS = 0x465 + 17
_LION_GLOB_BIT = 3
_LION_MAP_POS = 0x1748F + 100
_LION_MAP_BIT = 3


def _clean_slot(save):
    """A slot with no known real event-flag tear, for tests that need
    a controlled starting state (slot 1 has real, pre-existing
    corruption; slot 2 also shows a low-confidence single disagreement).
    """
    for i in (0, 3, 4, 5, 6, 9):
        slot = save.character_slots[i]
        if not slot.is_empty():
            return i
    raise AssertionError("no known-clean slot available in fixture")


def _set_bit(ef: bytearray, pos: int, bit: int, value: bool) -> None:
    if value:
        ef[pos] |= 1 << bit
    else:
        ef[pos] &= ~(1 << bit)


# ---------------------------------------------------------------------------
# Main netman/SteamID-pivot scan (scan_only / detect)
# ---------------------------------------------------------------------------


def test_scan_only_reports_no_confidence_on_healthy_save(sanitized_save):
    """
    The sanitized fixture has SteamID zeroed everywhere (see
    conftest.py), so _get_save_steam_id returns 0 and the scan
    short-circuits before ever searching - this is the scan's own
    documented early-exit, not evidence of "no corruption".
    """
    fix = DeepScanFix()
    for i, slot in enumerate(sanitized_save.character_slots):
        if slot.is_empty():
            continue
        result = fix.scan_only(sanitized_save, i)
        assert result.steamid_found is False
        assert result.confidence == "none"
        assert fix.detect(sanitized_save, i) is False


def test_apply_is_no_op_when_steamid_unreadable(sanitized_save):
    i = _clean_slot(sanitized_save)
    result = DeepScanFix().apply(sanitized_save, i)
    assert result.applied is False


# ---------------------------------------------------------------------------
# ef_scan_only - the event-flag tear diagnostic
# ---------------------------------------------------------------------------


def test_ef_scan_no_false_positive_on_clean_slot(sanitized_save):
    i = _clean_slot(sanitized_save)
    result = DeepScanFix().ef_scan_only(sanitized_save, i)
    assert result.torn is False
    assert result.confident is False


def test_ef_scan_detects_the_real_tear_in_this_fixture(sanitized_save):
    result = DeepScanFix().ef_scan_only(sanitized_save, 1)

    assert result.torn is True
    assert result.confident is True
    assert "Divine Beast Dancing Lion" in result.disagreeing
    assert "Royal Knight Loretta" in result.disagreeing
    assert len(result.agreeing) > 0


def test_ef_scan_low_confidence_when_no_agreeing_anchor(sanitized_save):
    i = _clean_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    ef = bytearray(slot.event_flags)

    _set_bit(ef, _ROMINA_GLOB_POS, _ROMINA_GLOB_BIT, True)
    _set_bit(ef, _ROMINA_MAP_POS, _ROMINA_MAP_BIT, False)
    slot.event_flags = bytes(ef)

    result = DeepScanFix().ef_scan_only(sanitized_save, i)

    assert result.torn is True
    assert result.confident is False
    assert result.agreeing == []
    assert "Romina, Saint Of The Bud" in result.disagreeing


def test_ef_scan_confident_tear_with_one_agreeing_and_one_disagreeing(sanitized_save):
    i = _clean_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    ef = bytearray(slot.event_flags)

    # Romina: agreeing (both bits on)
    _set_bit(ef, _ROMINA_GLOB_POS, _ROMINA_GLOB_BIT, True)
    _set_bit(ef, _ROMINA_MAP_POS, _ROMINA_MAP_BIT, True)
    # Dancing Lion: disagreeing (global on, map off)
    _set_bit(ef, _LION_GLOB_POS, _LION_GLOB_BIT, True)
    _set_bit(ef, _LION_MAP_POS, _LION_MAP_BIT, False)
    slot.event_flags = bytes(ef)

    result = DeepScanFix().ef_scan_only(sanitized_save, i)

    assert result.torn is True
    assert result.confident is True
    assert "Romina, Saint Of The Bud" in result.agreeing
    assert "Divine Beast Dancing Lion" in result.disagreeing
    assert result.tear_lo < result.tear_hi


def test_undefeated_boss_is_never_flagged(sanitized_save):
    """Both flags being 0 (boss never fought) is consistent but
    uninformative and must not be reported either way.
    """
    i = _clean_slot(sanitized_save)
    result = DeepScanFix().ef_scan_only(sanitized_save, i)
    assert "Romina, Saint Of The Bud" not in result.agreeing
    assert "Romina, Saint Of The Bud" not in result.disagreeing


# ---------------------------------------------------------------------------
# The gap: detect()/apply() do not act on ef_scan_only's findings
# ---------------------------------------------------------------------------


def test_detect_does_not_surface_a_confident_event_flag_tear(sanitized_save):
    i = _clean_slot(sanitized_save)
    slot = sanitized_save.character_slots[i]
    ef = bytearray(slot.event_flags)
    _set_bit(ef, _ROMINA_GLOB_POS, _ROMINA_GLOB_BIT, True)
    _set_bit(ef, _ROMINA_MAP_POS, _ROMINA_MAP_BIT, True)
    _set_bit(ef, _LION_GLOB_POS, _LION_GLOB_BIT, True)
    _set_bit(ef, _LION_MAP_POS, _LION_MAP_BIT, False)
    slot.event_flags = bytes(ef)

    fix = DeepScanFix()
    ef_result = fix.ef_scan_only(sanitized_save, i)
    assert ef_result.torn is True
    assert ef_result.confident is True

    # detect()/scan_only() are blind to the above on the sanitized
    # fixture regardless, since SteamID is zeroed (see
    # test_scan_only_reports_no_confidence_on_healthy_save) - the point
    # here is specifically that ef_scan_only's own confident finding
    # has no path into detect()'s boolean result at all.
    assert fix.detect(sanitized_save, i) is False


# ---------------------------------------------------------------------------
# Event flag splice fallback (bytes removed in event flags + NetMan size error)
# ---------------------------------------------------------------------------

_SLOT_SIZE = 0x280000
_EF_SIZE = 0x1BF99F
_NETMAN_BLOB_SIZE = 0x20004
_TEST_STEAM_ID = 0x0110000100000001


def _with_steam_id(save, slot_index: int) -> None:
    """Restore a SteamID the sanitized fixture zeroed, in USER_DATA_10 and the slot."""
    save.user_data_10_parsed.steam_id = _TEST_STEAM_ID
    slot = save.character_slots[slot_index]
    save._raw_data[slot.steamid_offset : slot.steamid_offset + 8] = (
        _TEST_STEAM_ID.to_bytes(8, "little")
    )


def _longest_inner_zero_run(ef: bytes) -> tuple[int, int]:
    """(start, length) of the longest zero run between the first and last set byte."""
    nonzero = [i for i, b in enumerate(ef) if b]
    best = (0, 0)
    for prev, nxt in zip(nonzero, nonzero[1:], strict=False):
        if nxt - prev - 1 > best[1]:
            best = (prev + 1, nxt - prev - 1)
    return best


def _corrupt_ef_and_netman(save, slot_index: int, removed: int, netman_extra: int):
    """Remove zero bytes inside the event flags and grow NetMan, as seen in the wild."""
    slot = save.character_slots[slot_index]
    start = slot.data_start
    original = bytes(save._raw_data[start : start + _SLOT_SIZE])
    ef_rel = slot.event_flags_offset - start
    run_start, run_len = _longest_inner_zero_run(original[ef_rel : ef_rel + _EF_SIZE])
    assert run_len > 2 * removed
    cut = ef_rel + run_start + run_len // 2
    # net_man_offset points past the blob's 4-byte prefix (see NetMan docstring)
    netman_rel = slot.net_man_offset - start - 4
    netman_mid = netman_rel + _NETMAN_BLOB_SIZE // 2
    corrupted = (
        original[:cut]
        + original[cut + removed : netman_mid]
        + b"\xab" * netman_extra
        + original[netman_mid:]
    )[:_SLOT_SIZE]
    save._raw_data[start : start + _SLOT_SIZE] = corrupted
    # Everything the parser reads ends where the stale rest buffer begins
    parsed_end_rel = _SLOT_SIZE - len(slot.rest)
    return original, netman_rel, parsed_end_rel


def test_ef_splice_fallback_ignores_healthy_slots(sanitized_save):
    fix = DeepScanFix()
    for i, slot in enumerate(sanitized_save.character_slots):
        if slot.is_empty():
            continue
        _with_steam_id(sanitized_save, i)
        assert fix._scan_ef_splice(sanitized_save, i) is None
        assert fix.detect(sanitized_save, i) is False
        assert fix.scan_only(sanitized_save, i).tear_location != "event_flags_splice"


def test_ef_splice_fallback_repairs_removed_flags_and_oversized_netman(
    sanitized_save,
):
    from er_save_manager.fixes.deep_scan import _load_clean_netman

    i = _clean_slot(sanitized_save)
    _with_steam_id(sanitized_save, i)
    steamid_offset = sanitized_save.character_slots[i].steamid_offset
    original, netman_rel, parsed_end_rel = _corrupt_ef_and_netman(
        sanitized_save, i, removed=178, netman_extra=534
    )

    fix = DeepScanFix()
    scan = fix.scan_only(sanitized_save, i)
    assert scan.tear_location == "event_flags_splice"
    assert scan.delta == -178
    assert fix.detect(sanitized_save, i) is True

    result = fix.apply(sanitized_save, i)
    assert result.applied is True
    assert result.flags_relocated is True
    assert result.netman_reset is True

    start = sanitized_save.character_slots[i].data_start
    repaired = bytes(sanitized_save._raw_data[start : start + _SLOT_SIZE])
    netman_end = netman_rel + _NETMAN_BLOB_SIZE
    assert repaired[:netman_rel] == original[:netman_rel]
    assert repaired[netman_rel:netman_end] == _load_clean_netman()
    assert repaired[netman_end:parsed_end_rel] == original[netman_end:parsed_end_rel]

    assert sanitized_save.character_slots[i].steamid_offset == steamid_offset
    assert fix.detect(sanitized_save, i) is False


def test_netman_tear_repair_reparses_slot(sanitized_save):
    """After a shift repair the parsed slot must describe the repaired bytes,
    otherwise to_file() refreshes PlayerGameDataHash at pre-repair offsets."""
    i = _clean_slot(sanitized_save)
    _with_steam_id(sanitized_save, i)
    slot = sanitized_save.character_slots[i]
    start = slot.data_start
    steamid_offset = slot.steamid_offset
    hash_offset = slot.player_data_hash_offset
    original = bytes(sanitized_save._raw_data[start : start + _SLOT_SIZE])

    # Drop 13 bytes from the middle of NetMan
    cut = slot.net_man_offset - start + _NETMAN_BLOB_SIZE // 2
    torn = (original[:cut] + original[cut + 13 :] + bytes(13))[:_SLOT_SIZE]
    sanitized_save._raw_data[start : start + _SLOT_SIZE] = torn

    fix = DeepScanFix()
    scan = fix.scan_only(sanitized_save, i)
    assert scan.tear_location == "netman"
    assert scan.delta == -13

    result = fix.apply(sanitized_save, i)
    assert result.applied is True
    assert result.netman_reset is True
    assert result.flags_relocated is False
    reparsed = sanitized_save.character_slots[i]
    assert reparsed is not slot
    assert reparsed.steamid_offset == steamid_offset
    assert reparsed.player_data_hash_offset == hash_offset
