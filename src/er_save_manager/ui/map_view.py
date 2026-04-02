"""Interactive map popout window - small tile selector."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import TYPE_CHECKING

import customtkinter as ctk
from PIL import Image, ImageTk

if TYPE_CHECKING:
    from er_save_manager.data.locations import MapLocation

# Native image resolution calibration
_IMG_W = 3584
_IMG_H = 4608

# Big tile grid bounds in native pixels (cols 8-14, rows 7-15)
_GRID_X0 = 0
_GRID_X1 = 3584
_GRID_Y0 = 0
_GRID_Y1 = 4608

_BIG_COL_MIN = 8
_BIG_COL_MAX = 14
_BIG_ROW_MIN = 7
_BIG_ROW_MAX = 15

_TILE_W = (_GRID_X1 - _GRID_X0) / (_BIG_COL_MAX - _BIG_COL_MIN + 1)
_TILE_H = (_GRID_Y1 - _GRID_Y0) / (_BIG_ROW_MAX - _BIG_ROW_MIN + 1)
_SMALL_W = _TILE_W / 4
_SMALL_H = _TILE_H / 4

_ZOOM_MIN = 0.1
_ZOOM_MAX = 2.0
_ZOOM_STEP = 0.15


def _small_tile_native_rect(col: int, row: int) -> tuple[float, float, float, float]:
    """Return (x0, y0, x1, y1) in native image pixels for a m60_col_row_00 tile."""
    big_col = col // 4
    big_row = row // 4
    frac_col = col % 4
    frac_row = row % 4
    x0 = _GRID_X0 + (big_col - _BIG_COL_MIN) * _TILE_W + frac_col * _SMALL_W
    y0 = _GRID_Y0 + (_BIG_ROW_MAX - big_row) * _TILE_H + (3 - frac_row) * _SMALL_H
    return x0, y0, x0 + _SMALL_W, y0 + _SMALL_H


class MapWindow:
    """Toplevel popout window with the interactive map."""

    _instance: MapWindow | None = None

    def __init__(
        self,
        parent,
        locations: list[MapLocation],
        on_select: Callable[[MapLocation], None],
        map_image_path: str,
        current_map_id: str | None = None,
    ):
        if MapWindow._instance is not None:
            try:
                MapWindow._instance._win.focus()
                return
            except Exception:
                MapWindow._instance = None

        MapWindow._instance = self
        self._on_select = on_select
        self._selected: MapLocation | None = None
        self._hover_id: int | None = None
        self._rect_map: dict[int, MapLocation] = {}
        self._current_map_id = current_map_id
        self._scale = 1.0
        self._img_cache: ImageTk.PhotoImage | None = None
        self._player_item: int | None = None

        self._locations = [
            loc
            for loc in locations
            if loc.map_id_str.startswith("m60_") and loc.map_id_str.endswith("_00")
        ]

        # Precompute native rects once
        self._native_rects: dict[str, tuple[float, float, float, float]] = {}
        for loc in self._locations:
            parts = loc.map_id_str.split("_")
            col, row = int(parts[1]), int(parts[2])
            self._native_rects[loc.map_id_str] = _small_tile_native_rect(col, row)

        self._raw_image = Image.open(map_image_path)

        self._win = ctk.CTkToplevel(parent)
        self._win.title("Map - Teleport")
        self._win.protocol("WM_DELETE_WINDOW", self._close)

        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        win_w = int(sw * 0.88)
        win_h = int(sh * 0.88)
        x = (sw - win_w) // 2
        y = (sh - win_h) // 2
        self._win.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self._win.minsize(800, 600)

        self._build_ui()
        self._win.after(50, self._initial_render)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        info_bar = ctk.CTkFrame(self._win, corner_radius=0, height=44)
        info_bar.pack(fill=tk.X, side=tk.TOP)
        info_bar.pack_propagate(False)

        self._info_var = tk.StringVar(value="Click a tile to select it")
        ctk.CTkLabel(info_bar, textvariable=self._info_var, font=("Consolas", 11)).pack(
            side=tk.LEFT, padx=12, pady=8
        )

        self._teleport_btn = ctk.CTkButton(
            info_bar,
            text="Teleport",
            width=100,
            state="disabled",
            command=self._on_teleport,
        )
        self._teleport_btn.pack(side=tk.RIGHT, padx=12, pady=6)

        ctk.CTkButton(
            info_bar,
            text="Close",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._close,
        ).pack(side=tk.RIGHT, padx=(0, 6), pady=6)

        legend = ctk.CTkFrame(info_bar, fg_color="transparent")
        legend.pack(side=tk.RIGHT, padx=12)
        for color, label in [
            ("#00cfff", "You are here"),
            ("#ff6644", "Selected"),
            ("#00cc44", "Available"),
        ]:
            dot = tk.Canvas(legend, width=10, height=10, bg=color, highlightthickness=0)
            dot.pack(side=tk.LEFT, padx=(4, 2))
            ctk.CTkLabel(legend, text=label, font=("Segoe UI", 9)).pack(
                side=tk.LEFT, padx=(0, 8)
            )

        ctk.CTkLabel(
            info_bar,
            text="Ctrl+scroll to zoom",
            font=("Segoe UI", 9),
            text_color=("gray40", "gray60"),
        ).pack(side=tk.RIGHT, padx=(0, 12))

        canvas_frame = ctk.CTkFrame(self._win, fg_color="transparent")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._canvas = tk.Canvas(
            canvas_frame,
            xscrollcommand=h_scroll.set,
            yscrollcommand=v_scroll.set,
            highlightthickness=0,
            bg="#1a1a2e",
        )
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        h_scroll.config(command=self._canvas.xview)
        v_scroll.config(command=self._canvas.yview)

        self._canvas.bind("<ButtonPress-1>", self._on_click)
        self._canvas.bind("<Motion>", self._on_hover)
        self._canvas.bind("<Leave>", self._on_leave)
        self._canvas.bind("<Button-4>", self._on_scroll)
        self._canvas.bind("<Button-5>", self._on_scroll)
        self._canvas.bind("<MouseWheel>", self._on_scroll)
        self._canvas.bind(
            "<Shift-Button-4>", lambda e: self._canvas.xview_scroll(-1, "units")
        )
        self._canvas.bind(
            "<Shift-Button-5>", lambda e: self._canvas.xview_scroll(1, "units")
        )

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _initial_render(self):
        self._win.update_idletasks()
        canvas_w = self._canvas.winfo_width()
        canvas_h = self._canvas.winfo_height()
        scale_w = canvas_w / _IMG_W
        scale_h = canvas_h / _IMG_H
        self._scale = min(scale_w, scale_h)
        self._redraw()

        if self._current_map_id and self._current_map_id in self._native_rects:
            nx0, ny0, nx1, ny1 = self._native_rects[self._current_map_id]
            cx = int((nx0 + nx1) / 2 * self._scale)
            cy = int((ny0 + ny1) / 2 * self._scale)
            self._win.after(80, lambda: self._scroll_to(cx, cy))

    def _redraw(self):
        self._canvas.delete("all")
        self._rect_map.clear()
        self._hover_id = None
        self._player_item = None

        scaled_w = int(_IMG_W * self._scale)
        scaled_h = int(_IMG_H * self._scale)

        img = self._raw_image.resize((scaled_w, scaled_h), Image.LANCZOS)
        self._img_cache = ImageTk.PhotoImage(img)
        self._canvas.create_image(0, 0, anchor=tk.NW, image=self._img_cache)
        self._canvas.configure(scrollregion=(0, 0, scaled_w, scaled_h))

        dark_mode = ctk.get_appearance_mode() == "Dark"
        self._fill_color = "#00cc44" if dark_mode else "#00aa33"
        self._hover_color = "#ffdd00"
        self._sel_color = "#ff6644"
        self._player_color = "#00cfff"

        selected_map_id = self._selected.map_id_str if self._selected else None
        self._selected = None

        for loc in self._locations:
            nx0, ny0, nx1, ny1 = self._native_rects[loc.map_id_str]
            sx0 = int(nx0 * self._scale)
            sy0 = int(ny0 * self._scale)
            sx1 = int(nx1 * self._scale)
            sy1 = int(ny1 * self._scale)

            is_player = loc.map_id_str == self._current_map_id
            is_selected = loc.map_id_str == selected_map_id

            if is_selected:
                fill = self._sel_color
                self._selected = loc
            elif is_player:
                fill = self._player_color
            else:
                fill = self._fill_color

            item = self._canvas.create_rectangle(
                sx0,
                sy0,
                sx1,
                sy1,
                fill=fill,
                outline="#003311",
                width=1,
                stipple="gray25",
                tags=("tile",),
            )
            self._rect_map[item] = loc
            if is_player:
                self._player_item = item

        if self._selected:
            self._teleport_btn.configure(state="normal")

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def _on_scroll(self, event):
        ctrl = (event.state & 0x4) != 0
        if event.num == 4 or (event.delta and event.delta > 0):
            direction = 1
        else:
            direction = -1

        if ctrl:
            self._zoom(direction, event)
        else:
            self._canvas.yview_scroll(-direction, "units")

    def _zoom(self, direction: int, event):
        new_scale = self._scale * (1 + direction * _ZOOM_STEP)
        new_scale = max(_ZOOM_MIN, min(_ZOOM_MAX, new_scale))
        if abs(new_scale - self._scale) < 0.001:
            return

        # Point under cursor in canvas coords before zoom
        cx = self._canvas.canvasx(event.x)
        cy = self._canvas.canvasy(event.y)
        ratio = new_scale / self._scale

        self._scale = new_scale
        self._redraw()

        new_img_w = int(_IMG_W * self._scale)
        new_img_h = int(_IMG_H * self._scale)
        fx = max(0.0, min(1.0, (cx * ratio - event.x) / new_img_w))
        fy = max(0.0, min(1.0, (cy * ratio - event.y) / new_img_h))
        self._canvas.xview_moveto(fx)
        self._canvas.yview_moveto(fy)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _scroll_to(self, cx: int, cy: int):
        canvas_w = self._canvas.winfo_width()
        canvas_h = self._canvas.winfo_height()
        img_w = int(_IMG_W * self._scale)
        img_h = int(_IMG_H * self._scale)
        fx = max(0.0, min(1.0, (cx - canvas_w / 2) / img_w))
        fy = max(0.0, min(1.0, (cy - canvas_h / 2) / img_h))
        self._canvas.xview_moveto(fx)
        self._canvas.yview_moveto(fy)

    def _tile_color(self, loc: MapLocation) -> str:
        if loc == self._selected:
            return self._sel_color
        if loc.map_id_str == self._current_map_id:
            return self._player_color
        return self._fill_color

    def _item_at(self, event) -> int | None:
        cx = self._canvas.canvasx(event.x)
        cy = self._canvas.canvasy(event.y)
        items = self._canvas.find_overlapping(cx - 1, cy - 1, cx + 1, cy + 1)
        for item in reversed(items):
            if item in self._rect_map:
                return item
        return None

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_click(self, event):
        item = self._item_at(event)
        if item is None:
            return
        for i, loc in self._rect_map.items():
            if loc != self._selected:
                self._canvas.itemconfig(i, fill=self._tile_color(loc))
        loc = self._rect_map[item]
        self._selected = loc
        self._canvas.itemconfig(item, fill=self._sel_color)
        self._info_var.set(f"{loc.map_id_str}  {loc.name[:80]}")
        self._teleport_btn.configure(state="normal")

    def _on_hover(self, event):
        item = self._item_at(event)
        if item == self._hover_id:
            return
        if self._hover_id is not None and self._hover_id in self._rect_map:
            self._canvas.itemconfig(
                self._hover_id, fill=self._tile_color(self._rect_map[self._hover_id])
            )
        self._hover_id = item
        if item is not None and self._rect_map[item] != self._selected:
            self._canvas.itemconfig(item, fill=self._hover_color)

    def _on_leave(self, event):
        if self._hover_id is not None and self._hover_id in self._rect_map:
            self._canvas.itemconfig(
                self._hover_id, fill=self._tile_color(self._rect_map[self._hover_id])
            )
        self._hover_id = None

    def _on_teleport(self):
        if self._selected:
            self._on_select(self._selected)

    def _close(self):
        MapWindow._instance = None
        self._win.destroy()


def open_map_window(
    parent,
    locations: list[MapLocation],
    on_select: Callable[[MapLocation], None],
    map_image_path: str,
    current_map_id: str | None = None,
) -> None:
    """Open (or focus) the map popout window."""
    MapWindow(parent, locations, on_select, map_image_path, current_map_id)
