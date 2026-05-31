"""
Inventory Editor - add, remove, and set quantities using inventory_ops.
"""

from __future__ import annotations

# ---- item-id helpers --------------------------------------------------------
import platform as _platform
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.toast import show_toast
from er_save_manager.ui.utils import bind_mousewheel


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

        def _setup():
            import tkinter as _tk

            canvas = getattr(dm, "_canvas", None)
            if canvas is None:

                def _find(w):
                    if isinstance(w, _tk.Canvas):
                        return w
                    for c in w.winfo_children():
                        found = _find(c)
                        if found:
                            return found
                    return None

                canvas = _find(dm)
            if canvas is None:
                return

            def _scroll(e):
                canvas.yview_scroll(int(-e.delta / 120), "units")

            def _bind_all(w):
                try:
                    w.bind("<MouseWheel>", _scroll, add="+")
                    for child in w.winfo_children():
                        _bind_all(child)
                except Exception:
                    pass

            _bind_all(dm)

        dm.after(50, _setup)

    combo._open_dropdown_menu = _open
    return combo


def _center_over(window, parent, w=None, h=None, *, top=False) -> None:
    """Center window over parent. Pass w/h explicitly to avoid pre-map size queries."""
    import re as _re

    if w is None:
        window.update_idletasks()
        w = window.winfo_reqwidth()
    if h is None:
        window.update_idletasks()
        h = window.winfo_reqheight()
    x = max(0, parent.winfo_rootx() + (parent.winfo_width() - w) // 2)
    if top:
        # wm_geometry gives the outer frame Y (includes titlebar) on all platforms
        m = _re.search(r"\+(\-?\d+)\+(\-?\d+)$", parent.winfo_toplevel().wm_geometry())
        y = int(m.group(2)) if m else parent.winfo_rooty()
    else:
        y = max(0, parent.winfo_rooty() + (parent.winfo_height() - h) // 2)
    window.geometry(f"+{x}+{max(0, y)}")


def _ask_value(title: str, text: str, parent) -> str | None:
    """Centered modal single-line input dialog."""
    result: list = [None]
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.attributes("-alpha", 0)
    ctk.CTkLabel(dialog, text=text, wraplength=260, anchor="w").pack(
        padx=20, pady=(16, 6), fill="x"
    )
    var = ctk.StringVar()
    entry = ctk.CTkEntry(dialog, textvariable=var, width=260)
    entry.pack(padx=20, pady=(0, 10))
    btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_row.pack(fill="x", padx=20, pady=(0, 16))

    def _ok(_e=None):
        result[0] = var.get()
        dialog.destroy()

    entry.bind("<Return>", _ok)
    entry.bind("<Escape>", lambda _e: dialog.destroy())
    ctk.CTkButton(btn_row, text="OK", command=_ok, width=80).pack(side="left")
    ctk.CTkButton(
        btn_row,
        text="Cancel",
        command=dialog.destroy,
        width=80,
        fg_color=("gray70", "gray35"),
    ).pack(side="right")
    _center_over(dialog, parent)
    dialog.attributes("-alpha", 1)
    dialog.grab_set()
    entry.focus_set()
    dialog.wait_window()
    return result[0]


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


def _item_name(
    full_item_id: int, upgrade: int = 0, is_convergence: bool = False
) -> str:
    """Look up item name, falling back to talisman category on goods miss."""
    from er_save_manager.data.item_database import get_item_database, get_item_name

    name = get_item_name(full_item_id, upgrade, is_convergence)
    if name.startswith("Unknown") and (full_item_id & 0xF0000000) == 0x40000000:
        # B0 handles cannot distinguish goods from talismans; try talisman category
        alt = 0x20000000 | (full_item_id & 0x0FFFFFFF)
        alt_name = get_item_database().get_item_by_id(alt, is_convergence)
        if alt_name:
            return alt_name.name
    return name


# ---- editor -----------------------------------------------------------------


class InventoryEditor:
    """Inventory editor: browse, add, remove, and adjust item quantities."""

    # ---- constants ----------------------------------------------------------

    _AFFINITIES_VANILLA: list[tuple[int, str]] = [
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
    ]
    _AFFINITIES_CNV: list[tuple[int, str]] = [
        (0, "Standard"),
        (1, "Heavy"),
        (2, "Keen"),
        (3, "Quality"),
        (4, "Glint"),
        (5, "Dragonkin"),
        (6, "Gravity"),
        (7, "Flame"),
        (8, "Golden"),
        (9, "Draconic"),
        (10, "Bestial"),
        (11, "Night"),
        (12, "Lava"),
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
    # Keep _AFFINITIES as alias used by visual_inventory and external callers
    _AFFINITIES = _AFFINITIES_VANILLA

    def _affinities(self) -> list[tuple[int, str]]:
        return self._AFFINITIES_CNV if self._is_cnv_save() else self._AFFINITIES_VANILLA

    def _affinity_names(self) -> list[str]:
        return [n for _, n in self._affinities()]

    def _affinity_by_code(self) -> dict[int, str]:
        return dict(self._affinities())

    def _is_cnv_save(self) -> bool:
        sf = self.get_save_file()
        if sf and hasattr(sf, "is_convergence"):
            return bool(sf.is_convergence)
        return ".cnv" in str(self.get_save_path() or "").lower()

    _SEAMLESS_CATS = {"Seamless Co-op Items"}
    _CONVERGENCE_CATS = {
        "Convergence Melee Weapons",
        "Convergence Reworked Weapons",
        "Convergence Shields",
        "Convergence Armor",
        "Convergence Spell Tools",
        "Convergence Keystones and Remnants",
        "Convergence Steeds",
        "Convergence Stones",
        "Convergence Runes",
        "Convergence Notes",
        "Convergence Remembrances",
        "Convergence Consumables",
        "Convergence Crystal Tears",
        "Convergence Gems",
        "Convergence Talismans",
        "Convergence Ammo",
        "Convergence Ashes",
        "Convergence Magic",
        "Convergence Bell Bearings",
    }

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_char_slot_callback,
        get_save_path_callback,
        ensure_mutable_callback,
        on_inventory_changed=None,
        get_settings_callback=None,
    ):
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_char_slot = get_char_slot_callback
        self.get_save_path = get_save_path_callback
        self.ensure_mutable = ensure_mutable_callback
        self._on_inventory_changed = on_inventory_changed
        self.get_settings = get_settings_callback

        self.selected_item = None
        self._all_rows: list[tuple[str, int | None, str | None]] = []
        self._item_data: list[tuple[int, str, int] | None] = []

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
        self._inventory_change_listeners: list = []
        self._forced_selection: tuple | None = None
        self._affinity_icon_lbl: ctk.CTkLabel | None = None
        self._aow_icon_lbl: ctk.CTkLabel | None = None

        self._search_var: ctk.StringVar | None = None
        self._search_cat_var: ctk.StringVar | None = None
        self._search_cat_combo: ctk.CTkComboBox | None = None
        self._results_listbox: tk.Listbox | None = None
        self._results_items: list = []

        self.inventory_listbox: tk.Listbox | None = None
        self.inv_filter_var: ctk.StringVar | None = None
        self._inv_search_var: ctk.StringVar | None = None
        self._inv_cat_var: ctk.StringVar | None = None

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
            command=lambda _e=None: (self._search_items(), self._update_browse_state()),
        )
        self._search_cat_combo.pack(side=ctk.LEFT)
        _patch_combo_scroll(self._search_cat_combo)
        self._populate_search_categories()

        browse_row = ctk.CTkFrame(parent, fg_color="transparent")
        browse_row.pack(fill=ctk.X, padx=10, pady=(0, 4))
        self._browse_btn = ctk.CTkButton(
            browse_row,
            text="Visual Item Picker...",
            height=28,
            command=self._open_icon_browser,
            fg_color=("#6a3fa0", "#7c4dac"),
            hover_color=("#7c4dac", "#9d5fd4"),
            state="disabled",
        )
        self._browse_btn.pack(fill=ctk.X)

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

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill=ctk.X, padx=10, pady=(0, 10), side=ctk.BOTTOM)
        ctk.CTkButton(
            btn_row,
            text="Add Item",
            command=self.add_item,
            height=34,
            font=("Segoe UI", 11, "bold"),
        ).pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 4))
        ctk.CTkButton(
            btn_row,
            text="Import Build",
            command=self._import_nyasu,
            height=34,
            width=110,
            fg_color=("gray70", "gray35"),
        ).pack(side=ctk.RIGHT)

        opts = ctk.CTkFrame(parent, fg_color="transparent")
        opts.pack(fill=ctk.X, padx=10, pady=(0, 4), side=ctk.BOTTOM)
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
        _patch_combo_scroll(self._upgrade_combo)

        ctk.CTkLabel(opts, text="Affinity:", anchor="w").grid(
            row=1, column=0, sticky=ctk.W, padx=(0, 6), pady=4
        )
        self.inv_affinity_var = ctk.StringVar(value="Standard")
        _aff_frame = ctk.CTkFrame(opts, fg_color="transparent")
        _aff_frame.grid(row=1, column=1, sticky=ctk.W, pady=4)
        self._affinity_icon_lbl = ctk.CTkLabel(_aff_frame, text="", width=26, height=26)
        self._affinity_icon_lbl.pack(side=ctk.LEFT, padx=(0, 4))
        self._affinity_combo = ctk.CTkComboBox(
            _aff_frame,
            variable=self.inv_affinity_var,
            values=[n for _, n in self._AFFINITIES_VANILLA],
            width=140,
            state="disabled",
            command=self._on_affinity_combo_changed,
        )
        self._affinity_combo.pack(side=ctk.LEFT)
        _patch_combo_scroll(self._affinity_combo)

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

        ctk.CTkLabel(opts, text="Ash of War:", anchor="w").grid(
            row=2, column=0, sticky=ctk.W, padx=(0, 6), pady=4
        )
        self.inv_aow_var = ctk.StringVar(value="None")
        _aow_frame = ctk.CTkFrame(opts, fg_color="transparent")
        _aow_frame.grid(row=2, column=1, sticky=ctk.W, pady=4)
        self._aow_icon_lbl = ctk.CTkLabel(_aow_frame, text="", width=26, height=26)
        self._aow_icon_lbl.pack(side=ctk.LEFT, padx=(0, 4))
        self._aow_label = ctk.CTkLabel(
            _aow_frame,
            textvariable=self.inv_aow_var,
            text_color=("gray50", "gray60"),
            width=140,
            anchor="w",
        )
        self._aow_label.pack(side=ctk.LEFT)
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

        sep = ctk.CTkFrame(parent, height=1, fg_color=("gray75", "gray30"))
        sep.pack(fill=ctk.X, padx=10, pady=(0, 4), side=ctk.BOTTOM)

        self._selected_item_label = ctk.CTkLabel(
            parent,
            text="No item selected",
            text_color=("gray50", "gray60"),
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=400,
        )
        self._selected_item_label.pack(
            fill=ctk.X, padx=12, pady=(0, 4), side=ctk.BOTTOM
        )
        self._selected_item_label.bind(
            "<Configure>",
            lambda e: self._selected_item_label.configure(
                wraplength=max(160, e.width - 8)
            ),
        )

    # ---- right panel: current inventory -------------------------------------

    def _build_inventory_panel(self, parent: ctk.CTkFrame):
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

        cat_row = ctk.CTkFrame(parent, fg_color="transparent")
        cat_row.pack(fill=ctk.X, padx=10, pady=(0, 4))
        ctk.CTkLabel(cat_row, text="Category:", width=60).pack(side=ctk.LEFT)
        self._inv_cat_var = ctk.StringVar(value="All")
        ctk.CTkComboBox(
            cat_row,
            variable=self._inv_cat_var,
            values=["All", "Weapons", "Armor", "Talismans", "Goods", "Gems"],
            width=140,
            command=lambda _e=None: self._apply_inv_filter(),
        ).pack(side=ctk.LEFT, padx=(0, 6))

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
        ctk.CTkButton(
            search_row,
            text="Visual Inventory...",
            width=130,
            height=28,
            fg_color=("#6a3fa0", "#7c4dac"),
            hover_color=("#7c4dac", "#9d5fd4"),
            command=self._open_visual_inventory,
        ).pack(side=ctk.RIGHT)

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

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill=ctk.X, padx=10, pady=(0, 10))

        ctk.CTkButton(
            actions,
            text="Remove Selected",
            command=self.remove_item,
            width=125,
        ).pack(side=ctk.LEFT, padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="Set Quantity",
            command=self.set_quantity,
            width=110,
        ).pack(side=ctk.LEFT, padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="Set Upgrade",
            command=self.set_upgrade,
            width=100,
        ).pack(side=ctk.LEFT, padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="Set Affinity",
            command=self.set_affinity,
            width=100,
        ).pack(side=ctk.LEFT, padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="Set AoW",
            command=self.set_aow,
            width=80,
        ).pack(side=ctk.LEFT, padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="Refresh",
            command=self.refresh_inventory,
            width=80,
        ).pack(side=ctk.LEFT)

    # ---- search browser helpers ---------------------------------------------

    def _visible_categories(self) -> list[str]:
        try:
            from er_save_manager.data.item_database import get_categories

            all_cats = get_categories()
        except Exception:
            return []

        save_path = str(self.get_save_path() or "").lower()
        is_co2 = ".co2" in save_path
        is_cnv = self._is_cnv_save()

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
                if not self._is_cnv_save():
                    results = [
                        i
                        for i in results
                        if i.category_name not in self._CONVERGENCE_CATS
                    ]
                if ".co2" not in str(self.get_save_path() or "").lower():
                    results = [
                        i for i in results if i.category_name not in self._SEAMLESS_CATS
                    ]
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

    def _apply_item_selection(self, item) -> None:
        """Apply item selection state - called from listbox and icon browser."""
        self.selected_item = item
        self._selected_item_label.configure(
            text=f"Selected: {item.name}",
            text_color=("#7c4dac", "#c084fc"),
        )

        is_weapon = self.selected_item.category == 0x00000000
        is_armor = self.selected_item.category == 0x10000000
        is_gem = self.selected_item.category == 0x80000000
        is_ashes = "Ashes" in self.selected_item.category_name
        is_upgradable = is_weapon or is_ashes
        reinforcement = (
            getattr(self.selected_item, "reinforcement", "standard")
            if is_weapon
            else "standard"
        )
        aow_allowed = is_weapon and getattr(self.selected_item, "aow_allowed", True)
        affinity_allowed = is_weapon and reinforcement == "standard" and aow_allowed

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
                weapon_affs = self.selected_item.get_affinities(is_convergence_save)
                affinity_values = weapon_affs or self._affinity_names()
                self._affinity_combo.configure(values=affinity_values, state="normal")
                self.inv_affinity_var.set("Standard")
                self._update_affinity_icon("Standard")
            else:
                self._affinity_combo.configure(state="disabled")
                self.inv_affinity_var.set("Standard")
                self._update_affinity_icon("Standard")

        aow_state = "normal" if aow_allowed else "disabled"
        if self._aow_pick_btn:
            self._aow_pick_btn.configure(state=aow_state)
            self._aow_clear_btn.configure(state=aow_state)
        if not aow_allowed:
            self._clear_aow()

        if self._location_combo:
            self._location_combo.configure(state="normal")

    def _on_result_select(self, _event=None):
        sel = self._results_listbox.curselection()
        if not sel or sel[0] >= len(self._results_items):
            return
        self._apply_item_selection(self._results_items[sel[0]])

    def _update_browse_state(self) -> None:
        if not hasattr(self, "_browse_btn") or self._browse_btn is None:
            return
        self._search_cat_var.get() if hasattr(self, "_search_cat_var") else "All"
        self._browse_btn.configure(state="normal")

    def _open_visual_inventory(self) -> None:
        from er_save_manager.ui.visual_inventory import VisualInventoryBrowser

        VisualInventoryBrowser(self.parent, self)

    def _on_affinity_combo_changed(self, value: str) -> None:
        self._update_affinity_icon(value)

    def _update_affinity_icon(self, affinity_name: str) -> None:
        if not self._affinity_icon_lbl:
            return
        try:
            from er_save_manager.data.icon_manager import get_affinity_icon

            img = get_affinity_icon(affinity_name, is_convergence=self._is_cnv_save())
            if img:
                cimg = ctk.CTkImage(img, img, (22, 22))
                self._affinity_icon_lbl.configure(image=cimg)
                self._affinity_icon_lbl._cached_icon = cimg
            else:
                self._affinity_icon_lbl.configure(image=None)
        except Exception:
            self._affinity_icon_lbl.configure(image=None)

    def _update_aow_icon(self, aow_name: str) -> None:
        if not self._aow_icon_lbl:
            return
        try:
            from er_save_manager.data.icon_manager import get_icon

            img = get_icon(aow_name) if aow_name and aow_name != "None" else None
            if img:
                cimg = ctk.CTkImage(img, img, (22, 22))
                self._aow_icon_lbl.configure(image=cimg)
                self._aow_icon_lbl._cached_icon = cimg
            else:
                self._aow_icon_lbl.configure(image=None)
        except Exception:
            self._aow_icon_lbl.configure(image=None)

    def _sync_browse_category(self, category: str) -> None:
        """Called when the icon browser switches category; syncs the add-item dropdown."""
        if hasattr(self, "_search_cat_var"):
            self._search_cat_var.set(category)
            self._search_items()
            self._update_browse_state()

    def _open_icon_browser(self):
        cat = self._search_cat_var.get() if hasattr(self, "_search_cat_var") else "All"
        cats = self._visible_categories()
        if cat == "All":
            cat = cats[0] if cats else ""
        from er_save_manager.ui.icon_browser import IconBrowser

        settings = self.get_settings() if self.get_settings else None
        dev_icon_export = (
            settings.get("icon_export_enabled", False) if settings else False
        )
        IconBrowser(
            self.parent, self, initial_category=cat, dev_icon_export=dev_icon_export
        )

    def _pick_aow(self):
        import tkinter as tk

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Select Ash of War")
        dialog.geometry("380x400")
        dialog.resizable(False, True)
        dialog.transient(self.parent)
        dialog.attributes("-alpha", 0)
        dialog.update_idletasks()
        _center_over(dialog, self.parent, 380, 400)
        dialog.attributes("-alpha", 1)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()

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
                self._update_aow_icon(item.name)
                if self._aow_label:
                    self._aow_label.configure(text_color=("#7c4dac", "#c084fc"))
            if (
                self._affinity_combo
                and not is_convergence_save
                and item.allowed_affinities
            ):
                # Gem allowed_affinities uses vanilla affinity names; skip in
                # convergence saves where the affinity name set is different.
                self._affinity_combo.configure(values=item.allowed_affinities)
                default = item.default_affinity or item.allowed_affinities[0]
                self.inv_affinity_var.set(default)
                self._update_affinity_icon(default)
            elif self._affinity_combo:
                gem_affs = item.get_affinities(is_convergence_save)
                if gem_affs:
                    self._affinity_combo.configure(values=gem_affs)
                    default = (
                        item.default_affinity
                        if item.default_affinity in gem_affs
                        else gem_affs[0]
                    )
                    self.inv_affinity_var.set(default)
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

    def _clear_aow(self):
        self._selected_gem_id = 0
        if self.inv_aow_var:
            self.inv_aow_var.set("None")
            self._update_aow_icon("None")
        if self._aow_label:
            self._aow_label.configure(text_color=("gray50", "gray60"))
        if self._affinity_combo and self.inv_affinity_var:
            is_cnv = self._is_cnv_save()
            weapon_affs = (
                self.selected_item.get_affinities(is_cnv)
                if self.selected_item is not None
                else []
            )
            values = weapon_affs or self._affinity_names()
            self._affinity_combo.configure(values=values)
            self.inv_affinity_var.set("Standard")
            self._update_affinity_icon("Standard")

    # ---- inventory display --------------------------------------------------

    def refresh_inventory(self):
        self._populate_search_categories()
        self._update_browse_state()
        if self._affinity_combo:
            self._affinity_combo.configure(values=self._affinity_names())
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
            cnv = self._is_cnv_save()
            self._all_rows = []

            if filt in ("All", "Held") and hasattr(slot, "inventory_held"):
                self._collect_section(
                    "HELD INVENTORY",
                    slot.inventory_held.common_items,
                    gaitem_map,
                    "held",
                    key=False,
                    is_convergence=cnv,
                )
            if filt in ("All", "Key Items") and hasattr(slot, "inventory_held"):
                self._collect_section(
                    "KEY ITEMS (HELD)",
                    slot.inventory_held.key_items,
                    gaitem_map,
                    "held",
                    key=True,
                    is_convergence=cnv,
                )
            if filt in ("All", "Storage") and hasattr(slot, "inventory_storage_box"):
                self._collect_section(
                    "STORAGE BOX",
                    slot.inventory_storage_box.common_items,
                    gaitem_map,
                    "storage",
                    key=False,
                    is_convergence=cnv,
                )
                self._collect_section(
                    "KEY ITEMS (STORAGE)",
                    slot.inventory_storage_box.key_items,
                    gaitem_map,
                    "storage",
                    key=True,
                    is_convergence=cnv,
                )

            self._apply_inv_filter()
            for _cb in list(getattr(self, "_inventory_change_listeners", [])):
                try:
                    _cb()
                except Exception:
                    pass

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to refresh inventory:\n{e}", parent=self.parent
            )

    def _collect_section(
        self, header, items, gaitem_map, location, key, is_convergence: bool = False
    ):
        rows: list[tuple[str, int, str]] = []

        for inv_item in items:
            if inv_item.gaitem_handle == 0 or inv_item.quantity == 0:
                continue
            full_id, upgrade = _decode_inv_item(inv_item, gaitem_map)
            name = _item_name(full_id, upgrade, is_convergence)
            if not name or name.startswith("Unknown"):
                continue

            cat = full_id & 0xF0000000
            suffix = f" +{upgrade}" if upgrade > 0 and cat != 0x00000000 else ""
            affinity_label = ""
            if cat == 0x00000000:
                affinity_code = (full_id // 100) % 100
                if affinity_code != 0:
                    affinity_label = f" [{self._affinity_by_code().get(affinity_code, affinity_code)}]"

            loc_tag = "K" if key else ""
            text = (
                f"  [{location[0].upper()}{loc_tag}] "
                f"{name}{suffix}{affinity_label}"
                f"  |  Qty: {inv_item.quantity}"
            )
            rows.append((text, full_id, location, inv_item.gaitem_handle))

        count = len(rows)
        label = "item" if count == 1 else "items"
        self._all_rows.append((f"  {header}  ({count} {label})", None, None))
        self._all_rows.extend(rows)

    def _apply_inv_filter(self):
        if self.inventory_listbox is None:
            return

        query = (
            (self._inv_search_var.get() if self._inv_search_var else "").lower().strip()
        )
        cat_filter = self._inv_cat_var.get() if self._inv_cat_var else "All"

        _CAT_BITS = {
            "Weapons": 0x00000000,
            "Armor": 0x10000000,
            "Talismans": 0x20000000,
            "Goods": 0x40000000,
            "Gems": 0x80000000,
        }
        cat_mask = _CAT_BITS.get(cat_filter)

        self.inventory_listbox.delete(0, tk.END)
        self._item_data = []

        mode = ctk.get_appearance_mode()
        hdr_fg = "#9d7fc4" if mode == "Dark" else "#6a3fa0"

        for text, full_id, location, *rest in self._all_rows:
            gaitem_handle = rest[0] if rest else 0
            if full_id is None:
                self.inventory_listbox.insert(tk.END, text)
                self.inventory_listbox.itemconfig(tk.END, foreground=hdr_fg)
                self._item_data.append(None)
            else:
                if cat_mask is not None and (full_id & 0xF0000000) != cat_mask:
                    continue
                if query and query not in text.lower():
                    continue
                self.inventory_listbox.insert(tk.END, text)
                self._item_data.append((full_id, location, gaitem_handle))

    # ---- operations ---------------------------------------------------------

    def _max_qty_for_location(self, item, location: str) -> int:
        max_arrow = getattr(item, "max_arrow_quantity", 1)
        if max_arrow > 1:
            return max_arrow
        if location == "storage":
            repo = getattr(item, "max_repository_num", 0)
            return repo if repo > 0 else getattr(item, "max_num", 1)
        return getattr(item, "max_num", 1)

    def _validate_add_item(
        self,
        full_id: int,
        qty: int,
        upgrade: int,
        location: str,
        slot,
    ) -> tuple[bool, str]:
        """Pre-flight validation before calling inventory_ops.add_item."""
        from er_save_manager.data.item_database import get_item_database
        from er_save_manager.parser.inventory_ops import (
            _direct_handle,
            _find_gaitem_by_item,
            _needs_gaitem,
        )

        cat = full_id & 0xF0000000
        db = get_item_database()

        # Upgrade range - CNV saves cap standard/somber at +15
        if cat == 0x00000000:
            item = db.get_item_by_id(full_id & 0xFFFF0000)
            reinforcement = (
                getattr(item, "reinforcement", "standard") if item else "standard"
            )
            sf = self.get_save_file()
            is_cnv = (
                sf.is_convergence
                if sf
                else (".cnv" in str(self.get_save_path() or "").lower())
            )
            if is_cnv and reinforcement in ("standard", "somber"):
                cap = 15
            else:
                cap = {"standard": 25, "somber": 10, "ash": 10, "none": 0}.get(
                    reinforcement, 25
                )
            if upgrade < 0 or upgrade > cap:
                return False, f"Upgrade must be 0-{cap} for this weapon."

        # Quantity range
        item_for_qty = db.get_item_by_id(full_id)
        if item_for_qty is not None:
            max_qty = self._max_qty_for_location(item_for_qty, location)
            if qty < 1 or qty > max_qty:
                return (
                    False,
                    f"Quantity must be 1-{max_qty} for this item in {location}.",
                )

        # Duplicate check (direct-handle items only - gaitem items checked by ops layer)
        inventory = (
            slot.inventory_held if location == "held" else slot.inventory_storage_box
        )
        if _needs_gaitem(full_id):
            gaitem_idx, _ = _find_gaitem_by_item(slot, full_id)
            if gaitem_idx != -1:
                pass  # ops layer raises correctly
        else:
            handle = _direct_handle(full_id)
            from er_save_manager.parser.inventory_ops import _is_key_item

            item_list = (
                inventory.key_items
                if _is_key_item(full_id, inventory)
                else inventory.common_items
            )
            for it in item_list:
                if it.gaitem_handle == handle and it.quantity > 0:
                    return False, "This item is already in the inventory."

        return True, ""

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
        is_ashes = "Ashes" in self.selected_item.category_name

        try:
            qty = int(self.inv_quantity_var.get())
            upg = int(self.inv_upgrade_var.get()) if (is_weapon or is_ashes) else 0
        except (ValueError, tk.TclError):
            qty = 1
            upg = 0

        location = self.inv_location_var.get()

        if is_weapon or is_armor or is_gem:
            max_arrow = getattr(self.selected_item, "max_arrow_quantity", 1)
            is_ammo = is_weapon and max_arrow > 1
            if not is_ammo:
                qty = 1
            else:
                max_qty = self._max_qty_for_location(self.selected_item, location)
                if qty < 1 or qty > max_qty:
                    CTkMessageBox.showerror(
                        "Invalid Quantity",
                        f"Quantity must be 1-{max_qty} for this ammo.",
                        parent=self.parent,
                    )
                    return
        else:
            max_qty = self._max_qty_for_location(self.selected_item, location)
            if max_qty > 1 and (qty < 1 or qty > max_qty):
                CTkMessageBox.showerror(
                    "Invalid Quantity",
                    f"Quantity must be 1-{max_qty} for this item in {location}.",
                    parent=self.parent,
                )
                return
            qty = max(1, min(qty, max_qty))

        if is_ashes and upg > 0:
            cat_bits = full_id & 0xF0000000
            base = full_id & 0x0FFFFFFF
            full_id = cat_bits | (base + upg)
            upg = 0

        affinity_code = 0
        affinity_label = ""
        if is_weapon:
            affinity_name = self.inv_affinity_var.get()
            affinity_code = next(
                (c for c, n in self._affinities() if n == affinity_name), 0
            )
            cat_bits = full_id & 0xF0000000
            base = full_id & 0x0FFFFFFF
            full_id = cat_bits | (base + affinity_code * 100)
            if affinity_code != 0:
                affinity_label = f" ({affinity_name})"

        auto_storage = False
        if location == "held":
            try:
                slot = save_file.characters[slot_idx]
                held_full = all(
                    it.gaitem_handle != 0 for it in slot.inventory_held.common_items
                )
                if held_full:
                    location = "storage"
                    self.inv_location_var.set("storage")
                    auto_storage = True
            except Exception:
                pass

        try:
            slot = save_file.characters[slot_idx]
            ok, err = self._validate_add_item(full_id, qty, upg, location, slot)
            if not ok:
                CTkMessageBox.showerror("Validation Error", err, parent=self.parent)
                return
        except Exception:
            pass

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

            note = " (held full, sent to storage)" if auto_storage else ""
            msg = (
                f"Added {self.selected_item.name}"
                + (f" +{upg}" if upg else "")
                + affinity_label
                + f" x{result['quantity']} to {location}{note}."
            )
            show_toast(self.parent.winfo_toplevel(), msg, type="success")
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to add item:\n{e}", parent=self.parent
            )

    def remove_item(self):
        result = self._get_forced_or_listbox()
        if result is None:
            CTkMessageBox.showwarning(
                "No Selection", "Select an item to remove.", parent=self.parent
            )
            return
        full_id, location, gaitem_handle = result
        item_label = f"0x{full_id:08X}"
        if self._forced_selection is None and self.inventory_listbox:
            sel = self.inventory_listbox.curselection()
            if sel:
                item_label = self.inventory_listbox.get(sel[0]).strip()

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
            if self._on_inventory_changed:
                self._on_inventory_changed()
            show_toast(self.parent.winfo_toplevel(), "Item removed.", type="success")
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to remove item:\n{e}", parent=self.parent
            )

    def set_quantity(self):
        result = self._get_forced_or_listbox()
        if result is None:
            CTkMessageBox.showwarning(
                "No Selection", "Select an item first.", parent=self.parent
            )
            return
        full_id, location, gaitem_handle = result
        cat = full_id & 0xF0000000

        max_qty = None
        try:
            from er_save_manager.data.item_database import get_item_database

            db = get_item_database()
            item = db.get_item_by_id(full_id)
            if item is None and cat == 0x00000000:
                item = db.get_item_by_id(full_id & 0xFFFF0000)
            if item:
                max_qty = self._max_qty_for_location(item, location)
        except Exception:
            pass

        is_weapon = cat == 0x00000000
        is_armor = cat == 0x10000000
        is_gem = cat == 0x80000000
        is_ammo = is_weapon and max_qty is not None and max_qty > 1

        if (is_weapon and not is_ammo) or is_armor or is_gem:
            CTkMessageBox.showinfo(
                "Not Stackable",
                "Quantity editing does not apply to this item type.",
                parent=self.parent,
            )
            return

        qty_str = _ask_value(
            "Set Quantity",
            f"Enter new quantity{f' (max {max_qty})' if max_qty else ''}:",
            self.parent,
        )
        if qty_str is None:
            return
        try:
            new_qty = int(qty_str)
        except ValueError:
            CTkMessageBox.showerror(
                "Input Error", "Quantity must be an integer.", parent=self.parent
            )
            return

        if new_qty < 1:
            CTkMessageBox.showerror(
                "Input Error", "Quantity must be at least 1.", parent=self.parent
            )
            return
        if max_qty is not None and new_qty > max_qty:
            CTkMessageBox.showerror(
                "Invalid Quantity",
                f"Maximum quantity for this item is {max_qty}.",
                parent=self.parent,
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
            if self._on_inventory_changed:
                self._on_inventory_changed()
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to set quantity:\n{e}", parent=self.parent
            )

    def _patch_gaitem(self, save_file, slot_idx: int, slot, gaitem_idx: int) -> None:
        from io import BytesIO

        CHECKSUM_SIZE = 0x10
        slot_data_base = save_file._slot_offsets[slot_idx] + CHECKSUM_SIZE
        entry_abs = slot_data_base + slot.gaitem_offsets[gaitem_idx]
        g = slot.gaitem_map[gaitem_idx]
        buf = BytesIO()
        g.write(buf)
        data = buf.getvalue()
        save_file._raw_data[entry_abs : entry_abs + len(data)] = data

    def _get_forced_or_listbox(self):
        if self._forced_selection is not None:
            return self._forced_selection
        if self.inventory_listbox is None:
            return None
        sel = self.inventory_listbox.curselection()
        if not sel:
            return None
        idx = sel[0]
        if idx >= len(self._item_data) or self._item_data[idx] is None:
            return None
        return self._item_data[idx]

    def _get_selected_weapon(self) -> tuple[int, str, int] | None:
        # Support forced selection from the visual inventory popup
        if self._forced_selection is not None:
            full_id, location, gaitem_handle = self._forced_selection
            if (full_id & 0xF0000000) != 0x00000000:
                CTkMessageBox.showinfo(
                    "Not a Weapon",
                    "This operation only applies to weapons.",
                    parent=self.parent,
                )
                return None
            return full_id, location, gaitem_handle

        sel = self.inventory_listbox.curselection()
        if not sel:
            CTkMessageBox.showwarning(
                "No Selection", "Select an item first.", parent=self.parent
            )
            return None
        idx = sel[0]
        if idx >= len(self._item_data) or self._item_data[idx] is None:
            return None
        full_id, location, gaitem_handle = self._item_data[idx]
        if (full_id & 0xF0000000) != 0x00000000:
            CTkMessageBox.showinfo(
                "Not a Weapon",
                "This operation only applies to weapons.",
                parent=self.parent,
            )
            return None
        return full_id, location, gaitem_handle

    def _lookup_weapon_item(self, full_id: int):
        try:
            from er_save_manager.data.item_database import get_item_database

            db = get_item_database()
            base = (full_id & 0x0FFFFFFF) // 10000 * 10000
            return db.get_item_by_id(0x00000000 | base)
        except Exception:
            return None

    def set_upgrade(self):
        result = self._get_selected_weapon()
        if result is None:
            return
        full_id, location, gaitem_handle = result

        item = self._lookup_weapon_item(full_id)
        reinforcement = (
            getattr(item, "reinforcement", "standard") if item else "standard"
        )
        explicit_cap = getattr(item, "max_upgrade", -1) if item else -1
        save_path = str(self.get_save_path() or "").lower()
        is_convergence_save = ".cnv" in save_path

        if reinforcement == "none":
            CTkMessageBox.showinfo(
                "Not Upgradable", "This weapon cannot be upgraded.", parent=self.parent
            )
            return

        if explicit_cap >= 0:
            cap = explicit_cap
        elif is_convergence_save and reinforcement in ("standard", "somber"):
            cap = 15
        else:
            cap = 25 if reinforcement == "standard" else 10

        upg_str = _ask_value(
            "Set Upgrade",
            f"Enter upgrade level (0-{cap}):",
            self.parent,
        )
        if upg_str is None:
            return
        try:
            new_upg = int(upg_str)
        except ValueError:
            CTkMessageBox.showerror(
                "Input Error", "Upgrade level must be an integer.", parent=self.parent
            )
            return
        if new_upg < 0 or new_upg > cap:
            CTkMessageBox.showerror(
                "Invalid Upgrade", f"Upgrade must be 0-{cap}.", parent=self.parent
            )
            return

        save_file = self.get_save_file()
        slot_idx = self.get_char_slot()
        try:
            self.ensure_mutable()
            slot = save_file.characters[slot_idx]
            base_id = (full_id & 0x0FFFFFFF) // 100 * 100
            for i, g in enumerate(slot.gaitem_map):
                if g.gaitem_handle != gaitem_handle:
                    continue
                self._create_backup(save_file, slot_idx, "set_upgrade")
                g.item_id = base_id + new_upg
                self._patch_gaitem(save_file, slot_idx, slot, i)
                save_file.recalculate_checksums()
                if self.get_save_path():
                    save_file.to_file(Path(self.get_save_path()))
                self.refresh_inventory()
                if self._on_inventory_changed:
                    self._on_inventory_changed()
                show_toast(
                    self.parent.winfo_toplevel(),
                    f"Upgrade set to +{new_upg}.",
                    type="success",
                )
                return
            CTkMessageBox.showerror(
                "Not Found", "Weapon gaitem entry not found.", parent=self.parent
            )
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to set upgrade:\n{e}", parent=self.parent
            )

    def set_affinity(
        self,
        forced_full_id: int | None = None,
        forced_gaitem_handle: int | None = None,
        allowed: list | None = None,
    ):
        save_path = str(self.get_save_path() or "").lower()
        is_convergence_save = ".cnv" in save_path

        if forced_full_id is not None:
            full_id = forced_full_id
            gaitem_handle = forced_gaitem_handle
        else:
            result = self._get_selected_weapon()
            if result is None:
                return
            full_id, _, gaitem_handle = result

            if allowed is None and gaitem_handle is not None:
                try:
                    slot0 = self.get_save_file().characters[self.get_char_slot()]
                    for g0 in slot0.gaitem_map:
                        if g0.gaitem_handle != gaitem_handle:
                            continue
                        gem_h = getattr(g0, "gem_gaitem_handle", None)
                        if gem_h and gem_h not in (0, -1):
                            gem_h_u = gem_h & 0xFFFFFFFF
                            for gg in slot0.gaitem_map:
                                if gg.gaitem_handle == gem_h_u:
                                    from er_save_manager.data.item_database import (
                                        get_item_database,
                                    )

                                    gem_item = get_item_database().get_item_by_id(
                                        0x80000000 | (gg.item_id & 0x0FFFFFFF)
                                    )
                                    if gem_item:
                                        gem_affs = gem_item.get_affinities(
                                            is_convergence_save
                                        )
                                        if gem_affs:
                                            allowed = gem_affs
                                    break
                        break
                except Exception:
                    pass

        item = self._lookup_weapon_item(full_id)
        if item and not getattr(item, "aow_allowed", True):
            CTkMessageBox.showinfo(
                "Not Infusable", "This weapon cannot be infused.", parent=self.parent
            )
            return

        base_list = self._affinity_names()
        if item:
            weapon_affs = item.get_affinities(is_convergence_save)
            if weapon_affs:
                base_list = weapon_affs
        affinity_list = (
            base_list if allowed is None else [a for a in base_list if a in allowed]
        )
        if not affinity_list:
            affinity_list = base_list

        import tkinter as tk

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Set Affinity")
        dialog.geometry("260x400")
        dialog.resizable(False, True)
        dialog.transient(self.parent)
        dialog.update_idletasks()
        _center_over(dialog, self.parent, 260, 400)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()

        mode = ctk.get_appearance_mode()
        lb_bg = "#1a1a24" if mode == "Dark" else "#f0f0f0"
        lb_fg = "#d4d4e8" if mode == "Dark" else "#111111"
        lb_sel = "#7c4dac" if mode == "Dark" else "#b8a0d0"

        _AFF_ROW_H = 32
        cv_frame = ctk.CTkFrame(dialog, fg_color=("gray82", "gray14"), corner_radius=6)
        cv_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=(10, 4))
        aff_sb = tk.Scrollbar(cv_frame)
        aff_sb.pack(side=tk.RIGHT, fill=tk.Y)
        aff_cv = tk.Canvas(
            cv_frame, bg=lb_bg, highlightthickness=0, bd=0, yscrollcommand=aff_sb.set
        )
        aff_cv.pack(side=tk.LEFT, fill=ctk.BOTH, expand=True, padx=2, pady=2)
        aff_sb.config(command=aff_cv.yview)
        aff_cv.bind("<Button-4>", lambda _e: aff_cv.yview_scroll(-1, "units"))
        aff_cv.bind("<Button-5>", lambda _e: aff_cv.yview_scroll(1, "units"))

        _sel_name: list[str | None] = [None]
        _sel_aff_idx: list[int | None] = [None]
        _aff_photos: list = []
        is_cnv_now = self._is_cnv_save()

        cw_aff = 230
        for i, name in enumerate(affinity_list):
            y0 = i * _AFF_ROW_H
            aff_cv.create_rectangle(
                0, y0, cw_aff, y0 + _AFF_ROW_H, fill=lb_bg, outline="", tags=f"arow_{i}"
            )
            aff_cv.create_text(
                32,
                y0 + _AFF_ROW_H // 2,
                text=name,
                fill=lb_fg,
                font=("Consolas", 11),
                anchor="w",
                tags=f"atext_{i}",
            )
        aff_cv.configure(scrollregion=(0, 0, cw_aff, len(affinity_list) * _AFF_ROW_H))

        def _aff_click(event) -> None:
            cy = aff_cv.canvasy(event.y)
            idx = int(cy // _AFF_ROW_H)
            if 0 <= idx < len(affinity_list):
                prev = _sel_aff_idx[0]
                _sel_aff_idx[0] = idx
                _sel_name[0] = affinity_list[idx]
                for i in (prev, idx):
                    if i is None:
                        continue
                    aff_cv.itemconfigure(
                        f"arow_{i}", fill=lb_sel if i == _sel_aff_idx[0] else lb_bg
                    )

        aff_cv.bind("<Button-1>", _aff_click)
        aff_cv.bind("<Double-Button-1>", lambda e: (_aff_click(e), _confirm()))

        def _load_aff_icons() -> None:
            try:
                from PIL import Image, ImageTk

                from er_save_manager.data.icon_manager import get_affinity_icon
            except Exception:
                return
            for i, name in enumerate(affinity_list):
                try:
                    _pil = get_affinity_icon(name, is_convergence=is_cnv_now)
                    if _pil:
                        _pil = _pil.convert("RGBA").resize((22, 22), Image.LANCZOS)
                        _ph = ImageTk.PhotoImage(_pil)
                        _aff_photos.append(_ph)
                        y0 = i * _AFF_ROW_H
                        aff_cv.create_image(
                            4,
                            y0 + _AFF_ROW_H // 2,
                            image=_ph,
                            anchor="w",
                            tags=f"arow_{i}",
                        )
                except Exception:
                    pass
            # Pin list to canvas so PhotoImages are not GC'd
            aff_cv._photo_refs = _aff_photos

        dialog.after(80, _load_aff_icons)

        def _apply_affinity(affinity_code: int):
            save_file2 = self.get_save_file()
            slot_idx2 = self.get_char_slot()
            try:
                self.ensure_mutable()
                slot = save_file2.characters[slot_idx2]
                raw_base = full_id & 0x0FFFFFFF
                true_base = raw_base // 10000 * 10000
                upgrade = raw_base % 100
                new_item_id = true_base + affinity_code * 100 + upgrade
                for i, g in enumerate(slot.gaitem_map):
                    if gaitem_handle is not None:
                        if g.gaitem_handle != gaitem_handle:
                            continue
                    else:
                        if (g.gaitem_handle & 0xF0000000) != 0x80000000:
                            continue
                        if (getattr(g, "item_id", 0) // 10000) * 10000 != true_base:
                            continue
                    self._create_backup(save_file2, slot_idx2, "set_affinity")
                    g.item_id = new_item_id
                    self._patch_gaitem(save_file2, slot_idx2, slot, i)
                    save_file2.recalculate_checksums()
                    if self.get_save_path():
                        save_file2.to_file(Path(self.get_save_path()))
                    self.refresh_inventory()
                    if self._on_inventory_changed:
                        self._on_inventory_changed()
                    return
                CTkMessageBox.showerror(
                    "Not Found", "Weapon gaitem entry not found.", parent=self.parent
                )
            except Exception as e:
                CTkMessageBox.showerror(
                    "Error", f"Failed to set affinity:\n{e}", parent=self.parent
                )

        def _confirm():
            if not _sel_name[0]:
                return
            affinity_name = _sel_name[0]
            affinity_code = next(
                (c for c, n in self._affinities() if n == affinity_name), 0
            )
            dialog.destroy()
            _apply_affinity(affinity_code)

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill=ctk.X, padx=10, pady=(0, 10))
        ctk.CTkButton(btn_row, text="Apply", command=_confirm, width=90).pack(
            side=ctk.LEFT, padx=(0, 6)
        )
        ctk.CTkButton(btn_row, text="Cancel", command=dialog.destroy, width=80).pack(
            side=ctk.RIGHT
        )

    def set_aow(self):
        result = self._get_selected_weapon()
        if result is None:
            return
        full_id, location, gaitem_handle = result

        item = self._lookup_weapon_item(full_id)
        if item and not getattr(item, "aow_allowed", True):
            CTkMessageBox.showinfo(
                "AoW Not Supported",
                "This weapon does not accept an Ash of War.",
                parent=self.parent,
            )
            return

        wep_col = getattr(item, "wep_type_col", "") if item else ""
        save_path_str = str(self.get_save_path() or "").lower()
        is_convergence_save = ".cnv" in save_path_str

        current_aow_name = "None"
        try:
            slot0 = self.get_save_file().characters[self.get_char_slot()]
            for g0 in slot0.gaitem_map:
                if g0.gaitem_handle != gaitem_handle:
                    continue
                gem_h = getattr(g0, "gem_gaitem_handle", None)
                if gem_h and gem_h not in (0, -1):
                    gem_h_u = gem_h & 0xFFFFFFFF
                    for gg in slot0.gaitem_map:
                        if gg.gaitem_handle == gem_h_u:
                            from er_save_manager.data.item_database import (
                                get_item_database,
                            )

                            gi = get_item_database().get_item_by_id(
                                0x80000000 | (gg.item_id & 0x0FFFFFFF)
                            )
                            if gi:
                                current_aow_name = gi.name
                            break
                break
        except Exception:
            pass

        import tkinter as tk

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Set Ash of War")
        dialog.geometry("380x440")
        dialog.resizable(False, True)
        dialog.transient(self.parent)
        dialog.update_idletasks()
        _center_over(dialog, self.parent, 380, 440)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()

        mode = ctk.get_appearance_mode()
        lb_bg = "#1a1a24" if mode == "Dark" else "#f0f0f0"
        lb_fg = "#d4d4e8" if mode == "Dark" else "#111111"
        lb_sel = "#7c4dac" if mode == "Dark" else "#b8a0d0"

        cur_frame = ctk.CTkFrame(dialog, fg_color=("gray78", "gray18"), corner_radius=6)
        cur_frame.pack(fill=ctk.X, padx=10, pady=(8, 2))
        ctk.CTkLabel(cur_frame, text="Current:", anchor="w", width=60).pack(
            side=ctk.LEFT, padx=6, pady=4
        )
        ctk.CTkLabel(
            cur_frame,
            text=current_aow_name,
            anchor="w",
            text_color=("#7c4dac", "#c084fc")
            if current_aow_name != "None"
            else ("gray50", "gray60"),
        ).pack(side=ctk.LEFT, padx=4, pady=4)

        search_var = ctk.StringVar()
        ctk.CTkLabel(dialog, text="Search:").pack(anchor="w", padx=10, pady=(4, 0))
        ctk.CTkEntry(dialog, textvariable=search_var, width=340).pack(
            padx=10, pady=(0, 4)
        )

        _ROW_H = 34
        lb_frame = ctk.CTkFrame(dialog, fg_color=("gray82", "gray14"), corner_radius=6)
        lb_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=4)
        sb = tk.Scrollbar(lb_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        cv = tk.Canvas(
            lb_frame, bg=lb_bg, highlightthickness=0, bd=0, yscrollcommand=sb.set
        )
        cv.pack(side=tk.LEFT, fill=ctk.BOTH, expand=True, padx=2, pady=2)
        sb.config(command=cv.yview)
        cv.bind("<Button-4>", lambda _e: cv.yview_scroll(-1, "units"))
        cv.bind("<Button-5>", lambda _e: cv.yview_scroll(1, "units"))
        _aow_sel_idx: list[int | None] = [None]
        _aow_photos: list = []
        _aow_drawn_gems: list = []

        _aow_icon_job: list[str | None] = [None]

        def _draw_aow_rows(gems) -> None:
            if _aow_icon_job[0]:
                try:
                    dialog.after_cancel(_aow_icon_job[0])
                except Exception:
                    pass
                _aow_icon_job[0] = None
            cv.delete("all")
            _aow_photos.clear()
            _aow_drawn_gems.clear()
            _aow_sel_idx[0] = None
            cw = max(cv.winfo_width(), 300)
            for i, g in enumerate(gems):
                y0 = i * _ROW_H
                cv.create_rectangle(
                    0, y0, cw, y0 + _ROW_H, fill=lb_bg, outline="", tags=f"row_{i}"
                )
                cv.create_text(
                    32,
                    y0 + _ROW_H // 2,
                    text=g.name,
                    fill=lb_fg,
                    font=("Consolas", 10),
                    anchor="w",
                    tags=f"text_{i}",
                )
                _aow_drawn_gems.append(g)
            cv.configure(scrollregion=(0, 0, cw, len(gems) * _ROW_H))
            _aow_icon_job[0] = dialog.after(80, lambda: _load_aow_icons(0))

        def _load_aow_icons(start: int, batch: int = 20) -> None:
            try:
                from PIL import Image, ImageTk

                from er_save_manager.data.icon_manager import get_icon
            except Exception:
                return
            end = min(start + batch, len(_aow_drawn_gems))
            max(cv.winfo_width(), 300)
            for i in range(start, end):
                g = _aow_drawn_gems[i]
                try:
                    _pil = get_icon(g.name)
                    if _pil:
                        _pil = _pil.convert("RGBA").resize((24, 24), Image.LANCZOS)
                        _ph = ImageTk.PhotoImage(_pil)
                        _aow_photos.append(_ph)
                        y0 = i * _ROW_H
                        cv.create_image(
                            4, y0 + _ROW_H // 2, image=_ph, anchor="w", tags=f"row_{i}"
                        )
                except Exception:
                    pass
            if end < len(_aow_drawn_gems):
                _aow_icon_job[0] = dialog.after(30, lambda: _load_aow_icons(end, batch))
            else:
                _aow_icon_job[0] = None
                cv._photo_refs = _aow_photos  # prevent GC

        def _aow_click(event) -> None:
            cy = cv.canvasy(event.y)
            idx = int(cy // _ROW_H)
            if 0 <= idx < len(_aow_drawn_gems):
                prev = _aow_sel_idx[0]
                _aow_sel_idx[0] = idx
                max(cv.winfo_width(), 300)
                for i in (prev, idx):
                    if i is None:
                        continue
                    cv.itemconfigure(
                        f"row_{i}", fill=lb_sel if i == _aow_sel_idx[0] else lb_bg
                    )

        cv.bind("<Button-1>", _aow_click)
        cv.bind("<Double-Button-1>", lambda e: (_aow_click(e), _confirm()))

        try:
            from er_save_manager.data.item_database import get_item_database

            db = get_item_database()
            cats = ["Gems", "DLC Gems"]
            if is_convergence_save:
                cats.append("Convergence Gems")
            all_gems = []
            for cat in cats:
                all_gems += db.get_items_by_category(cat)
            if wep_col:
                all_gems = [
                    g
                    for g in all_gems
                    if not g.compatible_wep_types or wep_col in g.compatible_wep_types
                ]
        except Exception:
            all_gems = []

        visible_gems: list = []

        def _filter(*_):
            q = search_var.get().lower().strip()
            visible_gems.clear()
            visible_gems.extend(g for g in all_gems if not q or q in g.name.lower())
            _draw_aow_rows(visible_gems[:200])

        search_var.trace_add("write", _filter)
        _filter()

        def _confirm():
            idx2 = _aow_sel_idx[0]
            if idx2 is None or idx2 >= len(visible_gems):
                return
            gem_item = visible_gems[idx2]
            gem_full_id = 0x80000000 | gem_item.id
            dialog.destroy()

            save_file2 = self.get_save_file()
            slot_idx2 = self.get_char_slot()
            try:
                self.ensure_mutable()
                self._create_backup(save_file2, slot_idx2, "set_aow")
                from er_save_manager.parser.inventory_ops import insert_gaitem

                gem_handle, _ = insert_gaitem(save_file2, slot_idx2, gem_full_id)
                slot2 = save_file2.characters[slot_idx2]
                (full_id & 0x0FFFFFFF) // 10000 * 10000
                for i2, g2 in enumerate(slot2.gaitem_map):
                    if g2.gaitem_handle != gaitem_handle:
                        continue
                    g2.gem_gaitem_handle = (
                        gem_handle - 0x100000000
                        if gem_handle >= 0x80000000
                        else gem_handle
                    )
                    self._patch_gaitem(save_file2, slot_idx2, slot2, i2)
                    break
                save_file2.recalculate_checksums()
                if self.get_save_path():
                    save_file2.to_file(Path(self.get_save_path()))
                self.refresh_inventory()
                if self._on_inventory_changed:
                    self._on_inventory_changed()

                gem_affs = gem_item.get_affinities(is_convergence_save)
                if gem_affs:
                    raw_base = full_id & 0x0FFFFFFF
                    cur_code = (raw_base // 100) % 100
                    cur_name = self._affinity_by_code().get(cur_code, "Standard")
                    if cur_name not in gem_affs:
                        self.set_affinity(
                            forced_full_id=full_id,
                            forced_gaitem_handle=gaitem_handle,
                            allowed=gem_affs,
                        )
            except Exception as e:
                CTkMessageBox.showerror(
                    "Error", f"Failed to set AoW:\n{e}", parent=self.parent
                )

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill=ctk.X, padx=10, pady=(4, 10))
        ctk.CTkButton(btn_row, text="Apply", command=_confirm, width=90).pack(
            side=ctk.LEFT, padx=(0, 6)
        )
        ctk.CTkButton(btn_row, text="Cancel", command=dialog.destroy, width=80).pack(
            side=ctk.RIGHT
        )

    # ---- import build -------------------------------------------------------

    def _import_nyasu(self) -> None:
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Load a save file first.", parent=self.parent
            )
            return

        slot_idx = self.get_char_slot()
        try:
            slot = save_file.characters[slot_idx]
            if not slot or slot.is_empty():
                CTkMessageBox.showwarning(
                    "Empty Slot", "Select a character first.", parent=self.parent
                )
                return
        except Exception as e:
            CTkMessageBox.showerror("Error", str(e), parent=self.parent)
            return

        from er_save_manager.ui.nyasu_import import import_nyasu

        def _on_refresh():
            self.refresh_inventory()
            if self._on_inventory_changed:
                self._on_inventory_changed()

        import_nyasu(
            parent=self.parent,
            save_file=save_file,
            slot_idx=slot_idx,
            get_save_path=self.get_save_path,
            ensure_mutable=self.ensure_mutable,
            create_backup=self._create_backup,
            on_refresh=_on_refresh,
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
