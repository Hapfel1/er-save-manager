"""
Inventory Editor Module (customtkinter)
Full implementation with gaitem system for adding/removing items using item browser
"""

import re
import tkinter as tk
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
        self.selected_item = None  # Currently selected item from browser
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

        # Add item frame - DISABLED FOR NOW
        # add_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        # add_frame.pack(fill=ctk.X, pady=5, padx=10)
        # ctk.CTkLabel(
        #     add_frame,
        #     text="Add/Spawn Item",
        #     font=("Segoe UI", 12, "bold"),
        # ).grid(row=0, column=0, columnspan=4, sticky=ctk.W, padx=5, pady=(5, 0))

        # Skip add item UI - will be re-enabled after serialization fixes

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
            state=ctk.DISABLED,
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
            state=ctk.DISABLED,
        ).pack(side=ctk.LEFT, padx=5)

        # Disabled notice
        notice_label = ctk.CTkLabel(
            self.frame,
            text="⚠️ Item editing (add/remove) is temporarily disabled for stability.",
            font=("Segoe UI", 10, "bold"),
            text_color="#ff6b6b",
        )
        notice_label.pack(pady=5, padx=10)

        # Info section
        info_label = ctk.CTkLabel(
            self.frame,
            text=(
                "You can view your inventory here. Adding and removing items has been temporarily disabled.\n"
                "Refresh List will reload your current inventory from the save file."
            ),
            font=("Segoe UI", 9),
            text_color=("gray30", "gray80"),
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

            # CRITICAL FIX: Determine the SIZE of the item BEFORE looking for an empty slot!
            # Different items have different serialized sizes:
            # - Weapons (0x00000000): 21 bytes
            # - Armor (0x10000000): 16 bytes
            # - Consumables/Talismans: 8 bytes

            item_category = item_id & 0xF0000000
            log.debug(f"add_item: item_category={hex(item_category)}")

            # Calculate the SIZE this new item will have
            if item_category == 0x00000000:  # Weapon - 21 bytes
                required_size = 21
            elif item_category == 0x10000000:  # Armor - 16 bytes
                required_size = 16
            else:  # Consumables (0x40000000) and Talismans (0x20000000) - 8 bytes
                required_size = 8

            log.debug(f"add_item: item requires {required_size} bytes")

            # Find first EMPTY gaitem slot with the REQUIRED SIZE
            from er_save_manager.parser.er_types import Gaitem

            empty_gaitem_idx = -1
            for i, gaitem in enumerate(slot.gaitem_map):
                if gaitem.item_id in (0, 0xFFFFFFFF):
                    gaitem_size = gaitem.get_size()
                    if gaitem_size == required_size:
                        empty_gaitem_idx = i
                        break

            if empty_gaitem_idx == -1:
                # NO matching size slot found - this is critical!
                # Show the user what slots are available
                size_counts = {}
                for gaitem in slot.gaitem_map:
                    if gaitem.item_id in (0, 0xFFFFFFFF):
                        size = gaitem.get_size()
                        size_counts[size] = size_counts.get(size, 0) + 1

                size_names = {8: "Consumable/Talisman", 16: "Armor", 21: "Weapon"}
                required_name = size_names.get(required_size, f"{required_size}-byte")

                available_str = ", ".join(
                    f"{size_names.get(s, f'{s}-byte')}: {count}"
                    for s, count in sorted(size_counts.items())
                )

                log.error(
                    f"add_item: Cannot add {required_name} - no empty {required_size}-byte slots. "
                    f"Available: {available_str}"
                )
                CTkMessageBox.showerror(
                    "No Space for Item",
                    f"Cannot add {required_name} item.\n\n"
                    f"Empty slots needed: {required_name} ({required_size} bytes)\n"
                    f"Available empty slots:\n"
                    f"  {available_str}\n\n"
                    f"Try removing items of the same type to free up space.",
                    parent=self.parent,
                )
                return

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

            empty_inv_idx = -1
            for i, inv_item in enumerate(inventory.common_items):
                if inv_item.gaitem_handle == 0 or inv_item.quantity == 0:
                    empty_inv_idx = i
                    break

            if empty_inv_idx == -1:
                log.warning("add_item: no empty inventory slots!")
                CTkMessageBox.showwarning(
                    "Inventory Full", "No empty slots in inventory!", parent=self.parent
                )
                return

            log.debug(f"add_item: empty_inv_idx={empty_inv_idx}")

            # Strip category prefix to get base item ID
            # For consumables/goods, the full_id has 0x40000000 prefix, but we need just the base ID
            base_item_id = item_id & 0x0FFFFFFF

            # Generate gaitem_handle based on item type (matching Rust editor logic)
            # Consumables/Goods: gaitem_handle = base_id | 0xB0000000
            # Weapons: gaitem_handle would be generated (0x80000000 | counter), but we use simple formula for now
            # Armor: gaitem_handle would be generated (0x90000000 | counter)
            # Talismans: gaitem_handle = base_id | 0xA0000000
            if item_category == 0x40000000:  # Consumable/Good
                gaitem_handle = base_item_id | 0xB0000000
                actual_item_id = item_id  # Consumables KEEP the 0x40000000 prefix for size calculation
            elif item_category == 0x00000000:  # Weapon
                gaitem_handle = 0x80000000 | (empty_gaitem_idx & 0xFFFF)
                actual_item_id = base_item_id
            elif item_category == 0x10000000:  # Armor
                gaitem_handle = 0x90000000 | (empty_gaitem_idx & 0xFFFF)
                actual_item_id = item_id  # Armor keeps the 0x10000000 prefix
            elif item_category == 0x20000000:  # Talisman
                gaitem_handle = base_item_id | 0xA0000000
                actual_item_id = (
                    item_id  # Talismans KEEP the 0x20000000 prefix for size calculation
                )
            else:
                # Fallback for unknown types
                gaitem_handle = 0xB0000000 | (empty_gaitem_idx & 0xFFFF)
                actual_item_id = item_id

            log.debug(
                f"add_item: item_category={hex(item_category)}, base_item_id={hex(base_item_id)}, gaitem_handle={hex(gaitem_handle)}, actual_item_id={hex(actual_item_id)}"
            )

            # Create new gaitem in gaitem_map
            new_gaitem = Gaitem()
            new_gaitem.item_id = actual_item_id
            log.debug(f"add_item: set new_gaitem.item_id={hex(new_gaitem.item_id)}")
            new_gaitem.gaitem_handle = gaitem_handle

            # Set extended fields ONLY for items that need them (weapons/armor)
            # Check based on the ORIGINAL item_id's category prefix (0xF0000000)
            # NOT the base_item_id which always has upper nibble = 0x0
            #   0x00000000 (weapons) = 21 bytes, needs extended fields
            #   0x10000000 (armor) = 16 bytes, needs extended fields
            #   0x40000000 (consumables) = 8 bytes, NO extended fields
            #   0x20000000 (talismans) = 8 bytes, NO extended fields

            if item_category == 0x00000000:  # Weapons - set extended fields
                # CRITICAL: Default unk0x10 and unk0x14 to -1 for weapons
                new_gaitem.unk0x10 = -1
                new_gaitem.unk0x14 = -1

                # Only override with upgrade/reinforcement if user specified it
                if upgrade > 0:
                    new_gaitem.unk0x10 = upgrade
                    if self.inv_reinforcement_var.get() == "somber":
                        new_gaitem.unk0x14 = 0x30
                    else:
                        new_gaitem.unk0x14 = 0x20

                # Default gem/AoW handle to 0xFFFFFFFF for weapons
                new_gaitem.gem_gaitem_handle = 0xFFFFFFFF
                new_gaitem.unk0x1c = 0

            elif item_category == 0x10000000:  # Armor - set extended fields (16 bytes)
                new_gaitem.unk0x10 = -1
                new_gaitem.unk0x14 = -1

            # For consumables (0x40000000) and talismans (0x20000000), leave extended fields as None (8-byte gaitem)

            log.debug(
                f"add_item: before get_size(), new_gaitem.item_id={hex(new_gaitem.item_id)}"
            )
            size_before = new_gaitem.get_size()
            log.debug(f"add_item: after get_size(), size={size_before}")
            log.debug(
                f"add_item: created gaitem, item_id={hex(item_id)}, size={size_before}, handle={hex(gaitem_handle)}, unk0x10={new_gaitem.unk0x10}, unk0x14={new_gaitem.unk0x14}, gem_handle={hex(new_gaitem.gem_gaitem_handle) if new_gaitem.gem_gaitem_handle else 'None'}"
            )

            slot.gaitem_map[empty_gaitem_idx] = new_gaitem
            slot.gaitem_map_entry_sizes = [g.get_size() for g in slot.gaitem_map]

            log.debug(
                f"add_item: gaitem_map_entry_sizes calculated, count={len(slot.gaitem_map_entry_sizes)}"
            )

            # Create inventory item that references the gaitem
            new_inv_item = InventoryItem()
            new_inv_item.gaitem_handle = gaitem_handle
            new_inv_item.quantity = quantity
            new_inv_item.acquisition_index = inventory.acquisition_index_counter
            inventory.acquisition_index_counter += 1

            inventory.common_items[empty_inv_idx] = new_inv_item
            inventory.common_item_count += 1

            log.debug("add_item: created inventory item, now serializing slot...")

            # Serialize and write the full slot to keep offsets consistent
            slot_bytes = slot.to_bytes()
            log.debug(f"add_item: slot serialized, length={len(slot_bytes)}")

            save_file.write_slot_data(slot_idx, slot_bytes)
            log.debug("add_item: slot data written")

            # Recalculate checksums and save
            save_file.recalculate_checksums()
            log.debug("add_item: checksums recalculated")

            save_path = self.get_save_path()
            if save_path:
                save_file.to_file(Path(save_path))
                log.debug(f"add_item: save file written to {save_path}")

                # Ensure file is flushed to disk
                import time

                time.sleep(0.1)

            # DO NOT call refresh_inventory() - it reloads from disk and overwrites our changes!
            # Instead, just show success message

            CTkMessageBox.showinfo(
                "Success",
                f"Added item {item_id} (x{quantity}) +{upgrade} to {location}!\nPlease reload the save to see changes.",
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
            slot_bytes = slot.to_bytes()
            save_file.write_slot_data(slot_idx, slot_bytes)

            # Recalculate checksums to prevent corruption
            save_file.recalculate_checksums()

            # Save to disk
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
            slot.gaitem_map_entry_sizes = [g.get_size() for g in slot.gaitem_map]

            # Serialize and write the full slot to keep offsets consistent
            slot_bytes = slot.to_bytes()
            save_file.write_slot_data(slot_idx, slot_bytes)

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
