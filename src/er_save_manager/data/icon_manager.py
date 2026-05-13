"""
Icon manager for the item browser.

Icons are stored in icons.zip alongside this file.
Images are loaded on demand and cached in memory.
Returns PIL Images; callers create CTkImage at the desired display size.
"""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage

_zip: zipfile.ZipFile | None = None
_available: dict[str, str] | None = None
_cache: dict[str, PILImage.Image] = {}

_SUFFIX_RE = re.compile(r"\s*-\s*MENU_Knowledge_\d+.*$", re.IGNORECASE)
_CAT_PRE_RE = re.compile(r"^\[.*?\]\s*")
_UPG_RE = re.compile(r"\s*\+\d+$")


def _zip_path() -> Path:
    return Path(__file__).parent / "icons.zip"


def _ensure_loaded() -> bool:
    global _zip, _available
    if _available is not None:
        return _zip is not None
    _available = {}
    p = _zip_path()
    if not p.exists():
        return False
    _zip = zipfile.ZipFile(p, "r")
    for entry in _zip.namelist():
        if not entry.endswith(".webp"):
            continue
        key = _norm_icon(entry[:-5])
        if key not in _available:
            _available[key] = entry
    return True


def _norm_icon(s: str) -> str:
    s = _SUFFIX_RE.sub("", s).strip()
    s = re.sub(r"_s\b", "'s", s)
    s = re.sub(r"_\s", ": ", s)
    # Strip [Sorcery]/[Incantation] prefix - spells keyed without it
    # so lookups work whether the DB entry has the prefix or not
    s = _CAT_PRE_RE.sub("", s)
    # Strip Convergence weapon prefix and numeric ID suffix
    s = re.sub(r"^wep-", "", s, flags=re.I)
    s = re.sub(r"-\d+$", "", s)
    return s.lower()


def _norm_db(name: str) -> str:
    return name.lower().replace("\u2019", "'").replace("\u2018", "'")


def _ammo_lookup(key: str) -> str | None:
    """DB stores ammo as '{Type} - {Name}', icons as '{Name} {Type}'."""
    if _available is None:
        return None
    m = re.match(
        r"^(great arrow|greatbolt|arrow|bolt|ballista bolt)\s*-\s*(.+?)(\s*\(fletched\))?$",
        key,
        re.I,
    )
    if not m:
        return None
    type_, name = m.group(1).lower(), m.group(2).strip().lower()
    fletched = " (fletched)" if m.group(3) else ""
    for candidate in (
        f"{name} {type_}{fletched}",  # normal: "fire arrow"
        f"{name}{fletched}",  # standalone: "bone ballista bolt"
    ):
        if candidate in _available:
            return _available[candidate]
    return None


def _lookup(name: str) -> str | None:
    if not _ensure_loaded() or _available is None:
        return None
    key = _norm_db(name)

    if key in _available:
        return _available[key]

    # Strip [Sorcery]/[Incantation] from DB key (icon already stripped by norm_icon)
    stripped_cat = _CAT_PRE_RE.sub("", key).strip()
    if stripped_cat != key and stripped_cat in _available:
        return _available[stripped_cat]

    # Strip upgrade suffix (+1, +2, ...)
    base_upg = _UPG_RE.sub("", key).rstrip()
    if base_upg != key and base_upg in _available:
        return _available[base_upg]

    # Empty flask: "Flask of X +N (Empty)" -> "Flask of X"
    if "(empty)" in key:
        no_empty = re.sub(r"\s*\(empty\)$", "", key, flags=re.I).rstrip()
        no_empty = _UPG_RE.sub("", no_empty).rstrip()
        if no_empty in _available:
            return _available[no_empty]

    # Unpowered great rune: strip "(Unpowered)"
    no_unpow = re.sub(r"\s*\(unpowered\)$", "", key, flags=re.I).rstrip()
    if no_unpow != key and no_unpow in _available:
        return _available[no_unpow]

    # Prattling Pate: `"Hello"` in DB -> `_Hello_` in icon filename
    pp = re.sub(r'"([^"]+)"', lambda m: f"_{m.group(1).lower()}_", key)
    if pp != key and pp in _available:
        return _available[pp]

    # Ammo: "Arrow - Fire" -> "Fire Arrow"
    ammo = _ammo_lookup(key)
    if ammo:
        return ammo

    # Talisman/item name: "Branchsword" -> "Branch Sword"
    alt = key.replace("branchsword", "branch sword")
    if alt != key and alt in _available:
        return _available[alt]

    # Numbered items: strip "[N]" suffix for cookbook base lookup
    no_num = re.sub(r"\s*\[\d+\]$", "", key).rstrip()
    if no_num != key and no_num in _available:
        return _available[no_num]

    # "Axe Of Epiphany" -> try "Epiphany Axe" inversion (Convergence weapon naming)
    m = re.match(r"^(.+?)\s+of\s+(?:the\s+)?(.+)$", key)
    if m:
        inv = f"{m.group(2)} {m.group(1)}"
        if inv in _available:
            return _available[inv]

    # Convergence icon filenames after merge use camelCase-split names.
    # This catches any remaining mismatches from the merge normalization.
    # e.g. "bestial cruciblehorn" (if merge missed camelCase) -> "bestial crucible horn"
    cnv = re.sub(r"([a-z])([A-Z])", r"\1 \2", key).lower()
    cnv = re.sub(r"_s\b", "'s", cnv).replace("_", " ").strip()
    if cnv != key and cnv in _available:
        return _available[cnv]

    return None


def icons_available() -> bool:
    return _ensure_loaded()


def has_icon(name: str) -> bool:
    return _lookup(name) is not None


def get_icon(name: str) -> PILImage.Image | None:
    """Return a PIL RGBA image for the item name, or None if not found."""
    entry = _lookup(name)
    if entry is None:
        return None
    if entry in _cache:
        return _cache[entry]
    if _zip is None:
        return None
    try:
        from PIL import Image

        data = _zip.read(entry)
        img = Image.open(BytesIO(data)).convert("RGBA")
        _cache[entry] = img
        return img
    except Exception:
        return None


def coverage_stats() -> dict[str, int]:
    _ensure_loaded()
    return {"total_icons": len(_available) if _available else 0, "cached": len(_cache)}
