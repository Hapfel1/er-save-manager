"""
Inventory Editor Module
Full implementation with gaitem system for adding/removing items
"""

import re
import tkinter as tk
from io import BytesIO
from pathlib import Path
from tkinter import messagebox, ttk


class InventoryEditor:
    """Full inventory editor with gaitem system support"""
    
    def __init__(self, parent, get_save_file_callback, get_char_slot_callback, get_save_path_callback, ensure_mutable_callback):
        """
        Initialize inventory editor
        
        Args:
            parent: Parent tkinter widget
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
        # Create scrollable frame
        canvas = tk.Canvas(self.parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.parent, orient=tk.VERTICAL, command=canvas.yview)
        self.frame = ttk.Frame(canvas)
        
        self.frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mousewheel
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add item frame
        add_frame = ttk.LabelFrame(self.frame, text="Add/Spawn Item", padding=10)
        add_frame.pack(fill=tk.X, pady=5)
        
        # Category dropdown
        ttk.Label(add_frame, text="Category:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.inv_category_var = tk.StringVar(value="Weapon")
        category_combo = ttk.Combobox(
            add_frame,
            textvariable=self.inv_category_var,
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
            state="readonly",
            width=20,
        )
        category_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # Item ID
        ttk.Label(add_frame, text="Item ID:").grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.inv_item_id_var = tk.IntVar(value=0)
        ttk.Entry(add_frame, textvariable=self.inv_item_id_var, width=15).grid(
            row=0, column=3, padx=5, pady=5
        )
        
        # Quantity
        ttk.Label(add_frame, text="Quantity:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.inv_quantity_var = tk.IntVar(value=1)
        ttk.Entry(add_frame, textvariable=self.inv_quantity_var, width=10).grid(
            row=1, column=1, padx=5, pady=5
        )
        
        # Upgrade level
        ttk.Label(add_frame, text="Upgrade Level:").grid(
            row=1, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.inv_upgrade_var = tk.IntVar(value=0)
        ttk.Entry(add_frame, textvariable=self.inv_upgrade_var, width=10).grid(
            row=1, column=3, padx=5, pady=5
        )
        
        # Reinforcement type (regular/somber)
        ttk.Label(add_frame, text="Reinforcement:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.inv_reinforcement_var = tk.StringVar(value="regular")
        reinforcement_combo = ttk.Combobox(
            add_frame,
            textvariable=self.inv_reinforcement_var,
            values=["regular", "somber"],
            state="readonly",
            width=10,
        )
        reinforcement_combo.grid(row=2, column=1, padx=5, pady=5)
        
        # Storage location
        ttk.Label(add_frame, text="Location:").grid(
            row=2, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.inv_location_var = tk.StringVar(value="held")
        location_combo = ttk.Combobox(
            add_frame,
            textvariable=self.inv_location_var,
            values=["held", "storage"],
            state="readonly",
            width=10,
        )
        location_combo.grid(row=2, column=3, padx=5, pady=5)
        
        # Add button
        ttk.Button(
            add_frame,
            text="Add Item",
            command=self.add_item,
            width=15,
        ).grid(row=3, column=0, columnspan=4, pady=10)
        
        # Item list frame
        list_frame = ttk.LabelFrame(self.frame, text="Current Inventory", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Filter frame
        filter_frame = ttk.Frame(list_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(filter_frame, text="Filter by Category:").pack(side=tk.LEFT, padx=5)
        self.inv_filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.inv_filter_var,
            values=["All", "Held", "Storage", "Key Items"],
            state="readonly",
            width=15,
        )
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_inventory())
        
        # Inventory display
        inv_list_frame = ttk.Frame(list_frame)
        inv_list_frame.pack(fill=tk.BOTH, expand=True)
        
        inv_scrollbar = ttk.Scrollbar(inv_list_frame)
        inv_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.inventory_listbox = tk.Listbox(
            inv_list_frame,
            yscrollcommand=inv_scrollbar.set,
            font=("Consolas", 9),
            height=15,
        )
        self.inventory_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inv_scrollbar.config(command=self.inventory_listbox.yview)
        
        # Remove item frame
        remove_frame = ttk.Frame(self.frame)
        remove_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            remove_frame,
            text="Remove Selected Item",
            command=self.remove_item,
            width=20,
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            remove_frame,
            text="Refresh List",
            command=self.refresh_inventory,
            width=15,
        ).pack(side=tk.LEFT, padx=5)
        
        # Info section
        info_label = ttk.Label(
            self.frame,
            text="Item IDs can be found in ITEM_IDS_Elden_Ring.txt reference file.\n"
            "Upgrade level: 0-25 for regular, 0-10 for somber.\n"
            "Changes are saved immediately when adding/removing items.",
            font=("Segoe UI", 9),
            foreground="gray",
            justify=tk.LEFT,
        )
        info_label.pack(pady=10)
    
    def refresh_inventory(self):
        """Refresh the inventory display"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        slot_idx = self.get_char_slot()
        
        try:
            slot = save_file.characters[slot_idx]
            
            if not slot or slot.is_empty():
                messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
                return
            
            self.inventory_listbox.delete(0, tk.END)
            
            # Get filter value
            filter_val = self.inv_filter_var.get() if self.inv_filter_var else "All"
            
            # Build gaitem lookup map
            gaitem_map = {}
            if hasattr(slot, "gaitem_map"):
                for gaitem in slot.gaitem_map:
                    if gaitem.gaitem_handle != 0xFFFFFFFF:
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
                        # Resolve gaitem
                        gaitem = gaitem_map.get(inv_item.gaitem_handle)
                        if gaitem:
                            item_id = gaitem.item_id
                            # unk0x10 typically contains upgrade level
                            upgrade = gaitem.unk0x10 if gaitem.unk0x10 is not None else 0
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
                            upgrade = gaitem.unk0x10 if gaitem.unk0x10 is not None else 0
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
            messagebox.showerror("Error", f"Failed to refresh inventory:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def add_item(self):
        """Add item to inventory"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        slot_idx = self.get_char_slot()
        item_id = self.inv_item_id_var.get()
        quantity = self.inv_quantity_var.get()
        upgrade = self.inv_upgrade_var.get()
        location = self.inv_location_var.get()
        
        if item_id == 0:
            messagebox.showwarning("Invalid Item", "Please enter a valid item ID!")
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
                messagebox.showerror("Error", "Could not access inventory")
                return
            
            # Find first empty gaitem slot
            from er_save_manager.parser.er_types import Gaitem
            
            empty_gaitem_idx = -1
            for i, gaitem in enumerate(slot.gaitem_map):
                if gaitem.item_id == 0xFFFFFFFF or gaitem.item_id == 0:
                    empty_gaitem_idx = i
                    break
            
            if empty_gaitem_idx == -1:
                messagebox.showwarning("Gaitem Map Full", "No empty gaitem slots!")
                return
            
            # Find first empty inventory slot
            from er_save_manager.parser.equipment import InventoryItem
            
            empty_inv_idx = -1
            for i, inv_item in enumerate(inventory.common_items):
                if inv_item.gaitem_handle == 0 or inv_item.quantity == 0:
                    empty_inv_idx = i
                    break
            
            if empty_inv_idx == -1:
                messagebox.showwarning("Inventory Full", "No empty slots in inventory!")
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
            # Write gaitem_map
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
            save_file._raw_data[gaitem_abs_offset : gaitem_abs_offset + len(gaitem_data)] = gaitem_data
            
            # Write back inventory
            if hasattr(slot, inv_offset_attr):
                inv_bytes = BytesIO()
                inventory.write(inv_bytes)
                inv_data = inv_bytes.getvalue()
                
                inv_abs_offset = slot_offset + CHECKSUM_SIZE + getattr(slot, inv_offset_attr)
                
                save_file._raw_data[inv_abs_offset : inv_abs_offset + len(inv_data)] = inv_data
                
                # Recalculate checksums and save
                save_file.recalculate_checksums()
                save_path = self.get_save_path()
                if save_path:
                    save_file.to_file(Path(save_path))
                
                # Refresh
                self.refresh_inventory()
                
                messagebox.showinfo(
                    "Success",
                    f"Added item {item_id} (x{quantity}) +{upgrade} to {location}!",
                )
            else:
                messagebox.showerror("Error", "Offset not tracked for inventory")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add item:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def remove_item(self):
        """Remove selected item from inventory"""
        selection = self.inventory_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an item to remove!")
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
            save_file._raw_data[gaitem_abs_offset : gaitem_abs_offset + len(gaitem_data)] = gaitem_data
            
            # Write back inventory
            if hasattr(slot, offset_attr):
                inv_bytes = BytesIO()
                inventory.write(inv_bytes)
                inv_data = inv_bytes.getvalue()
                
                inv_abs_offset = slot_offset + CHECKSUM_SIZE + getattr(slot, offset_attr)
                self.ensure_mutable()
                
                save_file._raw_data[inv_abs_offset : inv_abs_offset + len(inv_data)] = inv_data
                
                save_file.recalculate_checksums()
                save_path = self.get_save_path()
                if save_path:
                    save_file.to_file(Path(save_path))
                
                self.refresh_inventory()
                
                messagebox.showinfo("Success", "Item removed from inventory!")
            else:
                messagebox.showerror("Error", "Offset not tracked for inventory")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove item:\n{str(e)}")
            import traceback
            traceback.print_exc()
