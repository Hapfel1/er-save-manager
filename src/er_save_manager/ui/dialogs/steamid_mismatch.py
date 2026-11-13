"""Prompt after a load when the save holds another Steam account's SteamID
than the SteamID folder it sits in (a save copied from a friend or a
download): the game does not load it until it is patched."""

from __future__ import annotations

from pathlib import Path

SETTING = "show_steamid_mismatch_warning"


def folder_steam64(save_path: Path, profile) -> int | None:
    """Steam64 of the SteamID folder holding the save, None outside one."""
    from er_save_manager.games.game_profiles import (
        _folder_name_to_steam64,
        _steamid_subfolder_matches,
    )

    if not profile.has_steamid_subfolder:
        return None
    folder = save_path.parent
    if not _steamid_subfolder_matches(folder, profile):
        return None
    return _folder_name_to_steam64(folder.name, profile)


def save_steam64(save_path: Path, game_key: str, er_save=None) -> int | None:
    """SteamID stored in a PC save, None when the save has none (console
    saves, Dark Souls Remastered) or it cannot be read."""
    from er_save_manager.games.ps_userdata import is_ps_userdata

    try:
        if is_ps_userdata(save_path):
            return None
        if game_key == "elden_ring":
            if er_save is None or er_save.is_ps or not er_save.user_data_10_parsed:
                return None
            return er_save.user_data_10_parsed.steam_id or None
        if game_key == "nightreign":
            from er_save_manager.games.nightreign_steamid import (
                detect_steamid_nr,
                is_ps_memory_dat,
            )

            return None if is_ps_memory_dat(save_path) else detect_steamid_nr(save_path)
        if game_key == "dark_souls_3":
            from er_save_manager.games.ds3_steamid import detect_steamid_ds3

            return detect_steamid_ds3(save_path)
        if game_key == "dark_souls_2":
            from er_save_manager.games.ds2_dsr_steamid import detect_steamid

            return detect_steamid(save_path, game_key)
        if game_key == "sekiro":
            from er_save_manager.games.sekiro_steamid import detect_steamid_sekiro

            return detect_steamid_sekiro(save_path)
        if game_key == "armored_core_6":
            from er_save_manager.games.ac6_steamid import detect_steamid_ac6

            return detect_steamid_ac6(save_path)
    except Exception:
        return None
    return None


def mismatch(save_path: Path, profile, er_save=None) -> tuple[int, int] | None:
    """(SteamID in the save, SteamID of its folder) when they differ."""
    folder_id = folder_steam64(save_path, profile)
    if folder_id is None:
        return None
    save_id = save_steam64(save_path, profile.key, er_save)
    if save_id is None or save_id == folder_id:
        return None
    return save_id, folder_id


def ask_patch(parent, game_name: str, save_id: int, folder_id: int) -> bool:
    """True when the user chose to patch the save to the folder's SteamID."""
    from er_save_manager.ui import palette
    from er_save_manager.ui.dialogs.opt_out_warning import confirm_warning

    return confirm_warning(
        parent,
        SETTING,
        "Save From Another Steam Account",
        "Save from another Steam account",
        [
            f"This save belongs to SteamID {save_id}, but it is in the folder "
            f"of SteamID {folder_id}. {game_name} does not load it like this.",
            "Patching writes the folder's SteamID into the save. A backup is "
            "made first. Choose Not Now if you only load this save to look at "
            "or test it.",
        ],
        confirm_text="Patch to My SteamID",
        cancel_text="Not Now",
        remember_on_cancel=True,
        icon="ℹ",
        icon_color=palette.PURPLE_TEXT,
    )
