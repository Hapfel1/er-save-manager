"""
Relic and relic effect icons for Nightreign.

Icons are stored in data/nr_icons.db (SQLite): relic icons
from EquipParamAntique iconId, effect icons from AttachEffectParam
statusIconId (the game's buff category icons), chalice icons from
AntiqueStandParam iconId. Images are loaded on demand
and cached in memory. Returns PIL Images; callers size them.
"""

from __future__ import annotations

import sqlite3
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage

_db: sqlite3.Connection | None = None
_loaded = False
_relic_keys: dict[int, int] = {}
_effect_keys: dict[int, int] = {}
_vessel_keys: dict[int, int] = {}
_cache: dict[int, PILImage.Image | None] = {}


def _ensure_loaded() -> bool:
    global _db, _loaded
    if _loaded:
        return _db is not None
    _loaded = True
    p = Path(__file__).parent / "data" / "nr_icons.db"
    if not p.exists():
        return False
    _db = sqlite3.connect(f"file:{p}?mode=ro", uri=True, check_same_thread=False)
    _relic_keys.update(_db.execute("SELECT relic_id, blob_id FROM relic_icons"))
    _effect_keys.update(_db.execute("SELECT effect_id, blob_id FROM effect_icons"))
    _vessel_keys.update(_db.execute("SELECT vessel_id, blob_id FROM vessel_icons"))
    return True


def _blob(blob_id: int | None) -> PILImage.Image | None:
    if blob_id is None or _db is None:
        return None
    if blob_id not in _cache:
        img = None
        try:
            from PIL import Image

            row = _db.execute(
                "SELECT data FROM blobs WHERE id = ?", (blob_id,)
            ).fetchone()
            if row is not None:
                img = Image.open(BytesIO(row[0])).convert("RGBA")
        except Exception:
            img = None
        _cache[blob_id] = img
    return _cache[blob_id]


def relic_icon(real_item_id: int) -> PILImage.Image | None:
    """Icon of a relic type, or None when the game has none for it."""
    if not _ensure_loaded():
        return None
    return _blob(_relic_keys.get(real_item_id))


def effect_icon(effect_id: int) -> PILImage.Image | None:
    """Buff category icon of a relic effect or curse, or None."""
    if not _ensure_loaded():
        return None
    return _blob(_effect_keys.get(effect_id))


def vessel_icon(vessel_id: int) -> PILImage.Image | None:
    """Icon of a chalice, or None when the game has none for it."""
    if not _ensure_loaded():
        return None
    return _blob(_vessel_keys.get(vessel_id))
