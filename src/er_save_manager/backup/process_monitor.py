"""Process monitor for automatic backups on game launch."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

from er_save_manager.backup.manager import BackupManager
from er_save_manager.ui.settings import get_settings

# Map game key -> process name to detect
_PROCESS_NAMES: dict[str, str] = {
    "elden_ring": "eldenring.exe",
    "nightreign": "nightreign.exe",
    "armored_core_6": "armoredcore6.exe",
    "dark_souls_3": "darksoulsiii.exe",
    "dark_souls_2": "darksoulsii.exe",
    "dark_souls_remastered": "darksoulsremastered.exe",
    "sekiro": "sekiro.exe",
}


def _is_process_running(process_name: str) -> bool:
    """
    Check if a process is currently running.

    Windows: tasklist with CREATE_NO_WINDOW to avoid CMD flash.
    Linux: pgrep -f - same approach as PlatformUtils.is_game_running(), works for Wine/Proton.
    """
    name_lower = process_name.lower()
    try:
        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/NH"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=2.0,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=si,
            )
            return name_lower in result.stdout.decode(errors="replace").lower()
        else:
            result = subprocess.run(
                ["pgrep", "-f", process_name],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2.0,
            )
            return result.returncode == 0
    except Exception:
        return False


def _running_processes_text() -> str:
    """Lowercased list of all running processes, from one process spawn.

    Windows: image names from tasklist. Elsewhere: full command lines from
    ps, which hold the .exe name for Wine/Proton games as pgrep -f sees it.
    Empty when the listing fails.
    """
    try:
        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=2.0,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=si,
            )
        else:
            result = subprocess.run(
                ["ps", "-A", "-o", "args="],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=2.0,
            )
        return result.stdout.decode(errors="replace").lower()
    except Exception:
        return ""


class GameProcessMonitor:
    """
    Monitors for any configured game process and triggers automatic backups.

    Configuration is read from settings key "auto_backup_games":
        {
            "elden_ring": {"enabled": true, "save_path": "/path/to/ER0000.sl2"},
            "nightreign": {"enabled": true, "save_path": "/path/to/NR0000.sl2"},
            ...
        }
    """

    CHECK_INTERVAL = 5.0  # seconds

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._on_backup_created: Callable[[str, Path], None] | None = None
        # Timestamp of the last interval backup per game key, reset on each launch
        self._interval_last_backup: dict[str, float] = {}

    def set_backup_callback(self, callback: Callable[[str, Path], None]) -> None:
        """
        Set callback invoked when a backup is created.
        Receives (game_key, backup_path).
        """
        self._on_backup_created = callback

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _create_backup_for_game(self, game_key: str, save_path: str) -> Path | None:
        try:
            path = Path(save_path)
            if not path.exists():
                return None

            manager = BackupManager(path)

            # Try to parse ER saves for character info; skip for others
            save_obj = None
            if game_key == "elden_ring":
                try:
                    from er_save_manager.parser import Save

                    save_obj = Save.from_file(save_path)
                except Exception:
                    pass

            backup_path, _ = manager.create_backup(
                description="game_launch",
                operation="auto_backup",
                save=save_obj,
            )
            return backup_path
        except Exception as e:
            print(f"Auto-backup failed for {game_key}: {e}")
            return None

    # Games that support CPU 0 exclusion.
    _CPU0_GAMES = frozenset(("elden_ring", "dark_souls_3", "nightreign"))

    def _monitor_loop(self) -> None:
        was_running: dict[str, bool] = dict.fromkeys(_PROCESS_NAMES, False)

        while self._running:
            try:
                settings = get_settings()
                auto_backup_cfg: dict = settings.get("auto_backup_games", {})
                cpu0_enabled = sys.platform == "win32" and settings.get(
                    "cpu0_exclude_on_launch", False
                )

                listing = _running_processes_text()
                for game_key, process_name in _PROCESS_NAMES.items():
                    is_running = process_name.lower() in listing
                    launched = is_running and not was_running[game_key]

                    if launched:
                        # CPU 0 exclusion runs regardless of auto-backup config.
                        if cpu0_enabled and game_key in self._CPU0_GAMES:
                            try:
                                from er_save_manager.platform.cpu0_launcher import (
                                    apply_cpu0_exclusion,
                                )

                                apply_cpu0_exclusion(process_name)
                            except Exception as exc:
                                print(f"CPU0 exclusion failed: {exc}")

                        # Auto-backup requires the game to be configured and enabled.
                        game_cfg = auto_backup_cfg.get(game_key, {})
                        save_path = (
                            game_cfg.get("save_path", "")
                            if game_cfg.get("enabled", False)
                            else ""
                        )
                        if save_path:
                            backup_path = self._create_backup_for_game(
                                game_key, save_path
                            )
                            if backup_path:
                                if self._on_backup_created:
                                    self._on_backup_created(game_key, backup_path)

                        # Reset the interval timer for this session regardless of
                        # whether an on-launch backup was created above.
                        self._interval_last_backup[game_key] = time.time()

                    elif is_running:
                        # Interval backups require auto-backup on game launch to
                        # be enabled for the same monitored save file.
                        game_cfg = auto_backup_cfg.get(game_key, {})
                        try:
                            interval_minutes = int(game_cfg.get("interval_minutes", 0))
                        except (TypeError, ValueError):
                            interval_minutes = 0
                        save_path = game_cfg.get("save_path", "")
                        if (
                            game_cfg.get("enabled", False)
                            and game_cfg.get("interval_enabled", False)
                            and interval_minutes > 0
                            and save_path
                        ):
                            last = self._interval_last_backup.get(game_key, 0.0)
                            if time.time() - last >= interval_minutes * 60:
                                backup_path = self._create_backup_for_game(
                                    game_key, save_path
                                )
                                if backup_path:
                                    self._interval_last_backup[game_key] = time.time()
                                    if self._on_backup_created:
                                        self._on_backup_created(game_key, backup_path)

                    if not is_running:
                        self._interval_last_backup.pop(game_key, None)

                    was_running[game_key] = is_running

            except Exception as e:
                print(f"Process monitor error: {e}")

            time.sleep(self.CHECK_INTERVAL)


def show_auto_backup_first_run_dialog(
    parent=None,
    profile=None,
    # Legacy params kept for backward compat but ignored
    get_save_path_callback=None,
    get_default_save_path_callback=None,
) -> bool:
    """
    Show the auto-backup setup wizard the first time Backup Manager is
    opened for a given game. Records completion per-game so it only shows once.

    Returns True if auto-backup was configured, False if dismissed.
    """
    try:
        import tkinter.filedialog as filedialog

        from er_save_manager.ui.messagebox import CTkMessageBox

        settings = get_settings()

        # Mark this game as done regardless of user choice
        done: list = list(settings.get("auto_backup_first_run_done", []))
        game_key = profile.key if profile else "elden_ring"
        game_name = profile.name if profile else "Elden Ring"
        if game_key not in done:
            done.append(game_key)
            settings.set("auto_backup_first_run_done", done)

        # Also clear the legacy global flag so old code paths don't re-trigger
        settings.set("auto_backup_first_run_check", False)

        result = CTkMessageBox.askyesno(
            "Auto-Backup Setup",
            f"Would you like to enable automatic backups for {game_name}?\n\n"
            f"When enabled, a backup of your {game_name} save will be created "
            "automatically whenever the game launches.\n\n"
            "You can change this later in Settings.",
            parent=parent,
        )

        if not result:
            return False

        found_paths = []
        if profile:
            try:
                from er_save_manager.platform.utils import PlatformUtils

                found_paths = PlatformUtils.find_all_save_files(profile)
            except Exception:
                pass

        chosen_path = None

        if len(found_paths) == 1:
            use_found = CTkMessageBox.askyesno(
                "Save File Found",
                f"Found save file:\n\n{found_paths[0]}\n\n"
                "Use this file for auto-backup?",
                parent=parent,
            )
            if use_found:
                chosen_path = str(found_paths[0])

        elif len(found_paths) > 1:
            from er_save_manager.ui.dialogs.save_selector import SaveSelectorDialog

            # Closing without a pick falls through to the file dialog below
            chosen_path = SaveSelectorDialog.show(
                parent, found_paths, lambda _path: None
            )

        if not chosen_path:
            ext_str = " ".join(
                f"*{e}" for e in (profile.extensions if profile else [".sl2"])
            )
            file_path = filedialog.askopenfilename(
                title=f"Choose Save File for Auto-Backup - {game_name}",
                filetypes=[(f"{game_name} Save", ext_str), ("All files", "*.*")],
                parent=parent,
            )
            if file_path:
                chosen_path = str(file_path)

        if not chosen_path:
            return False

        from pathlib import Path

        chosen_path = str(Path(chosen_path).resolve())
        auto_backup_cfg: dict = dict(settings.get("auto_backup_games", {}))
        auto_backup_cfg[game_key] = {"enabled": True, "save_path": chosen_path}
        settings.set("auto_backup_games", auto_backup_cfg)

        CTkMessageBox.showinfo(
            "Auto-Backup Enabled",
            f"Auto-backup is now enabled for {game_name}.\n\n"
            f"Monitored file:\n{chosen_path}\n\n"
            "A backup will be created automatically each time the game launches.",
            parent=parent,
        )
        return True

    except Exception as e:
        print(f"Auto-backup first-run dialog error: {e}")
        return False
