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
        """Update item dropdown when category changes"""
        category = self.category_var.get()
        items = self.item_db.get_items_by_category(category)
        item_names = [f"{item.name} [0x{item.full_id:08X}]" for item in items]
        self.item_combobox.configure(values=item_names)
        if item_names:
            self.item_name_var.set(item_names[0])
        else:
            self.item_name_var.set("")

        # Item list frame
        list_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        list_frame.pack(fill=ctk.BOTH, expand=True, pady=5, padx=10)
        ctk.CTkLabel(
            list_frame,
            text="Current Inventory",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=ctk.W, padx=5, pady=(5, 0))

        # Filter frame
        filter_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
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
        inv_list_container = ctk.CTkFrame(list_frame, fg_color="transparent")
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
            base_item_id = item_id & 0x0FFFFFFF

            logger.info("=" * 80)
            logger.info(f"STARTING ITEM ADDITION: Item ID {item_id:08X}")
            logger.info("=" * 80)

            # Try to find an existing item to use as a template (for legacy compatibility)
            template_gaitem = None
            for _i, gaitem in enumerate(slot.gaitem_map):
                if gaitem.item_id == item_id:
                    template_gaitem = gaitem
                    break

            # Determine category enum and expected size
            if item_category == 0x00000000:  # Weapon
                category = 0
                category_name = "Weapon"
                expected_size = 21
                default_unk0x10 = upgrade
                default_unk0x14 = 0x20
                default_gem_gaitem_handle = 0
                default_unk0x1c = 0
            elif item_category == 0x10000000:  # Protector (Armor)
                category = 3
                category_name = "Protector (Armor)"
                expected_size = 16
                default_unk0x10 = 0
                default_unk0x14 = 0
                default_gem_gaitem_handle = 0
                default_unk0x1c = 0
            elif item_category == 0x20000000:  # Accessory (Talisman)
                category = 2
                category_name = "Accessory (Talisman)"
                expected_size = 16
                default_unk0x10 = 0
                default_unk0x14 = 0
                default_gem_gaitem_handle = 0
                default_unk0x1c = 0
            elif item_category == 0x40000000:  # Goods (Consumable)
                category = 1
                category_name = "Goods (Consumable)"
                expected_size = 16
                default_unk0x10 = 0
                default_unk0x14 = 0
                default_gem_gaitem_handle = 0
                default_unk0x1c = 0
            elif item_category == 0x80000000:  # Gem/AoW
                category = 0
                category_name = "Gem/AoW"
                expected_size = 21
                default_unk0x10 = 0
                default_unk0x14 = 0
                default_gem_gaitem_handle = 0
                default_unk0x1c = 0
            else:
                logger.error(f"Unknown item category: 0x{item_category:08X}")
                CTkMessageBox.showerror(
                    "Invalid Item",
                    f"Unknown item category: 0x{item_category:08X}",
                    parent=self.parent,
                )
                return

            # Find empty gaitem slot as before
            from er_save_manager.parser.er_types import Gaitem

            # Generate gaitem handle
            if template_gaitem:
                template_prefix = template_gaitem.gaitem_handle & 0xF0000000
            else:
                # Use category prefix: 0x8 for weapons/gems, 0x9 for goods, 0xA for accessories, 0xB for armor
                if item_category == 0x00000000 or item_category == 0x80000000:
                    template_prefix = 0x80000000
                elif item_category == 0x40000000:
                    template_prefix = 0x90000000
                elif item_category == 0x20000000:
                    template_prefix = 0xA0000000
                elif item_category == 0x10000000:
                    template_prefix = 0xB0000000
                else:
                    template_prefix = 0x80000000

            # Find the highest handle index for this category to determine next sequential index
            category_indices = []
            for gaitem in slot.gaitem_map:
                if gaitem.gaitem_handle != 0 and gaitem.item_id not in (0, 0xFFFFFFFF):
                    gaitem_prefix = gaitem.gaitem_handle & 0xF0000000
                    if gaitem_prefix == template_prefix:
                        handle_index = gaitem.gaitem_handle & 0x00FFFFFF
                        category_indices.append(handle_index)

            category_indices.sort()

            # Find first gap in the sequence
            next_handle_index = None
            if category_indices:
                for i in range(len(category_indices) - 1):
                    current = category_indices[i]
                    next_expected = category_indices[i + 1]
                    if next_expected - current > 1:
                        next_handle_index = current + 1
                        break
                if next_handle_index is None:
                    next_handle_index = category_indices[-1] + 1
            else:
                next_handle_index = 0x8C

            gaitem_handle = (template_prefix | next_handle_index) & 0xFFFFFFFF

            # Create new gaitem (clone if template, else use defaults)
            new_gaitem = Gaitem()
            new_gaitem.gaitem_handle = gaitem_handle
            new_gaitem.item_id = item_id
            if template_gaitem:
                new_gaitem.unk0x10 = template_gaitem.unk0x10
                new_gaitem.unk0x14 = template_gaitem.unk0x14
                new_gaitem.gem_gaitem_handle = template_gaitem.gem_gaitem_handle
                new_gaitem.unk0x1c = template_gaitem.unk0x1c
            else:
                new_gaitem.unk0x10 = default_unk0x10
                new_gaitem.unk0x14 = default_unk0x14
                new_gaitem.gem_gaitem_handle = default_gem_gaitem_handle
                new_gaitem.unk0x1c = default_unk0x1c

            # Apply upgrade if requested (for weapons)
            if item_category == 0x00000000 and upgrade > 0:
                new_gaitem.unk0x10 = upgrade
                if self.inv_reinforcement_var.get() == "somber":
                    new_gaitem.unk0x14 = 0x30
                else:
                    new_gaitem.unk0x14 = 0x20

            # DEBUG: Check existing weapon handles to verify correct category
            logger.info("\n--- EXISTING WEAPON HANDLES (for category verification) ---")
            weapon_count = 0
            for i, gaitem in enumerate(slot.gaitem_map):
                if gaitem.item_id != 0 and gaitem.item_id != 0xFFFFFFFF:
                    item_cat = gaitem.item_id & 0xF0000000
                    if item_cat == 0x00000000:  # Weapon item
                        handle_prefix = (gaitem.gaitem_handle >> 28) & 0xF
                        logger.info(
                            f"  Weapon[{i}]: item_id=0x{gaitem.item_id:08X}, handle=0x{gaitem.gaitem_handle:08X}, prefix=0x{handle_prefix:X}, size={gaitem.get_size()}"
                        )
                        weapon_count += 1
                        if weapon_count >= 3:  # Only show first 3 for brevity
                            break

            logger.info("\n--- STEP 1: CLASSIFY ITEM ---")
            logger.info(f"Full item ID: 0x{item_id:08X}")
            logger.info(f"Base item ID: 0x{base_item_id:08X}")
            logger.info(f"Category bits: 0x{item_category:08X}")

            # Determine category enum and expected size
            # CRITICAL: Handle type determines gaitem size in er_types.py:
            # - Type 0x8 (category 0): 21 bytes with gem fields - WEAPONS
            # - Type 0x9-0xB (category 1-3): 16 bytes with upgrade fields - ARMOR/GOODS/TALISMANS
            # - Type 0xC (category 4): 8 bytes base only - SPECIAL/EQUIPPED ITEMS
            if item_category == 0x00000000:  # Weapon
                category = 0  # Prefix 0x8 - gets full 21-byte structure
                category_name = "Weapon"
                expected_size = 21
            elif item_category == 0x10000000:  # Protector (Armor)
                category = 3  # Prefix 0xB
                category_name = "Protector (Armor)"
                expected_size = 16
            elif item_category == 0x20000000:  # Accessory (Talisman)
                category = 2  # Prefix 0xA
                category_name = "Accessory (Talisman)"
                expected_size = 16
            elif item_category == 0x40000000:  # Goods (Consumable)
                category = 1  # Prefix 0x9
                category_name = "Goods (Consumable)"
                expected_size = 16
            elif item_category == 0x80000000:  # Gem/AoW
                category = 0  # Prefix 0x8 - same as weapons, gets gem fields
                category_name = "Gem/AoW"
                expected_size = 21
            else:
                logger.error(f"Unknown item category: 0x{item_category:08X}")
                CTkMessageBox.showerror(
                    "Invalid Item",
                    f"Unknown item category: 0x{item_category:08X}",
                    parent=self.parent,
                )
                return

            logger.info(f"Category: {category} ({category_name})")
            logger.info(f"Expected final gaitem size: {expected_size} bytes")

            # Find empty gaitem slot IN THE SAME REGION as existing items of this category
            from er_save_manager.parser.er_types import Gaitem

            logger.info("\n--- STEP 2: FIND EMPTY GAITEM SLOT ---")

            # First, find where items of this category are stored
            category_indices = []
            for i, gaitem in enumerate(slot.gaitem_map):
                if gaitem.gaitem_handle != 0 and gaitem.item_id not in (0, 0xFFFFFFFF):
                    gaitem_category = (gaitem.gaitem_handle >> 28) & 0xF
                    # Map back to our category format (0x8->0, 0x9->1, 0xA->2, 0xB->3)
                    if gaitem_category == 0x8 and category == 0x00000000:  # Weapons
                        category_indices.append(i)
                    elif gaitem_category == 0x9 and category == 0x40000000:  # Goods
                        category_indices.append(i)
                    elif (
                        gaitem_category == 0xA and category == 0x20000000
                    ):  # Accessories
                        category_indices.append(i)
                    elif gaitem_category == 0xB and category == 0x10000000:  # Armor
                        category_indices.append(i)

            if category_indices:
                min_idx = min(category_indices)
                max_idx = max(category_indices)
                logger.info(
                    f"Found {len(category_indices)} existing items of this category"
                )
                logger.info(f"  Category region: indices {min_idx} to {max_idx}")

                # Search for empty slot within or near this region
                # First try within the region
                empty_gaitem_idx = -1
                for i in range(min_idx, max_idx + 1):
                    if slot.gaitem_map[i].item_id in (0, 0xFFFFFFFF):
                        empty_gaitem_idx = i
                        logger.info(
                            f"Found empty slot WITHIN category region at index: {i}"
                        )
                        break

                # If no empty slot within region, try right after
                if empty_gaitem_idx == -1:
                    for i in range(max_idx + 1, len(slot.gaitem_map)):
                        if slot.gaitem_map[i].item_id in (0, 0xFFFFFFFF):
                            empty_gaitem_idx = i
                            logger.info(
                                f"Found empty slot AFTER category region at index: {i}"
                            )
                            break
            else:
                # No existing items of this category, find any empty slot
                logger.info(
                    "No existing items of this category found, using first empty slot"
                )
                empty_gaitem_idx = -1
                for i, gaitem in enumerate(slot.gaitem_map):
                    if gaitem.item_id in (0, 0xFFFFFFFF):
                        empty_gaitem_idx = i
                        logger.info(f"Found empty slot at index: {i}")
                        break

            if empty_gaitem_idx == -1:
                logger.error("No empty gaitem slots available!")
                CTkMessageBox.showerror(
                    "No Space",
                    "No empty gaitem slots available!",
                    parent=self.parent,
                )
                return

            # Log the slot
            gaitem = slot.gaitem_map[empty_gaitem_idx]
            logger.info(f"  BEFORE - handle: 0x{gaitem.gaitem_handle:08X}")
            logger.info(f"  BEFORE - item_id: 0x{gaitem.item_id:08X}")
            logger.info(f"  BEFORE - size: {gaitem.get_size()} bytes")

            log.debug(f"add_item: empty_gaitem_idx={empty_gaitem_idx}")

            # Log the gaitem we're replacing
            old_gaitem = slot.gaitem_map[empty_gaitem_idx]
            old_size = old_gaitem.get_size()
            log.debug(
                f"add_item: replacing gaitem[{empty_gaitem_idx}]: handle={hex(old_gaitem.gaitem_handle)}, "
                f"item_id={hex(old_gaitem.item_id)}, size={old_size}, "
                f"unk0x10={old_gaitem.unk0x10}, unk0x14={old_gaitem.unk0x14}"
            )

            # Find first empty inventory slot
            from er_save_manager.parser.equipment import InventoryItem

            # Find the last used inventory slot, then place after it
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

            logger.info(f"Last used inventory slot: {last_used_idx}")
            logger.info(f"Placing new item at slot: {empty_inv_idx}")

            log.debug(f"add_item: empty_inv_idx={empty_inv_idx}")

            # Generate gaitem handle using game's algorithm
            logger.info(
                "\n--- STEP 3: GENERATE GAITEM HANDLE (next sequential index) ---"
            )

            # Find the highest handle index for this category to determine next sequential index

            if template_gaitem:
                template_prefix = template_gaitem.gaitem_handle & 0xF0000000

            # Collect all handle indices for this category, sorted
            category_indices = []
            for gaitem in slot.gaitem_map:
                if gaitem.gaitem_handle != 0 and gaitem.item_id not in (0, 0xFFFFFFFF):
                    gaitem_prefix = gaitem.gaitem_handle & 0xF0000000
                    if gaitem_prefix == template_prefix:
                        handle_index = gaitem.gaitem_handle & 0x00FFFFFF
                        category_indices.append(handle_index)

            category_indices.sort()

            # Find first gap in the sequence
            next_handle_index = None
            if category_indices:
                # Look for first missing number in sequence
                for i in range(len(category_indices) - 1):
                    current = category_indices[i]
                    next_expected = category_indices[i + 1]
                    if next_expected - current > 1:
                        # Found a gap!
                        next_handle_index = current + 1
                        logger.info(
                            f"Found gap in sequence between 0x{current:X} and 0x{next_expected:X}"
                        )
                        break

                # If no gap found, use max + 1
                if next_handle_index is None:
                    next_handle_index = category_indices[-1] + 1
                    logger.info("No gaps in sequence, using max + 1")
            else:
                # No existing items in category, start from a base number
                next_handle_index = 0x8C  # Start from same base as existing weapons
                logger.info("No existing items in category, starting from 0x8C")

            new_handle = (template_prefix | next_handle_index) & 0xFFFFFFFF

            if template_gaitem:
                logger.info(f"Template handle: 0x{template_gaitem.gaitem_handle:08X}")
            else:
                logger.info(
                    "No template gaitem found; using category defaults for handle prefix."
                )
            logger.info(f"Template prefix: 0x{template_prefix:08X}")
            logger.info(f"Category has {len(category_indices)} existing items")
            logger.info(
                f"Next sequential handle index: 0x{next_handle_index:X} ({next_handle_index})"
            )
            logger.info(f"Array position for storage: {empty_gaitem_idx}")
            logger.info(f"GENERATED HANDLE: 0x{new_handle:08X}")

            gaitem_handle = new_handle

            log.debug(f"add_item: gaitem_handle=0x{gaitem_handle:08X}")

            # Create new gaitem by CLONING the template EXACTLY
            logger.info("\n--- STEP 4: CREATE NEW WEAPON FROM TEMPLATE ---")
            new_gaitem = Gaitem()
            new_gaitem.gaitem_handle = gaitem_handle  # New handle with new index
            new_gaitem.item_id = item_id  # Always use the selected item_id

            # Clone ALL fields from template to ensure correct structure, or use defaults
            if template_gaitem:
                new_gaitem.unk0x10 = template_gaitem.unk0x10
                new_gaitem.unk0x14 = template_gaitem.unk0x14
                new_gaitem.gem_gaitem_handle = template_gaitem.gem_gaitem_handle
                new_gaitem.unk0x1c = template_gaitem.unk0x1c
            else:
                new_gaitem.unk0x10 = default_unk0x10
                new_gaitem.unk0x14 = default_unk0x14
                new_gaitem.gem_gaitem_handle = default_gem_gaitem_handle
                new_gaitem.unk0x1c = default_unk0x1c

            logger.info("Cloning weapon:")
            if template_gaitem:
                logger.info(
                    f"  Template: item_id=0x{template_gaitem.item_id:08X}, handle=0x{template_gaitem.gaitem_handle:08X}"
                )
            else:
                logger.info("  No template gaitem found; using category defaults.")
            logger.info(
                f"  New copy: item_id=0x{new_gaitem.item_id:08X}, handle=0x{new_gaitem.gaitem_handle:08X}"
            )
            logger.info("Cloned fields:")
            logger.info(f"  unk0x10={new_gaitem.unk0x10}")
            logger.info(f"  unk0x14={new_gaitem.unk0x14}")
            logger.info(f"  gem_gaitem_handle=0x{new_gaitem.gem_gaitem_handle:08X}")
            logger.info(f"  unk0x1c={new_gaitem.unk0x1c}")
            logger.info(f"New gaitem final size: {new_gaitem.get_size()} bytes")

            # Apply upgrade if requested
            if upgrade > 0:
                logger.info(f"\n--- APPLYING UPGRADE: +{upgrade} ---")
                new_gaitem.unk0x10 = upgrade
                if self.inv_reinforcement_var.get() == "somber":
                    new_gaitem.unk0x14 = 0x30  # Somber reinforcement
                else:
                    new_gaitem.unk0x14 = 0x20  # Standard reinforcement
                logger.info(f"  unk0x10={new_gaitem.unk0x10}")
                logger.info(f"  unk0x14=0x{new_gaitem.unk0x14:02X}")

            # Calculate size delta
            old_size = slot.gaitem_map[empty_gaitem_idx].get_size()
            new_size = new_gaitem.get_size()
            size_delta = new_size - old_size
            logger.info("\n--- SIZE CHANGE ---")
            logger.info(f"Old slot size: {old_size} bytes")
            logger.info(f"New slot size: {new_size} bytes")
            logger.info(f"Size delta: +{size_delta} bytes (gaitem map will expand)")

            # Update gaitem map
            logger.info("\n--- STEP 6: UPDATE GAITEM MAP ---")
            logger.info(f"Replacing slot {empty_gaitem_idx}")

            logger.info(
                f"  Fields to write: unk0x10={new_gaitem.unk0x10} (type={type(new_gaitem.unk0x10).__name__})"
            )
            logger.info(
                f"  Fields to write: unk0x14={new_gaitem.unk0x14} (type={type(new_gaitem.unk0x14).__name__})"
            )
            logger.info(
                f"  Fields to write: gem_handle={new_gaitem.gem_gaitem_handle:08X} (type={type(new_gaitem.gem_gaitem_handle).__name__})"
            )
            logger.info(
                f"  Fields to write: unk0x1c={new_gaitem.unk0x1c} (type={type(new_gaitem.unk0x1c).__name__})"
            )

            slot.gaitem_map[empty_gaitem_idx] = new_gaitem
            logger.info(
                f"  AFTER - handle: 0x{slot.gaitem_map[empty_gaitem_idx].gaitem_handle:08X}"
            )
            logger.info(
                f"  AFTER - item_id: 0x{slot.gaitem_map[empty_gaitem_idx].item_id:08X}"
            )
            logger.info(
                f"  AFTER - size: {slot.gaitem_map[empty_gaitem_idx].get_size()} bytes"
            )

            # Log new gaitem map stats
            new_total_size = sum(g.get_size() for g in slot.gaitem_map)
            logger.info(
                f"New total gaitem_map size: {new_total_size} bytes (delta: +{size_delta})"
            )

            # Create inventory item
            logger.info("\n--- STEP 8: CREATE INVENTORY ITEM ---")

            # Find max acquisition index from existing items
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
            logger.info(f"Max existing acquisition index: {max_acquisition}")
            logger.info(f"Using acquisition index: {next_acquisition}")

            new_inv_item = InventoryItem()
            new_inv_item.gaitem_handle = gaitem_handle
            new_inv_item.quantity = quantity
            new_inv_item.acquisition_index = next_acquisition
            logger.info("New inventory item:")
            logger.info(f"  handle: 0x{new_inv_item.gaitem_handle:08X}")
            logger.info(f"  quantity: {new_inv_item.quantity}")
            logger.info(f"  acquisition_index: {new_inv_item.acquisition_index}")

            # Update inventory
            logger.info("\n--- STEP 9: UPDATE INVENTORY ---")
            old_count = inventory.common_item_count
            old_acq_counter = inventory.acquisition_index_counter
            old_equip_counter = inventory.equip_index_counter

            inventory.common_items[empty_inv_idx] = new_inv_item
            inventory.common_item_count += 1
            inventory.acquisition_index_counter = (
                next_acquisition + 1
            )  # Update counter to next value

            logger.info(
                f"Inventory count: {old_count} -> {inventory.common_item_count}"
            )
            logger.info(
                f"Acquisition counter: {old_acq_counter} -> {inventory.acquisition_index_counter}"
            )
            logger.info(f"Equip index counter: {old_equip_counter} (unchanged)")
            logger.info(
                f"  AFTER - handle: 0x{inventory.common_items[empty_inv_idx].gaitem_handle:08X}"
            )
            logger.info(
                f"  AFTER - quantity: {inventory.common_items[empty_inv_idx].quantity}"
            )

            # Rebuild slot (handles variable sizes correctly)
            logger.info("\n--- STEP 10: REBUILD SLOT ---")
            logger.info(
                "Calling rebuild_slot() to serialize with expanded gaitem map..."
            )

            try:
                slot_bytes = rebuild_slot(slot)
                logger.info(
                    f"Rebuild successful! New slot size: {len(slot_bytes)} bytes"
                )
                logger.info("Expected size: 2,621,440 bytes (0x280000)")

                if len(slot_bytes) != 0x280000:
                    logger.warning(
                        f"SIZE MISMATCH! Got {len(slot_bytes)}, expected 2,621,440"
                    )
                else:
                    logger.info("✓ Slot size is correct")
            except Exception as e:
                logger.error(f"REBUILD FAILED: {e}")
                raise

            # Write rebuilt slot to _raw_data at the correct offset
            CHECKSUM_SIZE = 0x10
            slot_offset = save_file._slot_offsets[slot_idx]
            abs_offset = slot_offset + CHECKSUM_SIZE

            logger.info(
                f"Writing {len(slot_bytes)} bytes to _raw_data at offset {abs_offset:08X}"
            )
            logger.info(
                f"_raw_data type: {type(save_file._raw_data).__name__}, size: {len(save_file._raw_data)}"
            )
            logger.info(
                f"Slot offset: {slot_offset:08X}, checksum size: {CHECKSUM_SIZE:02X}"
            )
            logger.info(
                f"Write range: {abs_offset:08X} to {abs_offset + len(slot_bytes):08X}"
            )

            # Verify we're not writing beyond the file bounds
            if abs_offset + len(slot_bytes) > len(save_file._raw_data):
                logger.error(
                    f"ERROR: Write would exceed file bounds! File size: {len(save_file._raw_data)}, Write end: {abs_offset + len(slot_bytes)}"
                )
                raise ValueError("Write would exceed file bounds")

            save_file._raw_data[abs_offset : abs_offset + len(slot_bytes)] = slot_bytes
            log.debug("add_item: slot data written to _raw_data")

            # Recalculate checksums and save
            logger.info("\n--- STEP 11: SAVE & VERIFY ---")
            save_file.recalculate_checksums()
            log.debug("add_item: checksums recalculated")

            save_path = self.get_save_path()
            if save_path:
                logger.info("Writing slot data...")
                save_file.to_file(Path(save_path))
                log.debug(f"add_item: save file written to {save_path}")

                # Ensure file is flushed to disk
                import time

                time.sleep(0.1)

            logger.info("\n" + "=" * 80)
            logger.info("POST-WRITE VERIFICATION")
            logger.info("=" * 80)

            # Re-read the save file to verify the item persisted
            try:
                logger.info(f"Re-reading save file: {save_path}")
                verification_save = Save.from_file(str(save_path))
                verification_slot = verification_save.get_slot(slot_idx)

                logger.info(
                    f"Verification: Slot loaded, gaitem_map has {len(verification_slot.gaitem_map)} entries"
                )

                # Check if handle exists in gaitem_map
                found_in_gaitem = False
                for idx, gaitem in enumerate(verification_slot.gaitem_map):
                    if gaitem.gaitem_handle == gaitem_handle:
                        found_in_gaitem = True
                        logger.info(
                            f"✓ Found handle 0x{gaitem_handle:08X} in gaitem_map[{idx}]"
                        )
                        logger.info(
                            f"  item_id=0x{gaitem.item_id:08X}, size={gaitem.get_size()} bytes"
                        )
                        break

                if not found_in_gaitem:
                    logger.error(
                        f"✗ Handle 0x{gaitem_handle:08X} NOT FOUND in gaitem_map after write!"
                    )

                # Check if handle exists in inventory
                found_in_inventory = False
                if location == "held":
                    for idx, inv_item in enumerate(
                        verification_slot.inventory_held.common_items
                    ):
                        if inv_item.gaitem_handle == gaitem_handle:
                            found_in_inventory = True
                            logger.info(
                                f"✓ Found handle 0x{gaitem_handle:08X} in inventory_held.common_items[{idx}]"
                            )
                            logger.info(f"  quantity={inv_item.quantity}")
                            break
                else:  # storage
                    for idx, inv_item in enumerate(
                        verification_slot.inventory_storage_box.common_items
                    ):
                        if inv_item.gaitem_handle == gaitem_handle:
                            found_in_inventory = True
                            logger.info(
                                f"✓ Found handle 0x{gaitem_handle:08X} in inventory_storage_box.common_items[{idx}]"
                            )
                            logger.info(f"  quantity={inv_item.quantity}")
                            break

                if not found_in_inventory:
                    logger.error(
                        f"✗ Handle 0x{gaitem_handle:08X} NOT FOUND in inventory after write!"
                    )

                # Scan and log all inventory items to verify
                logger.info("\n--- FULL INVENTORY SCAN ---")
                logger.info(
                    f"Total common items: {verification_slot.inventory_held.common_item_count}"
                )
                logger.info(
                    f"Scanning all {len(verification_slot.inventory_held.common_items)} inventory slots:"
                )

                # Log first few slots for debugging
                logger.info("First 5 inventory slots:")
                for idx in range(
                    min(5, len(verification_slot.inventory_held.common_items))
                ):
                    inv_item = verification_slot.inventory_held.common_items[idx]
                    logger.info(
                        f"  [{idx}] handle=0x{inv_item.gaitem_handle:08X}, qty={inv_item.quantity}, acq={inv_item.acquisition_index}"
                    )

                found_items = []
                for idx, inv_item in enumerate(
                    verification_slot.inventory_held.common_items
                ):
                    if (
                        inv_item.gaitem_handle != 0
                        and inv_item.gaitem_handle != 0xFFFFFFFF
                    ):
                        # Find the item_id from gaitem_map
                        item_id = None
                        for gaitem in verification_slot.gaitem_map:
                            if gaitem.gaitem_handle == inv_item.gaitem_handle:
                                item_id = gaitem.item_id
                                break

                        found_items.append(
                            {
                                "idx": idx,
                                "handle": inv_item.gaitem_handle,
                                "item_id": item_id,
                                "quantity": inv_item.quantity,
                                "acquisition": inv_item.acquisition_index,
                            }
                        )

                # Log items sorted by acquisition index
                found_items.sort(key=lambda x: x["acquisition"])
                logger.info(
                    f"Found {len(found_items)} items in inventory (sorted by acquisition):"
                )
                for item in found_items[
                    -10:
                ]:  # Show last 10 items (most recently acquired)
                    marker = " ← NEW!" if item["handle"] == gaitem_handle else ""
                    item_id_str = (
                        f"0x{item['item_id']:08X}"
                        if item["item_id"] is not None
                        else "NOT_FOUND"
                    )
                    logger.info(
                        f"  [{item['idx']:4d}] handle=0x{item['handle']:08X}, "
                        f"item_id={item_id_str}, qty={item['quantity']}, acq={item['acquisition']}{marker}"
                    )

                # Check equipped items arrays
                logger.info("\nChecking equipped items arrays:")

                # Get equipped handles from the EquipmentSlots structure
                equipped_handles = [
                    verification_slot.equipped_items_gaitem_handle.left_hand_armament1,
                    verification_slot.equipped_items_gaitem_handle.right_hand_armament1,
                    verification_slot.equipped_items_gaitem_handle.left_hand_armament2,
                    verification_slot.equipped_items_gaitem_handle.right_hand_armament2,
                    verification_slot.equipped_items_gaitem_handle.left_hand_armament3,
                    verification_slot.equipped_items_gaitem_handle.right_hand_armament3,
                ]

                logger.info(
                    f"  Equipped weapon handles: {len([h for h in equipped_handles if h != 0 and h != 0xFFFFFFFF])} weapons equipped"
                )

                # Show equipped handles
                logger.info("  Equipped weapon handles:")
                for i, handle in enumerate(equipped_handles):
                    if handle != 0 and handle != 0xFFFFFFFF:
                        logger.info(f"    slot[{i}]: 0x{handle:08X}")

                # Check if handle appears in equipped arrays (it shouldn't for unequipped items)
                found_in_equipped = False
                if gaitem_handle in equipped_handles:
                    found_in_equipped = True
                    logger.warning(
                        f"! Handle 0x{gaitem_handle:08X} found in equipped weapons - unexpected for unequipped item!"
                    )

                if not found_in_equipped:
                    logger.info(
                        f"✓ Handle 0x{gaitem_handle:08X} correctly NOT in equipped arrays (item is unequipped)"
                    )

            except Exception as verify_error:
                logger.error(f"Verification failed: {verify_error}")
                import traceback

                logger.error(traceback.format_exc())

            logger.info("\n" + "=" * 80)
            logger.info("ITEM ADDITION COMPLETE")
            logger.info("=" * 80)

            item_id_display = f"0x{item_id:08X}" if item_id is not None else "Unknown"
            CTkMessageBox.showinfo(
                "Success",
                f"Added {category_name}: {item_id_display} (x{quantity}) +{upgrade} to {location}!\n"
                f"Handle: 0x{gaitem_handle:08X}\n"
                f"Gaitem expanded from {old_size} to {new_size} bytes\n\n"
                f"Please reload the save to see changes.",
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
