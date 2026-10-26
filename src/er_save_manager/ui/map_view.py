"""World map window: teleport locations and map markers on the game's map."""

from __future__ import annotations

import json
import math
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageTk

from er_save_manager.data.floor_points import FloorPoint, floors_near, pin_location
from er_save_manager.data.grace_data import arena_gate, location_gate
from er_save_manager.data.locations import MapLocation, get_name_for_map_id
from er_save_manager.data.map_pieces import (
    MAP_PIECES,
    MapPiece,
    fragment_at,
    grace_piece,
    pieces_on_map,
)
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
from er_save_manager.ui.utils import (
    bind_mousewheel,
    center_window,
    patch_combo_scroll,
    style_window_frame,
)

_MAP_ORDER = (MAP_LANDS_BETWEEN, MAP_UNDERGROUND, MAP_REALM_OF_SHADOW)
# Opacity of the unrevealed-area art over a locked map fragment. The
# Underground's unrevealed art is black over an already dark map.
_PROGRESS_ALPHA = 0.65
_PROGRESS_ALPHA_BY_MAP = {MAP_UNDERGROUND: 0.4}
_ZOOM_MAX = 2.0  # screen pixels per map unit
_ZOOM_STEP = 1.2
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
_PLAYER_COLOR = "#00cfff"
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
_KIND_LABELS = {"grace": "Site of Grace", "dungeon": "Dungeon", "small": "Tile"}


@dataclass
class _Placed:
    loc: MapLocation
    map_no: int
    rect: tuple[float, float, float, float] | None = None
    point: tuple[float, float] | None = None
    icon: int | None = None  # dungeon map icon id


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

    def select_ring(self, icon_size: int) -> ImageTk.PhotoImage:
        """The game's map selection ring, sized so its rim (at 0.49 of the
        sprite's half width) clears an icon of icon_size by 3 px."""
        size = round((icon_size / 2 + 3) / 0.49 * 2)
        key = ("r", size)
        if key not in self._photos:
            img = self._select_ring.resize((size, size), Image.LANCZOS)
            self._photos[key] = ImageTk.PhotoImage(img)
        return self._photos[key]

    def ctk_sprite(self, name: str, size: int, dimmed: bool = False) -> ctk.CTkImage:
        img = self._fit(self._sprites[name], size)
        if dimmed:
            img = self._dimmed(img)
        return ctk.CTkImage(img, size=img.size)

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
        self._grace_state = grace_state
        self._on_set_grace = on_set_grace
        self._on_unlock = on_unlock
        # Dungeon map id -> WorldMapPointParam icon id of the nearest map point.
        self._dungeon_icons = meta["dungeon_icons"]
        self._place_locations(locations)
        self._hover_tile: _Placed | None = None
        self._list_rows: list[_Placed] = []
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
        self._tile_key: tuple[int, float, frozenset[int]] | None = None
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
        self._grace_state = grace_state
        self._on_set_grace = on_set_grace
        self._on_unlock = on_unlock
        self._update_location_info()
        self._schedule_render()

    def set_locations(self, locations: list[MapLocation], convergence: bool):
        """Teleport targets and map art of the save's flavor."""
        if convergence == self._images.convergence:
            return
        self._images.set_convergence(convergence)
        self._place_locations(locations)
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
        # Two groups that move onto separate lines when the window is narrow
        flow = ds.FlowRow(bar, gap=8)
        flow.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0), pady=8)
        pick = ctk.CTkFrame(flow, fg_color="transparent")
        toggles = ctk.CTkFrame(flow, fg_color="transparent")

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
            )
        ):
            ctk.CTkCheckBox(
                toggles,
                text=text,
                variable=var,
                command=self._schedule_render,
                font=ds.SMALL,
                width=20,
            ).pack(side=tk.LEFT, padx=(0 if i == 0 else 6, 4))
        flow.add(pick, toggles)

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

    def _build_side_panel(self, side):
        pad = {"padx": 12}

        ctk.CTkLabel(side, text="Location", font=ds.BOLD, anchor="w").pack(
            fill=tk.X, pady=(12, 2), **pad
        )
        self._info_var = tk.StringVar(value="")
        ctk.CTkLabel(
            side,
            textvariable=self._info_var,
            font=ds.SMALL,
            anchor="w",
            justify=tk.LEFT,
            wraplength=290,
        ).pack(fill=tk.X, **pad)
        self._floor_frame = ctk.CTkFrame(side, fg_color="transparent")
        self._teleport_btn = ds.button(
            side, "Teleport Here", self._teleport, state="disabled"
        )
        self._teleport_btn.pack(fill=tk.X, pady=(6, 4), **pad)

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
        ctk.CTkSegmentedButton(
            left,
            values=[_FILTER_ALL, _FILTER_GRACES, _FILTER_DUNGEONS, _FILTER_TILES],
            variable=self._filter_var,
            command=lambda _v: self._fill_location_list(),
            font=ds.SMALL,
        ).pack(fill=tk.X, pady=6, **pad)
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

    def _build_legend(self, parent):
        """Icon legend, packed at the bottom of parent."""
        legend = ctk.CTkFrame(parent, fg_color=ds.BOX, corner_radius=8)
        legend.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        ctk.CTkLabel(legend, text="Legend", font=ds.BOLD, anchor="w").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(6, 2)
        )
        dot = Image.new("RGBA", (20, 20))
        draw = ImageDraw.Draw(dot)
        draw.ellipse((3, 3, 17, 17), fill=_PLAYER_COLOR, outline="white", width=2)
        tile = Image.new("RGBA", (20, 20))
        ImageDraw.Draw(tile).rectangle((2, 2, 17, 17), outline="white", width=2)
        entries = (
            (ctk.CTkImage(dot, size=(20, 20)), "Character"),
            (self._icons.ctk_sprite("bloodstain", 22), "Bloodstain"),
            (self._icons.ctk_sprite("bloodstain", 22, dimmed=True), "No runes"),
            (self._icons.ctk_sprite("grace", 22), "Site of Grace"),
            (self._icons.ctk_sprite("grace", 22, dimmed=True), "Locked grace"),
            (self._icons.ctk_sprite("dungeon_4", 24), "Dungeon"),
            (ctk.CTkImage(tile, size=(20, 20)), "Tile (hover)"),
            (self._icons.ctk_marker(1, 22), "Map marker"),
            (self._icons.ctk_sprite("beacon", 24), "Beacon"),
        )
        for n, (image, text) in enumerate(entries):
            row, col = 1 + n // 2, (n % 2) * 2
            ctk.CTkLabel(legend, text="", image=image, width=26).grid(
                row=row, column=col, padx=(8, 2), pady=1
            )
            ctk.CTkLabel(legend, text=text, font=ds.SMALL, anchor="w").grid(
                row=row, column=col + 1, sticky="w", padx=(0, 6), pady=1
            )
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

    def _fill_location_list(self):
        query = self._search_var.get().strip().lower()
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

    def _on_location_list_select(self, _event=None):
        sel = self._loc_list.selection()
        if not sel:
            return
        if sel[0].startswith("r:"):
            self._loc_list.item(sel[0], open=not self._loc_list.item(sel[0], "open"))
            return
        placed = self._list_rows[int(sel[0])]
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
        self._schedule_render()

    def _schedule_render(self):
        if not self._render_pending:
            self._render_pending = True
            self._win.after_idle(self._update_view)

    def _update_view(self):
        """Redraw icons; rebuild map tiles only when zoom or map changed."""
        self._render_pending = False
        if not self._win.winfo_exists():
            return
        if self._tile_key != (self._map_no, self._zoom, self._locked_pieces()):
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
        self._tile_key = (self._map_no, self._zoom, self._locked_pieces())
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

    def _view_image(self, w: int, h: int, vx: float, vy: float) -> Image.Image:
        """The map in a w x h screen box whose top-left is map point (vx, vy)."""
        x0, y0, x1, y1 = self._images.bounds(self._map_no)
        levels = self._images.levels(self._map_no, self._tile_key[2])
        # Image pixels per screen pixel at full resolution; use the smallest
        # copy that still has at least one pixel per screen pixel.
        density = self._images.scale / self._zoom
        level = 0
        while level + 1 < len(levels) and density / 2 ** (level + 1) >= 1:
            level += 1
        src = levels[level]
        k = self._images.scale / 2**level
        out = Image.new("RGB", (w, h), _BACKGROUND)
        # Part of the screen box covered by the map, in map units
        ax0, ay0 = max(vx, x0), max(vy, y0)
        ax1, ay1 = min(vx + w / self._zoom, x1), min(vy + h / self._zoom, y1)
        if ax1 <= ax0 or ay1 <= ay0:
            return out
        sx0 = round((ax0 - vx) * self._zoom)
        sy0 = round((ay0 - vy) * self._zoom)
        sx1 = round((ax1 - vx) * self._zoom)
        sy1 = round((ay1 - vy) * self._zoom)
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
        return out

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
        if hit is not None:
            self._hover_tile = None
            kind, obj = hit
            if kind == "loc":
                text = self._location_text(obj)
            elif kind == "bloodstain":
                text = f"Bloodstain\n{obj[3]}"
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
            w, h = self._canvas_size()
            dx = min(0, w - x1 - 4)
            dy = min(0, h - y1 - 4)
            c.move(label, dx, dy)
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
        r = 7
        self._canvas.create_oval(
            sx - r, sy - r, sx + r, sy + r, fill=_PLAYER_COLOR, outline="white", width=2
        )

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
        return found

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
