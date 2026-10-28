"""Save Fixer fixes on the healthy fixture: nothing detected, nothing written."""

from __future__ import annotations

from er_save_manager.fixes import ALL_FIXES

# The sanitized fixture has its SteamIDs zeroed and the DLC entry flag set,
# so these two fire on it by design (see test_steamid_fix, test_dlc_fix).
_FIRE_ON_FIXTURE = {"SteamIdFix", "DLCFlagFix"}


def test_fixes_are_no_op_on_healthy_save(sanitized_save):
    assert _FIRE_ON_FIXTURE <= {f.__name__ for f in ALL_FIXES}
    before = bytes(sanitized_save._raw_data)
    for fix_cls in ALL_FIXES:
        if fix_cls.__name__ in _FIRE_ON_FIXTURE:
            continue
        fix = fix_cls()
        for i in range(10):
            assert fix.detect(sanitized_save, i) is False, (fix_cls.__name__, i)
            assert fix.apply(sanitized_save, i).applied is False, (fix_cls.__name__, i)
    assert bytes(sanitized_save._raw_data) == before
