"""Process monitor for automatic backups when Elden Ring launches."""

from __future__ import annotations

import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

from er_save_manager.backup.manager import BackupManager
from er_save_manager.parser import Save
from er_save_manager.ui.settings import get_settings


class GameProcessMonitor:
    """
    Monitors for Elden Ring process and triggers automatic backups.

    Features:
    - Detects eldenring.exe launch
    - Creates automatic backup before first game session
    - One backup per tool session to avoid spam
    - Runs in background thread
    """

    PROCESS_NAME = "eldenring.exe"
    CHECK_INTERVAL = 5.0  # seconds

    def __init__(self):
        """Initialize the process monitor."""
        self._running = False
        self._thread: threading.Thread | None = None
        self._backup_created_this_session = False
        self._on_backup_created: Callable[[Path], None] | None = None

    def set_backup_callback(self, callback: Callable[[Path], None]) -> None:
        """Set callback to be called when backup is created."""
        self._on_backup_created = callback

    def start(self) -> None:
        """Start monitoring for Elden Ring process."""
        if self._running:
            return

        self._running = True
        self._backup_created_this_session = False
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _is_process_running(self) -> bool:
        """Check if Elden Ring is currently running."""
        try:
            if subprocess.sys.platform == "win32":
                # Windows: use tasklist
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {self.PROCESS_NAME}"],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
                return self.PROCESS_NAME.lower() in result.stdout.lower()
            else:
                # Linux: use ps
                result = subprocess.run(
                    ["pgrep", "-x", "eldenring.exe"],
                    capture_output=True,
                    timeout=2.0,
                )
                return result.returncode == 0
        except Exception:
            return False

    def _create_auto_backup(self) -> Path | None:
        """Create automatic backup for configured save file."""
        try:
            settings = get_settings()
            save_path = settings.get("auto_backup_save_path", "")

            if not save_path or not Path(save_path).exists():
                return None

            # Create backup
            manager = BackupManager(save_path)

            # Try to parse save for character info
            save_obj = None
            try:
                save_obj = Save.from_file(save_path)
            except Exception:
                pass  # Continue without character info

            backup_path, _ = manager.create_backup(
                description="game_launch",
                operation="auto_backup",
                save=save_obj,
            )

            return backup_path

        except Exception as e:
            print(f"Auto-backup failed: {e}")
            return None

    def _monitor_loop(self) -> None:
        """Main monitoring loop (runs in background thread)."""
        game_was_running = False

        while self._running:
            try:
                settings = get_settings()

                # Check if auto-backup is enabled
                if not settings.get("auto_backup_on_game_launch", False):
                    time.sleep(self.CHECK_INTERVAL)
                    continue

                # Check if game is running
                game_is_running = self._is_process_running()

                # Trigger backup on game launch (transition from not running to running)
                if game_is_running and not game_was_running:
                    if not self._backup_created_this_session:
                        backup_path = self._create_auto_backup()
                        if backup_path:
                            self._backup_created_this_session = True
                            if self._on_backup_created:
                                self._on_backup_created(backup_path)

                game_was_running = game_is_running

            except Exception as e:
                print(f"Process monitor error: {e}")

            time.sleep(self.CHECK_INTERVAL)


def show_auto_backup_first_run_dialog(
    parent=None, get_save_path_callback=None, get_default_save_path_callback=None
) -> bool:
    """
    Show first-run dialog asking if user wants to enable auto-backup.

    Args:
        parent: Parent window for centering the dialog
        get_save_path_callback: Optional callback to get currently loaded save path
        get_default_save_path_callback: Optional callback to get default save location

    Returns:
        True if configured successfully, False if dismissed
    """
    try:
        import os
        import tkinter.filedialog as filedialog

        from er_save_manager.ui.messagebox import CTkMessageBox

        # Mark first run complete
        settings = get_settings()
        settings.set("auto_backup_first_run_check", False)

        # Ask if they want to enable auto-backup
        result = CTkMessageBox.askyesno(
            "Auto-Backup Feature",
            "Would you like to enable automatic backups?\n\n"
            "When enabled, the tool will automatically create a backup of your "
            "chosen save file whenever Elden Ring launches.\n\n"
            "You can configure this in Settings > Backups later.",
            parent=parent,
            font_size=12,
        )

        if not result:
            return False

        # User wants to configure - show save file selection dialog
        current_save = None
        if get_save_path_callback:
            current_save = get_save_path_callback()

        # If save is loaded, offer to use it
        if current_save and Path(current_save).exists():
            choice = CTkMessageBox.askyesnocancel(
                "Choose Save File",
                f"Currently loaded save file:\n\n{current_save}\n\n"
                "Would you like to use this save file for auto-backup?\n\n"
                "Yes - Use current save\n"
                "No - Browse for a different save\n"
                "Cancel - Don't configure now",
                parent=parent,
                font_size=11,
            )

            if choice is None:  # Cancel
                return False
            elif choice:  # Yes - use current save
                file_path = str(Path(current_save).resolve())
                settings.set("auto_backup_save_path", file_path)
                settings.set("auto_backup_on_game_launch", True)

                CTkMessageBox.showinfo(
                    "Auto-Backup Enabled",
                    f"Auto-backup is now enabled and will monitor:\n\n{file_path}\n\n"
                    "A backup will be created automatically when Elden Ring launches.",
                    parent=parent,
                )
                return True
            # If No, continue to file browser below

        # Get default save location
        initial_dir = os.path.expanduser("~")
        if get_default_save_path_callback:
            default_path = get_default_save_path_callback()
            if default_path and Path(default_path).exists():
                initial_dir = str(default_path)

        # Show file browser
        file_path = filedialog.askopenfilename(
            title="Choose Save File for Auto-Backup",
            filetypes=[
                ("Elden Ring Save", "*.sl2;*.co2"),
                ("PC Save Files", "*.sl2"),
                ("Console Save Files", "*.co2"),
                ("All files", "*.*"),
            ],
            initialdir=initial_dir,
            parent=parent,
        )

        if file_path:
            file_path = str(Path(file_path).resolve())
            settings.set("auto_backup_save_path", file_path)
            settings.set("auto_backup_on_game_launch", True)

            CTkMessageBox.showinfo(
                "Auto-Backup Enabled",
                f"Auto-backup is now enabled and will monitor:\n\n{file_path}\n\n"
                "A backup will be created automatically when Elden Ring launches.",
                parent=parent,
            )
            return True

        return False

    except Exception as e:
        print(f"Auto-backup first-run dialog error: {e}")
        return False
