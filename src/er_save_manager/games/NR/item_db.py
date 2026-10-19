"""
Nightreign item database.

Effect tier classification (from AttachEffectParam ID ranges):
  "deep"    6000000-6799999  - effects on deep relics
  "normal"  7000000-7999999  - effects on normal relics
  "special" <100000          - fixed hero/ability effects (any relic type)
  "curse"   6800000-6999999  - curse slot effects (separate from effect slots)

The tiers only sort effect lists for display. Which effects a relic can
roll comes from the game's roll tables, see relic_rules.py.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "nr_items.json"
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


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------


def get_effect(effect_id: int) -> dict | None:
    if effect_id == 0xFFFFFFFF or effect_id < 0:
        return None
    return _load()["effects"].get(str(effect_id))


# "[Relic] " and "[Special Relic] " name prefixes, with an optional hero
_RELIC_PREFIX = re.compile(r"^\[(?:Special )?Relic(?: - ([^\]]+))?\] ")


def _display_name(name: str) -> str:
    """Effect name without the "[Relic]" tag; hero effects keep "[Hero]"."""
    return _RELIC_PREFIX.sub(lambda m: f"[{m.group(1)}] " if m.group(1) else "", name)


def effect_name(effect_id: int) -> str:
    if effect_id == 0xFFFFFFFF or effect_id < 0:
        return "(empty)"
    e = get_effect(effect_id)
    return _display_name(e["name"]) if e else f"Unknown ({effect_id})"


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
        result.append((int(sid), _display_name(e["name"])))
    return sorted(result, key=lambda x: x[1])


def effects_for_curse_slot() -> list[tuple[int, str]]:
    """Return (effect_id, name) pairs valid for a curse slot."""
    return sorted(
        (
            (int(sid), _display_name(e["name"]))
            for sid, e in _load()["effects"].items()
            if e["tier"] == "curse"
        ),
        key=lambda x: x[1],
    )


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
