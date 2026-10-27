"""Elden Ring NPC placement data (data/npc_locations*.json)."""

from __future__ import annotations

import pytest

from er_save_manager.data.npc_data import NPC_FLAGS
from er_save_manager.data.npc_locations import _placements, npc_spots
from er_save_manager.data.world_map import location_map_point

DATASETS = pytest.mark.parametrize(
    "is_convergence", [False, True], ids=["vanilla", "convergence"]
)
BLOCKS = {base for base, _ in NPC_FLAGS.values()}


@DATASETS
def test_flags_are_block_location_flags(is_convergence):
    stray = [
        flag
        for flag in _placements(is_convergence)
        if not any(base + 5 <= flag <= base + 17 for base in BLOCKS)
    ]
    assert stray == []


@DATASETS
def test_parts_on_world_map(is_convergence):
    off_map = {
        map_id
        for parts in _placements(is_convergence).values()
        for _name, map_id, x, _y, z in parts
        if location_map_point(map_id, x, z, is_convergence) is None
    }
    assert off_map == set()


def test_spots_follow_flags():
    """Varre at First Step (3185), marked hostile, then dead in place."""
    flags = {3180, 3185}
    spots = npc_spots(lambda f: f in flags)
    assert {s.name for s in spots} == {"White Mask Varré"}
    assert not any(s.hostile for s in spots)
    assert {s.map_id for s in spots} == {"m60_42_36_00"}

    flags = {3181, 3185}
    assert all(s.hostile for s in npc_spots(lambda f: f in flags))

    flags = {3181, 3183, 3185}
    spots = npc_spots(lambda f: f in flags)
    assert spots and all(s.dead and not s.hostile for s in spots)
