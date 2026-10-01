"""
Icon lookup for the DS3 item views.

data/icons.db holds the vanilla game's 128px WebP item icons keyed by the
params' icon id (iconId for weapons, rings and goods, iconIdM for armor),
which the item lists carry as IconId, plus the 32px infusion icons keyed by
infusion index. icons_<mod>.db holds only the icons a mod redraws, and the
mod's own infusion icons; anything missing there falls back to vanilla.
Several items share one icon, hence the icon id key. Images are decoded on
demand and cached.
"""

from __future__ import annotations

import sqlite3
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage

_DATA_DIR = Path(__file__).parent / "data"
_dbs: dict[str, sqlite3.Connection | None] = {}
_cache: dict[tuple[str, str, int], PILImage.Image | None] = {}


def _db(source: str) -> sqlite3.Connection | None:
    if source not in _dbs:
        name = "icons.db" if source == "vanilla" else f"icons_{source}.db"
        path = _DATA_DIR / name
        _dbs[source] = (
            sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
            if path.exists()
            else None
        )
    return _dbs[source]


def _lookup(source: str, table: str, key: int) -> PILImage.Image | None:
    cache_key = (source, table, key)
    if cache_key in _cache:
        return _cache[cache_key]
    img = None
    db = _db(source)
    if db is not None:
        column = "icon_id" if table == "icons" else "infusion"
        row = db.execute(
            f"SELECT data FROM {table} WHERE {column} = ?", (key,)
        ).fetchone()
        if row is not None:
            from PIL import Image

            img = Image.open(BytesIO(row[0])).convert("RGBA")
    _cache[cache_key] = img
    return img


def get_icon(icon_id: int | None, source: str = "vanilla") -> PILImage.Image | None:
    """RGBA item icon for a params icon id, or None when there is none."""
    if icon_id is None:
        return None
    img = _lookup(source, "icons", icon_id) if source != "vanilla" else None
    return img or _lookup("vanilla", "icons", icon_id)


def get_infusion_icon(index: int, source: str = "vanilla") -> PILImage.Image | None:
    """RGBA infusion icon for an infusion index (0 is the plain weapon)."""
    return _lookup(source, "infusion_icons", index)


# Share of the weapon icon the infusion badge covers.
_BADGE_FRACTION = 0.38


def item_icon(item: dict | None, source: str = "vanilla") -> PILImage.Image | None:
    """Item icon; infused weapons get their infusion icon in the top-right
    corner, where DS3's diagonal weapon art leaves the icon empty."""
    if item is None:
        return None
    icon = get_icon(item.get("IconId"), source)
    if icon is None or "Infusion" not in item:
        return icon
    index = int(item["Id"], 16) % 10000 // 100
    badge = get_infusion_icon(index, source) if index else None
    if badge is None:
        return icon
    key = (source, "badged", int(item["Id"], 16))
    if key not in _cache:
        from PIL import Image

        canvas = icon.copy()
        size = max(1, round(canvas.width * _BADGE_FRACTION))
        canvas.alpha_composite(
            badge.resize((size, size), Image.LANCZOS), (canvas.width - size, 0)
        )
        _cache[key] = canvas
    return _cache[key]
