"""
Main GUI Application
Modular Elden Ring Save Manager GUI
"""

import os
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

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
    BackupManagerTab,
    CharacterManagementTab,
    EventFlagsTab,
    GesturesRegionsTab,
    HexEditorTab,
    SaveInspectorTab,
    SettingsTab,
    SteamIDPatcherTab,
    WorldStateTab,
)


class SaveManagerGUI:
    """Main GUI application for Elden Ring Save Manager"""

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
        self.selected_slot_index = -1  # Current selected character slot (0-9)

        # Status
        self.status_var = tk.StringVar(value="Ready")

        self.setup_ui()

    def setup_ui(self):
        """Setup main UI structure"""
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
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            path_frame,
            text="Auto-Find",
            command=self.auto_detect,
            width=10,
        ).pack(side=tk.LEFT, padx=2)

        # Linux help button
        if PlatformUtils.is_linux():
            ttk.Button(
                path_frame,
                text="Linux Info",
                command=self.show_linux_steam_info_dialog,
                width=12,
            ).pack(side=tk.LEFT, padx=2)

        # Load button
        buttons_frame = ttk.Frame(file_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            buttons_frame,
            text="Load Save File",
            command=self.load_save,
            width=20,
        ).pack(side=tk.LEFT)

        ttk.Button(
            buttons_frame,
            text="Backup Manager",
            command=self.show_backup_manager_standalone,
            width=20,
        ).pack(side=tk.LEFT, padx=10)

        # Main content - tabbed interface
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Create all tabs
        # Initialize settings
        self.settings = get_settings()

        self.create_tabs()

        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Label(
            status_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=5,
        ).pack(fill=tk.X)

    def create_tabs(self):
        """Create all tabs with modular components"""

        # Tab 1: Save Inspector
        tab_inspector = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_inspector, text="Save Inspector")
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
        tab_char_mgmt = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_char_mgmt, text="Character Management")
        self.char_mgmt_tab = CharacterManagementTab(
            tab_char_mgmt,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
        )
        self.char_mgmt_tab.setup_ui()

        # Tab 3: Character Editor
        tab_character = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_character, text="Character Editor")
        self.setup_character_editor_tab(tab_character)

        # Tab 4: Appearance
        tab_appearance = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_appearance, text="Appearance")
        self.appearance_tab = AppearanceTab(
            tab_appearance,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
        )
        self.appearance_tab.setup_ui()

        # Tab 5: World State
        tab_world = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_world, text="World State")
        self.world_tab = WorldStateTab(
            tab_world,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
            lambda: self.selected_slot_index,
        )
        self.world_tab.setup_ui()

        # Tab 6: SteamID Patcher
        tab_steamid = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_steamid, text="SteamID Patcher")
        self.steamid_tab = SteamIDPatcherTab(
            tab_steamid, lambda: self.save_file, lambda: self.save_path, self.load_save
        )
        self.steamid_tab.setup_ui()

        # Tab 7: Event Flags
        tab_event_flags = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_event_flags, text="Event Flags")
        self.event_flags_tab = EventFlagsTab(
            tab_event_flags,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
        )
        self.event_flags_tab.setup_ui()

        # Tab 8: Gestures
        tab_gestures = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_gestures, text="Gestures")
        self.gestures_tab = GesturesRegionsTab(
            tab_gestures,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
        )
        self.gestures_tab.setup_ui()

        # Tab 9: Hex Editor
        tab_hex = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_hex, text="Hex Editor")
        self.hex_tab = HexEditorTab(tab_hex, lambda: self.save_file)
        self.hex_tab.setup_ui()

        # Tab 10: Advanced Tools
        tab_advanced = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_advanced, text="Advanced Tools")
        self.advanced_tab = AdvancedToolsTab(
            tab_advanced, lambda: self.save_file, lambda: self.save_path, self.load_save
        )
        self.advanced_tab.setup_ui()

        # Tab 11: Backup Manager
        tab_backup = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_backup, text="Backup Manager")
        self.backup_tab = BackupManagerTab(
            tab_backup, lambda: self.save_file, lambda: self.save_path, self.load_save
        )
        self.backup_tab.setup_ui()

        # Tab 12: Settings
        tab_settings = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_settings, text="Settings")
        self.settings_tab = SettingsTab(tab_settings)
        self.settings_tab.setup_ui()

        # Bind tab change event to refresh world state
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def setup_character_editor_tab(self, parent):
        """Setup character editor tab with modular editors"""
        ttk.Label(
            parent,
            text="Character Editor",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        # Slot selector
        select_frame = ttk.Frame(parent)
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
        ).pack(side=tk.LEFT, padx=5)

        # Editor notebook
        editor_notebook = ttk.Notebook(parent)
        editor_notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        # Stats editor
        stats_frame = ttk.Frame(editor_notebook, padding=10)
        editor_notebook.add(stats_frame, text="Stats")
        self.stats_editor = StatsEditor(
            stats_frame,
            lambda: self.save_file,
            lambda: self.char_slot_var.get() - 1,
            lambda: self.save_path,
        )
        self.stats_editor.setup_ui()

        # Equipment editor
        equipment_frame = ttk.Frame(editor_notebook, padding=10)
        editor_notebook.add(equipment_frame, text="Equipment")
        self.equipment_editor = EquipmentEditor(
            equipment_frame,
            lambda: self.save_file,
            lambda: self.char_slot_var.get() - 1,
        )
        self.equipment_editor.setup_ui()

        # Character info editor
        info_frame = ttk.Frame(editor_notebook, padding=10)
        editor_notebook.add(info_frame, text="Info")
        self.char_info_editor = CharacterInfoEditor(
            info_frame,
            lambda: self.save_file,
            lambda: self.char_slot_var.get() - 1,
            lambda: self.save_path,
        )
        self.char_info_editor.setup_ui()

        # Inventory editor
        inventory_frame = ttk.Frame(editor_notebook, padding=10)
        editor_notebook.add(inventory_frame, text="Inventory")
        self.inventory_editor = InventoryEditor(
            inventory_frame,
            lambda: self.save_file,
            lambda: self.char_slot_var.get() - 1,
            lambda: self.save_path,
            self.ensure_raw_data_mutable,
        )
        self.inventory_editor.setup_ui()

    def load_character_for_edit(self):
        """Load character data into editors"""
        if not self.save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.char_slot_var.get() - 1
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
        filename = filedialog.askopenfilename(
            title="Select Elden Ring Save File",
            initialdir=self.default_save_path,
            filetypes=[("Elden Ring Saves", "*.sl2 *.co2"), ("All files", "*.*")],
        )
        if filename:
            self.file_path_var.set(filename)
            self.status_var.set(f"Selected: {os.path.basename(filename)}")

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

            option_entry = ttk.Entry(option_frame, font=("Consolas", 9))
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

        dialog = tk.Toplevel(self.root)
        dialog.title("Linux Steam / Proton Info")
        dialog.geometry("650x550")
        dialog.transient(self.root)

        msg_frame = ttk.Frame(dialog, padding=20)
        msg_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            msg_frame,
            text="Elden Ring on Linux (Steam/Proton)",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(0, 15))

        # Info sections
        info_text = """Save File Locations:
Elden Ring on Linux uses Steam's Proton compatibility layer. Your saves are stored in:

~/.steam/steam/steamapps/compatdata/[NUMBER]/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing/[SteamID]/

The [NUMBER] is called the "compatdata ID" and varies depending on installation.

Common Issues:
1. Multiple Save Locations: If you've reinstalled the game, Steam may create a NEW compatdata folder, making old saves appear lost.

2. Disappearing Saves: If Steam removes the game data, the compatdata folder may be deleted.

Solution - Fixed Launch Option:
Add this to Elden Ring's Steam launch options to always use the same location:

"""

        ttk.Label(
            msg_frame,
            text=info_text,
            justify=tk.LEFT,
            wraplength=600,
        ).pack(pady=10)

        # Launch option
        launch_option = PlatformUtils.get_steam_launch_option_hint()
        if launch_option:
            option_frame = ttk.Frame(msg_frame)
            option_frame.pack(fill=tk.X, pady=10)

            option_entry = ttk.Entry(option_frame, font=("Consolas", 9))
            option_entry.insert(0, launch_option)
            option_entry.config(state="readonly")
            option_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

            def copy_to_clipboard():
                self.root.clipboard_clear()
                self.root.clipboard_append(launch_option)
                messagebox.showinfo("Copied", "Copied to clipboard!")

            ttk.Button(
                option_frame, text="Copy", command=copy_to_clipboard, width=10
            ).pack(side=tk.LEFT)

        # How to add launch option
        steps_text = """How to Add Launch Options:
1. Right-click Elden Ring in Steam
2. Properties → General → Launch Options
3. Paste the command above
4. Click OK and restart the game

This ensures your saves always go to the same location!"""

        ttk.Label(
            msg_frame,
            text=steps_text,
            justify=tk.LEFT,
            wraplength=600,
            font=("Segoe UI", 9),
        ).pack(pady=10)

        # Flatpak warning
        if PlatformUtils.is_flatpak_steam():
            ttk.Label(
                msg_frame,
                text="Note: Flatpak Steam detected - using appropriate path.",
                font=("Segoe UI", 9, "italic"),
                foreground="blue",
            ).pack(pady=5)

        ttk.Button(msg_frame, text="Close", command=dialog.destroy, width=15).pack(
            pady=10
        )

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

        except Exception as e:
            print(f"Warning: Could not check if game is running: {e}")

        return False

    def _on_tab_changed(self, event=None):
        """Handle tab change event - refresh world state when switching to it."""
        current_tab = self.notebook.select()
        tab_text = self.notebook.tab(current_tab, "text")

        # Refresh world state tab when switched to
        if tab_text == "World State":
            self.world_tab.refresh()

    def on_slot_selected(self, slot_index: int):
        """Handle character slot selection from Save Inspector."""
        self.selected_slot_index = slot_index

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

        # EAC warning for PC save files (.sl2)
        if save_path.lower().endswith(".sl2") and self.settings.get(
            "show_eac_warning", True
        ):
            # Create custom dialog with "Don't show again" option
            warning_dialog = tk.Toplevel(self.root)
            warning_dialog.title("⚠️ EAC Warning - PC Save File Detected")
            warning_dialog.geometry("520x420")
            warning_dialog.transient(self.root)
            warning_dialog.grab_set()

            # Warning message
            msg_frame = ttk.Frame(warning_dialog, padding=20)
            msg_frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(
                msg_frame,
                text="⚠️ EAC Warning - PC Save File Detected",
                font=("Segoe UI", 12, "bold"),
                foreground="red",
            ).pack(pady=(0, 10))

            warning_text = (
                "You are loading a PC save file (.sl2).\n\n"
                "WARNING: Modifying save files can result in a BAN if:\n"
                "• Easy Anti-Cheat (EAC) is enabled\n"
                "• You play online with modified saves\n\n"
                "To avoid bans:\n"
                "1. Launch Elden Ring with EAC disabled (use -eac_launcher flag)\n"
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

        try:
            self.status_var.set("Loading save file...")
            self.root.update()

            self.save_file = Save.from_file(save_path)
            self.save_path = Path(save_path)

            # Update all tab displays
            self.inspector_tab.populate_character_list()
            self.appearance_tab.load_presets()
            self.advanced_tab.update_save_info()
            self.backup_tab.update_backup_stats()

            # Update SteamID display
            if hasattr(self.steamid_tab, "update_steamid_display"):
                self.steamid_tab.update_steamid_display()

            # Update hex view
            if self.save_file:
                try:
                    with open(self.save_path, "rb") as f:
                        self.save_file._raw_data = f.read()
                    self.hex_tab.hex_display_at_offset(0)
                except Exception:
                    pass

            self.status_var.set(f"Loaded: {os.path.basename(save_path)}")
            messagebox.showinfo("Success", "Save file loaded successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load save file:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def show_character_details(self, slot_idx):
        """Show character details dialog"""
        CharacterDetailsDialog.show(
            self.root, self.save_file, slot_idx, self.save_path, self.load_save
        )

    def show_backup_manager_standalone(self):
        """Show backup manager from top button"""
        if hasattr(self.backup_tab, "show_backup_manager"):
            self.backup_tab.show_backup_manager()
        else:
            messagebox.showwarning("No Save", "Please load a save file first!")


def main():
    """Main entry point for GUI"""
    root = tk.Tk()
    SaveManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
