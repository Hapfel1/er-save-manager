"""
Inventory Editor - add, remove, and set quantities using inventory_ops.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

# ---- item-id helpers --------------------------------------------------------


def _decode_inv_item(inv_item, gaitem_map: dict) -> tuple[int, int]:
    """
    Return (full_item_id, upgrade_level) for an inventory item.

    For gaitem items (weapons/armor/gems) the full_id is read from the gaitem
    entry. For direct-handle items (goods/talismans, 0xB0 prefix) the full_id
    is reconstructed from the handle's lower 24 bits.
    """
    handle = inv_item.gaitem_handle
    gaitem = gaitem_map.get(handle)
    if gaitem:
        prefix = gaitem.gaitem_handle & 0xF0000000
        if prefix == 0x80000000:
            # Weapon: item_id = base_id + upgrade, no category bits (0x00 = weapon)
            upgrade = gaitem.item_id % 100
            return (gaitem.item_id // 100) * 100, upgrade
        # Armor (0x90) and gem/AoW (0xC0): item_id already carries category bits
        return gaitem.item_id, 0

    # Direct handle: 0xA0 prefix = talisman (game-native encoding)
    if handle & 0xF0000000 == 0xA0000000:
        return 0x20000000 | (handle & 0x00FFFFFF), 0

    # Direct handle: 0xB0 prefix encodes goods or talismans (inventory_ops encoding)
    if handle & 0xF0000000 == 0xB0000000:
        base = handle & 0x00FFFFFF
        return 0x40000000 | base, 0  # treat as goods; name lookup will clarify

    return handle, 0


def _item_name(full_item_id: int, upgrade: int = 0) -> str:
    """Look up item name, falling back to talisman category on goods miss."""
    from er_save_manager.data.item_database import get_item_database, get_item_name

    name = get_item_name(full_item_id, upgrade)
    if name.startswith("Unknown") and (full_item_id & 0xF0000000) == 0x40000000:
        # B0 handles cannot distinguish goods from talismans; try talisman category
        alt = 0x20000000 | (full_item_id & 0x0FFFFFFF)
        alt_name = get_item_database().get_item_by_id(alt)
        if alt_name:
            return alt_name.name
    return name


# ---- editor -----------------------------------------------------------------


class InventoryEditor:
    """Inventory editor: browse, add, remove, and adjust item quantities."""

    # ---- constants ----------------------------------------------------------

    _AFFINITIES: list[tuple[int, str]] = [
        (0, "Standard"),
        (1, "Heavy"),
        (2, "Keen"),
        (3, "Quality"),
        (4, "Fire"),
        (5, "Flame Art"),
        (6, "Lightning"),
        (7, "Sacred"),
        (8, "Magic"),
        (9, "Cold"),
        (10, "Poison"),
        (11, "Blood"),
        (12, "Occult"),
        # Convergence mod affinities
        (13, "Frenzy"),
        (14, "Death"),
        (15, "Godslayer"),
        (16, "Frost"),
        (17, "Aberrant"),
        (18, "Bloodflame"),
        (19, "Rotten"),
        (20, "Storm"),
        (21, "Psionic"),
    ]
    _AFFINITY_BY_CODE: dict[int, str] = dict(_AFFINITIES)
    _AFFINITY_NAMES: list[str] = [name for _, name in _AFFINITIES]

    _SEAMLESS_CATS = {"Seamless Co-op Items"}
    _CONVERGENCE_CATS = {
        "Convergence Melee Weapons",
        "Convergence Reworked Weapons",
        "Convergence Shields",
        "Convergence Armor",
        "Convergence Spell Tools",
        "Convergence Keystones and Remnants",
        "Convergence Stones",
        "Convergence Runes",
        "Convergence Notes",
        "Convergence Remembrances",
        "Convergence Consumables",
        "Convergence Crystal Tears",
        "Convergence Gems",
    }

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_char_slot_callback,
        get_save_path_callback,
        ensure_mutable_callback,
        on_inventory_changed=None,
    ):
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_char_slot = get_char_slot_callback
        self.get_save_path = get_save_path_callback
        self.ensure_mutable = ensure_mutable_callback
        self._on_inventory_changed = on_inventory_changed

        self.selected_item = None
        # All parsed rows before search filter: (text, full_id, location) - header rows have None full_id
        self._all_rows: list[tuple[str, int | None, str | None]] = []
        # Rows currently visible in listbox (parallel index)
        self._item_data: list[tuple[int, str] | None] = []

        # Add-panel widgets
        self.inv_quantity_var: ctk.IntVar | None = None
        self._quantity_entry: ctk.CTkEntry | None = None
        self._current_max_num: int = 1
        self.inv_upgrade_var: ctk.StringVar | None = None
        self.inv_affinity_var: ctk.StringVar | None = None
        self.inv_location_var: ctk.StringVar | None = None
        self._upgrade_combo: ctk.CTkComboBox | None = None
        self._affinity_combo: ctk.CTkComboBox | None = None
        self._location_combo: ctk.CTkComboBox | None = None
        self._aow_pick_btn: ctk.CTkButton | None = None
        self._aow_clear_btn: ctk.CTkButton | None = None
        self._aow_label: ctk.CTkLabel | None = None
        self.inv_aow_var: ctk.StringVar | None = None
        self._selected_gem_id: int = 0
        self._selected_item_label: ctk.CTkLabel | None = None

        # Browser widgets
        self._search_var: ctk.StringVar | None = None
        self._search_cat_var: ctk.StringVar | None = None
        self._search_cat_combo: ctk.CTkComboBox | None = None
        self._results_listbox: tk.Listbox | None = None
        self._results_items: list = []

        # Inventory widgets
        self.inventory_listbox: tk.Listbox | None = None
        self.inv_filter_var: ctk.StringVar | None = None
        self._inv_search_var: ctk.StringVar | None = None

        self.frame: ctk.CTkFrame | None = None

    # ---- UI setup -----------------------------------------------------------

    def setup_ui(self):
        self.frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.frame.pack(fill=ctk.BOTH, expand=True)

        pane = tk.PanedWindow(
            self.frame,
            orient=tk.HORIZONTAL,
            sashwidth=6,
            sashrelief=tk.FLAT,
            bg="#2b2b2b",
        )
        pane.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        left = ctk.CTkFrame(pane, fg_color=("gray88", "gray18"), corner_radius=8)
        right = ctk.CTkFrame(pane, fg_color=("gray88", "gray18"), corner_radius=8)

        pane.add(left, minsize=340, width=420)
        pane.add(right, minsize=340)

        self._build_browser_panel(left)
        self._build_inventory_panel(right)

    # ---- left panel: item browser -------------------------------------------

    def _build_browser_panel(self, parent: ctk.CTkFrame):
        ctk.CTkLabel(
            parent,
            text="Add Item",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor=ctk.W, padx=12, pady=(10, 4))

        # Search bar row
        search_row = ctk.CTkFrame(parent, fg_color="transparent")
        search_row.pack(fill=ctk.X, padx=10, pady=(0, 4))

        ctk.CTkLabel(search_row, text="Search:", width=54).pack(side=ctk.LEFT)
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._search_items())
        ctk.CTkEntry(search_row, textvariable=self._search_var, width=160).pack(
            side=ctk.LEFT, padx=(0, 6)
        )
        self._search_cat_var = ctk.StringVar(value="All")
        self._search_cat_combo = ctk.CTkComboBox(
            search_row,
            variable=self._search_cat_var,
            values=["All"],
            width=150,
            command=lambda _e=None: self._search_items(),
        )
        self._search_cat_combo.pack(side=ctk.LEFT)
        self._populate_search_categories()

        # Results listbox
        lb_frame = ctk.CTkFrame(parent, fg_color=("gray82", "gray14"), corner_radius=6)
        lb_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=(0, 4))

        mode = ctk.get_appearance_mode()
        lb_bg = "#1a1a24" if mode == "Dark" else "#f0f0f0"
        lb_fg = "#d4d4e8" if mode == "Dark" else "#111111"
        lb_sel = "#7c4dac" if mode == "Dark" else "#b8a0d0"

        sb = tk.Scrollbar(lb_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._results_listbox = tk.Listbox(
            lb_frame,
            yscrollcommand=sb.set,
            font=("Consolas", 9),
            height=5,
            bg=lb_bg,
            fg=lb_fg,
            selectbackground=lb_sel,
            relief=tk.FLAT,
            borderwidth=0,
            activestyle="none",
        )
        self._results_listbox.pack(
            side=tk.LEFT, fill=ctk.BOTH, expand=True, padx=2, pady=2
        )
        sb.config(command=self._results_listbox.yview)
        bind_mousewheel(self._results_listbox)
        self._results_listbox.bind("<<ListboxSelect>>", self._on_result_select)

        # Selected item label
        self._selected_item_label = ctk.CTkLabel(
            parent,
            text="No item selected",
            text_color=("gray50", "gray60"),
            font=("Segoe UI", 10),
            anchor="w",
        )
        self._selected_item_label.pack(fill=ctk.X, padx=12, pady=(0, 6))

        sep = ctk.CTkFrame(parent, height=1, fg_color=("gray75", "gray30"))
        sep.pack(fill=ctk.X, padx=10, pady=(0, 8))

        # Options grid packed top-down after the sep so all rows are always visible
        opts = ctk.CTkFrame(parent, fg_color="transparent")
        opts.pack(fill=ctk.X, padx=10, pady=(0, 4))
        opts.columnconfigure(1, weight=1)
        opts.columnconfigure(3, weight=1)

        ctk.CTkLabel(opts, text="Quantity:", anchor="w").grid(
            row=0, column=0, sticky=ctk.W, padx=(0, 6), pady=4
        )
        self.inv_quantity_var = ctk.IntVar(value=1)
        self._quantity_entry = ctk.CTkEntry(
            opts, textvariable=self.inv_quantity_var, width=70
        )
        self._quantity_entry.grid(row=0, column=1, sticky=ctk.W, pady=4)

        ctk.CTkLabel(opts, text="Upgrade:", anchor="w").grid(
            row=0, column=2, sticky=ctk.W, padx=(14, 6), pady=4
        )
        self.inv_upgrade_var = ctk.StringVar(value="0")
        self._upgrade_combo = ctk.CTkComboBox(
            opts,
            variable=self.inv_upgrade_var,
            values=["0"],
            width=70,
            state="disabled",
        )
        self._upgrade_combo.grid(row=0, column=3, sticky=ctk.W, pady=4)

        ctk.CTkLabel(opts, text="Affinity:", anchor="w").grid(
            row=1, column=0, sticky=ctk.W, padx=(0, 6), pady=4
        )
        self.inv_affinity_var = ctk.StringVar(value="Standard")
        self._affinity_combo = ctk.CTkComboBox(
            opts,
            variable=self.inv_affinity_var,
            values=self._AFFINITY_NAMES,
            width=140,
            state="disabled",
        )
        self._affinity_combo.grid(row=1, column=1, sticky=ctk.W, pady=4)

        ctk.CTkLabel(opts, text="Location:", anchor="w").grid(
            row=1, column=2, sticky=ctk.W, padx=(14, 6), pady=4
        )
        self.inv_location_var = ctk.StringVar(value="held")
        self._location_combo = ctk.CTkComboBox(
            opts,
            variable=self.inv_location_var,
            values=["held", "storage"],
            width=120,
        )
        self._location_combo.grid(row=1, column=3, sticky=ctk.W, pady=4)

        # AoW row (row 2) - weapons only
        ctk.CTkLabel(opts, text="Ash of War:", anchor="w").grid(
            row=2, column=0, sticky=ctk.W, padx=(0, 6), pady=4
        )
        self.inv_aow_var = ctk.StringVar(value="None")
        self._aow_label = ctk.CTkLabel(
            opts,
            textvariable=self.inv_aow_var,
            text_color=("gray50", "gray60"),
            width=140,
            anchor="w",
        )
        self._aow_label.grid(row=2, column=1, sticky=ctk.W, pady=4)
        self._aow_pick_btn = ctk.CTkButton(
            opts,
            text="Pick...",
            width=60,
            height=24,
            command=self._pick_aow,
            state="disabled",
        )
        self._aow_pick_btn.grid(row=2, column=2, sticky=ctk.W, pady=4)
        self._aow_clear_btn = ctk.CTkButton(
            opts,
            text="Clear",
            width=55,
            height=24,
            command=self._clear_aow,
            state="disabled",
            fg_color=("gray70", "gray35"),
        )
        self._aow_clear_btn.grid(row=2, column=3, sticky=ctk.W, pady=4)
        self._selected_gem_id: int = 0

        ctk.CTkButton(
            parent,
            text="Add Item",
            command=self.add_item,
            height=34,
            font=("Segoe UI", 11, "bold"),
        ).pack(fill=ctk.X, padx=10, pady=(4, 10))

    # ---- right panel: current inventory -------------------------------------

    def _build_inventory_panel(self, parent: ctk.CTkFrame):
        # Header row: title + filter
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill=ctk.X, padx=10, pady=(10, 4))

        ctk.CTkLabel(
            header,
            text="Current Inventory",
            font=("Segoe UI", 13, "bold"),
        ).pack(side=ctk.LEFT)

        self.inv_filter_var = ctk.StringVar(value="All")
        ctk.CTkComboBox(
            header,
            variable=self.inv_filter_var,
            values=["All", "Held", "Storage", "Key Items"],
            width=120,
            command=lambda _e=None: self.refresh_inventory(),
        ).pack(side=ctk.RIGHT, padx=(6, 0))
        ctk.CTkLabel(header, text="Show:").pack(side=ctk.RIGHT)

        # Inventory search bar
        search_row = ctk.CTkFrame(parent, fg_color="transparent")
        search_row.pack(fill=ctk.X, padx=10, pady=(0, 4))

        ctk.CTkLabel(search_row, text="Filter:", width=42).pack(side=ctk.LEFT)
        self._inv_search_var = ctk.StringVar()
        self._inv_search_var.trace_add("write", lambda *_: self._apply_inv_filter())
        ctk.CTkEntry(
            search_row,
            textvariable=self._inv_search_var,
            placeholder_text="Filter items...",
            width=220,
        ).pack(side=ctk.LEFT, padx=(0, 6))
        ctk.CTkButton(
            search_row,
            text="Clear",
            width=60,
            height=28,
            command=lambda: self._inv_search_var.set(""),
        ).pack(side=ctk.LEFT)

        # Inventory listbox
        lb_frame = ctk.CTkFrame(parent, fg_color=("gray82", "gray14"), corner_radius=6)
        lb_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=(0, 6))

        mode = ctk.get_appearance_mode()
        lb_bg = "#1a1a24" if mode == "Dark" else "#f0f0f0"
        lb_fg = "#d4d4e8" if mode == "Dark" else "#111111"
        lb_sel = "#7c4dac" if mode == "Dark" else "#b8a0d0"

        sb = tk.Scrollbar(lb_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.inventory_listbox = tk.Listbox(
            lb_frame,
            yscrollcommand=sb.set,
            font=("Consolas", 10),
            bg=lb_bg,
            fg=lb_fg,
            selectbackground=lb_sel,
            relief=tk.FLAT,
            borderwidth=0,
            activestyle="none",
        )
        self.inventory_listbox.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2
        )
        sb.config(command=self.inventory_listbox.yview)
        bind_mousewheel(self.inventory_listbox)

        # Action bar
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill=ctk.X, padx=10, pady=(0, 10))

        ctk.CTkButton(
            actions,
            text="Remove Selected",
            command=self.remove_item,
            width=150,
        ).pack(side=ctk.LEFT, padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="Set Quantity",
            command=self.set_quantity,
            width=120,
        ).pack(side=ctk.LEFT, padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="Refresh",
            command=self.refresh_inventory,
            width=90,
        ).pack(side=ctk.LEFT)

    # ---- search browser helpers ---------------------------------------------

    def _visible_categories(self) -> list[str]:
        """Return category list filtered by save file type."""
        try:
            from er_save_manager.data.item_database import get_categories

            all_cats = get_categories()
        except Exception:
            return []

        save_path = str(self.get_save_path() or "")
        is_co2 = ".co2" in save_path
        is_cnv = ".cnv" in save_path

        return [
            c
            for c in all_cats
            if (c not in self._SEAMLESS_CATS or is_co2)
            and (c not in self._CONVERGENCE_CATS or is_cnv)
        ]

    def _populate_search_categories(self):
        cats = ["All"] + self._visible_categories()
        self._search_cat_combo.configure(values=cats)
        if self._search_cat_var.get() not in cats:
            self._search_cat_var.set("All")

    def _search_items(self):
        if self._results_listbox is None:
            return
        try:
            from er_save_manager.data.item_database import get_item_database

            db = get_item_database()
            query = self._search_var.get().strip()
            cat = self._search_cat_var.get()

            if not query and cat == "All":
                self._results_items = []
                self._results_listbox.delete(0, tk.END)
                return

            if cat == "All":
                results = db.search_items(query) if query else []
            else:
                items = db.get_items_by_category(cat)
                results = (
                    [i for i in items if query.lower() in i.name.lower()]
                    if query
                    else items
                )

            self._results_items = results[:200]
            self._results_listbox.delete(0, tk.END)
            for item in self._results_items:
                self._results_listbox.insert(tk.END, item.name)
        except Exception:
            pass

    def _on_result_select(self, _event=None):
        sel = self._results_listbox.curselection()
        if not sel or sel[0] >= len(self._results_items):
            return
        self.selected_item = self._results_items[sel[0]]
        self._selected_item_label.configure(
            text=f"Selected: {self.selected_item.name}",
            text_color=("#7c4dac", "#c084fc"),
        )

        is_weapon = self.selected_item.category == 0x00000000
        is_armor = self.selected_item.category == 0x10000000
        is_gem = self.selected_item.category == 0x80000000
        is_ashes = self.selected_item.category_name in ("Ashes", "DLC Ashes")
        is_upgradable = is_weapon or is_ashes
        reinforcement = (
            getattr(self.selected_item, "reinforcement", "standard")
            if is_weapon
            else "standard"
        )
        aow_allowed = is_weapon and getattr(self.selected_item, "aow_allowed", True)
        affinity_allowed = is_weapon and reinforcement == "standard" and aow_allowed

        # Gaitem items (weapon/armor/gem) are always qty 1, except ammo which uses max_arrow_quantity
        if self._quantity_entry:
            max_arrow = getattr(self.selected_item, "max_arrow_quantity", 1)
            is_ammo = is_weapon and max_arrow > 1
            if (is_weapon and not is_ammo) or is_armor or is_gem:
                self.inv_quantity_var.set(1)
                self._quantity_entry.configure(state="disabled")
                self._current_max_num = 1
            else:
                max_num = (
                    max_arrow if is_ammo else getattr(self.selected_item, "max_num", 1)
                )
                self._current_max_num = max_num
                self.inv_quantity_var.set(1)
                self._quantity_entry.configure(
                    state="normal" if max_num > 1 else "disabled"
                )

        if self._upgrade_combo:
            if is_upgradable:
                if is_ashes:
                    cap = 10
                else:
                    save_path = self.get_save_path() or ""
                    is_convergence_save = ".cnv" in str(save_path).lower()
                    explicit_cap = getattr(self.selected_item, "max_upgrade", -1)
                    if explicit_cap >= 0:
                        cap = explicit_cap
                    elif is_convergence_save and reinforcement in (
                        "standard",
                        "somber",
                    ):
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
                self.inv_upgrade_var.set("0")
            else:
                self._upgrade_combo.configure(values=["0"], state="disabled")
                self.inv_upgrade_var.set("0")

        save_path = self.get_save_path() or ""
        is_convergence_save = ".cnv" in str(save_path).lower()

        if self._affinity_combo:
            if affinity_allowed:
                affinity_values = (
                    self._AFFINITY_NAMES
                    if is_convergence_save
                    else self._AFFINITY_NAMES[:13]  # base 13 only
                )
                self._affinity_combo.configure(values=affinity_values, state="normal")
                self.inv_affinity_var.set("Standard")
            else:
                self._affinity_combo.configure(state="disabled")
                self.inv_affinity_var.set("Standard")

        aow_state = "normal" if aow_allowed else "disabled"
        if self._aow_pick_btn:
            self._aow_pick_btn.configure(state=aow_state)
            self._aow_clear_btn.configure(state=aow_state)
        if not aow_allowed:
            self._clear_aow()

        if self._location_combo:
            self._location_combo.configure(state="normal")

    def _pick_aow(self):
        """Open a gem picker dialog and store the selected gem's full_id."""
        import tkinter as tk

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Select Ash of War")
        dialog.geometry("380x400")
        dialog.resizable(False, True)
        dialog.transient(self.parent)
        dialog.attributes("-alpha", 0)
        dialog.update_idletasks()
        dialog.attributes("-alpha", 1)
        dialog.grab_set()

        mode = ctk.get_appearance_mode()
        lb_bg = "#1a1a24" if mode == "Dark" else "#f0f0f0"
        lb_fg = "#d4d4e8" if mode == "Dark" else "#111111"
        lb_sel = "#7c4dac" if mode == "Dark" else "#b8a0d0"

        search_var = ctk.StringVar()
        ctk.CTkLabel(dialog, text="Search:").pack(anchor="w", padx=10, pady=(10, 0))
        ctk.CTkEntry(dialog, textvariable=search_var, width=340).pack(
            padx=10, pady=(0, 4)
        )

        lb_frame = ctk.CTkFrame(dialog, fg_color=("gray82", "gray14"), corner_radius=6)
        lb_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=4)
        sb = tk.Scrollbar(lb_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb = tk.Listbox(
            lb_frame,
            yscrollcommand=sb.set,
            font=("Consolas", 10),
            bg=lb_bg,
            fg=lb_fg,
            selectbackground=lb_sel,
            relief=tk.FLAT,
            borderwidth=0,
            activestyle="none",
        )
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        sb.config(command=lb.yview)
        bind_mousewheel(lb)

        gem_items: list = []

        # Gems compatible with the currently selected weapon
        wep_col = (
            getattr(self.selected_item, "wep_type_col", "")
            if self.selected_item
            else ""
        )
        save_path_str = str(self.get_save_path() or "").lower()
        is_convergence_save = ".cnv" in save_path_str

        def _load():
            try:
                from er_save_manager.data.item_database import get_item_database

                db = get_item_database()
                cats = ["Gems", "DLC Gems"]
                if is_convergence_save:
                    cats.append("Convergence Gems")
                gems = []
                for cat in cats:
                    gems += db.get_items_by_category(cat)
                if wep_col:
                    gems = [
                        g
                        for g in gems
                        if not g.compatible_wep_types
                        or wep_col in g.compatible_wep_types
                    ]
                return gems
            except Exception:
                return []

        all_gems = _load()

        def _filter(*_):
            q = search_var.get().lower().strip()
            gem_items.clear()
            gem_items.extend(g for g in all_gems if not q or q in g.name.lower())
            lb.delete(0, tk.END)
            for g in gem_items[:200]:
                lb.insert(tk.END, g.name)

        search_var.trace_add("write", _filter)
        _filter()

        def _confirm():
            sel = lb.curselection()
            if not sel or sel[0] >= len(gem_items):
                return
            item = gem_items[sel[0]]
            self._selected_gem_id = 0x80000000 | item.id
            if self.inv_aow_var:
                self.inv_aow_var.set(item.name)
                if self._aow_label:
                    self._aow_label.configure(text_color=("#7c4dac", "#c084fc"))
            # Update affinity combo to show only affinities this AoW supports
            if self._affinity_combo and item.allowed_affinities:
                self._affinity_combo.configure(values=item.allowed_affinities)
                default = item.default_affinity or item.allowed_affinities[0]
                self.inv_affinity_var.set(default)
            dialog.destroy()

        lb.bind("<Double-Button-1>", lambda _e: _confirm())

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill=ctk.X, padx=10, pady=(4, 10))
        ctk.CTkButton(btn_row, text="Select", command=_confirm, width=100).pack(
            side=ctk.LEFT, padx=(0, 6)
        )
        ctk.CTkButton(btn_row, text="Cancel", command=dialog.destroy, width=80).pack(
            side=ctk.RIGHT
        )

    def _clear_aow(self):
        self._selected_gem_id = 0
        if self.inv_aow_var:
            self.inv_aow_var.set("None")
        if self._aow_label:
            self._aow_label.configure(text_color=("gray50", "gray60"))
        if self._affinity_combo and self.inv_affinity_var:
            is_convergence_save = ".cnv" in str(self.get_save_path() or "").lower()
            values = (
                self._AFFINITY_NAMES
                if is_convergence_save
                else self._AFFINITY_NAMES[:13]
            )
            self._affinity_combo.configure(values=values)
            self.inv_affinity_var.set("Standard")

    # ---- inventory display --------------------------------------------------

    def refresh_inventory(self):
        self._populate_search_categories()
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first.", parent=self.parent
            )
            return

        slot_idx = self.get_char_slot()
        try:
            slot = save_file.characters[slot_idx]
            if not slot or slot.is_empty():
                CTkMessageBox.showwarning(
                    "Empty Slot", f"Slot {slot_idx + 1} is empty.", parent=self.parent
                )
                return

            gaitem_map = {}
            for g in getattr(slot, "gaitem_map", []):
                if g.gaitem_handle not in (0, 0xFFFFFFFF):
                    gaitem_map[g.gaitem_handle] = g

            filt = self.inv_filter_var.get() if self.inv_filter_var else "All"
            self._all_rows = []

            if filt in ("All", "Held") and hasattr(slot, "inventory_held"):
                self._collect_section(
                    "HELD INVENTORY",
                    slot.inventory_held.common_items,
                    gaitem_map,
                    "held",
                    key=False,
                )
            if filt in ("All", "Key Items") and hasattr(slot, "inventory_held"):
                self._collect_section(
                    "KEY ITEMS (HELD)",
                    slot.inventory_held.key_items,
                    gaitem_map,
                    "held",
                    key=True,
                )
            if filt in ("All", "Storage") and hasattr(slot, "inventory_storage_box"):
                self._collect_section(
                    "STORAGE BOX",
                    slot.inventory_storage_box.common_items,
                    gaitem_map,
                    "storage",
                    key=False,
                )
                self._collect_section(
                    "KEY ITEMS (STORAGE)",
                    slot.inventory_storage_box.key_items,
                    gaitem_map,
                    "storage",
                    key=True,
                )

            self._apply_inv_filter()

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to refresh inventory:\n{e}", parent=self.parent
            )

    def _collect_section(self, header, items, gaitem_map, location, key):
        """Parse items into _all_rows without touching the listbox."""
        rows: list[tuple[str, int, str]] = []

        for inv_item in items:
            if inv_item.gaitem_handle == 0 or inv_item.quantity == 0:
                continue
            full_id, upgrade = _decode_inv_item(inv_item, gaitem_map)
            name = _item_name(full_id, upgrade)
            if not name:
                continue

            cat = full_id & 0xF0000000
            # Weapons: get_item_name already appends +N
            suffix = f" +{upgrade}" if upgrade > 0 and cat != 0x00000000 else ""
            affinity_label = ""
            if cat == 0x00000000:
                affinity_code = (full_id // 100) % 100
                if affinity_code != 0:
                    affinity_label = (
                        f" [{self._AFFINITY_BY_CODE.get(affinity_code, affinity_code)}]"
                    )

            loc_tag = "K" if key else ""
            text = (
                f"  [{location[0].upper()}{loc_tag}] "
                f"{name}{suffix}{affinity_label}"
                f"  |  Qty: {inv_item.quantity}"
            )
            rows.append((text, full_id, location))

        count = len(rows)
        label = "item" if count == 1 else "items"
        self._all_rows.append((f"  {header}  ({count} {label})", None, None))
        self._all_rows.extend(rows)

    def _apply_inv_filter(self):
        """Re-render the listbox from _all_rows, applying the text filter."""
        if self.inventory_listbox is None:
            return

        query = (
            (self._inv_search_var.get() if self._inv_search_var else "").lower().strip()
        )
        self.inventory_listbox.delete(0, tk.END)
        self._item_data = []

        mode = ctk.get_appearance_mode()
        hdr_fg = "#9d7fc4" if mode == "Dark" else "#6a3fa0"

        for text, full_id, location in self._all_rows:
            if full_id is None:
                # Section header - always visible
                self.inventory_listbox.insert(tk.END, text)
                self.inventory_listbox.itemconfig(tk.END, foreground=hdr_fg)
                self._item_data.append(None)
            else:
                if query and query not in text.lower():
                    continue
                self.inventory_listbox.insert(tk.END, text)
                self._item_data.append((full_id, location))

    # ---- operations ---------------------------------------------------------

    def add_item(self):
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Load a save file first.", parent=self.parent
            )
            return
        if not self.selected_item:
            CTkMessageBox.showwarning(
                "No Item", "Select an item from the browser first.", parent=self.parent
            )
            return

        slot_idx = self.get_char_slot()
        full_id = self.selected_item.full_id
        cat = full_id & 0xF0000000
        is_weapon = cat == 0x00000000
        is_armor = cat == 0x10000000
        is_gem = cat == 0x80000000
        is_ashes = self.selected_item.category_name in ("Ashes", "DLC Ashes")

        try:
            qty = int(self.inv_quantity_var.get())
            upg = int(self.inv_upgrade_var.get()) if (is_weapon or is_ashes) else 0
        except (ValueError, tk.TclError):
            qty = 1
            upg = 0

        if is_weapon or is_armor or is_gem:
            max_arrow = getattr(self.selected_item, "max_arrow_quantity", 1)
            is_ammo = is_weapon and max_arrow > 1
            if not is_ammo:
                qty = 1
            elif qty < 1 or qty > max_arrow:
                CTkMessageBox.showerror(
                    "Invalid Quantity",
                    f"Quantity must be 1-{max_arrow} for this ammo.",
                    parent=self.parent,
                )
                return
        else:
            max_arrow = getattr(self.selected_item, "max_arrow_quantity", 1)
            max_num = (
                max_arrow
                if max_arrow > 1
                else getattr(self.selected_item, "max_num", 1)
            )
            if max_num > 1 and (qty < 1 or qty > max_num):
                CTkMessageBox.showerror(
                    "Invalid Quantity",
                    f"Quantity must be 1-{max_num} for this item.",
                    parent=self.parent,
                )
                return
            qty = max(1, min(qty, max_num))

        # Ashes: encode upgrade directly into goods ID (base + level)
        if is_ashes and upg > 0:
            cat_bits = full_id & 0xF0000000
            base = full_id & 0x0FFFFFFF
            full_id = cat_bits | (base + upg)
            upg = 0  # already baked

        affinity_code = 0
        affinity_label = ""
        if is_weapon:
            affinity_name = self.inv_affinity_var.get()
            affinity_code = next(
                (c for c, n in self._AFFINITIES if n == affinity_name), 0
            )
            cat_bits = full_id & 0xF0000000
            base = full_id & 0x0FFFFFFF
            full_id = cat_bits | (base + affinity_code * 100)
            if affinity_code != 0:
                affinity_label = f" ({affinity_name})"

        location = self.inv_location_var.get()

        try:
            self.ensure_mutable()
            self._create_backup(save_file, slot_idx, "add_item")

            from er_save_manager.parser.inventory_ops import add_item

            result = add_item(
                save_file,
                slot_idx,
                full_id,
                qty,
                location,
                upgrade=upg,
                gem_full_id=self._selected_gem_id,
                reinforcement="ash" if is_ashes else "standard",
            )

            save_file.recalculate_checksums()
            save_path = self.get_save_path()
            if save_path:
                save_file.to_file(Path(save_path))

            self.refresh_inventory()
            if self._on_inventory_changed:
                self._on_inventory_changed()
            CTkMessageBox.showinfo(
                "Done",
                f"Added {self.selected_item.name}"
                + (f" +{upg}" if upg else "")
                + affinity_label
                + f" x{result['quantity']} to {location}.",
                parent=self.parent,
            )
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to add item:\n{e}", parent=self.parent
            )

    def remove_item(self):
        sel = self.inventory_listbox.curselection()
        if not sel:
            CTkMessageBox.showwarning(
                "No Selection", "Select an item to remove.", parent=self.parent
            )
            return

        idx = sel[0]
        if idx >= len(self._item_data) or self._item_data[idx] is None:
            return

        full_id, location = self._item_data[idx]
        item_label = self.inventory_listbox.get(idx).strip()

        if not CTkMessageBox.askyesno(
            "Confirm Remove",
            f"Remove this item from {location}?\n\n{item_label}",
            parent=self.parent,
        ):
            return

        save_file = self.get_save_file()
        slot_idx = self.get_char_slot()

        try:
            self.ensure_mutable()
            self._create_backup(save_file, slot_idx, "remove_item")

            from er_save_manager.parser.inventory_ops import remove_item

            remove_item(save_file, slot_idx, full_id, location)

            save_file.recalculate_checksums()
            save_path = self.get_save_path()
            if save_path:
                save_file.to_file(Path(save_path))

            self.refresh_inventory()
            CTkMessageBox.showinfo("Done", "Item removed.", parent=self.parent)
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to remove item:\n{e}", parent=self.parent
            )

    def set_quantity(self):
        sel = self.inventory_listbox.curselection()
        if not sel:
            CTkMessageBox.showwarning(
                "No Selection", "Select an item first.", parent=self.parent
            )
            return

        idx = sel[0]
        if idx >= len(self._item_data) or self._item_data[idx] is None:
            return

        full_id, location = self._item_data[idx]
        cat = full_id & 0xF0000000
        if cat not in (0x40000000, 0x20000000):
            CTkMessageBox.showinfo(
                "Not Stackable",
                "Quantity editing only applies to goods and spells.",
                parent=self.parent,
            )
            return

        qty_str = ctk.CTkInputDialog(
            text="Enter new quantity:", title="Set Quantity"
        ).get_input()
        if qty_str is None:
            return
        try:
            new_qty = int(qty_str)
        except ValueError:
            CTkMessageBox.showerror(
                "Input Error", "Quantity must be an integer.", parent=self.parent
            )
            return

        save_file = self.get_save_file()
        slot_idx = self.get_char_slot()

        try:
            self.ensure_mutable()
            self._create_backup(save_file, slot_idx, "set_quantity")

            from er_save_manager.parser.inventory_ops import set_quantity

            set_quantity(save_file, slot_idx, full_id, new_qty, location)

            save_file.recalculate_checksums()
            save_path = self.get_save_path()
            if save_path:
                save_file.to_file(Path(save_path))

            self.refresh_inventory()
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to set quantity:\n{e}", parent=self.parent
            )

    # ---- helpers ------------------------------------------------------------

    def _create_backup(self, save_file, slot_idx, operation):
        save_path = self.get_save_path()
        if not save_path:
            return
        from er_save_manager.backup.manager import BackupManager

        manager = BackupManager(Path(save_path))
        manager.create_backup(
            description=f"before_{operation}_slot_{slot_idx + 1}",
            operation=operation,
            save=save_file,
        )
