"""Preset manager for community character presets."""

import json
import urllib.request
from pathlib import Path


class PresetManager:
    """Manage community character presets."""

    def __init__(self):
        """Initialize preset manager."""
        self.cache_dir = Path.home() / ".er_save_manager" / "presets"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # GitHub repo URL - update this to your actual repo
        self.base_url = (
            "https://raw.githubusercontent.com/Hapfel1/er-character-presets/main/"
        )

        self.cache_file = self.cache_dir / "cache.json"
        self.index_url = self.base_url + "index.json"

    def fetch_index(self, force_refresh: bool = False) -> dict:
        """
        Fetch preset index from remote or cache.

        Args:
            force_refresh: Force download even if cache exists

        Returns:
            Index data dict
        """
        # Check cache first if not forcing refresh
        if not force_refresh and self.cache_file.exists():
            try:
                import datetime

                # Check if cache is less than 1 hour old
                cache_age = (
                    datetime.datetime.now().timestamp()
                    - self.cache_file.stat().st_mtime
                )
                if cache_age < 3600:  # 1 hour
                    with open(self.cache_file, encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass

        # Download from remote
        try:
            with urllib.request.urlopen(self.index_url, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            # Cache it
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)

            return data

        except Exception as e:
            print(f"Failed to fetch remote index: {e}")

            # Fall back to cache if available
            if self.cache_file.exists():
                with open(self.cache_file, encoding="utf-8") as f:
                    return json.load(f)

            # No cache available
            return {"version": "0.0.0", "presets": []}

    def download_preset(self, preset_id: str, preset_info: dict) -> dict | None:
        """
        Download preset data and screenshot.

        Args:
            preset_id: Preset ID
            preset_info: Preset metadata from index

        Returns:
            Preset data dict or None if failed
        """
        try:
            # Download preset JSON
            data_url = self.base_url + preset_info["data_url"]
            with urllib.request.urlopen(data_url, timeout=10) as response:
                preset_data = json.loads(response.read().decode("utf-8"))

            # Download screenshot
            screenshot_url = self.base_url + preset_info["screenshot_url"]
            screenshot_path = self.cache_dir / f"{preset_id}.png"

            with urllib.request.urlopen(screenshot_url, timeout=10) as response:
                screenshot_path.write_bytes(response.read())

            # Cache preset data
            preset_path = self.cache_dir / f"{preset_id}.json"
            with open(preset_path, "w", encoding="utf-8") as f:
                json.dump(preset_data, f)

            preset_data["screenshot_path"] = str(screenshot_path)
            return preset_data

        except Exception as e:
            print(f"Failed to download preset {preset_id}: {e}")
            return None

    def get_cached_preset(self, preset_id: str) -> dict | None:
        """
        Get preset from local cache.

        Args:
            preset_id: Preset ID

        Returns:
            Preset data or None if not cached
        """
        preset_path = self.cache_dir / f"{preset_id}.json"
        screenshot_path = self.cache_dir / f"{preset_id}.png"

        if preset_path.exists():
            with open(preset_path, encoding="utf-8") as f:
                data = json.load(f)

            if screenshot_path.exists():
                data["screenshot_path"] = str(screenshot_path)

            return data

        return None

    def apply_preset_to_character(self, preset_data: dict, character_presets_module):
        """
        Apply preset appearance data to character using CharacterPresets.

        Args:
            preset_data: Preset data dict with 'appearance' key
            character_presets_module: CharacterPresets instance

        Returns:
            True if successful
        """
        try:
            # Get appearance dict from preset
            appearance = preset_data["appearance"]

            # Use CharacterPresets to apply the appearance
            character_presets_module.from_dict(appearance)

            return True

        except Exception as e:
            print(f"Failed to apply preset: {e}")
            return False

    def clear_cache(self):
        """Clear all cached presets."""
        import shutil

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True)
