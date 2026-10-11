"""Rebuild the load screen copy of a character (CSProfileSummary entry) from its slot.

Every field the slot also holds is taken from the slot's raw bytes: name,
level, play time, runes memory, map, the equipment preview, body type, class
and starting gift. The place name id and the equipment block's unknown words
are kept, since the slot has no copy of them.

The game writes eye colors and the frenzied flame byte differently into the
two FACE copies, so the profile's FACE block is only taken from the slot when
the profile has none.
"""

from __future__ import annotations

import struct

PROFILE_SIZE = 0x24C

# Offsets in the profile entry
_PROFILE_NAME = 0x0
_PROFILE_LEVEL = 0x22
_PROFILE_SECONDS = 0x26
_PROFILE_RUNES_MEMORY = 0x2A
_PROFILE_MAP = 0x2E
_PROFILE_FACE = 0x36
_PROFILE_FACE_SIZE = 0x124
_PROFILE_EQUIPMENT = 0x15A
_PROFILE_BODY_TYPE = 0x242

# Offsets in the slot: header, then PlayerGameData
_HEADER_MAP = 0x4
_HEADER_PLAY_TIME_MS = 0x8
_PGD_NAME = 0x94
_PGD_NAME_SIZE = 0x22  # 16 UTF-16 chars + terminator
_PGD_LEVEL = 0x60
_PGD_RUNES_MEMORY = 0x68
_PGD_GENDER = 0xB6
_PGD_ARCHETYPE = 0xB7
_PGD_GIFT = 0xBB
_EQUIPPED_PHYSICS_SIZE = 0xC

# Equipment preview, in uint32 words: ActiveWeaponSlotsAndArmStyle, then the 22
# EquipmentSlots as tagged ids, then the same slots as item ids
_EQUIP_ACTIVE_SLOTS = 2
_EQUIP_TAGGED = 9
_EQUIP_ITEM_IDS = 31
_EQUIP_SLOT_COUNT = 22
_ARMOR_SLOTS = range(12, 17)  # head, chest, arms, legs, hair
_TALISMAN_SLOTS = range(17, 22)


def _tagged(slot_index: int, item_id: int) -> int:
    """Equipment slot item id as the profile's tagged id (0 when empty)."""
    if item_id == 0xFFFFFFFF:
        return 0
    if slot_index in _ARMOR_SLOTS:
        return 0x90000000 | item_id
    if slot_index in _TALISMAN_SLOTS:
        return 0xA0000000 | item_id
    return 0x80000000 | (item_id & 0x7FFFFF)


def profile_from_slot(raw: bytes | bytearray, slot, profile: bytes) -> bytes:
    """Return profile with every field the slot also holds taken from the slot.

    slot is a parsed UserDataX whose offsets describe raw.
    """
    out = bytearray(profile)
    start = slot.data_start
    pgd = slot.player_game_data_offset

    # The slot keeps old characters after the terminator; the profile has zeros
    name = bytes(raw[pgd + _PGD_NAME : pgd + _PGD_NAME + _PGD_NAME_SIZE - 2])
    end = next((k for k in range(0, len(name), 2) if name[k : k + 2] == b"\0\0"), None)
    if end is not None:
        name = name[:end]
    out[_PROFILE_NAME : _PROFILE_NAME + _PGD_NAME_SIZE] = name.ljust(
        _PGD_NAME_SIZE, b"\0"
    )
    out[_PROFILE_LEVEL : _PROFILE_LEVEL + 4] = raw[
        pgd + _PGD_LEVEL : pgd + _PGD_LEVEL + 4
    ]
    play_time_ms = struct.unpack_from("<Q", raw, start + _HEADER_PLAY_TIME_MS)[0]
    struct.pack_into("<I", out, _PROFILE_SECONDS, min(play_time_ms // 1000, 0xFFFFFFFF))
    out[_PROFILE_RUNES_MEMORY : _PROFILE_RUNES_MEMORY + 4] = raw[
        pgd + _PGD_RUNES_MEMORY : pgd + _PGD_RUNES_MEMORY + 4
    ]
    out[_PROFILE_MAP : _PROFILE_MAP + 4] = raw[
        start + _HEADER_MAP : start + _HEADER_MAP + 4
    ]

    if out[_PROFILE_FACE + 4 : _PROFILE_FACE + 8] != b"FACE":
        face = start + slot.equipped_physics_offset + _EQUIPPED_PHYSICS_SIZE
        out[_PROFILE_FACE : _PROFILE_FACE + _PROFILE_FACE_SIZE] = raw[
            face : face + _PROFILE_FACE_SIZE
        ]

    active = start + slot.active_weapon_slots_and_arm_style_offset
    item_ids = struct.unpack_from(
        f"<{_EQUIP_SLOT_COUNT}I", raw, start + slot.equipped_items_item_id_offset
    )
    words = list(struct.unpack_from("<58I", out, _PROFILE_EQUIPMENT))
    words[_EQUIP_ACTIVE_SLOTS : _EQUIP_ACTIVE_SLOTS + 7] = struct.unpack_from(
        "<7I", raw, active
    )
    words[_EQUIP_TAGGED : _EQUIP_TAGGED + _EQUIP_SLOT_COUNT] = [
        _tagged(i, item_id) for i, item_id in enumerate(item_ids)
    ]
    words[_EQUIP_ITEM_IDS : _EQUIP_ITEM_IDS + _EQUIP_SLOT_COUNT] = item_ids
    struct.pack_into("<58I", out, _PROFILE_EQUIPMENT, *words)

    out[_PROFILE_BODY_TYPE] = raw[pgd + _PGD_GENDER]
    out[_PROFILE_BODY_TYPE + 1] = raw[pgd + _PGD_ARCHETYPE]
    out[_PROFILE_BODY_TYPE + 2] = raw[pgd + _PGD_GIFT]
    return bytes(out)
