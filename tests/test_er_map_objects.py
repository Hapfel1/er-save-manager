"""Elden Ring summoning pools, imp seals and paintings (data/map_objects*)."""

from __future__ import annotations

from er_save_manager.data.map_objects import POOL, SEAL, map_objects, paintings
from er_save_manager.data.world_map import location_map_point
from er_save_manager.parser.event_flags import EventFlags

_BLANK = bytes(EventFlags.EVENT_FLAGS_SIZE)
# The Elden Beast's arena (Stone Platform) is outside every world map
OFF_MAP = {"m19_00_00_00"}


def test_map_objects():
    for cnv in (False, True):
        objects = map_objects(cnv)
        flags = [o.flag_id for o in objects]
        assert len(flags) == len(set(flags))
        for flag in flags:
            EventFlags.get_flag(_BLANK, flag)

        kinds = [o.kind for o in objects]
        assert kinds.count(POOL) > 200 and kinds.count(SEAL) > 30
        seals = [o for o in objects if o.kind == SEAL]
        assert {o.keys for o in seals} == {1, 2}
        # Roundtable Hold's treasure room seal takes two keys
        assert next(o for o in seals if o.flag_id == 11100575).keys == 2

        off = {
            o.map_id
            for o in objects
            if location_map_point(o.map_id, o.position[0], o.position[2], cnv) is None
        }
        assert off <= OFF_MAP

        pairs = paintings(cnv)
        assert len(pairs) == 10
        for p in pairs:
            assert p.painting.items[0][2].endswith("Painting")
            assert p.reward.flag_id == p.painting.flag_id + 300
            assert p.reward.position is not None
