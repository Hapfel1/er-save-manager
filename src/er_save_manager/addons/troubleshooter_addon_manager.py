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
        # Get addon installation directory
        if os.name == "nt":  # Windows
            self.addon_dir = (
                Path(os.environ.get("APPDATA"))
                / "ERSaveManager"
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
            "FromSoftware-Troubleshooter.exe"
            if os.name == "nt"
            else "FromSoftware-Troubleshooter"
        )
        self.executable_path = self.addon_dir / self.executable_name

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
        """Get download URL for specific version"""
        platform = "Windows" if os.name == "nt" else "Linux"
        return f"https://github.com/Hapfel1/fromsoftware-troubleshooter/releases/download/{version}/FromSoftware-Troubleshooter_{platform}_{version}.zip"

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

            # Download
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            # Save to temp file
            temp_dir = Path.home() / ".cache" / "er-save-manager"
            temp_dir.mkdir(parents=True, exist_ok=True)
            zip_path = temp_dir / "troubleshooter.zip"

            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if progress_callback:
                progress_callback("Extracting files...")

            # Extract
            self.addon_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(self.addon_dir)

            # After extraction, ensure the executable is at the expected location
            if not self.executable_path.exists():
                # On Linux, the file may be named *.AppImage, so find and rename it
                if os.name != "nt":
                    for root, _dirs, files in os.walk(self.addon_dir):
                        for fname in files:
                            if fname.endswith(".AppImage"):
                                found_path = Path(root) / fname
                                found_path.rename(self.executable_path)
                                break
                        if self.executable_path.exists():
                            break
                else:
                    # On Windows, search for the expected exe name
                    for root, _dirs, files in os.walk(self.addon_dir):
                        if self.executable_name in files:
                            found_path = Path(root) / self.executable_name
                            found_path.rename(self.executable_path)
                            break

            # Make executable on Linux
            if os.name != "nt" and self.executable_path.exists():
                self.executable_path.chmod(0o755)

            # Save version info
            with open(self.version_file, "w") as f:
                json.dump({"version": version}, f)

            # Cleanup
            zip_path.unlink()

            if progress_callback:
                progress_callback("Installation complete!")

            return self.executable_path.exists()

        except Exception as e:
            print(f"Installation failed: {e}")
            if progress_callback:
                progress_callback(f"Installation failed: {e}")
            return False

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
                # Linux - launch in background
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            # Optionally, check if process starts and does not exit immediately
            import time

            time.sleep(0.5)
            if proc.poll() is not None:
                # Process exited
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

    def uninstall(self) -> bool:
        """Uninstall the troubleshooter"""
        try:
            if self.addon_dir.exists():
                shutil.rmtree(self.addon_dir)
            return True
        except Exception as e:
            print(f"Failed to uninstall: {e}")
            return False
