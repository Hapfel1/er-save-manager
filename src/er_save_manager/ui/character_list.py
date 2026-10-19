"""Character list of the Save Inspector tabs.

One gray card per character: the name, then values in fixed-width columns
under a heading row, then the issue status on the right. Every game uses the
same column order (columns()); a game leaves out the columns it has no data
for. Columns that do not fit the list width are hidden, highest drop value
first.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass, field

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.tooltip import add_tooltip
from er_save_manager.ui.utils import bind_mousewheel

NAME_WIDTH = 170
STATUS_WIDTH = 160
# Space between columns and the card's inner margins, before widget scaling
_GAP = 10
_MARGIN = 12


@dataclass(frozen=True)
class Column:
    key: str
    heading: str
    width: int
    # Hidden first when the list is too narrow; 0 never hides.
    drop: int = 0


@dataclass
class CharacterRow:
    slot: int  # 0-based slot index, shown 1-based
    name: str
    values: dict[str, str] = field(default_factory=dict)
    # None when the game has no issue check
    issues: list[str] | None = field(default_factory=list)


def columns(
    currency: str,
    *,
    level: bool = True,
    char_class: bool = True,
    ng_plus: bool = True,
    playtime: bool = True,
    extras: tuple[tuple[str, str, int], ...] = (),
) -> list[Column]:
    """Columns in the shared order: Slot, Level, Class, currency, NG+, Playtime,
    then the game's own (key, heading, width) extras."""
    cols = [Column("slot", "Slot", 40)]
    if level:
        cols.append(Column("level", "Level", 50))
    if char_class:
        cols.append(Column("class", "Class", 110, drop=2))
    cols.append(Column("currency", currency, 110, drop=1))
    if ng_plus:
        cols.append(Column("ng", "NG+", 50, drop=3))
    if playtime:
        cols.append(Column("playtime", "Playtime", 80, drop=4))
    cols += [
        Column(key, heading, width, drop=5 + i)
        for i, (key, heading, width) in enumerate(extras)
    ]
    return cols


def format_playtime(seconds: float | None) -> str:
    if seconds is None:
        return ""
    seconds = int(seconds)
    return f"{seconds // 3600}h {seconds % 3600 // 60:02d}m"


def _status(issues: list[str] | None) -> tuple[str, tuple[str, str] | None]:
    if issues is None:
        return "", None
    if not issues:
        return "✓  OK", ds.FOUND
    n = len(issues)
    return f"⚠  {n} issue{'s' if n != 1 else ''} detected", ds.WARNING


class CharacterList:
    """Scrollable character cards with single selection.

    on_select(slot) runs when a card is clicked, on_double(slot) on a
    double-click.
    """

    def __init__(
        self,
        parent,
        *,
        on_select: Callable[[int], None] | None = None,
        on_double: Callable[[int], None] | None = None,
    ) -> None:
        self.frame = ctk.CTkScrollableFrame(
            parent, width=900, height=320, corner_radius=10
        )
        bind_mousewheel(self.frame)
        self._on_select = on_select
        self._on_double = on_double
        self.selected: int | None = None
        self._columns: list[Column] = []
        self._cards: list[tuple[int, ctk.CTkFrame]] = []
        # Per grid line (heading first): column key -> label
        self._cells: list[dict[str, ctk.CTkLabel]] = []
        self._hidden: set[str] = set()
        self.frame._parent_canvas.bind("<Configure>", self._fit, add="+")

    def pack(self, **kwargs) -> None:
        self.frame.pack(**kwargs)

    def clear(self) -> None:
        for child in self.frame.winfo_children():
            child.destroy()
        self._cards.clear()
        self._cells.clear()
        self._hidden = set()
        self.selected = None

    def message(self, text: str) -> None:
        """Replace the list with one line of text."""
        self.clear()
        ctk.CTkLabel(self.frame, text=text, text_color=ds.MUTED).pack(
            anchor="w", padx=6, pady=6
        )

    def show(self, cols: list[Column], rows: list[CharacterRow]) -> None:
        """Fill the list and select the first row."""
        self.clear()
        self._columns = cols
        if not rows:
            self.message("No active characters found.")
            return
        heading = ctk.CTkFrame(self.frame, fg_color="transparent")
        heading.pack(fill=tk.X, padx=4, pady=(2, 0))
        self._cells.append(
            self._grid_line(
                heading,
                "Name",
                {c.key: c.heading for c in cols},
                ("Status", None) if any(r.issues is not None for r in rows) else None,
                font=ds.SMALL,
                name_color=ds.MUTED,
                value_color=ds.MUTED,
            )
        )
        for row in rows:
            card = ctk.CTkFrame(self.frame, fg_color=ds.CARD_ROW, corner_radius=8)
            card.pack(fill=tk.X, padx=4, pady=3)
            values = dict(row.values, slot=str(row.slot + 1))
            status = _status(row.issues)
            cells = self._grid_line(
                card,
                row.name,
                values,
                status if row.issues is not None else None,
                font=ds.BOLD,
                name_color=ds.ROW_TEXT,
                value_color=ds.MUTED,
            )
            if row.issues:
                add_tooltip(cells["_status"], "\n".join(f"•  {t}" for t in row.issues))
            for widget in (card, *cells.values()):
                widget.bind("<Button-1>", lambda _e, s=row.slot: self.select(s))
                if self._on_double:
                    widget.bind(
                        "<Double-Button-1>",
                        lambda _e, s=row.slot: self._on_double(s),
                    )
            self._cells.append(cells)
            self._cards.append((row.slot, card))
        self.select(rows[0].slot)
        self.frame.after_idle(self._fit)

    def _grid_line(
        self, parent, name, values, status, *, font, name_color, value_color
    ):
        cells: dict[str, ctk.CTkLabel] = {}
        pady = 7 if font == ds.BOLD else 0
        cells["_name"] = ctk.CTkLabel(
            parent, text=name, font=font, text_color=name_color,
            width=NAME_WIDTH, anchor="w",
        )  # fmt: skip
        cells["_name"].grid(row=0, column=0, padx=(_MARGIN, _GAP), pady=pady)
        for i, col in enumerate(self._columns, start=1):
            cells[col.key] = ctk.CTkLabel(
                parent, text=values.get(col.key, ""), font=ds.SMALL,
                text_color=value_color, width=col.width, anchor="w",
            )  # fmt: skip
            cells[col.key].grid(row=0, column=i, padx=(0, _GAP), pady=pady)
        parent.grid_columnconfigure(len(self._columns) + 1, weight=1)
        if status is not None:
            text, color = status
            cells["_status"] = ctk.CTkLabel(
                parent, text=text, font=ds.BOLD if color else font,
                text_color=color or value_color, width=STATUS_WIDTH, anchor="e",
            )  # fmt: skip
            cells["_status"].grid(
                row=0, column=len(self._columns) + 2, padx=(0, _MARGIN + 2), pady=pady
            )
        return cells

    def select(self, slot: int) -> None:
        self.selected = slot
        for value, card in self._cards:
            ds.select_card_row(card, value == slot)
        if self._on_select:
            self._on_select(slot)

    def _fit(self, _event=None) -> None:
        """Hide the columns that do not fit, highest drop value first."""
        if not self._cells:
            return
        heading = self._cells[0]
        available = self.frame._parent_canvas.winfo_width()
        if available <= 1:
            return
        scale = ctk.ScalingTracker.get_widget_scaling(self.frame)
        gap = round(_GAP * scale)
        widths = {c.key: heading[c.key].winfo_reqwidth() + gap for c in self._columns}
        needed = (
            round((2 * _MARGIN + 8 + _GAP + 2) * scale)
            + heading["_name"].winfo_reqwidth()
            + round(STATUS_WIDTH * scale)
            + sum(widths.values())
        )
        hidden = set()
        for col in sorted(self._columns, key=lambda c: -c.drop):
            if needed <= available or col.drop == 0:
                break
            hidden.add(col.key)
            needed -= widths[col.key]
        if hidden == self._hidden:
            return
        self._hidden = hidden
        for cells in self._cells:
            for col in self._columns:
                if col.key in hidden:
                    cells[col.key].grid_remove()
                else:
                    cells[col.key].grid()


def slot_issues(issues, slot: int) -> list[str] | None:
    """Texts of the save_check issues for one slot plus the save-wide ones;
    None when issues is None (no check ran)."""
    if issues is None:
        return None
    return [i.text for i in issues if i.slot in (slot, None)]
