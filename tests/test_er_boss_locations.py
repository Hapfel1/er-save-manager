"""Elden Ring boss map data (data/boss_locations*.json)."""

from __future__ import annotations

import pytest

from er_save_manager.data.boss_data import BOSSES
from er_save_manager.data.boss_locations import boss_spots
from er_save_manager.data.icon_manager import has_icon, icons_available
from er_save_manager.data.world_map import location_map_point

# Arenas outside any world map: Elden Beast, the Chapel of Anticipation
# (Grafted Scion) and the Siofra / Nokron ancestor arenas
OFF_MAP = {
    "Elden Beast",
    "Grafted Scion",
    "Ancestor Spirit",
    "Regal Ancestor Spirit",
}


def test_boss_spots():
    assert {b.name for b in boss_spots()} <= set(BOSSES)
    spots = boss_spots(True)
    names = [b.name for b in spots]
    assert len(names) == len(set(names))
    assert all(b.flags for b in spots)
    # The mod's own bosses and the vanilla flags it gives to another boss
    assert "Franken-Abductor-Stein" in names
    sigur = next(b for b in spots if b.name == "Sigur, Night's Captain")
    assert sigur.flags == tuple(BOSSES["Godfrey, First Elden Lord"]["flags"])

    for cnv in (False, True):
        off = {
            b.name
            for b in boss_spots(cnv)
            if location_map_point(b.map_id, b.position[0], b.position[2], cnv) is None
        }
        assert off <= OFF_MAP, cnv


@pytest.mark.skipif(not icons_available(), reason="icons.db not present")
def test_faces_have_icons():
    for cnv in (False, True):
        spots = boss_spots(cnv)
        assert [b.name for b in spots if b.face and not has_icon(b.face)] == []
        # Only bosses whose defeat awards no item are left without one
        assert sum(1 for b in spots if not b.face) <= 15
