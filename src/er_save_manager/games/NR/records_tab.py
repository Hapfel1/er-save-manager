"""
Nightreign Records tab: the Visual Codex battle record of one character.

  Summary            - play time, expedition time, totals, win streaks
  Battle Record      - all-time totals and personal bests, normal and Depths
  Nightfarers        - expeditions and wins per hero
  Nightlords         - wins per Nightlord

Edits wait for Apply All. Play time is also written into the slot's
load-screen summary.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import (
    FieldTracker,
    PendingPage,
    StageCancelled,
    StageError,
    var_state,
)
from er_save_manager.ui.scrollable_frame import ScrollableFrame

from .records import (
    DEPTHS_ALL,
    DEPTHS_BEST,
    NORMAL_ALL,
    NORMAL_BEST,
    SUMMARY_FIELDS,
    U32_MAX,
    SlotRecords,
    read_records,
    write_records,
)

_PLAY_TIME = "play_time"
_NO_RECORDS = (
    "The records of this slot could not be located: its data does not match "
    "the layout the editor expects."
)
_ENTRY_WIDTH = 130


def _fmt_time(ms: int) -> str:
    seconds = ms // 1000
    return f"{seconds // 3600}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"


def _parse_time(text: str, label: str) -> int:
    """Milliseconds of an H:MM:SS value; StageError naming the field when the
    text is not a time or exceeds the u32 millisecond range."""
    parts = text.strip().split(":")
    try:
        if len(parts) != 3:
            raise ValueError
        h, m, s = (int(p) for p in parts)
    except ValueError:
        raise StageError(f"{label} must be a time as H:MM:SS.") from None
    if h < 0 or not 0 <= m < 60 or not 0 <= s < 60:
        raise StageError(f"{label} must be a time as H:MM:SS.")
    ms = ((h * 60 + m) * 60 + s) * 1000
    if ms > U32_MAX:
        raise StageError(f"{label} must be at most {_fmt_time(U32_MAX)}.")
    return ms


def _parse_count(text: str, label: str) -> int:
    try:
        value = int(text.strip().replace(",", ""))
    except ValueError:
        raise StageError(f"{label} must be a whole number.") from None
    if not 0 <= value <= U32_MAX:
        raise StageError(f"{label} must be between 0 and {U32_MAX:,}.")
    return value


class NRRecordsTab:
    """Records tab for the Nightreign character in the selected slot."""

    def __init__(
        self,
        parent,
        get_nr_save: Callable,
        pending_register: Callable[[str], Callable] | None = None,
    ) -> None:
        self.parent = parent
        self._get_nr_save = get_nr_save
        self._pending_register = pending_register
        self._current_slot = -1
        self._records: SlotRecords | None = None
        # tracked key -> (variable, label)
        self._vars: dict[str, tk.StringVar] = {}
        self._labels: dict[str, str] = {}
        self._entries: list[ctk.CTkEntry] = []
        # Rebuilt per character: a modded save can hold more heroes
        self._farer_keys: list[tuple[str, str]] = []
        self._lord_keys: list[str] = []

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))
        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(header, text="Records", font=("Inter", 16, "bold")).pack(
            side="left"
        )
        self._match_btn = ds.button(
            header, "Match Totals", self._match_totals, primary=False, width=130
        )
        self._match_btn.pack(side="right")
        self._totals_label = ctk.CTkLabel(
            header, text="", font=ds.SMALL, text_color=ds.MUTED
        )
        self._totals_label.pack(side="right", padx=(0, 10))

        self._body = ScrollableFrame(outer, fg_color="transparent")
        self._body.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self._locked = ds.wrap_to_width(
            ctk.CTkLabel(
                self._body,
                text=_NO_RECORDS,
                anchor="w",
                justify="left",
                text_color=ds.ERROR,
            )
        )

        title = "Battle Record - Summary"
        self._first_card = self._field_grid(
            title,
            [(_PLAY_TIME, "Play time")] + [(f.key, f.label) for f in SUMMARY_FIELDS],
        )
        for title, fields in (
            ("Battle Record - All", NORMAL_ALL),
            ("Battle Record - Personal Bests", NORMAL_BEST),
            ("Battle Record (Depths) - All", DEPTHS_ALL),
            ("Battle Record (Depths) - Personal Bests", DEPTHS_BEST),
        ):
            self._field_grid(title, [(f.key, f.label) for f in fields])

        self._tables = self._card("Battle Record - Character Usage and Victories")[1]

        self._tracker = FieldTracker(var_state(self._vars), self._labels)
        if self._pending_register is not None:
            self._pending_register("Records")(
                PendingPage(
                    "Records",
                    self._tracker.changes,
                    self._prepare,
                    self._refill,
                    None,
                    self._tracker.details,
                )
            )
        self._set_enabled(False)

    def _card(self, title: str) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
        """Titled card in the scroll body and the grid frame inside it."""
        card = ctk.CTkFrame(self._body, corner_radius=10, fg_color=("gray86", "gray22"))
        card.pack(fill="x", padx=4, pady=(0, 10))
        ctk.CTkLabel(card, text=title, font=("Inter", 14, "bold")).pack(
            anchor="w", padx=14, pady=(12, 6)
        )
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(anchor="nw", padx=14, pady=(0, 12))
        return card, grid

    def _add_field(
        self, grid, row: int, col: int, key: str, label: str, list_label: str
    ) -> None:
        """Label + entry at grid cell (row, col); col 0 or 1 of a two-column
        layout. list_label is the field name in the Review list."""
        var = tk.StringVar()
        self._vars[key] = var
        self._labels[key] = list_label
        ctk.CTkLabel(grid, text=label, anchor="w", width=230).grid(
            row=row, column=col * 2, sticky="w", padx=(0 if col == 0 else 30, 0), pady=3
        )
        entry = ctk.CTkEntry(grid, textvariable=var, width=_ENTRY_WIDTH)
        entry.grid(row=row, column=col * 2 + 1, sticky="w", padx=(6, 0), pady=3)
        self._entries.append(entry)

    def _field_grid(self, title: str, fields: list[tuple[str, str]]) -> ctk.CTkFrame:
        """Card of (key, label) fields in two columns, first half left;
        returns the card."""
        card, grid = self._card(title)
        half = (len(fields) + 1) // 2
        for i, (key, label) in enumerate(fields):
            col, row = divmod(i, half)
            self._add_field(grid, row, col, key, label, f"{title}: {label}")
        return card

    def _build_tables(self, rec: SlotRecords | None) -> None:
        """Nightfarer and Nightlord rows for this character's table sizes;
        None leaves the area empty."""
        for key in self._table_keys():
            self._vars.pop(key, None)
            self._labels.pop(key, None)
        for child in self._tables.winfo_children():
            child.destroy()
        self._entries = [e for e in self._entries if e.winfo_exists()]
        self._farer_keys, self._lord_keys = [], []
        if rec is None:
            return
        if not rec.nightfarers:
            ctk.CTkLabel(
                self._tables,
                text="The per-character tables of this slot could not be located.",
                text_color=ds.MUTED,
            ).grid(row=0, column=0, sticky="w")
            return
        for col, text in enumerate(("Nightfarer", "Expeditions", "Wins")):
            ctk.CTkLabel(self._tables, text=text, font=ds.BOLD, anchor="w").grid(
                row=0, column=col, sticky="w", padx=(0 if col == 0 else 6, 0)
            )
        for i, farer in enumerate(rec.nightfarers):
            exp_key, win_key = f"farer{i}_exp", f"farer{i}_wins"
            ctk.CTkLabel(self._tables, text=farer.name, anchor="w", width=150).grid(
                row=i + 1, column=0, sticky="w", pady=3
            )
            for col, (key, what) in enumerate(
                ((exp_key, "expeditions"), (win_key, "wins")), start=1
            ):
                var = tk.StringVar()
                self._vars[key] = var
                self._labels[key] = f"{farer.name} {what}"
                entry = ctk.CTkEntry(self._tables, textvariable=var, width=110)
                entry.grid(row=i + 1, column=col, sticky="w", padx=(6, 0), pady=3)
                self._entries.append(entry)
            self._farer_keys.append((exp_key, farer.name))

        if not rec.nightlords:
            return
        lord_col = 4
        ctk.CTkLabel(self._tables, text="Nightlord", font=ds.BOLD, anchor="w").grid(
            row=0, column=lord_col, sticky="w", padx=(40, 0)
        )
        ctk.CTkLabel(self._tables, text="Victories", font=ds.BOLD, anchor="w").grid(
            row=0, column=lord_col + 1, sticky="w", padx=(6, 0)
        )
        for i, lord in enumerate(rec.nightlords):
            key = f"lord{i}"
            ctk.CTkLabel(self._tables, text=lord.name, anchor="w", width=190).grid(
                row=i + 1, column=lord_col, sticky="w", padx=(40, 0), pady=3
            )
            var = tk.StringVar()
            self._vars[key] = var
            self._labels[key] = f"{lord.name} victories"
            entry = ctk.CTkEntry(self._tables, textvariable=var, width=110)
            entry.grid(row=i + 1, column=lord_col + 1, sticky="w", padx=(6, 0), pady=3)
            self._entries.append(entry)
            self._lord_keys.append(key)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_slot(self, slot_index: int) -> None:
        """Show the records of slot_index; -1 or an empty slot clears the tab."""
        save = self._get_nr_save()
        slot = None
        if save is not None and 0 <= slot_index < len(save.slots):
            slot = save.slots[slot_index]
        self._current_slot = slot_index if slot is not None else -1
        self._records = None
        if slot is None or slot.is_empty():
            self._show(None, clear=True)
            return
        self._records = read_records(slot)
        self._show(slot)

    def _refill(self) -> None:
        self.load_slot(self._current_slot)

    def _show(self, slot, clear: bool = False) -> None:
        rec = self._records
        if rec is None:
            self._build_tables(None)
            for var in self._vars.values():
                var.set("")
            if clear:
                self._locked.pack_forget()
            else:
                self._locked.pack(
                    fill="x", padx=8, pady=(0, 8), before=self._first_card
                )
            self._set_enabled(False)
            self._tracker.clear()
            self._update_totals()
            return
        self._locked.pack_forget()
        self._build_tables(rec)
        self._vars[_PLAY_TIME].set(_fmt_time(slot.play_time_ms))
        for f in SUMMARY_FIELDS + NORMAL_ALL + NORMAL_BEST + DEPTHS_ALL + DEPTHS_BEST:
            value = rec.values[f.key]
            self._vars[f.key].set(_fmt_time(value) if f.is_time else str(value))
        for (key, _name), farer in zip(self._farer_keys, rec.nightfarers, strict=True):
            self._vars[key].set(str(farer.expeditions))
            self._vars[key.replace("_exp", "_wins")].set(str(farer.wins))
        for key, lord in zip(self._lord_keys, rec.nightlords, strict=True):
            self._vars[key].set(str(lord.wins))
        for key in self._table_keys():
            self._vars[key].trace_add("write", lambda *_: self._update_totals())
        self._set_enabled(True)
        self._tracker.mark_clean()
        self._update_totals()

    def _table_keys(self) -> list[str]:
        keys = []
        for key, _ in self._farer_keys:
            keys += [key, key.replace("_exp", "_wins")]
        return keys + self._lord_keys

    def _set_enabled(self, on: bool) -> None:
        for entry in self._entries:
            if entry.winfo_exists():
                entry.configure(state="normal" if on else "disabled")
        self._match_btn.configure(
            state="normal" if on and self._farer_keys else "disabled"
        )

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------

    def _sums(self) -> tuple[int, int, int] | None:
        """(expeditions, Nightfarer wins, Nightlord wins) summed over the
        tables; None while a table field is not a whole number."""
        try:
            exp = sum(int(self._vars[k].get()) for k, _ in self._farer_keys)
            wins = sum(
                int(self._vars[k.replace("_exp", "_wins")].get())
                for k, _ in self._farer_keys
            )
            lords = sum(int(self._vars[k].get()) for k in self._lord_keys)
        except ValueError:
            return None
        return exp, wins, lords

    def _update_totals(self) -> None:
        sums = self._sums() if self._farer_keys else None
        if sums is None:
            self._totals_label.configure(text="")
            return
        exp, wins, lords = sums
        text = f"Table sums: {exp:,} expeditions, {wins:,} wins"
        if self._lord_keys and lords != wins:
            text += f" ({lords:,} Nightlord victories)"
        self._totals_label.configure(text=text)

    def _match_totals(self) -> None:
        """Set total expeditions and wins to the Nightfarer table sums."""
        sums = self._sums()
        if sums is None:
            CTkMessageBox.showerror(
                "Invalid Value",
                "Every Nightfarer and Nightlord field must be a whole number.",
                parent=self.parent,
            )
            return
        exp, wins, _lords = sums
        self._vars["total_expeditions"].set(str(exp))
        self._vars["wins"].set(str(wins))

    def _mismatch_lines(self, values: dict[str, int], farers, lords) -> list[str]:
        lines = []
        if farers:
            exp = sum(e for e, _ in farers)
            wins = sum(w for _, w in farers)
            if values["total_expeditions"] != exp:
                lines.append(
                    f"Total expeditions is {values['total_expeditions']:,}, the "
                    f"Nightfarer expeditions add up to {exp:,}."
                )
            if values["wins"] != wins:
                lines.append(
                    f"Wins is {values['wins']:,}, the Nightfarer wins add up to "
                    f"{wins:,}."
                )
        if lords and sum(lords) != values["wins"]:
            lines.append(
                f"Wins is {values['wins']:,}, the Nightlord victories add up to "
                f"{sum(lords):,}."
            )
        return lines

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------

    def _prepare(self):
        save = self._get_nr_save()
        rec = self._records
        if save is None or self._current_slot < 0 or rec is None:
            raise StageError("No character loaded.")
        slot = save.slots[self._current_slot]
        slot_index = self._current_slot

        play_ms = _parse_time(self._vars[_PLAY_TIME].get(), "Play time")
        values = {}
        for f in SUMMARY_FIELDS + NORMAL_ALL + NORMAL_BEST + DEPTHS_ALL + DEPTHS_BEST:
            text = self._vars[f.key].get()
            label = self._labels[f.key]
            values[f.key] = (
                _parse_time(text, label) if f.is_time else _parse_count(text, label)
            )
        farers = [
            (
                _parse_count(self._vars[k].get(), self._labels[k]),
                _parse_count(
                    self._vars[k.replace("_exp", "_wins")].get(),
                    self._labels[k.replace("_exp", "_wins")],
                ),
            )
            for k, _ in self._farer_keys
        ]
        lords = [
            _parse_count(self._vars[k].get(), self._labels[k]) for k in self._lord_keys
        ]
        if values["current_streak"] > values["win_streak"] or (
            values["current_streak_depths"] > values["win_streak_depths"]
        ):
            raise StageError("A current win streak cannot be longer than the best one.")

        mismatch = self._mismatch_lines(values, farers, lords)
        if mismatch and not CTkMessageBox.askyesno(
            "Totals Do Not Match",
            "\n".join(mismatch)
            + "\n\nThe game keeps these equal. Match Totals sets total "
            "expeditions and wins from the Nightfarer table.\n\nApply anyway?",
            parent=self.parent,
        ):
            raise StageCancelled

        def commit() -> None:
            from .character_ops import sync_summary_play_time

            slot.play_time_ms = play_ms
            sync_summary_play_time(save, slot_index)
            write_records(slot, rec, values, farers, lords)
            self._records = read_records(slot)

        return commit
