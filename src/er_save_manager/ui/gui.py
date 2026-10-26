"""
Main GUI Application
Modular Elden Ring Save Manager GUI
"""

import logging
import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import replace
from importlib import resources
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk

import customtkinter as ctk

from er_save_manager import VersionChecker, __version__
from er_save_manager.games.extension_copy import (
    SUPPORTED_GAMES as SUPPORTED_EXTENSION_GAMES,
)
from er_save_manager.games.game_profiles import GAME_PROFILES, PROFILES_BY_KEY
from er_save_manager.own_writes import is_own_write
from er_save_manager.parser import Save
from er_save_manager.platform import PlatformUtils
from er_save_manager.ui import palette, popups
from er_save_manager.ui.character_pages import CharacterPagesTab
from er_save_manager.ui.dialogs.character_details import CharacterDetailsDialog
from er_save_manager.ui.dialogs.save_selector import SaveSelectorDialog
from er_save_manager.ui.editors import (
    CharacterInfoEditor,
    EquipmentEditor,
    InventoryEditor,
    StatsEditor,
)
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import CharacterBar, PendingBar, PendingPage
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
from er_save_manager.ui.theme import ThemeManager
from er_save_manager.ui.utils import (
    center_window,
    fit_size_to_work_area,
    get_work_area,
    open_url,
    pick_file,
    style_window_frame,
    title_bar_height,
    trace_variable,
)

# Nightreign
try:
    from er_save_manager.games.NR.editor_tab import NREditorTab
    from er_save_manager.games.NR.inspector_tab import NRInspectorTab
    from er_save_manager.games.NR.parser import NightreignSave

    _NR_AVAILABLE = True
except ImportError:
    _NR_AVAILABLE = False


# Pause between building queued tabs, so input is handled in between.
_TAB_BUILD_DELAY_MS = 15

# Main window height (logical px) below which the header is compacted
_COMPACT_HEIGHT = 900

# Tab labels used when the full names do not fit the window width
_SHORT_TAB_NAMES = {
    "Save Fixer": "Fixer",
    "Save Inspector": "Inspector",
    "Character Management": "Characters",
    "Character Editor": "Editor",
    "World State": "World",
    "SteamID Patcher": "SteamID",
    "Event Flags": "Flags",
    "Advanced Tools": "Tools",
}
# Header button width (logical px) when the row is too narrow for the full one
_NARROW_HEADER_BUTTON = 130

# Games that load console saves, shown the console save help button
_CONSOLE_SAVE_GAMES = ("elden_ring", "nightreign", "dark_souls_3")


def _console_button_text(game_key: str) -> str:
    return "PS4 Save?" if game_key == "dark_souls_3" else "PS / Switch Save?"


_log = logging.getLogger(__name__)


class SaveManagerGUI:
    """Main GUI application for Elden Ring Save Manager"""

    def __init__(self, root):
        self.root = root
        self.root.title("Elden Ring Save Manager")
        self.root.geometry("1200x1000")

        try:
            if getattr(sys, "frozen", False):
                if hasattr(sys, "_MEIPASS"):
                    # PyInstaller (Linux)
                    base_path = Path(sys._MEIPASS)
                else:
                    # cx_Freeze (Windows)
                    base_path = Path(sys.executable).parent
            else:
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

        self.settings = get_settings()

        # Configure customtkinter appearance based on saved theme (default to dark)
        theme_name = self.settings.get("theme", None)
        if theme_name is None or theme_name == "dark":
            ctk.set_appearance_mode("dark")
            theme_name = "dark"
        elif theme_name == "bright" or theme_name == "default":
            ctk.set_appearance_mode("light")
            theme_name = "bright"

        try:
            import customtkinterthemes as ctt

            theme_path = resources.files(ctt).joinpath("Themes", "lavender.json")
            ctk.set_default_color_theme(theme_path)
            palette.apply_theme_overrides()
        except Exception:
            ctk.set_default_color_theme("dark-blue")

        # Apply UI scaling before any widgets are created.
        # Uses the saved value; falls back to auto-detecting the OS scale.
        # set_widget_scaling scales CTk widget dimensions and fonts.
        # The tk named fonts are also scaled so ttk/tk widgets match.
        from er_save_manager.ui.settings import detect_system_scale

        _saved_scale = self.settings.get("ui_scale", 1.0)
        _scale = (
            detect_system_scale(_windows_dpi_ignored())
            if _saved_scale is None
            else _saved_scale
        )
        if _scale != 1.0:
            ctk.set_widget_scaling(_scale)
            ctk.set_window_scaling(_scale)
            self._scale_tk_fonts(_scale)

        # Initialize theme manager for any remaining ttk widgets (during migration)
        self.theme_manager = ThemeManager(theme_name)

        style = ttk.Style()
        style.theme_use("clam")
        self.theme_manager.apply_theme(style)

        self.root.configure(bg=self.theme_manager.get_color("bg"))

        self.default_save_path = Path(os.environ.get("APPDATA", "")) / "EldenRing"
        self.save_file = None
        self.save_path = None
        # Vanilla saves already confirmed in the ban warning this session
        self._vanilla_warned_paths: set[str] = set()
        self.selected_slot = None
        self.selected_slot_index = -1  # Current selected character slot (0-9)

        # Active game (key from game_profiles.py); drives which tabs are shown.
        # Starts on the saved default game.
        self.active_game = self._get_default_game_key()

        # DSR-specific parsed save (separate from ER save_file)
        self.dsr_save = None
        self.ds3_save = None
        self.ds2_save = None
        self._nr_save: NightreignSave | None = None
        self._file_load_buttons: list = []

        # Lazy loading flags (track which tabs have been initialized with data)
        self.tabs_loaded = {
            "Save Fixer": False,
            "Appearance": False,
            "Advanced Tools": False,
            "SteamID Patcher": False,
            "Hex Editor": False,
            "Gestures": False,
        }

        self.status_var = tk.StringVar(value="Ready")

        # Resize debouncing for performance
        self._resize_timer = None
        self._last_width = None
        self._last_height = None

        self.process_monitor = None

        self._watched_mtime: float | None = None
        self._file_change_dialog_open: bool = False
        self._file_watcher_running: bool = False
        self._pending_file_change: bool = False

        # Tab widgets built after the visible tab, in tab order (see _build_tab)
        self._pending_tabs: dict[str, deque] = {}
        # Tabs of the active game that show the character picked in the
        # character bar: tab name -> load(slot index, -1 for none)
        self._character_tabs: dict[str, Callable[[int], None]] = {}
        # Tab name -> (link text, action) shown in the character bar
        self._feature_links: dict[str, list[tuple[str, Callable[[], None]]]] = {}
        # Slot shown by the Elden Ring Character Editor
        self._er_slot = -1
        # Set while reloading after a failed Apply All, which must not ask
        self._guard_bypass = False
        # Set while the save path field is put back after a cancelled load
        self._suppress_path_load = False
        self._auto_detect_running = False
        self._tab_build_job: str | None = None

        self._bind_select_all()
        self.setup_ui()

        # Keep the "default game" button in sync with the Settings tab
        self.settings.add_listener(self._on_setting_changed)

        # Placed after scaling is applied so the scaled size is used
        self._normal_geometry: str | None = None
        self._compact = False
        self._game_row_inline = False
        self._header_narrow = False
        self._restore_window_state()
        self.root.after(100, lambda: style_window_frame(self.root, dialog=False))

        self.theme_manager.apply_tk_widget_colors(self.root)

        self.root.bind("<Configure>", self._on_window_resize)

        # Show external-modification dialog when the user refocuses the main
        # window or one of its popups (world map, editor dialogs)
        self.root.bind_all("<FocusIn>", self._on_window_focus, add="+")

        self.root.after(2000, self._init_process_monitor)

        # Check for updates asynchronously (don't block UI startup)
        self.root.after(1000, self._check_for_updates)

    def _bind_select_all(self) -> None:
        """Make Ctrl+A select all text in entries and text boxes.

        Tk on X11 binds Ctrl+A to "line start" (emacs style) instead. Class
        bindings cover every CTk entry, combobox and textbox. macOS keeps its
        own convention (Command+A selects all, Ctrl+A is line start).
        """
        if sys.platform == "darwin":
            return

        def select_entry(event):
            event.widget.select_range(0, "end")
            event.widget.icursor("end")
            return "break"

        def select_text(event):
            event.widget.tag_add("sel", "1.0", "end-1c")
            event.widget.mark_set("insert", "end-1c")
            return "break"

        for sequence in ("<Control-a>", "<Control-A>"):
            for widget_class in ("Entry", "TEntry", "Spinbox", "TSpinbox", "TCombobox"):
                self.root.bind_class(widget_class, sequence, select_entry)
            self.root.bind_class("Text", sequence, select_text)

    def _get_default_game_key(self) -> str:
        """Return the saved default game key, falling back to Elden Ring."""
        key = self.settings.get("default_game", "elden_ring")
        return key if key in PROFILES_BY_KEY else "elden_ring"

    def _set_default_game(self) -> None:
        """Save the currently selected game as the one opened at startup."""
        self.settings.set("default_game", self.active_game)

    def _update_default_game_button(self) -> None:
        """Show whether the selected game is the startup default."""
        if not hasattr(self, "_default_game_btn"):
            return
        is_default = self.active_game == self._get_default_game_key()
        self._default_game_btn.configure(
            text="Default game" if is_default else "Set as default",
            state="disabled" if is_default else "normal",
        )

    def _on_setting_changed(self, key: str | None) -> None:
        """Settings listener; None means any key may have changed."""
        if key in ("default_game", None):
            self._update_default_game_button()

    @staticmethod
    def _scale_tk_fonts(scale: float) -> None:
        """Scale the three named tk fonts used by ttk/tk widgets.

        CTk handles its own font scaling, but ttk.Treeview, ttk.Label,
        tk.Text and similar widgets use the tk named fonts which are unaffected
        by set_widget_scaling. Multiplying their size here keeps them in sync.
        """
        for name in ("TkDefaultFont", "TkTextFont", "TkFixedFont"):
            try:
                f = tkfont.nametofont(name)
                f.configure(size=round(f.actual("size") * scale))
            except Exception:
                pass

    def _on_window_resize(self, event=None):
        """Debounce window resize events to improve responsiveness"""
        # The binding on the root also receives every child widget's
        # Configure event
        if event is None or event.widget is not self.root:
            return

        # Only process if size actually changed (skip if just movement)
        width = event.width
        height = event.height

        if width == self._last_width and height == self._last_height:
            return

        self._last_width = width
        self._last_height = height

        if self._resize_timer:
            self.root.after_cancel(self._resize_timer)

        # Delay actual processing to batch multiple resize events
        self._resize_timer = self.root.after(200, self._process_resize)

    def _process_resize(self):
        """Process pending resize - CTk handles its own layout."""
        self._resize_timer = None
        if not self._is_maximized():
            self._normal_geometry = self.root.geometry()
        self._update_compact_header()

    def _update_compact_header(self) -> None:
        """Compact header below _COMPACT_HEIGHT (logical px), e.g. 1280x800.

        Hides the subtitle and the "Select a save file" label, moves the game
        selector into the save path row and tightens the button row, which
        leaves about 110 px more for the tab content.
        """
        if not self.root.winfo_ismapped():
            return
        height = self.root.winfo_height() / self.root._get_window_scaling()
        compact = height < _COMPACT_HEIGHT
        if compact != self._compact:
            self._compact = compact
            if compact:
                self._subtitle_label.pack_forget()
                self._title_label.pack_configure(pady=(14, 14))
                self._select_save_label.pack_forget()
                self._path_frame.pack_configure(pady=(10, 0))
                self._buttons_frame.pack_configure(pady=(4, 8))
                for child in self._buttons_frame.pack_slaves():
                    child.pack_configure(pady=4)
                for child in self._path_frame.pack_slaves():
                    if child is not self._game_row:
                        child.pack_configure(pady=6)
            else:
                self._title_label.pack_configure(pady=(10, 2))
                self._subtitle_label.pack(pady=(0, 10))
                self._select_save_label.pack(
                    anchor="w", padx=12, pady=(4, 4), before=self._path_frame
                )
                self._path_frame.pack_configure(pady=(0, 12))
                self._buttons_frame.pack_configure(pady=(6, 10))
                for child in self._buttons_frame.pack_slaves():
                    child.pack_configure(pady=10)
                for child in self._path_frame.pack_slaves():
                    if child is not self._game_row:
                        child.pack_configure(pady=10)
        self._place_game_row()
        self._fit_header_buttons()
        self._fit_tab_labels()

    def _place_game_row(self) -> None:
        """Game selector inside the save path row when compact and it fits
        there next to the path buttons, else on its own row above."""
        self.root.update_idletasks()
        path_buttons = [
            c for c in self._path_frame.pack_slaves() if c is not self._game_row
        ]
        # Room the path entry keeps, plus the row's paddings
        spare = round(320 * self.root._get_window_scaling())
        needed = (
            self._game_row.winfo_reqwidth()
            + sum(c.winfo_reqwidth() for c in path_buttons)
            + spare
        )
        inline = self._compact and needed <= self._path_frame.winfo_width()
        if inline == self._game_row_inline:
            return
        self._game_row_inline = inline
        self._game_row.pack_forget()
        if inline:
            self._game_row.pack(
                in_=self._path_frame,
                side=tk.LEFT,
                padx=(8, 8),
                pady=6,
                before=self._path_entry,
            )
            # Created before path_frame, so it would be drawn underneath it
            self._game_row.lift(self._path_frame)
        else:
            self._game_row.pack(
                in_=self._game_row.master,
                fill=tk.X,
                padx=12,
                pady=(10 if self._compact else 12, 4),
                before=self._select_save_label
                if self._select_save_label.winfo_manager()
                else self._path_frame,
            )

    def _fit_header_buttons(self) -> None:
        """Narrower header buttons when the full widths do not fit the row."""
        self.root.update_idletasks()
        scale = self.root._get_window_scaling()
        shown = [(b, w) for b, w in self._header_buttons if b.winfo_manager() == "pack"]
        full = sum(round((w + 12) * scale) for _b, w in shown)
        narrow = full > self._buttons_frame.winfo_width()
        if narrow == self._header_narrow:
            return
        self._header_narrow = narrow
        for button, width in self._header_buttons:
            button.configure(width=_NARROW_HEADER_BUTTON if narrow else width)

    def _fit_tab_labels(self) -> None:
        """Short tab labels when the full names do not fit the window width.

        Only the button text changes; the tab names used by the code stay.
        """
        segmented = self.notebook._segmented_button
        buttons = segmented._buttons_dict
        if not buttons:
            return
        self.root.update_idletasks()
        # Width with the full names = current width + the text width they add
        font = tkfont.Font(font=next(iter(buttons.values()))._text_label.cget("font"))
        full = segmented.winfo_reqwidth() + sum(
            font.measure(name) - font.measure(button.cget("text"))
            for name, button in buttons.items()
        )
        short = full > self.notebook.winfo_width() - round(
            24 * self.root._get_window_scaling()
        )
        for name, button in buttons.items():
            text = _SHORT_TAB_NAMES.get(name, name) if short else name
            if button.cget("text") != text:
                button.configure(text=text)

    def _is_maximized(self) -> bool:
        try:
            if sys.platform.startswith("linux"):
                return bool(self.root.attributes("-zoomed"))
            return self.root.state() == "zoomed"
        except tk.TclError:
            return False

    def _maximize(self) -> None:
        try:
            if sys.platform.startswith("linux"):
                self.root.attributes("-zoomed", True)
            else:
                self.root.state("zoomed")
        except tk.TclError:
            pass

    def _restore_window_state(self) -> None:
        """Reopen the main window as it was closed, if it still fits.

        window_state holds the logical size (before UI scaling), the physical
        x/y of the frame and the maximized flag. The position is restored on
        Windows only: X11 window managers place new windows themselves, and
        Tk reports the client origin there while geometry() sets the frame,
        so a restored position would move down by the title bar every start.
        A saved size or position that no longer fits a work area (monitor
        removed, scale or resolution changed) falls back to the default size
        centered on the work area.
        """
        min_w, min_h = fit_size_to_work_area(self.root, 800, 700)
        self.root.minsize(min_w, min_h)

        state = self.settings.get("window_state") or {}
        try:
            w, h, x, y = (int(state[k]) for k in ("width", "height", "x", "y"))
        except (KeyError, TypeError, ValueError):
            w = h = x = y = None
        if w is None:
            center_window(self.root, 1200, 1000)
        elif sys.platform != "win32":
            if fit_size_to_work_area(self.root, w, h) == (w, h):
                center_window(self.root, w, h)
            else:
                center_window(self.root, 1200, 1000)
        elif self._fits_work_area(w, h, x, y):
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        else:
            center_window(self.root, 1200, 1000)
        if state.get("maximized"):
            # After the first map; CTk shows the window once mainloop starts
            self.root.after(50, self._maximize)

    def _fits_work_area(self, width: int, height: int, x: int, y: int) -> bool:
        """Whether the framed window at (x, y) lies inside one monitor's work area."""
        scale = self.root._get_window_scaling()
        phys_w, phys_h = round(width * scale), round(height * scale)
        outer_h = phys_h + title_bar_height(self.root)
        wx, wy, ww, wh = get_work_area(self.root, (x + phys_w // 2, y + outer_h // 2))
        return wx <= x and wy <= y and x + phys_w <= wx + ww and y + outer_h <= wy + wh

    def save_window_state(self) -> None:
        """Store size, position and maximized state for the next start."""
        try:
            maximized = self._is_maximized()
            geometry = self._normal_geometry if maximized else self.root.geometry()
            state = dict(self.settings.get("window_state") or {})
            state["maximized"] = maximized
            m = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$", geometry or "")
            if m and self.root.state() != "iconic":
                w, h, x, y = (int(v) for v in m.groups())
                state.update(width=w, height=h, x=x, y=y)
            self.settings.set("window_state", state)
        except tk.TclError:
            pass

    def _check_for_updates(self):
        """Check for application updates in a background thread"""

        def check_in_thread():
            try:
                if not self.settings.get("show_update_notifications", True):
                    return

                checker = VersionChecker(__version__)
                has_update, latest_version, download_url = checker.check_for_updates()

                if has_update and latest_version and download_url:
                    # Schedule the dialog to show on the main thread
                    self.root.after(
                        0,
                        lambda: self._show_update_dialog(latest_version, download_url),
                    )

            except Exception as e:
                print(f"Update check failed: {e}")

        import threading

        thread = threading.Thread(target=check_in_thread, daemon=True)
        thread.start()

    def _handle_game_running_dialog(self, profile=None) -> bool:
        """
        Show dialog when game is running and handle user choice.
        Blocks loading until game process is terminated.

        Returns:
            True if game was successfully terminated
            False if user cancelled or kill failed
        """
        game_name = profile.name if profile else "Elden Ring"
        process_name = (
            profile.process_name
            if profile and profile.process_name
            else "eldenring.exe"
        )

        result = CTkMessageBox.askyesno(
            "Game Is Running",
            f"{game_name} is currently running.\n\n"
            "The save file cannot be loaded while the game is running.\n\n"
            "Would you like to force kill the game process?",
            parent=self.root,
        )

        if not result:
            return False

        if not PlatformUtils.kill_game_process(process_name):
            CTkMessageBox.showerror(
                "Terminate Failed",
                f"Failed to terminate {game_name} process.\n\n"
                "The game may require manual closing or administrator permissions.",
                parent=self.root,
            )
            return False

        import time

        max_wait = 5
        wait_interval = 0.2
        elapsed = 0

        while elapsed < max_wait:
            if not self.is_game_running(process_name):
                self.show_toast(f"{game_name} closed. You can now proceed safely.")
                return True
            time.sleep(wait_interval)
            elapsed += wait_interval
            self.root.update()

        CTkMessageBox.showerror(
            "Timeout",
            f"Game process is still running after kill attempt.\n\n"
            f"Close {game_name} manually and try again.",
            parent=self.root,
        )
        return False

    def _init_process_monitor(self):
        """Initialize auto-backup process monitor"""
        try:
            from er_save_manager.backup.process_monitor import GameProcessMonitor

            # Start process monitor (first-run dialog moved to backup manager tab)
            self.process_monitor = GameProcessMonitor()
            self.process_monitor.set_backup_callback(self._on_auto_backup_created)
            self.process_monitor.start()

        except Exception as e:
            print(f"Failed to initialize process monitor: {e}")

    def _on_auto_backup_created(self, game_key: str, backup_path):
        """Callback when auto-backup is created."""
        try:
            if not self.settings.get("show_auto_backup_notification", True):
                return

            from er_save_manager.games.game_profiles import PROFILES_BY_KEY

            profile = PROFILES_BY_KEY.get(game_key)
            game_name = profile.name if profile else game_key

            self.root.after(
                0,
                lambda: self.show_toast(
                    f"{game_name} launched - backup created: {backup_path.name}"
                ),
            )
        except Exception:
            pass

    def show_toast(self, message: str, duration: int = 3000, type: str = "success"):
        """Show toast notification"""
        from er_save_manager.ui.toast import show_toast as _show_toast

        _show_toast(self.root, message, duration, type)

    def _show_update_dialog(self, latest_version: str, download_url: str):
        """Show update available dialog with GitHub and Nexus Mods download options"""
        from er_save_manager.ui import dialog_style as ds

        dialog = ds.create(self.root, "Update Available")
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=16)

        dont_show_var = ctk.BooleanVar(value=False)

        def on_close():
            if dont_show_var.get():
                self.settings.set("show_update_notifications", False)
            dialog.destroy()

        def open_github():
            open_url(download_url)
            dialog.destroy()

        def open_nexus():
            open_url("https://www.nexusmods.com/eldenring/mods/9271?tab=files")
            dialog.destroy()

        from er_save_manager.ui.utils import icon_image

        _, (github_btn, nexus_btn, _) = ds.button_row(
            main_frame,
            [
                {"text": "GitHub Releases", "command": open_github, "width": 150},
                {"text": "Nexus Mods", "command": open_nexus, "width": 130},
                {"text": "Close", "command": on_close, "primary": False},
            ],
        )
        github_icon = icon_image("github", 18)
        if github_icon:
            github_btn.configure(image=github_icon, compound="left")
        nexus_icon = icon_image("nexusmods", 18)
        if nexus_icon:
            nexus_btn.configure(image=nexus_icon, compound="left")

        header = ctk.CTkFrame(main_frame, fg_color="transparent")
        header.pack(fill=ctk.X)
        update_icon = icon_image("update", 34)
        ctk.CTkLabel(
            header,
            text="" if update_icon else "↑",
            image=update_icon,
            font=("Inter SemiBold", 24),
            text_color=palette.PURPLE_TEXT,
        ).pack(side=ctk.LEFT, padx=(0, 10))
        ctk.CTkLabel(header, text="Update Available", font=("Inter", 19, "bold")).pack(
            side=ctk.LEFT
        )
        versions = ds.box(main_frame, pady=(12, 10))
        for i, (label, value) in enumerate(
            (("Current version", __version__), ("Latest version", latest_version))
        ):
            ctk.CTkLabel(
                versions, text=label, font=("Inter", 14), text_color=ds.MUTED
            ).grid(
                row=i,
                column=0,
                sticky="w",
                padx=(12, 24),
                pady=(8 if i == 0 else 2, 8 if i else 2),
            )
            ctk.CTkLabel(versions, text=value, font=("Inter", 14, "bold")).grid(
                row=i,
                column=1,
                sticky="w",
                padx=(0, 12),
                pady=(8 if i == 0 else 2, 8 if i else 2),
            )
        ctk.CTkCheckBox(
            main_frame,
            text="Don't show update notifications in the future",
            variable=dont_show_var,
            font=ds.FONT,
        ).pack(anchor=ctk.W)
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        ds.finish(dialog, self.root, min_width=420)

    def _open_kofi(self):
        """Open Ko-fi support page in browser."""
        open_url("https://ko-fi.com/hapfell")

    def _open_discord(self):
        """Open Discord server invite in browser."""
        open_url("https://dsc.gg/er-saveman")

    def _open_youtube(self):
        """Open YouTube guide in browser."""
        open_url("https://www.youtube.com/watch?v=OHhM7BF72eg")

    def setup_ui(self):
        """Setup main UI structure with optimized layout"""
        self.root.grid_rowconfigure(0, weight=0)  # Title
        self.root.grid_rowconfigure(1, weight=0)  # File selection
        self.root.grid_rowconfigure(2, weight=0)  # Character bar
        self.root.grid_rowconfigure(3, weight=1)  # Main content (tabs)
        self.root.grid_rowconfigure(4, weight=0)  # Unapplied changes bar
        self.root.grid_rowconfigure(5, weight=0)  # Status bar
        self.root.grid_columnconfigure(0, weight=1)

        title_frame = ctk.CTkFrame(self.root, corner_radius=12)
        title_frame.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")

        support_btn = ctk.CTkButton(
            title_frame,
            text="☕ Support me",
            command=self._open_kofi,
            width=100,
            height=32,
            font=("Inter", 11),
        )
        support_btn.place(relx=1.0, x=-12, y=12, anchor="ne")

        discord_btn = ctk.CTkButton(
            title_frame,
            text="Discord Server",
            command=self._open_discord,
            width=100,
            height=32,
            font=("Inter", 11),
        )
        discord_btn.place(relx=0.0, x=12, y=12, anchor="nw")

        youtube_btn = ctk.CTkButton(
            title_frame,
            text="Video Guide",
            command=self._open_youtube,
            width=100,
            height=32,
            font=("Inter", 11),
        )
        youtube_btn.place(relx=0.0, x=124, y=12, anchor="nw")

        self._title_label = ctk.CTkLabel(
            title_frame,
            text="Elden Ring Save Manager",
            font=("Inter", 20, "bold"),
        )
        self._title_label.pack(pady=(10, 2))

        self._subtitle_label = ctk.CTkLabel(
            title_frame,
            text="Complete save editor, backup manager, and corruption fixer",
            font=("Inter", 11),
        )
        self._subtitle_label.pack(pady=(0, 10))

        file_frame = ctk.CTkFrame(self.root, corner_radius=12)
        file_frame.grid(row=1, column=0, padx=12, pady=10, sticky="ew")

        game_row = ctk.CTkFrame(file_frame, fg_color="transparent")
        game_row.pack(fill=tk.X, padx=12, pady=(12, 4))
        self._game_row = game_row

        ctk.CTkLabel(game_row, text="Game:", font=("Inter", 11)).pack(
            side=tk.LEFT, padx=(0, 8)
        )

        self._game_selector_var = tk.StringVar(
            value=PROFILES_BY_KEY[self.active_game].name
        )
        game_names = [p.name for p in GAME_PROFILES]
        self._game_combo = ctk.CTkComboBox(
            game_row,
            values=game_names,
            variable=self._game_selector_var,
            state="readonly",
            width=260,
            command=self._on_game_changed,
        )
        self._game_combo.pack(side=tk.LEFT)

        self._default_game_btn = ctk.CTkButton(
            game_row,
            text="",
            width=130,
            command=self._set_default_game,
        )
        self._default_game_btn.pack(side=tk.LEFT, padx=(8, 0))
        self._update_default_game_button()

        self._extension_btn = ctk.CTkButton(
            game_row,
            text="Change Extension",
            command=self._open_extension_copy,
            width=150,
        )
        if self.active_game in SUPPORTED_EXTENSION_GAMES:
            self._extension_btn.pack(side=tk.RIGHT, padx=(8, 4))

        self._select_save_label = ctk.CTkLabel(
            file_frame,
            text="Select a save file",
            font=("Inter", 12, "bold"),
        )
        self._select_save_label.pack(anchor="w", padx=12, pady=(4, 4))

        self.file_path_var = tk.StringVar(value="")
        # Auto-load when valid file path is entered
        trace_variable(self.file_path_var, "w", self._on_file_path_changed)

        path_frame = ctk.CTkFrame(file_frame, corner_radius=8)
        path_frame.pack(fill=tk.X, padx=12, pady=(0, 12))
        self._path_frame = path_frame

        self._path_entry = ctk.CTkEntry(path_frame, textvariable=self.file_path_var)
        self._path_entry.pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), pady=10
        )

        _browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse",
            command=self.browse_file,
            width=110,
        )
        _browse_btn.pack(side=tk.LEFT, padx=4, pady=10)
        self._file_load_buttons.append(_browse_btn)

        _autofind_btn = ctk.CTkButton(
            path_frame,
            text="Auto-Find",
            command=self.auto_detect,
            width=110,
        )
        _autofind_btn.pack(side=tk.LEFT, padx=4, pady=10)
        self._file_load_buttons.append(_autofind_btn)

        buttons_frame = ctk.CTkFrame(file_frame, corner_radius=8)
        buttons_frame.pack(fill=tk.X, pady=(6, 10), padx=12)
        self._buttons_frame = buttons_frame

        _reload_btn = ctk.CTkButton(
            buttons_frame,
            text="Reload",
            command=self.load_save,
            width=160,
        )
        _reload_btn.pack(side=tk.LEFT, padx=6, pady=10)
        self._file_load_buttons.append(_reload_btn)

        _backup_btn = ctk.CTkButton(
            buttons_frame,
            text="Backup Manager",
            command=self.show_backup_manager_standalone,
            width=160,
        )
        _backup_btn.pack(side=tk.LEFT, padx=6, pady=10)

        _troubleshoot_btn = ctk.CTkButton(
            buttons_frame,
            text="Troubleshooting",
            command=self.open_troubleshooting,
            width=160,
        )
        _troubleshoot_btn.pack(side=tk.RIGHT, padx=6, pady=10)

        self._ps_save_btn = ctk.CTkButton(
            buttons_frame,
            text=_console_button_text(self.active_game),
            command=self.show_console_save_info,
            width=160,
        )
        if self.active_game in _CONSOLE_SAVE_GAMES:
            self._ps_save_btn.pack(side=tk.RIGHT, padx=6, pady=10)

        _itemgib_btn = ctk.CTkButton(
            buttons_frame,
            text="Item Gib",
            command=self._open_inventory_editor,
            width=200,
        )
        _itemgib_btn.pack(side=tk.RIGHT, padx=6, pady=10)
        self._file_load_buttons.append(_itemgib_btn)
        # (button, full width) for _fit_header_buttons
        self._header_buttons = [
            (_reload_btn, 160),
            (_backup_btn, 160),
            (_troubleshoot_btn, 160),
            (self._ps_save_btn, 160),
            (_itemgib_btn, 200),
        ]

        self.character_bar = CharacterBar(self.root, self._on_character_selected)
        self.pending_bar = PendingBar(
            self.root,
            get_slot=lambda: self.character_bar.index,
            backup=self._pending_backup,
            write=self._pending_write,
            blocks_write=self._pending_blocks_write,
            after_apply=self._after_apply,
            reload_from_disk=self._reload_after_failed_apply,
            show_toast=self.show_toast,
            on_visibility=self._show_pending_bar,
        )

        self.notebook = ctk.CTkTabview(
            self.root,
            width=1100,
            height=620,
            corner_radius=12,
            command=self._on_tab_changed,
        )
        self._grid_notebook()

        if self.active_game == "elden_ring":
            self.create_tabs()
        else:
            self._create_other_game_tabs(PROFILES_BY_KEY[self.active_game])
        self._place_character_bar()

        status_frame = ctk.CTkFrame(self.root, corner_radius=0)
        status_frame.grid(row=5, column=0, sticky="ew")

        ctk.CTkLabel(
            status_frame,
            textvariable=self.status_var,
            anchor="w",
            padx=8,
            pady=6,
        ).pack(fill=tk.X)

    def _open_extension_copy(self):
        """Copy the loaded save to another extension (vanilla / Seamless Co-op /
        Convergence / custom)."""
        from er_save_manager.ui.dialogs.extension_copy import open_extension_copy

        profile = PROFILES_BY_KEY[self.active_game]
        open_extension_copy(
            self.root,
            self.active_game,
            self.save_path,
            on_done=lambda message: self.show_toast(message, duration=4000),
            is_game_running=lambda: (
                not self.settings.get("skip_game_running_check", False)
                and self.is_game_running(profile.process_name)
            ),
        )

    # ------------------------------------------------------------------
    # Character bar and unapplied changes
    # ------------------------------------------------------------------

    def _grid_notebook(self) -> None:
        self.notebook.grid(row=3, column=0, padx=12, pady=(6, 10), sticky="nsew")

    def _place_character_bar(self) -> None:
        """Show the character bar for games with character tabs."""
        if self._character_tabs:
            self.character_bar.grid(row=2, column=0, padx=12, pady=0, sticky="ew")
        else:
            self.character_bar.grid_remove()
        self._update_character_bar_state()

    def _update_character_bar_state(self) -> None:
        try:
            current = self.notebook.get()
        except Exception:
            current = ""
        self.character_bar.set_active(current in self._character_tabs)
        self.character_bar.set_links(self._feature_links.get(current, []))

    def _feature(
        self, tab: str, open_feature: Callable[[], None]
    ) -> Callable[[], None]:
        """Action of a feature link: show the tab, then open the feature."""

        def run() -> None:
            self._flush_pending_tabs()
            if self.notebook.get() != tab:
                self.notebook.set(tab)
                self._on_tab_changed()
            open_feature()

        return run

    def _show_editor_sub(self, sub: str) -> None:
        """Select sub in the active game's Character Editor sub-tabs."""
        if self.active_game == "elden_ring":
            self._er_editor_tabs.set(sub)
            self._ensure_tab_built(f"Character Editor/{sub}")
            return
        attr = {
            "dark_souls_3": "ds3_editor_tab",
            "dark_souls_remastered": "dsr_editor_tab",
            "dark_souls_2": "ds2_editor_tab",
        }.get(self.active_game)
        editor = getattr(self, attr, None) if attr else None
        if editor is not None:
            editor.select(sub)

    def _editor_feature(
        self, sub: str, open_feature: Callable[[], None]
    ) -> Callable[[], None]:
        """Action of a feature link on a Character Editor sub-tab."""

        def open_sub() -> None:
            self._show_editor_sub(sub)
            open_feature()

        return self._feature("Character Editor", open_sub)

    def _register_appearance(self, host: CharacterPagesTab) -> None:
        """Pending page for the Appearance page of host, built later."""

        def changes() -> int:
            page = host.pages.get("Appearance")
            return page.changes() if page is not None else 0

        def discard() -> None:
            page = host.pages.get("Appearance")
            if page is not None:
                page.discard()

        self._pending_register("Appearance")(
            PendingPage(
                "Appearance",
                changes,
                lambda: host.pages["Appearance"].prepare(),
                discard,
            )
        )

    def _set_er_feature_links(self) -> None:
        editor = self._editor_feature
        self._feature_links = {
            "Character Editor": [
                (
                    "Visual Item Picker",
                    editor(
                        "Inventory", lambda: self.inventory_editor._open_icon_browser()
                    ),
                ),
                (
                    "Visual Inventory",
                    editor(
                        "Inventory",
                        lambda: self.inventory_editor._open_visual_inventory(),
                    ),
                ),
                (
                    "Equipment Share Codes",
                    editor(
                        "Equipment", lambda: self.equipment_editor.share_loadout_code()
                    ),
                ),
            ],
            "Appearance": [
                (
                    "Community Presets",
                    self._feature(
                        "Appearance", lambda: self.appearance_tab.open_preset_browser()
                    ),
                ),
            ],
            "Character Management": [
                (
                    "Community Characters",
                    self._feature(
                        "Character Management",
                        lambda: self.char_mgmt_tab.open_character_browser(),
                    ),
                ),
            ],
            "World State": [
                (
                    "World Map",
                    self._feature(
                        "World State", lambda: self.world_tab._open_map_window()
                    ),
                ),
                (
                    "Messages",
                    self._feature(
                        "World State", lambda: self.world_tab._open_message_manager()
                    ),
                ),
            ],
        }

    def _show_pending_bar(self, shown: bool) -> None:
        if shown:
            self.pending_bar.grid(row=4, column=0, padx=12, pady=(0, 10), sticky="ew")
        else:
            self.pending_bar.grid_remove()

    def _pending_register(self, tab_name: str) -> Callable[[PendingPage], None]:
        """Register function for one tab's pages; showing a page also selects
        the tab."""

        def register(page: PendingPage) -> None:
            inner = page.show

            def show() -> None:
                self._ensure_tab_built(tab_name)
                self.notebook.set(tab_name)
                self._on_tab_changed()
                if inner is not None:
                    inner()

            self.pending_bar.register(replace(page, show=show))

        return register

    def _guard_pending(self, action: str) -> bool:
        """Ask before an action that drops unapplied edits. A cancelled load
        puts the loaded save's path back into the path field."""
        if self._guard_bypass or self.pending_bar.guard(action):
            return True
        loaded = str(self.save_path) if self.save_path else ""
        if self.file_path_var.get() != loaded:
            self._suppress_path_load = True
            self.file_path_var.set(loaded)
            self._suppress_path_load = False
        return False

    def _slot_entries(self) -> list[tuple[int, str, bool]]:
        """(slot index, label, holds a character) for the character bar."""
        game = self.active_game
        if game == "elden_ring" and self.save_file is not None:
            save = self.save_file
            profiles = None
            try:
                profiles = save.user_data_10_parsed.profile_summary.profiles
            except Exception:
                pass
            # Deleted characters keep their slot data and profile summary
            # entry until a new character is created in the slot, so only
            # slots marked active in the profile summary hold a character.
            active = set(save.get_active_slots())
            entries = []
            for i in range(10):
                if save.characters[i].is_empty() or i not in active:
                    entries.append((i, f"Slot {i + 1} - Empty", False))
                    continue
                name = "Unknown"
                if profiles and i < len(profiles):
                    name = getattr(profiles[i], "character_name", "") or "Unknown"
                entries.append((i, f"Slot {i + 1} - {name}", True))
            return entries
        save = {
            "dark_souls_3": self.ds3_save,
            "dark_souls_remastered": self.dsr_save,
        }.get(game)
        if save is not None:
            return [
                (
                    i,
                    f"Slot {i + 1} - {c.name}" if c else f"Slot {i + 1} - Empty",
                    bool(c),
                )
                for i, c in enumerate(save.characters)
            ]
        if game == "dark_souls_2" and self.ds2_save is not None:
            from er_save_manager.games.DS2.editor_tab import slot_entries
            from er_save_manager.games.DS2.save import SlotState

            return [
                (i, label, self.ds2_save.slot_state(i) is not SlotState.NEVER_CREATED)
                for i, label in slot_entries(self.ds2_save)
            ]
        if game == "nightreign" and self._nr_save is not None:
            return [
                (
                    i,
                    f"Slot {i + 1} - {slot.player_name}"
                    if slot.player_name
                    else f"Slot {i + 1} - Empty",
                    bool(slot.player_name),
                )
                for i, slot in enumerate(self._nr_save.slots)
            ]
        return []

    def _slot_detail(self, slot_idx: int) -> str:
        """Level shown next to the character bar."""
        if slot_idx < 0:
            return ""
        try:
            game = self.active_game
            if game == "elden_ring" and self.save_file is not None:
                level = self.save_file.characters[slot_idx].player_game_data.level
            elif game == "dark_souls_3" and self.ds3_save is not None:
                level = self.ds3_save.characters[slot_idx].level
            elif game == "dark_souls_remastered" and self.dsr_save is not None:
                level = self.dsr_save.characters[slot_idx].level
            elif game == "dark_souls_2" and self.ds2_save is not None:
                level = self.ds2_save.characters[slot_idx].get_stat("level")
            else:
                return ""
        except Exception:
            return ""
        return f"Level {level}"

    def _refresh_character_bar(self) -> None:
        """List the loaded save's characters and load the selected one, or
        the first character when the selected slot is empty."""
        entries = self._slot_entries()
        current = self.character_bar.index
        used = [i for i, _label, holds in entries if holds]
        if current not in used:
            current = used[0] if used else (entries[0][0] if entries else -1)
        self.character_bar.set_slots([(i, label) for i, label, _h in entries], current)
        world = getattr(self, "world_tab", None)
        if self.active_game == "elden_ring" and world is not None:
            world.set_slot_labels(self.character_bar.labels)
        self._load_character(current)

    def _load_character(self, slot_idx: int) -> None:
        """Show the character in slot_idx in every character tab."""
        self._flush_pending_tabs()
        self.selected_slot_index = slot_idx
        self.character_bar.set_detail(self._slot_detail(slot_idx))
        for name, load in self._character_tabs.items():
            try:
                load(slot_idx)
            except Exception:
                _log.exception("Loading slot %s into %s failed", slot_idx, name)

    def _on_character_selected(self, slot_idx: int) -> bool:
        """Character picked in the bar; False keeps the previous one."""
        if not self._guard_pending("switch characters"):
            return False
        self._load_character(slot_idx)
        return True

    def _select_character(self, slot_idx: int) -> bool:
        """Pick a character for the bar from elsewhere (inspector, map)."""
        if slot_idx == self.character_bar.index:
            return True
        if not self._on_character_selected(slot_idx):
            return False
        self.character_bar.select(slot_idx)
        return True

    def _active_save(self):
        return {
            "elden_ring": self.save_file,
            "dark_souls_3": self.ds3_save,
            "dark_souls_remastered": self.dsr_save,
            "dark_souls_2": self.ds2_save,
            "nightreign": self._nr_save,
        }.get(self.active_game)

    def _pending_backup(self, slot: int, changes: str) -> None:
        from er_save_manager.backup.manager import BackupManager

        if self.save_path is None or self._active_save() is None:
            raise RuntimeError("No save file loaded")
        BackupManager(Path(self.save_path)).create_backup(
            description=f"Slot {slot + 1}: {changes}",
            operation="apply_changes",
            save=self.save_file if self.active_game == "elden_ring" else None,
        )

    def _pending_write(self) -> None:
        save, path = self._active_save(), Path(self.save_path)
        if self.active_game == "elden_ring":
            if isinstance(save._raw_data, bytes):
                save._raw_data = bytearray(save._raw_data)
            save.recalculate_checksums()
            save.to_file(path)
        elif self.active_game == "nightreign":
            save.write_file(path)
        else:
            save.save_to_file(path)
        self.acknowledge_save_written()

    def _pending_blocks_write(self) -> bool:
        from er_save_manager.ui.utils import game_blocks_write

        profile = self._active_profile()
        if profile is None or not profile.process_name:
            return False
        return game_blocks_write(self.root, profile.process_name, profile.name)

    def _after_apply(self) -> None:
        """Reload the character into every tab after Apply All; names and
        levels in the bar may have changed."""
        self._refresh_character_bar()

    def _reload_after_failed_apply(self) -> None:
        """Re-read the save from disk; the in-memory one holds partial
        writes."""
        if self.save_path is None:
            return
        path = str(self.save_path)
        self._guard_bypass = True
        try:
            if self.active_game == "elden_ring":
                self.load_save(silent=True)
            elif self.active_game == "dark_souls_3":
                self._load_ds3_save(path)
            elif self.active_game == "dark_souls_remastered":
                self._load_dsr_save(path)
            elif self.active_game == "dark_souls_2":
                self._load_ds2_save(path)
            elif self.active_game == "nightreign":
                self._load_nr_save(path)
        finally:
            self._guard_bypass = False

    def _on_game_changed(self, _value=None):
        """Rebuild notebook tabs for the newly selected game."""
        name = self._game_selector_var.get()
        profile = next((p for p in GAME_PROFILES if p.name == name), None)
        if profile is None or profile.key == self.active_game:
            return
        if not self.pending_bar.guard("switch games"):
            self._game_selector_var.set(PROFILES_BY_KEY[self.active_game].name)
            return

        self.active_game = profile.key
        self._update_default_game_button()

        if hasattr(self, "_ps_save_btn"):
            if profile.key in _CONSOLE_SAVE_GAMES:
                self._ps_save_btn.configure(text=_console_button_text(profile.key))
                self._ps_save_btn.pack(
                    side=tk.RIGHT, padx=6, pady=4 if self._compact else 10
                )
            else:
                self._ps_save_btn.pack_forget()

        if hasattr(self, "_extension_btn"):
            if profile.key in SUPPORTED_EXTENSION_GAMES:
                self._extension_btn.pack(side=tk.RIGHT, padx=(8, 4))
            else:
                self._extension_btn.pack_forget()

        # Clear save state - switching games means the loaded save is no longer relevant.
        # This prevents tab setup_ui() calls from accessing stale save data.
        self.save_file = None
        self.save_path = None
        self._pending_file_change = False
        self.file_path_var.set("")

        # Null out all tab references so _finalize_save_load doesn't call methods
        # on widgets that are about to be destroyed.
        self.dsr_save = None
        self.ds3_save = None
        self.ds2_save = None
        self._nr_save = None

        for attr in (
            "inspector_tab",
            "char_mgmt_tab",
            "world_tab",
            "event_flags_tab",
            "gestures_tab",
            "appearance_tab",
            "steamid_tab",
            "hex_tab",
            "advanced_tab",
            "settings_tab",
            "dsr_inspector_tab",
            "dsr_editor_tab",
            "dsr_appearance_tab",
            "dsr_npc_tab",
            "dsr_world_tab",
            "dsr_flags_tab",
            "dsr_char_mgmt_tab",
            "ds3_inspector_tab",
            "ds3_editor_tab",
            "ds3_appearance_tab",
            "ds3_world_tab",
            "ds3_npcs_bosses_tab",
            "ds3_char_mgmt_tab",
            "ds2_inspector_tab",
            "ds2_editor_tab",
            "ds2_appearance_tab",
            "ds2_world_tab",
            "ds2_npcs_bosses_tab",
            "ds2_management_tab",
            "nr_inspector_tab",
            "nr_editor_tab",
            "nr_steamid_tab",
            "nr_char_mgmt_tab",
        ):
            setattr(self, attr, None)

        self._drop_pending_tabs()
        self.pending_bar.clear_pages()
        self._character_tabs = {}
        self._feature_links = {}
        self.character_bar.set_slots([], -1)
        self.character_bar.set_detail("")
        self.notebook.destroy()
        self.notebook = ctk.CTkTabview(
            self.root,
            width=1100,
            height=620,
            corner_radius=12,
            command=self._on_tab_changed,
        )
        self._grid_notebook()

        self.tabs_loaded = {
            "Save Fixer": False,
            "Appearance": False,
            "Advanced Tools": False,
            "SteamID Patcher": False,
            "Hex Editor": False,
            "Gestures": False,
        }

        if profile.key == "elden_ring":
            self.create_tabs()
        else:
            self._create_other_game_tabs(profile)
        self._place_character_bar()
        # New tab names and header buttons: fit them to the current width
        self.root.after_idle(self._update_compact_header)

    def create_tabs(self):
        """Create all Elden Ring tabs."""

        self.notebook.add("Save Fixer")
        tab_inspector = self.notebook.tab("Save Fixer")
        self.inspector_tab = SaveInspectorTab(
            tab_inspector,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
            self.show_character_details,
            self.on_slot_selected,
        )
        self._build_tab("Save Fixer", self.inspector_tab.setup_ui)

        self.notebook.add("Character Management")
        tab_char_mgmt = self.notebook.tab("Character Management")
        self.char_mgmt_tab = CharacterManagementTab(
            tab_char_mgmt,
            lambda: self.save_file,
            lambda: self.save_path,
            self.reload_save,
            self.show_toast,
            # Read at call time so toggling the advanced setting takes effect
            # without rebuilding the tab.
            lambda: (
                not self.settings.get("skip_game_running_check", False)
                and self.is_game_running()
            ),
        )
        self._build_tab("Character Management", self.char_mgmt_tab.setup_ui)

        self.notebook.add("Character Editor")
        tab_character = self.notebook.tab("Character Editor")
        self._build_tab(
            "Character Editor", lambda: self.setup_character_editor_tab(tab_character)
        )

        self.notebook.add("Appearance")
        tab_appearance = self.notebook.tab("Appearance")
        self.appearance_tab = AppearanceTab(
            tab_appearance,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
            self.show_toast,
        )
        self._build_tab("Appearance", self.appearance_tab.setup_ui)
        self._pending_register("Appearance")(
            PendingPage(
                "Eye overrides",
                self.appearance_tab.eye_changes,
                self.appearance_tab.prepare_eyes,
                self.appearance_tab.discard_eyes,
            )
        )

        self.notebook.add("World State")
        tab_world = self.notebook.tab("World State")
        self.world_tab = WorldStateTab(
            tab_world,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
            lambda: self.selected_slot_index,
            self.show_toast,
        )
        try:
            if getattr(sys, "frozen", False):
                _base = (
                    Path(sys._MEIPASS)
                    if hasattr(sys, "_MEIPASS")
                    else Path(sys.executable).parent
                )
            else:
                _base = Path(__file__).parent.parent.parent
            _maps_dir = _base / "resources" / "maps"
            if (_maps_dir / "maps.json").exists():
                self.world_tab.set_maps_dir(_maps_dir)
        except Exception:
            pass
        self.world_tab.select_character = self._select_character
        self.world_tab.apply_all = self.pending_bar.apply_all
        self._build_tab("World State", self.world_tab.setup_ui)
        self._pending_register("World State")(
            PendingPage(
                "Map markers",
                self.world_tab.marker_changes,
                self.world_tab.prepare_markers,
                self.world_tab.discard_markers,
            )
        )

        self.notebook.add("Event Flags")
        tab_event_flags = self.notebook.tab("Event Flags")
        self.event_flags_tab = EventFlagsTab(
            tab_event_flags,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
            self.show_toast,
        )
        self._build_tab("Event Flags", self.event_flags_tab.setup_ui)
        self._pending_register("Event Flags")(
            PendingPage(
                "Event flags",
                self.event_flags_tab.flag_changes,
                self.event_flags_tab.prepare_flags,
                self.event_flags_tab.discard_flags,
            )
        )

        self.notebook.add("Gestures")
        tab_gestures = self.notebook.tab("Gestures")
        self.gestures_tab = GesturesRegionsTab(
            tab_gestures,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
            self.show_toast,
        )
        self._build_tab("Gestures", self.gestures_tab.setup_ui)
        register = self._pending_register("Gestures")
        register(
            PendingPage(
                "Gestures",
                self.gestures_tab.gesture_changes,
                self.gestures_tab.prepare_gestures,
                self.gestures_tab.discard_gestures,
            )
        )
        register(
            PendingPage(
                "Gesture wheel",
                self.gestures_tab.wheel_changes,
                self.gestures_tab.prepare_wheel,
                self.gestures_tab.discard_wheel,
            )
        )
        self.notebook.add("SteamID Patcher")
        tab_steamid = self.notebook.tab("SteamID Patcher")
        self.steamid_tab = SteamIDPatcherTab(
            tab_steamid,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
            self.show_toast,
        )
        self._build_tab("SteamID Patcher", self.steamid_tab.setup_ui)

        self._character_tabs = {
            "Character Editor": self._er_load_character,
            "Appearance": self.appearance_tab.load_slot,
            "World State": self.world_tab.load_slot,
            "Event Flags": self.event_flags_tab.load_slot,
            "Gestures": self.gestures_tab.load_slot,
        }
        self._set_er_feature_links()

        # Tab 9: Hex Editor - hidden for now
        _hex_hidden = ctk.CTkFrame(self.root, fg_color="transparent")
        self.hex_tab = HexEditorTab(_hex_hidden, lambda: self.save_file)
        self._build_tab("Hex Editor", self.hex_tab.setup_ui)

        self.notebook.add("Advanced Tools")
        tab_advanced = self.notebook.tab("Advanced Tools")
        self.advanced_tab = AdvancedToolsTab(
            tab_advanced,
            lambda: self.save_file,
            lambda: self.save_path,
            self.load_save,
            self.show_toast,
        )
        self._build_tab("Advanced Tools", self.advanced_tab.setup_ui)

        self.notebook.add("Settings")
        tab_settings = self.notebook.tab("Settings")
        self.settings_tab = SettingsTab(
            tab_settings,
            get_save_path_callback=lambda: self.save_path,
            get_default_save_path_callback=lambda: self.default_save_path,
            active_game="elden_ring",
            root=self.root,
        )
        self._build_tab("Settings", self.settings_tab.setup_steps)

    def _create_other_game_tabs(self, profile):
        """Create the reduced tab set for non-Elden Ring games."""

        if profile.key == "nightreign" and _NR_AVAILABLE:
            self._create_nightreign_tabs(profile)
            return

        if profile.key == "dark_souls_3":
            from er_save_manager.games.DS3.tabs import (
                DS3BossesTab,
                DS3EditorTab,
                DS3InspectorTab,
                DS3NpcsTab,
                DS3WorldStateTab,
            )
            from er_save_manager.games.DS3.tabs.appearance import DS3AppearanceTab

            self.notebook.add("Save Inspector")
            self.ds3_inspector_tab = DS3InspectorTab(
                self.notebook.tab("Save Inspector"),
                get_save=lambda: self.ds3_save,
                on_slot_selected=self._on_ds3_slot_edit,
                check_save=self._check_game_save,
                get_issues=self._game_issues,
            )
            self._build_tab("Save Inspector", self.ds3_inspector_tab.setup_ui)

            from er_save_manager.games.DS3.character_management_tab import (
                DS3CharacterManagementTab,
            )

            self.notebook.add("Character Management")
            self.ds3_char_mgmt_tab = DS3CharacterManagementTab(
                self.notebook.tab("Character Management"),
                get_save=lambda: self.ds3_save,
                get_save_path=lambda: self.save_path,
                reload_callback=self.load_save,
                show_toast=self.show_toast,
                is_game_running=lambda: (
                    not self.settings.get("skip_game_running_check", False)
                    and self.is_game_running(profile.process_name)
                ),
            )
            self._build_tab("Character Management", self.ds3_char_mgmt_tab.setup_ui)

            # Game data source (vanilla or a mod), shared by the editor and
            # inventory tabs.
            from er_save_manager.games.DS3 import catalog as ds3_catalog

            ds3_source_var = tk.StringVar(value=ds3_catalog.SOURCES["vanilla"])
            self.notebook.add("Character Editor")
            self.ds3_editor_tab = DS3EditorTab(
                self.notebook.tab("Character Editor"),
                get_save=lambda: self.ds3_save,
                get_save_path=lambda: self.save_path,
                show_toast=self.show_toast,
                source_var=ds3_source_var,
                register_pending=self._pending_register("Character Editor"),
            )
            self._build_tab("Character Editor", self.ds3_editor_tab.setup_steps)

            self.notebook.add("Appearance")
            self.ds3_appearance_tab = CharacterPagesTab(
                self.notebook.tab("Appearance"),
                "Appearance",
                [
                    (
                        "Appearance",
                        lambda p: DS3AppearanceTab(
                            p, lambda: self.ds3_save, self.show_toast
                        ),
                    )
                ],
            )
            self._build_tab("Appearance", self.ds3_appearance_tab.setup_steps)
            self._register_appearance(self.ds3_appearance_tab)

            self.notebook.add("World State")
            self.ds3_world_tab = DS3WorldStateTab(
                self.notebook.tab("World State"),
                get_save=lambda: self.ds3_save,
                get_save_path=lambda: self.save_path,
                show_toast=self.show_toast,
                register_pending=self._pending_register("World State"),
            )
            self._build_tab("World State", self.ds3_world_tab.setup_ui)

            def ds3_page(cls):
                return lambda p: cls(
                    p,
                    get_save=lambda: self.ds3_save,
                    get_save_path=lambda: self.save_path,
                    show_toast=self.show_toast,
                )

            self.notebook.add("NPCs & Bosses")
            self.ds3_npcs_bosses_tab = CharacterPagesTab(
                self.notebook.tab("NPCs & Bosses"),
                "NPCs & Bosses",
                [("NPCs", ds3_page(DS3NpcsTab)), ("Bosses", ds3_page(DS3BossesTab))],
            )
            self._build_tab("NPCs & Bosses", self.ds3_npcs_bosses_tab.setup_steps)
            self._character_tabs = {
                "Character Editor": self.ds3_editor_tab.load_slot,
                "Appearance": self.ds3_appearance_tab.load_slot,
                "World State": self.ds3_world_tab.load_slot,
                "NPCs & Bosses": self.ds3_npcs_bosses_tab.load_slot,
            }
            self._feature_links = {
                "Character Editor": [
                    (
                        "Visual Picker",
                        self._editor_feature(
                            "Inventory",
                            lambda: self.ds3_editor_tab.inventory._open_visual_picker(),
                        ),
                    ),
                    (
                        "Visual Editor",
                        self._editor_feature(
                            "Inventory",
                            lambda: self.ds3_editor_tab.inventory._open_visual_editor(),
                        ),
                    ),
                ]
            }

            self.notebook.add("SteamID Patcher")
            self.steamid_tab = SteamIDPatcherTab(
                self.notebook.tab("SteamID Patcher"),
                lambda: self.save_file,
                lambda: self.save_path,
                self.load_save,
                self.show_toast,
            )
            steamid_tab = self.steamid_tab
            self._build_tab(
                "SteamID Patcher",
                steamid_tab.setup_ui,
                lambda: steamid_tab.set_active_profile("Dark Souls III"),
            )

            self.notebook.add("Settings")
            self.settings_tab = SettingsTab(
                self.notebook.tab("Settings"),
                get_save_path_callback=lambda: self.save_path,
                get_default_save_path_callback=lambda: self.default_save_path,
                active_game="dark_souls_3",
                root=self.root,
            )
            self._build_tab("Settings", self.settings_tab.setup_steps)
            return

        if profile.key == "dark_souls_2":
            from er_save_manager.games.DS2.character_management_tab import (
                DS2CharacterManagementTab,
            )
            from er_save_manager.games.DS2.editor_tab import DS2EditorTab
            from er_save_manager.games.DS2.inspector_tab import DS2InspectorTab

            self.notebook.add("Save Inspector")
            self.ds2_inspector_tab = DS2InspectorTab(
                self.notebook.tab("Save Inspector"),
                get_save=lambda: self.ds2_save,
                on_slot_selected=self._on_ds2_slot_selected,
                check_save=self._check_game_save,
                get_issues=self._game_issues,
            )
            self._build_tab("Save Inspector", self.ds2_inspector_tab.setup_ui)

            self.notebook.add("Character Management")
            self.ds2_management_tab = DS2CharacterManagementTab(
                self.notebook.tab("Character Management"),
                get_save=lambda: self.ds2_save,
                get_save_path=lambda: self.save_path,
                reload_save=lambda: self._load_ds2_save(str(self.save_path)),
                show_toast=self.show_toast,
                is_game_running=lambda: (
                    not self.settings.get("skip_game_running_check", False)
                    and self.is_game_running(profile.process_name)
                ),
            )
            self._build_tab("Character Management", self.ds2_management_tab.setup_ui)

            self.notebook.add("Character Editor")
            self.ds2_editor_tab = DS2EditorTab(
                self.notebook.tab("Character Editor"),
                get_save=lambda: self.ds2_save,
                get_save_path=lambda: self.save_path,
                show_toast=self.show_toast,
                register_pending=self._pending_register("Character Editor"),
            )
            self._build_tab("Character Editor", self.ds2_editor_tab.setup_steps)
            from er_save_manager.games.DS2.appearance_tab import DS2AppearanceTab
            from er_save_manager.games.DS2.bonfire_tab import DS2BonfirePanel
            from er_save_manager.games.DS2.boss_tab import DS2BossPanel
            from er_save_manager.games.DS2.editor_tab import SlotPanelPage
            from er_save_manager.games.DS2.npc_tab import DS2NpcPanel

            def ds2_page(cls):
                return lambda p: SlotPanelPage(
                    cls,
                    p,
                    lambda: self.ds2_save,
                    get_save_path=lambda: self.save_path,
                    show_toast=self.show_toast,
                )

            self.notebook.add("Appearance")
            self.ds2_appearance_tab = CharacterPagesTab(
                self.notebook.tab("Appearance"),
                "Appearance",
                [
                    (
                        "Appearance",
                        lambda p: DS2AppearanceTab(
                            p, lambda: self.ds2_save, self.show_toast
                        ),
                    )
                ],
            )
            self._build_tab("Appearance", self.ds2_appearance_tab.setup_steps)
            self._register_appearance(self.ds2_appearance_tab)

            self.notebook.add("World State")
            self.ds2_world_tab = CharacterPagesTab(
                self.notebook.tab("World State"),
                "World State",
                [("Bonfires", ds2_page(DS2BonfirePanel))],
            )
            self._build_tab("World State", self.ds2_world_tab.setup_steps)

            self.notebook.add("NPCs & Bosses")
            self.ds2_npcs_bosses_tab = CharacterPagesTab(
                self.notebook.tab("NPCs & Bosses"),
                "NPCs & Bosses",
                [("NPCs", ds2_page(DS2NpcPanel)), ("Bosses", ds2_page(DS2BossPanel))],
            )
            self._build_tab("NPCs & Bosses", self.ds2_npcs_bosses_tab.setup_steps)
            self._character_tabs = {
                "Character Editor": self.ds2_editor_tab.load_slot,
                "Appearance": self.ds2_appearance_tab.load_slot,
                "World State": self.ds2_world_tab.load_slot,
                "NPCs & Bosses": self.ds2_npcs_bosses_tab.load_slot,
            }
            ed = self.ds2_editor_tab
            self._feature_links = {
                "Character Editor": [
                    (
                        "Visual Picker",
                        self._editor_feature(
                            "Inventory", lambda: ed.inventory_panel._open_icon_browser()
                        ),
                    ),
                    (
                        "Visual Inventory",
                        self._editor_feature(
                            "Inventory",
                            lambda: ed.inventory_panel._open_visual_inventory(),
                        ),
                    ),
                ],
                "World State": [
                    (
                        "Visual Bonfires",
                        self._feature(
                            "World State",
                            lambda: self.ds2_world_tab.pages[
                                "Bonfires"
                            ].panel._open_visual_view(),
                        ),
                    ),
                ],
            }

            self.notebook.add("SteamID Patcher")
            self.steamid_tab = SteamIDPatcherTab(
                self.notebook.tab("SteamID Patcher"),
                lambda: self.save_file,
                lambda: self.save_path,
                self.load_save,
                self.show_toast,
            )
            steamid_tab = self.steamid_tab
            self._build_tab(
                "SteamID Patcher",
                steamid_tab.setup_ui,
                lambda: steamid_tab.set_active_profile(
                    "Dark Souls II: Scholar of the First Sin"
                ),
            )

            self.notebook.add("Settings")
            self.settings_tab = SettingsTab(
                self.notebook.tab("Settings"),
                get_save_path_callback=lambda: self.save_path,
                get_default_save_path_callback=lambda: self.default_save_path,
                active_game="dark_souls_2",
                root=self.root,
            )
            self._build_tab("Settings", self.settings_tab.setup_steps)
            return

        # DSR has no embedded SteamID - SteamID Patcher tab is not shown.
        # All other non-ER games get: SteamID Patcher + Settings.
        # Backup Manager is available via the top-level button, not as a tab.

        if profile.key != "dark_souls_remastered":
            self.notebook.add("SteamID Patcher")
            tab_steamid = self.notebook.tab("SteamID Patcher")
            self.steamid_tab = SteamIDPatcherTab(
                tab_steamid,
                lambda: self.save_file,
                lambda: self.save_path,
                self.load_save,
                self.show_toast,
            )
            steamid_tab = self.steamid_tab
            self._build_tab(
                "SteamID Patcher",
                steamid_tab.setup_ui,
                lambda: steamid_tab.set_active_profile(profile.name),
            )

        if profile.key == "dark_souls_remastered":
            from er_save_manager.games.DSR.appearance_tab import DSRAppearanceTab
            from er_save_manager.games.DSR.editor_tab import DSREditorTab
            from er_save_manager.games.DSR.inspector_tab import DSRInspectorTab
            from er_save_manager.games.DSR.npc_tab import DSRNPCTab
            from er_save_manager.games.DSR.world_state_tab import DSRWorldStateTab

            self.notebook.add("Save Inspector")
            self.dsr_inspector_tab = DSRInspectorTab(
                self.notebook.tab("Save Inspector"),
                get_dsr_save=lambda: self.dsr_save,
                on_slot_selected=self._on_dsr_slot_edit,
                check_save=self._check_game_save,
                get_issues=self._game_issues,
            )
            self._build_tab("Save Inspector", self.dsr_inspector_tab.setup_ui)

            from er_save_manager.games.DSR.character_management_tab import (
                DSRCharacterManagementTab,
            )

            self.notebook.add("Character Management")
            self.dsr_char_mgmt_tab = DSRCharacterManagementTab(
                self.notebook.tab("Character Management"),
                get_dsr_save=lambda: self.dsr_save,
                get_save_path=lambda: self.save_path,
                reload_callback=self.load_save,
                show_toast=self.show_toast,
                is_game_running=lambda: (
                    not self.settings.get("skip_game_running_check", False)
                    and self.is_game_running(profile.process_name)
                ),
            )
            self._build_tab("Character Management", self.dsr_char_mgmt_tab.setup_ui)

            self.notebook.add("Character Editor")
            self.dsr_editor_tab = DSREditorTab(
                self.notebook.tab("Character Editor"),
                get_dsr_save=lambda: self.dsr_save,
                get_save_path=lambda: self.save_path,
                show_toast=self.show_toast,
                register_pending=self._pending_register("Character Editor"),
            )
            self._build_tab("Character Editor", self.dsr_editor_tab.setup_steps)

            self.notebook.add("Appearance")
            self.dsr_appearance_tab = CharacterPagesTab(
                self.notebook.tab("Appearance"),
                "Appearance",
                [
                    (
                        "Appearance",
                        lambda p: DSRAppearanceTab(
                            p, lambda: self.dsr_save, self.show_toast
                        ),
                    )
                ],
            )
            self._build_tab("Appearance", self.dsr_appearance_tab.setup_steps)
            self._register_appearance(self.dsr_appearance_tab)

            self.notebook.add("World State")
            self.dsr_world_tab = DSRWorldStateTab(
                self.notebook.tab("World State"),
                get_dsr_save=lambda: self.dsr_save,
                get_save_path=lambda: self.save_path,
                show_toast=self.show_toast,
                register_pending=self._pending_register("World State"),
            )
            self._build_tab("World State", self.dsr_world_tab.setup_ui)

            self.notebook.add("NPCs & Bosses")
            self.dsr_npc_tab = DSRNPCTab(
                self.notebook.tab("NPCs & Bosses"),
                get_dsr_save=lambda: self.dsr_save,
                get_save_path=lambda: self.save_path,
                show_toast=self.show_toast,
            )
            self._build_tab("NPCs & Bosses", self.dsr_npc_tab.setup_ui)

            self.notebook.add("Event Flags")
            from er_save_manager.games.DSR.event_flags_tab import DSREventFlagsTab

            self.dsr_flags_tab = DSREventFlagsTab(
                self.notebook.tab("Event Flags"),
                get_dsr_save=lambda: self.dsr_save,
                get_save_path=lambda: self.save_path,
                show_toast=self.show_toast,
            )
            self._build_tab("Event Flags", self.dsr_flags_tab.setup_ui)
            self._character_tabs = {
                "Character Editor": self.dsr_editor_tab.load_slot,
                "Appearance": self.dsr_appearance_tab.load_slot,
                "World State": self.dsr_world_tab.load_slot,
                "NPCs & Bosses": self.dsr_npc_tab.load_slot,
                "Event Flags": self.dsr_flags_tab.load_slot,
            }
            self._feature_links = {
                "Character Editor": [
                    (
                        "Visual Picker",
                        self._editor_feature(
                            "Inventory",
                            lambda: self.dsr_editor_tab.inventory._open_picker(),
                        ),
                    ),
                    (
                        "Visual Editor",
                        self._editor_feature(
                            "Inventory",
                            lambda: self.dsr_editor_tab.inventory._open_editor(),
                        ),
                    ),
                ]
            }

        self.notebook.add("Settings")
        tab_settings = self.notebook.tab("Settings")
        self.settings_tab = SettingsTab(
            tab_settings,
            get_save_path_callback=lambda: self.save_path,
            get_default_save_path_callback=lambda: self.default_save_path,
            active_game=profile.key,
            root=self.root,
        )
        self._build_tab("Settings", self.settings_tab.setup_steps)

    def _create_nightreign_tabs(self, profile):
        """Create tab set for Nightreign."""
        self.nr_inspector_tab = None
        self.nr_editor_tab = None
        self.nr_steamid_tab = None

        self.notebook.add("Save Inspector")
        self.nr_inspector_tab = NRInspectorTab(
            self.notebook.tab("Save Inspector"),
            lambda: self._nr_save,
            on_slot_selected=self._nr_on_slot_selected,
            check_save=self._check_game_save,
            get_issues=self._game_issues,
        )
        self._build_tab("Save Inspector", self.nr_inspector_tab.setup_ui)

        from er_save_manager.games.NR.character_management_tab import (
            NRCharacterManagementTab,
        )

        self.notebook.add("Character Management")
        self.nr_char_mgmt_tab = NRCharacterManagementTab(
            self.notebook.tab("Character Management"),
            get_nr_save=lambda: self._nr_save,
            get_save_path=lambda: self.save_path,
            reload_callback=self.reload_save,
            show_toast=self.show_toast,
            is_game_running=lambda: (
                not self.settings.get("skip_game_running_check", False)
                and self.is_game_running(profile.process_name)
            ),
        )
        self._build_tab("Character Management", self.nr_char_mgmt_tab.setup_ui)

        for name in ("Character Editor", "Relics", "Loadouts"):
            self.notebook.add(name)
        self.nr_editor_tab = NREditorTab(
            self.notebook.tab("Character Editor"),
            lambda: self._nr_save,
            lambda: self.save_path,
            self.show_toast,
            self._pending_register,
            relics_parent=self.notebook.tab("Relics"),
            loadouts_parent=self.notebook.tab("Loadouts"),
        )
        self._build_tab("Character Editor", self.nr_editor_tab.setup_steps)
        self._build_tab("Relics", self.nr_editor_tab.setup_relics)
        self._build_tab("Loadouts", self.nr_editor_tab.setup_loadouts)
        self._character_tabs = {
            "Character Editor": self.nr_editor_tab.load_overview,
            "Relics": self.nr_editor_tab.load_relics,
            "Loadouts": self.nr_editor_tab.load_loadouts,
        }

        self.notebook.add("SteamID Patcher")
        self.nr_steamid_tab = SteamIDPatcherTab(
            self.notebook.tab("SteamID Patcher"),
            lambda: self.save_file,
            lambda: self.save_path,
            self.reload_save,
            self.show_toast,
        )
        nr_steamid_tab = self.nr_steamid_tab
        self._build_tab(
            "SteamID Patcher",
            nr_steamid_tab.setup_ui,
            lambda: nr_steamid_tab.set_active_profile(profile.name),
        )

        self.notebook.add("Settings")
        self.settings_tab = SettingsTab(
            self.notebook.tab("Settings"),
            get_save_path_callback=lambda: self.save_path,
            get_default_save_path_callback=lambda: self.default_save_path,
            active_game=profile.key,
            root=self.root,
        )
        self._build_tab("Settings", self.settings_tab.setup_steps)

    def _nr_on_slot_selected(self, slot_index: int) -> None:
        """Navigate from inspector to editor for the selected slot."""
        self._open_in_editor(slot_index)

    def _open_in_editor(self, slot_index: int) -> None:
        """Pick slot_index in the character bar and show the Character
        Editor (inspector Edit Character buttons)."""
        self._flush_pending_tabs()
        if self._select_character(slot_index):
            self.notebook.set("Character Editor")
            self._on_tab_changed()

    def setup_character_editor_tab(self, parent):
        """Setup character editor tab with modular editors"""
        header = ctk.CTkLabel(
            parent,
            text="Character Editor",
            font=("Inter", 16, "bold"),
        )
        header.pack(anchor="w", padx=20, pady=(6, 8))

        container = ctk.CTkFrame(
            parent, corner_radius=10, fg_color=("gray86", "gray22")
        )
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 12))

        editor_tabs = ctk.CTkTabview(
            container,
            width=900,
            height=520,
            command=lambda: self._ensure_tab_built(
                f"Character Editor/{editor_tabs.get()}"
            ),
            fg_color=("gray90", "gray20"),
            segmented_button_fg_color=("gray80", "gray35"),
            segmented_button_selected_color=palette.PURPLE,
            segmented_button_unselected_color=("gray70", "gray30"),
        )
        editor_tabs.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 12))
        self._er_editor_tabs = editor_tabs

        def current_slot_index() -> int:
            return self._er_slot

        stats_frame = editor_tabs.add("Stats")
        stats_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.stats_editor = StatsEditor(
            stats_frame,
            lambda: self.save_file,
            current_slot_index,
            lambda: self.save_path,
        )
        self.stats_editor.setup_ui()

        info_tab = editor_tabs.add("Identity")
        info_frame = ctk.CTkFrame(info_tab, fg_color="transparent")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.char_info_editor = CharacterInfoEditor(
            info_frame,
            lambda: self.save_file,
            current_slot_index,
            lambda: self.save_path,
        )
        # Only the visible Stats editor is built now; the others follow in
        # the background like top-level tabs (see _build_tab).
        self._build_tab("Character Editor/Identity", self.char_info_editor.setup_ui)
        self.char_info_editor.on_archetype_change = (
            self.stats_editor.on_archetype_changed
        )

        equipment_tab = editor_tabs.add("Equipment")
        equipment_frame = ctk.CTkFrame(equipment_tab, fg_color="transparent")
        equipment_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.equipment_editor = EquipmentEditor(
            equipment_frame,
            lambda: self.save_file,
            current_slot_index,
            lambda: self.save_path,
        )
        self._build_tab("Character Editor/Equipment", self.equipment_editor.setup_steps)

        inventory_tab = editor_tabs.add("Inventory")
        inventory_frame = ctk.CTkFrame(inventory_tab, fg_color="transparent")
        inventory_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.inventory_editor = InventoryEditor(
            inventory_frame,
            lambda: self.save_file,
            current_slot_index,
            lambda: self.save_path,
            self.ensure_raw_data_mutable,
            on_inventory_changed=self._on_inventory_changed,
            get_settings_callback=lambda: self.settings,
        )
        self._build_tab("Character Editor/Inventory", self.inventory_editor.setup_steps)

        self.equipment_editor.apply_all = self.pending_bar.apply_all
        register = self._pending_register("Character Editor")
        for name, editor, reload in (
            ("Stats", self.stats_editor, self.stats_editor.load_stats),
            ("Equipment", self.equipment_editor, self.equipment_editor.load_equipment),
            (
                "Identity",
                self.char_info_editor,
                self.char_info_editor.load_character_info,
            ),
        ):
            register(
                PendingPage(
                    name,
                    getattr(editor, "changes", editor.tracker.changes),
                    editor.prepare,
                    reload,
                    lambda n=name: editor_tabs.set(n),
                )
            )

    def acknowledge_save_written(self) -> None:
        """Resnapshot the save file mtime after an internal write.

        Call this after any tab writes the save so the file watcher does not
        treat the internal change as an external modification.
        """
        self._update_watched_mtime()

    def _on_inventory_changed(self) -> None:
        """Refresh matchmaking weapon level floor after inventory changes."""
        self.acknowledge_save_written()
        try:
            slot = self.save_file.characters[self._er_slot]
            if hasattr(self, "stats_editor") and self.stats_editor:
                self.stats_editor._refresh_matchmaking_min(slot)
        except Exception:
            pass

    def _er_load_character(self, slot_idx: int) -> None:
        """Show the character in slot_idx in the Character Editor; -1 or an
        empty slot clears it."""
        self._er_slot = slot_idx
        if not hasattr(self, "stats_editor"):
            return
        save = self.save_file
        if (
            save is None
            or not 0 <= slot_idx < len(save.characters)
            or save.characters[slot_idx].is_empty()
            # A deleted character keeps its slot data until a new one is
            # created there, so the active flag decides, as in the fixer.
            or slot_idx not in save.get_active_slots()
        ):
            for editor in (
                self.stats_editor,
                self.equipment_editor,
                self.char_info_editor,
            ):
                editor.tracker.clear()
            self.inventory_editor.clear_inventory()
            return
        self.stats_editor.load_stats()
        self.equipment_editor.load_equipment()
        self.char_info_editor.load_character_info()
        self.inventory_editor.refresh_inventory()

    def ensure_raw_data_mutable(self):
        """Ensure save file _raw_data is mutable (bytearray)"""
        if self.save_file and isinstance(self.save_file._raw_data, bytes):
            self.save_file._raw_data = bytearray(self.save_file._raw_data)

    def _active_profile(self):
        """Return the GameProfile for the currently selected game."""
        return PROFILES_BY_KEY.get(self.active_game)

    def _reject_wrong_game(self, save_path: str) -> bool:
        """Show an error and return True if save_path belongs to another game."""
        from er_save_manager.games.save_identify import KNOWN_GAMES, identify_game

        if self.active_game not in KNOWN_GAMES:
            return False
        owner = identify_game(save_path)
        if owner is None or owner == self.active_game:
            return False
        owner_profile = PROFILES_BY_KEY.get(owner)
        active_profile = self._active_profile()
        owner_name = owner_profile.name if owner_profile else owner
        active_name = active_profile.name if active_profile else self.active_game
        CTkMessageBox.showerror(
            "Wrong Game",
            f"{os.path.basename(save_path)} is a {owner_name} save, "
            f"not a {active_name} save.\n\n"
            f"Switch to {owner_name} to load it.",
            parent=self.root,
        )
        self.status_var.set("Load cancelled - save belongs to another game")
        return True

    # File operations
    def show_console_save_info(self):
        """Show instructions for loading a PlayStation or Switch save."""
        from er_save_manager.ui import dialog_style as ds

        ds3 = self.active_game == "dark_souls_3"
        title = "PS4 Saves" if ds3 else "PS / Switch Saves"
        dialog = ds.create(self.root, title)
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=16)

        ds.button_row(main_frame, [{"text": "Close", "command": dialog.destroy}])
        header = ctk.CTkFrame(main_frame, fg_color="transparent")
        header.pack(fill=ctk.X)
        ctk.CTkLabel(
            header,
            text="ℹ",
            font=("Inter", 30, "bold"),
            text_color=palette.PURPLE_TEXT,
        ).pack(side=ctk.LEFT, padx=(0, 10))
        ctk.CTkLabel(header, text=title, font=("Inter", 19, "bold")).pack(side=ctk.LEFT)
        if ds3:
            text = (
                "PS4 saves must be decrypted and exported as userdata files "
                "(userdata0000 to userdata0009 for the characters, userdata0010 "
                "for the load screen) before you can load them. Open any of them "
                "and the files next to it are loaded too. A file opened on its "
                "own only gives access to its own character. Auto-Find does not "
                "find userdata files."
            )
        else:
            text = (
                "Console saves must be decrypted and exported as memory.dat "
                "before you can load them. Auto-Find does not find memory.dat files."
            )
        ctk.CTkLabel(
            main_frame,
            text=text,
            font=("Inter", 15),
            wraplength=500,
            justify=ctk.LEFT,
        ).pack(anchor=ctk.W, pady=(10, 10))
        note = ds.box(main_frame, pady=(0, 0))
        ctk.CTkLabel(
            note,
            text="Exporting or decrypting a console save may require custom "
            "firmware on your console; there are no instructions for that here. "
            "Use at your own risk.",
            font=("Inter", 14),
            wraplength=476,
            justify=ctk.LEFT,
        ).pack(anchor=ctk.W, padx=12, pady=10)
        ds.finish(dialog, self.root)

    def browse_file(self):
        """Browse for a save file for the active game."""
        profile = self._active_profile()

        # Block loading if the game is currently running
        if (
            not self.settings.get("skip_game_running_check", False)
            and profile
            and profile.process_name
            and self.is_game_running(profile.process_name)
        ):
            if not self._handle_game_running_dialog(profile):
                return

        initialdir = None
        if self.settings.get("remember_last_location", True):
            last_path = self.settings.get("last_save_path", "")
            if last_path:
                last_dir = os.path.dirname(last_path)
                if os.path.exists(last_dir):
                    initialdir = last_dir

        if not initialdir:
            default_loc = PlatformUtils.get_default_save_location(profile)
            if default_loc and default_loc.exists():
                initialdir = str(default_loc)

        if not initialdir:
            # ER legacy fallback
            if self.default_save_path.exists():
                initialdir = str(self.default_save_path)

        if not initialdir and PlatformUtils.is_linux():
            steam_base = Path.home() / ".local" / "share" / "Steam"
            if steam_base.exists():
                initialdir = str(steam_base)

        if not initialdir:
            initialdir = str(Path.home())

        if profile:
            ext_str = " ".join(f"*{e}" for e in profile.extensions)
            if profile.key in ("elden_ring", "nightreign"):
                ext_str += " *.dat"
            elif profile.key == "dark_souls_3":
                ext_str += " userdata*"
            filetypes = [(f"{profile.name} Saves", ext_str), ("All files", "*.*")]
            title = f"Select {profile.name} Save File"
        else:
            filetypes = [
                ("Save Files", "*.sl2 *.co2 *.cnv *.cnvco2 *.dat"),
                ("PlayStation (Save Wizard)", "*"),
                ("All files", "*.*"),
            ]
            title = "Select Save File"

        filename = pick_file(title=title, initialdir=initialdir, filetypes=filetypes)
        if filename:
            self.file_path_var.set(filename)
            self.status_var.set(f"Selected: {os.path.basename(filename)}")

            if self.settings.get("remember_last_location", True):
                self.settings.set("last_save_path", filename)

            if (
                PlatformUtils.is_linux()
                and not PlatformUtils.is_save_in_default_location(
                    Path(filename), profile
                )
                and self.settings.get("show_linux_save_warning", True)
            ):
                self.show_linux_save_location_warning(Path(filename), profile)

    def auto_detect(self):
        """Auto-detect save file for the active game.

        The search runs on a worker thread: on Linux it globs every Steam
        library's compatdata, which can stall on a cold cache or a library
        on a sleeping disk. The result is handled on the UI thread.
        """
        if self._auto_detect_running:
            return
        self._auto_detect_running = True
        profile = self._active_profile()
        self.status_var.set("Searching for saves...")

        def search():
            try:
                found = PlatformUtils.find_all_save_files(profile)
            except Exception:
                found = []
            self.root.after(0, self._finish_auto_detect, profile, found)

        threading.Thread(target=search, daemon=True).start()

    def _finish_auto_detect(self, profile, found_saves) -> None:
        self._auto_detect_running = False
        self.status_var.set("Ready")
        # The game was switched while searching; that search is stale.
        if profile is not self._active_profile():
            return
        game_name = profile.name if profile else "Elden Ring"

        if not found_saves:
            if PlatformUtils.is_linux():
                CTkMessageBox.showinfo(
                    "No Saves Found",
                    f"No {game_name} save files found.\n\n"
                    "Make sure you have launched the game at least once.\n"
                    "On Linux, saves are stored in Steam's compatdata folder.",
                    parent=self.root,
                )
            else:
                CTkMessageBox.showwarning(
                    "Not Found",
                    f"No {game_name} save files found.",
                    parent=self.root,
                )
            return

        def _on_selected(path: str):
            self.file_path_var.set(path)
            if (
                PlatformUtils.is_linux()
                and not PlatformUtils.is_save_in_default_location(Path(path), profile)
                and self.settings.get("show_linux_save_warning", True)
            ):
                self.show_linux_save_location_warning(Path(path), profile)

        if len(found_saves) == 1:
            _on_selected(str(found_saves[0]))
            self.status_var.set(f"{game_name} save auto-detected")
        else:
            SaveSelectorDialog.show(self.root, found_saves, _on_selected)

    def show_linux_save_location_warning(self, save_path, profile=None):
        """Show warning about non-default save location on Linux."""
        game_name = profile.name if profile else "Elden Ring"
        from er_save_manager.ui import dialog_style as ds

        dialog = ds.create(self.root, "Save Location Warning")
        msg_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        msg_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        def copy_to_default():
            target_dir = PlatformUtils.get_default_save_location(profile)
            current_path = Path(save_path)
            steamid = current_path.parent.name
            if target_dir and steamid:
                target_dir = target_dir / steamid

            if target_dir:
                if CTkMessageBox.askyesno(
                    "Copy Save",
                    f"Copy save file to:\n{target_dir}\n\nThe original file will remain in its current location.",
                    parent=self.root,
                ):
                    try:
                        import shutil

                        target_dir.mkdir(parents=True, exist_ok=True)
                        new_path = target_dir / current_path.name
                        shutil.copy2(save_path, new_path)
                        self.file_path_var.set(str(new_path))
                        CTkMessageBox.showinfo(
                            "Save Copied",
                            f"Save file copied to:\n{new_path}\n\nOriginal file remains at:\n{save_path}",
                            parent=self.root,
                        )
                        dialog.destroy()
                    except Exception as e:
                        CTkMessageBox.showerror(
                            "Copy Failed",
                            f"Failed to copy save:\n{e}",
                            parent=self.root,
                        )

        def dont_show_again():
            self.settings.set("show_linux_save_warning", False)
            dialog.destroy()

        ds.button_row(
            msg_frame,
            [
                {
                    "text": "Don't Show Again",
                    "command": dont_show_again,
                    "primary": False,
                    "width": 140,
                },
                {
                    "text": "Keep Current",
                    "command": dialog.destroy,
                    "primary": False,
                    "width": 120,
                },
                {"text": "Copy to Default", "command": copy_to_default, "width": 130},
            ],
        )
        ds.header(msg_frame, "Non-standard save location", icon="⚠")
        ctk.CTkLabel(
            msg_frame,
            text=f"Your {game_name} save is not in the default Steam compatdata folder:",
            font=ds.FONT,
            wraplength=500,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(10, 2))
        ctk.CTkLabel(
            msg_frame,
            text=str(save_path),
            font=ds.SMALL,
            text_color=ds.MUTED,
            wraplength=500,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 10))
        ctk.CTkLabel(
            msg_frame,
            text='If you remove the custom launcher (e.g. "ersc_launcher.exe") '
            "from Steam, Steam removes that compatdata folder and the save is "
            "lost. Set a fixed Steam launch option and copy the save to the "
            "default location with Copy to Default.",
            font=ds.FONT,
            wraplength=500,
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        launch_option = PlatformUtils.get_steam_launch_option_hint(profile)
        if launch_option:
            ctk.CTkLabel(
                msg_frame,
                text="Custom launcher Steam launch options",
                font=ds.BOLD,
            ).pack(anchor=tk.W, pady=(12, 0))
            option_box = ds.box(msg_frame, pady=(4, 0))
            option_entry = ctk.CTkEntry(option_box, font=("Consolas", 12))
            option_entry.insert(0, launch_option)
            option_entry.configure(state="readonly")
            option_entry.pack(
                side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 8), pady=10
            )

            def copy_to_clipboard():
                dialog.clipboard_clear()
                dialog.clipboard_append(launch_option)
                dialog.update()
                self.show_toast("Launch option copied")

            ds.button(option_box, "Copy", copy_to_clipboard, width=80).pack(
                side=tk.LEFT, padx=(0, 12), pady=10
            )

        ds.finish(dialog, self.root, min_width=540)

    def is_game_running(self, process_name: str = "eldenring.exe") -> bool:
        """Check if a game process is running."""
        if process_name == "eldenring.exe":
            return PlatformUtils.is_game_running()
        try:
            if PlatformUtils.is_windows():
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 0  # SW_HIDE
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/NH"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    startupinfo=si,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                return (
                    process_name.lower()
                    in result.stdout.decode(errors="replace").lower()
                )
            else:
                # -i: Proton command lines keep the exe's mixed case
                # (DarkSoulsIII.exe), profile names are lowercase.
                result = subprocess.run(
                    ["pgrep", "-if", process_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return result.returncode == 0
        except Exception:
            return False

    def _get_game_folder(self) -> Path | None:
        """Attempt to detect the Elden Ring installation folder."""
        try:
            # Try to find via Steam registry on Windows
            if PlatformUtils.is_windows():
                import winreg

                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\WOW6432Node\Valve\Steam",
                    )
                    steam_path = Path(winreg.QueryValueEx(key, "InstallPath")[0])
                    winreg.CloseKey(key)

                    game_folder = steam_path / "steamapps" / "common" / "ELDEN RING"
                    if game_folder.exists():
                        return game_folder

                    library_file = steam_path / "steamapps" / "libraryfolders.vdf"
                    if library_file.exists():
                        content = library_file.read_text(encoding="utf-8")
                        # Simple parse for paths (not perfect VDF parsing)
                        import re

                        paths = re.findall(r'"path"\s+"(.+?)"', content)
                        for path_str in paths:
                            lib_path = Path(path_str.replace("\\\\", "\\"))
                            game_folder = (
                                lib_path / "steamapps" / "common" / "ELDEN RING"
                            )
                            if game_folder.exists():
                                return game_folder

                except Exception:
                    pass

            # Fallback: Check common default locations
            common_paths = [
                Path("C:/Program Files (x86)/Steam/steamapps/common/ELDEN RING"),
                Path("C:/Program Files/Steam/steamapps/common/ELDEN RING"),
                Path.home()
                / ".steam"
                / "steam"
                / "steamapps"
                / "common"
                / "ELDEN RING",
                Path.home()
                / ".local"
                / "share"
                / "Steam"
                / "steamapps"
                / "common"
                / "ELDEN RING",
            ]

            for path in common_paths:
                if path.exists():
                    return path

        except Exception:
            pass

        return None

    def _open_inventory_editor(self):
        """Show Character Editor > Inventory for the active game; for
        Nightreign the Relics tab with the new relic pane."""
        self._flush_pending_tabs()
        tab = "Relics" if self.active_game == "nightreign" else "Character Editor"
        if tab not in self.notebook._name_list:
            return
        self.notebook.set(tab)
        self._on_tab_changed()
        if self.active_game == "nightreign":
            if self.nr_editor_tab is not None:
                self.nr_editor_tab.open_spawner()
            return
        self._show_editor_sub("Inventory")

    def open_troubleshooting(self):
        """Open the troubleshooting dialog or install addon"""
        from er_save_manager.addons.troubleshooter_addon_manager import (
            TroubleshooterAddon,
        )
        from er_save_manager.addons.troubleshooter_install_dialog import (
            show_troubleshooter_dialog,
        )

        addon_manager = TroubleshooterAddon()
        show_troubleshooter_dialog(self.root, addon_manager)

    # --- Deferred tab construction -------------------------------------- #

    def _build_tab(self, name: str, *steps) -> None:
        """Run a tab's widget construction steps.

        CustomTkinter widgets draw themselves on creation, so building every
        tab of a game at once blocks the window for seconds. The tab that is
        showing is built immediately; the others are queued and built one
        step per event loop turn, or at once when they are selected or
        anything reads them (see _flush_pending_tabs). A step that returns a
        generator is resumed one yield per turn, so a large tab can split its
        construction into stages.
        """
        self._pending_tabs[name] = deque(steps)
        if len(self._pending_tabs) == 1 and self.notebook.get() == name:
            self._ensure_tab_built(name)
            return
        if self._tab_build_job is None:
            self._schedule_tab_build()

    def _schedule_tab_build(self) -> None:
        # Tk runs due timers before the idle callbacks that repaint the window,
        # so the timer is armed from an idle callback: the window is drawn
        # (and input handled) before each queued step is run.
        self._tab_build_job = self.root.after_idle(
            lambda: setattr(
                self,
                "_tab_build_job",
                self.root.after(_TAB_BUILD_DELAY_MS, self._build_next_tab),
            )
        )

    def _build_next_tab(self) -> None:
        self._tab_build_job = None
        if not self._pending_tabs:
            return
        self._advance_tab(next(iter(self._pending_tabs)))
        if self._pending_tabs:
            self._schedule_tab_build()

    def _advance_tab(self, name: str) -> None:
        """Run the next step of a queued tab, or the next stage of a staged step."""
        queue = self._pending_tabs[name]
        if not isinstance(queue[0], Iterator):
            result = queue.popleft()()
            if isinstance(result, Iterator):
                queue.appendleft(result)
        if queue and isinstance(queue[0], Iterator):
            try:
                next(queue[0])
            except StopIteration:
                queue.popleft()
        if not queue:
            del self._pending_tabs[name]

    def _ensure_tab_built(self, name: str) -> None:
        while name in self._pending_tabs:
            self._advance_tab(name)

    def _flush_pending_tabs(self) -> None:
        """Finish all queued tabs; call before code that reads tab widgets."""
        while self._pending_tabs:
            self._ensure_tab_built(next(iter(self._pending_tabs)))

    def _drop_pending_tabs(self) -> None:
        """Forget queued tabs whose notebook is about to be destroyed."""
        if self._tab_build_job is not None:
            self.root.after_cancel(self._tab_build_job)
            self._tab_build_job = None
        self._pending_tabs.clear()

    def _on_tab_changed(self, event=None):
        """Handle tab change event - lazy load and refresh tabs."""
        current_tab = self.notebook.get()
        self._ensure_tab_built(current_tab)
        self._update_character_bar_state()

        # Load tab content in background for non-blocking UI
        if not self.tabs_loaded.get(current_tab, False):
            thread = threading.Thread(
                target=self._lazy_load_tab_background, args=(current_tab,), daemon=True
            )
            thread.start()
        elif current_tab == "World State" and hasattr(self, "world_tab"):
            self.world_tab.refresh()

    def _lazy_load_tab_background(self, tab_name):
        """Schedule tab data load on the main thread - all CTk calls must stay on the main thread."""
        # Nothing here is actually safe to run off-thread; dispatch everything via after().
        self.root.after(0, lambda: self._lazy_load_tab_main(tab_name))

    def _lazy_load_tab_main(self, tab_name):
        """Load tab data on the main thread."""
        try:
            if not self.save_file:
                return
            if self.tabs_loaded.get(tab_name, False):
                return

            if tab_name == "Save Fixer":
                self.inspector_tab.populate_character_list()
            elif tab_name == "Appearance":
                if self.appearance_tab is not None:
                    self.appearance_tab.load_presets()
            elif tab_name == "Advanced Tools":
                self.advanced_tab.update_save_info()
            elif tab_name == "Event Flags":
                if hasattr(self, "dsr_flags_tab") and self.dsr_flags_tab:
                    self.dsr_flags_tab.refresh()
            elif tab_name == "SteamID Patcher":
                if hasattr(self.steamid_tab, "update_steamid_display"):
                    self.steamid_tab.update_steamid_display()
            elif tab_name == "Character Management":
                if hasattr(self, "ds3_char_mgmt_tab") and self.ds3_char_mgmt_tab:
                    self.ds3_char_mgmt_tab.refresh()
                if hasattr(self, "dsr_char_mgmt_tab") and self.dsr_char_mgmt_tab:
                    self.dsr_char_mgmt_tab.refresh()
                if hasattr(self, "nr_char_mgmt_tab") and self.nr_char_mgmt_tab:
                    self.nr_char_mgmt_tab.refresh()
                if hasattr(self, "ds2_management_tab") and self.ds2_management_tab:
                    self.ds2_management_tab.refresh()
            elif tab_name == "Hex Editor":
                if self.save_file:
                    try:
                        with open(self.save_path, "rb") as f:
                            self.save_file._raw_data = f.read()
                        self.hex_tab.hex_display_at_offset(0)
                    except Exception:
                        pass
            # "Gestures" has no auto-load

            self.tabs_loaded[tab_name] = True
        except Exception:
            pass

    def _on_file_path_changed(self, *args):
        """Auto-load save file when a valid file path is entered."""
        if self._suppress_path_load:
            return
        save_path = self.file_path_var.get()
        if not save_path or not os.path.exists(save_path):
            return

        if self.active_game == "elden_ring":
            filename = os.path.basename(save_path).lower()
            if filename.startswith("er") or filename == "memory.dat":
                self.root.after(500, self.load_save)
        elif self.active_game == "dark_souls_remastered":
            self.root.after(500, lambda p=save_path: self._load_dsr_save(p))
        elif self.active_game == "dark_souls_3":
            self.root.after(500, lambda p=save_path: self._load_ds3_save(p))
        elif self.active_game == "dark_souls_2":
            self.root.after(500, lambda p=save_path: self._load_ds2_save(p))
        elif self.active_game == "nightreign" and _NR_AVAILABLE:
            self.root.after(500, lambda p=save_path: self._load_nr_save(p))
        else:
            self._load_non_er_save(save_path)

    def _load_non_er_save(self, save_path: str):
        """Store the selected save path for non-ER games and refresh the SteamID display."""
        self._flush_pending_tabs()
        if not self._guard_pending("load another save file"):
            return
        if self._reject_wrong_game(save_path):
            return
        profile = self._active_profile()
        if (
            not self.settings.get("skip_game_running_check", False)
            and profile
            and profile.process_name
            and self.is_game_running(profile.process_name)
        ):
            if not self._handle_game_running_dialog(profile):
                return

        self.save_path = Path(save_path)
        self.save_file = None
        self._update_watched_mtime()
        self._start_file_watcher()
        self.status_var.set(f"Selected: {os.path.basename(save_path)}")
        self.show_toast(
            f"Save file loaded: {os.path.basename(save_path)}", duration=2500
        )
        if hasattr(self, "steamid_tab") and self.steamid_tab:
            import threading

            threading.Thread(
                target=self.steamid_tab._refresh_steamid_display, daemon=True
            ).start()

    def on_slot_selected(self, slot_index: int):
        """Handle character slot selection from Fixer tab."""
        self._flush_pending_tabs()
        self.selected_slot_index = slot_index

    def load_save(self, silent=False, toast_message="Save file loaded successfully."):
        """Load save file in background thread to prevent UI freezing

        Args:
            silent: If True, suppress the success message (used for reloads after operations)
            toast_message: Success toast shown once loading finishes
        """
        self._flush_pending_tabs()
        save_path = self.file_path_var.get()

        if not save_path or not os.path.exists(save_path):
            CTkMessageBox.showerror(
                "No Save File", "Select a valid save file first.", parent=self.root
            )
            return
        if not self._guard_pending("load the save file"):
            return

        if self._reject_wrong_game(save_path):
            return

        # The game must be closed before writing
        profile = self._active_profile()
        process_name = (
            profile.process_name
            if profile and profile.process_name
            else "eldenring.exe"
        )
        if not self.settings.get(
            "skip_game_running_check", False
        ) and self.is_game_running(process_name):
            if not self._handle_game_running_dialog(profile):
                return

        if self.active_game == "elden_ring" and not self._confirm_vanilla_save(
            save_path
        ):
            return

        # Route non-ER games to their own loaders so the Load button works too
        if self.active_game == "dark_souls_remastered":
            self._load_dsr_save(save_path)
            return
        if self.active_game == "dark_souls_3":
            self._load_ds3_save(save_path, running_checked=True)
            return
        if self.active_game == "dark_souls_2":
            self._load_ds2_save(save_path)
            return
        if self.active_game == "nightreign" and _NR_AVAILABLE:
            self._load_nr_save(save_path)
            return

        self.status_var.set("Loading save file...")
        thread = threading.Thread(
            target=self._load_save_background,
            args=(save_path, silent, toast_message),
            daemon=True,
        )
        thread.start()

    def _load_save_background(
        self, save_path, silent=False, toast_message="Save file loaded successfully."
    ):
        """Background thread for loading save file"""
        try:
            verbose = self.settings.get("verbose_logging", False)
            if verbose:
                self._verbose_log(f"Loading save: {save_path}")

            save_file = Save.from_file(save_path)

            if verbose:
                self._verbose_log(f"Parsed successfully: {save_path}")

            self.root.after(
                0,
                self._finalize_save_load,
                save_file,
                save_path,
                silent,
                toast_message,
            )
        except Exception as e:
            error_msg = str(e)
            if self.settings.get("verbose_logging", False):
                self._verbose_log(f"Load failed: {save_path}: {error_msg}")

            self.root.after(
                0,
                lambda: CTkMessageBox.showerror(
                    "Load Failed",
                    f"Failed to load save file:\n{error_msg}",
                    parent=self.root,
                ),
            )
            self.root.after(0, lambda: self.status_var.set("Load failed"))

    def _confirm_vanilla_save(self, save_path: str) -> bool:
        """Show the per-game online ban warning for a vanilla save.

        Asked once per path per session, so reloads after edits do not
        prompt again. Returns False when the user cancels.
        """
        from er_save_manager.ui.dialogs.vanilla_save_warning import (
            VanillaSaveWarningDialog,
            is_vanilla_save,
            warning_key,
        )

        key = os.path.normcase(os.path.abspath(save_path))
        if (
            not is_vanilla_save(save_path)
            or not self.settings.get("show_eac_warning", True)
            or key in self._vanilla_warned_paths
        ):
            return True

        profile = self._active_profile()
        dialog = VanillaSaveWarningDialog(
            self.root,
            warning_key(self.active_game, save_path),
            profile.name if profile else "Elden Ring",
            os.path.basename(save_path),
        )
        if not dialog.show():
            self.status_var.set(
                "Load cancelled - click 'Continue' in the warning to load a vanilla save"
            )
            return False
        if dialog.dont_show_again:
            self.settings.set("show_eac_warning", False)
        self._vanilla_warned_paths.add(key)
        return True

    def _game_issues(self):
        """save_check issues of the loaded non-ER save file."""
        from er_save_manager.games import save_check

        if not self.save_path:
            return None
        return save_check.check(self.active_game, self.save_path)

    def _check_game_save(self, slot_idx: int) -> None:
        """Show the issue view for one character of the active non-ER game."""
        from er_save_manager.ui.dialogs.save_check_dialog import show_issues

        game = self.active_game
        if game == "dark_souls_3":
            loader, char = self._load_ds3_save, self.ds3_save.characters[slot_idx]
            name = char.name if char else ""
        elif game == "dark_souls_remastered":
            loader, char = self._load_dsr_save, self.dsr_save.characters[slot_idx]
            name = char.name if char else ""
        elif game == "dark_souls_2":
            loader = self._load_ds2_save
            name = self.ds2_save.slot_display_name(slot_idx)
        elif game == "nightreign":
            loader = self._load_nr_save
            name = self._nr_save.slots[slot_idx].player_name
        else:
            return
        path = self.save_path
        show_issues(
            self.root,
            game,
            path,
            slot_idx,
            name or f"Character {slot_idx + 1}",
            lambda: loader(str(path)),
        )

    def _load_dsr_save(self, save_path: str) -> None:
        """Parse a DSR save file and refresh all DSR tabs."""
        self._flush_pending_tabs()
        if not self._guard_pending("load the save file"):
            return
        if self._reject_wrong_game(save_path):
            return
        from er_save_manager.games.DSR.save import DSRSave

        profile = self._active_profile()
        if (
            not self.settings.get("skip_game_running_check", False)
            and profile
            and profile.process_name
            and self.is_game_running(profile.process_name)
        ):
            if not self._handle_game_running_dialog(profile):
                return

        if not self._confirm_vanilla_save(save_path):
            return

        try:
            self.dsr_save = DSRSave.from_file(save_path)
        except Exception as e:
            CTkMessageBox.showerror(
                "Load Failed", f"Failed to load DSR save:\n{e}", parent=self.root
            )
            return

        self.save_path = Path(save_path)
        self.save_file = None
        self._update_watched_mtime()
        self._start_file_watcher()

        # Character tabs load through the character bar.
        for attr in ("dsr_inspector_tab", "dsr_char_mgmt_tab"):
            tab = getattr(self, attr, None)
            if tab is not None:
                tab.refresh()
        self._refresh_character_bar()

        self.status_var.set(f"Loaded: {os.path.basename(save_path)}")
        self.show_toast(
            f"DSR save loaded: {os.path.basename(save_path)}", duration=2500
        )

    def _on_dsr_slot_edit(self, slot_idx: int) -> None:
        """Navigate to Character Editor and load the selected slot.
        Called only from the inspector 'Edit Character' button - never from row clicks.
        """
        self._open_in_editor(slot_idx)

    def _load_ds3_save(self, save_path: str, running_checked: bool = False) -> None:
        """Parse a DS3 save file and refresh all DS3 tabs.

        running_checked skips the game-running check when the caller has
        already done it; the process query is slow on Windows.
        """
        self._flush_pending_tabs()
        if not self._guard_pending("load the save file"):
            return
        if self._reject_wrong_game(save_path):
            return
        from er_save_manager.games.DS3.save import DS3Save

        profile = self._active_profile()
        if (
            not running_checked
            and not self.settings.get("skip_game_running_check", False)
            and profile
            and profile.process_name
            and self.is_game_running(profile.process_name)
        ):
            if not self._handle_game_running_dialog(profile):
                return

        if not self._confirm_vanilla_save(save_path):
            return

        try:
            self.ds3_save = DS3Save.from_file(save_path)
        except Exception as e:
            CTkMessageBox.showerror(
                "Load Failed", f"Failed to load DS3 save:\n{e}", parent=self.root
            )
            return

        self.save_path = Path(save_path)
        self.save_file = None
        self._update_watched_mtime()
        self._start_file_watcher()

        # Character tabs load through the character bar.
        for attr in ("ds3_inspector_tab", "ds3_char_mgmt_tab"):
            tab = getattr(self, attr, None)
            if tab is not None:
                tab.refresh()
        self._refresh_character_bar()

        # The SteamID scan reads the whole save in pure Python; run it off the
        # UI thread so reloads do not freeze the window.
        steamid_tab = getattr(self, "steamid_tab", None)
        if steamid_tab is not None:
            threading.Thread(target=steamid_tab._on_game_changed, daemon=True).start()

        self.status_var.set(f"Loaded: {os.path.basename(save_path)}")
        self.show_toast(
            f"DS3 save loaded: {os.path.basename(save_path)}", duration=2500
        )

    def _load_ds2_save(self, save_path: str) -> None:
        """Parse a DS2 SOTFS save file and refresh the DS2 tabs."""
        self._flush_pending_tabs()
        if not self._guard_pending("load the save file"):
            return
        if self._reject_wrong_game(save_path):
            return
        from er_save_manager.games.DS2.save import DS2Save

        profile = self._active_profile()
        if (
            not self.settings.get("skip_game_running_check", False)
            and profile
            and profile.process_name
            and self.is_game_running(profile.process_name)
        ):
            if not self._handle_game_running_dialog(profile):
                return

        if not self._confirm_vanilla_save(save_path):
            return

        try:
            self.ds2_save = DS2Save.from_file(save_path)
        except Exception as e:
            CTkMessageBox.showerror(
                "Load Failed", f"Failed to load DS2 save:\n{e}", parent=self.root
            )
            return

        self.save_path = Path(save_path)
        self.save_file = None
        self._update_watched_mtime()
        self._start_file_watcher()

        # Character tabs load through the character bar.
        for attr in ("ds2_inspector_tab", "ds2_management_tab"):
            tab = getattr(self, attr, None)
            if tab is not None:
                tab.refresh()
        self._refresh_character_bar()

        # The SteamID scan reads the whole save in pure Python; run it off the
        # UI thread so reloads do not freeze the window.
        steamid_tab = getattr(self, "steamid_tab", None)
        if steamid_tab is not None:
            threading.Thread(target=steamid_tab._on_game_changed, daemon=True).start()

        self.status_var.set(f"Loaded: {os.path.basename(save_path)}")
        self.show_toast(
            f"DS2 save loaded: {os.path.basename(save_path)}", duration=2500
        )

    def _load_nr_save(self, save_path: str) -> None:
        """Parse a Nightreign save file and refresh all NR tabs."""
        self._flush_pending_tabs()
        if not self._guard_pending("load the save file"):
            return
        if self._reject_wrong_game(save_path):
            return
        profile = self._active_profile()
        if (
            not self.settings.get("skip_game_running_check", False)
            and profile
            and profile.process_name
            and self.is_game_running(profile.process_name)
        ):
            if not self._handle_game_running_dialog(profile):
                return

        if not self._confirm_vanilla_save(save_path):
            return

        try:
            self._nr_save = NightreignSave.from_file(save_path)
        except Exception as e:
            CTkMessageBox.showerror(
                "Load Failed", f"Failed to load Nightreign save:\n{e}", parent=self.root
            )
            return

        self.save_path = Path(save_path)
        self.save_file = None
        self._update_watched_mtime()
        self._start_file_watcher()

        # Character tabs load through the character bar.
        for attr in ("nr_inspector_tab", "nr_char_mgmt_tab"):
            tab = getattr(self, attr, None)
            if tab is not None:
                tab.refresh()
        self._refresh_character_bar()

        if hasattr(self, "nr_steamid_tab") and self.nr_steamid_tab:
            if self._nr_save and self._nr_save.profile:
                sid = self._nr_save.profile.steam_id
                path = Path(save_path)
                try:
                    self.nr_steamid_tab.current_steamid_var.set(
                        f"Save: {path.name}  |  SteamID: {sid}"
                    )
                except Exception:
                    pass

        self.status_var.set(f"Loaded: {os.path.basename(save_path)}")
        self.show_toast(
            f"Nightreign save loaded: {os.path.basename(save_path)}", duration=2500
        )

    def reload_save(self):
        """Reload the current save file without showing success message"""
        self.load_save(silent=True)

    def _on_ds3_slot_edit(self, slot_idx: int) -> None:
        """Navigate to Character Editor and load the selected slot.
        Called only from the DS3 inspector 'Edit Character' button.
        """
        self._open_in_editor(slot_idx)

    def _on_ds2_slot_selected(self, slot_idx: int) -> None:
        """Navigate to Character Editor and load the selected slot.
        Called from the DS2 inspector row double-click or Edit Character
        button.
        """
        self._open_in_editor(slot_idx)

    def _finalize_save_load(
        self,
        save_file,
        save_path,
        silent=False,
        toast_message="Save file loaded successfully.",
    ):
        """Finalize save loading on main thread"""
        self._flush_pending_tabs()
        self.save_file = save_file
        self.save_path = Path(save_path)
        self._update_watched_mtime()
        self._start_file_watcher()

        if self.active_game == "elden_ring":
            if hasattr(self, "char_mgmt_tab") and self.char_mgmt_tab:
                self.char_mgmt_tab.refresh_slot_names()
            if hasattr(self, "event_flags_tab") and self.event_flags_tab:
                self.event_flags_tab.refresh()

        # Reset all tab flags so views will refresh with the new save
        for tab_name in self.tabs_loaded:
            self.tabs_loaded[tab_name] = False

        if hasattr(self, "inventory_editor") and self.inventory_editor:
            self.inventory_editor.refresh_category_visibility()
        if self.active_game == "elden_ring":
            self._refresh_character_bar()

        # Lazy-load the currently visible tab immediately (ensures live refresh)
        current_tab = self.notebook.get()
        self._lazy_load_tab_background(current_tab)

        # Hide SteamID Patcher for PS saves - they have no SteamID.
        # Rebuild the notebook when toggling so the tab stays in its original position.
        if self.active_game == "elden_ring" and hasattr(self, "steamid_tab"):
            is_ps = getattr(save_file, "is_ps", False)
            tab_names = list(
                self.notebook._tab_dict.keys()
                if hasattr(self.notebook, "_tab_dict")
                else []
            )
            has_tab = "SteamID Patcher" in tab_names
            if is_ps and has_tab:
                self.notebook.delete("SteamID Patcher")
            elif not is_ps and not has_tab:
                # Rebuild the full ER notebook so SteamID Patcher lands at position 5
                # rather than being appended at the end.
                self._rebuild_er_notebook()

        self.status_var.set(f"Loaded: {os.path.basename(save_path)}")
        if not silent:
            self.show_toast(toast_message, duration=2500)

    def _rebuild_er_notebook(self) -> None:
        """Rebuild the ER notebook in place, preserving save state.

        Called when switching from a PS save back to a PC save so SteamID Patcher
        is re-inserted at its correct position rather than appended at the end.
        """
        self._drop_pending_tabs()
        self.pending_bar.clear_pages()
        self._character_tabs = {}
        self._feature_links = {}
        self.notebook.destroy()
        self.notebook = ctk.CTkTabview(
            self.root,
            width=1100,
            height=620,
            corner_radius=12,
            command=self._on_tab_changed,
        )
        self._grid_notebook()
        self.tabs_loaded = dict.fromkeys(self.tabs_loaded, False)
        for attr in (
            "inspector_tab",
            "char_mgmt_tab",
            "world_tab",
            "event_flags_tab",
            "gestures_tab",
            "appearance_tab",
            "steamid_tab",
            "hex_tab",
            "advanced_tab",
            "settings_tab",
        ):
            setattr(self, attr, None)
        self.create_tabs()
        self._place_character_bar()
        if self.save_file is not None:
            self._refresh_character_bar()
        self.root.after_idle(self._fit_tab_labels)

    def show_character_details(self, slot_idx):
        """Show character details dialog"""
        self._flush_pending_tabs()
        CharacterDetailsDialog.show(
            self.root,
            self.save_file,
            slot_idx,
            self.save_path,
            self.load_save,
            open_backup_settings=self.open_auto_backup_settings,
        )

    def open_auto_backup_settings(self):
        """Switch to the Settings tab, scrolled to the auto-backup section."""
        self._ensure_tab_built("Settings")
        self.notebook.set("Settings")
        self._on_tab_changed()
        tab = getattr(self, "settings_tab", None)
        if tab is not None:
            self.root.after(100, tab.scroll_to_auto_backup)

    def show_backup_manager_standalone(self):
        """Show backup manager from top button."""
        try:
            profile = PROFILES_BY_KEY.get(self.active_game)
            if not profile:
                return

            if not hasattr(self, "_backup_tab_helper"):
                self._backup_tab_helper = BackupManagerTab(
                    self.root,
                    lambda: self.save_file,
                    lambda: self.save_path,
                    self.load_save,
                    self.show_toast,
                )

            self._backup_tab_helper.open_for_profile(profile)

        except Exception as e:
            CTkMessageBox.showerror(
                "Backup Manager Failed",
                f"Failed to open backup manager:\n{e}",
                parent=self.root,
            )

    def _update_watched_mtime(self) -> None:
        """Snapshot the current mtime of the loaded save file."""
        try:
            if self.save_path and self.save_path.exists():
                self._watched_mtime = self.save_path.stat().st_mtime
        except OSError:
            self._watched_mtime = None

    def _start_file_watcher(self) -> None:
        """Start the external-modification poll loop if not already running."""
        if self._file_watcher_running:
            return
        self._file_watcher_running = True
        self.root.after(3000, self._poll_file_change)

    def _poll_file_change(self) -> None:
        """Poll for external save modifications every 3 seconds.

        Sets a pending flag instead of showing the dialog immediately so the
        user is only notified when they refocus the window.
        """
        if not self.save_path:
            self._file_watcher_running = False
            return

        try:
            current_mtime = self.save_path.stat().st_mtime
        except OSError:
            self.root.after(3000, self._poll_file_change)
            return

        if self._watched_mtime is not None and current_mtime != self._watched_mtime:
            self._watched_mtime = current_mtime
            # Writes from any tab, dialog or backup restore go through the
            # per-game save writers, the SteamID patchers or the backup
            # manager, which record them.
            if not self._file_change_dialog_open and not is_own_write(self.save_path):
                self._pending_file_change = True

        self.root.after(3000, self._poll_file_change)

    def _on_window_focus(self, event=None) -> None:
        """Show the external-modification dialog when an app window regains
        focus."""
        # Only fire for a window itself, not child widgets gaining focus
        window = self.root
        if event is not None:
            window = event.widget
            if isinstance(window, str) or window is not window.winfo_toplevel():
                return
        if not self._pending_file_change or self._file_change_dialog_open:
            return
        self._pending_file_change = False
        if self.settings.get("external_file_change_auto_reload", False):
            self._reload_changed_save()
            return
        if not self.settings.get("external_file_change_notification", True):
            return

        self._file_change_dialog_open = True

        from er_save_manager.ui import dialog_style as ds

        dialog = ds.create(window, "Save File Modified")
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=ctk.BOTH, expand=True, padx=20, pady=16)

        disable_var = ctk.BooleanVar(value=False)
        auto_var = ctk.BooleanVar(value=False)

        def on_reload():
            if auto_var.get():
                self.settings.set("external_file_change_auto_reload", True)
            self._file_change_dialog_open = False
            dialog.destroy()
            self._reload_changed_save()

        def on_dismiss():
            if disable_var.get():
                self.settings.set("external_file_change_notification", False)
            self._file_change_dialog_open = False
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_dismiss)

        ds.button_row(
            main,
            [
                {"text": "Reload Now", "command": on_reload, "width": 110},
                {"text": "Dismiss", "command": on_dismiss, "primary": False},
            ],
        )
        ctk.CTkCheckBox(
            main, text="Don't show this again", variable=disable_var, font=ds.FONT
        ).pack(side=ctk.BOTTOM, anchor=ctk.W, pady=(6, 0))
        ctk.CTkCheckBox(
            main,
            text="Always reload automatically",
            variable=auto_var,
            font=ds.FONT,
        ).pack(side=ctk.BOTTOM, anchor=ctk.W, pady=(12, 0))
        ds.header(main, "Save modified externally", icon="⚠")
        ctk.CTkLabel(
            main,
            text=(
                f"{self.save_path.name} was changed while the save manager "
                "had it loaded. Reload to avoid overwriting those changes."
            ),
            font=ds.FONT,
            justify=ctk.LEFT,
            wraplength=400,
        ).pack(anchor=ctk.W, pady=(10, 0))
        ds.finish(dialog, window)

    def _reload_changed_save(self) -> None:
        """Reload the save after an external change, keeping open popups."""
        self._reopen_popups_after_reload(popups.open_popups(self.root))
        if self.active_game in (
            "elden_ring",
            "dark_souls_remastered",
            "dark_souls_3",
            "dark_souls_2",
        ) or (self.active_game == "nightreign" and _NR_AVAILABLE):
            self.load_save(toast_message="Save file reloaded")
        else:
            # SteamID-only games have no parser; load_save would treat
            # the file as an Elden Ring save.
            self._load_non_er_save(str(self.save_path))

    def _reopen_popups_after_reload(self, windows) -> None:
        """Rebuild open data popups once the reload has replaced the save."""
        if not windows:
            return
        old = self._active_save()

        def wait(tries: int) -> None:
            if self._active_save() is old and tries < 300:
                self.root.after(100, wait, tries + 1)
                return
            self.root.after_idle(popups.reopen, windows)

        self.root.after(100, wait, 0)

    def _verbose_log(self, message: str) -> None:
        """Write a timestamped line to the verbose log file next to the current save."""
        import datetime

        save_path = self.file_path_var.get() if hasattr(self, "file_path_var") else ""
        log_dir = Path(save_path).parent if save_path else Path.home()
        log_path = log_dir / "er_save_manager.log"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except OSError:
            pass


def _windows_dpi_ignored() -> bool:
    """Whether the "Ignore Windows display scaling" setting applies."""
    return sys.platform == "win32" and bool(
        get_settings().get("ignore_windows_dpi", True)
    )


def _set_dpi_aware_unscaled() -> None:
    """Draw at 100% size on Windows while staying sharp.

    CTk normally makes the process per-monitor DPI aware and multiplies every
    size by the monitor scale. Turning its automatic scaling off would also
    skip the awareness call, and Windows would then bitmap-stretch the window
    (blurry). Setting the awareness here keeps pixels 1:1 at a factor of 1.0.
    """
    import ctypes

    ctk.deactivate_automatic_dpi_awareness()
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def main():
    """Main entry point for GUI"""
    from er_save_manager.ui.emoji_fallback import install as install_emoji_fallback
    from er_save_manager.ui.fonts import register as register_fonts

    install_emoji_fallback()
    register_fonts()
    ignore_dpi = _windows_dpi_ignored()
    if ignore_dpi:
        _set_dpi_aware_unscaled()
    root = ctk.CTk()
    if ignore_dpi:
        # Tk sizes point fonts from the monitor DPI; pin it to 96 DPI (100%)
        root.tk.call("tk", "scaling", 96 / 72)
    app = SaveManagerGUI(root)

    def on_closing():
        if not app.pending_bar.guard("close the window"):
            return
        app.save_window_state()
        if app.process_monitor:
            app.process_monitor.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
