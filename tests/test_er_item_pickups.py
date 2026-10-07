"""Elden Ring item pickup checklist data (data/item_pickups*.csv).

Every pickup flag must have storage in the save's event flag tree, or the
checklist would report it as missing forever. Grace references must resolve
to a known Site of Grace, and every item must have a display name.
"""

from __future__ import annotations

import pytest

from er_save_manager.data.grace_data import get_graces
from er_save_manager.data.item_pickups import ITEM_TYPES, SOURCE_LABELS, get_pickups
from er_save_manager.parser.event_flags import EventFlags

DATASETS = pytest.mark.parametrize(
    "is_convergence", [False, True], ids=["vanilla", "convergence"]
)


@DATASETS
def test_flags_unique_and_stored(is_convergence):
    flags = [p.flag_id for p in get_pickups(is_convergence)]
    assert len(flags) == len(set(flags))
    assert [f for f in flags if not EventFlags.has_flag(f)] == []


@DATASETS
def test_graces_resolve(is_convergence):
    graces = {g.flag_id for g in get_graces(include_convergence=is_convergence)}
    unknown = [
        p.flag_id
        for p in get_pickups(is_convergence)
        if p.grace_flag and p.grace_flag not in graces
    ]
    assert unknown == []


@DATASETS
def test_items_named_and_typed(is_convergence):
    for p in get_pickups(is_convergence):
        assert p.items, p.flag_id
        assert p.item_type in ITEM_TYPES
        assert p.source in SOURCE_LABELS
        for _, qty, name in p.items:
            assert qty >= 1
            assert name and not name.startswith("Unknown "), (p.flag_id, name)


def test_progression_counts():
    """Seeds, tears, fragments and ashes: every world copy, no duplicates."""
    names = [p.items[0][2] for p in get_pickups() if p.item_type == "Progression"]
    assert names.count("Golden Seed") >= 30
    assert names.count("Sacred Tear") == 12
    assert names.count("Memory Stone") == 7
