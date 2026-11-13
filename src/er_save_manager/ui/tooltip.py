"""Hover tooltips for widgets."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui import palette
from er_save_manager.ui.utils import get_monitor_area

_DELAY_MS = 500
_BG = ("gray90", "gray22")
_BORDER = ("gray70", "gray35")


class Tooltip:
    """Shows text in a small borderless window while the pointer rests on widget."""

    def __init__(
        self,
        widget,
        text: str,
        rows: list[tuple[str, str]] | None = None,
        footer: str = "",
        anchored: bool = False,
    ) -> None:
        self.widget = widget
        self.text = text
        # Anchored tips open under the widget, right-aligned to it, so they
        # stay over the window instead of following the pointer to a screen
        # edge (help icons at the right of a row)
        self.anchored = anchored
        # Two-column table under text (key in the accent color), then footer
        self.rows = rows or []
        self.footer = footer
        self._job: str | None = None
        self._tip: tk.Toplevel | None = None
        for target in self._targets(widget):
            target.bind("<Enter>", self._schedule, add="+")
            target.bind("<Leave>", self._on_leave, add="+")
            target.bind("<ButtonPress>", self._hide, add="+")

    @staticmethod
    def _targets(widget) -> list:
        # CTk widgets draw on inner canvases/labels that get the pointer events
        inner = [
            getattr(widget, name, None)
            for name in ("_canvas", "_label", "_text_label", "_image_label", "_entry")
        ]
        return [widget, *(w for w in inner if w is not None)]

    def _schedule(self, _event=None) -> None:
        if self._tip is not None:
            # Moved between the widget's inner parts; the tip stays
            return
        self._cancel()
        self._job = self.widget.after(_DELAY_MS, self._show)

    def _on_leave(self, _event=None) -> None:
        """Hide unless the pointer only moved onto another part of the
        widget (a CTk widget is a frame with a canvas and a label on top)."""
        try:
            x, y = self.widget.winfo_pointerxy()
            under = self.widget.winfo_containing(x, y)
        except (tk.TclError, KeyError):
            under = None
        while under is not None:
            if under is self.widget:
                return
            under = under.master
        self._hide()

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
        # Hidden until sized and placed, so it never shows off screen first
        tip.withdraw()
        tip.wm_overrideredirect(True)
        # Pixel sizes follow the UI scaling of the widget's window (Windows
        # display scaling), as CTk widgets do
        scale = ctk.ScalingTracker.get_widget_scaling(self.widget)
        font = ("Inter", -round(12 * scale))
        bold = (*font, "bold")
        wrap = round(360 * scale)
        dark = ctk.get_appearance_mode() == "Dark"
        pick = 1 if dark else 0
        frame = tk.Frame(tip, bg=_BORDER[pick], padx=1, pady=1)
        frame.pack()
        bg, fg = _BG[pick], "gray90" if dark else "gray10"
        body = tk.Frame(frame, bg=bg, padx=round(8 * scale), pady=round(4 * scale))
        body.pack()
        tk.Label(
            body,
            text=self.text,
            justify="left",
            bg=bg,
            fg=fg,
            font=bold if self.rows else font,
            wraplength=wrap,
        ).pack(anchor="w")
        if self.rows:
            table = tk.Frame(body, bg=bg)
            table.pack(anchor="w", pady=(4, 4))
            key_fg = palette.PURPLE_TEXT[pick]
            for r, (key, value) in enumerate(self.rows):
                tk.Label(table, text=key, bg=bg, fg=key_fg, font=bold).grid(
                    row=r, column=0, sticky="w", padx=(0, round(12 * scale))
                )
                tk.Label(table, text=value, bg=bg, fg=fg, font=font).grid(
                    row=r, column=1, sticky="w"
                )
        if self.footer:
            tk.Label(
                body,
                text=self.footer,
                justify="left",
                bg=bg,
                fg="gray70" if dark else "gray35",
                font=font,
                wraplength=wrap,
            ).pack(anchor="w")
        tip.update_idletasks()
        w, h = tip.winfo_reqwidth(), tip.winfo_reqheight()
        x, y = self._position(x, y, w, h)
        tip.wm_geometry(f"+{x}+{y}")
        tip.deiconify()
        tip.lift()
        self._tip = tip

    def _position(self, x: int, y: int, w: int, h: int) -> tuple[int, int]:
        """Top-left of a w x h tip, inside the usable screen area.

        Pointer tips flip to the pointer's left (and above) at an edge.
        Anchored tips sit under the widget, right-aligned to it, or above it
        when there is no room below, and do not pass the window's left edge.
        """
        widget = self.widget
        if self.anchored:
            wx, wy = widget.winfo_rootx(), widget.winfo_rooty()
            x = wx + widget.winfo_width() - w
            y = wy + widget.winfo_height() + 6
            ax, ay, aw, ah = get_monitor_area(widget, (wx, wy))
            if y + h > ay + ah:
                y = wy - h - 6
            x = max(x, widget.winfo_toplevel().winfo_rootx())
        else:
            ax, ay, aw, ah = get_monitor_area(widget, (x, y))
            if x + w > ax + aw:
                x = x - w - 28
            if y + h > ay + ah:
                y = y - h - 36
        x = min(max(x, ax), ax + aw - w)
        y = min(max(y, ay), ay + ah - h)
        return x, y

    def show_text(self, text: str) -> None:
        """Hide the current tip and show text after the hover delay, for a
        widget that draws several items (canvas cells) with their own text."""
        self._hide()
        self.text = text
        if text:
            self._schedule()

    def show_now(self, _event=None) -> None:
        """Show at once (click on a help icon), without the hover delay."""
        self._hide()
        self._show()

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
