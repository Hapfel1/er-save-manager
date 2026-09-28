"""Vertical scroll container for editor tabs on small displays."""

from __future__ import annotations

import sys
from tkinter import TclError, ttk

import customtkinter as ctk


class ScrollableFrame(ctk.CTkScrollableFrame):
    """CTkScrollableFrame whose content fills the viewport when it fits.

    CTkScrollableFrame sizes its content to the requested height, so
    expanding children (Treeviews, PanedWindows) collapse to their minimum.
    This variant sets the content height to the larger of the viewport and
    the requested height: content stretches on large windows and scrolls on
    small ones.

    Wheel events over a ttk.Treeview scroll the tree, not the frame.
    Depends on CTkScrollableFrame internals (customtkinter 5.2.x).
    """

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        if sys.platform.startswith("linux"):
            # Tk 8.6 on X11 reports the wheel as Button-4/5, not <MouseWheel>.
            self.bind_all("<Button-4>", self._wheel_linux, add="+")
            self.bind_all("<Button-5>", self._wheel_linux, add="+")

    def _fit_frame_dimensions_to_canvas(self, event) -> None:
        super()._fit_frame_dimensions_to_canvas(event)
        if self._orientation == "vertical":
            self._parent_canvas.itemconfigure(
                self._create_window_id,
                height=max(self._parent_canvas.winfo_height(), self.winfo_reqheight()),
            )

    def _mouse_wheel_all(self, event) -> None:
        if isinstance(event.widget, ttk.Treeview):
            return
        super()._mouse_wheel_all(event)

    def _wheel_linux(self, event) -> None:
        try:
            if isinstance(event.widget, ttk.Treeview):
                return
            if not self.check_if_master_is_canvas(event.widget):
                return
            self._parent_canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
        except (AttributeError, TclError):
            # Widget path is a string, or this frame was destroyed.
            return
