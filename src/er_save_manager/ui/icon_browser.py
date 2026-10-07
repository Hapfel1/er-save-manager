"""Visual icon-grid add-item popup."""

from __future__ import annotations

import re
import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.ui import palette
from er_save_manager.ui.utils import (
    center_window,
    debounced_trace,
    patch_combo_scroll,
    pick_file,
)

if TYPE_CHECKING:
    from er_save_manager.data.item_database import Item
    from er_save_manager.ui.editors.inventory_editor import InventoryEditor

_DEFAULT_COLS = 4
_ICON_SIZE = 64
_CELL_W = 116
_CELL_H = 110
_CELL_PAD = 4
_SCROLLBAR_W = 24
# Buttons created per event-loop turn when filling a category. CTkButton
# construction costs a few ms each, so a large category built in one go
# freezes the window for seconds.
_BUILD_BATCH = 8
_CELL_COLOR = ("gray82", "gray18")
_CELL_SELECTED = palette.PURPLE_SELECT


def _center_over(window, parent, w=None, h=None, *, top=False) -> None:
    """Center window over parent. Pass w/h explicitly to avoid pre-map size queries."""
    center_window(window, w, h, parent=parent, align_top=top)


class IconBrowser(ctk.CTkToplevel):
    """
    Visual add-item popup.
    Select from the icon grid, configure options in the panel below, click Add Item.
    """

    def __init__(
        self,
        parent,
        editor: InventoryEditor,
        initial_category: str = "",
        dev_icon_export: bool = False,
    ):
        super().__init__(parent)
        self._editor = editor
        self._cols = _DEFAULT_COLS
        self._buttons: list[tuple[ctk.CTkButton, Item]] = []
        self._ctk_images: list = []
        self._resize_job: str | None = None
        self._build_job: str | None = None
        self._pending_items: list[Item] = []
        self._filter_q = ""
        self._grid_count = 0
        self._current_cat = initial_category
        self._selected_item: Item | None = None
        self._selected_gem_id: int = 0
        self._dev_icon_export = dev_icon_export

        w = _DEFAULT_COLS * (_CELL_W + _CELL_PAD * 2) + 12 + _SCROLLBAR_W + 30
        self.title("Add Item")
        self.geometry(f"{w}x800")
        self.minsize(w, 520)
        self.resizable(True, True)
        self.transient(parent)
        self.attributes("-alpha", 0)
        self.update_idletasks()
        _center_over(self, parent, w, 800, top=True)
        self.attributes("-alpha", 1)
        # Non-modal by design: the visual inventory may be open at the same time
        self.raise_window()

        self._build_ui()

        cats = editor._visible_categories()
        if not self._current_cat and cats:
            self._current_cat = cats[0]
            self._cat_var.set(self._current_cat)
        self._load_category(self._current_cat)

        self._scroll.bind("<Configure>", self._on_scroll_resize)
        self.after(120, self._reflow)

        # Add buttons say where items go while Loadout Mode is on.
        self._mode_trace = editor.loadout_mode_var.trace_add(
            "write", lambda *_: self._update_add_labels()
        )
        self._update_add_labels()

    def raise_window(self) -> None:
        """Bring the window forward. Called on open and when reopened from the editor."""
        if not self.winfo_exists():
            return
        self.deiconify()
        self.lift()
        self.focus_force()

    # ---- UI ------------------------------------------------------------------

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill=ctk.X, padx=10, pady=(10, 4))

        ctk.CTkLabel(top, text="Search:", width=52).pack(side=ctk.LEFT)
        self._search_var = ctk.StringVar()
        debounced_trace(
            self, self._search_var, lambda: self._apply_filter(self._search_var.get())
        )
        ctk.CTkEntry(
            top, textvariable=self._search_var, placeholder_text="Filter..."
        ).pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 8))
        ctk.CTkButton(
            top,
            text="Close",
            width=72,
            height=28,
            fg_color=("gray70", "gray35"),
            command=self.destroy,
        ).pack(side=ctk.RIGHT)

        cat_row = ctk.CTkFrame(self, fg_color="transparent")
        cat_row.pack(fill=ctk.X, padx=10, pady=(0, 6))
        ctk.CTkLabel(cat_row, text="Category:", width=68).pack(side=ctk.LEFT)
        cats = self._editor._visible_categories()
        self._cat_var = ctk.StringVar(value=self._current_cat)
        patch_combo_scroll(
            ctk.CTkComboBox(
                cat_row,
                variable=self._cat_var,
                values=cats,
                command=self._on_category_change,
            )
        ).pack(side=ctk.LEFT, fill=ctk.X, expand=True)

        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.pack(fill=ctk.BOTH, expand=True, padx=6, pady=(0, 4))

        self._build_add_panel()

    def _build_add_panel(self):
        panel = ctk.CTkFrame(self, fg_color=("gray88", "gray18"), corner_radius=8)
        panel.pack(fill=ctk.X, padx=6, pady=(0, 8))

        self._sel_lbl = ctk.CTkLabel(
            panel,
            text="No item selected",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            text_color=("gray50", "gray60"),
        )
        self._sel_lbl.pack(fill=ctk.X, padx=10, pady=(8, 4))

        opts = ctk.CTkFrame(panel, fg_color="transparent")
        opts.pack(fill=ctk.X, padx=10, pady=(0, 4))
        opts.columnconfigure(1, weight=1)
        opts.columnconfigure(3, weight=1)

        # Quantity + Upgrade
        ctk.CTkLabel(opts, text="Quantity:", anchor="w").grid(
            row=0, column=0, sticky=ctk.W, padx=(0, 6), pady=3
        )
        self._qty_var = ctk.IntVar(value=1)
        self._qty_entry = ctk.CTkEntry(
            opts, textvariable=self._qty_var, width=70, state="disabled"
        )
        self._qty_entry.grid(row=0, column=1, sticky=ctk.W, pady=3)

        ctk.CTkLabel(opts, text="Upgrade:", anchor="w").grid(
            row=0, column=2, sticky=ctk.W, padx=(14, 6), pady=3
        )
        self._upgrade_var = ctk.StringVar(value="0")
        self._upgrade_combo = ctk.CTkComboBox(
            opts, variable=self._upgrade_var, values=["0"], width=70, state="disabled"
        )
        self._upgrade_combo.grid(row=0, column=3, sticky=ctk.W, pady=3)
        patch_combo_scroll(self._upgrade_combo)

        # Affinity + Location
        ctk.CTkLabel(opts, text="Affinity:", anchor="w").grid(
            row=1, column=0, sticky=ctk.W, padx=(0, 6), pady=3
        )
        aff_frame = ctk.CTkFrame(opts, fg_color="transparent")
        aff_frame.grid(row=1, column=1, sticky=ctk.W, pady=3)
        self._affinity_icon_lbl = ctk.CTkLabel(aff_frame, text="", width=26, height=26)
        self._affinity_icon_lbl.pack(side=ctk.LEFT, padx=(0, 4))
        self._affinity_var = ctk.StringVar(value="Standard")
        self._affinity_combo = ctk.CTkComboBox(
            aff_frame,
            variable=self._affinity_var,
            values=[n for _, n in self._editor._AFFINITIES_VANILLA],
            width=140,
            state="disabled",
            command=self._on_affinity_changed,
        )
        self._affinity_combo.pack(side=ctk.LEFT)
        patch_combo_scroll(self._affinity_combo)

        ctk.CTkLabel(opts, text="Location:", anchor="w").grid(
            row=1, column=2, sticky=ctk.W, padx=(14, 6), pady=3
        )
        self._location_var = ctk.StringVar(value="held")
        ctk.CTkComboBox(
            opts, variable=self._location_var, values=["held", "storage"], width=120
        ).grid(row=1, column=3, sticky=ctk.W, pady=3)

        # AoW
        ctk.CTkLabel(opts, text="Ash of War:", anchor="w").grid(
            row=2, column=0, sticky=ctk.W, padx=(0, 6), pady=3
        )
        aow_frame = ctk.CTkFrame(opts, fg_color="transparent")
        aow_frame.grid(row=2, column=1, sticky=ctk.W, pady=3)
        self._aow_icon_lbl = ctk.CTkLabel(aow_frame, text="", width=26, height=26)
        self._aow_icon_lbl.pack(side=ctk.LEFT, padx=(0, 4))
        self._aow_var = ctk.StringVar(value="None")
        self._aow_name_lbl = ctk.CTkLabel(
            aow_frame,
            textvariable=self._aow_var,
            text_color=("gray50", "gray60"),
            width=140,
            anchor="w",
        )
        self._aow_name_lbl.pack(side=ctk.LEFT)

        self._aow_pick_btn = ctk.CTkButton(
            opts,
            text="Pick...",
            width=60,
            height=24,
            command=self._pick_aow,
            state="disabled",
        )
        self._aow_pick_btn.grid(row=2, column=2, sticky=ctk.W, pady=3)
        self._aow_clear_btn = ctk.CTkButton(
            opts,
            text="Clear",
            width=55,
            height=24,
            command=self._clear_aow,
            state="disabled",
            fg_color=("gray70", "gray35"),
        )
        self._aow_clear_btn.grid(row=2, column=3, sticky=ctk.W, pady=3)

        add_row = ctk.CTkFrame(panel, fg_color="transparent")
        add_row.pack(fill=ctk.X, padx=10, pady=(4, 10))

        self._add_btn = ctk.CTkButton(
            add_row,
            text="Add Item",
            height=34,
            font=("Segoe UI", 11, "bold"),
            command=self._do_add,
            state="disabled",
        )
        self._add_btn.pack(side=ctk.LEFT, fill=ctk.X, expand=True)

        self._batch_btn = ctk.CTkButton(
            add_row,
            text="Batch Add Category",
            height=34,
            fg_color=palette.BLUE,
            hover_color=palette.BLUE_HOVER,
            text_color=palette.ON_BLUE,
            command=self._batch_add_category,
        )
        self._batch_btn.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(6, 0))

        self._loadout_switch = ctk.CTkSwitch(
            add_row,
            text="Loadout Mode",
            variable=self._editor.loadout_mode_var,
            font=("Segoe UI", 11),
            width=40,
        )
        self._loadout_switch.pack(side=ctk.LEFT, padx=(10, 0))

        if self._dev_icon_export:
            self._save_icon_btn = ctk.CTkButton(
                add_row,
                text="Save Icon",
                height=34,
                width=100,
                fg_color=("gray70", "gray35"),
                command=self._save_icon,
                state="disabled",
            )
            self._save_icon_btn.pack(side=ctk.LEFT, padx=(6, 0))
        else:
            self._save_icon_btn = None

    # ---- items ---------------------------------------------------------------

    def _load_category(self, cat: str):
        from er_save_manager.data.item_database import get_item_database

        items = list(get_item_database().get_items_by_category(cat)) if cat else []
        self._load_items(items)

    def _load_items(self, items: list[Item]):
        self._cancel_build()
        for btn, _ in self._buttons:
            btn.destroy()
        self._buttons.clear()
        self._ctk_images.clear()
        self._pending_items = list(items)
        self._apply_filter(
            self._search_var.get() if hasattr(self, "_search_var") else ""
        )
        self._build_next_batch()

    def _build_next_batch(self):
        """Create the next batch of item buttons, then yield to the event loop."""
        self._build_job = None
        if not self.winfo_exists():
            return
        from er_save_manager.data.icon_manager import get_icon

        batch = self._pending_items[:_BUILD_BATCH]
        del self._pending_items[:_BUILD_BATCH]
        for item in batch:
            img = get_icon(item.name, getattr(item, "category_name", ""))
            ctk_img = None
            if img:
                ctk_img = ctk.CTkImage(
                    light_image=img, dark_image=img, size=(_ICON_SIZE, _ICON_SIZE)
                )
                self._ctk_images.append(ctk_img)

            btn = ctk.CTkButton(
                self._scroll,
                image=ctk_img,
                text=item.name,
                compound="top",
                width=_CELL_W,
                height=_CELL_H,
                font=("Segoe UI", 11),
                fg_color=_CELL_SELECTED if item is self._selected_item else _CELL_COLOR,
                hover_color=("gray70", "gray28"),
                text_color=("gray10", "gray90"),
                command=lambda it=item: self._on_item_click(it),
                anchor="center",
            )
            if hasattr(btn, "_text_label") and btn._text_label is not None:
                btn._text_label.configure(wraplength=_CELL_W - 8, justify="center")
            self._buttons.append((btn, item))
            if not self._filter_q or self._filter_q in item.name.lower():
                self._grid_button(btn, self._grid_count)
                self._grid_count += 1

        self._sync_scroll_region()
        if self._pending_items:
            self._build_job = self.after(1, self._build_next_batch)

    def _cancel_build(self):
        if self._build_job:
            self.after_cancel(self._build_job)
            self._build_job = None
        self._pending_items = []

    def destroy(self):
        self._cancel_build()
        trace = getattr(self, "_mode_trace", None)
        if trace is not None:
            self._editor.loadout_mode_var.trace_remove("write", trace)
            self._mode_trace = None
        super().destroy()

    def _update_add_labels(self) -> None:
        """Mark the add buttons like the editor's while Loadout Mode is on."""
        from er_save_manager.ui.editors.inventory_editor import style_add_buttons

        style_add_buttons(
            self._add_btn, self._batch_btn, self._editor.loadout_mode_var.get()
        )

    def _on_category_change(self, value: str):
        self._current_cat = value
        self.title(f"Add Item - {value}")
        # Clear the query first so the new category loads unfiltered.
        self._search_var.set("")
        self._load_category(value)
        self._scroll._parent_canvas.yview_moveto(0)
        self._editor._sync_browse_category(value)

    # ---- layout / filter -----------------------------------------------------

    def _apply_filter(self, q: str):
        q = q.lower().strip()
        self._filter_q = q
        visible = [
            btn for btn, item in self._buttons if not q or q in item.name.lower()
        ]
        for btn, _ in self._buttons:
            btn.grid_forget()
        for idx, btn in enumerate(visible):
            self._grid_button(btn, idx)
        # Buttons still being built continue after the visible ones.
        self._grid_count = len(visible)
        self._sync_scroll_region()

    def _grid_button(self, btn: ctk.CTkButton, idx: int):
        row, col = divmod(idx, self._cols)
        btn.grid(row=row, column=col, padx=_CELL_PAD, pady=_CELL_PAD, sticky="nsew")

    def _sync_scroll_region(self):
        # Let tkinter measure the new grid, then sync the canvas scroll region.
        self._scroll.update_idletasks()
        canvas = self._scroll._parent_canvas
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_scroll_resize(self, event):
        if self._resize_job:
            self.after_cancel(self._resize_job)
            self._resize_job = None
        self._resize_job = self.after(60, self._reflow)

    def _reflow(self):
        available = max(1, self._scroll.winfo_width() - _SCROLLBAR_W)
        new_cols = max(1, available // (_CELL_W + _CELL_PAD * 2))
        if new_cols != self._cols:
            self._cols = new_cols
            self._apply_filter(self._search_var.get())

    # ---- item selection ------------------------------------------------------

    def _on_item_click(self, item: Item):
        previous = self._selected_item
        self._selected_item = item
        for btn, cell_item in self._buttons:
            if cell_item is item:
                btn.configure(fg_color=_CELL_SELECTED)
            elif cell_item is previous:
                btn.configure(fg_color=_CELL_COLOR)
        self._sel_lbl.configure(
            text=f"Selected: {item.name}", text_color=palette.PURPLE_TEXT
        )
        self._update_form(item)

    def _resolved_item(self) -> Item | None:
        """The selected item as the loaded save's game version defines it."""
        if self._selected_item is None:
            return None
        from er_save_manager.data.item_database import get_item_database

        return get_item_database().resolve(
            self._selected_item, self._editor._is_cnv_save()
        )

    def _update_form(self, item: Item):
        """Reset and enable/disable form controls based on item type."""
        from er_save_manager.data.item_database import ItemCategory

        item = self._resolved_item() or item

        is_weapon = item.category == ItemCategory.WEAPON
        is_armor = item.category == ItemCategory.ARMOR
        is_gem = item.category == ItemCategory.GEM
        is_ashes = item.category_name in ("Ashes", "DLC Ashes")
        is_upgradable = is_weapon or is_ashes
        reinforcement = (
            getattr(item, "reinforcement", "standard") if is_weapon else "standard"
        )
        aow_allowed = is_weapon and getattr(item, "aow_allowed", True)
        affinity_allowed = is_weapon and reinforcement == "standard" and aow_allowed

        max_arrow = getattr(item, "max_arrow_quantity", 1)
        is_ammo = is_weapon and max_arrow > 1
        if (is_weapon and not is_ammo) or is_armor or is_gem:
            self._qty_var.set(1)
            self._qty_entry.configure(state="disabled")
        else:
            max_num = max_arrow if is_ammo else getattr(item, "max_num", 1)
            self._qty_var.set(1)
            self._qty_entry.configure(state="normal" if max_num > 1 else "disabled")

        if is_upgradable:
            if is_ashes:
                cap = 10
            else:
                is_cnv = self._editor._is_cnv_save()
                explicit_cap = getattr(item, "max_upgrade", -1)
                if explicit_cap >= 0:
                    cap = explicit_cap
                elif is_cnv and reinforcement in ("standard", "somber"):
                    cap = 15
                else:
                    cap = (
                        25
                        if reinforcement == "standard"
                        else 10
                        if reinforcement == "somber"
                        else 0
                    )
            self._upgrade_combo.configure(
                values=[str(i) for i in range(cap + 1)], state="normal"
            )
            self._upgrade_var.set("0")
        else:
            self._upgrade_combo.configure(values=["0"], state="disabled")
            self._upgrade_var.set("0")

        is_cnv = self._editor._is_cnv_save()
        # Vanilla only infuses through an Ash of War
        if affinity_allowed and (is_cnv or self._selected_gem_id):
            weapon_affs = item.get_affinities(is_cnv)
            self._affinity_combo.configure(
                values=weapon_affs or self._editor._affinity_names(), state="normal"
            )
            self._affinity_var.set("Standard")
            self._update_affinity_icon("Standard")
        else:
            self._affinity_combo.configure(state="disabled")
            self._affinity_var.set("Standard")
            self._update_affinity_icon("Standard")

        aow_state = "normal" if aow_allowed else "disabled"
        self._aow_pick_btn.configure(state=aow_state)
        self._aow_clear_btn.configure(state=aow_state)
        if not aow_allowed:
            self._clear_aow()

        self._add_btn.configure(state="normal")
        if self._save_icon_btn:
            self._save_icon_btn.configure(state="normal")

    # ---- icon helpers --------------------------------------------------------

    def _on_affinity_changed(self, value: str):
        self._update_affinity_icon(value)

    def _update_affinity_icon(self, name: str):
        try:
            from er_save_manager.data.icon_manager import get_affinity_icon

            img = get_affinity_icon(name, is_convergence=self._editor._is_cnv_save())
            if img:
                cimg = ctk.CTkImage(img, img, (22, 22))
                self._affinity_icon_lbl.configure(image=cimg)
                self._affinity_icon_lbl._cached_icon = cimg
            else:
                self._affinity_icon_lbl.configure(image=None)
        except Exception:
            self._affinity_icon_lbl.configure(image=None)

    def _update_aow_icon(self, name: str):
        try:
            from er_save_manager.data.icon_manager import get_icon

            img = get_icon(name) if name and name != "None" else None
            if img:
                cimg = ctk.CTkImage(img, img, (22, 22))
                self._aow_icon_lbl.configure(image=cimg)
                self._aow_icon_lbl._cached_icon = cimg
            else:
                self._aow_icon_lbl.configure(image=None)
        except Exception:
            self._aow_icon_lbl.configure(image=None)

    def _clear_aow(self):
        self._selected_gem_id = 0
        self._aow_var.set("None")
        self._aow_name_lbl.configure(text_color=("gray50", "gray60"))
        self._update_aow_icon("None")
        is_cnv = self._editor._is_cnv_save()
        item = self._resolved_item()
        weapon_affs = item.get_affinities(is_cnv) if item is not None else []
        self._affinity_combo.configure(
            values=weapon_affs or self._editor._affinity_names()
        )
        if not is_cnv:
            self._affinity_combo.configure(state="disabled")
        self._affinity_var.set("Standard")
        self._update_affinity_icon("Standard")

    # ---- AoW picker ----------------------------------------------------------

    def _pick_aow(self):
        if not self._selected_item:
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Select Ash of War")
        dialog.geometry("400x420")
        dialog.resizable(False, True)
        dialog.transient(self)
        dialog.attributes("-alpha", 0)
        dialog.update_idletasks()
        _center_over(dialog, self, 400, 420)
        dialog.attributes("-alpha", 1)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()

        mode = ctk.get_appearance_mode()
        lb_bg = "#1a1a24" if mode == "Dark" else "#f0f0f0"
        lb_fg = "#d4d4e8" if mode == "Dark" else "#111111"
        lb_sel = palette.pick(palette.PURPLE_SELECT)

        search_var = ctk.StringVar()
        ctk.CTkLabel(dialog, text="Search:").pack(anchor="w", padx=10, pady=(10, 0))
        ctk.CTkEntry(dialog, textvariable=search_var, width=360).pack(
            padx=10, pady=(0, 4)
        )

        lb_frame = ctk.CTkFrame(dialog, fg_color=("gray82", "gray14"), corner_radius=6)
        lb_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=4)

        cv = tk.Canvas(lb_frame, bg=lb_bg, highlightthickness=0, bd=0)
        sb = tk.Scrollbar(lb_frame, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        cv.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        _ROW_H = 32
        _photos: list = []
        _drawn: list = []
        _sel: list[int | None] = [None]
        _job: list = [None]

        is_cnv = self._editor._is_cnv_save()
        weapon = self._resolved_item()
        wep_col = getattr(weapon, "wep_type_col", "")
        weapon_affs = weapon.get_affinities(is_cnv) if weapon is not None else []
        aff_state = (
            "normal"
            if getattr(weapon, "reinforcement", "standard") == "standard"
            else "disabled"
        )

        def _draw(gems):
            if _job[0]:
                try:
                    dialog.after_cancel(_job[0])
                except Exception:
                    pass
                _job[0] = None
            cv.delete("all")
            _photos.clear()
            _drawn.clear()
            _sel[0] = None
            cw = max(cv.winfo_width(), 360)
            for i, g in enumerate(gems):
                y0 = i * _ROW_H
                cv.create_rectangle(
                    0,
                    y0,
                    cw,
                    y0 + _ROW_H,
                    fill=lb_bg,
                    outline="",
                    tags=f"row_{i}",
                )
                cv.create_text(
                    36,
                    y0 + _ROW_H // 2,
                    text=g.name,
                    fill=lb_fg,
                    font=("Consolas", 10),
                    anchor="w",
                    tags=f"text_{i}",
                )
                _drawn.append(g)
            cv.configure(scrollregion=(0, 0, cw, len(gems) * _ROW_H))
            _job[0] = dialog.after(80, lambda: _load_icons(0))

        def _load_icons(start: int, batch: int = 20):
            try:
                from PIL import Image, ImageTk

                from er_save_manager.data.icon_manager import get_icon
            except Exception:
                return
            end = min(start + batch, len(_drawn))
            for i in range(start, end):
                try:
                    pil = get_icon(_drawn[i].name)
                    if pil:
                        pil = pil.convert("RGBA").resize((24, 24), Image.LANCZOS)
                        ph = ImageTk.PhotoImage(pil)
                        _photos.append(ph)
                        y0 = i * _ROW_H
                        cv.create_image(
                            4, y0 + _ROW_H // 2, image=ph, anchor="w", tags=f"icon_{i}"
                        )
                except Exception:
                    pass
            if end < len(_drawn):
                _job[0] = dialog.after(30, lambda: _load_icons(end, batch))
            else:
                _job[0] = None
                cv._photo_refs = _photos  # prevent GC

        def _click(event):
            idx = int(cv.canvasy(event.y) // _ROW_H)
            if 0 <= idx < len(_drawn):
                prev = _sel[0]
                _sel[0] = idx
                for i in (prev, idx):
                    if i is not None:
                        cv.itemconfigure(
                            f"row_{i}", fill=lb_sel if i == _sel[0] else lb_bg
                        )

        cv.bind("<Button-1>", _click)
        cv.bind("<Double-Button-1>", lambda e: (_click(e), _confirm()))
        cv.bind("<MouseWheel>", lambda e: cv.yview_scroll(int(-e.delta / 120), "units"))
        cv.bind("<Button-4>", lambda _e: cv.yview_scroll(-1, "units"))
        cv.bind("<Button-5>", lambda _e: cv.yview_scroll(1, "units"))

        try:
            from er_save_manager.data.item_database import (
                common_affinities,
                get_item_database,
            )

            db = get_item_database()
            gem_cats = ["Gems", "DLC Gems"] + (["Convergence Gems"] if is_cnv else [])
            unique_gems: dict = {}
            for c in gem_cats:
                for g in db.get_items_by_category(c):
                    g = db.resolve(g, is_cnv)
                    unique_gems.setdefault(g.full_id, g)
            all_gems: list = list(unique_gems.values())
            if wep_col:
                all_gems = [
                    g
                    for g in all_gems
                    if not g.compatible_wep_types or wep_col in g.compatible_wep_types
                ]
        except Exception:
            all_gems = []

        visible: list = []

        def _filter(*_):
            q = search_var.get().lower().strip()
            visible.clear()
            visible.extend(g for g in all_gems if not q or q in g.name.lower())
            _draw(visible[:200])

        search_var.trace_add("write", _filter)
        _filter()

        def _confirm():
            idx = _sel[0]
            if idx is None or idx >= len(visible):
                return
            gem = visible[idx]
            self._selected_gem_id = 0x80000000 | gem.id
            self._aow_var.set(gem.name)
            self._aow_name_lbl.configure(text_color=palette.PURPLE_TEXT)
            self._update_aow_icon(gem.name)
            gem_affs = common_affinities(gem.get_affinities(is_cnv), weapon_affs)
            if gem_affs:
                self._affinity_combo.configure(values=gem_affs, state=aff_state)
                default = (
                    gem.default_affinity
                    if gem.default_affinity in gem_affs
                    else gem_affs[0]
                )
                self._affinity_var.set(default)
                self._update_affinity_icon(default)
            dialog.destroy()

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill=ctk.X, padx=10, pady=(4, 10))
        ctk.CTkButton(btn_row, text="Select", command=_confirm, width=100).pack(
            side=ctk.LEFT, padx=(0, 6)
        )
        ctk.CTkButton(btn_row, text="Cancel", command=dialog.destroy, width=80).pack(
            side=ctk.RIGHT
        )

    # ---- add -----------------------------------------------------------------

    def _save_icon(self):
        if not self._selected_item:
            return
        from er_save_manager.data.icon_manager import get_icon

        img = get_icon(
            self._selected_item.name,
            getattr(self._selected_item, "category_name", ""),
        )
        if img is None:
            from er_save_manager.ui.messagebox import CTkMessageBox

            CTkMessageBox.showwarning(
                "No Icon",
                f"No icon found for {self._selected_item.name}.",
                parent=self,
            )
            return

        safe_name = re.sub(r'[\/:*?"<>|]', "_", self._selected_item.name)
        path = pick_file(
            title="Save Icon",
            save=True,
            defaultextension=".webp",
            initialfile=f"{safe_name}.webp",
            filetypes=[("WebP image", "*.webp"), ("PNG image", "*.png")],
        )
        if not path:
            return
        fmt = "PNG" if path.lower().endswith(".png") else "WEBP"
        img.save(path, fmt)

    def _do_add(self):
        if not self._selected_item:
            return
        editor = self._editor
        editor.selected_item = self._resolved_item()
        editor.inv_quantity_var.set(self._qty_var.get())
        editor.inv_upgrade_var.set(self._upgrade_var.get())
        editor.inv_affinity_var.set(self._affinity_var.get())
        editor.inv_location_var.set(self._location_var.get())
        editor._selected_gem_id = self._selected_gem_id

        # Parent dialogs to this window so grab_set is not lost on error
        orig_parent = editor.parent
        editor.parent = self
        try:
            if editor.loadout_mode_var.get():
                editor.add_to_loadout()
            else:
                editor.add_item()
        finally:
            editor.parent = orig_parent

    def _batch_add_category(self):
        editor = self._editor
        editor.inv_quantity_var.set(self._qty_var.get())
        editor.inv_upgrade_var.set(self._upgrade_var.get())
        editor.inv_location_var.set(self._location_var.get())
        editor.batch_add_category(self._current_cat, parent_window=self)
