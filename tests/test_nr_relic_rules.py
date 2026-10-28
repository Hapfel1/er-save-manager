"""Relic roll rules (games/NR/relic_rules.py) on relics the game rolled."""

import pytest

from er_save_manager.games.NR import relic_rules as rr
from er_save_manager.games.NR.relic_ops import prepare_relic, validate_relic

E = 0xFFFFFFFF

# Grand Luminous Scene, three normal effects.
GRAND = (1007222, [7060100, 7090100, 7001702], [E, E, E])
# Deep Grand Tranquil Scene: an Undertaker effect, rune acquisition, and
# Holy Attack Power Up +4 carrying Reduced Vigor and Arcane.
DEEP = (2010302, [6500900, 7110000, 6001801], [E, E, 6830400])
# Old Pocketwatch, a fixed relic.
FIXED = (10000, [10000, 7000402, E], [E, E, E])


def codes(relic):
    return {i.code for i in rr.check(*relic)}


def test_game_relics_pass_and_keep_their_order():
    for relic in (GRAND, DEEP, FIXED):
        assert rr.check(*relic) == []
        assert rr.canonical(relic[1], relic[2]) == (relic[1], relic[2])
    _rid, effects, curses = DEEP
    # Curse rows move with their effects
    assert rr.canonical(effects[::-1], curses[::-1]) == (effects, curses)


def test_normal_relic_rules():
    rid, effects, curses = GRAND
    heroes = sorted(
        e for e in rr.rollable_effects(rid) if rr._effect_info(e)[0] == 900
    )[:2]
    # Two hero effects share compatibility group 900
    assert codes((rid, [*heroes, effects[2]], curses)) == {"compat"}
    assert codes((rid, effects[:2], curses)) == {"count"}
    assert codes((rid, effects, [6830400, E, E])) == {"curse"}
    deep_only = DEEP[1][2]
    assert codes((rid, [effects[0], effects[1], deep_only], curses)) == {"pool"}


def test_deep_curse_pairing():
    rid, effects, curses = DEEP
    assert codes((rid, effects, [E, E, E])) == {"pairing"}
    other_curse = min(rr.curse_pool() - {curses[2]})
    assert codes((rid, effects, [other_curse, E, curses[2]])) == {"pairing"}


def test_fixed_and_placeholder_relics():
    rid = FIXED[0]
    assert rr.relic_kind(rid) == "fixed"
    assert prepare_relic(rid, [E, E, E], [E, E, E]) == (FIXED[1], FIXED[2])
    assert codes((rid, [10000, 7000502, E], [E, E, E])) == {"fixed"}
    assert rr.relic_kind(30000) == "unobtainable"
    with pytest.raises(ValueError):
        validate_relic(30000, [E, E, E], [E, E, E])


def test_edit_keeps_old_version_issues_as_warnings():
    rid, effects, _ = DEEP
    old = (rid, effects, [E, E, E])
    blocking, warnings = rr.edit_issues(old, old)
    assert blocking == [] and {i.code for i in warnings} == {"pairing"}

    blocking, _ = rr.edit_issues(DEEP, old)
    assert {i.code for i in blocking} == {"pairing"}


def test_unknown_effect_only_warns_on_edit():
    rid, effects, curses = GRAND
    edited = (rid, [effects[0], effects[1], 1234567], curses)
    blocking, warnings = rr.edit_issues(GRAND, edited)
    assert blocking == [] and {i.code for i in warnings} == {"unknown"}
    with pytest.raises(ValueError):
        validate_relic(*edited)


def test_conflicts_hides_same_effect_and_same_group():
    rid, effects, _ = GRAND
    heroes = sorted(
        e for e in rr.rollable_effects(rid) if rr._effect_info(e)[0] == 900
    )[:2]
    assert rr.conflicts(heroes[1], [heroes[0], E])
    assert rr.conflicts(effects[0], [effects[0]])
    assert not rr.conflicts(effects[0], [effects[1], effects[2]])
    assert not rr.conflicts(effects[0], [E, E])


def test_picker_lists_each_relic_type_once():
    entries = rr.picker_relics()
    labels = [label for _rid, label, _deep in entries]
    assert len(labels) == len(set(labels))
    kinds = {rr.relic_kind(rid) for rid, _l, _d in entries}
    assert kinds <= {"random", "deep", "fixed"}
    assert all(rr.slot_count(rid) > 0 for rid, _l, _d in entries)
    assert not any(label == "Antique" for _rid, label, _deep in entries)


def test_effect_names_drop_the_relic_tag():
    from er_save_manager.games.NR.item_db import effect_name

    assert effect_name(7001702) == "Lightning Attack Power Up +2"
    assert effect_name(6500900) == "[Undertaker] Executing Art readies Character Skill"
    assert effect_name(10000) == "FP Restoration upon Successive Attacks"


def test_allocation_follows_the_handle_ring():
    from types import SimpleNamespace

    from er_save_manager.games.NR.relic_ops import _allocate_state

    def slot(handles):
        return SimpleNamespace(
            item_states=[(h, 8, i * 8) for i, h in enumerate(handles)]
        )

    # Newest generation 0x81 ends at index 1: next free index after it.
    states = [0xC0810000, 0xC0810001, 0, 0xC0800003, 0]
    assert _allocate_state(slot(states)) == (16, 0xC0810002)
    # Last index used by the newest generation: wrap with the next one.
    states = [0, 0xC0800001, 0xC0800002]
    assert _allocate_state(slot(states)) == (0, 0xC0810000)
    assert _allocate_state(slot([0, 0])) == (0, 0xC0800000)
    assert _allocate_state(slot([0xC0800000])) is None
