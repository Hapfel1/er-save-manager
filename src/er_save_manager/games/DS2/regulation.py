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
  Infusion Weapons only. WeaponReinforceParam.custom_attr_spec_param_id ->
           CustomAttrSpecParam, whose single s32 is a bit mask. Bit n set
           means infusion n is allowed. Bit 0 is the plain weapon.
  Spells   ItemParam.spell_id -> SpellParam casts. The inventory quantity of
           a spell is its cast count, so the limit is the highest
           casts_tier value instead of ItemParam.max_held_count.
           SpellParam.slots_used is the attunement slot cost.
  Others   ItemParam.max_held_count only.
Attunement slots: PhysicalStatsPerLevelStatValuesParam has one row per stat
level (row id 1-99) whose attunement_slots is the slot count at that level.
RelatePhysicalStatToLevelStatParam row 0 names attunement as the stat that
drives it.
Starting classes: PlayerStatusParam rows 20-110 hold each class's starting
level and attributes. Row 10 and the rows from 500 up are not classes.
Level-up cost: PlayerLevelUpSoulsParam row N is the soul cost of going from
level N to N + 1 (row 999 is not a level). Rows 0-850 cover every level the
game allows.
Bosses: BossBattleParam has one row per boss fight. killedEventId is the map
event flag the fight sets on a win, onceKilledEventId the global "ever
defeated" event flag, bonfireEventValueId the global event value counting
defeats, and bonfireId the bonfire whose Bonfire Ascetic the fight belongs to.
Some fights have a second row for a variant (multiplayer, first phase) that
repeats or zeroes these ids.
Infusion index n is the value stored in the second byte of an inventory
entry's unk_2. The order is the material order of CustomAttrCostParam, which
lists one infusion stone per index: Palestone, Firedrake, Faintstone,
Boltstone, Darknight, Poison, Bleed, Raw, Magic and Old Mundane Stone.
Items missing from ItemParam are unknown to the regulation and report no
limits.

Field offsets are byte offsets into a row, following the column order of
the Smithbox CSV exports. Unused game-written items carry these durability
values.
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

# Display names by infusion index, 0 being the plain weapon.
INFUSION_NAMES = (
    "Normal",
    "Fire",
    "Magic",
    "Lightning",
    "Dark",
    "Poison",
    "Bleed",
    "Raw",
    "Enchanted",
    "Mundane",
)

# ItemParam
_ITEM_WEAPON_ID = 0x14  # s32
_ITEM_ARMOR_ID = 0x18  # s32
_ITEM_RING_ID = 0x20  # s32
_ITEM_SPELL_ID = 0x24  # s32
_ITEM_MAX_HELD = 0x4A  # u16
# WeaponParam
_WEAPON_REINFORCE_ID = 0x8  # s32
_WEAPON_DURABILITY = 0x28  # f32
# WeaponReinforceParam
_WEAPON_REINFORCE_MAX_LEVEL = 0x48  # s32
_WEAPON_REINFORCE_ATTR_SPEC_ID = 0xE8  # s32
# CustomAttrSpecParam
_ATTR_SPEC_INFUSION_MASK = 0  # s32
# ArmorParam
_ARMOR_REINFORCE_ID = 0x18  # s32
_ARMOR_DURABILITY = 0x38  # f32
# ArmorReinforceParam
_ARMOR_REINFORCE_MAX_LEVEL = 0x60  # s32
# SpellParam
_SPELL_SLOTS_USED = 0xF0  # u8
# One u8 per attunement tier
_SPELL_CASTS_FIRST_TIER = 0xF1
_SPELL_TIER_COUNT = 10
# RingParam
_RING_DURABILITY = 0x4  # f32
# PhysicalStatsPerLevelStatValuesParam
_STATS_ATTUNEMENT_SLOTS = 0x2  # u8
# PlayerStatusParam, all u16. The attribute order differs from the profile's:
# attunement comes before vitality.
_CLASS_LEVEL = 0x4
_CLASS_STATS = {
    "vigor": 0x6,
    "endurance": 0xC,
    "attunement": 0xE,
    "vitality": 0x10,
    "strength": 0x12,
    "dexterity": 0x14,
    "intelligence": 0x16,
    "faith": 0x18,
    "adaptability": 0x1A,
}
_CLASS_ROWS = range(20, 111, 10)
# PlayerLevelUpSoulsParam
_LEVEL_UP_SOULS = 0x8  # s32
_LEVEL_UP_MAX_ROW = 850
# BossBattleParam, ids stored as u32
_BOSS_KILLED_FLAG = 0x10
_BOSS_ONCE_KILLED_FLAG = 0x14
_BOSS_DEFEAT_VALUE = 0x18
_BOSS_BONFIRE_ID = 0x40  # u16


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
class ClassBase:
    """A starting class's level and attributes."""

    level: int
    stats: dict[str, int]


@dataclass(frozen=True)
class BossFight:
    """Event ids of one boss fight, from its BossBattleParam row."""

    row_id: int
    killed_flag: int
    once_killed_flag: int
    defeat_value: int
    bonfire_id: int


@dataclass(frozen=True)
class _ItemLimits:
    max_held: int
    max_upgrade: int = 0
    durability: float | None = None
    infusion_mask: int = 0
    spell_slots: int = 0


class Regulation:
    """Per-item limits (stack size, upgrade level, durability, infusions)
    resolved from the embedded params."""

    def __init__(
        self,
        items: dict[int, _ItemLimits],
        attunement_slots: dict[int, int],
        class_bases: dict[int, ClassBase],
        level_up_souls: dict[int, int],
        boss_fights: tuple[BossFight, ...] = (),
    ) -> None:
        self._items = items
        self._attunement_slots = attunement_slots
        self._class_bases = class_bases
        self._level_up_souls = level_up_souls
        self._boss_fights = boss_fights

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
        attr_specs = param("CustomAttrSpecParam.param")
        stat_values = param("PhysicalStatsPerLevelStatValuesParam.param")

        items: dict[int, _ItemLimits] = {}
        for item_id in item_param.ids():
            max_held = item_param.u16(item_id, _ITEM_MAX_HELD)
            weapon_id = item_param.s32(item_id, _ITEM_WEAPON_ID)
            armor_id = item_param.s32(item_id, _ITEM_ARMOR_ID)
            ring_id = item_param.s32(item_id, _ITEM_RING_ID)
            spell_id = item_param.s32(item_id, _ITEM_SPELL_ID)

            max_upgrade = 0
            infusion_mask = 0
            durability: float | None = None
            if weapons.has(weapon_id):
                reinforce_id = weapons.s32(weapon_id, _WEAPON_REINFORCE_ID)
                if weapon_reinforce.has(reinforce_id):
                    max_upgrade = weapon_reinforce.s32(
                        reinforce_id, _WEAPON_REINFORCE_MAX_LEVEL
                    )
                    spec_id = weapon_reinforce.s32(
                        reinforce_id, _WEAPON_REINFORCE_ATTR_SPEC_ID
                    )
                    if attr_specs.has(spec_id):
                        infusion_mask = attr_specs.s32(
                            spec_id, _ATTR_SPEC_INFUSION_MASK
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

            spell_slots = 0
            if spells.has(spell_id):
                max_held = max(
                    spells.u8(spell_id, _SPELL_CASTS_FIRST_TIER + tier)
                    for tier in range(_SPELL_TIER_COUNT)
                )
                spell_slots = spells.u8(spell_id, _SPELL_SLOTS_USED)

            items[item_id] = _ItemLimits(
                max_held, max(0, max_upgrade), durability, infusion_mask, spell_slots
            )
        attunement_slots = {
            level: stat_values.u8(level, _STATS_ATTUNEMENT_SLOTS)
            for level in stat_values.ids()
        }
        # Optional: a regulation without them still gives item limits.
        class_bases: dict[int, ClassBase] = {}
        if "PlayerStatusParam.param" in files:
            statuses = param("PlayerStatusParam.param")
            for row_id in _CLASS_ROWS:
                if statuses.has(row_id):
                    class_bases[row_id] = ClassBase(
                        statuses.u16(row_id, _CLASS_LEVEL),
                        {
                            name: statuses.u16(row_id, off)
                            for name, off in _CLASS_STATS.items()
                        },
                    )
        level_up_souls: dict[int, int] = {}
        if "PlayerLevelUpSoulsParam.param" in files:
            costs = param("PlayerLevelUpSoulsParam.param")
            level_up_souls = {
                level: costs.s32(level, _LEVEL_UP_SOULS)
                for level in costs.ids()
                if level <= _LEVEL_UP_MAX_ROW
            }
        boss_fights: list[BossFight] = []
        if "BossBattleParam.param" in files:
            battles = param("BossBattleParam.param")
            seen: set[int] = set()
            for row_id in battles.ids():
                fight = BossFight(
                    row_id,
                    battles.s32(row_id, _BOSS_KILLED_FLAG),
                    battles.s32(row_id, _BOSS_ONCE_KILLED_FLAG),
                    battles.s32(row_id, _BOSS_DEFEAT_VALUE),
                    battles.u16(row_id, _BOSS_BONFIRE_ID),
                )
                # Variant rows either repeat their fight's ids or hold none.
                if fight.once_killed_flag <= 0 or fight.once_killed_flag in seen:
                    continue
                seen.add(fight.once_killed_flag)
                boss_fights.append(fight)
        return cls(
            items, attunement_slots, class_bases, level_up_souls, tuple(boss_fights)
        )

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

    def spell_slots(self, item_id: int) -> int | None:
        """Attunement slots a spell takes, or None for an unknown item."""
        info = self._items.get(item_id)
        return info.spell_slots if info else None

    def attunement_slots(self, attunement: int) -> int | None:
        """Attunement slots at an attunement level, or None for a level
        the regulation has no row for."""
        return self._attunement_slots.get(attunement)

    def class_base(self, row_id: int) -> ClassBase | None:
        """Starting level and attributes of the class in a PlayerStatusParam
        row, or None when the row is not a class."""
        return self._class_bases.get(row_id)

    def level_up_souls(self, from_level: int, to_level: int) -> int | None:
        """Souls the level-ups from from_level to to_level cost, 0 when
        to_level is not higher. None when a level in between has no row."""
        total = 0
        for level in range(from_level, to_level):
            cost = self._level_up_souls.get(level)
            if cost is None:
                return None
            total += cost
        return total

    def boss_fights(self) -> tuple[BossFight, ...]:
        """Every boss fight in BossBattleParam order, one per fight."""
        return self._boss_fights

    def durability(self, item_id: int) -> float | None:
        """Maximum durability of a weapon, armor piece or ring, or None when
        the item has none or is unknown."""
        info = self._items.get(item_id)
        return info.durability if info else None

    def allowed_infusions(self, item_id: int) -> tuple[int, ...]:
        """Infusion indices a weapon can take, always including 0. Only 0 for
        items that cannot be infused or are absent from the regulation."""
        info = self._items.get(item_id)
        mask = info.infusion_mask if info else 0
        return tuple(n for n in range(len(INFUSION_NAMES)) if n == 0 or mask >> n & 1)
