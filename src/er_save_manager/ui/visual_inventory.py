"""Visual inventory browser popup - Canvas-based to avoid X11 resource exhaustion."""

from __future__ import annotations

import gc
import platform as _platform
import re
import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from er_save_manager.ui.editors.inventory_editor import InventoryEditor

_CELL_W = 124
_CELL_H = 128
_IMG_SZ = 60
_PAD = 3
_BATCH = 10
_DELAY = 50
_MAX_IMG = 999


def _is_weapon(full_id: int) -> bool:
    return (full_id & 0xF0000000) == 0x00000000


def _parse_cell_info(text: str, full_id: int):
    """Return (display_name, suffix) parsed from the row text string."""
    # Strip location tag [H] / [S] / [HK] etc.
    name_part = re.sub(r"^\s*\[[HS]K?\]\s*", "", text.split("|")[0]).strip()
    # Name may already have +N suffix for weapons - keep it as-is from text
    suffix = ""
    upg_m = re.search(r"\s*\+(\d+)$", name_part)
    qty_m = re.search(r"Qty:\s*(\d+)", text)
    is_w = _is_weapon(full_id)

    if is_w and upg_m:
        base_name = name_part[: upg_m.start()].strip()
        upg = int(upg_m.group(1))
        suffix = f" +{upg}" if upg else ""
    else:
        base_name = name_part
        if not is_w and qty_m:
            qty = int(qty_m.group(1))
            if qty > 1:
                suffix = f" x{qty}"

    return base_name, suffix


def _cell_icon(full_id, gaitem_handle, slot, aff_code, affinity_names):
    try:
        from er_save_manager.data.icon_manager import (
            compose_weapon_icon,
            get_affinity_icon,
            get_icon,
        )
        from er_save_manager.data.item_database import get_item_database

        db = get_item_database()
        cat = full_id & 0xF0000000
        is_w = cat == 0x00000000
        if is_w:
            base = (full_id & 0x0FFFFFFF) // 10000 * 10000
            item = db.get_item_by_id(cat | base) or db.get_item_by_id(full_id)
        else:
            item = db.get_item_by_id(full_id)
        name = item.name if item else None
        base_img = get_icon(name) if name else None
        if not base_img:
            return None
        if not is_w:
            return base_img
        aow_img = aff_img = None
        if slot and gaitem_handle:
            for g in getattr(slot, "gaitem_map", []):
                if g.gaitem_handle != gaitem_handle:
                    continue
                gem_h = getattr(g, "gem_gaitem_handle", None)
                if gem_h and gem_h not in (0, -1):
                    gem_u = gem_h & 0xFFFFFFFF
                    for gg in getattr(slot, "gaitem_map", []):
                        if gg.gaitem_handle == gem_u:
                            gi = db.get_item_by_id(
                                0x80000000 | (gg.item_id & 0x0FFFFFFF)
                            )
                            if gi:
                                aow_img = get_icon(gi.name)
                            break
                break
        aff_name = affinity_names.get(aff_code)
        if aff_name and aff_name != "Standard":
            is_cnv = len(affinity_names) > 13
            aff_img = get_affinity_icon(aff_name, is_convergence=is_cnv)
        if aow_img or aff_img:
            return compose_weapon_icon(base_img, aow_img, aff_img)
        return base_img
    except Exception:
        return None


def _patch_combo_scroll(combo):
    """Bind mousewheel to CTkComboBox dropdown on Windows. Returns combo."""
    if _platform.system() != "Windows":
        return combo
    orig = combo._open_dropdown_menu

    def _open():
        orig()
        dm = getattr(combo, "_dropdown_menu", None)
        if dm is None:
            return
        frame = getattr(dm, "_frame", None)
        if frame is None:
            return
        canvas = getattr(frame, "_parent_canvas", None)
        if canvas is None:
            return

        def _scroll(e):
            canvas.yview_scroll(int(-e.delta / 120), "units")

        canvas.bind("<MouseWheel>", _scroll, add="+")
        for child in frame.winfo_children():
            child.bind("<MouseWheel>", _scroll, add="+")
            for sub in child.winfo_children():
                sub.bind("<MouseWheel>", _scroll, add="+")

    combo._open_dropdown_menu = _open
    return combo


def _center_over(window, parent) -> None:
    """Position window centered over parent."""
    window.update_idletasks()
    w = window.winfo_reqwidth()
    h = window.winfo_reqheight()
    x = max(0, parent.winfo_rootx() + (parent.winfo_width() - w) // 2)
    y = max(0, parent.winfo_rooty() + (parent.winfo_height() - h) // 2)
    window.geometry(f"+{x}+{y}")


class VisualInventoryBrowser(ctk.CTkToplevel):
    """Single Canvas grid view - one X11 window regardless of inventory size."""

    def __init__(self, parent, editor: InventoryEditor):
        super().__init__(parent)
        self._editor = editor
        self._tab = "held"
        self._cat_filter = "All"
        self._visible: list[tuple] = []
        self._sel_idx: int | None = None
        self._photos: list = []
        self._load_job: str | None = None

        self.title("Visual Inventory")
        self.geometry("760x680")
        self.minsize(500, 400)
        self.resizable(True, True)
        self.transient(parent)
        self.after(100, self.grab_set)

        self._build_ui()
        self._rebuild()
        _center_over(self, parent)
        self._editor._inventory_change_listeners.append(self._on_editor_changed)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- UI ------------------------------------------------------------------

    def _build_ui(self):
        mode = ctk.get_appearance_mode()
        self._bg = "#1a1a24" if mode == "Dark" else "#f0f0f0"
        self._fg = "#d4d4e8" if mode == "Dark" else "#111111"
        self._sel_bg = "#3a1a6a" if mode == "Dark" else "#b8a0d0"
        self._cell_bg = "#222230" if mode == "Dark" else "#e8e8f0"
        self._cell_out = "#444460" if mode == "Dark" else "#ccccdd"

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill=ctk.X, padx=10, pady=(10, 4))

        tab_f = ctk.CTkFrame(top, fg_color="transparent")
        tab_f.pack(side=ctk.LEFT)
        self._btn_held = ctk.CTkButton(
            tab_f,
            text="Held",
            width=72,
            height=28,
            command=lambda: self._switch_tab("held"),
        )
        self._btn_held.pack(side=ctk.LEFT, padx=(0, 4))
        self._btn_stor = ctk.CTkButton(
            tab_f,
            text="Storage",
            width=80,
            height=28,
            fg_color=("gray70", "gray35"),
            command=lambda: self._switch_tab("storage"),
        )
        self._btn_stor.pack(side=ctk.LEFT)

        self._cat_var = ctk.StringVar(value="All")
        ctk.CTkLabel(top, text="Category:", width=68).pack(side=ctk.LEFT, padx=(12, 0))
        self._cat_combo = ctk.CTkComboBox(
            top,
            variable=self._cat_var,
            values=["All"],
            width=170,
            command=self._on_cat_changed,
        )
        self._cat_combo.pack(side=ctk.LEFT, padx=(0, 8))
        _patch_combo_scroll(self._cat_combo)

        self._filter_var = ctk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkLabel(top, text="Filter:").pack(side=ctk.LEFT)
        ctk.CTkEntry(
            top, textvariable=self._filter_var, placeholder_text="Search...", width=150
        ).pack(side=ctk.LEFT, padx=(4, 0))
        ctk.CTkButton(
            top,
            text="Close",
            width=68,
            height=28,
            fg_color=("gray70", "gray35"),
            command=self._on_close,
        ).pack(side=ctk.RIGHT)

        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill=ctk.X, padx=10, pady=(0, 2))
        self._sort_var = ctk.StringVar(value="Name A-Z")
        ctk.CTkLabel(row2, text="Sort:").pack(side=ctk.LEFT)
        ctk.CTkComboBox(
            row2,
            variable=self._sort_var,
            width=120,
            values=["Default", "Name A-Z", "Name Z-A", "Qty \u2193", "Qty \u2191"],
            command=self._on_sort_changed,
        ).pack(side=ctk.LEFT, padx=(4, 0))

        cf = ctk.CTkFrame(self, fg_color=("gray82", "gray14"), corner_radius=6)
        cf.pack(fill=ctk.BOTH, expand=True, padx=6, pady=(4, 0))
        self._canvas = tk.Canvas(cf, bg=self._bg, highlightthickness=0, bd=0)
        vsb = tk.Scrollbar(cf, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self._canvas.bind("<Configure>", lambda _e: self._draw_grid())
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind(
            "<MouseWheel>", lambda e: self._on_scroll(int(-e.delta / 120))
        )
        self._canvas.bind("<Button-4>", lambda _e: self._on_scroll(-1))
        self._canvas.bind("<Button-5>", lambda _e: self._on_scroll(1))

        # Fixed-height bottom panel: two label rows
        bot = ctk.CTkFrame(self, fg_color=("gray88", "gray16"))
        bot.pack(fill=ctk.X, padx=6, pady=(0, 6))

        self._name_lbl = ctk.CTkLabel(
            bot,
            text="No item selected",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            text_color=("gray50", "gray60"),
            height=22,
        )
        self._name_lbl.pack(fill=ctk.X, padx=10, pady=(6, 0))

        self._detail_lbl = ctk.CTkLabel(
            bot,
            text="",
            font=("Segoe UI", 9),
            anchor="w",
            text_color=("gray50", "gray60"),
            height=18,
        )
        self._detail_lbl.pack(fill=ctk.X, padx=10, pady=(0, 2))

        btn_row = ctk.CTkFrame(bot, fg_color="transparent")
        btn_row.pack(fill=ctk.X, padx=10, pady=(2, 6))

        def _b(text, cmd, w=100):
            return ctk.CTkButton(btn_row, text=text, width=w, height=28, command=cmd)

        self._btn_remove = _b("Remove", self._do_remove, w=90)
        self._btn_qty = _b("Set Quantity", self._do_qty, w=100)
        self._btn_upgrade = _b("Set Upgrade", self._do_upgrade, w=100)
        self._btn_affinity = _b("Set Affinity", self._do_affinity, w=100)
        self._btn_aow = _b("Set AoW", self._do_aow, w=80)
        for b in (
            self._btn_remove,
            self._btn_qty,
            self._btn_upgrade,
            self._btn_affinity,
            self._btn_aow,
        ):
            b.pack(side=ctk.LEFT, padx=(0, 6))
            b.configure(state="disabled")

    # ---- data ----------------------------------------------------------------

    def _rebuild(self):
        # Category list in editor order, filtered to categories present in inventory
        inv_cats: set[str] = set()
        for row in self._editor._all_rows:
            if row[1] is not None:
                c = self._row_cat(row)
                if c:
                    inv_cats.add(c)

        try:
            # Use editor's visible_categories() which already applies cnv + co2 filter
            cats_ordered = self._editor._visible_categories()
        except Exception:
            cats_ordered = sorted(inv_cats)

        cats = [c for c in cats_ordered if c in inv_cats]
        self._cat_combo.configure(values=["All"] + cats)
        self._apply_filter()

    def _row_cat(self, row) -> str | None:
        try:
            from er_save_manager.data.item_database import get_item_database

            item = get_item_database().get_item_by_id(row[1])
            return item.category_name if item else None
        except Exception:
            return None

    # ---- filter / tabs -------------------------------------------------------

    def _on_sort_changed(self, value: str) -> None:
        self._sort_mode = value
        self._apply_filter()

    def _switch_tab(self, tab: str):
        self._tab = tab
        hi, lo = ("gray50", "gray25"), ("gray70", "gray35")
        self._btn_held.configure(fg_color=hi if tab == "held" else lo)
        self._btn_stor.configure(fg_color=hi if tab == "storage" else lo)
        self._sel_idx = None
        self._clear_bottom()
        self._apply_filter()

    def _on_cat_changed(self, value: str):
        self._cat_filter = value
        self._apply_filter()

    def _apply_filter(self):
        q = self._filter_var.get().lower().strip()
        self._visible = [
            row
            for row in self._editor._all_rows
            if row[1] is not None
            and row[2] == self._tab
            and (self._cat_filter == "All" or self._row_cat(row) == self._cat_filter)
            and (not q or q in row[0].lower())
        ]
        # Sort
        sort_mode = getattr(self, "_sort_mode", "Name A-Z")
        if sort_mode != "Default":

            def _sort_key(row):
                text = row[0]
                name = re.sub(r"^\s*\[[HS]K?\]\s*", "", text.split("|")[0]).strip()
                name = re.sub(r"\s*\+\d+$", "", name).strip()
                qty_m = re.search(r"Qty:\s*(\d+)", text)
                qty = int(qty_m.group(1)) if qty_m else 0
                return name.lower(), qty

            if "Qty" in sort_mode:
                self._visible.sort(
                    key=lambda r: _sort_key(r)[1], reverse=(sort_mode == "Qty \u2191")
                )
            else:
                self._visible.sort(
                    key=lambda r: _sort_key(r)[0], reverse=(sort_mode == "Name Z-A")
                )
        self._sel_idx = None
        self._clear_bottom()
        self._stop_loading()
        self._photos.clear()
        self._icons_loaded_to = 0
        gc.collect()
        self._draw_grid()

    # ---- canvas drawing ------------------------------------------------------

    def _cols(self) -> int:
        return max(1, (self._canvas.winfo_width() or 600) // _CELL_W)

    def _draw_grid(self):
        self._canvas.delete("all")
        cols = self._cols()
        total = len(self._visible)
        nrows = max(1, (total + cols - 1) // cols)
        w = self._canvas.winfo_width() or 600
        self._canvas.configure(scrollregion=(0, 0, w, nrows * _CELL_H + 4))

        try:
            from er_save_manager.data.item_database import get_item_database

            db = get_item_database()
        except Exception:
            db = None

        for idx, row in enumerate(self._visible):
            r, c = divmod(idx, cols)
            x0 = c * _CELL_W + _PAD
            y0 = r * _CELL_H + _PAD
            x1 = x0 + _CELL_W - _PAD * 2
            y1 = y0 + _CELL_H - _PAD * 2
            cx = (x0 + x1) // 2
            fill = self._sel_bg if idx == self._sel_idx else self._cell_bg

            # Background rectangle — tag "rect_N"
            self._canvas.create_rectangle(
                x0, y0, x1, y1, fill=fill, outline=self._cell_out, tags=f"rect_{idx}"
            )

            # Image placeholder rectangle — tag "imgbg_N"
            img_y0 = y0 + 6
            img_y1 = img_y0 + _IMG_SZ
            self._canvas.create_rectangle(
                cx - _IMG_SZ // 2,
                img_y0,
                cx + _IMG_SZ // 2,
                img_y1,
                fill=fill,
                outline="",
                tags=f"imgbg_{idx}",
            )

            # Name text — tag "text_N" (separate from rect so colour isn't clobbered)
            text, full_id = row[0], row[1]
            if db:
                item = db.get_item_by_id(full_id)
                raw_name = item.name if item else None
            else:
                raw_name = None
            if not raw_name:
                raw_name = re.sub(r"^\s*\[[HS]K?\]\s*", "", text.split("|")[0]).strip()
                raw_name = re.sub(r"\s*\+\d+$", "", raw_name).strip()

            _, suffix = _parse_cell_info(text, full_id)
            display = raw_name + suffix

            # Centre text in the space below the image
            text_area_mid = (img_y1 + y1) // 2
            self._canvas.create_text(
                cx,
                text_area_mid,
                text=display,
                fill=self._fg,
                font=("Segoe UI", 9),
                anchor="center",
                width=_CELL_W - 10,
                tags=f"text_{idx}",
            )

        self._load_icons(0)

    def _load_icons(self, start: int):
        if start >= len(self._visible) or start >= _MAX_IMG:
            self._icons_loaded_to = start
            return
        try:
            sf = self._editor.get_save_file()
            slot = sf.characters[self._editor.get_char_slot()] if sf else None
        except Exception:
            slot = None
        try:
            sf = self._editor.get_save_file()
            is_c = getattr(sf, "is_convergence", False) if sf else False
        except Exception:
            is_c = False
        aff_list = (
            self._editor._AFFINITIES_CNV if is_c else self._editor._AFFINITIES_VANILLA
        )
        affinity_names: dict[int, str] = dict(aff_list)
        cols = self._cols()
        end = min(start + _BATCH, len(self._visible), _MAX_IMG)
        for idx in range(start, end):
            row = self._visible[idx]
            full_id = row[1]
            gaitem_h = row[3] if len(row) > 3 else None
            aff_code = ((full_id & 0x0FFFFFFF) % 10000) // 100
            try:
                pil = _cell_icon(full_id, gaitem_h, slot, aff_code, affinity_names)
                if pil is None:
                    continue
                from PIL import Image, ImageTk

                pil = pil.convert("RGBA").resize((_IMG_SZ, _IMG_SZ), Image.LANCZOS)
                photo = ImageTk.PhotoImage(pil)
                self._photos.append(photo)
                r, c = divmod(idx, cols)
                cx = c * _CELL_W + _PAD + (_CELL_W - _PAD * 2) // 2
                img_y = r * _CELL_H + _PAD + 6 + _IMG_SZ // 2
                self._canvas.create_image(
                    cx, img_y, image=photo, anchor="center", tags=f"img_{idx}"
                )
            except Exception:
                pass
        self._icons_loaded_to = end
        if end < len(self._visible) and end < _MAX_IMG:
            self._load_job = self.after(_DELAY, lambda: self._load_icons(end))
        else:
            self._load_job = None

    def _on_scroll(self, units: int) -> None:
        self._canvas.yview_scroll(units, "units")
        # Resume icon loading if there are unloaded cells
        if self._load_job is None:
            next_idx = getattr(self, "_icons_loaded_to", 0)
            if next_idx < len(self._visible):
                self._load_job = self.after(80, lambda: self._load_icons(next_idx))

    def _stop_loading(self):
        if self._load_job:
            self.after_cancel(self._load_job)
            self._load_job = None

    # ---- click / selection ---------------------------------------------------

    def _on_click(self, event: tk.Event):
        cols = self._cols()
        cx = self._canvas.canvasx(event.x)
        cy = self._canvas.canvasy(event.y)
        c = int(cx // _CELL_W)
        r = int(cy // _CELL_H)
        idx = r * cols + c
        if 0 <= c < cols and 0 <= idx < len(self._visible):
            self._select(idx)

    def _select(self, idx: int):
        prev = self._sel_idx
        self._sel_idx = idx
        for i in (prev, idx):
            if i is None or i >= len(self._visible):
                continue
            fill = self._sel_bg if i == self._sel_idx else self._cell_bg
            try:
                # Only update rect and imgbg — never touch text colour
                self._canvas.itemconfigure(f"rect_{i}", fill=fill)
                self._canvas.itemconfigure(f"imgbg_{i}", fill=fill)
            except Exception:
                pass
        self._update_bottom(self._visible[idx])

    # ---- bottom panel --------------------------------------------------------

    def _clear_bottom(self):
        self._name_lbl.configure(
            text="No item selected", text_color=("gray50", "gray60")
        )
        self._detail_lbl.configure(text="")
        for b in (
            self._btn_remove,
            self._btn_qty,
            self._btn_upgrade,
            self._btn_affinity,
            self._btn_aow,
        ):
            b.configure(state="disabled")

    def _update_bottom(self, row: tuple):
        try:
            text, full_id, location = row[0], row[1], row[2]
            from er_save_manager.data.item_database import get_item_database

            db = get_item_database()
            # Weapons encode affinity+upgrade in last 4 digits - look up base ID
            if _is_weapon(full_id):
                base_id = (full_id & 0x0FFFFFFF) // 10000 * 10000
                item = db.get_item_by_id(full_id & 0xF0000000 | base_id)
            else:
                item = db.get_item_by_id(full_id)
            name = (
                item.name
                if item
                else re.sub(r"^\s*\[[HS]K?\]\s*", "", text.split("|")[0]).strip()
            )
            _, suffix = _parse_cell_info(text, full_id)
            self._name_lbl.configure(
                text=name + suffix, text_color=("gray15", "gray90")
            )

            # Detail: qty + location
            qty_m = re.search(r"Qty:\s*(\d+)", text)
            qty = int(qty_m.group(1)) if qty_m else 1
            self._detail_lbl.configure(
                text=f"Qty: {qty}  |  {location}", text_color=("gray40", "gray60")
            )

            # Button states — same validation rules as the main editor
            is_w = _is_weapon(full_id)
            reinf = getattr(item, "reinforcement", "standard") if item else "standard"
            aow_ok = is_w and (getattr(item, "aow_allowed", True) if item else False)

            # Qty: goods/ammo only; also check maxRepositoryNum cap
            qty_ok = False
            if not is_w and item:
                max_repo = getattr(
                    item, "max_repository_num", getattr(item, "max_num", 1)
                )
                cap = max_repo if location == "storage" else getattr(item, "max_num", 1)
                qty_ok = cap > 1
            elif is_w:
                # Ammo is a weapon-category item with max_arrow_quantity > 1
                qty_ok = getattr(item, "max_arrow_quantity", 1) > 1 if item else False

            self._btn_remove.configure(state="normal")
            self._btn_qty.configure(state="normal" if qty_ok else "disabled")
            self._btn_upgrade.configure(
                state="normal" if is_w and reinf != "none" else "disabled"
            )
            self._btn_affinity.configure(state="normal" if aow_ok else "disabled")
            self._btn_aow.configure(state="normal" if aow_ok else "disabled")
        except Exception:
            self._clear_bottom()

    # ---- actions -------------------------------------------------------------

    def _run(self, method: str):
        if self._sel_idx is None or self._sel_idx >= len(self._visible):
            return
        row = self._visible[self._sel_idx]
        gh = row[3] if len(row) > 3 else None
        self._editor._forced_selection = (row[1], row[2], gh)
        # Parent dialogs to this popup so they appear in front of it
        orig_parent = self._editor.parent
        self._editor.parent = self
        try:
            getattr(self._editor, method)()
        finally:
            self._editor._forced_selection = None
            self._editor.parent = orig_parent

    def _do_remove(self):
        self._run("remove_item")

    def _do_qty(self):
        self._run("set_quantity")

    def _do_upgrade(self):
        self._run("set_upgrade")

    def _do_affinity(self):
        self._run("set_affinity")

    def _do_aow(self):
        self._run("set_aow")

    # ---- live update ---------------------------------------------------------

    def _on_editor_changed(self):
        self._sel_idx = None
        self._stop_loading()
        self._photos.clear()
        gc.collect()
        self._clear_bottom()
        self._rebuild()

    def _on_close(self):
        self._stop_loading()
        try:
            self._editor._inventory_change_listeners.remove(self._on_editor_changed)
        except ValueError:
            pass
        self.destroy()
