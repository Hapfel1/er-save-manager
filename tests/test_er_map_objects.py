"""Elden Ring summoning pools, imp seals and paintings (data/map_objects*)."""

from __future__ import annotations

import pytest

from er_save_manager.data.map_objects import POOL, SEAL, map_objects, paintings
from er_save_manager.data.world_map import location_map_point
from er_save_manager.parser.event_flags import EventFlags

DATASETS = pytest.mark.parametrize(
    "is_convergence", [False, True], ids=["vanilla", "convergence"]
)
_BLANK = bytes(EventFlags.EVENT_FLAGS_SIZE)
# The Elden Beast's arena (Stone Platform) is outside every world map
OFF_MAP = {"m19_00_00_00"}


@DATASETS
def test_flags_are_storable_and_unique(is_convergence):
    objects = map_objects(is_convergence)
    flags = [o.flag_id for o in objects]
    assert len(flags) == len(set(flags))
    for flag in flags:
        EventFlags.get_flag(_BLANK, flag)


@DATASETS
def test_kinds(is_convergence):
    kinds = [o.kind for o in map_objects(is_convergence)]
    assert kinds.count(POOL) > 200
    assert kinds.count(SEAL) > 30


@DATASETS
def test_seal_keys(is_convergence):
    seals = [o for o in map_objects(is_convergence) if o.kind == SEAL]
    assert {o.keys for o in seals} == {1, 2}
    # Roundtable Hold's treasure room seal takes two keys
    assert next(o for o in seals if o.flag_id == 11100575).keys == 2


@DATASETS
def test_on_world_map(is_convergence):
    off = {
        o.map_id
        for o in map_objects(is_convergence)
        if location_map_point(o.map_id, o.position[0], o.position[2], is_convergence)
        is None
    }
    assert off <= OFF_MAP


@DATASETS
def test_paintings_pair_with_vista_reward(is_convergence):
    pairs = paintings(is_convergence)
    assert len(pairs) == 10
    for p in pairs:
        assert p.painting.items[0][2].endswith("Painting")
        assert p.reward.flag_id == p.painting.flag_id + 300
        assert p.reward.position is not None
