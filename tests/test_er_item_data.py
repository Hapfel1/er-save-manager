"""Elden Ring weapon and Ash of War CSVs checked against the game params.

tests/fixtures/er_weapon_params.json holds the relevant EquipParamWeapon,
EquipParamGem and ReinforceParamWeapon facts for every ID in the CSVs, taken
from the vanilla regulation and the Convergence regulation. A wrong CSV value
lets the editor create items the game cannot produce (an impossible upgrade
level, an affinity on a weapon that cannot be infused) or hides valid Ashes
of War from the picker.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

ITEMS = Path(__file__).parent.parent / "src" / "er_save_manager" / "data" / "items"
PARAMS = json.loads(
    (Path(__file__).parent / "fixtures" / "er_weapon_params.json").read_text(
        encoding="utf-8"
    )
)

AFFINITIES = {
    "vanilla": [
        "Standard", "Heavy", "Keen", "Quality", "Fire", "Flame Art", "Lightning",
        "Sacred", "Magic", "Cold", "Poison", "Blood", "Occult",
    ],
    "convergence": [
        "Standard", "Heavy", "Keen", "Quality", "Glint", "Dragonkin", "Gravity",
        "Flame", "Golden", "Draconic", "Bestial", "Night", "Lava", "Frenzy",
        "Death", "Godslayer", "Frost", "Aberrant", "Bloodflame", "Rotten",
        "Storm", "Psionic",
    ],
}  # fmt: skip

# Upgrade cap the editor applies per reinforcement kind (inventory_editor).
UPGRADE_CAP = {
    "vanilla": {"standard": 25, "somber": 10, "none": 0},
    "convergence": {"standard": 15, "somber": 15, "none": 0},
}

BASE_WEAPON_FILES = [
    "Weapons/*.csv",
    "DLC/DLCWeapons/*.csv",
    "TarnishedPack/*Weapons.csv",
]
BASE_GEM_FILES = ["Gems.csv", "DLC/DLCGems.csv"]
CNV_WEAPON_FILES = ["Convergence/Weapons/*.csv", "Convergence/Spelltools/*.csv"]
CNV_GEM_FILES = ["Convergence/ConvergenceGems.csv"]

# (fixture section, game, files, column prefix): base-game rows describe both
# games, the vanilla values in the plain columns and the Convergence values in
# the convergence_* columns. Convergence-only rows use the plain columns.
WEAPON_VIEWS = [
    ("vanilla", "vanilla", BASE_WEAPON_FILES, ""),
    ("convergence_base", "convergence", BASE_WEAPON_FILES, "convergence_"),
    ("convergence", "convergence", CNV_WEAPON_FILES, ""),
]
GEM_VIEWS = [
    ("vanilla", "vanilla", BASE_GEM_FILES, ""),
    ("convergence_base", "convergence", BASE_GEM_FILES, "convergence_"),
    ("convergence", "convergence", CNV_GEM_FILES, ""),
]


def _rows(patterns: list[str]) -> list[tuple[str, dict]]:
    out = []
    for pattern in patterns:
        for path in sorted(ITEMS.glob(pattern)):
            with path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    out.append((f"{path.relative_to(ITEMS)}:{row['ID']}", row))
    return out


def _split(value: str | None) -> list[str]:
    return [x for x in (value or "").split("|") if x]


def _cases(views):
    for section, game, patterns, prefix in views:
        for tag, row in _rows(patterns):
            if int(row["ID"]) >= 0:
                yield pytest.param(section, game, prefix, row, id=f"{section}:{tag}")


@pytest.mark.parametrize(("section", "game", "prefix", "row"), _cases(WEAPON_VIEWS))
def test_weapon_row_matches_params(
    section: str, game: str, prefix: str, row: dict
) -> None:
    param = PARAMS[section]["weapons"].get(row["ID"])
    assert param is not None, (
        f"{row['Name']} is not in the param fixture; regenerate it"
    )
    affinities = AFFINITIES[game]
    # Base rows keep the vanilla affinities in allowed_affinities
    aff_col = "convergence_affinities" if prefix else "allowed_affinities"

    assert int(row[f"{prefix}wepType"]) == param["wepType"]
    assert row[f"{prefix}wepTypeCol"] == PARAMS["wepTypeColumns"].get(
        str(param["wepType"]), ""
    ), "wepTypeCol must name the EquipParamGem canMountWep column for this wepType"
    assert (row[f"{prefix}aow_allowed"] == "1") == param["mountable"]
    assert int(row["maxArrowQuantity"]) == param["maxArrowQuantity"]
    assert UPGRADE_CAP[game][row[f"{prefix}reinforcement"]] == param["maxUpgrade"]

    listed = _split(row[aff_col])
    if param["infusable"]:
        assert listed == [affinities[i] for i in param["affinityRows"]]
    else:
        assert listed in ([], ["Standard"])


@pytest.mark.parametrize(("section", "game", "prefix", "row"), _cases(GEM_VIEWS))
def test_gem_row_matches_params(
    section: str, game: str, prefix: str, row: dict
) -> None:
    param = PARAMS[section]["gems"].get(row["ID"])
    assert param is not None, (
        f"{row['Name']} is not in the param fixture; regenerate it"
    )
    affinities = AFFINITIES[game]
    aff_col = "convergence_affinities" if prefix else "allowedAffinities"

    assert sorted(_split(row[f"{prefix}compatibleWepTypes"])) == param["mount"]
    assert _split(row[aff_col]) == [affinities[i] for i in param["affinities"]]
    if section != "convergence":
        default = row[f"{prefix}defaultAffinity"] or "Standard"
        assert default == affinities[param["default"]]


@pytest.fixture(scope="module")
def item_db():
    from er_save_manager.data.item_database import get_item_database

    return get_item_database()


def _weapons_and_gems(db, is_cnv: bool):
    from er_save_manager.data.item_database import ItemCategory

    weapons, gems = {}, {}
    for name, cat in db.categories:
        if not is_cnv and name.startswith("Convergence"):
            continue
        for item in db.get_items_by_category(name):
            item = db.resolve(item, is_cnv)
            if cat == ItemCategory.WEAPON:
                weapons[item.full_id] = item
            elif cat == ItemCategory.GEM and item.id >= 0:
                gems[item.full_id] = item
    return weapons, gems


@pytest.mark.parametrize("is_cnv", [False, True], ids=["vanilla", "convergence"])
def test_every_mountable_weapon_has_an_ash_of_war(item_db, is_cnv: bool) -> None:
    """An empty Ash of War picker means a wepTypeCol no gem uses."""
    weapons, gems = _weapons_and_gems(item_db, is_cnv)
    columns = {c for g in gems.values() for c in g.compatible_wep_types}
    missing = [
        w.name
        for w in weapons.values()
        if w.aow_allowed and w.reinforcement == "standard"
        and w.wep_type_col not in columns
    ]  # fmt: skip
    assert not missing


def test_convergence_view_of_base_rows(item_db) -> None:
    lance = item_db.get_item_by_id(17060000)
    assert len(lance.allowed_affinities) == 13
    cnv_lance = item_db.get_item_by_id(17060000, True)
    assert cnv_lance.max_upgrade == 15
    assert "Psionic" in cnv_lance.allowed_affinities

    # Bows take Ashes of War only in Convergence
    assert not item_db.get_item_by_id(41030000).aow_allowed
    assert item_db.get_item_by_id(41030000, True).aow_allowed

    # A Convergence CSV row replaces the generated view
    assert item_db.get_item_by_id(1150000, True).category_name.startswith("Convergence")


# ---- add-time validation ----------------------------------------------------

GEM = 0x80000000
LANCE, METEORITE_STAFF, BUCKLER, ERDTREE_BOW = 17060000, 33250000, 30000000, 41030000
CHARGE_FORTH, LIONS_CLAW = GEM | 10500, GEM | 10000


def _validate(item_db, is_cnv: bool, base_id: int, upgrade=0, aow_id=0):
    from types import SimpleNamespace

    from er_save_manager.ui.editors.inventory_editor import InventoryEditor

    table = (
        InventoryEditor._AFFINITIES_CNV
        if is_cnv
        else InventoryEditor._AFFINITIES_VANILLA
    )
    stub = SimpleNamespace(
        _is_cnv_save=lambda: is_cnv, _affinity_by_code=lambda: dict(table)
    )
    return InventoryEditor._validate_weapon(stub, item_db, base_id, upgrade, aow_id)[0]


def test_validation_vanilla(item_db) -> None:
    fire = 4 * 100
    assert _validate(item_db, False, LANCE + fire, aow_id=CHARGE_FORTH)
    assert not _validate(item_db, False, LANCE + fire)
    assert not _validate(item_db, False, LANCE, aow_id=LIONS_CLAW)
    assert not _validate(item_db, False, LANCE, upgrade=26)
    assert _validate(item_db, False, METEORITE_STAFF)
    assert not _validate(item_db, False, METEORITE_STAFF, upgrade=25)


def test_validation_convergence(item_db) -> None:
    psionic = 21 * 100
    assert _validate(item_db, True, LANCE + psionic, aow_id=CHARGE_FORTH)
    assert not _validate(item_db, True, LANCE, upgrade=16)
    # Shields keep Standard in Convergence
    assert not _validate(item_db, True, BUCKLER + 100)
    _, gems = _weapons_and_gems(item_db, True)
    bow_col = item_db.get_item_by_id(ERDTREE_BOW, True).wep_type_col
    bow_gem = next(g for g in gems.values() if bow_col in g.compatible_wep_types)
    assert _validate(item_db, True, ERDTREE_BOW, aow_id=bow_gem.full_id)
    assert not _validate(item_db, False, ERDTREE_BOW, aow_id=bow_gem.full_id)
