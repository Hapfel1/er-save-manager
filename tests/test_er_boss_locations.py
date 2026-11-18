"""Elden Ring boss map data (data/boss_locations*.json)."""

from __future__ import annotations

import pytest

from er_save_manager.data.boss_data import BOSS_CATEGORIES, BOSSES
from er_save_manager.data.boss_locations import boss_regions, boss_spots
from er_save_manager.data.grace_data import grace_gate
from er_save_manager.data.icon_manager import has_icon, icons_available
from er_save_manager.data.world_map import location_map_point
from er_save_manager.parser.event_flags import EventFlags

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
    by_name = {b.name: b for b in spots}
    sigur = by_name["Sigur, Night's Captain"]
    assert sigur.flags[:7] == tuple(BOSSES["Godfrey, First Elden Lord"]["flags"])
    # Defeat flags the mod's events leave set, not phase flags they clear
    assert by_name["Scion of the Sealed God"].flags[0] == 12010810
    assert by_name["Dakk, Starcaller Lord"].flags[0] == 1051360800
    assert "Crucible Knight & Misbegotten Warrior" not in by_name
    assert by_name["Seera, Blade of the Ancients"].flags[0] == 13000850
    # One row per defeat flag, every flag storable in the save
    assert len({b.flags[0] for b in spots}) == len(spots)
    assert all(EventFlags.has_flag(f) for b in spots for f in b.flags)
    assert boss_regions() == sorted(BOSS_CATEGORIES)
    # Grace gate warnings name the boss of the save's flavor
    assert grace_gate(71101, False).boss == "Godfrey, First Elden Lord"
    assert grace_gate(71101, True).boss == "Sigur, Night's Captain"

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
