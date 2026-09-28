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
from er_save_manager.games.DS2.regulation import Regulation
from er_save_manager.games.DS2.save import (
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
# (item_database lookups, Character.add_item/delete_item) always use the
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
        ctk.CTkLabel(parent, text="Add Item", font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=10, pady=(10, 4)
        )

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
        ctk.CTkButton(
            button_row, text="Add Selected", command=self._on_add, height=32
        ).pack(side="left", fill="x", expand=True, padx=(0, 3))
        ctk.CTkButton(
            button_row, text="Add All Listed", command=self._on_add_all, height=32
        ).pack(side="left", fill="x", expand=True, padx=(3, 0))

        qty_row = ctk.CTkFrame(parent, fg_color="transparent")
        qty_row.pack(side="bottom", fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(qty_row, text="Quantity:", width=70).pack(side="left")
        self.add_qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(qty_row, textvariable=self.add_qty_var, width=60).pack(side="left")
        ctk.CTkLabel(qty_row, text="Upgrade:").pack(side="left", padx=(10, 4))
        self.add_upgrade_var = tk.StringVar(value="0")
        ctk.CTkEntry(qty_row, textvariable=self.add_upgrade_var, width=50).pack(
            side="left"
        )

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

        self._search_items()

    def _build_inventory_panel(self, parent) -> None:
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(
            header, text="Current Inventory", font=("Segoe UI", 13, "bold")
        ).pack(side="left")

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

        columns = ("name", "category", "quantity", "upgrade")
        # Action rows are packed to the bottom first so they are never clipped.
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        upgrade_actions = ctk.CTkFrame(parent, fg_color="transparent")
        upgrade_actions.pack(side="bottom", fill="x", padx=10, pady=(0, 6))

        self._inventory_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=6
        )
        self._column_labels = {
            "name": "Name",
            "category": "Category",
            "quantity": "Qty",
            "upgrade": "Upgrade",
        }
        for col, label, width in (
            ("name", "Name", 220),
            ("category", "Category", 110),
            ("quantity", "Qty", 50),
            ("upgrade", "Upgrade", 70),
        ):
            self._inventory_tree.heading(
                col, text=label, command=lambda c=col: self._sort_by(c)
            )
            self._inventory_tree.column(col, width=width)
        self._inventory_tree.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        ctk.CTkButton(
            actions, text="Remove Selected", command=self._on_remove, width=130
        ).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(actions, text="New qty:").pack(side="left", padx=(10, 4))
        self.set_qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(actions, textvariable=self.set_qty_var, width=60).pack(side="left")
        ctk.CTkButton(
            actions, text="Set Quantity", command=self._on_set_quantity, width=110
        ).pack(side="left", padx=6)

        ctk.CTkLabel(upgrade_actions, text="New upgrade:").pack(
            side="left", padx=(0, 4)
        )
        self.set_upgrade_var = tk.StringVar(value="0")
        ctk.CTkEntry(upgrade_actions, textvariable=self.set_upgrade_var, width=60).pack(
            side="left"
        )
        ctk.CTkButton(
            upgrade_actions,
            text="Set Upgrade",
            command=self._on_set_upgrade,
            width=110,
        ).pack(side="left", padx=6)

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
        quantity, upgrade = inputs

        item_id = _hex_id_to_int(hex_id)
        if item_id in UNSAFE_IDS and not CTkMessageBox.askyesno(
            "Unsafe item",
            f"{item_name} is flagged unsafe.\n\n"
            "Adding it can get an account soft-banned online.\n\n"
            "Add it anyway? (No Risk on Seamless Co-op saves)",
            parent=self.parent,
        ):
            return
        character = save.characters[self.get_slot_index()]
        if category in UNIQUE_CATEGORIES and character.owns(item_id):
            self.show_toast(f"{item_name} is already owned", duration=2000)
            return
        if category in STACKABLE_CATEGORIES:
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

        added = character.add_item(
            item_id, category, quantity=quantity, upgrade=upgrade
        )
        if not added:
            self.show_toast("No empty inventory slot available", duration=2500)
            return

        self._write_and_refresh(save, operation="add_item")
        self._reset_add_inputs()
        label = f"{item_name} +{upgrade}" if upgrade else item_name
        suffix = " (capped at max upgrade)" if capped else ""
        self.show_toast(f"Added {label}{suffix}", duration=2500)

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

    def _read_add_inputs(self) -> tuple[int, int] | None:
        """Parse the Quantity and Upgrade fields as (quantity, upgrade).
        Shows a toast and returns None when either is invalid."""
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
        return quantity, upgrade

    def _reset_add_inputs(self) -> None:
        """Return the Quantity and Upgrade fields to their defaults so a
        previous addition does not carry into the next one."""
        self.add_qty_var.set("1")
        self.add_upgrade_var.set("0")

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
        quantity, upgrade = inputs

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

        if category in UPGRADABLE_CATEGORIES and upgrade > 0:
            if self._load_regulation(save) is None:
                return

        lines = [f"Add {len(safe_ids)} {CATEGORY_LABELS[category]} item(s)?"]
        if category in STACKABLE_CATEGORIES:
            lines.append(
                f"Quantity {quantity}, capped per item at its stack limit. "
                "Owned stacks are set to it."
            )
        else:
            lines.append("Items already owned are skipped.")
        if category in UPGRADABLE_CATEGORIES and upgrade > 0:
            lines.append(f"Upgrade +{upgrade}, capped per item at its maximum.")
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
        )
        summary = ", ".join(
            f"{count} {label}"
            for count, label in (
                (result.added, "added"),
                (result.updated, "updated"),
                (result.skipped_owned, "already owned"),
                (result.clamped, "capped at max upgrade"),
                (result.no_space, "no space"),
                (unsafe_count, "unsafe skipped"),
            )
            if count
        )
        if result.added or result.updated:
            self._write_and_refresh(save, operation="add_items_bulk")
            self._reset_add_inputs()
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
            rows.append((item, name, item_category, display_category, qty, level))

        sort_key = {
            "name": lambda r: r[1].lower(),
            "category": lambda r: r[3].lower(),
            "quantity": lambda r: r[4],
            "upgrade": lambda r: r[5],
        }.get(self._sort_column, lambda r: r[1].lower())
        rows.sort(key=sort_key, reverse=self._sort_reverse)

        self._inventory_tree.delete(*self._inventory_tree.get_children())
        self._visible_items = []
        for item, name, item_category, display_category, qty, level in rows:
            self._visible_items.append((item, name, item_category))
            qty_str = str(qty) if qty >= 0 else ""
            level_str = ""
            if level >= 0:
                level_str = f"+{level}"
                if self._regulation is not None:
                    limit = self._regulation.max_upgrade(item.item_id, item_category)
                    level_str += f"/{limit}"
            self._inventory_tree.insert(
                "", "end", values=(name, display_category, qty_str, level_str)
            )

    def _on_remove(self) -> None:
        if _game_blocks_write(self.parent):
            return

        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return

        selection = self._inventory_tree.selection()
        if not selection:
            self.show_toast("No item selected", duration=2000)
            return

        index = self._inventory_tree.index(selection[0])
        item, name, category = self._visible_items[index]
        character = save.characters[self.get_slot_index()]
        deleted = character.delete_item(item.item_id, category)
        if not deleted:
            self.show_toast("Item not found in inventory", duration=2000)
            return

        self._write_and_refresh(save, operation="remove_item")
        self.show_toast(f"Removed {name}", duration=2000)

    def _on_set_quantity(self) -> None:
        if _game_blocks_write(self.parent):
            return

        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return

        selection = self._inventory_tree.selection()
        if not selection:
            self.show_toast("No item selected", duration=2000)
            return

        index = self._inventory_tree.index(selection[0])
        item, name, category = self._visible_items[index]
        if item.item_id == _ESTUS_FLASK_ID:
            self.show_toast(
                "Estus Flask count is packed with its level; change it in game",
                duration=3000,
            )
            return
        if category not in STACKABLE_CATEGORIES:
            self.show_toast(
                "Quantity only applies to goods, bolts, spells, and upgrade materials",
                duration=3000,
            )
            return

        try:
            quantity = int(self.set_qty_var.get())
        except ValueError:
            self.show_toast("Quantity must be a number", duration=2000)
            return
        character = save.characters[self.get_slot_index()]
        stack_limit = character.max_stack(item.item_id)
        if not (1 <= quantity <= stack_limit):
            self.show_toast(
                f"Quantity must be between 1 and {stack_limit}", duration=2500
            )
            return

        character.add_item(item.item_id, category, quantity=quantity, stack=True)
        self._write_and_refresh(save, operation="set_item_quantity")
        self.show_toast(f"Set {name} to x{quantity}", duration=2000)

    def _on_set_upgrade(self) -> None:
        save = self._writable_save()
        if save is None:
            return

        selection = self._inventory_tree.selection()
        if not selection:
            self.show_toast("No item selected", duration=2000)
            return

        index = self._inventory_tree.index(selection[0])
        item, name, category = self._visible_items[index]
        if category not in UPGRADABLE_CATEGORIES:
            self.show_toast("Upgrade only applies to weapons and armor", duration=3000)
            return

        try:
            level = int(self.set_upgrade_var.get())
        except ValueError:
            self.show_toast("Upgrade must be a number", duration=2000)
            return

        regulation = self._load_regulation(save)
        if regulation is None:
            return
        limit = regulation.max_upgrade(item.item_id, category)
        if limit == 0:
            self.show_toast(f"{name} cannot be upgraded", duration=2500)
            return
        if not (0 <= level <= limit):
            self.show_toast(f"{name} allows upgrade 0 to {limit}", duration=2500)
            return

        item.upgrade = level
        save.characters[self.get_slot_index()].write_inventory_slot(item)
        self._write_and_refresh(save, operation="set_item_upgrade")
        self.show_toast(f"Set {name} to +{level}", duration=2000)

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
