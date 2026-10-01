"""
Soulsplanner build parsing, against the inline script of build 32589 as the
site served it.
"""

from __future__ import annotations

import pytest

from er_save_manager.games.DS2.soulsplanner import (
    PlannerError,
    parse_build_html,
    parse_build_id,
)

_PAGE = (
    "<body><script>;var plannerId='darksouls2',savedBuild={class_:'knight',"
    "gender:0,covenant:'No_Covenant',armor:'Kings_Crown;Llewellyn_Armor;"
    "Faraam_Gauntlets;Saints_Trousers',weapons:'Fume_Sword;Fire;"
    "Dragonslayer_Spear;No_Infusion;Dagger;No_Infusion;Dagger;No_Infusion;"
    "Bare_Fists;No_Infusion;Helm_of_Aurous_Transparent;No_Infusion',grip:0,"
    "rings:'Third_Dragon_Ring;Life_Ring_3;Ring_of_Blades_2;No_Ring',"
    "spells:'Heal;No_Spell',items:'Estus_Flask;Lifegem;No_Item',vigor:50,"
    "endurance:28,vitality:10,attunement:4,strength:16,dexterity:50,"
    "adaptability:20,intelligence:15,faith:15};</script></body>"
)


def test_parse_build_id():
    assert parse_build_id("https://soulsplanner.com/darksouls2/32589") == "32589"
    assert parse_build_id("soulsplanner.com/darksouls2/32589/") == "32589"
    assert parse_build_id(" 32589 ") == "32589"
    with pytest.raises(PlannerError):
        parse_build_id("https://soulsplanner.com/darksouls3/32589")
    with pytest.raises(PlannerError):
        parse_build_id("https://example.com/darksouls2/32589")
    # The host must match exactly, not just contain the domain.
    with pytest.raises(PlannerError):
        parse_build_id("https://soulsplanner.com.example.com/darksouls2/32589")
    with pytest.raises(PlannerError):
        parse_build_id("https://soulsplanner.com@example.com/darksouls2/32589")


def test_parse_build_html():
    build = parse_build_html(_PAGE, "32589")
    assert build.class_name == "Knight"
    assert build.stats["vigor"] == 50
    assert build.level == 155

    by_name = {item.name: item for item in build.items}
    assert by_name["Fume Sword"].infusion == 1  # Fire
    assert by_name["Dagger"].count == 2
    assert by_name["Life Ring+3"].category == "rings"
    assert by_name["King's Crown"].category == "armors"
    assert by_name["Heal"].category == "spells"
    assert by_name["Lifegem"].category == "goods"
    # Empty slots are dropped, unmapped and unsafe slugs are reported.
    assert "Bare Fists" not in by_name
    assert build.unknown == ["Helm of Aurous Transparent", "Estus Flask"]


def test_page_without_build():
    with pytest.raises(PlannerError):
        parse_build_html("<html></html>", "1")
