"""Elden Ring NPC placement data (data/npc_locations*.json)."""

from __future__ import annotations

from er_save_manager.data.invader_data import (
    get_invaders,
    invader_blocked,
    reset_invader,
)
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


def _quest_spots(flags):
    return [s for s in npc_spots(lambda f: f in flags) if not s.invader_key]


def test_spots_follow_flags():
    """Varre at First Step (3185), marked hostile, then dead in place."""
    spots = _quest_spots({3180, 3185})
    assert {s.name for s in spots} == {"White Mask Varré"}
    assert not any(s.hostile for s in spots)
    assert {s.map_id for s in spots} == {"m60_42_36_00"}
    assert all(s.hostile for s in _quest_spots({3181, 3185}))
    spots = _quest_spots({3181, 3183, 3185})
    assert spots and all(s.dead and not s.hostile for s in spots)


class _Flags(dict):
    def get_flag(self, flag_id):
        return self.get(flag_id, False)

    def set_flag(self, flag_id, state):
        self[flag_id] = state


def test_invaders():
    """Leontiel: hostile until defeated; reset clears the invasion flags and
    the reward only on request. The Convergence drops four invasions."""
    for cnv in (False, True):
        invaders = get_invaders(cnv)
        assert all(
            location_map_point(i.map_id, i.position[0], i.position[2], cnv)
            for i in invaders
        )
    assert len(get_invaders()) - len(get_invaders(True)) == 4
    leontiel = next(i for i in get_invaders() if i.name == "Knight Leontiel")
    spot = next(s for s in npc_spots(lambda f: False) if s.invader_key == leontiel.key)
    assert spot.hostile and not spot.dead
    flags = _Flags(dict.fromkeys((*leontiel.clear_flags, 1052397500), True))
    reset_invader(flags, leontiel)
    assert flags == {
        1052390180: False,
        1052392181: False,
        1052392182: False,
        1052397500: True,
    }
    reset_invader(flags, leontiel, reward=True)
    assert flags[1052397500] is False
    # Gate: Tarnished Pack + Radahn defeated
    assert invader_blocked(_Flags(), leontiel)
    assert not invader_blocked(_Flags({1052390910: True}), leontiel)
    # Defeating a Moore invasion ends his revenge invasions
    moore = [i for i in get_invaders() if i.name == "Moore"]
    assert len(moore) == 6
    assert all(invader_blocked(_Flags({2045429280: True}), i) for i in moore)
    # Varre's red sign stands elsewhere in The Convergence
    varre = [
        next(i for i in get_invaders(cnv) if i.name == "White Mask Varré")
        for cnv in (False, True)
    ]
    assert varre[0].position != varre[1].position
