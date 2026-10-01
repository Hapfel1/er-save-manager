"""
Visual inventory editor for DSR.

Icon grid of the loaded character's items. Click selects an item, Ctrl
click adds or removes one and Shift click selects a range. The actions match
the inventory tab (quantity, upgrade, infusion, removal) and go through its
batch operations, so limits, the equipped-item guard and the backup/save
step are shared.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.games.DS3.icon_browser import (
    SELECTED_TEXT,
    IconGrid,
    open_popup,
    search_row,
)
from er_save_manager.games.DS3.tabs.inventory import enable
from er_save_manager.games.DSR import catalog
from er_save_manager.games.DSR.icon_browser import item_button
from er_save_manager.ui.messagebox import CTkMessageBox

if TYPE_CHECKING:
    from er_save_manager.games.DSR.inventory_tab import DSRInventoryTab

_HINT = ("gray40", "gray60")


class DSRVisualInventory(ctk.CTkToplevel):
    def __init__(self, parent, tab: DSRInventoryTab) -> None:
        super().__init__(parent)
        self._tab = tab
        open_popup(self, parent, "Inventory")
        self._build_ui()
        self._load_items()
        tab.listeners.append(self._on_saved)
        self.bind("<Destroy>", self._on_destroy, add="+")

    def _on_destroy(self, event) -> None:
        if event.widget is self and self._on_saved in self._tab.listeners:
            self._tab.listeners.remove(self._on_saved)

    def _build_ui(self) -> None:
        search_row(self, lambda q: self._grid.apply_filter(q))
        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(filters, text="Category:").pack(side="left", padx=(0, 6))
        self._cat_var = tk.StringVar(value="All")
        ctk.CTkComboBox(
            filters,
            variable=self._cat_var,
            values=self._tab.category_options(include_seamless=True),
            state="readonly",
            width=150,
            command=lambda _: self._load_items(),
        ).pack(side="left")

        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        self._grid = IconGrid(self, scroll, self._on_select)

        panel = ctk.CTkFrame(self, fg_color=("gray88", "gray18"), corner_radius=8)
        panel.pack(fill="x", padx=6, pady=(0, 8))
        self._sel_lbl = ctk.CTkLabel(
            panel,
            text="Click to select, Ctrl or Shift click for several",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            text_color=("gray50", "gray60"),
        )
        self._sel_lbl.pack(fill="x", padx=10, pady=(8, 4))
        rows = ctk.CTkFrame(panel, fg_color="transparent")
        rows.pack(fill="x", padx=10, pady=(0, 4))
        rows.grid_columnconfigure(2, weight=1)
        self._qty_var = tk.StringVar(value="1")
        self._upgrade_var = tk.StringVar(value="0")
        self._infusion_var = tk.StringVar(value="")

        ctk.CTkLabel(rows, text="Quantity:").grid(row=0, column=0, sticky="w")
        self._qty_entry = ctk.CTkEntry(rows, textvariable=self._qty_var, width=60)
        self._qty_entry.grid(row=0, column=1, sticky="w", padx=6, pady=2)
        self._qty_btn = ctk.CTkButton(
            rows,
            text="Set Quantity",
            width=120,
            command=lambda: self._apply(
                self._qty_var, "Quantity", self._tab.set_quantity
            ),
        )
        self._qty_btn.grid(row=0, column=3, sticky="e", pady=2)
        ctk.CTkLabel(rows, text="Upgrade:").grid(row=1, column=0, sticky="w")
        self._upgrade_entry = ctk.CTkEntry(
            rows, textvariable=self._upgrade_var, width=60
        )
        self._upgrade_entry.grid(row=1, column=1, sticky="w", padx=6, pady=2)
        self._upgrade_btn = ctk.CTkButton(
            rows,
            text="Set Upgrade",
            width=120,
            command=lambda: self._apply(
                self._upgrade_var, "Upgrade", self._tab.set_upgrade
            ),
        )
        self._upgrade_btn.grid(row=1, column=3, sticky="e", pady=2)
        ctk.CTkLabel(rows, text="Infusion:").grid(row=2, column=0, sticky="w")
        self._infusion_combo = ctk.CTkComboBox(
            rows,
            variable=self._infusion_var,
            values=catalog.INFUSIONS,
            width=140,
            state="readonly",
        )
        self._infusion_combo.grid(
            row=2, column=1, columnspan=2, sticky="w", padx=6, pady=2
        )
        self._infusion_btn = ctk.CTkButton(
            rows,
            text="Set Infusion",
            width=120,
            command=lambda: self._tab.set_infusion(
                self._grid.selected, self._infusion_var.get(), self
            ),
        )
        self._infusion_btn.grid(row=2, column=3, sticky="e", pady=2)
        self._info = ctk.CTkLabel(
            panel, text="", font=("Segoe UI", 9), text_color=_HINT
        )
        self._info.pack(fill="x", padx=10)

        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.pack(fill="x", padx=10, pady=(6, 10))
        self._remove_btn = ctk.CTkButton(
            buttons,
            text="Remove",
            command=lambda: self._tab.remove_entries(self._grid.selected, self),
            fg_color=("gray60", "gray35"),
            hover_color=("gray50", "gray25"),
        )
        self._remove_btn.pack(fill="x")
        self._apply_states([])

    def _load_items(self, keep_selection: bool = False) -> None:
        rows = self._tab.inventory_rows(category=self._cat_var.get())

        def make(row):
            slot, name, _cat, qty, item_type, item_id = row
            hit = catalog.lookup(item_type, item_id)
            text = f"{name}\nx{qty}" if qty > 1 else name
            btn = item_button(
                self._grid.scroll, hit[0] if hit else None, text, self._grid.images
            )
            return btn, name.lower(), slot

        self._grid.load(rows, make, keep_selection=keep_selection)

    def _on_saved(self) -> None:
        if self.winfo_exists():
            self._grid.selected = list(self._tab.last_offsets)
            self._load_items(keep_selection=True)

    def _apply_states(self, slots: list) -> None:
        edits = self._tab.applicable_edits(slots)
        for widget, key in (
            (self._qty_entry, "quantity"),
            (self._qty_btn, "quantity"),
            (self._upgrade_entry, "upgrade"),
            (self._upgrade_btn, "upgrade"),
            (self._infusion_combo, "infusion"),
            (self._infusion_btn, "infusion"),
            (self._remove_btn, "remove"),
        ):
            enable(widget, edits[key])

    def _on_select(self, slots: list) -> None:
        self._apply_states(slots)
        if len(slots) != 1:
            self._sel_lbl.configure(
                text=f"{len(slots)} items selected" if slots else "No item selected",
                text_color=SELECTED_TEXT if slots else ("gray50", "gray60"),
            )
            self._info.configure(
                text="Each item is capped at its own limits" if slots else ""
            )
            return
        row = self._tab.row_for(slots[0])
        opts = self._tab.edit_options(slots[0])
        if not row or not opts:
            return
        self._sel_lbl.configure(text=f"Selected: {row[1]}", text_color=SELECTED_TEXT)
        self._qty_var.set(str(row[3]))
        self._upgrade_var.set(str(opts["level"]))
        if opts["variants"]:
            self._infusion_combo.configure(
                values=[v["infusion"] for v in opts["variants"]]
            )
            self._infusion_var.set(opts["item"]["infusion"])
        lim = opts["limits"]
        info = []
        if opts["quantity"]:
            info.append(f"Max stack: {lim.max_quantity}")
        if lim.max_upgrade:
            info.append(f"Max upgrade: +{lim.max_upgrade}")
        self._info.configure(text="  ".join(info))

    def _apply(self, var: tk.StringVar, what: str, action) -> None:
        try:
            value = int(var.get())
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Value", f"{what} must be a whole number.", parent=self
            )
            return
        action(self._grid.selected, value, self)
