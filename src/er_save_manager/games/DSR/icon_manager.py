"""
Icon lookup for the DSR item views.

data/icons.db holds the game's item icons (96px WebP, padded to square)
keyed by the params' icon id, cut from the menu Icon<thousands><page>
atlases. Several items share one icon, hence the icon id key. Images are
decoded on demand and cached.
"""

from __future__ import annotations

import sqlite3
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage

_DB_PATH = Path(__file__).parent / "data" / "icons.db"
_db: sqlite3.Connection | None = None
_cache: dict[int, PILImage.Image | None] = {}


def get_icon(icon_id: int | None) -> PILImage.Image | None:
    """RGBA item icon for a params icon id, or None when there is none."""
    global _db
    if icon_id is None:
        return None
    if icon_id in _cache:
        return _cache[icon_id]
    img = None
    if _db is None and _DB_PATH.exists():
        _db = sqlite3.connect(
            f"file:{_DB_PATH}?mode=ro", uri=True, check_same_thread=False
        )
    if _db is not None:
        row = _db.execute(
            "SELECT data FROM icons WHERE icon_id = ?", (icon_id,)
        ).fetchone()
        if row is not None:
            from PIL import Image

            img = Image.open(BytesIO(row[0])).convert("RGBA")
    _cache[icon_id] = img
    return img
