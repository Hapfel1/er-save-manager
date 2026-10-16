"""Shared look for dialogs: fonts, colors, buttons and size-to-content placement."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui import palette
from er_save_manager.ui.utils import (
    center_window,
    force_render_dialog,
    get_work_area,
    style_window_frame,
    title_bar_height,
)

FONT = ("Segoe UI", 13)
BOLD = ("Segoe UI Semibold", 13)
SMALL = ("Segoe UI", 12)
TITLE = ("Segoe UI Semibold", 15)
# Main windows and announcement dialogs (update, console saves)
TITLE_LARGE = ("Segoe UI", 19, "bold")
MUTED = ("gray40", "gray65")
BOX = ("gray90", "gray18")
WARNING = palette.WARNING_TEXT
HINT = palette.HINT_TEXT
INFO = palette.PURPLE_TEXT
FOUND = palette.GREEN_TEXT
ERROR = palette.RED_TEXT
SECONDARY = ("gray70", "gray35")
BUTTON_HEIGHT = 32


def _scale(widget) -> float:
    """Window scaling factor of the toplevel holding widget."""
    get_scale = getattr(widget.winfo_toplevel(), "_get_window_scaling", None)
    return get_scale() if get_scale else 1.0


def button(parent, text, command, *, primary=True, width=100, **kwargs):
    """Dialog button: 13 pt, 32 px high; secondary buttons are gray."""
    if not primary:
        kwargs.setdefault("fg_color", SECONDARY)
    kwargs.setdefault("height", BUTTON_HEIGHT)
    return ctk.CTkButton(
        parent, text=text, command=command, font=FONT, width=width, **kwargs
    )


def button_row(parent, buttons, pady=(16, 0)):
    """Right aligned row of buttons, given left to right as button kwargs dicts."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(side=tk.BOTTOM, fill=tk.X, pady=pady)
    widgets = []
    for spec in reversed(buttons):
        spec = dict(spec)
        widget = button(row, spec.pop("text"), spec.pop("command"), **spec)
        widget.pack(side=tk.RIGHT, padx=(8, 0))
        widgets.append(widget)
    return row, widgets[::-1]


def header(parent, text, icon=None, icon_color=WARNING, font=TITLE):
    """Title row with an optional symbol on the left."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill=tk.X)
    if icon:
        ctk.CTkLabel(
            row, text=icon, font=("Segoe UI Semibold", 24), text_color=icon_color
        ).pack(side=tk.LEFT, padx=(0, 10))
    ctk.CTkLabel(row, text=text, font=font, anchor="w", justify=tk.LEFT).pack(
        side=tk.LEFT, fill=tk.X
    )
    return row


def box(parent, **pack):
    """Gray rounded group box."""
    frame = ctk.CTkFrame(parent, fg_color=BOX, corner_radius=8)
    frame.pack(fill=tk.X, **({"pady": (4, 8)} | pack))
    return frame


def create(parent, title, *, transient=True):
    """New dialog, withdrawn until finish() has sized and placed it.

    Withdrawing (not only alpha 0) keeps window managers that ignore alpha on
    unmapped windows from showing it at the default spot first.
    """
    dialog = ctk.CTkToplevel(parent)
    dialog.withdraw()
    dialog.attributes("-alpha", 0)
    dialog.title(title)
    dialog.resizable(False, False)
    if transient and parent is not None:
        dialog.transient(parent)
    return dialog


def finish(dialog, parent, *, min_width=0, width=None, height=None):
    """Size the dialog to its content (or the given size), center and show it.

    min_width and the content's requested size are logical pixels; the window
    stays hidden (alpha 0) until it is placed.
    """
    dialog.update_idletasks()
    scale = _scale(dialog)
    if width is None:
        width = max(round(dialog.winfo_reqwidth() / scale), min_width)
    if height is None:
        height = round(dialog.winfo_reqheight() / scale)
    center_window(dialog, width, height, parent=parent)
    dialog.deiconify()
    style_window_frame(dialog)
    force_render_dialog(dialog)
    dialog.attributes("-alpha", 1)
    try:
        dialog.wait_visibility()
        dialog.grab_set()
    except tk.TclError:
        # Closed before it became visible
        pass


def content(parent, build, *, max_height=520, width=None, **pack):
    """Pack the widgets from build(frame) into parent, scrolling when tall.

    build is called once with a plain frame; when that is taller than
    max_height (logical pixels) it is rebuilt inside a scrollable frame of
    that height, so the dialog never outgrows the screen.
    """
    from er_save_manager.ui.utils import bind_mousewheel

    pack = {"fill": tk.BOTH, "expand": True} | pack
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(**pack)
    build(frame)
    frame.update_idletasks()
    scale = _scale(frame)
    req_w = frame.winfo_reqwidth() / scale
    if frame.winfo_reqheight() / scale <= max_height:
        return frame
    frame.destroy()
    frame = ctk.CTkScrollableFrame(
        parent,
        fg_color="transparent",
        width=round(width if width is not None else req_w),
        height=max_height,
    )
    frame.pack(**pack)
    bind_mousewheel(frame)
    build(frame)
    return frame


def ask_string(parent, title, prompt, initial="", *, ok_text="OK", font=TITLE):
    """Single-line input dialog; returns the entered text or None if cancelled."""
    result = [None]
    dialog = create(parent, title)
    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
    var = tk.StringVar(value=initial)

    def confirm(_event=None):
        result[0] = var.get()
        dialog.destroy()

    button_row(
        main,
        [
            {"text": ok_text, "command": confirm},
            {"text": "Cancel", "command": dialog.destroy, "primary": False},
        ],
    )
    ctk.CTkLabel(
        main, text=prompt, font=font, wraplength=360, justify=tk.LEFT, anchor="w"
    ).pack(anchor="w")
    entry = ctk.CTkEntry(main, textvariable=var, width=360, height=32, font=FONT)
    entry.pack(fill=tk.X, pady=(10, 0))
    entry.bind("<Return>", confirm)
    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    finish(dialog, parent)
    entry.focus_set()
    entry.select_range(0, "end")
    dialog.wait_window()
    return result[0]


def show_code(parent, title, heading, code, on_copy, *, font=TITLE):
    """Show a share code in a large read-only field with a Copy Code button."""
    dialog = create(parent, title)
    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

    def copy_code():
        dialog.clipboard_clear()
        dialog.clipboard_append(code)
        on_copy()

    button_row(
        main,
        [
            {"text": "Copy Code", "command": copy_code, "width": 110},
            {"text": "Close", "command": dialog.destroy, "primary": False},
        ],
    )
    header(main, heading, font=font)
    ctk.CTkLabel(
        main, text="Send this code to share it.", font=SMALL, text_color=MUTED
    ).pack(anchor="w", pady=(2, 10))
    entry = ctk.CTkEntry(
        main, width=340, height=36, justify="center", font=("Consolas", 16)
    )
    entry.pack(fill=tk.X)
    entry.insert(0, code)
    entry.configure(state="readonly")
    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    finish(dialog, parent, min_width=380)
    return dialog


# List rows sit as separate cards on the BOX background
ROW = ("#f4f4f4", "#383838")
ROW_TEXT = ("#111111", "#dce4ee")


# Card rows sit on the default frame color, so they need more contrast than ROW
CARD_ROW = ("#f9f9f9", "gray27")


def card_row(parent, title, detail="", *, on_click=None, on_double=None, font=None):
    """Clickable gray card: title, then muted detail text on the same line.

    Packed with fill="x"; select_card_row() marks it selected. on_click and
    on_double run for clicks on the card and on both labels.
    """
    row = ctk.CTkFrame(parent, fg_color=CARD_ROW, corner_radius=8)
    row.pack(fill=tk.X, padx=4, pady=3)
    labels = [ctk.CTkLabel(row, text=title, font=font or BOLD, text_color=ROW_TEXT)]
    labels[0].pack(side=tk.LEFT, padx=(12, 10), pady=7)
    if detail:
        labels.append(
            ctk.CTkLabel(row, text=detail, font=SMALL, text_color=MUTED, anchor="w")
        )
        labels[1].pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12), pady=7)
    for widget in (row, *labels):
        if on_click:
            widget.bind("<Button-1>", lambda _e: on_click(), add="+")
        if on_double:
            widget.bind("<Double-Button-1>", lambda _e: on_double(), add="+")
    return row


def select_card_row(row, selected: bool) -> None:
    row.configure(fg_color=palette.PURPLE_TINT if selected else CARD_ROW)


def _round_rect(canvas, x0, y0, x1, y1, *, radius, **kwargs):
    """Rounded rectangle as a smoothed polygon (tk canvases have no native one)."""
    r = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
    points = [
        x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r,
        x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
        x0, y1, x0, y1 - r, x0, y0 + r, x0, y0,
    ]  # fmt: skip
    return canvas.create_polygon(points, smooth=True, outline="", **kwargs)


class RowList(ctk.CTkFrame):
    """Scrollable list of text rows with optional icons, drawn on a canvas.

    For picker popups. Rows are cards separated by a gap; the selected row
    uses the theme's selection purple. Only the rows in view are drawn, so
    long lists filter and scroll quickly. on_activate(index) runs on
    double-click and Enter.
    """

    def __init__(
        self,
        parent,
        *,
        row_height=34,
        icon_space=0,
        on_activate=None,
        width=200,
    ):
        super().__init__(parent, fg_color=BOX, corner_radius=8, width=width)
        self._row_h = row_height
        self._icon_space = icon_space
        self._on_activate = on_activate
        self._labels: list[str] = []
        self._photos: list = []
        self._icon_job = None
        self._redraw_job = None
        self._drawn = (0, 0)
        self.selected: int | None = None

        self._canvas = tk.Canvas(
            self, bg=palette.pick(BOX), highlightthickness=0, bd=0, width=width
        )
        self._scrollbar = ctk.CTkScrollbar(self, command=self._canvas.yview)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=6)
        self._canvas.configure(yscrollcommand=self._on_scroll)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 2), pady=6)
        self._font = ctk.CTkFont(family=FONT[0], size=FONT[1])
        self._canvas.bind("<Configure>", lambda _e: self._redraw())
        self._canvas.bind("<Button-1>", self._click)
        self._canvas.bind("<Double-Button-1>", self._double_click)
        self._canvas.bind("<Return>", lambda _e: self._activate())
        for seq, step in (("<Button-4>", -1), ("<Button-5>", 1)):
            self._canvas.bind(
                seq, lambda _e, s=step: self._canvas.yview_scroll(s, "units")
            )
        self._canvas.bind(
            "<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"),
        )

    # ---- content ------------------------------------------------------------

    def set_rows(self, labels: list[str]) -> None:
        self.clear()
        self._labels = list(labels)
        self._schedule_redraw()
        self._canvas.yview_moveto(0)

    def clear(self) -> None:
        """Remove all rows."""
        self._labels = []
        if self._icon_job is not None:
            self.after_cancel(self._icon_job)
            self._icon_job = None
        self._canvas.delete("icon")
        self._photos.clear()
        self.selected = None
        self._schedule_redraw()

    # ---- selection ----------------------------------------------------------

    def selection_set(self, index: int) -> None:
        if not 0 <= index < len(self._labels):
            return
        previous, self.selected = self.selected, index
        for i in (previous, index):
            if i is not None:
                self._recolor(i)

    def select(self, index: int) -> None:
        """Select a row and scroll it into view."""
        self.selection_set(index)
        self.see(index)

    def see(self, index: int) -> None:
        if not self._labels:
            return
        self.update_idletasks()
        total = len(self._labels) * self._row_h
        visible = self._canvas.winfo_height() / max(1, total)
        top = index / len(self._labels) - visible / 2
        self._canvas.yview_moveto(max(0.0, top))

    # ---- icons --------------------------------------------------------------

    def set_icon(self, index: int, photo) -> None:
        """Place a PhotoImage at the left of a row (keeps a reference)."""
        self._photos.append(photo)
        y = index * self._row_h + self._row_h // 2
        self._canvas.create_image(8, y, image=photo, anchor="w", tags=("icon",))

    def load_icons(self, fetch, size=24, batch=20) -> None:
        """Load row icons in batches so the list shows before all are read.

        fetch(index) returns a PIL image or None.
        """
        from PIL import Image, ImageTk

        def run(start: int) -> None:
            end = min(start + batch, len(self._labels))
            for i in range(start, end):
                try:
                    image = fetch(i)
                except Exception:
                    image = None
                if image is not None:
                    image = image.convert("RGBA").resize((size, size), Image.LANCZOS)
                    self.set_icon(i, ImageTk.PhotoImage(image))
            if end < len(self._labels):
                self._icon_job = self.after(30, lambda: run(end))
            else:
                self._icon_job = None

        self._icon_job = self.after(50, lambda: run(0))

    # ---- drawing ------------------------------------------------------------

    def _schedule_redraw(self) -> None:
        if self._redraw_job is None:
            self._redraw_job = self.after_idle(self._redraw)

    def _redraw(self) -> None:
        self._redraw_job = None
        width = max(self._canvas.winfo_width(), 200)
        self._canvas.configure(
            scrollregion=(0, 0, width, len(self._labels) * self._row_h)
        )
        self._drawn = (0, 0)
        self._draw_visible()

    def _on_scroll(self, first, last) -> None:
        self._scrollbar.set(first, last)
        self._draw_visible()

    def _draw_visible(self) -> None:
        cv = self._canvas
        top = cv.canvasy(0)
        bottom = top + cv.winfo_height()
        start = max(0, int(top // self._row_h) - 10)
        end = min(len(self._labels), int(bottom // self._row_h) + 11)
        if (start, end) == self._drawn:
            return
        self._drawn = (start, end)
        cv.delete("row")
        width = max(cv.winfo_width(), 200)
        text_color = palette.pick(ROW_TEXT)
        for i in range(start, end):
            y0 = i * self._row_h
            _round_rect(
                cv,
                0,
                y0 + 2,
                width - 2,
                y0 + self._row_h - 2,
                radius=10,
                fill=self._row_color(i),
                tags=("row", f"bg_{i}"),
            )
            cv.create_text(
                10 + self._icon_space,
                y0 + self._row_h // 2,
                text=self._labels[i],
                fill=text_color,
                font=self._font,
                anchor="w",
                tags=("row",),
            )
        cv.tag_raise("icon")

    def _row_color(self, index: int) -> str:
        if index == self.selected:
            return palette.pick(palette.PURPLE_SELECT)
        return palette.pick(ROW)

    def _recolor(self, index: int) -> None:
        self._canvas.itemconfigure(f"bg_{index}", fill=self._row_color(index))

    # ---- events -------------------------------------------------------------

    def _index_at(self, event) -> int | None:
        index = int(self._canvas.canvasy(event.y) // self._row_h)
        if 0 <= index < len(self._labels):
            return index
        return None

    def _click(self, event) -> None:
        index = self._index_at(event)
        if index is None:
            return
        self.selection_set(index)
        self._canvas.focus_set()

    def _double_click(self, event) -> None:
        self._click(event)
        self._activate()

    def _activate(self) -> None:
        if self.selected is not None and self._on_activate:
            self._on_activate(self.selected)


def refit(dialog) -> None:
    """Resize a dialog to its content after widgets were shown or hidden.

    Keeps the position and never makes the dialog narrower than it is.
    """
    dialog.update_idletasks()
    scale = _scale(dialog)
    width = max(dialog.winfo_width(), dialog.winfo_reqwidth())
    # Not past the bottom of the work area (taskbar) from the current position
    _, work_y, _, work_h = get_work_area(dialog)
    room = work_y + work_h - dialog.winfo_y() - title_bar_height(dialog)
    height = min(dialog.winfo_reqheight(), max(room, int(work_h * 0.5)))
    dialog.geometry(
        f"{round(width / scale)}x{round(height / scale)}"
        f"+{dialog.winfo_x()}+{dialog.winfo_y()}"
    )


def wrap_to_width(label: ctk.CTkLabel) -> ctk.CTkLabel:
    """Rewrap a CTkLabel's text to its current width; pack it with fill="x"."""

    def rewrap(event) -> None:
        width = round(event.width / label._get_widget_scaling()) - 8
        if width > 50 and width != label.cget("wraplength"):
            label.configure(wraplength=width)

    label.configure(justify="left", anchor="w")
    # On the outer frame: CTkLabel.bind targets the inner text label, whose
    # width follows the text
    tk.Misc.bind(label, "<Configure>", rewrap, add="+")
    return label


class FlowRow(ctk.CTkFrame):
    """Transparent row of widgets that wraps onto more lines when narrow.

    Create the widgets with the row as master and add() them in order; the
    row grids them again whenever its width changes the line breaks.
    """

    def __init__(self, master, gap: int = 6, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self._gap = gap
        self._items: list = []
        self._lines: list[int] = []
        self._line_frames: list[ctk.CTkFrame] = []
        self.bind("<Configure>", lambda _e: self._reflow(), add="+")

    def add(self, *widgets) -> None:
        self._items.extend(widgets)
        self._lines = []
        self._reflow()

    def _reflow(self) -> None:
        width = self.winfo_width()
        if width <= 1:
            # Not mapped yet: one line, the real width arrives with <Configure>
            width = 1 << 30
        gap = round(self._apply_widget_scaling(self._gap))
        lines, used = [], 0
        for widget in self._items:
            w = widget.winfo_reqwidth()
            if not lines or used + gap + w > width:
                lines.append(0)
                used = w
            else:
                used += gap + w
            lines[-1] += 1
        if lines == self._lines:
            return
        self._lines = lines
        while len(self._line_frames) < len(lines):
            self._line_frames.append(ctk.CTkFrame(self, fg_color="transparent"))
        items = iter(self._items)
        for row, frame in enumerate(self._line_frames):
            if row >= len(lines):
                frame.pack_forget()
                continue
            frame.pack(fill="x", pady=(0 if row == 0 else self._gap, 0))
            for col in range(lines[row]):
                widget = next(items)
                widget.pack(
                    in_=frame, side="left", padx=(0 if col == 0 else self._gap, 0)
                )
                widget.lift(frame)


def collapsible(parent, title, build, *, expanded=False, pady=(10, 0)):
    """Section with a clickable title that shows or hides a gray box.

    build(box) fills the box once. The dialog is refitted on every toggle.
    """
    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.pack(fill=tk.X, pady=pady)
    body = ctk.CTkFrame(container, fg_color=BOX, corner_radius=8)
    build(body)
    state = {"open": expanded}

    def label() -> str:
        return f"{'▾' if state['open'] else '▸'}  {title}"

    def toggle() -> None:
        state["open"] = not state["open"]
        if state["open"]:
            body.pack(fill=tk.X, pady=(4, 0))
        else:
            body.pack_forget()
        toggle_button.configure(text=label())
        refit(container.winfo_toplevel())

    toggle_button = ctk.CTkButton(
        container,
        text=label(),
        command=toggle,
        font=BOLD,
        anchor="w",
        height=26,
        fg_color="transparent",
        hover_color=BOX,
        text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"],
    )
    toggle_button.pack(fill=tk.X)
    if expanded:
        body.pack(fill=tk.X, pady=(4, 0))
    return container


# Lists and tables sit in an inset well, darker than the panel around them
LIST_BG = ("gray97", "gray13")
# Row text and height in unscaled px, matching the app's 13 px labels
LIST_TEXT_PX = 13
LIST_ROW_PX = 26


def _list_font(box: ctk.CTkFrame, family: str = "Segoe UI") -> tuple[str, int]:
    """Font tuple in negative (pixel) size, scaled like CTk fonts."""
    return (family, -round(box._apply_widget_scaling(LIST_TEXT_PX)))


def themed_listbox(parent, **kwargs):
    """tk.Listbox in a rounded box with theme colors and a CTk scrollbar.

    Returns (box, listbox); the caller packs box. kwargs go to the listbox.
    """

    def pick(color):
        return box._apply_appearance_mode(color)

    box = ctk.CTkFrame(parent, corner_radius=8)
    bg = pick(LIST_BG)
    box.configure(fg_color=bg)
    fg = pick(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
    # CTkScrollbar requests 200 px by default; the box should follow the list
    sb = ctk.CTkScrollbar(box, height=40)
    sb.pack(side="right", fill="y", padx=(0, 3), pady=6)
    listbox = tk.Listbox(
        box,
        font=_list_font(box),
        bg=bg,
        fg=fg,
        selectbackground=palette.pick(palette.PURPLE_SELECT),
        selectforeground=fg,
        relief="flat",
        borderwidth=0,
        highlightthickness=0,
        activestyle="none",
        yscrollcommand=sb.set,
        **kwargs,
    )
    listbox.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=6)
    sb.configure(command=listbox.yview)
    return box, listbox


def themed_tree(parent, xscroll: bool = False, **kwargs):
    """ttk.Treeview styled like themed_listbox: rounded box, theme colors,
    CTk scrollbar (plus a horizontal one with xscroll). Returns (box, tree);
    the caller places box."""
    from tkinter import ttk

    box = ctk.CTkFrame(parent, corner_radius=8)
    bg = box._apply_appearance_mode(LIST_BG)
    box.configure(fg_color=bg)
    fg = box._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
    head_bg = box._apply_appearance_mode(("gray84", "gray24"))
    select = palette.pick(palette.PURPLE_SELECT)
    style = ttk.Style()
    name = "Themed.Treeview"
    style.configure(
        name,
        background=bg,
        fieldbackground=bg,
        foreground=fg,
        rowheight=round(box._apply_widget_scaling(LIST_ROW_PX)),
        borderwidth=0,
        font=_list_font(box),
    )
    style.configure(
        f"{name}.Heading",
        background=head_bg,
        foreground=fg,
        relief="flat",
        borderwidth=0,
        font=_list_font(box, "Segoe UI Semibold"),
    )
    style.map(f"{name}.Heading", background=[("active", head_bg)])
    style.map(name, background=[("selected", select)], foreground=[("selected", fg)])
    style.layout(name, [("Treeview.treearea", {"sticky": "nswe"})])

    # CTkScrollbar requests 200 px by default; the box should follow the list
    sb = ctk.CTkScrollbar(box, height=40)
    sb.pack(side="right", fill="y", padx=(0, 3), pady=6)
    tree = ttk.Treeview(box, style=name, yscrollcommand=sb.set, **kwargs)
    sb.configure(command=tree.yview)
    if xscroll:
        hsb = ctk.CTkScrollbar(
            box, orientation="horizontal", width=40, command=tree.xview
        )
        hsb.pack(side="bottom", fill="x", padx=(8, 0), pady=(0, 3))
        tree.configure(xscrollcommand=hsb.set)
    tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=6)
    return box, tree
