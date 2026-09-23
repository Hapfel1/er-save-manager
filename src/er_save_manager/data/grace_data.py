"""
Site of Grace records derived from the event flag database.

Each grace is unlocked by a single event flag. The names, regions and the
Convergence marker come from event_flags_db, so this module only adds the
region grouping (base game or Shadow of the Erdtree) used by the grace dialog.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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
