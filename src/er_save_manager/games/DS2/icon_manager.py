"""
Icon manager for the DS2 item browser.

Icons are stored in icons.db (SQLite) alongside this file, keyed by item id.
Images are loaded on demand and cached in memory.
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
# icon in-game, checked for each one:
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


# ------------------------------------------------------------------
# Infusion icons
# ------------------------------------------------------------------


# Infusion icons live in the named_icons table as "<infusion name>.webp",
# with names from regulation.INFUSION_NAMES. The plain weapon has none.
_named_cache: dict[str, PILImage.Image | None] = {}

# Share of the square weapon icon the infusion badge covers.
_INFUSION_BADGE_FRACTION = 0.42


def _named_lookup(name: str) -> PILImage.Image | None:
    if name in _named_cache:
        return _named_cache[name]
    img = None
    if _ensure_loaded() and _db is not None:
        try:
            from PIL import Image

            row = _db.execute(
                "SELECT data FROM named_icons WHERE name = ?", (name,)
            ).fetchone()
            if row is not None:
                img = Image.open(BytesIO(row[0])).convert("RGBA")
        except Exception:
            img = None
    _named_cache[name] = img
    return img


def get_infusion_icon(infusion_index: int) -> PILImage.Image | None:
    """Icon of an infusion index, or None for the plain weapon or a missing
    icon."""
    from er_save_manager.games.DS2.regulation import INFUSION_NAMES

    if not 0 < infusion_index < len(INFUSION_NAMES):
        return None
    return _named_lookup(f"{INFUSION_NAMES[infusion_index]}.webp")


def get_infusion_icon_by_name(name: str) -> PILImage.Image | None:
    """Icon of an infusion by its display name, or None for "Normal"."""
    from er_save_manager.games.DS2.regulation import INFUSION_NAMES

    if name not in INFUSION_NAMES:
        return None
    return get_infusion_icon(INFUSION_NAMES.index(name))


def with_infusion_badge(weapon: PILImage.Image, infusion_index: int) -> PILImage.Image:
    """The weapon icon centered on a square canvas with the infusion icon in
    the top-right corner. Weapon icons are tall and narrow, so the badge sits
    in the empty space beside the blade instead of covering it. Returns the
    weapon unchanged when the infusion has no icon."""
    badge = get_infusion_icon(infusion_index)
    if badge is None:
        return weapon
    try:
        from PIL import Image

        side = max(weapon.size)
        canvas = Image.new("RGBA", (side, side))
        canvas.alpha_composite(
            weapon.convert("RGBA"),
            ((side - weapon.width) // 2, (side - weapon.height) // 2),
        )
        size = max(1, round(side * _INFUSION_BADGE_FRACTION))
        canvas.alpha_composite(
            badge.resize((size, size), Image.LANCZOS), (side - size, 0)
        )
        return canvas
    except Exception:
        return weapon


def bind_infusion_icon(label, variable, size: int = 22) -> None:
    """Show the icon of the infusion named by variable on a CTkLabel, kept
    current through a trace so values set by code update it too."""
    import customtkinter as ctk

    def update(*_args) -> None:
        if not label.winfo_exists():
            return
        img = get_infusion_icon_by_name(variable.get())
        if img is None:
            label.configure(image=None)
            label._infusion_image = None
            return
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        label.configure(image=ctk_img)
        label._infusion_image = ctk_img

    variable.trace_add("write", update)
    update()


def add_infusion_menu_icons(combo, size: int = 20) -> None:
    """Show each infusion's icon beside its entry in a CTkComboBox's dropdown
    list. CTk rebuilds the entries whenever the values change, so the icons
    are applied again after every rebuild. Normal gets a blank image of the
    same size so all names stay aligned."""
    from PIL import Image, ImageTk

    menu = combo._dropdown_menu
    px = max(1, round(menu._apply_widget_scaling(size)))
    blank = ImageTk.PhotoImage(Image.new("RGBA", (px, px)), master=menu)
    photos: dict[str, ImageTk.PhotoImage] = {}
    rebuild = menu._add_menu_commands

    def rebuild_with_icons() -> None:
        rebuild()
        for index, value in enumerate(menu._values):
            if value not in photos:
                img = get_infusion_icon_by_name(value)
                photos[value] = (
                    ImageTk.PhotoImage(img.resize((px, px), Image.LANCZOS), master=menu)
                    if img is not None
                    else blank
                )
            menu.entryconfigure(index, image=photos[value])

    menu._add_menu_commands = rebuild_with_icons
    # Tk drops images that Python no longer references.
    menu._infusion_photos = (blank, photos)
    rebuild_with_icons()
