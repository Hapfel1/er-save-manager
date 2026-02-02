"""Scrollable frame widget for CustomTkinter."""

import customtkinter as ctk


class ScrollableFrame(ctk.CTkScrollableFrame):
    """A scrollable frame widget."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
