"""
Visual add-item popup for DS2.

Shows the same items as the panel's Add Item list as an icon grid. Selecting
items and clicking Add Item drives the panel's own controls and _on_add,
so quantity/upgrade/infusion capping and the unsafe-item check are shared
with the text form. Click selects one icon, Ctrl click adds or removes one
and Shift click selects a range; several items go through the panel's
batch add.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.games.DS2.icon_manager import (
    add_infusion_menu_icons,
    bind_infusion_icon,
)
from er_save_manager.games.DS2.item_database import CATEGORIES, _hex_id_to_int
from er_save_manager.games.DS2.regulation import INFUSION_NAMES
from er_save_manager.games.DS2.save import KEY_LIST_CATEGORIES
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
    from er_save_manager.games.DS2.inventory_tab import DS2InventoryPanel

_ICON_SIZE = 64
_CELL_W = 116
_CELL_H = 124
_CELL_PAD = 4
_SCROLLBAR_W = 24
_DEFAULT_COLS = 4
# Category key for the "All" entry of the category list
_ALL = ""


def _center_over(window, parent, w=None, h=None) -> None:
    center_window(window, w, h, parent=parent, align_top=True)


class IconBrowser(ctk.CTkToplevel):
    """Visual add-item popup. Click an icon, set quantity/upgrade/infusion,
    click Add Item."""

    def __init__(self, parent, panel: DS2InventoryPanel, initial_category: str = ""):
        super().__init__(parent)
        self._panel = panel
        self._current_cat = initial_category or panel._selected_add_category()
        # Selected (category, name) keys in grid order; the form follows the first.
        self._selected_keys: list[tuple[str, str]] = []
        self._selected_cat: str | None = None
        self._selected_name: str | None = None

        w = _DEFAULT_COLS * (_CELL_W + _CELL_PAD * 2) + 12 + _SCROLLBAR_W + 30
        self.title("Add Item")
        self.geometry(f"{w}x720")
        self.minsize(w, 480)
        self.transient(parent)
        self.attributes("-alpha", 0)
        self.update_idletasks()
        _center_over(self, parent, w, 720)
        self.attributes("-alpha", 1)
        self.lift()
        self.focus_force()

        self._build_ui()
        self._load_category(self._current_cat)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(top, text="Search:", width=52).pack(side="left")
        self._search_var = tk.StringVar()
        debounced_trace(self, self._search_var, self._apply_filter)
        ctk.CTkEntry(top, textvariable=self._search_var).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ctk.CTkButton(
            top,
            text="Close",
            width=64,
            height=28,
            fg_color=("gray70", "gray35"),
            command=self.destroy,
        ).pack(side="right")

        cat_row = ctk.CTkFrame(self, fg_color="transparent")
        cat_row.pack(fill="x", padx=10, pady=(0, 6))
        from er_save_manager.games.DS2.inventory_tab import CATEGORY_LABELS

        ctk.CTkLabel(cat_row, text="Category:", width=68).pack(side="left")
        self._category_labels = CATEGORY_LABELS
        self._cat_var = tk.StringVar(value=CATEGORY_LABELS[self._current_cat])
        patch_combo_scroll(
            ctk.CTkComboBox(
                cat_row,
                variable=self._cat_var,
                values=["All", *self._panel._visible_add_labels()],
                state="readonly",
                command=self._on_category_change,
            )
        ).pack(side="left", fill="x", expand=True)

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

        ctk.CTkLabel(opts, text="Quantity:").grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        self._qty_var = tk.StringVar(value="1")
        self._qty_entry = ctk.CTkEntry(
            opts, textvariable=self._qty_var, width=60, state="disabled"
        )
        self._qty_entry.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(opts, text="Upgrade:").grid(
            row=0, column=2, sticky="w", padx=(14, 6)
        )
        self._upgrade_var = tk.StringVar(value="0")
        self._upgrade_entry = ctk.CTkEntry(
            opts, textvariable=self._upgrade_var, width=50, state="disabled"
        )
        self._upgrade_entry.grid(row=0, column=3, sticky="w")

        ctk.CTkLabel(opts, text="Infusion:").grid(
            row=1, column=0, sticky="w", padx=(0, 6), pady=(6, 0)
        )
        self._infusion_var = tk.StringVar(value=INFUSION_NAMES[0])
        infusion_cell = ctk.CTkFrame(opts, fg_color="transparent")
        infusion_cell.grid(row=1, column=1, columnspan=3, sticky="w", pady=(6, 0))
        infusion_icon = ctk.CTkLabel(infusion_cell, text="", width=24)
        infusion_icon.pack(side="left", padx=(0, 4))
        bind_infusion_icon(infusion_icon, self._infusion_var)
        self._infusion_combo = ctk.CTkComboBox(
            infusion_cell,
            variable=self._infusion_var,
            values=[INFUSION_NAMES[0]],
            width=120,
            state="disabled",
        )
        self._infusion_combo.pack(side="left")
        add_infusion_menu_icons(self._infusion_combo)

        from er_save_manager.games.DS2.inventory_tab import ADD_LOCATIONS

        ctk.CTkLabel(opts, text="Location:").grid(
            row=2, column=0, sticky="w", padx=(0, 6), pady=(6, 0)
        )
        # Shares the panel's variable, since adding goes through the panel.
        self._location_combo = ctk.CTkComboBox(
            opts,
            variable=self._panel.add_location_var,
            values=list(ADD_LOCATIONS),
            width=120,
            state="readonly",
        )
        self._location_combo.grid(
            row=2, column=1, columnspan=3, sticky="w", pady=(6, 0)
        )

        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.pack(fill="x", padx=10, pady=(6, 10))
        buttons.grid_columnconfigure((0, 1), weight=1)
        self._add_btn = ctk.CTkButton(
            buttons,
            text="Add Selected",
            height=34,
            font=("Segoe UI", 11, "bold"),
            command=self._do_add,
            state="disabled",
        )
        self._add_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self._add_all_btn = ctk.CTkButton(
            buttons,
            text="Add All Shown",
            height=34,
            command=self._do_add_all,
        )
        self._add_all_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def _load_category(self, category: str) -> None:
        from er_save_manager.games.DS2.icon_manager import get_icon

        if category == _ALL:
            shown = self._panel._visible_add_labels()
            cats = [k for k, label in self._category_labels.items() if label in shown]
        else:
            cats = [category]

        def icon(cat: str, name: str):
            item_id = _hex_id_to_int(CATEGORIES[cat][name])
            return get_icon(item_id, cat) if item_id is not None else None

        self._grid.set_entries(
            [
                GridEntry(
                    (cat, name), name, name.lower(), lambda c=cat, n=name: icon(c, n)
                )
                for cat in cats
                for name in sorted(CATEGORIES.get(cat, {}).keys())
            ]
        )
        self._apply_filter()
        self._on_select([])

    def _on_category_change(self, label: str) -> None:
        self._current_cat = next(
            (k for k, v in self._category_labels.items() if v == label), _ALL
        )
        self.title(f"Add Item - {label}")
        self._load_category(self._current_cat)

    def _apply_filter(self) -> None:
        self._grid.apply_filter(self._search_var.get())

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _visible_names(self) -> list[str]:
        return [name for _, name in self._grid.visible_keys()]

    def _on_select(self, keys: list) -> None:
        self._selected_keys = list(keys)
        self._selected_cat, self._selected_name = keys[0] if keys else (None, None)
        count = len(keys)
        self._sel_lbl.configure(
            text=f"Selected: {self._selected_name}"
            if count == 1
            else f"{count} items selected"
            if count
            else "No item selected",
            text_color=palette.PURPLE_TEXT if count else ("gray50", "gray60"),
        )
        self._update_form()

    def _update_form(self) -> None:
        """Enable/disable quantity, upgrade and infusion using the same
        Character caps the panel's own text form uses."""
        from er_save_manager.games.DS2.inventory_tab import STACKABLE_CATEGORIES
        from er_save_manager.games.DS2.save import (
            MULTI_COPY_CATEGORIES,
            UPGRADABLE_CATEGORIES,
        )

        category = self._selected_cat or self._current_cat
        character = self._panel._current_character()
        item_id = None
        if self._selected_name is not None:
            hex_id = CATEGORIES.get(category, {}).get(self._selected_name)
            item_id = _hex_id_to_int(hex_id) if hex_id else None

        quantity = category in STACKABLE_CATEGORIES or category in MULTI_COPY_CATEGORIES
        upgrade = category in UPGRADABLE_CATEGORIES
        infusion = category == "weapons"
        allowed: tuple[int, ...] = tuple(range(len(INFUSION_NAMES)))

        if item_id is not None and character is not None:
            if category in STACKABLE_CATEGORIES:
                quantity = character.max_stack(item_id) > 1
            if upgrade:
                upgrade = character.max_upgrade(item_id, category) > 0
            if infusion:
                allowed = character.allowed_infusions(item_id)
                infusion = len(allowed) > 1

        self._qty_entry.configure(state="normal" if quantity else "disabled")
        if not quantity:
            self._qty_var.set("1")
        self._upgrade_entry.configure(state="normal" if upgrade else "disabled")
        if not upgrade:
            self._upgrade_var.set("0")
        names = [INFUSION_NAMES[n] for n in allowed] or [INFUSION_NAMES[0]]
        self._infusion_combo.configure(
            values=names, state="readonly" if infusion else "disabled"
        )
        if self._infusion_var.get() not in names:
            self._infusion_var.set(INFUSION_NAMES[0])
        from er_save_manager.games.DS2.inventory_tab import ADD_LOCATIONS

        key_list = category in KEY_LIST_CATEGORIES
        self._location_combo.configure(state="disabled" if key_list else "readonly")
        if key_list:
            self._panel.add_location_var.set(ADD_LOCATIONS[0])

        self._add_btn.configure(state="normal" if self._selected_name else "disabled")

    # ------------------------------------------------------------------
    # Add
    # ------------------------------------------------------------------

    def _sync_panel(self, category: str) -> None:
        """Point the panel's add form at category and this picker's values,
        since adding goes through the panel."""
        panel = self._panel
        panel.add_category_var.set(self._category_labels[category])
        panel._search_items()
        panel.add_qty_var.set(self._qty_var.get())
        panel.add_upgrade_var.set(self._upgrade_var.get())
        panel.add_infusion_var.set(self._infusion_var.get())

    def _do_add_all(self) -> None:
        """Add every item the grid shows (category and search filter) in one
        write, with the quantity, upgrade and infusion fields."""
        keys = self._grid.visible_keys()
        if not keys:
            self._panel.show_toast("No items shown", duration=2000)
            return
        save = self._panel._writable_save()
        if save is None:
            return
        if self._current_cat != _ALL:
            self._sync_panel(self._current_cat)
            self._panel._add_many(save, [name for _, name in keys])
            return
        if CTkMessageBox._create_dialog(
            self,
            "Add All Shown",
            f"Add all {len(keys)} shown items from every category?\n\n"
            "This fills most of the inventory. A backup is made first; restore "
            "it in the Backup Manager to undo.",
            icon_type="warning",
            buttons=[("Add All", True), ("Cancel", False)],
        ):
            self._add_groups(save, keys)

    def _add_groups(self, save, keys: list[tuple[str, str]]) -> None:
        """Add (category, name) keys of several categories with one write;
        the panel adds from one category at a time."""
        groups: dict[str, list[str]] = {}
        for cat, name in keys:
            groups.setdefault(cat, []).append(name)
        results: list = []
        for cat, names in groups.items():
            self._sync_panel(cat)
            self._panel._add_many(save, names, batch=results)
        self._panel._report_bulk_add(save, results)

    def _do_add(self) -> None:
        if self._selected_name is None:
            return
        panel = self._panel
        groups: dict[str, list[str]] = {}
        for cat, name in self._selected_keys:
            groups.setdefault(cat, []).append(name)
        if len(groups) > 1:
            save = panel._writable_save()
            if save is None:
                return
            n = len(self._selected_keys)
            if CTkMessageBox.askyesno(
                "Add Items",
                f"Add the {n} selected items from {len(groups)} categories?",
                parent=self,
            ):
                self._add_groups(save, self._selected_keys)
            return

        [(category, names)] = groups.items()
        panel.add_category_var.set(self._category_labels[category])
        panel._search_items()

        children = panel._results_tree.get_children()
        rows = [
            children[panel._search_results.index(name)]
            for name in names
            if name in panel._search_results
        ]
        if not rows:
            panel.show_toast("Item not found in database", duration=2000)
            return
        panel._results_tree.selection_set(rows)

        panel.add_qty_var.set(self._qty_var.get())
        panel.add_upgrade_var.set(self._upgrade_var.get())
        panel.add_infusion_var.set(self._infusion_var.get())
        panel._update_add_controls()
        panel._on_add()
