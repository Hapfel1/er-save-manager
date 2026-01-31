"""Settings management for ER Save Manager."""

import json
from pathlib import Path
from typing import Any


class Settings:
    """Application settings manager."""

    def __init__(self, settings_file: Path | None = None):
        """Initialize settings."""
        if settings_file is None:
            # Store in program directory instead of user home
            program_dir = Path(__file__).parent.parent.parent.parent
            settings_dir = program_dir / "data"
            settings_dir.mkdir(exist_ok=True)
            settings_file = settings_dir / "settings.json"

        self.settings_file = settings_file
        self.settings = self._load_settings()

    def _load_settings(self) -> dict:
        """Load settings from file."""
        if not self.settings_file.exists():
            return self._get_default_settings()

        try:
            with open(self.settings_file, encoding="utf-8") as f:
                return json.load(f)
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
