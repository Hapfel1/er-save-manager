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


@pytest.mark.parametrize("relic", [GRAND, DEEP, FIXED])
def test_game_relics_pass_and_keep_their_order(relic):
    assert rr.check(*relic) == []
    assert rr.canonical(relic[1], relic[2]) == (relic[1], relic[2])


def test_canonical_restores_game_order_with_curse_rows():
    rid, effects, curses = DEEP
    shuffled = (effects[::-1], curses[::-1])
    assert rr.canonical(*shuffled) == (effects, curses)


def test_two_hero_effects_share_a_compatibility_group():
    rid = GRAND[0]
    heroes = sorted(
        e for e in rr.rollable_effects(rid) if rr._effect_info(e)[0] == 900
    )[:2]
    assert codes((rid, [*heroes, GRAND[1][2]], [E, E, E])) == {"compat"}


def test_effect_count_follows_slot_count():
    rid, effects, curses = GRAND
    assert codes((rid, effects[:2], curses)) == {"count"}


def test_normal_relic_rules():
    rid, effects, _ = GRAND
    assert codes((rid, effects, [6830400, E, E])) == {"curse"}
    deep_only = DEEP[1][2]
    assert codes((rid, [effects[0], effects[1], deep_only], [E, E, E])) == {"pool"}


def test_deep_curse_pairing():
    rid, effects, curses = DEEP
    assert codes((rid, effects, [E, E, E])) == {"pairing"}
    other_curse = min(rr.curse_pool() - {curses[2]})
    assert codes((rid, effects, [other_curse, E, curses[2]])) == {"pairing"}


def test_fixed_relic_effects():
    rid = FIXED[0]
    assert rr.relic_kind(rid) == "fixed"
    assert prepare_relic(rid, [E, E, E], [E, E, E]) == (FIXED[1], FIXED[2])
    assert codes((rid, [10000, 7000502, E], [E, E, E])) == {"fixed"}


def test_placeholder_relic_is_unobtainable():
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
