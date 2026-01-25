"""
Inventory Editor Module (customtkinter)
Full implementation with gaitem system for adding/removing items
"""

import re
import tkinter as tk
from io import BytesIO
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


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
        self.inv_category_var = None
        self.inv_item_id_var = None
        self.inv_quantity_var = None
        self.inv_upgrade_var = None
        self.inv_reinforcement_var = None
        self.inv_location_var = None
        self.inv_filter_var = None
        self.inventory_listbox = None

        self.frame = None

    def setup_ui(self):
        """Setup the inventory editor UI"""
        self.frame = ctk.CTkScrollableFrame(
            self.parent,
            fg_color=("gray86", "gray25"),
            scrollbar_button_color=("gray70", "gray30"),
            scrollbar_button_hover_color=("gray60", "gray40"),
        )
        self.frame.pack(fill=ctk.BOTH, expand=True)
        bind_mousewheel(self.frame)

        # Add item frame
        add_frame = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        add_frame.pack(fill=ctk.X, pady=5, padx=10)
        ctk.CTkLabel(
            add_frame,
            text="Add/Spawn Item",
            font=("Segoe UI", 12, "bold"),
            text_color=("black", "white"),
        ).grid(row=0, column=0, columnspan=4, sticky=ctk.W, padx=5, pady=(5, 0))

        # Category dropdown
        ctk.CTkLabel(add_frame, text="Category:", text_color=("black", "white")).grid(
            row=1, column=0, sticky=ctk.W, padx=5, pady=5
        )
        self.inv_category_var = ctk.StringVar(value="Weapon")
        category_combo = ctk.CTkComboBox(
            add_frame,
            variable=self.inv_category_var,
            values=[
                "Weapon",
                "Armor",
                "Accessory (Talisman)",
                "Goods (Consumable)",
                "Key Item",
                "Spell (Sorcery)",
                "Spell (Incantation)",
                "Ash of War",
                "Upgrade Material",
                "Crafting Material",
                "Info Item",
            ],
            width=180,
        )
        category_combo.grid(row=1, column=1, padx=5, pady=5)

        # Item ID
        ctk.CTkLabel(add_frame, text="Item ID:", text_color=("black", "white")).grid(
            row=1, column=2, sticky=ctk.W, padx=5, pady=5
        )
        self.inv_item_id_var = ctk.IntVar(value=0)
        ctk.CTkEntry(add_frame, textvariable=self.inv_item_id_var, width=100).grid(
            row=1, column=3, padx=5, pady=5
        )

        # Quantity
        ctk.CTkLabel(add_frame, text="Quantity:", text_color=("black", "white")).grid(
            row=2, column=0, sticky=ctk.W, padx=5, pady=5
        )
        self.inv_quantity_var = ctk.IntVar(value=1)
        ctk.CTkEntry(add_frame, textvariable=self.inv_quantity_var, width=80).grid(
            row=2, column=1, padx=5, pady=5
        )

        # Upgrade level
        ctk.CTkLabel(
            add_frame, text="Upgrade Level:", text_color=("black", "white")
        ).grid(row=2, column=2, sticky=ctk.W, padx=5, pady=5)
        self.inv_upgrade_var = ctk.IntVar(value=0)
        ctk.CTkEntry(add_frame, textvariable=self.inv_upgrade_var, width=80).grid(
            row=2, column=3, padx=5, pady=5
        )

        # Reinforcement type (regular/somber)
        ctk.CTkLabel(
            add_frame, text="Reinforcement:", text_color=("black", "white")
        ).grid(row=3, column=0, sticky=ctk.W, padx=5, pady=5)
        self.inv_reinforcement_var = ctk.StringVar(value="regular")
        reinforcement_combo = ctk.CTkComboBox(
            add_frame,
            variable=self.inv_reinforcement_var,
            values=["regular", "somber"],
            width=120,
        )
        reinforcement_combo.grid(row=3, column=1, padx=5, pady=5)

        # Storage location
        ctk.CTkLabel(add_frame, text="Location:", text_color=("black", "white")).grid(
            row=3, column=2, sticky=ctk.W, padx=5, pady=5
        )
        self.inv_location_var = ctk.StringVar(value="held")
        location_combo = ctk.CTkComboBox(
            add_frame,
            variable=self.inv_location_var,
            values=["held", "storage"],
            width=120,
        )
        location_combo.grid(row=3, column=3, padx=5, pady=5)

        # Add button
        ctk.CTkButton(
            add_frame,
            text="Add Item",
            command=self.add_item,
            width=140,
        ).grid(row=4, column=0, columnspan=4, pady=10)

        # Item list frame
        list_frame = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        list_frame.pack(fill=ctk.BOTH, expand=True, pady=5, padx=10)
        ctk.CTkLabel(
            list_frame,
            text="Current Inventory",
            font=("Segoe UI", 12, "bold"),
            text_color=("black", "white"),
        ).pack(anchor=ctk.W, padx=5, pady=(5, 0))

        # Filter frame
        filter_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        filter_frame.pack(fill=ctk.X, pady=(0, 5))

        ctk.CTkLabel(
            filter_frame, text="Filter by Category:", text_color=("black", "white")
        ).pack(side=ctk.LEFT, padx=5)
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

        self.inventory_listbox = tk.Listbox(
            inv_list_container,
            yscrollcommand=inv_scrollbar.set,
            font=("Consolas", 10),
            height=18,
            bg="#1f1f28",
            fg="#e5e5f5",
            selectbackground="#c9a0dc",
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

        # Info section
        info_label = ctk.CTkLabel(
            self.frame,
            text=(
                "Item IDs can be found in ITEM_IDS_Elden_Ring.txt reference file.\n"
                "Upgrade level: 0-25 for regular, 0-10 for somber.\n"
                "Changes are saved immediately when adding/removing items."
            ),
            font=("Segoe UI", 9),
            text_color=("gray30", "gray80"),
            justify=ctk.LEFT,
        )
        info_label.pack(pady=10, padx=10, anchor=ctk.W)

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

                # Common items
                for i, inv_item in enumerate(inv.common_items):
                    if inv_item.gaitem_handle != 0 and inv_item.quantity > 0:
                        gaitem = gaitem_map.get(inv_item.gaitem_handle)
                        if gaitem:
                            item_id = gaitem.item_id
                            upgrade = (
                                gaitem.unk0x10 if gaitem.unk0x10 is not None else 0
                            )
                            self.inventory_listbox.insert(
                                tk.END,
                                f"  [{i}] ID: {item_id} | Qty: {inv_item.quantity} | +{upgrade}",
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
                for i, inv_item in enumerate(inv.key_items):
                    if inv_item.gaitem_handle != 0 and inv_item.quantity > 0:
                        gaitem = gaitem_map.get(inv_item.gaitem_handle)
                        if gaitem:
                            item_id = gaitem.item_id
                            self.inventory_listbox.insert(
                                tk.END,
                                f"  [K{i}] ID: {item_id} | Qty: {inv_item.quantity}",
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

                # Common items
                for i, inv_item in enumerate(inv.common_items):
                    if inv_item.gaitem_handle != 0 and inv_item.quantity > 0:
                        gaitem = gaitem_map.get(inv_item.gaitem_handle)
                        if gaitem:
                            item_id = gaitem.item_id
                            upgrade = (
                                gaitem.unk0x10 if gaitem.unk0x10 is not None else 0
                            )
                            self.inventory_listbox.insert(
                                tk.END,
                                f"  [S{i}] ID: {item_id} | Qty: {inv_item.quantity} | +{upgrade}",
                            )
                        else:
                            self.inventory_listbox.insert(
                                tk.END,
                                f"  [S{i}] Handle: {inv_item.gaitem_handle:08X} | Qty: {inv_item.quantity}",
                            )

                # Key items in storage (only if All or Storage selected)
                if filter_val in ["All", "Storage"]:
                    for i, inv_item in enumerate(inv.key_items):
                        if inv_item.gaitem_handle != 0 and inv_item.quantity > 0:
                            gaitem = gaitem_map.get(inv_item.gaitem_handle)
                            if gaitem:
                                item_id = gaitem.item_id
                                self.inventory_listbox.insert(
                                    tk.END,
                                    f"  [SK{i}] ID: {item_id} | Qty: {inv_item.quantity}",
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
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        slot_idx = self.get_char_slot()
        item_id = self.inv_item_id_var.get()
        quantity = self.inv_quantity_var.get()
        upgrade = self.inv_upgrade_var.get()
        location = self.inv_location_var.get()

        if item_id == 0:
            CTkMessageBox.showwarning(
                "Invalid Item", "Please enter a valid item ID!", parent=self.parent
            )
            return

        try:
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

            # Select inventory based on location
            if location == "held":
                inventory = slot.inventory_held
                inv_offset_attr = "inventory_held_offset"
            else:
                inventory = slot.inventory_storage_box
                inv_offset_attr = "inventory_storage_box_offset"

            if not inventory:
                CTkMessageBox.showerror(
                    "Error", "Could not access inventory", parent=self.parent
                )
                return

            # Find first empty gaitem slot
            from er_save_manager.parser.er_types import Gaitem

            empty_gaitem_idx = -1
            for i, gaitem in enumerate(slot.gaitem_map):
                if gaitem.item_id == 0xFFFFFFFF or gaitem.item_id == 0:
                    empty_gaitem_idx = i
                    break

            if empty_gaitem_idx == -1:
                CTkMessageBox.showwarning(
                    "Gaitem Map Full", "No empty gaitem slots!", parent=self.parent
                )
                return

            # Find first empty inventory slot
            from er_save_manager.parser.equipment import InventoryItem

            empty_inv_idx = -1
            for i, inv_item in enumerate(inventory.common_items):
                if inv_item.gaitem_handle == 0 or inv_item.quantity == 0:
                    empty_inv_idx = i
                    break

            if empty_inv_idx == -1:
                CTkMessageBox.showwarning(
                    "Inventory Full", "No empty slots in inventory!", parent=self.parent
                )
                return

            # Create new gaitem in gaitem_map
            gaitem_handle = 0x40000000 + empty_gaitem_idx
            new_gaitem = Gaitem()
            new_gaitem.item_id = item_id
            new_gaitem.gaitem_handle = gaitem_handle
            # unk0x10 stores upgrade level, unk0x14 stores reinforcement type
            new_gaitem.unk0x10 = upgrade

            # Set reinforcement type in unk0x14
            if self.inv_reinforcement_var.get() == "somber":
                new_gaitem.unk0x14 = 0x30
            else:
                new_gaitem.unk0x14 = 0x20

            slot.gaitem_map[empty_gaitem_idx] = new_gaitem

            # Create inventory item that references the gaitem
            new_inv_item = InventoryItem()
            new_inv_item.gaitem_handle = gaitem_handle
            new_inv_item.quantity = quantity
            new_inv_item.acquisition_index = inventory.acquisition_index_counter
            inventory.acquisition_index_counter += 1

            inventory.common_items[empty_inv_idx] = new_inv_item
            inventory.common_item_count += 1

            # Write back gaitem_map (after header at data_start)
            gaitem_bytes = BytesIO()
            for gaitem in slot.gaitem_map:
                gaitem.write(gaitem_bytes)
            gaitem_data = gaitem_bytes.getvalue()

            slot_offset = save_file._slot_offsets[slot_idx]
            CHECKSUM_SIZE = 0x10
            HEADER_SIZE = 32  # version + map_id + unk fields
            gaitem_abs_offset = slot_offset + CHECKSUM_SIZE + HEADER_SIZE

            # Ensure raw_data is mutable
            self.ensure_mutable()
            save_file._raw_data[
                gaitem_abs_offset : gaitem_abs_offset + len(gaitem_data)
            ] = gaitem_data

            # Write back inventory
            if hasattr(slot, inv_offset_attr):
                inv_bytes = BytesIO()
                inventory.write(inv_bytes)
                inv_data = inv_bytes.getvalue()

                inv_abs_offset = (
                    slot_offset + CHECKSUM_SIZE + getattr(slot, inv_offset_attr)
                )

                save_file._raw_data[inv_abs_offset : inv_abs_offset + len(inv_data)] = (
                    inv_data
                )

                # Recalculate checksums and save
                save_file.recalculate_checksums()
                save_path = self.get_save_path()
                if save_path:
                    save_file.to_file(Path(save_path))

                # Refresh
                self.refresh_inventory()

                CTkMessageBox.showinfo(
                    "Success",
                    f"Added item {item_id} (x{quantity}) +{upgrade} to {location}!",
                    parent=self.parent,
                )
            else:
                CTkMessageBox.showerror(
                    "Error", "Offset not tracked for inventory", parent=self.parent
                )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to add item:\n{str(e)}", parent=self.parent
            )
            import traceback

            traceback.print_exc()

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
            # Extract index from format like "[123]" or "[S123]"
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
                offset_attr = "inventory_storage_box_offset"
                is_key = location_prefix == "SK"
            else:
                inventory = slot.inventory_held
                offset_attr = "inventory_held_offset"
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
            from er_save_manager.parser.er_types import Gaitem

            for i, gaitem in enumerate(slot.gaitem_map):
                if gaitem.gaitem_handle == old_handle:
                    slot.gaitem_map[i] = Gaitem()
                    break

            # Write back gaitem_map
            gaitem_bytes = BytesIO()
            for gaitem in slot.gaitem_map:
                gaitem.write(gaitem_bytes)
            gaitem_data = gaitem_bytes.getvalue()

            slot_offset = save_file._slot_offsets[slot_idx]
            CHECKSUM_SIZE = 0x10
            HEADER_SIZE = 32
            gaitem_abs_offset = slot_offset + CHECKSUM_SIZE + HEADER_SIZE

            self.ensure_mutable()
            save_file._raw_data[
                gaitem_abs_offset : gaitem_abs_offset + len(gaitem_data)
            ] = gaitem_data

            # Write back inventory
            if hasattr(slot, offset_attr):
                inv_bytes = BytesIO()
                inventory.write(inv_bytes)
                inv_data = inv_bytes.getvalue()

                inv_abs_offset = (
                    slot_offset + CHECKSUM_SIZE + getattr(slot, offset_attr)
                )
                self.ensure_mutable()

                save_file._raw_data[inv_abs_offset : inv_abs_offset + len(inv_data)] = (
                    inv_data
                )

                save_file.recalculate_checksums()
                save_path = self.get_save_path()
                if save_path:
                    save_file.to_file(Path(save_path))

                self.refresh_inventory()

                CTkMessageBox.showinfo(
                    "Success", "Item removed from inventory!", parent=self.parent
                )
            else:
                CTkMessageBox.showerror(
                    "Error", "Offset not tracked for inventory", parent=self.parent
                )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to remove item:\n{str(e)}", parent=self.parent
            )
            import traceback

            traceback.print_exc()
