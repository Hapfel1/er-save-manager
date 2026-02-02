"""Version checking and update notification."""

import urllib.request

from packaging.version import Version


class VersionChecker:
    """Check for application updates from GitHub releases."""

    GITHUB_API_URL = (
        "https://api.github.com/repos/Hapfel1/er-save-manager/releases/latest"
    )
    GITHUB_RELEASES_URL = "https://github.com/Hapfel1/er-save-manager/releases"

    def __init__(self, current_version: str):
        """
        Initialize version checker.

        Args:
            current_version: Current application version (e.g., "0.7.4")
        """
        self.current_version = current_version

    def check_for_updates(self) -> tuple[bool, str | None, str | None]:
        """
        Check if a newer version is available on GitHub.

        Returns:
            Tuple of (has_update, latest_version, download_url)
            - has_update: True if newer version available
            - latest_version: Version string of latest release (e.g., "0.8.0")
            - download_url: URL to the releases page
        """
        try:
            # Fetch latest release info from GitHub API
            req = urllib.request.Request(
                self.GITHUB_API_URL,
                headers={"Accept": "application/vnd.github.v3+json"},
            )

            with urllib.request.urlopen(req, timeout=5) as response:
                import json

                data = json.loads(response.read().decode("utf-8"))

            # Extract version from tag_name (e.g., "v0.8.0" -> "0.8.0")
            tag_name = data.get("tag_name", "")
            latest_version = tag_name.lstrip("v")

            if not latest_version:
                return False, None, None

            # Compare versions
            try:
                current = Version(self.current_version)
                latest = Version(latest_version)

                if latest > current:
                    return (
                        True,
                        latest_version,
                        data.get("html_url", self.GITHUB_RELEASES_URL),
                    )
                else:
                    return False, latest_version, None

            except Exception:
                # If version comparison fails, assume no update
                return False, None, None

        except Exception:
            # Network error or API failure - silently fail
            return False, None, None
