"""
Visual inventory editor for DS3.

Icon grid of the loaded character's held items, key items and storage box;
infused weapons show their infusion icon in the corner. Click selects an
item, Ctrl click adds or removes one and Shift click selects a range. The
actions match the inventory tab (quantity, upgrade, infusion, moving
between the inventory and the storage box, removal) and go through its
batch operations, so limits, the equipped-item guard and the backup/save
step are shared.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.games.DS3 import catalog
from er_save_manager.games.DS3.icon_browser import (
    SELECTED_TEXT,
    IconGrid,
    item_button,
    open_popup,
    search_row,
)
from er_save_manager.games.DS3.icon_manager import get_infusion_icon
from er_save_manager.games.DS3.tabs.inventory import (
    WHERE_HELD,
    WHERE_KEY,
    WHERE_STORAGE,
    enable,
)
from er_save_manager.ui.messagebox import CTkMessageBox

if TYPE_CHECKING:
    from er_save_manager.games.DS3.tabs.inventory import DS3InventoryTab

_HINT = ("gray40", "gray60")
_INFUSION_ICON = 22


class DS3VisualInventory(ctk.CTkToplevel):
    """Icon grid over the character's inventory with batch actions."""

    def __init__(self, parent, tab: DS3InventoryTab) -> None:
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

    # --- Layout ------------------------------------------------------------ #

    def _build_ui(self) -> None:
        search_row(self, lambda q: self._grid.apply_filter(q))

        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(filters, text="Location:").pack(side="left", padx=(0, 6))
        self._where_var = tk.StringVar(value=WHERE_HELD)
        ctk.CTkComboBox(
            filters,
            variable=self._where_var,
            values=["All", WHERE_HELD, WHERE_KEY, WHERE_STORAGE],
            state="readonly",
            width=110,
            command=lambda _: self._load_items(),
        ).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(filters, text="Category:").pack(side="left", padx=(0, 6))
        self._cat_var = tk.StringVar(value="All")
        ctk.CTkComboBox(
            filters,
            variable=self._cat_var,
            values=self._tab.category_options(),
            state="readonly",
            width=120,
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
            rows, text="Set Quantity", width=120, command=self._set_quantity
        )
        self._qty_btn.grid(row=0, column=3, sticky="e", pady=2)

        ctk.CTkLabel(rows, text="Upgrade:").grid(row=1, column=0, sticky="w")
        self._upgrade_entry = ctk.CTkEntry(
            rows, textvariable=self._upgrade_var, width=60
        )
        self._upgrade_entry.grid(row=1, column=1, sticky="w", padx=6, pady=2)
        self._upgrade_btn = ctk.CTkButton(
            rows, text="Set Upgrade", width=120, command=self._set_upgrade
        )
        self._upgrade_btn.grid(row=1, column=3, sticky="e", pady=2)

        ctk.CTkLabel(rows, text="Infusion:").grid(row=2, column=0, sticky="w")
        inf_cell = ctk.CTkFrame(rows, fg_color="transparent")
        inf_cell.grid(row=2, column=1, columnspan=2, sticky="w", padx=6, pady=2)
        self._infusion_icon = ctk.CTkLabel(inf_cell, text="", width=_INFUSION_ICON)
        self._infusion_icon.pack(side="left", padx=(0, 4))
        labels = self._tab.infusion_labels()
        self._infusion_var.set(labels[0] if labels else "")
        self._infusion_combo = ctk.CTkComboBox(
            inf_cell,
            variable=self._infusion_var,
            values=labels,
            width=140,
            state="readonly",
            command=self._show_infusion_icon,
        )
        self._infusion_combo.pack(side="left")
        self._show_infusion_icon(self._infusion_var.get())
        self._infusion_btn = ctk.CTkButton(
            rows, text="Set Infusion", width=120, command=self._set_infusion
        )
        self._infusion_btn.grid(row=2, column=3, sticky="e", pady=2)

        self._info = ctk.CTkLabel(
            panel, text="", font=("Segoe UI", 9), text_color=_HINT
        )
        self._info.pack(fill="x", padx=10)

        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.pack(fill="x", padx=10, pady=(6, 10))
        buttons.grid_columnconfigure((0, 1, 2), weight=1)
        self._to_storage_btn = ctk.CTkButton(
            buttons,
            text="To Storage",
            command=lambda: self._tab.move_entries(self._grid.selected, True, self),
        )
        self._to_storage_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self._to_inventory_btn = ctk.CTkButton(
            buttons,
            text="To Inventory",
            command=lambda: self._tab.move_entries(self._grid.selected, False, self),
        )
        self._to_inventory_btn.grid(row=0, column=1, sticky="ew", padx=4)
        self._remove_btn = ctk.CTkButton(
            buttons,
            text="Remove",
            command=lambda: self._tab.remove_entries(self._grid.selected, self),
            fg_color=("gray60", "gray35"),
            hover_color=("gray50", "gray25"),
        )
        self._remove_btn.grid(row=0, column=2, sticky="ew", padx=(4, 0))
        self._apply_states([])

    # --- Items ------------------------------------------------------------- #

    def _load_items(self, keep_selection: bool = False) -> None:
        source = self._tab.source
        rows = self._tab.inventory_rows(
            category=self._cat_var.get(), where=self._where_var.get()
        )

        def make(row):
            offset, name, _cat, qty, where, item_id = row
            text = f"{name}\nx{qty}" if qty > 1 else name
            if self._where_var.get() == "All" and where != WHERE_HELD:
                text += f"\n({where})"
            btn = item_button(
                self._grid.scroll,
                catalog.lookup(item_id, source),
                source,
                text,
                self._grid.images,
            )
            return btn, name.lower(), offset

        self._grid.load(rows, make, keep_selection=keep_selection)

    def _on_saved(self) -> None:
        if self.winfo_exists():
            # Moves give items new places; the tab reports where they went.
            self._grid.selected = list(self._tab.last_offsets)
            self._load_items(keep_selection=True)

    # --- Selection and actions --------------------------------------------- #

    def _apply_states(self, offsets: list) -> None:
        edits = self._tab.applicable_edits(offsets)
        for widget, key in (
            (self._qty_entry, "quantity"),
            (self._qty_btn, "quantity"),
            (self._upgrade_entry, "upgrade"),
            (self._upgrade_btn, "upgrade"),
            (self._infusion_combo, "infusion"),
            (self._infusion_btn, "infusion"),
            (self._to_storage_btn, "to_storage"),
            (self._to_inventory_btn, "to_inventory"),
            (self._remove_btn, "remove"),
        ):
            enable(widget, edits[key])

    def _on_select(self, offsets: list) -> None:
        self._apply_states(offsets)
        if len(offsets) != 1:
            self._sel_lbl.configure(
                text=f"{len(offsets)} items selected"
                if offsets
                else "No item selected",
                text_color=SELECTED_TEXT if offsets else ("gray50", "gray60"),
            )
            self._info.configure(
                text="Each item is capped at its own limits" if offsets else ""
            )
            return
        row = self._tab.row_for(offsets[0])
        opts = self._tab.edit_options(offsets[0])
        if not row or not opts:
            return
        self._sel_lbl.configure(
            text=f"Selected: {row[1]} ({row[4]})", text_color=SELECTED_TEXT
        )
        self._qty_var.set(str(row[3]))
        self._upgrade_var.set(str(opts["level"]))
        if opts["item"] is not None and "Infusion" in opts["item"]:
            self._infusion_var.set(opts["item"]["Infusion"])
            self._show_infusion_icon(self._infusion_var.get())
        lim = opts["limits"]
        info = []
        if lim is not None and lim.max_quantity > 1:
            info.append(f"Max stack: {lim.max_quantity}")
        if lim is not None and lim.max_upgrade:
            info.append(f"Max upgrade: +{lim.max_upgrade}")
        if row[4] == WHERE_KEY:
            info.append("Key items stay in the inventory")
        self._info.configure(text="  ".join(info))

    def _show_infusion_icon(self, label: str) -> None:
        labels = self._tab.infusion_labels()
        img = (
            get_infusion_icon(labels.index(label), self._tab.source)
            if label in labels
            else None
        )
        size = (_INFUSION_ICON, _INFUSION_ICON)
        self._infusion_icon.configure(
            image=ctk.CTkImage(light_image=img, dark_image=img, size=size)
            if img
            else None
        )

    def _read(self, var: tk.StringVar, what: str) -> int | None:
        try:
            return int(var.get())
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Value", f"{what} must be a whole number.", parent=self
            )
            return None

    def _set_quantity(self) -> None:
        qty = self._read(self._qty_var, "Quantity")
        if qty is not None:
            self._tab.set_quantity(self._grid.selected, qty, self)

    def _set_upgrade(self) -> None:
        level = self._read(self._upgrade_var, "Upgrade")
        if level is not None:
            self._tab.set_upgrade(self._grid.selected, level, self)

    def _set_infusion(self) -> None:
        self._tab.set_infusion(self._grid.selected, self._infusion_var.get(), self)
