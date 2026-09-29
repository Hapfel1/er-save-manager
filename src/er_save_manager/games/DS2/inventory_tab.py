"""
DS2 inventory editor panel.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk

from er_save_manager.games.DS2.item_database import (
    CATEGORIES,
    UNSAFE_IDS,
    _hex_id_to_int,
    build_item_db,
)
from er_save_manager.games.DS2.regulation import INFUSION_NAMES, Regulation
from er_save_manager.games.DS2.save import (
    MULTI_COPY_CATEGORIES,
    UNIQUE_CATEGORIES,
    UPGRADABLE_CATEGORIES,
    DS2Save,
)
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.scrollable_frame import ScrollableFrame
from er_save_manager.ui.utils import game_blocks_write


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(parent, "darksoulsii.exe", "Dark Souls II")


STACKABLE_CATEGORIES = ("goods", "bolts", "spells", "upgrade", "seamless")

# The game stores Estus Flask count and flask level packed into one value, so
# a plain quantity write would corrupt it.
_ESTUS_FLASK_ID = 0x0395E478

# Internal category key -> display label. Kept separate so backend calls
# (item_database lookups, Character.add_item/delete_entry) always use the
# lowercase key, while the UI only ever shows the capitalized label.
CATEGORY_LABELS = {
    "goods": "Goods",
    "weapons": "Weapons",
    "armors": "Armor",
    "rings": "Rings",
    "keys": "Key Items",
    "gestures": "Gestures",
    "bolts": "Bolts",
    "spells": "Spells",
    "upgrade": "Upgrade Materials",
    "seamless": "Seamless Co-op Items",
}
_DISPLAY_CATEGORIES = list(CATEGORY_LABELS.keys())

# Requested height of the browser/inventory split. Without it the paned
# window reports an unstable height and the surrounding scroll area never
# settles; below this height the tab scrolls instead of clipping.
_MIN_PANE_HEIGHT = 380

# Categories that are only offered in the Add Item browser for .co2 saves.
_SEAMLESS_CATEGORIES = frozenset({"seamless"})


_DISABLED_TEXT = ("gray60", "gray45")
_DISABLED_FILL = ("gray78", "gray28")
_HINT_COLOR = ("gray40", "gray60")
_HINT_FONT = ("Segoe UI", 11)


class _Greyable:
    """A customtkinter widget that can be greyed out and restored.

    kind is "entry", "combo", "button" or "label". Entries and labels have no
    disabled look of their own, so their text colour is swapped, and a button
    also swaps its fill so it does not stay the accent colour.
    """

    def __init__(self, widget, kind: str) -> None:
        self.widget = widget
        self.kind = kind
        self._text_color = (
            widget.cget("text_color") if kind in ("entry", "label") else None
        )
        self._fill = widget.cget("fg_color") if kind == "button" else None

    def set_enabled(self, enabled: bool) -> None:
        options = {}
        if self.kind != "label":
            on = "readonly" if self.kind == "combo" else "normal"
            options["state"] = on if enabled else "disabled"
        if self._text_color is not None:
            options["text_color"] = self._text_color if enabled else _DISABLED_TEXT
        if self._fill is not None:
            options["fg_color"] = self._fill if enabled else _DISABLED_FILL
        self.widget.configure(**options)


class DS2InventoryPanel:
    """
    Args:
        parent: parent widget the panel is built into.
        get_save: callable returning the current DS2Save, or None if unloaded.
        get_slot_index: callable returning the currently selected slot index.
        get_save_path: callable returning the current save file path.
        show_toast: callable(message, duration) for transient status messages.
    """

    def __init__(
        self,
        parent,
        get_save,
        get_slot_index: Callable[[], int],
        get_save_path,
        show_toast,
    ) -> None:
        self.parent = parent
        self.get_save = get_save
        self.get_slot_index = get_slot_index
        self.get_save_path = get_save_path
        self.show_toast = show_toast
        self._item_db = build_item_db()
        self._current_items: list[tuple] = []  # (item, name, category)
        self._search_results: list[str] = []
        self._visible_items: list[tuple] = []
        self._sort_column: str = "name"
        self._sort_reverse: bool = False
        # Only used for the Upgrade column. Edits load it on demand.
        self._regulation: Regulation | None = None
        # Widgets greyed out by _update_add_controls and
        # _update_inventory_controls, set once the panels are built.
        self._add_controls: dict[str, list[_Greyable]] | None = None
        self._set_controls: dict[str, list[_Greyable]] | None = None
        self._add_hints: dict[str, ctk.CTkLabel] = {}
        self._set_hints: dict[str, ctk.CTkLabel] = {}
        self._free_slots_label: ctk.CTkLabel | None = None

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        self.frame = ScrollableFrame(self.parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True)

        pane = tk.PanedWindow(
            self.frame,
            orient=tk.HORIZONTAL,
            sashwidth=6,
            sashrelief=tk.FLAT,
            bg="#2b2b2b",
            height=_MIN_PANE_HEIGHT,
        )
        pane.pack(fill="both", expand=True, padx=4, pady=4)

        left = ctk.CTkFrame(pane, fg_color=("gray88", "gray18"), corner_radius=8)
        right = ctk.CTkFrame(pane, fg_color=("gray88", "gray18"), corner_radius=8)
        pane.add(left, minsize=320, width=380)
        pane.add(right, minsize=360)

        self._build_browser_panel(left)
        self._build_inventory_panel(right)

        self.refresh()

    def _build_browser_panel(self, parent) -> None:
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(header, text="Add Item", font=("Segoe UI", 13, "bold")).pack(
            side="left"
        )
        ctk.CTkButton(
            header,
            text="Visual Picker...",
            width=120,
            height=26,
            command=self._open_icon_browser,
        ).pack(side="right")

        cat_row = ctk.CTkFrame(parent, fg_color="transparent")
        cat_row.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(cat_row, text="Category:", width=70).pack(side="left")
        self.add_category_var = tk.StringVar(
            value=CATEGORY_LABELS[_DISPLAY_CATEGORIES[0]]
        )
        self._add_category_combo = ctk.CTkComboBox(
            cat_row,
            variable=self.add_category_var,
            values=self._visible_add_labels(),
            state="readonly",
            width=160,
            command=lambda _v: self._search_items(),
        )
        self._add_category_combo.pack(side="left", padx=(0, 6))

        search_row = ctk.CTkFrame(parent, fg_color="transparent")
        search_row.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(search_row, text="Search:", width=70).pack(side="left")
        self.add_search_var = tk.StringVar()
        self.add_search_var.trace_add("write", lambda *_: self._search_items())
        ctk.CTkEntry(search_row, textvariable=self.add_search_var, width=200).pack(
            side="left", padx=(0, 6)
        )

        ctk.CTkLabel(
            parent,
            text="Ctrl or Shift+click selects several items",
            text_color=("gray40", "gray60"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=10, pady=(0, 2))

        # Pack order decides which widgets are clipped when the parent is short.
        # The button and quantity row are packed to the bottom first so they
        # always keep their space, and the tree takes whatever remains.
        button_row = ctk.CTkFrame(parent, fg_color="transparent")
        button_row.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        add_selected = ctk.CTkButton(
            button_row, text="Add Selected", command=self._on_add, height=32
        )
        add_selected.pack(side="left", fill="x", expand=True, padx=(0, 3))
        add_all = ctk.CTkButton(
            button_row, text="Add All Listed", command=self._on_add_all, height=32
        )
        add_all.pack(side="left", fill="x", expand=True, padx=(3, 0))

        self._free_slots_label = ctk.CTkLabel(
            parent, text="", text_color=_HINT_COLOR, font=_HINT_FONT
        )
        self._free_slots_label.pack(side="bottom", anchor="w", padx=10, pady=(0, 4))

        infusion_row = ctk.CTkFrame(parent, fg_color="transparent")
        infusion_row.pack(side="bottom", fill="x", padx=10, pady=(0, 6))
        infusion_label = ctk.CTkLabel(infusion_row, text="Infusion:", width=70)
        infusion_label.pack(side="left")
        self.add_infusion_var = tk.StringVar(value=INFUSION_NAMES[0])
        self._add_infusion_combo = ctk.CTkComboBox(
            infusion_row,
            variable=self.add_infusion_var,
            values=list(INFUSION_NAMES),
            state="readonly",
            width=120,
        )
        self._add_infusion_combo.pack(side="left")
        self._add_hints["infusion"] = ctk.CTkLabel(
            infusion_row, text="", text_color=_HINT_COLOR, font=_HINT_FONT
        )
        self._add_hints["infusion"].pack(side="left", padx=(8, 0))

        qty_row = ctk.CTkFrame(parent, fg_color="transparent")
        qty_row.pack(side="bottom", fill="x", padx=10, pady=(0, 6))
        qty_label = ctk.CTkLabel(qty_row, text="Quantity:", width=70)
        qty_label.pack(side="left")
        self.add_qty_var = tk.StringVar(value="1")
        qty_entry = ctk.CTkEntry(qty_row, textvariable=self.add_qty_var, width=60)
        qty_entry.pack(side="left")
        self._add_hints["quantity"] = ctk.CTkLabel(
            qty_row, text="", text_color=_HINT_COLOR, font=_HINT_FONT
        )
        self._add_hints["quantity"].pack(side="left", padx=(6, 0))
        upgrade_label = ctk.CTkLabel(qty_row, text="Upgrade:")
        upgrade_label.pack(side="left", padx=(10, 4))
        self.add_upgrade_var = tk.StringVar(value="0")
        upgrade_entry = ctk.CTkEntry(
            qty_row, textvariable=self.add_upgrade_var, width=50
        )
        upgrade_entry.pack(side="left")
        self._add_hints["upgrade"] = ctk.CTkLabel(
            qty_row, text="", text_color=_HINT_COLOR, font=_HINT_FONT
        )
        self._add_hints["upgrade"].pack(side="left", padx=(6, 0))

        self._results_tree = ttk.Treeview(
            parent,
            columns=("name",),
            show="headings",
            height=6,
            selectmode="extended",
        )
        self._results_tree.heading("name", text="Item")
        self._results_tree.column("name", width=260)
        self._results_tree.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._results_tree.bind(
            "<<TreeviewSelect>>", lambda _e: self._update_add_controls()
        )

        self._add_controls = {
            "quantity": [_Greyable(qty_label, "label"), _Greyable(qty_entry, "entry")],
            "upgrade": [
                _Greyable(upgrade_label, "label"),
                _Greyable(upgrade_entry, "entry"),
            ],
            "infusion": [
                _Greyable(infusion_label, "label"),
                _Greyable(self._add_infusion_combo, "combo"),
            ],
            "add_selected": [_Greyable(add_selected, "button")],
            "add_all": [_Greyable(add_all, "button")],
        }
        self._search_items()

    def _build_inventory_panel(self, parent) -> None:
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(
            header, text="Current Inventory", font=("Segoe UI", 13, "bold")
        ).pack(side="left")
        ctk.CTkButton(
            header,
            text="Visual View...",
            width=110,
            height=26,
            command=self._open_visual_inventory,
        ).pack(side="right")

        filter_row = ctk.CTkFrame(parent, fg_color="transparent")
        filter_row.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(filter_row, text="Category:", width=70).pack(side="left")
        self.filter_category_var = tk.StringVar(value="All")
        ctk.CTkComboBox(
            filter_row,
            variable=self.filter_category_var,
            values=["All"] + list(CATEGORY_LABELS.values()),
            state="readonly",
            width=160,
            command=lambda _v: self._apply_filter(),
        ).pack(side="left", padx=(0, 6))

        search_row = ctk.CTkFrame(parent, fg_color="transparent")
        search_row.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(search_row, text="Filter:", width=70).pack(side="left")
        self.filter_search_var = tk.StringVar()
        self.filter_search_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(search_row, textvariable=self.filter_search_var, width=200).pack(
            side="left", padx=(0, 6)
        )

        columns = ("name", "category", "quantity", "upgrade", "infusion")
        # Action rows are packed to the bottom first so they are never clipped.
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        upgrade_actions = ctk.CTkFrame(parent, fg_color="transparent")
        upgrade_actions.pack(side="bottom", fill="x", padx=10, pady=(0, 6))
        infusion_actions = ctk.CTkFrame(parent, fg_color="transparent")
        infusion_actions.pack(side="bottom", fill="x", padx=10, pady=(0, 6))

        self._inventory_tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=6,
            selectmode="extended",
        )
        self._column_labels = {
            "name": "Name",
            "category": "Category",
            "quantity": "Qty",
            "upgrade": "Upgrade",
            "infusion": "Infusion",
        }
        for col, label, width in (
            ("name", "Name", 190),
            ("category", "Category", 90),
            ("quantity", "Qty", 45),
            ("upgrade", "Upgrade", 65),
            ("infusion", "Infusion", 80),
        ):
            self._inventory_tree.heading(
                col, text=label, command=lambda c=col: self._sort_by(c)
            )
            self._inventory_tree.column(col, width=width)
        self._inventory_tree.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        remove_button = ctk.CTkButton(
            actions, text="Remove Selected", command=self._on_remove, width=130
        )
        remove_button.pack(side="left", padx=(0, 6))
        qty_label = ctk.CTkLabel(actions, text="New qty:")
        qty_label.pack(side="left", padx=(10, 4))
        self.set_qty_var = tk.StringVar(value="1")
        qty_entry = ctk.CTkEntry(actions, textvariable=self.set_qty_var, width=60)
        qty_entry.pack(side="left")
        qty_button = ctk.CTkButton(
            actions, text="Set Quantity", command=self._on_set_quantity, width=110
        )
        qty_button.pack(side="left", padx=6)

        upgrade_label = ctk.CTkLabel(upgrade_actions, text="New upgrade:")
        upgrade_label.pack(side="left", padx=(0, 4))
        self.set_upgrade_var = tk.StringVar(value="0")
        upgrade_entry = ctk.CTkEntry(
            upgrade_actions, textvariable=self.set_upgrade_var, width=60
        )
        upgrade_entry.pack(side="left")
        upgrade_button = ctk.CTkButton(
            upgrade_actions,
            text="Set Upgrade",
            command=self._on_set_upgrade,
            width=110,
        )
        upgrade_button.pack(side="left", padx=6)
        self._set_hints["upgrade"] = ctk.CTkLabel(
            upgrade_actions, text="", text_color=_HINT_COLOR, font=_HINT_FONT
        )
        self._set_hints["upgrade"].pack(side="left")

        infusion_label = ctk.CTkLabel(infusion_actions, text="New infusion:")
        infusion_label.pack(side="left", padx=(0, 4))
        self.set_infusion_var = tk.StringVar(value=INFUSION_NAMES[0])
        self._set_infusion_combo = ctk.CTkComboBox(
            infusion_actions,
            variable=self.set_infusion_var,
            values=list(INFUSION_NAMES),
            state="readonly",
            width=110,
        )
        self._set_infusion_combo.pack(side="left")
        infusion_button = ctk.CTkButton(
            infusion_actions,
            text="Set Infusion",
            command=self._on_set_infusion,
            width=110,
        )
        infusion_button.pack(side="left", padx=6)
        self._set_hints["infusion"] = ctk.CTkLabel(
            infusion_actions, text="", text_color=_HINT_COLOR, font=_HINT_FONT
        )
        self._set_hints["infusion"].pack(side="left")

        self._inventory_tree.bind(
            "<<TreeviewSelect>>", lambda _e: self._update_inventory_controls()
        )
        self._set_controls = {
            "remove": [_Greyable(remove_button, "button")],
            "quantity": [
                _Greyable(qty_label, "label"),
                _Greyable(qty_entry, "entry"),
                _Greyable(qty_button, "button"),
            ],
            "upgrade": [
                _Greyable(upgrade_label, "label"),
                _Greyable(upgrade_entry, "entry"),
                _Greyable(upgrade_button, "button"),
            ],
            "infusion": [
                _Greyable(infusion_label, "label"),
                _Greyable(self._set_infusion_combo, "combo"),
                _Greyable(infusion_button, "button"),
            ],
        }
        self._update_inventory_controls()

    def _open_icon_browser(self) -> None:
        from er_save_manager.games.DS2.icon_browser import IconBrowser
        from er_save_manager.games.DS2.icon_manager import icons_available

        if not icons_available():
            self.show_toast(
                "No icons.db found; run build_icon_db.py to enable icons",
                duration=3500,
            )
        IconBrowser(self.parent, self, initial_category=self._selected_add_category())

    def _open_visual_inventory(self) -> None:
        from er_save_manager.games.DS2.icon_manager import icons_available
        from er_save_manager.games.DS2.visual_inventory import VisualInventoryBrowser

        if not icons_available():
            self.show_toast(
                "No icons.db found; run build_icon_db.py to enable icons",
                duration=3500,
            )
        VisualInventoryBrowser(self.parent, self)

    # ------------------------------------------------------------------
    # Left panel: item browser
    # ------------------------------------------------------------------

    def _is_co2(self) -> bool:
        path = self.get_save_path()
        return bool(path) and Path(path).suffix.lower() == ".co2"

    def _visible_add_labels(self) -> list[str]:
        """Add Item category labels for the current save. Seamless Co-op
        categories are only offered for .co2 saves."""
        is_co2 = self._is_co2()
        return [
            label
            for key, label in CATEGORY_LABELS.items()
            if key not in _SEAMLESS_CATEGORIES or is_co2
        ]

    def refresh_category_visibility(self) -> None:
        """Re-evaluate the Add Item categories after the save path changes."""
        labels = self._visible_add_labels()
        self._add_category_combo.configure(values=labels)
        if self.add_category_var.get() not in labels:
            self.add_category_var.set(labels[0])
            self._search_items()

    def _selected_add_category(self) -> str:
        label = self.add_category_var.get()
        for key, value in CATEGORY_LABELS.items():
            if value == label:
                return key
        return _DISPLAY_CATEGORIES[0]

    def _search_items(self) -> None:
        category = self._selected_add_category()
        query = self.add_search_var.get().strip().lower()
        names = sorted(CATEGORIES.get(category, {}).keys())
        if query:
            names = [n for n in names if query in n.lower()]

        self._results_tree.delete(*self._results_tree.get_children())
        self._search_results = names
        for name in names:
            self._results_tree.insert("", "end", values=(name,))
        self._update_add_controls()

    def _current_character(self):
        save: DS2Save | None = self.get_save()
        return save.characters[self.get_slot_index()] if save is not None else None

    @staticmethod
    def _apply_group(
        group: list[_Greyable],
        enabled: bool,
        var: tk.StringVar | None,
        default: str,
        value: str | None = None,
    ) -> None:
        """Enable or grey out a control group. Enabling sets the given value,
        and greying out returns the field to its default, so a hidden value is
        never used."""
        for control in group:
            control.set_enabled(enabled)
        if var is None:
            return
        if not enabled:
            var.set(default)
        elif value is not None:
            var.set(value)

    @staticmethod
    def _apply_infusion_choices(combo, var: tk.StringVar, allowed: tuple[int, ...]):
        """Offer only the given infusions, falling back to Normal when the
        current choice is no longer offered."""
        names = [INFUSION_NAMES[n] for n in allowed]
        combo.configure(values=names)
        if var.get() not in names:
            var.set(INFUSION_NAMES[0])

    def _update_add_controls(self) -> None:
        """Grey out the add fields that do not apply and update their hints. The
        category decides first, then with a single item selected the item does:
        a stack limit of 1 removes Quantity, an item with no upgrade levels
        removes Upgrade, and Infusion offers only what that weapon allows. The
        free slot count follows the category."""
        if self._add_controls is None:
            return

        category = self._selected_add_category()
        is_spell = category == "spells"
        quantity = (
            category in STACKABLE_CATEGORIES or category in MULTI_COPY_CATEGORIES
        ) and not is_spell
        upgrade = category in UPGRADABLE_CATEGORIES
        infusion = category == "weapons"
        allowed = tuple(range(len(INFUSION_NAMES)))
        upgrade_hint = "capped per item" if upgrade else ""
        infusion_hint = "plain if not allowed" if infusion else ""
        quantity_hint = "always added with full uses" if is_spell else ""

        selection = self._results_tree.selection()
        character = self._current_character()
        if len(selection) == 1 and character is not None:
            name = self._results_tree.item(selection[0], "values")[0]
            hex_id = CATEGORIES.get(category, {}).get(name)
            item_id = _hex_id_to_int(hex_id) if hex_id else None
            if item_id is not None:
                if category in STACKABLE_CATEGORIES and not is_spell:
                    quantity = character.max_stack(item_id) > 1
                if upgrade:
                    limit = character.max_upgrade(item_id, category)
                    upgrade = limit > 0
                    upgrade_hint = f"max +{limit}" if upgrade else ""
                if infusion:
                    allowed = character.allowed_infusions(item_id)
                    infusion = len(allowed) > 1
                    infusion_hint = (
                        f"{len(allowed) - 1} of {len(INFUSION_NAMES) - 1} allowed"
                        if infusion
                        else ""
                    )

        controls = self._add_controls
        self._apply_group(controls["quantity"], quantity, self.add_qty_var, "1")
        self._apply_group(controls["upgrade"], upgrade, self.add_upgrade_var, "0")
        self._apply_group(
            controls["infusion"], infusion, self.add_infusion_var, INFUSION_NAMES[0]
        )
        self._apply_infusion_choices(
            self._add_infusion_combo, self.add_infusion_var, allowed
        )
        self._apply_group(controls["add_selected"], bool(selection), None, "")
        self._apply_group(controls["add_all"], bool(self._search_results), None, "")

        self._add_hints["upgrade"].configure(text=upgrade_hint if upgrade else "")
        self._add_hints["infusion"].configure(text=infusion_hint if infusion else "")
        self._add_hints["quantity"].configure(text=quantity_hint)
        free = character.free_slots(category) if character is not None else None
        self._free_slots_label.configure(
            text="Free slots: -" if free is None else f"Free slots: {free}"
        )

    def _on_add(self) -> None:
        if _game_blocks_write(self.parent):
            return

        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return

        selection = self._results_tree.selection()
        if not selection:
            self.show_toast("Select an item to add", duration=2000)
            return
        if len(selection) > 1:
            names = [self._results_tree.item(row, "values")[0] for row in selection]
            self._add_many(save, names)
            return

        item_name = self._results_tree.item(selection[0], "values")[0]
        category = self._selected_add_category()
        hex_id = CATEGORIES.get(category, {}).get(item_name)
        if hex_id is None:
            self.show_toast("Item not found in database", duration=2000)
            return

        inputs = self._read_add_inputs()
        if inputs is None:
            return
        quantity, upgrade, infusion = inputs

        item_id = _hex_id_to_int(hex_id)
        if item_id in UNSAFE_IDS and not CTkMessageBox.askyesno(
            "Unsafe item",
            f"{item_name} is flagged unsafe.\n\n"
            "Adding it can get an account soft-banned online.\n\n"
            "Add it anyway? (Safe on SeamlessCoop saves)",
            parent=self.parent,
        ):
            return
        character = save.characters[self.get_slot_index()]
        if category in UNIQUE_CATEGORIES and character.owns(item_id):
            self.show_toast(f"{item_name} is already owned", duration=2000)
            return
        if category in STACKABLE_CATEGORIES and category != "spells":
            stack_limit = character.max_stack(item_id)
            if quantity > stack_limit:
                quantity = stack_limit
                self.show_toast(f"Quantity capped at {stack_limit}", duration=2000)
        capped = False
        if category in UPGRADABLE_CATEGORIES and upgrade > 0:
            if self._load_regulation(save) is None:
                return
            limit = character.max_upgrade(item_id, category)
            capped = upgrade > limit
            upgrade = min(upgrade, limit)
        else:
            upgrade = 0
        if category != "weapons":
            infusion = 0
        elif infusion > 0:
            if self._load_regulation(save) is None:
                return
            allowed = character.allowed_infusions(item_id)
            if infusion not in allowed:
                names = ", ".join(INFUSION_NAMES[n] for n in allowed)
                self.show_toast(f"{item_name} allows: {names}", duration=3500)
                return

        copies = quantity if category in MULTI_COPY_CATEGORIES else 1
        if category in MULTI_COPY_CATEGORIES:
            written = character.add_copies(
                item_id, category, copies, upgrade=upgrade, infusion=infusion
            )
        else:
            written = int(
                character.add_item(
                    item_id, category, quantity=quantity, upgrade=upgrade
                )
            )
        if not written:
            self.show_toast("No empty inventory slot available", duration=2500)
            return

        self._write_and_refresh(save, operation="add_item")
        self._reset_inputs()
        label = f"{written}x {item_name}" if written > 1 else item_name
        if upgrade:
            label += f" +{upgrade}"
        if infusion:
            label += f" {INFUSION_NAMES[infusion]}"
        suffix = " (capped at max upgrade)" if capped else ""
        if written < copies:
            suffix += f", only {written} of {copies} fit"
        self.show_toast(f"Added {label}{suffix}", duration=3000)

    def _on_add_all(self) -> None:
        save = self._writable_save()
        if save is None:
            return
        if not self._search_results:
            self.show_toast("No items listed", duration=2000)
            return
        self._add_many(save, list(self._search_results))

    def _writable_save(self) -> DS2Save | None:
        if _game_blocks_write(self.parent):
            return None
        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
        return save

    def _read_add_inputs(self) -> tuple[int, int, int] | None:
        """Parse the add fields as (quantity, upgrade, infusion index). Shows a
        toast and returns None when the quantity or upgrade is invalid."""
        try:
            quantity = int(self.add_qty_var.get())
            upgrade = int(self.add_upgrade_var.get())
        except ValueError:
            self.show_toast("Quantity and upgrade must be numbers", duration=2000)
            return None
        if quantity < 1:
            self.show_toast("Quantity must be at least 1", duration=2000)
            return None
        if upgrade < 0:
            self.show_toast("Upgrade cannot be negative", duration=2000)
            return None
        return quantity, upgrade, INFUSION_NAMES.index(self.add_infusion_var.get())

    def _reset_inputs(self) -> None:
        """Return every quantity, upgrade and infusion field to its default so
        a previous edit does not carry into the next one."""
        self.add_qty_var.set("1")
        self.add_upgrade_var.set("0")
        self.add_infusion_var.set(INFUSION_NAMES[0])
        self.set_qty_var.set("1")
        self.set_upgrade_var.set("0")
        self.set_infusion_var.set(INFUSION_NAMES[0])

    def _load_regulation(self, save: DS2Save, quiet: bool = False) -> Regulation | None:
        """Upgrade caps of the loaded save, or None if its regulation cannot
        be read. Edits that need caps must not proceed on None."""
        try:
            return save.regulation
        except ValueError as e:
            if not quiet:
                self.show_toast(f"Cannot read upgrade caps: {e}", duration=3500)
            return None

    def _add_many(self, save: DS2Save, names: list[str]) -> None:
        """Add several items of the selected category in one write."""
        inputs = self._read_add_inputs()
        if inputs is None:
            return
        quantity, upgrade, infusion = inputs

        category = self._selected_add_category()
        table = CATEGORIES.get(category, {})
        item_ids = [
            item_id
            for item_id in (_hex_id_to_int(table[n]) for n in names if n in table)
            if item_id is not None
        ]
        safe_ids = [i for i in item_ids if i not in UNSAFE_IDS]
        unsafe_count = len(item_ids) - len(safe_ids)
        if not safe_ids:
            self.show_toast("No addable items", duration=2000)
            return

        if (category in UPGRADABLE_CATEGORIES and upgrade > 0) or (
            category == "weapons" and infusion > 0
        ):
            if self._load_regulation(save) is None:
                return

        lines = [f"Add {len(safe_ids)} {CATEGORY_LABELS[category]} item(s)?"]
        if category == "spells":
            lines.append(
                "Each is added as a new entry with a full set of uses. "
                "Copies already owned do not block it."
            )
        elif category in STACKABLE_CATEGORIES:
            lines.append(
                f"Quantity {quantity}, capped per item at its stack limit. "
                "Owned stacks are set to it."
            )
        elif category in MULTI_COPY_CATEGORIES:
            lines.append(
                f"{quantity} of each. Copies already owned with the same "
                "upgrade and infusion count toward it."
            )
        else:
            lines.append("Items already owned are skipped.")
        if category in UPGRADABLE_CATEGORIES and upgrade > 0:
            lines.append(f"Upgrade +{upgrade}, capped per item at its maximum.")
        if category == "weapons" and infusion > 0:
            lines.append(
                f"{INFUSION_NAMES[infusion]} infusion. Weapons that do not allow "
                "it are added plain."
            )
        if unsafe_count:
            lines.append(f"{unsafe_count} unsafe item(s) will be skipped.")
        if not CTkMessageBox.askyesno(
            "Add items", "\n\n".join(lines), parent=self.parent
        ):
            return

        character = save.characters[self.get_slot_index()]
        result = character.add_items_bulk(
            safe_ids,
            category,
            quantity=quantity,
            upgrade=upgrade,
            infusion=infusion,
        )
        summary = ", ".join(
            f"{count} {label}"
            for count, label in (
                (result.added, "added"),
                (result.updated, "updated"),
                (result.skipped_owned, "already owned"),
                (result.clamped, "capped at max upgrade"),
                (result.infusion_fallback, "added plain, infusion not allowed"),
                (result.no_space, "no space"),
                (unsafe_count, "unsafe skipped"),
            )
            if count
        )
        if result.added or result.updated:
            self._write_and_refresh(save, operation="add_items_bulk")
            self._reset_inputs()
        self.show_toast(summary or "Nothing changed", duration=4000)

    # ------------------------------------------------------------------
    # Right panel: current inventory
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        self.refresh_category_visibility()
        save: DS2Save | None = self.get_save()
        self._current_items = []
        self._regulation = (
            self._load_regulation(save, quiet=True) if save is not None else None
        )
        if save is not None:
            character = save.characters[self.get_slot_index()]
            for item in character.inventory() + character.key_items():
                if item.item_id == 0:
                    continue
                info = self._item_db.get(item.item_id)
                name, category = info if info else (f"Unknown ({item.item_id})", None)
                self._current_items.append((item, name, category))
        self._apply_filter()
        self._update_add_controls()

    def _sort_by(self, column: str) -> None:
        if self._sort_column == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column
            self._sort_reverse = False

        for col, label in self._column_labels.items():
            if col == self._sort_column:
                arrow = " \u25bc" if self._sort_reverse else " \u25b2"
                self._inventory_tree.heading(col, text=label + arrow)
            else:
                self._inventory_tree.heading(col, text=label)

        self._apply_filter()

    def _apply_filter(self) -> None:
        category_label = self.filter_category_var.get()
        query = self.filter_search_var.get().strip().lower()

        rows = []
        for item, name, item_category in self._current_items:
            display_category = CATEGORY_LABELS.get(item_category, "Unknown")
            if category_label != "All" and display_category != category_label:
                continue
            if query and query not in name.lower():
                continue
            qty = item.quantity if item_category in STACKABLE_CATEGORIES else -1
            level = item.upgrade if item_category in UPGRADABLE_CATEGORIES else -1
            infusion = item.infusion if item_category == "weapons" else -1
            rows.append(
                (item, name, item_category, display_category, qty, level, infusion)
            )

        sort_key = {
            "name": lambda r: r[1].lower(),
            "category": lambda r: r[3].lower(),
            "quantity": lambda r: r[4],
            "upgrade": lambda r: r[5],
            "infusion": lambda r: r[6],
        }.get(self._sort_column, lambda r: r[1].lower())
        rows.sort(key=sort_key, reverse=self._sort_reverse)

        self._inventory_tree.delete(*self._inventory_tree.get_children())
        self._visible_items = []
        for item, name, item_category, display_category, qty, level, infusion in rows:
            self._visible_items.append((item, name, item_category))
            qty_str = str(qty) if qty >= 0 else ""
            level_str = ""
            if level >= 0:
                level_str = f"+{level}"
                if self._regulation is not None:
                    limit = self._regulation.max_upgrade(item.item_id, item_category)
                    level_str += f"/{limit}"
            infusion_str = ""
            if infusion >= 0:
                infusion_str = (
                    INFUSION_NAMES[infusion]
                    if infusion < len(INFUSION_NAMES)
                    else f"Unknown ({infusion})"
                )
            self._inventory_tree.insert(
                "",
                "end",
                values=(name, display_category, qty_str, level_str, infusion_str),
            )
        self._update_inventory_controls()

    def _selected_inventory_rows(self) -> list[tuple]:
        """(item, name, category) of every selected inventory row."""
        return [
            self._visible_items[self._inventory_tree.index(row)]
            for row in self._inventory_tree.selection()
        ]

    @staticmethod
    def _quantity_limit(character, item, category) -> int:
        """Largest quantity Set Quantity can write for a row, or 0 when the row
        takes none. The Estus Flask packs its count with its level. A spell's
        uses are always its cap, in game and here, so it never takes a custom
        quantity either."""
        if (
            category not in STACKABLE_CATEGORIES
            or category == "spells"
            or item.item_id == _ESTUS_FLASK_ID
        ):
            return 0
        limit = character.max_stack(item.item_id)
        return limit if limit > 1 else 0

    @staticmethod
    def _upgrade_limit(character, item, category) -> int:
        """Highest upgrade level of a row, or 0 when it has none."""
        if category not in UPGRADABLE_CATEGORIES:
            return 0
        return character.max_upgrade(item.item_id, category)

    @staticmethod
    def _infusion_choices(character, item, category) -> tuple[int, ...]:
        """Infusions a row can take, or empty when it can only stay plain."""
        if category != "weapons":
            return ()
        allowed = character.allowed_infusions(item.item_id)
        return allowed if len(allowed) > 1 else ()

    @staticmethod
    def _common(values: list[int], default: int) -> int:
        """The value shared by every row, else the default."""
        return values[0] if values and all(v == values[0] for v in values) else default

    def _update_inventory_controls(self) -> None:
        """Grey out the edit controls that do not apply to the selection and
        fill the Set fields with the current values. Remove needs a selection.
        Each Set control needs at least one selected row that takes it, and
        acts on every such row. Hints show the limits."""
        if self._set_controls is None:
            return

        picked = self._selected_inventory_rows()
        character = self._current_character()
        quantity_rows, upgrade_rows, infusion_rows = [], [], []
        if character is not None:
            for row in picked:
                item, _name, category = row
                if self._quantity_limit(character, item, category):
                    quantity_rows.append(row)
                if self._upgrade_limit(character, item, category):
                    upgrade_rows.append(row)
                if self._infusion_choices(character, item, category):
                    infusion_rows.append(row)

        controls = self._set_controls
        self._apply_group(controls["remove"], bool(picked), None, "")

        self._apply_group(
            controls["quantity"],
            bool(quantity_rows),
            self.set_qty_var,
            "1",
            str(self._common([item.quantity for item, _, _ in quantity_rows], 1)),
        )

        limits = [self._upgrade_limit(character, i, c) for i, _, c in upgrade_rows]
        upgrade_hint = ""
        if limits:
            lo, hi = min(limits), max(limits)
            upgrade_hint = f"max +{lo}" if lo == hi else f"max +{lo} to +{hi}"
        self._apply_group(
            controls["upgrade"],
            bool(upgrade_rows),
            self.set_upgrade_var,
            "0",
            str(self._common([item.upgrade for item, _, _ in upgrade_rows], 0)),
        )
        self._set_hints["upgrade"].configure(text=upgrade_hint)

        offered = sorted(
            {
                n
                for i, _, c in infusion_rows
                for n in self._infusion_choices(character, i, c)
            }
        ) or [0]
        current = self._common([item.infusion for item, _, _ in infusion_rows], 0)
        self._apply_infusion_choices(
            self._set_infusion_combo, self.set_infusion_var, tuple(offered)
        )
        self._apply_group(
            controls["infusion"],
            bool(infusion_rows),
            self.set_infusion_var,
            INFUSION_NAMES[0],
            INFUSION_NAMES[current if current in offered else 0],
        )
        infusion_hint = ""
        if len(infusion_rows) == 1:
            infusion_hint = f"{len(offered) - 1} of {len(INFUSION_NAMES) - 1} allowed"
        elif infusion_rows:
            infusion_hint = "skips unsupported"
        self._set_hints["infusion"].configure(text=infusion_hint)

    def _on_remove(self) -> None:
        save = self._writable_save()
        if save is None:
            return

        selection = self._inventory_tree.selection()
        if not selection:
            self.show_toast("No item selected", duration=2000)
            return

        picked = self._selected_inventory_rows()
        if len(picked) > 1 and not CTkMessageBox.askyesno(
            "Remove items", f"Remove {len(picked)} items?", parent=self.parent
        ):
            return

        character = save.characters[self.get_slot_index()]
        removed = [name for item, name, _ in picked if character.delete_entry(item)]
        if not removed:
            self.show_toast("Item not found in inventory", duration=2000)
            return

        self._write_and_refresh(save, operation="remove_item")
        self.show_toast(
            f"Removed {removed[0]}"
            if len(removed) == 1
            else f"Removed {len(removed)} items",
            duration=2000,
        )

    @staticmethod
    def _edit_toast(value: str, changed: list[str], capped: int, skipped: int) -> str:
        head = (
            f"Set {changed[0]} to {value}"
            if len(changed) == 1
            else f"Set {len(changed)} items to {value}"
        )
        notes = ", ".join(
            f"{count} {label}"
            for count, label in ((capped, "capped at max"), (skipped, "skipped"))
            if count
        )
        return f"{head} ({notes})" if notes else head

    def _on_set_quantity(self) -> None:
        save = self._writable_save()
        if save is None:
            return

        rows = self._selected_inventory_rows()
        if not rows:
            self.show_toast("No item selected", duration=2000)
            return

        try:
            quantity = int(self.set_qty_var.get())
        except ValueError:
            self.show_toast("Quantity must be a number", duration=2000)
            return
        if quantity < 1:
            self.show_toast("Quantity must be at least 1", duration=2000)
            return

        character = save.characters[self.get_slot_index()]
        targets = [
            (item, name, self._quantity_limit(character, item, category))
            for item, name, category in rows
        ]
        targets = [t for t in targets if t[2]]
        if not targets:
            self.show_toast(
                "Quantity only applies to stackable items, not the Estus Flask "
                "whose count is packed with its level",
                duration=3500,
            )
            return

        changed, capped = [], 0
        for item, name, limit in targets:
            value = min(quantity, limit)
            capped += quantity > limit
            if item.quantity != value:
                item.quantity = value
                character.write_inventory_slot(item)
                changed.append(name)
        if not changed:
            self.show_toast("Already set", duration=2000)
            return

        self._write_and_refresh(save, operation="set_item_quantity")
        self._reset_inputs()
        self.show_toast(
            self._edit_toast(f"x{quantity}", changed, capped, len(rows) - len(targets)),
            duration=3000,
        )

    def _on_set_upgrade(self) -> None:
        save = self._writable_save()
        if save is None:
            return

        rows = self._selected_inventory_rows()
        if not rows:
            self.show_toast("No item selected", duration=2000)
            return

        try:
            level = int(self.set_upgrade_var.get())
        except ValueError:
            self.show_toast("Upgrade must be a number", duration=2000)
            return
        if level < 0:
            self.show_toast("Upgrade cannot be negative", duration=2000)
            return

        if self._load_regulation(save) is None:
            return
        character = save.characters[self.get_slot_index()]
        targets = [
            (item, name, self._upgrade_limit(character, item, category))
            for item, name, category in rows
        ]
        targets = [t for t in targets if t[2]]
        if not targets:
            self.show_toast(
                "Upgrade only applies to weapons and armor that can be upgraded",
                duration=3000,
            )
            return

        changed, capped = [], 0
        for item, name, limit in targets:
            value = min(level, limit)
            capped += level > limit
            if item.upgrade != value:
                item.upgrade = value
                character.write_inventory_slot(item)
                changed.append(name)
        if not changed:
            self.show_toast("Already set", duration=2000)
            return

        self._write_and_refresh(save, operation="set_item_upgrade")
        self._reset_inputs()
        self.show_toast(
            self._edit_toast(f"+{level}", changed, capped, len(rows) - len(targets)),
            duration=3000,
        )

    def _on_set_infusion(self) -> None:
        save = self._writable_save()
        if save is None:
            return

        rows = self._selected_inventory_rows()
        if not rows:
            self.show_toast("No item selected", duration=2000)
            return

        infusion = INFUSION_NAMES.index(self.set_infusion_var.get())
        if self._load_regulation(save) is None:
            return
        character = save.characters[self.get_slot_index()]
        targets = [
            (item, name)
            for item, name, category in rows
            if infusion in self._infusion_choices(character, item, category)
            or (infusion == 0 and category == "weapons")
        ]
        if not targets:
            self.show_toast(
                f"None of the selected items allow {INFUSION_NAMES[infusion]}",
                duration=3000,
            )
            return

        changed = []
        for item, name in targets:
            if item.infusion != infusion:
                item.infusion = infusion
                character.write_inventory_slot(item)
                changed.append(name)
        if not changed:
            self.show_toast("Already set", duration=2000)
            return

        self._write_and_refresh(save, operation="set_item_infusion")
        self._reset_inputs()
        self.show_toast(
            self._edit_toast(
                INFUSION_NAMES[infusion], changed, 0, len(rows) - len(targets)
            ),
            duration=3000,
        )

    def _write_and_refresh(
        self, save: DS2Save, operation: str = "inventory_edit"
    ) -> None:
        save_path = self.get_save_path()
        if save_path:
            self._backup(save_path, f"before_{operation}", operation)
            try:
                save.save_to_file(save_path)
            except Exception as e:
                self.show_toast(f"Failed to write save: {e}", duration=3000)
        self.refresh()

    def _backup(self, save_path, description: str, operation: str) -> None:
        if not save_path:
            return
        try:
            from er_save_manager.backup.manager import BackupManager

            BackupManager(Path(save_path)).create_backup(
                description=description, operation=operation
            )
        except Exception:
            pass
