"""
Visual spawn popup for DS3.

Shows the inventory tab's spawn list (category, search, game data source
and cut content filter included) as an icon grid. Click selects an item,
Ctrl click adds or removes one and Shift click selects a range. Spawn goes
through the tab's own spawn path, so limits and the save/backup step are
shared with the text list.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.games.DS3 import catalog
from er_save_manager.games.DS3.icon_manager import item_icon
from er_save_manager.games.DS3.slot import ID_WEAPON, id_kind
from er_save_manager.games.DS3.tabs.inventory import (
    LOCATIONS,
    enable,
    infusion_image,
)
from er_save_manager.ui import palette
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.tooltip import MULTI_SELECT_TIP, add_tooltip
from er_save_manager.ui.utils import (
    center_window,
    debounced_trace,
    patch_combo_scroll,
)
from er_save_manager.ui.virtual_grid import GridEntry, VirtualIconGrid

if TYPE_CHECKING:
    from er_save_manager.games.DS3.tabs.inventory import DS3InventoryTab

ICON_SIZE = 64
CELL_W = 116
CELL_H = 124
CELL_PAD = 4
SCROLLBAR_W = 24
DEFAULT_COLS = 5
SELECTED_TEXT = palette.PURPLE_TEXT


def item_entry(key, item: dict | None, source: str, text: str, search: str):
    """Grid entry for an item; the icon loads when the cell scrolls into view."""
    return GridEntry(key, text, search, lambda: item_icon(item, source))


class IconGrid(VirtualIconGrid):
    """Multi-select grid of item cells. load(entries, make) builds the cells
    from make(entry), which returns a GridEntry."""

    def __init__(self, parent, on_select) -> None:
        super().__init__(
            parent,
            on_select,
            multi=True,
            cell_w=CELL_W,
            cell_h=CELL_H,
            pad=CELL_PAD,
            icon_size=ICON_SIZE,
        )

    def load(self, entries: list, make, keep_selection: bool = False) -> None:
        self.set_entries([make(e) for e in entries], keep_selection)
        # Keys selected before a reload may be gone now.
        self.set_selection(self.selected)


def open_popup(window: ctk.CTkToplevel, parent, title: str) -> None:
    """Size, center and raise a grid popup."""
    w = DEFAULT_COLS * (CELL_W + CELL_PAD * 2) + 12 + SCROLLBAR_W + 30
    window.title(title)
    window.geometry(f"{w}x760")
    window.minsize(w, 480)
    window.transient(parent)
    window.attributes("-alpha", 0)
    window.update_idletasks()
    center_window(window, w, 760, parent=parent, align_top=True)
    window.attributes("-alpha", 1)
    window.lift()
    window.focus_force()


def search_row(window, on_change=None, var: tk.StringVar | None = None) -> tk.StringVar:
    """Search entry plus Close button across the top of a popup.

    on_change gets the lowercased query once typing pauses. var binds the
    entry to an existing variable instead, such as the tab's spawn search.
    """
    top = ctk.CTkFrame(window, fg_color="transparent")
    top.pack(fill="x", padx=10, pady=(10, 4))
    ctk.CTkLabel(top, text="Search:", width=52).pack(side="left")
    if var is None:
        var = tk.StringVar()
    if on_change is not None:
        debounced_trace(window, var, lambda: on_change(var.get().lower().strip()))
    ctk.CTkEntry(top, textvariable=var).pack(
        side="left", fill="x", expand=True, padx=(0, 8)
    )
    ctk.CTkButton(
        top,
        text="Close",
        width=64,
        height=28,
        fg_color=("gray70", "gray35"),
        command=window.destroy,
    ).pack(side="right")
    return var


def follow_spawn_list(window: ctk.CTkToplevel, tab, reload) -> None:
    """Call reload whenever tab recomputes its spawn list, until window closes.

    The picker shares the tab's search and category, so the tab's spawn list
    is the only filter; reloads are coalesced while the user types.
    """
    job = None

    def fire():
        nonlocal job
        job = None
        if window.winfo_exists():
            reload()

    def changed():
        nonlocal job
        if job is not None:
            window.after_cancel(job)
        job = window.after(150, fire)

    def on_destroy(event):
        if event.widget is window and changed in tab.spawn_listeners:
            tab.spawn_listeners.remove(changed)

    tab.spawn_listeners.append(changed)
    window.bind("<Destroy>", on_destroy, add="+")


class DS3IconBrowser(ctk.CTkToplevel):
    """Icon grid over the inventory tab's spawn list."""

    def __init__(self, parent, tab: DS3InventoryTab) -> None:
        super().__init__(parent)
        self._tab = tab
        self._rows: dict[int, tuple[str, dict, list[dict]]] = {}
        self._selected_item: dict | None = None
        self._variants: list[dict] = []
        open_popup(self, parent, "Spawn Items")
        self._build_ui()
        self._load_items()
        follow_spawn_list(self, tab, self._load_items)

    def _build_ui(self) -> None:
        # Shares the tab's search and category, so the grid and the spawn
        # list always show the same items.
        search_row(self, var=self._tab.spawn_search_var)

        cat_row = ctk.CTkFrame(self, fg_color="transparent")
        cat_row.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(cat_row, text="Category:", width=68).pack(side="left")
        # Drives the tab's own category, so the grid mirrors the spawn list.
        options = self._tab.category_options()
        self._cat_var = self._tab.spawn_category_var
        patch_combo_scroll(
            ctk.CTkComboBox(
                cat_row,
                variable=self._cat_var,
                values=options,
                state="readonly",
                command=self._on_category_change,
            )
        ).pack(side="left", fill="x", expand=True)

        self._grid = IconGrid(self, self._on_select)
        self._grid.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        add_tooltip(self._grid._canvas, MULTI_SELECT_TIP)
        panel = ctk.CTkFrame(self, fg_color=("gray88", "gray18"), corner_radius=8)
        panel.pack(fill="x", padx=6, pady=(0, 8))
        self._sel_lbl = ctk.CTkLabel(
            panel,
            text="No item selected",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            text_color=("gray50", "gray60"),
        )
        self._sel_lbl.pack(fill="x", padx=10, pady=(8, 4))

        opts = ctk.CTkFrame(panel, fg_color="transparent")
        opts.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(opts, text="Quantity:").grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        self._qty_var = tk.StringVar(value="1")
        self._qty_entry = ctk.CTkEntry(opts, textvariable=self._qty_var, width=60)
        self._qty_entry.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(opts, text="Upgrade:").grid(
            row=0, column=2, sticky="w", padx=(14, 6)
        )
        self._upgrade_var = tk.StringVar(value="0")
        self._upgrade_entry = ctk.CTkEntry(
            opts, textvariable=self._upgrade_var, width=50
        )
        self._upgrade_entry.grid(row=0, column=3, sticky="w")

        ctk.CTkLabel(opts, text="Infusion:").grid(
            row=1, column=0, sticky="w", padx=(0, 6), pady=(6, 0)
        )
        inf_cell = ctk.CTkFrame(opts, fg_color="transparent")
        inf_cell.grid(row=1, column=1, columnspan=3, sticky="w", pady=(6, 0))
        self._infusion_icon = ctk.CTkLabel(inf_cell, text="", width=24)
        self._infusion_icon.pack(side="left", padx=(0, 4))
        self._infusion_var = tk.StringVar(value="")
        self._infusion_combo = ctk.CTkComboBox(
            inf_cell,
            variable=self._infusion_var,
            values=[],
            width=140,
            state="disabled",
            command=self._on_infusion,
        )
        self._infusion_combo.pack(side="left")

        ctk.CTkLabel(opts, text="Location:").grid(
            row=2, column=0, sticky="w", padx=(0, 6), pady=(6, 0)
        )
        # Shares the tab's variable, since spawning goes through the tab.
        ctk.CTkComboBox(
            opts,
            variable=self._tab.location_var,
            values=list(LOCATIONS),
            width=130,
            state="readonly",
        ).grid(row=2, column=1, columnspan=3, sticky="w", pady=(6, 0))
        self._info = ctk.CTkLabel(
            opts, text="", font=("Segoe UI", 9), text_color=("gray40", "gray60")
        )
        self._info.grid(row=3, column=0, columnspan=4, sticky="w", pady=(4, 0))

        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.pack(fill="x", padx=10, pady=(6, 10))
        buttons.grid_columnconfigure((0, 1), weight=1)
        self._spawn_btn = ctk.CTkButton(
            buttons,
            text="Spawn Selected",
            height=34,
            font=("Segoe UI", 11, "bold"),
            command=self._do_spawn,
            state="disabled",
        )
        self._spawn_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(
            buttons,
            text="Spawn All Shown",
            height=34,
            command=self._do_spawn_all,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

    # --- Items ------------------------------------------------------------- #

    def _load_items(self) -> None:
        source = self._tab.source
        self._rows = dict(enumerate(self._tab.visible_spawn_items()))

        def make(entry):
            index, (label, item, _variants) = entry
            return item_entry(index, item, source, label, label.lower())

        self._grid.load(list(self._rows.items()), make)

    def _on_category_change(self, label: str) -> None:
        self._tab.set_category(label)

    # --- Selection and spawn ----------------------------------------------- #

    def _on_select(self, keys: list) -> None:
        self._spawn_btn.configure(state="normal" if keys else "disabled")
        if len(keys) != 1:
            self._selected_item = None
            self._variants = []
            self._infusion_combo.configure(values=[], state="disabled")
            self._infusion_var.set("")
            self._infusion_icon.configure(image=None)
            self._sel_lbl.configure(
                text=f"{len(keys)} items selected" if keys else "No item selected",
                text_color=SELECTED_TEXT if keys else ("gray50", "gray60"),
            )
            self._info.configure(
                text="Quantity and upgrade are capped per item" if keys else ""
            )
            # Several or no items (Spawn All Shown): both apply, capped per item.
            enable(self._qty_entry, True)
            enable(self._upgrade_entry, True)
            return
        label, item, variants = self._rows[keys[0]]
        self._variants = variants
        labels = [v["Infusion"] for v in variants]
        self._infusion_combo.configure(
            values=labels, state="readonly" if labels else "disabled"
        )
        self._infusion_var.set(item.get("Infusion", "") if labels else "")
        self._sel_lbl.configure(text=f"Selected: {label}", text_color=SELECTED_TEXT)
        self._select_item(item)

    def _on_infusion(self, chosen: str) -> None:
        item = next((v for v in self._variants if v["Infusion"] == chosen), None)
        if item is not None:
            self._select_item(item)

    def _select_item(self, item: dict) -> None:
        self._selected_item = item
        self._infusion_icon.configure(image=infusion_image(item, self._tab.source))
        lim = catalog.limits(item)
        upgradable = id_kind(int(item["Id"], 16)) == ID_WEAPON and lim.max_upgrade > 0
        enable(self._qty_entry, lim.max_quantity > 1)
        enable(self._upgrade_entry, upgradable)
        info = []
        if lim.max_quantity > 1:
            info.append(f"Max stack: {lim.max_quantity}")
        if lim.max_upgrade:
            info.append(f"Max upgrade: +{lim.max_upgrade}")
        if lim.key_item:
            info.append("Key item")
        self._info.configure(text="  ".join(info))

    def _read_values(self) -> tuple[int, int] | None:
        try:
            return int(self._qty_var.get()), int(self._upgrade_var.get())
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Value", "Enter valid integers.", parent=self
            )
            return None

    def _do_spawn(self) -> None:
        values = self._read_values()
        if values is None:
            return
        if len(self._grid.selected) == 1 and self._selected_item is not None:
            items = [self._selected_item]
        else:
            items = [self._rows[k][1] for k in self._grid.selected]
        self._tab.spawn_items(items, *values, parent=self)

    def _do_spawn_all(self) -> None:
        values = self._read_values()
        if values is None:
            return
        items = [self._rows[k][1] for k in self._grid.visible_keys()]
        self._tab.spawn_items(items, *values, parent=self)
