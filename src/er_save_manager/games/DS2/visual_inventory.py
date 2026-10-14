"""
Visual current-inventory popup for DS2.

The inventory is a fixed slot table that is almost all empty, so a plain
button grid is fast enough.

Selecting icons selects the matching rows in the panel's own inventory tree
and drives its existing Remove/Set Quantity/Set Upgrade/Set Infusion/move
controls, so the write logic and its caps stay in one place. Click selects
one icon, Ctrl click adds or removes one and Shift click selects a range;
the panel's actions apply to every selected row.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.games.DS2.icon_manager import (
    add_infusion_menu_icons,
    bind_infusion_icon,
)
from er_save_manager.games.DS2.regulation import INFUSION_NAMES
from er_save_manager.games.DS2.save import INVENTORY_END, INVENTORY_START
from er_save_manager.ui import palette
from er_save_manager.ui.tooltip import MULTI_SELECT_TIP, add_tooltip
from er_save_manager.ui.utils import (
    center_window,
    patch_combo_scroll,
)
from er_save_manager.ui.virtual_grid import GridEntry, VirtualIconGrid

if TYPE_CHECKING:
    from er_save_manager.games.DS2.inventory_tab import DS2InventoryPanel

_ICON_SIZE = 56
_CELL_W = 110
_CELL_H = 124
_CELL_PAD = 4
_SCROLLBAR_W = 24
_DEFAULT_COLS = 5
# Show choices, both locations first as the default.
_LOCATION_FILTERS = ("All", "Inventory", "Item Box")


def _center_over(window, parent, w=None, h=None) -> None:
    center_window(window, w, h, parent=parent, align_top=True)


class VisualInventoryBrowser(ctk.CTkToplevel):
    """Icon-grid view of the current character's inventory."""

    def __init__(self, parent, panel: DS2InventoryPanel):
        super().__init__(parent)
        self._panel = panel
        # Selected tree indices in grid order
        self._selected: list[int] = []
        # Rows the grid was built from; indices above point into this, so a
        # panel re-filter can never shift them onto other items.
        self._items: list[tuple] = []
        self._reload_job: str | None = None

        w = _DEFAULT_COLS * (_CELL_W + _CELL_PAD * 2) + 12 + _SCROLLBAR_W + 30
        self.title("Visual Inventory")
        self.geometry(f"{w}x740")
        self.minsize(560, 480)
        self.transient(parent)
        self.attributes("-alpha", 0)
        self.update_idletasks()
        _center_over(self, parent, w, 740)
        self.attributes("-alpha", 1)
        self.lift()
        self.focus_force()

        self._build_ui()
        self._load_icons()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        panel.listeners.append(self._on_panel_filtered)
        self.bind("<Destroy>", self._on_destroy, add="+")

    def _on_destroy(self, event) -> None:
        if event.widget is self and self._on_panel_filtered in self._panel.listeners:
            self._panel.listeners.remove(self._on_panel_filtered)

    def _on_panel_filtered(self) -> None:
        """The panel's rows changed (filter typed here or in the tab, an edit,
        another character); reload once changes pause."""
        if self._reload_job is not None:
            self.after_cancel(self._reload_job)
        self._reload_job = self.after(150, self._reload_from_panel)

    def _reload_from_panel(self) -> None:
        self._reload_job = None
        if self.winfo_exists():
            self._load_icons()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(top, text="Category:", width=68).pack(side="left")
        # Category and filter share the panel's variables, so the tab and this
        # window always show the same rows.
        patch_combo_scroll(
            ctk.CTkComboBox(
                top,
                variable=self._panel.filter_category_var,
                values=["All"] + list(self._category_labels().values()),
                state="readonly",
                width=150,
                command=lambda _v: self._panel._apply_filter(),
            )
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(top, text="Show:").pack(side="left")
        self._location_var = tk.StringVar(value=_LOCATION_FILTERS[0])
        ctk.CTkComboBox(
            top,
            variable=self._location_var,
            values=list(_LOCATION_FILTERS),
            state="readonly",
            width=100,
            command=lambda _v: self._load_icons(),
        ).pack(side="left", padx=(4, 8))

        ctk.CTkLabel(top, text="Filter:").pack(side="left")
        ctk.CTkEntry(top, textvariable=self._panel.filter_search_var).pack(
            side="left", fill="x", expand=True, padx=(4, 8)
        )
        ctk.CTkButton(
            top,
            text="Close",
            width=64,
            height=28,
            fg_color=("gray70", "gray35"),
            command=self.destroy,
        ).pack(side="right")

        self._grid = VirtualIconGrid(
            self,
            self._on_select,
            multi=True,
            cell_w=_CELL_W,
            cell_h=_CELL_H,
            pad=_CELL_PAD,
            icon_size=_ICON_SIZE,
        )
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

        ctk.CTkLabel(opts, text="Qty:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self._qty_var = tk.StringVar(value="1")
        self._qty_entry = ctk.CTkEntry(
            opts, textvariable=self._qty_var, width=55, state="disabled"
        )
        self._qty_entry.grid(row=0, column=1, sticky="w")
        self._qty_btn = ctk.CTkButton(
            opts, text="Set", width=44, command=self._do_qty, state="disabled"
        )
        self._qty_btn.grid(row=0, column=2, sticky="w", padx=(4, 14))

        ctk.CTkLabel(opts, text="Upgrade:").grid(
            row=0, column=3, sticky="w", padx=(0, 6)
        )
        self._upgrade_var = tk.StringVar(value="0")
        self._upgrade_entry = ctk.CTkEntry(
            opts, textvariable=self._upgrade_var, width=50, state="disabled"
        )
        self._upgrade_entry.grid(row=0, column=4, sticky="w")
        self._upgrade_btn = ctk.CTkButton(
            opts, text="Set", width=44, command=self._do_upgrade, state="disabled"
        )
        self._upgrade_btn.grid(row=0, column=5, sticky="w", padx=(4, 14))

        ctk.CTkLabel(opts, text="Infusion:").grid(
            row=1, column=0, sticky="w", padx=(0, 6), pady=(6, 0)
        )
        self._infusion_var = tk.StringVar(value=INFUSION_NAMES[0])
        infusion_cell = ctk.CTkFrame(opts, fg_color="transparent")
        infusion_cell.grid(row=1, column=1, columnspan=2, sticky="w", pady=(6, 0))
        infusion_icon = ctk.CTkLabel(infusion_cell, text="", width=24)
        infusion_icon.pack(side="left", padx=(0, 4))
        bind_infusion_icon(infusion_icon, self._infusion_var)
        self._infusion_combo = ctk.CTkComboBox(
            infusion_cell,
            variable=self._infusion_var,
            values=[INFUSION_NAMES[0]],
            width=110,
            state="disabled",
        )
        self._infusion_combo.pack(side="left")
        add_infusion_menu_icons(self._infusion_combo)
        self._infusion_btn = ctk.CTkButton(
            opts, text="Set", width=44, command=self._do_infusion, state="disabled"
        )
        self._infusion_btn.grid(row=1, column=3, sticky="w", padx=(4, 0), pady=(6, 0))

        move_row = ctk.CTkFrame(panel, fg_color="transparent")
        move_row.pack(fill="x", padx=10, pady=(6, 0))
        self._to_box_btn = ctk.CTkButton(
            move_row,
            text="To Item Box",
            height=30,
            command=lambda: self._do_move(True),
            state="disabled",
        )
        self._to_box_btn.pack(side="left", fill="x", expand=True, padx=(0, 3))
        self._to_inventory_btn = ctk.CTkButton(
            move_row,
            text="To Inventory",
            height=30,
            command=lambda: self._do_move(False),
            state="disabled",
        )
        self._to_inventory_btn.pack(side="left", fill="x", expand=True, padx=(3, 0))

        self._remove_btn = ctk.CTkButton(
            panel,
            text="Remove Selected",
            height=32,
            command=self._do_remove,
            state="disabled",
        )
        self._remove_btn.pack(fill="x", padx=10, pady=(6, 10))

    def _category_labels(self) -> dict:
        from er_save_manager.games.DS2.inventory_tab import CATEGORY_LABELS

        return CATEGORY_LABELS

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load_icons(self) -> None:
        from er_save_manager.games.DS2.icon_manager import (
            get_icon,
            with_infusion_badge,
        )
        from er_save_manager.games.DS2.inventory_tab import STACKABLE_CATEGORIES
        from er_save_manager.games.DS2.save import UPGRADABLE_CATEGORIES

        def icon(item, category):
            img = get_icon(item.item_id, category)
            if img and category == "weapons" and item.infusion:
                img = with_infusion_badge(img, item.infusion)
            return img

        location = self._location_var.get()
        self._items = list(self._panel._visible_items)
        entries = []
        for idx, (item, name, category) in enumerate(self._items):
            if location != _LOCATION_FILTERS[0] and item.in_box != (
                location == _LOCATION_FILTERS[2]
            ):
                continue
            label = name
            if category in STACKABLE_CATEGORIES and item.quantity > 1:
                label = f"{name} x{item.quantity}"
            elif category in UPGRADABLE_CATEGORIES and item.upgrade:
                label = f"{name} +{item.upgrade}"
            if item.in_box:
                label = f"{label}\n(Item Box)"
            entries.append(
                GridEntry(
                    idx, label, name.lower(), lambda i=item, c=category: icon(i, c)
                )
            )
        self._grid.set_entries(entries)
        self._selected = []
        self._sel_lbl.configure(
            text="No item selected", text_color=("gray50", "gray60")
        )
        self._update_form()

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _select_tree_rows(self, indices: list[int]) -> None:
        """Select the panel tree rows holding these grid items. Rows are
        matched by item object, not position, so a tree that was re-filtered
        or reloaded since the grid was built never gets other items selected."""
        tree = self._panel._inventory_tree
        children = tree.get_children()
        row_of = {id(entry[0]): k for k, entry in enumerate(self._panel._visible_items)}
        rows = (row_of.get(id(self._items[i][0])) for i in indices)
        tree.selection_set([children[r] for r in rows if r is not None])

    def _on_select(self, keys: list) -> None:
        self._selected = list(keys)
        if len(self._selected) == 1:
            name = self._items[self._selected[0]][1]
            text = f"Selected: {name}"
        else:
            text = f"{len(self._selected)} items selected"
        self._sel_lbl.configure(
            text=text if self._selected else "No item selected",
            text_color=palette.PURPLE_TEXT,
        )
        self._select_tree_rows(self._selected)
        self._panel._update_inventory_controls()
        self._update_form()

    def _update_form(self) -> None:
        """Enable each control when it applies to at least one selected item;
        the panel's actions skip and report the ones it does not apply to.
        With one item selected its current values fill the fields."""
        panel = self._panel
        character = panel._current_character()
        rows = [self._items[i] for i in self._selected]
        quantity = upgrade = infusion = False
        allowed: set[int] = set()
        can_box = can_unbox = False

        if character is not None:
            for item, _name, category in rows:
                if panel._quantity_limit(character, item, category):
                    quantity = True
                if panel._upgrade_limit(character, item, category):
                    upgrade = True
                choices = panel._infusion_choices(character, item, category)
                if choices:
                    infusion = True
                    allowed.update(choices)
                if INVENTORY_START <= item.offset < INVENTORY_END:
                    can_box = can_box or not item.in_box
                    can_unbox = can_unbox or item.in_box
            if len(rows) == 1:
                item, _name, category = rows[0]
                if quantity:
                    self._qty_var.set(str(item.quantity))
                if upgrade:
                    self._upgrade_var.set(str(item.upgrade))
                if infusion:
                    self._infusion_var.set(INFUSION_NAMES[item.infusion])

        self._qty_entry.configure(state="normal" if quantity else "disabled")
        self._qty_btn.configure(state="normal" if quantity else "disabled")
        self._upgrade_entry.configure(state="normal" if upgrade else "disabled")
        self._upgrade_btn.configure(state="normal" if upgrade else "disabled")
        names = [INFUSION_NAMES[n] for n in sorted(allowed or {0})]
        self._infusion_combo.configure(
            values=names, state="readonly" if infusion else "disabled"
        )
        self._infusion_btn.configure(state="normal" if infusion else "disabled")
        if self._infusion_var.get() not in names:
            self._infusion_var.set(names[0])
        self._remove_btn.configure(state="normal" if rows else "disabled")
        self._to_box_btn.configure(state="normal" if can_box else "disabled")
        self._to_inventory_btn.configure(state="normal" if can_unbox else "disabled")

    # ------------------------------------------------------------------
    # Actions, delegated to the panel's own Set/Remove
    # ------------------------------------------------------------------

    # Each action re-selects this window's items in the panel tree first (the
    # tree may have been re-filtered since), then re-filters the panel, which
    # reloads this grid through the panel listener.
    def _do_qty(self) -> None:
        self._select_tree_rows(self._selected)
        self._panel.set_qty_var.set(self._qty_var.get())
        self._panel._on_set_quantity()
        self._panel._apply_filter()

    def _do_upgrade(self) -> None:
        self._select_tree_rows(self._selected)
        self._panel.set_upgrade_var.set(self._upgrade_var.get())
        self._panel._on_set_upgrade()
        self._panel._apply_filter()

    def _do_infusion(self) -> None:
        self._select_tree_rows(self._selected)
        self._panel.set_infusion_var.set(self._infusion_var.get())
        self._panel._on_set_infusion()
        self._panel._apply_filter()

    def _do_move(self, to_box: bool) -> None:
        self._select_tree_rows(self._selected)
        self._panel._on_move(to_box)
        self._panel._apply_filter()

    def _do_remove(self) -> None:
        self._select_tree_rows(self._selected)
        self._panel._on_remove()
        self._panel._apply_filter()
