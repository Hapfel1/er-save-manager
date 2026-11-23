"""
Troubleshooter Addon Manager
Handles installation and updates of the standalone troubleshooter
"""

import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import requests


class TroubleshooterAddon:
    """Manages the FromSoftware Troubleshooter addon"""

    CURRENT_VERSION = "1.1"
    GITHUB_API_URL = "https://api.github.com/repos/Hapfel1/fromsoftware-troubleshooter/releases/latest"

    def __init__(self):
        """Initialize addon manager"""
        if os.name == "nt":  # Windows
            self.addon_dir = (
                Path(os.environ.get("APPDATA"))
                / "ER Save Manager"
                / "addons"
                / "troubleshooter"
            )
        else:  # Linux
            self.addon_dir = (
                Path.home()
                / ".local"
                / "share"
                / "er-save-manager"
                / "addons"
                / "troubleshooter"
            )

        self.version_file = self.addon_dir / "version.json"
        self.executable_name = (
            "FromSoftware Troubleshooter.exe"
            if os.name == "nt"
            else "FromSoftware-Troubleshooter"
        )
        self.executable_path = self.addon_dir / self.executable_name
        # Assets of the release found by check_for_updates, keyed by name
        self._release_assets: dict[str, str] = {}

    def is_installed(self) -> bool:
        """Check if troubleshooter is installed"""
        return self.executable_path.exists()

    def get_installed_version(self) -> str | None:
        """Get installed version"""
        if not self.version_file.exists():
            return None

        try:
            with open(self.version_file) as f:
                data = json.load(f)
                return data.get("version")
        except Exception:
            return None

    def check_for_updates(self) -> tuple[bool, str | None]:
        """
        Check if update is available

        Returns:
            (has_update, latest_version)
        """
        try:
            response = requests.get(self.GITHUB_API_URL, timeout=10)
            response.raise_for_status()

            data = response.json()
            latest_version = data["tag_name"].lstrip("v")
            self._release_assets = {
                asset["name"]: asset["browser_download_url"]
                for asset in data.get("assets", [])
            }

            installed = self.get_installed_version()
            if not installed:
                return True, latest_version

            # Simple version comparison (works for x.y format)
            def version_tuple(v):
                return tuple(map(int, v.split(".")))

            has_update = version_tuple(latest_version) > version_tuple(installed)
            return has_update, latest_version

        except Exception as e:
            print(f"Failed to check for updates: {e}")
            return False, None

    def get_download_url(self, version: str) -> str:
        """Download URL of this platform's asset for the given release.

        Uses the asset list of the release read by check_for_updates; asset
        names carry the platform (FromSoftware-Troubleshooter_<ver>_Linux.AppImage,
        or _Linux_<ver>.zip before 1.9.0). Falls back to the current naming
        scheme when the release was not read.
        """
        platform = "Windows" if os.name == "nt" else "Linux"
        for name, url in self._release_assets.items():
            if f"_{platform}" in name:
                return url
        suffix = "zip" if platform == "Windows" else "AppImage"
        return (
            "https://github.com/Hapfel1/fromsoftware-troubleshooter/releases/download/"
            f"v{version}/FromSoftware-Troubleshooter_{version}_{platform}.{suffix}"
        )

    def download_and_install(self, version: str, progress_callback=None) -> bool:
        """
        Download and install troubleshooter

        Args:
            version: Version to install
            progress_callback: Optional callback(message: str) for progress updates

        Returns:
            True if successful
        """
        try:
            download_url = self.get_download_url(version)

            if progress_callback:
                progress_callback("Downloading troubleshooter...")

            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            temp_dir = Path.home() / ".cache" / "er-save-manager"
            temp_dir.mkdir(parents=True, exist_ok=True)
            download_path = temp_dir / "troubleshooter.download"

            with open(download_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.addon_dir.mkdir(parents=True, exist_ok=True)

            if zipfile.is_zipfile(download_path):
                if progress_callback:
                    progress_callback("Extracting files...")
                extract_dir = temp_dir / "troubleshooter_extract"
                shutil.rmtree(extract_dir, ignore_errors=True)
                with zipfile.ZipFile(download_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)
                download_path.unlink()
                new_exe = self._find_executable(extract_dir)
                if new_exe is None:
                    shutil.rmtree(extract_dir, ignore_errors=True)
                    raise FileNotFoundError("No executable found in the download")
                os.replace(new_exe, self.executable_path)
                shutil.rmtree(extract_dir, ignore_errors=True)
            else:
                # Linux releases from 1.9.0 on are a bare AppImage
                os.replace(download_path, self.executable_path)

            if os.name != "nt":
                self.executable_path.chmod(0o755)

            with open(self.version_file, "w") as f:
                json.dump({"version": version}, f)

            if progress_callback:
                progress_callback("Installation complete.")

            return self.executable_path.exists()

        except Exception as e:
            print(f"Installation failed: {e}")
            if progress_callback:
                progress_callback(f"Installation failed: {e}")
            return False

    def _find_executable(self, root_dir: Path) -> Path | None:
        """The troubleshooter executable inside an extracted release zip."""
        for root, _dirs, files in os.walk(root_dir):
            for fname in files:
                if fname == self.executable_name or (
                    os.name != "nt" and fname.endswith(".AppImage")
                ):
                    return Path(root) / fname
        return None

    def launch(self, show_error=None) -> bool:
        """
        Launch the troubleshooter

        Args:
            show_error: Optional callback to show error messages to the user (e.g., a messagebox)

        Returns:
            True if launched successfully
        """
        if not self.is_installed():
            if show_error:
                show_error("Troubleshooter is not installed.")
            return False

        try:
            cmd = [str(self.executable_path)]
            print(f"Launching troubleshooter: {cmd}")
            if os.name == "nt":
                # Windows - launch without console window
                proc = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                # Linux - launch in background, without this AppImage's
                # bundled library paths leaking into the child process
                from er_save_manager.ui.utils import _get_subprocess_env

                proc = subprocess.Popen(
                    cmd,
                    env=_get_subprocess_env(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            # Detect an executable that exits immediately after launch
            import time

            time.sleep(0.5)
            if proc.poll() is not None:
                msg = "Troubleshooter process exited immediately. Check if the executable is valid."
                print(msg)
                if show_error:
                    show_error(msg)
                return False
            return True
        except Exception as e:
            msg = f"Failed to launch troubleshooter: {e}"
            print(msg)
            if show_error:
                show_error(msg)
            return False
