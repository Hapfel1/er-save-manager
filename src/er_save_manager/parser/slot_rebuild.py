"""Utility to rebuild character slot data for save modification.

Implements full save serialization similar to the Rust implementation.
When modifications are made to variable-size structures like Regions,
we rebuild the entire slot by serializing all components in order.
"""

from __future__ import annotations

import struct
from io import BytesIO
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from er_save_manager.parser.user_data_x import UserDataX


def rebuild_slot_with_map(slot: UserDataX) -> tuple[bytes, list[dict[str, Any]]]:
    """Rebuild entire character slot from parsed structure.

    This serializes all components in the exact order they appear in the file.
    This is the proper way to handle variable-size structures like Regions
    without corrupting the save file.

    Args:
        slot: Modified UserDataX structure

    Returns:
        Tuple of (rebuilt slot bytes, section map list)
    """
    buf = BytesIO()
    sections: list[dict[str, Any]] = []

    def mark(name: str, start: int, end: int):
        sections.append({"name": name, "start": start, "end": end, "size": end - start})

    def write_section(name: str, writer):
        s = buf.tell()
        writer()
        e = buf.tell()
        mark(name, s, e)

    # Version (4 bytes)
    write_section("version", lambda: buf.write(struct.pack("<I", slot.version)))

    # Empty slot check
    if slot.version == 0:
        # Pad to slot size (2,621,440 bytes)
        slot_size = 0x280000
        bytes_written = buf.tell()
        remaining = slot_size - bytes_written
        if remaining > 0:
            write_section("padding_to_slot_end", lambda: buf.write(b"\x00" * remaining))
        return buf.getvalue(), sections

    # Map ID and header
    write_section("map_id", lambda: slot.map_id.write(buf))
    write_section("unk0x8", lambda: buf.write(slot.unk0x8))
    write_section("unk0x10", lambda: buf.write(slot.unk0x10))

    # Gaitem map
    def write_gaitem_map():
        for gaitem in slot.gaitem_map:
            gaitem.write(buf)

    write_section("gaitem_map", write_gaitem_map)

    # PlayerGameData
    write_section("player_game_data", lambda: slot.player_game_data.write(buf))

    # SPEffects
    def write_sp_effects():
        for sp_effect in slot.sp_effects:
            sp_effect.write(buf)

    write_section("sp_effects", write_sp_effects)

    # Equipment structures
    write_section(
        "equipped_items_equip_index", lambda: slot.equipped_items_equip_index.write(buf)
    )
    write_section(
        "active_weapon_slots_and_arm_style",
        lambda: slot.active_weapon_slots_and_arm_style.write(buf),
    )
    write_section(
        "equipped_items_item_id", lambda: slot.equipped_items_item_id.write(buf)
    )
    write_section(
        "equipped_items_gaitem_handle",
        lambda: slot.equipped_items_gaitem_handle.write(buf),
    )

    # Inventory held
    write_section("inventory_held", lambda: slot.inventory_held.write(buf))

    # More equipment
    write_section("equipped_spells", lambda: slot.equipped_spells.write(buf))
    write_section("equipped_items", lambda: slot.equipped_items.write(buf))
    write_section("equipped_gestures", lambda: slot.equipped_gestures.write(buf))
    write_section("acquired_projectiles", lambda: slot.acquired_projectiles.write(buf))
    write_section(
        "equipped_armaments_and_items",
        lambda: slot.equipped_armaments_and_items.write(buf),
    )
    write_section("equipped_physics", lambda: slot.equipped_physics.write(buf))

    # Face data
    write_section("face_data", lambda: slot.face_data.write(buf))

    # Inventory storage
    write_section(
        "inventory_storage_box", lambda: slot.inventory_storage_box.write(buf)
    )

    # Gestures and regions (KEY: This is where modifications happen)
    write_section("gestures", lambda: slot.gestures.write(buf))
    write_section("unlocked_regions", lambda: slot.unlocked_regions.write(buf))

    # Horse/Torrent
    write_section("horse", lambda: slot.horse.write(buf))

    # Control byte
    write_section(
        "control_byte_maybe",
        lambda: buf.write(struct.pack("<B", slot.control_byte_maybe)),
    )

    # Blood stain
    write_section("blood_stain", lambda: slot.blood_stain.write(buf))

    # Unknown fields
    write_section(
        "unk_gamedataman_0x120_or_gamedataman_0x130",
        lambda: buf.write(
            struct.pack("<I", slot.unk_gamedataman_0x120_or_gamedataman_0x130)
        ),
    )
    write_section(
        "unk_gamedataman_0x88",
        lambda: buf.write(struct.pack("<I", slot.unk_gamedataman_0x88)),
    )

    # Menu and game data
    write_section(
        "menu_profile_save_load", lambda: slot.menu_profile_save_load.write(buf)
    )
    write_section("trophy_equip_data", lambda: slot.trophy_equip_data.write(buf))
    write_section("gaitem_game_data", lambda: slot.gaitem_game_data.write(buf))
    write_section("tutorial_data", lambda: slot.tutorial_data.write(buf))

    # GameMan bytes
    write_section(
        "gameman_0x8c", lambda: buf.write(struct.pack("<B", slot.gameman_0x8c))
    )
    write_section(
        "gameman_0x8d", lambda: buf.write(struct.pack("<B", slot.gameman_0x8d))
    )
    write_section(
        "gameman_0x8e", lambda: buf.write(struct.pack("<B", slot.gameman_0x8e))
    )

    # Death and character info
    write_section(
        "total_deaths_count",
        lambda: buf.write(struct.pack("<I", slot.total_deaths_count)),
    )
    write_section(
        "character_type", lambda: buf.write(struct.pack("<i", slot.character_type))
    )
    write_section(
        "in_online_session_flag",
        lambda: buf.write(struct.pack("<B", slot.in_online_session_flag)),
    )
    write_section(
        "character_type_online",
        lambda: buf.write(struct.pack("<I", slot.character_type_online)),
    )
    write_section(
        "last_rested_grace",
        lambda: buf.write(struct.pack("<I", slot.last_rested_grace)),
    )
    write_section(
        "not_alone_flag", lambda: buf.write(struct.pack("<B", slot.not_alone_flag))
    )
    write_section(
        "in_game_countdown_timer",
        lambda: buf.write(struct.pack("<I", slot.in_game_countdown_timer)),
    )
    write_section(
        "unk_gamedataman_0x124_or_gamedataman_0x134",
        lambda: buf.write(
            struct.pack("<I", slot.unk_gamedataman_0x124_or_gamedataman_0x134)
        ),
    )

    # Event flags
    write_section("event_flags", lambda: buf.write(slot.event_flags))
    write_section(
        "event_flags_terminator",
        lambda: buf.write(struct.pack("<B", slot.event_flags_terminator)),
    )

    # World structures
    def write_field_area():
        # If size is unreasonable, write size as 0 to avoid parsing errors
        size = (
            slot.field_area.size
            if slot.field_area.size > 0 and slot.field_area.size < 0x10000
            else 0
        )
        buf.write(struct.pack("<i", size))
        if size > 0:
            buf.write(slot.field_area.data)

    write_section("field_area", write_field_area)

    def write_world_area():
        size = (
            slot.world_area.size
            if slot.world_area.size > 0 and slot.world_area.size < 0x10000
            else 0
        )
        buf.write(struct.pack("<i", size))
        if size > 0:
            buf.write(slot.world_area.data)

    write_section("world_area", write_world_area)

    def write_world_geom_man():
        size = (
            slot.world_geom_man.size
            if slot.world_geom_man.size > 0 and slot.world_geom_man.size < 0x100000
            else 0
        )
        buf.write(struct.pack("<i", size))
        if size > 0:
            buf.write(slot.world_geom_man.data)

    write_section("world_geom_man", write_world_geom_man)

    def write_world_geom_man2():
        size = (
            slot.world_geom_man2.size
            if slot.world_geom_man2.size > 0 and slot.world_geom_man2.size < 0x100000
            else 0
        )
        buf.write(struct.pack("<i", size))
        if size > 0:
            buf.write(slot.world_geom_man2.data)

    write_section("world_geom_man2", write_world_geom_man2)

    # RendMan - has raw bytes data
    def write_rend_man():
        # If size is unreasonable, write size as 0 to avoid parsing errors
        size = (
            slot.rend_man.size
            if slot.rend_man.size > 0 and slot.rend_man.size < 0x100000
            else 0
        )
        buf.write(struct.pack("<i", size))
        if size > 0:
            if isinstance(slot.rend_man.data, bytes):
                buf.write(slot.rend_man.data)
            else:
                slot.rend_man.data.write(buf)

    write_section("rend_man", write_rend_man)

    # Player coordinates
    write_section("player_coordinates", lambda: slot.player_coordinates.write(buf))

    # Padding after PlayerCoordinates (2 bytes)
    write_section("padding_after_player_coordinates", lambda: buf.write(b"\x00" * 2))

    # More bytes
    write_section(
        "spawn_point_entity_id",
        lambda: buf.write(struct.pack("<I", slot.spawn_point_entity_id)),
    )
    write_section(
        "game_man_0xb64", lambda: buf.write(struct.pack("<I", slot.game_man_0xb64))
    )

    # Version-specific fields
    if slot.version >= 65 and slot.temp_spawn_point_entity_id is not None:
        write_section(
            "temp_spawn_point_entity_id",
            lambda: buf.write(struct.pack("<I", slot.temp_spawn_point_entity_id)),
        )
    if slot.version >= 66 and slot.game_man_0xcb3 is not None:
        write_section(
            "game_man_0xcb3", lambda: buf.write(struct.pack("<B", slot.game_man_0xcb3))
        )

    # Network and world state
    write_section("net_man", lambda: slot.net_man.write(buf))

    # Weather, time, base version
    write_section("world_area_weather", lambda: slot.world_area_weather.write(buf))

    write_section("world_area_time", lambda: slot.world_area_time.write(buf))

    write_section("base_version", lambda: slot.base_version.write(buf))

    # Steam ID
    write_section("steam_id", lambda: buf.write(struct.pack("<Q", slot.steam_id)))

    # PS5 Activity and DLC
    write_section("ps5_activity", lambda: slot.ps5_activity.write(buf))
    write_section("dlc", lambda: slot.dlc.write(buf))
    write_section("player_data_hash", lambda: slot.player_data_hash.write(buf))

    # Pad to exact slot boundary (2,621,440 bytes)
    slot_size = 0x280000
    current_size = buf.tell()
    if current_size < slot_size:
        if hasattr(slot, "rest") and slot.rest:
            # Don't write the rest field - we rebuild everything properly
            pass
            # # Write the rest field if available
            # write_section("rest_padding", lambda: buf.write(slot.rest))
            current_size = buf.tell()

        if current_size < slot_size:
            # Fill remaining with zeros
            padding_needed = slot_size - current_size
            write_section(
                "padding_to_slot_end", lambda: buf.write(b"\x00" * padding_needed)
            )

    return buf.getvalue(), sections


def rebuild_slot(slot: UserDataX) -> bytes:
    """Rebuild slot and return only bytes (compat wrapper)."""
    data, _ = rebuild_slot_with_map(slot)
    return data
