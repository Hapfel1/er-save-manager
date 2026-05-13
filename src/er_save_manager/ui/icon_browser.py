"""Icon-grid item browser popup."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from er_save_manager.data.item_database import Item

_DEFAULT_COLS = 4
_ICON_SIZE = 64
_CELL_W = 116
_CELL_H = 100
_CELL_PAD = 4
_SCROLLBAR_W = 24  # CTkScrollableFrame scrollbar + inner border buffer


class IconBrowser(ctk.CTkToplevel):
    """
    Modal grid browser. Calls on_select(item) and closes when an item is clicked.
    Columns adjust when the window is resized.
    Optionally shows a category switcher when categories list is provided.
    """

    def __init__(
        self,
        parent,
        items: list[Item],
        on_select: Callable[[Item], None],
        title: str = "Browse Items",
        categories: list[str] | None = None,
        initial_category: str = "",
    ):
        super().__init__(parent)
        self._on_select = on_select
        self._cols = _DEFAULT_COLS
        self._buttons: list[tuple[ctk.CTkButton, Item]] = []
        self._ctk_images: list = []
        self._resize_job = None
        self._categories = categories or []
        self._current_cat = initial_category

        self.title(title)
        # +12 pack padx, +_SCROLLBAR_W for scrollbar/borders, +30 buffer
        w = _DEFAULT_COLS * (_CELL_W + _CELL_PAD * 2) + 12 + _SCROLLBAR_W + 30
        self.geometry(f"{w}x620")
        self.minsize(w, 300)
        self.resizable(True, True)
        self.transient(parent)
        self.attributes("-alpha", 0)
        self.update_idletasks()
        self.attributes("-alpha", 1)
        self.grab_set()

        self._build_ui()
        self._load_items(items)
        self._scroll.bind("<Configure>", self._on_scroll_resize)
        # Initial reflow after window actually renders to get real winfo_width()
        self.after(120, self._reflow)

    # ---- UI construction -----------------------------------------------------

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill=ctk.X, padx=10, pady=(10, 4))

        ctk.CTkLabel(top, text="Search:", width=52).pack(side=ctk.LEFT)
        self._search_var = ctk.StringVar()
        self._search_var.trace_add(
            "write", lambda *_: self._apply_filter(self._search_var.get())
        )
        ctk.CTkEntry(
            top, textvariable=self._search_var, placeholder_text="Filter..."
        ).pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 8))

        ctk.CTkButton(
            top,
            text="Cancel",
            width=72,
            height=28,
            fg_color=("gray70", "gray35"),
            command=self.destroy,
        ).pack(side=ctk.RIGHT)

        # Category switcher row - only shown when categories are provided
        if self._categories:
            cat_row = ctk.CTkFrame(self, fg_color="transparent")
            cat_row.pack(fill=ctk.X, padx=10, pady=(0, 6))
            ctk.CTkLabel(cat_row, text="Category:", width=68).pack(side=ctk.LEFT)
            self._cat_var = ctk.StringVar(value=self._current_cat)
            ctk.CTkComboBox(
                cat_row,
                variable=self._cat_var,
                values=self._categories,
                command=self._on_category_change,
            ).pack(side=ctk.LEFT, fill=ctk.X, expand=True)

        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.pack(fill=ctk.BOTH, expand=True, padx=6, pady=(0, 8))

    # ---- items ---------------------------------------------------------------

    def _load_items(self, items: list[Item]):
        for btn, _ in self._buttons:
            btn.destroy()
        self._buttons.clear()
        self._ctk_images.clear()

        from er_save_manager.data.icon_manager import get_icon

        for item in items:
            img = get_icon(item.name)
            if img:
                ctk_img = ctk.CTkImage(
                    light_image=img, dark_image=img, size=(_ICON_SIZE, _ICON_SIZE)
                )
                self._ctk_images.append(ctk_img)
            else:
                ctk_img = None

            display = item.name if len(item.name) <= 18 else item.name[:16] + "\u2026"

            btn = ctk.CTkButton(
                self._scroll,
                image=ctk_img,
                text=display,
                compound="top",
                width=_CELL_W,
                height=_CELL_H,
                font=("Segoe UI", 9),
                fg_color=("gray82", "gray18"),
                hover_color=("gray70", "gray28"),
                text_color=("gray10", "gray90"),
                command=lambda it=item: self._select(it),
                anchor="center",
            )
            self._buttons.append((btn, item))

        self._apply_filter(
            self._search_var.get() if hasattr(self, "_search_var") else ""
        )

    def _on_category_change(self, value: str):
        from er_save_manager.data.item_database import get_item_database

        self._current_cat = value
        self.title(f"Browse: {value}")
        items = list(get_item_database().get_items_by_category(value))
        self._search_var.set("")
        self._load_items(items)

    # ---- layout & filtering --------------------------------------------------

    def _apply_filter(self, q: str):
        q = q.lower().strip()
        visible = [
            btn for btn, item in self._buttons if not q or q in item.name.lower()
        ]
        for btn, _ in self._buttons:
            btn.grid_forget()
        for idx, btn in enumerate(visible):
            row, col = divmod(idx, self._cols)
            btn.grid(row=row, column=col, padx=_CELL_PAD, pady=_CELL_PAD, sticky="nsew")
        # Force geometry propagation so the canvas scrollregion updates
        # correctly and the scrollbar reflects the true content height.
        self._scroll.update_idletasks()

    def _on_scroll_resize(self, event):
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(60, self._reflow)

    def _reflow(self):
        # Subtract scrollbar width so the 4th column doesn't end up behind it
        available = max(1, self._scroll.winfo_width() - _SCROLLBAR_W)
        new_cols = max(1, available // (_CELL_W + _CELL_PAD * 2))
        if new_cols != self._cols:
            self._cols = new_cols
            self._apply_filter(self._search_var.get())

    # ---- selection -----------------------------------------------------------

    def _select(self, item: Item):
        self._on_select(item)
        self.destroy()
