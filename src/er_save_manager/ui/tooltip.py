"""Hover tooltips for widgets."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui import palette
from er_save_manager.ui.utils import get_work_area

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
    ) -> None:
        self.widget = widget
        self.text = text
        # Two-column table under text (key in the accent color), then footer
        self.rows = rows or []
        self.footer = footer
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
        bg, fg = _BG[pick], "gray90" if dark else "gray10"
        body = tk.Frame(frame, bg=bg, padx=8, pady=4)
        body.pack()
        tk.Label(
            body,
            text=self.text,
            justify="left",
            bg=bg,
            fg=fg,
            font=("Inter", -12, "bold") if self.rows else ("Inter", -12),
            wraplength=360,
        ).pack(anchor="w")
        if self.rows:
            table = tk.Frame(body, bg=bg)
            table.pack(anchor="w", pady=(4, 4))
            key_fg = palette.PURPLE_TEXT[pick]
            for r, (key, value) in enumerate(self.rows):
                tk.Label(
                    table, text=key, bg=bg, fg=key_fg, font=("Inter", -12, "bold")
                ).grid(row=r, column=0, sticky="w", padx=(0, 12))
                tk.Label(table, text=value, bg=bg, fg=fg, font=("Inter", -12)).grid(
                    row=r, column=1, sticky="w"
                )
        if self.footer:
            tk.Label(
                body,
                text=self.footer,
                justify="left",
                bg=bg,
                fg="gray70" if dark else "gray35",
                font=("Inter", -12),
                wraplength=360,
            ).pack(anchor="w")
        # Flip to the pointer's left (and above) when the tip would leave the
        # screen's usable area
        tip.update_idletasks()
        ax, ay, aw, ah = get_work_area(self.widget, (x, y))
        w, h = tip.winfo_reqwidth(), tip.winfo_reqheight()
        if x + w > ax + aw:
            x = max(ax, x - w - 28)
        if y + h > ay + ah:
            y = max(ay, y - h - 36)
        tip.wm_geometry(f"+{x}+{y}")
        self._tip = tip

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
