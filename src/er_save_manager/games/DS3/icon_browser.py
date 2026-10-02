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
from collections import deque
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
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import (
    center_window,
    debounced_trace,
    patch_combo_scroll,
)

if TYPE_CHECKING:
    from er_save_manager.games.DS3.tabs.inventory import DS3InventoryTab

ICON_SIZE = 64
CELL_W = 116
CELL_H = 106
CELL_PAD = 4
SCROLLBAR_W = 24
DEFAULT_COLS = 5
# Building every button in one pass freezes the popup on large lists, so a
# few are created per event loop turn.
BATCH = 16
DELAY_MS = 8

_CELL_COLOR = ("gray82", "gray18")
_CELL_SELECTED = ("#c9a0dc", "#4b3a6b")
_SHIFT = 0x0001
_CONTROL = 0x0004
SELECTED_TEXT = ("#7c4dac", "#c084fc")


def item_button(parent, item: dict | None, source: str, text: str, images: list):
    """Icon grid cell for an item; keeps its CTkImage alive in images."""
    img = item_icon(item, source)
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


class IconGrid:
    """Batched, reflowing grid of selectable buttons in a scrollable frame.

    Click selects one cell, Ctrl click toggles a cell and Shift click
    selects the visible range from the last clicked cell. on_select gets
    the selected keys in grid order.
    """

    def __init__(
        self, window: ctk.CTkToplevel, scroll: ctk.CTkScrollableFrame, on_select
    ):
        self._window = window
        self.scroll = scroll
        self._on_select = on_select
        self.cols = DEFAULT_COLS
        # (button, search text, key)
        self.cells: list[tuple[ctk.CTkButton, str, object]] = []
        self.images: list[ctk.CTkImage] = []
        self.selected: list = []
        self._anchor = None
        self._pending: deque = deque()
        self._make = None
        self._job: str | None = None
        self._resize_job: str | None = None
        self._count = 0
        self.query = ""
        scroll.bind("<Configure>", self._on_resize)

    def load(self, entries: list, make, keep_selection: bool = False) -> None:
        """Rebuild the grid; make(entry) returns (button, search text, key)."""
        if self._job is not None:
            self._window.after_cancel(self._job)
            self._job = None
        for btn, _, _ in self.cells:
            btn.destroy()
        self.cells.clear()
        self.images.clear()
        if not keep_selection:
            self.selected = []
        self._count = 0
        self._pending = deque(entries)
        self._make = make
        self._next_batch()

    def busy(self) -> bool:
        return self._job is not None

    def _next_batch(self) -> None:
        if not self._window.winfo_exists():
            return
        for _ in range(BATCH):
            if not self._pending:
                break
            btn, text, key = self._make(self._pending.popleft())
            btn.bind("<Button-1>", lambda e, k=key: self._click(k, e.state))
            if key in self.selected:
                btn.configure(fg_color=_CELL_SELECTED)
            self.cells.append((btn, text, key))
            if not self.query:
                # Grid straight into the next cell; re-laying out every
                # button per batch would be quadratic in the list size.
                row, col = divmod(self._count, self.cols)
                btn.grid(
                    row=row, column=col, padx=CELL_PAD, pady=CELL_PAD, sticky="nsew"
                )
                self._count += 1
        if not self._pending or self.query:
            self.apply_filter()
        if self._pending:
            self._job = self._window.after(DELAY_MS, self._next_batch)
        else:
            self._job = None
            # Keys selected before a reload may be gone now.
            self._set_selection([k for _, _, k in self.cells if k in self.selected])

    def _visible_keys(self) -> list:
        return [k for _, text, k in self.cells if not self.query or self.query in text]

    def _click(self, key, state: int) -> None:
        if state & _SHIFT and self._anchor is not None:
            keys = self._visible_keys()
            if self._anchor in keys and key in keys:
                a, b = sorted((keys.index(self._anchor), keys.index(key)))
                self._set_selection(keys[a : b + 1])
                return
        if state & _CONTROL:
            chosen = [k for k in self.selected if k != key]
            if key not in self.selected:
                chosen.append(key)
        else:
            chosen = [key]
        self._anchor = key
        self._set_selection(chosen)

    def _set_selection(self, keys: list) -> None:
        order = {k: i for i, (_, _, k) in enumerate(self.cells)}
        previous = set(self.selected)
        self.selected = sorted(keys, key=lambda k: order.get(k, 0))
        chosen = set(self.selected)
        # Recoloring redraws the button, so touch only cells whose state
        # changed; repainting every cell made each click scale with the grid.
        changed = previous ^ chosen
        for btn, _, key in self.cells:
            if key in changed:
                btn.configure(fg_color=_CELL_SELECTED if key in chosen else _CELL_COLOR)
        self._on_select(self.selected)

    def apply_filter(self, query: str | None = None) -> None:
        if query is not None:
            self.query = query
        visible = [
            b for b, text, _ in self.cells if not self.query or self.query in text
        ]
        for btn, _, _ in self.cells:
            btn.grid_forget()
        for idx, btn in enumerate(visible):
            row, col = divmod(idx, self.cols)
            btn.grid(row=row, column=col, padx=CELL_PAD, pady=CELL_PAD, sticky="nsew")
        self._count = len(visible)
        self.scroll.update_idletasks()
        canvas = self.scroll._parent_canvas
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_resize(self, _event) -> None:
        if self._resize_job:
            self._window.after_cancel(self._resize_job)
        self._resize_job = self._window.after(60, self._reflow)

    def _reflow(self) -> None:
        available = max(1, self.scroll.winfo_width() - SCROLLBAR_W)
        cols = max(1, available // (CELL_W + CELL_PAD * 2))
        if cols != self.cols:
            self.cols = cols
            self.apply_filter()


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
        # "All" would mean thousands of buttons, so the grid starts on Weapons.
        options = [o for o in self._tab.category_options() if o != "All"]
        if self._tab.category() not in options:
            self._tab.set_category(options[0])
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
            btn = item_button(self._grid.scroll, item, source, label, self._grid.images)
            return btn, label.lower(), index

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
        items = [self._rows[k][1] for k in self._grid._visible_keys()]
        self._tab.spawn_items(items, *values, parent=self)
