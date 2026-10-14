"""Visual inventory browser popup."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.ui import palette
from er_save_manager.ui.editors.inventory_editor import (
    INVENTORY_SORT_MODES,
    sort_inventory_rows,
)
from er_save_manager.ui.utils import (
    center_window,
    debounced_trace,
    patch_combo_scroll,
)
from er_save_manager.ui.virtual_grid import GridEntry, VirtualIconGrid

if TYPE_CHECKING:
    from er_save_manager.ui.editors.inventory_editor import InventoryEditor


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


def _center_over(window, parent, w=None, h=None, *, top=False) -> None:
    """Center window over parent. Pass w/h explicitly to avoid pre-map size queries."""
    center_window(window, w, h, parent=parent, align_top=top)


class VisualInventoryBrowser(ctk.CTkToplevel):
    """Icon grid of the held or storage inventory with the editor's actions."""

    def __init__(self, parent, editor: InventoryEditor):
        super().__init__(parent)
        self._editor = editor
        self._tab = "held"
        self._cat_filter = "All"
        self._visible: list[tuple] = []
        self._sel_idx: int | None = None

        self.title("Visual Inventory")
        self.geometry("760x680")
        self.minsize(500, 400)
        self.resizable(True, True)
        self.transient(parent)

        self._build_ui()
        self._rebuild()
        self.attributes("-alpha", 0)
        self.update_idletasks()
        _center_over(self, parent, 760, 680, top=True)
        self.attributes("-alpha", 1)
        # Non-modal by design: the icon browser may be open at the same time
        self.after(100, self.raise_window)
        self._editor._inventory_change_listeners.append(self._on_editor_changed)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

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
        patch_combo_scroll(self._cat_combo)

        ctk.CTkButton(
            top,
            text="Batch Remove Category",
            width=150,
            height=28,
            fg_color=palette.BLUE,
            hover_color=palette.BLUE_HOVER,
            text_color=palette.ON_BLUE,
            command=self._do_batch_remove,
        ).pack(side=ctk.RIGHT, padx=(12, 0))

        self._filter_var = ctk.StringVar()
        debounced_trace(self, self._filter_var, self._apply_filter)
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
            values=INVENTORY_SORT_MODES,
            command=self._on_sort_changed,
        ).pack(side=ctk.LEFT, padx=(4, 0))

        ctk.CTkButton(
            row2,
            text="Batch Upgrade Weapons",
            width=150,
            height=28,
            fg_color=palette.BLUE,
            hover_color=palette.BLUE_HOVER,
            text_color=palette.ON_BLUE,
            command=self._do_batch_upgrade,
        ).pack(side=ctk.RIGHT, padx=(12, 0))

        self._grid = VirtualIconGrid(self, self._on_grid_select)
        self._grid.pack(fill=ctk.BOTH, expand=True, padx=6, pady=(4, 4))

        # Fixed-height bottom panel: two label rows
        bot = ctk.CTkFrame(self, fg_color=("gray88", "gray18"), corner_radius=8)
        bot.pack(fill=ctk.X, padx=6, pady=(0, 8))

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

            db = get_item_database()
            full_id = row[1]
            item = db.get_item_by_id(full_id)
            if item is None and (full_id & 0xF0000000) == 0x00000000:
                # Infused/upgraded weapons encode affinity+upgrade in last 4 digits
                base_id = (full_id & 0x0FFFFFFF) // 10000 * 10000
                item = db.get_item_by_id(base_id)
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
        sort_mode = getattr(self, "_sort_mode", "Name A-Z")
        self._visible = sort_inventory_rows(self._visible, sort_mode)
        self._sel_idx = None
        self._clear_bottom()
        self._grid.set_entries(self._entries())

    def _entries(self) -> list[GridEntry]:
        try:
            from er_save_manager.data.item_database import get_item_database

            db = get_item_database()
        except Exception:
            db = None
        try:
            sf = self._editor.get_save_file()
            slot = sf.characters[self._editor.get_char_slot()] if sf else None
            is_c = getattr(sf, "is_convergence", False) if sf else False
        except Exception:
            slot, is_c = None, False
        aff_list = (
            self._editor._AFFINITIES_CNV if is_c else self._editor._AFFINITIES_VANILLA
        )
        affinity_names: dict[int, str] = dict(aff_list)

        entries = []
        for idx, row in enumerate(self._visible):
            text, full_id = row[0], row[1]
            item = db.get_item_by_id(full_id) if db else None
            raw_name = item.name if item else None
            if not raw_name:
                raw_name = re.sub(r"^\s*\[[HS]K?\]\s*", "", text.split("|")[0]).strip()
                raw_name = re.sub(r"\s*\+\d+$", "", raw_name).strip()
            _, suffix = _parse_cell_info(text, full_id)
            gaitem_h = row[3] if len(row) > 3 else None
            aff_code = ((full_id & 0x0FFFFFFF) % 10000) // 100
            entries.append(
                GridEntry(
                    idx,
                    raw_name + suffix,
                    text.lower(),
                    lambda f=full_id, g=gaitem_h, a=aff_code: _cell_icon(
                        f, g, slot, a, affinity_names
                    ),
                )
            )
        return entries

    # ---- click / selection ---------------------------------------------------

    def _on_grid_select(self, keys: list):
        if not keys:
            return
        self._sel_idx = keys[0]
        self._update_bottom(self._visible[self._sel_idx])

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
            sf = self._editor.get_save_file()
            is_cnv = bool(getattr(sf, "is_convergence", False)) if sf else False
            # Weapons encode affinity+upgrade in last 4 digits - look up base ID
            if _is_weapon(full_id):
                base_id = (full_id & 0x0FFFFFFF) // 10000 * 10000
                item = db.get_item_by_id(full_id & 0xF0000000 | base_id, is_cnv)
            else:
                item = db.get_item_by_id(full_id, is_cnv)
            name = (
                item.name
                if item
                else re.sub(r"^\s*\[[HS]K?\]\s*", "", text.split("|")[0]).strip()
            )
            _, suffix = _parse_cell_info(text, full_id)
            self._name_lbl.configure(
                text=name + suffix, text_color=("gray15", "gray90")
            )

            qty_m = re.search(r"Qty:\s*(\d+)", text)
            qty = int(qty_m.group(1)) if qty_m else 1
            self._detail_lbl.configure(
                text=f"Qty: {qty}  |  {location}", text_color=("gray40", "gray60")
            )

            # Button states - same validation rules as the main editor
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

    def _do_batch_remove(self):
        self._editor.batch_remove_category(
            self._cat_filter, self._tab, parent_window=self
        )

    def _do_batch_upgrade(self):
        self._editor.batch_upgrade_weapons(
            self._cat_filter, self._tab, parent_window=self
        )

    # ---- live update ---------------------------------------------------------

    def _on_editor_changed(self):
        self._sel_idx = None
        self._clear_bottom()
        self._rebuild()

    def _on_close(self):
        try:
            self._editor._inventory_change_listeners.remove(self._on_editor_changed)
        except ValueError:
            pass
        self.destroy()
