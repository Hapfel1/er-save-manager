"""
Elden Ring Save Manager - Comprehensive GUI
Handles corruption fixes, preset management, character editing, and more.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..parser import Save


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

        # Tab 1: Quick Fix
        self.tab_quick_fix = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_quick_fix, text="Quick Fix")
        self.setup_quick_fix_tab()

        # Tab 2: Character Editor
        self.tab_character = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_character, text="Character Editor")
        self.setup_character_tab()

        # Tab 3: Appearance
        self.tab_appearance = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_appearance, text="Appearance")
        self.setup_appearance_tab()

        # Tab 4: World
        self.tab_world = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_world, text="World")
        self.setup_world_tab()

        # Tab 5: Advanced
        self.tab_advanced = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_advanced, text="Advanced")
        self.setup_advanced_tab()

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

    def setup_quick_fix_tab(self):
        """Quick Fix tab - similar to save fixer"""
        # Character selection
        char_frame = ttk.LabelFrame(
            self.tab_quick_fix, text="Select Character", padding="10"
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
        action_frame = ttk.LabelFrame(self.tab_quick_fix, text="Actions", padding="10")
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
                from ..fixes.teleport import TeleportFix

                backup_path = self.save_path + ".backup"
                shutil.copy2(self.save_path, backup_path)

                teleport = TeleportFix(location_var.get())
                result = teleport.apply(self.save_file, slot_idx)

                if result.applied:
                    self.save_file.recalculate_checksums()
                    self.save_file.to_file(self.save_path)
                    self.load_save()

                    details = "\n".join(result.details) if result.details else ""
                    messagebox.showinfo(
                        "Success",
                        f"{result.description}\n\n{details}\n\nBackup: {os.path.basename(backup_path)}",
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
            backup_path = self.save_path + ".backup"
            shutil.copy2(self.save_path, backup_path)

            # Apply fix using the existing corruption fix method
            was_fixed, fixes = self.save_file.fix_character_corruption(slot_idx)

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
                    f"Backup created: {os.path.basename(backup_path)}",
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
            backup_path = self.save_path + ".backup"
            shutil.copy2(self.save_path, backup_path)

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
                    + f"\n\nBackup: {os.path.basename(backup_path)}",
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
            backup_path = self.save_path + ".backup"
            shutil.copy2(self.save_path, backup_path)

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
                        f"Stats updated successfully!\n\nBackup: {os.path.basename(backup_path)}",
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
                f"  Luster: {preset.hair_luster}",
                f"  Root Darkness: {preset.hair_root_darkness}",
                f"  White Hairs: {preset.hair_white_hairs}",
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
                presets = json.load(f)

            if not isinstance(presets, list) or not presets:
                messagebox.showerror("Error", "Invalid JSON file format")
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
                        backup_path = self.save_path + ".backup"
                        shutil.copy2(self.save_path, backup_path)

                        self.save_file.to_file(self.save_path)
                        self.load_save()

                        messagebox.showinfo(
                            "Success",
                            f"Preset imported to slot {dest_slot}!\n\n"
                            f"Backup: {os.path.basename(backup_path)}",
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

                    backup_path = self.save_path + ".backup"
                    shutil.copy2(self.save_path, backup_path)

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
                        f"Backup: {os.path.basename(backup_path)}",
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
            from ..fixes.teleport import TeleportFix

            backup_path = self.save_path + ".backup"
            shutil.copy2(self.save_path, backup_path)

            teleport = TeleportFix(location)
            result = teleport.apply(self.save_file, slot_idx)

            if result.applied:
                self.save_file.recalculate_checksums()
                self.save_file.to_file(self.save_path)
                self.load_save()

                details = "\n".join(result.details) if result.details else ""
                messagebox.showinfo(
                    "Success",
                    f"{result.description}\n\n{details}\n\nBackup: {os.path.basename(backup_path)}",
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
            backup_path = self.save_path + ".backup"
            shutil.copy2(self.save_path, backup_path)

            self.save_file.recalculate_checksums()
            self.save_file.to_file(self.save_path)

            messagebox.showinfo(
                "Success",
                f"Checksums recalculated!\n\nBackup: {os.path.basename(backup_path)}",
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


def main():
    root = tk.Tk()
    SaveManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
