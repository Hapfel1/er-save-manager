"""
Visual current-inventory popup for DS2.

The inventory is a fixed slot table that is almost all empty, so a plain
button grid is fast enough.

Selecting an icon selects the matching row in the panel's own inventory tree
and drives its existing Remove/Set Quantity/Set Upgrade/Set Infusion
controls, so the write logic and its caps stay in one place.
"""

from __future__ import annotations

import tkinter as tk
from collections import deque
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.games.DS2.regulation import INFUSION_NAMES
from er_save_manager.ui.utils import center_window, patch_combo_scroll

if TYPE_CHECKING:
    from er_save_manager.games.DS2.inventory_tab import DS2InventoryPanel

_ICON_SIZE = 56
_CELL_W = 110
_CELL_H = 100
_CELL_PAD = 4
_SCROLLBAR_W = 24
_DEFAULT_COLS = 5
# Builds a few icons per frame so a large inventory does not freeze the popup,
# see icon_browser.py.
_BATCH = 12
_DELAY_MS = 8


def _center_over(window, parent, w=None, h=None) -> None:
    center_window(window, w, h, parent=parent, align_top=True)


class VisualInventoryBrowser(ctk.CTkToplevel):
    """Icon-grid view of the current character's inventory."""

    def __init__(self, parent, panel: DS2InventoryPanel):
        super().__init__(parent)
        self._panel = panel
        self._cols = _DEFAULT_COLS
        self._buttons: list[tuple[ctk.CTkButton, int]] = []  # (button, tree index)
        self._ctk_images: list = []
        self._resize_job: str | None = None
        self._selected_index: int | None = None
        self._pending_indices: deque[int] = deque()
        self._batch_job: str | None = None
        self._grid_count = 0  # buttons already placed this load

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
        self._rebuild()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(top, text="Category:", width=68).pack(side="left")
        self._cat_var = tk.StringVar(value=self._panel.filter_category_var.get())
        patch_combo_scroll(
            ctk.CTkComboBox(
                top,
                variable=self._cat_var,
                values=["All"] + list(self._category_labels().values()),
                state="readonly",
                width=150,
                command=lambda _v: self._rebuild(),
            )
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(top, text="Filter:").pack(side="left")
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(top, textvariable=self._filter_var).pack(
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

        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        self._scroll.bind("<Configure>", self._on_scroll_resize)

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
        self._infusion_combo = ctk.CTkComboBox(
            opts,
            variable=self._infusion_var,
            values=[INFUSION_NAMES[0]],
            width=110,
            state="disabled",
        )
        self._infusion_combo.grid(
            row=1, column=1, columnspan=2, sticky="w", pady=(6, 0)
        )
        self._infusion_btn = ctk.CTkButton(
            opts, text="Set", width=44, command=self._do_infusion, state="disabled"
        )
        self._infusion_btn.grid(row=1, column=3, sticky="w", padx=(4, 0), pady=(6, 0))

        self._remove_btn = ctk.CTkButton(
            panel,
            text="Remove Selected",
            height=32,
            command=self._do_remove,
            state="disabled",
            fg_color=("#a03030", "#7c2020"),
            hover_color=("#c04040", "#9c3030"),
        )
        self._remove_btn.pack(fill="x", padx=10, pady=(6, 10))

    def _category_labels(self) -> dict:
        from er_save_manager.games.DS2.inventory_tab import CATEGORY_LABELS

        return CATEGORY_LABELS

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _rebuild(self) -> None:
        """Sync the panel's own filter to this popup's, refresh its tree, then
        rebuild the icon grid from panel._visible_items so both stay in the
        same order and indices line up for selection."""
        self._panel.filter_category_var.set(self._cat_var.get())
        self._panel.filter_search_var.set(self._filter_var.get())
        self._panel._apply_filter()
        self._load_icons()

    def _apply_filter(self) -> None:
        self._rebuild()

    def _load_icons(self) -> None:
        if self._batch_job is not None:
            self.after_cancel(self._batch_job)
            self._batch_job = None
        for btn, _ in self._buttons:
            btn.destroy()
        self._buttons.clear()
        self._ctk_images.clear()
        self._selected_index = None
        self._update_form()

        self._grid_count = 0
        self._pending_indices = deque(range(len(self._panel._visible_items)))
        self._build_next_batch()

    def _build_next_batch(self) -> None:
        """Create up to _BATCH icon buttons, then reschedule for the rest so
        a large inventory stays responsive while it loads."""
        if not self.winfo_exists():
            return
        from er_save_manager.games.DS2.icon_manager import fit_size, get_icon
        from er_save_manager.games.DS2.inventory_tab import STACKABLE_CATEGORIES
        from er_save_manager.games.DS2.save import UPGRADABLE_CATEGORIES

        for _ in range(_BATCH):
            if not self._pending_indices:
                break
            idx = self._pending_indices.popleft()
            item, name, category = self._panel._visible_items[idx]
            img = get_icon(item.item_id, category)
            ctk_img = None
            if img:
                ctk_img = ctk.CTkImage(
                    light_image=img, dark_image=img, size=fit_size(img, _ICON_SIZE)
                )
                self._ctk_images.append(ctk_img)
            label = name
            if category in STACKABLE_CATEGORIES and item.quantity > 1:
                label = f"{name} x{item.quantity}"
            elif category in UPGRADABLE_CATEGORIES and item.upgrade:
                label = f"{name} +{item.upgrade}"
            btn = ctk.CTkButton(
                self._scroll,
                image=ctk_img,
                text=label,
                compound="top",
                width=_CELL_W,
                height=_CELL_H,
                font=("Segoe UI", 10),
                fg_color=("gray82", "gray18"),
                hover_color=("gray70", "gray28"),
                text_color=("gray10", "gray90"),
                command=lambda i=idx: self._on_item_click(i),
                anchor="center",
            )
            if getattr(btn, "_text_label", None) is not None:
                btn._text_label.configure(wraplength=_CELL_W - 8, justify="center")
            self._buttons.append((btn, idx))
            # Grid straight to the next slot, see icon_browser.py. A full
            # _layout_grid() still runs on resize and after the last batch.
            row, col = divmod(self._grid_count, self._cols)
            btn.grid(row=row, column=col, padx=_CELL_PAD, pady=_CELL_PAD, sticky="nsew")
            self._grid_count += 1

        if self._pending_indices:
            self._scroll.update_idletasks()
            canvas = self._scroll._parent_canvas
            canvas.configure(scrollregion=canvas.bbox("all"))
            self._batch_job = self.after(_DELAY_MS, self._build_next_batch)
        else:
            self._layout_grid()
            self._batch_job = None

    def _layout_grid(self) -> None:
        for col_idx, (btn, _) in enumerate(self._buttons):
            row, col = divmod(col_idx, self._cols)
            btn.grid(row=row, column=col, padx=_CELL_PAD, pady=_CELL_PAD, sticky="nsew")
        self._scroll.update_idletasks()
        canvas = self._scroll._parent_canvas
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_scroll_resize(self, _event) -> None:
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(60, self._reflow)

    def _reflow(self) -> None:
        available = max(1, self._scroll.winfo_width() - _SCROLLBAR_W)
        new_cols = max(1, available // (_CELL_W + _CELL_PAD * 2))
        if new_cols != self._cols:
            self._cols = new_cols
            self._layout_grid()

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _select_tree_row(self, index: int) -> None:
        tree = self._panel._inventory_tree
        children = tree.get_children()
        if 0 <= index < len(children):
            tree.selection_set(children[index])

    def _on_item_click(self, index: int) -> None:
        self._selected_index = index
        item, name, category = self._panel._visible_items[index]
        self._sel_lbl.configure(
            text=f"Selected: {name}", text_color=("#7c4dac", "#c084fc")
        )
        self._select_tree_row(index)
        self._panel._update_inventory_controls()
        self._update_form()

    def _update_form(self) -> None:
        panel = self._panel
        character = panel._current_character()
        has_selection = self._selected_index is not None
        quantity = upgrade = infusion = False
        allowed: tuple[int, ...] = (0,)

        if has_selection and character is not None:
            item, name, category = panel._visible_items[self._selected_index]
            if panel._quantity_limit(character, item, category):
                quantity = True
                self._qty_var.set(str(item.quantity))
            if panel._upgrade_limit(character, item, category):
                upgrade = True
                self._upgrade_var.set(str(item.upgrade))
            choices = panel._infusion_choices(character, item, category)
            if choices:
                infusion = True
                allowed = choices
                self._infusion_var.set(INFUSION_NAMES[item.infusion])

        self._qty_entry.configure(state="normal" if quantity else "disabled")
        self._qty_btn.configure(state="normal" if quantity else "disabled")
        self._upgrade_entry.configure(state="normal" if upgrade else "disabled")
        self._upgrade_btn.configure(state="normal" if upgrade else "disabled")
        names = [INFUSION_NAMES[n] for n in allowed]
        self._infusion_combo.configure(
            values=names, state="readonly" if infusion else "disabled"
        )
        self._infusion_btn.configure(state="normal" if infusion else "disabled")
        if self._infusion_var.get() not in names:
            self._infusion_var.set(names[0])
        self._remove_btn.configure(state="normal" if has_selection else "disabled")

    # ------------------------------------------------------------------
    # Actions, delegated to the panel's own Set/Remove
    # ------------------------------------------------------------------

    def _do_qty(self) -> None:
        self._panel.set_qty_var.set(self._qty_var.get())
        self._panel._on_set_quantity()
        self._rebuild()

    def _do_upgrade(self) -> None:
        self._panel.set_upgrade_var.set(self._upgrade_var.get())
        self._panel._on_set_upgrade()
        self._rebuild()

    def _do_infusion(self) -> None:
        self._panel.set_infusion_var.set(self._infusion_var.get())
        self._panel._on_set_infusion()
        self._rebuild()

    def _do_remove(self) -> None:
        self._panel._on_remove()
        self._rebuild()
