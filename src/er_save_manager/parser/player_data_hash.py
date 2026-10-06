"""
PlayerGameDataHash recalculation.

The 0x80-byte block after the DLC section holds one checksum per tracked
value. The game rewrites it on every save; it is recomputed here so an
edited slot carries the same hashes a game-written one would.

Each checksum is an Adler-32 variant over little-endian bytes: lo starts at
1 and adds every byte, hi adds lo after every byte, both are reduced modulo
0xFFF1 and the result is (lo | hi << 16) * 2.

Inputs, by hash entry:

    0  level                        u32
    1  stats                        vigor..arcane (8 x u32) + PGD+0x54
    2  archetype                    u32 of the u8 class
    3  PGD+0xB8                     single byte
    5  runes held                   u32
    6  runes memory                 u32
    7  equipped weapons             item id slots L1, L2, L3, R1, R2, R3,
                                    arrows 1, arrows 2, bolts 1, bolts 2
    8  armor and talismans          item id slots 12-15 and 17-21
    10 equipped spells              14 spell ids

Entry 4, entry 9 (quick items, inputs unknown) and the 0x54 bytes after
entry 10 (uninitialized memory in game-written saves) are left untouched.
"""

from __future__ import annotations

import struct

# PlayerGameData field offsets used as hash inputs.
_PGD_STATS = 0x34  # vigor..arcane, then the u32 at 0x54
_PGD_LEVEL = 0x60
_PGD_RUNES = 0x64
_PGD_RUNES_MEMORY = 0x68
_PGD_ARCHETYPE = 0xB7
_PGD_0xB8 = 0xB8

# Indexes into the 22 equipped item id slots.
_WEAPON_SLOTS = (0, 2, 4, 1, 3, 5, 6, 8, 7, 9)
_ARMOR_TALISMAN_SLOTS = (12, 13, 14, 15, 17, 18, 19, 20, 21)
_SPELL_COUNT = 14
_SPELL_STRIDE = 8

# Hash entry index -> PlayerGameDataHash attribute.
_FIELDS = {
    0: "level",
    1: "stats",
    2: "archetype",
    3: "playergame_data_0xc0",
    5: "runes",
    6: "runes_memory",
    7: "equipped_weapons",
    8: "equipped_armors_and_talismans",
    10: "equipped_spells",
}


def _reduce(value: int) -> int:
    quotient = ((0x80078071 * value) >> 32) >> 15
    return (value - quotient * 0xFFF1) & 0xFFFFFFFF


def bytes_hash(data: bytes) -> int:
    lo, hi = 1, 0
    for byte in data:
        lo = (lo + byte) & 0xFFFFFFFF
        hi = (hi + lo) & 0xFFFFFFFF
    return ((_reduce(lo) | (_reduce(hi) << 16)) * 2) & 0xFFFFFFFF


def _u32s_hash(values) -> int:
    return bytes_hash(b"".join(struct.pack("<I", v & 0xFFFFFFFF) for v in values))


def compute(raw: bytes, slot) -> dict[str, int]:
    """Hash values for a slot, read from raw at the slot's tracked offsets."""
    pgd = slot.player_game_data_offset
    item_ids = struct.unpack_from(
        "<22I", raw, slot.data_start + slot.equipped_items_item_id_offset
    )
    spells_off = slot.data_start + slot.equipped_spells_offset
    spells = [
        struct.unpack_from("<I", raw, spells_off + k * _SPELL_STRIDE)[0]
        for k in range(_SPELL_COUNT)
    ]

    def u32(rel: int) -> int:
        return struct.unpack_from("<I", raw, pgd + rel)[0]

    return {
        "level": _u32s_hash([u32(_PGD_LEVEL)]),
        "stats": bytes_hash(bytes(raw[pgd + _PGD_STATS : pgd + _PGD_STATS + 9 * 4])),
        "archetype": _u32s_hash([raw[pgd + _PGD_ARCHETYPE]]),
        "playergame_data_0xc0": bytes_hash(bytes([raw[pgd + _PGD_0xB8]])),
        "runes": _u32s_hash([u32(_PGD_RUNES)]),
        "runes_memory": _u32s_hash([u32(_PGD_RUNES_MEMORY)]),
        "equipped_weapons": _u32s_hash(item_ids[i] for i in _WEAPON_SLOTS),
        "equipped_armors_and_talismans": _u32s_hash(
            item_ids[i] for i in _ARMOR_TALISMAN_SLOTS
        ),
        "equipped_spells": _u32s_hash(spells),
    }


def refresh(raw: bytearray, slot) -> bool:
    """Rewrite the slot's hash entries in raw and in slot.player_data_hash.

    Returns True when any entry changed.
    """
    values = compute(raw, slot)
    base = slot.player_data_hash_offset
    changed = False
    for index, attr in _FIELDS.items():
        off = base + index * 4
        new = struct.pack("<I", values[attr])
        if raw[off : off + 4] != new:
            raw[off : off + 4] = new
            changed = True
        setattr(slot.player_data_hash, attr, values[attr])
    return changed
