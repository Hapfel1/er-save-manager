"""
Inventory Editor Module (customtkinter)
Full implementation with gaitem system for adding/removing items using item browser
"""

import logging
import re
import tkinter as tk
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

from er_save_manager.parser.save import Save
from er_save_manager.parser.slot_rebuild import rebuild_slot
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

# Setup logging with file output
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Create log filename with timestamp
log_filename = (
    log_dir / f"inventory_editor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

# Configure logging to both file and console
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename, mode="w", encoding="utf-8"),
        logging.StreamHandler(),  # Keep console output too
    ],
)

logger.info(f"Logging to file: {log_filename}")


class InventoryEditor:
    """Full inventory editor with gaitem system support"""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_char_slot_callback,
        get_save_path_callback,
        ensure_mutable_callback,
    ):
        """
        Initialize inventory editor

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_char_slot_callback: Function that returns current character slot index
            get_save_path_callback: Function that returns save file path
            ensure_mutable_callback: Function to ensure raw_data is mutable
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_char_slot = get_char_slot_callback
        self.get_save_path = get_save_path_callback
        self.ensure_mutable = ensure_mutable_callback

        # UI variables
        self.selected_item = None
        self.inv_quantity_var = None
        self.inv_upgrade_var = None
        self.inv_reinforcement_var = None
        self.inv_location_var = None
        self.inv_filter_var = None
        self.inventory_listbox = None
        self.selected_item_label = None

        self.frame = None

    def setup_ui(self):
        """Setup the inventory editor UI"""
        self.frame = ctk.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
        )
        self.frame.pack(fill=ctk.BOTH, expand=True)
        bind_mousewheel(self.frame)

        # Add item frame
        add_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        add_frame.pack(fill=ctk.X, pady=5, padx=10)
        ctk.CTkLabel(
            add_frame,
            text="Add/Spawn Item",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky=ctk.W, padx=5, pady=(5, 0))

        # Item selection using database with category filter
        from er_save_manager.data.item_database import get_item_database

        ctk.CTkLabel(add_frame, text="Category:").grid(
            row=1, column=0, sticky=ctk.W, padx=5, pady=2
        )
        self.item_db = get_item_database()
        self.category_names = self.item_db.get_all_categories()
        self.category_var = ctk.StringVar()
        self.category_combobox = ctk.CTkComboBox(
            add_frame,
            variable=self.category_var,
            values=self.category_names,
            width=180,
            command=self._on_category_change,
        )
        self.category_combobox.grid(row=1, column=1, sticky=ctk.W, padx=5, pady=2)

        ctk.CTkLabel(add_frame, text="Item:").grid(
            row=1, column=2, sticky=ctk.W, padx=5, pady=2
        )
        self.item_name_var = ctk.StringVar()
        self.item_combobox = ctk.CTkComboBox(
            add_frame,
            variable=self.item_name_var,
            values=[],
            width=220,
        )
        self.item_combobox.grid(row=1, column=3, sticky=ctk.W, padx=5, pady=2)

        # Separator for clarity
        ctk.CTkLabel(add_frame, text="").grid(row=2, column=0, columnspan=4, pady=2)

        # Quantity
        ctk.CTkLabel(add_frame, text="Quantity:").grid(
            row=3, column=0, sticky=ctk.W, padx=5, pady=2
        )
        self.inv_quantity_var = ctk.IntVar(value=1)
        ctk.CTkEntry(add_frame, textvariable=self.inv_quantity_var, width=80).grid(
            row=3, column=1, sticky=ctk.W, padx=5, pady=2
        )

        # Upgrade level
        ctk.CTkLabel(add_frame, text="Upgrade:").grid(
            row=4, column=0, sticky=ctk.W, padx=5, pady=2
        )
        self.inv_upgrade_var = ctk.IntVar(value=0)
        ctk.CTkEntry(add_frame, textvariable=self.inv_upgrade_var, width=80).grid(
            row=4, column=1, sticky=ctk.W, padx=5, pady=2
        )

        # Reinforcement type
        ctk.CTkLabel(add_frame, text="Type:").grid(
            row=4, column=2, sticky=ctk.W, padx=5, pady=2
        )
        self.inv_reinforcement_var = ctk.StringVar(value="standard")
        ctk.CTkComboBox(
            add_frame,
            variable=self.inv_reinforcement_var,
            values=["standard", "somber"],
            width=100,
        ).grid(row=4, column=3, sticky=ctk.W, padx=5, pady=2)

        # Location
        ctk.CTkLabel(add_frame, text="Location:").grid(
            row=5, column=0, sticky=ctk.W, padx=5, pady=2
        )
        self.inv_location_var = ctk.StringVar(value="held")
        ctk.CTkComboBox(
            add_frame,
            variable=self.inv_location_var,
            values=["held", "storage"],
            width=100,
        ).grid(row=5, column=1, sticky=ctk.W, padx=5, pady=2)

        # Add button
        ctk.CTkButton(
            add_frame,
            text="Add Item",
            command=self.add_item_simple,
            width=140,
            fg_color="#4CAF50",
            hover_color="#45a049",
        ).grid(row=6, column=0, columnspan=2, sticky=ctk.W, padx=5, pady=5)

    def _on_category_change(self, _event=None):
        """Update item dropdown when category changes and prevent duplicate inventory windows."""
        category = self.category_var.get()
        items = self.item_db.get_items_by_category(category)
        item_names = [f"{item.name} [0x{item.full_id:08X}]" for item in items]
        self.item_combobox.configure(values=item_names)
        if item_names:
            self.item_name_var.set(item_names[0])
        else:
            self.item_name_var.set("")

        # Destroy previous inventory overview window if it exists
        if (
            hasattr(self, "_inventory_list_frame")
            and self._inventory_list_frame is not None
        ):
            self._inventory_list_frame.destroy()

        # Item list frame
        self._inventory_list_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self._inventory_list_frame.pack(fill=ctk.BOTH, expand=True, pady=5, padx=10)
        ctk.CTkLabel(
            self._inventory_list_frame,
            text="Current Inventory",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=ctk.W, padx=5, pady=(5, 0))

        # Filter frame
        filter_frame = ctk.CTkFrame(self._inventory_list_frame, fg_color="transparent")
        filter_frame.pack(fill=ctk.X, pady=(0, 5))

        ctk.CTkLabel(filter_frame, text="Filter by Category:").pack(
            side=ctk.LEFT, padx=5
        )
        self.inv_filter_var = ctk.StringVar(value="All")
        filter_combo = ctk.CTkComboBox(
            filter_frame,
            variable=self.inv_filter_var,
            values=["All", "Held", "Storage", "Key Items"],
            width=140,
            command=lambda _e=None: self.refresh_inventory(),
        )
        filter_combo.pack(side=ctk.LEFT, padx=5)

        # Inventory display (tk Listbox for rich text & performance)
        inv_list_container = ctk.CTkFrame(
            self._inventory_list_frame, fg_color="transparent"
        )
        inv_list_container.pack(fill=ctk.BOTH, expand=True)

        inv_scrollbar = tk.Scrollbar(inv_list_container)
        inv_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Get current theme mode
        mode = ctk.get_appearance_mode()
        if mode == "Light":
            listbox_bg = "#f0f0f0"
            listbox_fg = "#000000"
            listbox_select_bg = "#b8a0d0"
        else:
            listbox_bg = "#1f1f28"
            listbox_fg = "#e5e5f5"
            listbox_select_bg = "#c9a0dc"

        self.inventory_listbox = tk.Listbox(
            inv_list_container,
            yscrollcommand=inv_scrollbar.set,
            font=("Consolas", 10),
            height=18,
            bg=listbox_bg,
            fg=listbox_fg,
            selectbackground=listbox_select_bg,
            relief=tk.FLAT,
        )
        self.inventory_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inv_scrollbar.config(command=self.inventory_listbox.yview)
        bind_mousewheel(self.inventory_listbox)

        # Remove / refresh buttons
        remove_frame = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        remove_frame.pack(fill=ctk.X, pady=5, padx=10)

        ctk.CTkButton(
            remove_frame,
            text="Remove Selected Item",
            command=self.remove_item,
            width=200,
        ).pack(side=ctk.LEFT, padx=5)

        ctk.CTkButton(
            remove_frame,
            text="Refresh List",
            command=self.refresh_inventory,
            width=140,
        ).pack(side=ctk.LEFT, padx=5)

        ctk.CTkButton(
            remove_frame,
            text="Apply Changes",
            command=self.apply_inventory_changes,
            width=140,
            fg_color="#4CAF50",
            hover_color="#45a049",
        ).pack(side=ctk.LEFT, padx=5)

        # Info section
        info_label = ctk.CTkLabel(
            self.frame,
            text=(
                "⚠️ Item spawning enabled with new algorithm! Enter item ID in hex format (e.g., 0x00100000 for weapon).\n"
                "Check logs for detailed debugging information. Always backup before adding items!"
            ),
            font=("Segoe UI", 9),
            text_color=("#ff6b00", "#ffaa00"),
            justify=ctk.LEFT,
        )
        info_label.pack(pady=10, padx=10, anchor=ctk.W)

    # Item browser disabled - commenting out unused function
    # def _browse_item_to_add(self):
    #     """Open item browser to select item for adding"""
    #     # Feature disabled for stability

    @staticmethod
    def _make_blank_gaitem_with_size(size: int):
        """Return an empty Gaitem placeholder that preserves the serialized size."""

    def add_item_simple(self):
        """Add item using selected item from database"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        # Get selected item from combobox
        selected_name = self.item_name_var.get()
        if not selected_name:
            CTkMessageBox.showwarning(
                "No Item", "Please select an item from the list!", parent=self.parent
            )
            return

        # Find the item in the database
        try:
            # Extract full_id from string (format: name [0xXXXXXXXX])
            full_id_hex = selected_name.split("[0x")[-1].rstrip("]")
            item_id = int(full_id_hex, 16)
            item = self.item_db.get_item_by_id(item_id)
        except Exception:
            CTkMessageBox.showerror(
                "Invalid Selection",
                f"Could not parse item from selection: {selected_name}",
                parent=self.parent,
            )
            return

        if not item:
            CTkMessageBox.showerror(
                "Item Not Found",
                f"Item not found in database: {selected_name}",
                parent=self.parent,
            )
            return

        # Use the item as selected_item
        self.selected_item = item
        self.add_item()

    @staticmethod
    def _make_blank_gaitem_with_size(size: int):
        """Return an empty Gaitem placeholder that preserves the serialized size."""
        from er_save_manager.parser.er_types import Gaitem

        g = Gaitem()
        if size >= 16:
            g.unk0x10 = 0
            g.unk0x14 = 0
        if size == 21:
            g.gem_gaitem_handle = 0xFFFFFFFF
            g.unk0x1c = 0
        return g

    def refresh_inventory(self):
        """Refresh the inventory display"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        slot_idx = self.get_char_slot()

        try:
            slot = save_file.characters[slot_idx]

            if not slot or slot.is_empty():
                CTkMessageBox.showwarning(
                    "Empty Slot", f"Slot {slot_idx + 1} is empty!", parent=self.parent
                )
                return

            if self.inventory_listbox is None:
                return
            self.inventory_listbox.delete(0, tk.END)

            # Get filter value
            filter_val = self.inv_filter_var.get() if self.inv_filter_var else "All"

            # Build gaitem lookup map
            gaitem_map = {}
            if hasattr(slot, "gaitem_map"):
                for gaitem in slot.gaitem_map:
                    if getattr(gaitem, "gaitem_handle", 0) != 0xFFFFFFFF:
                        gaitem_map[gaitem.gaitem_handle] = gaitem

            # Display held inventory
            if (
                (filter_val in ["All", "Held"])
                and hasattr(slot, "inventory_held")
                and slot.inventory_held
            ):
                inv = slot.inventory_held
                self.inventory_listbox.insert(tk.END, "=== HELD INVENTORY ===")
                for i, inv_item in enumerate(inv.common_items):
                    if inv_item.gaitem_handle != 0 and inv_item.quantity > 0:
                        gaitem = gaitem_map.get(inv_item.gaitem_handle)
                        if gaitem:
                            item_id = gaitem.item_id
                            upgrade = (
                                gaitem.unk0x10 if gaitem.unk0x10 is not None else 0
                            )
                            from er_save_manager.data.item_database import get_item_name

                            item_name = get_item_name(item_id, upgrade)
                            self.inventory_listbox.insert(
                                tk.END,
                                f"  [{i}] {item_name} | Qty: {inv_item.quantity} | +{upgrade}",
                            )
                        else:
                            self.inventory_listbox.insert(
                                tk.END,
                                f"  [{i}] Handle: {inv_item.gaitem_handle:08X} | Qty: {inv_item.quantity}",
                            )

            # Key items (only if All or Key Items selected)
            if (
                (filter_val in ["All", "Key Items"])
                and hasattr(slot, "inventory_held")
                and slot.inventory_held
            ):
                inv = slot.inventory_held
                self.inventory_listbox.insert(tk.END, "")
                self.inventory_listbox.insert(tk.END, "=== KEY ITEMS ===")
                from er_save_manager.data.item_database import get_item_name

                for i, inv_item in enumerate(inv.key_items):
                    if inv_item.gaitem_handle != 0 and inv_item.quantity > 0:
                        gaitem = gaitem_map.get(inv_item.gaitem_handle)
                        if gaitem:
                            item_id = gaitem.item_id
                            item_name = get_item_name(item_id)
                            self.inventory_listbox.insert(
                                tk.END,
                                f"  [K{i}] {item_name} | Qty: {inv_item.quantity}",
                            )
                        else:
                            self.inventory_listbox.insert(
                                tk.END,
                                f"  [K{i}] Handle: {inv_item.gaitem_handle:08X} | Qty: {inv_item.quantity}",
                            )

            # Display storage inventory
            if (
                (filter_val in ["All", "Storage"])
                and hasattr(slot, "inventory_storage_box")
                and slot.inventory_storage_box
            ):
                inv = slot.inventory_storage_box
                self.inventory_listbox.insert(tk.END, "")
                self.inventory_listbox.insert(tk.END, "=== STORAGE BOX ===")
                from er_save_manager.data.item_database import get_item_name

                for i, inv_item in enumerate(inv.common_items):
                    if inv_item.gaitem_handle != 0 and inv_item.quantity > 0:
                        gaitem = gaitem_map.get(inv_item.gaitem_handle)
                        if gaitem:
                            item_id = gaitem.item_id
                            upgrade = (
                                gaitem.unk0x10 if gaitem.unk0x10 is not None else 0
                            )
                            item_name = get_item_name(item_id, upgrade)
                            self.inventory_listbox.insert(
                                tk.END,
                                f"  [S{i}] {item_name} | Qty: {inv_item.quantity} | +{upgrade}",
                            )
                        else:
                            self.inventory_listbox.insert(
                                tk.END,
                                f"  [S{i}] Handle: {inv_item.gaitem_handle:08X} | Qty: {inv_item.quantity}",
                            )

                # Key items in storage (only if All or Storage selected)
                if filter_val in ["All", "Storage"]:
                    from er_save_manager.data.item_database import get_item_name

                    for i, inv_item in enumerate(inv.key_items):
                        if inv_item.gaitem_handle != 0 and inv_item.quantity > 0:
                            gaitem = gaitem_map.get(inv_item.gaitem_handle)
                            if gaitem:
                                item_id = gaitem.item_id
                                item_name = get_item_name(item_id)
                                self.inventory_listbox.insert(
                                    tk.END,
                                    f"  [SK{i}] {item_name} | Qty: {inv_item.quantity}",
                                )
                            else:
                                self.inventory_listbox.insert(
                                    tk.END,
                                    f"  [SK{i}] Handle: {inv_item.gaitem_handle:08X} | Qty: {inv_item.quantity}",
                                )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to refresh inventory:\n{str(e)}", parent=self.parent
            )
            import traceback

            traceback.print_exc()

    def add_item(self):
        """Add item to inventory"""
        import logging

        log = logging.getLogger("er_save_manager.ui.inventory_editor")

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        if not self.selected_item:
            CTkMessageBox.showwarning(
                "No Item", "Please browse and select an item first!", parent=self.parent
            )
            return

        slot_idx = self.get_char_slot()
        item_id = self.selected_item.full_id
        quantity = self.inv_quantity_var.get()
        upgrade = self.inv_upgrade_var.get()
        location = self.inv_location_var.get()

        log.debug(
            f"add_item: selected_item.full_id={hex(self.selected_item.full_id)}, item_id={hex(item_id)}"
        )
        log.debug(
            f"add_item: slot_idx={slot_idx}, item_id={hex(item_id)}, quantity={quantity}, upgrade={upgrade}, location={location}"
        )

        try:
            # Ensure raw_data is mutable BEFORE any modifications
            self.ensure_mutable()
            if isinstance(save_file._raw_data, bytes):
                save_file._raw_data = bytearray(save_file._raw_data)

            # Create backup
            from er_save_manager.backup.manager import BackupManager

            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_add_item_{item_id}_slot_{slot_idx + 1}",
                    operation="add_inventory_item",
                    save=save_file,
                )

            slot = save_file.characters[slot_idx]
            log.debug(f"add_item: loaded slot, version={slot.version}")

            # Select inventory based on location
            if location == "held":
                inventory = slot.inventory_held
            else:
                inventory = slot.inventory_storage_box

            if not inventory:
                CTkMessageBox.showerror(
                    "Error", "Could not access inventory", parent=self.parent
                )
                return

            # Classify item into one of 5 categories
            item_category = item_id & 0xF0000000

            # Snapshot all four equipment structures before modification
            def _equip_snapshot(s) -> dict:
                return {
                    "lh1": s.left_hand_armament1,
                    "rh1": s.right_hand_armament1,
                    "lh2": s.left_hand_armament2,
                    "rh2": s.right_hand_armament2,
                    "lh3": s.left_hand_armament3,
                    "rh3": s.right_hand_armament3,
                    "head": s.head,
                    "chest": s.chest,
                    "arms": s.arms,
                    "legs": s.legs,
                    "tal1": s.talisman1,
                    "tal2": s.talisman2,
                    "tal3": s.talisman3,
                    "tal4": s.talisman4,
                }

            def _armaments_snapshot(s) -> dict:
                return {
                    "lh1": s.left_hand_armament1,
                    "rh1": s.right_hand_armament1,
                    "lh2": s.left_hand_armament2,
                    "rh2": s.right_hand_armament2,
                    "lh3": s.left_hand_armament3,
                    "rh3": s.right_hand_armament3,
                    "head": s.head,
                    "chest": s.chest,
                    "arms": s.arms,
                    "legs": s.legs,
                    "tal1": s.talisman1,
                    "tal2": s.talisman2,
                    "tal3": s.talisman3,
                    "tal4": s.talisman4,
                    "q1": s.quickitem1,
                    "q2": s.quickitem2,
                    "q3": s.quickitem3,
                    "pouch1": s.pouch1,
                    "pouch2": s.pouch2,
                }

            _pre_handles = _equip_snapshot(slot.equipped_items_gaitem_handle)
            _pre_item_ids = _equip_snapshot(slot.equipped_items_item_id)
            _pre_equip_idx = _equip_snapshot(slot.equipped_items_equip_index)
            _pre_armaments = _armaments_snapshot(slot.equipped_armaments_and_items)

            def _fmt(d):
                return ", ".join(
                    f"{k}=0x{v:08X}" for k, v in d.items() if v and v != 0xFFFFFFFF
                )

            log.debug(f"add_item: pre handles:    {_fmt(_pre_handles)}")
            log.debug(f"add_item: pre item_ids:   {_fmt(_pre_item_ids)}")
            log.debug(f"add_item: pre equip_idx:  {_fmt(_pre_equip_idx)}")
            log.debug(f"add_item: pre armaments:  {_fmt(_pre_armaments)}")

            log.debug(
                f"add_item: item_id=0x{item_id:08X} upgrade={upgrade} qty={quantity} location={location} slot={slot_idx}"
            )

            # Try to find an existing item to use as a template (for legacy compatibility)
            template_gaitem = None
            for _i, gaitem in enumerate(slot.gaitem_map):
                if gaitem.item_id == item_id:
                    template_gaitem = gaitem
                    break

            # Set gaitem field defaults (used by the gaitem path for weapons/armor/gems)
            if item_category == 0x00000000:  # Weapon
                default_unk0x10 = upgrade
                default_unk0x14 = (
                    0  # must be 0; non-zero values corrupt armor equip slots
                )
                default_gem_gaitem_handle = 0
                default_unk0x1c = 0
            elif item_category == 0x80000000:  # Gem/AoW
                default_unk0x10 = 0
                default_unk0x14 = 0
                default_gem_gaitem_handle = 0
                default_unk0x1c = 0
            else:  # Armor, Talisman, Goods — defaults unused for non-gaitem paths
                default_unk0x10 = 0
                default_unk0x14 = 0
                default_gem_gaitem_handle = 0
                default_unk0x1c = 0

            # Determine category and gaitem requirements.
            # Valid gaitem handle MSNs (from RE): 0x8 (weapons/gems), 0x9 (armor).
            # Goods and talismans do NOT have gaitem entries. They use a 0xB0 direct
            # handle stored in common_items:  handle = (item_id & 0x00FFFFFF) | 0xB0000000
            needs_gaitem = item_category in (0x00000000, 0x10000000, 0x80000000)
            if item_category == 0x00000000:  # Weapon
                category_name = "Weapon"
            elif (
                item_category == 0x10000000
            ):  # Protector (Armor) - 0x9 prefix, 16 bytes
                category_name = "Protector (Armor)"
            elif (
                item_category == 0x20000000
            ):  # Accessory (Talisman) - 0xB0 direct handle
                category_name = "Accessory (Talisman)"
            elif item_category == 0x40000000:  # Goods (Consumable) - 0xB0 direct handle
                category_name = "Goods (Consumable)"
            elif item_category == 0x80000000:  # Gem/AoW
                category_name = "Gem/AoW"
            else:
                logger.error(f"Unknown item category: 0x{item_category:08X}")
                CTkMessageBox.showerror(
                    "Invalid Item",
                    f"Unknown item category: 0x{item_category:08X}",
                    parent=self.parent,
                )
                return

            # Initialise gaitem size trackers; only set inside the gaitem branch.
            old_size = None
            new_size = None

            # ---- EARLY PATH: goods and talismans skip all gaitem logic ----
            if not needs_gaitem:
                gaitem_handle = (item_id & 0x00FFFFFF) | 0xB0000000
                log.debug(
                    f"add_item: {category_name} direct handle=0x{gaitem_handle:08X}"
                )
            else:
                # ---- GAITEM PATH: weapons, armor, gems -------------------------
                from er_save_manager.parser.er_types import Gaitem

                # Generate gaitem handle with correct prefix for this category
                if template_gaitem:
                    template_prefix = template_gaitem.gaitem_handle & 0xF0000000
                else:
                    if item_category == 0x00000000:  # Weapon
                        template_prefix = 0x80000000
                    elif item_category == 0x10000000:  # Armor
                        template_prefix = 0x90000000
                    else:  # Gem/AoW
                        template_prefix = 0xC0000000
                log.debug(
                    f"add_item: category={category_name} prefix=0x{template_prefix:08X}"
                )

                # The low 24 bits of a gaitem handle form a shared index space across all
                # prefixes (0x8=weapon/gem, 0x9=armor, 0xC=gem/AoW). The game indexes into
                # internal tables by this value, so 0x80800094 and 0x90800094 COLLIDE even
                # though their prefixes differ. Always scan all non-empty gaitems when
                # finding the next free index.
                all_indices = set()
                category_indices = set()
                for gaitem in slot.gaitem_map:
                    if gaitem.gaitem_handle != 0 and gaitem.item_id not in (
                        0,
                        0xFFFFFFFF,
                    ):
                        idx = gaitem.gaitem_handle & 0x00FFFFFF
                        all_indices.add(idx)
                        if (gaitem.gaitem_handle & 0xF0000000) == template_prefix:
                            category_indices.add(idx)

                # Find first gap in the unified index space at or above 0x80008C
                next_handle_index = 0x80008C
                if all_indices:
                    sorted_all = sorted(all_indices)
                    found_gap = False
                    for i in range(1, len(sorted_all)):
                        expected = sorted_all[i - 1] + 1
                        if sorted_all[i] != expected and expected >= 0x80008C:
                            log.debug(
                                f"add_item: handle gap between 0x{sorted_all[i - 1]:06X} and 0x{sorted_all[i]:06X}"
                            )
                            next_handle_index = expected
                            found_gap = True
                            break
                    if not found_gap:
                        next_handle_index = sorted_all[-1] + 1
                log.debug(
                    f"add_item: all_indices={len(all_indices)} category={len(category_indices)} next=0x{next_handle_index:06X}"
                )
                gaitem_handle = (template_prefix | next_handle_index) & 0xFFFFFFFF
                log.debug(
                    f"add_item: generated handle=0x{gaitem_handle:08X} gaitem_idx={next_handle_index:#x}"
                )

                # Create new gaitem (clone from template or use defaults)
                new_gaitem = Gaitem()
                new_gaitem.gaitem_handle = gaitem_handle
                new_gaitem.item_id = item_id
                if template_gaitem:
                    new_gaitem.unk0x10 = template_gaitem.unk0x10
                    new_gaitem.unk0x14 = (
                        0  # never copy unk0x14; non-zero corrupts armor slots
                    )
                    new_gaitem.gem_gaitem_handle = 0  # don't share gem entries
                    new_gaitem.unk0x1c = template_gaitem.unk0x1c
                else:
                    new_gaitem.unk0x10 = default_unk0x10
                    new_gaitem.unk0x14 = default_unk0x14
                    new_gaitem.gem_gaitem_handle = default_gem_gaitem_handle
                    new_gaitem.unk0x1c = default_unk0x1c

                # unk0x10 = upgrade level, unk0x14 = 0 always (non-zero corrupts armor slots)
                if item_category == 0x00000000:
                    new_gaitem.unk0x10 = upgrade

                # Find where items of this category live in the gaitem_map
                category_indices = []
                for i, gaitem in enumerate(slot.gaitem_map):
                    if gaitem.gaitem_handle != 0 and gaitem.item_id not in (
                        0,
                        0xFFFFFFFF,
                    ):
                        gaitem_prefix = (gaitem.gaitem_handle >> 28) & 0xF
                        if (
                            gaitem_prefix == 0x8 and item_category == 0x00000000
                        ):  # Weapons
                            category_indices.append(i)
                        elif (
                            gaitem_prefix == 0x9 and item_category == 0x10000000
                        ):  # Armor
                            category_indices.append(i)
                        elif (
                            gaitem_prefix == 0x8 and item_category == 0x80000000
                        ):  # Gems/AoW
                            category_indices.append(i)

                if category_indices:
                    min_idx = min(category_indices)
                    max_idx = max(category_indices)

                    empty_gaitem_idx = -1
                    for i in range(min_idx, max_idx + 1):
                        if slot.gaitem_map[i].item_id in (0, 0xFFFFFFFF):
                            empty_gaitem_idx = i
                            break
                    if empty_gaitem_idx == -1:
                        for i in range(max_idx + 1, len(slot.gaitem_map)):
                            if slot.gaitem_map[i].item_id in (0, 0xFFFFFFFF):
                                empty_gaitem_idx = i
                                break
                else:
                    empty_gaitem_idx = -1
                    for i, gaitem in enumerate(slot.gaitem_map):
                        if gaitem.item_id in (0, 0xFFFFFFFF):
                            empty_gaitem_idx = i
                            break

                if empty_gaitem_idx == -1:
                    logger.error("No empty gaitem slots available!")
                    CTkMessageBox.showerror(
                        "No Space",
                        "No empty gaitem slots available!",
                        parent=self.parent,
                    )
                    return

                old_gaitem = slot.gaitem_map[empty_gaitem_idx]
                old_size = old_gaitem.get_size()
                log.debug(
                    f"add_item: gaitem[{empty_gaitem_idx}] {hex(old_gaitem.gaitem_handle)}/{hex(old_gaitem.item_id)} -> handle=0x{gaitem_handle:08X} item=0x{item_id:08X} unk0x10={new_gaitem.unk0x10} unk0x14={new_gaitem.unk0x14}"
                )

                slot.gaitem_map[empty_gaitem_idx] = new_gaitem
                new_size = new_gaitem.get_size()

            # ---- COMMON: build inventory entry and write to common_items ----
            # All categories (weapons, armor, gems, goods, talismans) go into common_items.
            # key_items is not used for player inventory spawning.
            max_acquisition = 0
            for inv_item in inventory.common_items:
                if (
                    inv_item.gaitem_handle != 0
                    and inv_item.acquisition_index > max_acquisition
                ):
                    max_acquisition = inv_item.acquisition_index
            for inv_item in inventory.key_items:
                if (
                    inv_item.gaitem_handle != 0
                    and inv_item.acquisition_index > max_acquisition
                ):
                    max_acquisition = inv_item.acquisition_index

            next_acquisition = max_acquisition + 1

            from er_save_manager.parser.equipment import InventoryItem

            new_inv_item = InventoryItem()
            new_inv_item.gaitem_handle = gaitem_handle
            new_inv_item.quantity = quantity
            new_inv_item.acquisition_index = next_acquisition

            last_used_idx = -1
            for i, inv_item in enumerate(inventory.common_items):
                if inv_item.gaitem_handle != 0 and inv_item.gaitem_handle != 0xFFFFFFFF:
                    last_used_idx = i
            empty_inv_idx = last_used_idx + 1
            if empty_inv_idx >= len(inventory.common_items):
                log.warning("add_item: no empty inventory slots!")
                CTkMessageBox.showwarning(
                    "Inventory Full", "No empty slots in inventory!", parent=self.parent
                )
                return
            log.debug(f"add_item: inv slot {last_used_idx} -> {empty_inv_idx}")
            log.debug(
                f"add_item: counters equip_idx={inventory.equip_index_counter} acq={inventory.acquisition_index_counter}"
            )

            # Warn if this inventory index is currently used as an equip_index slot
            # (game resolves equipped items by inv array index, not by handle)
            for eq_slot, eq_idx in _pre_equip_idx.items():
                if eq_idx == empty_inv_idx and eq_idx != 0 and eq_idx != 0xFFFFFFFF:
                    log.warning(
                        f"add_item: inv slot {empty_inv_idx} is equip_idx[{eq_slot}]=0x{eq_idx:08X} - may overwrite equipped item"
                    )
            inventory.common_items[empty_inv_idx] = new_inv_item
            inventory.common_item_count += 1
            inventory.acquisition_index_counter = next_acquisition + 1
            log.debug(
                f"add_item: inv[{empty_inv_idx}] handle=0x{gaitem_handle:08X} qty={quantity} acq={next_acquisition} count={inventory.common_item_count}"
            )

            # Register item in GaitemGameData (the game's item registry).
            # Without this entry the game ignores the item entirely — it never appears.
            # Structure: fixed 7000-entry array, active entries = count.
            # next_item_id forms a sorted linked list by item_id across all entries.
            # Only needed for gaitem-backed items (weapons/armor/gems) not direct-handle goods.
            if not (gaitem_handle & 0xF0000000) == 0xB0000000:
                from er_save_manager.parser.world import GaitemGameDataEntry

                ggd = slot.gaitem_game_data
                already_registered = any(
                    e.id == item_id for e in ggd.entries[: ggd.count]
                )
                new_idx = ggd.count
                if already_registered:
                    log.debug(
                        f"add_item: ggd already has 0x{item_id:08X}, skipping registration"
                    )
                elif new_idx < len(ggd.entries):
                    _old_e = ggd.entries[new_idx]
                    log.debug(
                        f"add_item: ggd[{new_idx}] BEFORE: id=0x{_old_e.id:08X} unk0x4={_old_e.unk0x4} next=0x{_old_e.next_item_id:08X} unk0xc={_old_e.unk0xc}"
                    )
                    new_entry = GaitemGameDataEntry()
                    new_entry.id = item_id
                    new_entry.unk0x4 = 1
                    new_entry.unk0xc = 1
                    # Each item category forms its own sorted chain (weapon, armor, goods, etc).
                    # Only entries with the same category prefix as item_id belong to this chain.
                    cat_prefix = item_id & 0xF0000000
                    cat_entries = {
                        e.id: i
                        for i, e in enumerate(ggd.entries[:new_idx])
                        if (e.id & 0xF0000000) == cat_prefix
                    }
                    cat_nexts = {
                        ggd.entries[i].next_item_id for i in cat_entries.values()
                    }
                    cat_ids = set(cat_entries.keys())
                    head_ids = cat_ids - cat_nexts
                    head_id = min(head_ids) if head_ids else None
                    pred_idx = -1
                    if head_id is not None:
                        cur_id = head_id
                        while cur_id and cur_id in cat_entries:
                            cur_e = ggd.entries[cat_entries[cur_id]]
                            nxt = cur_e.next_item_id
                            if cur_id < item_id and (nxt == 0 or nxt > item_id):
                                pred_idx = cat_entries[cur_id]
                                break
                            if nxt == 0 or nxt > item_id:
                                break
                            cur_id = nxt
                    if pred_idx >= 0:
                        new_entry.next_item_id = ggd.entries[pred_idx].next_item_id
                        ggd.entries[pred_idx].next_item_id = item_id
                    else:
                        new_entry.next_item_id = head_id if head_id else 0
                    ggd.entries[new_idx] = new_entry
                    ggd.count += 1
                    log.debug(
                        f"add_item: ggd[{new_idx}] registered id=0x{item_id:08X} next=0x{new_entry.next_item_id:08X} (count={ggd.count})"
                    )
                    # Dump entries around insertion to verify chain
                    for di in range(
                        max(0, new_idx - 2), min(len(ggd.entries), new_idx + 3)
                    ):
                        e = ggd.entries[di]
                        log.debug(
                            f"add_item: ggd[{di}] id=0x{e.id:08X} unk0x4={e.unk0x4} next=0x{e.next_item_id:08X} unk0xc={e.unk0xc}"
                        )
                else:
                    log.warning(
                        f"add_item: gaitem_game_data full ({len(ggd.entries)} entries), item may not appear in game"
                    )

            # Rebuild slot
            try:
                slot_bytes = rebuild_slot(slot)
                if len(slot_bytes) != 0x280000:
                    log.error(
                        f"add_item: rebuild size mismatch: {len(slot_bytes)} != 0x280000"
                    )
                    raise ValueError("Rebuild size mismatch")
            except Exception as e:
                log.error(f"add_item: rebuild failed: {e}")
                raise

            # Write rebuilt slot to _raw_data at the correct offset
            CHECKSUM_SIZE = 0x10
            slot_offset = save_file._slot_offsets[slot_idx]
            abs_offset = slot_offset + CHECKSUM_SIZE

            if abs_offset + len(slot_bytes) > len(save_file._raw_data):
                log.error(
                    f"add_item: write OOB: {abs_offset + len(slot_bytes)} > {len(save_file._raw_data)}"
                )
                raise ValueError("Write would exceed file bounds")

            save_file._raw_data[abs_offset : abs_offset + len(slot_bytes)] = slot_bytes

            # Re-parse the slot from _raw_data so the in-memory object reflects the
            # new gaitem_map. Without this, a second add_item call in the same session
            # reads the stale pre-modification slot and generates duplicate handles.
            try:
                from io import BytesIO as _BytesIO

                from er_save_manager.parser.user_data_x import UserDataX as _UserDataX

                _slot_buf = _BytesIO(
                    bytes(
                        save_file._raw_data[abs_offset : abs_offset + len(slot_bytes)]
                    )
                )
                save_file.character_slots[slot_idx] = _UserDataX.read(
                    _slot_buf, save_file.is_ps, 0, len(slot_bytes)
                )
                log.debug("add_item: in-memory slot refreshed from _raw_data")
            except Exception as _e:
                log.warning(f"add_item: could not refresh slot in memory: {_e}")

            # Recalculate checksums and save
            save_file.recalculate_checksums()
            log.debug("add_item: checksums recalculated")

            save_path = self.get_save_path()
            if save_path:
                save_file.to_file(Path(save_path))
                log.debug(f"add_item: saved to {save_path}")

                # Ensure file is flushed to disk
                import time

                time.sleep(0.1)

            # Re-read the save file to verify the item persisted
            try:
                verification_save = Save.from_file(str(save_path))
                verification_slot = verification_save.get_slot(slot_idx)

                # Verify gaitem entry (not applicable for B0 direct-handle items)
                is_direct = (gaitem_handle & 0xF0000000) == 0xB0000000
                gaitem_ok = is_direct
                gaitem_idx = -1
                gaitem_size = 0
                if not is_direct:
                    for idx, gm in enumerate(verification_slot.gaitem_map):
                        if gm.gaitem_handle == gaitem_handle:
                            gaitem_ok = True
                            gaitem_idx = idx
                            gaitem_size = gm.get_size()
                            break

                # Verify inventory slot
                inv_list = (
                    verification_slot.inventory_held.common_items
                    if location == "held"
                    else verification_slot.inventory_storage_box.common_items
                )
                inv_ok = any(i.gaitem_handle == gaitem_handle for i in inv_list)

                # Collect equipped weapon + armor handles for cross-check
                gh = verification_slot.equipped_items_gaitem_handle
                equipped_weapons = [
                    gh.left_hand_armament1,
                    gh.right_hand_armament1,
                    gh.left_hand_armament2,
                    gh.right_hand_armament2,
                    gh.left_hand_armament3,
                    gh.right_hand_armament3,
                ]
                equipped_armor = [gh.head, gh.chest, gh.arms, gh.legs]
                equipped_talismans = [
                    gh.talisman1,
                    gh.talisman2,
                    gh.talisman3,
                    gh.talisman4,
                ]
                all_equipped = equipped_weapons + equipped_armor + equipped_talismans

                gaitem_str = (
                    f"gaitem[{gaitem_idx}] size={gaitem_size}B"
                    if gaitem_ok and not is_direct
                    else ("direct-handle" if is_direct else "MISSING-FROM-GAITEM-MAP")
                )
                inv_str = "ok" if inv_ok else "MISSING-FROM-INVENTORY"
                equipped_str = (
                    "unexpectedly-equipped!"
                    if gaitem_handle in all_equipped
                    else "unequipped"
                )

                status = "OK" if (gaitem_ok and inv_ok) else "FAIL"
                logger.info(
                    f"[{status}] 0x{item_id:08X} {category_name} +{upgrade} "
                    f"handle=0x{gaitem_handle:08X} {gaitem_str} inv={inv_str} equip={equipped_str}"
                )

                # Log equipped armor handles so we can verify none were clobbered
                armor_names = ["head", "chest", "arms", "legs"]
                armor_strs = [
                    f"{n}=0x{h:08X}"
                    for n, h in zip(armor_names, equipped_armor, strict=False)
                    if h and h != 0xFFFFFFFF
                ]
                talisman_strs = [
                    f"tal{i + 1}=0x{h:08X}"
                    for i, h in enumerate(equipped_talismans)
                    if h and h != 0xFFFFFFFF
                ]
                if armor_strs or talisman_strs:
                    logger.info(f"  equipped: {', '.join(armor_strs + talisman_strs)}")

                # Diff all four equipment structures against pre-write snapshots
                post_handles = _equip_snapshot(gh)
                post_item_ids = _equip_snapshot(
                    verification_slot.equipped_items_item_id
                )
                post_equip_idx = _equip_snapshot(
                    verification_slot.equipped_items_equip_index
                )
                post_armaments = _armaments_snapshot(
                    verification_slot.equipped_armaments_and_items
                )

                for label, pre, post in [
                    ("handles", _pre_handles, post_handles),
                    ("item_ids", _pre_item_ids, post_item_ids),
                    ("equip_idx", _pre_equip_idx, post_equip_idx),
                    ("armaments", _pre_armaments, post_armaments),
                ]:
                    for k in pre:
                        if pre[k] != post.get(k, 0):
                            log.warning(
                                f"add_item: {label}[{k}] changed: 0x{pre[k]:08X} -> 0x{post.get(k, 0):08X}"
                            )

                if gaitem_handle in all_equipped:
                    log.warning(
                        f"add_item: new item 0x{gaitem_handle:08X} landed in equip slots - check unk0x14"
                    )

            except Exception as verify_error:
                log.error(f"add_item: verification failed: {verify_error}")
                import traceback

                log.error(traceback.format_exc())

            item_id_display = f"0x{item_id:08X}" if item_id is not None else "Unknown"
            gaitem_line = (
                f"Gaitem expanded from {old_size} to {new_size} bytes\n\n"
                if old_size is not None
                else "\n"
            )
            CTkMessageBox.showinfo(
                "Success",
                f"Added {category_name}: {item_id_display} (x{quantity}) +{upgrade} to {location}!\n"
                f"Handle: 0x{gaitem_handle:08X}\n"
                + gaitem_line
                + "Please reload the save to see changes.",
                parent=self.parent,
            )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to add item:\n{str(e)}", parent=self.parent
            )
            import traceback

            traceback.print_exc()

    def apply_inventory_changes(self):
        """Apply inventory changes - save to disk with checksum recalculation"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        slot_idx = self.get_char_slot()
        if not CTkMessageBox.askyesno(
            "Confirm",
            f"Apply all inventory changes to Slot {slot_idx + 1}?\n\nA backup will be created.",
            parent=self.parent,
        ):
            return

        try:
            # Ensure raw_data is mutable
            if isinstance(save_file._raw_data, bytes):
                save_file._raw_data = bytearray(save_file._raw_data)

            slot = save_file.characters[slot_idx]
            if not slot or slot.is_empty():
                CTkMessageBox.showwarning(
                    "Empty Slot", f"Slot {slot_idx + 1} is empty!", parent=self.parent
                )
                return

            # Create backup
            save_path = self.get_save_path()
            if save_path:
                from pathlib import Path

                from er_save_manager.backup.manager import BackupManager

                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_inventory_changes_slot_{slot_idx + 1}",
                    operation=f"inventory_changes_slot_{slot_idx + 1}",
                    save=save_file,
                )

            # Serialize whole slot and write back
            logger.info(f"Rebuilding slot {slot_idx + 1}...")
            slot_bytes = rebuild_slot(slot)
            logger.info(f"Slot rebuilt: {len(slot_bytes)} bytes")

            # Write to _raw_data
            CHECKSUM_SIZE = 0x10
            slot_offset = save_file._slot_offsets[slot_idx]
            abs_offset = slot_offset + CHECKSUM_SIZE
            save_file._raw_data[abs_offset : abs_offset + len(slot_bytes)] = slot_bytes

            save_file.recalculate_checksums()
            save_file.save(save_path)

            CTkMessageBox.showinfo(
                "Success",
                "Inventory changes applied successfully!",
                parent=self.parent,
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            CTkMessageBox.showerror(
                "Error", f"Failed to apply inventory changes:\n{e}", parent=self.parent
            )

    def remove_item(self):
        """Remove selected item from inventory"""
        selection = self.inventory_listbox.curselection()
        if not selection:
            CTkMessageBox.showwarning(
                "No Selection", "Please select an item to remove!", parent=self.parent
            )
            return

        save_file = self.get_save_file()
        if not save_file:
            return

        # Parse selection to get item location and index
        selected_text = self.inventory_listbox.get(selection[0])

        # Skip header lines
        if "===" in selected_text:
            return

        try:
            # Extract index from format
            match = re.search(r"\[([SK]?)(\d+)\]", selected_text)
            if not match:
                return

            location_prefix = match.group(1)
            idx = int(match.group(2))

            slot_idx = self.get_char_slot()
            slot = save_file.characters[slot_idx]

            # Determine inventory and offset
            if location_prefix.startswith("S"):
                inventory = slot.inventory_storage_box
                is_key = location_prefix == "SK"
            else:
                inventory = slot.inventory_held
                is_key = location_prefix == "K"

            # Create backup
            from er_save_manager.backup.manager import BackupManager

            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_remove_item_slot_{slot_idx + 1}",
                    operation="remove_inventory_item",
                    save=save_file,
                )

            # Clear the item
            from er_save_manager.parser.equipment import InventoryItem

            if is_key:
                old_handle = inventory.key_items[idx].gaitem_handle
                inventory.key_items[idx] = InventoryItem()
                inventory.key_item_count = max(0, inventory.key_item_count - 1)
            else:
                old_handle = inventory.common_items[idx].gaitem_handle
                inventory.common_items[idx] = InventoryItem()
                inventory.common_item_count = max(0, inventory.common_item_count - 1)

            # Also clear the gaitem in gaitem_map

            for i, gaitem in enumerate(slot.gaitem_map):
                if gaitem.gaitem_handle == old_handle:
                    size_to_preserve = gaitem.get_size()
                    slot.gaitem_map[i] = self._make_blank_gaitem_with_size(
                        size_to_preserve
                    )
                    break

            # Serialize and write the full slot to keep offsets consistent
            logger.info("Rebuilding slot after item removal...")
            slot_bytes = rebuild_slot(slot)
            logger.info(f"Slot rebuilt: {len(slot_bytes)} bytes")

            # Write to _raw_data
            CHECKSUM_SIZE = 0x10
            slot_offset = save_file._slot_offsets[slot_idx]
            abs_offset = slot_offset + CHECKSUM_SIZE
            save_file._raw_data[abs_offset : abs_offset + len(slot_bytes)] = slot_bytes

            save_file.recalculate_checksums()
            save_path = self.get_save_path()
            if save_path:
                save_file.to_file(Path(save_path))

            self.refresh_inventory()

            CTkMessageBox.showinfo(
                "Success", "Item removed from inventory!", parent=self.parent
            )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to remove item:\n{str(e)}", parent=self.parent
            )
            import traceback

            traceback.print_exc()
