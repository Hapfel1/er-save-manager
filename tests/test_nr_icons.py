"""Relic and effect icons (games/NR/icons.py, nr_icons.db)."""

import json
from pathlib import Path

from er_save_manager.games.NR import icons
from er_save_manager.games.NR.icons import effect_icon, relic_icon, vessel_icon


def test_icons_by_id():
    # Grand Luminous Scene; Dexterity +3; Wylder's Urn
    assert relic_icon(1007222).size == (128, 128)
    assert effect_icon(7000402).size == (80, 80)
    assert vessel_icon(1000).size == (128, 128)
    # Old Pocketwatch (fixed), curse Reduced Vigor and Arcane, Wylder's Goblet
    assert None not in (relic_icon(10000), effect_icon(6830400), vessel_icon(1001))
    assert (
        relic_icon(123456789)
        is effect_icon(0xFFFFFFFF)
        is vessel_icon(123456789)
        is None
    )


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
