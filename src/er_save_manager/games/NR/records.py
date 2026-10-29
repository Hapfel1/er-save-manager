"""
Nightreign battle records (Visual Codex > Battle Record pages).

All records are per character slot. Positions derive from the end of the
relic loadout chunk (E = loadout.offset + 8 + chunk_size); the bytes between
E and the records block, and between the block and the tables, are not
decoded.

Records block at E + 0x35 (u32 unless noted):
  0x00  expedition time (ms)
  0x04  total expeditions
  0x08  wins
  0x0C  current win streak            0x10  win streak (best, shown)
  0x14  current win streak (Depths)   0x18  win streak (Depths, best, shown)
  0x1C  ending reached
  0x20  greatest Depth conquered: depth level
  0x24  greatest Depth conquered: score
  0x44  battle record, normal expeditions (0xA0 bytes)
  0xE4  battle record, Depths (0xA0 bytes, same layout)

Battle record block (PB = personal best of one expedition):
  0x04 enemies felled        0x08 great enemies felled  0x0C chests opened
  0x14 PB enemies felled     0x18 PB great enemies      0x1C PB chests opened
  0x24 shifting earth        0x28 raid events           0x2C PB greatest attack
  0x30 PB runes acquired     0x34 PB runes used         0x38 rescues performed
  0x3C PB rescues            0x40 effects & powers      0x44 PB special effects
  0x48 armaments discovered  0x4C PB runes lost         0x50 enemies (variants)
  0x54 PB enemies (variants) 0x5C runes used            0x64 runes acquired
  0x6C murk acquired         0x74 sovereign sigils acquired
  The last four are followed by a u32 that is always 0 (likely the high half
  of a u64); only the low u32 is read and written.

Nightfarer table at E + 0x1CC09: u32 count, then count 12-byte entries
  {u8 hero id (1-based), 3 bytes not decoded, u32 expeditions, u32 wins}.
  Modded saves can hold more than the 10 vanilla heroes.

Nightlord table at Nightfarer table + 0x11BC (fixed, also with modded hero
  counts): u32 count, u32 not decoded, then count 12-byte entries
  {u32 wins, u32 not decoded, u32 index}.

Totals as the game keeps them: sum of Nightfarer expeditions = total
expeditions; sum of Nightfarer wins = sum of Nightlord wins = wins.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from .parser import HERO_NAMES, NightreignSlot

_RECORDS_REL = 0x35  # records block, from the loadout chunk end
_NORMAL_BLOCK = 0x44
_DEPTHS_BLOCK = 0xE4
_NIGHTFARER_REL = 0x1CC09  # Nightfarer table, from the loadout chunk end
_NIGHTLORD_REL = 0x11BC  # Nightlord table, from the Nightfarer table
_TABLE_ENTRY = 12
_MAX_TABLE_COUNT = 64

U32_MAX = 0xFFFFFFFF

# Stored Nightlord order; the game lists Heolstor last.
NIGHTLORD_NAMES = [
    "Gladius",
    "Adel",
    "Gnoster",
    "Maris",
    "Libra",
    "Fulghor",
    "Caligo",
    "Heolstor the Nightlord",
    "Harmonia",
    "Straghess",
]


@dataclass(frozen=True)
class RecordField:
    key: str
    label: str
    rel: int  # offset from the records block
    is_time: bool = False  # milliseconds, shown as H:MM:SS


def _block(prefix: str, base: int, fields: list[tuple[str, str, int]]):
    return [RecordField(f"{prefix}_{k}", label, base + rel) for k, label, rel in fields]


SUMMARY_FIELDS = [
    RecordField("expedition_time", "Expedition time", 0x00, is_time=True),
    RecordField("total_expeditions", "Total expeditions", 0x04),
    RecordField("wins", "Wins", 0x08),
    RecordField("win_streak", "Win streak", 0x10),
    RecordField("win_streak_depths", "Win streak (Depths)", 0x18),
    RecordField("current_streak", "Current win streak", 0x0C),
    RecordField("current_streak_depths", "Current win streak (Depths)", 0x14),
]

# (key, label, offset in the battle record block)
_ALL = [
    ("shifting_earth", "Encounters with shifting earth", 0x24),
    ("raids", "Raid events completed", 0x28),
    ("runes_acquired", "Runes acquired", 0x64),
    ("runes_used", "Runes used", 0x5C),
    ("murk", "Murk acquired", 0x6C),
    ("sigils", "Sovereign Sigils acquired", 0x74),
    ("armaments", "Armaments discovered", 0x48),
    ("effects", "Effects & powers gained", 0x40),
    ("enemies", "Enemies felled", 0x04),
    ("great_enemies", "Great enemies felled", 0x08),
    ("chests", "Chests opened", 0x0C),
    ("rescues", "Rescues performed", 0x38),
]
_VARIANTS = [("variants", "Enemies felled (variants)", 0x50)]
_BEST = [
    ("pb_attack", "Greatest attack", 0x2C),
    ("pb_runes_acquired", "Runes acquired", 0x30),
    ("pb_runes_used", "Runes used", 0x34),
    ("pb_runes_lost", "Runes lost", 0x4C),
    ("pb_effects", "Special effects obtained", 0x44),
    ("pb_enemies", "Enemies felled", 0x14),
    ("pb_great_enemies", "Great enemies felled", 0x18),
    ("pb_chests", "Chests opened", 0x1C),
    ("pb_rescues", "Rescues performed", 0x3C),
]
_BEST_VARIANTS = [("pb_variants", "Enemies felled (variants)", 0x54)]

NORMAL_ALL = [RecordField("ending", "Ending reached", 0x1C)] + _block(
    "normal", _NORMAL_BLOCK, _ALL
)
NORMAL_BEST = _block("normal", _NORMAL_BLOCK, _BEST)
DEPTHS_ALL = _block("depths", _DEPTHS_BLOCK, _ALL + _VARIANTS)
DEPTHS_BEST = [
    RecordField("depth_level", "Greatest Depth conquered: level", 0x20),
    RecordField("depth_score", "Greatest Depth conquered: score", 0x24),
] + _block("depths", _DEPTHS_BLOCK, _BEST + _BEST_VARIANTS)

ALL_FIELDS = SUMMARY_FIELDS + NORMAL_ALL + NORMAL_BEST + DEPTHS_ALL + DEPTHS_BEST


@dataclass
class NightfarerRecord:
    hero_id: int
    expeditions: int
    wins: int
    offset: int  # absolute offset of the expeditions field

    @property
    def name(self) -> str:
        if 1 <= self.hero_id <= len(HERO_NAMES):
            return HERO_NAMES[self.hero_id - 1]
        return f"Hero {self.hero_id}"


@dataclass
class NightlordRecord:
    index: int  # position in the stored table
    wins: int
    offset: int  # absolute offset of the wins field

    @property
    def name(self) -> str:
        if self.index < len(NIGHTLORD_NAMES):
            return NIGHTLORD_NAMES[self.index]
        return f"Nightlord {self.index + 1}"


@dataclass
class SlotRecords:
    """Records of one slot; values maps RecordField.key to its value."""

    base: int  # absolute offset of the records block
    values: dict[str, int] = field(default_factory=dict)
    nightfarers: list[NightfarerRecord] = field(default_factory=list)
    nightlords: list[NightlordRecord] = field(default_factory=list)


def _u32(dec: bytearray, off: int) -> int:
    return struct.unpack_from("<I", dec, off)[0]


def _read_table_count(dec: bytearray, off: int) -> int:
    """Entry count at off, or 0 when it is out of range or overruns dec."""
    if off + 4 > len(dec):
        return 0
    count = _u32(dec, off)
    if not 0 < count <= _MAX_TABLE_COUNT:
        return 0
    return count


def _read_nightfarers(dec: bytearray, table: int) -> list[NightfarerRecord]:
    count = _read_table_count(dec, table)
    if not count or table + 4 + count * _TABLE_ENTRY > len(dec):
        return []
    out = []
    for i in range(count):
        entry = table + 4 + i * _TABLE_ENTRY
        if dec[entry] != i + 1:
            return []  # hero ids are stored 1..count; anything else is not the table
        out.append(
            NightfarerRecord(
                hero_id=dec[entry],
                expeditions=_u32(dec, entry + 4),
                wins=_u32(dec, entry + 8),
                offset=entry + 4,
            )
        )
    return out


def _read_nightlords(dec: bytearray, table: int) -> list[NightlordRecord]:
    count = _read_table_count(dec, table)
    entries = table + 8
    if not count or entries + count * _TABLE_ENTRY > len(dec):
        return []
    return [
        NightlordRecord(
            index=i,
            wins=_u32(dec, entries + i * _TABLE_ENTRY),
            offset=entries + i * _TABLE_ENTRY,
        )
        for i in range(count)
    ]


def read_records(slot: NightreignSlot) -> SlotRecords | None:
    """Records of a slot, or None for a slot without a parsed loadout chunk."""
    if slot.loadout is None:
        return None
    dec = slot.decrypted
    end = slot.loadout.offset + 8 + slot.loadout.chunk_size
    base = end + _RECORDS_REL
    if base + max(f.rel for f in ALL_FIELDS) + 4 > len(dec):
        return None
    rec = SlotRecords(base=base)
    for f in ALL_FIELDS:
        rec.values[f.key] = _u32(dec, base + f.rel)
    farers = end + _NIGHTFARER_REL
    rec.nightfarers = _read_nightfarers(dec, farers)
    if rec.nightfarers:
        rec.nightlords = _read_nightlords(dec, farers + _NIGHTLORD_REL)
    return rec


def write_records(
    slot: NightreignSlot,
    rec: SlotRecords,
    values: dict[str, int],
    nightfarers: list[tuple[int, int]],
    nightlords: list[int],
) -> None:
    """Write values (RecordField.key -> value), Nightfarer (expeditions, wins)
    pairs and Nightlord wins in table order into the slot."""
    dec = slot.decrypted
    rels = {f.key: f.rel for f in ALL_FIELDS}
    for key, value in values.items():
        struct.pack_into("<I", dec, rec.base + rels[key], value)
    for farer, (expeditions, wins) in zip(rec.nightfarers, nightfarers, strict=True):
        struct.pack_into("<II", dec, farer.offset, expeditions, wins)
    for lord, wins in zip(rec.nightlords, nightlords, strict=True):
        struct.pack_into("<I", dec, lord.offset, wins)
