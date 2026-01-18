"""
Elden Ring Save Manager - Comprehensive GUI
Handles corruption fixes, preset management, character editing, and more.
"""

from __future__ import annotations

import os
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from er_save_manager.data.item_database import get_item_name
from er_save_manager.parser import Save


class SaveManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Elden Ring Save Manager")
        self.root.geometry("1115x850")
        self.root.minsize(800, 700)

        # Configure style
        style = ttk.Style()
        style.theme_use("clam")

        self.colors = {"pink": "#F5A9B8", "text": "#1f1f1f", "bg": "#f0f0f0"}
        style.configure("Accent.TButton", padding=6)
        style.map(
            "Accent.TButton",
            background=[("active", self.colors["pink"])],
            foreground=[("active", self.colors["text"])],
        )

        # State
        self.default_save_path = Path(os.environ.get("APPDATA", "")) / "EldenRing"
        self.save_file = None
        self.save_path = None
        self.selected_slot = None

        self.setup_ui()

    def bind_mousewheel(self, widget):
        """Bind mousewheel scrolling to a widget (canvas)"""

        def on_mousewheel(event):
            # Windows and MacOS use different event.delta values
            if event.num == 5 or event.delta < 0:
                widget.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                widget.yview_scroll(-1, "units")

        def on_enter(event):
            # Bind when mouse enters the canvas
            widget.bind_all("<MouseWheel>", on_mousewheel)
            widget.bind_all("<Button-4>", on_mousewheel)
            widget.bind_all("<Button-5>", on_mousewheel)

        def on_leave(event):
            # Unbind when mouse leaves the canvas
            widget.unbind_all("<MouseWheel>")
            widget.unbind_all("<Button-4>")
            widget.unbind_all("<Button-5>")

        # Bind enter/leave events
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def ensure_raw_data_mutable(self):
        """Ensure save file _raw_data is mutable (bytearray)"""
        if self.save_file and isinstance(self.save_file._raw_data, bytes):
            self.save_file._raw_data = bytearray(self.save_file._raw_data)

    def setup_ui(self):
        # Title
        title_frame = ttk.Frame(self.root, padding="15")
        title_frame.pack(fill=tk.X)

        ttk.Label(
            title_frame,
            text="Elden Ring Save Manager",
            font=("Segoe UI", 20, "bold"),
        ).pack()

        ttk.Label(
            title_frame,
            text="Complete save editor, backup manager, and corruption fixer",
            font=("Segoe UI", 10),
        ).pack()

        # File Selection
        file_frame = ttk.LabelFrame(
            self.root, text="Step 1: Select Save File", padding="15"
        )
        file_frame.pack(fill=tk.X, padx=15, pady=10)

        self.file_path_var = tk.StringVar()

        path_frame = ttk.Frame(file_frame)
        path_frame.pack(fill=tk.X)

        ttk.Entry(path_frame, textvariable=self.file_path_var, width=60).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )

        ttk.Button(
            path_frame,
            text="Browse",
            command=self.browse_file,
            width=10,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            path_frame,
            text="Auto-Find",
            command=self.auto_detect,
            width=10,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=2)

        # Load button
        buttons_frame = ttk.Frame(file_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            buttons_frame,
            text="Load Save File",
            command=self.load_save,
            width=20,
            style="Accent.TButton",
        ).pack(side=tk.LEFT)

        ttk.Button(
            buttons_frame,
            text="Backup Manager",
            command=self.show_backup_manager,
            width=20,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=10)

        # Main content - tabbed interface
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Tab 1: Save File Inspector (issue detection and viewing)
        self.tab_inspector = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_inspector, text="Save Inspector")
        self.setup_save_inspector_tab()

        # Tab 2: Character Management (transfer, copy, etc)
        self.tab_char_mgmt = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_char_mgmt, text="Character Management")
        self.setup_character_management_tab()

        # Tab 3: Character Editor (stats, equipment, inventory)
        self.tab_character = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_character, text="Character Editor")
        self.setup_character_tab()

        # Tab 4: Appearance
        self.tab_appearance = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_appearance, text="Appearance")
        self.setup_appearance_tab()

        # Tab 5: World State
        self.tab_world = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_world, text="World State")
        self.setup_world_tab()

        # Tab 6: SteamID Patcher
        self.tab_steamid = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_steamid, text="SteamID Patcher")
        self.setup_steamid_tab()

        # Tab 7: Event Flags
        self.tab_event_flags = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_event_flags, text="Event Flags")
        self.setup_event_flags_tab()

        # Tab 8: Gestures & Regions
        self.tab_gestures = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_gestures, text="Gestures & Regions")
        self.setup_gestures_tab()

        # Tab 9: Hex Editor
        self.tab_hex = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_hex, text="Hex Editor")
        self.setup_hex_tab()

        # Tab 10: Advanced Tools
        self.tab_advanced = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_advanced, text="Advanced Tools")
        self.setup_advanced_tab()

        # Tab 11: Backup Manager
        self.tab_backup = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_backup, text="Backup Manager")
        self.setup_backup_tab()

        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_var = tk.StringVar(value="Ready - Select a save file to begin")
        ttk.Label(
            status_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2),
        ).pack(fill=tk.X)

    def setup_backup_tab(self):
        """Backup Manager tab - central hub for all backups"""
        title_frame = ttk.Frame(self.tab_backup)
        title_frame.pack(fill=tk.X, pady=10)

        ttk.Label(
            title_frame,
            text="Backup Manager",
            font=("Segoe UI", 16, "bold"),
        ).pack()

        ttk.Label(
            title_frame,
            text="All save modifications automatically create timestamped backups with operation details",
            font=("Segoe UI", 9),
            foreground="gray",
        ).pack()

        # Main button
        ttk.Button(
            self.tab_backup,
            text="Open Backup Manager Window",
            command=self.show_backup_manager,
            width=35,
            style="Accent.TButton",
        ).pack(pady=20)

        # Quick stats frame
        stats_frame = ttk.LabelFrame(self.tab_backup, text="Quick Stats", padding=15)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.backup_stats_var = tk.StringVar(
            value="Load a save file to view backup statistics"
        )
        stats_label = ttk.Label(
            stats_frame,
            textvariable=self.backup_stats_var,
            font=("Consolas", 10),
            justify=tk.LEFT,
        )
        stats_label.pack(anchor=tk.W)

        # Info section
        info_frame = ttk.LabelFrame(
            self.tab_backup, text="Backup Information", padding=15
        )
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        info_text = """Automatic Backups:
• Fix Corruption - Before fixing any character issues
• Teleport - Before moving character location
• Edit Stats - Before changing character attributes
• Import Preset - Before applying appearance changes
• Patch SteamID - Before account transfers
• Recalculate Checksums - Before save validation

Backup Format:
• Timestamp: YYYY-MM-DD_HH-MM-SS
• Location: [save_name].sl2.backups/
• Metadata: Character info, operation type, changes made"""

        ttk.Label(
            info_frame,
            text=info_text,
            font=("Segoe UI", 9),
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

    def setup_save_inspector_tab(self):
        """Quick Fix tab - similar to save fixer"""
        # Character selection
        char_frame = ttk.LabelFrame(
            self.tab_inspector, text="Select Character", padding="10"
        )
        char_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Character listbox
        list_frame = ttk.Frame(char_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.char_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            height=10,
            selectmode=tk.SINGLE,
        )
        self.char_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.char_listbox.yview)

        self.char_listbox.bind("<ButtonRelease-1>", self.on_character_select)
        self.char_listbox.bind("<Double-Button-1>", self.show_character_details)

        # Actions frame
        action_frame = ttk.LabelFrame(self.tab_inspector, text="Actions", padding="10")
        action_frame.pack(fill=tk.X)

        ttk.Button(
            action_frame,
            text="View Details & Issues",
            command=self.show_character_details,
            width=25,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            action_frame,
            text="Quick Fix All Issues",
            command=self.quick_fix_all,
            width=25,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

    def setup_character_management_tab(self):
        """Character Management tab - transfer, copy, delete characters"""
        ttk.Label(
            self.tab_char_mgmt,
            text="Character Management",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=10)

        info_text = ttk.Label(
            self.tab_char_mgmt,
            text="Transfer characters between save files, copy slots, and manage your character roster",
            font=("Segoe UI", 10),
            foreground="gray",
        )
        info_text.pack(pady=5)

        # Operation selector
        selector_frame = ttk.LabelFrame(
            self.tab_char_mgmt, text="Select Operation", padding=15
        )
        selector_frame.pack(fill=tk.X, padx=20, pady=10)

        self.char_operation_var = tk.StringVar(value="copy")

        operations = [
            ("Copy Character", "copy"),
            ("Transfer to Another Save", "transfer"),
            ("Swap Slots", "swap"),
            ("Export Character", "export"),
            ("Import Character", "import"),
            ("Delete Character", "delete"),
        ]

        # Dropdown selector
        ttk.Label(selector_frame, text="Operation:").pack(side=tk.LEFT, padx=(0, 10))
        operation_combo = ttk.Combobox(
            selector_frame,
            textvariable=self.char_operation_var,
            values=[op[0] for op in operations],
            state="readonly",
            width=30,
        )
        operation_combo.pack(side=tk.LEFT, padx=5)

        # Map display names to internal values
        self.operation_map = {op[0]: op[1] for op in operations}
        self.operation_map_reverse = {op[1]: op[0] for op in operations}

        # Set initial display value
        operation_combo.set("Copy Character")

        # Bind change event
        operation_combo.bind(
            "<<ComboboxSelected>>", lambda e: self.update_char_operation_panel()
        )

        # Operation panel frame
        self.char_ops_panel = ttk.LabelFrame(
            self.tab_char_mgmt, text="Operation Details", padding=15
        )
        self.char_ops_panel.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Initialize with copy operation
        self.update_char_operation_panel()

    def setup_character_tab(self):
        """Character editor tab"""
        ttk.Label(
            self.tab_character,
            text="Character Editor",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        # Slot selector
        select_frame = ttk.Frame(self.tab_character)
        select_frame.pack(fill=tk.X, pady=10)

        ttk.Label(select_frame, text="Character Slot:").pack(side=tk.LEFT, padx=5)

        self.char_slot_var = tk.IntVar(value=1)
        slot_combo = ttk.Combobox(
            select_frame,
            textvariable=self.char_slot_var,
            values=list(range(1, 11)),
            state="readonly",
            width=5,
        )
        slot_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            select_frame,
            text="Load Character",
            command=self.load_character_for_edit,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        # Editor notebook
        editor_notebook = ttk.Notebook(self.tab_character)
        editor_notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        # Stats sub-tab
        stats_frame = ttk.Frame(editor_notebook, padding=10)
        editor_notebook.add(stats_frame, text="Stats")
        self.setup_stats_editor(stats_frame)

        # Equipment sub-tab
        equipment_frame = ttk.Frame(editor_notebook, padding=10)
        editor_notebook.add(equipment_frame, text="Equipment")
        self.setup_equipment_editor(equipment_frame)

        # Info sub-tab
        info_frame = ttk.Frame(editor_notebook, padding=10)
        editor_notebook.add(info_frame, text="Info")
        self.setup_character_info(info_frame)

        # Inventory sub-tab
        inventory_frame = ttk.Frame(editor_notebook, padding=10)
        editor_notebook.add(inventory_frame, text="Inventory")
        self.setup_inventory_editor(inventory_frame)

    def setup_stats_editor(self, parent):
        """Stats editing interface"""
        # Create scrollable frame
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Bind mousewheel scrolling
        self.bind_mousewheel(canvas)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Stats fields
        self.stat_vars = {}

        # Top row: Attributes and Resources side by side
        top_row = ttk.Frame(scrollable_frame)
        top_row.pack(fill=tk.X, pady=5)

        # Attributes on the left
        stats_frame = ttk.LabelFrame(top_row, text="Attributes", padding=10)
        stats_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        attributes = [
            ("Vigor", "vigor"),
            ("Mind", "mind"),
            ("Endurance", "endurance"),
            ("Strength", "strength"),
            ("Dexterity", "dexterity"),
            ("Intelligence", "intelligence"),
            ("Faith", "faith"),
            ("Arcane", "arcane"),
        ]

        for i, (label, key) in enumerate(attributes):
            ttk.Label(stats_frame, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=5
            )

            var = tk.IntVar(value=0)
            self.stat_vars[key] = var
            entry = ttk.Entry(stats_frame, textvariable=var, width=10)
            entry.grid(row=i, column=1, padx=5, pady=5)

            # Bind to calculate level on attribute change
            entry.bind("<KeyRelease>", lambda e: self.calculate_character_level())

        # HP/FP/Stamina on the right
        resources_frame = ttk.LabelFrame(
            top_row, text="Health/FP/Stamina (Max Values)", padding=10
        )
        resources_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        resources = [
            ("Max HP", "max_hp", "base_max_hp"),
            ("Max FP", "max_fp", "base_max_fp"),
            ("Max Stamina", "max_sp", "base_max_sp"),
        ]

        for i, (label, max_key, base_key) in enumerate(resources):
            ttk.Label(resources_frame, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=5
            )

            var_max = tk.IntVar(value=0)
            self.stat_vars[max_key] = var_max
            ttk.Entry(resources_frame, textvariable=var_max, width=10).grid(
                row=i, column=1, padx=5, pady=5
            )

            ttk.Label(resources_frame, text="Base:").grid(
                row=i, column=2, sticky=tk.W, padx=5, pady=5
            )

            var_base = tk.IntVar(value=0)
            self.stat_vars[base_key] = var_base
            ttk.Entry(resources_frame, textvariable=var_base, width=10).grid(
                row=i, column=3, padx=5, pady=5
            )

        # Bottom row: Level & Runes in one compact frame
        bottom_row = ttk.Frame(scrollable_frame)
        bottom_row.pack(fill=tk.X, pady=5)

        other_frame = ttk.LabelFrame(bottom_row, text="Level & Runes", padding=10)
        other_frame.pack(fill=tk.X)

        # Level row
        ttk.Label(other_frame, text="Level:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.level_var = tk.IntVar(value=0)
        ttk.Entry(other_frame, textvariable=self.level_var, width=10).grid(
            row=0, column=1, padx=5, pady=5
        )

        ttk.Label(other_frame, text="Calculated Level:").grid(
            row=0, column=2, sticky=tk.W, padx=(20, 5), pady=5
        )
        self.calculated_level_var = tk.IntVar(value=0)
        ttk.Label(
            other_frame,
            textvariable=self.calculated_level_var,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=3, padx=5, pady=5)

        # Level warning
        self.level_warning_var = tk.StringVar(value="")
        self.level_warning_label = ttk.Label(
            other_frame,
            textvariable=self.level_warning_var,
            foreground="red",
            font=("Segoe UI", 9),
        )
        self.level_warning_label.grid(row=0, column=4, padx=10, pady=5, sticky=tk.W)

        # Runes row
        ttk.Label(other_frame, text="Runes:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.runes_var = tk.IntVar(value=0)
        ttk.Entry(other_frame, textvariable=self.runes_var, width=15).grid(
            row=1, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5
        )

        # Apply/Revert buttons
        button_frame = ttk.LabelFrame(scrollable_frame, text="Actions", padding=10)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            button_frame,
            text="Apply Changes",
            command=self.apply_stat_changes,
            width=20,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Revert",
            command=self.load_character_for_edit,
            width=15,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

    def setup_equipment_editor(self, parent):
        """Equipment editing interface"""
        # Create scrollable frame
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Bind mousewheel scrolling
        self.bind_mousewheel(canvas)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.equipment_vars = {}
        self.equipment_name_labels = {}  # Store item name label widgets

        # Top row: Weapons and Armor
        top_row = ttk.Frame(scrollable_frame)
        top_row.pack(fill=tk.X, pady=5)

        # Weapons frame (left)
        weapons_frame = ttk.LabelFrame(top_row, text="Weapons", padding=10)
        weapons_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        weapons = [
            ("Right Hand 1", "right_hand_armament1"),
            ("Right Hand 2", "right_hand_armament2"),
            ("Right Hand 3", "right_hand_armament3"),
            ("Left Hand 1", "left_hand_armament1"),
            ("Left Hand 2", "left_hand_armament2"),
            ("Left Hand 3", "left_hand_armament3"),
        ]

        for i, (label, key) in enumerate(weapons):
            ttk.Label(weapons_frame, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=3
            )
            var = tk.IntVar(value=0)
            self.equipment_vars[key] = var
            entry = ttk.Entry(weapons_frame, textvariable=var, width=12)
            entry.grid(row=i, column=1, padx=5, pady=3)

            # Item name label
            name_label = ttk.Label(
                weapons_frame, text="", foreground="blue", width=28, anchor="w"
            )
            name_label.grid(row=i, column=2, sticky=tk.W, padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            var.trace("w", lambda *args, k=key: self.update_equipment_name(k))

        # Armor frame (right)
        armor_frame = ttk.LabelFrame(top_row, text="Armor", padding=10)
        armor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        armor = [
            ("Head", "head"),
            ("Chest", "chest"),
            ("Arms", "arms"),
            ("Legs", "legs"),
        ]

        for i, (label, key) in enumerate(armor):
            ttk.Label(armor_frame, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=3
            )
            var = tk.IntVar(value=0)
            self.equipment_vars[key] = var
            entry = ttk.Entry(armor_frame, textvariable=var, width=12)
            entry.grid(row=i, column=1, padx=5, pady=3)

            # Item name label
            name_label = ttk.Label(
                armor_frame, text="", foreground="blue", width=28, anchor="w"
            )
            name_label.grid(row=i, column=2, sticky=tk.W, padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            var.trace("w", lambda *args, k=key: self.update_equipment_name(k))

        # Middle row: Talismans and Arrows/Bolts
        middle_row = ttk.Frame(scrollable_frame)
        middle_row.pack(fill=tk.X, pady=5)

        # Talismans frame (left)
        talisman_frame = ttk.LabelFrame(middle_row, text="Talismans", padding=10)
        talisman_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        talismans = [
            ("Talisman 1", "talisman1"),
            ("Talisman 2", "talisman2"),
            ("Talisman 3", "talisman3"),
            ("Talisman 4", "talisman4"),
        ]

        for i, (label, key) in enumerate(talismans):
            ttk.Label(talisman_frame, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=3
            )
            var = tk.IntVar(value=0)
            self.equipment_vars[key] = var
            entry = ttk.Entry(talisman_frame, textvariable=var, width=12)
            entry.grid(row=i, column=1, padx=5, pady=3)

            # Item name label
            name_label = ttk.Label(
                talisman_frame, text="", foreground="blue", width=28, anchor="w"
            )
            name_label.grid(row=i, column=2, sticky=tk.W, padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            var.trace("w", lambda *args, k=key: self.update_equipment_name(k))

        # Arrows/Bolts frame (right)
        ammo_frame = ttk.LabelFrame(middle_row, text="Arrows & Bolts", padding=10)
        ammo_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        ammo = [
            ("Arrows 1", "arrows1"),
            ("Arrows 2", "arrows2"),
            ("Bolts 1", "bolts1"),
            ("Bolts 2", "bolts2"),
        ]

        for i, (label, key) in enumerate(ammo):
            ttk.Label(ammo_frame, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=3
            )
            var = tk.IntVar(value=0)
            self.equipment_vars[key] = var
            entry = ttk.Entry(ammo_frame, textvariable=var, width=12)
            entry.grid(row=i, column=1, padx=5, pady=3)

            # Item name label
            name_label = ttk.Label(
                ammo_frame, text="", foreground="blue", width=28, anchor="w"
            )
            name_label.grid(row=i, column=2, sticky=tk.W, padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            var.trace("w", lambda *args, k=key: self.update_equipment_name(k))

        # Bottom: Spells (12 slots in 2 columns)
        spells_frame = ttk.LabelFrame(
            scrollable_frame, text="Spells (Memory Slots)", padding=10
        )
        spells_frame.pack(fill=tk.X, pady=5)

        for i in range(12):
            row = i // 2
            col = (i % 2) * 2

            ttk.Label(spells_frame, text=f"Spell {i + 1}:").grid(
                row=row, column=col, sticky=tk.W, padx=5, pady=3
            )
            var = tk.IntVar(value=0)
            key = f"spell{i + 1}"
            self.equipment_vars[key] = var
            entry = ttk.Entry(spells_frame, textvariable=var, width=12)
            entry.grid(row=row, column=col + 1, padx=5, pady=3)

            # Item name label
            name_label = ttk.Label(
                spells_frame, text="", foreground="blue", width=20, anchor="w"
            )
            name_label.grid(row=row, column=col + 2, sticky=tk.W, padx=5, pady=3)
            self.equipment_name_labels[key] = name_label
            var.trace("w", lambda *args, k=key: self.update_equipment_name(k))

        # Info label
        info_label = ttk.Label(
            scrollable_frame,
            text="Enter item IDs directly. Values are gaitem handles that reference inventory items.",
            font=("Segoe UI", 9),
            foreground="gray",
        )
        info_label.pack(pady=10)

        # Apply/Revert buttons
        button_frame = ttk.LabelFrame(scrollable_frame, text="Actions", padding=10)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            button_frame,
            text="Apply Changes",
            command=self.apply_equipment_changes,
            width=20,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Revert",
            command=self.load_equipment_for_edit,
            width=15,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

    def setup_character_info(self, parent):
        """Character info display and editing"""
        # Create scrollable frame
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Bind mousewheel scrolling
        self.bind_mousewheel(canvas)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.char_info_vars = {}

        # Character creation info
        creation_frame = ttk.LabelFrame(
            scrollable_frame, text="Character Creation", padding=10
        )
        creation_frame.pack(fill=tk.X, pady=5)

        # Name
        ttk.Label(creation_frame, text="Name:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_name_var = tk.StringVar(value="")

        # Add validation for max 16 characters
        def validate_name(new_value):
            if len(new_value) <= 16:
                return True
            return False

        name_vcmd = (creation_frame.register(validate_name), "%P")
        name_entry = ttk.Entry(
            creation_frame,
            textvariable=self.char_name_var,
            width=30,
            validate="key",
            validatecommand=name_vcmd,
        )
        name_entry.grid(row=0, column=1, columnspan=3, padx=5, pady=5)

        # Add label showing character count
        self.char_name_count_label = ttk.Label(
            creation_frame, text="0/16", font=("Segoe UI", 8), foreground="gray"
        )
        self.char_name_count_label.grid(row=0, column=4, padx=5, pady=5)

        # Update counter on change
        def update_name_count(*args):
            count = len(self.char_name_var.get())
            self.char_name_count_label.config(text=f"{count}/16")

        self.char_name_var.trace("w", update_name_count)

        # Body Type
        ttk.Label(creation_frame, text="Body Type:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_body_type_var = tk.IntVar(value=0)
        body_type_combo = ttk.Combobox(
            creation_frame,
            textvariable=self.char_body_type_var,
            values=["Type A (0)", "Type B (1)"],
            state="readonly",
            width=15,
        )
        body_type_combo.grid(row=1, column=1, padx=5, pady=5)

        # Archetype (starting class)
        ttk.Label(creation_frame, text="Archetype:").grid(
            row=1, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.char_archetype_var = tk.IntVar(value=0)
        ttk.Entry(creation_frame, textvariable=self.char_archetype_var, width=10).grid(
            row=1, column=3, padx=5, pady=5
        )

        # Voice type
        ttk.Label(creation_frame, text="Voice Type:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_voice_var = tk.IntVar(value=0)
        voice_combo = ttk.Combobox(
            creation_frame,
            textvariable=self.char_voice_var,
            values=["Young (0)", "Mature (1)", "Aged (2)"],
            state="readonly",
            width=15,
        )
        voice_combo.grid(row=2, column=1, padx=5, pady=5)

        # Keepsake gift
        ttk.Label(creation_frame, text="Keepsake:").grid(
            row=2, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.char_gift_var = tk.IntVar(value=0)
        ttk.Entry(creation_frame, textvariable=self.char_gift_var, width=10).grid(
            row=2, column=3, padx=5, pady=5
        )

        # Game progression info
        progression_frame = ttk.LabelFrame(
            scrollable_frame, text="Game Progression", padding=10
        )
        progression_frame.pack(fill=tk.X, pady=5)

        # Additional talisman slots
        ttk.Label(progression_frame, text="Extra Talisman Slots:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_talisman_slots_var = tk.IntVar(value=0)
        ttk.Entry(
            progression_frame, textvariable=self.char_talisman_slots_var, width=10
        ).grid(row=0, column=1, padx=5, pady=5)

        # Spirit summon level
        ttk.Label(progression_frame, text="Spirit Summon Level:").grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.char_spirit_level_var = tk.IntVar(value=0)
        ttk.Entry(
            progression_frame, textvariable=self.char_spirit_level_var, width=10
        ).grid(row=0, column=3, padx=5, pady=5)

        # Flask info
        flask_frame = ttk.LabelFrame(scrollable_frame, text="Flasks", padding=10)
        flask_frame.pack(fill=tk.X, pady=5)

        ttk.Label(flask_frame, text="Max Crimson Flasks:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_crimson_flask_var = tk.IntVar(value=0)
        ttk.Entry(flask_frame, textvariable=self.char_crimson_flask_var, width=10).grid(
            row=0, column=1, padx=5, pady=5
        )

        ttk.Label(flask_frame, text="Max Cerulean Flasks:").grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.char_cerulean_flask_var = tk.IntVar(value=0)
        ttk.Entry(
            flask_frame, textvariable=self.char_cerulean_flask_var, width=10
        ).grid(row=0, column=3, padx=5, pady=5)

        # Apply/Revert buttons
        button_frame = ttk.LabelFrame(scrollable_frame, text="Actions", padding=10)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            button_frame,
            text="Apply Changes",
            command=self.apply_character_info_changes,
            width=20,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Revert",
            command=self.load_character_info_for_edit,
            width=15,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

    def setup_inventory_editor(self, parent):
        """Inventory editing interface"""
        # Create scrollable frame
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        # Bind mousewheel scrolling
        self.bind_mousewheel(canvas)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add item frame
        add_frame = ttk.LabelFrame(scrollable_frame, text="Add/Spawn Item", padding=10)
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
            command=self.add_inventory_item,
            width=15,
            style="Accent.TButton",
        ).grid(row=3, column=0, columnspan=4, pady=10)

        # Item list frame
        list_frame = ttk.LabelFrame(
            scrollable_frame, text="Current Inventory", padding=10
        )
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
        filter_combo.bind(
            "<<ComboboxSelected>>", lambda e: self.refresh_inventory_list()
        )

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
        remove_frame = ttk.Frame(scrollable_frame)
        remove_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            remove_frame,
            text="Remove Selected Item",
            command=self.remove_inventory_item,
            width=20,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            remove_frame,
            text="Refresh List",
            command=self.refresh_inventory_list,
            width=15,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        # Info section
        info_label = ttk.Label(
            scrollable_frame,
            text="Item IDs can be found in ITEM_IDS_Elden_Ring.txt reference file.\n"
            "Upgrade level: 0-25 for regular, 0-10 for somber.\n"
            "Changes are saved immediately when adding/removing items.",
            font=("Segoe UI", 9),
            foreground="gray",
            justify=tk.LEFT,
        )
        info_label.pack(pady=10)

    def setup_appearance_tab(self):
        """Appearance and presets tab"""
        ttk.Label(
            self.tab_appearance,
            text="Character Appearance & Presets",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        # Preset list
        preset_frame = ttk.LabelFrame(
            self.tab_appearance, text="Character Presets (15 slots)", padding=10
        )
        preset_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        list_frame = ttk.Frame(preset_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.preset_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            height=12,
        )
        self.preset_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.preset_listbox.yview)

        # Preset actions
        action_frame = ttk.Frame(self.tab_appearance)
        action_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            action_frame,
            text="View Details",
            command=self.view_preset_details,
            width=18,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            action_frame,
            text="Export to JSON",
            command=self.export_presets,
            width=18,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            action_frame,
            text="Import from JSON",
            command=self.import_preset_from_json,
            width=18,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

    def setup_world_tab(self):
        """World state tab"""
        ttk.Label(
            self.tab_world,
            text="World State Editor",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        # Slot selector
        select_frame = ttk.Frame(self.tab_world)
        select_frame.pack(fill=tk.X, pady=10)

        ttk.Label(select_frame, text="Character Slot:").pack(side=tk.LEFT, padx=5)

        self.world_slot_var = tk.IntVar(value=1)
        ttk.Combobox(
            select_frame,
            textvariable=self.world_slot_var,
            values=list(range(1, 11)),
            state="readonly",
            width=5,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            select_frame,
            text="Load World State",
            command=self.load_world_state,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        # Location info
        location_frame = ttk.LabelFrame(
            self.tab_world, text="Current Location", padding=10
        )
        location_frame.pack(fill=tk.X, pady=10)

        self.location_text = tk.Text(
            location_frame,
            height=6,
            font=("Consolas", 9),
            state="disabled",
            wrap=tk.WORD,
        )
        self.location_text.pack(fill=tk.X)

        # Teleport
        teleport_frame = ttk.LabelFrame(
            self.tab_world, text="Teleportation", padding=10
        )
        teleport_frame.pack(fill=tk.X, pady=10)

        ttk.Label(teleport_frame, text="Teleport to safe location:").pack(
            anchor=tk.W, pady=5
        )

        teleport_buttons = ttk.Frame(teleport_frame)
        teleport_buttons.pack(fill=tk.X)

        locations = [
            ("Church of Elleh", "limgrave"),
            ("Lake-Facing Cliffs", "liurnia"),
            ("Smoldering Wall", "caelid"),
        ]

        for i, (name, key) in enumerate(locations):
            ttk.Button(
                teleport_buttons,
                text=name,
                command=lambda k=key: self.teleport_character(k),
                width=20,
                style="Accent.TButton",
            ).grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky=tk.W)

    def setup_steamid_tab(self):
        """SteamID Patcher tab"""
        ttk.Label(
            self.tab_steamid,
            text="SteamID Patcher",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=10)

        info_text = ttk.Label(
            self.tab_steamid,
            text="Transfer save files between Steam accounts by patching SteamID",
            font=("Segoe UI", 10),
            foreground="gray",
        )
        info_text.pack(pady=5)

        # Current SteamID display
        current_frame = ttk.LabelFrame(
            self.tab_steamid, text="Current Save File", padding=15
        )
        current_frame.pack(fill=tk.X, padx=20, pady=10)

        self.current_steamid_var = tk.StringVar(value="No save file loaded")
        ttk.Label(
            current_frame,
            textvariable=self.current_steamid_var,
            font=("Consolas", 10),
        ).pack(anchor=tk.W)

        # Patch section
        patch_frame = ttk.LabelFrame(self.tab_steamid, text="Patch SteamID", padding=15)
        patch_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(
            patch_frame,
            text="Enter new SteamID (17-digit number):",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=5)

        steamid_entry_frame = ttk.Frame(patch_frame)
        steamid_entry_frame.pack(fill=tk.X, pady=5)

        self.new_steamid_var = tk.StringVar()
        steamid_entry = ttk.Entry(
            steamid_entry_frame,
            textvariable=self.new_steamid_var,
            font=("Consolas", 11),
            width=20,
        )
        steamid_entry.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            steamid_entry_frame,
            text="Patch SteamID",
            command=self.patch_steamid,
            width=15,
            style="Accent.TButton",
        ).pack(side=tk.LEFT)

        ttk.Button(
            steamid_entry_frame,
            text="Auto-Detect from System",
            command=self.auto_detect_steamid,
            width=20,
        ).pack(side=tk.LEFT, padx=5)

        # Info
        info_frame = ttk.LabelFrame(self.tab_steamid, text="Information", padding=15)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        info = """What is SteamID Patching?
When you transfer a save file to another computer or Steam account, the SteamID
mismatch can cause issues. This tool updates the SteamID in all character slots.

How to use:
1. Load the save file you want to transfer
2. Enter the target Steam account's SteamID (17 digits)
3. Click "Patch SteamID" to update the save file
4. A backup is automatically created before patching

Warning:
• Make sure you have the correct SteamID
• Patching to the wrong SteamID may cause save corruption
• Always test the patched save file before deleting the original"""

        ttk.Label(
            info_frame,
            text=info,
            font=("Segoe UI", 9),
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

    def setup_event_flags_tab(self):
        """Event Flags tab"""
        ttk.Label(
            self.tab_event_flags,
            text="Event Flags",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=10)

        info_text = ttk.Label(
            self.tab_event_flags,
            text="View and edit event flags that control game progression",
            font=("Segoe UI", 10),
            foreground="gray",
        )
        info_text.pack(pady=5)

        # Slot selector
        slot_frame = ttk.Frame(self.tab_event_flags)
        slot_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(slot_frame, text="Character Slot:", font=("Segoe UI", 10)).pack(
            side=tk.LEFT, padx=5
        )

        self.eventflag_slot_var = tk.IntVar(value=1)
        slot_combo = ttk.Combobox(
            slot_frame,
            textvariable=self.eventflag_slot_var,
            values=list(range(1, 11)),
            state="readonly",
            width=5,
        )
        slot_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            slot_frame,
            text="Load Event Flags",
            command=self.load_event_flags,
            width=20,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=10)

        # Quick fixes
        fixes_frame = ttk.LabelFrame(
            self.tab_event_flags, text="Quick Fixes", padding=15
        )
        fixes_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(
            fixes_frame,
            text="Fix common event flag issues:",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=5)

        button_grid = ttk.Frame(fixes_frame)
        button_grid.pack(fill=tk.X)

        ttk.Button(
            button_grid,
            text="Fix Ranni Quest",
            command=lambda: self.fix_event_flag_issue("ranni"),
            width=18,
        ).grid(row=0, column=0, padx=5, pady=5)

        ttk.Button(
            button_grid,
            text="Fix Warp Sickness",
            command=lambda: self.fix_event_flag_issue("warp"),
            width=18,
        ).grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(
            button_grid,
            text="Clear Softlock Flags",
            command=lambda: self.fix_event_flag_issue("softlock"),
            width=18,
        ).grid(row=0, column=2, padx=5, pady=5)

        # Event flag viewer (placeholder)
        viewer_frame = ttk.LabelFrame(
            self.tab_event_flags, text="Event Flags", padding=10
        )
        viewer_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Add scrollable text area for flags
        text_frame = ttk.Frame(viewer_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.eventflag_text = tk.Text(
            text_frame,
            height=15,
            font=("Consolas", 9),
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
        )
        self.eventflag_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.eventflag_text.yview)

        self.eventflag_text.insert("1.0", "Load a character to view event flags")
        self.eventflag_text.config(state="disabled")

    def setup_gestures_tab(self):
        """Gestures & Regions tab"""
        ttk.Label(
            self.tab_gestures,
            text="Gestures & Regions",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=10)

        info_text = ttk.Label(
            self.tab_gestures,
            text="View and manage unlocked gestures and discovered regions",
            font=("Segoe UI", 10),
            foreground="gray",
        )
        info_text.pack(pady=5)

        # Slot selector
        slot_frame = ttk.Frame(self.tab_gestures)
        slot_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(slot_frame, text="Character Slot:", font=("Segoe UI", 10)).pack(
            side=tk.LEFT, padx=5
        )

        self.gesture_slot_var = tk.IntVar(value=1)
        slot_combo = ttk.Combobox(
            slot_frame,
            textvariable=self.gesture_slot_var,
            values=list(range(1, 11)),
            state="readonly",
            width=5,
        )
        slot_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            slot_frame,
            text="Load Character",
            command=self.load_gestures_regions,
            width=20,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=10)

        # Notebook for gestures and regions
        notebook = ttk.Notebook(self.tab_gestures)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Gestures tab
        gestures_frame = ttk.Frame(notebook, padding=10)
        notebook.add(gestures_frame, text="Gestures")

        gestures_text_frame = ttk.Frame(gestures_frame)
        gestures_text_frame.pack(fill=tk.BOTH, expand=True)

        gestures_scrollbar = ttk.Scrollbar(gestures_text_frame)
        gestures_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.gestures_text = tk.Text(
            gestures_text_frame,
            height=15,
            font=("Consolas", 9),
            yscrollcommand=gestures_scrollbar.set,
            wrap=tk.WORD,
        )
        self.gestures_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        gestures_scrollbar.config(command=self.gestures_text.yview)

        self.gestures_text.insert("1.0", "Load a character to view unlocked gestures")
        self.gestures_text.config(state="disabled")

        # Regions tab
        regions_frame = ttk.Frame(notebook, padding=10)
        notebook.add(regions_frame, text="Regions")

        regions_text_frame = ttk.Frame(regions_frame)
        regions_text_frame.pack(fill=tk.BOTH, expand=True)

        regions_scrollbar = ttk.Scrollbar(regions_text_frame)
        regions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.regions_text = tk.Text(
            regions_text_frame,
            height=15,
            font=("Consolas", 9),
            yscrollcommand=regions_scrollbar.set,
            wrap=tk.WORD,
        )
        self.regions_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        regions_scrollbar.config(command=self.regions_text.yview)

        self.regions_text.insert("1.0", "Load a character to view discovered regions")
        self.regions_text.config(state="disabled")

    def setup_hex_tab(self):
        """Hex Editor tab"""
        ttk.Label(
            self.tab_hex,
            text="Hex Editor",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=10)

        info_text = ttk.Label(
            self.tab_hex,
            text="Advanced: View and edit raw save file data in hexadecimal format",
            font=("Segoe UI", 10),
            foreground="gray",
        )
        info_text.pack(pady=5)

        # Warning
        warning_frame = ttk.Frame(self.tab_hex, padding=10)
        warning_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(
            warning_frame,
            text="⚠️  Warning: Direct hex editing can corrupt your save file. Use with caution!",
            font=("Segoe UI", 10, "bold"),
            foreground="red",
        ).pack()

        # Controls
        control_frame = ttk.Frame(self.tab_hex)
        control_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(control_frame, text="Offset:", font=("Segoe UI", 10)).pack(
            side=tk.LEFT, padx=5
        )

        self.hex_offset_var = tk.StringVar(value="0x0000")
        offset_entry = ttk.Entry(
            control_frame,
            textvariable=self.hex_offset_var,
            font=("Consolas", 10),
            width=12,
        )
        offset_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            control_frame,
            text="Go to Offset",
            command=self.hex_goto_offset,
            width=15,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            control_frame,
            text="Refresh",
            command=self.hex_refresh,
            width=12,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            control_frame,
            text="Save Changes",
            command=self.hex_save,
            width=15,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        # Hex viewer
        hex_frame = ttk.LabelFrame(self.tab_hex, text="Hex Data", padding=10)
        hex_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Create a frame for hex and ASCII
        display_frame = ttk.Frame(hex_frame)
        display_frame.pack(fill=tk.BOTH, expand=True)

        # Hex display
        hex_text_frame = ttk.Frame(display_frame)
        hex_text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        hex_scrollbar = ttk.Scrollbar(hex_text_frame)
        hex_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.hex_text = tk.Text(
            hex_text_frame,
            height=20,
            width=60,
            font=("Consolas", 9),
            yscrollcommand=hex_scrollbar.set,
            wrap=tk.NONE,
        )
        self.hex_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hex_scrollbar.config(command=self.hex_text.yview)

        self.hex_text.insert("1.0", "Load a save file to view hex data")
        self.hex_text.config(state="disabled")

        # Info panel
        info_panel = ttk.LabelFrame(
            self.tab_hex, text="Save Structure Info", padding=10
        )
        info_panel.pack(fill=tk.X, padx=20, pady=5)

        structure_info = """Save File Structure:
• 0x0000-0x0003: Magic bytes (BND4 or SL2\x00)
• 0x0004-0x02FF: Header data
• 0x0300-0x280FFF: Character slots (10 slots × 0x280000 bytes)
  - Each slot: 0x10 checksum + 0x27FFF0 data
• User data sections contain character stats, inventory, world state"""

        ttk.Label(
            info_panel,
            text=structure_info,
            font=("Consolas", 8),
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

    def setup_advanced_tab(self):
        """Advanced tools tab"""
        ttk.Label(
            self.tab_advanced,
            text="Advanced Tools",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        # Save info
        info_frame = ttk.LabelFrame(
            self.tab_advanced, text="Save Information", padding=10
        )
        info_frame.pack(fill=tk.X, pady=10)

        self.save_info_text = tk.Text(
            info_frame, height=8, font=("Consolas", 9), state="disabled", wrap=tk.WORD
        )
        self.save_info_text.pack(fill=tk.X)

        # Tools
        tools_frame = ttk.LabelFrame(self.tab_advanced, text="Tools", padding=10)
        tools_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            tools_frame,
            text="Validate Save File",
            command=self.validate_save,
            width=25,
            style="Accent.TButton",
        ).pack(pady=5)

        ttk.Button(
            tools_frame,
            text="Recalculate All Checksums",
            command=self.recalculate_checksums,
            width=25,
            style="Accent.TButton",
        ).pack(pady=5)

    # File operations
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select Elden Ring Save File",
            initialdir=self.default_save_path,
            filetypes=[("Elden Ring Saves", "*.sl2 *.co2"), ("All files", "*.*")],
        )
        if filename:
            self.file_path_var.set(filename)
            self.status_var.set(f"Selected: {os.path.basename(filename)}")

    def auto_detect(self):
        if not self.default_save_path.exists():
            messagebox.showerror(
                "Not Found",
                f"Elden Ring save folder not found:\n{self.default_save_path}",
            )
            return

        saves = list(self.default_save_path.rglob("ER*.sl2")) + list(
            self.default_save_path.rglob("ER*.co2")
        )

        if not saves:
            messagebox.showwarning("Not Found", "No Elden Ring save files found.")
            return

        if len(saves) == 1:
            self.file_path_var.set(str(saves[0]))
            self.status_var.set("Save file auto-detected")
        else:
            self.show_save_selector(saves)

    def show_save_selector(self, saves):
        """Show dialog to select from multiple saves"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Save File")
        dialog.geometry("600x350")
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"600x350+{x}+{y}")

        ttk.Label(
            dialog,
            text=f"Found {len(saves)} save files:",
            font=("Segoe UI", 11, "bold"),
            padding=15,
        ).pack()

        listbox_frame = ttk.Frame(dialog, padding=15)
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(
            listbox_frame, yscrollcommand=scrollbar.set, font=("Consolas", 9)
        )
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        for save in saves:
            listbox.insert(tk.END, str(save))

        def select_save():
            selection = listbox.curselection()
            if selection:
                self.file_path_var.set(str(saves[selection[0]]))
                self.status_var.set(f"Selected: {saves[selection[0]].name}")
                dialog.destroy()

        ttk.Button(
            dialog, text="Select", command=select_save, style="Accent.TButton"
        ).pack(pady=15)
        listbox.bind("<Double-Button-1>", lambda e: select_save())

    def is_game_running(self):
        """Check if Elden Ring is running"""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq eldenring.exe", "/NH"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if "eldenring.exe" in result.stdout.lower():
                return True

            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq start_protected_game.exe", "/NH"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if "start_protected_game.exe" in result.stdout.lower():
                return True

            return False
        except Exception:
            return None

    def update_backup_stats(self):
        """Update backup statistics display"""
        if not self.save_path:
            self.backup_stats_var.set("Load a save file to view backup statistics")
            return

        try:
            from er_save_manager.backup.manager import BackupManager

            manager = BackupManager(self.save_path)
            backups = manager.list_backups()

            if not backups:
                self.backup_stats_var.set(
                    f"Save File: {os.path.basename(self.save_path)}\n"
                    f"Backups: 0\n\n"
                    f"No backups yet. Backups are created automatically when you make changes."
                )
                return

            # Count by operation type
            operation_counts = {}
            for backup in backups:
                op = backup.operation or "unknown"
                operation_counts[op] = operation_counts.get(op, 0) + 1

            # Format stats
            stats_lines = [
                f"Save File: {os.path.basename(self.save_path)}",
                f"Total Backups: {len(backups)}",
                f"Backup Location: {self.save_path}.backups/",
                "",
                "Backups by Type:",
            ]

            for op, count in sorted(
                operation_counts.items(), key=lambda x: x[1], reverse=True
            ):
                op_name = op.replace("_", " ").title()
                stats_lines.append(f"  • {op_name}: {count}")

            if backups:
                latest = backups[0]
                stats_lines.append("")
                stats_lines.append(f"Latest Backup: {latest.timestamp.split('T')[0]}")

            self.backup_stats_var.set("\n".join(stats_lines))

        except Exception as e:
            self.backup_stats_var.set(f"Error loading backup stats:\n{str(e)}")

    def load_save(self):
        """Load save file"""
        save_path = self.file_path_var.get()

        if not save_path or not os.path.exists(save_path):
            messagebox.showerror("Error", "Please select a valid save file first!")
            return

        # Check if game is running
        if self.is_game_running():
            messagebox.showerror(
                "Elden Ring is Running!",
                "Please close Elden Ring before loading the save file.",
            )
            return

        try:
            self.status_var.set("Loading save file...")
            self.root.update()

            self.save_file = Save.from_file(save_path)
            self.save_path = save_path

            # Populate character list
            self.populate_character_list()

            # Update save info
            self.update_save_info()

            # Load presets
            self.load_presets()

            self.status_var.set(f"Loaded: {os.path.basename(save_path)}")

            # Update backup stats
            if hasattr(self, "update_backup_stats"):
                self.update_backup_stats()

            # Update SteamID display
            if hasattr(self, "current_steamid_var"):
                if self.save_file and hasattr(self.save_file, "user_data_10"):
                    try:
                        steamid = self.save_file.user_data_10.steam_id
                        self.current_steamid_var.set(f"Current SteamID: {steamid}")
                    except Exception:
                        self.current_steamid_var.set("SteamID: Unable to read")
                else:
                    self.current_steamid_var.set("No save file loaded")

            # Update hex view
            if hasattr(self, "hex_text") and self.save_file:
                try:
                    # Store raw data
                    with open(self.save_path, "rb") as f:
                        self.save_file._raw_data = f.read()
                    self.hex_display_at_offset(0)
                except Exception:
                    pass  # Silently fail

            messagebox.showinfo("Success", "Save file loaded successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load save file:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def populate_character_list(self):
        """Populate character listbox"""
        self.char_listbox.delete(0, tk.END)

        if not self.save_file:
            return

        try:
            active_slots = self.save_file.get_active_slots()

            if not active_slots:
                self.char_listbox.insert(tk.END, "No active characters found")
                return

            # Get profiles safely
            profiles = None
            try:
                if self.save_file.user_data_10_parsed:
                    profiles = (
                        self.save_file.user_data_10_parsed.profile_summary.profiles
                    )
            except Exception as e:
                print(f"Warning: Could not load profiles: {e}")

            for slot_idx in active_slots:
                try:
                    slot = self.save_file.characters[slot_idx]
                    if not slot:
                        continue

                    # Get character info safely
                    name = "Unknown"
                    level = "?"

                    if profiles and slot_idx < len(profiles):
                        try:
                            profile = profiles[slot_idx]
                            name = profile.character_name or "Unknown"
                            level = str(profile.level) if profile.level else "?"
                        except Exception as e:
                            print(
                                f"Warning: Could not load profile for slot {slot_idx}: {e}"
                            )

                    # Get map location safely
                    map_str = "Unknown"
                    try:
                        if hasattr(slot, "map_id") and slot.map_id:
                            map_str = slot.map_id.to_string_decimal()
                    except Exception as e:
                        print(f"Warning: Could not get map for slot {slot_idx}: {e}")

                    display_text = f"Slot {slot_idx + 1:2d} | {name:16s} | Lv.{level:>3s} | Map: {map_str}"
                    self.char_listbox.insert(tk.END, display_text)

                except Exception as e:
                    # If individual character fails, show error but continue
                    self.char_listbox.insert(
                        tk.END, f"Slot {slot_idx + 1:2d} | Error loading data"
                    )
                    print(f"Error loading slot {slot_idx}: {e}")

        except Exception as e:
            self.char_listbox.insert(tk.END, "Error loading characters")
            messagebox.showerror("Error", f"Failed to load character list:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def update_save_info(self):
        """Update save information display"""
        if not self.save_file:
            return

        info = []
        info.append("SAVE FILE INFORMATION")
        info.append("=" * 40)
        info.append(f"Platform: {'PlayStation' if self.save_file.is_ps else 'PC'}")
        info.append(f"Magic: {self.save_file.magic.hex()}")

        if self.save_file.user_data_10_parsed:
            ud10 = self.save_file.user_data_10_parsed
            info.append(f"SteamID: {ud10.steam_id}")

        active_slots = self.save_file.get_active_slots()
        info.append(f"Active Characters: {len(active_slots)}")

        self.save_info_text.config(state="normal")
        self.save_info_text.delete("1.0", tk.END)
        self.save_info_text.insert("1.0", "\n".join(info))
        self.save_info_text.config(state="disabled")

    def load_presets(self):
        """Load character presets"""
        self.preset_listbox.delete(0, tk.END)

        if not self.save_file:
            return

        try:
            presets = self.save_file.get_character_presets()
            if not presets:
                self.preset_listbox.insert(tk.END, "No presets found")
                return

            for i in range(15):
                try:
                    preset = presets.presets[i]
                    if preset.is_empty():
                        self.preset_listbox.insert(tk.END, f"Preset {i + 1:2d}: Empty")
                    else:
                        # Use get_body_type() method instead of body_type attribute
                        body_type_value = (
                            preset.get_body_type()
                            if hasattr(preset, "get_body_type")
                            else 0
                        )
                        body_type = "Type A" if body_type_value == 0 else "Type B"
                        self.preset_listbox.insert(
                            tk.END, f"Preset {i + 1:2d}: {body_type}"
                        )
                except Exception:
                    # If individual preset fails, show error but continue
                    self.preset_listbox.insert(tk.END, f"Preset {i + 1:2d}: Error")

        except Exception as e:
            self.preset_listbox.insert(tk.END, "Error loading presets")
            print(f"Error loading presets: {e}")
            import traceback

            traceback.print_exc()

    # Character operations
    def on_character_select(self, event):
        """Handle character selection"""
        selection = self.char_listbox.curselection()
        if selection:
            self.selected_slot = self.save_file.get_active_slots()[selection[0]]

    def show_character_details(self, event=None):
        """Show detailed character information popup with corruption detection"""
        if not self.save_file or self.selected_slot is None:
            messagebox.showwarning("No Selection", "Please select a character first!")
            return

        slot_idx = self.selected_slot
        slot = self.save_file.characters[slot_idx]

        # Get character info from profile
        profiles = None
        name = f"Character {slot_idx + 1}"
        level = "?"
        playtime = "Unknown"

        try:
            if self.save_file.user_data_10_parsed:
                profiles = self.save_file.user_data_10_parsed.profile_summary.profiles
                if profiles and slot_idx < len(profiles):
                    profile = profiles[slot_idx]
                    name = profile.character_name or name
                    level = str(profile.level) if profile.level else level
                    playtime = self.format_playtime(profile.seconds_played)
        except Exception as e:
            print(f"Warning: Could not load profile data: {e}")

        # Get location
        location = "Unknown"
        is_dlc_location = False
        try:
            if hasattr(slot, "map_id") and slot.map_id:
                location = slot.map_id.to_string_decimal()
                is_dlc_location = slot.map_id.is_dlc()
        except Exception as e:
            print(f"Warning: Could not get location: {e}")

        # Use proper corruption detection method
        has_corruption = False
        issues_detected = []
        try:
            has_corruption, corruption_issues = slot.has_corruption()
            if has_corruption:
                issues_detected = corruption_issues
        except Exception as e:
            print(f"Warning: Could not check corruption: {e}")

        # Additional DLC info for display
        has_dlc_flag = False
        has_invalid_dlc = False
        try:
            if hasattr(slot, "dlc_data"):
                from er_save_manager.parser.world import DLC

                dlc = DLC.from_bytes(slot.dlc_data)
                has_dlc_flag = dlc.has_dlc_access()
                has_invalid_dlc = dlc.has_invalid_flags()
        except Exception as e:
            print(f"Warning: Could not check DLC flags: {e}")

        # Build info text
        info = []
        info.append("=" * 50)
        info.append(f"  CHARACTER: {name}")
        info.append("=" * 50)
        info.append(f"  Level: {level}")
        info.append(f"  Playtime: {playtime}")
        info.append(f"  Location: {location}")
        if is_dlc_location:
            info.append("  WARNING: Currently in DLC area!")
        info.append("")

        # DLC info
        if has_dlc_flag or has_invalid_dlc:
            info.append("DLC FLAGS:")
            info.append(f"  Has DLC Access: {'Yes' if has_dlc_flag else 'No'}")
            if has_invalid_dlc:
                info.append("  WARNING: Invalid data in unused DLC slots")
            info.append("")

        # Issues section
        if issues_detected:
            info.append("=" * 50)
            info.append("ISSUES DETECTED:")
            info.append("=" * 50)
            for issue in issues_detected:
                info.append(f"  • {issue}")
            info.append("")
            info.append("Click 'Fix All Issues' to correct everything")
        else:
            info.append("=" * 50)
            info.append("✓ NO ISSUES DETECTED")
            info.append("=" * 50)
            info.append("")
            info.append("Character appears healthy!")

        # Create popup window
        dialog = tk.Toplevel(self.root)
        dialog.withdraw()
        dialog.title(f"Character Details - {name}")

        width, height = 600, 500
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.resizable(False, False)

        # Text display
        text_widget = tk.Text(
            dialog,
            font=("Consolas", 9),
            bg="#f0f0f0",
            wrap=tk.WORD,
            padx=10,
            pady=10,
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        text_widget.insert("1.0", "\n".join(info))
        text_widget.config(state="disabled")

        # Buttons
        button_frame = ttk.Frame(dialog, padding="10")
        button_frame.pack(fill=tk.X)

        if issues_detected:
            ttk.Button(
                button_frame,
                text="Fix All Issues",
                command=lambda: self.fix_character_from_dialog(
                    dialog, slot_idx, len(issues_detected)
                ),
                width=20,
                style="Accent.TButton",
            ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Teleport Character",
            command=lambda: self.teleport_from_dialog(dialog, slot_idx),
            width=20,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Close",
            command=dialog.destroy,
            width=15,
            style="Accent.TButton",
        ).pack(side=tk.RIGHT, padx=5)

        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()
        dialog.attributes("-topmost", True)
        dialog.grab_set()

    def teleport_from_dialog(self, dialog, slot_idx):
        """Teleport character and close dialog"""
        dialog.destroy()

        teleport_dialog = tk.Toplevel(self.root)
        teleport_dialog.title("Teleport Character")
        teleport_dialog.geometry("400x250")
        teleport_dialog.grab_set()

        teleport_dialog.update_idletasks()
        x = (teleport_dialog.winfo_screenwidth() // 2) - (
            teleport_dialog.winfo_width() // 2
        )
        y = (teleport_dialog.winfo_screenheight() // 2) - (
            teleport_dialog.winfo_height() // 2
        )
        teleport_dialog.geometry(f"400x250+{x}+{y}")

        ttk.Label(
            teleport_dialog,
            text=f"Teleport Slot {slot_idx + 1}",
            font=("Segoe UI", 14, "bold"),
            padding=10,
        ).pack()

        location_frame = ttk.LabelFrame(
            teleport_dialog, text="Select Destination", padding=10
        )
        location_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        location_var = tk.StringVar(value="limgrave")

        locations = [
            ("limgrave", "Limgrave - First Step"),
            ("roundtable", "Roundtable Hold"),
            ("liurnia", "Liurnia - Lake-Facing Cliffs"),
            ("altus", "Altus Plateau - Erdtree-Gazing Hill"),
        ]

        for key, name in locations:
            ttk.Radiobutton(
                location_frame,
                text=name,
                value=key,
                variable=location_var,
            ).pack(anchor=tk.W, pady=2)

        def do_teleport():
            try:
                from er_save_manager.backup.manager import BackupManager
                from er_save_manager.fixes.teleport import TeleportFix

                # Get destination first
                destination = location_var.get()

                manager = BackupManager(self.save_path)
                manager.create_backup(
                    description=f"before_teleport_to_{destination}",
                    operation=f"teleport_to_{destination}",
                    save=self.save_file,
                )

                teleport = TeleportFix(destination)
                result = teleport.apply(self.save_file, slot_idx)

                if result.applied:
                    self.save_file.recalculate_checksums()
                    self.save_file.to_file(self.save_path)
                    self.load_save()

                    details = "\n".join(result.details) if result.details else ""
                    messagebox.showinfo(
                        "Success",
                        f"{result.description}\n\n{details}\n\nBackup saved to backup manager.",
                    )
                    teleport_dialog.destroy()
                else:
                    messagebox.showwarning("Not Applied", result.description)

            except Exception as e:
                messagebox.showerror("Error", f"Teleport failed:\n{str(e)}")
                import traceback

                traceback.print_exc()

        button_frame = ttk.Frame(teleport_dialog, padding=10)
        button_frame.pack(fill=tk.X)

        ttk.Button(
            button_frame,
            text="Teleport",
            command=do_teleport,
            width=15,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=teleport_dialog.destroy,
            width=15,
            style="Accent.TButton",
        ).pack(side=tk.RIGHT, padx=5)

    def fix_character_from_dialog(self, dialog, slot_idx, issue_count):
        """Fix character corruption and close dialog"""
        dialog.destroy()

        # Confirm
        if not messagebox.askyesno(
            "Confirm",
            f"Fix all {issue_count} issue(s) in Slot {slot_idx + 1}?\n\nA backup will be created.",
        ):
            return

        try:
            # Create backup
            from er_save_manager.backup.manager import BackupManager

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_fix_slot_{slot_idx + 1}",
                operation="fix_corruption",
                save=self.save_file,
            )

            # Apply fix using the existing corruption fix method
            was_fixed, fixes = self.save_file.fix_character_corruption(slot_idx)

            # Update operation description based on what was fixed
            if fixes:
                # Use first fix type as primary operation
                first_fix = fixes[0].lower()
                if "torrent" in first_fix:
                    manager.history.backups[0].operation = "fix_corruption_torrent"
                elif "weather" in first_fix:
                    manager.history.backups[0].operation = "fix_corruption_weather"
                elif "time" in first_fix:
                    manager.history.backups[0].operation = "fix_corruption_time"
                elif "steamid" in first_fix:
                    manager.history.backups[0].operation = "fix_corruption_steamid"
                elif "event" in first_fix or "flag" in first_fix:
                    manager.history.backups[0].operation = "fix_corruption_event_flags"
                elif "dlc" in first_fix:
                    manager.history.backups[0].operation = "fix_corruption_dlc"
                manager._save_history()

            if was_fixed:
                # Save
                self.save_file.recalculate_checksums()
                self.save_file.to_file(self.save_path)

                # Reload
                self.load_save()

                # Show success message
                fix_list = "\n".join(f"  • {fix}" for fix in fixes[:5])
                if len(fixes) > 5:
                    fix_list += f"\n  • ...and {len(fixes) - 5} more"

                messagebox.showinfo(
                    "Success",
                    f"Fixed {len(fixes)} issue(s):\n\n{fix_list}\n\n"
                    "Backup saved to backup manager.",
                )
            else:
                messagebox.showinfo("No Issues", "No corruption was detected or fixed")

        except Exception as e:
            messagebox.showerror("Error", f"Fix failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def format_playtime(self, seconds):
        """Format seconds as HH:MM:SS"""
        if not seconds:
            return "0h 0m 0s"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs}s"

    def quick_fix_all(self):
        """Apply all fixes to selected character"""
        if not self.save_file or self.selected_slot is None:
            messagebox.showwarning("No Selection", "Please select a character first!")
            return

        if not messagebox.askyesno(
            "Confirm",
            f"Fix all issues in Slot {self.selected_slot + 1}?\n\nA backup will be created.",
        ):
            return

        try:
            # Create backup
            from er_save_manager.backup.manager import BackupManager

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description="before_fix",
                operation="fix_corruption",
                save=self.save_file,
            )

            # Apply fix
            was_fixed, fixes = self.save_file.fix_character_corruption(
                self.selected_slot
            )

            if was_fixed:
                # Save
                self.save_file.recalculate_checksums()
                self.save_file.to_file(self.save_path)

                # Reload
                self.load_save()

                messagebox.showinfo(
                    "Success",
                    f"Fixed {len(fixes)} issue(s):\n\n"
                    + "\n".join(fixes[:5])
                    + (f"\n...and {len(fixes) - 5} more" if len(fixes) > 5 else "")
                    + "\n\nBackup saved to backup manager.",
                )
            else:
                messagebox.showinfo("No Issues", "No corruption detected")

        except Exception as e:
            messagebox.showerror("Error", f"Fix failed:\n{str(e)}")

    # Character editor operations
    def calculate_character_level(self):
        """Calculate expected character level from attributes based on starting class"""
        try:
            # Get archetype from currently loaded character
            archetype = 9  # Default to Wretch

            if self.save_file and hasattr(self, "char_slot_var"):
                slot_idx = self.char_slot_var.get() - 1
                try:
                    slot = self.save_file.characters[slot_idx]
                    if (
                        slot
                        and hasattr(slot, "player_game_data")
                        and slot.player_game_data
                    ):
                        archetype = slot.player_game_data.archetype
                        # Debug output
                        print(f"DEBUG: Slot {slot_idx + 1} archetype = {archetype}")
                except Exception as e:
                    print(f"DEBUG: Failed to get archetype: {e}")
                    import traceback

                    traceback.print_exc()

            # Get current attributes
            vigor = self.stat_vars["vigor"].get()
            mind = self.stat_vars["mind"].get()
            endurance = self.stat_vars["endurance"].get()
            strength = self.stat_vars["strength"].get()
            dexterity = self.stat_vars["dexterity"].get()
            intelligence = self.stat_vars["intelligence"].get()
            faith = self.stat_vars["faith"].get()
            arcane = self.stat_vars["arcane"].get()

            # Calculate level using actual class data
            from er_save_manager.data import calculate_level_from_stats, get_class_data

            calculated_level = calculate_level_from_stats(
                vigor,
                mind,
                endurance,
                strength,
                dexterity,
                intelligence,
                faith,
                arcane,
                archetype,
            )

            # Update calculated level display
            self.calculated_level_var.set(calculated_level)

            # Show class name in warning if available
            class_data = get_class_data(archetype)
            class_name = class_data.get("name", "Unknown")
            print(f"DEBUG: Class name = {class_name}, archetype = {archetype}")

            # Check if current level matches
            current_level = self.level_var.get()
            if current_level != calculated_level:
                self.level_warning_var.set(
                    f"⚠ Mismatch! Recommend {calculated_level} (based on {class_name})"
                )
            else:
                self.level_warning_var.set("")

        except Exception as e:
            # If any errors occur, just clear the display
            print(f"DEBUG: Exception in calculate_character_level: {e}")
            import traceback

            traceback.print_exc()
            self.calculated_level_var.set(0)
            self.level_warning_var.set("")

    def load_character_for_edit(self):
        """Load character data for editing"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.char_slot_var.get() - 1

        try:
            slot = self.save_file.characters[slot_idx]

            if not slot or slot.is_empty():
                messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
                return

            # Load stats safely
            if hasattr(slot, "player_game_data") and slot.player_game_data:
                char = slot.player_game_data

                # Set stats with error handling
                try:
                    self.stat_vars["vigor"].set(getattr(char, "vigor", 0))
                    self.stat_vars["mind"].set(getattr(char, "mind", 0))
                    self.stat_vars["endurance"].set(getattr(char, "endurance", 0))
                    self.stat_vars["strength"].set(getattr(char, "strength", 0))
                    self.stat_vars["dexterity"].set(getattr(char, "dexterity", 0))
                    self.stat_vars["intelligence"].set(getattr(char, "intelligence", 0))
                    self.stat_vars["faith"].set(getattr(char, "faith", 0))
                    self.stat_vars["arcane"].set(getattr(char, "arcane", 0))

                    self.level_var.set(getattr(char, "level", 0))
                    self.runes_var.set(getattr(char, "runes", 0))

                    self.stat_vars["max_hp"].set(getattr(char, "max_hp", 0))
                    self.stat_vars["base_max_hp"].set(getattr(char, "base_max_hp", 0))
                    self.stat_vars["max_fp"].set(getattr(char, "max_fp", 0))
                    self.stat_vars["base_max_fp"].set(getattr(char, "base_max_fp", 0))
                    self.stat_vars["max_sp"].set(getattr(char, "max_sp", 0))
                    self.stat_vars["base_max_sp"].set(getattr(char, "base_max_sp", 0))

                    # Calculate and show expected level
                    self.calculate_character_level()

                    # Also load equipment and character info
                    try:
                        self.load_equipment_for_edit_internal(slot)
                        self.load_character_info_for_edit_internal(slot)
                    except Exception:
                        pass  # These are optional, don't fail main load

                    messagebox.showinfo(
                        "Loaded", f"Character data loaded for Slot {slot_idx + 1}"
                    )
                except Exception as e:
                    messagebox.showerror(
                        "Error", f"Failed to load some stats:\n{str(e)}"
                    )
            else:
                messagebox.showerror(
                    "Error", "Could not load character data - player_game_data missing"
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load character:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def apply_stat_changes(self):
        """Apply stat changes to character"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.char_slot_var.get() - 1

        # Check for level mismatch
        current_level = self.level_var.get()
        calculated_level = self.calculated_level_var.get()

        if current_level != calculated_level:
            response = messagebox.askyesnocancel(
                "Level Mismatch",
                f"Current level ({current_level}) does not match calculated level ({calculated_level}) based on attributes.\n\n"
                f"It's recommended to set level to {calculated_level}.\n\n"
                f"Yes - Update level to {calculated_level}\n"
                f"No - Keep current level {current_level}\n"
                f"Cancel - Abort changes",
            )

            if response is None:  # Cancel
                return
            elif response:  # Yes - update to calculated level
                self.level_var.set(calculated_level)

        if not messagebox.askyesno(
            "Confirm",
            f"Apply stat changes to Slot {slot_idx + 1}?\n\nA backup will be created.",
        ):
            return

        try:
            # Create backup
            from er_save_manager.backup.manager import BackupManager

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_edit_stats_slot_{slot_idx + 1}",
                operation=f"edit_stats_slot_{slot_idx + 1}",
                save=self.save_file,
            )

            # Modify stats
            slot = self.save_file.characters[slot_idx]
            if hasattr(slot, "player_game_data") and slot.player_game_data:
                char = slot.player_game_data

                # Update stats in memory
                char.vigor = self.stat_vars["vigor"].get()
                char.mind = self.stat_vars["mind"].get()
                char.endurance = self.stat_vars["endurance"].get()
                char.strength = self.stat_vars["strength"].get()
                char.dexterity = self.stat_vars["dexterity"].get()
                char.intelligence = self.stat_vars["intelligence"].get()
                char.faith = self.stat_vars["faith"].get()
                char.arcane = self.stat_vars["arcane"].get()

                char.level = self.level_var.get()
                char.runes = self.runes_var.get()

                char.max_hp = self.stat_vars["max_hp"].get()
                char.base_max_hp = self.stat_vars["base_max_hp"].get()
                char.max_fp = self.stat_vars["max_fp"].get()
                char.base_max_fp = self.stat_vars["base_max_fp"].get()
                char.max_sp = self.stat_vars["max_sp"].get()
                char.base_max_sp = self.stat_vars["base_max_sp"].get()

                # Write back to raw data using tracked offset
                if (
                    hasattr(slot, "player_game_data_offset")
                    and slot.player_game_data_offset >= 0
                ):
                    from io import BytesIO

                    # Serialize character data
                    char_bytes = BytesIO()
                    char.write(char_bytes)
                    char_data = char_bytes.getvalue()

                    # Verify size
                    if len(char_data) != 432:  # PlayerGameData is exactly 432 bytes
                        raise RuntimeError(
                            f"PlayerGameData serialization error: expected 432 bytes, got {len(char_data)}"
                        )

                    # Calculate absolute offset in save file using tracked offset
                    slot_offset = self.save_file._slot_offsets[slot_idx]
                    CHECKSUM_SIZE = 0x10

                    abs_offset = (
                        slot_offset + CHECKSUM_SIZE + slot.player_game_data_offset
                    )

                    # Ensure raw_data is mutable
                    self.ensure_raw_data_mutable()

                    # Write to raw data

                    self.save_file._raw_data[
                        abs_offset : abs_offset + len(char_data)
                    ] = char_data

                    # Recalculate checksums and save
                    self.save_file.recalculate_checksums()
                    self.save_file.to_file(self.save_path)

                    # Reload to verify
                    self.load_save()

                    messagebox.showinfo(
                        "Success",
                        "Stats updated successfully!\n\nBackup saved to backup manager.",
                    )
                else:
                    messagebox.showerror(
                        "Error",
                        "Offset not tracked - cannot save changes.\n\n"
                        "Your parsers need to be updated with offset tracking.\n"
                        "See ERROR_HANDLING.md for details.",
                    )
            else:
                messagebox.showerror("Error", "Could not access character data")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply changes:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def load_equipment_for_edit(self):
        """Load equipment data for editing"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.char_slot_var.get() - 1

        try:
            slot = self.save_file.characters[slot_idx]

            if not slot or slot.is_empty():
                messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
                return

            self.load_equipment_for_edit_internal(slot)
            messagebox.showinfo("Loaded", f"Equipment loaded for Slot {slot_idx + 1}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load equipment:\n{str(e)}")

    def load_equipment_for_edit_internal(self, slot):
        """Internal method to load equipment without messagebox"""
        # Load equipment from equipped_items_item_id
        if hasattr(slot, "equipped_items_item_id") and slot.equipped_items_item_id:
            equip = slot.equipped_items_item_id

            # Set equipment IDs
            self.equipment_vars["right_hand_armament1"].set(
                getattr(equip, "right_hand_armament1", 0)
            )
            self.equipment_vars["right_hand_armament2"].set(
                getattr(equip, "right_hand_armament2", 0)
            )
            self.equipment_vars["right_hand_armament3"].set(
                getattr(equip, "right_hand_armament3", 0)
            )
            self.equipment_vars["left_hand_armament1"].set(
                getattr(equip, "left_hand_armament1", 0)
            )
            self.equipment_vars["left_hand_armament2"].set(
                getattr(equip, "left_hand_armament2", 0)
            )
            self.equipment_vars["left_hand_armament3"].set(
                getattr(equip, "left_hand_armament3", 0)
            )

            self.equipment_vars["head"].set(getattr(equip, "head", 0))
            self.equipment_vars["chest"].set(getattr(equip, "chest", 0))
            self.equipment_vars["arms"].set(getattr(equip, "arms", 0))
            self.equipment_vars["legs"].set(getattr(equip, "legs", 0))

            self.equipment_vars["talisman1"].set(getattr(equip, "talisman1", 0))
            self.equipment_vars["talisman2"].set(getattr(equip, "talisman2", 0))
            self.equipment_vars["talisman3"].set(getattr(equip, "talisman3", 0))
            self.equipment_vars["talisman4"].set(getattr(equip, "talisman4", 0))

            self.equipment_vars["arrows1"].set(getattr(equip, "arrows1", 0))
            self.equipment_vars["arrows2"].set(getattr(equip, "arrows2", 0))
            self.equipment_vars["bolts1"].set(getattr(equip, "bolts1", 0))
            self.equipment_vars["bolts2"].set(getattr(equip, "bolts2", 0))
        # Update all equipment name labels
        for key in self.equipment_vars.keys():
            if key in self.equipment_name_labels:
                self.update_equipment_name(key)

    def update_equipment_name(self, equipment_key):
        """Update equipment name label when ID changes"""
        if equipment_key not in self.equipment_name_labels:
            return

        try:
            item_id = self.equipment_vars[equipment_key].get()
            if item_id == 0 or item_id == -1:
                self.equipment_name_labels[equipment_key].config(text="")
                return

            # Get name from item database
            item_name = get_item_name(item_id)

            # Truncate if too long
            if len(item_name) > 28:
                item_name = item_name[:25] + "..."

            self.equipment_name_labels[equipment_key].config(text=item_name)
        except Exception:
            self.equipment_name_labels[equipment_key].config(text="(Unknown)")

    def apply_equipment_changes(self):
        """Apply equipment changes to character"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.char_slot_var.get() - 1

        if not messagebox.askyesno(
            "Confirm",
            f"Apply equipment changes to Slot {slot_idx + 1}?\n\nA backup will be created.",
        ):
            return

        try:
            # Create backup
            from er_save_manager.backup.manager import BackupManager

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_edit_equipment_slot_{slot_idx + 1}",
                operation=f"edit_equipment_slot_{slot_idx + 1}",
                save=self.save_file,
            )

            # Modify equipment
            slot = self.save_file.characters[slot_idx]
            if hasattr(slot, "equipped_items_item_id") and slot.equipped_items_item_id:
                equip = slot.equipped_items_item_id

                # Update equipment IDs
                equip.right_hand_armament1 = self.equipment_vars[
                    "right_hand_armament1"
                ].get()
                equip.right_hand_armament2 = self.equipment_vars[
                    "right_hand_armament2"
                ].get()
                equip.right_hand_armament3 = self.equipment_vars[
                    "right_hand_armament3"
                ].get()
                equip.left_hand_armament1 = self.equipment_vars[
                    "left_hand_armament1"
                ].get()
                equip.left_hand_armament2 = self.equipment_vars[
                    "left_hand_armament2"
                ].get()
                equip.left_hand_armament3 = self.equipment_vars[
                    "left_hand_armament3"
                ].get()

                equip.head = self.equipment_vars["head"].get()
                equip.chest = self.equipment_vars["chest"].get()
                equip.arms = self.equipment_vars["arms"].get()
                equip.legs = self.equipment_vars["legs"].get()

                equip.talisman1 = self.equipment_vars["talisman1"].get()
                equip.talisman2 = self.equipment_vars["talisman2"].get()
                equip.talisman3 = self.equipment_vars["talisman3"].get()
                equip.talisman4 = self.equipment_vars["talisman4"].get()

                equip.arrows1 = self.equipment_vars["arrows1"].get()
                equip.arrows2 = self.equipment_vars["arrows2"].get()
                equip.bolts1 = self.equipment_vars["bolts1"].get()
                equip.bolts2 = self.equipment_vars["bolts2"].get()

                # Write back using offset
                if hasattr(slot, "equipped_items_item_id_offset"):
                    from io import BytesIO

                    equip_bytes = BytesIO()
                    equip.write(equip_bytes)
                    equip_data = equip_bytes.getvalue()

                    # Calculate absolute offset
                    slot_offset = self.save_file._slot_offsets[slot_idx]
                    CHECKSUM_SIZE = 0x10
                    abs_offset = (
                        slot_offset + CHECKSUM_SIZE + slot.equipped_items_item_id_offset
                    )

                    # Ensure raw_data is mutable
                    self.ensure_raw_data_mutable()

                    # Write to raw data

                    self.save_file._raw_data[
                        abs_offset : abs_offset + len(equip_data)
                    ] = equip_data

                    # Recalculate checksums and save
                    self.save_file.recalculate_checksums()
                    self.save_file.to_file(self.save_path)

                    # Reload to verify
                    self.load_save()

                    messagebox.showinfo(
                        "Success",
                        "Equipment updated successfully!\n\nBackup saved to backup manager.",
                    )
                else:
                    messagebox.showerror("Error", "Offset not tracked for equipment")
            else:
                messagebox.showerror("Error", "Could not access equipment data")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply changes:\n{str(e)}")

    def load_character_info_for_edit(self):
        """Load character info for editing"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.char_slot_var.get() - 1

        try:
            slot = self.save_file.characters[slot_idx]

            if not slot or slot.is_empty():
                messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
                return

            self.load_character_info_for_edit_internal(slot)
            messagebox.showinfo(
                "Loaded", f"Character info loaded for Slot {slot_idx + 1}"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load character info:\n{str(e)}")

    def load_character_info_for_edit_internal(self, slot):
        """Internal method to load character info without messagebox"""
        if hasattr(slot, "player_game_data") and slot.player_game_data:
            char = slot.player_game_data

            self.char_name_var.set(getattr(char, "character_name", ""))
            self.char_body_type_var.set(getattr(char, "gender", 0))
            self.char_archetype_var.set(getattr(char, "archetype", 0))
            self.char_voice_var.set(getattr(char, "voice_type", 0))
            self.char_gift_var.set(getattr(char, "gift", 0))
            self.char_talisman_slots_var.set(
                getattr(char, "additional_talisman_slot_count", 0)
            )
            self.char_spirit_level_var.set(getattr(char, "summon_spirit_level", 0))
            self.char_crimson_flask_var.set(getattr(char, "max_crimson_flask_count", 0))
            self.char_cerulean_flask_var.set(
                getattr(char, "max_cerulean_flask_count", 0)
            )

    def apply_character_info_changes(self):
        """Apply character info changes"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.char_slot_var.get() - 1

        if not messagebox.askyesno(
            "Confirm",
            f"Apply character info changes to Slot {slot_idx + 1}?\n\nA backup will be created.",
        ):
            return

        try:
            # Create backup
            from er_save_manager.backup.manager import BackupManager

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_edit_character_info_slot_{slot_idx + 1}",
                operation=f"edit_character_info_slot_{slot_idx + 1}",
                save=self.save_file,
            )

            # Modify character info
            slot = self.save_file.characters[slot_idx]
            if hasattr(slot, "player_game_data") and slot.player_game_data:
                char = slot.player_game_data

                char.character_name = self.char_name_var.get()
                char.gender = self.char_body_type_var.get()
                char.archetype = self.char_archetype_var.get()
                char.voice_type = self.char_voice_var.get()
                char.gift = self.char_gift_var.get()
                char.additional_talisman_slot_count = self.char_talisman_slots_var.get()
                char.summon_spirit_level = self.char_spirit_level_var.get()
                char.max_crimson_flask_count = self.char_crimson_flask_var.get()
                char.max_cerulean_flask_count = self.char_cerulean_flask_var.get()

                # Write back using offset
                if hasattr(slot, "player_game_data_offset"):
                    from io import BytesIO

                    char_bytes = BytesIO()
                    char.write(char_bytes)
                    char_data = char_bytes.getvalue()

                    # Calculate absolute offset
                    slot_offset = self.save_file._slot_offsets[slot_idx]
                    CHECKSUM_SIZE = 0x10
                    abs_offset = (
                        slot_offset + CHECKSUM_SIZE + slot.player_game_data_offset
                    )

                    # Ensure raw_data is mutable
                    self.ensure_raw_data_mutable()

                    # Write to raw data

                    self.save_file._raw_data[
                        abs_offset : abs_offset + len(char_data)
                    ] = char_data

                    # Recalculate checksums and save
                    self.save_file.recalculate_checksums()
                    self.save_file.to_file(self.save_path)

                    # Reload to verify
                    self.load_save()

                    messagebox.showinfo(
                        "Success",
                        "Character info updated successfully!\n\nBackup saved to backup manager.",
                    )
                else:
                    messagebox.showerror("Error", "Offset not tracked")
            else:
                messagebox.showerror("Error", "Could not access character data")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply changes:\n{str(e)}")

    def refresh_inventory_list(self):
        """Refresh the inventory display"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.char_slot_var.get() - 1

        try:
            slot = self.save_file.characters[slot_idx]

            if not slot or slot.is_empty():
                messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
                return

            self.inventory_listbox.delete(0, tk.END)

            # Get filter value
            filter_val = (
                self.inv_filter_var.get() if hasattr(self, "inv_filter_var") else "All"
            )

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
            messagebox.showerror("Error", f"Failed to refresh inventory:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def add_inventory_item(self):
        """Add item to inventory"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.char_slot_var.get() - 1
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

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_add_item_{item_id}_slot_{slot_idx + 1}",
                operation="add_inventory_item",
                save=self.save_file,
            )

            slot = self.save_file.characters[slot_idx]

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
            from io import BytesIO

            # Write gaitem_map
            gaitem_bytes = BytesIO()
            for gaitem in slot.gaitem_map:
                gaitem.write(gaitem_bytes)
            gaitem_data = gaitem_bytes.getvalue()

            slot_offset = self.save_file._slot_offsets[slot_idx]
            CHECKSUM_SIZE = 0x10
            HEADER_SIZE = 32  # version + map_id + unk fields
            gaitem_abs_offset = slot_offset + CHECKSUM_SIZE + HEADER_SIZE

            # Ensure raw_data is mutable
            self.save_file._raw_data[
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

                self.save_file._raw_data[
                    inv_abs_offset : inv_abs_offset + len(inv_data)
                ] = inv_data

                # Recalculate checksums and save
                self.save_file.recalculate_checksums()
                self.save_file.to_file(self.save_path)

                # Reload
                self.load_save()
                self.refresh_inventory_list()

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

    def remove_inventory_item(self):
        """Remove selected item from inventory"""
        selection = self.inventory_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an item to remove!")
            return

        if not self.save_file:
            return

        # Parse selection to get item location and index
        selected_text = self.inventory_listbox.get(selection[0])

        # Skip header lines
        if "===" in selected_text:
            return

        try:
            # Extract index from format like "[123]" or "[S123]"
            import re

            match = re.search(r"\[([SK]?)(\d+)\]", selected_text)
            if not match:
                return

            location_prefix = match.group(1)
            idx = int(match.group(2))

            slot_idx = self.char_slot_var.get() - 1
            slot = self.save_file.characters[slot_idx]

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

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_remove_item_slot_{slot_idx + 1}",
                operation="remove_inventory_item",
                save=self.save_file,
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
            from io import BytesIO

            gaitem_bytes = BytesIO()
            for gaitem in slot.gaitem_map:
                gaitem.write(gaitem_bytes)
            gaitem_data = gaitem_bytes.getvalue()

            slot_offset = self.save_file._slot_offsets[slot_idx]
            CHECKSUM_SIZE = 0x10
            HEADER_SIZE = 32
            gaitem_abs_offset = slot_offset + CHECKSUM_SIZE + HEADER_SIZE

            self.ensure_raw_data_mutable()
            self.save_file._raw_data[
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
                self.ensure_raw_data_mutable()

                self.save_file._raw_data[
                    inv_abs_offset : inv_abs_offset + len(inv_data)
                ] = inv_data

                self.save_file.recalculate_checksums()
                self.save_file.to_file(self.save_path)

                self.load_save()
                self.refresh_inventory_list()

                messagebox.showinfo("Success", "Item removed from inventory!")
            else:
                messagebox.showerror("Error", "Offset not tracked for inventory")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove item:\n{str(e)}")
            import traceback

            traceback.print_exc()

    # Preset operations (stubs)
    def view_preset_details(self):
        """View detailed preset information"""
        selection = self.preset_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a preset to view!")
            return

        preset_idx = selection[0]

        try:
            presets = self.save_file.get_character_presets()
            if not presets or preset_idx >= len(presets.presets):
                messagebox.showerror("Error", "Could not load preset data")
                return

            preset = presets.presets[preset_idx]

            if preset.is_empty():
                messagebox.showinfo("Empty Preset", f"Preset {preset_idx + 1} is empty")
                return

            dialog = tk.Toplevel(self.root)
            dialog.withdraw()
            dialog.title(f"Preset {preset_idx + 1} Details")

            width, height = 700, 600
            screen_w = dialog.winfo_screenwidth()
            screen_h = dialog.winfo_screenheight()
            x = (screen_w // 2) - (width // 2)
            y = (screen_h // 2) - (height // 2)
            dialog.geometry(f"{width}x{height}+{x}+{y}")

            ttk.Label(
                dialog,
                text=f"Preset {preset_idx + 1} - Character Appearance",
                font=("Segoe UI", 14, "bold"),
                padding=10,
            ).pack()

            notebook = ttk.Notebook(dialog)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            tab_basic = ttk.Frame(notebook, padding=10)
            notebook.add(tab_basic, text="Basic")

            tab_face = ttk.Frame(notebook, padding=10)
            notebook.add(tab_face, text="Facial Structure")

            tab_colors = ttk.Frame(notebook, padding=10)
            notebook.add(tab_colors, text="Colors & Cosmetics")

            def create_scrollable_text(parent):
                text_frame = ttk.Frame(parent)
                text_frame.pack(fill=tk.BOTH, expand=True)

                scrollbar = ttk.Scrollbar(text_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

                text = tk.Text(
                    text_frame,
                    font=("Consolas", 9),
                    wrap=tk.WORD,
                    yscrollcommand=scrollbar.set,
                )
                text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.config(command=text.yview)

                return text

            text_basic = create_scrollable_text(tab_basic)
            text_face = create_scrollable_text(tab_face)
            text_colors = create_scrollable_text(tab_colors)

            body_type_value = preset.get_body_type()
            body_type = "Type A" if body_type_value == 0 else "Type B"

            basic_info = [
                "BASIC INFORMATION",
                "=" * 50,
                f"Body Type: {body_type}",
                f"Face Model: {preset.face_model}",
                f"Hair Model: {preset.hair_model}",
                f"Eyebrow Model: {preset.eyebrow_model}",
                f"Beard Model: {preset.beard_model}",
                f"Eyepatch Model: {preset.eyepatch_model}",
                "",
                "BODY PROPORTIONS",
                "=" * 50,
                f"Head Size: {preset.head_size}",
                f"Chest Size: {preset.chest_size}",
                f"Abdomen Size: {preset.abdomen_size}",
                f"Arms Size: {preset.arms_size}",
                f"Legs Size: {preset.legs_size}",
            ]

            facial_structure = [
                "FACIAL STRUCTURE",
                "=" * 50,
                f"Apparent Age: {preset.apparent_age}",
                f"Facial Aesthetic: {preset.facial_aesthetic}",
                f"Form Emphasis: {preset.form_emphasis}",
                "",
                "Brow & Cheekbone:",
                f"  Brow Ridge Height: {preset.brow_ridge_height}",
                f"  Inner Brow Ridge: {preset.inner_brow_ridge}",
                f"  Outer Brow Ridge: {preset.outer_brow_ridge}",
                f"  Cheekbone Height: {preset.cheekbone_height}",
                f"  Cheekbone Depth: {preset.cheekbone_depth}",
                f"  Cheekbone Width: {preset.cheekbone_width}",
                f"  Cheeks: {preset.cheeks}",
                "",
                "Chin:",
                f"  Chin Tip Position: {preset.chin_tip_position}",
                f"  Chin Length: {preset.chin_length}",
                f"  Chin Protrusion: {preset.chin_protrusion}",
                f"  Chin Size: {preset.chin_size}",
                f"  Chin Width: {preset.chin_width}",
                "",
                "Eyes:",
                f"  Eye Position: {preset.eye_position}",
                f"  Eye Size: {preset.eye_size}",
                f"  Eye Slant: {preset.eye_slant}",
                f"  Eye Spacing: {preset.eye_spacing}",
                "",
                "Nose:",
                f"  Nose Size: {preset.nose_size}",
                f"  Nose Position: {preset.nose_position}",
                f"  Nose Tip Height: {preset.nose_tip_height}",
                f"  Nose Protrusion: {preset.nose_protrusion}",
                f"  Nose Bridge Height: {preset.nose_bridge_height}",
                f"  Nose Bridge Width: {preset.nose_bridge_width}",
                "",
                "Mouth:",
                f"  Lip Shape: {preset.lip_shape}",
                f"  Lip Size: {preset.lip_size}",
                f"  Mouth Width: {preset.mouth_width}",
                f"  Mouth Position: {preset.mouth_position}",
            ]

            colors_info = [
                "SKIN & COLORS",
                "=" * 50,
                f"Skin Color RGB: ({preset.skin_color_r}, {preset.skin_color_g}, {preset.skin_color_b})",
                f"Skin Luster: {preset.skin_luster}",
                f"Pores: {preset.pores}",
                f"Stubble: {preset.stubble}",
                "",
                "Dark Circles:",
                f"  Intensity: {preset.dark_circles}",
                f"  Color RGB: ({preset.dark_circle_color_r}, {preset.dark_circle_color_g}, {preset.dark_circle_color_b})",
                "",
                "Cheeks:",
                f"  Intensity: {preset.cheeks_color_intensity}",
                f"  Color RGB: ({preset.cheek_color_r}, {preset.cheek_color_g}, {preset.cheek_color_b})",
                "",
                "Eye Liner:",
                f"  Intensity: {preset.eye_liner}",
                f"  Color RGB: ({preset.eye_liner_color_r}, {preset.eye_liner_color_g}, {preset.eye_liner_color_b})",
                "",
                "Lips:",
                f"  Intensity: {preset.lip_stick}",
                f"  Color RGB: ({preset.lip_stick_color_r}, {preset.lip_stick_color_g}, {preset.lip_stick_color_b})",
                "",
                "Hair:",
                f"  Color RGB: ({preset.hair_color_r}, {preset.hair_color_g}, {preset.hair_color_b})",
                f"  Luster: {preset.luster}",
                f"  Root Darkness: {preset.hair_root_darkness}",
                f"  White Hairs: {preset.white_hairs}",
                "",
                "Eyes:",
                f"  Right Iris RGB: ({preset.right_iris_color_r}, {preset.right_iris_color_g}, {preset.right_iris_color_b})",
                f"  Left Iris RGB: ({preset.left_iris_color_r}, {preset.left_iris_color_g}, {preset.left_iris_color_b})",
                f"  Right Clouding: {preset.right_eye_clouding}",
                f"  Left Clouding: {preset.left_eye_clouding}",
                f"  Right White RGB: ({preset.right_eye_white_color_r}, {preset.right_eye_white_color_g}, {preset.right_eye_white_color_b})",
                f"  Left White RGB: ({preset.left_eye_white_color_r}, {preset.left_eye_white_color_g}, {preset.left_eye_white_color_b})",
            ]

            text_basic.insert("1.0", "\n".join(basic_info))
            text_basic.config(state="disabled")

            text_face.insert("1.0", "\n".join(facial_structure))
            text_face.config(state="disabled")

            text_colors.insert("1.0", "\n".join(colors_info))
            text_colors.config(state="disabled")

            button_frame = ttk.Frame(dialog, padding=10)
            button_frame.pack(fill=tk.X)

            ttk.Button(
                button_frame,
                text="Close",
                command=dialog.destroy,
                width=15,
                style="Accent.TButton",
            ).pack(side=tk.RIGHT)

            dialog.deiconify()
            dialog.lift()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to view preset:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def export_presets(self):
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        output_path = filedialog.asksaveasfilename(
            title="Export Presets",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )

        if output_path:
            try:
                count = self.save_file.export_presets(output_path)
                messagebox.showinfo("Success", f"Exported {count} preset(s) to JSON")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed:\n{str(e)}")

    def import_preset_from_json(self):
        """Import preset from external JSON file"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        json_path = filedialog.askopenfilename(
            title="Select Preset JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if not json_path:
            return

        try:
            import json

            with open(json_path) as f:
                data = json.load(f)

            # Support both formats: direct list or {'presets': [...]}
            if isinstance(data, dict) and "presets" in data:
                presets = data["presets"]
            elif isinstance(data, list):
                presets = data
            else:
                messagebox.showerror("Error", "Invalid JSON file format")
                return

            if not presets:
                messagebox.showerror("Error", "No presets found in JSON file")
                return

            dialog = tk.Toplevel(self.root)
            dialog.title("Import from JSON")
            dialog.geometry("550x250")
            dialog.grab_set()

            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"550x250+{x}+{y}")

            frame = ttk.Frame(dialog, padding=20)
            frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(
                frame,
                text=f"Import from: {os.path.basename(json_path)}",
                font=("Segoe UI", 11, "bold"),
            ).grid(row=0, column=0, columnspan=3, pady=(0, 15))

            ttk.Label(frame, text="Select Preset from JSON:").grid(
                row=1, column=0, sticky=tk.W, pady=5
            )

            preset_var = tk.StringVar()
            preset_options = []
            for i, preset_entry in enumerate(presets):
                slot = preset_entry.get("slot", i)
                preset_data = preset_entry.get("data", {})
                body_type = (
                    "Type A" if preset_data.get("body_type", 0) == 0 else "Type B"
                )
                preset_options.append(
                    f"Preset {i + 1} (Original Slot {slot + 1}, {body_type})"
                )

            preset_combo = ttk.Combobox(
                frame,
                textvariable=preset_var,
                values=preset_options,
                state="readonly",
                width=40,
            )
            preset_combo.grid(row=1, column=1, columnspan=2, padx=5)
            preset_combo.current(0)

            ttk.Label(frame, text="Destination Slot (1-15):").grid(
                row=2, column=0, sticky=tk.W, pady=5
            )

            dest_slot_var = tk.StringVar(value="1")
            dest_slot_entry = ttk.Entry(frame, textvariable=dest_slot_var, width=10)
            dest_slot_entry.grid(row=2, column=1, sticky=tk.W, padx=5)

            def do_import():
                try:
                    preset_index = preset_combo.current()
                    dest_slot = int(dest_slot_var.get())

                    if dest_slot < 1 or dest_slot > 15:
                        messagebox.showerror("Error", "Slot must be between 1 and 15")
                        return

                    success = self.save_file.import_preset_from_json(
                        json_path, preset_index, dest_slot - 1
                    )

                    if success:
                        from er_save_manager.backup.manager import BackupManager

                        manager = BackupManager(self.save_path)
                        manager.create_backup(
                            description=f"before_preset_import_slot_{dest_slot}",
                            operation="import_preset",
                            save=self.save_file,
                        )

                        self.save_file.to_file(self.save_path)
                        self.load_save()

                        messagebox.showinfo(
                            "Success",
                            f"Preset imported to slot {dest_slot}!\n\n"
                            "Backup saved to backup manager.",
                        )
                        dialog.destroy()
                    else:
                        messagebox.showerror(
                            "Error", "Failed to import preset from JSON"
                        )

                except ValueError:
                    messagebox.showerror(
                        "Error", "Invalid slot number - must be an integer (1-15)"
                    )
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to import:\n{str(e)}")
                    import traceback

                    traceback.print_exc()

            button_frame = ttk.Frame(frame)
            button_frame.grid(row=3, column=0, columnspan=3, pady=(15, 0))

            ttk.Button(
                button_frame,
                text="Import",
                command=do_import,
                width=15,
                style="Accent.TButton",
            ).pack(side=tk.LEFT, padx=5)

            ttk.Button(
                button_frame,
                text="Cancel",
                command=dialog.destroy,
                width=15,
                style="Accent.TButton",
            ).pack(side=tk.LEFT, padx=5)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def apply_preset_to_character(self):
        """Import preset to character slot"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        selection = self.preset_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a preset to import!")
            return

        preset_idx = selection[0]

        try:
            presets = self.save_file.get_character_presets()
            if not presets or preset_idx >= len(presets.presets):
                messagebox.showerror("Error", "Could not load preset data")
                return

            preset = presets.presets[preset_idx]

            if preset.is_empty():
                messagebox.showwarning(
                    "Empty Preset", f"Preset {preset_idx + 1} is empty"
                )
                return

            dialog = tk.Toplevel(self.root)
            dialog.title("Import Preset")
            dialog.geometry("400x300")
            dialog.grab_set()

            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"400x300+{x}+{y}")

            ttk.Label(
                dialog,
                text=f"Import Preset {preset_idx + 1}",
                font=("Segoe UI", 14, "bold"),
                padding=10,
            ).pack()

            body_type_value = preset.get_body_type()
            body_type = "Type A" if body_type_value == 0 else "Type B"

            info_frame = ttk.LabelFrame(dialog, text="Preset Info", padding=10)
            info_frame.pack(fill=tk.X, padx=10, pady=10)

            ttk.Label(info_frame, text=f"Body Type: {body_type}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"Face Model: {preset.face_model}").pack(
                anchor=tk.W
            )
            ttk.Label(info_frame, text=f"Hair Model: {preset.hair_model}").pack(
                anchor=tk.W
            )

            slot_frame = ttk.LabelFrame(
                dialog, text="Select Character Slot", padding=10
            )
            slot_frame.pack(fill=tk.X, padx=10, pady=10)

            ttk.Label(slot_frame, text="Import to slot:").pack(side=tk.LEFT, padx=5)

            slot_var = tk.IntVar(value=1)
            slot_combo = ttk.Combobox(
                slot_frame,
                textvariable=slot_var,
                values=list(range(1, 11)),
                state="readonly",
                width=5,
            )
            slot_combo.pack(side=tk.LEFT, padx=5)

            def do_import():
                target_slot = slot_var.get() - 1

                if not messagebox.askyesno(
                    "Confirm Import",
                    f"Apply preset {preset_idx + 1} to character in Slot {target_slot + 1}?\n\n"
                    "This will replace the character's appearance.\nA backup will be created.",
                ):
                    return

                try:
                    from io import BytesIO

                    from er_save_manager.backup.manager import BackupManager

                    manager = BackupManager(self.save_path)
                    manager.create_backup(
                        description=f"before_preset_import_slot_{target_slot + 1}",
                        operation="import_preset",
                        save=self.save_file,
                    )

                    slot = self.save_file.characters[target_slot]
                    if slot.is_empty():
                        messagebox.showerror(
                            "Error", f"Slot {target_slot + 1} is empty"
                        )
                        return

                    preset_bytes = BytesIO()
                    preset.write(preset_bytes)
                    preset_data = preset_bytes.getvalue()

                    if len(preset_data) != 0x130:
                        raise RuntimeError(
                            f"Preset size mismatch: {len(preset_data)} != 0x130"
                        )

                    slot_offset = self.save_file._slot_offsets[target_slot]
                    CHECKSUM_SIZE = 0x10

                    if not hasattr(slot, "face_data_offset"):
                        messagebox.showerror(
                            "Error",
                            "Face data offset not tracked.\n"
                            "Parser needs to track face_data_offset for this feature.",
                        )
                        return

                    face_offset = slot_offset + CHECKSUM_SIZE + slot.face_data_offset

                    preset_face_data = preset_data[0x20:]
                    if len(preset_face_data) < 0x12F:
                        raise RuntimeError(
                            f"Preset face data too short: {len(preset_face_data)}"
                        )
                    face_data_size = 0x12F

                    self.ensure_raw_data_mutable()
                    self.save_file._raw_data[
                        face_offset : face_offset + face_data_size
                    ] = preset_face_data[:face_data_size]

                    self.save_file.recalculate_checksums()
                    self.save_file.to_file(self.save_path)

                    self.load_save()
                    dialog.destroy()

                    messagebox.showinfo(
                        "Success",
                        f"Preset {preset_idx + 1} applied to Slot {target_slot + 1}!\n\n"
                        "Backup saved to backup manager.",
                    )

                except Exception as e:
                    messagebox.showerror("Error", f"Failed to import preset:\n{str(e)}")
                    import traceback

                    traceback.print_exc()

            button_frame = ttk.Frame(dialog, padding=10)
            button_frame.pack(fill=tk.X)

            ttk.Button(
                button_frame,
                text="Import",
                command=do_import,
                width=15,
                style="Accent.TButton",
            ).pack(side=tk.LEFT, padx=5)

            ttk.Button(
                button_frame,
                text="Cancel",
                command=dialog.destroy,
                width=15,
                style="Accent.TButton",
            ).pack(side=tk.RIGHT, padx=5)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to prepare import:\n{str(e)}")
            import traceback

            traceback.print_exc()

    # World operations (stubs)
    def load_world_state(self):
        messagebox.showinfo("World", "Load world state not implemented yet")

    def teleport_character(self, location):
        """Teleport character to a safe location"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.world_slot_var.get() - 1

        if not messagebox.askyesno(
            "Confirm Teleport",
            f"Teleport character in Slot {slot_idx + 1} to {location.title()}?\n\nA backup will be created.",
        ):
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.fixes.teleport import TeleportFix

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_teleport_to_{location}_slot_{slot_idx + 1}",
                operation=f"teleport_to_{location}",
                save=self.save_file,
            )

            teleport = TeleportFix(location)
            result = teleport.apply(self.save_file, slot_idx)

            if result.applied:
                self.save_file.recalculate_checksums()
                self.save_file.to_file(self.save_path)
                self.load_save()

                details = "\n".join(result.details) if result.details else ""
                messagebox.showinfo(
                    "Success",
                    f"{result.description}\n\n{details}\n\nBackup saved to backup manager.",
                )
            else:
                messagebox.showwarning("Not Applied", result.description)

        except Exception as e:
            messagebox.showerror("Error", f"Teleport failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    # Advanced operations
    def validate_save(self):
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        messagebox.showinfo("Validation", "Save validation not implemented yet")

    def recalculate_checksums(self):
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        if not messagebox.askyesno(
            "Confirm", "Recalculate all checksums?\n\nA backup will be created."
        ):
            return

        try:
            from er_save_manager.backup.manager import BackupManager

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description="before_checksum_recalc",
                operation="recalculate_checksums",
                save=self.save_file,
            )

            self.save_file.recalculate_checksums()
            self.save_file.to_file(self.save_path)

            messagebox.showinfo(
                "Success",
                "Checksums recalculated!\n\nBackup saved to backup manager.",
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to recalculate:\n{str(e)}")

    def show_backup_manager(self):
        """Show backup manager window"""
        if not self.save_file or not self.save_path:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        try:
            from er_save_manager.backup.manager import BackupManager

            manager = BackupManager(self.save_path)

            dialog = tk.Toplevel(self.root)
            dialog.title("Backup Manager")
            dialog.geometry("800x600")
            dialog.grab_set()

            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"800x600+{x}+{y}")

            ttk.Label(
                dialog,
                text="Backup Manager",
                font=("Segoe UI", 14, "bold"),
                padding=10,
            ).pack()

            list_frame = ttk.LabelFrame(dialog, text="Backups", padding=10)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            columns = ("timestamp", "operation", "description", "size")
            tree = ttk.Treeview(
                list_frame, columns=columns, show="tree headings", height=15
            )

            tree.heading("#0", text="Filename")
            tree.heading("timestamp", text="Timestamp")
            tree.heading("operation", text="Operation")
            tree.heading("description", text="Description")
            tree.heading("size", text="Size")

            tree.column("#0", width=200)
            tree.column("timestamp", width=150)
            tree.column("operation", width=150)
            tree.column("description", width=200)
            tree.column("size", width=80)

            scrollbar = ttk.Scrollbar(
                list_frame, orient=tk.VERTICAL, command=tree.yview
            )
            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            def refresh_list():
                tree.delete(*tree.get_children())
                backups = manager.list_backups()
                for backup in backups:
                    timestamp = (
                        backup.timestamp.split("T")[0]
                        + " "
                        + backup.timestamp.split("T")[1][:8]
                    )
                    size_mb = f"{backup.file_size / (1024 * 1024):.1f} MB"
                    tree.insert(
                        "",
                        tk.END,
                        text=backup.filename,
                        values=(
                            timestamp,
                            backup.operation,
                            backup.description,
                            size_mb,
                        ),
                    )

            refresh_list()

            button_frame = ttk.Frame(dialog, padding=10)
            button_frame.pack(fill=tk.X)

            def create_backup():
                desc = tk.simpledialog.askstring(
                    "Create Backup",
                    "Enter backup description (optional):",
                    parent=dialog,
                )
                if desc is not None:
                    try:
                        manager.create_backup(
                            description=desc or "manual",
                            operation="manual_backup",
                            save=self.save_file,
                        )
                        refresh_list()
                        messagebox.showinfo("Success", "Backup created successfully!")
                    except Exception as e:
                        messagebox.showerror(
                            "Error", f"Failed to create backup:\n{str(e)}"
                        )

            def restore_backup():
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning(
                        "No Selection", "Please select a backup to restore!"
                    )
                    return

                item = tree.item(selection[0])
                backup_name = item["text"]

                if not messagebox.askyesno(
                    "Confirm Restore",
                    f"Restore backup '{backup_name}'?\n\nCurrent save will be backed up first.",
                ):
                    return

                try:
                    manager.restore_backup(backup_name)
                    self.load_save()
                    refresh_list()
                    messagebox.showinfo("Success", "Backup restored successfully!")
                except Exception as e:
                    messagebox.showerror(
                        "Error", f"Failed to restore backup:\n{str(e)}"
                    )

            def delete_backup():
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning(
                        "No Selection", "Please select a backup to delete!"
                    )
                    return

                item = tree.item(selection[0])
                backup_name = item["text"]

                if not messagebox.askyesno(
                    "Confirm Delete",
                    f"Delete backup '{backup_name}'?\n\nThis cannot be undone.",
                ):
                    return

                try:
                    manager.delete_backup(backup_name)
                    refresh_list()
                    messagebox.showinfo("Success", "Backup deleted successfully!")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete backup:\n{str(e)}")

            def view_details():
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning(
                        "No Selection", "Please select a backup to view!"
                    )
                    return

                item = tree.item(selection[0])
                backup_name = item["text"]
                info = manager.get_backup_info(backup_name)

                if info:
                    details = []
                    details.append(f"Filename: {info.filename}")
                    details.append(f"Timestamp: {info.timestamp}")
                    details.append(f"Operation: {info.operation}")
                    details.append(f"Description: {info.description}")
                    details.append(f"Size: {info.file_size / (1024 * 1024):.2f} MB")

                    if info.character_summary:
                        details.append("\nCharacters:")
                        for char in info.character_summary:
                            details.append(
                                f"  Slot {char['slot']}: {char['name']} (Lv.{char['level']})"
                            )

                    messagebox.showinfo("Backup Details", "\n".join(details))

            ttk.Button(
                button_frame,
                text="Create Backup",
                command=create_backup,
                width=15,
                style="Accent.TButton",
            ).pack(side=tk.LEFT, padx=5)

            ttk.Button(
                button_frame,
                text="Restore",
                command=restore_backup,
                width=15,
                style="Accent.TButton",
            ).pack(side=tk.LEFT, padx=5)

            ttk.Button(
                button_frame,
                text="View Details",
                command=view_details,
                width=15,
                style="Accent.TButton",
            ).pack(side=tk.LEFT, padx=5)

            ttk.Button(
                button_frame,
                text="Delete",
                command=delete_backup,
                width=15,
                style="Accent.TButton",
            ).pack(side=tk.LEFT, padx=5)

            ttk.Button(
                button_frame,
                text="Refresh",
                command=refresh_list,
                width=15,
                style="Accent.TButton",
            ).pack(side=tk.LEFT, padx=5)

            ttk.Button(
                button_frame,
                text="Close",
                command=dialog.destroy,
                width=15,
                style="Accent.TButton",
            ).pack(side=tk.RIGHT, padx=5)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open backup manager:\n{str(e)}")
            import traceback

            traceback.print_exc()

    # Character Management methods (transfer, copy, delete)
    def update_char_operation_panel(self):
        """Update the operation panel based on selected operation"""
        # Clear existing widgets
        for widget in self.char_ops_panel.winfo_children():
            widget.destroy()

        # Get internal operation value from display name
        display_name = self.char_operation_var.get()
        operation = self.operation_map.get(display_name, "copy")

        if operation == "copy":
            self.setup_copy_panel()
        elif operation == "transfer":
            self.setup_transfer_panel()
        elif operation == "swap":
            self.setup_swap_panel()
        elif operation == "export":
            self.setup_export_panel()
        elif operation == "import":
            self.setup_import_panel()
        elif operation == "delete":
            self.setup_delete_panel()

    def setup_copy_panel(self):
        """Setup copy operation panel"""
        ttk.Label(
            self.char_ops_panel,
            text="Copy a character from one slot to another in the same save file",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=10)

        controls = ttk.Frame(self.char_ops_panel)
        controls.pack(fill=tk.X, pady=10)

        ttk.Label(controls, text="From Slot:").pack(side=tk.LEFT, padx=5)
        self.copy_from_var = tk.IntVar(value=1)
        ttk.Combobox(
            controls,
            textvariable=self.copy_from_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(controls, text="To Slot:").pack(side=tk.LEFT, padx=15)
        self.copy_to_var = tk.IntVar(value=2)
        ttk.Combobox(
            controls,
            textvariable=self.copy_to_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            controls,
            text="Copy Character",
            command=self.copy_character_slot,
            style="Accent.TButton",
            width=20,
        ).pack(side=tk.LEFT, padx=20)

    def setup_transfer_panel(self):
        """Setup transfer operation panel"""
        ttk.Label(
            self.char_ops_panel,
            text="Transfer a character to a different save file",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=10)

        controls = ttk.Frame(self.char_ops_panel)
        controls.pack(fill=tk.X, pady=10)

        ttk.Label(controls, text="From Slot:").pack(side=tk.LEFT, padx=5)
        self.transfer_from_var = tk.IntVar(value=1)
        ttk.Combobox(
            controls,
            textvariable=self.transfer_from_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            controls,
            text="Select Target Save...",
            command=self.transfer_character,
            style="Accent.TButton",
            width=25,
        ).pack(side=tk.LEFT, padx=20)

    def setup_swap_panel(self):
        """Setup swap operation panel"""
        ttk.Label(
            self.char_ops_panel,
            text="Exchange two character slots",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=10)

        controls = ttk.Frame(self.char_ops_panel)
        controls.pack(fill=tk.X, pady=10)

        ttk.Label(controls, text="Slot A:").pack(side=tk.LEFT, padx=5)
        self.swap_a_var = tk.IntVar(value=1)
        ttk.Combobox(
            controls,
            textvariable=self.swap_a_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(controls, text="Slot B:").pack(side=tk.LEFT, padx=15)
        self.swap_b_var = tk.IntVar(value=2)
        ttk.Combobox(
            controls,
            textvariable=self.swap_b_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            controls,
            text="Swap Slots",
            command=self.swap_character_slots,
            style="Accent.TButton",
            width=20,
        ).pack(side=tk.LEFT, padx=20)

    def setup_export_panel(self):
        """Setup export operation panel"""
        ttk.Label(
            self.char_ops_panel,
            text="Save character to a standalone .erc file for backup or sharing",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=10)

        controls = ttk.Frame(self.char_ops_panel)
        controls.pack(fill=tk.X, pady=10)

        ttk.Label(controls, text="Slot:").pack(side=tk.LEFT, padx=5)
        self.export_slot_var = tk.IntVar(value=1)
        ttk.Combobox(
            controls,
            textvariable=self.export_slot_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            controls,
            text="Export Character...",
            command=self.export_character,
            style="Accent.TButton",
            width=25,
        ).pack(side=tk.LEFT, padx=20)

    def setup_import_panel(self):
        """Setup import operation panel"""
        ttk.Label(
            self.char_ops_panel,
            text="Load a character from a .erc file into a slot",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=10)

        controls = ttk.Frame(self.char_ops_panel)
        controls.pack(fill=tk.X, pady=10)

        ttk.Label(controls, text="To Slot:").pack(side=tk.LEFT, padx=5)
        self.import_slot_var = tk.IntVar(value=1)
        ttk.Combobox(
            controls,
            textvariable=self.import_slot_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            controls,
            text="Import Character...",
            command=self.import_character,
            style="Accent.TButton",
            width=25,
        ).pack(side=tk.LEFT, padx=20)

    def setup_delete_panel(self):
        """Setup delete operation panel"""
        ttk.Label(
            self.char_ops_panel,
            text="Clear a character slot (creates backup)",
            font=("Segoe UI", 10),
            foreground="red",
        ).pack(anchor=tk.W, pady=10)

        controls = ttk.Frame(self.char_ops_panel)
        controls.pack(fill=tk.X, pady=10)

        ttk.Label(controls, text="Slot:").pack(side=tk.LEFT, padx=5)
        self.delete_slot_var = tk.IntVar(value=1)
        ttk.Combobox(
            controls,
            textvariable=self.delete_slot_var,
            values=list(range(1, 11)),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            controls,
            text="Delete Character",
            command=self.delete_character_slot,
            width=20,
        ).pack(side=tk.LEFT, padx=20)

    def copy_character_slot(self):
        """Copy character from one slot to another"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        from_slot = self.copy_from_var.get() - 1
        to_slot = self.copy_to_var.get() - 1

        if from_slot == to_slot:
            messagebox.showerror(
                "Error", "Source and destination slots must be different!"
            )
            return

        from_char = self.save_file.characters[from_slot]
        to_char = self.save_file.characters[to_slot]

        if from_char.is_empty():
            messagebox.showerror("Error", f"Slot {from_slot + 1} is empty!")
            return

        from_name = from_char.get_character_name()

        if not to_char.is_empty():
            to_name = to_char.get_character_name()
            if not messagebox.askyesno(
                "Overwrite?",
                f"Slot {to_slot + 1} contains '{to_name}'.\n\nOverwrite with '{from_name}'?",
            ):
                return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.transfer.character_ops import CharacterOperations

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_copy_{from_name}_slot{from_slot + 1}_to_slot{to_slot + 1}",
                operation="copy_character",
                save=self.save_file,
            )

            # Copy character data
            CharacterOperations.copy_slot(self.save_file, from_slot, to_slot)

            # Recalculate checksums
            self.save_file.recalculate_checksums()

            # Save to file
            self.save_file.to_file(self.save_path)

            # Reload
            self.load_save()

            messagebox.showinfo(
                "Success",
                f"Character '{from_name}' copied from Slot {from_slot + 1} to Slot {to_slot + 1}!\n\n"
                f"Backup created in backup manager.",
            )

        except Exception as e:
            messagebox.showerror("Error", f"Copy failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def transfer_character(self):
        """Transfer character to another save file"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        from_slot = self.transfer_from_var.get() - 1
        from_char = self.save_file.characters[from_slot]

        if from_char.is_empty():
            messagebox.showerror("Error", f"Slot {from_slot + 1} is empty!")
            return

        from_name = from_char.get_character_name()

        # Select target save file
        from tkinter import filedialog

        # Default to EldenRing save directory
        default_dir = self.default_save_path
        if not default_dir.exists():
            default_dir = Path.home()

        target_path = filedialog.askopenfilename(
            title="Select Target Save File",
            initialdir=str(default_dir),
            filetypes=[("Save Files", "*.sl2 *.co2"), ("All Files", "*.*")],
        )

        if not target_path:
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.transfer.character_ops import CharacterOperations

            # Load target save
            target_save = Save.from_file(target_path)

            # Ask which slot in target
            slot_dialog = tk.Toplevel(self.root)
            slot_dialog.title("Select Target Slot")
            slot_dialog.geometry("400x300")
            slot_dialog.transient(self.root)
            slot_dialog.grab_set()

            ttk.Label(
                slot_dialog,
                text=f"Transfer '{from_name}' to which slot?",
                font=("Segoe UI", 12, "bold"),
            ).pack(pady=15)

            # Show target slots
            slots_frame = ttk.Frame(slot_dialog, padding=10)
            slots_frame.pack(fill=tk.BOTH, expand=True)

            selected_slot = tk.IntVar(value=1)

            for i in range(10):
                char = target_save.characters[i]
                if char.is_empty():
                    status = "Empty"
                else:
                    status = f"{char.get_character_name()} (Lv {char.get_level()})"

                ttk.Radiobutton(
                    slots_frame,
                    text=f"Slot {i + 1}: {status}",
                    variable=selected_slot,
                    value=i + 1,
                ).pack(anchor=tk.W, pady=3)

            result = {"confirmed": False, "slot": 0}

            def confirm():
                result["confirmed"] = True
                result["slot"] = selected_slot.get() - 1
                slot_dialog.destroy()

            def cancel():
                slot_dialog.destroy()

            btn_frame = ttk.Frame(slot_dialog)
            btn_frame.pack(pady=10)

            ttk.Button(
                btn_frame,
                text="Transfer",
                command=confirm,
                style="Accent.TButton",
                width=15,
            ).pack(side=tk.LEFT, padx=5)

            ttk.Button(btn_frame, text="Cancel", command=cancel, width=15).pack(
                side=tk.LEFT, padx=5
            )

            self.root.wait_window(slot_dialog)

            if not result["confirmed"]:
                return

            to_slot = result["slot"]
            to_char = target_save.characters[to_slot]

            # Confirm overwrite if slot not empty
            if not to_char.is_empty():
                to_name = to_char.get_character_name()
                if not messagebox.askyesno(
                    "Overwrite?",
                    f"Target Slot {to_slot + 1} contains '{to_name}'.\n\nOverwrite with '{from_name}'?",
                ):
                    return

            # Backup source
            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_transfer_{from_name}_out_to_{Path(target_path).name}",
                operation="transfer_character_out",
                save=self.save_file,
            )

            # Backup target
            target_manager = BackupManager(target_path)
            target_manager.create_backup(
                description=f"before_transfer_{from_name}_in_from_{Path(self.save_path).name}",
                operation="transfer_character_in",
                save=target_save,
            )

            # Transfer character
            CharacterOperations.transfer_slot(
                self.save_file, from_slot, target_save, to_slot
            )

            # Recalculate checksums
            target_save.recalculate_checksums()

            # Save target file
            target_save.to_file(target_path)

            messagebox.showinfo(
                "Success",
                f"Character '{from_name}' transferred!\n\n"
                f"From: {Path(self.save_path).name} Slot {from_slot + 1}\n"
                f"To: {Path(target_path).name} Slot {to_slot + 1}\n\n"
                f"Backups created for both save files.",
            )

        except Exception as e:
            messagebox.showerror("Error", f"Transfer failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def delete_character_slot(self):
        """Delete character from slot"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot = self.delete_slot_var.get() - 1
        char = self.save_file.characters[slot]

        if char.is_empty():
            messagebox.showwarning("Empty Slot", f"Slot {slot + 1} is already empty!")
            return

        char_name = char.get_character_name()
        char_level = char.get_level()

        if not messagebox.askyesno(
            "Confirm Delete",
            f"DELETE '{char_name}' (Lv {char_level}) from Slot {slot + 1}?\n\n"
            f"This will clear the slot completely.\n"
            f"A backup will be created before deletion.",
        ):
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.transfer.character_ops import CharacterOperations

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_delete_{char_name}_lv{char_level}_slot{slot + 1}",
                operation="delete_character",
                save=self.save_file,
            )

            # Delete character
            CharacterOperations.delete_slot(self.save_file, slot)

            # Recalculate checksums
            self.save_file.recalculate_checksums()

            # Save to file
            self.save_file.to_file(self.save_path)

            # Reload
            self.load_save()

            messagebox.showinfo(
                "Success",
                f"Character '{char_name}' deleted from Slot {slot + 1}!\n\n"
                f"Backup created in backup manager.",
            )

        except Exception as e:
            messagebox.showerror("Error", f"Delete failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def swap_character_slots(self):
        """Swap two character slots"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_a = self.swap_a_var.get() - 1
        slot_b = self.swap_b_var.get() - 1

        if slot_a == slot_b:
            messagebox.showerror("Error", "Slots must be different!")
            return

        char_a = self.save_file.characters[slot_a]
        char_b = self.save_file.characters[slot_b]

        if char_a.is_empty() and char_b.is_empty():
            messagebox.showwarning("Empty Slots", "Both slots are empty!")
            return

        name_a = char_a.get_character_name() if not char_a.is_empty() else "Empty"
        name_b = char_b.get_character_name() if not char_b.is_empty() else "Empty"

        if not messagebox.askyesno(
            "Confirm Swap",
            f"Swap these slots?\n\n"
            f"Slot {slot_a + 1}: {name_a}\n"
            f"Slot {slot_b + 1}: {name_b}\n\n"
            f"A backup will be created.",
        ):
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.transfer.character_ops import CharacterOperations

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_swap_slot{slot_a + 1}_slot{slot_b + 1}",
                operation="swap_character",
                save=self.save_file,
            )

            # Swap slots
            CharacterOperations.swap_slots(self.save_file, slot_a, slot_b)

            # Recalculate checksums
            self.save_file.recalculate_checksums()

            # Save to file
            self.save_file.to_file(self.save_path)

            # Reload
            self.load_save()

            messagebox.showinfo(
                "Success",
                f"Slots swapped!\n\n"
                f"Slot {slot_a + 1}: {name_b}\n"
                f"Slot {slot_b + 1}: {name_a}",
            )

        except Exception as e:
            messagebox.showerror("Error", f"Swap failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def export_character(self):
        """Export character to .erc file"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot = self.export_slot_var.get() - 1
        char = self.save_file.characters[slot]

        if char.is_empty():
            messagebox.showwarning("Empty Slot", f"Slot {slot + 1} is empty!")
            return

        char_name = char.get_character_name()

        from tkinter import filedialog

        default_name = f"{char_name.replace(' ', '_')}_slot{slot + 1}.erc"

        export_path = filedialog.asksaveasfilename(
            title="Export Character",
            defaultextension=".erc",
            initialfile=default_name,
            filetypes=[("Character Files", "*.erc"), ("All Files", "*.*")],
        )

        if not export_path:
            return

        try:
            from er_save_manager.transfer.character_ops import CharacterOperations

            CharacterOperations.export_character(self.save_file, slot, export_path)

            messagebox.showinfo(
                "Success",
                f"Character '{char_name}' exported!\n\nFile: {Path(export_path).name}",
            )

        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def import_character(self):
        """Import character from .erc file"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        from tkinter import filedialog

        import_path = filedialog.askopenfilename(
            title="Import Character",
            filetypes=[("Character Files", "*.erc"), ("All Files", "*.*")],
        )

        if not import_path:
            return

        slot = self.import_slot_var.get() - 1
        char = self.save_file.characters[slot]

        if not char.is_empty():
            char_name = char.get_character_name()
            if not messagebox.askyesno(
                "Overwrite?",
                f"Slot {slot + 1} contains '{char_name}'.\n\nOverwrite with imported character?",
            ):
                return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.transfer.character_ops import CharacterOperations

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_import_to_slot{slot + 1}",
                operation="import_character",
                save=self.save_file,
            )

            # Import character
            imported_name = CharacterOperations.import_character(
                self.save_file, slot, import_path
            )

            # Recalculate checksums
            self.save_file.recalculate_checksums()

            # Save to file
            self.save_file.to_file(self.save_path)

            # Reload
            self.load_save()

            messagebox.showinfo(
                "Success",
                f"Character '{imported_name}' imported to Slot {slot + 1}!\n\n"
                f"Backup created in backup manager.",
            )

        except Exception as e:
            messagebox.showerror("Error", f"Import failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    # SteamID Patcher methods
    def patch_steamid(self):
        """Patch SteamID in save file"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        new_steamid = self.new_steamid_var.get().strip()

        if not new_steamid.isdigit() or len(new_steamid) != 17:
            messagebox.showerror("Invalid SteamID", "SteamID must be exactly 17 digits")
            return

        if not messagebox.askyesno(
            "Confirm Patch",
            f"Patch all character slots to SteamID: {new_steamid}?\n\nA backup will be created.",
        ):
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.fixes.steamid import SteamIDFix

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_steamid_patch_{new_steamid[:8]}",
                operation="patch_steamid",
                save=self.save_file,
            )

            # Apply SteamID fix to all slots
            patched_count = 0
            for slot_idx in range(10):
                fix = SteamIDFix(int(new_steamid))
                result = fix.apply(self.save_file, slot_idx)
                if result.applied:
                    patched_count += 1

            if patched_count > 0:
                self.save_file.recalculate_checksums()
                self.save_file.to_file(self.save_path)
                self.load_save()

                messagebox.showinfo(
                    "Success",
                    f"Patched {patched_count} character slot(s)!\n\nBackup saved to backup manager.",
                )
            else:
                messagebox.showinfo("No Changes", "No character slots needed patching")

        except Exception as e:
            messagebox.showerror("Error", f"SteamID patch failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def auto_detect_steamid(self):
        """Auto-detect SteamID from system"""
        try:
            import winreg

            # Try to get Steam user ID from registry
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam\ActiveProcess"
            )
            user_id, _ = winreg.QueryValueEx(key, "ActiveUser")
            winreg.CloseKey(key)

            if user_id and user_id != 0:
                # Convert to SteamID64 format
                steamid64 = 76561197960265728 + user_id
                self.new_steamid_var.set(str(steamid64))
                messagebox.showinfo("Detected", f"SteamID detected: {steamid64}")
            else:
                messagebox.showwarning(
                    "Not Found", "Could not detect SteamID. Please enter manually."
                )

        except Exception as e:
            messagebox.showwarning(
                "Detection Failed", f"Could not auto-detect SteamID:\n{str(e)}"
            )

    # Event Flags methods
    def load_event_flags(self):
        """Load event flags for selected character"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.eventflag_slot_var.get() - 1
        slot = self.save_file.characters[slot_idx]

        if slot.is_empty():
            messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
            return

        self.eventflag_text.config(state="normal")
        self.eventflag_text.delete("1.0", tk.END)
        self.eventflag_text.insert(
            "1.0",
            f"Event Flags for {slot.get_character_name()} (Slot {slot_idx + 1})\n\n",
        )
        self.eventflag_text.insert(tk.END, "Event flag viewing coming soon...\n\n")
        self.eventflag_text.insert(tk.END, "This feature will display:\n")
        self.eventflag_text.insert(tk.END, "• Boss defeats\n")
        self.eventflag_text.insert(tk.END, "• Grace sites unlocked\n")
        self.eventflag_text.insert(tk.END, "• Quest progression\n")
        self.eventflag_text.insert(tk.END, "• NPC states\n")
        self.eventflag_text.config(state="disabled")

    def fix_event_flag_issue(self, issue_type):
        """Fix specific event flag issues"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.eventflag_slot_var.get() - 1

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.fixes.event_flags import EventFlagFix

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_fix_{issue_type}_flags_slot_{slot_idx + 1}",
                operation=f"fix_event_flags_{issue_type}",
                save=self.save_file,
            )

            fix = EventFlagFix()
            result = fix.apply(self.save_file, slot_idx)

            if result.applied:
                self.save_file.recalculate_checksums()
                self.save_file.to_file(self.save_path)
                self.load_save()

                messagebox.showinfo(
                    "Success",
                    f"{result.description}\n\nBackup saved to backup manager.",
                )
            else:
                messagebox.showinfo("No Changes", "No issues were detected or fixed")

        except Exception as e:
            messagebox.showerror("Error", f"Fix failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    # Gestures & Regions methods
    def load_gestures_regions(self):
        """Load gestures and regions for selected character"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.gesture_slot_var.get() - 1
        slot = self.save_file.characters[slot_idx]

        if slot.is_empty():
            messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
            return

        # Gestures
        self.gestures_text.config(state="normal")
        self.gestures_text.delete("1.0", tk.END)
        self.gestures_text.insert(
            "1.0", f"Gestures for {slot.get_character_name()}\n\n"
        )

        if hasattr(slot, "gestures") and slot.gestures:
            self.gestures_text.insert(
                tk.END,
                f"Total gestures unlocked: {len([g for g in slot.gestures.gesture_ids if g > 0])}\n\n",
            )
            self.gestures_text.insert(tk.END, "Gesture IDs:\n")
            for i, gesture_id in enumerate(slot.gestures.gesture_ids):
                if gesture_id > 0:
                    self.gestures_text.insert(tk.END, f"  {i}: {gesture_id}\n")
        else:
            self.gestures_text.insert(tk.END, "No gesture data available")

        self.gestures_text.config(state="disabled")

        # Regions
        self.regions_text.config(state="normal")
        self.regions_text.delete("1.0", tk.END)
        self.regions_text.insert("1.0", f"Regions for {slot.get_character_name()}\n\n")

        if hasattr(slot, "regions") and slot.regions:
            self.regions_text.insert(
                tk.END, f"Total regions discovered: {slot.regions.count}\n\n"
            )
            self.regions_text.insert(tk.END, "Region IDs:\n")
            for i, region_id in enumerate(slot.regions.region_ids):
                if region_id > 0:
                    self.regions_text.insert(tk.END, f"  {i}: {region_id}\n")
        else:
            self.regions_text.insert(tk.END, "No region data available")

        self.regions_text.config(state="disabled")

    # Hex Editor methods
    def hex_goto_offset(self):
        """Jump to specific offset in hex view"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        offset_str = self.hex_offset_var.get().strip()
        try:
            if offset_str.startswith("0x"):
                offset = int(offset_str, 16)
            else:
                offset = int(offset_str)

            self.hex_display_at_offset(offset)

        except ValueError:
            messagebox.showerror(
                "Invalid Offset", "Please enter a valid hex offset (e.g., 0x1000)"
            )

    def hex_display_at_offset(self, offset=0, length=512):
        """Display hex data at offset"""
        if not self.save_file or not hasattr(self.save_file, "_raw_data"):
            return

        raw_data = self.save_file._raw_data
        max_offset = len(raw_data)

        if offset >= max_offset:
            messagebox.showerror(
                "Invalid Offset", f"Offset {offset} exceeds file size {max_offset}"
            )
            return

        end_offset = min(offset + length, max_offset)

        self.hex_text.config(state="normal")
        self.hex_text.delete("1.0", tk.END)

        # Display hex dump
        for i in range(offset, end_offset, 16):
            line_offset = f"{i:08X}: "
            hex_part = ""
            ascii_part = ""

            for j in range(16):
                if i + j < end_offset:
                    byte = raw_data[i + j]
                    hex_part += f"{byte:02X} "
                    ascii_part += chr(byte) if 32 <= byte < 127 else "."
                else:
                    hex_part += "   "
                    ascii_part += " "

                if j == 7:
                    hex_part += " "

            self.hex_text.insert(tk.END, f"{line_offset}{hex_part} {ascii_part}\n")

        self.hex_text.config(state="disabled")

    def hex_refresh(self):
        """Refresh hex view"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        self.hex_display_at_offset(0)

    def hex_save(self):
        """Save hex changes"""
        messagebox.showinfo(
            "Not Implemented",
            "Direct hex editing is not yet implemented.\n\n"
            "This is a read-only hex viewer for now.",
        )


def main():
    root = tk.Tk()
    SaveManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
