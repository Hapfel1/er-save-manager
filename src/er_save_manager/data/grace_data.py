"""
Site of Grace records derived from the event flag database.

Each grace is unlocked by a single event flag. The names, regions and the
Convergence marker come from event_flags_db, so this module only adds the
region grouping (base game or Shadow of the Erdtree) used by the grace dialog.

grace_entities.json maps each grace flag to its BonfireWarpParam
bonfireEntityId, one table per regulation (Convergence moves and removes some
vanilla graces).

grace_regions.json maps each grace flag to the PlayRegionParam rows whose
mapMenuUnlockEventId is that flag, per regulation (ids as stored in the
slot's Regions list).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from er_save_manager.data.event_flags_db import (
    get_category_flags,
    get_flag_info,
    is_convergence,
)

GRACE_CATEGORY = "Grace"

NO_REGION_NAME = "Roundtable Hold"

# Regions whose graces all sit in Shadow of the Erdtree areas.
DLC_REGIONS = frozenset(
    {
        "Abyssal Woods",
        "Ancient Ruins of Rauh",
        "Belurat, Tower Settlement",
        "Castle Ensis",
        "Cerulean Coast",
        "Charo's Hidden Grave",
        "Enir-Ilim",
        "Foot of the Jagged Peak",
        "Gravesite Plain",
        "Jagged Peak",
        "Midra's Manse",
        "Rauh Base",
        "Scadu Altus",
        "Scaduview",
        "Shadow Keep",
        "Shadow Keep, Church District",
        "Specimen Storehouse",
        "Stone Coffin Fissure",
    }
)

# GameMan last_rested_grace holds the grace's bonfireEntityId + 1000.
LAST_RESTED_GRACE_OFFSET = 1000

_REGION_PREFIX = re.compile(r"^\[[^\]]+\]\s*")
_UNLOCKED_SUFFIX = re.compile(r"\s*\|\s*Unlocked\s*$")


@dataclass(frozen=True)
class Grace:
    flag_id: int
    name: str
    region: str
    is_dlc: bool
    requires_convergence: bool


def get_graces(include_convergence: bool = False) -> list[Grace]:
    """Return all graces sorted by base/DLC, region and name.

    Graces that only exist in Convergence saves are omitted unless
    include_convergence is True.
    """
    graces = []
    for flag_id in get_category_flags(GRACE_CATEGORY):
        info = get_flag_info(flag_id)
        if info is None:
            continue
        requires_convergence = is_convergence(flag_id)
        if requires_convergence and not include_convergence:
            continue
        name = _REGION_PREFIX.sub("", info["name"])
        name = _UNLOCKED_SUFFIX.sub("", name)
        region = info.get("subcategory") or NO_REGION_NAME
        graces.append(
            Grace(
                flag_id=flag_id,
                name=name,
                region=region,
                is_dlc=region in DLC_REGIONS,
                requires_convergence=requires_convergence,
            )
        )
    graces.sort(key=lambda g: (g.is_dlc, g.region, g.name.lower()))
    return graces


@cache
def _entity_tables() -> dict[str, dict[int, int]]:
    raw = json.loads(
        (Path(__file__).parent / "grace_entities.json").read_text(encoding="utf-8")
    )
    return {
        flavor: {int(flag): entity for flag, entity in table.items()}
        for flavor, table in raw.items()
    }


def last_rested_grace_value(grace: Grace, convergence: bool) -> int | None:
    """Return the last_rested_grace value for a grace, or None if unmapped."""
    tables = _entity_tables()
    entity = tables["convergence" if convergence else "vanilla"].get(grace.flag_id)
    return None if entity is None else entity + LAST_RESTED_GRACE_OFFSET


def grace_from_last_rested(value: int, convergence: bool) -> Grace | None:
    """Resolve a last_rested_grace value to a grace.

    The other regulation's table is the fallback: Convergence saves are not
    always detected as such.
    """
    entity = value - LAST_RESTED_GRACE_OFFSET
    tables = _entity_tables()
    order = ("convergence", "vanilla") if convergence else ("vanilla", "convergence")
    graces = {g.flag_id: g for g in get_graces(include_convergence=True)}
    for flavor in order:
        for flag_id, table_entity in tables[flavor].items():
            if table_entity == entity:
                return graces.get(flag_id)
    return None


@cache
def _region_tables() -> dict[str, dict[int, tuple[int, ...]]]:
    raw = json.loads(
        (Path(__file__).parent / "grace_regions.json").read_text(encoding="utf-8")
    )
    return {
        flavor: {int(flag): tuple(ids) for flag, ids in table.items()}
        for flavor, table in raw.items()
    }


def grace_region_ids(flag_id: int, convergence: bool) -> tuple[int, ...]:
    """PlayRegion ids belonging to a grace (empty when it has none)."""
    return _region_tables()["convergence" if convergence else "vanilla"].get(
        flag_id, ()
    )
