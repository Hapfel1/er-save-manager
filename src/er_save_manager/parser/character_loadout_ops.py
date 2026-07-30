"""
Character loadout data layer.

Collects and applies the Stats, Info, and Event Flags sections of a
character loadout directly against parsed save data.
"""

from __future__ import annotations

import struct
from typing import Any

from er_save_manager.editors.matchmaking_utils import get_max_weapon_upgrade
from er_save_manager.parser.event_flags import EventFlags
from er_save_manager.parser.slot_rebuild import rebuild_slot
from er_save_manager.transfer.character_ops import CharacterOperations

STATS_ATTR_KEYS = (
    "vigor",
    "mind",
    "endurance",
    "strength",
    "dexterity",
    "intelligence",
    "faith",
    "arcane",
)

INFO_ATTR_KEYS = (
    "gender",
    "archetype",
    "voice_type",
    "gift",
    "additional_talisman_slot_count",
    "summon_spirit_level",
    "max_crimson_flask_count",
    "max_cerulean_flask_count",
)

NG_FLAG_IDS = (50, 51, 52, 53, 54, 55, 56, 57)

_PROFILE_SIZE = 0x24C


# ---- stats --------------------------------------------------------------


def collect_stats(save_file, slot_idx: int) -> dict[str, int]:
    """Capture attributes, level, runes and matchmaking weapon level."""
    char = save_file.characters[slot_idx].player_game_data
    data = {key: getattr(char, key, 0) for key in STATS_ATTR_KEYS}
    data["level"] = getattr(char, "level", 0)
    data["runes"] = getattr(char, "runes", 0)
    data["matchmaking_weapon_level"] = getattr(char, "matchmaking_weapon_level", 0)
    return data


def apply_stats(save_file, slot_idx: int, data: dict[str, Any]) -> None:
    """Write stats onto the in-memory slot. Call finalize_slot() afterward."""
    slot = save_file.characters[slot_idx]
    char = slot.player_game_data

    for key in STATS_ATTR_KEYS:
        if key in data:
            setattr(char, key, int(data[key]))
    if "level" in data:
        char.level = int(data["level"])
    if "runes" in data:
        char.runes = int(data["runes"])

    if "matchmaking_weapon_level" in data:
        floor = get_max_weapon_upgrade(slot)
        value = max(0, min(25, int(data["matchmaking_weapon_level"])))
        char.matchmaking_weapon_level = max(value, floor)

    _patch_profile_level(save_file, slot_idx, char.level)


def _patch_profile_level(save_file, slot_idx: int, level: int) -> None:
    if not hasattr(save_file, "_user_data_10_offset"):
        return
    ps_off = 0 if save_file.is_ps else 16
    profile_summary_off = (
        save_file._user_data_10_offset + ps_off + 4 + 8 + 0x140 + 0x1808
    )
    level_off = profile_summary_off + 10 + slot_idx * _PROFILE_SIZE + 0x22
    save_file._raw_data[level_off : level_off + 4] = struct.pack("<I", level)
    profiles = _profiles(save_file)
    if profiles and slot_idx < len(profiles):
        profiles[slot_idx].level = level


# ---- info -----------------------------------------------------------------


def collect_info(save_file, slot_idx: int) -> dict[str, Any]:
    """Capture character info fields plus NG+ level and playtime."""
    slot = save_file.characters[slot_idx]
    char = slot.player_game_data
    data: dict[str, Any] = {"character_name": getattr(char, "character_name", "")}
    for key in INFO_ATTR_KEYS:
        data[key] = getattr(char, key, 0)
    data["ng_level"] = _read_ng_level(slot)

    time = getattr(slot, "world_area_time", None)
    data["playtime_h"] = getattr(time, "hour", 0) if time else 0
    data["playtime_m"] = getattr(time, "minute", 0) if time else 0
    data["playtime_s"] = getattr(time, "second", 0) if time else 0
    return data


def _read_ng_level(slot) -> int:
    flags = slot.event_flags
    bits = [1 if EventFlags.get_flag(flags, fid) else 0 for fid in NG_FLAG_IDS]
    if bits[0] == 1 and sum(bits[1:]) == 0:
        return 0
    if sum(bits[1:]) == 1 and bits[0] == 0:
        return bits[1:].index(1) + 1
    return 0


def apply_info(save_file, slot_idx: int, data: dict[str, Any]) -> None:
    """Write info fields onto the in-memory slot. Call finalize_slot() afterward."""
    slot = save_file.characters[slot_idx]
    char = slot.player_game_data

    if "character_name" in data:
        char.character_name = data["character_name"]
        _patch_profile_name(save_file, slot_idx, data["character_name"])

    for key in INFO_ATTR_KEYS:
        if key in data:
            setattr(char, key, data[key])

    if "ng_level" in data:
        _apply_ng_level(slot, int(data["ng_level"]))

    if "playtime_h" in data or "playtime_m" in data or "playtime_s" in data:
        _apply_playtime(
            save_file,
            slot_idx,
            slot,
            data.get("playtime_h", 0),
            data.get("playtime_m", 0),
            data.get("playtime_s", 0),
        )


def _profiles(save_file):
    if save_file.user_data_10_parsed and save_file.user_data_10_parsed.profile_summary:
        return save_file.user_data_10_parsed.profile_summary.profiles
    return None


def _patch_profile_name(save_file, slot_idx: int, name: str) -> None:
    profiles = _profiles(save_file)
    if not profiles or slot_idx >= len(profiles):
        return
    profiles[slot_idx].character_name = name

    _, profiles_base = CharacterOperations.get_profile_summary_offsets(save_file)
    profile_offset = profiles_base + slot_idx * _PROFILE_SIZE
    name_bytes = name.encode("utf-16-le")
    name_bytes = (name_bytes + b"\x00" * 32)[:32]
    save_file._raw_data[profile_offset : profile_offset + 32] = name_bytes
    save_file._raw_data[profile_offset + 32 : profile_offset + 34] = b"\x00\x00"


def _apply_ng_level(slot, target_level: int) -> None:
    flags = (
        bytearray(slot.event_flags)
        if not isinstance(slot.event_flags, bytearray)
        else slot.event_flags
    )
    for flag_id in NG_FLAG_IDS:
        EventFlags.set_flag(flags, flag_id, False)
    EventFlags.set_flag(flags, NG_FLAG_IDS[target_level], True)
    slot.event_flags = bytes(flags)

    if hasattr(slot, "unk_gamedataman_0x120_or_gamedataman_0x130"):
        slot.unk_gamedataman_0x120_or_gamedataman_0x130 = target_level


def _apply_playtime(save_file, slot_idx: int, slot, h: int, m: int, s: int) -> None:
    h = max(0, int(h))
    m = max(0, min(59, int(m)))
    s = max(0, min(59, int(s)))
    total_seconds = h * 3600 + m * 60 + s

    profiles = _profiles(save_file)
    if profiles and slot_idx < len(profiles):
        profiles[slot_idx].seconds_played = total_seconds
        _, profiles_base = CharacterOperations.get_profile_summary_offsets(save_file)
        sp_offset = profiles_base + slot_idx * _PROFILE_SIZE + 0x26
        save_file._raw_data[sp_offset : sp_offset + 4] = struct.pack(
            "<I", total_seconds
        )

    time = getattr(slot, "world_area_time", None)
    if time is not None:
        time.hour = h
        time.minute = m
        time.second = s


# ---- event flags ----------------------------------------------------------


def collect_event_flags(save_file, slot_idx: int) -> list[dict[str, Any]]:
    """Capture all set event flags, matching the Event Flags tab export format."""
    from er_save_manager.data.event_flags_db import (
        CATEGORIES,
        get_category_flags,
        get_flag_name,
        get_subcategories,
    )

    flags_obj = save_file.characters[slot_idx].event_flags
    set_flags: list[dict[str, Any]] = []
    seen: set[int] = set()

    for category in CATEGORIES:
        subcats = get_subcategories(category) or [None]
        for subcat in subcats:
            for flag_id in get_category_flags(category, subcat):
                if flag_id in seen:
                    continue
                seen.add(flag_id)
                try:
                    if EventFlags.get_flag(flags_obj, flag_id):
                        set_flags.append(
                            {"id": flag_id, "name": get_flag_name(flag_id)}
                        )
                except Exception:
                    pass
    return set_flags


def apply_event_flags(save_file, slot_idx: int, flags: list[dict[str, Any]]) -> None:
    """Set/clear event flags onto the in-memory slot. Call finalize_slot() afterward."""
    slot = save_file.characters[slot_idx]
    buf = (
        bytearray(slot.event_flags)
        if not isinstance(slot.event_flags, bytearray)
        else slot.event_flags
    )
    for entry in flags:
        try:
            flag_id = int(entry["id"])
            state = bool(entry.get("state", True))
            EventFlags.set_flag(buf, flag_id, state)
        except Exception:
            continue
    slot.event_flags = bytes(buf)


# ---- finalize ---------------------------------------------------------------


def finalize_slot(save_file, slot_idx: int, save_path) -> None:
    """Rebuild the slot from in-memory state, recalc checksums and write to disk."""
    slot = save_file.characters[slot_idx]
    rebuilt = rebuild_slot(slot)
    save_file._raw_data[slot.data_start : slot.data_start + len(rebuilt)] = rebuilt
    save_file.recalculate_checksums()
    if save_path:
        save_file.to_file(save_path)
