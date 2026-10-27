"""
Nightreign character tabs.

  Character Editor - player name, murk, sovereign sigils
  Relics           - searchable icon grid with color / Deep filters, detail
                     pane that edits the selected relic or spawns a new one
                     (icon pickers), remove, copy to new relic, JSON
                     import/export
  Loadouts         - chalice / preset icon grid per hero, detail pane with
                     one card per relic slot (icon picker of the relics that
                     fit), preset rename/create/delete, loadout chunk budget
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.dialogs.opt_out_warning import confirm_warning
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import (
    FieldTracker,
    PendingPage,
    StageCancelled,
    StageError,
    var_state,
)
from er_save_manager.ui.toast import notify
from er_save_manager.ui.tooltip import add_tooltip
from er_save_manager.ui.utils import game_blocks_write


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(parent, "nightreign.exe", "Elden Ring Nightreign")


_EMPTY_EFFECT = 0xFFFFFFFF
# Upper bound for Murk and Sovereign Sigils: FromSoftware's usual currency
# cap. The game's own cap for these is not confirmed.
_MAX_CURRENCY = 999_999_999
# Hero selector entry for modded hero vessels whose ID maps to no hero
_MODDED_HERO_LABEL = "Modded (no hero)"


def _backup_and_save(nr_save, save_path: Path, op: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=op, save=None)
    nr_save.write_file(save_path)


def _parse_int(s: str) -> int:
    s = s.strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def _fmt_effect(effect_id: int) -> str:
    from er_save_manager.games.NR.item_db import effect_name

    return effect_name(effect_id)


class _PickerDialog(ctk.CTkToplevel):
    """Modal searchable list for picking a relic or effect ID. icon(id)
    gives a row's PIL icon."""

    def __init__(
        self,
        parent,
        title: str,
        items: list[tuple[int, str]],
        current: int = -1,
        icon: Callable | None = None,
        width: int = 540,
    ):
        super().__init__(parent)
        from er_save_manager.ui import dialog_style as ds

        self.withdraw()
        self.attributes("-alpha", 0)
        self.title(title)
        self.transient(parent)
        self.resizable(True, True)

        self.result: int | None = None
        self._items = items
        self._icon = icon

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=16)
        btn_row = ctk.CTkFrame(main, fg_color="transparent")
        btn_row.pack(side="bottom", fill="x", pady=(12, 0))
        ds.header(main, title, font=ds.TITLE_LARGE)

        search_var = tk.StringVar()
        search_var.trace_add("write", lambda *_: self._filter(search_var.get()))
        search = ctk.CTkEntry(
            main,
            textvariable=search_var,
            placeholder_text="Search name or ID",
            height=32,
            font=ds.FONT,
        )
        search.pack(fill="x", pady=(10, 8))

        self._rows = ds.RowList(
            main,
            icon_space=30 if icon else 0,
            on_activate=lambda _i: self._on_confirm(),
        )
        self._rows.pack(fill="both", expand=True)

        ds.button(
            btn_row, "Clear / Empty", self._on_clear, primary=False, width=120
        ).pack(side="left")
        ds.button(btn_row, "Cancel", self.destroy, primary=False).pack(side="right")
        ds.button(btn_row, "Select", self._on_confirm).pack(side="right", padx=(0, 8))
        self.bind("<Escape>", lambda _e: self.destroy())

        self._render(items)
        ds.finish(self, parent, width=width, height=520)

        if current >= 0:
            for idx, (iid, _) in enumerate(self._filtered):
                if iid == current:
                    self._rows.select(idx)
                    break

        search.focus_set()
        self.wait_window()

    def _render(self, items: list[tuple[int, str]]) -> None:
        self._filtered = items
        self._rows.set_rows([name for _, name in items])
        if self._icon is not None:
            self._rows.load_icons(lambda i: self._icon(self._filtered[i][0]))

    def _filter(self, q: str) -> None:
        q = q.lower()
        filtered = [
            (iid, name)
            for iid, name in self._items
            if not q or q in name.lower() or q in str(iid)
        ]
        self._render(filtered)

    def _on_confirm(self, _event=None) -> None:
        sel = self._rows.selected
        if sel is not None and sel < len(self._filtered):
            self.result = self._filtered[sel][0]
        self.destroy()

    def _on_clear(self) -> None:
        self.result = _EMPTY_EFFECT
        self.destroy()


# Relic color filters: nr_items relic "color" (EquipParamAntique relicColor)
_RELIC_COLORS = ("Burning", "Drizzly", "Luminous", "Tranquil")


def _relic_grid_icon(real_item_id: int):
    from er_save_manager.games.NR.icons import relic_icon
    from er_save_manager.ui.virtual_grid import no_image_icon

    return relic_icon(real_item_id) or no_image_icon()


def _relic_filter_match(real_item_id: int, choice: str) -> bool:
    """Whether a relic type passes the color / Deep / Fixed filter."""
    from er_save_manager.games.NR.item_db import get_relic
    from er_save_manager.games.NR.relic_rules import relic_kind

    if choice == "All":
        return True
    if choice == "Deep":
        return real_item_id >= 2000000
    if choice == "Fixed":
        return relic_kind(real_item_id) == "fixed"
    row = get_relic(real_item_id)
    return (
        bool(row) and row["color"] in range(4) and _RELIC_COLORS[row["color"]] == choice
    )


class _RelicTypePicker(ctk.CTkToplevel):
    """Modal icon grid for picking a relic type."""

    def __init__(self, parent, items: list[tuple[int, str]], current: int = -1):
        super().__init__(parent)
        from er_save_manager.ui.virtual_grid import GridEntry, VirtualIconGrid

        self.withdraw()
        self.attributes("-alpha", 0)
        self.title("Select Relic Type")
        self.transient(parent)
        self.resizable(True, True)

        self.result: int | None = None
        self._labels = dict(items)
        self._all = [
            GridEntry(
                rid,
                label,
                f"{label} {rid}".lower(),
                lambda r=rid: _relic_grid_icon(r),
            )
            for rid, label in items
        ]

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=16)
        btn_row = ctk.CTkFrame(main, fg_color="transparent")
        btn_row.pack(side="bottom", fill="x", pady=(12, 0))
        ds.header(main, "Select Relic Type", font=ds.TITLE_LARGE)

        search_var = tk.StringVar()
        search_var.trace_add(
            "write", lambda *_: self._grid.apply_filter(search_var.get())
        )
        search = ctk.CTkEntry(
            main,
            textvariable=search_var,
            placeholder_text="Search name or ID",
            height=32,
            font=ds.FONT,
        )
        search.pack(fill="x", pady=(10, 8))
        self._filter = ctk.CTkSegmentedButton(
            main,
            values=["All", *_RELIC_COLORS, "Deep", "Fixed"],
            command=lambda _v: self._apply_filter(),
        )
        self._filter.set("All")
        self._filter.pack(anchor="w", pady=(0, 8))

        self._grid = VirtualIconGrid(
            main,
            lambda _keys: None,
            on_activate=lambda _key: self._on_confirm(),
            tooltip=self._labels.get,
            cell_w=112,
            cell_h=126,
            icon_size=64,
            fg_color=ds.LIST_BG,
            corner_radius=8,
        )
        self._grid.pack(fill="both", expand=True)
        self._grid.set_entries(self._all)
        if current >= 0 and current not in self._labels:
            # The picker lists one id per relic name and kind
            from er_save_manager.games.NR.item_db import relic_name
            from er_save_manager.games.NR.relic_rules import relic_kind

            name, kind = relic_name(current), relic_kind(current)
            current = next(
                (
                    rid
                    for rid in self._labels
                    if relic_name(rid) == name and relic_kind(rid) == kind
                ),
                -1,
            )
        if current in self._labels:
            self._grid.set_selection([current], notify=False)
            # The grid has its size once the window is shown
            self.after(100, lambda: self._grid.see(current))

        ds.button(btn_row, "Cancel", self.destroy, primary=False).pack(side="right")
        ds.button(btn_row, "Select", self._on_confirm).pack(side="right", padx=(0, 8))
        self.bind("<Escape>", lambda _e: self.destroy())

        ds.finish(self, parent, width=760, height=720)
        search.focus_set()
        self.wait_window()

    def _apply_filter(self) -> None:
        choice = self._filter.get()
        self._grid.set_entries(
            [e for e in self._all if _relic_filter_match(e.key, choice)],
            keep_selection=True,
        )

    def _on_confirm(self) -> None:
        if self._grid.selected:
            self.result = self._grid.selected[0]
        self.destroy()


# Vessel slot stripe colors by nr_items color code; 4 (any color) is gray
_SLOT_COLORS = {
    0: ("#C0392B", "#E05A4F"),  # Burning
    1: ("#2E6DB4", "#5B9BE0"),  # Drizzly
    2: ("#C9A227", "#E6C24A"),  # Luminous
    3: ("#3F9A4A", "#62C06E"),  # Tranquil
}


def _short_vessel_name(name: str) -> str:
    """Vessel name without its "[Hero] " prefix."""
    return name.split("] ", 1)[1] if name.startswith("[") and "] " in name else name


def _slot_title(vessel_id: int, idx: int) -> str:
    """Title of vessel slot idx (0-5), e.g. "Slot 2, Burning"."""
    from er_save_manager.games.NR.item_db import COLOR_NAMES, vessel_slot_color

    color = vessel_slot_color(vessel_id, idx)
    if color == 4:
        return f"Slot {idx + 1}, any color"
    return f"Slot {idx + 1}, {COLOR_NAMES.get(color, 'unknown color')}"


def _clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "\u2026"


def _vessel_grid_icon(vessel_id: int):
    from er_save_manager.games.NR.icons import vessel_icon
    from er_save_manager.ui.virtual_grid import no_image_icon

    return vessel_icon(vessel_id) or no_image_icon()


class _SlotRelicPicker(ctk.CTkToplevel):
    """Modal icon grid of the character's relics for one loadout slot."""

    def __init__(self, parent, title: str, relics: list, current: int, effect_lines):
        super().__init__(parent)
        from er_save_manager.games.NR.item_db import relic_name
        from er_save_manager.ui.virtual_grid import GridEntry, VirtualIconGrid

        self.withdraw()
        self.attributes("-alpha", 0)
        self.title(title)
        self.transient(parent)
        self.resizable(True, True)

        self.result: int | None = None
        self._tips: dict[int, str] = {}
        entries = []
        for rs in relics:
            name = relic_name(rs.real_item_id)
            lines = effect_lines(rs)
            self._tips[rs.ga_handle] = "\n".join([name, "", *lines])
            # Relics of one name differ by effects; the tile lists them, the
            # curses are in the tooltip
            shown = [_clip(ln, 34) for ln in lines if not ln.startswith(" ")]
            entries.append(
                GridEntry(
                    rs.ga_handle,
                    "\n".join([name, *shown]),
                    " ".join([name, *lines]).lower(),
                    lambda r=rs.real_item_id: _relic_grid_icon(r),
                )
            )

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=16)
        btn_row = ctk.CTkFrame(main, fg_color="transparent")
        btn_row.pack(side="bottom", fill="x", pady=(12, 0))
        ds.header(main, title, font=ds.TITLE_LARGE)
        ctk.CTkLabel(
            main,
            text="Relics of this character that fit the slot's color and type, "
            "except the ones in the other slots.",
            font=ds.SMALL,
            text_color=ds.MUTED,
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        search_var = tk.StringVar()
        search_var.trace_add(
            "write", lambda *_: self._grid.apply_filter(search_var.get())
        )
        search = ctk.CTkEntry(
            main,
            textvariable=search_var,
            placeholder_text="Search name or effect",
            height=32,
            font=ds.FONT,
        )
        search.pack(fill="x", pady=(10, 8))

        self._grid = VirtualIconGrid(
            main,
            lambda _keys: None,
            on_activate=lambda _key: self._on_confirm(),
            tooltip=self._tips.get,
            cell_w=230,
            cell_h=150,
            icon_size=56,
            fg_color=ds.LIST_BG,
            corner_radius=8,
        )
        if entries:
            self._grid.pack(fill="both", expand=True)
            self._grid.set_entries(entries)
            if current in self._tips:
                self._grid.set_selection([current], notify=False)
                # The grid has its size once the window is shown
                self.after(100, lambda: self._grid.see(current))
        else:
            ctk.CTkLabel(
                main,
                text="No relic of this character fits this slot.",
                font=ds.FONT,
                text_color=ds.MUTED,
            ).pack(fill="both", expand=True)

        ds.button(btn_row, "Cancel", self.destroy, primary=False).pack(side="right")
        ds.button(btn_row, "Select", self._on_confirm).pack(side="right", padx=(0, 8))
        self.bind("<Escape>", lambda _e: self.destroy())

        ds.finish(self, parent, width=1000, height=760)
        search.focus_set()
        self.wait_window()

    def _on_confirm(self) -> None:
        if self._grid.selected:
            self.result = self._grid.selected[0]
        self.destroy()


class NREditorTab:
    """Builds the Character Editor (parent), Relics and Loadouts tabs, which
    share one character and the icon cache."""

    def __init__(
        self,
        parent,
        get_nr_save: Callable,
        get_save_path: Callable,
        show_toast: Callable,
        pending_register: Callable[[str], Callable] | None = None,
        *,
        relics_parent=None,
        loadouts_parent=None,
    ) -> None:
        self.parent = parent
        self._relics_parent = relics_parent if relics_parent is not None else parent
        self._loadouts_parent = (
            loadouts_parent if loadouts_parent is not None else parent
        )
        self._get_nr_save = get_nr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        # pending_register(tab name) gives the register function of that tab
        self._pending_register = pending_register
        # CTkImage per (icon kind, id, size)
        self._icon_images: dict[tuple, ctk.CTkImage | None] = {}
        self._current_slot = -1
        self._name_var = tk.StringVar()
        self._murk_var = tk.StringVar()
        self._mon_var = tk.StringVar()

    def setup_ui(self) -> None:
        self.setup_steps()
        self.setup_relics()
        self.setup_loadouts()

    @staticmethod
    def _tab_frame(parent, title: str) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
        """Rounded tab body and its header row holding the title."""
        outer = ctk.CTkFrame(parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))
        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(header, text=title, font=("Inter", 16, "bold")).pack(side="left")
        return outer, header

    def setup_steps(self) -> None:
        """Character Editor tab: name and currencies."""
        outer, _header = self._tab_frame(self.parent, "Character Editor")
        self._build_overview(outer)
        if self._pending_register is not None:
            self._pending_register("Character Editor")(
                PendingPage(
                    "Overview",
                    self._overview_tracker.changes,
                    self._prepare_overview,
                    lambda: self._refill_overview(),
                    None,
                )
            )

    def setup_relics(self) -> None:
        outer, header = self._tab_frame(self._relics_parent, "Relics")
        self._build_relics(outer, header)

    def setup_loadouts(self) -> None:
        outer, header = self._tab_frame(self._loadouts_parent, "Loadouts")
        self._build_loadouts(outer, header)
        if self._pending_register is not None:
            self._pending_register("Loadouts")(
                PendingPage(
                    "Loadout",
                    self._loadout_changes,
                    self._prepare_loadout,
                    self._discard_loadout,
                    None,
                )
            )

    # ------------------------------------------------------------------
    # Slot selector
    # ------------------------------------------------------------------

    def load_slot(self, slot_index: int) -> None:
        """Show the character in slot_index in all three tabs."""
        self.load_overview(slot_index)
        self.load_relics(slot_index)
        self.load_loadouts(slot_index)

    def _set_slot(self, slot_index: int):
        """Make slot_index current; returns its slot, or None (and current
        -1) for no save or an index out of range."""
        save = self._get_nr_save()
        if save is None or not 0 <= slot_index < len(save.slots):
            self._current_slot = -1
            return None
        self._current_slot = slot_index
        return save.slots[slot_index]

    def load_overview(self, slot_index: int) -> None:
        """Character Editor tab; -1 or an empty slot clears it."""
        slot = self._set_slot(slot_index)
        if slot is None:
            self._overview_tracker.clear()
            for var in (self._name_var, self._murk_var, self._mon_var):
                var.set("")
            return
        self._populate_overview(slot)

    def load_relics(self, slot_index: int) -> None:
        slot = self._set_slot(slot_index)
        if slot is not None:
            self._populate_relics(slot)

    def load_loadouts(self, slot_index: int) -> None:
        """Loadouts tab; -1 or an empty slot clears it."""
        slot = self._set_slot(slot_index)
        if slot is None:
            self._clear_loadout_edit()
            self._populate_loadout_grid()
            return
        self._populate_loadouts(slot)

    def refresh(self) -> None:
        self.load_slot(self._current_slot)

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    def _build_overview(self, parent) -> None:
        f = ctk.CTkFrame(parent, corner_radius=10, fg_color=("gray86", "gray22"))
        f.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(f, text="Character overview", font=("Inter", 14, "bold")).pack(
            anchor="w", padx=14, pady=(12, 6)
        )
        grid = ctk.CTkFrame(f, fg_color="transparent")
        grid.pack(anchor="nw", padx=14)

        for row, (label, var) in enumerate(
            [
                ("Player Name:", self._name_var),
                ("Murk:", self._murk_var),
                ("Sovereign Sigils:", self._mon_var),
            ]
        ):
            ctk.CTkLabel(grid, text=label, anchor="w", width=150).grid(
                row=row, column=0, sticky="w", pady=4
            )
            ctk.CTkEntry(grid, textvariable=var, width=200).grid(
                row=row, column=1, padx=(6, 0), pady=4
            )

        self._overview_tracker = FieldTracker(
            var_state(
                {"name": self._name_var, "murk": self._murk_var, "mon": self._mon_var}
            )
        )

    def _populate_overview(self, slot) -> None:
        self._name_var.set(slot.player_name)
        self._murk_var.set(str(slot.murk))
        self._mon_var.set(str(slot.marks_of_night))
        self._overview_tracker.mark_clean()

    def _refill_overview(self) -> None:
        slot = self._current_nr_slot()
        if slot is not None:
            self._populate_overview(slot)

    def _prepare_overview(self):
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            raise StageError("No character loaded.")
        slot = save.slots[self._current_slot]
        try:
            murk = int(self._murk_var.get())
            mon = int(self._mon_var.get())
        except ValueError:
            raise StageError("Murk and Sovereign Sigils must be integers.") from None
        if not (0 <= murk <= _MAX_CURRENCY and 0 <= mon <= _MAX_CURRENCY):
            raise StageError(f"Values must be between 0 and {_MAX_CURRENCY:,}.")
        name = self._name_var.get().strip()
        if len(name) > 16:
            raise StageError("Player name cannot exceed 16 characters.")

        def commit() -> None:
            slot.murk = murk
            slot.marks_of_night = mon
            if name:
                slot.player_name = name

        return commit

    # ------------------------------------------------------------------
    # Relics
    # ------------------------------------------------------------------

    def _build_relics(self, parent, header) -> None:
        from er_save_manager.games.NR.item_db import (
            effects_for_curse_slot,
            effects_for_slot,
        )
        from er_save_manager.games.NR.relic_rules import picker_relics
        from er_save_manager.ui.virtual_grid import VirtualIconGrid

        self._all_relic_opts: list[tuple[int, str, bool]] = picker_relics()
        self._normal_effect_opts: list[tuple[int, str]] = effects_for_slot(False)
        self._deep_effect_opts: list[tuple[int, str]] = effects_for_slot(True)
        self._curse_opts: list[tuple[int, str]] = effects_for_curse_slot()

        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        top = header
        self._relic_count_label = ctk.CTkLabel(top, text="", text_color=ds.MUTED)
        self._relic_count_label.pack(side="left", padx=(8, 0))
        ds.button(top, "New Relic", lambda: self._show_relic_pane("spawn")).pack(
            side="right"
        )
        ds.button(
            top,
            "Export JSON...",
            self._export_relics_json,
            primary=False,
            width=120,
        ).pack(side="right", padx=(0, 8))
        # No textvariable: CTkEntry hides the placeholder while one is set
        self._relic_search = ctk.CTkEntry(
            top, placeholder_text="Search name or effect", width=240
        )
        self._relic_search.pack(side="right", padx=(0, 8))
        self._relic_search.bind("<KeyRelease>", lambda _e: self._filter_relics())

        self._relic_filter = ctk.CTkSegmentedButton(
            body,
            values=["All", *_RELIC_COLORS, "Deep"],
            command=lambda _v: self._populate_relic_grid(keep_selection=True),
        )
        self._relic_filter.set("All")
        self._relic_filter.pack(anchor="w", pady=(0, 6))

        split = ctk.CTkFrame(body, fg_color="transparent")
        split.pack(fill="both", expand=True)
        split.grid_columnconfigure(0, weight=1)
        split.grid_rowconfigure(0, weight=1)

        self._relic_grid = VirtualIconGrid(
            split,
            self._on_relic_select,
            tooltip=self._relic_tooltip,
            cell_w=112,
            cell_h=126,
            icon_size=72,
            fg_color=ds.LIST_BG,
            corner_radius=8,
        )
        self._relic_grid.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self._re_item_var = tk.StringVar(value="-1")
        self._spawn_relic_id = tk.IntVar(value=-1)
        self._panes: dict[str, dict] = {}
        self._edit_panel = self._build_relic_pane(split, "edit")
        self._spawn_panel = self._build_relic_pane(split, "spawn")
        self._edit_panel.grid(row=0, column=1, sticky="nsew")

        self._selected_relic_ga: int | None = None
        self._all_relic_data: list = []
        self._refresh_rows("edit")
        self._refresh_rows("spawn")

    def _build_relic_pane(self, parent, which: str) -> ctk.CTkFrame:
        """Detail pane of the selected relic (edit) or a new relic (spawn):
        relic type, one card per effect slot with its curse below."""
        edit = which == "edit"
        pane = ctk.CTkFrame(
            parent, width=500, corner_radius=10, fg_color=("gray84", "gray24")
        )
        pane.grid_propagate(False)
        pane.pack_propagate(False)

        head = ctk.CTkFrame(pane, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(14, 6))
        icon = ctk.CTkLabel(head, text="", width=72, height=72)
        icon.pack(side="left", padx=(0, 12))
        ds.button(
            head,
            "Change...",
            self._browse_relic_type if edit else self._browse_spawn_relic,
            primary=False,
            width=90,
        ).pack(side="right", anchor="n")
        text = ctk.CTkFrame(head, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True)
        if not edit:
            ctk.CTkLabel(
                text, text="New relic", font=ds.SMALL, text_color=ds.MUTED, anchor="w"
            ).pack(fill="x")
        name = ds.wrap_to_width(ctk.CTkLabel(text, text="", font=ds.TITLE))
        name.pack(fill="x")
        kind = ds.wrap_to_width(
            ctk.CTkLabel(text, text="", font=ds.SMALL, text_color=ds.MUTED)
        )
        kind.pack(fill="x")

        btns = ctk.CTkFrame(pane, fg_color="transparent")
        btns.pack(side="bottom", fill="x", padx=14, pady=14)
        if edit:
            ds.button(btns, "Apply Edit", self._apply_relic_edit, width=110).pack(
                side="right"
            )
            ds.button(
                btns,
                "Copy to New Relic",
                self._copy_to_spawn,
                primary=False,
                width=140,
            ).pack(side="right", padx=(0, 8))
            ds.button(
                btns, "Remove", self._remove_selected_relic, primary=False, width=90
            ).pack(side="left")
        else:
            ds.button(btns, "Spawn", self._spawn_relic, width=110).pack(side="right")
            ds.button(
                btns,
                "Import JSON...",
                self._import_relics_json,
                primary=False,
                width=120,
            ).pack(side="left")

        ctk.CTkLabel(pane, text="Effects", font=ds.BOLD, anchor="w").pack(
            fill="x", padx=14, pady=(10, 2)
        )
        # Scrolls when the window is too short for three cards with curses
        cards = ctk.CTkScrollableFrame(pane, fg_color="transparent", corner_radius=0)
        cards.pack(fill="both", expand=True, padx=8)

        browse_effect = self._browse_effect if edit else self._browse_spawn_effect
        browse_curse = self._browse_curse if edit else self._browse_spawn_curse
        effect_vars = [tk.StringVar(value=str(_EMPTY_EFFECT)) for _ in range(3)]
        curse_vars = [tk.StringVar(value=str(_EMPTY_EFFECT)) for _ in range(3)]
        effect_labels, effect_icons, effect_btns = [], [], []
        curse_widgets, curse_icons, curse_tips, rows = [], [], [], []
        for j in range(3):
            card = ctk.CTkFrame(cards, fg_color=ds.BOX, corner_radius=8)
            line = ctk.CTkFrame(card, fg_color="transparent")
            line.pack(fill="x", padx=8, pady=6)
            e_icon = ctk.CTkLabel(line, text="", width=28)
            e_icon.pack(side="left", anchor="n")
            btn_e = ds.button(
                line,
                "Change...",
                lambda jj=j: browse_effect(jj),
                primary=False,
                width=84,
            )
            btn_e.pack(side="right", anchor="n")
            lbl_e = ds.wrap_to_width(ctk.CTkLabel(line, text="", font=ds.FONT))
            lbl_e.pack(side="left", fill="x", expand=True, padx=8)

            curse_line = ctk.CTkFrame(card, fg_color="transparent")
            c_icon = ctk.CTkLabel(curse_line, text="", width=22)
            c_icon.pack(side="left", anchor="n")
            btn_c = ds.button(
                curse_line,
                "Change...",
                lambda jj=j: browse_curse(jj),
                primary=False,
                width=84,
                height=26,
            )
            btn_c.pack(side="right", anchor="n")
            lbl_c = ds.wrap_to_width(
                ctk.CTkLabel(curse_line, text="", font=ds.SMALL, text_color=ds.MUTED)
            )
            lbl_c.pack(side="left", fill="x", expand=True, padx=8)

            effect_labels.append(lbl_e)
            effect_icons.append(e_icon)
            effect_btns.append(btn_e)
            curse_widgets.append((lbl_c, btn_c, curse_line))
            curse_icons.append(c_icon)
            curse_tips.append((add_tooltip(lbl_c, ""), add_tooltip(btn_c, "")))
            rows.append(card)

        if edit:
            self._re_item_label = name
            self._re_effect_vars = effect_vars
            self._re_curse_vars = curse_vars
            self._re_effect_labels = effect_labels
            self._re_curse_widgets = curse_widgets
            self._re_curse_tips = curse_tips
            self._re_effect_btns = effect_btns
            self._re_rows = rows
        else:
            self._spawn_relic_label = name
            self._spawn_effect_vars = effect_vars
            self._spawn_curse_vars = curse_vars
            self._spawn_effect_labels = effect_labels
            self._spawn_curse_widgets = curse_widgets
            self._spawn_curse_tips = curse_tips
            self._spawn_effect_btns = effect_btns
            self._spawn_rows = rows
        self._panes[which] = {
            "icon": icon,
            "kind": kind,
            "effect_icons": effect_icons,
            "curse_icons": curse_icons,
        }
        return pane

    def _show_relic_pane(self, which: str) -> None:
        """Show the edit pane or the new relic (spawn) pane."""
        show, hide = (
            (self._edit_panel, self._spawn_panel)
            if which == "edit"
            else (self._spawn_panel, self._edit_panel)
        )
        hide.grid_remove()
        show.grid(row=0, column=1, sticky="nsew")

    def open_spawner(self) -> None:
        """Show the new relic pane in the Relics tab (Item Gib)."""
        self._show_relic_pane("spawn")

    def _icon_image(self, kind: str, item_id: int, size: int):
        """Cached CTkImage of a relic, effect or vessel (chalice) icon."""
        key = (kind, item_id, size)
        if key not in self._icon_images:
            from er_save_manager.games.NR.icons import (
                effect_icon,
                relic_icon,
                vessel_icon,
            )

            load = {"relic": relic_icon, "effect": effect_icon, "vessel": vessel_icon}
            pil = load[kind](item_id)
            self._icon_images[key] = (
                ctk.CTkImage(pil, size=(size, size)) if pil is not None else None
            )
        return self._icon_images[key]

    # ------------------------------------------------------------------
    # Curse slot visibility
    # ------------------------------------------------------------------

    def _panel(self, which: str) -> tuple:
        """(relic id, effect vars, effect labels, effect buttons, curse vars,
        curse widgets, rows) of the edit or spawn panel."""
        if which == "edit":
            try:
                relic_id = int(self._re_item_var.get())
            except ValueError:
                relic_id = -1
            return (
                relic_id,
                self._re_effect_vars,
                self._re_effect_labels,
                self._re_effect_btns,
                self._re_curse_vars,
                self._re_curse_widgets,
                self._re_rows,
            )
        return (
            self._spawn_relic_id.get(),
            self._spawn_effect_vars,
            self._spawn_effect_labels,
            self._spawn_effect_btns,
            self._spawn_curse_vars,
            self._spawn_curse_widgets,
            self._spawn_rows,
        )

    def _refresh_rows(self, which: str) -> None:
        """Show one effect card per relic slot and a curse line where a deep
        effect needs one. Cards that still hold a value stay visible so it
        can be cleared; fixed relic effects cannot be picked. Also updates
        the relic header, effect texts and icons from the panel's values."""
        from er_save_manager.games.NR.item_db import get_relic
        from er_save_manager.games.NR.relic_rules import (
            fixed_effects,
            needs_curse,
            relic_kind,
            slot_count,
        )

        relic_id, evars, elabels, ebtns, cvars, cwidgets, rows = self._panel(which)
        tips = self._re_curse_tips if which == "edit" else self._spawn_curse_tips
        pane = self._panes[which]
        kind = relic_kind(relic_id) if relic_id >= 0 else "unknown"
        effects = [int(v.get()) for v in evars]
        curses = [int(v.get()) for v in cvars]
        filled = [
            j + 1
            for j in range(3)
            if effects[j] != _EMPTY_EFFECT or curses[j] != _EMPTY_EFFECT
        ]
        shown = 3 if kind == "unknown" else slot_count(relic_id)
        shown = max([shown, *filled])
        for row in rows:
            row.pack_forget()
        for row in rows[:shown]:
            row.pack(fill="x", pady=3)

        row_info = get_relic(relic_id) if relic_id >= 0 else None
        pane["icon"].configure(
            image=self._icon_image("relic", relic_id, 72) if relic_id >= 0 else None
        )
        if relic_id < 0:
            (
                self._re_item_label if which == "edit" else self._spawn_relic_label
            ).configure(
                text="No relic selected" if which == "edit" else "No relic type"
            )
            pane["kind"].configure(
                text="Select a relic in the grid."
                if which == "edit"
                else "Choose a relic type with Change."
            )
        else:
            pane["kind"].configure(text=self._relic_kind_line(relic_id, kind, row_info))
        deep = kind == "deep" or (
            kind == "unknown" and bool(row_info and row_info["deep"])
        )
        # A fixed relic's effects are set for it; the buttons only open when
        # the stored effects differ, so wrong ones can be cleared.
        locked = kind == "fixed" and sorted(
            e for e in effects if e != _EMPTY_EFFECT
        ) == (sorted(fixed_effects(relic_id)))
        for j in range(3):
            elabels[j].configure(text=_fmt_effect(effects[j]))
            pane["effect_icons"][j].configure(
                image=self._icon_image("effect", effects[j], 26)
            )
            ebtns[j].configure(state="disabled" if locked else "normal")
            lbl_c, _btn_c, curse_line = cwidgets[j]
            required = kind == "deep" and needs_curse(effects[j])
            show = deep and (
                kind == "unknown" or required or curses[j] != _EMPTY_EFFECT
            )
            text = ""
            if required:
                text = (
                    f"{_fmt_effect(effects[j])} always comes with a curse: the "
                    "game never rolls it without one, so this row needs a curse."
                )
            elif kind == "deep" and curses[j] != _EMPTY_EFFECT:
                text = (
                    "This curse has no effect in its row. Clear it."
                    if effects[j] == _EMPTY_EFFECT
                    else f"{_fmt_effect(effects[j])} never comes with a curse. "
                    "Clear this curse."
                )
            for tip in tips[j]:
                tip.text = text
            if show:
                missing = required and curses[j] == _EMPTY_EFFECT
                lbl_c.configure(
                    text=f"Curse{' (required)' if missing else ''}: "
                    f"{_fmt_effect(curses[j])}"
                )
                pane["curse_icons"][j].configure(
                    image=self._icon_image("effect", curses[j], 20)
                )
                curse_line.pack(fill="x", padx=(44, 8), pady=(0, 6))
            else:
                curse_line.pack_forget()

    @staticmethod
    def _relic_kind_line(relic_id: int, kind: str, row_info: dict | None) -> str:
        """Kind, color and slot count under the relic name."""
        from er_save_manager.games.NR.relic_rules import slot_count

        parts = [
            {
                "random": "Random effects",
                "deep": "Deep relic",
                "fixed": "Fixed effects",
                "unobtainable": "Not obtainable in game",
            }.get(kind, "Unknown relic")
        ]
        if row_info and row_info["color"] in range(4):
            parts.append(_RELIC_COLORS[row_info["color"]])
        if kind != "unknown":
            n = slot_count(relic_id)
            parts.append(f"{n} effect slot{'' if n == 1 else 's'}")
        return "  ·  ".join(parts)

    def _fit_to_relic(self, which: str) -> None:
        """After a relic type change, drop effects the new type cannot hold
        and curses their effects cannot carry."""
        from er_save_manager.games.NR.relic_rules import (
            can_add,
            needs_curse,
            relic_kind,
            slot_count,
        )

        relic_id, evars, elabels, _btns, cvars, _cw, _rows = self._panel(which)
        kind = relic_kind(relic_id)
        if kind == "unknown":
            return
        kept: list[int] = []
        for j in range(3):
            effect = int(evars[j].get())
            fits = (
                effect != _EMPTY_EFFECT
                and j < slot_count(relic_id)
                and can_add(relic_id, effect, kept)
            )
            if fits:
                kept.append(effect)
            else:
                evars[j].set(str(_EMPTY_EFFECT))
                elabels[j].configure(text=_fmt_effect(_EMPTY_EFFECT))
            if not fits or kind != "deep" or not needs_curse(effect):
                cvars[j].set(str(_EMPTY_EFFECT))

    def _set_effect(self, which: str, idx: int, effect_id: int) -> None:
        """Set an effect row; a curse the new effect cannot carry is cleared."""
        from er_save_manager.games.NR.relic_rules import needs_curse, relic_kind

        relic_id, evars, elabels, _btns, cvars, _cw, _rows = self._panel(which)
        evars[idx].set(str(effect_id))
        elabels[idx].configure(text=_fmt_effect(effect_id))
        if relic_kind(relic_id) == "deep" and not needs_curse(effect_id):
            cvars[idx].set(str(_EMPTY_EFFECT))
        self._refresh_rows(which)

    # ------------------------------------------------------------------
    # Picker helpers
    # ------------------------------------------------------------------

    def _relic_picker_items(self) -> list[tuple[int, str]]:
        return [(rid, label) for rid, label, _deep in self._all_relic_opts]

    def _effect_picker_items(
        self, relic_id: int, others: list[int]
    ) -> list[tuple[int, str]]:
        """Effects the relic type can roll (the tier list for a relic type
        the roll tables do not cover), minus those that cannot share the
        relic with the effects in the other rows or no longer fit its slot
        tables."""
        from er_save_manager.games.NR.item_db import effect_name, get_relic
        from er_save_manager.games.NR.relic_rules import can_add, rollable_effects

        rollable = rollable_effects(relic_id)
        if rollable is None:
            row = get_relic(relic_id)
            deep = bool(row and row["deep"])
            opts = self._deep_effect_opts if deep else self._normal_effect_opts
        else:
            opts = sorted(((e, effect_name(e)) for e in rollable), key=lambda x: x[1])
        opts = [(e, name) for e, name in opts if can_add(relic_id, e, others)]
        return [(_EMPTY_EFFECT, "(empty)")] + opts

    def _curse_picker_items(self, others: list[int]) -> list[tuple[int, str]]:
        """Curses not already used in another row."""
        return [(_EMPTY_EFFECT, "(empty)")] + [
            (c, name) for c, name in self._curse_opts if c not in others
        ]

    def _fill_fixed_effects(
        self, relic_id: int, effect_vars, effect_labels, curse_vars
    ) -> None:
        """Show a fixed relic's effects, which cannot be chosen."""
        from er_save_manager.games.NR.relic_rules import fixed_effects, relic_kind

        if relic_kind(relic_id) != "fixed":
            return
        effects = fixed_effects(relic_id)
        effects += [_EMPTY_EFFECT] * (3 - len(effects))
        for j in range(3):
            effect_vars[j].set(str(effects[j]))
            effect_labels[j].configure(text=_fmt_effect(effects[j]))
            curse_vars[j].set(str(_EMPTY_EFFECT))

    def _effect_picker(
        self, title: str, items: list[tuple[int, str]], current: int
    ) -> _PickerDialog:
        """Effect or curse picker with the effect icons, wide enough for the
        longest effect names."""
        from er_save_manager.games.NR.icons import effect_icon

        return _PickerDialog(
            self.parent, title, items, current, icon=effect_icon, width=780
        )

    # Edit panel pickers

    def _browse_relic_type(self) -> None:
        try:
            cur = int(self._re_item_var.get())
        except ValueError:
            cur = -1
        dlg = _RelicTypePicker(self.parent, self._relic_picker_items(), cur)
        if dlg.result is not None and dlg.result != _EMPTY_EFFECT:
            from er_save_manager.games.NR.item_db import relic_name

            self._re_item_var.set(str(dlg.result))
            self._re_item_label.configure(text=relic_name(dlg.result))
            self._fill_fixed_effects(
                dlg.result,
                self._re_effect_vars,
                self._re_effect_labels,
                self._re_curse_vars,
            )
            self._fit_to_relic("edit")
            self._refresh_rows("edit")

    def _browse_effect(self, idx: int) -> None:
        try:
            cur = int(self._re_effect_vars[idx].get())
        except ValueError:
            cur = _EMPTY_EFFECT
        try:
            relic_id = int(self._re_item_var.get())
        except ValueError:
            relic_id = -1
        others = [int(v.get()) for j, v in enumerate(self._re_effect_vars) if j != idx]
        items = self._effect_picker_items(relic_id, others)
        dlg = self._effect_picker(f"Select Effect {idx + 1}", items, cur)
        if dlg.result is not None:
            self._set_effect("edit", idx, dlg.result)

    def _browse_curse(self, idx: int) -> None:
        try:
            cur = int(self._re_curse_vars[idx].get())
        except ValueError:
            cur = _EMPTY_EFFECT
        others = [int(v.get()) for j, v in enumerate(self._re_curse_vars) if j != idx]
        dlg = self._effect_picker(
            f"Select Curse {idx + 1}", self._curse_picker_items(others), cur
        )
        if dlg.result is not None:
            self._re_curse_vars[idx].set(str(dlg.result))
            self._refresh_rows("edit")

    # Spawn pickers

    def _browse_spawn_relic(self) -> None:
        cur = self._spawn_relic_id.get()
        dlg = _RelicTypePicker(self.parent, self._relic_picker_items(), cur)
        if dlg.result is not None and dlg.result != _EMPTY_EFFECT:
            from er_save_manager.games.NR.item_db import relic_name

            self._spawn_relic_id.set(dlg.result)
            self._spawn_relic_label.configure(text=relic_name(dlg.result))
            self._fill_fixed_effects(
                dlg.result,
                self._spawn_effect_vars,
                self._spawn_effect_labels,
                self._spawn_curse_vars,
            )
            self._fit_to_relic("spawn")
            self._refresh_rows("spawn")

    def _browse_spawn_effect(self, idx: int) -> None:
        try:
            cur = int(self._spawn_effect_vars[idx].get())
        except ValueError:
            cur = _EMPTY_EFFECT
        others = [
            int(v.get()) for j, v in enumerate(self._spawn_effect_vars) if j != idx
        ]
        items = self._effect_picker_items(self._spawn_relic_id.get(), others)
        dlg = self._effect_picker(f"Select Effect {idx + 1}", items, cur)
        if dlg.result is not None:
            self._set_effect("spawn", idx, dlg.result)

    def _browse_spawn_curse(self, idx: int) -> None:
        try:
            cur = int(self._spawn_curse_vars[idx].get())
        except ValueError:
            cur = _EMPTY_EFFECT
        others = [
            int(v.get()) for j, v in enumerate(self._spawn_curse_vars) if j != idx
        ]
        dlg = self._effect_picker(
            f"Select Curse {idx + 1}", self._curse_picker_items(others), cur
        )
        if dlg.result is not None:
            self._spawn_curse_vars[idx].set(str(dlg.result))
            self._refresh_rows("spawn")

    # ------------------------------------------------------------------
    # Relic list
    # ------------------------------------------------------------------

    def _populate_relics(self, slot, keep_selection: bool = False) -> None:
        """Fill the grid from slot; keep_selection keeps the selected relic
        when it still exists, otherwise the edit pane is cleared."""
        self._all_relic_data = list(slot.relic_states.values())
        if not (keep_selection and self._selected_relic_ga in slot.relic_states):
            self._selected_relic_ga = None
            self._clear_edit_pane()
        self._populate_relic_grid(keep_selection=self._selected_relic_ga is not None)

    def _populate_relic_grid(self, keep_selection: bool) -> None:
        """Grid entries of the relics passing the color / Deep filter."""
        from er_save_manager.games.NR.item_db import effect_name, relic_name
        from er_save_manager.ui.virtual_grid import GridEntry

        choice = self._relic_filter.get()
        entries = []
        for rs in sorted(
            self._all_relic_data, key=lambda r: relic_name(r.real_item_id)
        ):
            if not _relic_filter_match(rs.real_item_id, choice):
                continue
            name = relic_name(rs.real_item_id)
            texts = [effect_name(e) for e in rs.effects_list() if e != _EMPTY_EFFECT]
            entries.append(
                GridEntry(
                    rs.ga_handle,
                    name,
                    " ".join([name, *texts]).lower(),
                    lambda r=rs.real_item_id: _relic_grid_icon(r),
                )
            )
        self._relic_grid.set_entries(entries, keep_selection=keep_selection)
        if keep_selection and self._selected_relic_ga is not None:
            self._relic_grid.set_selection([self._selected_relic_ga], notify=False)
            self._relic_grid.update_idletasks()
            self._relic_grid.see(self._selected_relic_ga)
        self._update_relic_count()

    def _filter_relics(self) -> None:
        self._relic_grid.apply_filter(self._relic_search.get())
        self._update_relic_count()

    def _update_relic_count(self) -> None:
        shown = len(self._relic_grid.visible_keys())
        total = len(self._all_relic_data)
        self._relic_count_label.configure(
            text=f"{total}" if shown == total else f"{shown} of {total}"
        )

    def _relic_tooltip(self, ga: int) -> str:
        """Relic name with every effect and curse, one per line."""
        from er_save_manager.games.NR.item_db import effect_name, relic_name

        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            return ""
        rs = save.slots[self._current_slot].relic_states.get(ga)
        if rs is None:
            return ""
        lines = [relic_name(rs.real_item_id), ""]
        effects = rs.effects_list()
        for j in range(3):
            if effects[j] != _EMPTY_EFFECT:
                lines.append(effect_name(effects[j]))
            if effects[j + 3] != _EMPTY_EFFECT:
                lines.append(f"    Curse: {effect_name(effects[j + 3])}")
        return "\n".join(lines)

    def _clear_edit_pane(self) -> None:
        self._re_item_var.set("-1")
        for var in (*self._re_effect_vars, *self._re_curse_vars):
            var.set(str(_EMPTY_EFFECT))
        self._refresh_rows("edit")

    def _on_relic_select(self, keys: list) -> None:
        from er_save_manager.games.NR.item_db import effect_name, relic_name

        if not keys:
            return
        ga = keys[0]
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            return
        rs = save.slots[self._current_slot].relic_states.get(ga)
        if rs is None:
            return
        self._show_relic_pane("edit")
        self._selected_relic_ga = ga
        self._re_item_var.set(str(rs.real_item_id))
        self._re_item_label.configure(text=relic_name(rs.real_item_id))
        effects = rs.effects_list()
        for j in range(3):
            self._re_effect_vars[j].set(str(effects[j]))
            self._re_effect_labels[j].configure(text=effect_name(effects[j]))
            self._re_curse_vars[j].set(str(effects[j + 3]))
        self._refresh_rows("edit")

    # ------------------------------------------------------------------
    # Edit / remove
    # ------------------------------------------------------------------

    def _apply_relic_edit(self) -> None:
        if _game_blocks_write(self.parent):
            return

        if self._selected_relic_ga is None:
            notify(self.parent, "Select a relic row first.", "warning")
            return
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            return
        try:
            real_id = int(self._re_item_var.get())
            effects = [int(v.get()) for v in self._re_effect_vars]
            curses = [int(v.get()) for v in self._re_curse_vars]
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Input", "Could not parse IDs.", parent=self.parent
            )
            return

        from er_save_manager.games.NR.relic_ops import prepare_relic
        from er_save_manager.games.NR.relic_rules import edit_issues

        rs = save.slots[self._current_slot].relic_states.get(self._selected_relic_ga)
        if rs is None:
            return
        old = (
            rs.real_item_id,
            [rs.effect_1, rs.effect_2, rs.effect_3],
            [rs.curse_1, rs.curse_2, rs.curse_3],
        )
        effects, curses = prepare_relic(real_id, effects, curses)
        blocking, warnings = edit_issues(old, (real_id, effects, curses))
        if blocking:
            CTkMessageBox.showerror(
                "Invalid Relic",
                "The game cannot roll this relic:\n"
                + "\n".join(i.message for i in blocking),
                parent=self.parent,
            )
            return
        # Unknown effects (mod data) and issues the relic already had, which
        # an older game version may have rolled, only warn.
        if warnings and not confirm_warning(
            self.parent,
            "show_relic_validation_warning",
            "Validation Warning",
            "Unknown relic effects",
            [
                "\n".join(i.message for i in warnings),
                "The relic may come from mod data or an older game version.",
            ],
            confirm_text="Apply",
        ):
            return

        try:
            save.modify_relic(
                self._current_slot,
                self._selected_relic_ga,
                relic_id=real_id,
                effect_1=effects[0],
                effect_2=effects[1],
                effect_3=effects[2],
                curse_1=curses[0],
                curse_2=curses[1],
                curse_3=curses[2],
            )
            _backup_and_save(save, self._get_save_path(), "nr_relic_edit")
            self._populate_relics(save.slots[self._current_slot], keep_selection=True)
            self._populate_loadouts(save.slots[self._current_slot])
            self._show_toast("Relic saved.")
        except Exception as e:
            CTkMessageBox.showerror("Save Failed", str(e), parent=self.parent)

    def _remove_selected_relic(self) -> None:
        if _game_blocks_write(self.parent):
            return

        if self._selected_relic_ga is None:
            notify(self.parent, "Select a relic row first.", "warning")
            return
        if not CTkMessageBox.askyesno(
            "Confirm Remove", "Remove this relic permanently?", parent=self.parent
        ):
            return
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            return
        try:
            from er_save_manager.games.NR.relic_ops import remove_relic

            cleared = remove_relic(
                save.slots[self._current_slot], self._selected_relic_ga
            )
            _backup_and_save(save, self._get_save_path(), "nr_relic_remove")
            self._selected_relic_ga = None
            self._populate_relics(save.slots[self._current_slot])
            self._populate_loadouts(save.slots[self._current_slot])
            self._show_toast(
                f"Relic removed and unequipped from {cleared} loadout slot(s)."
                if cleared
                else "Relic removed."
            )
        except Exception as e:
            CTkMessageBox.showerror("Remove Failed", str(e), parent=self.parent)

    # ------------------------------------------------------------------
    # Spawn
    # ------------------------------------------------------------------

    def _spawn_relic(self) -> None:
        if _game_blocks_write(self.parent):
            return

        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            notify(self.parent, "Load a slot first.", "warning")
            return
        rid = self._spawn_relic_id.get()
        if rid < 0:
            notify(self.parent, "Select a relic type first.", "warning")
            return
        try:
            effects = [int(v.get()) for v in self._spawn_effect_vars]
            curses = [int(v.get()) for v in self._spawn_curse_vars]
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Input", "Could not parse IDs.", parent=self.parent
            )
            return
        try:
            from er_save_manager.games.NR.relic_ops import spawn_relic

            spawn_relic(
                save.slots[self._current_slot],
                real_item_id=rid,
                effect_1=effects[0],
                effect_2=effects[1],
                effect_3=effects[2],
                curse_1=curses[0],
                curse_2=curses[1],
                curse_3=curses[2],
            )
            _backup_and_save(save, self._get_save_path(), "nr_relic_spawn")
            self._populate_relics(save.slots[self._current_slot], keep_selection=True)
            self._populate_loadouts(save.slots[self._current_slot])
            self._show_toast("Relic spawned.")
        except Exception as e:
            CTkMessageBox.showerror("Spawn Failed", str(e), parent=self.parent)

    # ------------------------------------------------------------------
    # Copy to spawn / JSON import and export
    # ------------------------------------------------------------------

    def _copy_to_spawn(self) -> None:
        """Fill the spawn panel with the selected relic's type and rolls."""
        from er_save_manager.games.NR.item_db import relic_name

        if self._selected_relic_ga is None:
            notify(self.parent, "Select a relic row first.", "warning")
            return
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            return
        rs = save.slots[self._current_slot].relic_states.get(self._selected_relic_ga)
        if rs is None:
            return
        self._spawn_relic_id.set(rs.real_item_id)
        self._spawn_relic_label.configure(text=relic_name(rs.real_item_id))
        effects = rs.effects_list()
        for j in range(3):
            self._spawn_effect_vars[j].set(str(effects[j]))
            self._spawn_effect_labels[j].configure(text=_fmt_effect(effects[j]))
            self._spawn_curse_vars[j].set(str(effects[j + 3]))
        self._refresh_rows("spawn")
        self._show_relic_pane("spawn")

    def _export_relics_json(self) -> None:
        import json

        from er_save_manager.games.NR.relic_ops import relic_to_dict
        from er_save_manager.ui.utils import pick_file

        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            notify(self.parent, "Load a slot first.", "warning")
            return
        # Export what the grid currently shows, so a search or filter narrows
        # the export
        shown = set(self._relic_grid.visible_keys())
        slot = save.slots[self._current_slot]
        rows = [
            relic_to_dict(rs)
            for rs in slot.relic_states.values()
            if rs.ga_handle in shown
        ]
        path = pick_file(
            "Export Relics",
            filetypes=[("JSON", "*.json")],
            save=True,
            defaultextension=".json",
            initialfile=f"nr_relics_{slot.player_name or 'slot'}.json",
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(rows, indent=2), encoding="utf-8")
            self._show_toast(f"Exported {len(rows)} relics.")
        except OSError as e:
            CTkMessageBox.showerror("Export Failed", str(e), parent=self.parent)

    def _import_relics_json(self) -> None:
        import json

        from er_save_manager.games.NR.relic_ops import import_issues, import_relics
        from er_save_manager.ui.utils import pick_file

        if _game_blocks_write(self.parent):
            return
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            notify(self.parent, "Load a slot first.", "warning")
            return
        path = pick_file("Import Relics", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            rows = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(rows, list):
                raise ValueError("Expected a JSON list of relics")
        except (OSError, ValueError) as e:
            CTkMessageBox.showerror("Import Failed", str(e), parent=self.parent)
            return
        blocking, warnings = import_issues(rows)
        if blocking:
            CTkMessageBox.showerror(
                "Import Failed",
                "The game cannot roll these relics:\n" + "\n".join(blocking),
                parent=self.parent,
            )
            return
        prompt = f"Spawn {len(rows)} relics into this slot?"
        if warnings:
            prompt = (
                "\n".join(warnings)
                + "\n\nThese relics may come from mod data or an older game "
                "version.\n\n" + prompt
            )
        if not CTkMessageBox.askyesno("Confirm Import", prompt, parent=self.parent):
            return
        slot = save.slots[self._current_slot]
        try:
            handles = import_relics(slot, rows, allow_warnings=True)
            _backup_and_save(save, self._get_save_path(), "nr_relic_import")
        except Exception as e:
            CTkMessageBox.showerror("Import Failed", str(e), parent=self.parent)
            return
        self._populate_relics(slot, keep_selection=True)
        self._populate_loadouts(slot)
        self._show_toast(f"Imported {len(handles)} relics.")

    # ------------------------------------------------------------------
    # Loadouts (chalices and presets)
    # ------------------------------------------------------------------

    def _build_loadouts(self, parent, header) -> None:
        from er_save_manager.games.NR.parser import HERO_NAMES
        from er_save_manager.ui.utils import patch_combo_scroll
        from er_save_manager.ui.virtual_grid import VirtualIconGrid

        self._lo_count_label = ctk.CTkLabel(header, text="", text_color=ds.MUTED)
        self._lo_count_label.pack(side="left", padx=(8, 0))
        self._lo_view = ctk.CTkSegmentedButton(
            header,
            values=["Chalices", "Presets"],
            command=lambda _v: self._populate_loadout_grid(),
        )
        self._lo_view.set("Chalices")
        self._lo_view.pack(side="right")
        self._lo_hero_var = tk.StringVar(value=HERO_NAMES[0])
        self._lo_hero_combo = ctk.CTkComboBox(
            header,
            variable=self._lo_hero_var,
            values=HERO_NAMES,
            state="readonly",
            width=170,
            command=lambda _v: self._populate_loadout_grid(),
        )
        patch_combo_scroll(self._lo_hero_combo)
        self._lo_hero_combo.pack(side="right", padx=(0, 12))
        ctk.CTkLabel(header, text="Hero:").pack(side="right", padx=(0, 6))

        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._budget_label = ds.wrap_to_width(
            ctk.CTkLabel(body, text="", anchor="w", justify="left", font=ds.SMALL)
        )
        # Shown only for a missing, modded or over capacity loadout block

        split = ctk.CTkFrame(body, fg_color="transparent")
        split.pack(fill="both", expand=True)
        split.grid_columnconfigure(0, weight=1)
        split.grid_rowconfigure(0, weight=1)
        self._lo_split = split
        self._lo_grid = VirtualIconGrid(
            split,
            self._on_loadout_select,
            tooltip=self._loadout_tooltip,
            cell_w=124,
            cell_h=140,
            icon_size=72,
            fg_color=ds.LIST_BG,
            corner_radius=8,
        )
        self._lo_grid.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        # Grid key ("vessel" | "preset", position) -> VesselLoadout / CustomPreset
        self._lo_map: dict[tuple, object] = {}

        pane = ctk.CTkFrame(
            split, width=500, corner_radius=10, fg_color=("gray84", "gray24")
        )
        pane.grid_propagate(False)
        pane.pack_propagate(False)
        pane.grid(row=0, column=1, sticky="nsew")

        head = ctk.CTkFrame(pane, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(14, 6))
        self._lo_icon = ctk.CTkLabel(head, text="", width=72, height=72)
        self._lo_icon.pack(side="left", padx=(0, 12))
        text = ctk.CTkFrame(head, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True)
        self._lo_target_label = ds.wrap_to_width(
            ctk.CTkLabel(text, text="", font=ds.TITLE)
        )
        self._lo_target_label.pack(fill="x")
        self._lo_kind_label = ds.wrap_to_width(
            ctk.CTkLabel(text, text="", font=ds.SMALL, text_color=ds.MUTED)
        )
        self._lo_kind_label.pack(fill="x")

        btns = ctk.CTkFrame(pane, fg_color="transparent")
        btns.pack(side="bottom", fill="x", padx=14, pady=14)
        self._lo_delete_btn = ds.button(
            btns, "Delete Preset", self._delete_preset, primary=False, width=120
        )
        self._lo_delete_btn.pack(side="left")
        self._lo_new_btn = ds.button(
            btns, "Save as New Preset", self._save_as_new_preset, width=150
        )
        self._lo_new_btn.pack(side="right")

        self._lo_name_row = ctk.CTkFrame(pane, fg_color="transparent")
        self._lo_name_title = ctk.CTkLabel(self._lo_name_row, text="", anchor="w")
        self._lo_name_title.pack(side="left")
        self._lo_name_var = tk.StringVar()
        ctk.CTkEntry(self._lo_name_row, textvariable=self._lo_name_var).pack(
            side="left", fill="x", expand=True, padx=(8, 0)
        )

        # Packed holder, so the name row can be packed before it (the
        # scrollable frame itself is placed through an inner canvas)
        self._lo_cards_box = ctk.CTkFrame(pane, fg_color="transparent")
        self._lo_cards_box.pack(fill="both", expand=True, padx=8)
        # Scrolls when the window is too short for six cards
        self._lo_cards = ctk.CTkScrollableFrame(
            self._lo_cards_box, fg_color="transparent", corner_radius=0
        )
        self._lo_cards.pack(fill="both", expand=True)
        self._lo_slot_widgets: list[dict] = []
        for i in range(6):
            if i in (0, 3):
                ctk.CTkLabel(
                    self._lo_cards,
                    text="Relics" if i == 0 else "Deep relics",
                    font=ds.BOLD,
                    anchor="w",
                ).pack(fill="x", padx=6, pady=(6 if i == 0 else 12, 2))
            card = ctk.CTkFrame(self._lo_cards, fg_color=ds.BOX, corner_radius=8)
            card.pack(fill="x", pady=3)
            # height=1: fill="y" sizes it, CTkFrame would request 200 px
            stripe = ctk.CTkFrame(card, width=6, height=1, corner_radius=3)
            stripe.pack(side="left", fill="y", padx=(6, 0), pady=6)
            icon = ctk.CTkLabel(card, text="", width=48, height=48)
            icon.pack(side="left", padx=(8, 0), pady=6, anchor="n")
            side = ctk.CTkFrame(card, fg_color="transparent")
            side.pack(side="right", padx=8, pady=6, anchor="n")
            change = ds.button(
                side,
                "Change...",
                lambda ii=i: self._browse_loadout_slot(ii),
                primary=False,
                width=84,
                height=28,
            )
            change.pack()
            clear = ds.button(
                side,
                "Clear",
                lambda ii=i: self._set_loadout_slot(ii, 0),
                primary=False,
                width=84,
                height=28,
            )
            clear.pack(pady=(4, 0))
            col = ctk.CTkFrame(card, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True, padx=8, pady=6, anchor="n")
            title = ctk.CTkLabel(
                col, text="", font=ds.SMALL, text_color=ds.MUTED, anchor="w"
            )
            title.pack(fill="x")
            name = ds.wrap_to_width(ctk.CTkLabel(col, text="", font=ds.FONT))
            name.pack(fill="x")
            effects = ds.wrap_to_width(
                ctk.CTkLabel(col, text="", font=ds.SMALL, text_color=ds.MUTED)
            )
            effects.pack(fill="x")
            problem = ds.wrap_to_width(
                ctk.CTkLabel(col, text="", font=ds.SMALL, text_color=ds.ERROR)
            )
            self._lo_slot_widgets.append(
                {
                    "stripe": stripe,
                    "icon": icon,
                    "title": title,
                    "name": name,
                    "effects": effects,
                    "problem": problem,
                    "buttons": (change, clear),
                }
            )

        self._lo_kind: str | None = None
        self._lo_target = None
        self._lo_relics: list[int] = [0] * 6
        self._clear_loadout_edit()

    def _current_nr_slot(self):
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            return None
        return save.slots[self._current_slot]

    def _relic_effect_lines(self, rs) -> list[str]:
        """Effect names of a relic, each curse indented below its effect."""
        from er_save_manager.games.NR.item_db import effect_name

        effects = rs.effects_list()
        lines = []
        for j in range(3):
            if effects[j] != _EMPTY_EFFECT:
                lines.append(effect_name(effects[j]))
            if effects[j + 3] != _EMPTY_EFFECT:
                lines.append(f"    Curse: {effect_name(effects[j + 3])}")
        return lines

    def _populate_loadouts(self, slot) -> None:
        info = slot.loadout
        lines = []
        color = ds.WARNING
        if info is None:
            lines.append("No relic loadout section found in this slot.")
        else:
            if not info.is_vanilla:
                lines.append("Modded chalice counts (vanilla: 4 universal, 70 hero).")
            if info.spare_bytes < 0:
                lines.append(
                    f"Over capacity by {-info.spare_bytes} bytes. The game still "
                    f"writes the {info.presets_that_fit} presets that fit but "
                    "loads none of them. They stay in the file."
                )
                color = ds.ERROR
        if lines:
            self._budget_label.configure(text="\n".join(lines), text_color=color)
            self._budget_label.pack(fill="x", pady=(0, 6), before=self._lo_split)
        else:
            self._budget_label.pack_forget()
        from er_save_manager.games.NR.parser import HERO_NAMES

        heroes = list(HERO_NAMES)
        if slot.unassigned_vessels:
            heroes.append(_MODDED_HERO_LABEL)
        self._lo_hero_combo.configure(values=heroes)
        if self._lo_hero_var.get() not in heroes:
            self._lo_hero_var.set(HERO_NAMES[0])
        self._clear_loadout_edit()
        self._populate_loadout_grid()

    def _selected_hero_type(self) -> int:
        from er_save_manager.games.NR.parser import HERO_NAMES

        name = self._lo_hero_var.get()
        if name == _MODDED_HERO_LABEL:
            return 0
        return HERO_NAMES.index(name) + 1 if name in HERO_NAMES else 1

    def _populate_loadout_grid(self) -> None:
        """Grid of the selected hero's chalices or presets; the edited target
        stays selected when it is shown."""
        from er_save_manager.games.NR.item_db import vessel_name
        from er_save_manager.ui.virtual_grid import GridEntry

        self._lo_map.clear()
        slot = self._current_nr_slot()
        vessels, presets = [], []
        if slot is not None:
            hero_type = self._selected_hero_type()
            if hero_type == 0:
                vessels = slot.unassigned_vessels
            elif (hero := slot.heroes.get(hero_type)) is not None:
                vessels = hero.vessels
                presets = sorted(hero.presets, key=lambda p: p.counter)

        entries = []
        if self._lo_view.get() == "Chalices":
            for pos, v in enumerate(vessels):
                name = _short_vessel_name(vessel_name(v.vessel_id))
                key = ("vessel", pos)
                self._lo_map[key] = v
                entries.append(
                    GridEntry(
                        key,
                        name,
                        name.lower(),
                        lambda vid=v.vessel_id: _vessel_grid_icon(vid),
                    )
                )
        else:
            for pos, p in enumerate(presets):
                name = p.name or "(unnamed)"
                chalice = _short_vessel_name(vessel_name(p.vessel_id))
                key = ("preset", pos)
                self._lo_map[key] = p
                entries.append(
                    GridEntry(
                        key,
                        f"{name}\n{chalice}",
                        f"{name} {chalice}".lower(),
                        lambda vid=p.vessel_id: _vessel_grid_icon(vid),
                    )
                )
        self._lo_grid.set_entries(entries)
        self._lo_count_label.configure(text=str(len(entries)) if slot else "")
        self._reselect_loadout_target()

    def _loadout_tooltip(self, key) -> str:
        """Chalice or preset name, then each slot with its relic."""
        from er_save_manager.games.NR.item_db import relic_name, vessel_name

        target = self._lo_map.get(key)
        slot = self._current_nr_slot()
        if target is None or slot is None:
            return ""
        lines = [vessel_name(target.vessel_id)]
        if key[0] == "preset":
            lines.insert(0, target.name or "(unnamed)")
        lines.append("")
        for i, ga in enumerate(target.relics):
            rs = slot.relic_states.get(ga) if ga else None
            what = "-" if not ga else relic_name(rs.real_item_id) if rs else "missing"
            lines.append(f"{_slot_title(target.vessel_id, i)}: {what}")
        return "\n".join(lines)

    def _clear_loadout_edit(self) -> None:
        self._lo_kind = None
        self._lo_target = None
        self._lo_relics = [0] * 6
        self._lo_icon.configure(image=None)
        self._lo_target_label.configure(text="No chalice selected")
        self._lo_kind_label.configure(text="Select a chalice or preset in the grid.")
        self._lo_name_row.pack_forget()
        self._lo_delete_btn.configure(state="disabled")
        self._lo_new_btn.configure(state="disabled")
        self._refresh_loadout_slots()

    def _target_vessel_id(self) -> int:
        return self._lo_target.vessel_id if self._lo_target is not None else 0

    def _on_loadout_select(self, keys: list) -> None:
        from er_save_manager.games.NR.item_db import vessel_name

        target = self._lo_map.get(keys[0]) if keys else None
        if target is None or target is self._lo_target:
            return
        if self._loadout_changes() and not CTkMessageBox.askyesno(
            "Unapplied Loadout",
            "Discard the unapplied changes of the selected chalice or preset?",
            parent=self.parent,
        ):
            self._reselect_loadout_target()
            return

        self._lo_kind = keys[0][0]
        self._lo_target = target
        self._lo_relics = list(target.relics)
        vid = target.vessel_id
        self._lo_icon.configure(image=self._icon_image("vessel", vid, 72))
        hero = self._lo_hero_var.get()
        if self._lo_kind == "preset":
            self._lo_target_label.configure(text=target.name or "(unnamed)")
            self._lo_kind_label.configure(
                text=f"{hero} preset, {_short_vessel_name(vessel_name(vid))}"
            )
            self._lo_name_title.configure(text="Preset name:")
            self._lo_name_var.set(target.name)
            self._lo_delete_btn.configure(state="normal")
        else:
            self._lo_target_label.configure(text=_short_vessel_name(vessel_name(vid)))
            self._lo_kind_label.configure(text=f"{hero} chalice")
            # Name is only used when saving this chalice as a new preset
            self._lo_name_title.configure(text="New preset name:")
            self._lo_name_var.set("")
            self._lo_delete_btn.configure(state="disabled")
        self._lo_new_btn.configure(state="normal")
        self._lo_name_row.pack(
            fill="x", padx=14, pady=(0, 6), before=self._lo_cards_box
        )
        self._refresh_loadout_slots()

    def _reselect_loadout_target(self) -> None:
        """Select the edited chalice or preset in the grid, or nothing when it
        is not shown."""
        key = next((k for k, t in self._lo_map.items() if t is self._lo_target), None)
        self._lo_grid.set_selection([key] if key is not None else [], notify=False)

    def _refresh_loadout_slots(self) -> None:
        """Slot cards from the edit state: slot color stripe, relic icon,
        name, effects and why a relic does not fit its slot."""
        from er_save_manager.games.NR.item_db import (
            relic_name,
            vessel_slot_color,
            vessel_slot_error,
        )

        slot = self._current_nr_slot()
        vid = self._target_vessel_id()
        active = self._lo_target is not None
        for i, w in enumerate(self._lo_slot_widgets):
            color = vessel_slot_color(vid, i) if active else None
            w["stripe"].configure(fg_color=_SLOT_COLORS.get(color, ds.SECONDARY))
            w["title"].configure(
                text=_slot_title(vid, i) if active else f"Slot {i + 1}"
            )
            for btn in w["buttons"]:
                btn.configure(state="normal" if active else "disabled")
            ga = self._lo_relics[i]
            rs = slot.relic_states.get(ga) if slot is not None and ga else None
            problem = ""
            if not ga:
                w["icon"].configure(image=None)
                w["name"].configure(text="Empty")
                w["effects"].configure(text="")
            elif rs is None:
                w["icon"].configure(image=None)
                w["name"].configure(text=f"Missing relic 0x{ga:08X}")
                w["effects"].configure(text="")
                problem = "This relic is not in the inventory."
            else:
                w["icon"].configure(
                    image=self._icon_image("relic", rs.real_item_id, 48)
                )
                w["name"].configure(text=relic_name(rs.real_item_id))
                w["effects"].configure(text="\n".join(self._relic_effect_lines(rs)))
                err = vessel_slot_error(vid, i, rs.real_item_id)
                if err:
                    problem = f"Does not fit: {err}."
                elif ga in self._lo_relics[:i]:
                    problem = "Same relic as an earlier slot."
            w["problem"].configure(text=problem)
            if problem:
                w["problem"].pack(fill="x")
            else:
                w["problem"].pack_forget()

    def _set_loadout_slot(self, idx: int, ga: int) -> None:
        if self._lo_target is None:
            return
        self._lo_relics[idx] = ga
        self._refresh_loadout_slots()

    def _browse_loadout_slot(self, idx: int) -> None:
        from er_save_manager.games.NR.item_db import relic_name, vessel_slot_error

        slot = self._current_nr_slot()
        if self._lo_target is None or slot is None:
            return
        vid = self._target_vessel_id()
        # Relics in the other slots are left out: one relic per loadout
        others = {ga for j, ga in enumerate(self._lo_relics) if j != idx and ga}
        relics = sorted(
            (
                rs
                for rs in slot.relic_states.values()
                if not vessel_slot_error(vid, idx, rs.real_item_id)
                and rs.ga_handle not in others
            ),
            key=lambda rs: relic_name(rs.real_item_id),
        )
        picker = _SlotRelicPicker(
            self.parent,
            f"Select Relic for Slot {idx + 1}",
            relics,
            self._lo_relics[idx],
            self._relic_effect_lines,
        )
        if picker.result is not None:
            self._set_loadout_slot(idx, picker.result)

    def _loadout_changes(self) -> int:
        if self._lo_target is None:
            return 0
        changed = sum(
            a != b
            for a, b in zip(self._lo_relics, self._lo_target.relics, strict=False)
        )
        if self._lo_kind == "preset":
            changed += int(self._lo_name_var.get().strip() != self._lo_target.name)
        return changed

    def _discard_loadout(self) -> None:
        if self._lo_target is None:
            return
        self._lo_relics = list(self._lo_target.relics)
        if self._lo_kind == "preset":
            self._lo_name_var.set(self._lo_target.name)
        self._refresh_loadout_slots()

    def _prepare_loadout(self):
        from er_save_manager.games.NR.item_db import vessel_slot_error

        save = self._get_nr_save()
        slot = self._current_nr_slot()
        if self._lo_target is None or save is None or slot is None:
            raise StageError("Select a chalice or preset first.")

        vid = self._target_vessel_id()
        warnings = []
        seen: set[int] = set()
        for i, ga in enumerate(self._lo_relics):
            if ga == 0:
                continue
            rs = slot.relic_states.get(ga)
            if rs is None:
                warnings.append(f"Slot {i + 1}: relic 0x{ga:08X} is not in inventory")
                continue
            err = vessel_slot_error(vid, i, rs.real_item_id)
            if err:
                warnings.append(f"Slot {i + 1}: {err}")
            if ga in seen:
                warnings.append(f"Slot {i + 1}: same relic equipped twice")
            seen.add(ga)
        if warnings and not CTkMessageBox.askyesno(
            "Loadout Issues",
            "Issues found in the loadout:\n"
            + "\n".join(warnings)
            + "\n\nApply anyway?",
            parent=self.parent,
        ):
            raise StageCancelled()

        kind, target, slot_index = self._lo_kind, self._lo_target, self._current_slot
        relics = list(self._lo_relics)
        name = self._lo_name_var.get().strip()

        def commit() -> None:
            if kind == "preset":
                save.update_preset(slot_index, target.index, name=name, relics=relics)
            else:
                target.relics = relics
                target.write_to(slot.decrypted)

        return commit

    def _save_as_new_preset(self) -> None:
        """Store the edit panel's relics as a new preset for the target's hero."""
        if _game_blocks_write(self.parent):
            return
        if self._lo_target is None:
            notify(self.parent, "Select a chalice or preset first.", "warning")
            return
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            return
        name = self._lo_name_var.get().strip()
        if len(name) > 18:
            CTkMessageBox.showerror(
                "Name Too Long",
                "Preset name cannot exceed 18 characters.",
                parent=self.parent,
            )
            return
        hero_type = (
            self._lo_target.hero_id
            if self._lo_kind == "preset"
            else self._selected_hero_type()
        )
        if hero_type == 0:
            notify(
                self.parent,
                "Modded chalices have no known hero, so no preset can be made from them.",
                "warning",
            )
            return
        try:
            save.create_preset(
                self._current_slot,
                hero_type,
                name,
                self._lo_target.vessel_id,
                self._lo_relics,
            )
            _backup_and_save(save, self._get_save_path(), "nr_preset_create")
        except Exception as e:
            CTkMessageBox.showerror("Save Failed", str(e), parent=self.parent)
            return
        self._populate_loadouts(save.slots[self._current_slot])
        self._show_toast("Preset created.")

    def _delete_preset(self) -> None:
        if _game_blocks_write(self.parent):
            return
        if self._lo_kind != "preset" or self._lo_target is None:
            notify(self.parent, "Select a preset first.", "warning")
            return
        name = self._lo_target.name or "(unnamed)"
        if not CTkMessageBox.askyesno(
            "Confirm Delete", f"Delete preset '{name}'?", parent=self.parent
        ):
            return
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            return
        try:
            save.delete_preset(self._current_slot, self._lo_target.index)
            _backup_and_save(save, self._get_save_path(), "nr_preset_delete")
        except Exception as e:
            CTkMessageBox.showerror("Delete Failed", str(e), parent=self.parent)
            return
        self._populate_loadouts(save.slots[self._current_slot])
        self._show_toast("Preset deleted.")
