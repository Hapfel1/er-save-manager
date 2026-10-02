"""
Visual item picker for DSR: the inventory tab's spawn list as an icon grid.

Click selects an item, Ctrl click adds or removes one, Shift click selects a
range. Spawning goes through the tab, so limits, the Estus rule, the cut
content prompt and the backup/save step are shared.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.games.DS3.icon_browser import (
    CELL_H,
    CELL_W,
    ICON_SIZE,
    SELECTED_TEXT,
    IconGrid,
    follow_spawn_list,
    open_popup,
    search_row,
)
from er_save_manager.games.DS3.tabs.inventory import enable
from er_save_manager.games.DSR import catalog
from er_save_manager.games.DSR.icon_manager import get_icon
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import patch_combo_scroll

if TYPE_CHECKING:
    from er_save_manager.games.DSR.inventory_tab import DSRInventoryTab

_CELL_COLOR = ("gray82", "gray18")


def item_button(parent, item: dict | None, text: str, images: list):
    """Icon grid cell for an item; keeps its CTkImage alive in images."""
    img = get_icon(item["icon_id"]) if item else None
    ctk_img = None
    if img is not None:
        ctk_img = ctk.CTkImage(
            light_image=img, dark_image=img, size=(ICON_SIZE, ICON_SIZE)
        )
        images.append(ctk_img)
    btn = ctk.CTkButton(
        parent,
        image=ctk_img,
        text=text,
        compound="top",
        width=CELL_W,
        height=CELL_H,
        font=("Segoe UI", 11),
        fg_color=_CELL_COLOR,
        hover_color=("gray70", "gray28"),
        text_color=("gray10", "gray90"),
        anchor="center",
    )
    if getattr(btn, "_text_label", None) is not None:
        btn._text_label.configure(wraplength=CELL_W - 8, justify="center")
    return btn


class DSRIconBrowser(ctk.CTkToplevel):
    def __init__(self, parent, tab: DSRInventoryTab) -> None:
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
        cats = ctk.CTkFrame(self, fg_color="transparent")
        cats.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(cats, text="Category:").pack(side="left", padx=(0, 6))
        self._cat_var = self._tab.spawn_category_var
        combo = ctk.CTkComboBox(
            cats,
            variable=self._cat_var,
            values=self._tab.category_options(),
            state="readonly",
            width=150,
            command=self._on_category,
        )
        combo.pack(side="left")
        patch_combo_scroll(combo)

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
        self._infusion_var = tk.StringVar(value="")
        self._infusion_combo = ctk.CTkComboBox(
            opts,
            variable=self._infusion_var,
            values=[],
            width=140,
            state="disabled",
            command=self._on_infusion,
        )
        self._infusion_combo.grid(
            row=1, column=1, columnspan=3, sticky="w", pady=(6, 0)
        )
        self._info = ctk.CTkLabel(
            opts, text="", font=("Segoe UI", 9), text_color=("gray40", "gray60")
        )
        self._info.grid(row=2, column=0, columnspan=4, sticky="w", pady=(4, 0))

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
            buttons, text="Spawn All Shown", height=34, command=self._do_spawn_all
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def _load_items(self) -> None:
        self._rows = dict(enumerate(self._tab.visible_spawn_items()))

        def make(entry):
            index, (label, item, _variants) = entry
            btn = item_button(self._grid.scroll, item, label, self._grid.images)
            return btn, label.lower(), index

        self._grid.load(list(self._rows.items()), make)

    def _on_category(self, label: str) -> None:
        self._tab.set_category(label)

    def _on_select(self, keys: list) -> None:
        self._spawn_btn.configure(state="normal" if keys else "disabled")
        if len(keys) != 1:
            self._selected_item = None
            self._variants = []
            self._infusion_combo.configure(values=[], state="disabled")
            self._infusion_var.set("")
            self._sel_lbl.configure(
                text=f"{len(keys)} items selected" if keys else "No item selected",
                text_color=SELECTED_TEXT if keys else ("gray50", "gray60"),
            )
            self._info.configure(
                text="Quantity and upgrade are capped per item" if keys else ""
            )
            enable(self._qty_entry, True)
            enable(self._upgrade_entry, True)
            return
        label, item, variants = self._rows[keys[0]]
        self._variants = variants
        labels = [v["infusion"] for v in variants]
        self._infusion_combo.configure(
            values=labels, state="readonly" if labels else "disabled"
        )
        self._infusion_var.set(item["infusion"] if labels else "")
        self._sel_lbl.configure(text=f"Selected: {label}", text_color=SELECTED_TEXT)
        self._select_item(item)

    def _on_infusion(self, chosen: str) -> None:
        item = next((v for v in self._variants if v["infusion"] == chosen), None)
        if item is not None:
            self._select_item(item)

    def _select_item(self, item: dict) -> None:
        self._selected_item = item
        lim = catalog.limits(item)
        enable(self._qty_entry, lim.max_quantity > 1)
        enable(self._upgrade_entry, lim.max_upgrade > 0)
        info = [f"Max stack: {lim.max_quantity}"]
        if lim.max_upgrade:
            info.append(f"Max upgrade: +{lim.max_upgrade}")
        if item["key_item"]:
            info.append("Key item")
        if not item["obtainable"]:
            info.append("Cut content")
        self._info.configure(text="  ".join(info))

    def _values(self) -> tuple[int, int] | None:
        try:
            return int(self._qty_var.get()), int(self._upgrade_var.get())
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Value", "Enter whole numbers.", parent=self
            )
            return None

    def _do_spawn(self) -> None:
        values = self._values()
        if values is None:
            return
        if len(self._grid.selected) == 1 and self._selected_item is not None:
            items = [self._selected_item]
        else:
            items = [self._rows[k][1] for k in self._grid.selected]
        self._tab.spawn_items(items, *values, parent=self)

    def _do_spawn_all(self) -> None:
        values = self._values()
        if values is None:
            return
        items = [self._rows[k][1] for k in self._grid._visible_keys()]
        self._tab.spawn_items(items, *values, parent=self)
