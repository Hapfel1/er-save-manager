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
    if name.startswith("Unknown Item") and (full_item_id & 0xF0000000) == 0x40000000:
        # B0 handles cannot distinguish goods from talismans; try talisman category
        alt = 0x20000000 | (full_item_id & 0x0FFFFFFF)
        alt_name = get_item_database().get_item_by_id(alt)
        if alt_name:
            return alt_name.name
    return name


# ---- editor -----------------------------------------------------------------


class InventoryEditor:
    """Inventory editor: browse, add, remove, and adjust item quantities."""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_char_slot_callback,
        get_save_path_callback,
        ensure_mutable_callback,
    ):
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_char_slot = get_char_slot_callback
        self.get_save_path = get_save_path_callback
        self.ensure_mutable = ensure_mutable_callback

        self.selected_item = None  # Item from the search browser
        self._item_data: list[tuple[int, str] | None] = []  # parallel to listbox rows

        self.inv_quantity_var = None
        self.inv_upgrade_var = None
        self.inv_location_var = None
        self.inv_filter_var = None
        self.inventory_listbox = None
        self._search_var = None
        self._search_cat_var = None
        self._results_listbox = None
        self._results_items: list = []  # Item objects matching current search
        self._selected_item_label = None

        self.frame = None

    # ---- UI setup -----------------------------------------------------------

    def setup_ui(self):
        self.frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        self.frame.pack(fill=ctk.BOTH, expand=True)
        bind_mousewheel(self.frame)

        self._build_add_panel()
        self._build_inventory_list()
        self._build_action_bar()

    def _build_add_panel(self):
        add_frame = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        add_frame.pack(fill=ctk.X, pady=5, padx=10)

        ctk.CTkLabel(add_frame, text="Add Item", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=4, sticky=ctk.W, padx=5, pady=(5, 0)
        )

        # Search row
        ctk.CTkLabel(add_frame, text="Search:").grid(
            row=1, column=0, sticky=ctk.W, padx=5, pady=3
        )
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._search_items())
        search_entry = ctk.CTkEntry(add_frame, textvariable=self._search_var, width=200)
        search_entry.grid(row=1, column=1, padx=5, pady=3)

        # Category filter for search
        self._search_cat_var = ctk.StringVar(value="All")
        search_cat = ctk.CTkComboBox(
            add_frame,
            variable=self._search_cat_var,
            values=["All"],
            width=160,
            command=lambda _e=None: self._search_items(),
        )
        search_cat.grid(row=1, column=2, padx=5, pady=3)
        self._search_cat_combo = search_cat

        # Populate category list after DB loads
        self._populate_search_categories()

        # Search results listbox
        results_container = ctk.CTkFrame(add_frame, fg_color="transparent")
        results_container.grid(
            row=2, column=0, columnspan=4, sticky=ctk.EW, padx=5, pady=3
        )
        results_sb = tk.Scrollbar(results_container)
        results_sb.pack(side=tk.RIGHT, fill=tk.Y)

        mode = ctk.get_appearance_mode()
        lb_bg = "#1f1f28" if mode == "Dark" else "#f0f0f0"
        lb_fg = "#e5e5f5" if mode == "Dark" else "#000000"
        lb_sel = "#c9a0dc" if mode == "Dark" else "#b8a0d0"

        self._results_listbox = tk.Listbox(
            results_container,
            yscrollcommand=results_sb.set,
            font=("Consolas", 9),
            height=5,
            bg=lb_bg,
            fg=lb_fg,
            selectbackground=lb_sel,
            relief=tk.FLAT,
        )
        self._results_listbox.pack(side=tk.LEFT, fill=ctk.BOTH, expand=True)
        results_sb.config(command=self._results_listbox.yview)
        self._results_listbox.bind("<<ListboxSelect>>", self._on_result_select)

        # Selected item label
        self._selected_item_label = ctk.CTkLabel(
            add_frame, text="No item selected", text_color=("gray50", "gray70")
        )
        self._selected_item_label.grid(
            row=3, column=0, columnspan=4, sticky=ctk.W, padx=5, pady=(0, 3)
        )

        # Options row: qty, upgrade, location, add button
        ctk.CTkLabel(add_frame, text="Qty:").grid(
            row=4, column=0, sticky=ctk.W, padx=5, pady=3
        )
        self.inv_quantity_var = ctk.IntVar(value=1)
        ctk.CTkEntry(add_frame, textvariable=self.inv_quantity_var, width=60).grid(
            row=4, column=1, sticky=ctk.W, padx=5, pady=3
        )

        ctk.CTkLabel(add_frame, text="Upgrade:").grid(
            row=4, column=2, sticky=ctk.W, padx=(10, 5), pady=3
        )
        self.inv_upgrade_var = ctk.IntVar(value=0)
        ctk.CTkEntry(add_frame, textvariable=self.inv_upgrade_var, width=50).grid(
            row=4, column=3, sticky=ctk.W, padx=5, pady=3
        )

        ctk.CTkLabel(add_frame, text="Location:").grid(
            row=5, column=0, sticky=ctk.W, padx=5, pady=3
        )
        self.inv_location_var = ctk.StringVar(value="held")
        ctk.CTkComboBox(
            add_frame,
            variable=self.inv_location_var,
            values=["held", "storage"],
            width=120,
        ).grid(row=5, column=1, sticky=ctk.W, padx=5, pady=3)

        ctk.CTkButton(
            add_frame, text="Add Item", command=self.add_item, width=120
        ).grid(row=5, column=2, columnspan=2, padx=5, pady=3)

    def _build_inventory_list(self):
        list_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        list_frame.pack(fill=ctk.BOTH, expand=True, pady=5, padx=10)

        ctk.CTkLabel(
            list_frame, text="Current Inventory", font=("Segoe UI", 12, "bold")
        ).pack(anchor=ctk.W, padx=5, pady=(5, 0))

        filter_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        filter_frame.pack(fill=ctk.X, pady=(0, 5))
        ctk.CTkLabel(filter_frame, text="Show:").pack(side=ctk.LEFT, padx=5)
        self.inv_filter_var = ctk.StringVar(value="All")
        ctk.CTkComboBox(
            filter_frame,
            variable=self.inv_filter_var,
            values=["All", "Held", "Storage", "Key Items"],
            width=140,
            command=lambda _e=None: self.refresh_inventory(),
        ).pack(side=ctk.LEFT, padx=5)

        inv_container = ctk.CTkFrame(list_frame, fg_color="transparent")
        inv_container.pack(fill=ctk.BOTH, expand=True)
        sb = tk.Scrollbar(inv_container)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        mode = ctk.get_appearance_mode()
        lb_bg = "#1f1f28" if mode == "Dark" else "#f0f0f0"
        lb_fg = "#e5e5f5" if mode == "Dark" else "#000000"
        lb_sel = "#c9a0dc" if mode == "Dark" else "#b8a0d0"

        self.inventory_listbox = tk.Listbox(
            inv_container,
            yscrollcommand=sb.set,
            font=("Consolas", 10),
            height=18,
            bg=lb_bg,
            fg=lb_fg,
            selectbackground=lb_sel,
            relief=tk.FLAT,
        )
        self.inventory_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.inventory_listbox.yview)
        bind_mousewheel(self.inventory_listbox)

    def _build_action_bar(self):
        bar = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        bar.pack(fill=ctk.X, pady=5, padx=10)

        self._remove_btn = ctk.CTkButton(
            bar, text="Remove Selected", command=self.remove_item, width=160
        )
        self._remove_btn.pack(side=ctk.LEFT, padx=5, pady=5)

        self._set_qty_btn = ctk.CTkButton(
            bar, text="Set Quantity", command=self.set_quantity, width=120
        )
        self._set_qty_btn.pack(side=ctk.LEFT, padx=5, pady=5)

        ctk.CTkButton(
            bar, text="Refresh", command=self.refresh_inventory, width=100
        ).pack(side=ctk.LEFT, padx=5, pady=5)

        ctk.CTkLabel(
            bar,
            text="Select an item from the list then use Remove or Set Quantity.",
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 9),
        ).pack(side=ctk.LEFT, padx=10)

    # ---- search browser helpers ---------------------------------------------

    def _populate_search_categories(self):
        try:
            from er_save_manager.data.item_database import get_categories

            cats = ["All"] + get_categories()
            self._search_cat_combo.configure(values=cats)
        except Exception:
            pass

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

            # Cap at 200 to keep the listbox responsive
            self._results_items = results[:200]
            self._results_listbox.delete(0, tk.END)
            for item in self._results_items:
                self._results_listbox.insert(
                    tk.END, f"{item.name}  [{item.category_name}]"
                )
        except Exception:
            pass

    def _on_result_select(self, _event=None):
        sel = self._results_listbox.curselection()
        if not sel or sel[0] >= len(self._results_items):
            return
        self.selected_item = self._results_items[sel[0]]
        self._selected_item_label.configure(
            text=f"Selected: {self.selected_item.name}",
            text_color=("#2563eb", "#60a5fa"),
        )

    # ---- inventory display --------------------------------------------------

    def refresh_inventory(self):
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

            self.inventory_listbox.delete(0, tk.END)
            self._item_data = []

            gaitem_map = {}
            for g in getattr(slot, "gaitem_map", []):
                if g.gaitem_handle not in (0, 0xFFFFFFFF):
                    gaitem_map[g.gaitem_handle] = g

            filt = self.inv_filter_var.get() if self.inv_filter_var else "All"

            if filt in ("All", "Held") and hasattr(slot, "inventory_held"):
                self._append_section(
                    "HELD INVENTORY",
                    slot.inventory_held.common_items,
                    gaitem_map,
                    "held",
                    key=False,
                )

            if filt in ("All", "Key Items") and hasattr(slot, "inventory_held"):
                self._append_section(
                    "KEY ITEMS (HELD)",
                    slot.inventory_held.key_items,
                    gaitem_map,
                    "held",
                    key=True,
                )

            if filt in ("All", "Storage") and hasattr(slot, "inventory_storage_box"):
                self._append_section(
                    "STORAGE BOX",
                    slot.inventory_storage_box.common_items,
                    gaitem_map,
                    "storage",
                    key=False,
                )
                self._append_section(
                    "KEY ITEMS (STORAGE)",
                    slot.inventory_storage_box.key_items,
                    gaitem_map,
                    "storage",
                    key=True,
                )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to refresh inventory:\n{e}", parent=self.parent
            )

    def _append_section(self, header, items, gaitem_map, location, key):
        self.inventory_listbox.insert(tk.END, f"=== {header} ===")
        self._item_data.append(None)

        for inv_item in items:
            if inv_item.gaitem_handle == 0 or inv_item.quantity == 0:
                continue
            full_id, upgrade = _decode_inv_item(inv_item, gaitem_map)
            name = _item_name(full_id, upgrade)
            suffix = f" +{upgrade}" if upgrade > 0 else ""
            prefix = "K" if key else ""
            self.inventory_listbox.insert(
                tk.END,
                f"  [{location[0].upper()}{prefix}] {name}{suffix}  | Qty: {inv_item.quantity}",
            )
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
        try:
            qty = int(self.inv_quantity_var.get())
            upg = int(self.inv_upgrade_var.get())
        except (ValueError, tk.TclError):
            CTkMessageBox.showerror(
                "Input Error",
                "Quantity and upgrade must be integers.",
                parent=self.parent,
            )
            return
        location = self.inv_location_var.get()

        try:
            self.ensure_mutable()
            self._create_backup(save_file, slot_idx, "add_item")

            from er_save_manager.parser.inventory_ops import add_item

            result = add_item(save_file, slot_idx, full_id, qty, location, upgrade=upg)

            save_file.recalculate_checksums()
            save_path = self.get_save_path()
            if save_path:
                save_file.to_file(Path(save_path))

            self.refresh_inventory()
            CTkMessageBox.showinfo(
                "Done",
                f"Added {self.selected_item.name}"
                + (f" +{upg}" if upg else "")
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
            return  # header row

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
            return  # header row

        full_id, location = self._item_data[idx]

        # Only stackable items (goods/spells) make sense to edit quantity
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
