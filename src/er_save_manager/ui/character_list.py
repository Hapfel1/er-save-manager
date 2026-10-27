"""Character list of the Save Inspector tabs.

One gray card per character: the name, then values in fixed-width columns
under a heading row, then the issue status on the right. Every game uses the
same column order (columns()); a game leaves out the columns it has no data
for. Columns that do not fit the list width are hidden, highest drop value
first.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
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


def _elide(label: ctk.CTkLabel, text: str) -> str:
    """Show text in label, cut with an ellipsis when it is wider than the
    name column. A CTkLabel grows with its text, so a long name would push
    the row's other columns right. Returns the tooltip text: the full text
    when it was cut, else ""."""
    font = tkfont.Font(font=label._label.cget("font"))
    limit = round(NAME_WIDTH * ctk.ScalingTracker.get_widget_scaling(label))
    if font.measure(text) <= limit:
        label.configure(text=text)
        return ""
    cut = len(text)
    while cut > 1 and font.measure(text[:cut] + "…") > limit:
        cut -= 1
    label.configure(text=text[:cut].rstrip() + "…")
    return text


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
        # Slot of each card, read by the cards' click bindings so a refresh
        # with the same layout can reuse the cards
        self._slots: list[int] = []
        # (columns, row count, status shown) of the cards on screen
        self._layout: tuple | None = None
        # Pending after() job that adds the next card, see show()
        self._build_job = None
        self.frame._parent_canvas.bind("<Configure>", self._fit, add="+")

    def pack(self, **kwargs) -> None:
        self.frame.pack(**kwargs)

    def clear(self) -> None:
        if self._build_job is not None:
            self.frame.after_cancel(self._build_job)
            self._build_job = None
        for child in self.frame.winfo_children():
            child.destroy()
        self._cards.clear()
        self._cells.clear()
        self._slots.clear()
        self._layout = None
        self._hidden = set()
        self.selected = None

    def message(self, text: str) -> None:
        """Replace the list with one line of text."""
        self.clear()
        ctk.CTkLabel(self.frame, text=text, text_color=ds.MUTED).pack(
            anchor="w", padx=6, pady=6
        )

    def show(self, cols: list[Column], rows: list[CharacterRow]) -> None:
        """Fill the list and select the first row. Cards are reused when the
        columns, row count and status column match the shown list."""
        layout = (tuple(cols), len(rows), any(r.issues is not None for r in rows))
        if rows and layout == self._layout:
            for n, row in enumerate(rows):
                self._fill_line(self._cells[n + 1], row)
                self._slots[n] = row.slot
                self._cards[n] = (row.slot, self._cards[n][1])
            self.select(rows[0].slot)
            return
        self.clear()
        self._columns = cols
        if not rows:
            self.message("No active characters found.")
            return
        heading = ctk.CTkFrame(self.frame, fg_color="transparent")
        heading.pack(fill=tk.X, padx=4, pady=(2, 0))
        cells = self._grid_line(
            heading,
            layout[2],
            font=ds.SMALL,
            name_color=ds.MUTED,
            value_color=ds.MUTED,
        )
        cells["_name"].configure(text="Name")
        for c in cols:
            cells[c.key].configure(text=c.heading)
        if "_status" in cells:
            cells["_status"].configure(text="Status")
        self._cells.append(cells)
        # The first card now, the others one per event loop turn: building
        # every card (about ten CTkLabels each) at once froze the window
        self._add_card(0, rows[0], layout[2])
        self.select(rows[0].slot)
        if len(rows) > 1:
            self._build_job = self.frame.after(1, self._add_cards, rows, 1, layout)
        else:
            self._layout = layout
        self.frame.after_idle(self._fit)

    def _add_cards(self, rows: list[CharacterRow], n: int, layout: tuple) -> None:
        self._build_job = None
        if not self.frame.winfo_exists():
            return
        self._add_card(n, rows[n], layout[2])
        if n + 1 < len(rows):
            self._build_job = self.frame.after(1, self._add_cards, rows, n + 1, layout)
        else:
            self._layout = layout

    def _add_card(self, n: int, row: CharacterRow, status: bool) -> None:
        card = ctk.CTkFrame(self.frame, fg_color=ds.CARD_ROW, corner_radius=8)
        card.pack(fill=tk.X, padx=4, pady=3)
        cells = self._grid_line(
            card,
            status,
            font=ds.BOLD,
            name_color=ds.ROW_TEXT,
            value_color=ds.MUTED,
        )
        for key in ("_name", "_status"):
            if key in cells:
                add_tooltip(cells[key], "")
        self._fill_line(cells, row)
        for widget in (card, *cells.values()):
            widget.bind("<Button-1>", lambda _e, n=n: self.select(self._slots[n]))
            if self._on_double:
                widget.bind(
                    "<Double-Button-1>",
                    lambda _e, n=n: self._on_double(self._slots[n]),
                )
        # Columns _fit hid before this card existed
        for key in self._hidden:
            cells[key].grid_remove()
        ds.select_card_row(card, row.slot == self.selected)
        self._cells.append(cells)
        self._cards.append((row.slot, card))
        self._slots.append(row.slot)

    def _fill_line(self, cells: dict[str, ctk.CTkLabel], row: CharacterRow) -> None:
        """Texts of one character card."""
        cells["_name"]._tooltip.text = _elide(cells["_name"], row.name)
        values = dict(row.values, slot=str(row.slot + 1))
        for col in self._columns:
            cells[col.key].configure(text=values.get(col.key, ""))
        if "_status" in cells:
            text, color = _status(row.issues)
            cells["_status"].configure(
                text=text,
                font=ds.BOLD,
                text_color=color or ds.MUTED,
            )
            cells["_status"]._tooltip.text = "\n".join(
                f"•  {t}" for t in row.issues or ()
            )

    def _grid_line(self, parent, status: bool, *, font, name_color, value_color):
        """Empty labels of one grid line: name, the columns, and the status
        when status is set."""
        cells: dict[str, ctk.CTkLabel] = {}
        pady = 7 if font == ds.BOLD else 0
        cells["_name"] = ctk.CTkLabel(
            parent, text="", font=font, text_color=name_color,
            width=NAME_WIDTH, anchor="w",
        )  # fmt: skip
        cells["_name"].grid(row=0, column=0, padx=(_MARGIN, _GAP), pady=pady)
        for i, col in enumerate(self._columns, start=1):
            cells[col.key] = ctk.CTkLabel(
                parent, text="", font=ds.SMALL,
                text_color=value_color, width=col.width, anchor="w",
            )  # fmt: skip
            cells[col.key].grid(row=0, column=i, padx=(0, _GAP), pady=pady)
        parent.grid_columnconfigure(len(self._columns) + 1, weight=1)
        if status:
            cells["_status"] = ctk.CTkLabel(
                parent, text="", font=font,
                text_color=value_color, width=STATUS_WIDTH, anchor="e",
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
