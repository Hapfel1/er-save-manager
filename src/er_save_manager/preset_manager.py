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

            # Cache preset data with metadata
            preset_path = self.cache_dir / f"{preset_id}.json"
            metadata = {
                "data": preset_data,
                "hash": self._compute_data_hash(preset_data),
                "preset_info_hash": self._compute_data_hash(preset_info),
            }
            with open(preset_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f)

            preset_data["screenshot_path"] = str(screenshot_path)
            return preset_data

        except Exception as e:
            print(f"Failed to download preset {preset_id}: {e}")
            return None

    def get_cached_preset(self, preset_id: str) -> dict | None:
        """
        Get preset from local cache with validation.

        Args:
            preset_id: Preset ID

        Returns:
            Preset data or None if not cached or invalid
        """
        preset_path = self.cache_dir / f"{preset_id}.json"
        screenshot_path = self.cache_dir / f"{preset_id}.png"

        if preset_path.exists():
            try:
                with open(preset_path, encoding="utf-8") as f:
                    cached = json.load(f)

                # Handle both old format (direct data) and new format (with metadata)
                if isinstance(cached, dict):
                    # New format with metadata
                    if "data" in cached and "hash" in cached:
                        data = cached["data"]
                        stored_hash = cached["hash"]
                        # Validate hash to detect corruption
                        if self._compute_data_hash(data) != stored_hash:
                            print(
                                f"Cache validation failed for {preset_id}: hash mismatch"
                            )
                            return None
                    else:
                        # Old format, use as-is
                        data = cached

                    if screenshot_path.exists():
                        data["screenshot_path"] = str(screenshot_path)

                    return data
            except Exception as e:
                print(f"Error reading cached preset {preset_id}: {e}")
                return None

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

    def download_image(self, preset_id: str, url: str, suffix: str = "") -> Path | None:
        """Download image from URL and save to cache with suffix."""
        try:
            import urllib.request
            from pathlib import Path

            cache_dir = self.cache_dir / preset_id
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Build full URL
            if not url.startswith("http"):
                full_url = self.base_url + url
            else:
                full_url = url

            # Save with suffix
            ext = Path(url).suffix or ".png"
            filename = f"{preset_id}{suffix}{ext}"
            filepath = cache_dir / filename

            # Download if not cached
            if not filepath.exists():
                with urllib.request.urlopen(full_url, timeout=10) as response:
                    filepath.write_bytes(response.read())

            return filepath
        except Exception as e:
            print(f"Failed to download image: {e}")
            return None

    def _compute_data_hash(self, data: dict) -> str:
        """Compute hash of preset data for validation."""
        import hashlib

        # Create a stable JSON string for hashing
        stable_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.md5(stable_json.encode()).hexdigest()

    def validate_preset_in_index(
        self, preset_id: str, preset_info: dict
    ) -> tuple[bool, str]:
        """
        Validate cached preset against index metadata.

        Returns:
            (is_valid: bool, reason: str)
        """
        cached = self.get_cached_preset(preset_id)
        if not cached:
            return False, "Not cached"

        preset_path = self.cache_dir / f"{preset_id}.json"
        try:
            with open(preset_path, encoding="utf-8") as f:
                metadata = json.load(f)

            # Check if it's new format with metadata
            if "preset_info_hash" in metadata:
                stored_info_hash = metadata["preset_info_hash"]
                current_info_hash = self._compute_data_hash(preset_info)

                if stored_info_hash != current_info_hash:
                    return False, "Preset metadata changed in index"

            return True, "Valid"
        except Exception as e:
            print(f"Error validating preset {preset_id}: {e}")
            return False, f"Validation error: {e}"

    def clear_cache(self):
        """Clear all cached presets."""
        import shutil

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True)
