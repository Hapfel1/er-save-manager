"""Toast notification system."""

import sys
import tkinter as tk

import customtkinter as ctk

_active_toasts: list[dict] = []

# On Windows each geometry() call triggers a DWM redraw; use alpha fade instead.
_USE_FADE = sys.platform == "win32"


def show_toast(root: tk.Tk, message: str, duration: int = 3000, type: str = "success"):
    """Show a stacking toast notification."""

    colors = {
        "success": {"bg": "#a6e3a1", "fg": "#11111b"},
        "info": {"bg": "#89b4fa", "fg": "#11111b"},
        "warning": {"bg": "#f9e2af", "fg": "#11111b"},
        "error": {"bg": "#f38ba8", "fg": "#11111b"},
    }
    theme = colors.get(type, colors["success"])

    # Keep the window invisible until fully positioned to avoid white flash.
    toast = ctk.CTkToplevel(root)
    toast.attributes("-alpha", 0)
    toast.withdraw()
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)
    toast.configure(fg_color=theme["bg"])

    label = ctk.CTkLabel(
        toast,
        text=message,
        text_color=theme["fg"],
        fg_color=theme["bg"],
        font=("Segoe UI", 12, "bold"),
        wraplength=400,
    )
    label.pack(padx=20, pady=12)

    # Measure size while still hidden.
    toast.update_idletasks()
    toast_width = toast.winfo_reqwidth()
    toast_height = toast.winfo_reqheight()

    root.update_idletasks()
    app_x = root.winfo_rootx()
    app_y = root.winfo_rooty()
    app_width = root.winfo_width()

    x = app_x + (app_width - toast_width) // 2
    base_y = app_y + 20
    spacing = 12

    y = base_y
    for t in _active_toasts:
        if t["toast"].winfo_exists():
            y = t["y"] + t["height"] + spacing

    toast_info: dict = {
        "toast": toast,
        "x": x,
        "y": y,
        "width": toast_width,
        "height": toast_height,
        "duration": duration,
    }
    _active_toasts.append(toast_info)

    # Position then show -- one geometry call before deiconify to prevent flash.
    toast.geometry(f"{toast_width}x{toast_height}+{x}+{y}")
    toast.deiconify()

    if _USE_FADE:
        _fade_in(toast, root, duration, toast_info)
    else:
        toast.attributes("-alpha", 0.96)
        _slide_in(toast, root, x, y, toast_width, toast_height, duration, toast_info)


def _fade_in(toast, root, duration, toast_info, step=0, steps=10):
    """Fade in by incrementing alpha -- avoids per-frame geometry calls on Windows."""
    if not toast.winfo_exists():
        return
    alpha = min(0.96, (step + 1) / steps * 0.96)
    toast.attributes("-alpha", alpha)
    if step + 1 < steps:
        root.after(
            16, lambda: _fade_in(toast, root, duration, toast_info, step + 1, steps)
        )
    else:
        root.after(duration, lambda: _dismiss(toast, root, toast_info))


def _slide_in(toast, root, x, y, w, h, duration, toast_info, step=0, steps=15):
    """Slide in from above (Linux -- geometry calls are cheap there)."""
    if not toast.winfo_exists():
        return
    start_y = y - 30
    progress = (step + 1) / steps
    eased = 1 - pow(1 - progress, 3)
    new_y = int(start_y + (y - start_y) * eased)
    toast.geometry(f"{w}x{h}+{x}+{new_y}")
    toast.attributes("-alpha", min(0.96, progress * 2))
    if step + 1 < steps:
        root.after(
            16,
            lambda: _slide_in(
                toast, root, x, y, w, h, duration, toast_info, step + 1, steps
            ),
        )
    else:
        root.after(duration, lambda: _dismiss(toast, root, toast_info))


def _dismiss(toast, root, toast_info):
    """Fade out and destroy."""
    if not toast.winfo_exists():
        _active_toasts.discard(toast_info) if hasattr(
            _active_toasts, "discard"
        ) else None
        return

    def fade_out(step=0, steps=8):
        if not toast.winfo_exists():
            return
        alpha = max(0.0, 0.96 * (1 - (step + 1) / steps))
        toast.attributes("-alpha", alpha)
        if step + 1 < steps:
            root.after(16, lambda: fade_out(step + 1, steps))
        else:
            if toast.winfo_exists():
                toast.destroy()
            if toast_info in _active_toasts:
                _active_toasts.remove(toast_info)
            _reposition_toasts(root)

    fade_out()

    toast.bind("<Button-1>", lambda e: None)  # block clicks during fade
    label_widget = toast.winfo_children()[0] if toast.winfo_children() else None
    if label_widget:
        label_widget.bind("<Button-1>", lambda e: None)


def show_toast_bound(root, toast, toast_info):
    """Bind click-to-dismiss after the toast is shown."""

    def on_click(e):
        _dismiss(toast, root, toast_info)

    if toast.winfo_exists():
        toast.bind("<Button-1>", on_click)
        for child in toast.winfo_children():
            child.bind("<Button-1>", on_click)


def _reposition_toasts(root):
    """Reposition remaining toasts after one is dismissed."""
    if not root.winfo_exists():
        return
    root.update_idletasks()
    app_x = root.winfo_rootx()
    app_y = root.winfo_rooty()
    app_width = root.winfo_width()
    base_y = app_y + 20
    spacing = 12
    current_y = base_y

    for info in _active_toasts:
        if not info["toast"].winfo_exists():
            continue
        new_x = app_x + (app_width - info["width"]) // 2
        new_y = current_y
        if info["y"] != new_y or info["x"] != new_x:
            if _USE_FADE:
                # Skip repositioning animation on Windows; just snap.
                info["toast"].geometry(
                    f"{info['width']}x{info['height']}+{new_x}+{new_y}"
                )
                info["x"] = new_x
                info["y"] = new_y
            else:
                _animate_reposition(
                    root,
                    info["toast"],
                    info["x"],
                    info["y"],
                    new_x,
                    new_y,
                    info["width"],
                    info["height"],
                    info,
                )
        current_y = new_y + info["height"] + spacing


def _animate_reposition(root, widget, sx, sy, ex, ey, w, h, info, step=0, steps=10):
    if not widget.winfo_exists():
        return
    progress = (step + 1) / steps
    eased = 1 - pow(1 - progress, 2)
    nx = int(sx + (ex - sx) * eased)
    ny = int(sy + (ey - sy) * eased)
    widget.geometry(f"{w}x{h}+{nx}+{ny}")
    if step + 1 < steps:
        root.after(
            16,
            lambda: _animate_reposition(
                root, widget, sx, sy, ex, ey, w, h, info, step + 1, steps
            ),
        )
    else:
        info["x"] = ex
        info["y"] = ey
