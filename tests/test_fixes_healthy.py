"""Save Fixer fixes on the healthy fixture: nothing detected, nothing written."""

from __future__ import annotations

import pytest

from er_save_manager.fixes import ALL_FIXES

# The sanitized fixture has its SteamIDs zeroed and the DLC entry flag set,
# so these two fire on it by design (see test_steamid_fix, test_dlc_fix).
_FIRE_ON_FIXTURE = {"SteamIdFix", "DLCFlagFix"}

HEALTHY_FIXES = [f for f in ALL_FIXES if f.__name__ not in _FIRE_ON_FIXTURE]


@pytest.mark.parametrize("fix_cls", HEALTHY_FIXES, ids=lambda f: f.__name__)
def test_fix_is_no_op_on_healthy_save(sanitized_save, fix_cls):
    before = bytes(sanitized_save._raw_data)
    fix = fix_cls()
    for i, slot in enumerate(sanitized_save.character_slots):
        if slot.is_empty():
            continue
        assert fix.detect(sanitized_save, i) is False, f"slot {i} flagged"
        assert fix.apply(sanitized_save, i).applied is False, f"slot {i} applied"
    assert bytes(sanitized_save._raw_data) == before


def test_excluded_fixes_exist():
    """A renamed fix must not drop out of the exclusion list unnoticed."""
    assert _FIRE_ON_FIXTURE <= {f.__name__ for f in ALL_FIXES}
