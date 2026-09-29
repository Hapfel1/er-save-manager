"""
Visual add-item popup for DS2.

Shows the same items as the panel's Add Item list as an icon grid. Selecting
an item and clicking Add Item drives the panel's own controls and _on_add,
so quantity/upgrade/infusion capping and the unsafe-item check are shared
with the text form.
"""

from __future__ import annotations

import tkinter as tk
from collections import deque
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.games.DS2.item_database import CATEGORIES, _hex_id_to_int
from er_save_manager.games.DS2.regulation import INFUSION_NAMES
from er_save_manager.ui.utils import center_window, patch_combo_scroll

if TYPE_CHECKING:
    from er_save_manager.games.DS2.inventory_tab import DS2InventoryPanel

_ICON_SIZE = 64
_CELL_W = 116
_CELL_H = 106
_CELL_PAD = 4
_SCROLLBAR_W = 24
_DEFAULT_COLS = 4
# Icons are decoded and turned into Tk PhotoImages on first use, and a big
# category (Armor has 430+ entries) doing that in one pass visibly freezes
# the popup. Building a few buttons per frame keeps it responsive.
_BATCH = 12
_DELAY_MS = 8


def _center_over(window, parent, w=None, h=None) -> None:
    center_window(window, w, h, parent=parent, align_top=True)


class IconBrowser(ctk.CTkToplevel):
    """Visual add-item popup. Click an icon, set quantity/upgrade/infusion,
    click Add Item."""

    def __init__(self, parent, panel: DS2InventoryPanel, initial_category: str = ""):
        super().__init__(parent)
        self._panel = panel
        self._cols = _DEFAULT_COLS
        self._buttons: list[tuple[ctk.CTkButton, str]] = []
        self._ctk_images: list = []
        self._resize_job: str | None = None
        self._current_cat = initial_category or panel._selected_add_category()
        self._selected_name: str | None = None
        self._pending_names: deque[str] = deque()
        self._batch_job: str | None = None
        self._grid_count = 0  # buttons already placed, when no filter is active

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
        self._scroll.bind("<Configure>", self._on_scroll_resize)
        self.after(120, self._reflow)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(top, text="Search:", width=52).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
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
                values=self._panel._visible_add_labels(),
                state="readonly",
                command=self._on_category_change,
            )
        ).pack(side="left", fill="x", expand=True)

        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True, padx=6, pady=(0, 4))

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
        self._infusion_combo = ctk.CTkComboBox(
            opts,
            variable=self._infusion_var,
            values=[INFUSION_NAMES[0]],
            width=120,
            state="disabled",
        )
        self._infusion_combo.grid(
            row=1, column=1, columnspan=3, sticky="w", pady=(6, 0)
        )

        self._add_btn = ctk.CTkButton(
            panel,
            text="Add Item",
            height=34,
            font=("Segoe UI", 11, "bold"),
            command=self._do_add,
            state="disabled",
        )
        self._add_btn.pack(fill="x", padx=10, pady=(6, 10))

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def _load_category(self, category: str) -> None:
        if self._batch_job is not None:
            self.after_cancel(self._batch_job)
            self._batch_job = None
        for btn, _ in self._buttons:
            btn.destroy()
        self._buttons.clear()
        self._ctk_images.clear()
        self._selected_name = None
        self._update_form()

        self._grid_count = 0
        self._pending_names = deque(sorted(CATEGORIES.get(category, {}).keys()))
        self._build_next_batch(category)

    def _build_next_batch(self, category: str) -> None:
        """Create up to _BATCH buttons, then reschedule for the rest so the
        popup stays responsive while a large category loads."""
        if not self.winfo_exists():
            return
        from er_save_manager.games.DS2.icon_manager import fit_size, get_icon

        for _ in range(_BATCH):
            if not self._pending_names:
                break
            name = self._pending_names.popleft()
            item_id = _hex_id_to_int(CATEGORIES[category][name])
            img = get_icon(item_id, category) if item_id is not None else None
            ctk_img = None
            if img:
                ctk_img = ctk.CTkImage(
                    light_image=img, dark_image=img, size=fit_size(img, _ICON_SIZE)
                )
                self._ctk_images.append(ctk_img)
            btn = ctk.CTkButton(
                self._scroll,
                image=ctk_img,
                text=name,
                compound="top",
                width=_CELL_W,
                height=_CELL_H,
                font=("Segoe UI", 11),
                fg_color=("gray82", "gray18"),
                hover_color=("gray70", "gray28"),
                text_color=("gray10", "gray90"),
                command=lambda n=name: self._on_item_click(n),
                anchor="center",
            )
            if getattr(btn, "_text_label", None) is not None:
                btn._text_label.configure(wraplength=_CELL_W - 8, justify="center")
            self._buttons.append((btn, name))
            if not self._search_var.get().strip():
                # Without a filter, grid straight to the next slot. Re-laying
                # out every button each batch makes loading quadratic in the
                # button count, which is slow on large categories like Armor.
                row, col = divmod(self._grid_count, self._cols)
                btn.grid(
                    row=row, column=col, padx=_CELL_PAD, pady=_CELL_PAD, sticky="nsew"
                )
                self._grid_count += 1

        if not self._pending_names or self._search_var.get().strip():
            self._apply_filter()
        else:
            self._scroll.update_idletasks()
            canvas = self._scroll._parent_canvas
            canvas.configure(scrollregion=canvas.bbox("all"))

        if self._pending_names:
            self._batch_job = self.after(
                _DELAY_MS, lambda: self._build_next_batch(category)
            )
        else:
            self._batch_job = None

    def _on_category_change(self, label: str) -> None:
        for key, value in self._category_labels.items():
            if value == label:
                self._current_cat = key
                break
        self.title(f"Add Item - {label}")
        self._load_category(self._current_cat)

    # ------------------------------------------------------------------
    # Layout / filter
    # ------------------------------------------------------------------

    def _apply_filter(self) -> None:
        q = self._search_var.get().lower().strip()
        visible = [btn for btn, name in self._buttons if not q or q in name.lower()]
        for btn, _ in self._buttons:
            btn.grid_forget()
        for idx, btn in enumerate(visible):
            row, col = divmod(idx, self._cols)
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
            self._apply_filter()

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_item_click(self, name: str) -> None:
        self._selected_name = name
        self._sel_lbl.configure(
            text=f"Selected: {name}", text_color=("#7c4dac", "#c084fc")
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

        category = self._current_cat
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

        self._add_btn.configure(state="normal" if self._selected_name else "disabled")

    # ------------------------------------------------------------------
    # Add
    # ------------------------------------------------------------------

    def _do_add(self) -> None:
        if self._selected_name is None:
            return
        panel = self._panel

        label = self._category_labels[self._current_cat]
        panel.add_category_var.set(label)
        panel._search_items()

        try:
            idx = panel._search_results.index(self._selected_name)
        except ValueError:
            panel.show_toast("Item not found in database", duration=2000)
            return
        children = panel._results_tree.get_children()
        panel._results_tree.selection_set(children[idx])

        panel.add_qty_var.set(self._qty_var.get())
        panel.add_upgrade_var.set(self._upgrade_var.get())
        panel.add_infusion_var.set(self._infusion_var.get())
        panel._update_add_controls()
        panel._on_add()
