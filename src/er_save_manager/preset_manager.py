"""Preset manager for community character presets."""

import json
import os
import platform
import tempfile
import time
import urllib.request
from pathlib import Path


class PresetManager:
    """Manage community character presets."""

    # Cache settings
    MAX_CACHE_SIZE_MB = 500  # Maximum total cache size
    FULL_IMAGE_EXPIRY_DAYS = 7  # Delete full images after 7 days
    THUMBNAIL_SIZE = (150, 150)  # Thumbnail dimensions

    def __init__(self):
        """Initialize preset manager with platform-appropriate cache location."""
        # Determine cache directory based on platform
        if platform.system() == "Linux":
            # Use XDG_CACHE_HOME if available, otherwise ~/.cache
            xdg_cache = os.environ.get("XDG_CACHE_HOME")
            if xdg_cache:
                self.cache_dir = Path(xdg_cache) / "er-save-manager"
            else:
                self.cache_dir = Path.home() / ".cache" / "er-save-manager"
        else:
            # Windows/macOS: use program directory
            program_dir = Path(__file__).parent.parent.parent
            self.cache_dir = program_dir / "data" / "presets"

        # Try to create cache directory, fallback to temp if permission denied
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            print(f"[Image Cache] Using cache directory: {self.cache_dir}")
        except (OSError, PermissionError) as e:
            # Fallback to system temp directory
            print(f"[Image Cache] Cannot write to {self.cache_dir}: {e}")
            self.cache_dir = Path(tempfile.gettempdir()) / "er-save-manager-cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            print(f"[Image Cache] Fallback cache directory: {self.cache_dir}")

        # Separate directories for different cache types
        self.thumbnails_dir = self.cache_dir / "thumbnails"
        self.thumbnails_dir.mkdir(exist_ok=True)
        print(f"[Image Cache] Thumbnails directory: {self.thumbnails_dir}")

        self.full_images_dir = self.cache_dir / "full_images"
        self.full_images_dir.mkdir(exist_ok=True)
        print(f"[Image Cache] Full images directory: {self.full_images_dir}")

        # GitHub repo URL
        self.base_url = (
            "https://raw.githubusercontent.com/Hapfel1/er-character-presets/main/"
        )

        self.cache_file = self.cache_dir / "cache.json"
        self.index_url = self.base_url + "index.json"

        # Perform cache maintenance on init
        self._cleanup_cache()

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
        Download preset data and thumbnails (not full images).

        Args:
            preset_id: Preset ID
            preset_info: Preset metadata from index

        Returns:
            Preset data dict or None if failed
        """
        try:
            print(f"[Preset Download] Starting download for preset {preset_id}")
            # Download preset JSON
            data_url = self.base_url + preset_info["data_url"]
            print(f"[Preset Download] Data URL: {data_url}")
            with urllib.request.urlopen(data_url, timeout=10) as response:
                preset_data = json.loads(response.read().decode("utf-8"))
            print(f"[Preset Download] Downloaded preset data for {preset_id}")

            # Download and create thumbnail
            screenshot_url = self.base_url + preset_info["screenshot_url"]
            print(f"[Preset Download] Screenshot URL: {screenshot_url}")
            thumbnail_path = self._download_and_create_thumbnail(
                preset_id, screenshot_url
            )

            # Cache preset data with metadata
            preset_path = self.cache_dir / f"{preset_id}.json"
            metadata = {
                "data": preset_data,
                "hash": self._compute_data_hash(preset_data),
                "preset_info_hash": self._compute_data_hash(preset_info),
            }
            with open(preset_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f)
            print(f"[Preset Download] Cached preset data to {preset_path}")

            if thumbnail_path:
                preset_data["screenshot_path"] = str(thumbnail_path)
                print(f"[Preset Download] Set screenshot path: {thumbnail_path}")
            else:
                print(f"[Preset Download] WARNING: No thumbnail for {preset_id}")
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
        thumbnail_path = self.thumbnails_dir / f"{preset_id}.png"

        # Legacy path for migration
        legacy_screenshot = self.cache_dir / f"{preset_id}.png"

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

                    # Check for thumbnail (prefer new location, fall back to legacy)
                    if thumbnail_path.exists():
                        data["screenshot_path"] = str(thumbnail_path)
                    elif legacy_screenshot.exists():
                        data["screenshot_path"] = str(legacy_screenshot)

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
        """
        Download full-size image from URL and save to cache with suffix.
        Full images are stored with access time tracking for LRU cleanup.
        """
        try:
            import urllib.request
            from pathlib import Path

            cache_dir = self.full_images_dir / preset_id
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

            # Update access time for LRU tracking
            filepath.touch()

            # Trigger cleanup if cache is too large
            self._cleanup_cache()

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
            self.thumbnails_dir.mkdir(exist_ok=True)
            self.full_images_dir.mkdir(exist_ok=True)

    def _download_and_create_thumbnail(
        self, preset_id: str, image_url: str
    ) -> Path | None:
        """
        Download image and create thumbnail. Thumbnails are always cached.

        Args:
            preset_id: Preset ID
            image_url: URL to download from

        Returns:
            Path to thumbnail or None if failed
        """
        try:
            thumbnail_path = self.thumbnails_dir / f"{preset_id}.png"

            # Return if already cached
            if thumbnail_path.exists():
                return thumbnail_path

            # Download full image temporarily
            with urllib.request.urlopen(image_url, timeout=10) as response:
                image_data = response.read()

            # Try to create thumbnail using PIL if available
            try:
                import io

                from PIL import Image

                img = Image.open(io.BytesIO(image_data))
                img.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                img.save(thumbnail_path, "PNG", optimize=True)
            except ImportError:
                # PIL not available, save full image as thumbnail
                thumbnail_path.write_bytes(image_data)

            return thumbnail_path
        except Exception:
            return None

    def _cleanup_cache(self):
        """
        Clean up cache:
        1. Delete full images older than FULL_IMAGE_EXPIRY_DAYS
        2. If cache exceeds MAX_CACHE_SIZE_MB, delete least recently accessed full images
        Thumbnails are never deleted.
        """
        try:
            current_time = time.time()
            expiry_seconds = self.FULL_IMAGE_EXPIRY_DAYS * 24 * 60 * 60

            # Collect all full image files with their stats
            full_image_files = []
            for file in self.full_images_dir.rglob("*"):
                if file.is_file():
                    stat = file.stat()
                    age = current_time - stat.st_mtime

                    # Delete expired files
                    if age > expiry_seconds:
                        try:
                            file.unlink()
                            print(f"Deleted expired cache file: {file.name}")
                            continue
                        except Exception:
                            pass

                    # Track for LRU cleanup
                    full_image_files.append(
                        {
                            "path": file,
                            "size": stat.st_size,
                            "atime": stat.st_atime,
                        }
                    )

            # Check total size
            total_size = sum(f["size"] for f in full_image_files)
            max_bytes = self.MAX_CACHE_SIZE_MB * 1024 * 1024

            # If over limit, delete oldest files (LRU)
            if total_size > max_bytes:
                # Sort by access time (oldest first)
                full_image_files.sort(key=lambda f: f["atime"])

                bytes_to_free = total_size - max_bytes
                freed = 0

                for file_info in full_image_files:
                    if freed >= bytes_to_free:
                        break

                    try:
                        file_info["path"].unlink()
                        freed += file_info["size"]
                        print(
                            f"Deleted cache file to free space: {file_info['path'].name}"
                        )
                    except Exception:
                        pass

                # Clean up empty directories
                for dir_path in self.full_images_dir.iterdir():
                    if dir_path.is_dir() and not any(dir_path.iterdir()):
                        try:
                            dir_path.rmdir()
                        except Exception:
                            pass

        except Exception as e:
            print(f"Cache cleanup error: {e}")

    def get_cache_size(self) -> dict:
        """
        Get current cache size information.

        Returns:
            Dict with 'thumbnails_mb', 'full_images_mb', 'total_mb'
        """
        try:
            thumbnails_size = sum(
                f.stat().st_size for f in self.thumbnails_dir.rglob("*") if f.is_file()
            )
            full_images_size = sum(
                f.stat().st_size for f in self.full_images_dir.rglob("*") if f.is_file()
            )

            return {
                "thumbnails_mb": thumbnails_size / (1024 * 1024),
                "full_images_mb": full_images_size / (1024 * 1024),
                "total_mb": (thumbnails_size + full_images_size) / (1024 * 1024),
            }
        except Exception:
            return {"thumbnails_mb": 0, "full_images_mb": 0, "total_mb": 0}
