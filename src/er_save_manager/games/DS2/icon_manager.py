"""
Icon manager for the DS2 item browser.

Icons are stored in icons.db (SQLite) alongside this file, keyed by item id
(see build_icon_db.py). Images are loaded on demand and cached in memory.
Returns PIL Images; callers create CTkImage at the desired display size.
"""

from __future__ import annotations

import sqlite3
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage

_db: sqlite3.Connection | None = None
_available: set[int] | None = None
_cache: dict[int, PILImage.Image] = {}


def _db_path() -> Path:
    return Path(__file__).parent / "icons.db"


def _ensure_loaded() -> bool:
    global _db, _available
    if _available is not None:
        return _db is not None
    _available = set()
    p = _db_path()
    if not p.exists():
        return False
    _db = sqlite3.connect(f"file:{p}?mode=ro", uri=True, check_same_thread=False)
    _available.update(row[0] for row in _db.execute("SELECT item_id FROM icons"))
    return True


def icons_available() -> bool:
    return _ensure_loaded()


def has_icon(item_id: int) -> bool:
    return _ensure_loaded() and item_id in (_available or ())


# A few items have no icon of their own and share another item's exported
# icon in-game. Verified case by case, not a guess:
#   - Old Mirrah Greatsword is a unique NPC-drop variant of Mirrah Greatsword
#     with no separate icon; the base weapon's icon is the one the game uses.
_FALLBACK_ICON_ID: dict[int, int] = {
    1911000: 1910000,  # Old Mirrah Greatsword -> Mirrah Greatsword
}


def _direct_lookup(item_id: int) -> PILImage.Image | None:
    if not _ensure_loaded() or _db is None or item_id not in (_available or ()):
        return None
    if item_id in _cache:
        return _cache[item_id]
    try:
        from PIL import Image

        row = _db.execute(
            "SELECT data FROM icons WHERE item_id = ?", (item_id,)
        ).fetchone()
        if row is None:
            return None
        img = Image.open(BytesIO(row[0])).convert("RGBA")
        _cache[item_id] = img
        return img
    except Exception:
        return None


def get_icon(item_id: int, category: str | None = None) -> PILImage.Image | None:
    """Return a PIL RGBA image for the item id, or None if unavailable.

    Ring upgrades (e.g. "Bracing Knuckle Ring+1", id ...001) share their base
    ring's icon in-game rather than getting one of their own, so a ring
    lookup falls back to its base id (the id with the trailing +N zeroed)
    when the exact id has no icon. Verified against every +N ring in the
    database: the base id is always (item_id // 100) * 100.
    """
    img = _direct_lookup(item_id)
    if img is not None:
        return img
    if category == "rings":
        base_id = (item_id // 100) * 100
        if base_id != item_id:
            img = _direct_lookup(base_id)
            if img is not None:
                return img
    fallback = _FALLBACK_ICON_ID.get(item_id)
    if fallback is not None:
        return _direct_lookup(fallback)
    return None


def coverage_stats() -> dict[str, int]:
    _ensure_loaded()
    return {"total_icons": len(_available) if _available else 0, "cached": len(_cache)}


def fit_size(img: PILImage.Image, max_dim: int) -> tuple[int, int]:
    """(width, height) that fits img within a max_dim square, aspect intact.

    DS2 icons are not all square (armor/weapons are commonly 128x256), so
    callers must not pass a fixed (size, size) to CTkImage - that stretches
    a 1:2 icon into a square and squashes it.
    """
    w, h = img.size
    if w <= 0 or h <= 0:
        return (max_dim, max_dim)
    scale = max_dim / max(w, h)
    return (max(1, round(w * scale)), max(1, round(h * scale)))


# ---- infusion icons ---------------------------------------------------------


def get_infusion_icon(_infusion_index: int) -> PILImage.Image | None:
    return None
