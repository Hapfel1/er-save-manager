"""
DS3 Inventory Editor tab.

Left: item spawner (category, search, cut content filter, visual picker).
Right: held inventory, key items and the storage box (visual editor).

Both lists take several rows at once (Ctrl or Shift click), and every
action applies to all of them with one backup and one save.

Item lists, limits and icons come from the selected game data source
(vanilla, Convergence or Cinders), each generated from that game's own
files (see catalog.py). Slot writes go through DS3Slot, which stores items
the way the game does (see slot.py).
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk

from er_save_manager.games.DS3 import catalog
from er_save_manager.games.DS3.icon_manager import get_infusion_icon
from er_save_manager.games.DS3.slot import ID_ARMOR, ID_WEAPON, LayoutError, id_kind
from er_save_manager.games.DS3.tabs.style import apply_treeview_style
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import game_blocks_write


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(parent, "darksoulsiii.exe", "Dark Souls III")


_HIDDEN_NAMES = frozenset({"npc", "load check", "test"})

LOCATIONS = ("Inventory", "Storage Box")
WHERE_HELD = "Held"
WHERE_KEY = "Key"
WHERE_STORAGE = "Storage"

_ERROR_TEXT = ("#b00020", "#ff6b6b")
_HINT = ("gray40", "gray60")
_INFUSION_ICON_SIZE = 22
# Spawning more rows than this at once asks for confirmation first.
_CONFIRM_SPAWN_COUNT = 25
# Reasons listed in a result message before the rest are summarised.
_MAX_REASONS = 4


def _backup_and_save(ds3_save, save_path: Path, op: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=op, save=None)
    ds3_save.save_to_file(save_path)


_DISABLED_FG = ("gray72", "gray28")
_DISABLED_TEXT = ("gray50", "gray50")
# Tk path name -> the colour a widget had before enable() greyed it out.
_enabled_colors: dict[str, object] = {}


def enable(widget, on: bool) -> None:
    """Enable or grey out a CTk entry, button or read-only combo box. CTk's
    disabled state barely changes buttons and entries, so their colour is
    swapped as well."""
    if isinstance(widget, ctk.CTkComboBox):
        widget.configure(state="readonly" if on else "disabled")
        return
    option = "fg_color" if isinstance(widget, ctk.CTkButton) else "text_color"
    key = str(widget)
    if not on and key not in _enabled_colors:
        _enabled_colors[key] = widget.cget(option)
    if on and key in _enabled_colors:
        widget.configure(state="normal", **{option: _enabled_colors.pop(key)})
    elif not on:
        disabled = _DISABLED_FG if option == "fg_color" else _DISABLED_TEXT
        widget.configure(state="disabled", **{option: disabled})
    else:
        widget.configure(state="normal")


def infusion_image(item: dict | None, source: str) -> ctk.CTkImage | None:
    """CTkImage of the item's infusion icon, None for non-infusable items."""
    if item is None or "Infusion" not in item:
        return None
    img = get_infusion_icon(catalog.infusion_index(int(item["Id"], 16)), source)
    if img is None:
        return None
    size = (_INFUSION_ICON_SIZE, _INFUSION_ICON_SIZE)
    return ctk.CTkImage(light_image=img, dark_image=img, size=size)


def _summary(done: str, count: int, skipped: list[str], capped: int = 0) -> str:
    """Toast text for a batch: what happened, what was capped or skipped."""
    text = done if count else "Nothing changed"
    if capped:
        text += f" ({capped} capped at the item's limit)"
    if skipped:
        shown = "; ".join(skipped[:_MAX_REASONS])
        more = len(skipped) - _MAX_REASONS
        text += f". Skipped: {shown}" + (f" and {more} more" if more > 0 else "")
    return text


class DS3InventoryTab:
    def __init__(
        self, parent, get_save, get_save_path, show_toast, reload_save=None
    ) -> None:
        self.parent = parent
        self._get_save = get_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._reload_save = reload_save
        self._current_slot = -1
        self._spawn_tree_ready = False
        self._selected_db_item: dict | None = None
        # Spawn tree row id -> (representative item, infusion variants)
        self._spawn_rows: dict[str, tuple[dict, list[dict]]] = {}
        self._visible_spawn: list[tuple[str, dict, list[dict]]] = []
        # Whether the spawn list was last built with the Seamless Co-op goods.
        self._spawn_seamless = False
        # (offset, name, category label, quantity, location, item id)
        self._all_items: list[tuple] = []
        self._sort_col: str | None = None
        self._sort_asc = True
        self._source_var = tk.StringVar(value=catalog.SOURCES["vanilla"])
        self._show_cut = tk.BooleanVar(value=False)
        self._spawn_job: str | None = None
        self._spawn_variants: list[dict] = []
        self.editing_error: str | None = None
        self._infusion_labels: dict[str, list[str]] = {}
        # Offsets the last batch left its entries at (new places after a
        # move, none after a removal), for popups to reselect.
        self.last_offsets: list[int] = []
        # Called after every save write, so open popups can reload.
        self.listeners: list = []

    # --- Source ------------------------------------------------------------ #

    @property
    def source(self) -> str:
        label = self._source_var.get()
        return next(k for k, v in catalog.SOURCES.items() if v == label)

    def _on_source_change(self, _value=None) -> None:
        self._reload_inventory()
        self._refresh_spawn_tree()

    def infusion_labels(self) -> list[str]:
        """Infusion names of the current source, by infusion index."""
        source = self.source
        if source not in self._infusion_labels:
            labels: dict[int, str] = {}
            for item in catalog.items(source).get("weapon_items", []):
                if "Infusion" in item:
                    index = catalog.infusion_index(int(item["Id"], 16))
                    labels.setdefault(index, item["Infusion"])
            self._infusion_labels[source] = [labels[k] for k in sorted(labels)]
        return self._infusion_labels[source]

    # --- Layout ------------------------------------------------------------ #

    def setup_ui(self) -> None:
        apply_treeview_style()

        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(
            header, text="Inventory Editor", font=("Segoe UI", 16, "bold")
        ).pack(side="left")
        ctk.CTkLabel(header, text="Game data:").pack(side="left", padx=(20, 6))
        ctk.CTkSegmentedButton(
            header,
            values=list(catalog.SOURCES.values()),
            variable=self._source_var,
            command=self._on_source_change,
        ).pack(side="left")
        ctk.CTkButton(header, text="Load", command=self._load_selected, width=70).pack(
            side="right", padx=(6, 0)
        )
        self._slot_var = tk.StringVar()
        self._slot_combo = ctk.CTkComboBox(
            header, variable=self._slot_var, values=[], state="readonly", width=240
        )
        self._slot_combo.pack(side="right")
        ctk.CTkLabel(header, text="Slot:").pack(side="right", padx=(0, 6))

        self._error_label = ctk.CTkLabel(
            outer,
            text="",
            text_color=_ERROR_TEXT,
            anchor="w",
            justify="left",
            wraplength=900,
        )

        body = ctk.CTkFrame(outer, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self._body = body

        self._build_spawner_panel(body)
        self._build_inventory_panel(body)
        self._apply_edit_states()
        self._apply_spawn_states()

    def _infusion_widgets(self, parent, variable, command):
        """Infusion icon plus dropdown packed into parent; returns both."""
        icon = ctk.CTkLabel(parent, text="", width=_INFUSION_ICON_SIZE)
        icon.pack(side="left", padx=(0, 4))
        combo = ctk.CTkComboBox(
            parent,
            variable=variable,
            values=[],
            state="readonly",
            width=140,
            command=command,
        )
        combo.pack(side="left", padx=(0, 6))
        return icon, combo

    def _build_spawner_panel(self, parent) -> None:
        left = ctk.CTkFrame(parent, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(left, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 4))
        ctk.CTkLabel(head, text="Spawn Items", font=("Segoe UI", 12, "bold")).pack(
            side="left"
        )
        ctk.CTkCheckBox(
            head,
            text="Cut content",
            variable=self._show_cut,
            command=self._refresh_spawn_tree,
        ).pack(side="left", padx=(16, 0))
        ctk.CTkButton(
            head, text="Visual Picker", width=110, command=self._open_visual_picker
        ).pack(side="right")

        frow = ctk.CTkFrame(left, fg_color="transparent")
        frow.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 4))
        self._spawn_cat_var = tk.StringVar(value="All")
        ctk.CTkComboBox(
            frow,
            variable=self._spawn_cat_var,
            values=self.category_options(),
            state="readonly",
            width=130,
            command=lambda _: self._refresh_spawn_tree(),
        ).pack(side="left", padx=(0, 6))
        self._spawn_search_var = tk.StringVar()
        self._spawn_search_var.trace_add("write", lambda *_: self._refresh_spawn_tree())
        ctk.CTkEntry(
            frow, textvariable=self._spawn_search_var, placeholder_text="Search..."
        ).pack(side="left", fill="x", expand=True)

        self._spawn_tree = ttk.Treeview(
            left,
            columns=("name",),
            show="headings",
            style="DS3.Treeview",
            height=10,
            selectmode="extended",
        )
        self._spawn_tree.heading("name", text="Item (Ctrl or Shift click for several)")
        self._spawn_tree.column("name", width=260, anchor="w")
        self._spawn_tree.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        ssb = ttk.Scrollbar(left, orient="vertical", command=self._spawn_tree.yview)
        ssb.grid(row=2, column=1, sticky="ns", pady=(0, 4))
        self._spawn_tree.configure(yscrollcommand=ssb.set)
        self._spawn_tree.bind("<<TreeviewSelect>>", self._on_spawn_select)
        # The spawn tree is filled on first character load, not at setup.

        self._spawn_inf_row = ctk.CTkFrame(left, fg_color="transparent")
        ctk.CTkLabel(self._spawn_inf_row, text="Infusion:").pack(
            side="left", padx=(0, 4)
        )
        self._spawn_inf_var = tk.StringVar(value="")
        self._spawn_inf_icon, self._spawn_inf_combo = self._infusion_widgets(
            self._spawn_inf_row, self._spawn_inf_var, self._on_spawn_infusion
        )
        self._spawn_inf_row.grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 2)
        )

        ctrl = ctk.CTkFrame(left, fg_color="transparent")
        ctrl.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        ctk.CTkLabel(ctrl, text="Qty:").grid(row=0, column=0, padx=(0, 2), pady=4)
        self._spawn_qty_var = tk.StringVar(value="1")
        self._spawn_qty_entry = ctk.CTkEntry(
            ctrl, textvariable=self._spawn_qty_var, width=50
        )
        self._spawn_qty_entry.grid(row=0, column=1, padx=(0, 8), pady=4)
        ctk.CTkLabel(ctrl, text="Upgrade:").grid(row=0, column=2, padx=(0, 2), pady=4)
        self._spawn_upg_var = tk.StringVar(value="0")
        self._spawn_upg_entry = ctk.CTkEntry(
            ctrl, textvariable=self._spawn_upg_var, width=40
        )
        self._spawn_upg_entry.grid(row=0, column=3, padx=(0, 8), pady=4)
        self.location_var = tk.StringVar(value=LOCATIONS[0])
        self._location_combo = ctk.CTkComboBox(
            ctrl,
            variable=self.location_var,
            values=list(LOCATIONS),
            state="readonly",
            width=120,
        )
        self._location_combo.grid(row=0, column=4, padx=(0, 8), pady=4)

        buttons = ctk.CTkFrame(ctrl, fg_color="transparent")
        buttons.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(2, 2))
        self._spawn_btn = ctk.CTkButton(
            buttons, text="Spawn Selected", command=self._spawn_selected_rows, width=130
        )
        self._spawn_btn.pack(side="left", padx=(0, 6))
        self._spawn_all_btn = ctk.CTkButton(
            buttons, text="Spawn All Listed", command=self._spawn_all_listed, width=130
        )
        self._spawn_all_btn.pack(side="left")
        self._spawn_info = ctk.CTkLabel(
            ctrl, text="", font=("Segoe UI", 9), text_color=_HINT
        )
        self._spawn_info.grid(row=2, column=0, columnspan=5, sticky="w", pady=(0, 4))

    def _build_inventory_panel(self, parent) -> None:
        right = ctk.CTkFrame(parent, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(right, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 4))
        ctk.CTkLabel(head, text="Inventory", font=("Segoe UI", 12, "bold")).pack(
            side="left"
        )
        ctk.CTkButton(
            head, text="Visual Editor", width=110, command=self._open_visual_editor
        ).pack(side="right")

        frow = ctk.CTkFrame(right, fg_color="transparent")
        frow.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 4))
        self._inv_search_var = tk.StringVar()
        self._inv_search_var.trace_add(
            "write", lambda *_: self._refresh_inventory_tree()
        )
        ctk.CTkEntry(
            frow, textvariable=self._inv_search_var, placeholder_text="Filter..."
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._inv_cat_var = tk.StringVar(value="All")
        ctk.CTkComboBox(
            frow,
            variable=self._inv_cat_var,
            values=self.category_options(),
            state="readonly",
            width=110,
            command=lambda _: self._refresh_inventory_tree(),
        ).pack(side="left", padx=(0, 6))
        self._inv_where_var = tk.StringVar(value="All")
        ctk.CTkComboBox(
            frow,
            variable=self._inv_where_var,
            values=["All", WHERE_HELD, WHERE_KEY, WHERE_STORAGE],
            state="readonly",
            width=100,
            command=lambda _: self._refresh_inventory_tree(),
        ).pack(side="left")

        self._inv_tree = ttk.Treeview(
            right,
            columns=("name", "type", "qty", "where"),
            show="headings",
            style="DS3.Treeview",
            height=10,
            selectmode="extended",
        )
        for col, heading, width in self._inv_columns():
            self._inv_tree.heading(
                col, text=heading, command=lambda c=col: self._sort_by(c)
            )
            self._inv_tree.column(
                col, width=width, anchor="w" if col == "name" else "center"
            )
        self._inv_tree.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        vsb = ttk.Scrollbar(right, orient="vertical", command=self._inv_tree.yview)
        vsb.grid(row=2, column=1, sticky="ns", pady=(0, 4))
        self._inv_tree.configure(yscrollcommand=vsb.set)
        self._inv_tree.bind("<<TreeviewSelect>>", self._on_inv_select)

        edits = ctk.CTkFrame(right, fg_color="transparent")
        edits.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 2))
        self._edit_qty_var = tk.StringVar(value="1")
        self._edit_upg_var = tk.StringVar(value="0")
        self._edit_inf_var = tk.StringVar(value="")

        qty_row = ctk.CTkFrame(edits, fg_color="transparent")
        qty_row.pack(fill="x", pady=2)
        ctk.CTkLabel(qty_row, text="Qty:", width=60, anchor="w").pack(side="left")
        self._edit_qty_entry = ctk.CTkEntry(
            qty_row, textvariable=self._edit_qty_var, width=55
        )
        self._edit_qty_entry.pack(side="left", padx=(0, 6))
        self._set_qty_btn = ctk.CTkButton(
            qty_row, text="Set Quantity", width=110, command=self._set_quantity_rows
        )
        self._set_qty_btn.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(qty_row, text="Upgrade:").pack(side="left", padx=(0, 4))
        self._edit_upg_entry = ctk.CTkEntry(
            qty_row, textvariable=self._edit_upg_var, width=45
        )
        self._edit_upg_entry.pack(side="left", padx=(0, 6))
        self._set_upg_btn = ctk.CTkButton(
            qty_row, text="Set Upgrade", width=110, command=self._set_upgrade_rows
        )
        self._set_upg_btn.pack(side="left")

        inf_row = ctk.CTkFrame(edits, fg_color="transparent")
        inf_row.pack(fill="x", pady=2)
        ctk.CTkLabel(inf_row, text="Infusion:", width=60, anchor="w").pack(side="left")
        self._edit_inf_icon, self._edit_inf_combo = self._infusion_widgets(
            inf_row, self._edit_inf_var, self._on_edit_infusion
        )
        self._set_inf_btn = ctk.CTkButton(
            inf_row, text="Set Infusion", width=110, command=self._set_infusion_rows
        )
        self._set_inf_btn.pack(side="left")

        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=(2, 2))
        self._to_storage_btn = ctk.CTkButton(
            btn_row,
            text="To Storage",
            width=100,
            command=lambda: self.move_entries(self.selected_offsets(), True),
        )
        self._to_storage_btn.pack(side="left", padx=(0, 4))
        self._to_inventory_btn = ctk.CTkButton(
            btn_row,
            text="To Inventory",
            width=100,
            command=lambda: self.move_entries(self.selected_offsets(), False),
        )
        self._to_inventory_btn.pack(side="left", padx=(0, 4))
        self._remove_btn = ctk.CTkButton(
            btn_row,
            text="Remove Selected",
            command=lambda: self.remove_entries(self.selected_offsets()),
            width=130,
            fg_color=("gray60", "gray35"),
            hover_color=("gray50", "gray25"),
        )
        self._remove_btn.pack(side="left")
        self._edit_info = ctk.CTkLabel(
            right, text="", font=("Segoe UI", 9), text_color=_HINT, anchor="w"
        )
        self._edit_info.grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8)
        )
        self._write_buttons = (
            self._set_qty_btn,
            self._set_upg_btn,
            self._set_inf_btn,
            self._to_storage_btn,
            self._to_inventory_btn,
            self._remove_btn,
            self._spawn_btn,
            self._spawn_all_btn,
        )

    @staticmethod
    def _inv_columns() -> list[tuple[str, str, int]]:
        return [
            ("name", "Item", 220),
            ("type", "Type", 70),
            ("qty", "Qty", 45),
            ("where", "Location", 70),
        ]

    @staticmethod
    def category_options() -> list[str]:
        return ["All", *catalog.CATEGORY_LABELS.values(), catalog.SPELLS_LABEL]

    # --- Refresh ----------------------------------------------------------- #

    def refresh(self) -> None:
        save = self._get_save()
        if save is None:
            self._slot_combo.configure(values=[])
            return
        options = [
            f"Slot {i + 1} - {c.name}" if c else f"Slot {i + 1} - Empty"
            for i, c in enumerate(save.characters)
        ]
        self._slot_combo.configure(values=options)
        if (
            0 <= self._current_slot < len(options)
            and save.characters[self._current_slot]
        ):
            self._slot_var.set(options[self._current_slot])
            self._reload_inventory()
        else:
            self._current_slot = -1
            self._slot_var.set(options[0] if options else "")
            self._clear_inventory()

    def load_slot(self, slot_idx: int) -> None:
        options = self._slot_combo.cget("values")
        if options and slot_idx < len(options):
            self._slot_var.set(options[slot_idx])
        self._current_slot = slot_idx
        self._reload_inventory()

    def _load_selected(self) -> None:
        idx = self._slot_idx()
        if idx < 0:
            return
        save = self._get_save()
        if save is None or save.characters[idx] is None:
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {idx + 1} is empty.", parent=self.parent
            )
            return
        self._current_slot = idx
        self._reload_inventory()

    # --- Inventory list ---------------------------------------------------- #

    def _clear_inventory(self) -> None:
        self._all_items = []
        self._inv_tree.delete(*self._inv_tree.get_children())
        self._set_error(None)

    def _set_error(self, message: str | None) -> None:
        if message:
            self._error_label.configure(
                text="Inventory editing is disabled for this character: "
                + message
                + ". Restore a backup from before the earlier edit to edit items again."
            )
            self._error_label.pack(fill="x", padx=12, pady=(0, 6), before=self._body)
        else:
            self._error_label.pack_forget()
        self.editing_error = message
        for btn in self._write_buttons:
            enable(btn, not message)
        self._apply_edit_states()
        self._apply_spawn_states()

    def _seamless_save(self) -> bool:
        """True when the loaded save is a Seamless Co-op (.co2) save, the
        only kind that may hold the mod's goods."""
        path = self._get_save_path()
        return path is not None and Path(path).suffix.lower() == ".co2"

    def current_character(self):
        save = self._get_save()
        if save is None or self._current_slot < 0:
            return None
        return save.characters[self._current_slot]

    def _reload_inventory(self) -> None:
        char = self.current_character()
        if char is None:
            self._clear_inventory()
            return
        if not self._spawn_tree_ready or self._spawn_seamless != self._seamless_save():
            self._spawn_tree_ready = True
            self.parent.after(0, self._refresh_spawn_tree)

        self._set_error(char.layout_error or char.inventory_error)
        self._all_items = []
        if not char.layout_error:
            source = self.source
            rows = [
                (e, WHERE_KEY if e.is_key else WHERE_HELD)
                for e in char.iter_inventory()
            ]
            rows += [(e, WHERE_STORAGE) for e in char.iter_storage()]
            for entry, where in rows:
                if (
                    not char.is_real_item(entry)
                    or entry.item_id in catalog.PLACEHOLDER_IDS
                ):
                    continue
                self._all_items.append(
                    (
                        entry.offset,
                        catalog.display_name(entry.item_id, source),
                        self._category_label(entry.item_id),
                        entry.quantity,
                        where,
                        entry.item_id,
                    )
                )
        self._refresh_inventory_tree()

    def _category_label(self, item_id: int) -> str:
        item = catalog.lookup(item_id, self.source)
        if item is not None and catalog.is_spell(item):
            return catalog.SPELLS_LABEL
        return catalog.CATEGORY_LABELS.get(
            catalog.category_of(item_id, self.source), "?"
        )

    def inventory_rows(
        self, query: str = "", category: str = "All", where: str = "All"
    ) -> list[tuple]:
        """Inventory rows filtered like the list (used by the visual editor)."""
        rows = self._all_items
        if query:
            rows = [r for r in rows if query in r[1].lower()]
        if category != "All":
            rows = [r for r in rows if r[2] == category]
        if where != "All":
            rows = [r for r in rows if r[4] == where]
        return rows

    def _refresh_inventory_tree(self) -> None:
        selected = set(self._inv_tree.selection()) | {str(o) for o in self.last_offsets}
        self._inv_tree.delete(*self._inv_tree.get_children())
        rows = self.inventory_rows(
            self._inv_search_var.get().strip().lower(),
            self._inv_cat_var.get(),
            self._inv_where_var.get(),
        )
        col_index = {"name": 1, "type": 2, "qty": 3, "where": 4}.get(
            self._sort_col or ""
        )
        if col_index is not None:
            rows = sorted(rows, key=lambda r: r[col_index], reverse=not self._sort_asc)
        for offset, name, cat, qty, where, _ in rows:
            self._inv_tree.insert(
                "", "end", iid=str(offset), values=(name, cat, qty, where)
            )
        keep = [iid for iid in self._inv_tree.get_children() if iid in selected]
        if keep:
            self._inv_tree.selection_set(keep)
        self._on_inv_select(None)

    def _sort_by(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True
        arrow = " ^" if self._sort_asc else " v"
        for c, heading, _ in self._inv_columns():
            self._inv_tree.heading(c, text=heading + (arrow if c == col else ""))
        self._refresh_inventory_tree()

    # --- Editing selected inventory rows ------------------------------------ #

    def selected_offsets(self) -> list[int]:
        return [int(iid) for iid in self._inv_tree.selection()]

    def row_for(self, offset: int) -> tuple | None:
        return next((r for r in self._all_items if r[0] == offset), None)

    def edit_options(self, offset: int) -> dict:
        """What can be edited for an inventory row: limits, infusion variants
        and whether the row can move between inventory and storage."""
        row = self.row_for(offset)
        if row is None:
            return {}
        item_id = row[5]
        item = catalog.lookup(item_id, self.source)
        lim = catalog.limits(item) if item else None
        is_weapon = id_kind(item_id) == ID_WEAPON
        return {
            "item": item,
            "limits": lim,
            "quantity": lim is not None and lim.max_quantity > 1,
            "upgrade": is_weapon and lim is not None and lim.max_upgrade > 0,
            "level": item_id % catalog.INFUSION_STEP if is_weapon else 0,
            "variants": catalog.infusion_variants(item, self.source)
            if item and "Infusion" in item
            else [],
            "movable": row[4] != WHERE_KEY,
            "in_storage": row[4] == WHERE_STORAGE,
        }

    def applicable_edits(self, offsets: list[int]) -> dict[str, bool]:
        """Which edits apply to a selection: one row enables what that item
        supports, several rows enable everything (each item is capped or
        skipped on its own), none enables nothing. All are off while
        inventory editing is disabled for the character."""
        opts = self.edit_options(offsets[0]) if len(offsets) == 1 else {}
        if opts:
            edits = {
                "quantity": opts["quantity"],
                "upgrade": opts["upgrade"],
                "infusion": bool(opts["variants"]),
                "to_storage": opts["movable"] and not opts["in_storage"],
                "to_inventory": opts["in_storage"],
                "remove": True,
            }
        else:
            many = len(offsets) > 1
            edits = dict.fromkeys(
                (
                    "quantity",
                    "upgrade",
                    "infusion",
                    "to_storage",
                    "to_inventory",
                    "remove",
                ),
                many,
            )
        if self.editing_error:
            edits = dict.fromkeys(edits, False)
        return edits

    def _apply_edit_states(self) -> None:
        edits = self.applicable_edits(self.selected_offsets())
        for widget, key in (
            (self._edit_qty_entry, "quantity"),
            (self._set_qty_btn, "quantity"),
            (self._edit_upg_entry, "upgrade"),
            (self._set_upg_btn, "upgrade"),
            (self._edit_inf_combo, "infusion"),
            (self._set_inf_btn, "infusion"),
            (self._to_storage_btn, "to_storage"),
            (self._to_inventory_btn, "to_inventory"),
            (self._remove_btn, "remove"),
        ):
            enable(widget, edits[key])

    def _on_inv_select(self, _event) -> None:
        self._apply_edit_states()
        offsets = self.selected_offsets()
        labels = self.infusion_labels()
        self._edit_inf_combo.configure(values=labels)
        if len(offsets) != 1:
            self._edit_info.configure(
                text=f"{len(offsets)} items selected" if offsets else ""
            )
            if self._edit_inf_var.get() not in labels:
                self._edit_inf_var.set(labels[0] if labels else "")
            self._on_edit_infusion(self._edit_inf_var.get())
            return
        opts = self.edit_options(offsets[0])
        if not opts:
            return
        row = self.row_for(offsets[0])
        self._edit_qty_var.set(str(row[3]))
        self._edit_upg_var.set(str(opts["level"]))
        lim = opts["limits"]
        info = [row[1]]
        if lim is not None and lim.max_quantity > 1:
            info.append(f"max {lim.max_quantity}")
        if lim is not None and lim.max_upgrade:
            info.append(f"max +{lim.max_upgrade}")
        self._edit_info.configure(text=", ".join(info))
        if opts["variants"]:
            self._edit_inf_combo.configure(
                values=[v["Infusion"] for v in opts["variants"]]
            )
            self._edit_inf_var.set(opts["item"]["Infusion"])
        self._on_edit_infusion(self._edit_inf_var.get())

    def _on_edit_infusion(self, label: str) -> None:
        index = next(
            (i for i, name in enumerate(self.infusion_labels()) if name == label), None
        )
        img = get_infusion_icon(index, self.source) if index is not None else None
        size = (_INFUSION_ICON_SIZE, _INFUSION_ICON_SIZE)
        self._edit_inf_icon.configure(
            image=ctk.CTkImage(light_image=img, dark_image=img, size=size)
            if img
            else None
        )

    def _read_int(self, var: tk.StringVar, what: str, parent) -> int | None:
        try:
            value = int(var.get())
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Value", f"{what} must be a whole number.", parent=parent
            )
            return None
        return value

    def _set_quantity_rows(self) -> None:
        qty = self._read_int(self._edit_qty_var, "Quantity", self.parent)
        if qty is not None:
            self.set_quantity(self.selected_offsets(), qty)

    def _set_upgrade_rows(self) -> None:
        level = self._read_int(self._edit_upg_var, "Upgrade", self.parent)
        if level is not None:
            self.set_upgrade(self.selected_offsets(), level)

    def _set_infusion_rows(self) -> None:
        self.set_infusion(self.selected_offsets(), self._edit_inf_var.get())

    # --- Batch operations (shared with the visual editor) ------------------ #

    def _begin(self, offsets: list[int], parent):
        """(save, save path, character) for a batch, or Nones after telling
        the user why nothing can be written."""
        if not offsets:
            CTkMessageBox.showwarning(
                "No Selection", "Select one or more items first.", parent=parent
            )
            return None, None, None
        if _game_blocks_write(parent):
            return None, None, None
        save, save_path, char = self._get_char()
        if char is None or self.editing_error:
            return None, None, None
        return save, save_path, char

    def _finish(self, save, save_path, op: str, message: str, changed: int) -> bool:
        if not changed:
            self._show_toast(message)
            return False
        return self._save(save, save_path, op, message)

    def set_quantity(self, offsets: list[int], quantity: int, parent=None) -> bool:
        parent = parent or self.parent
        save, save_path, char = self._begin(offsets, parent)
        if char is None:
            return False
        changed, capped, skipped = 0, 0, []
        for offset in offsets:
            row, opts = self.row_for(offset), self.edit_options(offset)
            if not opts or not opts["quantity"]:
                skipped.append(f"{row[1] if row else offset} (not stackable)")
                continue
            value = max(1, min(quantity, opts["limits"].max_quantity))
            capped += value != quantity
            if value != row[3]:
                char.set_quantity(char.entry_at(offset), value)
                changed += 1
        self.last_offsets = list(offsets)
        return self._finish(
            save,
            save_path,
            "ds3_set_quantity",
            _summary(f"Set quantity on {changed} item(s)", changed, skipped, capped),
            changed,
        )

    def set_upgrade(self, offsets: list[int], level: int, parent=None) -> bool:
        parent = parent or self.parent
        save, save_path, char = self._begin(offsets, parent)
        if char is None:
            return False
        changed, capped, skipped = 0, 0, []
        for offset in offsets:
            row, opts = self.row_for(offset), self.edit_options(offset)
            if not opts or not opts["upgrade"]:
                skipped.append(f"{row[1] if row else offset} (not upgradable)")
                continue
            value = max(0, min(level, opts["limits"].max_upgrade))
            capped += value != level
            if value != opts["level"]:
                char.set_weapon_level(char.entry_at(offset), value)
                changed += 1
        self.last_offsets = list(offsets)
        return self._finish(
            save,
            save_path,
            "ds3_set_upgrade",
            _summary(f"Set upgrade on {changed} weapon(s)", changed, skipped, capped),
            changed,
        )

    def set_infusion(self, offsets: list[int], infusion: str, parent=None) -> bool:
        """Give each selected weapon the named infusion, keeping its upgrade
        level (capped at the infused weapon's limit)."""
        parent = parent or self.parent
        save, save_path, char = self._begin(offsets, parent)
        if char is None:
            return False
        changed, capped, skipped = 0, 0, []
        for offset in offsets:
            row, opts = self.row_for(offset), self.edit_options(offset)
            target = next(
                (
                    v
                    for v in (opts or {}).get("variants", [])
                    if v["Infusion"] == infusion
                ),
                None,
            )
            if target is None:
                skipped.append(f"{row[1] if row else offset} (no {infusion} version)")
                continue
            lim = catalog.limits(target)
            level = min(opts["level"], lim.max_upgrade)
            capped += level != opts["level"]
            new_id = int(target["Id"], 16) + level
            if new_id != row[5]:
                try:
                    char.set_weapon_id(
                        char.entry_at(offset), new_id, lim.sort_key + level
                    )
                except (ValueError, LayoutError) as exc:
                    skipped.append(f"{row[1]} ({exc})")
                    continue
                changed += 1
        self.last_offsets = list(offsets)
        return self._finish(
            save,
            save_path,
            "ds3_set_infusion",
            _summary(
                f"Set {infusion} on {changed} weapon(s)", changed, skipped, capped
            ),
            changed,
        )

    def move_entries(self, offsets: list[int], to_storage: bool, parent=None) -> bool:
        """Move rows into the storage box or back into the inventory; rows
        already there and key items are skipped."""
        parent = parent or self.parent
        save, save_path, char = self._begin(offsets, parent)
        if char is None:
            return False
        moved, skipped = [], []
        for offset in offsets:
            row, opts = self.row_for(offset), self.edit_options(offset)
            if not opts:
                continue
            if not opts["movable"]:
                skipped.append(f"{row[1]} (key item)")
                continue
            if opts["in_storage"] == to_storage:
                continue
            lim = opts["limits"]
            try:
                entry = char.move_item(
                    char.entry_at(offset), lim.max_quantity if lim else 0
                )
            except (ValueError, LayoutError) as exc:
                skipped.append(f"{row[1]} ({exc})")
                continue
            moved.append(entry.offset)
        self.last_offsets = moved
        where = "storage box" if to_storage else "inventory"
        return self._finish(
            save,
            save_path,
            "ds3_move_to_storage" if to_storage else "ds3_move_to_inventory",
            _summary(f"Moved {len(moved)} item(s) to the {where}", len(moved), skipped),
            len(moved),
        )

    def remove_entries(self, offsets: list[int], parent=None) -> bool:
        parent = parent or self.parent
        save, save_path, char = self._begin(offsets, parent)
        if char is None:
            return False
        names = [self.row_for(o)[1] for o in offsets if self.row_for(o)]
        prompt = (
            f"Remove {names[0]}?" if len(names) == 1 else f"Remove {len(names)} items?"
        )
        if not CTkMessageBox.askyesno("Confirm Remove", prompt, parent=parent):
            return False
        removed, skipped = 0, []
        for offset in offsets:
            row = self.row_for(offset)
            entry = char.entry_at(offset)
            if row is None or entry is None:
                continue
            try:
                char.remove_item(entry)
            except (ValueError, LayoutError) as exc:
                skipped.append(f"{row[1]} ({exc})")
                continue
            removed += 1
        self.last_offsets = []
        return self._finish(
            save,
            save_path,
            "ds3_remove_items",
            _summary(f"Removed {removed} item(s)", removed, skipped),
            removed,
        )

    # --- Spawn list -------------------------------------------------------- #

    def _parse_category(self) -> tuple[str | None, bool | None]:
        """(category key or None, spell filter or None) for the spawn list."""
        label = self._spawn_cat_var.get()
        if label == "All":
            return None, None
        if label == catalog.SPELLS_LABEL:
            return "goods_items", True
        key = next(k for k, v in catalog.CATEGORY_LABELS.items() if v == label)
        return key, False if key == "goods_items" else None

    def _refresh_spawn_tree(self) -> None:
        if self._spawn_job is not None:
            self.parent.after_cancel(self._spawn_job)
            self._spawn_job = None
        self._spawn_tree.delete(*self._spawn_tree.get_children())
        self._spawn_rows.clear()
        self._spawn_variants = []
        self.select_item(None)

        query = self._spawn_search_var.get().strip().lower()
        cat_key, spell_filter = self._parse_category()
        show_cut = self._show_cut.get()
        source = self.source
        self._spawn_seamless = self._seamless_save()

        def label(item: dict) -> str:
            name = item["Name"]
            return name if catalog.is_obtainable(item) else f"{name} (cut)"

        rows: list[tuple[str, dict, list[dict]]] = []
        seen_families: set[int] = set()
        for db_cat, cat_items in catalog.items(source).items():
            if cat_key and db_cat != cat_key:
                continue
            for item in cat_items:
                if (
                    item["Name"].lower() in _HIDDEN_NAMES
                    or int(item["Id"], 16) in catalog.PLACEHOLDER_IDS
                ):
                    continue
                if not show_cut and not catalog.is_obtainable(item):
                    continue
                if catalog.is_seamless(item) and not self._spawn_seamless:
                    continue
                if spell_filter is not None and catalog.is_spell(item) != spell_filter:
                    continue
                if "Infusion" not in item:
                    if not query or query in item["Name"].lower():
                        rows.append((label(item), item, []))
                    continue
                # One row per weapon family, at its first member's position.
                family = int(item["Id"], 16) // catalog.WEAPON_FAMILY
                if family in seen_families:
                    continue
                seen_families.add(family)
                variants = [
                    v
                    for v in catalog.infusion_variants(item, source)
                    if show_cut or catalog.is_obtainable(v)
                ]
                matching = [
                    v for v in variants if not query or query in v["Name"].lower()
                ]
                if not matching:
                    continue
                # A search that names one infusion preselects it.
                first = matching[0] if query else variants[0]
                ordered = [first] + [v for v in variants if v is not first]
                rows.append(
                    (label(variants[0]), first, ordered if len(ordered) > 1 else [])
                )

        self._visible_spawn = rows
        self._insert_spawn_batch(rows, 0)

    _SPAWN_BATCH = 300

    def _insert_spawn_batch(self, rows: list, start: int) -> None:
        end = min(start + self._SPAWN_BATCH, len(rows))
        for label, item, variants in rows[start:end]:
            row_iid = self._spawn_tree.insert("", "end", values=(label,))
            self._spawn_rows[row_iid] = (item, variants)
        if end < len(rows):
            self._spawn_job = self.parent.after(
                0, lambda s=end: self._insert_spawn_batch(rows, s)
            )
        else:
            self._spawn_job = None

    def _on_spawn_select(self, _event) -> None:
        sel = self._spawn_tree.selection()
        if len(sel) != 1:
            self._spawn_variants = []
            self.select_item(None)
            if sel:
                self._spawn_info.configure(
                    text=f"{len(sel)} items selected; each is capped at its own limits"
                )
            return
        item, variants = self._spawn_rows[sel[0]]
        self._spawn_variants = variants
        if variants:
            self._spawn_inf_combo.configure(values=[v["Infusion"] for v in variants])
            self._spawn_inf_var.set(item["Infusion"])
        self.select_item(item)

    def _on_spawn_infusion(self, label: str) -> None:
        item = next((v for v in self._spawn_variants if v["Infusion"] == label), None)
        if item is not None:
            self.select_item(item)

    def select_item(self, item: dict | None) -> None:
        """Select a catalog item for spawning (also used by the visual picker)."""
        self._selected_db_item = item
        if item is None or not self._spawn_variants:
            self._spawn_inf_var.set("")
        self._spawn_inf_icon.configure(image=infusion_image(item, self.source))
        self._update_spawn_info()
        self._apply_spawn_states()

    def _apply_spawn_states(self) -> None:
        """Grey out spawn fields that do not apply to the single selected
        item; with several or no rows selected, quantity and upgrade apply
        (capped per item) and the infusion does not."""
        item = self._selected_db_item
        lim = catalog.limits(item) if item is not None else None
        single = len(self._spawn_tree.selection()) == 1 and lim is not None
        is_weapon = single and id_kind(int(item["Id"], 16)) == ID_WEAPON
        enable(self._spawn_qty_entry, not single or lim.max_quantity > 1)
        enable(self._spawn_upg_entry, not single or (is_weapon and lim.max_upgrade > 0))
        enable(self._spawn_inf_combo, single and bool(self._spawn_variants))

    def selected_limits(self) -> catalog.Limits | None:
        if self._selected_db_item is None:
            return None
        return catalog.limits(self._selected_db_item)

    def _update_spawn_info(self) -> None:
        lim = self.selected_limits()
        if lim is None:
            self._spawn_info.configure(text="")
            return
        parts = [f"Max stack: {lim.max_quantity}"]
        if lim.max_upgrade:
            parts.append(f"Max upgrade: +{lim.max_upgrade}")
        if lim.key_item:
            parts.append("Key item")
        if not catalog.is_obtainable(self._selected_db_item):
            parts.append("Cut content")
        self._spawn_info.configure(text="  ".join(parts))

    def category(self) -> str:
        return self._spawn_cat_var.get()

    def set_category(self, label: str) -> None:
        self._spawn_cat_var.set(label)
        self._refresh_spawn_tree()

    def visible_spawn_items(self) -> list[tuple[str, dict, list[dict]]]:
        """(label, item, infusion variants) rows listed in the spawn tree."""
        return list(self._visible_spawn)

    # --- Spawning ---------------------------------------------------------- #

    def _get_char(self):
        save = self._get_save()
        save_path = self._get_save_path()
        if save is None or save_path is None or self._current_slot < 0:
            return None, None, None
        return save, save_path, save.characters[self._current_slot]

    def _save(self, save, save_path, op: str, message: str) -> bool:
        try:
            _backup_and_save(save, save_path, f"{op}_slot_{self._current_slot + 1}")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)
            return False
        self._reload_inventory()
        self._show_toast(message)
        for listener in list(self.listeners):
            listener()
        return True

    def _spawn_selected_rows(self) -> None:
        sel = self._spawn_tree.selection()
        if len(sel) == 1 and self._selected_db_item is not None:
            # A single row spawns the infusion chosen in the dropdown.
            items = [self._selected_db_item]
        else:
            items = [self._spawn_rows[iid][0] for iid in sel]
        self.spawn_items(items)

    def _spawn_all_listed(self) -> None:
        self.spawn_items([item for _, item, _ in self._visible_spawn])

    def spawn_items(
        self,
        items: list[dict],
        quantity: int | None = None,
        upgrade: int | None = None,
        parent=None,
    ) -> bool:
        """Spawn catalog items with one backup and save. Quantity and upgrade
        (read from the tab's fields when not given) are capped per item."""
        parent = parent or self.parent
        if getattr(self, "_spawn_in_progress", False):
            return False
        self._spawn_in_progress = True
        try:
            return self._do_spawn(items, quantity, upgrade, parent)
        finally:
            self._spawn_in_progress = False

    def _do_spawn(self, items, quantity, upgrade, parent) -> bool:
        if not items:
            CTkMessageBox.showwarning(
                "No Item", "Select one or more items to spawn first.", parent=parent
            )
            return False
        if _game_blocks_write(parent):
            return False
        save, save_path, char = self._get_char()
        if char is None:
            CTkMessageBox.showwarning(
                "No Character", "Load a character first.", parent=parent
            )
            return False
        if self.editing_error:
            return False
        if quantity is None:
            quantity = self._read_int(self._spawn_qty_var, "Quantity", parent)
        if upgrade is None:
            upgrade = self._read_int(self._spawn_upg_var, "Upgrade", parent)
        if quantity is None or upgrade is None:
            return False
        if len(items) > _CONFIRM_SPAWN_COUNT and not CTkMessageBox.askyesno(
            "Spawn Items", f"Spawn {len(items)} items?", parent=parent
        ):
            return False
        cut = [i["Name"] for i in items if not catalog.is_obtainable(i)]
        if cut and not CTkMessageBox.askyesno(
            "Cut Content",
            f"{', '.join(cut[:5])}{' and more' if len(cut) > 5 else ''} "
            "cannot be obtained in the game data. Cut items can behave oddly "
            "and are likely to be flagged online.\n\nSpawn anyway?",
            parent=parent,
        ):
            return False

        to_storage = self.location_var.get() == LOCATIONS[1]
        spawned, capped, skipped = [], 0, []
        held_groups = {
            catalog.single_group(e.item_id)
            for e in [*char.iter_inventory(), *char.iter_storage()]
        }
        for item in items:
            lim = catalog.limits(item)
            item_id = int(item["Id"], 16)
            group = catalog.single_group(item_id)
            if group is not None:
                if group in held_groups:
                    skipped.append(
                        f"{item['Name']} (the character already has an {group}; "
                        "remove it first)"
                    )
                    continue
                held_groups.add(group)
            sort_key = lim.sort_key
            if id_kind(item_id) == ID_WEAPON and lim.max_upgrade:
                level = max(0, min(upgrade, lim.max_upgrade))
                capped += level != upgrade
                item_id += level
                sort_key += level
            qty = max(1, min(quantity, lim.max_quantity))
            capped += lim.max_quantity > 1 and qty != quantity
            wears = id_kind(item_id) in (ID_WEAPON, ID_ARMOR)
            try:
                char.add_item(
                    item_id,
                    qty,
                    sort_key=sort_key,
                    durability=lim.durability if wears else 0,
                    key_item=lim.key_item,
                    max_quantity=lim.max_quantity,
                    to_storage=to_storage and not lim.key_item,
                )
            except (ValueError, LayoutError) as exc:
                skipped.append(f"{item['Name']} ({exc})")
                continue
            spawned.append(catalog.display_name(item_id, self.source))
        where = "storage box" if to_storage else "inventory"
        done = (
            f"Spawned {spawned[0]} into the {where}"
            if len(spawned) == 1
            else f"Spawned {len(spawned)} items into the {where}"
        )
        return self._finish(
            save,
            save_path,
            "ds3_spawn_items",
            _summary(done, len(spawned), skipped, capped),
            len(spawned),
        )

    # --- Popups ------------------------------------------------------------ #

    def _require_character(self) -> bool:
        if self.current_character() is None:
            CTkMessageBox.showwarning(
                "No Character", "Load a character first.", parent=self.parent
            )
            return False
        return True

    def _open_visual_picker(self) -> None:
        if self._require_character():
            from er_save_manager.games.DS3.icon_browser import DS3IconBrowser

            DS3IconBrowser(self.parent.winfo_toplevel(), self)

    def _open_visual_editor(self) -> None:
        if self._require_character():
            from er_save_manager.games.DS3.visual_inventory import DS3VisualInventory

            DS3VisualInventory(self.parent.winfo_toplevel(), self)

    def _slot_idx(self) -> int:
        val = self._slot_var.get()
        if not val:
            return -1
        try:
            return int(val.split(" - ")[0].replace("Slot", "").strip()) - 1
        except (ValueError, IndexError):
            return -1
