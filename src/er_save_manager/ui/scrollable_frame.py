"""Vertical scroll container for editor tabs on small displays."""

from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

from er_save_manager.ui.utils import bind_mousewheel


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
        bind_mousewheel(self)

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
