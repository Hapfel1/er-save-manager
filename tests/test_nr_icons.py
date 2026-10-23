"""Relic and effect icons (games/NR/icons.py, nr_icons.db)."""

import json
from pathlib import Path

from er_save_manager.games.NR import icons
from er_save_manager.games.NR.icons import effect_icon, relic_icon, vessel_icon

E = 0xFFFFFFFF


def test_relic_icons_by_relic_id():
    # Grand Luminous Scene, Old Pocketwatch (fixed)
    assert relic_icon(1007222).size == (128, 128)
    assert relic_icon(10000) is not None


def test_effect_and_curse_icons():
    # Dexterity +3, curse Reduced Vigor and Arcane
    assert effect_icon(7000402).size == (80, 80)
    assert effect_icon(6830400) is not None


def test_vessel_icons():
    # Wylder's Urn, Wylder's Goblet
    assert vessel_icon(1000).size == (128, 128)
    assert vessel_icon(1001) is not None


def test_missing_ids_have_no_icon():
    assert relic_icon(123456789) is None
    assert effect_icon(E) is None
    assert vessel_icon(123456789) is None


def test_every_item_has_an_icon():
    items = json.loads(
        (Path(icons.__file__).parent / "data" / "nr_items.json").read_text(
            encoding="utf-8"
        )
    )
    icons._ensure_loaded()
    for table, keys in (
        ("relics", icons._relic_keys),
        ("effects", icons._effect_keys),
        ("vessels", icons._vessel_keys),
    ):
        missing = [i for i in map(int, items[table]) if i not in keys]
        assert not missing, (table, missing)
