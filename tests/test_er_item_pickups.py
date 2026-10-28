"""Elden Ring item pickup checklist data (data/item_pickups*.csv).

Every pickup flag must have storage in the save's event flag tree, or the
checklist would report it as missing forever.
"""

from __future__ import annotations

from er_save_manager.data.grace_data import get_graces
from er_save_manager.data.item_pickups import ITEM_TYPES, SOURCE_LABELS, get_pickups
from er_save_manager.data.world_map import location_map_point
from er_save_manager.parser.event_flags import EventFlags


def test_pickup_tables():
    for cnv in (False, True):
        pickups = get_pickups(cnv)
        flags = [p.flag_id for p in pickups]
        assert len(flags) == len(set(flags))
        assert [f for f in flags if not EventFlags.has_flag(f)] == []

        graces = {g.flag_id for g in get_graces(include_convergence=cnv)}
        assert [
            p.flag_id for p in pickups if p.grace_flag and p.grace_flag not in graces
        ] == []

        for p in pickups:
            assert p.items and p.item_type in ITEM_TYPES and p.source in SOURCE_LABELS
            for _, qty, name in p.items:
                assert qty >= 1
                assert name and not name.startswith("Unknown "), (p.flag_id, name)

        # Only the Chapel of Anticipation has no world map placement
        off_map = {
            p.map_id
            for p in pickups
            if p.position is not None
            and location_map_point(p.map_id, p.position[0], p.position[2], cnv) is None
        }
        assert off_map <= {"m10_01_00_00"}, cnv


def test_progression_counts():
    """Seeds, tears, fragments and ashes: every world copy, no duplicates."""
    names = [p.items[0][2] for p in get_pickups() if p.item_type == "Progression"]
    assert names.count("Golden Seed") >= 30
    assert names.count("Sacred Tear") == 12
    assert names.count("Memory Stone") == 7
