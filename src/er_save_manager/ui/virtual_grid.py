"""Scrollable icon grid that only draws the cells on screen.

A CTkButton costs a few ms to build, and embedded widgets make a canvas
slow to scroll, so cells are canvas items (rounded rectangle, icon, text)
styled like the app's buttons. A pool sized to the visible rows is reused
while scrolling. Icons are loaded when a cell first comes into view.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from collections import OrderedDict
from collections.abc import Callable, Hashable
from typing import NamedTuple

import customtkinter as ctk
from PIL import Image, ImageTk

from er_save_manager.ui import palette
from er_save_manager.ui.dialog_style import _round_rect

CELL_COLOR = ("gray82", "gray18")
CELL_SELECTED = palette.PURPLE_SELECT
_HOVER = ("gray70", "gray28")
_TEXT = ("gray10", "gray90")
_SHIFT = 0x0001
_CONTROL = 0x0004
# Loaded icons kept for cells that scroll back into view.
_IMAGE_CACHE = 600
_NO_IMAGE: Image.Image | None = None


def no_image_icon() -> Image.Image:
    """Square "No image" tile for entries without a picture.

    Transparent with mid-gray text, so it reads on the cell color of both
    themes. The grid scales it to the icon size like any other icon.
    """
    global _NO_IMAGE
    if _NO_IMAGE is None:
        from PIL import ImageDraw, ImageFont

        size = 150
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(
            (8, 8, size - 9, size - 9), radius=10, outline=(128, 128, 128, 255), width=2
        )
        font = ImageFont.load_default(size=20)
        draw.text(
            (size / 2, size / 2),
            "No image",
            fill=(128, 128, 128, 255),
            font=font,
            anchor="mm",
        )
        _NO_IMAGE = img
    return _NO_IMAGE


class GridEntry(NamedTuple):
    key: Hashable
    text: str
    # Lowercase text the search query is matched against
    search: str
    # Returns a PIL image or None; called once per entry while cached
    icon: Callable[[], object]


class _Cell:
    __slots__ = ("tag", "rect", "image", "text", "x", "y", "pos")

    def __init__(self, tag: str, rect: int, image: int, text: int) -> None:
        self.tag = tag
        self.rect = rect
        self.image = image
        self.text = text
        # Top-left corner on the canvas
        self.x = 0.0
        self.y = 0.0
        # Index into the entry list the cell currently shows, or -1
        self.pos = -1


class VirtualIconGrid(ctk.CTkFrame):
    """Icon grid over a list of GridEntry.

    Click selects one cell. With multi, Ctrl click toggles a cell and Shift
    click selects the shown range from the last clicked cell. on_select gets
    the selected keys in entry order; on_activate gets the key of a
    double-clicked cell. tooltip(key) gives the hover text of a cell.
    """

    def __init__(
        self,
        parent,
        on_select: Callable[[list], None],
        *,
        multi: bool = False,
        on_activate: Callable[[Hashable], None] | None = None,
        tooltip: Callable[[Hashable], str] | None = None,
        cell_w: int = 116,
        cell_h: int = 124,
        pad: int = 4,
        icon_size: int = 64,
        icon_height: int | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._on_select = on_select
        self._on_activate = on_activate
        self._multi = multi
        self._cell_w = cell_w
        self._cell_h = cell_h
        self._pad = pad
        # Icons fit an icon_size x icon_height box (square by default)
        self._icon_size = icon_size
        self._icon_h = icon_height if icon_height is not None else icon_size

        self._entries: list[GridEntry] = []
        self._order: dict[Hashable, int] = {}
        # Positions in _entries that pass the search query
        self._shown: list[int] = []
        self.query = ""
        self.selected: list = []
        self._anchor = None
        self._cols = 1

        self._cells: dict[int, _Cell] = {}  # shown index -> cell
        self._free: list[_Cell] = []
        self._by_tag: dict[str, _Cell] = {}
        self._hover: _Cell | None = None
        self._images: OrderedDict[int, ImageTk.PhotoImage | None] = OrderedDict()
        self._refresh_job: str | None = None
        self._font: tkfont.Font | None = None
        self._fitted: dict[str, str] = {}
        # font.measure is a Tk round trip; widths are summed per character
        self._char_w: dict[str, int] = {}
        self._line_h = 0

        self._canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self._scrollbar = ctk.CTkScrollbar(self, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._on_yview)
        self._canvas.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        self._scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 3), pady=6)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._update_canvas_bg()

        self._canvas.bind("<Configure>", lambda _e: self._relayout())
        self._bind_wheel(self._canvas)
        self._tooltip_text = tooltip
        self._tip = None
        if tooltip is not None:
            from er_save_manager.ui.tooltip import Tooltip

            self._tip = Tooltip(self._canvas, "")

    # ---- public --------------------------------------------------------------

    def set_entries(self, entries: list[GridEntry], keep_selection: bool = False):
        self._entries = list(entries)
        self._order = {e.key: i for i, e in enumerate(self._entries)}
        # Dropping a PhotoImage deletes the Tk image, and Tk fails any later
        # itemconfigure of a canvas item that still names it, so the cells
        # let go of their images first.
        for cell in [*self._cells.values(), *self._free]:
            self._canvas.itemconfigure(cell.image, image="")
            cell.pos = -1
        self._images.clear()
        if keep_selection:
            self.selected = [k for k in self.selected if k in self._order]
        else:
            self.selected = []
            self._anchor = None
        self._filter()
        self._canvas.yview_moveto(0)
        self._relayout()

    def apply_filter(self, query: str) -> None:
        query = query.lower().strip()
        if query == self.query:
            return
        self.query = query
        self._filter()
        self._canvas.yview_moveto(0)
        self._relayout()

    def refresh_icon(self, key: Hashable) -> None:
        """Load an entry's icon again, e.g. after it finished downloading."""
        pos = self._order.get(key)
        if pos is None:
            return
        self._images.pop(pos, None)
        for cell in self._cells.values():
            if cell.pos == pos:
                self._canvas.itemconfigure(cell.image, image=self._image(pos) or "")

    def visible_keys(self) -> list:
        return [self._entries[p].key for p in self._shown]

    def see(self, key: Hashable) -> None:
        """Scroll the cell of key into the middle of the view when it is not
        in view."""
        pos = self._order.get(key)
        if pos is None or pos not in self._shown:
            return
        _, pitch_h = self._pitch()
        top = (self._shown.index(pos) // self._cols) * pitch_h
        view_top = self._canvas.canvasy(0)
        view_h = self._canvas.winfo_height()
        if view_top <= top and top + pitch_h <= view_top + view_h:
            return
        region = self._canvas.cget("scrollregion").split()
        height = float(region[3]) if len(region) == 4 else 0.0
        if height > 0:
            self._canvas.yview_moveto(max(0.0, top - (view_h - pitch_h) / 2) / height)

    def set_selection(self, keys: list, notify: bool = True) -> None:
        self.selected = sorted(
            (k for k in set(keys) if k in self._order), key=self._order.__getitem__
        )
        chosen = set(self.selected)
        for cell in self._cells.values():
            key = self._entries[cell.pos].key
            self._paint(cell, key in chosen)
        if notify:
            self._on_select(self.selected)

    # ---- layout --------------------------------------------------------------

    def _filter(self) -> None:
        q = self.query
        self._shown = [i for i, e in enumerate(self._entries) if not q or q in e.search]

    def _pitch(self) -> tuple[int, int]:
        """Cell pitch in screen pixels; cell sizes are given unscaled."""
        w = self._apply_widget_scaling(self._cell_w + 2 * self._pad)
        h = self._apply_widget_scaling(self._cell_h + 2 * self._pad)
        return round(w), round(h)

    def _relayout(self) -> None:
        width = max(1, self._canvas.winfo_width())
        pitch_w, pitch_h = self._pitch()
        self._cols = max(1, width // pitch_w)
        rows = -(-len(self._shown) // self._cols)
        height = max(rows * pitch_h, self._canvas.winfo_height())
        self._canvas.configure(scrollregion=(0, 0, width, height))
        # Positions depend on the column count, so every cell is placed again.
        for cell in self._cells.values():
            self._hide(cell)
        self._cells.clear()
        self._refresh()

    def _on_yview(self, first, last) -> None:
        self._scrollbar.set(first, last)
        if self._refresh_job is None:
            self._refresh_job = self.after_idle(self._refresh)

    def _refresh(self) -> None:
        self._refresh_job = None
        if not self.winfo_exists():
            return
        pitch_w, pitch_h = self._pitch()
        top = self._canvas.canvasy(0)
        bottom = top + self._canvas.winfo_height()
        lo = max(0, int(top // pitch_h)) * self._cols
        hi = min(len(self._shown), (int(bottom // pitch_h) + 1) * self._cols)

        for idx in [i for i in self._cells if not lo <= i < hi]:
            self._hide(self._cells.pop(idx))
        # Prefer a free cell that already shows the entry: no reconfigure.
        by_pos = {c.pos: c for c in self._free if c.pos >= 0}
        chosen = set(self.selected)
        for idx in range(lo, hi):
            if idx in self._cells:
                continue
            pos = self._shown[idx]
            cell = by_pos.pop(pos, None)
            if cell is not None:
                self._free.remove(cell)
            elif self._free:
                cell = self._free.pop()
                by_pos.pop(cell.pos, None)
            else:
                cell = self._new_cell()
            if cell.pos != pos:
                entry = self._entries[pos]
                self._canvas.itemconfigure(cell.text, text=self._fit(entry.text))
                self._canvas.itemconfigure(cell.image, image=self._image(pos) or "")
                cell.pos = pos
            self._paint(cell, self._entries[pos].key in chosen)
            row, col = divmod(idx, self._cols)
            x = col * pitch_w + self._apply_widget_scaling(self._pad)
            y = row * pitch_h + self._apply_widget_scaling(self._pad)
            self._canvas.move(cell.tag, x - cell.x, y - cell.y)
            cell.x, cell.y = x, y
            self._canvas.itemconfigure(cell.tag, state="normal")
            self._cells[idx] = cell

    def _text_font(self) -> tkfont.Font:
        if self._font is None:
            # Same size rule as CTk fonts: negative pixel size, scaled
            size = -abs(round(self._apply_widget_scaling(11)))
            self._font = tkfont.Font(family="Segoe UI", size=size)
            # Label height per line; the rest of the cell is icon and padding
            self._line_h = self._font.metrics("linespace")
        return self._font

    def _fit(self, text: str) -> str:
        """text wrapped to the cell width and cut to the lines below the icon.

        Extra lines after the first paragraph (quantity, location) are kept;
        the name gives up lines and ends in an ellipsis instead.
        """
        if text in self._fitted:
            return self._fitted[text]
        font = self._text_font()
        width = self._apply_widget_scaling(self._cell_w - 16)
        room = self._apply_widget_scaling(self._cell_h - self._icon_h - 16)
        max_lines = max(1, int(room // self._line_h))

        def measure(chunk: str) -> int:
            total = 0
            for ch in chunk:
                if ch not in self._char_w:
                    self._char_w[ch] = font.measure(ch)
                total += self._char_w[ch]
            return total

        def wrap(paragraph: str) -> list[str]:
            lines, line, line_w = [], "", 0
            space = measure(" ")
            for word in paragraph.split(" "):
                w = measure(word)
                if not line or line_w + space + w <= width:
                    line_w = line_w + space + w if line else w
                    line = f"{line} {word}" if line else word
                else:
                    lines.append(line)
                    line, line_w = word, w
            lines.append(line)
            return lines

        name, *rest = text.split("\n")
        rest_lines = [ln for p in rest for ln in wrap(p)]
        name_lines = wrap(name)
        keep = max(1, max_lines - len(rest_lines))
        if len(name_lines) > keep:
            name_lines = name_lines[:keep]
            last = name_lines[-1]
            while last and measure(last + "\u2026") > width:
                last = last[:-1]
            name_lines[-1] = last.rstrip() + "\u2026"
        fitted = "\n".join(name_lines + rest_lines)
        self._fitted[text] = fitted
        return fitted

    def _hide(self, cell: _Cell) -> None:
        self._canvas.itemconfigure(cell.tag, state="hidden")
        if self._hover is cell:
            self._hover = None
        self._free.append(cell)

    def _new_cell(self) -> _Cell:
        cv = self._canvas
        tag = f"cell{len(self._by_tag)}"
        w = self._apply_widget_scaling(self._cell_w)
        h = self._apply_widget_scaling(self._cell_h)
        rect = _round_rect(
            cv, 0, 0, w, h, radius=self._apply_widget_scaling(6), tags=(tag,)
        )
        icon_y = self._apply_widget_scaling(8 + self._icon_h / 2)
        image = cv.create_image(w / 2, icon_y, anchor="center", tags=(tag,))
        text = cv.create_text(
            w / 2,
            self._apply_widget_scaling(self._icon_h + 14),
            anchor="n",
            justify="center",
            font=self._text_font(),
            tags=(tag,),
        )
        cell = _Cell(tag, rect, image, text)
        self._by_tag[tag] = cell
        cv.tag_bind(tag, "<Enter>", lambda _e, c=cell: self._set_hover(c))
        cv.tag_bind(tag, "<Leave>", lambda _e, c=cell: self._clear_hover(c))
        cv.tag_bind(tag, "<Button-1>", lambda e, c=cell: self._click(c, e.state))
        if self._on_activate is not None:
            cv.tag_bind(tag, "<Double-Button-1>", lambda _e, c=cell: self._activate(c))
        self._recolor_text(cell)
        return cell

    def _recolor_text(self, cell: _Cell) -> None:
        self._canvas.itemconfigure(cell.text, fill=self._apply_appearance_mode(_TEXT))

    def _cell_selected(self, cell: _Cell) -> bool:
        return cell.pos >= 0 and self._entries[cell.pos].key in set(self.selected)

    def _paint(self, cell: _Cell, selected: bool) -> None:
        if selected:
            color = CELL_SELECTED
        elif cell is self._hover:
            color = _HOVER
        else:
            color = CELL_COLOR
        self._canvas.itemconfigure(cell.rect, fill=self._apply_appearance_mode(color))

    def _set_hover(self, cell: _Cell) -> None:
        self._hover = cell
        self._paint(cell, self._cell_selected(cell))
        if self._tip is not None and cell.pos >= 0:
            self._tip.show_text(self._tooltip_text(self._entries[cell.pos].key))

    def _clear_hover(self, cell: _Cell) -> None:
        if self._hover is cell:
            self._hover = None
        self._paint(cell, self._cell_selected(cell))
        if self._tip is not None:
            self._tip.show_text("")

    def _image(self, pos: int) -> ImageTk.PhotoImage | None:
        if pos in self._images:
            self._images.move_to_end(pos)
            return self._images[pos]
        img = None
        try:
            pil = self._entries[pos].icon()
        except Exception:
            pil = None
        if pil is not None:
            w, h = pil.size
            scale = min(
                self._apply_widget_scaling(self._icon_size) / max(w, 1),
                self._apply_widget_scaling(self._icon_h) / max(h, 1),
            )
            size = (max(1, round(w * scale)), max(1, round(h * scale)))
            img = ImageTk.PhotoImage(
                pil.convert("RGBA").resize(size, Image.LANCZOS), master=self._canvas
            )
        self._images[pos] = img
        while len(self._images) > _IMAGE_CACHE:
            old, _ = self._images.popitem(last=False)
            # A pooled cell still showing the evicted entry is redrawn on reuse
            for cell in self._free:
                if cell.pos == old:
                    self._canvas.itemconfigure(cell.image, image="")
                    cell.pos = -1
        return img

    # ---- input ---------------------------------------------------------------

    def _bind_wheel(self, widget) -> None:
        widget.bind("<MouseWheel>", self._on_wheel, add="+")
        widget.bind("<Button-4>", lambda _e: self._scroll(-1), add="+")
        widget.bind("<Button-5>", lambda _e: self._scroll(1), add="+")

    def _on_wheel(self, event) -> None:
        if event.delta:
            self._scroll(-1 if event.delta > 0 else 1)

    def _scroll(self, direction: int) -> None:
        # A third of a row per notch, like a scrollable frame
        _, pitch_h = self._pitch()
        self._canvas.configure(yscrollincrement=max(1, pitch_h // 3))
        self._canvas.yview_scroll(direction * 2, "units")
        if self._tip is not None:
            self._tip.show_text("")

    def _click(self, cell: _Cell, state: int) -> None:
        if cell.pos < 0:
            return
        key = self._entries[cell.pos].key
        if self._multi and state & _SHIFT and self._anchor is not None:
            keys = self.visible_keys()
            if self._anchor in keys and key in keys:
                a, b = sorted((keys.index(self._anchor), keys.index(key)))
                self.set_selection(keys[a : b + 1])
                return
        if self._multi and state & _CONTROL:
            chosen = [k for k in self.selected if k != key]
            if key not in self.selected:
                chosen.append(key)
        else:
            chosen = [key]
        self._anchor = key
        self.set_selection(chosen)

    def _activate(self, cell: _Cell) -> None:
        if cell.pos >= 0:
            self._on_activate(self._entries[cell.pos].key)

    # ---- theme ---------------------------------------------------------------

    def _update_canvas_bg(self) -> None:
        self._canvas.configure(bg=self._apply_appearance_mode(self._fg_color))

    def _set_appearance_mode(self, mode_string) -> None:
        super()._set_appearance_mode(mode_string)
        self._update_canvas_bg()
        for cell in self._by_tag.values():
            self._recolor_text(cell)
            if cell.pos >= 0:
                self._paint(cell, self._cell_selected(cell))

    def destroy(self) -> None:
        if self._refresh_job is not None:
            self.after_cancel(self._refresh_job)
            self._refresh_job = None
        super().destroy()
