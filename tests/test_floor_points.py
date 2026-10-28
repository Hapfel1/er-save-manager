"""Teleport-anywhere floor points (data/floor_points.py, floor_*.bin)."""

import pytest

from er_save_manager.data import floor_points
from er_save_manager.data.floor_points import (
    bloodstain_location,
    floors_near,
    pin_location,
    tile_floor,
)
from er_save_manager.data.locations import get_grace_locations
from er_save_manager.data.world_map import (
    MAP_LANDS_BETWEEN,
    MAP_REALM_OF_SHADOW,
    global_to_map,
    location_map_point,
)
from er_save_manager.ui.boss_gate import closed_gate


def _overworld(tile_x, tile_z, x, z):
    return global_to_map(tile_x * 256 + 128 + x, tile_z * 256 + 128 + z)


def test_bridge_has_two_floors():
    # m60_43_37 bridge: deck and the ground under it
    mx, my = _overworld(43, 37, 89.0, -91.0)
    floors = floors_near(MAP_LANDS_BETWEEN, mx, my, False, radius=6)
    heights = sorted(round(p.y) for p in floors if p.map_id_str == "m60_43_37_00")
    assert heights == [65, 92]


def test_overworld_click_takes_the_top_floor_first():
    # m60_34_42: ground at y 238 and a ledge at y 400 within 4 units
    floors = floors_near(MAP_LANDS_BETWEEN, 1680, 5776, False, radius=18)
    assert round(floors[0].y) == 400
    assert any(round(p.y) == 238 for p in floors)


def test_leyndell_click_takes_the_city_before_the_sewers():
    # the Subterranean Shunning-Grounds (m35) lie nearer under this spot
    floors = floors_near(MAP_LANDS_BETWEEN, 4400, 3536, False, radius=18)
    maps = [p.map_id_str for p in floors]
    assert maps[0] == "m11_00_00_00"
    assert maps.index("m11_05_00_00") < maps.index("m35_00_00_00")


def test_sea_has_no_floor():
    # south of Caelid, on the sea surface sheet
    mx, my = _overworld(47, 37, -100.0, -60.0)
    assert floors_near(MAP_LANDS_BETWEEN, mx, my, False, radius=8) == []
    # m60_41_45: coarse sea bed at y -51
    mx, my = _overworld(41, 45, -3.0, -3.0)
    assert floors_near(MAP_LANDS_BETWEEN, mx, my, False, radius=8) == []


def test_hollow_under_the_ground_is_left_out():
    # m61_46_38 Cerulean Coast: a small navmesh pocket at y 0.6 under the
    # grass at y 3-5
    mx, my = _overworld(46, 38, 37.0, 115.0)
    floors = floors_near(MAP_REALM_OF_SHADOW, mx, my, False, radius=4)
    assert floors
    assert all(p.y > 2 for p in floors)


def test_coarse_land_tiles_are_kept():
    # m60_53_38 east Caelid: coarse navmesh, land on the world map
    mx, my = _overworld(53, 38, -1.0, -1.0)
    floors = floors_near(MAP_LANDS_BETWEEN, mx, my, False, radius=6)
    assert any(p.map_id_str == "m60_53_38_00" for p in floors)


def test_forge_of_the_giants_bowl_keeps_only_the_rim():
    # m60_54_53: bowl center (-86, -36), rim walkway at y ~1970
    mx, my = _overworld(54, 53, -86.0, -36.0)
    assert floors_near(MAP_LANDS_BETWEEN, mx, my, False, radius=30) == []
    mx, my = _overworld(54, 53, -86.0, -36.0 + 68.0)
    floors = floors_near(MAP_LANDS_BETWEEN, mx, my, False, radius=8)
    assert any(p.y > 1960 for p in floors)


def test_legacy_points_match_the_map_placement():
    f = floor_points._file("floor_vanilla.bin")
    checked = 0
    for map_id in ("m10_00_00_00", "m12_01_00_00", "m30_00_00_00", "m35_00_00_00"):
        rec = f.record(map_id)
        for (bx, bz), _ in list(rec.blocks.items())[:4]:
            first, _heights, _arena, place = floor_points._decode(rec, (bx, bz))
            for c in range(0, 1024, 31):
                for k in range(first[c], first[c + 1]):
                    x = (bx * 32 + c % 32 + 0.5) * 2
                    z = (bz * 32 + c // 32 + 0.5) * 2
                    no, ax, az, _ = rec.placement[place[k] - 1]
                    expected = location_map_point(map_id, x, z, False)
                    assert expected[0] == no
                    assert abs(expected[1] - (x + ax)) < 0.01
                    assert abs(expected[2] - (az - z)) < 0.01
                    checked += 1
    assert checked > 50


def test_arena_points_carry_the_boss_flag():
    # Godrick's spawn in m10_00_00_00
    no, mx, my = location_map_point("m10_00_00_00", -235.6, 348.3, False)
    floors = floors_near(no, mx, my, False, radius=6)
    pin = next(p for p in floors if p.map_id_str == "m10_00_00_00")
    assert pin.arena_flag == 10000800
    for loc, kind in (
        (pin_location(pin), "pin"),
        (bloodstain_location(pin), "bloodstain"),
    ):
        assert loc.tile_type == kind
        assert loc.safe_coords == (pin.x, pin.y, pin.z)
        assert closed_gate(loc, False, lambda f: False).boss == "Godrick the Grafted"
        assert closed_gate(loc, False, lambda f: True) is None


def test_pin_location_takes_the_map_region():
    mx, my = _overworld(42, 36, 13.0, -9.0)
    pin = floors_near(MAP_LANDS_BETWEEN, mx, my, False, radius=6)[0]
    loc = pin_location(pin)
    assert loc.map_id_str == "m60_42_36_00"
    assert loc.map_bytes == bytes([0, 36, 42, 60])
    assert loc.safe_coords == (pin.x, pin.y, pin.z)
    assert not loc.is_dlc


def test_convergence_maps_fall_back_to_vanilla():
    assert floor_points._record("m31_81_00_00", False) is None
    assert floor_points._record("m31_81_00_00", True) is not None
    # unchanged overworld tile: same record as vanilla
    assert floor_points._record("m60_42_36_00", True) is floor_points._record(
        "m60_42_36_00", False
    )


def test_grace_warp_points_are_anchors():
    # Convergence's Lucarian Nexus grace stands on a structure the mod adds
    # without navmesh
    grace = next(
        g
        for g in get_grace_locations(True)
        if g.name == "Liurnia of the Lakes - Lucarian Nexus"
    )
    no, mx, my = location_map_point(
        grace.map_id_str, grace.safe_coords[0], grace.safe_coords[2], True
    )
    pin = floors_near(no, mx, my, True, radius=2)[0]
    assert (pin.x, pin.y, pin.z) == pytest.approx(grace.safe_coords, abs=0.01)


def test_tile_floor():
    point = (9.3, 236.2, 43.8)  # m60_33_40_00 tile warp point
    assert tile_floor("m60_33_40_00", point, False) == point
    # m61_49_39_00 stored point lies past the tile edge (z 188.8), above a
    # gorge with floor at y -572
    point = (-14.0, 68.4, 188.8)
    assert tile_floor("m61_49_39_00", point, False) == pytest.approx(
        (93.779, 78.643, -94.08), abs=0.01
    )
