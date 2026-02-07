"""Character manager for community character library."""

import json
import os
import platform
import ssl
import tempfile
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


class CharacterManager:
    """Manage community character library with streaming downloads."""

    # Cache settings
    MAX_CACHE_SIZE_MB = 100  # Maximum total cache size (smaller than presets)
    METADATA_EXPIRY_HOURS = 1  # Cache metadata for 1 hour
    THUMBNAIL_SIZE = (200, 200)  # Thumbnail dimensions

    def __init__(self):
        """Initialize character manager with platform-appropriate cache location."""
        # Determine cache directory based on platform
        if platform.system() == "Linux":
            # Use XDG_CACHE_HOME if available, otherwise ~/.cache
            xdg_cache = os.environ.get("XDG_CACHE_HOME")
            if xdg_cache:
                self.cache_dir = Path(xdg_cache) / "er-save-manager" / "characters"
            else:
                self.cache_dir = (
                    Path.home() / ".cache" / "er-save-manager" / "characters"
                )
        else:
            # Windows/macOS: use program directory
            program_dir = Path(__file__).parent.parent.parent
            self.cache_dir = program_dir / "data" / "characters"

        # Try to create cache directory, fallback to temp if permission denied
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            print(f"[Character Cache] Using cache directory: {self.cache_dir}")
        except (OSError, PermissionError) as e:
            # Fallback to system temp directory
            print(f"[Character Cache] Cannot write to {self.cache_dir}: {e}")
            self.cache_dir = Path(tempfile.gettempdir()) / "er-save-manager-characters"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            print(f"[Character Cache] Fallback cache directory: {self.cache_dir}")

        # Separate directories for different cache types
        self.thumbnails_dir = self.cache_dir / "thumbnails"
        self.thumbnails_dir.mkdir(exist_ok=True)
        print(f"[Character Cache] Thumbnails directory: {self.thumbnails_dir}")

        self.metadata_dir = self.cache_dir / "metadata"
        self.metadata_dir.mkdir(exist_ok=True)
        print(f"[Character Cache] Metadata directory: {self.metadata_dir}")

        # GitHub repo URL
        self.base_url = (
            "https://raw.githubusercontent.com/Hapfel1/er-character-library/main/"
        )

        self.cache_file = self.cache_dir / "index_cache.json"
        self.index_url = self.base_url + "index.json"

        # Create SSL context for HTTPS requests
        self.ssl_context = self._create_ssl_context()

        # Perform cache maintenance on init
        self._cleanup_cache()

    def _create_ssl_context(self):
        """Create SSL context for HTTPS requests with proper certificate verification."""
        try:
            # Try to use certifi if available (recommended for cross-platform)
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            # Fallback to default context
            try:
                return ssl.create_default_context()
            except Exception:
                # Last resort: no verification (not recommended but better than crashing)
                return ssl._create_unverified_context()

    def fetch_index(self, force_refresh: bool = False) -> dict:
        """
        Fetch character index from remote or cache.

        Args:
            force_refresh: Force download even if cache exists

        Returns:
            Index data dict
        """
        # Check cache first if not forcing refresh
        if not force_refresh and self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    cached_data = json.load(f)

                # Check if cache is still valid (1 hour)
                cache_time = datetime.fromisoformat(cached_data.get("cached_at", ""))
                if datetime.now() - cache_time < timedelta(
                    hours=self.METADATA_EXPIRY_HOURS
                ):
                    print("[Character Manager] Using cached index")
                    return cached_data.get(
                        "data", {"version": "0.0.0", "characters": []}
                    )
            except Exception:
                pass

        # Download from remote
        try:
            # Add timestamp to bypass GitHub CDN cache
            import time

            cache_bust_url = f"{self.index_url}?ts={int(time.time())}"

            with urllib.request.urlopen(
                cache_bust_url, timeout=10, context=self.ssl_context
            ) as response:
                data = json.loads(response.read().decode())

            # Cache it with timestamp
            cache_data = {"cached_at": datetime.now().isoformat(), "data": data}
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

            return data

        except Exception as e:
            print(f"[Character Manager] Failed to fetch index: {e}")
            # Fall back to cache if available
            if self.cache_file.exists():
                with open(self.cache_file, encoding="utf-8") as f:
                    cached_data = json.load(f)
                return cached_data.get("data", {"version": "0.0.0", "characters": []})

            # No cache available
            return {"version": "0.0.0", "characters": []}

    def _resolve_url(self, url: str) -> str:
        """Resolve relative URLs against base_url; leave absolute URLs unchanged."""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return self.base_url + url

    def download_metadata(self, character_id: str, metadata_url: str) -> dict | None:
        """
        Download character metadata JSON (NOT the .erc file).

        Args:
            character_id: Character ID
            metadata_url: URL to metadata JSON

        Returns:
            Metadata dict or None if failed
        """
        try:
            print(f"[Character Manager] Downloading metadata for {character_id}")

            # Download metadata JSON
            full_url = self._resolve_url(metadata_url)
            with urllib.request.urlopen(
                full_url, timeout=10, context=self.ssl_context
            ) as response:
                metadata = json.loads(response.read().decode())

            # Cache metadata
            metadata_path = self.metadata_dir / f"{character_id}.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            print(f"[Character Manager] Cached metadata for {character_id}")
            return metadata

        except Exception as e:
            print(f"[Character Manager] Failed to download metadata: {e}")
            return None

    def get_cached_metadata(self, character_id: str) -> dict | None:
        """
        Get character metadata from local cache.

        Args:
            character_id: Character ID

        Returns:
            Metadata dict or None if not cached
        """
        metadata_path = self.metadata_dir / f"{character_id}.json"

        if metadata_path.exists():
            try:
                with open(metadata_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Character Manager] Failed to read cached metadata: {e}")

        return None

    def stream_character_download(
        self, character_id: str, erc_url: str, output_path: Path
    ) -> bool:
        """
        Stream download .erc file directly to output path (NO caching).

        Args:
            character_id: Character ID
            erc_url: URL to .erc file
            output_path: Where to save the .erc file

        Returns:
            True if successful
        """
        try:
            print(f"[Character Manager] Streaming download for {character_id}")

            full_url = self._resolve_url(erc_url)

            # Stream download to output path
            with urllib.request.urlopen(
                full_url, timeout=30, context=self.ssl_context
            ) as response:
                with open(output_path, "wb") as f:
                    # Stream in chunks to handle large files
                    chunk_size = 8192
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)

            print(f"[Character Manager] Downloaded {character_id} to {output_path}")
            return True

        except Exception as e:
            print(f"[Character Manager] Failed to download character: {e}")
            return False

    def download_thumbnail(self, character_id: str, thumbnail_url: str) -> Path | None:
        """
        Download and cache thumbnail image.

        Args:
            character_id: Character ID
            thumbnail_url: URL to thumbnail

        Returns:
            Path to cached thumbnail or None if failed
        """
        try:
            thumbnail_path = self.thumbnails_dir / f"{character_id}.jpg"

            # Return cached if exists
            if thumbnail_path.exists():
                return thumbnail_path

            print(f"[Character Manager] Downloading thumbnail for {character_id}")

            full_url = self._resolve_url(thumbnail_url)

            with urllib.request.urlopen(
                full_url, timeout=10, context=self.ssl_context
            ) as response:
                with open(thumbnail_path, "wb") as f:
                    f.write(response.read())

            print(f"[Character Manager] Cached thumbnail for {character_id}")
            return thumbnail_path

        except Exception as e:
            print(f"[Character Manager] Failed to download thumbnail: {e}")
            return None

    def download_screenshot(
        self, character_id: str, screenshot_url: str, suffix: str = ""
    ) -> Path | None:
        """
        Download full-size screenshot (face/body/preview).

        Args:
            character_id: Character ID
            screenshot_url: URL to screenshot
            suffix: File suffix (e.g., "_face", "_body", "_preview")

        Returns:
            Path to downloaded screenshot or None if failed
        """
        try:
            # Get file extension from URL
            ext = Path(screenshot_url).suffix or ".jpg"
            screenshot_path = self.cache_dir / f"{character_id}{suffix}{ext}"

            print(f"[Character Manager] Downloading screenshot {character_id}{suffix}")

            full_url = self._resolve_url(screenshot_url)

            with urllib.request.urlopen(
                full_url, timeout=15, context=self.ssl_context
            ) as response:
                with open(screenshot_path, "wb") as f:
                    f.write(response.read())

            # Update access time for LRU cleanup
            screenshot_path.touch()

            print(f"[Character Manager] Downloaded screenshot to {screenshot_path}")
            return screenshot_path

        except Exception as e:
            print(f"[Character Manager] Failed to download screenshot: {e}")
            return None

    def clear_cache(self):
        """Clear all cached data (metadata and thumbnails)."""
        print("[Character Manager] Clearing cache")

        if self.cache_dir.exists():
            import shutil

            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.thumbnails_dir.mkdir(exist_ok=True)
            self.metadata_dir.mkdir(exist_ok=True)

    def _cleanup_cache(self):
        """
        Clean up cache:
        1. Delete screenshots older than 7 days
        2. If cache exceeds MAX_CACHE_SIZE_MB, delete least recently accessed files
        Thumbnails and metadata are never deleted.
        """
        try:
            now = datetime.now()
            total_size = 0
            files_with_time = []

            # Scan cache directory for screenshots (not in thumbnails or metadata)
            for file_path in self.cache_dir.glob("*"):
                if file_path.is_file() and file_path.name not in ["index_cache.json"]:
                    size = file_path.stat().st_size
                    total_size += size

                    # Get last access time
                    try:
                        atime = datetime.fromtimestamp(file_path.stat().st_atime)
                    except Exception:
                        atime = datetime.fromtimestamp(file_path.stat().st_mtime)

                    files_with_time.append((file_path, atime, size))

                    # Delete if older than 7 days
                    if (now - atime).days > 7:
                        file_path.unlink()
                        total_size -= size
                        print(
                            f"[Character Cache] Deleted old screenshot: {file_path.name}"
                        )

            # Check total size
            total_mb = total_size / (1024 * 1024)
            if total_mb > self.MAX_CACHE_SIZE_MB:
                print(
                    f"[Character Cache] Cache size {total_mb:.1f}MB exceeds limit, cleaning up"
                )

                # Sort by access time (oldest first)
                files_with_time.sort(key=lambda x: x[1])

                # Delete oldest files until under limit
                for file_path, _, size in files_with_time:
                    if total_mb <= self.MAX_CACHE_SIZE_MB:
                        break

                    if file_path.exists():
                        file_path.unlink()
                        total_mb -= size / (1024 * 1024)
                        print(
                            f"[Character Cache] Deleted to reduce size: {file_path.name}"
                        )

        except Exception as e:
            print(f"[Character Cache] Cleanup failed: {e}")

    def get_cache_size(self) -> dict:
        """
        Get current cache size information.

        Returns:
            Dict with 'thumbnails_mb', 'metadata_mb', 'screenshots_mb', 'total_mb'
        """
        try:
            thumbnails_size = sum(
                f.stat().st_size for f in self.thumbnails_dir.glob("*") if f.is_file()
            )
            metadata_size = sum(
                f.stat().st_size for f in self.metadata_dir.glob("*") if f.is_file()
            )

            # Screenshots are in root cache dir
            screenshots_size = 0
            for f in self.cache_dir.glob("*"):
                if f.is_file() and f.name not in ["index_cache.json"]:
                    screenshots_size += f.stat().st_size

            return {
                "thumbnails_mb": thumbnails_size / (1024 * 1024),
                "metadata_mb": metadata_size / (1024 * 1024),
                "screenshots_mb": screenshots_size / (1024 * 1024),
                "total_mb": (thumbnails_size + metadata_size + screenshots_size)
                / (1024 * 1024),
            }
        except Exception:
            return {
                "thumbnails_mb": 0,
                "metadata_mb": 0,
                "screenshots_mb": 0,
                "total_mb": 0,
            }
