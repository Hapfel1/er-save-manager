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
