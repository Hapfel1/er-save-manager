"""
Game profiles for all supported FromSoftware games.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GameProfile:
    """Describes a FromSoftware game for backup and SteamID operations."""

    name: str
    key: str
    steam_app_id: int

    # Exact primary save filename (used for SteamID patching, backup display, etc.)
    save_filename: str

    # Glob pattern for finding save files (e.g. "ER*.*" catches ER0000.sl2 and .co2).
    # Should match the filename stem prefix + wildcard extension.
    save_glob: str

    # Folder under %APPDATA%\Roaming (Windows) / AppData/Roaming (Linux Proton).
    # Set to "" if the game uses documents_subdir instead (e.g. DSR).
    appdata_subdir: str

    # Relative path under Documents for games that don't use AppData (e.g. DSR).
    # Use forward slashes. Leave "" for all games that use appdata_subdir.
    documents_subdir: str = ""

    supports_steamid_patch: bool = True
    steamid_patch_note: str = ""
    has_steamid_subfolder: bool = True
    # Format of the SteamID subfolder name:
    #   "steam64_dec" - 17 decimal digits, equals Steam64 (default, most games)
    #   "steam64_hex" - 16 lowercase hex chars, equals Steam64 (DS2)
    #   "steam32_dec" - 1-10 decimal digits, equals Steam32; add 76561197960265728 for Steam64 (DSR)
    steamid_folder_format: str = "steam64_dec"
    extensions: list[str] = field(default_factory=lambda: [".sl2"])


GAME_PROFILES: list[GameProfile] = [
    GameProfile(
        name="Elden Ring",
        key="elden_ring",
        steam_app_id=1245620,
        save_filename="ER0000.sl2",
        save_glob="ER*.*",
        appdata_subdir="EldenRing",
        extensions=[".sl2", ".co2"],
    ),
    GameProfile(
        name="Elden Ring Nightreign",
        key="nightreign",
        steam_app_id=2622380,
        save_filename="NR0000.sl2",
        save_glob="NR*.*",
        appdata_subdir="Nightreign",
        extensions=[".sl2", ".co2"],
    ),
    GameProfile(
        name="Armored Core VI",
        key="armored_core_6",
        steam_app_id=1888160,
        save_filename="AC60000.sl2",
        save_glob="AC6*.*",
        appdata_subdir="ArmoredCore6",
    ),
    GameProfile(
        name="Dark Souls III",
        key="dark_souls_3",
        steam_app_id=374320,
        save_filename="DS30000.sl2",
        save_glob="DS3*.*",
        appdata_subdir="DarkSoulsIII",
    ),
    GameProfile(
        name="Dark Souls II: Scholar of the First Sin",
        key="dark_souls_2",
        steam_app_id=335300,
        save_filename="DS2SOFS0000.sl2",
        save_glob="DS2*.*",
        appdata_subdir="DarkSoulsII",
        steamid_folder_format="steam64_hex",
    ),
    GameProfile(
        # DSR saves to Documents\NBGI\DARK SOULS REMASTERED\, not AppData.
        # The SteamID subfolder is named with Steam32 decimal, not Steam64.
        name="Dark Souls: Remastered",
        key="dark_souls_remastered",
        steam_app_id=570940,
        save_filename="DRAKS0005.sl2",
        save_glob="DRAKS*.*",
        appdata_subdir="",
        documents_subdir="NBGI/DARK SOULS REMASTERED",
        steamid_folder_format="steam32_dec",
    ),
    GameProfile(
        name="Sekiro: Shadows Die Twice",
        key="sekiro",
        steam_app_id=814380,
        save_filename="S0000.sl2",
        save_glob="S*.*",
        appdata_subdir="Sekiro",
    ),
]

PROFILES_BY_KEY: dict[str, GameProfile] = {p.key: p for p in GAME_PROFILES}


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _is_linux() -> bool:
    return platform.system() == "Linux"


def find_save_paths(profile: GameProfile) -> list[Path]:
    """Return all save file paths found for the given game profile."""
    if _is_windows():
        return _find_windows(profile)
    elif _is_linux():
        return _find_linux(profile)
    return []


def _save_base_windows(profile: GameProfile) -> Path | None:
    """Return the Windows base directory that contains [steamid]/savefile."""
    if profile.documents_subdir:
        base = Path.home() / "Documents"
        for part in profile.documents_subdir.split("/"):
            base = base / part
        return base
    elif profile.appdata_subdir:
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return None
        return Path(appdata) / profile.appdata_subdir
    return None


def _steamid_subfolder_matches(subfolder: Path, profile: GameProfile) -> bool:
    """Return True if this directory name is a valid SteamID subfolder for the given profile."""
    if not subfolder.is_dir():
        return False
    name = subfolder.name
    fmt = profile.steamid_folder_format
    if fmt == "steam64_dec":
        return name.isdigit() and len(name) == 17
    elif fmt == "steam64_hex":
        return len(name) == 16 and all(c in "0123456789abcdef" for c in name.lower())
    elif fmt == "steam32_dec":
        return name.isdigit() and 1 <= len(name) <= 10
    return False


def _folder_name_to_steam64(folder_name: str, profile: GameProfile) -> int | None:
    """Convert a SteamID subfolder name to a Steam64 integer."""
    fmt = profile.steamid_folder_format
    try:
        if fmt == "steam64_dec":
            return int(folder_name)
        elif fmt == "steam64_hex":
            return int(folder_name, 16)
        elif fmt == "steam32_dec":
            return int(folder_name) + 76561197960265728
    except ValueError:
        pass
    return None


def _find_windows(profile: GameProfile) -> list[Path]:
    base = _save_base_windows(profile)
    if not base or not base.exists():
        return []
    results = []
    if profile.has_steamid_subfolder:
        for subfolder in base.iterdir():
            if _steamid_subfolder_matches(subfolder, profile):
                for candidate in subfolder.glob(profile.save_glob):
                    if candidate.is_file():
                        results.append(candidate)
    else:
        for candidate in base.glob(profile.save_glob):
            if candidate.is_file():
                results.append(candidate)
    return results


def _find_linux(profile: GameProfile) -> list[Path]:
    """On Linux (Proton), saves mirror the Windows path inside each game's compatdata prefix."""
    results = []

    if profile.documents_subdir:
        user_rel_parts = ["Documents"] + profile.documents_subdir.split("/")
    else:
        user_rel_parts = ["AppData", "Roaming", profile.appdata_subdir]

    for steam_base in _get_steam_bases():
        compat_base = steam_base / "steamapps" / "compatdata"
        if not compat_base.exists():
            continue

        game_dir = (
            compat_base
            / str(profile.steam_app_id)
            / "pfx"
            / "drive_c"
            / "users"
            / "steamuser"
        )
        for part in user_rel_parts:
            game_dir = game_dir / part

        if not game_dir.exists():
            continue

        if profile.has_steamid_subfolder:
            for subfolder in game_dir.iterdir():
                if _steamid_subfolder_matches(subfolder, profile):
                    for candidate in subfolder.glob(profile.save_glob):
                        if candidate.is_file():
                            results.append(candidate)
        else:
            for candidate in game_dir.glob(profile.save_glob):
                if candidate.is_file():
                    results.append(candidate)

    return results


def _get_steam_bases() -> list[Path]:
    bases = []
    symlink = Path.home() / ".steam" / "steam"
    if symlink.exists() and symlink.is_symlink():
        bases.append(symlink.resolve())
    bases.extend(
        [
            Path.home() / ".local" / "share" / "Steam",
            Path.home()
            / ".var"
            / "app"
            / "com.valvesoftware.Steam"
            / ".local"
            / "share"
            / "Steam",
        ]
    )
    seen: set[str] = set()
    unique = []
    for b in bases:
        resolved = str(b.resolve()) if b.exists() else str(b)
        if resolved not in seen:
            seen.add(resolved)
            unique.append(b)
    return unique
