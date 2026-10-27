"""Toast notification system."""

import ctypes
import sys
import time
import tkinter as tk
from tkinter import font as tkfont

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from er_save_manager.ui import palette

# On Windows each geometry() call triggers a DWM redraw; use alpha fade instead.
_USE_FADE = sys.platform == "win32"

_RADIUS = 14
_MAX_TOASTS = 4
_TOP = 20
_SPACING = 12
_PAD_X = 18
_PAD_Y = 11
_WRAP = 400
_ALPHA = 0.96
# Time left after the pointer leaves a paused toast, at least.
_MIN_RESUME_MS = 1000
_SUPERSAMPLE = 4
# The window under a toast can change while it shows (tab switch, list fill).
_BACKDROP_REFRESH_MS = 250

_active_toasts: list["_Toast"] = []


class _XImage(ctypes.Structure):
    # Leading fields of Xlib's XImage, up to the color masks.
    _fields_ = [
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("xoffset", ctypes.c_int),
        ("format", ctypes.c_int),
        ("data", ctypes.c_void_p),
        ("byte_order", ctypes.c_int),
        ("bitmap_unit", ctypes.c_int),
        ("bitmap_bit_order", ctypes.c_int),
        ("bitmap_pad", ctypes.c_int),
        ("depth", ctypes.c_int),
        ("bytes_per_line", ctypes.c_int),
        ("bits_per_pixel", ctypes.c_int),
        ("red_mask", ctypes.c_ulong),
        ("green_mask", ctypes.c_ulong),
        ("blue_mask", ctypes.c_ulong),
    ]


_ZPIXMAP = 2
_LSB_FIRST = 0
_ALL_PLANES = 0xFFFFFFFF

_XErrorHandler = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)


class _XBackdrop:
    """Reads pixels of the app's own X window on a second connection.

    Compositors that ignore the X SHAPE extension (KWin on XWayland) draw
    cut-away corners black, and Tk paints 32-bit ARGB windows fully
    transparent, so a toast gets its round corners by compositing its body
    over the pixels of the window it covers."""

    def __init__(self):
        x11 = ctypes.CDLL("libX11.so.6")
        self.x11 = x11
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XGetImage.restype = ctypes.POINTER(_XImage)
        x11.XGetImage.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_ulong,
            ctypes.c_int,
        ]
        x11.XDestroyImage.argtypes = [ctypes.POINTER(_XImage)]
        x11.XSetErrorHandler.restype = ctypes.c_void_p
        x11.XSetErrorHandler.argtypes = [ctypes.c_void_p]
        self.display = x11.XOpenDisplay(None)
        if not self.display:
            raise OSError("no X display")

        # The default handler exits the process. Errors on this connection
        # (window gone or unmapped mid-read) only make the read return NULL;
        # errors on Tk's connection go to the handler Tk installed.
        previous = ctypes.c_void_p()

        def handler(display, event):
            if display == self.display:
                return 0
            if previous.value:
                return _XErrorHandler(previous.value)(display, event)
            return 0

        self._handler = _XErrorHandler(handler)
        previous.value = x11.XSetErrorHandler(
            ctypes.cast(self._handler, ctypes.c_void_p)
        )

    def grab(self, window_id: int, x: int, y: int, w: int, h: int):
        """RGB image of the rectangle, or None when it cannot be read."""
        ptr = self.x11.XGetImage(
            self.display, window_id, x, y, w, h, _ALL_PLANES, _ZPIXMAP
        )
        if not ptr:
            return None
        try:
            img = ptr.contents
            if (
                img.bits_per_pixel != 32
                or img.byte_order != _LSB_FIRST
                or img.red_mask != 0xFF0000
                or img.blue_mask != 0xFF
            ):
                return None
            data = ctypes.string_at(img.data, img.bytes_per_line * img.height)
            return Image.frombuffer(
                "RGB",
                (img.width, img.height),
                data,
                "raw",
                "BGRX",
                img.bytes_per_line,
                1,
            ).copy()
        finally:
            self.x11.XDestroyImage(ptr)


_backdrop: _XBackdrop | None = None
_backdrop_failed = False


def _get_backdrop() -> _XBackdrop | None:
    global _backdrop, _backdrop_failed
    if sys.platform in ("win32", "darwin"):
        return None
    if _backdrop is None and not _backdrop_failed:
        try:
            _backdrop = _XBackdrop()
        except (OSError, AttributeError):
            _backdrop_failed = True
    return _backdrop


def _hex(widget, color) -> str:
    r, g, b = widget.winfo_rgb(color)
    return f"#{r >> 8:02x}{g >> 8:02x}{b >> 8:02x}"


def _under_color(root) -> str:
    """Fill of the header card the toast covers: the corner color when the
    window behind cannot be read, and the transparent key on Windows."""
    fill = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
    if isinstance(fill, (list, tuple)):
        fill = fill[1] if ctk.get_appearance_mode() == "Dark" else fill[0]
    return _hex(root, fill)


def _body_image(w: int, h: int, radius: int, fill: str) -> Image.Image:
    """Rounded body on a transparent background, drawn at a larger size and
    box-filtered down: grayscale anti-aliasing. CTk corner_radius draws
    corners with a font glyph, which gets colored subpixel fringes on Linux."""
    s = _SUPERSAMPLE
    big = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, w * s - 1, h * s - 1), radius * s, fill=fill
    )
    return big.resize((w, h), Image.BOX)


class _Toast:
    def __init__(self, root, message: str, duration: int, type: str):
        self.root = root
        self.message = message
        self.type = type
        self.duration = duration
        self.count = 1
        self.dismissing = False
        self.x = self.y = 0
        self.w = self.h = 0
        self._timer = None
        self._deadline = 0.0
        self._remaining = duration
        self._anim = 0
        self._anim_done = True
        self._body = None
        self._photo = None
        self._backdrop_key = None

        scale = ctk.ScalingTracker.get_widget_scaling(root)
        self.scale = scale
        self.radius = round(_RADIUS * scale)
        self.fill = palette.TOAST_COLORS.get(type, palette.TOAST_COLORS["success"])
        self.under = _under_color(root)
        self.font = tkfont.Font(
            root=root, family="Inter", size=-round(12 * scale), weight="bold"
        )

        # Keep the window invisible until fully positioned to avoid white flash.
        self.win = tk.Toplevel(root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-alpha", 0)
        self.win.attributes("-topmost", True)
        if sys.platform == "win32":
            self.win.attributes("-transparentcolor", self.under)

        self.canvas = tk.Canvas(
            self.win, highlightthickness=0, bd=0, bg=self.under, cursor="hand2"
        )
        self.canvas.pack()
        self._image_item = self.canvas.create_image(0, 0, anchor="nw")
        self._text = self.canvas.create_text(
            0,
            0,
            anchor="nw",
            font=self.font,
            fill=palette.TOAST_TEXT,
            width=round(_WRAP * scale),
        )
        self.canvas.bind("<Button-1>", lambda e: self.dismiss())
        self.canvas.bind("<Enter>", lambda e: self._pause())
        self.canvas.bind("<Leave>", lambda e: self._resume())
        self._render()

    def _render(self):
        """Lay out the text and draw the body for the current count."""
        text = self.message if self.count == 1 else f"{self.message} (x{self.count})"
        self.canvas.itemconfigure(self._text, text=text)
        x0, y0, x1, y1 = self.canvas.bbox(self._text)
        pad_x, pad_y = round(_PAD_X * self.scale), round(_PAD_Y * self.scale)
        self.w = (x1 - x0) + 2 * pad_x
        self.h = (y1 - y0) + 2 * pad_y
        self.canvas.coords(self._text, pad_x, pad_y)
        self.canvas.configure(width=self.w, height=self.h)
        self._body = _body_image(
            self.w, self.h, min(self.radius, self.h // 2), self.fill
        )
        self._photo = None
        self._backdrop_key = None

    def _read_behind(self, x: int, y: int):
        """Pixels of the window under the toast at screen position (x, y);
        parts outside that window stay the under color."""
        backdrop = _get_backdrop()
        if backdrop is None:
            return None
        try:
            if not self.root.winfo_viewable():
                return None
            rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
            rw, rh = self.root.winfo_width(), self.root.winfo_height()
            window_id = self.root.winfo_id()
        except tk.TclError:
            return None
        left, top = max(x, rx), max(y, ry)
        right, bottom = min(x + self.w, rx + rw), min(y + self.h, ry + rh)
        if right <= left or bottom <= top:
            return None
        part = backdrop.grab(window_id, left - rx, top - ry, right - left, bottom - top)
        if part is None:
            return None
        if part.size == (self.w, self.h):
            return part
        img = Image.new("RGB", (self.w, self.h), self.under)
        img.paste(part, (left - x, top - y))
        return img

    def _paint(self, x: int, y: int, reread: bool = False):
        """Composite the body over what is behind (x, y) into the canvas."""
        if not self.win.winfo_exists():
            return
        key = (x, y, self.w, self.h)
        if key == self._backdrop_key and not reread and self._photo is not None:
            return
        behind = None if sys.platform == "win32" else self._read_behind(x, y)
        if behind is None:
            behind = Image.new("RGB", (self.w, self.h), self.under)
        behind.paste(self._body, (0, 0), self._body)
        if self._photo is not None and (
            self._photo.width(),
            self._photo.height(),
        ) == (self.w, self.h):
            self._photo.paste(behind)
        else:
            self._photo = ImageTk.PhotoImage(behind)
            self.canvas.itemconfigure(self._image_item, image=self._photo)
        self._backdrop_key = key

    def _place(self, x: int, y: int):
        self._paint(x, y)
        self.win.geometry(f"{self.w}x{self.h}+{x}+{y}")

    def _refresh_loop(self):
        if self.dismissing or not self.win.winfo_exists():
            return
        if self._anim_done:
            self._paint(self.x, self.y, reread=True)
        self.root.after(_BACKDROP_REFRESH_MS, self._refresh_loop)

    def show(self, x: int, y: int):
        self.x, self.y = x, y
        start_y = y if _USE_FADE else y - 30
        # Position then show - one geometry call before deiconify to prevent flash.
        self._place(x, start_y)
        self.win.deiconify()
        self._anim_done = True
        if _USE_FADE:
            self._fade_in()
        else:
            self.win.attributes("-alpha", _ALPHA)
            self._move(x, start_y, x, y, steps=15, ease=3)
        self._start_timer(self.duration)
        self.root.after(_BACKDROP_REFRESH_MS, self._refresh_loop)

    def bump(self):
        """Same message again: count it and restart the timer."""
        self.count += 1
        old_w = self.w
        self._render()
        self.x -= (self.w - old_w) // 2
        self._anim += 1
        self._anim_done = True
        self._place(self.x, self.y)
        if self._timer is not None:
            self._start_timer(self.duration)
        else:
            self._remaining = self.duration

    def _start_timer(self, ms: int):
        self._cancel_timer()
        self._deadline = time.monotonic() + ms / 1000
        self._timer = self.root.after(ms, self.dismiss)

    def _cancel_timer(self):
        if self._timer is not None:
            self.root.after_cancel(self._timer)
            self._timer = None

    def _pause(self):
        if self.dismissing or self._timer is None:
            return
        self._remaining = max(0, round((self._deadline - time.monotonic()) * 1000))
        self._cancel_timer()

    def _resume(self):
        if self.dismissing or self._timer is not None:
            return
        self._start_timer(max(self._remaining, _MIN_RESUME_MS))

    def _fade_in(self, step=0, steps=10):
        """Fade in by incrementing alpha - avoids per-frame geometry calls on Windows."""
        if self.dismissing or not self.win.winfo_exists():
            return
        self.win.attributes("-alpha", min(_ALPHA, (step + 1) / steps * _ALPHA))
        if step + 1 < steps:
            self.root.after(16, lambda: self._fade_in(step + 1, steps))

    def move_to(self, x: int, y: int):
        if (x, y) == (self.x, self.y):
            return
        sx, sy = self.x, self.y
        self.x, self.y = x, y
        if _USE_FADE:
            # Skip repositioning animation on Windows; just snap.
            self._anim += 1
            self._place(x, y)
        else:
            self._move(sx, sy, x, y, steps=10, ease=2)

    def _move(self, sx, sy, ex, ey, steps, ease):
        """Animate to (ex, ey); a newer move cancels this one."""
        self._anim += 1
        self._anim_done = False
        token = self._anim

        def step(i=0):
            if token != self._anim or not self.win.winfo_exists():
                return
            p = 1 - pow(1 - (i + 1) / steps, ease)
            self._place(round(sx + (ex - sx) * p), round(sy + (ey - sy) * p))
            if i + 1 < steps:
                self.root.after(16, lambda: step(i + 1))
            else:
                self._anim_done = True

        step()

    def dismiss(self):
        """Fade out and destroy."""
        if self.dismissing:
            return
        self.dismissing = True
        self._cancel_timer()
        self.canvas.unbind("<Button-1>")

        def fade_out(step=0, steps=8):
            if not self.win.winfo_exists():
                self._forget()
                return
            self.win.attributes("-alpha", max(0.0, _ALPHA * (1 - (step + 1) / steps)))
            if step + 1 < steps:
                self.root.after(16, lambda: fade_out(step + 1, steps))
            else:
                self.win.destroy()
                self._forget()

        fade_out()

    def _forget(self):
        if self in _active_toasts:
            _active_toasts.remove(self)
        _reposition_toasts(self.root)


def _app_geometry(root):
    # No update_idletasks(): it lays out the whole app first, 60-90 ms
    # right after a save load.
    return root.winfo_rootx(), root.winfo_rooty(), root.winfo_width()


def show_toast(root: tk.Tk, message: str, duration: int = 3000, type: str = "success"):
    """Show a stacking toast notification. A message that is already showing
    gets a counter instead of a second toast; at most _MAX_TOASTS are shown,
    the oldest goes first. Click dismisses, hovering pauses the timer."""
    _active_toasts[:] = [t for t in _active_toasts if t.win.winfo_exists()]

    for t in _active_toasts:
        if not t.dismissing and t.message == message and t.type == type:
            t.bump()
            _reposition_toasts(root)
            return

    live = [t for t in _active_toasts if not t.dismissing]
    for t in live[: max(0, len(live) - _MAX_TOASTS + 1)]:
        t.dismiss()

    toast = _Toast(root, message, duration, type)
    app_x, app_y, app_width = _app_geometry(root)
    y = app_y + _TOP
    for t in _active_toasts:
        y = max(y, t.y + t.h + _SPACING)
    _active_toasts.append(toast)
    toast.show(app_x + (app_width - toast.w) // 2, y)


def _reposition_toasts(root):
    """Restack the remaining toasts after one is dismissed or resized."""
    if not root.winfo_exists():
        return
    app_x, app_y, app_width = _app_geometry(root)
    y = app_y + _TOP
    for t in _active_toasts:
        if not t.win.winfo_exists():
            continue
        t.move_to(app_x + (app_width - t.w) // 2, y)
        y += t.h + _SPACING


def notify(parent, message: str, type: str = "info", duration: int = 3000):
    """Toast over the window that holds parent, or nothing once that window
    is closed."""
    try:
        root = parent.winfo_toplevel()
    except tk.TclError:
        return
    show_toast(root, message, duration, type)
