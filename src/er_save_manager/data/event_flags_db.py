"""
Merged Event Flags Database for Elden Ring
Combined from Cheat Engine script (Dasaav/Umgak) and community documentation

Data lives in event_flags.json:
    flags: rows of [id, name, category, subcategory] plus an optional dict of
        the NotRequired EventFlagInfo keys
    categories: [category, [[subcategory, [flag ids]], ...]] in display order.
        Kept separately because it is curated, not derived from flags.
"""

import json
from pathlib import Path
from typing import NotRequired, TypedDict


class EventFlagInfo(TypedDict):
    name: str
    category: str
    subcategory: str | None
    related_flags: NotRequired[list[int]]
    requires_convergence: NotRequired[bool]


_DATA = json.loads(
    (Path(__file__).parent / "event_flags.json").read_text(encoding="utf-8")
)

EVENT_FLAGS: dict[int, EventFlagInfo] = {
    row[0]: {"name": row[1], "category": row[2], "subcategory": row[3], **extra}
    for row in _DATA["flags"]
    for extra in [row[4] if len(row) > 4 else {}]
}

FLAGS_BY_CATEGORY: dict[str, dict[str | None, list[int]]] = {
    category: dict(subcategories) for category, subcategories in _DATA["categories"]
}

del _DATA

CATEGORIES = list(FLAGS_BY_CATEGORY.keys())


def get_flag_info(flag_id: int) -> EventFlagInfo | None:
    """Get information about a flag"""
    return EVENT_FLAGS.get(flag_id)


def is_convergence(flag_id: int) -> bool:
    """Return True if the flag only exists in Convergence mod saves"""
    flag_info = EVENT_FLAGS.get(flag_id)
    return flag_info.get("requires_convergence", False) if flag_info else False


def get_flag_name(flag_id: int) -> str:
    """Get flag name or return ID as string"""
    info = EVENT_FLAGS.get(flag_id)
    return info["name"] if info else f"Flag {flag_id}"


def get_category_flags(category: str, subcategory: str = None) -> list[int]:
    """Get all flags in a category/subcategory"""
    if category not in FLAGS_BY_CATEGORY:
        return []
    if subcategory is not None:
        return FLAGS_BY_CATEGORY[category].get(subcategory, [])
    all_flags = []
    for subcat_flags in FLAGS_BY_CATEGORY[category].values():
        all_flags.extend(subcat_flags)
    return sorted(all_flags)


def get_subcategories(category: str, include_convergence: bool = True) -> list[str]:
    """Get all subcategories for a category.

    With include_convergence=False, subcategories whose flags all require
    the Convergence mod are omitted.
    """
    if category not in FLAGS_BY_CATEGORY:
        return []
    return sorted(
        sub
        for sub, flags in FLAGS_BY_CATEGORY[category].items()
        if sub is not None
        and (include_convergence or not all(is_convergence(f) for f in flags))
    )
