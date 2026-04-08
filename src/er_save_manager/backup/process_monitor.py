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


class GameProcessMonitor:
    """
    Monitors for any configured game process and triggers automatic backups.

    Configuration is read from settings key "auto_backup_games":
        {
            "elden_ring": {"enabled": true, "save_path": "/path/to/ER0000.sl2"},
            "nightreign": {"enabled": true, "save_path": "/path/to/NR0000.sl2"},
            ...
        }

    One backup per game per tool session to avoid spam.
    """

    CHECK_INTERVAL = 5.0  # seconds

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        # Track whether a backup has been created this session per game key
        self._backed_up_this_session: set[str] = set()
        self._on_backup_created: Callable[[str, Path], None] | None = None

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
        self._backed_up_this_session.clear()
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

    def _monitor_loop(self) -> None:
        was_running: dict[str, bool] = dict.fromkeys(_PROCESS_NAMES, False)

        while self._running:
            try:
                settings = get_settings()
                auto_backup_cfg: dict = settings.get("auto_backup_games", {})

                for game_key, process_name in _PROCESS_NAMES.items():
                    game_cfg = auto_backup_cfg.get(game_key, {})
                    if not game_cfg.get("enabled", False):
                        was_running[game_key] = False
                        continue

                    save_path = game_cfg.get("save_path", "")
                    if not save_path:
                        continue

                    is_running = _is_process_running(process_name)

                    # Trigger on launch transition (not-running -> running)
                    if is_running and not was_running[game_key]:
                        # Apply CPU 0 affinity exclusion for supported games if configured.
                        if (
                            game_key in ("elden_ring", "dark_souls_3", "nightreign")
                            and sys.platform == "win32"
                        ):
                            if settings.get("cpu0_exclude_on_launch", False):
                                try:
                                    from er_save_manager.platform.cpu0_launcher import (
                                        apply_cpu0_exclusion,
                                    )

                                    apply_cpu0_exclusion(process_name)
                                except Exception as exc:
                                    print(f"CPU0 exclusion failed: {exc}")

                        if game_key not in self._backed_up_this_session:
                            backup_path = self._create_backup_for_game(
                                game_key, save_path
                            )
                            if backup_path:
                                self._backed_up_this_session.add(game_key)
                                if self._on_backup_created:
                                    self._on_backup_created(game_key, backup_path)

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

        # Try to find existing saves automatically
        found_paths = []
        if profile:
            try:
                from er_save_manager.platform.utils import PlatformUtils

                found_paths = PlatformUtils.find_all_save_files(profile)
            except Exception:
                pass

        chosen_path = None

        if len(found_paths) == 1:
            # One save found - confirm with user
            use_found = CTkMessageBox.askyesno(
                "Save File Found",
                f"Found save file:\n\n{found_paths[0]}\n\n"
                "Use this file for auto-backup?",
                parent=parent,
            )
            if use_found:
                chosen_path = str(found_paths[0])

        elif len(found_paths) > 1:
            # Multiple - show a quick picker dialog
            import tkinter as tk

            import customtkinter as ctk

            from er_save_manager.ui.utils import bind_mousewheel, force_render_dialog

            selected = [None]
            dlg = ctk.CTkToplevel(parent)
            dlg.title(f"Select Save - {game_name}")
            dlg.geometry("620x400")
            dlg.resizable(True, True)
            dlg.minsize(500, 300)
            force_render_dialog(dlg)
            dlg.grab_set()

            ctk.CTkLabel(
                dlg,
                text="Multiple save files found. Select the one to monitor:",
                font=("Segoe UI", 11),
            ).pack(pady=(15, 8), padx=15)

            sf = ctk.CTkScrollableFrame(dlg, corner_radius=8)
            sf.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
            bind_mousewheel(sf)

            for p in found_paths:

                def make_sel(v):
                    def _sel():
                        selected[0] = str(v)
                        dlg.destroy()

                    return _sel

                ctk.CTkButton(
                    sf,
                    text=str(p),
                    font=("Consolas", 10),
                    fg_color="transparent",
                    text_color=("#2a2a2a", "#e5e5f5"),
                    hover_color=("#c9a0dc", "#3b2f5c"),
                    anchor="w",
                    command=make_sel(p),
                ).pack(fill=tk.X, padx=6, pady=3)

            ctk.CTkButton(
                dlg,
                text="Browse...",
                command=lambda: [setattr(selected, "__browse__", True), dlg.destroy()],
                width=100,
            ).pack(side=tk.LEFT, padx=15, pady=(0, 12))
            ctk.CTkButton(dlg, text="Skip", command=dlg.destroy, width=80).pack(
                side=tk.RIGHT, padx=15, pady=(0, 12)
            )

            dlg.wait_window()
            chosen_path = selected[0]

        # If nothing picked yet, offer file browser
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

        # Save configuration
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
