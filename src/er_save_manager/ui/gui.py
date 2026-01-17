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

from er_save_manager.parser import Save


class SaveManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Elden Ring Save Manager")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

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

        # Source save section
        source_frame = ttk.LabelFrame(
            self.tab_char_mgmt, text="Source Save File", padding=15
        )
        source_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(
            source_frame, text="Current save file loaded above", font=("Segoe UI", 10)
        ).pack(anchor=tk.W)

        # Operations section
        ops_frame = ttk.LabelFrame(self.tab_char_mgmt, text="Operations", padding=15)
        ops_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Copy character to another slot
        copy_frame = ttk.Frame(ops_frame)
        copy_frame.pack(fill=tk.X, pady=10)

        ttk.Label(
            copy_frame, text="Copy Character:", font=("Segoe UI", 11, "bold")
        ).pack(anchor=tk.W, pady=5)
        ttk.Label(
            copy_frame,
            text="Copy a character from one slot to another in the same save file",
        ).pack(anchor=tk.W)

        copy_controls = ttk.Frame(copy_frame)
        copy_controls.pack(fill=tk.X, pady=5)

        ttk.Label(copy_controls, text="From Slot:").pack(side=tk.LEFT, padx=5)
        self.copy_from_var = tk.IntVar(value=1)
        ttk.Combobox(
            copy_controls,
            textvariable=self.copy_from_var,
            values=list(range(1, 11)),
            width=5,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(copy_controls, text="To Slot:").pack(side=tk.LEFT, padx=10)
        self.copy_to_var = tk.IntVar(value=2)
        ttk.Combobox(
            copy_controls,
            textvariable=self.copy_to_var,
            values=list(range(1, 11)),
            width=5,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            copy_controls,
            text="Copy Character",
            command=self.copy_character_slot,
            width=18,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=10)

        ttk.Separator(ops_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

        # Transfer to another save file
        transfer_frame = ttk.Frame(ops_frame)
        transfer_frame.pack(fill=tk.X, pady=10)

        ttk.Label(
            transfer_frame,
            text="Transfer to Another Save:",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor=tk.W, pady=5)
        ttk.Label(
            transfer_frame, text="Copy a character to a different save file"
        ).pack(anchor=tk.W)

        transfer_controls = ttk.Frame(transfer_frame)
        transfer_controls.pack(fill=tk.X, pady=5)

        ttk.Label(transfer_controls, text="From Slot:").pack(side=tk.LEFT, padx=5)
        self.transfer_from_var = tk.IntVar(value=1)
        ttk.Combobox(
            transfer_controls,
            textvariable=self.transfer_from_var,
            values=list(range(1, 11)),
            width=5,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            transfer_controls,
            text="Select Target Save...",
            command=self.transfer_character,
            width=20,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=10)

        ttk.Separator(ops_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

        # Delete character
        delete_frame = ttk.Frame(ops_frame)
        delete_frame.pack(fill=tk.X, pady=10)

        ttk.Label(
            delete_frame, text="Delete Character:", font=("Segoe UI", 11, "bold")
        ).pack(anchor=tk.W, pady=5)
        ttk.Label(
            delete_frame,
            text="⚠️ Permanently delete a character slot (creates backup)",
            foreground="red",
        ).pack(anchor=tk.W)

        delete_controls = ttk.Frame(delete_frame)
        delete_controls.pack(fill=tk.X, pady=5)

        ttk.Label(delete_controls, text="Slot:").pack(side=tk.LEFT, padx=5)
        self.delete_slot_var = tk.IntVar(value=1)
        ttk.Combobox(
            delete_controls,
            textvariable=self.delete_slot_var,
            values=list(range(1, 11)),
            width=5,
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            delete_controls,
            text="Delete Character",
            command=self.delete_character_slot,
            width=18,
        ).pack(side=tk.LEFT, padx=10)

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
        ttk.Label(
            equipment_frame,
            text="Equipment editor coming soon",
            font=("Segoe UI", 11),
        ).pack(expand=True)

        # Info sub-tab
        info_frame = ttk.Frame(editor_notebook, padding=10)
        editor_notebook.add(info_frame, text="Info")
        ttk.Label(
            info_frame, text="Character info coming soon", font=("Segoe UI", 11)
        ).pack(expand=True)

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

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Stats fields
        self.stat_vars = {}

        stats_frame = ttk.LabelFrame(scrollable_frame, text="Attributes", padding=10)
        stats_frame.pack(fill=tk.X, pady=5)

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
            row = i // 2
            col = (i % 2) * 2

            ttk.Label(stats_frame, text=f"{label}:").grid(
                row=row, column=col, sticky=tk.W, padx=5, pady=5
            )

            var = tk.IntVar(value=0)
            self.stat_vars[key] = var
            ttk.Entry(stats_frame, textvariable=var, width=10).grid(
                row=row, column=col + 1, padx=5, pady=5
            )

        # Level and runes
        other_frame = ttk.LabelFrame(scrollable_frame, text="Level & Runes", padding=10)
        other_frame.pack(fill=tk.X, pady=5)

        ttk.Label(other_frame, text="Level:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.level_var = tk.IntVar(value=0)
        ttk.Entry(other_frame, textvariable=self.level_var, width=10).grid(
            row=0, column=1, padx=5, pady=5
        )

        ttk.Label(other_frame, text="Runes:").grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.runes_var = tk.IntVar(value=0)
        ttk.Entry(other_frame, textvariable=self.runes_var, width=15).grid(
            row=0, column=3, padx=5, pady=5
        )

        # HP/FP/Stamina
        resources_frame = ttk.LabelFrame(
            scrollable_frame, text="Health/FP/Stamina", padding=10
        )
        resources_frame.pack(fill=tk.X, pady=5)

        resources = [
            ("HP", "hp", "max_hp"),
            ("FP", "fp", "max_fp"),
            ("Stamina", "sp", "max_sp"),
        ]

        for i, (label, current_key, max_key) in enumerate(resources):
            ttk.Label(resources_frame, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=5
            )

            var_current = tk.IntVar(value=0)
            self.stat_vars[current_key] = var_current
            ttk.Entry(resources_frame, textvariable=var_current, width=10).grid(
                row=i, column=1, padx=5, pady=5
            )

            ttk.Label(resources_frame, text="/").grid(row=i, column=2, padx=2)

            var_max = tk.IntVar(value=0)
            self.stat_vars[max_key] = var_max
            ttk.Entry(resources_frame, textvariable=var_max, width=10).grid(
                row=i, column=3, padx=5, pady=5
            )

        # Apply buttons
        button_frame = ttk.Frame(scrollable_frame)
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
            from ..backup.manager import BackupManager

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
                from ..parser.world import DLC

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
                from ..backup.manager import BackupManager
                from ..fixes.teleport import TeleportFix

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
            from ..backup.manager import BackupManager

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
            from ..backup.manager import BackupManager

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

                    self.stat_vars["hp"].set(getattr(char, "hp", 0))
                    self.stat_vars["max_hp"].set(getattr(char, "max_hp", 0))
                    self.stat_vars["fp"].set(getattr(char, "fp", 0))
                    self.stat_vars["max_fp"].set(getattr(char, "max_fp", 0))
                    self.stat_vars["sp"].set(getattr(char, "sp", 0))
                    self.stat_vars["max_sp"].set(getattr(char, "max_sp", 0))

                    messagebox.showinfo(
                        "Loaded", f"Character stats loaded for Slot {slot_idx + 1}"
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

        if not messagebox.askyesno(
            "Confirm",
            f"Apply stat changes to Slot {slot_idx + 1}?\n\nA backup will be created.",
        ):
            return

        try:
            # Create backup
            from ..backup.manager import BackupManager

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

                char.hp = self.stat_vars["hp"].get()
                char.max_hp = self.stat_vars["max_hp"].get()
                char.fp = self.stat_vars["fp"].get()
                char.max_fp = self.stat_vars["max_fp"].get()
                char.sp = self.stat_vars["sp"].get()
                char.max_sp = self.stat_vars["max_sp"].get()

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

                    # Calculate absolute offset in save file
                    HEADER_SIZE = 0x300 if self.save_file.magic == b"BND4" else 0x6C
                    SLOT_SIZE = 0x280000
                    CHECKSUM_SIZE = 0x10

                    slot_start = HEADER_SIZE + (slot_idx * (SLOT_SIZE + CHECKSUM_SIZE))
                    abs_offset = (
                        slot_start + CHECKSUM_SIZE + slot.player_game_data_offset
                    )

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
                        from ..backup.manager import BackupManager

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

                    from ..backup.manager import BackupManager

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

                    HEADER_SIZE = 0x300 if self.save_file.magic == b"BND4" else 0x6C
                    SLOT_SIZE = 0x280000
                    CHECKSUM_SIZE = 0x10

                    slot_start = HEADER_SIZE + (
                        target_slot * (SLOT_SIZE + CHECKSUM_SIZE)
                    )

                    if not hasattr(slot, "face_data_offset"):
                        messagebox.showerror(
                            "Error",
                            "Face data offset not tracked.\n"
                            "Parser needs to track face_data_offset for this feature.",
                        )
                        return

                    face_offset = slot_start + CHECKSUM_SIZE + slot.face_data_offset

                    preset_face_data = preset_data[0x20:]
                    if len(preset_face_data) < 0x12F:
                        raise RuntimeError(
                            f"Preset face data too short: {len(preset_face_data)}"
                        )

                    face_data_size = 0x12F
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
            from ..backup.manager import BackupManager
            from ..fixes.teleport import TeleportFix

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
            from ..backup.manager import BackupManager

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
            from ..backup.manager import BackupManager

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

        if not to_char.is_empty():
            if not messagebox.askyesno(
                "Overwrite?",
                f"Slot {to_slot + 1} contains '{to_char.get_character_name()}'.\n\nOverwrite this character?",
            ):
                return

        try:
            from ..backup.manager import BackupManager

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_copy_slot_{from_slot + 1}_to_{to_slot + 1}",
                operation="copy_character",
                save=self.save_file,
            )

            # Copy character data
            # This is a placeholder - implement actual copy logic
            messagebox.showinfo(
                "Not Implemented",
                "Character copy functionality coming soon!\n\n"
                "This will copy all character data including:\n"
                "• Stats and level\n"
                "• Equipment and inventory\n"
                "• Quest progression\n"
                "• Gestures and regions",
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

        # Select target save file
        from tkinter import filedialog

        target_path = filedialog.askopenfilename(
            title="Select Target Save File",
            filetypes=[("Save Files", "*.sl2"), ("All Files", "*.*")],
        )

        if not target_path:
            return

        try:
            from ..backup.manager import BackupManager

            # Backup source
            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_transfer_slot_{from_slot + 1}_out",
                operation="transfer_character_out",
                save=self.save_file,
            )

            # Backup target
            target_manager = BackupManager(target_path)
            target_save = Save.from_file(target_path)
            target_manager.create_backup(
                description=f"before_transfer_slot_{from_slot + 1}_in",
                operation="transfer_character_in",
                save=target_save,
            )

            messagebox.showinfo(
                "Not Implemented",
                "Character transfer functionality coming soon!\n\n"
                "This will transfer the character to the target save file.",
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

        if not messagebox.askyesno(
            "Confirm Delete",
            f"⚠️ PERMANENTLY DELETE '{char_name}' from Slot {slot + 1}?\n\n"
            f"This cannot be undone (except via backup restore).\n\n"
            f"A backup will be created before deletion.",
        ):
            return

        try:
            from ..backup.manager import BackupManager

            manager = BackupManager(self.save_path)
            manager.create_backup(
                description=f"before_delete_slot_{slot + 1}_{char_name}",
                operation="delete_character",
                save=self.save_file,
            )

            # Delete character
            # This is a placeholder - implement actual delete logic
            messagebox.showinfo(
                "Not Implemented",
                "Character deletion functionality coming soon!\n\n"
                "This will clear the character slot completely.",
            )

        except Exception as e:
            messagebox.showerror("Error", f"Delete failed:\n{str(e)}")
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
            from ..backup.manager import BackupManager
            from ..fixes.steamid import SteamIDFix

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
            from ..backup.manager import BackupManager
            from ..fixes.event_flags import EventFlagFix

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
