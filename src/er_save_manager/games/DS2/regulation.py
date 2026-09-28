"""
DS2 regulation reader: per-item stack, upgrade and durability limits.

Every DS2 save embeds the game's param data in container entry 21. Upgrade
caps are read from that copy so they always match the regulation the save was
written with, including modded regulations. No baked table is used.

Entry 21 game data:
  [0x00:0x04]  u32 LE compressed size
  [0x04:0x08]  u32 LE decompressed size
  [0x08:...]   zlib stream of compressed size bytes, then zero padding
The decompressed payload is a BND4 archive of .param files.

BND4 fields used (LE):
  0x0C  u32  entry count
  0x10  u64  header size, which is also the start of the entry headers
  0x20  u64  entry header size
  0x31  u8   format flags, only 0x30 (names, 32-bit offsets, uncompressed)
             is supported
Entry header:
  +0x08  u64  data size
  +0x10  u32  data offset
  +0x14  u32  name offset (NUL terminated Shift-JIS)

Param file, 64-bit DS2 layout:
  0x00  u32  strings offset, which is the end of the row data
  0x0A  u16  row count
  0x30  u64  offset of the first row's data
  0x40  row table, 24 bytes per row: u64 id, u64 data offset, u64 name offset
The row size is not stored. It is derived as
(strings offset - first row data offset) / row count.

Item resolution, keyed by the inventory item id (an ItemParam row id):
  ItemParam links an item to its equipment row and holds the stack cap.
  Weapons  ItemParam.weapon_id -> WeaponParam row -> reinforce id
           -> WeaponReinforceParam max level. Durability is
           WeaponParam.max_durability.
  Armor    ItemParam.armor_id -> ArmorParam row -> armor_reinforce_id
           -> ArmorReinforceParam max level. Durability is
           ArmorParam.durability.
  Rings    ItemParam.ring_id -> RingParam.durability.
  Spells   ItemParam.spell_id -> SpellParam casts. The inventory quantity of
           a spell is its cast count, so the limit is the highest
           casts_tier value instead of ItemParam.max_held_count.
  Others   ItemParam.max_held_count only.
Items missing from ItemParam are unknown to the regulation and report no
limits.

Field offsets are byte offsets into a row. They were derived from the column
order of the Smithbox CSV exports and verified against those CSVs for every
row. Inventory durability of unused game-written items equals these values.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

REGULATION_ENTRY = 21

_BND4_MAGIC = b"BND4"
_BND4_FORMAT_OFFSET = 0x31
_BND4_SUPPORTED_FORMAT = 0x30

_PARAM_ROW_TABLE_START = 0x40
_PARAM_ROW_ENTRY_SIZE = 24

# ItemParam
_ITEM_WEAPON_ID = 20  # s32
_ITEM_ARMOR_ID = 24  # s32
_ITEM_RING_ID = 32  # s32
_ITEM_SPELL_ID = 36  # s32
_ITEM_MAX_HELD = 74  # u16
# WeaponParam
_WEAPON_REINFORCE_ID = 8  # s32
_WEAPON_DURABILITY = 40  # f32
# WeaponReinforceParam
_WEAPON_REINFORCE_MAX_LEVEL = 0x48  # s32
# ArmorParam
_ARMOR_REINFORCE_ID = 24  # s32
_ARMOR_DURABILITY = 56  # f32
# ArmorReinforceParam
_ARMOR_REINFORCE_MAX_LEVEL = 0x60  # s32
# SpellParam, one u8 per attunement tier
_SPELL_CASTS_FIRST_TIER = 241
_SPELL_TIER_COUNT = 10
# RingParam
_RING_DURABILITY = 4  # f32


class _Param:
    """Row lookup over one .param file inside the decompressed regulation."""

    def __init__(self, blob: bytes, start: int, size: int, name: str) -> None:
        strings_offset = struct.unpack_from("<I", blob, start)[0]
        row_count = struct.unpack_from("<H", blob, start + 0x0A)[0]
        data_start = struct.unpack_from("<Q", blob, start + 0x30)[0]
        if row_count == 0:
            raise ValueError(f"{name} has no rows")

        row_bytes = strings_offset - data_start
        if row_bytes <= 0 or row_bytes % row_count:
            raise ValueError(f"{name} row size is not an integer")
        self._row_size = row_bytes // row_count

        self._blob = blob
        self._rows: dict[int, int] = {}
        for i in range(row_count):
            entry = start + _PARAM_ROW_TABLE_START + i * _PARAM_ROW_ENTRY_SIZE
            row_id, data_offset, _name_offset = struct.unpack_from("<QQQ", blob, entry)
            if i == 0 and data_offset != data_start:
                raise ValueError(f"{name} first row does not match its data start")
            self._rows[row_id] = start + data_offset

    def ids(self) -> list[int]:
        return list(self._rows)

    def _read(self, fmt: str, row_id: int, field_offset: int):
        if field_offset + struct.calcsize(fmt) > self._row_size:
            raise ValueError("field offset is outside the row")
        return struct.unpack_from(fmt, self._blob, self._rows[row_id] + field_offset)[0]

    def has(self, row_id: int) -> bool:
        return row_id in self._rows

    def s32(self, row_id: int, field_offset: int) -> int:
        return self._read("<i", row_id, field_offset)

    def u16(self, row_id: int, field_offset: int) -> int:
        return self._read("<H", row_id, field_offset)

    def f32(self, row_id: int, field_offset: int) -> float:
        return self._read("<f", row_id, field_offset)

    def u8(self, row_id: int, field_offset: int) -> int:
        return self._read("<B", row_id, field_offset)


def _read_bnd4(blob: bytes) -> dict[str, tuple[int, int]]:
    """Map file name to (data offset, data size) for every BND4 entry."""
    if blob[:4] != _BND4_MAGIC:
        raise ValueError("regulation payload is not a BND4 archive")
    if blob[_BND4_FORMAT_OFFSET] != _BND4_SUPPORTED_FORMAT:
        raise ValueError(f"unsupported BND4 format 0x{blob[_BND4_FORMAT_OFFSET]:02X}")

    count = struct.unpack_from("<I", blob, 0x0C)[0]
    header_size = struct.unpack_from("<Q", blob, 0x10)[0]
    entry_size = struct.unpack_from("<Q", blob, 0x20)[0]

    files: dict[str, tuple[int, int]] = {}
    for i in range(count):
        base = header_size + i * entry_size
        size = struct.unpack_from("<Q", blob, base + 0x08)[0]
        data_offset, name_offset = struct.unpack_from("<II", blob, base + 0x10)
        name_end = blob.index(b"\x00", name_offset)
        name = blob[name_offset:name_end].decode("shift_jis", errors="replace")
        files[name] = (data_offset, size)
    return files


@dataclass(frozen=True)
class _ItemLimits:
    max_held: int
    max_upgrade: int = 0
    durability: float | None = None


class Regulation:
    """Per-item limits (stack size, upgrade level, durability) resolved from
    the embedded params."""

    def __init__(self, items: dict[int, _ItemLimits]) -> None:
        self._items = items

    @classmethod
    def from_entry(cls, entry: bytes | bytearray) -> Regulation:
        try:
            compressed_size, decompressed_size = struct.unpack_from("<II", entry, 0)
            payload = zlib.decompress(bytes(entry[8 : 8 + compressed_size]))
        except (struct.error, zlib.error) as e:
            raise ValueError(f"regulation entry is unreadable: {e}") from e
        if len(payload) != decompressed_size:
            raise ValueError("regulation size does not match its header")

        files = _read_bnd4(payload)

        def param(name: str) -> _Param:
            if name not in files:
                raise ValueError(f"{name} missing from regulation")
            start, size = files[name]
            return _Param(payload, start, size, name)

        item_param = param("ItemParam.param")
        weapons = param("WeaponParam.param")
        weapon_reinforce = param("WeaponReinforceParam.param")
        armors = param("ArmorParam.param")
        armor_reinforce = param("ArmorReinforceParam.param")
        rings = param("RingParam.param")
        spells = param("SpellParam.param")

        items: dict[int, _ItemLimits] = {}
        for item_id in item_param.ids():
            max_held = item_param.u16(item_id, _ITEM_MAX_HELD)
            weapon_id = item_param.s32(item_id, _ITEM_WEAPON_ID)
            armor_id = item_param.s32(item_id, _ITEM_ARMOR_ID)
            ring_id = item_param.s32(item_id, _ITEM_RING_ID)
            spell_id = item_param.s32(item_id, _ITEM_SPELL_ID)

            max_upgrade = 0
            durability: float | None = None
            if weapons.has(weapon_id):
                reinforce_id = weapons.s32(weapon_id, _WEAPON_REINFORCE_ID)
                if weapon_reinforce.has(reinforce_id):
                    max_upgrade = weapon_reinforce.s32(
                        reinforce_id, _WEAPON_REINFORCE_MAX_LEVEL
                    )
                durability = weapons.f32(weapon_id, _WEAPON_DURABILITY)
            elif armors.has(armor_id):
                reinforce_id = armors.s32(armor_id, _ARMOR_REINFORCE_ID)
                if armor_reinforce.has(reinforce_id):
                    max_upgrade = armor_reinforce.s32(
                        reinforce_id, _ARMOR_REINFORCE_MAX_LEVEL
                    )
                durability = armors.f32(armor_id, _ARMOR_DURABILITY)
            elif rings.has(ring_id):
                durability = rings.f32(ring_id, _RING_DURABILITY)

            if spells.has(spell_id):
                max_held = max(
                    spells.u8(spell_id, _SPELL_CASTS_FIRST_TIER + tier)
                    for tier in range(_SPELL_TIER_COUNT)
                )

            items[item_id] = _ItemLimits(max_held, max(0, max_upgrade), durability)
        return cls(items)

    @classmethod
    def from_container(cls, container) -> Regulation:
        return cls.from_entry(container.get_entry(REGULATION_ENTRY))

    def max_upgrade(self, item_id: int, category: str) -> int:
        """Highest upgrade level for a weapon or armor piece. 0 when it
        cannot be upgraded or is absent from the regulation."""
        if category not in ("weapons", "armors"):
            return 0
        info = self._items.get(item_id)
        return info.max_upgrade if info else 0

    def max_held(self, item_id: int) -> int | None:
        """Largest quantity the game allows: the stack size, or the highest cast
        count for a spell. None for an unknown item."""
        info = self._items.get(item_id)
        return info.max_held if info else None

    def durability(self, item_id: int) -> float | None:
        """Maximum durability of a weapon, armor piece or ring, or None when
        the item has none or is unknown."""
        info = self._items.get(item_id)
        return info.durability if info else None
