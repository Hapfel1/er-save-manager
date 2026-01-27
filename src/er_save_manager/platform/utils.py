"""Platform-specific utilities for cross-platform support."""

import platform
from pathlib import Path


class PlatformUtils:
    """Utilities for platform-specific operations."""

    @staticmethod
    def get_platform() -> str:
        """
        Get current platform.

        Returns:
            'windows', 'linux', or 'darwin' (macOS)
        """
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "linux":
            return "linux"
        elif system == "darwin":
            return "darwin"
        return system

    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows."""
        return PlatformUtils.get_platform() == "windows"

    @staticmethod
    def is_linux() -> bool:
        """Check if running on Linux."""
        return PlatformUtils.get_platform() == "linux"

    @staticmethod
    def is_macos() -> bool:
        """Check if running on macOS."""
        return PlatformUtils.get_platform() == "darwin"

    @staticmethod
    def get_default_save_locations() -> list[Path]:
        """
        Get platform-specific default save locations.

        Note: Save files are typically in SteamID subfolders:
        - Windows: AppData/Roaming/EldenRing/[SteamID]/
        - Linux: .../EldenRing/[SteamID]/
        - macOS: .../EldenRing/[SteamID]/

        Returns:
            List of Path objects to check for save files
        """
        platform_name = PlatformUtils.get_platform()

        if platform_name == "windows":
            # Windows: AppData\Roaming\EldenRing
            appdata = Path.home() / "AppData" / "Roaming" / "EldenRing"
            return [appdata] if appdata.exists() else []

        elif platform_name == "linux":
            # Linux: Multiple possible locations due to Proton
            locations = []

            # Standard Steam location (~/.steam/steam is just a symlink to this)
            local_steam = (
                Path.home() / ".local" / "share" / "Steam" / "steamapps" / "compatdata"
            )
            if local_steam.exists():
                locations.append(local_steam)

            # Flatpak Steam
            flatpak_steam = (
                Path.home()
                / ".var"
                / "app"
                / "com.valvesoftware.Steam"
                / ".local"
                / "share"
                / "Steam"
                / "steamapps"
                / "compatdata"
            )
            if flatpak_steam.exists():
                locations.append(flatpak_steam)

            return locations

        elif platform_name == "darwin":
            # macOS: Similar to Windows but in different location
            # ~/Library/Application Support/EldenRing
            app_support = Path.home() / "Library" / "Application Support" / "EldenRing"
            return [app_support] if app_support.exists() else []

        return []

    @staticmethod
    def find_all_save_files() -> list[Path]:
        """
        Find all Elden Ring save files on the system.

        Returns:
            List of Path objects to found save files (ER0000-ER0009 with any extension)
        """
        found_saves = []
        platform_name = PlatformUtils.get_platform()

        if platform_name == "windows":
            # Windows: AppData/Roaming/EldenRing/[SteamID]/ER*.*
            appdata = Path.home() / "AppData" / "Roaming" / "EldenRing"

            if appdata.exists():
                # Save files are in SteamID subfolders: EldenRing/[SteamID]/ER*.*
                files = list(appdata.glob("*/ER*.*"))
                found_saves.extend(files)
        elif platform_name == "linux":
            # Linux: Search all compatdata folders
            # Note: ~/.steam/steam is just a symlink to ~/.local/share/Steam, no need to check both
            search_patterns = [
                # Standard Steam location
                Path.home()
                / ".local"
                / "share"
                / "Steam"
                / "steamapps"
                / "compatdata"
                / "*"
                / "pfx"
                / "drive_c"
                / "users"
                / "steamuser"
                / "AppData"
                / "Roaming"
                / "EldenRing",
                # Flatpak Steam
                Path.home()
                / ".var"
                / "app"
                / "com.valvesoftware.Steam"
                / ".local"
                / "share"
                / "Steam"
                / "steamapps"
                / "compatdata"
                / "*"
                / "pfx"
                / "drive_c"
                / "users"
                / "steamuser"
                / "AppData"
                / "Roaming"
                / "EldenRing",
            ]

            # Search each pattern
            for pattern in search_patterns:
                parent = pattern.parent
                if not parent.exists():
                    continue

                # Get the wildcard part
                pattern_str = str(pattern)
                if "*" in pattern_str:
                    # Use glob to expand wildcards
                    try:
                        # Get base path before wildcard
                        parts = pattern.parts
                        wildcard_idx = next(i for i, p in enumerate(parts) if "*" in p)
                        base = Path(*parts[:wildcard_idx])
                        rest = "/".join(parts[wildcard_idx:])

                        if base.exists():
                            for match in base.glob(rest):
                                if match.is_dir():
                                    # Save files are in SteamID subfolders: EldenRing/[SteamID]/ER*.*
                                    found_saves.extend(match.glob("*/ER*.*"))
                                    # Also check if files are directly in EldenRing folder (edge case)
                                    found_saves.extend(match.glob("ER*.*"))
                    except (StopIteration, OSError):
                        continue

            # Also check custom Steam library folders
            custom_saves = PlatformUtils._find_in_custom_steam_libraries()
            found_saves.extend(custom_saves)

        elif platform_name == "darwin":
            # macOS: Library/Application Support/EldenRing/[SteamID]/ER*.*
            app_support = Path.home() / "Library" / "Application Support" / "EldenRing"
            if app_support.exists():
                # Save files are in SteamID subfolders
                found_saves.extend(app_support.glob("*/ER*.*"))
                # Covered by ER0000.* above

        # Remove duplicates
        unique_saves = list(set(found_saves))

        # Filter out backup files (.backup, .backups, .bak extensions)
        filtered_saves = [
            save
            for save in unique_saves
            if not any(
                save.name.endswith(ext) for ext in [".backup", ".backups", ".bak"]
            )
        ]

        return filtered_saves

    @staticmethod
    def _find_in_custom_steam_libraries() -> list[Path]:
        """Find saves in custom Steam library folders."""
        found = []
        steam_libraries = PlatformUtils.get_steam_library_folders()

        for library in steam_libraries:
            compat_path = library / "steamapps" / "compatdata"
            if not compat_path.exists():
                continue

            # Search all compatdata folders in this library
            (
                compat_path
                / "*"
                / "pfx"
                / "drive_c"
                / "users"
                / "steamuser"
                / "AppData"
                / "Roaming"
                / "EldenRing"
            )

            try:
                for match in compat_path.glob(
                    "*/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing"
                ):
                    if match.is_dir():
                        # Save files are in SteamID subfolders
                        found.extend(match.glob("*/ER*.*"))
                        # Also check direct files (edge case)
                        found.extend(match.glob("ER*.*"))
                        # Covered by ER0000.* above
            except OSError:
                continue

        return found

    @staticmethod
    def get_steam_library_folders() -> list[Path]:
        """
        Parse Steam's libraryfolders.vdf to find custom library locations.

        Returns:
            List of Path objects to Steam library folders
        """
        libraries = []
        platform_name = PlatformUtils.get_platform()

        if platform_name == "windows":
            # Windows Steam config
            config_path = (
                Path.home()
                / "Program Files (x86)"
                / "Steam"
                / "config"
                / "libraryfolders.vdf"
            )
            # Also check AppData location
            if not config_path.exists():
                config_path = (
                    Path.home()
                    / "AppData"
                    / "Local"
                    / "Steam"
                    / "config"
                    / "libraryfolders.vdf"
                )

            if config_path.exists():
                try:
                    with open(config_path, encoding="utf-8") as f:
                        content = f.read()

                    import re

                    paths = re.findall(r'"path"\s+"([^"]+)"', content)
                    for path_str in paths:
                        lib_path = Path(path_str)
                        if lib_path.exists():
                            libraries.append(lib_path)
                except Exception:
                    pass

        elif platform_name == "linux":
            # Linux Steam config locations (~/.steam/steam is just a symlink, no need to check both)
            config_paths = [
                Path.home()
                / ".local"
                / "share"
                / "Steam"
                / "config"
                / "libraryfolders.vdf",
                Path.home()
                / ".var"
                / "app"
                / "com.valvesoftware.Steam"
                / ".local"
                / "share"
                / "Steam"
                / "config"
                / "libraryfolders.vdf",
            ]

            for config_path in config_paths:
                if config_path.exists():
                    try:
                        with open(config_path, encoding="utf-8") as f:
                            content = f.read()

                        # Simple VDF parsing - look for "path" entries
                        import re

                        paths = re.findall(r'"path"\s+"([^"]+)"', content)
                        for path_str in paths:
                            lib_path = Path(path_str)
                            if lib_path.exists():
                                libraries.append(lib_path)
                    except Exception:
                        continue
                    break  # Found valid config, stop searching

        return libraries

    @staticmethod
    def is_flatpak_steam() -> bool:
        """Check if Steam is running via Flatpak."""
        if not PlatformUtils.is_linux():
            return False

        flatpak_path = (
            Path.home()
            / ".var"
            / "app"
            / "com.valvesoftware.Steam"
            / ".local"
            / "share"
            / "Steam"
        )
        return flatpak_path.exists()

    @staticmethod
    def get_default_compatdata_id() -> str:
        """
        Get the default Steam compatdata ID for Elden Ring.

        Returns:
            '1245620' (Elden Ring's Steam app ID)
        """
        return "1245620"

    @staticmethod
    def get_steam_launch_option_hint() -> str:
        """
        Get platform-specific launch option hint for Steam.

        Returns:
            Launch option string to show user
        """
        if PlatformUtils.is_linux():
            compatdata_id = PlatformUtils.get_default_compatdata_id()
            if PlatformUtils.is_flatpak_steam():
                return f"STEAM_COMPAT_LIBRARY_PATHS=$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/ STEAM_COMPAT_DATA_PATH=$STEAM_COMPAT_LIBRARY_PATHS/compatdata/{compatdata_id}/ %command%"
            else:
                return f"STEAM_COMPAT_LIBRARY_PATHS=$HOME/.local/share/Steam/steamapps/ STEAM_COMPAT_DATA_PATH=$STEAM_COMPAT_LIBRARY_PATHS/compatdata/{compatdata_id}/ %command%"
        return ""

    @staticmethod
    def is_save_in_default_location(save_path: Path) -> bool:
        """
        Check if save file is in the recommended default location.

        Args:
            save_path: Path to save file

        Returns:
            True if in default/recommended location
        """
        if PlatformUtils.is_windows():
            # Windows: AppData is always correct
            return True

        elif PlatformUtils.is_linux():
            # Linux: Only check if file is in compatdata
            path_str = str(save_path)

            # If not in compatdata at all, consider it fine
            if "/compatdata/" not in path_str:
                return True

            # If in compatdata, check if it's the default Elden Ring ID
            compatdata_id = PlatformUtils.get_default_compatdata_id()
            return compatdata_id in path_str

        return True

    @staticmethod
    def get_default_save_location() -> Path | None:
        """
        Get the recommended default save location for moving files.

        Returns:
            Path to default location, or None if not applicable
        """
        if PlatformUtils.is_windows():
            return Path.home() / "AppData" / "Roaming" / "EldenRing"

        elif PlatformUtils.is_linux():
            compatdata_id = PlatformUtils.get_default_compatdata_id()

            if PlatformUtils.is_flatpak_steam():
                base = (
                    Path.home()
                    / ".var"
                    / "app"
                    / "com.valvesoftware.Steam"
                    / ".local"
                    / "share"
                    / "Steam"
                )
            else:
                # Standard Steam location (~/.steam/steam is just a symlink to this)
                base = Path.home() / ".local" / "share" / "Steam"

            return (
                base
                / "steamapps"
                / "compatdata"
                / compatdata_id
                / "pfx"
                / "drive_c"
                / "users"
                / "steamuser"
                / "AppData"
                / "Roaming"
                / "EldenRing"
            )

        return None
