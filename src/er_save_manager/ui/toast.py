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

_active_toasts: list["_Toast"] = []


class _XShape:
    """Cuts an X11 window to a 1-bit mask through libXext (XWayland included)."""

    def __init__(self):
        self.x11 = ctypes.CDLL("libX11.so.6")
        self.xext = ctypes.CDLL("libXext.so.6")
        x11, xext = self.x11, self.xext
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XCreateBitmapFromData.restype = ctypes.c_ulong
        x11.XCreateBitmapFromData.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_char_p,
            ctypes.c_uint,
            ctypes.c_uint,
        ]
        x11.XFreePixmap.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XFlush.argtypes = [ctypes.c_void_p]
        xext.XShapeQueryExtension.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
        ]
        xext.XShapeCombineMask.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.c_int,
        ]
        self.display = x11.XOpenDisplay(None)
        if not self.display:
            raise OSError("no X display")
        event_base, error_base = ctypes.c_int(), ctypes.c_int()
        if not xext.XShapeQueryExtension(
            self.display, ctypes.byref(event_base), ctypes.byref(error_base)
        ):
            raise OSError("no SHAPE extension")

    def apply(self, window_id: int, mask: Image.Image):
        w, h = mask.size
        # XBM layout: least significant bit first, rows padded to whole bytes.
        data = mask.tobytes("raw", "1;R")
        bitmap = self.x11.XCreateBitmapFromData(self.display, window_id, data, w, h)
        # ShapeBounding, ShapeSet
        self.xext.XShapeCombineMask(self.display, window_id, 0, 0, 0, bitmap, 0)
        self.x11.XFreePixmap(self.display, bitmap)
        self.x11.XFlush(self.display)


_xshape: _XShape | None = None
_xshape_failed = False


def _get_xshape() -> _XShape | None:
    global _xshape, _xshape_failed
    if _xshape is None and not _xshape_failed:
        try:
            _xshape = _XShape()
        except (OSError, AttributeError):
            _xshape_failed = True
    return _xshape


def _can_round() -> bool:
    if sys.platform == "win32":
        return True
    if sys.platform == "darwin":
        return False
    return _get_xshape() is not None


def _hex(widget, color) -> str:
    r, g, b = widget.winfo_rgb(color)
    return f"#{r >> 8:02x}{g >> 8:02x}{b >> 8:02x}"


def _under_color(root) -> str:
    """Fill of the header card the toast covers. The rounded edge is blended
    into it, and on Windows it is the transparent key."""
    fill = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
    if isinstance(fill, (list, tuple)):
        fill = fill[1] if ctk.get_appearance_mode() == "Dark" else fill[0]
    return _hex(root, fill)


def _body_image(w: int, h: int, radius: int, fill: str, under: str) -> Image.Image:
    """Rounded body drawn at a larger size and box-filtered down: grayscale
    anti-aliasing. CTk corner_radius draws corners with a font glyph, which
    gets colored subpixel fringes on Linux."""
    s = _SUPERSAMPLE
    big = Image.new("RGB", (w * s, h * s), under)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, w * s - 1, h * s - 1), radius * s, fill=fill
    )
    return big.resize((w, h), Image.BOX)


def _outline_mask(w: int, h: int, radius: int) -> Image.Image:
    """Window shape; keeps every pixel the body touches so its anti-aliased
    edge stays visible."""
    s = _SUPERSAMPLE
    big = Image.new("L", (w * s, h * s), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, w * s - 1, h * s - 1), radius * s, fill=255
    )
    small = big.resize((w, h), Image.BOX)
    return small.point(lambda v: 255 if v else 0).convert("1")


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
        self._image = None

        scale = ctk.ScalingTracker.get_widget_scaling(root)
        self.scale = scale
        self.radius = round(_RADIUS * scale) if _can_round() else 0
        self.fill = palette.TOAST_COLORS.get(type, palette.TOAST_COLORS["success"])
        self.under = _under_color(root)

        # Keep the window invisible until fully positioned to avoid white flash.
        self.win = tk.Toplevel(root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-alpha", 0)
        self.win.attributes("-topmost", True)
        if sys.platform == "win32" and self.radius:
            self.win.attributes("-transparentcolor", self.under)

        self.font = tkfont.Font(
            root=root, family="Inter", size=-round(12 * scale), weight="bold"
        )
        self.canvas = tk.Canvas(
            self.win, highlightthickness=0, bd=0, bg=self.under, cursor="hand2"
        )
        self.canvas.pack()
        self._body = self.canvas.create_image(0, 0, anchor="nw")
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
        """Lay out the text and redraw the body for the current count."""
        text = self.message if self.count == 1 else f"{self.message} (x{self.count})"
        self.canvas.itemconfigure(self._text, text=text)
        x0, y0, x1, y1 = self.canvas.bbox(self._text)
        pad_x, pad_y = round(_PAD_X * self.scale), round(_PAD_Y * self.scale)
        self.w = (x1 - x0) + 2 * pad_x
        self.h = (y1 - y0) + 2 * pad_y
        self.canvas.coords(self._text, pad_x, pad_y)
        self.canvas.configure(width=self.w, height=self.h)
        radius = min(self.radius, self.h // 2)
        if radius:
            body = _body_image(self.w, self.h, radius, self.fill, self.under)
        else:
            body = Image.new("RGB", (self.w, self.h), self.fill)
        self._image = ImageTk.PhotoImage(body)
        self.canvas.itemconfigure(self._body, image=self._image)

    def _shape(self):
        radius = min(self.radius, self.h // 2)
        if not radius or sys.platform == "win32":
            return
        xshape = _get_xshape()
        frame = self.win.wm_frame()
        if xshape and frame:
            xshape.apply(int(frame, 16), _outline_mask(self.w, self.h, radius))

    def show(self, x: int, y: int):
        self.x, self.y = x, y
        start_y = y if _USE_FADE else y - 30
        # Position then show - one geometry call before deiconify to prevent flash.
        self.win.geometry(f"{self.w}x{self.h}+{x}+{start_y}")
        self.win.deiconify()
        self.win.update_idletasks()
        self._shape()
        if _USE_FADE:
            self._fade_in()
        else:
            self.win.attributes("-alpha", _ALPHA)
            self._move(x, start_y, x, y, steps=15, ease=3)
        self._start_timer(self.duration)

    def bump(self):
        """Same message again: count it and restart the timer."""
        self.count += 1
        self._render()
        self.win.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")
        self._shape()
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
            self.win.geometry(f"{self.w}x{self.h}+{x}+{y}")
        else:
            self._move(sx, sy, x, y, steps=10, ease=2)

    def _move(self, sx, sy, ex, ey, steps, ease):
        """Animate to (ex, ey); a newer move cancels this one."""
        self._anim += 1
        token = self._anim

        def step(i=0):
            if token != self._anim or not self.win.winfo_exists():
                return
            p = 1 - pow(1 - (i + 1) / steps, ease)
            nx = round(sx + (ex - sx) * p)
            ny = round(sy + (ey - sy) * p)
            self.win.geometry(f"{self.w}x{self.h}+{nx}+{ny}")
            if i + 1 < steps:
                self.root.after(16, lambda: step(i + 1))

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
    root.update_idletasks()
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
