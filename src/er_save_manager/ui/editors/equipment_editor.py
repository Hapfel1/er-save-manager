"""
Equipment Editor Module
Handles equipment editing UI and logic
"""

import customtkinter as ctk

from er_save_manager.data.item_database import get_item_name
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel, trace_variable


class EquipmentEditor:
    """Equipment editor for character equipment slots"""

    def __init__(self, parent, get_save_file_callback, get_char_slot_callback):
        """
        Initialize equipment editor

        Args:
            parent: Parent tkinter widget
            get_save_file_callback: Function that returns current save file
            get_char_slot_callback: Function that returns current character slot index
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_char_slot = get_char_slot_callback

        self.equipment_vars = {}
        self.equipment_name_labels = {}

        self.frame = None

    def setup_ui(self):
        """Setup the equipment editor UI"""
        self.frame = ctk.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
        )
        self.frame.pack(fill="both", expand=True)
        bind_mousewheel(self.frame)

        # Disabled notice
        notice_label = ctk.CTkLabel(
            self.frame,
            text="⚠️ Equipment editing is temporarily disabled for stability.",
            font=("Segoe UI", 10, "bold"),
            text_color="#ff6b6b",
        )
        notice_label.pack(pady=10, padx=10)

        # Top row: Weapons and Armor
        top_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        top_row.pack(fill="x", pady=5)

        # Weapons frame (left)
        weapons_frame = ctk.CTkFrame(
            top_row,
            fg_color="transparent",
        )
        weapons_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        ctk.CTkLabel(
            weapons_frame,
            text="Weapons",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=5, pady=(5, 0))

        weapons_grid = ctk.CTkFrame(weapons_frame, fg_color="transparent")
        weapons_grid.pack(fill="both", expand=True, padx=5, pady=5)

        weapons = [
            ("Right Hand 1", "right_hand_armament1"),
            ("Right Hand 2", "right_hand_armament2"),
            ("Right Hand 3", "right_hand_armament3"),
            ("Left Hand 1", "left_hand_armament1"),
            ("Left Hand 2", "left_hand_armament2"),
            ("Left Hand 3", "left_hand_armament3"),
        ]

        for i, (label, key) in enumerate(weapons):
            ctk.CTkLabel(
                weapons_grid,
                text=f"{label}:",
            ).grid(row=i, column=0, sticky="w", padx=5, pady=3)
            var = ctk.IntVar(value=0)
            self.equipment_vars[key] = var
            entry = ctk.CTkComboBox(
                weapons_grid,
                variable=var,
                values=[],
                width=120,
                fg_color=("gray86", "gray25"),
                text_color=("black", "white"),
                button_color=("gray70", "gray30"),
                command=lambda _v=None, k=key: self.update_equipment_name(k),
                state=ctk.DISABLED,
            )
            entry.grid(row=i, column=1, padx=5, pady=3)

            # Item name label
            name_label = ctk.CTkLabel(
                weapons_grid,
                text="",
                text_color="#60a5fa",
                width=200,
                anchor="w",
            )
            name_label.grid(row=i, column=2, sticky="w", padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            trace_variable(var, "w", lambda *args, k=key: self.update_equipment_name(k))

        # Armor frame (right)
        armor_frame = ctk.CTkFrame(
            top_row,
            fg_color=("gray86", "gray25"),
        )
        armor_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

        ctk.CTkLabel(
            armor_frame,
            text="Armor",
            font=("Segoe UI", 12, "bold"),
            text_color=("black", "white"),
        ).pack(anchor="w", padx=5, pady=(5, 0))

        armor_grid = ctk.CTkFrame(armor_frame, fg_color="transparent")
        armor_grid.pack(fill="both", expand=True, padx=5, pady=5)

        armor = [
            ("Head", "head"),
            ("Chest", "chest"),
            ("Arms", "arms"),
            ("Legs", "legs"),
        ]

        for i, (label, key) in enumerate(armor):
            ctk.CTkLabel(
                armor_grid,
                text=f"{label}:",
                text_color=("black", "white"),
            ).grid(row=i, column=0, sticky="w", padx=5, pady=3)
            var = ctk.IntVar(value=0)
            self.equipment_vars[key] = var
            entry = ctk.CTkComboBox(
                armor_grid,
                variable=var,
                values=[],
                width=120,
                fg_color=("gray86", "gray25"),
                text_color=("black", "white"),
                button_color=("gray70", "gray30"),
                command=lambda _v=None, k=key: self.update_equipment_name(k),
                state=ctk.DISABLED,
            )
            entry.grid(row=i, column=1, padx=5, pady=3)

            # Item name label
            name_label = ctk.CTkLabel(
                armor_grid,
                text="",
                text_color="#60a5fa",
                width=200,
                anchor="w",
            )
            name_label.grid(row=i, column=2, sticky="w", padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            trace_variable(var, "w", lambda *args, k=key: self.update_equipment_name(k))

        # Middle row: Talismans and Arrows/Bolts
        middle_row = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        middle_row.pack(fill="x", pady=5)

        # Talismans frame (left)
        talisman_frame = ctk.CTkFrame(
            middle_row,
            fg_color=("gray86", "gray25"),
        )
        talisman_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        ctk.CTkLabel(
            talisman_frame,
            text="Talismans",
            font=("Segoe UI", 12, "bold"),
            text_color=("black", "white"),
        ).pack(anchor="w", padx=5, pady=(5, 0))

        talisman_grid = ctk.CTkFrame(talisman_frame, fg_color="transparent")
        talisman_grid.pack(fill="both", expand=True, padx=5, pady=5)

        talismans = [
            ("Talisman 1", "talisman1"),
            ("Talisman 2", "talisman2"),
            ("Talisman 3", "talisman3"),
            ("Talisman 4", "talisman4"),
        ]

        for i, (label, key) in enumerate(talismans):
            ctk.CTkLabel(
                talisman_grid,
                text=f"{label}:",
                text_color=("black", "white"),
            ).grid(row=i, column=0, sticky="w", padx=5, pady=3)
            var = ctk.IntVar(value=0)
            self.equipment_vars[key] = var
            entry = ctk.CTkComboBox(
                talisman_grid,
                variable=var,
                values=[],
                width=120,
                fg_color=("gray86", "gray25"),
                text_color=("black", "white"),
                button_color=("gray70", "gray30"),
                command=lambda _v=None, k=key: self.update_equipment_name(k),
            )
            entry.grid(row=i, column=1, padx=5, pady=3)

            # Item name label
            name_label = ctk.CTkLabel(
                talisman_grid,
                text="",
                text_color="#60a5fa",
                width=200,
                anchor="w",
            )
            name_label.grid(row=i, column=2, sticky="w", padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            trace_variable(var, "w", lambda *args, k=key: self.update_equipment_name(k))

        # Arrows/Bolts frame (right)
        ammo_frame = ctk.CTkFrame(
            middle_row,
            fg_color=("gray86", "gray25"),
        )
        ammo_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

        ctk.CTkLabel(
            ammo_frame,
            text="Arrows & Bolts",
            font=("Segoe UI", 12, "bold"),
            text_color=("black", "white"),
        ).pack(anchor="w", padx=5, pady=(5, 0))

        ammo_grid = ctk.CTkFrame(ammo_frame, fg_color="transparent")
        ammo_grid.pack(fill="both", expand=True, padx=5, pady=5)

        ammo = [
            ("Arrows 1", "arrows1"),
            ("Arrows 2", "arrows2"),
            ("Bolts 1", "bolts1"),
            ("Bolts 2", "bolts2"),
        ]

        for i, (label, key) in enumerate(ammo):
            ctk.CTkLabel(
                ammo_grid,
                text=f"{label}:",
                text_color=("black", "white"),
            ).grid(row=i, column=0, sticky="w", padx=5, pady=3)
            var = ctk.IntVar(value=0)
            self.equipment_vars[key] = var
            entry = ctk.CTkComboBox(
                ammo_grid,
                variable=var,
                values=[],
                width=120,
                fg_color=("gray86", "gray25"),
                text_color=("black", "white"),
                button_color=("gray70", "gray30"),
                command=lambda _v=None, k=key: self.update_equipment_name(k),
            )
            entry.grid(row=i, column=1, padx=5, pady=3)

            # Item name label
            name_label = ctk.CTkLabel(
                ammo_grid,
                text="",
                text_color="#60a5fa",
                width=200,
                anchor="w",
            )
            name_label.grid(row=i, column=2, sticky="w", padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            trace_variable(var, "w", lambda *args, k=key: self.update_equipment_name(k))

        # Bottom: Spells (12 slots in 2 columns)
        spells_frame = ctk.CTkFrame(
            self.frame,
            fg_color=("gray86", "gray25"),
        )
        spells_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            spells_frame,
            text="Spells (Memory Slots)",
            font=("Segoe UI", 12, "bold"),
            text_color=("black", "white"),
        ).pack(anchor="w", padx=5, pady=(5, 0))

        spells_grid = ctk.CTkFrame(spells_frame, fg_color="transparent")
        spells_grid.pack(fill="x", padx=5, pady=5)

        for i in range(12):
            row = i // 2
            col = (i % 2) * 3  # Changed to 3 to make room for name labels

            ctk.CTkLabel(
                spells_grid,
                text=f"Spell {i + 1}:",
                text_color=("black", "white"),
            ).grid(row=row, column=col, sticky="w", padx=5, pady=3)
            var = ctk.IntVar(value=0)
            key = f"spell{i + 1}"
            self.equipment_vars[key] = var
            entry = ctk.CTkComboBox(
                spells_grid,
                variable=var,
                values=[],
                width=120,
                fg_color=("gray86", "gray25"),
                text_color=("black", "white"),
                button_color=("gray70", "gray30"),
                command=lambda _v=None, k=key: self.update_equipment_name(k),
            )
            entry.grid(row=row, column=col + 1, padx=5, pady=3)

            # Item name label
            name_label = ctk.CTkLabel(
                spells_grid,
                text="",
                text_color="#60a5fa",
                width=160,
                anchor="w",
            )
            name_label.grid(row=row, column=col + 2, sticky="w", padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            trace_variable(var, "w", lambda *args, k=key: self.update_equipment_name(k))

        # Apply button
        button_frame = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        button_frame.pack(fill="x", pady=10)

        ctk.CTkButton(
            button_frame,
            text="Apply Equipment Changes",
            command=self.apply_changes,
            width=240,
            state=ctk.DISABLED,
        ).pack()

    def load_equipment(self):
        """Load equipment from current character slot"""
        save_file = self.get_save_file()
        if not save_file:
            return

        slot_idx = self.get_char_slot()
        if slot_idx < 0 or slot_idx >= len(save_file.characters):
            return

        slot = save_file.characters[slot_idx]
        if (
            not hasattr(slot, "equipped_items_item_id")
            or not slot.equipped_items_item_id
        ):
            return

        equip = slot.equipped_items_item_id

        # Load all equipment IDs
        self.equipment_vars["right_hand_armament1"].set(
            str(getattr(equip, "right_hand_armament1", 0))
        )
        self.equipment_vars["right_hand_armament2"].set(
            str(getattr(equip, "right_hand_armament2", 0))
        )
        self.equipment_vars["right_hand_armament3"].set(
            str(getattr(equip, "right_hand_armament3", 0))
        )
        self.equipment_vars["left_hand_armament1"].set(
            str(getattr(equip, "left_hand_armament1", 0))
        )
        self.equipment_vars["left_hand_armament2"].set(
            str(getattr(equip, "left_hand_armament2", 0))
        )
        self.equipment_vars["left_hand_armament3"].set(
            str(getattr(equip, "left_hand_armament3", 0))
        )

        self.equipment_vars["head"].set(str(getattr(equip, "head", 0)))
        self.equipment_vars["chest"].set(str(getattr(equip, "chest", 0)))
        self.equipment_vars["arms"].set(str(getattr(equip, "arms", 0)))
        self.equipment_vars["legs"].set(str(getattr(equip, "legs", 0)))

        self.equipment_vars["talisman1"].set(str(getattr(equip, "talisman1", 0)))
        self.equipment_vars["talisman2"].set(str(getattr(equip, "talisman2", 0)))
        self.equipment_vars["talisman3"].set(str(getattr(equip, "talisman3", 0)))
        self.equipment_vars["talisman4"].set(str(getattr(equip, "talisman4", 0)))

        self.equipment_vars["arrows1"].set(str(getattr(equip, "arrows1", 0)))
        self.equipment_vars["arrows2"].set(str(getattr(equip, "arrows2", 0)))
        self.equipment_vars["bolts1"].set(str(getattr(equip, "bolts1", 0)))
        self.equipment_vars["bolts2"].set(str(getattr(equip, "bolts2", 0)))

        # Load spells if they exist
        for i in range(1, 13):
            key = f"spell{i}"
            if hasattr(equip, key):
                self.equipment_vars[key].set(str(getattr(equip, key, 0)))

        # Update all name labels
        for key in self.equipment_vars.keys():
            if key in self.equipment_name_labels:
                self.update_equipment_name(key)

    def apply_changes(self):
        """Apply equipment changes to save file"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first!", parent=self.parent
            )
            return

        slot_idx = self.get_char_slot()

        if not CTkMessageBox.askyesno(
            "Confirm",
            f"Apply equipment changes to Slot {slot_idx + 1}?\n\nA backup will be created.",
            parent=self.parent,
        ):
            return

        try:
            # Ensure raw_data is mutable
            if isinstance(save_file._raw_data, bytes):
                save_file._raw_data = bytearray(save_file._raw_data)

            # Create backup
            from pathlib import Path

            from er_save_manager.backup.manager import BackupManager

            save_path = getattr(save_file, "_save_path", None)
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_edit_equipment_slot_{slot_idx + 1}",
                    operation=f"edit_equipment_slot_{slot_idx + 1}",
                    save=save_file,
                )

            # Modify equipment
            slot = save_file.characters[slot_idx]
            if hasattr(slot, "equipped_items_item_id") and slot.equipped_items_item_id:
                equip = slot.equipped_items_item_id

                # Update all equipment
                equip.right_hand_armament1 = self._get_equipment_value(
                    "right_hand_armament1"
                )
                equip.right_hand_armament2 = self._get_equipment_value(
                    "right_hand_armament2"
                )
                equip.right_hand_armament3 = self._get_equipment_value(
                    "right_hand_armament3"
                )
                equip.left_hand_armament1 = self._get_equipment_value(
                    "left_hand_armament1"
                )
                equip.left_hand_armament2 = self._get_equipment_value(
                    "left_hand_armament2"
                )
                equip.left_hand_armament3 = self._get_equipment_value(
                    "left_hand_armament3"
                )

                equip.head = self._get_equipment_value("head")
                equip.chest = self._get_equipment_value("chest")
                equip.arms = self._get_equipment_value("arms")
                equip.legs = self._get_equipment_value("legs")

                equip.talisman1 = self._get_equipment_value("talisman1")
                equip.talisman2 = self._get_equipment_value("talisman2")
                equip.talisman3 = self._get_equipment_value("talisman3")
                equip.talisman4 = self._get_equipment_value("talisman4")

                equip.arrows1 = self._get_equipment_value("arrows1")
                equip.arrows2 = self._get_equipment_value("arrows2")
                equip.bolts1 = self._get_equipment_value("bolts1")
                equip.bolts2 = self._get_equipment_value("bolts2")

                # Update spells
                for i in range(1, 13):
                    key = f"spell{i}"
                    if hasattr(equip, key):
                        setattr(equip, key, self._get_equipment_value(key))

                CTkMessageBox.showinfo(
                    "Success", "Equipment updated successfully!", parent=self.parent
                )
            else:
                CTkMessageBox.showerror(
                    "Error", "Character has no equipment data", parent=self.parent
                )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to apply equipment changes:\n{e}", parent=self.parent
            )

    def update_equipment_name(self, equipment_key):
        """Update equipment name label when ID changes"""
        if equipment_key not in self.equipment_name_labels:
            return

        try:
            item_id = self._get_equipment_value(equipment_key)
            if item_id == 0 or item_id == -1:
                self.equipment_name_labels[equipment_key].configure(text="")
                return

            # Get name from item database
            item_name = get_item_name(item_id)

            # Truncate if too long
            if len(item_name) > 28:
                item_name = item_name[:25] + "..."

            self.equipment_name_labels[equipment_key].configure(text=item_name)
        except Exception:
            # Fallback for invalid/unknown IDs or decode failures
            self.equipment_name_labels[equipment_key].configure(text="(Unknown)")

    def _get_equipment_value(self, key):
        """Safely parse equipment value from its widget variable"""
        try:
            value = self.equipment_vars.get(key)
            if value is None:
                return 0
            raw = value.get()
            return int(raw) if raw not in ("", None) else 0
        except Exception:
            return 0
