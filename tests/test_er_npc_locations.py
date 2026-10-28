"""Elden Ring NPC placement data (data/npc_locations*.json)."""

from __future__ import annotations

from er_save_manager.data.npc_data import NPC_FLAGS
from er_save_manager.data.npc_locations import _placements, npc_spots
from er_save_manager.data.world_map import location_map_point

BLOCKS = {base for base, _ in NPC_FLAGS.values()}


def test_placements():
    for cnv in (False, True):
        placements = _placements(cnv)
        # Every placement flag is a location flag of an NPC block
        stray = [f for f in placements if not any(b + 5 <= f <= b + 17 for b in BLOCKS)]
        assert stray == []
        off_map = {
            map_id
            for parts in placements.values()
            for _name, map_id, x, _y, z in parts
            if location_map_point(map_id, x, z, cnv) is None
        }
        assert off_map == set()


def test_spots_follow_flags():
    """Varre at First Step (3185), marked hostile, then dead in place."""
    spots = npc_spots(lambda f: f in {3180, 3185})
    assert {s.name for s in spots} == {"White Mask Varré"}
    assert not any(s.hostile for s in spots)
    assert {s.map_id for s in spots} == {"m60_42_36_00"}
    assert all(s.hostile for s in npc_spots(lambda f: f in {3181, 3185}))
    spots = npc_spots(lambda f: f in {3181, 3183, 3185})
    assert spots and all(s.dead and not s.hostile for s in spots)
