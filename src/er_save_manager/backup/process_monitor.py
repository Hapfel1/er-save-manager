"""Process monitor for automatic backups on game launch."""

from __future__ import annotations

import os
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


# /proc/<pid>/comm holds the first 15 bytes of the program name
_COMM_LENGTH = 15


def _program_name(argv0: str) -> str:
    """Lowercased file name of a program path, Unix or Windows (Wine/Proton
    report the game as Z:\\...\\game.exe)."""
    return argv0.replace("\\", "/").rsplit("/", 1)[-1].strip().lower()


def _proc_programs() -> dict[int, tuple[str, str]]:
    """pid -> (program name from argv[0], comm) of every process in /proc."""
    programs: dict[int, tuple[str, str]] = {}
    for entry in os.scandir("/proc"):
        if not entry.name.isdigit():
            continue
        try:
            with open(f"/proc/{entry.name}/cmdline", "rb") as f:
                argv0 = f.read().split(b"\0", 1)[0].decode(errors="replace")
            with open(f"/proc/{entry.name}/comm", "rb") as f:
                comm = f.read().decode(errors="replace").strip().lower()
            with open(f"/proc/{entry.name}/stat", "rb") as f:
                # State is the first field after the parenthesised comm
                state = f.read().rsplit(b")", 1)[1].split(None, 1)[0]
        except (OSError, IndexError):
            continue
        if state == b"Z":
            # Killed or exited, not yet reaped by its parent: keeps its comm
            continue
        programs[int(entry.name)] = (_program_name(argv0), comm)
    return programs


def _is_program(process_name: str, program: str, comm: str) -> bool:
    """True for the game itself, not for a process that only mentions its
    exe in the arguments (launch wrappers, a terminal, an editor)."""
    name = process_name.lower()
    return program == name or comm == name[:_COMM_LENGTH]


def running_programs() -> set[str] | None:
    """Lowercased program names of all running processes (Linux: also their
    comm), None when the listing fails."""
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
            return {
                line.split(",", 1)[0].strip('"').lower()
                for line in result.stdout.decode(errors="replace").splitlines()
                if line
            }
        if os.path.isdir("/proc"):
            names: set[str] = set()
            for program, comm in _proc_programs().values():
                names.add(program)
                names.add(comm)
            return names
        result = subprocess.run(
            ["ps", "-A", "-o", "comm="],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=2.0,
        )
        return {
            _program_name(line)
            for line in result.stdout.decode(errors="replace").splitlines()
        }
    except Exception:
        return None


def is_running_in(process_name: str, programs: set[str] | None) -> bool:
    if not programs:
        return False
    name = process_name.lower()
    return name in programs or name[:_COMM_LENGTH] in programs


def game_pids(process_name: str) -> list[int]:
    """Pids of the game process (Linux /proc only)."""
    if not os.path.isdir("/proc"):
        return []
    return [
        pid
        for pid, (program, comm) in _proc_programs().items()
        if _is_program(process_name, program, comm)
    ]


def _is_process_running(process_name: str) -> bool:
    """Check if the game process is running. Matches the program itself
    (Windows image name, Linux argv[0] or comm), so a process that only has
    the exe name in its arguments does not count."""
    return is_running_in(process_name, running_programs())


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
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._on_backup_created: Callable[[str, Path], None] | None = None
        # Timestamp of the last interval backup per game key, reset on each launch
        self._interval_last_backup: dict[str, float] = {}
        # Last reported failure per game key; a repeat of it is not reported
        # again until a backup succeeds or the game exits.
        self._last_failure: dict[str, str] = {}

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
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _report_failure(self, game_key: str, exc: BaseException) -> None:
        """Log a failed auto-backup to errors.log and show an error toast."""
        from er_save_manager.games.game_profiles import PROFILES_BY_KEY

        profile = PROFILES_BY_KEY.get(game_key)
        game_name = profile.name if profile else game_key
        message = f"{game_name} auto-backup failed: {exc}"
        if self._last_failure.get(game_key) == message:
            return
        self._last_failure[game_key] = message

        try:
            from er_save_manager.ui.error_report import log_exception

            log_exception(type(exc), exc, exc.__traceback__, "Auto-backup")
        except Exception:
            pass
        try:
            import tkinter as tk

            from er_save_manager.ui.toast import show_toast

            root = tk._default_root
            if root is not None:
                root.after(0, lambda: show_toast(root, message, 8000, "error"))
        except Exception:
            pass

    def _create_backup_for_game(self, game_key: str, save_path: str) -> Path | None:
        try:
            path = Path(save_path)
            if not path.exists():
                raise FileNotFoundError(f"Save file not found: {path}")

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
            self._last_failure.pop(game_key, None)
            return backup_path
        except Exception as e:
            self._report_failure(game_key, e)
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

                listing = running_programs()
                for game_key, process_name in _PROCESS_NAMES.items():
                    is_running = is_running_in(process_name, listing)
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
                            if backup_path and self._on_backup_created:
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
                        self._last_failure.pop(game_key, None)

                    was_running[game_key] = is_running

            except Exception as e:
                print(f"Process monitor error: {e}")

            self._stop_event.wait(self.CHECK_INTERVAL)


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
        from er_save_manager.ui.messagebox import CTkMessageBox
        from er_save_manager.ui.utils import pick_file

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
                parent,
                found_paths,
                lambda _path: None,
                game_key=profile.key if profile else None,
            )

        if not chosen_path:
            ext_str = " ".join(
                f"*{e}" for e in (profile.extensions if profile else [".sl2"])
            )
            file_path = pick_file(
                title=f"Choose Save File for Auto-Backup - {game_name}",
                filetypes=[(f"{game_name} Save", ext_str), ("All files", "*.*")],
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
