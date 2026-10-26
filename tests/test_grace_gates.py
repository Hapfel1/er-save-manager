"""Boss-gated graces (data/grace_bosses.json, ui/boss_gate)."""

from er_save_manager.data.grace_data import grace_gate, location_gate
from er_save_manager.data.locations import LOCATIONS, get_grace_locations
from er_save_manager.ui import boss_gate
from er_save_manager.ui.boss_gate import closed_gate, filter_unlock


def test_boss_room_graces_have_their_boss():
    # common_func 9005810(10000800, ..., 10001950): Godrick's grace
    gate = grace_gate(71000, convergence=False)
    assert gate.flag_id == 10000800
    assert gate.boss == "Godrick the Grafted"
    # Morgott's grace waits for the throne event flag, not flags[0]
    assert grace_gate(71100, convergence=False).boss == "Morgott, the Omen King"
    # The First Step is registered unconditionally
    assert grace_gate(76101, convergence=False) is None


def test_convergence_uses_its_own_events():
    # Convergence gates Raya Lucaria Grand Library on the Red Wolf
    assert grace_gate(71400, convergence=False).flag_id == 14000800
    assert grace_gate(71400, convergence=True).flag_id == 14000850


def test_location_on_a_gated_grace_shares_the_gate():
    loc = LOCATIONS["m60_43_30_00"]
    gate = location_gate(loc.tile_type, loc.map_id_str, loc.flag_id, False)
    assert gate.boss == "Leonine Misbegotten"
    stormveil = LOCATIONS["m10_00_00_00"]
    assert location_gate(stormveil.tile_type, stormveil.map_id_str, 0, False) is None


def test_closed_gate_follows_the_boss_flag():
    grace = next(g for g in get_grace_locations() if g.flag_id == 71000)
    assert closed_gate(grace, False, lambda f: False) is not None
    assert closed_gate(grace, False, lambda f: f == 10000800) is None
    # unreadable flags count as open
    assert closed_gate(grace, False, lambda f: None) is None


def test_filter_unlock_skips_or_keeps_closed_graces(monkeypatch):
    flags = [71000, 76101]
    alive = lambda f: False  # noqa: E731
    answers = iter([False, True, None])
    monkeypatch.setattr(
        boss_gate.CTkMessageBox, "askyesnocancel", lambda *a, **k: next(answers)
    )
    assert filter_unlock(flags, {}, False, alive, None) == [76101]
    assert filter_unlock(flags, {}, False, alive, None) == flags
    assert filter_unlock(flags, {}, False, alive, None) is None
    # boss defeated: nothing to ask
    defeated = lambda f: f == 10000800  # noqa: E731
    assert filter_unlock(flags, {}, False, defeated, None) == flags
