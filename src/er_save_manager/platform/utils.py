"""Platform-specific utilities for cross-platform support."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.games.game_profiles import GameProfile


class PlatformUtils:
    """Utilities for platform-specific operations."""

    @staticmethod
    def get_platform() -> str:
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
        return PlatformUtils.get_platform() == "windows"

    @staticmethod
    def is_linux() -> bool:
        return PlatformUtils.get_platform() == "linux"

    @staticmethod
    def is_macos() -> bool:
        return PlatformUtils.get_platform() == "darwin"

    @staticmethod
    def is_game_running() -> bool:
        """Check if Elden Ring is running."""
        try:
            if PlatformUtils.is_windows():
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq eldenring.exe", "/NH"],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                return "eldenring.exe" in result.stdout.lower()
            elif PlatformUtils.is_linux():
                result = subprocess.run(
                    ["pgrep", "-f", "eldenring.exe"],
                    capture_output=True,
                    text=True,
                )
                return result.returncode == 0
        except Exception:
            pass
        return False

    @staticmethod
    def kill_game_process() -> bool:
        """Force kill Elden Ring process."""
        try:
            if PlatformUtils.is_windows():
                subprocess.run(
                    ["taskkill", "/F", "/IM", "eldenring.exe"],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    check=True,
                )
                return True
            elif PlatformUtils.is_linux():
                subprocess.run(
                    ["pkill", "-9", "-f", "eldenring.exe"],
                    check=True,
                )
                return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Game-aware methods.
    # All accept an optional profile; default to ER behaviour when None.
    # ------------------------------------------------------------------

    @staticmethod
    def _profile_params(profile: GameProfile | None) -> tuple[str, str, str, str]:
        """
        Return (appdata_subdir, save_glob, app_id, documents_subdir).

        save_glob is a glob pattern like "ER*.*" that matches all save files
        for the game (including alternate extensions like .co2).
        documents_subdir is non-empty only for DSR-style games.
        """
        if profile is None:
            # ER defaults - identical to original behaviour
            return ("EldenRing", "ER*.*", "1245620", "")
        documents_subdir = getattr(profile, "documents_subdir", "")
        save_glob = getattr(profile, "save_glob", profile.save_filename)
        return (
            profile.appdata_subdir,
            save_glob,
            str(profile.steam_app_id),
            documents_subdir,
        )

    @staticmethod
    def _roaming_rel(appdata_subdir: str, documents_subdir: str) -> str:
        """
        Relative path from drive_c/users/steamuser/ to the game's save directory
        inside a Proton prefix.
        """
        if documents_subdir:
            return "Documents/" + documents_subdir.replace("\\", "/")
        return f"AppData/Roaming/{appdata_subdir}"

    @staticmethod
    def get_default_save_locations(profile: GameProfile | None = None) -> list[Path]:
        """Get platform-specific directories containing saves for the given game."""
        appdata_subdir, _glob, _app_id, documents_subdir = (
            PlatformUtils._profile_params(profile)
        )
        platform_name = PlatformUtils.get_platform()

        if platform_name == "windows":
            if documents_subdir:
                base = Path.home() / "Documents"
                for part in documents_subdir.replace("\\", "/").split("/"):
                    base = base / part
            else:
                base = Path.home() / "AppData" / "Roaming" / appdata_subdir
            return [base] if base.exists() else []

        elif platform_name == "linux":
            locations = []
            local_steam = (
                Path.home() / ".local" / "share" / "Steam" / "steamapps" / "compatdata"
            )
            if local_steam.exists():
                locations.append(local_steam)
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
            if documents_subdir:
                base = Path.home() / "Documents"
                for part in documents_subdir.replace("\\", "/").split("/"):
                    base = base / part
            else:
                base = Path.home() / "Library" / "Application Support" / appdata_subdir
            return [base] if base.exists() else []

        return []

    @staticmethod
    def find_all_save_files(profile: GameProfile | None = None) -> list[Path]:
        """
        Find all save files for the given game on the system.
        When profile is None, finds ER saves (original behaviour).

        Uses save_glob (e.g. "ER*.*") to match all save file variants
        (different slot numbers, alternate extensions like .co2).
        """
        appdata_subdir, save_glob, _app_id, documents_subdir = (
            PlatformUtils._profile_params(profile)
        )
        found_saves: list[Path] = []
        platform_name = PlatformUtils.get_platform()

        if platform_name == "windows":
            if documents_subdir:
                base = Path.home() / "Documents"
                for part in documents_subdir.replace("\\", "/").split("/"):
                    base = base / part
            else:
                base = Path.home() / "AppData" / "Roaming" / appdata_subdir

            if base.exists():
                # Save files are in SteamID subfolders
                found_saves.extend(base.glob(f"*/{save_glob}"))
                # Also check direct files (edge case / no SteamID subfolder)
                found_saves.extend(base.glob(save_glob))

        elif platform_name == "linux":
            roaming_rel = PlatformUtils._roaming_rel(appdata_subdir, documents_subdir)
            # Full path from a compatdata entry to the game's save directory,
            # relative to the compatdata entry itself.
            user_rel = f"pfx/drive_c/users/steamuser/{roaming_rel}"

            compat_bases = [
                Path.home() / ".local" / "share" / "Steam" / "steamapps" / "compatdata",
                Path.home()
                / ".var"
                / "app"
                / "com.valvesoftware.Steam"
                / ".local"
                / "share"
                / "Steam"
                / "steamapps"
                / "compatdata",
            ]
            # Also check custom Steam library folders
            for lib in PlatformUtils.get_steam_library_folders():
                compat_bases.append(lib / "steamapps" / "compatdata")

            seen: set[Path] = set()
            for compat_base in compat_bases:
                if not compat_base.exists():
                    continue
                resolved = compat_base.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)

                try:
                    # Two-step search: first expand the compatdata/* wildcard,
                    # then look for the game's roaming path inside each entry.
                    # This mirrors the original approach and correctly handles
                    # directory names with spaces (e.g. "DARK SOULS REMASTERED").
                    parts = (compat_base / "*").parts
                    wildcard_idx = next(i for i, p in enumerate(parts) if "*" in p)
                    base_path = Path(*parts[:wildcard_idx])
                    rest = "/".join(parts[wildcard_idx:]) + "/" + user_rel

                    if base_path.exists():
                        for game_dir in base_path.glob(rest):
                            if game_dir.is_dir():
                                # Save files are in SteamID subfolders
                                found_saves.extend(game_dir.glob(f"*/{save_glob}"))
                                # Also check direct files (edge case)
                                found_saves.extend(game_dir.glob(save_glob))
                except (StopIteration, OSError):
                    continue

        elif platform_name == "darwin":
            if documents_subdir:
                base = Path.home() / "Documents"
                for part in documents_subdir.replace("\\", "/").split("/"):
                    base = base / part
            else:
                base = Path.home() / "Library" / "Application Support" / appdata_subdir

            if base.exists():
                found_saves.extend(base.glob(f"*/{save_glob}"))
                found_saves.extend(base.glob(save_glob))

        # Remove duplicates and backup files
        unique = list({p.resolve(): p for p in found_saves}.values())
        return [
            p
            for p in unique
            if not any(p.name.endswith(ext) for ext in (".backup", ".backups", ".bak"))
        ]

    @staticmethod
    def get_default_compatdata_id(profile: GameProfile | None = None) -> str:
        """Steam App ID used as the compatdata folder name. Defaults to ER."""
        if profile is not None:
            return str(profile.steam_app_id)
        return "1245620"

    @staticmethod
    def get_steam_launch_option_hint(profile: GameProfile | None = None) -> str:
        """STEAM_COMPAT_DATA_PATH launch option hint for the given game."""
        if not PlatformUtils.is_linux():
            return ""
        compatdata_id = PlatformUtils.get_default_compatdata_id(profile)
        if PlatformUtils.is_flatpak_steam():
            base = "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps"
        else:
            base = "$HOME/.local/share/Steam/steamapps"
        return (
            f"STEAM_COMPAT_LIBRARY_PATHS={base}/ "
            f"STEAM_COMPAT_DATA_PATH={base}/compatdata/{compatdata_id}/ %command%"
        )

    @staticmethod
    def is_save_in_default_location(
        save_path: Path,
        profile: GameProfile | None = None,
    ) -> bool:
        """
        Check whether a save is in the expected compatdata folder for the game.
        On Windows always returns True.
        """
        if PlatformUtils.is_windows():
            return True

        if PlatformUtils.is_linux():
            path_str = str(save_path)
            if "/compatdata/" not in path_str:
                return True
            compatdata_id = PlatformUtils.get_default_compatdata_id(profile)
            return compatdata_id in path_str

        return True

    @staticmethod
    def get_default_save_location(profile: GameProfile | None = None) -> Path | None:
        """Canonical save directory (contains the SteamID subfolder)."""
        appdata_subdir, _glob, app_id, documents_subdir = PlatformUtils._profile_params(
            profile
        )

        if PlatformUtils.is_windows():
            if documents_subdir:
                base = Path.home() / "Documents"
                for part in documents_subdir.replace("\\", "/").split("/"):
                    base = base / part
                return base
            return Path.home() / "AppData" / "Roaming" / appdata_subdir

        elif PlatformUtils.is_linux():
            if PlatformUtils.is_flatpak_steam():
                steam_base = (
                    Path.home()
                    / ".var"
                    / "app"
                    / "com.valvesoftware.Steam"
                    / ".local"
                    / "share"
                    / "Steam"
                )
            else:
                steam_base = Path.home() / ".local" / "share" / "Steam"

            prefix = (
                steam_base
                / "steamapps"
                / "compatdata"
                / app_id
                / "pfx"
                / "drive_c"
                / "users"
                / "steamuser"
            )

            if documents_subdir:
                result = prefix / "Documents"
                for part in documents_subdir.replace("\\", "/").split("/"):
                    result = result / part
                return result
            return prefix / "AppData" / "Roaming" / appdata_subdir

        return None

    @staticmethod
    def is_flatpak_steam() -> bool:
        """Check if Steam is running via Flatpak."""
        if not PlatformUtils.is_linux():
            return False
        return (
            Path.home()
            / ".var"
            / "app"
            / "com.valvesoftware.Steam"
            / ".local"
            / "share"
            / "Steam"
        ).exists()

    @staticmethod
    def get_steam_install_path() -> Path | None:
        """
        Return the Steam installation directory.

        On Windows: reads HKCU\\Software\\Valve\\Steam -> SteamPath via winreg.
        A plain registry read does not trigger Windows Defender heuristics.
        On Linux: checks the standard and Flatpak Steam locations.
        Returns None when Steam cannot be located.
        """
        platform_name = PlatformUtils.get_platform()

        if platform_name == "windows":
            try:
                import winreg

                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
                steam_path = Path(winreg.QueryValueEx(key, "SteamPath")[0])
                winreg.CloseKey(key)
                if steam_path.exists():
                    return steam_path
            except Exception:
                pass
            # Fallback: common default locations (no shell, no subprocess)
            for candidate in (
                Path("C:/Program Files (x86)/Steam"),
                Path("C:/Program Files/Steam"),
            ):
                if candidate.exists():
                    return candidate
            return None

        if platform_name == "linux":
            for candidate in (
                Path.home() / ".local" / "share" / "Steam",
                Path.home()
                / ".var"
                / "app"
                / "com.valvesoftware.Steam"
                / ".local"
                / "share"
                / "Steam",
            ):
                if candidate.exists():
                    return candidate
            return None

        return None

    @staticmethod
    def get_loginusers_steam_accounts() -> list[tuple[int, str]]:
        """
        Parse Steam's loginusers.vdf and return logged-in accounts.

        Returns a list of (steam64_id, persona_name) tuples, ordered by
        most recently used first (mostrecent flag).

        Scans all known Steam base directories so the file is found even
        when get_steam_install_path() resolves a symlink to a path that
        does not contain the config directory.
        """
        import re

        platform_name = PlatformUtils.get_platform()

        if platform_name == "windows":
            # Registry lookup is reliable on Windows.
            steam_dir = PlatformUtils.get_steam_install_path()
            vdf_candidates = (
                [steam_dir / "config" / "loginusers.vdf"] if steam_dir else []
            )
        else:
            # On Linux the resolved install path may not contain config/.
            # Check all known base paths explicitly.
            bases: list[Path] = [
                Path.home() / ".local" / "share" / "Steam",
                Path.home()
                / ".var"
                / "app"
                / "com.valvesoftware.Steam"
                / ".local"
                / "share"
                / "Steam",
            ]
            resolved = PlatformUtils.get_steam_install_path()
            if resolved is not None and resolved not in bases:
                bases.append(resolved)
            vdf_candidates = [b / "config" / "loginusers.vdf" for b in bases]

        vdf_content: str | None = None
        for vdf_path in vdf_candidates:
            if not vdf_path.exists():
                continue
            try:
                vdf_content = vdf_path.read_text(encoding="utf-8", errors="replace")
                break
            except OSError:
                continue

        if vdf_content is None:
            return []

        content = vdf_content
        STEAM64_BASE = 0x0110000100000000
        STEAM64_MAX = 0x01100001FFFFFFFF

        # Split into per-account blocks by finding each top-level SteamID key.
        block_pattern = re.compile(
            r'"(\d{17})"\s*\{([^}]*)\}',
            re.DOTALL,
        )
        kv_pattern = re.compile(r'"(\w+)"\s+"([^"]*)"')

        accounts: list[tuple[int, str, int]] = []  # (steamid, name, most_recent)
        for m in block_pattern.finditer(content):
            try:
                steamid = int(m.group(1))
            except ValueError:
                continue
            if not (STEAM64_BASE <= steamid <= STEAM64_MAX):
                continue

            fields: dict[str, str] = {}
            for kv in kv_pattern.finditer(m.group(2)):
                fields[kv.group(1).lower()] = kv.group(2)

            persona = (
                fields.get("personaname") or fields.get("accountname") or str(steamid)
            )
            most_recent = int(fields.get("mostrecent", "0"))
            accounts.append((steamid, persona, most_recent))

        # Most-recently-used account first.
        accounts.sort(key=lambda x: x[2], reverse=True)
        return [(sid, name) for sid, name, _ in accounts]

    @staticmethod
    def get_steam_library_folders() -> list[Path]:
        """Parse Steam's libraryfolders.vdf to find custom library locations."""
        import re

        libraries: list[Path] = []
        platform_name = PlatformUtils.get_platform()

        if platform_name == "windows":
            candidates = [
                Path.home()
                / "Program Files (x86)"
                / "Steam"
                / "config"
                / "libraryfolders.vdf",
                Path.home()
                / "AppData"
                / "Local"
                / "Steam"
                / "config"
                / "libraryfolders.vdf",
            ]
        elif platform_name == "linux":
            candidates = [
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
        else:
            return libraries

        for config_path in candidates:
            if not config_path.exists():
                continue
            try:
                content = config_path.read_text(encoding="utf-8")
                for path_str in re.findall(r'"path"\s+"([^"]+)"', content):
                    lib_path = Path(path_str)
                    if lib_path.exists():
                        libraries.append(lib_path)
            except Exception:
                continue
            break

        return libraries
