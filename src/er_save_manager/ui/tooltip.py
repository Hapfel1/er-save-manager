"""Hover tooltips for widgets."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

_DELAY_MS = 500
_BG = ("gray90", "gray22")
_BORDER = ("gray70", "gray35")


class Tooltip:
    """Shows text in a small borderless window while the pointer rests on widget."""

    def __init__(self, widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self._job: str | None = None
        self._tip: tk.Toplevel | None = None
        for target in self._targets(widget):
            target.bind("<Enter>", self._schedule, add="+")
            target.bind("<Leave>", self._hide, add="+")
            target.bind("<ButtonPress>", self._hide, add="+")

    @staticmethod
    def _targets(widget) -> list:
        # CTk widgets draw on inner canvases/labels that get the pointer events
        inner = [
            getattr(widget, name, None)
            for name in ("_canvas", "_text_label", "_image_label", "_entry")
        ]
        return [widget, *(w for w in inner if w is not None)]

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._job = self.widget.after(_DELAY_MS, self._show)

    def _cancel(self) -> None:
        if self._job is not None:
            self.widget.after_cancel(self._job)
            self._job = None

    def _show(self) -> None:
        self._job = None
        if self._tip is not None or not self.text or not self.widget.winfo_exists():
            return
        x = self.widget.winfo_pointerx() + 14
        y = self.widget.winfo_pointery() + 18
        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        dark = ctk.get_appearance_mode() == "Dark"
        pick = 1 if dark else 0
        frame = tk.Frame(tip, bg=_BORDER[pick], padx=1, pady=1)
        frame.pack()
        tk.Label(
            frame,
            text=self.text,
            justify="left",
            bg=_BG[pick],
            fg="gray90" if dark else "gray10",
            font=("Inter", -12),
            padx=8,
            pady=4,
            wraplength=360,
        ).pack()
        self._tip = tip

    def show_text(self, text: str) -> None:
        """Hide the current tip and show text after the hover delay, for a
        widget that draws several items (canvas cells) with their own text."""
        self._hide()
        self.text = text
        if text:
            self._schedule()

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None


def add_tooltip(widget, text: str) -> Tooltip:
    """Attach a hover tooltip to widget and return it."""
    tip = Tooltip(widget, text)
    widget._tooltip = tip
    return tip


MULTI_SELECT_TIP = "Ctrl+click adds or removes a row, Shift+click selects a range."
