"""World map window: teleport locations and map markers on the game's map."""

from __future__ import annotations

import json
import math
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageTk

from er_save_manager.data.boss_locations import BossSpot, boss_spots
from er_save_manager.data.floor_points import FloorPoint, floors_near, pin_location
from er_save_manager.data.grace_data import arena_gate, location_gate
from er_save_manager.data.icon_manager import get_icon
from er_save_manager.data.item_pickups import (
    ITEM_TYPES,
    SOURCE_LABELS,
    Pickup,
    get_pickups,
)
from er_save_manager.data.locations import MapLocation, get_name_for_map_id
from er_save_manager.data.map_objects import (
    POOL,
    MapObject,
    Painting,
    map_objects,
    paintings,
)
from er_save_manager.data.map_pieces import (
    MAP_PIECES,
    MapPiece,
    fragment_at,
    grace_piece,
    pieces_on_map,
)
from er_save_manager.data.merchants import RUNES, Merchant, ShopItem, get_merchants
from er_save_manager.data.npc_data import NPC_FLAGS, calm_npc, revive_npc
from er_save_manager.data.npc_locations import NpcSpot, npc_spots
from er_save_manager.data.quest_locations import QuestStep, quest_steps
from er_save_manager.data.world_map import (
    MAP_LANDS_BETWEEN,
    MAP_NAMES,
    MAP_REALM_OF_SHADOW,
    MAP_UNDERGROUND,
    location_map_point,
    map_to_global,
    parse_map_id,
    tile_map_rect,
)
from er_save_manager.editors.map_markers import (
    BEACON,
    MARKER,
    MARKER_ICONS,
    MapMarker,
    MapMarkerEditor,
)
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette
from er_save_manager.ui.boss_gate import gate_status
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.quest_progress_dialog import steps_up_to
from er_save_manager.ui.tooltip import Tooltip
from er_save_manager.ui.utils import (
    bind_mousewheel,
    center_window,
    patch_combo_scroll,
    pick_file,
    style_window_frame,
)

_MAP_ORDER = (MAP_LANDS_BETWEEN, MAP_UNDERGROUND, MAP_REALM_OF_SHADOW)
# Opacity of the unrevealed-area art over a locked map fragment. The
# Underground's unrevealed art is black over an already dark map.
_PROGRESS_ALPHA = 0.65
_PROGRESS_ALPHA_BY_MAP = {MAP_UNDERGROUND: 0.4}
_ZOOM_MAX = 2.0  # screen pixels per map unit
_ZOOM_STEP = 1.2
# While the wheel turns, the view is drawn as one half resolution image; the
# sharp tiles are built once no wheel step came for this long.
_ZOOM_SETTLE_MS = 120
_DRAG_THRESHOLD = 4
# The map is drawn as cached square tiles of this many screen pixels at the
# current zoom; a pan moves them and only creates tiles that come into view.
_TILE_PX = 256
# Icons and outlines are drawn this far outside the view, and drawn again
# once the view has stopped moving for _SETTLE_MS.
_RENDER_MARGIN = 300
_SETTLE_MS = 90
_BACKGROUND = (20, 20, 22)
_BACKGROUND_HEX = "#141416"

_HOVER_COLOR = "#ffffff"
_GRID_COLOR = "#d8d8c8"
# Tile selection outline, in the hue of the select_ring sprite.
_SELECT_COLOR = "#f0d890"
# A click snaps to walkable floor within this many screen pixels, kept
# between these map unit distances.
_PIN_PICK_PX = 18
_PIN_RADIUS_MIN = 4.0
_PIN_RADIUS_MAX = 60.0
# What a click on empty map selects: a pin on the nearest floor (the tile
# when there is none), or the small overworld tile.
_TARGET_PINS = "Pins"
_TARGET_TILES = "Tiles"
_MODE_SELECT = "Select"
_MODE_MARKER = "Add Marker"
_MODE_BEACON = "Add Beacon"
_MARKER_SIZE = 30
_BEACON_HEIGHT = 44
_LIST_ICON = 20
_GRACE_SIZE = 26
_DUNGEON_SIZE = 36
_FILTER_ALL = "All"
_FILTER_GRACES = "Graces"
_FILTER_DUNGEONS = "Dungeons"
_FILTER_TILES = "Tiles"
_FILTER_BOSSES = "Bosses"
_FILTER_NPCS = "NPCs"
_FILTER_ITEMS = "Items"
_FILTER_MERCHANTS = "Merchants"
_PIN_FILTERS = (_FILTER_BOSSES, _FILTER_NPCS, _FILTER_MERCHANTS, _FILTER_ITEMS)
_KIND_LABELS = {"grace": "Site of Grace", "dungeon": "Dungeon", "small": "Tile"}
_PLAYER_SIZE = 36
_NPC_SIZE = 26
_BOSS_SIZE = 40
# Bosses whose reward is a Remembrance or a Great Rune: larger, with an
# outer gold ring
_MAJOR_BOSS_SIZE = 50
_MAJOR_REWARDS = ("Remembrance", "Great Rune")
_MAJOR_GROUP = "Remembrance bosses"
_MERCHANT_SIZE = 30
_STEP_SIZE = 22
# A click that hits nothing selects the nearest marker this many screen
# pixels away before it places a floor pin
_SNAP_PX = 10
# Step pins sit this far up and left of the spot, clear of the NPC marker
_STEP_OFFSET = 14
# NPC spots closer than this many map units share one marker
_NPC_MERGE = 3.0
# Quest route line and current step text, in the inner gold of the rings
_ROUTE_COLOR = "#e2c478"
_DONE_GRAY = (120, 120, 120)
# Discs are drawn this many times larger, then scaled down smoothly
_SUPERSAMPLE = 3
# NPC name tags show from this zoom on; below it they cover the map
_NAME_TAG_ZOOM = 0.2
_TAG_FONT = ("Inter", 9)
# Pickup glow size range; it shrinks as the map zooms out
_PICKUP_MIN = 5
_PICKUP_MAX = 10
# Pickup glows are painted into the map tiles, not drawn as canvas items:
# thousands of alpha images make every pan frame slow. Hit tests use a grid
# of cells this many map units wide.
_PICKUP_CELL = 256.0
# Red tint of the NPC sprite for hostile NPCs
_HOSTILE_TINT = (255, 120, 110)
_GOLD_RING = ((120, 96, 52), (226, 196, 120))
_SILVER_RING = ((90, 92, 100), (200, 204, 214))
_POOL_SIZE = 28
# Plain dot markers (Dots layer option)
_DOT_SIZE = 14
_DOT_BOSS = (216, 80, 60)
_DOT_POOL = (226, 196, 120)
_DOT_SEAL = (200, 204, 214)
_DOT_PAINTING = (111, 180, 224)
_SEAL_SIZE = 30
_PAINTING_SIZE = 32
_SEAL_ICON = "Stonesword Key"
# Map-only pickup types carved out of Key Items, matched by item name
_BELL_BEARINGS = "Bell Bearings"
_PAINTINGS = "Paintings"
_PICKUP_TYPES = (*ITEM_TYPES, _BELL_BEARINGS, _PAINTINGS)
_FILTER_DONE = "Done %"
# Completion categories, in panel and export order
_DONE_PICKUPS = "Item pickups"
_DONE_BOSSES = "Bosses"
_DONE_GRACES = "Sites of Grace"
_DONE_POOLS = "Summoning pools"
_DONE_SEALS = "Imp seals"
_DONE_PAINTINGS = "Paintings solved"
_DONE_CATEGORIES = (
    _DONE_PICKUPS,
    _DONE_BOSSES,
    _DONE_GRACES,
    _DONE_POOLS,
    _DONE_SEALS,
    _DONE_PAINTINGS,
)
# What a left entry is called in the region panel and the export
_LEFT_LABELS = {
    _DONE_PICKUPS: "Item",
    _DONE_BOSSES: "Boss",
    _DONE_GRACES: "Grace",
    _DONE_POOLS: "Pool",
    _DONE_SEALS: "Imp seal",
    _DONE_PAINTINGS: "Painting",
}
_REGION_LEFT_ROWS = 8
_BAR_SIZE = (56, 8)
_BAR_COLOR = (31, 106, 165)
_BAR_FULL_COLOR = (201, 168, 76)
_PANEL_ICON = 64
_PANEL_ICON_SMALL = 40
_HOVER_ICON = 28
_HOVER_ICONS = 10


@dataclass
class _Placed:
    loc: MapLocation
    map_no: int
    rect: tuple[float, float, float, float] | None = None
    point: tuple[float, float] | None = None
    icon: int | None = None  # dungeon map icon id


@dataclass
class _Pin:
    """Item pickup, boss, NPC, merchant, summoning pool, imp seal or
    painting vista on the map. NPC spots at one map point are merged into
    one pin."""

    map_no: int
    point: tuple[float, float]
    pickup: Pickup | None = None
    npcs: list[NpcSpot] | None = None
    boss: BossSpot | None = None
    merchant: Merchant | None = None
    obj: MapObject | None = None
    painting: Painting | None = None


class _QuestList:
    """Quest steps as wrapped rows in a text widget, so long steps show in
    full: the step pin, "N. description", and Done for reached steps. Has
    the selection(), selection_set() and see() calls of a Treeview."""

    def __init__(self, parent, on_select: Callable[[], None], height: int = 9):
        self.box = ctk.CTkFrame(parent, corner_radius=8)
        bg = self.box._apply_appearance_mode(ds.LIST_BG)
        fg = self.box._apply_appearance_mode(
            ctk.ThemeManager.theme["CTkLabel"]["text_color"]
        )
        self.box.configure(fg_color=bg)
        sb = ctk.CTkScrollbar(self.box, height=40)
        sb.pack(side="right", fill="y", padx=(0, 3), pady=6)
        font = (ds.SMALL[0], -round(self.box._apply_widget_scaling(13)))
        self.text = tk.Text(
            self.box,
            height=height,
            wrap="word",
            bg=bg,
            fg=fg,
            font=font,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            cursor="arrow",
            yscrollcommand=sb.set,
            padx=4,
            pady=2,
            spacing1=3,
            spacing3=3,
        )
        sb.configure(command=self.text.yview)
        self.text.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=6)
        self.text.tag_configure("current", foreground=_ROUTE_COLOR)
        self.text.tag_configure(
            "done_mark", foreground=self.box._apply_appearance_mode(ds.MUTED)
        )
        self.text.tag_configure(
            "picked", background=palette.pick(palette.PURPLE_SELECT)
        )
        self._on_select = on_select
        self._rows = 0
        self._picked: str | None = None

    def add(self, image, label: str, done: bool, current: bool):
        n = self._rows
        tag = f"r{n}"
        t = self.text
        start = t.index("end-1c")
        t.image_create("end", image=image, padx=2)
        t.insert("end", f" {label}", (tag, "current") if current else (tag,))
        if done:
            t.insert("end", "  Done", (tag, "done_mark"))
        t.insert("end", "\n", (tag,))
        t.tag_add(tag, start, "end-1c")
        # Wrapped lines start under the text, not under the pin
        t.tag_configure(tag, lmargin2=image.width() + 10)
        t.tag_bind(tag, "<Button-1>", lambda _e, i=str(n): self._click(i))
        self._rows += 1

    def finish(self):
        self.text.configure(state="disabled")
        bind_mousewheel(self.text)

    def _click(self, iid: str):
        self.selection_set(iid)
        self._on_select()

    def selection(self) -> tuple[str, ...]:
        return (self._picked,) if self._picked is not None else ()

    def selection_set(self, iid: str):
        t = self.text
        t.tag_remove("picked", "1.0", "end")
        ranges = t.tag_ranges(f"r{iid}")
        if ranges:
            t.tag_add("picked", ranges[0], ranges[1])
        self._picked = iid

    def see(self, iid: str):
        ranges = self.text.tag_ranges(f"r{iid}")
        if ranges:
            self.text.see(ranges[0])


class _FlagChanges:
    """Event flag accessor for npc_data's calm / revive helpers: reads the
    character's flags and records the writes instead of making them."""

    def __init__(self, read: Callable[[int], bool | None]):
        self._read = read
        self.changes: dict[int, bool] = {}

    def get_flag(self, flag_id: int) -> bool:
        return self.changes.get(flag_id, bool(self._read(flag_id)))

    def set_flag(self, flag_id: int, state: bool):
        self.changes[flag_id] = state


def _safe_reader(
    read: Callable[[int], bool | None] | None,
) -> Callable[[int], bool | None] | None:
    """Flag reader that answers None for flags the save cannot store
    (quest and placement data name flags outside the save's flag blocks)."""
    if read is None:
        return None

    def safe(flag_id: int) -> bool | None:
        try:
            return read(flag_id)
        except (ValueError, KeyError, IndexError):
            return None

    return safe


def _major_boss(boss: BossSpot) -> bool:
    return any(word in boss.face for word in _MAJOR_REWARDS)


def _short_name(name: str) -> str:
    """Name tag text: the part before a title ("Sir Gideon Ofnir, the
    All-Knowing" -> "Sir Gideon Ofnir")."""
    return name.split(", ")[0]


def _place_merchants(convergence: bool) -> list[_Pin]:
    pins = []
    for m in get_merchants(convergence):
        point = location_map_point(m.map_id, m.position[0], m.position[2], convergence)
        if point is not None:
            pins.append(_Pin(point[0], (point[1], point[2]), merchant=m))
    return pins


def _place_objects(convergence: bool) -> list[_Pin]:
    """Summoning pools and imp seals."""
    pins = []
    for o in map_objects(convergence):
        point = location_map_point(o.map_id, o.position[0], o.position[2], convergence)
        if point is not None:
            pins.append(_Pin(point[0], (point[1], point[2]), obj=o))
    return pins


def _place_paintings(convergence: bool) -> list[_Pin]:
    """Painting vistas, at the reward the vista places."""
    pins = []
    for p in paintings(convergence):
        r = p.reward
        if r.position is None:
            continue
        point = location_map_point(r.map_id, r.position[0], r.position[2], convergence)
        if point is not None:
            pins.append(_Pin(point[0], (point[1], point[2]), painting=p))
    return pins


def _pickup_kind(pickup: Pickup) -> str:
    """Type for the map's pickup filter: the checklist type, with bell
    bearings and paintings split out of Key Items."""
    names = [name for _, _, name in pickup.items]
    if any("Bell Bearing" in n for n in names):
        return _BELL_BEARINGS
    if any(n.endswith("Painting") for n in names):
        return _PAINTINGS
    return pickup.item_type


def _bar_image(pct: int) -> Image.Image:
    """Progress bar for the completion list."""
    w, h = _BAR_SIZE
    img = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=(70, 70, 70))
    if pct:
        fill = _BAR_FULL_COLOR if pct >= 100 else _BAR_COLOR
        draw.rounded_rectangle(
            (0, 0, max(h, (w - 1) * pct // 100), h - 1), h // 2, fill=fill
        )
    return img


def _place_bosses(convergence: bool) -> list[_Pin]:
    pins = []
    for b in boss_spots(convergence):
        point = location_map_point(b.map_id, b.position[0], b.position[2], convergence)
        if point is not None:
            pins.append(_Pin(point[0], (point[1], point[2]), boss=b))
    return pins


def _place_pickups(convergence: bool) -> list[_Pin]:
    pins = []
    for p in get_pickups(convergence):
        if p.position is None:
            continue
        point = location_map_point(p.map_id, p.position[0], p.position[2], convergence)
        if point is not None:
            pins.append(_Pin(point[0], (point[1], point[2]), pickup=p))
    return pins


@cache
def _pickups_by_place(
    convergence: bool,
) -> tuple[dict[int, list[Pickup]], dict[str, list[Pickup]]]:
    """Pickups by nearest grace flag and by map id."""
    by_grace: dict[int, list[Pickup]] = {}
    by_map: dict[str, list[Pickup]] = {}
    for p in get_pickups(convergence):
        if p.grace_flag:
            by_grace.setdefault(p.grace_flag, []).append(p)
        if p.map_id:
            by_map.setdefault(p.map_id, []).append(p)
    return by_grace, by_map


@cache
def _spot_point(
    map_id: str, x: float, z: float, convergence: bool
) -> tuple[int, float, float] | None:
    return location_map_point(map_id, x, z, convergence)


def count_phrase(n: int, word: str) -> str:
    """Count with the word, plural unless n is 1."""
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _place(
    loc: MapLocation, dungeon_icons: dict[str, int], convergence: bool = False
) -> _Placed | None:
    """Map position of a teleport location: a tile rectangle for small
    overworld tiles, a point for graces and dungeons."""
    if loc.tile_type == "small":
        area, x, z, lod = parse_map_id(loc.map_id_str)
        if area not in (60, 61):
            return None
        map_no = MAP_LANDS_BETWEEN if area == 60 else MAP_REALM_OF_SHADOW
        return _Placed(loc, map_no, rect=tile_map_rect(x, z, lod))
    if loc.safe_coords is None:
        return None
    p = location_map_point(
        loc.map_id_str, loc.safe_coords[0], loc.safe_coords[2], convergence
    )
    if p is None:
        return None
    return _Placed(
        loc, p[0], point=(p[1], p[2]), icon=dungeon_icons.get(loc.map_id_str, 50)
    )


class _MapImages:
    """Map images from resources/maps. maps.json gives each image's top-left
    and size in map units and the image pixels per map unit. Each image keeps
    halved copies so zoomed-out views do not resample the full image.

    Convergence redraws some areas of the map: maps.json
    "convergence_patches" lists them as [map, x, y, w, h, atlas x, atlas y]
    in image pixels, cut from convergence_patches.jpg and pasted over the
    vanilla image when convergence is on.

    maps.json "progress" gives per map a bit mask of which fragment piece
    draws each pixel (bit i = flags[i] over the R, G, B bytes) and the
    game's art for unrevealed areas. Locked fragments get that art blended
    over their pixels."""

    def __init__(self, maps_dir: Path, convergence: bool = False):
        self._dir = maps_dir
        meta = json.loads((maps_dir / "maps.json").read_text(encoding="utf-8"))
        self.scale = float(meta["scale"])
        self._meta = {m["map"]: (key, m) for key, m in meta["maps"].items()}
        self._patches = meta.get("convergence_patches", [])
        self._progress = {
            meta["maps"][key]["map"]: entry
            for key, entry in meta.get("progress", {}).get("maps", {}).items()
        }
        self.convergence = convergence
        self._levels: dict[int, tuple[frozenset[int], list[Image.Image]]] = {}

    def set_convergence(self, convergence: bool):
        if convergence != self.convergence:
            self.convergence = convergence
            self._levels.clear()

    def bounds(self, map_no: int) -> tuple[float, float, float, float]:
        _, m = self._meta[map_no]
        ox, oy = m["origin"]
        w, h = m["size"]
        return ox, oy, ox + w, oy + h

    def progress_flags(self, map_no: int) -> list[int]:
        """Open flags of the fragment pieces the progress overlay covers."""
        entry = self._progress.get(map_no)
        return list(entry["flags"]) if entry else []

    def levels(
        self, map_no: int, locked: frozenset[int] = frozenset()
    ) -> list[Image.Image]:
        """The map image and its halved copies, with the fragments in locked
        shaded."""
        cached = self._levels.get(map_no)
        if cached is None or cached[0] != locked:
            key, _ = self._meta[map_no]
            img = Image.open(self._dir / f"{key}.jpg").convert("RGB")
            patches = [p for p in self._patches if p[0] == map_no]
            if self.convergence and patches:
                atlas = Image.open(self._dir / "convergence_patches.jpg").convert("RGB")
                for _, x, y, w, h, ax, ay in patches:
                    img.paste(atlas.crop((ax, ay, ax + w, ay + h)), (x, y))
            img = self._shade(img, map_no, locked)
            levels = [img]
            for _ in range(3):
                levels.append(levels[-1].reduce(2))
            self._levels[map_no] = (locked, levels)
        return self._levels[map_no][1]

    def _shade(
        self, img: Image.Image, map_no: int, locked: frozenset[int]
    ) -> Image.Image:
        entry = self._progress.get(map_no)
        if entry is None:
            return img
        bits = [i for i, flag_id in enumerate(entry["flags"]) if flag_id in locked]
        if not bits:
            return img
        planes = Image.open(self._dir / entry["mask"]).convert("RGB").split()
        alpha = Image.new("L", planes[0].size, 0)
        for byte, plane in enumerate(planes):
            sel = sum(1 << (i % 8) for i in bits if i // 8 == byte)
            if sel:
                alpha = ImageChops.lighter(
                    alpha, plane.point(lambda v, sel=sel: 255 if v & sel else 0)
                )
        level = round(255 * _PROGRESS_ALPHA_BY_MAP.get(map_no, _PROGRESS_ALPHA))
        alpha = (
            alpha.filter(ImageFilter.GaussianBlur(1))
            .point(lambda v: v * level // 255)
            .resize(img.size, Image.BILINEAR)
        )
        blank = (
            Image.open(self._dir / entry["blank"])
            .convert("RGB")
            .resize(img.size, Image.BILINEAR)
        )
        return Image.composite(blank, img, alpha)


class _MapIcons:
    """The game's map icons as PhotoImages per size, cut from the
    resources/maps/icons.png atlas (maps.json "icons" gives each one's
    x, y, w, h): marker_01..10 for the icon numbers the save stores, beacon,
    grace, dungeon_<WorldMapPointParam icon id> and select_ring."""

    def __init__(self, maps_dir: Path, rects: dict[str, list[int]]):
        atlas = Image.open(maps_dir / "icons.png").convert("RGBA")
        self._sprites = {
            name: atlas.crop((x, y, x + w, y + h))
            for name, (x, y, w, h) in rects.items()
        }
        self._markers = {i: self._sprites[f"marker_{i:02d}"] for i in MARKER_ICONS}
        self._beacon = self._sprites["beacon"]
        self._grace = self._sprites["grace"]
        self._bloodstain = self._sprites["bloodstain"]
        self._select_ring = self._sprites["select_ring"]
        self._photos: dict[tuple, ImageTk.PhotoImage] = {}
        self._images: dict[tuple, Image.Image] = {}

    @staticmethod
    def _dimmed(img: Image.Image) -> Image.Image:
        """Gray, half transparent copy for locked graces."""
        gray = img.convert("LA").convert("RGBA")
        gray.putalpha(img.getchannel("A").point(lambda a: a * 55 // 100))
        return gray

    @staticmethod
    def _fit(img: Image.Image, size: int) -> Image.Image:
        scale = size / max(img.width, img.height)
        return img.resize(
            (max(1, round(img.width * scale)), max(1, round(img.height * scale))),
            Image.LANCZOS,
        )

    def grace(self, size: int, locked: bool = False) -> ImageTk.PhotoImage:
        key = ("g", size, locked)
        if key not in self._photos:
            img = self._fit(self._grace, size)
            self._photos[key] = ImageTk.PhotoImage(self._dimmed(img) if locked else img)
        return self._photos[key]

    def dungeon(self, icon: int, size: int) -> ImageTk.PhotoImage:
        key = ("d", icon, size)
        if key not in self._photos:
            sprite = self._sprites.get(f"dungeon_{icon}", self._sprites["dungeon_50"])
            self._photos[key] = ImageTk.PhotoImage(self._fit(sprite, size))
        return self._photos[key]

    def marker(self, icon: int, size: int) -> ImageTk.PhotoImage:
        icon = icon if icon in self._markers else MARKER_ICONS[0]
        key = ("m", icon, size)
        if key not in self._photos:
            img = self._markers[icon].resize((size, size), Image.LANCZOS)
            self._photos[key] = ImageTk.PhotoImage(img)
        return self._photos[key]

    def beacon(self, height: int) -> ImageTk.PhotoImage:
        key = ("b", height)
        if key not in self._photos:
            w = max(1, round(self._beacon.width * height / self._beacon.height))
            img = self._beacon.resize((w, height), Image.LANCZOS)
            self._photos[key] = ImageTk.PhotoImage(img)
        return self._photos[key]

    def bloodstain(self, size: int, empty: bool = False) -> ImageTk.PhotoImage:
        """empty: gray, for a bloodstain that holds no runes."""
        key = ("s", size, empty)
        if key not in self._photos:
            img = self._fit(self._bloodstain, size)
            self._photos[key] = ImageTk.PhotoImage(self._dimmed(img) if empty else img)
        return self._photos[key]

    @staticmethod
    def _tinted(img: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
        """Gray levels of img scaled per channel by rgb, alpha kept."""
        gray = img.convert("L")
        channels = [gray.point(lambda v, c=c: v * c // 255) for c in rgb]
        return Image.merge("RGBA", [*channels, img.getchannel("A")])

    def player(self, size: int) -> ImageTk.PhotoImage:
        key = ("p", size)
        if key not in self._photos:
            self._photos[key] = ImageTk.PhotoImage(
                self._fit(self._sprites["player"], size)
            )
        return self._photos[key]

    def npc(
        self, size: int, hostile: bool = False, dead: bool = False
    ) -> ImageTk.PhotoImage:
        key = ("n", size, hostile, dead)
        if key not in self._photos:
            img = self._fit(self._sprites["npc"], size)
            if hostile:
                img = self._tinted(img, _HOSTILE_TINT)
            if dead:
                img = self._dimmed(img)
            self._photos[key] = ImageTk.PhotoImage(img)
        return self._photos[key]

    def merchant(self, size: int) -> ImageTk.PhotoImage:
        key = ("M", size)
        if key not in self._photos:
            self._photos[key] = ImageTk.PhotoImage(
                self._fit(self._sprites["merchant"], size)
            )
        return self._photos[key]

    @classmethod
    def disc_image(
        cls,
        icon: Image.Image,
        size: int,
        ring: tuple[tuple[int, int, int], tuple[int, int, int]] = _GOLD_RING,
    ) -> Image.Image:
        """An item icon cut to a dark disc inside a thin double ring (outer,
        inner color)."""
        img = Image.new("RGBA", (size, size))
        draw = ImageDraw.Draw(img)
        draw.ellipse((2, 2, size - 3, size - 3), fill=(22, 20, 18, 235))
        inner = cls._fit(icon, round(size * 0.8))
        mask = Image.new("L", inner.size, 0)
        ImageDraw.Draw(mask).ellipse(
            (0, 0, inner.width - 1, inner.height - 1), fill=255
        )
        inner.putalpha(ImageChops.multiply(inner.getchannel("A"), mask))
        img.alpha_composite(
            inner, ((size - inner.width) // 2, (size - inner.height) // 2)
        )
        draw = ImageDraw.Draw(img)
        draw.ellipse((2, 2, size - 3, size - 3), outline=ring[0], width=1)
        draw.ellipse((4, 4, size - 5, size - 5), outline=ring[1], width=1)
        return img

    def boss_image(
        self, face: str, size: int, defeated: bool, major: bool = False
    ) -> Image.Image:
        """The boss's reward icon in a thin double gold ring with the game's
        crossed swords badge; gray when defeated. Major bosses get a third,
        wider gold ring. Bosses without a reward icon show the swords inside
        the disc."""
        badge = self._sprites["boss_badge"]
        icon = get_icon(face) if face else None
        if icon is None:
            # No reward item with an icon: the crossed swords in the same
            # disc and ring as every other boss
            img = self.disc_image(badge, size)
            return self._dimmed(img) if defeated else img
        if major:
            pad = max(3, size // 12)
            img = Image.new("RGBA", (size, size))
            img.alpha_composite(self.disc_image(icon, size - 2 * pad), (pad, pad))
            ImageDraw.Draw(img).ellipse(
                (0, 0, size - 1, size - 1), outline=_GOLD_RING[1], width=2
            )
        else:
            img = self.disc_image(icon, size)
        small = self._fit(badge, size // 2)
        img.alpha_composite(small, (size - small.width, 0))
        return self._dimmed(img) if defeated else img

    @staticmethod
    def step_image(number: int, size: int, done: bool) -> Image.Image:
        """Quest step pin: dark disc in the boss markers' thin double gold
        ring with a gold number; gray once reached. Number 0 draws none."""
        k = _SUPERSAMPLE
        z = size * k
        img = Image.new("RGBA", (z, z))
        draw = ImageDraw.Draw(img)
        draw.ellipse(
            (k, k, z - k - 1, z - k - 1),
            fill=(22, 20, 18, 240),
            outline=_GOLD_RING[0],
            width=k,
        )
        inner = _DONE_GRAY if done else _GOLD_RING[1]
        draw.ellipse(
            (3 * k, 3 * k, z - 3 * k - 1, z - 3 * k - 1), outline=inner, width=k
        )
        if number:
            draw.text(
                (z / 2, z / 2),
                str(number),
                font=ImageFont.load_default(size=z // 2),
                fill=inner,
                anchor="mm",
            )
        return img.resize((size, size), Image.LANCZOS)

    def step(self, number: int, size: int, done: bool) -> ImageTk.PhotoImage:
        key = ("q", number, size, done)
        if key not in self._photos:
            self._photos[key] = ImageTk.PhotoImage(self.step_image(number, size, done))
        return self._photos[key]

    def dot(
        self, color: tuple[int, int, int], size: int, done: bool
    ) -> ImageTk.PhotoImage:
        """Plain marker: small dark disc with a gold rim and a colored core,
        gray when done."""
        key = ("o", color, size, done)
        if key not in self._photos:
            k = _SUPERSAMPLE
            z = size * k
            img = Image.new("RGBA", (z, z))
            draw = ImageDraw.Draw(img)
            draw.ellipse(
                (k, k, z - k - 1, z - k - 1),
                fill=(22, 20, 18, 235),
                outline=_GOLD_RING[0],
                width=k,
            )
            draw.ellipse(
                (3 * k, 3 * k, z - 3 * k - 1, z - 3 * k - 1),
                fill=_DONE_GRAY if done else color,
            )
            self._photos[key] = ImageTk.PhotoImage(
                img.resize((size, size), Image.LANCZOS)
            )
        return self._photos[key]

    def item_disc(
        self, name: str, size: int, dim: bool, badge: int = 0
    ) -> ImageTk.PhotoImage:
        """Item icon in a silver ring (imp seals, paintings); gray when dim.
        badge: a number in a gold dot at the top right (2-key imp seals)."""
        key = ("I", name, size, dim, badge)
        if key not in self._photos:
            icon = get_icon(name)
            if icon is None:
                icon = Image.new("RGBA", (size, size))
            img = self.disc_image(icon, size, _SILVER_RING)
            if badge:
                d = size * 9 // 20
                draw = ImageDraw.Draw(img)
                draw.ellipse(
                    (size - d - 1, 0, size - 1, d),
                    fill=(226, 196, 120),
                    outline=(40, 32, 18),
                )
                draw.text(
                    (size - 1 - d / 2, d / 2 + 0.5),
                    str(badge),
                    fill=(30, 24, 12),
                    anchor="mm",
                )
            self._photos[key] = ImageTk.PhotoImage(self._dimmed(img) if dim else img)
        return self._photos[key]

    def pool(self, size: int, active: bool) -> ImageTk.PhotoImage:
        """Summoning pool: the game's effigy icon on a dark disc (the bare
        sprite is too thin to see on the map); gray until activated."""
        key = ("P", size, active)
        if key not in self._photos:
            img = self.disc_image(self._sprites["pool"], size)
            self._photos[key] = ImageTk.PhotoImage(img if active else self._dimmed(img))
        return self._photos[key]

    def boss(
        self, face: str, size: int, defeated: bool, major: bool = False
    ) -> ImageTk.PhotoImage:
        key = ("B", face, size, defeated, major)
        if key not in self._photos:
            self._photos[key] = ImageTk.PhotoImage(
                self.boss_image(face, size, defeated, major)
            )
        return self._photos[key]

    @staticmethod
    def glow_image(size: int, dim: bool = False) -> Image.Image:
        """Golden glow like an item on the ground in game: a soft halo
        around a bright core, gray when dim."""
        n = round(size * 2.4)
        img = Image.new("RGBA", (n, n))
        c = n / 2
        halo = size * 0.85
        ImageDraw.Draw(img).ellipse(
            (c - halo, c - halo, c + halo, c + halo), fill=(255, 200, 90, 170)
        )
        img = img.filter(ImageFilter.GaussianBlur(size * 0.4))
        core = size * 0.32
        ImageDraw.Draw(img).ellipse(
            (c - core, c - core, c + core, c + core), fill=(255, 236, 170, 255)
        )
        return _MapIcons._dimmed(img) if dim else img

    def glow_cached(self, size: int, dim: bool = False) -> Image.Image:
        key = ("L", size, dim)
        if key not in self._images:
            self._images[key] = self.glow_image(size, dim)
        return self._images[key]

    def glow(self, size: int, dim: bool = False) -> ImageTk.PhotoImage:
        key = ("l", size, dim)
        if key not in self._photos:
            self._photos[key] = ImageTk.PhotoImage(self.glow_image(size, dim))
        return self._photos[key]

    def select_ring(self, icon_size: int) -> ImageTk.PhotoImage:
        """The game's map selection ring, sized so its rim (at 0.49 of the
        sprite's half width) clears an icon of icon_size by 3 px."""
        size = round((icon_size / 2 + 3) / 0.49 * 2)
        key = ("r", size)
        if key not in self._photos:
            img = self._select_ring.resize((size, size), Image.LANCZOS)
            self._photos[key] = ImageTk.PhotoImage(img)
        return self._photos[key]

    def ctk_sprite(
        self,
        name: str,
        size: int,
        dimmed: bool = False,
        tint: tuple[int, int, int] | None = None,
    ) -> ctk.CTkImage:
        img = self._fit(self._sprites[name], size)
        if dimmed:
            img = self._dimmed(img)
        if tint is not None:
            img = self._tinted(img, tint)
        return ctk.CTkImage(img, size=img.size)

    def sprite(self, name: str) -> Image.Image:
        return self._sprites[name]

    def ctk_marker(self, icon: int, size: int) -> ctk.CTkImage:
        return ctk.CTkImage(self._markers[icon], size=(size, size))


class MapWindow:
    """Toplevel with the world map, teleport targets and the marker editor."""

    _instance: MapWindow | None = None

    def __init__(
        self,
        parent,
        maps_dir: Path,
        locations: list[MapLocation],
        on_teleport: Callable[[MapLocation], None],
        player: tuple[int, float, float] | None = None,
        marker_editor: MapMarkerEditor | None = None,
        on_apply_markers: Callable[[MapMarkerEditor], MapMarkerEditor | None]
        | None = None,
        on_copy_markers: Callable[[dict], None] | None = None,
        on_import_markers: Callable[[MapMarkerEditor], bool] | None = None,
        on_export_markers: Callable[[MapMarkerEditor], None] | None = None,
        grace_state: Callable[[int], bool | None] | None = None,
        on_set_grace: Callable[[int, bool], None] | None = None,
        on_unlock: Callable[[list[int], list[int]], None] | None = None,
        on_select_slot: Callable[[str], None] | None = None,
        on_move_bloodstain: Callable[[], None] | None = None,
        convergence: bool = False,
    ):
        MapWindow._instance = self
        self._on_select_slot = on_select_slot
        self._on_move_bloodstain = on_move_bloodstain
        # (map number, map x, map y, label, runes) of the bloodstain, None
        # when there is none
        self._bloodstain: tuple[int, float, float, str, int] | None = None
        self._parent = parent
        self._images = _MapImages(maps_dir, convergence)
        meta = json.loads((maps_dir / "maps.json").read_text(encoding="utf-8"))
        self._icons = _MapIcons(maps_dir, meta["icons"])
        self._on_teleport = on_teleport
        self._on_apply_markers = on_apply_markers
        self._on_copy_markers = on_copy_markers
        self._on_import_markers = on_import_markers
        self._on_export_markers = on_export_markers
        self._grace_state = _safe_reader(grace_state)
        self._on_set_grace = on_set_grace
        self._on_unlock = on_unlock
        # Dungeon map id -> WorldMapPointParam icon id of the nearest map point.
        self._dungeon_icons = meta["dungeon_icons"]
        self._place_locations(locations)
        self._pickup_states: dict[int, bool | None] = {}
        self._pickup_version = 0
        # Pickup types shown on the map and in the Items list
        self._pickup_types: set[str] = set(_PICKUP_TYPES)
        self._completion_cache: dict[str, dict[str, tuple[list, list]]] | None = None
        self._selected_region: str | None = None
        self._set_pickup_pins(_place_pickups(convergence))
        self._boss_pins = _place_bosses(convergence)
        self._merchant_pins = _place_merchants(convergence)
        self._object_pins = _place_objects(convergence)
        self._painting_pins = _place_paintings(convergence)
        self._on_set_flags: Callable[[dict[int, bool], str, str, bool], None] | None = (
            None
        )
        self._selected_pin: _Pin | None = None
        # NpcSpot.npc whose quest the panel shows when NPCs share a marker
        self._active_npc: str | None = None
        # id(quest step) -> (map number, map x, map y) of the shown quest
        self._step_maps: dict[int, tuple[int, float, float]] = {}
        self._on_set_pickup: Callable[[int, bool], None] | None = None
        self._item_photos: dict[tuple[str, int], ImageTk.PhotoImage | None] = {}
        self._hover_tile: _Placed | None = None
        self._list_rows: list[_Placed | _Pin] = []
        self._player = player
        self._editor = marker_editor

        self._map_no = player[0] if player else MAP_LANDS_BETWEEN
        self._zoom = 0.1
        self._vx = 0.0
        self._vy = 0.0
        self._items: dict[int, tuple[str, object]] = {}
        self._selected_loc: _Placed | None = None
        self._selected_marker: MapMarker | None = None
        # Floors under the last map click, nearest first; _pin_var indexes it.
        self._pins: list[FloorPoint] = []
        self._pin_var = tk.IntVar(value=0)
        self._press: tuple[int, int] | None = None
        self._press_view: tuple[float, float] = (0.0, 0.0)
        self._pan_origin: tuple[int, int, float, float] = (0, 0, 0.0, 0.0)
        self._drag_marker: MapMarker | None = None
        self._dragging = False
        self._render_pending = False
        self._list_markers: list[MapMarker] = []
        self._syncing_list = False
        self._tile_items: dict[tuple[int, int], tuple[int, ImageTk.PhotoImage]] = {}
        self._tile_key: tuple | None = None
        self._settle_job = None
        self._marker_tags: dict[int, str] = {}

        self._win = ctk.CTkToplevel(parent)
        self._win.title("World Map")
        self._win.protocol("WM_DELETE_WINDOW", self._close)
        self._size_to_main_window()
        self._win.minsize(900, 600)
        style_window_frame(self._win, dialog=False)

        self._click_target = tk.StringVar(value=_TARGET_PINS)
        self._show_grid = tk.BooleanVar(value=False)
        self._show_graces = tk.BooleanVar(value=True)
        self._show_dungeons = tk.BooleanVar(value=True)
        self._show_markers = tk.BooleanVar(value=True)
        self._show_progress = tk.BooleanVar(value=True)
        self._show_pickups = tk.BooleanVar(value=False)
        self._show_npcs = tk.BooleanVar(value=True)
        self._show_bosses = tk.BooleanVar(value=True)
        self._show_merchants = tk.BooleanVar(value=True)
        self._show_pools = tk.BooleanVar(value=False)
        # Summoning pools exist only for vanilla .sl2 saves
        self._pools_available = False
        self._show_seals = tk.BooleanVar(value=True)
        self._show_paintings = tk.BooleanVar(value=True)
        self._show_names = tk.BooleanVar(value=True)
        # Bosses layer and list: only Remembrance / Great Rune bosses
        self._major_only = tk.BooleanVar(value=False)
        # Bosses, pools, seals and paintings as small plain dots
        self._plain_dots = tk.BooleanVar(value=False)
        self._click_mode = tk.StringVar(value=_MODE_SELECT)
        self._icon = MARKER_ICONS[0]
        self._icon_buttons: dict[int, ctk.CTkButton] = {}

        self._build_ui()
        self._refresh_marker_panel()
        self._win.after(60, self._initial_view)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def focus(self):
        self._win.deiconify()
        self._win.lift()
        self._win.focus_force()

    def set_player(self, player: tuple[int, float, float] | None):
        self._player = player
        self._schedule_render()

    def set_character(self, names: list[str], current: str | None):
        """Slot names for the character picker and the loaded one."""
        self._char_combo.configure(values=names or [""])
        self._char_combo.set(current or "")

    def set_bloodstain(self, bloodstain: tuple[int, float, float, str, int] | None):
        self._bloodstain = bloodstain
        if bloodstain is None:
            self._blood_var.set("Bloodstain: none")
        else:
            self._blood_var.set(f"Bloodstain: {bloodstain[3]}")
        movable = bloodstain is not None and bloodstain[4] > 0
        self._blood_btn.configure(state="normal" if movable else "disabled")
        self._schedule_render()

    def set_grace_callbacks(
        self,
        grace_state: Callable[[int], bool | None] | None,
        on_set_grace: Callable[[int, bool], None] | None,
        on_unlock: Callable[[list[int], list[int]], None] | None = None,
    ):
        """grace_state reads any event flag (graces and map pieces)."""
        self._grace_state = _safe_reader(grace_state)
        self._on_set_grace = on_set_grace
        self._on_unlock = on_unlock
        self._completion_cache = None
        self._read_pickup_states()
        sel = self._selected_pin
        if sel is not None and sel.npcs is not None:
            # NPC pins are rebuilt from the flags: pick up the new state
            self._selected_pin = next(
                (
                    p
                    for p in self._npc_pins(all_maps=True)
                    if (p.map_no, p.point) == (sel.map_no, sel.point)
                ),
                None,
            )
        if self._filter_var.get() in (*_PIN_FILTERS, _FILTER_DONE):
            self._fill_location_list()
        self._update_location_info()
        self._schedule_render()

    def set_locations(self, locations: list[MapLocation], convergence: bool):
        """Teleport targets and map art of the save's flavor."""
        if convergence == self._images.convergence:
            return
        self._images.set_convergence(convergence)
        self._place_locations(locations)
        self._set_pickup_pins(_place_pickups(convergence))
        self._boss_pins = _place_bosses(convergence)
        self._merchant_pins = _place_merchants(convergence)
        self._object_pins = _place_objects(convergence)
        self._painting_pins = _place_paintings(convergence)
        self._completion_cache = None
        self._selected_pin = None
        self._selected_region = None
        self._selected_loc = None
        self._hover_tile = None
        self._tile_key = None
        self._fill_location_list()
        self._update_location_info()
        self._schedule_render()

    def _place_locations(self, locations: list[MapLocation]):
        self._placed = [
            p
            for p in (
                _place(loc, self._dungeon_icons, self._images.convergence)
                for loc in locations
            )
            if p
        ]
        self._tiles = {p.loc.map_id_str: p for p in self._placed if p.rect is not None}
        self._graces_by_map: dict[int, list[_Placed]] = {}
        for g in self._placed:
            if g.loc.tile_type == "grace" and g.point is not None:
                self._graces_by_map.setdefault(g.map_no, []).append(g)

    def _set_pickup_pins(self, pins: list[_Pin]):
        self._pickup_pins = pins
        self._pickup_kinds = {
            p.flag_id: _pickup_kind(p) for p in get_pickups(self._images.convergence)
        }
        self._pickup_grid: dict[tuple[int, int, int], list[_Pin]] = {}
        for pin in pins:
            key = (
                pin.map_no,
                int(pin.point[0] // _PICKUP_CELL),
                int(pin.point[1] // _PICKUP_CELL),
            )
            self._pickup_grid.setdefault(key, []).append(pin)
        self._read_pickup_states()

    def _read_pickup_states(self):
        """Collected state of every pickup, read once per character load;
        the map tiles are painted again when it changes."""
        state = self._grace_state
        states = {
            pin.pickup.flag_id: state(pin.pickup.flag_id) if state else None
            for pin in self._pickup_pins
        }
        if states != self._pickup_states:
            self._pickup_states = states
            self._pickup_version += 1
            self._completion_cache = None
            if hasattr(self, "_win"):
                self._schedule_render()

    def _pins_near(self, map_no: int, x0: float, y0: float, x1: float, y1: float):
        """Pickup pins of the shown types with a point inside the map
        rectangle."""
        types = self._pickup_types
        for i in range(int(x0 // _PICKUP_CELL), int(x1 // _PICKUP_CELL) + 1):
            for j in range(int(y0 // _PICKUP_CELL), int(y1 // _PICKUP_CELL) + 1):
                for pin in self._pickup_grid.get((map_no, i, j), ()):
                    px, py = pin.point
                    if (
                        x0 <= px <= x1
                        and y0 <= py <= y1
                        and self._pickup_kinds[pin.pickup.flag_id] in types
                    ):
                        yield pin

    def _pickup_size(self) -> int:
        """Glow size, smaller as the map zooms out."""
        return max(_PICKUP_MIN, min(_PICKUP_MAX, round(self._zoom * 16)))

    def _tile_layers(self) -> tuple:
        """What the map tiles show besides the map: the pickup glows."""
        return (
            self._show_pickups.get(),
            self._pickup_version,
            frozenset(self._pickup_types),
        )

    def set_flag_callback(
        self, on_set_flags: Callable[[dict[int, bool], str, str, bool], None] | None
    ):
        """on_set_flags(changes, operation, message, to_roundtable) writes
        NPC and boss flags; to_roundtable also moves the character to
        Roundtable Hold so a respawned boss's area loads fresh."""
        self._on_set_flags = on_set_flags
        self._update_location_info()

    def set_pickup_callback(self, on_set_pickup: Callable[[int, bool], None] | None):
        """on_set_pickup(flag, collected) writes an item pickup flag."""
        self._on_set_pickup = on_set_pickup
        self._update_location_info()
        self._schedule_render()

    def set_pools_available(self, available: bool):
        """Show the summoning pool layer; set for vanilla .sl2 saves only."""
        if available == self._pools_available:
            return
        self._pools_available = available
        if available:
            self._pool_check.pack(side=tk.LEFT, padx=(6, 4), before=self._seal_check)
            for widget in self._pool_legend:
                widget.grid()
        else:
            self._pool_check.pack_forget()
            for widget in self._pool_legend:
                widget.grid_remove()
            sel = self._selected_pin
            if sel is not None and sel.obj is not None and sel.obj.kind == POOL:
                self._selected_pin = None
        self._completion_cache = None
        self._fill_location_list()
        self._update_location_info()
        self._schedule_render()

    def _pools_shown(self) -> bool:
        return self._pools_available and self._show_pools.get()

    def set_marker_editor(self, editor: MapMarkerEditor | None):
        self._editor = editor
        self._selected_marker = None
        self._refresh_marker_panel()
        self._schedule_render()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _size_to_main_window(self):
        """Same size as the main window and centered over it. The screen size
        is not used: on multi-monitor X11 it spans every monitor."""
        top = self._parent.winfo_toplevel()
        top.update_idletasks()
        get_scale = getattr(self._win, "_get_window_scaling", None)
        scale = get_scale() if get_scale else 1.0
        width = max(900, round(top.winfo_width() / scale))
        height = max(600, round(top.winfo_height() / scale))
        center_window(self._win, width, height, parent=top)

    def _build_ui(self):
        bar = ctk.CTkFrame(self._win, corner_radius=0)
        bar.pack(fill=tk.X, side=tk.TOP)
        # Packed first, so a narrow window wraps the groups, not this
        ds.button(bar, "Close", self._close, primary=False, width=80).pack(
            side=tk.RIGHT, padx=10, pady=8
        )
        ds.button(
            bar,
            "Export Progress",
            lambda: self._export_checklist(),
            primary=False,
            width=130,
        ).pack(side=tk.RIGHT, pady=8)
        # Two groups that move onto separate lines when the window is narrow
        flow = ds.FlowRow(bar, gap=8)
        flow.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0), pady=8)
        pick = ctk.CTkFrame(flow, fg_color="transparent")
        toggles = ctk.CTkFrame(flow, fg_color="transparent")
        # Layers of the save's state, a group of their own so a narrow
        # window wraps them onto the next line
        layers = ctk.CTkFrame(flow, fg_color="transparent")

        ctk.CTkLabel(pick, text="Character", font=ds.SMALL).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        self._char_combo = ctk.CTkComboBox(
            pick,
            values=[""],
            width=200,
            state="readonly",
            command=self._on_character_chosen,
        )
        self._char_combo.pack(side=tk.LEFT)
        patch_combo_scroll(self._char_combo)

        self._map_switch = ctk.CTkSegmentedButton(
            pick,
            values=[MAP_NAMES[m] for m in _MAP_ORDER],
            command=self._on_map_switch,
            font=ds.FONT,
        )
        self._map_switch.set(MAP_NAMES[self._map_no])
        self._map_switch.pack(side=tk.LEFT, padx=(14, 4))

        ctk.CTkLabel(toggles, text="Click", font=ds.SMALL).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ctk.CTkSegmentedButton(
            toggles,
            values=[_TARGET_PINS, _TARGET_TILES],
            variable=self._click_target,
            command=self._on_target_switch,
            font=ds.SMALL,
        ).pack(side=tk.LEFT, padx=(0, 10))
        for i, (text, var) in enumerate(
            (
                ("Grid", self._show_grid),
                ("Graces", self._show_graces),
                ("Dungeons", self._show_dungeons),
                ("Markers", self._show_markers),
                ("Progress", self._show_progress),
                ("Names", self._show_names),
                ("Dots", self._plain_dots),
                ("Pickups", self._show_pickups),
                ("NPCs", self._show_npcs),
                ("Bosses", self._show_bosses),
                ("Remembrance Only", self._major_only),
                ("Merchants", self._show_merchants),
                ("Pools", self._show_pools),
                ("Imp Seals", self._show_seals),
                ("Paintings", self._show_paintings),
            )
        ):
            parent = toggles if i < 7 else layers
            box = ctk.CTkCheckBox(
                parent,
                text=text,
                variable=var,
                command=self._on_major_only
                if var is self._major_only
                else self._schedule_render,
                font=ds.SMALL,
                width=20,
            )
            box.pack(side=tk.LEFT, padx=(0 if i in (0, 7) else 6, 4))
            if var is self._show_pools:
                self._pool_check = box
            elif var is self._show_seals:
                self._seal_check = box
            if var is self._show_pickups:
                self._types_btn = ds.button(
                    layers,
                    "Types",
                    self._open_type_filter,
                    primary=False,
                    width=56,
                )
                self._types_btn.pack(side=tk.LEFT, padx=(0, 4))
        flow.add(pick, toggles, layers)
        if not self._pools_available:
            self._pool_check.pack_forget()

        body = ctk.CTkFrame(self._win, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True)

        side = ctk.CTkFrame(body, width=320, corner_radius=0)
        side.pack(side=tk.RIGHT, fill=tk.Y)
        side.pack_propagate(False)
        self._build_side_panel(side)

        left = ctk.CTkFrame(body, width=330, corner_radius=0)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)
        self._build_location_list(left)

        self._canvas = tk.Canvas(body, highlightthickness=0, bg=_BACKGROUND_HEX)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        c = self._canvas
        c.bind("<Configure>", lambda e: self._on_resize())
        c.bind("<ButtonPress-1>", self._on_press)
        c.bind("<B1-Motion>", self._on_drag)
        c.bind("<ButtonRelease-1>", self._on_release)
        for button in ("2", "3"):
            c.bind(f"<ButtonPress-{button}>", self._on_pan_press)
            c.bind(f"<B{button}-Motion>", self._on_pan_drag)
        c.bind("<Button-4>", lambda e: self._zoom_at(e.x, e.y, _ZOOM_STEP))
        c.bind("<Button-5>", lambda e: self._zoom_at(e.x, e.y, 1 / _ZOOM_STEP))
        c.bind(
            "<MouseWheel>",
            lambda e: self._zoom_at(
                e.x, e.y, _ZOOM_STEP if e.delta > 0 else 1 / _ZOOM_STEP
            ),
        )
        c.bind("<Motion>", self._on_motion)
        c.bind("<Leave>", lambda e: self._clear_hover())
        self._win.bind("<Delete>", lambda e: self._delete_selected_marker())

    def _on_major_only(self):
        if self._major_only.get():
            self._show_bosses.set(True)
        if self._filter_var.get() in (_FILTER_ALL, _FILTER_BOSSES):
            self._fill_location_list()
        self._schedule_render()

    def _open_type_filter(self):
        """Popup under the Types button with a checkbox per pickup type."""
        old = getattr(self, "_type_popup", None)
        if old is not None and old.winfo_exists():
            old.destroy()
            return
        pop = ctk.CTkToplevel(self._win)
        self._type_popup = pop
        pop.overrideredirect(True)
        pop.transient(self._win)
        btn = self._types_btn
        pop.geometry(
            f"+{btn.winfo_rootx()}+{btn.winfo_rooty() + btn.winfo_height() + 2}"
        )
        frame = ctk.CTkFrame(pop, fg_color=ds.BOX, corner_radius=8)
        frame.pack(fill=tk.BOTH, expand=True)
        vars_: dict[str, tk.BooleanVar] = {}

        def apply():
            self._pickup_types = {t for t, v in vars_.items() if v.get()}
            self._show_pickups.set(True)
            if self._filter_var.get() == _FILTER_ITEMS:
                self._fill_location_list()
            self._schedule_render()

        def set_all(state: bool):
            for v in vars_.values():
                v.set(state)
            apply()

        for t in _PICKUP_TYPES:
            vars_[t] = tk.BooleanVar(value=t in self._pickup_types)
            ctk.CTkCheckBox(
                frame, text=t, variable=vars_[t], command=apply, font=ds.SMALL
            ).pack(anchor="w", padx=10, pady=2)
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill=tk.X, padx=10, pady=(6, 10))
        ds.button(row, "All", lambda: set_all(True), primary=False, width=60).pack(
            side=tk.LEFT
        )
        ds.button(row, "None", lambda: set_all(False), primary=False, width=60).pack(
            side=tk.LEFT, padx=6
        )
        ds.button(row, "Done", pop.destroy, width=60).pack(side=tk.LEFT)
        pop.bind("<Escape>", lambda _e: pop.destroy())
        pop.focus_set()

    def _build_side_panel(self, side):
        pad = {"padx": 12}

        ctk.CTkLabel(side, text="Location", font=ds.BOLD, anchor="w").pack(
            fill=tk.X, pady=(12, 2), **pad
        )
        self._info_var = tk.StringVar(value="")
        # Item icons of a selected pickup, packed above the info text
        self._pin_icons = ctk.CTkFrame(side, fg_color="transparent")
        self._info_label = ctk.CTkLabel(
            side,
            textvariable=self._info_var,
            font=ds.SMALL,
            anchor="w",
            justify=tk.LEFT,
            wraplength=290,
        )
        self._info_label.pack(fill=tk.X, **pad)
        self._floor_frame = ctk.CTkFrame(side, fg_color="transparent")
        self._teleport_btn = ds.button(
            side, "Teleport Here", self._teleport, state="disabled"
        )
        self._teleport_btn.pack(fill=tk.X, pady=(6, 4), **pad)
        # Packed under the teleport button while a world pickup is selected
        self._pin_btn = ds.button(side, "Respawn", self._pin_action, primary=False)

        blood_row = ctk.CTkFrame(side, fg_color="transparent")
        blood_row.pack(side=tk.TOP, fill=tk.X, pady=(2, 6), **pad)
        self._blood_var = tk.StringVar(value="Bloodstain: none")
        ctk.CTkLabel(
            blood_row,
            textvariable=self._blood_var,
            font=ds.SMALL,
            anchor="w",
            justify=tk.LEFT,
            wraplength=290,
        ).pack(fill=tk.X)
        self._blood_btn = ds.button(
            blood_row,
            "Move Bloodstain to Player",
            self._move_bloodstain,
            primary=False,
            state="disabled",
        )
        self._blood_btn.pack(fill=tk.X, pady=(4, 0))

        grace_row = ctk.CTkFrame(side, fg_color="transparent")
        grace_row.pack(fill=tk.X, pady=(0, 6), **pad)
        self._grace_var = tk.StringVar(value="")
        self._grace_label = ctk.CTkLabel(
            grace_row, textvariable=self._grace_var, font=ds.SMALL, anchor="w"
        )
        self._grace_label.pack(side=tk.LEFT)
        self._grace_btn = ds.button(
            grace_row, "Unlock", self._toggle_grace, primary=False, width=90
        )
        self._grace_row = grace_row
        unlock_row = ctk.CTkFrame(side, fg_color="transparent")
        unlock_row.pack(fill=tk.X, pady=(0, 6), **pad)
        self._area_btn = ds.button(
            unlock_row, "Unlock Area", self._unlock_area, primary=False
        )
        self._area_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        ds.button(unlock_row, "Unlock Whole Map", self._unlock_map, primary=False).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0)
        )
        self._unlock_row = unlock_row
        # Merchant lineup or NPC quest steps, packed under the unlock row
        # while a merchant or NPC is selected
        self._detail = ctk.CTkFrame(side, fg_color="transparent")
        self._detail_rows: list = []
        self._update_location_info()

        ctk.CTkFrame(side, height=2, fg_color=ds.BOX).pack(fill=tk.X, pady=6, **pad)

        ctk.CTkLabel(side, text="Map Markers", font=ds.BOLD, anchor="w").pack(
            fill=tk.X, pady=(4, 2), **pad
        )
        self._marker_status = tk.StringVar(value="")
        ctk.CTkLabel(
            side,
            textvariable=self._marker_status,
            font=ds.SMALL,
            anchor="w",
            justify=tk.LEFT,
            wraplength=290,
            text_color=ds.MUTED,
        ).pack(fill=tk.X, **pad)

        self._marker_frame = ctk.CTkFrame(side, fg_color="transparent")
        self._marker_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 10), **pad)
        mf = self._marker_frame

        ctk.CTkSegmentedButton(
            mf,
            values=[_MODE_SELECT, _MODE_MARKER, _MODE_BEACON],
            variable=self._click_mode,
            font=ds.SMALL,
        ).pack(fill=tk.X, pady=(0, 6))

        ctk.CTkLabel(mf, text="Marker icon", font=ds.SMALL, anchor="w").pack(fill=tk.X)
        grid = ctk.CTkFrame(mf, fg_color="transparent")
        grid.pack(fill=tk.X, pady=(2, 6))
        for n, icon in enumerate(MARKER_ICONS):
            button = ctk.CTkButton(
                grid,
                text="",
                image=self._icons.ctk_marker(icon, 32),
                width=44,
                height=44,
                fg_color="transparent",
                hover_color=palette.PURPLE_TINT,
                command=lambda i=icon: self._choose_icon(i),
            )
            button.grid(row=n // 5, column=n % 5, padx=2, pady=2)
            self._icon_buttons[icon] = button
        self._highlight_icon()

        # Buttons are packed from the bottom so the list takes what is left.
        row = ctk.CTkFrame(mf, fg_color="transparent")
        row.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        ds.button(row, "Apply All Changes", self._apply, width=160).pack(side=tk.LEFT)
        ds.button(row, "Revert", self._revert, primary=False, width=90).pack(
            side=tk.LEFT, padx=6
        )

        row = ctk.CTkFrame(mf, fg_color="transparent")
        row.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))
        ds.button(row, "Export...", self._export, primary=False, width=90).pack(
            side=tk.LEFT
        )
        ds.button(row, "Import...", self._import, primary=False, width=90).pack(
            side=tk.LEFT, padx=6
        )
        ds.button(row, "Copy To...", self._copy, primary=False, width=90).pack(
            side=tk.LEFT
        )

        row = ctk.CTkFrame(mf, fg_color="transparent")
        row.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))
        ds.button(row, "Delete", self._delete_selected_marker, width=90).pack(
            side=tk.LEFT
        )
        ds.button(row, "Clear Map", self._clear_map, primary=False, width=90).pack(
            side=tk.LEFT, padx=6
        )
        ds.button(row, "Clear All", self._clear_all, primary=False, width=90).pack(
            side=tk.LEFT
        )

        box, self._marker_list = ds.themed_tree(
            mf, show="tree", selectmode="browse", height=6
        )
        self._marker_list.column("#0", width=260, stretch=True)
        box.pack(fill=tk.BOTH, expand=True)
        self._marker_list.bind("<<TreeviewSelect>>", self._on_list_select)
        bind_mousewheel(self._marker_list)

    def _build_location_list(self, left):
        pad = {"padx": 10}
        ctk.CTkLabel(left, text="Locations", font=ds.BOLD, anchor="w").pack(
            fill=tk.X, pady=(12, 4), **pad
        )
        self._search_var = tk.StringVar()
        ctk.CTkEntry(
            left, textvariable=self._search_var, placeholder_text="Search..."
        ).pack(fill=tk.X, **pad)
        self._filter_var = tk.StringVar(value=_FILTER_ALL)
        # Two rows sharing one variable: a row shows no selection while the
        # other row's value is chosen
        for values, pady in (
            ([_FILTER_ALL, _FILTER_GRACES, _FILTER_DUNGEONS, _FILTER_TILES], (6, 2)),
            ([*_PIN_FILTERS, _FILTER_DONE], (2, 6)),
        ):
            ctk.CTkSegmentedButton(
                left,
                values=values,
                variable=self._filter_var,
                command=lambda _v: self._fill_location_list(),
                font=ds.SMALL,
            ).pack(fill=tk.X, pady=pady, **pad)
        self._this_map_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            left,
            text="Only this map",
            variable=self._this_map_var,
            command=self._fill_location_list,
            font=ds.SMALL,
        ).pack(anchor="w", pady=(0, 6), **pad)
        box, self._loc_list = ds.themed_tree(left, show="tree", selectmode="browse")
        self._loc_list.column("#0", width=290, stretch=True)
        self._build_legend(left)
        box.pack(fill=tk.BOTH, expand=True, pady=(0, 10), **pad)
        self._loc_list.bind("<<TreeviewSelect>>", self._on_location_list_select)
        bind_mousewheel(self._loc_list)
        self._search_var.trace_add("write", lambda *_: self._fill_location_list())
        self._fill_location_list()

    @staticmethod
    def _legend_step() -> ctk.CTkImage:
        img = _MapIcons.step_image(1, 44, False)
        return ctk.CTkImage(img, size=(22, 22))

    def _legend_boss(self, defeated: bool, major: bool = False) -> ctk.CTkImage:
        face = "Remembrance of the Grafted" if major else "Golden Seed"
        img = self._icons.boss_image(face, 48, defeated, major)
        return ctk.CTkImage(img, size=(24, 24))

    @staticmethod
    def _legend_disc(icon: Image.Image | None, ring=_GOLD_RING) -> ctk.CTkImage | None:
        if icon is None:
            return None
        img = _MapIcons.disc_image(icon, 44, ring)
        return ctk.CTkImage(img, size=(22, 22))

    def _legend_glow(self, dim: bool) -> ctk.CTkImage:
        img = self._icons.glow_image(_PICKUP_MAX, dim)
        return ctk.CTkImage(img, size=(22, 22))

    def _build_legend(self, parent):
        """Icon legend, packed at the bottom of parent."""
        legend = ctk.CTkFrame(parent, fg_color=ds.BOX, corner_radius=8)
        legend.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        ctk.CTkLabel(legend, text="Legend", font=ds.BOLD, anchor="w").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(6, 2)
        )
        tile = Image.new("RGBA", (20, 20))
        ImageDraw.Draw(tile).rectangle((2, 2, 17, 17), outline="white", width=2)
        entries = (
            (self._icons.ctk_sprite("player", 24), "Character"),
            (self._icons.ctk_sprite("bloodstain", 22), "Bloodstain"),
            (self._icons.ctk_sprite("bloodstain", 22, dimmed=True), "No runes"),
            (self._icons.ctk_sprite("grace", 22), "Site of Grace"),
            (self._icons.ctk_sprite("grace", 22, dimmed=True), "Locked grace"),
            (self._icons.ctk_sprite("dungeon_4", 24), "Dungeon"),
            (ctk.CTkImage(tile, size=(20, 20)), "Tile (hover)"),
            (self._icons.ctk_marker(1, 22), "Map marker"),
            (self._icons.ctk_sprite("beacon", 24), "Beacon"),
            (self._legend_glow(False), "Item pickup"),
            (self._legend_glow(True), "Collected"),
            (self._icons.ctk_sprite("npc", 22), "NPC"),
            (self._icons.ctk_sprite("npc", 22, tint=_HOSTILE_TINT), "Hostile NPC"),
            (self._icons.ctk_sprite("npc", 22, dimmed=True), "Dead NPC"),
            (self._legend_boss(False), "Boss"),
            (self._legend_boss(False, major=True), "Remembrance boss"),
            (self._legend_boss(True), "Defeated boss"),
            (self._icons.ctk_sprite("merchant", 22), "Merchant"),
            (self._legend_step(), "Quest step"),
            (self._legend_disc(get_icon(_SEAL_ICON), _SILVER_RING), "Imp seal"),
            (
                self._legend_disc(get_icon("Homing Instinct Painting"), _SILVER_RING),
                "Painting vista",
            ),
            # Last, so hiding it on saves without pools leaves no gap
            (self._legend_disc(self._icons.sprite("pool")), "Summoning pool"),
        )
        for n, (image, text) in enumerate(entries):
            row, col = 1 + n // 2, (n % 2) * 2
            icon = ctk.CTkLabel(legend, text="", image=image, width=26)
            icon.grid(row=row, column=col, padx=(8, 2), pady=1)
            label = ctk.CTkLabel(legend, text=text, font=ds.SMALL, anchor="w")
            label.grid(row=row, column=col + 1, sticky="w", padx=(0, 6), pady=1)
        self._pool_legend = (icon, label)
        if not self._pools_available:
            for widget in self._pool_legend:
                widget.grid_remove()
        ctk.CTkLabel(
            legend,
            text="Scroll to zoom, drag to pan (right or middle drag pans too)",
            font=ds.SMALL,
            text_color=ds.MUTED,
            anchor="w",
            justify=tk.LEFT,
            wraplength=280,
        ).grid(
            row=1 + (len(entries) + 1) // 2,
            column=0,
            columnspan=4,
            sticky="w",
            padx=8,
            pady=(4, 8),
        )

    def _pin_rows(self, kind: str) -> list[tuple[str, str, _Pin]]:
        """(group, label, pin) rows of the Bosses, NPCs or Items list.
        Bosses group by region, items by their nearest grace's region."""
        if kind == _FILTER_BOSSES:
            # Remembrance and Great Rune bosses also get a group of their own
            rows = [
                (
                    p.boss.region or self._region_at(p.map_no, p.point) or "Other",
                    p.boss.name,
                    p,
                )
                for p in self._boss_pins
                if not self._major_only.get() or _major_boss(p.boss)
            ]
            rows += [
                (_MAJOR_GROUP, p.boss.name, p)
                for p in self._boss_pins
                if _major_boss(p.boss)
            ]
            return rows
        if kind == _FILTER_MERCHANTS:
            return [("", p.merchant.name, p) for p in self._merchant_pins]
        if kind == _FILTER_NPCS:
            rows = []
            for p in self._npc_pins(all_maps=True):
                for spot in p.npcs:
                    state = " (dead)" if spot.dead else ""
                    rows.append(("", spot.name + state, p))
            return rows
        regions = {
            g.loc.flag_id: g.loc.name.partition(" - ")[0]
            for g in self._placed
            if g.loc.tile_type == "grace" and " - " in g.loc.name
        }
        return [
            (regions.get(p.pickup.grace_flag, "Other"), p.pickup.item_label, p)
            for p in self._pickup_pins
            if self._pickup_kinds[p.pickup.flag_id] in self._pickup_types
        ]

    def _pin_list_icon(self, pin: _Pin):
        if pin.obj is not None:
            if pin.obj.kind == POOL:
                return self._icons.pool(
                    _LIST_ICON, self._object_done(pin.obj) is not False
                )
            return self._icons.item_disc(
                _SEAL_ICON, _LIST_ICON, bool(self._object_done(pin.obj))
            )
        if pin.painting is not None:
            return self._icons.item_disc(
                pin.painting.painting.items[0][2],
                _LIST_ICON,
                bool(self._pickup_collected(pin.painting.reward)),
            )
        if pin.boss is not None:
            key = ("list", pin.boss.face)
            if key not in self._item_photos:
                img = self._icons.boss_image(pin.boss.face, _LIST_ICON * 2, False)
                self._item_photos[key] = ImageTk.PhotoImage(
                    _MapIcons._fit(img, _LIST_ICON)
                )
            return self._item_photos[key]
        if pin.merchant is not None:
            return self._icons.merchant(_LIST_ICON)
        if pin.npcs is not None:
            return self._icons.npc(
                _LIST_ICON,
                any(s.hostile for s in pin.npcs),
                all(s.dead for s in pin.npcs),
            )
        taken = bool(self._pickup_collected(pin.pickup))
        return self._icons.glow(_PICKUP_MAX, taken)

    def _fill_pin_list(self, kind: str, query: str):
        rows = [
            r
            for r in self._pin_rows(kind)
            if (not self._this_map_var.get() or r[2].map_no == self._map_no)
            and (not query or query in r[1].lower() or query in r[0].lower())
        ]
        rows.sort(key=lambda r: (r[0] != _MAJOR_GROUP, r[0].lower(), r[1].lower()))
        self._list_rows = [r[2] for r in rows]
        tree = self._loc_list
        tree.delete(*tree.get_children())
        groups: dict[str, str] = {}
        for n, (group, label, pin) in enumerate(rows):
            parent = ""
            if group:
                parent = groups.get(group)
                if parent is None:
                    parent = groups[group] = f"r:{group}"
                    tree.insert("", "end", iid=parent, text=group, open=bool(query))
            tree.insert(
                parent,
                "end",
                iid=str(n),
                text=f" {label}",
                image=self._pin_list_icon(pin),
            )

    def _fill_location_list(self):
        query = self._search_var.get().strip().lower()
        kind = self._filter_var.get()
        if kind in _PIN_FILTERS:
            self._fill_pin_list(kind, query)
            return
        if kind == _FILTER_DONE:
            self._fill_done_list(query)
            return
        wanted = {
            _FILTER_GRACES: ("grace",),
            _FILTER_DUNGEONS: ("dungeon",),
            _FILTER_TILES: ("small",),
        }.get(self._filter_var.get())
        rows = [
            p
            for p in self._placed
            if (wanted is None or p.loc.tile_type in wanted)
            and (not self._this_map_var.get() or p.map_no == self._map_no)
            and (not query or query in p.loc.name.lower() or query in p.loc.map_id_str)
        ]
        rows.sort(key=lambda p: p.loc.name.lower())
        self._list_rows = rows
        tree = self._loc_list
        tree.delete(*tree.get_children())
        # "Region - Name" rows go under a region row so the list shows the
        # name itself; names without a region stay top level.
        regions = {p.loc.name.partition(" - ")[0] for p in rows if " - " in p.loc.name}
        groups: dict[str, str] = {}
        for n, p in enumerate(rows):
            region, sep, name = p.loc.name.partition(" - ")
            parent = ""
            if sep or region in regions:
                parent = groups.get(region)
                if parent is None:
                    parent = groups[region] = f"r:{region}"
                    tree.insert("", "end", iid=parent, text=region, open=bool(query))
            if not sep:
                name = region
            if p.loc.tile_type == "grace":
                image = self._icons.grace(_LIST_ICON)
            elif p.loc.tile_type == "dungeon":
                image = self._icons.dungeon(p.icon, _LIST_ICON)
            else:
                image = ""
            tree.insert(parent, "end", iid=str(n), text=f" {name}", image=image)
        if kind == _FILTER_ALL:
            self._add_pin_groups(query)

    def _add_pin_groups(self, query: str):
        """All also lists bosses, NPCs, merchants and items, each under a
        group row that opens while searching."""
        tree = self._loc_list
        for kind in _PIN_FILTERS:
            rows = [
                r
                for r in self._pin_rows(kind)
                if r[0] != _MAJOR_GROUP
                and (not self._this_map_var.get() or r[2].map_no == self._map_no)
                and (not query or query in r[1].lower() or query in r[0].lower())
            ]
            if not rows:
                continue
            rows.sort(key=lambda r: r[1].lower())
            group = f"r:all:{kind}"
            tree.insert(
                "", "end", iid=group, text=f"{kind} ({len(rows)})", open=bool(query)
            )
            for _region, label, pin in rows:
                tree.insert(
                    group,
                    "end",
                    iid=str(len(self._list_rows)),
                    text=f" {label}",
                    image=self._pin_list_icon(pin),
                )
                self._list_rows.append(pin)

    def _on_location_list_select(self, _event=None):
        sel = self._loc_list.selection()
        if not sel:
            return
        if sel[0].startswith("r:"):
            self._loc_list.item(sel[0], open=not self._loc_list.item(sel[0], "open"))
            return
        placed = self._list_rows[int(sel[0])]
        if isinstance(placed, str):
            self._select_region(placed)
            return
        if isinstance(placed, _Pin):
            self._show_map(placed.map_no)
            # The pin's layer is turned on so the selection shows
            layer = (
                self._show_pools
                if placed.obj is not None and placed.obj.kind == POOL
                else self._show_seals
                if placed.obj is not None
                else self._show_paintings
                if placed.painting is not None
                else self._show_bosses
                if placed.boss is not None
                else self._show_merchants
                if placed.merchant is not None
                else self._show_npcs
                if placed.npcs is not None
                else self._show_pickups
            )
            layer.set(True)
            self._center_on(*placed.point, max(self._zoom, self._fit_zoom() * 4))
            self._select_pin(placed)
            return
        self._show_map(placed.map_no)
        if placed.point is not None:
            x, y = placed.point
        else:
            x0, y0, x1, y1 = placed.rect
            x, y = (x0 + x1) / 2, (y0 + y1) / 2
        self._center_on(x, y, max(self._zoom, self._fit_zoom() * 4))
        self._select_location(placed)

    # ------------------------------------------------------------------
    # View
    # ------------------------------------------------------------------

    def _canvas_size(self) -> tuple[int, int]:
        return max(1, self._canvas.winfo_width()), max(1, self._canvas.winfo_height())

    def _fit_zoom(self) -> float:
        w, h = self._canvas_size()
        x0, y0, x1, y1 = self._images.bounds(self._map_no)
        return min(w / (x1 - x0), h / (y1 - y0))

    def _fit(self):
        w, h = self._canvas_size()
        x0, y0, x1, y1 = self._images.bounds(self._map_no)
        self._zoom = self._fit_zoom()
        self._vx = (x0 + x1) / 2 - w / 2 / self._zoom
        self._vy = (y0 + y1) / 2 - h / 2 / self._zoom

    def _center_on(self, mx: float, my: float, zoom: float | None = None):
        w, h = self._canvas_size()
        if zoom is not None:
            self._zoom = max(self._fit_zoom(), min(_ZOOM_MAX, zoom))
        self._vx = mx - w / 2 / self._zoom
        self._vy = my - h / 2 / self._zoom
        self._clamp_view()
        self._schedule_render()

    def _initial_view(self):
        self._win.update_idletasks()
        self._fit()
        if self._player and self._player[0] == self._map_no:
            self._center_on(self._player[1], self._player[2], self._fit_zoom() * 3)
        else:
            self._render()

    def _on_resize(self):
        self._zoom = max(self._zoom, self._fit_zoom())
        self._clamp_view()
        self._schedule_render()

    def _clamp_view(self):
        w, h = self._canvas_size()
        x0, y0, x1, y1 = self._images.bounds(self._map_no)
        vw, vh = w / self._zoom, h / self._zoom
        for attr, lo, hi, span in (("_vx", x0, x1, vw), ("_vy", y0, y1, vh)):
            if span >= hi - lo:
                setattr(self, attr, (lo + hi) / 2 - span / 2)
            else:
                setattr(self, attr, max(lo, min(getattr(self, attr), hi - span)))

    def _to_screen(self, mx: float, my: float) -> tuple[float, float]:
        return (mx - self._vx) * self._zoom, (my - self._vy) * self._zoom

    def _to_map(self, sx: float, sy: float) -> tuple[float, float]:
        return self._vx + sx / self._zoom, self._vy + sy / self._zoom

    def _zoom_at(self, sx: int, sy: int, factor: float):
        mx, my = self._to_map(sx, sy)
        self._zoom = max(self._fit_zoom(), min(_ZOOM_MAX, self._zoom * factor))
        self._vx = mx - sx / self._zoom
        self._vy = my - sy / self._zoom
        self._clamp_view()
        self._zoom_preview()
        job = getattr(self, "_zoom_job", None)
        if job is not None:
            self._win.after_cancel(job)
        self._zoom_job = self._win.after(_ZOOM_SETTLE_MS, self._end_zoom)

    def _end_zoom(self):
        self._zoom_job = None
        self._schedule_render()

    def _zoom_preview(self):
        """The view at the new zoom from one half resolution image, scaled up
        by Tk; much cheaper than building the map tiles."""
        if not self._win.winfo_exists():
            return
        locked = self._tile_key[2] if self._tile_key else self._locked_pieces()
        self._cancel_settle()
        c = self._canvas
        c.delete("all")
        self._tile_items.clear()
        self._tile_key = None
        w, h = self._canvas_size()
        img = self._view_image(
            (w + 1) // 2, (h + 1) // 2, self._vx, self._vy, locked, scale=0.5
        )
        half = ImageTk.PhotoImage(img)
        self._preview_photo = tk.PhotoImage(master=c)
        self._preview_photo.tk.call(
            self._preview_photo, "copy", str(half), "-zoom", 2, 2
        )
        c.create_image(0, 0, anchor=tk.NW, image=self._preview_photo, tags="maptile")
        self._draw_overlays()

    def _schedule_render(self):
        if not self._render_pending:
            self._render_pending = True
            self._win.after_idle(self._update_view)

    def _update_view(self):
        """Redraw icons; rebuild map tiles only when zoom or map changed."""
        self._render_pending = False
        if not self._win.winfo_exists():
            return
        if self._tile_key != (
            self._map_no,
            self._zoom,
            self._locked_pieces(),
            self._tile_layers(),
        ):
            self._render()
            return
        # The view may have jumped (center_on, clamp): place the tiles again.
        ox, oy = self._vx * self._zoom, self._vy * self._zoom
        for (i, j), (item, _photo) in self._tile_items.items():
            self._canvas.coords(item, i * _TILE_PX - ox, j * _TILE_PX - oy)
        self._ensure_tiles()
        self._draw_overlays()

    def _render(self):
        """Draw everything again: map tiles for the current zoom and map, and
        the icons and outlines on top."""
        self._render_pending = False
        if not self._win.winfo_exists():
            return
        self._canvas.delete("all")
        self._tile_items.clear()
        self._tile_key = (
            self._map_no,
            self._zoom,
            self._locked_pieces(),
            self._tile_layers(),
        )
        self._ensure_tiles(ring=0)
        self._draw_overlays()
        # Tiles just outside the view, for the next pan, once this is shown
        self._win.after(30, self._ensure_tiles)

    def _ensure_tiles(self, ring: int = 1):
        """Create the map tiles covering the view plus ring tiles around it
        and drop the ones far outside it."""
        if self._tile_key is None or self._tile_key[:2] != (self._map_no, self._zoom):
            self._render()
            return
        c = self._canvas
        w, h = self._canvas_size()
        ox, oy = self._vx * self._zoom, self._vy * self._zoom
        i0 = math.floor(ox / _TILE_PX) - ring
        i1 = math.floor((ox + w) / _TILE_PX) + ring
        j0 = math.floor(oy / _TILE_PX) - ring
        j1 = math.floor((oy + h) / _TILE_PX) + ring
        for key in [
            k
            for k in self._tile_items
            if not (i0 - 2 <= k[0] <= i1 + 2 and j0 - 2 <= k[1] <= j1 + 2)
        ]:
            item, _photo = self._tile_items.pop(key)
            c.delete(item)
        span = _TILE_PX / self._zoom
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                if (i, j) in self._tile_items:
                    continue
                img = self._view_image(_TILE_PX, _TILE_PX, i * span, j * span)
                photo = ImageTk.PhotoImage(img)
                item = c.create_image(
                    i * _TILE_PX - ox,
                    j * _TILE_PX - oy,
                    anchor=tk.NW,
                    image=photo,
                    tags="maptile",
                )
                self._tile_items[(i, j)] = (item, photo)
        c.tag_lower("maptile")

    def _draw_overlays(self):
        self._cancel_settle()
        c = self._canvas
        c.delete("overlay")
        self._items.clear()
        self._draw_locations()
        self._draw_pin()
        self._draw_pins()
        self._draw_player()
        self._draw_markers()
        c.addtag_all("overlay")
        c.dtag("maptile", "overlay")
        # The ring's center is opaque: keep it under every icon.
        c.tag_lower("select_ring")
        c.tag_lower("maptile")

    def _locked_pieces(self) -> frozenset[int]:
        """Fragment pieces of the shown map the character has not revealed;
        empty with Progress off or no character loaded."""
        if not self._show_progress.get() or self._grace_state is None:
            return frozenset()
        states = {
            f: self._grace_state(f) for f in self._images.progress_flags(self._map_no)
        }
        if None in states.values():
            return frozenset()
        return frozenset(f for f, state in states.items() if not state)

    def _view_image(
        self,
        w: int,
        h: int,
        vx: float,
        vy: float,
        locked: frozenset[int] | None = None,
        scale: float = 1.0,
    ) -> Image.Image:
        """The map in a w x h image whose top-left is map point (vx, vy), at
        scale image pixels per screen pixel."""
        zoom = self._zoom * scale
        x0, y0, x1, y1 = self._images.bounds(self._map_no)
        levels = self._images.levels(
            self._map_no, self._tile_key[2] if locked is None else locked
        )
        # Image pixels per screen pixel at full resolution; use the smallest
        # copy that still has at least one pixel per screen pixel.
        density = self._images.scale / zoom
        level = 0
        while level + 1 < len(levels) and density / 2 ** (level + 1) >= 1:
            level += 1
        src = levels[level]
        k = self._images.scale / 2**level
        out = Image.new("RGB", (w, h), _BACKGROUND)
        # Part of the screen box covered by the map, in map units
        ax0, ay0 = max(vx, x0), max(vy, y0)
        ax1, ay1 = min(vx + w / zoom, x1), min(vy + h / zoom, y1)
        if ax1 <= ax0 or ay1 <= ay0:
            return out
        sx0 = round((ax0 - vx) * zoom)
        sy0 = round((ay0 - vy) * zoom)
        sx1 = round((ax1 - vx) * zoom)
        sy1 = round((ay1 - vy) * zoom)
        if sx1 <= sx0 or sy1 <= sy0:
            return out
        box = (
            min((ax0 - x0) * k, src.width),
            min((ay0 - y0) * k, src.height),
            min((ax1 - x0) * k, src.width),
            min((ay1 - y0) * k, src.height),
        )
        part = src.resize((sx1 - sx0, sy1 - sy0), Image.BILINEAR, box=box)
        out.paste(part, (sx0, sy0))
        if self._show_pickups.get():
            self._paint_pickups(out, vx, vy, zoom)
        return out

    def _paint_pickups(self, out: Image.Image, vx: float, vy: float, zoom: float):
        """Pickup glows inside the image whose top-left is map point (vx, vy),
        at zoom image pixels per map unit."""
        size = max(2, round(self._pickup_size() * zoom / self._zoom))
        half = self._icons.glow_cached(size).width / 2
        pad = half / zoom
        w, h = out.size
        x1, y1 = vx + w / zoom, vy + h / zoom
        for pin in self._pins_near(
            self._map_no, vx - pad, vy - pad, x1 + pad, y1 + pad
        ):
            glow = self._icons.glow_cached(
                size, bool(self._pickup_states.get(pin.pickup.flag_id))
            )
            px = round((pin.point[0] - vx) * zoom - half)
            py = round((pin.point[1] - vy) * zoom - half)
            out.paste(glow, (px, py), glow)

    def _pan_to(self, vx: float, vy: float):
        """Pan by moving what is drawn, adding map tiles that come into view;
        icons are drawn again once the view settles."""
        old_vx, old_vy = self._vx, self._vy
        self._vx, self._vy = vx, vy
        self._clamp_view()
        dx = (old_vx - self._vx) * self._zoom
        dy = (old_vy - self._vy) * self._zoom
        if not dx and not dy:
            return
        self._canvas.move("all", dx, dy)
        self._ensure_tiles()
        self._cancel_settle()
        self._settle_job = self._win.after(_SETTLE_MS, self._draw_overlays)

    def _cancel_settle(self):
        job = getattr(self, "_settle_job", None)
        if job is not None:
            self._win.after_cancel(job)
            self._settle_job = None

    def _grace_locked(self, placed: _Placed) -> bool:
        if self._grace_state is None or not placed.loc.flag_id:
            return False
        return self._grace_state(placed.loc.flag_id) is False

    def _draw_locations(self):
        c = self._canvas
        w, h = self._canvas_size()
        m = _RENDER_MARGIN
        if self._show_grid.get():
            for p in self._tiles.values():
                if p.map_no != self._map_no:
                    continue
                sx0, sy0 = self._to_screen(p.rect[0], p.rect[1])
                sx1, sy1 = self._to_screen(p.rect[2], p.rect[3])
                if sx1 < -m or sy1 < -m or sx0 > w + m or sy0 > h + m:
                    continue
                c.create_rectangle(sx0, sy0, sx1, sy1, outline=_GRID_COLOR, width=1)
        sel = self._selected_loc
        if sel is not None and sel.rect is not None and sel.map_no == self._map_no:
            sx0, sy0 = self._to_screen(sel.rect[0], sel.rect[1])
            sx1, sy1 = self._to_screen(sel.rect[2], sel.rect[3])
            c.create_rectangle(sx0, sy0, sx1, sy1, outline=_SELECT_COLOR, width=3)
        for p in self._placed:
            if p.map_no != self._map_no or p.point is None:
                continue
            grace = p.loc.tile_type == "grace"
            if not (self._show_graces if grace else self._show_dungeons).get():
                continue
            sx, sy = self._to_screen(*p.point)
            if not (-m - 30 < sx < w + m + 30 and -m - 30 < sy < h + m + 30):
                continue
            if p is sel:
                c.create_image(
                    sx,
                    sy,
                    image=self._icons.select_ring(
                        _GRACE_SIZE if grace else _DUNGEON_SIZE
                    ),
                    tags="select_ring",
                )
            image = (
                self._icons.grace(_GRACE_SIZE, self._grace_locked(p))
                if grace
                else self._icons.dungeon(p.icon, _DUNGEON_SIZE)
            )
            item = c.create_image(sx, sy, image=image)
            self._items[item] = ("loc", p)

    def _npc_pins(self, all_maps: bool = False) -> list[_Pin]:
        """NPC spots of the loaded character on the shown map (or every
        map), merged when they stand within _NPC_MERGE map units (one NPC
        part stands in several maps of one area, and some NPCs have two
        parts a step apart)."""
        if self._grace_state is None:
            return []
        pins: list[_Pin] = []
        convergence = self._images.convergence
        for spot in npc_spots(self._grace_state, convergence):
            point = _spot_point(
                spot.map_id, spot.position[0], spot.position[2], convergence
            )
            if point is None or (not all_maps and point[0] != self._map_no):
                continue
            pin = next(
                (
                    p
                    for p in pins
                    if p.map_no == point[0]
                    and abs(p.point[0] - point[1]) < _NPC_MERGE
                    and abs(p.point[1] - point[2]) < _NPC_MERGE
                ),
                None,
            )
            if pin is None:
                pins.append(_Pin(point[0], (point[1], point[2]), npcs=[spot]))
            elif all(s.name != spot.name for s in pin.npcs):
                pin.npcs.append(spot)
        return pins

    def _pickup_collected(self, pickup: Pickup) -> bool | None:
        return self._pickup_states.get(pickup.flag_id)

    def _pickup_at(self, sx: int, sy: int) -> _Pin | None:
        """Pickup whose glow core is under the screen point."""
        if not self._show_pickups.get():
            return None
        mx, my = self._to_map(sx, sy)
        r = max(4, self._pickup_size() * 0.6) / self._zoom
        near = list(self._pins_near(self._map_no, mx - r, my - r, mx + r, my + r))
        return min(
            near,
            key=lambda p: (p.point[0] - mx) ** 2 + (p.point[1] - my) ** 2,
            default=None,
        )

    def _draw_pins(self):
        c = self._canvas
        w, h = self._canvas_size()
        m = _RENDER_MARGIN
        sel = self._selected_pin

        def visible(pin: _Pin) -> tuple[float, float] | None:
            if pin.map_no != self._map_no:
                return None
            sx, sy = self._to_screen(*pin.point)
            if -m < sx < w + m and -m < sy < h + m:
                return sx, sy
            return None

        def ring(pin: _Pin, sx: float, sy: float, size: int):
            if pin == sel:
                c.create_image(
                    sx, sy, image=self._icons.select_ring(size), tags="select_ring"
                )

        dots = self._plain_dots.get()

        def marker(pin: _Pin, at, size: int, image, color: tuple, done: bool):
            """The marker art, or a plain dot (gray when done) with Dots on."""
            if dots:
                ring(pin, *at, _DOT_SIZE)
                item = c.create_image(
                    *at, image=self._icons.dot(color, _DOT_SIZE, done)
                )
            else:
                ring(pin, *at, size)
                item = c.create_image(*at, image=image())
            self._items[item] = ("pin", pin)

        if self._show_pickups.get() and sel is not None and sel.pickup is not None:
            at = visible(sel)
            if at is not None:
                ring(sel, *at, self._pickup_size())
        if self._show_bosses.get():
            for pin in self._boss_pins:
                major = _major_boss(pin.boss)
                if self._major_only.get() and not major:
                    continue
                at = visible(pin)
                if at is None:
                    continue
                defeated = self._boss_defeated(pin.boss)
                size = _MAJOR_BOSS_SIZE if major else _BOSS_SIZE
                marker(
                    pin,
                    at,
                    size,
                    lambda p=pin, d=defeated, z=size, m=major: self._icons.boss(
                        p.boss.face, z, d, m
                    ),
                    _DOT_BOSS,
                    bool(defeated),
                )
        if self._show_merchants.get():
            # Merchants who are also NPCs on the map sit beside the NPC ring
            npc_points = (
                [p.point for p in self._npc_pins()] if self._show_npcs.get() else []
            )
            near = 6 / self._zoom
            for pin in self._merchant_pins:
                at = visible(pin)
                if at is None:
                    continue
                sx, sy = at
                if any(
                    abs(px - pin.point[0]) < near and abs(py - pin.point[1]) < near
                    for px, py in npc_points
                ):
                    sx, sy = sx - _MERCHANT_SIZE * 0.8, sy - _MERCHANT_SIZE * 0.4
                ring(pin, sx, sy, _MERCHANT_SIZE)
                item = c.create_image(
                    sx, sy, image=self._icons.merchant(_MERCHANT_SIZE)
                )
                self._items[item] = ("pin", pin)
        if self._pools_shown() or self._show_seals.get():
            for pin in self._object_pins:
                pool = pin.obj.kind == POOL
                if not (self._pools_shown() if pool else self._show_seals.get()):
                    continue
                at = visible(pin)
                if at is None:
                    continue
                done = self._object_done(pin.obj)
                if pool:
                    # Pools show bright once activated, like graces
                    marker(
                        pin,
                        at,
                        _POOL_SIZE,
                        lambda d=done: self._icons.pool(_POOL_SIZE, d is not False),
                        _DOT_POOL,
                        done is False,
                    )
                else:
                    marker(
                        pin,
                        at,
                        _SEAL_SIZE,
                        lambda d=done, k=pin.obj.keys: self._icons.item_disc(
                            _SEAL_ICON, _SEAL_SIZE, bool(d), badge=k if k > 1 else 0
                        ),
                        _DOT_SEAL,
                        bool(done),
                    )
        if sel is not None and sel.painting is not None:
            self._draw_painting_line(sel)
        if self._show_paintings.get():
            for pin in self._painting_pins:
                at = visible(pin)
                if at is None:
                    continue
                solved = bool(self._pickup_collected(pin.painting.reward))
                name = pin.painting.painting.items[0][2]
                marker(
                    pin,
                    at,
                    _PAINTING_SIZE,
                    lambda n=name, d=solved: self._icons.item_disc(
                        n, _PAINTING_SIZE, d
                    ),
                    _DOT_PAINTING,
                    solved,
                )
        if sel is not None and sel.npcs is not None:
            self._draw_quest_route(sel)
        if self._show_npcs.get():
            tags = self._show_names.get() and self._zoom >= _NAME_TAG_ZOOM
            # Tags that would cover one already drawn are left out
            drawn: list[tuple[float, float, float, float]] = []
            for pin in self._npc_pins():
                at = visible(pin)
                if at is None:
                    continue
                sx, sy = at
                ring(pin, sx, sy, _NPC_SIZE)
                hostile = any(s.hostile for s in pin.npcs)
                dead = all(s.dead for s in pin.npcs)
                item = c.create_image(
                    sx, sy, image=self._icons.npc(_NPC_SIZE, hostile, dead)
                )
                self._items[item] = ("pin", pin)
                if tags:
                    self._name_tag(
                        pin, sx, sy + _NPC_SIZE / 2 + 2, hostile, dead, drawn
                    )

    def _name_tag(
        self,
        pin: _Pin,
        sx: float,
        sy: float,
        hostile: bool,
        dead: bool,
        drawn: list[tuple[float, float, float, float]],
    ):
        c = self._canvas
        text = " / ".join(dict.fromkeys(_short_name(s.name) for s in pin.npcs))
        color = "#a0a0a0" if dead else "#ff9a8c" if hostile else "#f0f0f0"
        label = c.create_text(
            sx, sy + 1, text=text, anchor=tk.N, fill=color, font=_TAG_FONT
        )
        x0, y0, x1, y1 = c.bbox(label)
        if any(x0 < b[2] and b[0] < x1 and y0 < b[3] and b[1] < y1 for b in drawn):
            c.delete(label)
            return
        drawn.append((x0 - 4, y0 - 1, x1 + 4, y1 + 1))
        box = c.create_rectangle(
            x0 - 4, y0 - 1, x1 + 4, y1 + 1, fill="#16161c", outline=""
        )
        c.tag_lower(box, label)
        self._items[label] = ("pin", pin)
        self._items[box] = ("pin", pin)

    def _npc_spot(self, pin: _Pin) -> NpcSpot:
        """The NPC of the pin the side panel is about: the one picked above
        the quest list, else the first."""
        return next((s for s in pin.npcs if s.npc == self._active_npc), pin.npcs[0])

    def _npc_base(self, pin: _Pin) -> int | None:
        """Life block of the pin's chosen NPC."""
        npc = self._npc_spot(pin).npc.split(" / ")[0]
        entry = NPC_FLAGS.get(npc)
        return entry[0] if entry else None

    def _step_done(self, step: QuestStep) -> bool:
        state = self._grace_state
        return state is not None and all(
            bool(state(flag_id)) == bool(value) for flag_id, value in step.flags
        )

    def _route(self, pin: _Pin) -> list[tuple[QuestStep, int, float, float]]:
        """(step, map number, map x, map y) of the selected NPC's quest
        steps that move it, in quest order."""
        base = self._npc_base(pin)
        if base is None:
            return []
        convergence = self._images.convergence
        route = []
        for step in quest_steps(base, convergence):
            for _name, map_id, x, _y, z in step.places:
                point = _spot_point(map_id, x, z, convergence)
                if point is not None:
                    route.append((step, *point))
                    break
        return route

    def _draw_quest_route(self, pin: _Pin):
        """Numbered pins where the quest moves the NPC and a dashed line
        through them; steps already reached are gray."""
        c = self._canvas
        off = _STEP_OFFSET
        prev = None
        route = self._route(pin)
        for n, (step, map_no, mx, my) in enumerate(route, start=1):
            if map_no != self._map_no:
                prev = None
                continue
            sx, sy = self._to_screen(mx, my)
            if prev is not None:
                c.create_line(*prev, sx, sy, fill=_ROUTE_COLOR, width=2, dash=(6, 4))
            prev = (sx, sy)
            done = self._step_done(step)
            item = c.create_image(
                sx - off, sy - off, image=self._icons.step(n, _STEP_SIZE, done)
            )
            self._items[item] = ("step", (pin, step))
            # Where the route leaves for (or comes from) another map
            changes = []
            if n > 1 and route[n - 2][1] != map_no:
                changes.append(f"from {MAP_NAMES[route[n - 2][1]]}")
            if n < len(route) and route[n][1] != map_no:
                changes.append(f"to {MAP_NAMES[route[n][1]]}")
            if changes:
                label = c.create_text(
                    sx - off + _STEP_SIZE / 2 + 4,
                    sy - off,
                    text=", ".join(changes),
                    anchor=tk.W,
                    fill=_ROUTE_COLOR,
                    font=_TAG_FONT,
                )
                x0, y0, x1, y1 = c.bbox(label)
                box = c.create_rectangle(
                    x0 - 3, y0 - 1, x1 + 3, y1 + 1, fill="#16161c", outline=""
                )
                c.tag_lower(box, label)
                self._items[label] = ("step", (pin, step))

    def _object_done(self, obj: MapObject) -> bool | None:
        """Pool activated / imp seal opened; None without a character."""
        if self._grace_state is None:
            return None
        return bool(self._grace_state(obj.flag_id))

    def _draw_painting_line(self, pin: _Pin):
        """Dashed line from where the painting lies to its vista."""
        p = pin.painting.painting
        if p.position is None:
            return
        point = _spot_point(
            p.map_id, p.position[0], p.position[2], self._images.convergence
        )
        if point is None or point[0] != self._map_no:
            return
        c = self._canvas
        sx, sy = self._to_screen(point[1], point[2])
        c.create_line(
            sx,
            sy,
            *self._to_screen(*pin.point),
            fill=_ROUTE_COLOR,
            width=2,
            dash=(6, 4),
        )
        c.create_image(sx, sy, image=self._icons.step(0, _STEP_SIZE - 4, False))

    def _boss_defeated(self, boss: BossSpot) -> bool | None:
        if self._grace_state is None:
            return None
        return self._grace_state(boss.flags[0])

    def _pin_text(self, pin: _Pin) -> str:
        if pin.obj is not None:
            pool = pin.obj.kind == POOL
            lines = ["Summoning Pool" if pool else "Imp Seal"]
            if not pool:
                lines.append(count_phrase(pin.obj.keys, "Stonesword Key"))
            grace = self._nearest_grace(pin.map_no, pin.point)
            if grace is not None:
                lines.append(grace.loc.name)
            done = self._object_done(pin.obj)
            if done is not None:
                lines.append(
                    ("Activated" if done else "Not activated")
                    if pool
                    else ("Opened" if done else "Sealed")
                )
            return "\n".join(lines)
        if pin.painting is not None:
            pt = pin.painting
            lines = [pt.painting.item_label, f"Vista reward: {pt.reward.item_label}"]
            found = self._pickup_collected(pt.painting)
            solved = self._pickup_collected(pt.reward)
            if found is not None:
                lines.append("Painting found" if found else "Painting not found")
                lines.append("Solved" if solved else "Not solved")
            return "\n".join(lines)
        if pin.pickup is not None:
            p = pin.pickup
            lines = [p.item_label, SOURCE_LABELS.get(p.source, p.source)]
            taken = self._pickup_collected(p)
            if taken is not None:
                lines.append("Collected" if taken else "Not collected")
            return "\n".join(lines)
        if pin.merchant is not None:
            m = pin.merchant
            lines = [m.name, f"Merchant, {len(m.lineup)} items"]
            if self._grace_state is not None:
                out = sum(
                    1
                    for i in m.lineup
                    if i.limited and i.bought(self._grace_state) >= i.quantity
                )
                if out:
                    lines.append(f"{out} sold out")
            return "\n".join(lines)
        if pin.boss is not None:
            b = pin.boss
            lines = [b.name, f"Boss  {b.region}"]
            defeated = self._boss_defeated(b)
            if defeated is not None:
                lines.append("Defeated" if defeated else "Alive")
            return "\n".join(lines)
        lines = []
        for spot in pin.npcs:
            line = spot.name if spot.name == spot.npc else f"{spot.name} ({spot.npc})"
            state = ", dead" if spot.dead else ", hostile" if spot.hostile else ""
            lines.append(line + state)
        return "\n".join(lines)

    def _tile_at(self, mx: float, my: float, fallback: bool = False) -> _Placed | None:
        """Small overworld tile under a map point, if it is a teleport target.
        In Pins mode only as the fallback for a click without floor."""
        if (
            self._map_no == MAP_UNDERGROUND
            or (self._click_target.get() != _TARGET_TILES and not fallback)
            or self._click_mode.get() != _MODE_SELECT
        ):
            return None
        gx, gz = map_to_global(mx, my)
        area = 61 if self._map_no == MAP_REALM_OF_SHADOW else 60
        key = f"m{area}_{int(gx // 256):02d}_{int(gz // 256):02d}_00"
        return self._tiles.get(key)

    def _clear_hover(self):
        self._canvas.delete("hover")
        self._hover_tile = None

    def _show_hover(self, sx: int, sy: int, hit):
        """Outline the tile under the cursor and show a tooltip."""
        c = self._canvas
        c.delete("hover")
        text = None
        icons: list[str] = []
        if hit is not None:
            self._hover_tile = None
            kind, obj = hit
            if kind == "loc":
                text = self._location_text(obj)
                lines, icons = self._overview(obj)
                text = "\n".join([text, *lines])
            elif kind == "bloodstain":
                text = f"Bloodstain\n{obj[3]}"
            elif kind == "pin":
                text = self._pin_text(obj)
            elif kind == "step":
                step = obj[1]
                state = "Reached" if self._step_done(step) else "Not reached"
                text = (
                    f"{step.quest}, step {step.index + 1}\n{step.description}\n{state}"
                )
            else:
                text = (
                    "Beacon" if obj.kind == BEACON else f"Map marker, icon {obj.icon}"
                )
        else:
            tile = self._tile_at(*self._to_map(sx, sy))
            self._hover_tile = tile
            if tile is not None:
                x0, y0 = self._to_screen(tile.rect[0], tile.rect[1])
                x1, y1 = self._to_screen(tile.rect[2], tile.rect[3])
                c.create_rectangle(
                    x0, y0, x1, y1, outline=_HOVER_COLOR, width=2, tags="hover"
                )
                text = self._location_text(tile)
                lines, icons = self._overview(tile)
                text = "\n".join([text, *lines])
        if text:
            tx, ty = sx + 16, sy + 14
            label = c.create_text(
                tx + 6,
                ty + 4,
                text=text,
                anchor=tk.NW,
                fill="#f0f0f0",
                font=("Inter", 10),
                tags="hover",
            )
            x0, y0, x1, y1 = c.bbox(label)
            photos = [p for p in (self._item_photo(n, _HOVER_ICON) for n in icons) if p]
            if photos:
                step = _HOVER_ICON + 4
                for n, photo in enumerate(photos):
                    c.create_image(
                        x0 + n * step,
                        y1 + 4,
                        image=photo,
                        anchor=tk.NW,
                        tags=("hover", "hover_icon"),
                    )
                x1 = max(x1, x0 + len(photos) * step - 4)
                y1 += step + 2
            w, h = self._canvas_size()
            dx = min(0, w - x1 - 4)
            dy = min(0, h - y1 - 4)
            c.move(label, dx, dy)
            c.move("hover_icon", dx, dy)
            box = c.create_rectangle(
                x0 - 6 + dx,
                y0 - 4 + dy,
                x1 + 6 + dx,
                y1 + 4 + dy,
                fill="#1e1e2a",
                outline="#55556a",
                tags="hover",
            )
            c.tag_lower(box, label)
            c.tag_raise("hover_icon")

    def _overview(self, placed: _Placed) -> tuple[list[str], list[str]]:
        """Tooltip lines and item icon names for a location: its region's
        completion, pickups whose nearest grace is the grace (or that lie in the
        dungeon's or tile's map) and NPCs standing there, each only while
        its layer is shown."""
        loc = placed.loc
        lines: list[str] = []
        icons: list[str] = []
        region = self._placed_region(placed)
        categories = self._completion().get(region) if region else None
        if categories:
            lines.append(f"{region}: {self._percent(categories)}% done")
        if self._show_pickups.get():
            by_grace, by_map = _pickups_by_place(self._images.convergence)
            if loc.tile_type == "grace":
                rows = by_grace.get(loc.flag_id, [])
            else:
                rows = by_map.get(loc.map_id_str, [])
            if rows and self._grace_state is not None:
                left = [p for p in rows if not self._pickup_collected(p)]
                lines.append(f"Pickups nearby: {len(left)} of {len(rows)} left")
                icons = [p.items[0][2] for p in left[:_HOVER_ICONS]]
            elif rows:
                lines.append(f"Pickups nearby: {len(rows)}")
                icons = [p.items[0][2] for p in rows[:_HOVER_ICONS]]
        if self._show_npcs.get():
            names = sorted({s.name for pin in self._npcs_at(placed) for s in pin.npcs})
            if names:
                lines.append("NPCs here: " + ", ".join(names))
        return lines, icons

    def _npcs_at(self, placed: _Placed) -> list[_Pin]:
        """NPC pins whose nearest grace on the map is this grace, or that
        stand in the dungeon's or tile's map."""
        pins = self._npc_pins()
        loc = placed.loc
        if loc.tile_type != "grace" or placed.point is None:
            return [p for p in pins if any(s.map_id == loc.map_id_str for s in p.npcs)]
        graces = [
            g
            for g in self._placed
            if g.loc.tile_type == "grace"
            and g.map_no == placed.map_no
            and g.point is not None
        ]

        def nearest(pin: _Pin) -> _Placed:
            return min(
                graces,
                key=lambda g: (g.point[0] - pin.point[0]) ** 2
                + (g.point[1] - pin.point[1]) ** 2,
            )

        return [p for p in pins if nearest(p) is placed]

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    @staticmethod
    def _grace_region(loc: MapLocation) -> str:
        """Region of a grace: its name before " - ", or the whole name."""
        return loc.name.partition(" - ")[0]

    @staticmethod
    def _grace_short(loc: MapLocation) -> str:
        """Grace name without its region."""
        return loc.name.partition(" - ")[2] or loc.name

    def _nearest_grace(self, map_no: int, point: tuple[float, float]) -> _Placed | None:
        graces = self._graces_by_map.get(map_no)
        if not graces:
            return None
        return min(
            graces,
            key=lambda g: (g.point[0] - point[0]) ** 2 + (g.point[1] - point[1]) ** 2,
        )

    def _region_at(self, map_no: int, point: tuple[float, float]) -> str | None:
        """Region of the nearest grace on the map."""
        g = self._nearest_grace(map_no, point)
        return self._grace_region(g.loc) if g else None

    def _placed_region(self, placed: _Placed) -> str | None:
        if placed.loc.tile_type == "grace":
            return self._grace_region(placed.loc)
        if placed.point is not None:
            return self._region_at(placed.map_no, placed.point)
        x0, y0, x1, y1 = placed.rect
        return self._region_at(placed.map_no, ((x0 + x1) / 2, (y0 + y1) / 2))

    def _completion(self) -> dict[str, dict[str, tuple[list, list]]]:
        """Region -> category -> (done, left), each a list of (label, target)
        where target is the pin or location to show (a Pickup for pickups
        without a map position). Empty without a character."""
        if self._grace_state is None:
            return {}
        if self._completion_cache is not None:
            return self._completion_cache
        state = self._grace_state
        out: dict[str, dict[str, tuple[list, list]]] = {}

        def add(region: str | None, category: str, label: str, target, done):
            entry = out.setdefault(region or "Other", {}).setdefault(category, ([], []))
            entry[0 if done else 1].append((label, target))

        graces = {
            g.loc.flag_id: g
            for g in self._placed
            if g.loc.tile_type == "grace" and g.loc.flag_id
        }
        pins = {p.pickup.flag_id: p for p in self._pickup_pins}
        for p in get_pickups(self._images.convergence):
            grace = graces.get(p.grace_flag)
            pin = pins.get(p.flag_id)
            if grace is not None:
                region = self._grace_region(grace.loc)
                label = f"{p.item_label} ({self._grace_short(grace.loc)})"
            else:
                region = self._region_at(pin.map_no, pin.point) if pin else None
                label = p.item_label
            add(region, _DONE_PICKUPS, label, pin or p, self._pickup_collected(p))
        for pin in self._boss_pins:
            add(
                self._region_at(pin.map_no, pin.point) or pin.boss.region,
                _DONE_BOSSES,
                pin.boss.name,
                pin,
                self._boss_defeated(pin.boss),
            )
        for g in graces.values():
            add(
                self._grace_region(g.loc),
                _DONE_GRACES,
                self._grace_short(g.loc),
                g,
                state(g.loc.flag_id),
            )
        for pin in self._object_pins:
            pool = pin.obj.kind == POOL
            if pool and not self._pools_available:
                continue
            grace = self._nearest_grace(pin.map_no, pin.point)
            add(
                self._grace_region(grace.loc) if grace else None,
                _DONE_POOLS if pool else _DONE_SEALS,
                (f"Near {self._grace_short(grace.loc)}" if grace else pin.obj.map_id)
                + ("" if pool or pin.obj.keys < 2 else f" ({pin.obj.keys} keys)"),
                pin,
                self._object_done(pin.obj),
            )
        for pin in self._painting_pins:
            pt = pin.painting
            add(
                self._region_at(pin.map_no, pin.point),
                _DONE_PAINTINGS,
                f"{pt.painting.item_label}: {pt.reward.item_label}",
                pin,
                self._pickup_collected(pt.reward),
            )
        self._completion_cache = out
        return out

    @staticmethod
    def _percent(categories: dict[str, tuple[list, list]]) -> int:
        done = sum(len(d) for d, _left in categories.values())
        total = done + sum(len(left) for _d, left in categories.values())
        return done * 100 // total if total else 0

    def _bar_photo(self, pct: int) -> ImageTk.PhotoImage:
        key = ("bar", pct)
        if key not in self._item_photos:
            self._item_photos[key] = ImageTk.PhotoImage(_bar_image(pct))
        return self._item_photos[key]

    def _fill_done_list(self, query: str):
        tree = self._loc_list
        tree.delete(*tree.get_children())
        comp = self._completion()
        if not comp:
            self._list_rows = []
            tree.insert(
                "", "end", iid="r:none", text="Load a character to see completion"
            )
            return
        regions = sorted(r for r in comp if not query or query in r.lower())
        self._list_rows = regions
        for n, region in enumerate(regions):
            pct = self._percent(comp[region])
            tree.insert(
                "",
                "end",
                iid=str(n),
                text=f"  {region}  {pct}%",
                image=self._bar_photo(pct),
            )

    def _select_region(self, region: str):
        """Region panel and a view that fits the region's graces."""
        self._selected_region = region
        self._selected_pin = None
        self._selected_loc = None
        self._pins = []
        by_map: dict[int, list[_Placed]] = {}
        for g in self._placed:
            if (
                g.loc.tile_type == "grace"
                and g.point
                and self._grace_region(g.loc) == region
            ):
                by_map.setdefault(g.map_no, []).append(g)
        if by_map:
            map_no, graces = max(by_map.items(), key=lambda kv: len(kv[1]))
            self._show_map(map_no)
            xs = [g.point[0] for g in graces]
            ys = [g.point[1] for g in graces]
            w, h = self._canvas_size()
            span = max(max(xs) - min(xs), max(ys) - min(ys), 200.0) * 1.3
            zoom = min(w, h) / span
            self._center_on((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, zoom)
        self._update_location_info()
        self._schedule_render()

    def _show_region_info(self, region: str):
        self._teleport_btn.configure(state="disabled")
        self._area_btn.configure(state="disabled")
        self._grace_row.pack_forget()
        self._floor_frame.pack_forget()
        self._pin_btn.pack_forget()
        self._show_pin_icons([])
        comp = self._completion()
        if not comp:
            self._info_var.set(f"{region}\nLoad a character to see what is left.")
            self._detail.pack_forget()
            return
        categories = comp.get(region, {})
        self._info_var.set(f"{region}\n{self._percent(categories)}% done")
        frame = self._detail
        for child in frame.winfo_children():
            child.destroy()
        self._detail_rows = []
        for category in _DONE_CATEGORIES:
            if category not in categories:
                continue
            done, left = categories[category]
            total = len(done) + len(left)
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill=tk.X)
            ctk.CTkLabel(row, text=category, font=ds.SMALL, anchor="w").pack(
                side=tk.LEFT
            )
            ctk.CTkLabel(
                row,
                text=f"{len(done)}/{total}",
                font=ds.SMALL,
                text_color=ds.FOUND if not left else ds.MUTED,
            ).pack(side=tk.RIGHT)
            bar = ctk.CTkProgressBar(frame, height=6)
            bar.set(len(done) / total)
            bar.pack(fill=tk.X, pady=(0, 4))
        ctk.CTkLabel(frame, text=f"Left in {region}", font=ds.BOLD, anchor="w").pack(
            fill=tk.X, pady=(6, 2)
        )
        box, tree = ds.themed_tree(
            frame, show="tree", selectmode="browse", height=_REGION_LEFT_ROWS
        )
        tree.column("#0", width=280, stretch=True)
        rows = [
            (category, label, target)
            for category in _DONE_CATEGORIES
            for label, target in categories.get(category, ([], []))[1]
        ]
        for n, (category, label, _target) in enumerate(rows):
            tree.insert(
                "", "end", iid=str(n), text=f"{_LEFT_LABELS[category]}: {label}"
            )
        if not rows:
            tree.insert("", "end", iid="none", text="Nothing left")
        box.pack(fill=tk.X)
        bind_mousewheel(tree)
        self._detail_rows = rows
        self._detail_tree = tree
        tree.bind("<<TreeviewSelect>>", lambda _e: self._on_left_selected())
        self._row_tips(tree, lambda iid: tree.item(iid, "text"))
        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(fill=tk.X, pady=(6, 0))
        ds.button(
            buttons, "Show On Map", self._show_region_layers, primary=False, width=140
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ds.button(
            buttons,
            "Export Region",
            lambda: self._export_checklist(region),
            primary=False,
            width=140,
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))
        frame.pack(fill=tk.X, padx=12, pady=(0, 6), after=self._unlock_row)

    def _on_left_selected(self):
        """Center the map on the chosen left entry."""
        sel = self._detail_tree.selection()
        if not sel or sel[0] == "none":
            return
        _category, _label, target = self._detail_rows[int(sel[0])]
        if not isinstance(target, (_Pin, _Placed)):
            return
        self._show_map(target.map_no)
        self._show_layer_of(target)
        self._center_on(*target.point, max(self._zoom, self._fit_zoom() * 4))
        self._schedule_render()

    def _show_layer_of(self, target: _Pin | _Placed):
        if isinstance(target, _Placed):
            self._show_graces.set(True)
        elif target.obj is not None:
            (self._show_pools if target.obj.kind == POOL else self._show_seals).set(
                True
            )
        elif target.painting is not None:
            self._show_paintings.set(True)
        elif target.boss is not None:
            self._show_bosses.set(True)
        elif target.pickup is not None:
            self._show_pickups.set(True)

    def _show_region_layers(self):
        """Turn on every layer that has something left in the region."""
        region = self._selected_region
        if region is None:
            return
        for category, (_done, left) in self._completion().get(region, {}).items():
            if left:
                {
                    _DONE_PICKUPS: self._show_pickups,
                    _DONE_BOSSES: self._show_bosses,
                    _DONE_GRACES: self._show_graces,
                    _DONE_POOLS: self._show_pools,
                    _DONE_SEALS: self._show_seals,
                    _DONE_PAINTINGS: self._show_paintings,
                }[category].set(True)
        self._select_region(region)

    def _export_checklist(self, region: str | None = None):
        """Export dialog: which regions (all, or the given one), which
        categories, and whether finished entries are listed too."""
        comp = self._completion()
        if not comp:
            CTkMessageBox.showinfo(
                "No Character",
                "Load a character in the World State tab first.",
                parent=self._win,
            )
            return
        dlg = ctk.CTkToplevel(self._win)
        dlg.title("Export Progress")
        dlg.transient(self._win)
        style_window_frame(dlg)
        body = ctk.CTkFrame(dlg, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=14)
        ds.header(body, "Export Progress", font=ds.TITLE)
        ctk.CTkLabel(
            body,
            text="A text file with each chosen region's progress.",
            font=ds.SMALL,
            text_color=ds.MUTED,
            anchor="w",
        ).pack(fill=tk.X, pady=(2, 8))

        columns = ctk.CTkFrame(body, fg_color="transparent")
        columns.pack(fill=tk.BOTH, expand=True)
        left = ctk.CTkFrame(columns, fg_color="transparent")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        ctk.CTkLabel(left, text="Regions", font=ds.BOLD, anchor="w").pack(fill=tk.X)
        regions = sorted(comp)
        region_vars = {
            r: tk.BooleanVar(value=region is None or r == region) for r in regions
        }
        listing = ctk.CTkScrollableFrame(left, width=260, height=300)
        listing.pack(fill=tk.BOTH, expand=True, pady=(4, 4))
        for r in regions:
            ctk.CTkCheckBox(
                listing,
                text=f"{r}  {self._percent(comp[r])}%",
                variable=region_vars[r],
                font=ds.SMALL,
            ).pack(anchor="w", pady=1)
        row = ctk.CTkFrame(left, fg_color="transparent")
        row.pack(fill=tk.X)

        def set_all(state: bool):
            for v in region_vars.values():
                v.set(state)

        ds.button(row, "Select All", lambda: set_all(True), primary=False).pack(
            side=tk.LEFT
        )
        ds.button(row, "Select None", lambda: set_all(False), primary=False).pack(
            side=tk.LEFT, padx=6
        )

        right = ctk.CTkFrame(columns, fg_color="transparent")
        right.pack(side=tk.LEFT, fill=tk.Y)
        ctk.CTkLabel(right, text="Include", font=ds.BOLD, anchor="w").pack(fill=tk.X)
        categories = [
            c for c in _DONE_CATEGORIES if c != _DONE_POOLS or self._pools_available
        ]
        category_vars = {c: tk.BooleanVar(value=True) for c in categories}
        for c in categories:
            ctk.CTkCheckBox(
                right, text=c, variable=category_vars[c], font=ds.SMALL
            ).pack(anchor="w", pady=2)
        done_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            right,
            text="Finished entries too",
            variable=done_var,
            font=ds.SMALL,
        ).pack(anchor="w", pady=(10, 2))
        if self._pickup_types != set(_PICKUP_TYPES):
            ds.wrap_to_width(
                ctk.CTkLabel(
                    right,
                    text="Items: only the pickup types picked under Types.",
                    font=ds.SMALL,
                    text_color=ds.MUTED,
                    anchor="w",
                    justify=tk.LEFT,
                )
            ).pack(fill=tk.X, pady=(8, 0))

        def export():
            chosen = [r for r in regions if region_vars[r].get()]
            cats = [c for c in categories if category_vars[c].get()]
            if not chosen or not cats:
                CTkMessageBox.showinfo(
                    "Nothing to Export",
                    "Pick at least one region and one category.",
                    parent=dlg,
                )
                return
            character = self._char_combo.get() or "Character"
            what = chosen[0] if len(chosen) == 1 else "progress"
            path = pick_file(
                "Export Progress",
                filetypes=[("Text", "*.txt")],
                save=True,
                defaultextension=".txt",
                initialfile=f"{character} {what}.txt",
            )
            if not path:
                return
            text = self._progress_text(character, chosen, cats, done_var.get())
            try:
                Path(path).write_text(text, encoding="utf-8")
            except OSError as e:
                CTkMessageBox.showerror("Export Failed", str(e), parent=dlg)
                return
            dlg.destroy()
            CTkMessageBox.showinfo(
                "Progress Exported", f"Saved to {path}", parent=self._win
            )

        ds.button_row(
            body,
            [
                {"text": "Cancel", "command": dlg.destroy, "primary": False},
                {"text": "Export...", "command": export},
            ],
        )
        center_window(dlg, 640, 520, parent=self._win)
        dlg.grab_set()

    def _progress_text(
        self,
        character: str,
        regions: list[str],
        categories: list[str],
        with_done: bool,
    ) -> str:
        """Plain text progress: per region its percentage, per category the
        count and what is left ([ ]), plus what is done ([x]) when asked."""
        comp = self._completion()
        lines = [f"{character}: Elden Ring progress", ""]
        if _DONE_PICKUPS in categories and self._pickup_types != set(_PICKUP_TYPES):
            types = ", ".join(t for t in _PICKUP_TYPES if t in self._pickup_types)
            lines += [f"Item types: {types}", ""]
        for reg in regions:
            cats = comp.get(reg, {})
            lines.append(f"{reg} - {self._percent(cats)}% done")
            lines.append("=" * len(lines[-1]))
            for category in categories:
                if category not in cats:
                    continue
                done, left = cats[category]
                if category == _DONE_PICKUPS:
                    done, left = (
                        [
                            (label, t)
                            for label, t in rows
                            if self._pickup_kinds[
                                (t.pickup if isinstance(t, _Pin) else t).flag_id
                            ]
                            in self._pickup_types
                        ]
                        for rows in (done, left)
                    )
                total = len(done) + len(left)
                if not total:
                    continue
                lines.append(f"  {category}: {len(done)}/{total}")
                lines += [f"    [ ] {label}" for label, _t in left]
                if with_done:
                    lines += [f"    [x] {label}" for label, _t in done]
            lines.append("")
        return "\n".join(lines)

    def _location_text(self, placed: _Placed) -> str:
        loc = placed.loc
        lines = [
            loc.name,
            f"{_KIND_LABELS.get(loc.tile_type, loc.tile_type)}  {loc.map_id_str}",
        ]
        if loc.tile_type == "grace" and self._grace_state is not None and loc.flag_id:
            state = self._grace_state(loc.flag_id)
            if state is not None:
                lines.append("Unlocked" if state else "Locked")
        gate = self._gate_line(loc)
        if gate:
            lines.append(gate)
        return "\n".join(lines)

    def _gate_line(self, loc: MapLocation) -> str | None:
        """ "Appears after: <boss> (alive)" for a boss-gated location."""
        gate = location_gate(
            loc.tile_type, loc.map_id_str, loc.flag_id, self._images.convergence
        )
        if gate is None:
            return None
        if self._grace_state is None:
            return f"Appears after: {gate.boss or f'event flag {gate.flag_id}'}"
        return f"Appears after: {gate_status(gate, self._grace_state)}"

    def _draw_player(self):
        blood = self._bloodstain
        if blood is not None and blood[0] == self._map_no:
            bx, by = self._to_screen(blood[1], blood[2])
            item = self._canvas.create_image(
                bx, by, image=self._icons.bloodstain(30, blood[4] <= 0)
            )
            self._items[item] = ("bloodstain", blood)
        if not self._player or self._player[0] != self._map_no:
            return
        sx, sy = self._to_screen(self._player[1], self._player[2])
        self._canvas.create_image(sx, sy, image=self._icons.player(_PLAYER_SIZE))

    def _draw_pin(self):
        if not self._pins:
            return
        pin = self._pins[self._pin_var.get()]
        if pin.map_no != self._map_no:
            return
        sx, sy = self._to_screen(pin.mx, pin.my)
        r = 7
        c = self._canvas
        c.create_oval(sx - r, sy - r, sx + r, sy + r, outline=_SELECT_COLOR, width=3)
        c.create_line(sx, sy - r - 5, sx, sy + r + 5, fill=_SELECT_COLOR, width=2)
        c.create_line(sx - r - 5, sy, sx + r + 5, sy, fill=_SELECT_COLOR, width=2)

    def _draw_markers(self):
        if self._editor is None or not self._show_markers.get():
            return
        c = self._canvas
        self._marker_tags = {}
        for n, m in enumerate(self._editor.markers):
            if m.map != self._map_no:
                continue
            tag = f"marker{n}"
            self._marker_tags[id(m)] = tag
            sx, sy = self._to_screen(m.x, m.y)
            selected = m is self._selected_marker
            if m.kind == BEACON:
                # The pillar's tip marks the position; the ring surrounds the
                # whole pillar.
                if selected:
                    c.create_image(
                        sx,
                        sy - _BEACON_HEIGHT / 2,
                        image=self._icons.select_ring(_BEACON_HEIGHT),
                        tags=(tag, "select_ring"),
                    )
                item = c.create_image(
                    sx,
                    sy,
                    image=self._icons.beacon(_BEACON_HEIGHT),
                    anchor=tk.S,
                    tags=tag,
                )
            else:
                if selected:
                    c.create_image(
                        sx,
                        sy,
                        image=self._icons.select_ring(_MARKER_SIZE),
                        tags=(tag, "select_ring"),
                    )
                item = c.create_image(
                    sx, sy, image=self._icons.marker(m.icon, _MARKER_SIZE), tags=tag
                )
            self._items[item] = ("marker", m)

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

    def _hit(self, sx: int, sy: int) -> tuple[str, object] | None:
        found = None
        for item in reversed(
            self._canvas.find_overlapping(sx - 2, sy - 2, sx + 2, sy + 2)
        ):
            hit = self._items.get(item)
            if hit is None:
                continue
            if hit[0] == "marker":
                return hit
            if found is None:
                found = hit
        if found is None:
            pin = self._pickup_at(sx, sy)
            if pin is not None:
                found = ("pin", pin)
        if found is None:
            found = self._nearest_hit(sx, sy)
        return found

    def _nearest_hit(self, sx: int, sy: int) -> tuple[str, object] | None:
        """Marker, NPC, step or location whose icon center is nearest the
        point, within _SNAP_PX of its edge (crowded spots like Jarburg)."""
        c = self._canvas
        r = _SNAP_PX
        best, dist = None, None
        for item in c.find_overlapping(sx - r, sy - r, sx + r, sy + r):
            hit = self._items.get(item)
            if hit is None:
                continue
            x0, y0, x1, y1 = c.bbox(item)
            d = ((x0 + x1) / 2 - sx) ** 2 + ((y0 + y1) / 2 - sy) ** 2
            if dist is None or d < dist:
                best, dist = hit, d
        return best

    def _markers_editable(self) -> bool:
        return self._editor is not None and self._editor.supported

    def _on_press(self, event):
        self._press = (event.x, event.y)
        self._press_view = (self._vx, self._vy)
        self._dragging = False
        hit = self._hit(event.x, event.y)
        self._drag_marker = (
            hit[1] if hit and hit[0] == "marker" and self._markers_editable() else None
        )

    def _on_drag(self, event):
        if self._press is None:
            return
        dx, dy = event.x - self._press[0], event.y - self._press[1]
        if not self._dragging and math.hypot(dx, dy) < _DRAG_THRESHOLD:
            return
        if not self._dragging and self._drag_marker is not None:
            # Redraw once so the dragged marker shows as selected.
            self._selected_marker = self._drag_marker
            self._render()
        self._dragging = True
        self._canvas.delete("hover")
        if self._drag_marker is not None:
            marker = self._drag_marker
            old = self._to_screen(marker.x, marker.y)
            marker.x, marker.y = self._to_map(event.x, event.y)
            tag = self._marker_tags.get(id(marker))
            if tag is not None:
                self._canvas.move(tag, event.x - old[0], event.y - old[1])
        else:
            self._pan_to(
                self._press_view[0] - dx / self._zoom,
                self._press_view[1] - dy / self._zoom,
            )

    def _on_release(self, event):
        if self._press is None:
            return
        press, self._press = self._press, None
        if self._dragging:
            marker, self._drag_marker = self._drag_marker, None
            if marker is not None and self._editor is not None:
                self._editor.move(marker, marker.x, marker.y)
                self._refresh_marker_panel(select=marker)
            return
        hit = self._hit(*press)
        mode = self._click_mode.get()
        if hit and hit[0] == "marker":
            self._select_marker(hit[1])
        elif mode != _MODE_SELECT and self._markers_editable():
            kind = BEACON if mode == _MODE_BEACON else MARKER
            self._place_marker(*self._to_map(*press), kind)
        elif hit and hit[0] == "loc":
            self._select_location(hit[1])
        elif hit and hit[0] == "pin":
            self._select_pin(hit[1])
        elif hit and hit[0] == "step":
            self._select_step(hit[1][1])
        else:
            mx, my = self._to_map(*press)
            if self._click_target.get() == _TARGET_TILES:
                self._select_location(self._tile_at(mx, my))
            elif not self._place_pin(mx, my):
                self._select_location(self._tile_at(mx, my, fallback=True))

    def _on_pan_press(self, event):
        self._press = None
        self._pan_origin = (event.x, event.y, self._vx, self._vy)

    def _on_pan_drag(self, event):
        x, y, vx, vy = self._pan_origin
        self._canvas.delete("hover")
        self._pan_to(vx - (event.x - x) / self._zoom, vy - (event.y - y) / self._zoom)

    def _on_motion(self, event):
        hit = self._hit(event.x, event.y)
        self._show_hover(event.x, event.y, hit)
        if hit or self._hover_tile is not None:
            cursor = "hand2"
        elif (
            self._click_target.get() == _TARGET_PINS
            and self._click_mode.get() == _MODE_SELECT
        ):
            cursor = "crosshair"
        else:
            cursor = ""
        self._canvas.configure(cursor=cursor)

    def _on_target_switch(self, _value: str):
        if self._pins:
            self._select_location(None)
        self._clear_hover()

    # ------------------------------------------------------------------
    # Selection and teleport
    # ------------------------------------------------------------------

    def _on_map_switch(self, value: str):
        self._map_no = next(m for m in _MAP_ORDER if MAP_NAMES[m] == value)
        self._fit()
        self._schedule_render()
        if self._this_map_var.get():
            self._fill_location_list()

    def _show_map(self, map_no: int):
        if map_no != self._map_no:
            self._map_no = map_no
            self._map_switch.set(MAP_NAMES[map_no])
            self._fit()

    def _select_location(self, placed: _Placed | None):
        self._selected_loc = placed
        self._pins = []
        self._selected_pin = None
        self._selected_region = None
        self._update_location_info()
        self._schedule_render()

    def _select_pin(self, pin: _Pin):
        self._selected_pin = pin
        self._active_npc = None
        self._selected_loc = None
        self._selected_region = None
        self._pins = []
        self._update_location_info()
        self._schedule_render()

    def _show_pin_info(self, pin: _Pin):
        """Location panel for a selected pickup or NPC: what it is, and for
        world pickups a button that respawns or collects it."""
        self._teleport_btn.configure(state="disabled")
        self._area_btn.configure(state="disabled")
        self._grace_row.pack_forget()
        self._floor_frame.pack_forget()
        self._pin_btn.pack_forget()
        self._show_detail(pin)
        p = pin.pickup
        if pin.obj is not None:
            self._show_pin_icons([] if pin.obj.kind == POOL else [_SEAL_ICON])
            self._info_var.set(f"{self._pin_text(pin)}\n{pin.obj.map_id}")
            done = self._object_done(pin.obj)
            if done is None or self._on_set_flags is None:
                return
            if pin.obj.kind == POOL:
                text = "Deactivate" if done else "Activate"
            else:
                text = "Seal" if done else "Open"
            self._pin_btn.configure(text=text)
            self._pin_btn.pack(
                fill=tk.X, pady=(0, 6), padx=12, after=self._teleport_btn
            )
            return
        if pin.painting is not None:
            pt = pin.painting
            self._show_pin_icons(
                [pt.painting.items[0][2]] + [name for _, _, name in pt.reward.items]
            )
            self._info_var.set(f"{self._pin_text(pin)}\n{pt.reward.map_id}")
            solved = self._pickup_collected(pt.reward)
            if solved is None or self._on_set_pickup is None:
                return
            self._pin_btn.configure(text="Respawn Reward" if solved else "Mark Solved")
            self._pin_btn.pack(
                fill=tk.X, pady=(0, 6), padx=12, after=self._teleport_btn
            )
            return
        if pin.merchant is not None:
            self._show_pin_icons([])
            self._info_var.set(f"{self._pin_text(pin)}\n{pin.merchant.map_id}")
            return
        if pin.boss is not None:
            self._show_pin_icons([pin.boss.face] if pin.boss.face else [])
            self._info_var.set(f"{self._pin_text(pin)}\n{pin.boss.map_id}")
            defeated = self._boss_defeated(pin.boss)
            if defeated is None or self._on_set_flags is None:
                return
            self._pin_btn.configure(text="Respawn" if defeated else "Mark Defeated")
            self._pin_btn.pack(
                fill=tk.X, pady=(0, 6), padx=12, after=self._teleport_btn
            )
            return
        if p is None:
            self._show_pin_icons([])
            self._info_var.set(self._pin_text(pin) + "\nNPC")
            spot = self._npc_spot(pin)
            if self._on_set_flags is None or not (spot.dead or spot.hostile):
                return
            self._pin_btn.configure(text="Revive" if spot.dead else "Calm")
            self._pin_btn.pack(
                fill=tk.X, pady=(0, 6), padx=12, after=self._teleport_btn
            )
            return
        self._show_pin_icons([name for _id, _qty, name in p.items])
        self._info_var.set(f"{self._pin_text(pin)}\n{p.map_id}")
        taken = self._pickup_collected(p)
        if p.source != "pickup" or taken is None or self._on_set_pickup is None:
            return
        self._pin_btn.configure(text="Respawn" if taken else "Mark Collected")
        self._pin_btn.pack(fill=tk.X, pady=(0, 6), padx=12, after=self._teleport_btn)

    def _item_photo(self, name: str, size: int) -> ImageTk.PhotoImage | None:
        key = (name, size)
        if key not in self._item_photos:
            img = get_icon(name)
            self._item_photos[key] = (
                ImageTk.PhotoImage(_MapIcons._fit(img, size)) if img else None
            )
        return self._item_photos[key]

    def _show_detail(self, pin: _Pin):
        """Merchant lineup or NPC quest steps under the location info."""
        frame = self._detail
        for child in frame.winfo_children():
            child.destroy()
        self._detail_rows = []
        if pin.merchant is not None:
            self._build_lineup(frame, pin.merchant)
        elif pin.npcs is not None:
            npcs = list(dict.fromkeys(s.npc for s in pin.npcs))
            if len(npcs) > 1:
                # Several NPCs share the marker: pick whose quest to show
                ctk.CTkSegmentedButton(
                    frame,
                    values=npcs,
                    command=self._on_npc_chosen,
                    font=ds.SMALL,
                ).pack(fill=tk.X, pady=(0, 6))
                frame.winfo_children()[-1].set(self._npc_spot(pin).npc)
            base = self._npc_base(pin)
            steps = quest_steps(base, self._images.convergence) if base else ()
            if steps:
                self._build_quest(frame, pin, steps)
            else:
                ctk.CTkLabel(
                    frame,
                    text=f"No quest steps known for {self._npc_spot(pin).npc}.",
                    font=ds.SMALL,
                    text_color=ds.MUTED,
                    anchor="w",
                ).pack(fill=tk.X)
        else:
            frame.pack_forget()
            return
        frame.pack(fill=tk.X, padx=12, pady=(0, 6), after=self._unlock_row)

    @staticmethod
    def _row_tips(tree, text_of: Callable[[str], str]):
        """Full row text as a hover tooltip; the panel cuts long rows off."""
        tip = Tooltip(tree, "")
        shown = {"row": None}

        def motion(event):
            row = tree.identify_row(event.y)
            if row != shown["row"]:
                shown["row"] = row
                tip.show_text(text_of(row) if row else "")

        tree.bind("<Motion>", motion, add="+")

    def _on_npc_chosen(self, npc: str):
        self._active_npc = npc
        self._update_location_info()
        self._schedule_render()

    def _stock_text(self, item: ShopItem) -> str:
        state = self._grace_state
        if item.release_flag and state is not None and not state(item.release_flag):
            return "Not yet"
        if not item.limited:
            return "Unlimited"
        if state is None:
            return str(item.quantity)
        left = item.quantity - item.bought(state)
        return "Sold out" if left <= 0 else f"{left}/{item.quantity}"

    def _build_lineup(self, frame, merchant: Merchant):
        ctk.CTkLabel(frame, text="Inventory", font=ds.BOLD, anchor="w").pack(fill=tk.X)
        box, tree = ds.themed_tree(
            frame,
            columns=("price", "stock"),
            show="tree headings",
            selectmode="extended",
            height=7,
        )
        tree.heading("#0", text="Item")
        tree.heading("price", text="Price")
        tree.heading("stock", text="Stock")
        tree.column("#0", width=130, stretch=True)
        tree.column("price", width=56, anchor="e", stretch=False)
        tree.column("stock", width=78, anchor="e", stretch=False)
        for n, item in enumerate(merchant.lineup):
            price = f"{item.price:,}" if item.cost_type == RUNES else "Trade"
            tree.insert(
                "",
                "end",
                iid=str(n),
                text=item.name,
                values=(price, self._stock_text(item)),
            )
        box.pack(fill=tk.X, pady=(2, 4))
        bind_mousewheel(tree)
        self._row_tips(tree, lambda iid: merchant.lineup[int(iid)].name)
        self._detail_rows = list(merchant.lineup)
        self._detail_tree = tree
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill=tk.X)
        for text, command in (
            ("Restock", lambda: self._stock_action("restock")),
            ("Sold Out", lambda: self._stock_action("sold_out")),
            ("Restock All", lambda: self._stock_action("restock_all")),
        ):
            ds.button(row, text, command, primary=False, width=90).pack(
                side=tk.LEFT, padx=(0, 4)
            )

    def _stock_action(self, action: str):
        """Restock or sell out the chosen limited rows (all of the
        merchant's for restock_all), after a confirm."""
        pin = self._selected_pin
        if pin is None or pin.merchant is None or self._on_set_flags is None:
            return
        if action == "restock_all":
            items = [i for i in pin.merchant.lineup if i.limited]
        else:
            items = [
                self._detail_rows[int(iid)]
                for iid in self._detail_tree.selection()
                if self._detail_rows[int(iid)].limited
            ]
        if not items:
            CTkMessageBox.showinfo(
                "Nothing to Change",
                "Select limited items in the list; unlimited items have no stock.",
                parent=self._win,
            )
            return
        sold_out = action == "sold_out"
        what = count_phrase(len(items), "item")
        verb = "Mark {} sold out" if sold_out else "Restock {}"
        if not CTkMessageBox.askyesno(
            "Sold Out" if sold_out else "Restock",
            f"{verb.format(what)} at {pin.merchant.name}?\n\n"
            "A backup is made before saving.",
            parent=self._win,
        ):
            return
        changes: dict[int, bool] = {}
        for item in items:
            changes.update(item.counter_changes(item.quantity if sold_out else 0))
        self._on_set_flags(
            changes,
            "shop_sold_out" if sold_out else "shop_restock",
            f"{what} {'sold out' if sold_out else 'restocked'} at {pin.merchant.name}.",
            False,
        )

    def _build_quest(self, frame, pin: _Pin, steps: tuple[QuestStep, ...]):
        ctk.CTkLabel(frame, text="Quest", font=ds.BOLD, anchor="w").pack(fill=tk.X)
        tree = _QuestList(frame, self._on_step_selected)
        current = max(
            (n for n, st in enumerate(steps) if self._step_done(st)), default=-1
        )
        route = self._route(pin)
        moves = {id(st): n for n, (st, *_rest) in enumerate(route, start=1)}
        self._step_maps = {id(st): (m, x, y) for st, m, x, y in route}
        # Steps on another map than the NPC's marker say which
        here = pin.map_no
        for n, st in enumerate(steps):
            done = self._step_done(st)
            spot = self._step_maps.get(id(st))
            other = f" ({MAP_NAMES[spot[0]]})" if spot and spot[0] != here else ""
            tree.add(
                self._step_photo(moves.get(id(st), 0), done),
                f"{st.index + 1}. {st.description}{other}",
                done,
                n == current,
            )
        tree.finish()
        tree.box.pack(fill=tk.X, pady=(2, 4))
        self._detail_rows = list(steps)
        self._detail_tree = tree
        self._step_var = tk.StringVar(value="")
        ds.wrap_to_width(
            ctk.CTkLabel(
                frame,
                textvariable=self._step_var,
                font=ds.SMALL,
                anchor="w",
                justify=tk.LEFT,
            )
        ).pack(fill=tk.X)
        self._move_btn = ds.button(
            frame, "Move Here", self._move_to_step, primary=False, state="disabled"
        )
        self._move_btn.pack(fill=tk.X, pady=(4, 0))
        if current >= 0:
            tree.see(str(current))

    def _step_photo(self, number: int, done: bool) -> ImageTk.PhotoImage:
        """The map's numbered step pin for the quest list; blank for steps
        that do not move the NPC, so the text lines up."""
        if number:
            return self._icons.step(number, _LIST_ICON, done)
        key = ("blank", _LIST_ICON)
        if key not in self._item_photos:
            self._item_photos[key] = ImageTk.PhotoImage(
                Image.new("RGBA", (_LIST_ICON, _LIST_ICON))
            )
        return self._item_photos[key]

    def _on_step_selected(self):
        sel = self._detail_tree.selection()
        if not sel:
            return
        step = self._detail_rows[int(sel[0])]
        self._step_var.set(f"Location: {step.location}" if step.location else "")
        spot = self._step_maps.get(id(step))
        if spot is not None and spot[0] != self._map_no:
            # The step is on another map: show it there
            self._show_map(spot[0])
            self._center_on(spot[1], spot[2], max(self._zoom, self._fit_zoom() * 4))
            self._schedule_render()
        movable = bool(step.places) and self._on_set_flags is not None
        self._move_btn.configure(state="normal" if movable else "disabled")

    def _select_step(self, step: QuestStep):
        """Pick a step clicked on the map in the quest list."""
        if step in self._detail_rows:
            iid = str(self._detail_rows.index(step))
            self._detail_tree.selection_set(iid)
            self._detail_tree.see(iid)
            self._on_step_selected()

    def _move_to_step(self):
        """Apply the quest steps between the current one and the chosen one,
        which moves the NPC to that step's location."""
        pin = self._selected_pin
        sel = self._detail_tree.selection()
        if pin is None or not sel or self._on_set_flags is None:
            return
        target = self._detail_rows[int(sel[0])]
        table = [st for st in self._detail_rows if st.quest == target.quest]
        chain = steps_up_to(table, table.index(target), self._step_done)
        if not CTkMessageBox.askyesno(
            "Move NPC",
            f"Apply {count_phrase(len(chain), 'quest step')} of {target.quest} up to "
            f"step {target.index + 1}?\n\n{target.description}\n\n"
            "A backup is made before saving.",
            parent=self._win,
        ):
            return
        changes: dict[int, bool] = {}
        for st in chain:
            changes.update({flag_id: bool(value) for flag_id, value in st.flags})
        self._on_set_flags(
            changes,
            "quest_step",
            f"{target.quest}: applied {count_phrase(len(chain), 'step')}.",
            False,
        )

    def _show_pin_icons(self, names: list[str]):
        """Item icons for the selected pin: the first large, the rest small."""
        frame = self._pin_icons
        for child in frame.winfo_children():
            child.destroy()
        shown = 0
        for n, name in enumerate(names):
            img = get_icon(name)
            if img is None:
                continue
            size = _PANEL_ICON if n == 0 else _PANEL_ICON_SMALL
            img = _MapIcons._fit(img, size)
            ctk.CTkLabel(frame, text="", image=ctk.CTkImage(img, size=img.size)).pack(
                side=tk.LEFT, padx=(0, 6), anchor="s"
            )
            shown += 1
        if shown:
            frame.pack(fill=tk.X, padx=12, pady=(2, 4), before=self._info_label)
        else:
            frame.pack_forget()

    def _pin_action(self):
        """The selected pin's button: pickup collect / respawn, NPC calm /
        revive, boss kill / respawn. NPC and boss changes ask first."""
        pin = self._selected_pin
        if pin is None:
            return
        if pin.pickup is not None:
            self._toggle_pickup()
            return
        if pin.painting is not None:
            self._toggle_pickup(pin.painting.reward)
            return
        if self._on_set_flags is None or self._grace_state is None:
            return
        if pin.obj is not None:
            pool = pin.obj.kind == POOL
            done = bool(self._object_done(pin.obj))
            what = "summoning pool" if pool else "imp seal"
            if pool:
                verb, past = (
                    ("Deactivate", "deactivated") if done else ("Activate", "activated")
                )
            else:
                verb, past = ("Seal", "sealed") if done else ("Open", "opened")
            grace = self._nearest_grace(pin.map_no, pin.point)
            where = f" near {self._grace_short(grace.loc)}" if grace else ""
            if not CTkMessageBox.askyesno(
                f"{verb} {what.title()}",
                f"{verb} this {what}{where}?\n\nA backup is made before saving.",
                parent=self._win,
            ):
                return
            self._on_set_flags(
                {pin.obj.flag_id: not done},
                "pool" if pool else "imp_seal",
                f"{what.capitalize()}{where} {past}.",
                False,
            )
            return
        if pin.boss is not None:
            b = pin.boss
            defeated = bool(self._boss_defeated(b))
            if defeated:
                title = "Respawn Boss"
                text = (
                    f"Respawn {b.name}?\n\nThe character is moved to Roundtable "
                    "Hold so the boss's area loads fresh."
                )
            else:
                title = "Kill Boss"
                text = f"Mark {b.name} as defeated?"
            if not CTkMessageBox.askyesno(
                title, text + "\n\nA backup is made before saving.", parent=self._win
            ):
                return
            changes = dict.fromkeys(b.flags, not defeated)
            self._on_set_flags(
                changes,
                "respawn_boss" if defeated else "kill_boss",
                f"{b.name} {'respawned' if defeated else 'marked defeated'}.",
                defeated,
            )
            return
        spot = self._npc_spot(pin)
        npc = spot.npc.split(" / ")[0]
        acc = _FlagChanges(self._grace_state)
        if spot.dead:
            title, done = "Revive NPC", "revived"
            revive_npc(acc, npc)
        else:
            title, done = "Calm NPC", "calmed"
            calm_npc(acc, npc)
        if not CTkMessageBox.askyesno(
            title,
            f"{title.split()[0]} {spot.name}?\n\nA backup is made before saving.",
            parent=self._win,
        ):
            return
        operation = "revive_npc" if spot.dead else "calm_npc"
        self._on_set_flags(acc.changes, operation, f"{spot.name} {done}.", False)

    def _toggle_pickup(self, pickup: Pickup | None = None):
        """Collect or respawn the selected pickup (or the given one)."""
        pin = self._selected_pin
        if pickup is None and pin is not None:
            pickup = pin.pickup
        if pickup is None or self._on_set_pickup is None:
            return
        taken = self._pickup_collected(pickup)
        if taken is None:
            return
        self._on_set_pickup(pickup.flag_id, not taken)
        self._update_location_info()
        self._schedule_render()

    def _place_pin(self, mx: float, my: float) -> bool:
        """Pin the walkable floor nearest a clicked map point. False when there
        is none within reach."""
        radius = min(max(_PIN_PICK_PX / self._zoom, _PIN_RADIUS_MIN), _PIN_RADIUS_MAX)
        floors = floors_near(
            self._map_no, mx, my, self._images.convergence, radius=radius
        )
        if not floors:
            return False
        self._selected_loc = None
        self._selected_pin = None
        self._selected_region = None
        self._pins = floors
        self._pin_var.set(0)
        self._fill_floor_choices()
        self._update_location_info()
        self._schedule_render()
        return True

    def _fill_floor_choices(self):
        """One radio button per floor under the pin, top floor first."""
        for child in self._floor_frame.winfo_children():
            child.destroy()
        if len(self._pins) < 2:
            return
        several_maps = len({p.map_id_str for p in self._pins}) > 1
        ctk.CTkLabel(
            self._floor_frame, text="Floors here", font=ds.SMALL, anchor="w"
        ).pack(fill=tk.X)
        order = sorted(range(len(self._pins)), key=lambda k: -self._pins[k].y)
        for k in order:
            pin = self._pins[k]
            text = f"Height {pin.y:.1f}"
            if several_maps:
                text = f"{get_name_for_map_id(pin.map_id_str)}, height {pin.y:.1f}"
            ctk.CTkRadioButton(
                self._floor_frame,
                text=text,
                variable=self._pin_var,
                value=k,
                font=ds.SMALL,
                command=self._on_floor_chosen,
            ).pack(fill=tk.X, pady=2)

    def _on_floor_chosen(self):
        self._update_location_info()
        self._schedule_render()

    def _pin_info(self, pin: FloorPoint) -> str:
        lines = [
            get_name_for_map_id(pin.map_id_str),
            f"Map pin  {pin.map_id_str}",
            f"Position {pin.x:.1f}, {pin.y:.1f}, {pin.z:.1f}",
        ]
        gate = arena_gate(pin.arena_flag)
        if gate is not None:
            status = (
                gate_status(gate, self._grace_state)
                if self._grace_state is not None
                else gate.boss or f"event flag {gate.flag_id}"
            )
            lines.append(f"Boss arena: {status}")
        return "\n".join(lines)

    def _update_location_info(self):
        if self._selected_pin is not None:
            self._show_pin_info(self._selected_pin)
            return
        if self._selected_region is not None:
            self._show_region_info(self._selected_region)
            return
        self._pin_btn.pack_forget()
        self._show_pin_icons([])
        self._detail.pack_forget()
        if self._pins:
            self._info_var.set(self._pin_info(self._pins[self._pin_var.get()]))
            self._teleport_btn.configure(state="normal")
            self._area_btn.configure(state="disabled")
            self._grace_row.pack_forget()
            if len(self._pins) > 1:
                self._floor_frame.pack(
                    fill=tk.X, pady=(6, 0), padx=12, before=self._teleport_btn
                )
            else:
                self._floor_frame.pack_forget()
            return
        self._floor_frame.pack_forget()
        placed = self._selected_loc
        if placed is None:
            self._info_var.set(
                "Click anywhere on the map, or pick a grace or dungeon from the list"
            )
            self._teleport_btn.configure(state="disabled")
            self._area_btn.configure(state="disabled")
            self._grace_row.pack_forget()
            return
        loc = placed.loc
        area = self._area_of(placed)
        gate = self._gate_line(loc)
        self._info_var.set(
            f"{loc.name}\n{_KIND_LABELS.get(loc.tile_type, loc.tile_type)}  "
            f"{loc.map_id_str}"
            + (f"\nMap area: {area.name}" if area else "")
            + (f"\n{gate}" if gate else "")
        )
        self._area_btn.configure(state="normal" if area else "disabled")
        self._teleport_btn.configure(state="normal")
        state = None
        if loc.tile_type == "grace" and loc.flag_id and self._grace_state is not None:
            state = self._grace_state(loc.flag_id)
        if state is None:
            self._grace_row.pack_forget()
            return
        self._grace_var.set(f"Grace {'unlocked' if state else 'locked'}  ")
        self._grace_label.configure(text_color=ds.FOUND if state else ds.MUTED)
        self._grace_btn.configure(text="Lock" if state else "Unlock")
        self._grace_btn.pack(side=tk.RIGHT)
        self._grace_row.pack(fill=tk.X, pady=(0, 6), padx=12, after=self._teleport_btn)

    def _on_character_chosen(self, value: str):
        if self._on_select_slot is not None:
            self._on_select_slot(value)

    def _move_bloodstain(self):
        if self._on_move_bloodstain is None:
            CTkMessageBox.showinfo(
                "Bloodstain",
                "Load a character in the World State tab first.",
                parent=self._win,
            )
            return
        self._on_move_bloodstain()

    def _area_of(self, placed: _Placed) -> MapPiece | None:
        """Map fragment area a grace belongs to, or that holds a location."""
        if placed.loc.tile_type == "grace" and placed.loc.flag_id:
            flag_id = grace_piece(placed.loc.flag_id, self._images.convergence)
            piece = next((p for p in MAP_PIECES if p.flag_id == flag_id), None)
            if piece is not None and piece.map_no == placed.map_no:
                return piece
        if placed.point is not None:
            x, y = placed.point
        else:
            x0, y0, x1, y1 = placed.rect
            x, y = (x0 + x1) / 2, (y0 + y1) / 2
        return fragment_at(placed.map_no, x, y)

    def _graces_on_map(self, map_no: int, area: MapPiece | None = None) -> list[int]:
        return sorted(
            {
                p.loc.flag_id
                for p in self._placed
                if p.map_no == map_no
                and p.loc.tile_type == "grace"
                and p.loc.flag_id
                and (
                    area is None
                    or grace_piece(p.loc.flag_id, self._images.convergence)
                    == area.flag_id
                )
            }
        )

    def _unlock_area(self):
        placed = self._selected_loc
        area = self._area_of(placed) if placed is not None else None
        if area is None:
            return
        self._confirm_unlock(
            "Unlock Area",
            f"{area.name} area",
            [area],
            self._graces_on_map(area.map_no, area),
        )

    def _unlock_map(self):
        self._confirm_unlock(
            "Unlock Map",
            f"{MAP_NAMES[self._map_no]} map",
            pieces_on_map(self._map_no),
            self._graces_on_map(self._map_no),
        )

    def _confirm_unlock(
        self, title: str, what: str, pieces: list[MapPiece], graces: list[int]
    ):
        """Ask which of the map pieces to reveal and whether to unlock the
        graces with their play regions, then unlock.

        Only fragment pieces are listed; the others are added when every
        fragment is chosen. Graces are those inside the chosen pieces, or all
        of the given ones when no piece or every piece is chosen.
        """
        if self._grace_state is None or self._on_unlock is None:
            CTkMessageBox.showinfo(
                "No Character Loaded",
                "Load a character in the World State tab first.",
                parent=self._win,
            )
            return
        fragments = [p for p in pieces if p.fragment]
        others = [p.flag_id for p in pieces if not p.fragment]
        dialog = ds.create(self._win, title)
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        chosen: list[tuple[list[int], list[int]]] = []

        piece_vars = {p.flag_id: tk.BooleanVar(value=True) for p in fragments}
        grace_var = tk.BooleanVar(value=True)

        def picked() -> tuple[list[int], list[int]]:
            flags = [f for f, var in piece_vars.items() if var.get()]
            if len(flags) in (0, len(fragments)):
                scope = graces
            else:
                scope = sorted(
                    {
                        f
                        for p in fragments
                        if p.flag_id in flags
                        for f in self._graces_on_map(p.map_no, p)
                    }
                )
            if len(flags) == len(fragments):
                flags += others
            return flags, scope

        def refresh():
            flags, scope = picked()
            locked = sum(self._grace_state(f) is False for f in scope)
            where = (
                f"in the {what}"
                if len(flags) in (0, len(fragments) + len(others))
                else "in the chosen pieces"
            )
            if not scope:
                text = f"Unlock graces (none {where})"
            elif locked:
                text = f"Unlock {count_phrase(locked, 'grace')} {where}"
            else:
                text = (
                    f"Add missing play regions of {count_phrase(len(scope), 'grace')} "
                    + where
                )
            grace_box.configure(text=text, state="normal" if scope else "disabled")
            hidden = sum(self._grace_state(f) is False for f in flags)
            if hidden:
                summary = f"{count_phrase(hidden, 'map piece')} to reveal."
            elif flags:
                summary = "Already revealed; the fog under them is cleared again."
            else:
                summary = "No map pieces chosen."
            summary_var.set(summary)
            ok = bool(flags) or (grace_var.get() and bool(scope))
            unlock_btn.configure(state="normal" if ok else "disabled")

        def confirm():
            flags, scope = picked()
            chosen.append((scope if grace_var.get() else [], flags))
            dialog.destroy()

        _row, (_cancel, unlock_btn) = ds.button_row(
            main,
            [
                {"text": "Cancel", "command": dialog.destroy, "primary": False},
                {"text": "Unlock", "command": confirm},
            ],
        )
        ds.header(main, what[0].upper() + what[1:])

        ctk.CTkLabel(main, text="Map pieces", font=ds.BOLD, anchor="w").pack(
            fill=tk.X, pady=(10, 2)
        )

        def build_pieces(frame):
            for p in fragments:
                revealed = self._grace_state(p.flag_id)
                ctk.CTkCheckBox(
                    frame,
                    text=p.name + (" (revealed)" if revealed else ""),
                    variable=piece_vars[p.flag_id],
                    command=refresh,
                    font=ds.FONT,
                ).pack(anchor="w", pady=2)

        ds.content(main, build_pieces, max_height=320, fill=tk.X, expand=False)
        if len(fragments) > 1:
            all_row = ctk.CTkFrame(main, fg_color="transparent")
            all_row.pack(fill=tk.X, pady=(4, 0))

            def set_all(state: bool):
                for var in piece_vars.values():
                    var.set(state)
                refresh()

            ds.button(
                all_row, "All", lambda: set_all(True), primary=False, width=70
            ).pack(side=tk.LEFT, padx=(0, 6))
            ds.button(
                all_row, "None", lambda: set_all(False), primary=False, width=70
            ).pack(side=tk.LEFT)
        summary_var = tk.StringVar()
        ds.wrap_to_width(
            ctk.CTkLabel(
                main,
                textvariable=summary_var,
                font=ds.SMALL,
                text_color=ds.MUTED,
                anchor="w",
                justify=tk.LEFT,
            )
        ).pack(fill=tk.X, pady=(4, 0))

        ctk.CTkLabel(main, text="Graces", font=ds.BOLD, anchor="w").pack(
            fill=tk.X, pady=(12, 2)
        )
        grace_box = ctk.CTkCheckBox(
            main, text="", variable=grace_var, command=refresh, font=ds.FONT
        )
        grace_box.pack(anchor="w", pady=2)
        ctk.CTkLabel(
            main,
            text="Their play regions are added too.",
            font=ds.SMALL,
            text_color=ds.MUTED,
            anchor="w",
        ).pack(fill=tk.X)
        ctk.CTkLabel(
            main,
            text="A backup is made before saving.",
            font=ds.SMALL,
            text_color=ds.MUTED,
            anchor="w",
        ).pack(fill=tk.X, pady=(10, 0))

        refresh()
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        ds.finish(dialog, self._win, min_width=380)
        dialog.wait_window()
        if not chosen:
            return
        self._on_unlock(*chosen[0])
        self._update_location_info()
        self._schedule_render()

    def _toggle_grace(self):
        placed = self._selected_loc
        if placed is None or self._on_set_grace is None or self._grace_state is None:
            return
        state = self._grace_state(placed.loc.flag_id)
        if state is None:
            return
        if not state and self._on_unlock is not None:
            self._on_unlock([placed.loc.flag_id], [])
        else:
            self._on_set_grace(placed.loc.flag_id, not state)
        self._update_location_info()
        self._schedule_render()

    def _teleport(self):
        if self._pins:
            self._on_teleport(pin_location(self._pins[self._pin_var.get()]))
        elif self._selected_loc is not None:
            self._on_teleport(self._selected_loc.loc)

    # ------------------------------------------------------------------
    # Markers
    # ------------------------------------------------------------------

    @staticmethod
    def _marker_label(m: MapMarker) -> str:
        where = MAP_NAMES.get(m.map, f"Map {m.map}")
        return f"  {'Beacon' if m.kind == BEACON else 'Marker'}  -  {where}"

    def _refresh_marker_panel(self, select: MapMarker | None = None):
        editor = self._editor
        enabled = self._markers_editable()
        if editor is None:
            self._marker_status.set("Load a character in the World State tab.")
        elif not editor.supported:
            self._marker_status.set(
                "This character uses the older marker layout "
                f"(version {editor.layout_version}). The game converts it on "
                "its next save; markers can be edited after that."
            )
        else:
            changed = "  Unapplied changes." if editor.dirty else ""
            self._marker_status.set(
                f"{editor.count(MARKER)} / 100 markers, "
                f"{editor.count(BEACON)} / 10 beacons.{changed}"
            )
        for widget in self._iter_controls(self._marker_frame):
            widget.configure(state="normal" if enabled else "disabled")

        tree = self._marker_list
        self._syncing_list = True
        tree.delete(*tree.get_children())
        self._list_markers = list(editor.markers) if enabled else []
        for n, m in enumerate(self._list_markers):
            image = (
                self._icons.beacon(_LIST_ICON)
                if m.kind == BEACON
                else self._icons.marker(m.icon, _LIST_ICON)
            )
            tree.insert("", "end", iid=str(n), text=self._marker_label(m), image=image)
        target = select or self._selected_marker
        if target in self._list_markers:
            iid = str(self._list_markers.index(target))
            tree.selection_set(iid)
            tree.see(iid)
        self._win.after_idle(self._end_list_sync)

    def _end_list_sync(self):
        self._syncing_list = False

    def _iter_controls(self, widget):
        for child in widget.winfo_children():
            if isinstance(
                child, (ctk.CTkButton, ctk.CTkCheckBox, ctk.CTkSegmentedButton)
            ):
                yield child
            else:
                yield from self._iter_controls(child)

    def _on_list_select(self, _event=None):
        sel = self._marker_list.selection()
        if self._syncing_list or not sel:
            return
        marker = self._list_markers[int(sel[0])]
        self._selected_marker = marker
        if marker.map in _MAP_ORDER:
            self._show_map(marker.map)
            self._center_on(marker.x, marker.y, max(self._zoom, self._fit_zoom() * 3))
        if marker.kind == MARKER:
            self._icon = marker.icon
            self._highlight_icon()

    def _select_marker(self, marker: MapMarker):
        self._selected_marker = marker
        if marker.kind == MARKER:
            self._icon = marker.icon
            self._highlight_icon()
        self._refresh_marker_panel(select=marker)
        self._schedule_render()

    def _highlight_icon(self):
        for icon, button in self._icon_buttons.items():
            button.configure(
                fg_color=palette.PURPLE_SELECT if icon == self._icon else "transparent"
            )

    def _choose_icon(self, icon: int):
        """Icon for new markers; also changes the selected marker's icon."""
        self._icon = icon
        self._highlight_icon()
        m = self._selected_marker
        if self._editor is not None and m is not None and m.kind == MARKER:
            self._editor.set_icon(m, icon)
            self._refresh_marker_panel(select=m)
            self._schedule_render()

    def _place_marker(self, mx: float, my: float, kind: str = MARKER):
        marker = self._editor.add(mx, my, self._map_no, self._icon, kind)
        if marker is None:
            what = "10 beacon" if kind == BEACON else "100 marker"
            CTkMessageBox.showwarning(
                "Map Markers",
                f"All {what} records are in use. Delete one first.",
                parent=self._win,
            )
            return
        self._selected_marker = marker
        self._refresh_marker_panel(select=marker)
        self._schedule_render()

    def _delete_selected_marker(self):
        m = self._selected_marker
        if not self._markers_editable() or m is None or m not in self._editor.markers:
            return
        self._editor.delete(m)
        self._selected_marker = None
        self._refresh_marker_panel()
        self._schedule_render()

    def _clear_map(self):
        if not self._markers_editable():
            return
        if not CTkMessageBox.askyesno(
            "Clear Map",
            f"Remove every marker and beacon on the {MAP_NAMES[self._map_no]} map?",
            parent=self._win,
        ):
            return
        self._editor.clear(map_no=self._map_no)
        self._selected_marker = None
        self._refresh_marker_panel()
        self._schedule_render()

    def _clear_all(self):
        if not self._markers_editable():
            return
        if not CTkMessageBox.askyesno(
            "Clear All", "Remove every marker and beacon on all maps?", parent=self._win
        ):
            return
        self._editor.clear()
        self._selected_marker = None
        self._refresh_marker_panel()
        self._schedule_render()

    def _export(self):
        if self._markers_editable() and self._on_export_markers:
            self._on_export_markers(self._editor)

    def _import(self):
        if self._markers_editable() and self._on_import_markers:
            if self._on_import_markers(self._editor):
                self._selected_marker = None
                self._refresh_marker_panel()
                self._schedule_render()

    def _copy(self):
        if self._markers_editable() and self._on_copy_markers:
            self._on_copy_markers(self._editor.to_dict())

    def _apply(self):
        if not self._markers_editable() or self._on_apply_markers is None:
            return
        editor = self._on_apply_markers(self._editor)
        if editor is not None:
            self.set_marker_editor(editor)

    def _revert(self):
        if not self._markers_editable():
            return
        self._editor.revert()
        self._selected_marker = None
        self._refresh_marker_panel()
        self._schedule_render()

    # ------------------------------------------------------------------

    def _close(self):
        # Staged markers stay in the main window's unapplied-changes bar.
        MapWindow._instance = None
        self._win.destroy()


def open_map_window(
    parent, maps_dir: Path, locations: list[MapLocation], **kwargs
) -> MapWindow:
    """Open the map window, or update and focus the one already open."""
    window = MapWindow._instance
    if window is not None:
        try:
            if window._win.winfo_exists():
                window.set_locations(locations, kwargs.get("convergence", False))
                window.set_player(kwargs.get("player"))
                window.set_marker_editor(kwargs.get("marker_editor"))
                window.focus()
                return window
        except tk.TclError:
            pass
    return MapWindow(parent, maps_dir, locations, **kwargs)


def current_window() -> MapWindow | None:
    window = MapWindow._instance
    try:
        if window is not None and window._win.winfo_exists():
            return window
    except tk.TclError:
        pass
    return None
