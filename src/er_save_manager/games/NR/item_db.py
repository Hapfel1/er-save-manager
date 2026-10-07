"""
Nightreign item database.

Effect tier classification (from AttachEffectParam ID ranges):
  "deep"    6000000-6799999  - effects valid on deep relics
  "normal"  7000000-7999999  - effects valid on normal relics
  "special" <100000          - fixed hero/ability effects (any relic type)
  "curse"   6800000-6999999  - curse slot effects (separate from effect slots)

Validation rules:
  Effect slots (1-3):
    - deep relic:   tier in ("deep", "special", "normal")  - game allows both
    - normal relic: tier in ("normal", "special", "deep")   both tiers in practice
    Practical filter: show deep effects for deep relics, normal effects for normal relics,
    special effects always. Both tiers work in-game, so the filter is advisory.
  Curse slots (1-3):
    - only tier == "curse" effects
  Hero restriction:
    - effect.heroes[hero_index] must be 1 (0-based, hero_type 1 = index 0)

Pool IDs in EquipParamAntique (attachEffectTableId_N) reference an unreleased
AttachEffectGroupParam table. Tier-based validation is the best available approach
without that table.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "nr_items.json"
_EMPTY = 0xFFFFFFFF
# Relic ids from here on are randomly rolled; lower ids are fixed relics.
_FIRST_RANDOM_RELIC = 1_000_000
# Effect names of hero-specific effects start with "[Relic - Hero]" or
# "[Special Relic - Hero]".
_HERO_LABEL = re.compile(r"\[[^\]]*? - ([^\]]+)\]")
_db: dict | None = None


def _load() -> dict:
    global _db
    if _db is None:
        _db = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    return _db


# ---------------------------------------------------------------------------
# Relics
# ---------------------------------------------------------------------------


def get_relic(real_item_id: int) -> dict | None:
    return _load()["relics"].get(str(real_item_id))


def relic_name(real_item_id: int) -> str:
    r = get_relic(real_item_id)
    return r["name"] if r else f"Unknown ({real_item_id})"


def all_relics() -> dict[str, dict]:
    return _load()["relics"]


def relics_sorted() -> list[tuple[int, str, bool]]:
    """Return (id, name, is_deep) sorted by name."""
    return sorted(
        ((int(k), v["name"], v["deep"]) for k, v in _load()["relics"].items()),
        key=lambda x: x[1],
    )


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------


def get_effect(effect_id: int) -> dict | None:
    if effect_id == 0xFFFFFFFF or effect_id < 0:
        return None
    return _load()["effects"].get(str(effect_id))


def effect_name(effect_id: int) -> str:
    if effect_id == 0xFFFFFFFF or effect_id < 0:
        return "(empty)"
    e = get_effect(effect_id)
    return e["name"] if e else f"Unknown ({effect_id})"


def all_effects() -> dict[str, dict]:
    return _load()["effects"]


def effects_for_slot(is_deep_relic: bool, hero_type: int = 0) -> list[tuple[int, str]]:
    """
    Return (effect_id, name) pairs valid for an effect slot (not curse slot).

    is_deep_relic: whether the relic has isDeepRelic=1.
    hero_type: 1-10 to filter by hero, 0 = no hero filter.

    Primary tier shown: "deep" for deep relics, "normal" for normal relics.
    "special" effects are always included.
    The opposite tier is excluded from the list (advisory filter matching game UI).
    """
    primary = "deep" if is_deep_relic else "normal"
    hero_idx = hero_type - 1
    result = []
    for sid, e in _load()["effects"].items():
        tier = e["tier"]
        if tier == "curse":
            continue
        if tier not in (primary, "special"):
            continue
        if hero_type != 0 and hero_idx < len(e["heroes"]) and not e["heroes"][hero_idx]:
            continue
        result.append((int(sid), e["name"]))
    return sorted(result, key=lambda x: x[1])


def effects_for_curse_slot() -> list[tuple[int, str]]:
    """Return (effect_id, name) pairs valid for a curse slot."""
    return sorted(
        (
            (int(sid), e["name"])
            for sid, e in _load()["effects"].items()
            if e["tier"] == "curse"
        ),
        key=lambda x: x[1],
    )


def validate_effect(
    effect_id: int, is_deep_relic: bool, hero_type: int = 0
) -> str | None:
    """
    Validate an effect ID for an effect slot.
    Returns None if valid, or an error string if invalid.
    """
    if effect_id == 0xFFFFFFFF:
        return None  # empty is always valid
    e = get_effect(effect_id)
    if e is None:
        return f"Effect {effect_id} not found in database."
    if e["tier"] == "curse":
        return "Curse effects cannot go in effect slots."
    if e["tier"] == "other":
        return "Not a relic effect."
    hero_idx = hero_type - 1
    if hero_type != 0 and hero_idx < len(e["heroes"]) and not e["heroes"][hero_idx]:
        hero_names = [
            "Wylder",
            "Guardian",
            "Ironeye",
            "Duchess",
            "Raider",
            "Revenant",
            "Recluse",
            "Executor",
            "Scholar",
            "Undertaker",
        ]
        name = (
            hero_names[hero_idx] if hero_idx < len(hero_names) else f"hero {hero_type}"
        )
        return f"Effect not allowed on {name}."
    return None


def combination_errors(
    real_item_id: int, effects: list[int], curses: list[int]
) -> list[str]:
    """Problems with a relic's effects taken together.

    No game-written relic repeats an effect, and a randomly rolled relic
    (ids from 1000000) never carries effects labelled for two different
    heroes. Fixed relics below that range can, so the hero rule skips them.
    """
    errors = []
    for label, ids in (("effect", effects), ("curse", curses)):
        filled = [e for e in ids if e != _EMPTY]
        if len(filled) != len(set(filled)):
            errors.append(f"The same {label} appears more than once.")
    if real_item_id >= _FIRST_RANDOM_RELIC:
        heroes = set()
        for effect in filter(None, map(get_effect, effects)):
            match = _HERO_LABEL.match(effect["name"])
            if match:
                heroes.add(match.group(1))
        if len(heroes) > 1:
            errors.append("Effects for different heroes cannot share one relic.")
    return errors


def validate_curse(effect_id: int) -> str | None:
    """Validate an effect ID for a curse slot. Returns None if valid."""
    if effect_id == 0xFFFFFFFF:
        return None
    e = get_effect(effect_id)
    if e is None:
        return f"Effect {effect_id} not found in database."
    if e["tier"] != "curse":
        return "Only curse-tier effects are valid in curse slots."
    return None


# ---------------------------------------------------------------------------
# Vessels
# ---------------------------------------------------------------------------


def get_vessel(vessel_id: int) -> dict | None:
    return _load()["vessels"].get(str(vessel_id))


def vessel_name(vessel_id: int) -> str:
    v = get_vessel(vessel_id)
    return v["name"] if v else f"Unknown ({vessel_id})"


def vessels_for_hero(hero_type: int) -> list[tuple[int, str]]:
    return sorted(
        (
            (int(vid), v["name"])
            for vid, v in _load()["vessels"].items()
            if v["hero"] == hero_type
        ),
        key=lambda x: x[0],
    )


def all_vessels() -> dict[str, dict]:
    return _load()["vessels"]


# ---------------------------------------------------------------------------
# Vessel slot rules
# ---------------------------------------------------------------------------

# Relic/vessel slot color codes; slot color 4 accepts any relic color
COLOR_NAMES = {0: "Burning", 1: "Drizzly", 2: "Luminous", 3: "Tranquil", 4: "Any"}
_COLOR_ANY = 4


def vessel_slot_color(vessel_id: int, slot_idx: int) -> int | None:
    """Color of vessel slot 0-5 (0-2 normal, 3-5 deep), or None if unknown."""
    v = get_vessel(vessel_id)
    if v is None:
        return None
    colors = v["slots"] + v["deep"]
    return colors[slot_idx] if 0 <= slot_idx < len(colors) else None


def vessel_slot_error(vessel_id: int, slot_idx: int, real_item_id: int) -> str | None:
    """Return why a relic cannot go into a vessel slot, or None if it fits."""
    relic = get_relic(real_item_id)
    if relic is None:
        return f"unknown relic {real_item_id}"
    want_deep = slot_idx >= 3
    if relic["deep"] != want_deep:
        return (
            "slots 1-3 take normal relics"
            if not want_deep
            else "slots 4-6 take deep relics"
        )
    color = vessel_slot_color(vessel_id, slot_idx)
    if color is None or color == _COLOR_ANY:
        return None
    if relic["color"] != color:
        return (
            f"slot is {COLOR_NAMES.get(color, color)}, relic is "
            f"{COLOR_NAMES.get(relic['color'], relic['color'])}"
        )
    return None
