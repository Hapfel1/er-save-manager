"""Settings management for ER Save Manager."""

import json
import platform
from pathlib import Path
from typing import Any


class Settings:
    """Application settings manager."""

    def __init__(self, settings_file: Path | None = None):
        """Initialize settings."""
        if settings_file is None:
            # Store in platform-appropriate AppData directory to persist across reinstalls
            settings_file = self._get_default_settings_path()
            settings_file.parent.mkdir(parents=True, exist_ok=True)

        self.settings_file = settings_file
        self.settings = self._load_settings()

    @staticmethod
    def _get_default_settings_path() -> Path:
        """Get platform-appropriate settings file path."""
        system = platform.system()

        if system == "Windows":
            # Windows: %APPDATA%\ER Save Manager\settings.json
            import os

            appdata = os.getenv("APPDATA")
            if appdata:
                return Path(appdata) / "ER Save Manager" / "settings.json"
        elif system == "Darwin":
            # macOS: ~/Library/Application Support/ER Save Manager/settings.json
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / "ER Save Manager"
                / "settings.json"
            )
        elif system == "Linux":
            # Linux: ~/.local/share/er-save-manager/settings.json or $XDG_DATA_HOME
            import os

            xdg_data = os.getenv("XDG_DATA_HOME")
            if xdg_data:
                return Path(xdg_data) / "er-save-manager" / "settings.json"
            return (
                Path.home() / ".local" / "share" / "er-save-manager" / "settings.json"
            )

        # Fallback to program directory if platform unknown
        program_dir = Path(__file__).parent.parent.parent.parent
        return program_dir / "data" / "settings.json"

    def _load_settings(self) -> dict:
        """Load settings from file."""
        if not self.settings_file.exists():
            return self._get_default_settings()

        try:
            with open(self.settings_file, encoding="utf-8") as f:
                data = json.load(f)
            # Merge with defaults so new keys are always present
            defaults = self._get_default_settings()
            for key, value in defaults.items():
                if key not in data:
                    data[key] = value
            # Migrate legacy single-game auto-backup into per-game format
            if data.get("auto_backup_on_game_launch") and not data.get(
                "auto_backup_games"
            ):
                legacy_path = data.get("auto_backup_save_path", "")
                if legacy_path:
                    data["auto_backup_games"] = {
                        "elden_ring": {"enabled": True, "save_path": legacy_path}
                    }
            return data
        except Exception:
            return self._get_default_settings()

    def _get_default_settings(self) -> dict:
        """Get default settings."""
        return {
            "show_eac_warning": True,
            "auto_backup": True,
            "backup_on_save": True,
            "max_backups": 50,
            "remember_last_location": True,
            "last_save_path": "",
            "theme": "dark",
            "show_linux_save_warning": True,
            "show_backup_pruning_warning": True,
            "show_update_notifications": True,
            "compress_backups": True,
            # Legacy single-game auto-backup (kept for migration)
            "auto_backup_on_game_launch": False,
            "auto_backup_save_path": "",
            "auto_backup_first_run_check": True,
            # Per-game first-run tracking: list of game keys that have been shown the wizard
            "auto_backup_first_run_done": [],
            # Per-game auto-backup: {game_key: {enabled: bool, save_path: str}}
            "auto_backup_games": {},
            # Advanced settings (unlocked via secret key sequence in Settings tab)
            "advanced_mode_unlocked": False,
            "skip_game_running_check": False,
            "verbose_logging": False,
            # Debug: show manual CSNetMan replace button in Character Details
            "debug_netman_replace": False,
            # Notify when the loaded save file is modified externally
            "external_file_change_notification": True,
            # UI scaling factor applied via CTk widget/window scaling APIs.
            # None means auto-detect from the system on startup.
            "ui_scale": 1.0,
        }

    def save(self):
        """Save settings to file."""
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        """Set a setting value."""
        self.settings[key] = value
        self.save()

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self.settings = self._get_default_settings()
        self.save()


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def detect_system_scale() -> float:
    """Return the display scale reported by the OS, or 1.0 as fallback.

    Linux: reads GDK_SCALE then QT_SCALE_FACTOR (set by Plasma global scale).
    Windows: reads the system DPI via GetDpiForSystem (Win8.1+) with a GDI
             fallback. 96 DPI = 1.0, 192 DPI = 2.0, etc.
    Returns 1.0 when detection fails or the value is out of the 0.5-4.0 range.
    """
    import platform as _platform

    system = _platform.system()

    if system == "Linux":
        import os

        for var in ("GDK_SCALE", "QT_SCALE_FACTOR"):
            raw = os.environ.get(var, "").strip()
            if raw:
                try:
                    value = float(raw)
                    if 0.5 <= value <= 4.0:
                        return value
                except ValueError:
                    pass
        return 1.0

    if system == "Windows":
        import ctypes

        try:
            # GetDpiForSystem available on Windows 8.1+
            dpi = ctypes.windll.user32.GetDpiForSystem()
            if dpi > 0:
                scale = dpi / 96.0
                if 0.5 <= scale <= 4.0:
                    return scale
        except Exception:
            pass

        try:
            # GDI fallback for older Windows
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, hdc)
            if dpi > 0:
                scale = dpi / 96.0
                if 0.5 <= scale <= 4.0:
                    return scale
        except Exception:
            pass

        return 1.0

    return 1.0
