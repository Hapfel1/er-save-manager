"""
Main GUI Application
Modular Elden Ring Save Manager GUI
"""

import os
import subprocess
import sys
import threading
import tkinter as tk
from importlib import resources
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from er_save_manager.parser import Save
from er_save_manager.platform import PlatformUtils

# Import all modular components
from er_save_manager.ui.dialogs.character_details import CharacterDetailsDialog
from er_save_manager.ui.dialogs.save_selector import SaveSelectorDialog
from er_save_manager.ui.editors import (
    CharacterInfoEditor,
    EquipmentEditor,
    InventoryEditor,
    StatsEditor,
)
from er_save_manager.ui.settings import get_settings
from er_save_manager.ui.tabs import (
    AdvancedToolsTab,
    AppearanceTab,
    CharacterManagementTab,
    EventFlagsTab,
    GesturesRegionsTab,
    HexEditorTab,
    SaveInspectorTab,
    SettingsTab,
    SteamIDPatcherTab,
    WorldStateTab,
)
from er_save_manager.ui.theme import ThemeManager


class SaveManagerGUI:
    """Main GUI application for Elden Ring Save Manager"""

    def __init__(self, root):
        self.root = root
        self.root.title("Elden Ring Save Manager")
        self.root.geometry("1200x950")
        self.root.minsize(800, 700)

        # Set application icon
        try:
            # Detect if running as frozen/packaged executable
            if getattr(sys, "frozen", False):
                # Running as compiled executable
                if hasattr(sys, "_MEIPASS"):
                    # PyInstaller (Linux)
                    base_path = Path(sys._MEIPASS)
                else:
                    # cx_Freeze (Windows)
                    base_path = Path(sys.executable).parent
            else:
                # Running as script
                base_path = Path(__file__).parent.parent.parent

            icon_path = base_path / "resources" / "icon" / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
            else:
                # Fallback to PNG if ICO doesn't exist
                icon_png = base_path / "resources" / "icon" / "icon.png"
                if icon_png.exists():
                    from PIL import Image, ImageTk

                    icon_image = Image.open(icon_png)
                    icon_photo = ImageTk.PhotoImage(icon_image)
                    self.root.iconphoto(True, icon_photo)
        except Exception:
            pass

        # Initialize settings
        self.settings = get_settings()

        # Configure customtkinter appearance based on saved theme
        theme_name = self.settings.get("theme", "default")
        appearance = "dark" if theme_name == "dark" else "light"
        ctk.set_appearance_mode(appearance)

        # Try to load lavender theme from customtkinterthemes
        try:
            import customtkinterthemes as ctt

            theme_path = resources.files(ctt).joinpath("themes", "lavender.json")
            ctk.set_default_color_theme(theme_path)
        except Exception:
            ctk.set_default_color_theme("dark-blue")

        # Initialize theme manager for any remaining ttk widgets (during migration)
        self.theme_manager = ThemeManager(theme_name)

        # Configure style for legacy ttk widgets
        style = ttk.Style()
        style.theme_use("clam")
        self.theme_manager.apply_theme(style)

        # Configure background for root window
        self.root.configure(bg=self.theme_manager.get_color("bg"))

        # State
        self.default_save_path = Path(os.environ.get("APPDATA", "")) / "EldenRing"
        self.save_file = None
        self.save_path = None
        self.selected_slot = None
        self.selected_slot_index = -1  # Current selected character slot (0-9)

        # Lazy loading flags (track which tabs have been initialized with data)
        self.tabs_loaded = {
            "Save Inspector": False,
            "Appearance": False,
            "Advanced Tools": False,
            "SteamID Patcher": False,
            "Hex Editor": False,
            "Gestures": False,
        }

        # Status
        self.status_var = tk.StringVar(value="Ready")

        # Resize debouncing for performance
        self._resize_timer = None
        self._last_width = None
        self._last_height = None

        self.setup_ui()

        # Apply theme colors to tk widgets (non-ttk)
        self.theme_manager.apply_tk_widget_colors(self.root)

        # Bind resize event with debouncing
        self.root.bind("<Configure>", self._on_window_resize)

    def _on_window_resize(self, event=None):
        """Debounce window resize events to improve responsiveness"""
        if event is None:
            return

        # Only process if size actually changed (skip if just movement)
        width = event.width
        height = event.height

        if width == self._last_width and height == self._last_height:
            return

        self._last_width = width
        self._last_height = height

        # Cancel pending resize processing
        if self._resize_timer:
            self.root.after_cancel(self._resize_timer)

        # Delay actual processing to batch multiple resize events
        self._resize_timer = self.root.after(200, self._process_resize)

    def _process_resize(self):
        """Process pending resize - called after resize events stop"""
        self._resize_timer = None
        self.root.update_idletasks()

    def setup_ui(self):
        """Setup main UI structure with optimized layout"""
        # Use grid for main container - more efficient than pack
        self.root.grid_rowconfigure(0, weight=0)  # Title
        self.root.grid_rowconfigure(1, weight=0)  # File selection
        self.root.grid_rowconfigure(2, weight=1)  # Main content (tabs)
        self.root.grid_rowconfigure(3, weight=0)  # Status bar
        self.root.grid_columnconfigure(0, weight=1)

        # Title
        title_frame = ctk.CTkFrame(self.root, corner_radius=12)
        title_frame.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")

        ctk.CTkLabel(
            title_frame,
            text="Elden Ring Save Manager",
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(10, 2))

        ctk.CTkLabel(
            title_frame,
            text="Complete save editor, backup manager, and corruption fixer",
            font=("Segoe UI", 11),
        ).pack(pady=(0, 10))

        # File Selection
        file_frame = ctk.CTkFrame(self.root, corner_radius=12)
        file_frame.grid(row=1, column=0, padx=12, pady=10, sticky="ew")

        ctk.CTkLabel(
            file_frame,
            text="Step 1: Select Save File",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 4))

        self.file_path_var = tk.StringVar(value="")

        path_frame = ctk.CTkFrame(file_frame, corner_radius=8)
        path_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

        ctk.CTkEntry(path_frame, textvariable=self.file_path_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), pady=10
        )

        ctk.CTkButton(
            path_frame,
            text="Browse",
            command=self.browse_file,
            width=110,
        ).pack(side=tk.LEFT, padx=4, pady=10)

        ctk.CTkButton(
            path_frame,
            text="Auto-Find",
            command=self.auto_detect,
            width=110,
        ).pack(side=tk.LEFT, padx=4, pady=10)

        # Linux help button
        if PlatformUtils.is_linux():
            ttk.Button(
                path_frame,
                text="Linux Info",
                command=self.show_linux_steam_info_dialog,
                width=12,
            ).pack(side=tk.LEFT, padx=2)

        # Load button
        buttons_frame = ctk.CTkFrame(file_frame, corner_radius=8)
        buttons_frame.pack(fill=tk.X, pady=(6, 10), padx=12)

        ctk.CTkButton(
            buttons_frame,
            text="Load Save File",
            command=self.load_save,
            width=160,
        ).pack(side=tk.LEFT, padx=6, pady=10)

        ctk.CTkButton(
            buttons_frame,
            text="Backup Manager",
            command=self.show_backup_manager_standalone,
            width=160,
        ).pack(side=tk.LEFT, padx=6, pady=10)

        # Main content - tabbed interface (customtkinter)
        self.notebook = ctk.CTkTabview(
            self.root,
            width=1100,
            height=620,
            corner_radius=12,
            command=self._on_tab_changed,
        )
        self.notebook.grid(row=2, column=0, padx=12, pady=10, sticky="nsew")

        # Create all tabs
        self.create_tabs()

        # Status bar
        status_frame = ctk.CTkFrame(self.root, corner_radius=0)
        status_frame.grid(row=3, column=0, sticky="ew")

        ctk.CTkLabel(
            status_frame,
            textvariable=self.status_var,
            anchor="w",
            padx=8,
            pady=6,
        ).pack(fill=tk.X)

    def create_tabs(self):
        """Create all tabs with modular components"""

        # Tab 1: Save Inspector
        self.notebook.add("Save Inspector")
        tab_inspector = self.notebook.tab("Save Inspector")
        self.inspector_tab = SaveInspectorTab(
            tab_inspector,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
            self.show_character_details,
            self.on_slot_selected,
        )
        self.inspector_tab.setup_ui()

        # Tab 2: Character Management
        self.notebook.add("Character Management")
        tab_char_mgmt = self.notebook.tab("Character Management")
        self.char_mgmt_tab = CharacterManagementTab(
            tab_char_mgmt,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
        )
        self.char_mgmt_tab.setup_ui()

        # Tab 3: Character Editor
        self.notebook.add("Character Editor")
        tab_character = self.notebook.tab("Character Editor")
        self.setup_character_editor_tab(tab_character)

        # Tab 4: Appearance
        self.notebook.add("Appearance")
        tab_appearance = self.notebook.tab("Appearance")
        self.appearance_tab = AppearanceTab(
            tab_appearance,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
        )
        self.appearance_tab.setup_ui()

        # Tab 5: World State
        self.notebook.add("World State")
        tab_world = self.notebook.tab("World State")
        self.world_tab = WorldStateTab(
            tab_world,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
            lambda: self.selected_slot_index,
        )
        self.world_tab.setup_ui()

        # Tab 6: SteamID Patcher
        self.notebook.add("SteamID Patcher")
        tab_steamid = self.notebook.tab("SteamID Patcher")
        self.steamid_tab = SteamIDPatcherTab(
            tab_steamid, lambda: self.save_file, lambda: self.save_path, self.load_save
        )
        self.steamid_tab.setup_ui()

        # Tab 7: Event Flags
        self.notebook.add("Event Flags")
        tab_event_flags = self.notebook.tab("Event Flags")
        self.event_flags_tab = EventFlagsTab(
            tab_event_flags,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
        )
        self.event_flags_tab.setup_ui()

        # Tab 8: Gestures
        self.notebook.add("Gestures")
        tab_gestures = self.notebook.tab("Gestures")
        self.gestures_tab = GesturesRegionsTab(
            tab_gestures,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
        )
        self.gestures_tab.setup_ui()

        # Tab 9: Hex Editor
        self.notebook.add("Hex Editor")
        tab_hex = self.notebook.tab("Hex Editor")
        self.hex_tab = HexEditorTab(tab_hex, lambda: self.save_file)
        self.hex_tab.setup_ui()

        # Tab 10: Advanced Tools
        self.notebook.add("Advanced Tools")
        tab_advanced = self.notebook.tab("Advanced Tools")
        self.advanced_tab = AdvancedToolsTab(
            tab_advanced, lambda: self.save_file, lambda: self.save_path, self.load_save
        )
        self.advanced_tab.setup_ui()

        # Tab 11: Settings
        self.notebook.add("Settings")
        tab_settings = self.notebook.tab("Settings")
        self.settings_tab = SettingsTab(tab_settings)
        self.settings_tab.setup_ui()

    def setup_character_editor_tab(self, parent):
        """Setup character editor tab with modular editors"""
        header = ctk.CTkLabel(
            parent,
            text="Character Editor",
            font=("Segoe UI", 18, "bold"),
        )
        header.pack(pady=(6, 12))

        container = ctk.CTkFrame(
            parent, corner_radius=10, fg_color=("gray12", "gray22")
        )
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 12))

        # Slot selector bar
        select_frame = ctk.CTkFrame(container, fg_color=("gray14", "gray24"))
        select_frame.pack(fill=tk.X, padx=10, pady=(12, 8))

        ctk.CTkLabel(select_frame, text="Character Slot:").pack(
            side=ctk.LEFT, padx=(0, 10)
        )

        self.char_slot_var = ctk.StringVar(value="1")
        slot_combo = ctk.CTkComboBox(
            select_frame,
            variable=self.char_slot_var,
            values=[str(i) for i in range(1, 11)],
            state="readonly",
            width=90,
        )
        slot_combo.pack(side=ctk.LEFT, padx=(0, 12))

        ctk.CTkButton(
            select_frame,
            text="Load Character",
            command=self.load_character_for_edit,
            width=140,
        ).pack(side=ctk.LEFT)

        # Editor tabs
        editor_tabs = ctk.CTkTabview(
            container,
            width=900,
            height=520,
            fg_color=("gray10", "gray20"),
            segmented_button_fg_color=("gray25", "gray35"),
            segmented_button_selected_color=("#7c5b9a", "#6a4b85"),
            segmented_button_unselected_color=("gray40", "gray30"),
            text_color=("white", "white"),
        )
        editor_tabs.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 12))

        def current_slot_index() -> int:
            try:
                return int(self.char_slot_var.get()) - 1
            except Exception:
                return -1

        # Stats editor
        stats_frame = editor_tabs.add("Stats")
        stats_frame = ctk.CTkFrame(stats_frame, fg_color=("gray12", "gray22"))
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.stats_editor = StatsEditor(
            stats_frame,
            lambda: self.save_file,
            current_slot_index,
            lambda: self.save_path,
        )
        self.stats_editor.setup_ui()

        # Equipment editor
        equipment_tab = editor_tabs.add("Equipment")
        equipment_frame = ctk.CTkFrame(equipment_tab, fg_color=("gray12", "gray22"))
        equipment_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.equipment_editor = EquipmentEditor(
            equipment_frame,
            lambda: self.save_file,
            current_slot_index,
        )
        self.equipment_editor.setup_ui()

        # Character info editor
        info_tab = editor_tabs.add("Info")
        info_frame = ctk.CTkFrame(info_tab, fg_color=("gray12", "gray22"))
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.char_info_editor = CharacterInfoEditor(
            info_frame,
            lambda: self.save_file,
            current_slot_index,
            lambda: self.save_path,
        )
        self.char_info_editor.setup_ui()

        # Inventory editor
        inventory_tab = editor_tabs.add("Inventory")
        inventory_frame = ctk.CTkFrame(inventory_tab, fg_color=("gray12", "gray22"))
        inventory_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.inventory_editor = InventoryEditor(
            inventory_frame,
            lambda: self.save_file,
            current_slot_index,
            lambda: self.save_path,
            self.ensure_raw_data_mutable,
        )
        self.inventory_editor.setup_ui()

    def load_character_for_edit(self):
        """Load character data into editors"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        try:
            slot_idx = int(self.char_slot_var.get()) - 1
        except Exception:
            messagebox.showwarning("Invalid Slot", "Please choose a character slot.")
            return
        slot = self.save_file.characters[slot_idx]

        if slot.is_empty():
            messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
            return

        # Load into all editors
        self.stats_editor.load_stats()
        self.equipment_editor.load_equipment()
        self.char_info_editor.load_character_info()
        self.inventory_editor.refresh_inventory()

        self.status_var.set(f"Loaded character from Slot {slot_idx + 1}")

    def ensure_raw_data_mutable(self):
        """Ensure save file _raw_data is mutable (bytearray)"""
        if self.save_file and isinstance(self.save_file._raw_data, bytes):
            self.save_file._raw_data = bytearray(self.save_file._raw_data)

    # File operations
    def browse_file(self):
        """Browse for save file"""
        # On Linux, try to start in a visible directory since .local is hidden
        initialdir = (
            str(self.default_save_path)
            if self.default_save_path.exists()
            else str(Path.home())
        )

        # On Linux, if default path doesn't exist, try to navigate to Steam directory
        if PlatformUtils.is_linux() and not self.default_save_path.exists():
            steam_base = Path.home() / ".local" / "share" / "Steam"
            if steam_base.exists():
                initialdir = str(steam_base)

        filename = filedialog.askopenfilename(
            title="Select Elden Ring Save File",
            initialdir=initialdir,
            filetypes=[("Elden Ring Saves", "*.sl2 *.co2"), ("All files", "*.*")],
        )
        if filename:
            self.file_path_var.set(filename)
            self.status_var.set(f"Selected: {os.path.basename(filename)}")

            # Linux: Check if in default location
            if (
                PlatformUtils.is_linux()
                and not PlatformUtils.is_save_in_default_location(Path(filename))
                and self.settings.get("show_linux_save_warning", True)
            ):
                self.show_linux_save_location_warning(Path(filename))

    def auto_detect(self):
        """Auto-detect save file with Linux support"""
        # Find all save files using platform utilities
        found_saves = PlatformUtils.find_all_save_files()

        if not found_saves:
            # Show platform-specific help
            if PlatformUtils.is_linux():
                messagebox.showinfo(
                    "No Saves Found",
                    "No Elden Ring save files found.\n\n"
                    "Linux users: Make sure you've launched Elden Ring at least once.\n"
                    "Saves are stored in Steam's compatdata folder.\n\n"
                    "Click 'Linux Steam Info' for help.",
                )
            else:
                messagebox.showwarning("Not Found", "No Elden Ring save files found.")
            return

        if len(found_saves) == 1:
            # Only one save found
            self.file_path_var.set(str(found_saves[0]))
            self.status_var.set("Save file auto-detected")

            # Linux: Check if in default location
            if (
                PlatformUtils.is_linux()
                and not PlatformUtils.is_save_in_default_location(found_saves[0])
            ):
                if self.settings.get("show_linux_save_warning", True):
                    self.show_linux_save_location_warning(found_saves[0])
        else:
            # Multiple saves found
            SaveSelectorDialog.show(
                self.root, found_saves, lambda path: self.file_path_var.set(path)
            )

    def show_linux_save_location_warning(self, save_path):
        """Show warning about non-default save location on Linux"""
        dialog = tk.Toplevel(self.root)
        dialog.title("⚠️ Save Location Warning")
        dialog.geometry("550x450")
        dialog.transient(self.root)

        msg_frame = ttk.Frame(dialog, padding=20)
        msg_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            msg_frame,
            text="⚠️ Non-Standard Save Location",
            font=("Segoe UI", 12, "bold"),
            foreground="orange",
        ).pack(pady=(0, 10))

        warning_text = (
            f"Your save file is located in:\n"
            f"{save_path}\n\n"
            f"This is NOT the default Steam compatdata location!\n\n"
            f"⚠️ If you remove Elden Ring from Steam and reinstall it, "
            f"Steam will create a NEW compatdata folder and your saves may become inaccessible.\n\n"
            f"Recommended: Set a fixed Steam launch option to prevent this."
        )

        ttk.Label(
            msg_frame,
            text=warning_text,
            wraplength=500,
            justify=tk.LEFT,
        ).pack(pady=10)

        # Show launch option
        launch_option = PlatformUtils.get_steam_launch_option_hint()
        if launch_option:
            ttk.Label(
                msg_frame,
                text="Add this to Elden Ring's Steam launch options:",
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor=tk.W, pady=(10, 5))

            option_frame = ttk.Frame(msg_frame)
            option_frame.pack(fill=tk.X, pady=5)

            option_entry = ttk.Entry(option_frame, font=("Consolas", 11))
            option_entry.insert(0, launch_option)
            option_entry.config(state="readonly")
            option_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

            def copy_to_clipboard():
                self.root.clipboard_clear()
                self.root.clipboard_append(launch_option)
                messagebox.showinfo("Copied", "Launch option copied to clipboard!")

            ttk.Button(
                option_frame, text="Copy", command=copy_to_clipboard, width=10
            ).pack(side=tk.LEFT)

        # Buttons
        button_frame = ttk.Frame(msg_frame)
        button_frame.pack(pady=10)

        def copy_to_default():
            default_loc = PlatformUtils.get_default_save_location()
            if default_loc:
                if messagebox.askyesno(
                    "Copy Save",
                    f"Copy save file to:\n{default_loc}\n\nThe original file will remain in its current location.",
                ):
                    try:
                        default_loc.mkdir(parents=True, exist_ok=True)
                        import shutil

                        new_path = default_loc / Path(save_path).name
                        shutil.copy2(save_path, new_path)
                        self.file_path_var.set(str(new_path))
                        messagebox.showinfo(
                            "Success",
                            f"Save file copied to:\n{new_path}\n\nOriginal file remains at:\n{save_path}",
                        )
                        dialog.destroy()
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to move save:\n{e}")

        def dont_show_again():
            self.settings.set("show_linux_save_warning", False)
            dialog.destroy()

        ttk.Button(
            button_frame, text="Copy to Default", command=copy_to_default, width=18
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            button_frame, text="Keep Current", command=dialog.destroy, width=15
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            button_frame, text="Don't Show Again", command=dont_show_again, width=18
        ).pack(side=tk.LEFT, padx=5)

    def show_linux_steam_info_dialog(self):
        """Show Linux-specific Steam/Proton information"""
        if not PlatformUtils.is_linux():
            return

        from er_save_manager.ui.utils import bind_mousewheel

        dialog = tk.Toplevel(self.root)
        dialog.title("Linux Steam / Proton Info")
        dialog.geometry("700x700")
        dialog.transient(self.root)
        dialog.grab_set()

        # Use CTkScrollableFrame for better scrolling and appearance
        msg_frame = ctk.CTkScrollableFrame(
            dialog,
            fg_color=("gray86", "gray25"),
            scrollbar_fg_color=("gray70", "gray40"),
        )
        msg_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        bind_mousewheel(msg_frame)

        # Title
        ctk.CTkLabel(
            msg_frame,
            text="Elden Ring on Linux (Steam/Proton)",
            font=("Segoe UI", 14, "bold"),
            text_color=("black", "white"),
        ).pack(pady=(15, 10), padx=20)

        # Info sections
        info_text = """Save File Locations:
Elden Ring on Linux uses Steam's Proton compatibility layer. Your saves are stored in:

~/.steam/steam/steamapps/compatdata/[NUMBER]/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing/[SteamID]/

The [NUMBER] is called the "compatdata ID" and varies depending on installation.

Common Issues:
1. Multiple Save Locations: If you've reinstalled the game, Steam may create a NEW compatdata folder, making old saves appear lost.

2. Disappearing Saves: If Steam removes the game data, the compatdata folder may be deleted.

Solution - Fixed Launch Option:
Add this to Elden Ring's Steam launch options to always use the same location:"""

        ctk.CTkLabel(
            msg_frame,
            text=info_text,
            justify=tk.LEFT,
            wraplength=650,
            text_color=("black", "white"),
        ).pack(pady=(0, 15), padx=20)

        # Launch option
        launch_option = PlatformUtils.get_steam_launch_option_hint()
        if launch_option:
            option_frame = ctk.CTkFrame(
                msg_frame, fg_color=("gray75", "gray35"), corner_radius=6
            )
            option_frame.pack(fill=tk.X, pady=(0, 15), padx=20)

            ctk.CTkLabel(
                option_frame,
                text="Launch Option:",
                text_color=("black", "white"),
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor=tk.W, padx=10, pady=(10, 5))

            option_entry = ctk.CTkEntry(
                option_frame,
                fg_color=("white", "gray20"),
                text_color=("black", "white"),
                border_color=("gray50", "gray60"),
                border_width=1,
            )
            option_entry.insert(0, launch_option)
            option_entry.configure(state="readonly")
            option_entry.pack(
                side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5), pady=(0, 10)
            )

            def copy_to_clipboard():
                self.root.clipboard_clear()
                self.root.clipboard_append(launch_option)
                messagebox.showinfo("Copied", "Copied to clipboard!")

            ctk.CTkButton(
                option_frame, text="Copy", command=copy_to_clipboard, width=70
            ).pack(side=tk.LEFT, padx=(0, 10), pady=(0, 10))

        # How to add launch option
        steps_text = """How to Add Launch Options:
1. Right-click Elden Ring in Steam
2. Properties → General → Launch Options
3. Paste the command above
4. Click OK and restart the game

This ensures your saves always go to the same location!"""

        ctk.CTkLabel(
            msg_frame,
            text=steps_text,
            justify=tk.LEFT,
            wraplength=650,
            text_color=("black", "white"),
        ).pack(pady=(0, 15), padx=20)

        # Flatpak warning
        if PlatformUtils.is_flatpak_steam():
            flatpak_frame = ctk.CTkFrame(
                msg_frame, fg_color=("#e3f2fd", "#1a2332"), corner_radius=6
            )
            flatpak_frame.pack(fill=tk.X, pady=(0, 15), padx=20)
            ctk.CTkLabel(
                flatpak_frame,
                text="⚠️ Flatpak Steam detected - using appropriate path.",
                text_color=("#1565c0", "#64b5f6"),
                font=("Segoe UI", 10),
            ).pack(padx=10, pady=8)

        # Close button frame at bottom
        button_frame = ctk.CTkFrame(dialog, fg_color=("gray86", "gray25"))
        button_frame.pack(fill=tk.X, padx=20, pady=15)

        ctk.CTkButton(
            button_frame, text="Close", command=dialog.destroy, width=120
        ).pack(side=tk.RIGHT)

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

        except Exception:
            pass

        return False

    def _on_tab_changed(self, event=None):
        """Handle tab change event - lazy load and refresh tabs."""
        current_tab = self.notebook.get()

        # Load tab content in background for non-blocking UI
        if not self.tabs_loaded.get(current_tab, False):
            thread = threading.Thread(
                target=self._lazy_load_tab_background, args=(current_tab,), daemon=True
            )
            thread.start()
        elif current_tab == "World State" and hasattr(self, "world_tab"):
            # Already loaded, just refresh
            self.world_tab.refresh()

    def _lazy_load_tab_background(self, tab_name):
        """Load tab data in background thread"""
        try:
            if not self.save_file:
                return

            # Skip if already loaded (double-check)
            if self.tabs_loaded.get(tab_name, False):
                return

            # Load data without blocking UI
            if tab_name == "Save Inspector":
                self.inspector_tab.populate_character_list()
            elif tab_name == "Appearance":
                self.appearance_tab.load_presets()
            elif tab_name == "Advanced Tools":
                self.advanced_tab.update_save_info()
            elif tab_name == "SteamID Patcher":
                if hasattr(self.steamid_tab, "update_steamid_display"):
                    self.steamid_tab.update_steamid_display()
            elif tab_name == "Hex Editor":
                if self.save_file:
                    try:
                        with open(self.save_path, "rb") as f:
                            self.save_file._raw_data = f.read()
                        self.hex_tab.hex_display_at_offset(0)
                    except Exception:
                        pass
            elif tab_name == "Gestures":
                pass  # Gestures tab doesn't auto-load

            # Mark as loaded
            self.root.after(0, lambda: self.tabs_loaded.update({tab_name: True}))

        except Exception:
            pass

    def on_slot_selected(self, slot_index: int):
        """Handle character slot selection from Save Inspector."""
        self.selected_slot_index = slot_index

    def load_save(self):
        """Load save file in background thread to prevent UI freezing"""
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

        # EAC warning for PC save files (.sl2)
        if save_path.lower().endswith(".sl2") and self.settings.get(
            "show_eac_warning", True
        ):
            # Create custom dialog with "Don't show again" option
            warning_dialog = tk.Toplevel(self.root)
            warning_dialog.title("⚠️ EAC Warning - Vanilla Save File Detected")
            warning_dialog.geometry("520x420")
            warning_dialog.transient(self.root)
            warning_dialog.grab_set()

            # Warning message
            msg_frame = ttk.Frame(warning_dialog, padding=20)
            msg_frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(
                msg_frame,
                text="⚠️ EAC Warning - Vanilla Save File Detected",
                font=("Segoe UI", 12, "bold"),
                foreground="red",
            ).pack(pady=(0, 10))

            warning_text = (
                "You are loading a Vanilla save file (.sl2).\n\n"
                "WARNING: Modifying save files can result in a BAN if:\n"
                "• Easy Anti-Cheat (EAC) is enabled\n"
                "• You play online with modified saves\n\n"
                "To avoid bans:\n"
                "1. Launch Elden Ring with EAC disabled\n"
                "2. Only play offline with modified saves\n"
                "3. Do not use modified saves in online/multiplayer\n\n"
                "Do you understand and want to continue?"
            )

            ttk.Label(
                msg_frame,
                text=warning_text,
                wraplength=470,
                justify=tk.LEFT,
            ).pack(pady=10)

            # Don't show again checkbox
            dont_show_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(
                msg_frame,
                text="Don't show this warning again",
                variable=dont_show_var,
            ).pack(pady=10)

            # Buttons
            button_frame = ttk.Frame(msg_frame)
            button_frame.pack(pady=10)

            result = {"continue": False}

            def on_yes():
                if dont_show_var.get():
                    self.settings.set("show_eac_warning", False)
                result["continue"] = True
                warning_dialog.destroy()

            def on_no():
                result["continue"] = False
                warning_dialog.destroy()

            ttk.Button(
                button_frame, text="Yes, Continue", command=on_yes, width=15
            ).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="No, Cancel", command=on_no, width=15).pack(
                side=tk.LEFT, padx=5
            )

            # Wait for dialog to close
            self.root.wait_window(warning_dialog)

            if not result["continue"]:
                self.status_var.set("Load cancelled by user")
                return

        # Start loading in background thread
        self.status_var.set("Loading save file...")
        thread = threading.Thread(
            target=self._load_save_background, args=(save_path,), daemon=True
        )
        thread.start()

    def _load_save_background(self, save_path):
        """Background thread for loading save file"""
        try:
            # Load save file in background
            save_file = Save.from_file(save_path)

            # Update main thread
            self.root.after(0, self._finalize_save_load, save_file, save_path)
        except Exception as e:
            error_msg = str(e)
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Error", f"Failed to load save file:\n{error_msg}"
                ),
            )
            self.root.after(0, lambda: self.status_var.set("Load failed"))

    def _finalize_save_load(self, save_file, save_path):
        """Finalize save loading on main thread"""
        self.save_file = save_file
        self.save_path = Path(save_path)

        # Reset all tab flags so views will refresh with the new save
        for tab_name in self.tabs_loaded:
            self.tabs_loaded[tab_name] = False

        # Lazy-load the currently visible tab immediately (ensures live refresh)
        current_tab = self.notebook.get()
        self._lazy_load_tab_background(current_tab)

        self.status_var.set(f"Loaded: {os.path.basename(save_path)}")
        messagebox.showinfo("Success", "Save file loaded successfully!")

    def show_character_details(self, slot_idx):
        """Show character details dialog"""
        CharacterDetailsDialog.show(
            self.root, self.save_file, slot_idx, self.save_path, self.load_save
        )

    def show_backup_manager_standalone(self):
        """Show backup manager from top button"""
        from tkinter import messagebox

        if not self.save_file or not self.save_path:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        # Reuse the full-featured BackupManagerTab window (with buttons + sorting)
        try:
            from er_save_manager.ui.tabs.backup_manager_tab import BackupManagerTab

            if not hasattr(self, "_backup_tab_helper"):
                self._backup_tab_helper = BackupManagerTab(
                    self.root,
                    lambda: self.save_file,
                    lambda: self.save_path,
                    self.load_save,
                )

            self._backup_tab_helper.show_backup_manager()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open backup manager:\n{str(e)}")


def main():
    """Main entry point for GUI"""
    root = ctk.CTk()
    SaveManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
