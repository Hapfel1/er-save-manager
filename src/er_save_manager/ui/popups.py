"""Popups that show save data and are rebuilt after the save is reloaded.

An opener decorated with @reopenable tags every window it creates with a
call that opens it again. reopen() replaces each tagged window that is
still open with a fresh one at the same position, so it shows the reloaded
save instead of the data it was built from.
"""

from __future__ import annotations

import functools
import tkinter as tk
from collections.abc import Callable

_REOPEN = "_er_reopen"


def _toplevels(root: tk.Misc) -> set[tk.Toplevel]:
    found: set[tk.Toplevel] = set()
    stack = list(root.winfo_children())
    while stack:
        w = stack.pop()
        if isinstance(w, tk.Toplevel):
            found.add(w)
        stack.extend(w.winfo_children())
    return found


def reopenable(opener: Callable) -> Callable:
    """Tag the windows a popup opener creates so reopen() can rebuild them."""

    @functools.wraps(opener)
    def wrapper(self, *args, **kwargs):
        root = tk._get_default_root()
        before = _toplevels(root)
        result = opener(self, *args, **kwargs)
        for window in _toplevels(root) - before:
            setattr(window, _REOPEN, lambda: wrapper(self, *args, **kwargs))
        return result

    return wrapper


def open_popups(root: tk.Misc) -> list[tk.Toplevel]:
    """Tagged popups that are open now."""
    return [w for w in _toplevels(root) if hasattr(w, _REOPEN) and w.winfo_exists()]


def reopen(windows: list[tk.Toplevel]) -> None:
    """Close each window and open it again at its old position."""
    root = tk._get_default_root()
    for window in windows:
        if not window.winfo_exists():
            continue
        again = getattr(window, _REOPEN)
        x, y = window.winfo_x(), window.winfo_y()
        window.destroy()
        before = _toplevels(root)
        again()
        for new in _toplevels(root) - before:
            new.update_idletasks()
            # Plain Tk geometry: winfo positions are already physical pixels,
            # CTkToplevel.geometry() would scale them again.
            tk.Toplevel.wm_geometry(new, f"+{x}+{y}")
