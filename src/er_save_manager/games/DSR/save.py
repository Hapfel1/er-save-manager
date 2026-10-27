"""
Dark Souls Remastered Save File Parser

File format: BND4 container with 11 AES-CBC encrypted slots.

=== FILE LAYOUT ===

Offset       Size        Description
0x0000       4           Magic: "BND4"
0x0004       8           Unknown header fields
0x000C       4           File count: always 11 (u32 LE)
0x0010       8           Header size: 0x40 (u64 LE)
0x0018       16          Version string (zero-padded ASCII)
0x0028       8           Combined header+entries size: 0x2C0 (u64 LE)
0x0040       11 * 0x20   BND4 file entry table (see below)
0x01A0       variable    UTF-16LE file name strings (USER_DATA000..USER_DATA010)
0x02C0       11 * 0x060030   Encrypted character slots

=== BND4 FILE ENTRY (0x20 bytes each, starting at 0x0040) ===

+0x00  u32   Flags: 0x50
+0x04  u32   Unknown: 0xFFFFFFFF
+0x08  u64   Slot size: 0x060030
+0x10  u64   Slot absolute offset in file (0x2C0, 0x602F0, ...)
+0x18  u64   Name string offset (within file, pointing into 0x01A0 area)

=== SLOT LAYOUT (0x060030 bytes each) ===

+0x00  16    IV / integrity checksum: MD5 of the encrypted payload
+0x10  0x060020    AES-128-CBC encrypted character data (see below)

The IV doubles as an integrity check: md5(ciphertext) must equal the stored IV.
When writing, re-encrypt with the existing IV and store md5(new_ciphertext) as the new IV.

AES key (16 bytes, fixed for all DSR saves):
  01 23 45 67 89 AB CD EF  FE DC BA 98 76 54 32 10

=== DECRYPTED SLOT DATA (0x060020 bytes) ===

Slots 0-9 hold character data. Slot 10 is system/profile data.
An empty character slot has bytes 0x20-0x90 all zero.

+0x0000  16   State hash / unknown header
+0x0010  4    Unknown (save format version?)
+0x0014  4    Unknown
+0x0018  8    Unknown
+0x0020  ...  First non-zero region for occupancy check (through 0x0090)

--- Play time ---
+0x001C  4    Play time in milliseconds (u32 LE)

--- HP / Stamina ---
+0x0074  4    Current HP (u32 LE)
+0x0078  4    Max HP including equipment bonuses (u32 LE)
+0x007C  4    Base max HP from Vitality (u32 LE)
+0x0090  4    Current stamina (u32 LE)
+0x0094  4    Max stamina including equipment bonuses (u32 LE)
+0x0098  4    Base max stamina from Endurance (u32 LE)

--- Base stats (each stored as u8 at 8-byte-aligned offsets) ---
+0x00A0  1    Vitality
+0x00A8  1    Attunement
+0x00B0  1    Endurance
+0x00B8  1    Strength
+0x00C0  1    Dexterity
+0x00C8  1    Intelligence
+0x00D0  1    Faith
+0x00E8  1    Resistance

--- Resources ---
+0x00E4  1    Humanity (u8)
+0x00F0  2    Level (u16 LE)
+0x00F4  4    Souls (u32 LE)

--- Character info ---
+0x0108  34   Name, primary copy (UTF-16LE, 16 chars + null terminator)
+0x012A  1    Body type: 0=Type B (female), 1=Type A (male)
+0x012E  1    Starting class (see DSRClass enum)
+0x012F  1    Physique
+0x0130  1    Starting gift
+0x014D  7    Covenant offering counts (u8 each): Warrior of Sunlight,
              Darkwraith, Path of the Dragon, Gravelord Servant, Forest
              Hunter, Darkmoon Blade, Chaos Servant. Rank 1/2/3 at
              COVENANT_RANK_COUNTS offerings.
+0x0173  1    Covenant (see DSRCovenant enum)
+0x0174  1    Face type
+0x0175  1    Hair type
+0x0176  1    Hair and eye color preset
+0x0179  1    Highest weapon upgrade level (used for matchmaking, must be calibrated)
+0x018C  34   Name, secondary copy (UTF-16LE, 16 chars + null terminator)

--- Equipment: slot indices into the inventory array ---
20 u32 LE inventory slot indices, 0xFFFFFFFF = nothing equipped:
+0x02A8  4    Left hand slot 1
+0x02AC  4    Right hand slot 1
+0x02B0  4    Left hand slot 2
+0x02B4  4    Right hand slot 2
+0x02B8  16   Ammo slots (4; arrow/bolt order unconfirmed)
+0x02C8  4    Helm slot
+0x02CC  4    Chest armor slot
+0x02D0  4    Gauntlets slot
+0x02D4  4    Leg armor slot
+0x02D8  4    Hair slot (always 0xFFFFFFFF)
+0x02DC  4    Ring slot 1
+0x02E0  4    Ring slot 2
+0x02E4  20   Quick item slots 1-5
An empty hand slot points at a bare hand entry (weapon 900000), an empty
armor slot at a bare armor entry (armor 900000 + 1000 * piece).

--- Equipment: cached item IDs, one per slot above ---
+0x0314  4    Left hand 1 item ID
+0x0318  4    Right hand 1 item ID
+0x031C  4    Left hand 2 item ID
+0x0320  4    Right hand 2 item ID
+0x0324  16   Ammo item IDs
+0x0334  4    Helm item ID
+0x0338  4    Chest armor item ID
+0x033C  4    Gauntlets item ID
+0x0340  4    Leg armor item ID
+0x0344  4    Hair item ID (set although the hair slot is empty)
+0x0348  4    Ring 1 item ID
+0x034C  4    Ring 2 item ID
+0x0350  20   Quick item IDs 1-5
The character-select directory keeps a copy of the 20 item IDs.

--- Inventory ---
+0x0370  2048 * 28   Item array (2048 slots, 28 bytes each; see item layout below)
+0xE370  4           Highest used inventory slot index (u32 LE)

Key items occupy slots 0-63; weapons, armor, rings, consumables use slots 64-2047.

--- Appearance (after the inventory) ---
+0xE414  16   Hair color RGBA (4 x f32, menu value / 255)
+0xE424  16   Eye color RGBA (4 x f32, menu value / 255)
+0xE434  100  Face data: 50 FaceGen geometry + 50 texture coefficients, u8,
              128 = mean face (FaceGenParam faceGeoData / faceTexData)

Physique 0-8, face type 0-9 (FaceGenParam row 1000 + n for Type A, 2000 + n
for Type B), hair type 0-9, hair and eye color preset 0-9
(MenuColorTableParam 36901 + n).

=== INVENTORY ITEM (28 bytes) ===

+0x00  4   Item type/category, big-endian u32 divided by 16:
              0 = Weapon / Shield
              1 = Unknown
              2 = Ring
              4 = Consumable / Ammunition / Spell / Key / Material
+0x04  4   Item ID (u32 LE)
           For weapons: base_id + infusion*100 + upgrade_level
           Infusions: 0=Standard, 1=Crystal, 2=Lightning, 3=Raw, 4=Magic,
                      5=Enchanted, 6=Divine, 7=Occult, 8=Fire, 9=Chaos
+0x08  4   Stack quantity (u32 LE)
+0x0C  4   Order: (sort key << 12) | slot (see ORDER_SORT_SHIFT)
+0x10  4   Exists flag: 1=occupied, 0 or 0xFFFFFFFF=empty (u32 LE)
+0x14  4   Durability (u32 LE); Crystal infusion = base_durability / 10
+0x18  4   Unknown (u32 LE)

An empty slot has all bytes 0x00 or all 0xFF.

=== EVENT FLAGS AND NG+ ===

The event flag array follows variable-length data; see FLAG_RECORD for how
it is found and how flag ids map to bits. The NG+ cycle (u32, 0 = NG) sits
NG_CYCLE_FROM_FLAGS bytes before the flag array, followed by a u32 holding
the ending that started it (0 none, 1 Link the Fire, 2 Dark Lord).

=== CHR BLOCK ===

After the flag array: u32 size, magic " RHC", u32 version, then one record
per map the character has loaded: u32 key (area << 24 | block << 16), u32
record size, u32 enemy part count, then one bit per enemy part of the map's
MSB in part order (LSB first). A set bit spawns that part dead; the part's
death event then runs again on load. 0xFFFFFFFF ends the records.
"""

from __future__ import annotations

import hashlib
import re
import struct
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

from er_save_manager import aes_cbc
from er_save_manager.own_writes import atomic_write

# --- Constants --------------------------------------------------------------- #

FILE_SIZE = 0x4204D0
SLOT_COUNT = 11  # slots 0-9 are characters; slot 10 is system data
CHARACTER_SLOTS = 10
SLOT_SIZE = 0x060030
SLOT_DATA_SIZE = 0x060020  # encrypted payload per slot
SLOTS_OFFSET = 0x02C0  # first slot starts here

AES_KEY = bytes(
    [
        0x01,
        0x23,
        0x45,
        0x67,
        0x89,
        0xAB,
        0xCD,
        0xEF,
        0xFE,
        0xDC,
        0xBA,
        0x98,
        0x76,
        0x54,
        0x32,
        0x10,
    ]
)

# Decrypted slot data offsets
OFF_STATE_HASH = 0x0000
OFF_PLAY_MS = 0x001C  # u32 LE, milliseconds
OFF_HP_CURRENT = 0x0074  # u32 LE
OFF_HP_MAX = 0x0078  # u32 LE, with equipment bonuses
OFF_HP_BASE = 0x007C  # u32 LE, from Vitality
OFF_STAMINA = 0x0098  # u32 LE, base max from Endurance
OFF_VIT = 0x00A0  # u8
OFF_ATN = 0x00A8  # u8
OFF_END = 0x00B0  # u8
OFF_STR = 0x00B8  # u8
OFF_DEX = 0x00C0  # u8
OFF_INT = 0x00C8  # u8
OFF_FTH = 0x00D0  # u8
OFF_RES = 0x00E8  # u8
OFF_HUMANITY = 0x00E4  # u8
OFF_LEVEL = 0x00F0  # u16 LE
OFF_SOULS = 0x00F4  # u32 LE
OFF_NAME_PRIMARY = 0x0108  # UTF-16LE, 34 bytes (16 chars + null)
OFF_BODY_TYPE = 0x012A  # u8; 0=Type B (female), 1=Type A (male)
OFF_CLASS = 0x012E  # u8
OFF_PHYSIQUE = 0x012F  # u8
OFF_GIFT = 0x0130  # u8
OFF_COVENANT_OFFERINGS = 0x014D  # 7 x u8, order of COVENANT_OFFERING_ORDER
OFF_COVENANT = 0x0173  # u8
OFF_FACE_TYPE = 0x0174  # u8
OFF_HAIR_TYPE = 0x0175  # u8
OFF_HAIR_EYE_COLOR = 0x0176  # u8
OFF_WEAPON_LEVEL = 0x0179  # u8, highest upgrade, used for matchmaking
OFF_NAME_SECONDARY = 0x018C  # UTF-16LE, 34 bytes (mirror of primary)

# Equipment slot indices (u32 LE each; 0xFFFFFFFF = empty)
OFF_EQ_LH1 = 0x02A8
OFF_EQ_RH1 = 0x02AC
OFF_EQ_LH2 = 0x02B0
OFF_EQ_RH2 = 0x02B4
OFF_EQ_HELM = 0x02C8
OFF_EQ_CHEST = 0x02CC
OFF_EQ_GAUNTLETS = 0x02D0
OFF_EQ_LEGS = 0x02D4
OFF_EQ_RING1 = 0x02DC
OFF_EQ_RING2 = 0x02E0

# Equipment cached item IDs (u32 LE each), paired with their slot fields
# below in _EQUIP_SLOT_ID_PAIRS.
OFF_EQ_ID_LH1 = 0x0314
OFF_EQ_ID_RH1 = 0x0318
OFF_EQ_ID_LH2 = 0x031C
OFF_EQ_ID_RH2 = 0x0320
OFF_EQ_ID_HELM = 0x0334
OFF_EQ_ID_CHEST = 0x0338
OFF_EQ_ID_GAUNTLETS = 0x033C
OFF_EQ_ID_LEGS = 0x0340
# Hair is equipped as a part id: HAIR_ITEM_BASE[body type] + 100 * hairstyle.
OFF_EQ_ID_HAIR = 0x0344
HAIR_ITEM_BASE = {0: 3000, 1: 1000}
OFF_EQ_ID_RING1 = 0x0348
OFF_EQ_ID_RING2 = 0x034C
# All 20 equip slots: index k at OFF_EQ_LH1 + 4 * k, its cached id at
# OFF_EQ_ID_LH1 + 4 * k.
EQUIP_SLOT_COUNT = 20
EQUIP_HANDS = range(4)
EQUIP_AMMO = range(4, 8)
EQUIP_ARMOR = range(8, 12)
EQUIP_HAIR = 12
EQUIP_RINGS = range(13, 15)
EQUIP_QUICK = range(15, 20)
_EQUIP_SLOT_ID_PAIRS = tuple(
    (OFF_EQ_LH1 + 4 * k, OFF_EQ_ID_LH1 + 4 * k) for k in range(EQUIP_SLOT_COUNT)
)
_EQUIP_EMPTY = 0xFFFFFFFF
# Ammo slots: arrows 1, bolts 1, arrows 2, bolts 2.
EQUIP_BOLT_SLOTS = frozenset({5, 7})
# Ammo ids: arrows 20xxxxx, bolts 21xxxxx.
_AMMO_FAMILY_STEP = 100000
_BOLT_FAMILY = 21
# Counts of held entries after the id cache: u32 common items (slots 64+),
# u32 key items (slots 0-63).
OFF_COMMON_COUNT = OFF_EQ_ID_LH1 + 4 * EQUIP_SLOT_COUNT
OFF_KEY_COUNT = OFF_COMMON_COUNT + 4
BARE_HAND_ID = 900000
BARE_ARMOR_BASE = 900000
# Armor ids are family * 10000 + piece * 1000 (+ upgrade): head, chest,
# hands, legs.
ARMOR_PIECE_STEP = 1000

# Inventory
OFF_INVENTORY = 0x0370  # start of item array
OFF_ITEMS_COUNT = 0xE370  # highest used slot index (u32 LE)
ITEM_SIZE = 28
MAX_INVENTORY_SLOTS = 2048
# Inventory entry order field: (sort key << 12) | slot. The sort key is the
# item's sortId, times 100 plus the level for weapons and armor; upgrades and
# infusions done in game keep the key the item was picked up with.
ORDER_SORT_SHIFT = 12
# The Ascended Pyromancy Flame is the per-level weapon family capped at +5;
# matchmaking counts it as weapon level 15 at any level.
ASCENDED_FLAME_CAP = 5
KEY_ITEM_SLOTS = 64  # key items occupy slots 0-63

# Attunement after the inventory array: ATTUNE_SLOTS records of (u32 spell
# id, u32 uses), packed from the first, empty (0xFFFFFFFF, 0); then the s32
# index of the selected record, -1 with none. The game sets it to 0 on the
# first attunement. uses = CASTS_PER_USE x the spell's Magic maxQuantity on
# an attuned spell.
OFF_ATTUNED = OFF_ITEMS_COUNT + 4
ATTUNE_SLOTS = 12
_ATTUNE_RECORD = 8
OFF_SELECTED_SPELL = OFF_ATTUNED + ATTUNE_SLOTS * _ATTUNE_RECORD
CASTS_PER_USE = 3

# Appearance block after the inventory array.
OFF_HAIR_RGBA = 0xE414  # 4 x f32
OFF_EYE_RGBA = 0xE424  # 4 x f32
OFF_FACE_DATA = 0xE434
FACE_DATA_SIZE = 100

# Slot occupancy check range: all-zero bytes here means empty character
EMPTY_CHECK_START = 0x0020
EMPTY_CHECK_END = 0x0090

# The flag record search starts here; everything before it is fixed layout.
FLAG_SEARCH_START = 0x1E5BE
# NG+ cycle (u32): this many bytes before the flag array.
NG_CYCLE_FROM_FLAGS = 0xC13

# Event flags: the game's flag array, stored after a variable-length run of
# records, so its offset differs per character. It starts FLAG_RECORD_TO_BASE bytes after the
# one record matching FLAG_RECORD (FF FF FF FF, a u32 whose top byte is 0,
# then 00 08). Layout as DS1 keeps it in memory: flag id GAAASNNN (group,
# area, section, number) lives at FLAG_GROUPS[G] + area index * 0x500 +
# S * 128 + (N // 32) * 4, a little-endian u32 with flag N % 32 = 0 in the
# top bit. The item pickup group's set bits are item lot flags.
FLAG_RECORD = re.compile(rb"\xff\xff\xff\xff[\x00-\xff]{3}\x00\x00\x08")
FLAG_RECORD_TO_BASE = 0xD
FLAG_SEARCH_SPAN = 0x2000
FLAG_GROUPS = {0: 0x00000, 1: 0x00500, 5: 0x05F00, 6: 0x0B900, 7: 0x11300}
FLAG_AREAS = {
    0: 0, 100: 1, 101: 2, 102: 3, 110: 4, 120: 5, 121: 6, 130: 7, 131: 8,
    132: 9, 140: 10, 141: 11, 150: 12, 151: 13, 160: 14, 170: 15, 180: 16,
    181: 17,
}  # fmt: skip
FLAG_AREA_SIZE = 0x500

CHR_MAGIC = b" RHC"
CHR_RECORDS_FROM_MAGIC = 8  # magic, u32 version
CHR_RECORD_HEADER = 12  # key, size, part count
CHR_END = 0xFFFFFFFF

# Bonfire state lives in the per-map object records of each visited map, not
# in the event flags: a 20-byte record u32 BONFIRE_RECORD_TYPE, u32 bonfire
# entity id, u32 kindle value (0 unlit, 10 lit, 20/30/40 kindled), then state
# bytes. A character has one record per bonfire of each map it visited.
BONFIRE_RECORD_TYPE = 0x0B
BONFIRE_LEVEL_OFFSET = 8
BONFIRE_LIT_LEVEL = 10
FLAG_SECTION_SIZE = 128

# Starting stats per class: (base_level, vit, atn, end, str, dex, int, fth, res)
# from CharaInitParam rows 2000-2009 (soulLv, baseVit, baseWil, baseEnd,
# baseStr, baseDex, baseMag, baseFai, baseDurability). Used to recalculate
# total level when individual stats are edited.
_CLASS_BASE_STATS: dict[int, tuple[int, ...]] = {
    0: (4, 11, 8, 12, 13, 13, 9, 9, 11),  # Warrior
    1: (5, 14, 10, 10, 11, 11, 9, 11, 10),  # Knight
    2: (3, 10, 11, 10, 10, 14, 11, 8, 12),  # Wanderer
    3: (5, 9, 11, 9, 9, 15, 12, 11, 10),  # Thief
    4: (4, 12, 8, 14, 14, 9, 8, 10, 11),  # Bandit
    5: (4, 11, 9, 11, 12, 14, 9, 9, 11),  # Hunter
    6: (3, 8, 15, 8, 9, 11, 15, 8, 8),  # Sorcerer
    7: (1, 10, 12, 11, 12, 9, 10, 8, 12),  # Pyromancer
    8: (2, 11, 11, 9, 12, 8, 8, 14, 11),  # Cleric
    9: (6, 11, 11, 11, 11, 11, 11, 11, 11),  # Deprived
}
STAT_KEYS = ("vit", "atn", "end", "str", "dex", "int", "fth", "res")
MAX_STAT = 99
MAX_SOULS = 999_999_999
MAX_HUMANITY = 99
NAME_MAX_CHARS = 13  # longest name the character creation screen accepts


def class_base_stats(player_class: int) -> dict[str, int] | None:
    """Starting attributes of a class by stat key, or None if unknown."""
    base = _CLASS_BASE_STATS.get(int(player_class))
    return dict(zip(STAT_KEYS, base[1:], strict=True)) if base else None


def calc_level_from_stats(
    player_class: int,
    vit: int,
    atn: int,
    end: int,
    str_: int,
    dex: int,
    int_: int,
    fth: int,
    res: int,
) -> int:
    """
    Compute total SL from current stats and starting class.
    SL = class_base_level + sum(current_stats) - sum(class_base_stats)
    """
    base = _CLASS_BASE_STATS.get(player_class, _CLASS_BASE_STATS[9])
    base_level, *base_stats = base
    current_sum = vit + atn + end + str_ + dex + int_ + fth + res
    base_sum = sum(base_stats)
    return base_level + (current_sum - base_sum)


# VIT -> max HP lookup
VIT_TO_HP: dict[int, int] = {
    1: 400,
    2: 415,
    3: 433,
    4: 451,
    5: 471,
    6: 490,
    7: 511,
    8: 531,
    9: 552,
    10: 573,
    11: 594,
    12: 616,
    13: 638,
    14: 659,
    15: 682,
    16: 698,
    17: 719,
    18: 742,
    19: 767,
    20: 793,
    21: 821,
    22: 849,
    23: 878,
    24: 908,
    25: 938,
    26: 970,
    27: 1001,
    28: 1034,
    29: 1066,
    30: 1100,
    31: 1123,
    32: 1147,
    33: 1170,
    34: 1193,
    35: 1216,
    36: 1239,
    37: 1261,
    38: 1283,
    39: 1304,
    40: 1325,
    41: 1346,
    42: 1366,
    43: 1386,
    44: 1405,
    45: 1424,
    46: 1442,
    47: 1458,
    48: 1474,
    49: 1489,
    50: 1500,
    51: 1508,
    52: 1517,
    53: 1526,
    54: 1535,
    55: 1544,
    56: 1553,
    57: 1562,
    58: 1571,
    59: 1580,
    60: 1588,
    61: 1597,
    62: 1606,
    63: 1615,
    64: 1623,
    65: 1632,
    66: 1641,
    67: 1649,
    68: 1658,
    69: 1666,
    70: 1675,
    71: 1683,
    72: 1692,
    73: 1700,
    74: 1709,
    75: 1717,
    76: 1725,
    77: 1734,
    78: 1742,
    79: 1750,
    80: 1758,
    81: 1767,
    82: 1775,
    83: 1783,
    84: 1791,
    85: 1799,
    86: 1807,
    87: 1814,
    88: 1822,
    89: 1830,
    90: 1837,
    91: 1845,
    92: 1852,
    93: 1860,
    94: 1867,
    95: 1874,
    96: 1881,
    97: 1888,
    98: 1894,
    99: 1900,
}

# END -> max stamina lookup
END_TO_STAMINA: dict[int, int] = {
    1: 80,
    2: 81,
    3: 82,
    4: 83,
    5: 84,
    6: 86,
    7: 87,
    8: 88,
    9: 90,
    10: 91,
    11: 93,
    12: 95,
    13: 97,
    14: 98,
    15: 100,
    16: 102,
    17: 104,
    18: 106,
    19: 108,
    20: 110,
    21: 112,
    22: 115,
    23: 117,
    24: 119,
    25: 121,
    26: 124,
    27: 126,
    28: 129,
    29: 131,
    30: 133,
    31: 136,
    32: 139,
    33: 141,
    34: 144,
    35: 146,
    36: 149,
    37: 152,
    38: 154,
    39: 157,
    **dict.fromkeys(range(40, 100), 160),
}


# --- Enums ------------------------------------------------------------------- #


class DSRClass(IntEnum):
    Warrior = 0
    Knight = 1
    Wanderer = 2
    Thief = 3
    Bandit = 4
    Hunter = 5
    Sorcerer = 6
    Pyromancer = 7
    Cleric = 8
    Deprived = 9


class DSRCovenant(IntEnum):
    None_ = 0
    WayOfWhite = 1
    PrincessGuard = 2
    WarriorOfSunlight = 3
    Darkwraith = 4
    PathOfTheDragon = 5
    GravelordServant = 6
    ForestHunter = 7
    DarkmoonBlade = 8
    ChaosServant = 9


# Covenants with an offering count, in save order. The count is what the
# covenant's talk script compares against COVENANT_RANK_COUNTS. Forest Hunter
# has a count but no rank check.
COVENANT_OFFERING_ORDER = (
    DSRCovenant.WarriorOfSunlight,
    DSRCovenant.Darkwraith,
    DSRCovenant.PathOfTheDragon,
    DSRCovenant.GravelordServant,
    DSRCovenant.ForestHunter,
    DSRCovenant.DarkmoonBlade,
    DSRCovenant.ChaosServant,
)
COVENANT_RANK_COUNTS = (10, 30, 80)
MAX_COVENANT_OFFERINGS = 0xFF


def covenant_rank(count: int) -> int:
    """Covenant rank (0-3) for an offering count."""
    return sum(count >= need for need in COVENANT_RANK_COUNTS)


class DSRItemCategory(IntEnum):
    WeaponShield = 0
    Unknown1 = 1
    Ring = 2
    Consumable = 4  # covers consumables, ammo, spells, key items, materials


class DSRInfusion(IntEnum):
    Standard = 0
    Crystal = 1
    Lightning = 2
    Raw = 3
    Magic = 4
    Enchanted = 5
    Divine = 6
    Occult = 7
    Fire = 8
    Chaos = 9


# --- Crypto helpers ---------------------------------------------------------- #


def _decrypt(iv: bytes, ciphertext: bytes) -> bytes:
    return aes_cbc.decrypt(AES_KEY, iv, ciphertext)


def _encrypt(iv: bytes, plaintext: bytes) -> bytes:
    return aes_cbc.encrypt(AES_KEY, iv, plaintext)


def _md5(data: bytes) -> bytes:
    return hashlib.md5(data).digest()


# --- Inventory item ---------------------------------------------------------- #


@dataclass
class DSRItem:
    """
    Single inventory slot entry (28 bytes).
    category: raw big-endian u32 / 16, maps to DSRItemCategory.
    item_id: encodes base item, infusion, and upgrade level for weapons.
    """

    category: int = 0
    item_id: int = 0
    quantity: int = 0
    order: int = 0
    exists: int = 0
    durability: int = 0
    unknown: int = 0

    slot_index: int = field(default=0, compare=False, repr=False)

    @classmethod
    def from_bytes(cls, data: bytes, slot_index: int) -> DSRItem:
        # category stored BE /16; all others LE
        raw_type = struct.unpack_from(">I", data, 0)[0]
        category, item_id, quantity, order, exists, durability, unknown = (
            struct.unpack_from(
                "<IIIIIII", bytes([0, 0, 0, raw_type & 0xFF]) + data[4:28]
            )
        )
        # simpler:
        category = raw_type // 16
        item_id = struct.unpack_from("<I", data, 4)[0]
        quantity = struct.unpack_from("<I", data, 8)[0]
        order = struct.unpack_from("<I", data, 12)[0]
        exists = struct.unpack_from("<I", data, 16)[0]
        durability = struct.unpack_from("<I", data, 20)[0]
        unknown = struct.unpack_from("<I", data, 24)[0]
        return cls(
            category, item_id, quantity, order, exists, durability, unknown, slot_index
        )

    def to_bytes(self) -> bytes:
        raw_type = self.category * 16
        out = bytearray(ITEM_SIZE)
        struct.pack_into(">I", out, 0, raw_type)
        struct.pack_into("<I", out, 4, self.item_id)
        struct.pack_into("<I", out, 8, self.quantity)
        struct.pack_into("<I", out, 12, self.order)
        struct.pack_into("<I", out, 16, self.exists)
        struct.pack_into("<I", out, 20, self.durability)
        struct.pack_into("<I", out, 24, self.unknown)
        return bytes(out)

    @property
    def is_empty(self) -> bool:
        return self.exists == 0 or all(b in (0x00, 0xFF) for b in self.to_bytes())

    # --- Weapon ID decomposition ---

    @property
    def base_item_id(self) -> int:
        """Item ID with infusion and upgrade stripped."""
        if self.category not in (DSRItemCategory.WeaponShield, 1):
            return self.item_id
        # Pyromancy Flame and Ascended share a special range
        if 0x145320 <= self.item_id < 0x145520:
            return 0x145320
        if 0x145520 <= self.item_id <= 0x145700:
            return 0x145520
        # Unique upgrade path (Uchigata / boss weapons): base at 311000
        if 311000 <= self.item_id <= 312705:
            return 311000
        without_upgrade = self.item_id - (self.item_id % 100)
        return without_upgrade - (without_upgrade % 1000)

    @property
    def upgrade_level(self) -> int:
        if self.category not in (DSRItemCategory.WeaponShield, 1):
            return 0
        if 0x145320 <= self.item_id < 0x145520:
            return (self.item_id - 0x145320) // 100
        if 0x145520 <= self.item_id <= 0x145700:
            return (self.item_id - 0x145520) // 100
        if 311000 <= self.item_id <= 312705:
            return self.item_id % 100
        return self.item_id % 100

    @property
    def infusion(self) -> int:
        if self.category != DSRItemCategory.WeaponShield:
            return DSRInfusion.Standard
        if 0x145320 <= self.item_id <= 0x145700:
            return DSRInfusion.Standard
        if 311000 <= self.item_id <= 312705:
            return DSRInfusion.Standard
        without_upgrade = self.item_id - (self.item_id % 100)
        return (without_upgrade % 1000) // 100


# --- Equipment snapshot ------------------------------------------------------ #


@dataclass
class DSREquipment:
    """Equipped item slot indices and their cached item IDs."""

    lh1_slot: int = -1
    lh1_id: int = 0
    rh1_slot: int = -1
    rh1_id: int = 0
    lh2_slot: int = -1
    lh2_id: int = 0
    rh2_slot: int = -1
    rh2_id: int = 0
    helm_slot: int = -1
    helm_id: int = 0
    chest_slot: int = -1
    chest_id: int = 0
    gauntlets_slot: int = -1
    gauntlets_id: int = 0
    legs_slot: int = -1
    legs_id: int = 0
    ring1_slot: int = -1
    ring1_id: int = 0
    ring2_slot: int = -1
    ring2_id: int = 0


# --- Character --------------------------------------------------------------- #


@dataclass
class DSRCharacter:
    """
    Parsed character data from a single decrypted slot.
    All offsets are relative to the decrypted payload start (offset 0).
    """

    # Slot index within the file (0-9)
    slot_index: int = 0

    # Raw decrypted data; all reads/writes go through this buffer
    _data: bytearray = field(default_factory=bytearray, repr=False)
    # Cached flag array offset: -2 = not yet computed, -1 = not found
    _flag_base_cache: int = field(default=-2, init=False, repr=False)

    # --- Character identity ---
    @property
    def is_empty(self) -> bool:
        """Slot has no character if 0x20-0x90 are all zero."""
        return all(b == 0 for b in self._data[EMPTY_CHECK_START : EMPTY_CHECK_END + 1])

    @property
    def name(self) -> str:
        return self._read_utf16(OFF_NAME_PRIMARY, length=34)

    @name.setter
    def name(self, value: str) -> None:
        self._write_utf16(OFF_NAME_PRIMARY, value, length=34)
        self._write_utf16(OFF_NAME_SECONDARY, value, length=34)

    @property
    def body_type(self) -> int:
        return self._data[OFF_BODY_TYPE]

    @body_type.setter
    def body_type(self, value: int) -> None:
        self._data[OFF_BODY_TYPE] = value & 0xFF

    # --- Appearance ---

    @property
    def physique(self) -> int:
        return self._data[OFF_PHYSIQUE]

    @physique.setter
    def physique(self, value: int) -> None:
        self._data[OFF_PHYSIQUE] = value & 0xFF

    @property
    def face_type(self) -> int:
        return self._data[OFF_FACE_TYPE]

    @face_type.setter
    def face_type(self, value: int) -> None:
        self._data[OFF_FACE_TYPE] = value & 0xFF

    @property
    def hair_type(self) -> int:
        return self._data[OFF_HAIR_TYPE]

    @hair_type.setter
    def hair_type(self, value: int) -> None:
        self._data[OFF_HAIR_TYPE] = value & 0xFF

    @property
    def hair_item_id(self) -> int:
        return struct.unpack_from("<I", self._data, OFF_EQ_ID_HAIR)[0]

    @hair_item_id.setter
    def hair_item_id(self, value: int) -> None:
        struct.pack_into("<I", self._data, OFF_EQ_ID_HAIR, value)

    @property
    def color_preset(self) -> int:
        return self._data[OFF_HAIR_EYE_COLOR]

    @color_preset.setter
    def color_preset(self, value: int) -> None:
        self._data[OFF_HAIR_EYE_COLOR] = value & 0xFF

    @property
    def hair_rgba(self) -> tuple[float, float, float, float]:
        return struct.unpack_from("<4f", self._data, OFF_HAIR_RGBA)

    @hair_rgba.setter
    def hair_rgba(self, value: tuple[float, float, float, float]) -> None:
        struct.pack_into("<4f", self._data, OFF_HAIR_RGBA, *value)

    @property
    def eye_rgba(self) -> tuple[float, float, float, float]:
        return struct.unpack_from("<4f", self._data, OFF_EYE_RGBA)

    @eye_rgba.setter
    def eye_rgba(self, value: tuple[float, float, float, float]) -> None:
        struct.pack_into("<4f", self._data, OFF_EYE_RGBA, *value)

    @property
    def face_data(self) -> bytes:
        return bytes(self._data[OFF_FACE_DATA : OFF_FACE_DATA + FACE_DATA_SIZE])

    @face_data.setter
    def face_data(self, value: bytes) -> None:
        if len(value) != FACE_DATA_SIZE:
            raise ValueError(f"Face data must be {FACE_DATA_SIZE} bytes")
        self._data[OFF_FACE_DATA : OFF_FACE_DATA + FACE_DATA_SIZE] = value

    @property
    def player_class(self) -> DSRClass:
        return DSRClass(self._data[OFF_CLASS])

    @player_class.setter
    def player_class(self, value: DSRClass) -> None:
        self._data[OFF_CLASS] = int(value) & 0xFF

    @property
    def covenant(self) -> DSRCovenant:
        return DSRCovenant(self._data[OFF_COVENANT])

    @covenant.setter
    def covenant(self, value: DSRCovenant) -> None:
        self._data[OFF_COVENANT] = int(value) & 0xFF

    def covenant_offerings(self, covenant: DSRCovenant) -> int:
        return self._data[
            OFF_COVENANT_OFFERINGS + COVENANT_OFFERING_ORDER.index(covenant)
        ]

    def set_covenant_offerings(self, covenant: DSRCovenant, count: int) -> None:
        if not 0 <= count <= MAX_COVENANT_OFFERINGS:
            raise ValueError(f"Offering count must be 0-{MAX_COVENANT_OFFERINGS}")
        self._data[OFF_COVENANT_OFFERINGS + COVENANT_OFFERING_ORDER.index(covenant)] = (
            count
        )

    # --- Stats ---

    @property
    def level(self) -> int:
        return struct.unpack_from("<H", self._data, OFF_LEVEL)[0]

    @level.setter
    def level(self, value: int) -> None:
        struct.pack_into("<H", self._data, OFF_LEVEL, value & 0xFFFF)

    @property
    def souls(self) -> int:
        return struct.unpack_from("<I", self._data, OFF_SOULS)[0]

    @souls.setter
    def souls(self, value: int) -> None:
        struct.pack_into("<I", self._data, OFF_SOULS, value & 0xFFFFFFFF)

    @property
    def humanity(self) -> int:
        return self._data[OFF_HUMANITY]

    @humanity.setter
    def humanity(self, value: int) -> None:
        self._data[OFF_HUMANITY] = value & 0xFF

    def get_stat(self, name: str) -> int:
        offset = {
            "vit": OFF_VIT,
            "atn": OFF_ATN,
            "end": OFF_END,
            "str": OFF_STR,
            "dex": OFF_DEX,
            "int": OFF_INT,
            "fth": OFF_FTH,
            "res": OFF_RES,
        }.get(name.lower())
        if offset is None:
            raise ValueError(f"Unknown stat: {name!r}")
        return self._data[offset]

    def set_stat(self, name: str, value: int, update_derived: bool = True) -> None:
        """
        Set a base stat. With update_derived=True, also updates HP/stamina so
        the game doesn't need to recalculate on load (it doesn't).
        """
        offset = {
            "vit": OFF_VIT,
            "atn": OFF_ATN,
            "end": OFF_END,
            "str": OFF_STR,
            "dex": OFF_DEX,
            "int": OFF_INT,
            "fth": OFF_FTH,
            "res": OFF_RES,
        }.get(name.lower())
        if offset is None:
            raise ValueError(f"Unknown stat: {name!r}")
        self._data[offset] = value & 0xFF
        if update_derived:
            if name.lower() == "vit":
                hp = VIT_TO_HP.get(value)
                if hp is not None:
                    self.set_hp(hp)
            elif name.lower() == "end":
                stamina = END_TO_STAMINA.get(value)
                if stamina is not None:
                    struct.pack_into("<I", self._data, OFF_STAMINA, stamina)

    def set_hp(self, value: int) -> None:
        """Set base, max and current HP to the same value (full health). The
        max with equipment bonuses is recalculated by the game on load."""
        for off in (OFF_HP_BASE, OFF_HP_MAX, OFF_HP_CURRENT):
            struct.pack_into("<I", self._data, off, value & 0xFFFFFFFF)

    @property
    def hp_current(self) -> int:
        return struct.unpack_from("<I", self._data, OFF_HP_CURRENT)[0]

    @property
    def hp_max(self) -> int:
        return struct.unpack_from("<I", self._data, OFF_HP_MAX)[0]

    @property
    def weapon_level(self) -> int:
        """Highest weapon upgrade level; must match actual inventory for correct matchmaking."""
        return self._data[OFF_WEAPON_LEVEL]

    @weapon_level.setter
    def weapon_level(self, value: int) -> None:
        self._data[OFF_WEAPON_LEVEL] = value & 0xFF

    # --- Play time ---

    @property
    def play_ms(self) -> int:
        return struct.unpack_from("<I", self._data, OFF_PLAY_MS)[0]

    @property
    def play_seconds(self) -> float:
        return self.play_ms / 1000.0

    # --- NG+ ---

    def _ng_cycle_offset(self) -> int:
        base = self.flag_base()
        if base < 0:
            raise ValueError("Event flag data not found in this character")
        return base - NG_CYCLE_FROM_FLAGS

    @property
    def ng_plus(self) -> int:
        """NG+ cycle (0 = first playthrough), or 0 when the flag data is
        not found."""
        try:
            off = self._ng_cycle_offset()
        except ValueError:
            return 0
        return struct.unpack_from("<I", self._data, off)[0]

    @ng_plus.setter
    def ng_plus(self, value: int) -> None:
        struct.pack_into("<I", self._data, self._ng_cycle_offset(), value)

    @property
    def last_ending(self) -> int:
        """Ending that started the current cycle: 0 none, 1 Link the Fire,
        2 Dark Lord. 0 when the flag data is not found."""
        try:
            off = self._ng_cycle_offset() + 4
        except ValueError:
            return 0
        return struct.unpack_from("<I", self._data, off)[0]

    # --- Inventory ---

    def read_item(self, slot: int) -> DSRItem:
        if not 0 <= slot < MAX_INVENTORY_SLOTS:
            raise IndexError(f"Inventory slot {slot} out of range")
        off = OFF_INVENTORY + slot * ITEM_SIZE
        return DSRItem.from_bytes(bytes(self._data[off : off + ITEM_SIZE]), slot)

    def write_item(self, slot: int, item: DSRItem) -> None:
        if not 0 <= slot < MAX_INVENTORY_SLOTS:
            raise IndexError(f"Inventory slot {slot} out of range")
        off = OFF_INVENTORY + slot * ITEM_SIZE
        self._data[off : off + ITEM_SIZE] = item.to_bytes()

    def iter_items(self) -> list[DSRItem]:
        """Return all non-empty inventory items."""
        return [
            self.read_item(i)
            for i in range(MAX_INVENTORY_SLOTS)
            if not self.read_item(i).is_empty
        ]

    @property
    def max_item_slot(self) -> int:
        """Highest occupied inventory slot index recorded by the game."""
        return struct.unpack_from("<I", self._data, OFF_ITEMS_COUNT)[0]

    def _update_max_item_slot(self, slot: int) -> None:
        if slot > self.max_item_slot:
            struct.pack_into("<I", self._data, OFF_ITEMS_COUNT, slot)

    # --- Equipment ---

    @property
    def equipment(self) -> DSREquipment:
        def slot_at(off: int) -> int:
            v = struct.unpack_from("<I", self._data, off)[0]
            return -1 if v == 0xFFFFFFFF else v

        def id_at(off: int) -> int:
            return struct.unpack_from("<I", self._data, off)[0]

        return DSREquipment(
            lh1_slot=slot_at(OFF_EQ_LH1),
            lh1_id=id_at(OFF_EQ_ID_LH1),
            rh1_slot=slot_at(OFF_EQ_RH1),
            rh1_id=id_at(OFF_EQ_ID_RH1),
            lh2_slot=slot_at(OFF_EQ_LH2),
            lh2_id=id_at(OFF_EQ_ID_LH2),
            rh2_slot=slot_at(OFF_EQ_RH2),
            rh2_id=id_at(OFF_EQ_ID_RH2),
            helm_slot=slot_at(OFF_EQ_HELM),
            helm_id=id_at(OFF_EQ_ID_HELM),
            chest_slot=slot_at(OFF_EQ_CHEST),
            chest_id=id_at(OFF_EQ_ID_CHEST),
            gauntlets_slot=slot_at(OFF_EQ_GAUNTLETS),
            gauntlets_id=id_at(OFF_EQ_ID_GAUNTLETS),
            legs_slot=slot_at(OFF_EQ_LEGS),
            legs_id=id_at(OFF_EQ_ID_LEGS),
            ring1_slot=slot_at(OFF_EQ_RING1),
            ring1_id=id_at(OFF_EQ_ID_RING1),
            ring2_slot=slot_at(OFF_EQ_RING2),
            ring2_id=id_at(OFF_EQ_ID_RING2),
        )

    # --- Weapon level calibration ---

    def calibrate_weapon_level(self) -> int:
        """
        Recalculate and store the highest weapon upgrade level from inventory.
        Returns the computed level.
        """
        max_wl = 0
        for item in self.iter_items():
            if item.category == DSRItemCategory.WeaponShield:
                max_wl = max(max_wl, _weapon_level_from_item(item))
        self.weapon_level = max_wl
        return max_wl

    # --- Internal helpers ---

    def _read_utf16(self, offset: int, length: int) -> str:
        raw = bytes(self._data[offset : offset + length])
        end = 0
        while end < length - 1 and not (raw[end] == 0 and raw[end + 1] == 0):
            end += 2
        return raw[:end].decode("utf-16-le", errors="replace")

    def _write_utf16(self, offset: int, value: str, length: int) -> None:
        self._data[offset : offset + length] = b"\x00" * length
        encoded = value.encode("utf-16-le")
        max_bytes = length - 2  # reserve null terminator
        self._data[offset : offset + min(len(encoded), max_bytes)] = encoded[:max_bytes]

    def get_raw(self) -> bytes:
        return bytes(self._data)

    # --- Inventory write ops ------------------------------------------------- #

    def add_item(
        self,
        item_type: int,
        item_id: int,
        quantity: int = 1,
        *,
        sort_key: int = 0,
        durability: int = 0,
        max_quantity: int = 1,
        key_item: bool = False,
    ) -> int:
        """
        Add an item the way the game stores a pickup. Key items use slots
        0-63, everything else 64-2047. Goods and ammo (max_quantity > 1)
        stack onto an existing entry of the same id, capped at max_quantity.
        The entry's order field is (sort_key << 12) | slot, as the game
        writes it.

        Returns the slot index used, or -1 if the inventory is full.
        """
        quantity = max(1, min(quantity, max_quantity))
        slot_start = 0 if key_item else KEY_ITEM_SLOTS
        slot_end = KEY_ITEM_SLOTS if key_item else MAX_INVENTORY_SLOTS
        free = -1
        for slot_idx in range(slot_start, slot_end):
            existing = self.read_item(slot_idx)
            if existing.is_empty:
                if free < 0:
                    free = slot_idx
                    if max_quantity <= 1:
                        break
                continue
            if (
                max_quantity > 1
                and existing.item_id == item_id
                and existing.category == item_type
            ):
                existing.quantity = min(existing.quantity + quantity, max_quantity)
                self.write_item(slot_idx, existing)
                return slot_idx
        if free < 0:
            return -1
        self.write_item(
            free,
            DSRItem(
                category=item_type,
                item_id=item_id,
                quantity=quantity,
                order=((sort_key << ORDER_SORT_SHIFT) | free) & 0xFFFFFFFF,
                exists=1,
                durability=durability,
                unknown=0,
                slot_index=free,
            ),
        )
        self._update_max_item_slot(free)
        self._bump_count(free, 1)
        return free

    def _bump_count(self, slot: int, step: int) -> None:
        """Keep the common or key item count in step with a slot that was
        filled (+1) or emptied (-1)."""
        off = OFF_KEY_COUNT if slot < KEY_ITEM_SLOTS else OFF_COMMON_COUNT
        count = struct.unpack_from("<I", self._data, off)[0]
        struct.pack_into("<I", self._data, off, max(0, count + step))

    def set_item_id(
        self, slot: int, item_id: int, durability: int | None = None
    ) -> None:
        """Change a held item's id (another upgrade level or infusion of the
        same item), keeping its order field like the game's smithing does.
        An equipment slot holding this entry gets its cached id updated."""
        item = self.read_item(slot)
        item.item_id = item_id
        if durability is not None:
            item.durability = durability
        self.write_item(slot, item)
        for slot_off, id_off in _EQUIP_SLOT_ID_PAIRS:
            if struct.unpack_from("<I", self._data, slot_off)[0] == slot:
                struct.pack_into("<I", self._data, id_off, item_id)

    def repair_unupgradable_levels(self) -> list[int]:
        """Reset weapons that carry an upgrade level their item cannot have
        (catalysts, talismans) to the base id; the game has no row for such
        ids and shows ?WikiName?. Returns the repaired inventory slots."""
        from er_save_manager.games.DSR import catalog

        repaired = []
        for item in self.iter_items():
            if item.category != DSRItemCategory.WeaponShield:
                continue
            if catalog.lookup(item.category, item.item_id) is not None:
                continue
            base_id = item.item_id - item.item_id % catalog.INFUSION_STEP
            hit = catalog.lookup(item.category, base_id)
            if hit is None or hit[0]["max_upgrade"] or hit[0]["id"] != base_id:
                continue
            self.set_item_id(item.slot_index, base_id)
            repaired.append(item.slot_index)
        return repaired

    def equipped_slots(self) -> set[int]:
        """Inventory slots referenced by the equipment slots."""
        return {
            slot
            for slot in (self.equip_slot(k)[0] for k in range(EQUIP_SLOT_COUNT))
            if slot != _EQUIP_EMPTY
        }

    def equip_slot(self, k: int) -> tuple[int, int]:
        """(inventory slot, cached item id) of equip slot k."""
        slot_off, id_off = _EQUIP_SLOT_ID_PAIRS[k]
        return (
            struct.unpack_from("<I", self._data, slot_off)[0],
            struct.unpack_from("<I", self._data, id_off)[0],
        )

    def equipped_ids(self) -> list[int]:
        """Cached item ids of the 20 equip slots, as the directory copy holds
        them."""
        return [self.equip_slot(k)[1] for k in range(EQUIP_SLOT_COUNT)]

    @staticmethod
    def is_bolt(item_id: int) -> bool:
        return item_id // _AMMO_FAMILY_STEP == _BOLT_FAMILY

    def attuned_spells(self) -> list[int]:
        """Spell ids of the attunement records, in order."""
        ids = []
        for k in range(ATTUNE_SLOTS):
            spell_id = struct.unpack_from(
                "<I", self._data, OFF_ATTUNED + k * _ATTUNE_RECORD
            )[0]
            if spell_id != _EQUIP_EMPTY:
                ids.append(spell_id)
        return ids

    def attune(self, spells: list[tuple[int, int]]) -> None:
        """Replace the attunement records with (spell id, Magic maxQuantity)
        pairs, packed from the first record with full casts. The selected
        record stays when it still holds a spell, else moves to the first
        (or -1 with no spells). Raises ValueError for more than ATTUNE_SLOTS
        spells."""
        if len(spells) > ATTUNE_SLOTS:
            raise ValueError(f"At most {ATTUNE_SLOTS} spells can be attuned")
        for k in range(ATTUNE_SLOTS):
            spell_id, casts = (
                (spells[k][0], spells[k][1] * CASTS_PER_USE)
                if k < len(spells)
                else (_EQUIP_EMPTY, 0)
            )
            struct.pack_into(
                "<II", self._data, OFF_ATTUNED + k * _ATTUNE_RECORD, spell_id, casts
            )
        selected = struct.unpack_from("<i", self._data, OFF_SELECTED_SPELL)[0]
        if not spells:
            selected = -1
        elif not 0 <= selected < len(spells):
            selected = 0
        struct.pack_into("<i", self._data, OFF_SELECTED_SPELL, selected)

    def set_equip(self, k: int, slot: int | None) -> None:
        """Point equip slot k at a held inventory slot and cache its item id,
        or empty it (both 0xFFFFFFFF). Hand and armor slots are never empty
        in game: pass a bare hand or bare armor entry instead. Raises
        ValueError for an empty or out of range inventory slot."""
        if not 0 <= k < EQUIP_SLOT_COUNT:
            raise ValueError(f"Equip slot {k} out of range")
        slot_off, id_off = _EQUIP_SLOT_ID_PAIRS[k]
        if slot is None:
            index, item_id = _EQUIP_EMPTY, _EQUIP_EMPTY
        else:
            if not 0 <= slot < MAX_INVENTORY_SLOTS:
                raise ValueError(f"Inventory slot {slot} out of range")
            item = self.read_item(slot)
            if item.is_empty:
                raise ValueError(f"Inventory slot {slot} is empty")
            index, item_id = slot, item.item_id
        struct.pack_into("<I", self._data, slot_off, index)
        struct.pack_into("<I", self._data, id_off, item_id)

    def remove_item(self, slot: int) -> None:
        """
        Clear an inventory slot.
        Fills the entry with 0xFF and sets the exists field to 0,
        matching the format the game uses for empty slots.
        """
        if not 0 <= slot < MAX_INVENTORY_SLOTS:
            raise IndexError(f"Slot {slot} out of range")
        if not self.read_item(slot).is_empty:
            self._bump_count(slot, -1)
        off = OFF_INVENTORY + slot * ITEM_SIZE
        self._data[off : off + ITEM_SIZE] = b"\xff" * ITEM_SIZE
        struct.pack_into("<I", self._data, off + 16, 0)  # exists = 0

    # --- Event flags ----------------------------------------------------- #

    def flag_base(self) -> int:
        """Offset of the flag array (see FLAG_RECORD), or -1 when the record
        is missing or not unique."""
        if self._flag_base_cache == -2:
            data = bytes(self._data)
            hits = [
                m.start()
                for m in FLAG_RECORD.finditer(
                    data, FLAG_SEARCH_START, FLAG_SEARCH_START + FLAG_SEARCH_SPAN
                )
            ]
            self._flag_base_cache = (
                hits[0] + FLAG_RECORD_TO_BASE if len(hits) == 1 else -1
            )
        return self._flag_base_cache

    def _flag_pos(self, flag_id: int) -> tuple[int, int]:
        group, rest = divmod(flag_id, 10_000_000)
        area, rest = divmod(rest, 10_000)
        section, number = divmod(rest, 1000)
        if group not in FLAG_GROUPS or area not in FLAG_AREAS:
            raise ValueError(f"Event flag {flag_id} is outside the known layout")
        base = self.flag_base()
        if base < 0:
            raise ValueError("Event flag data not found in this character")
        word = (
            base
            + FLAG_GROUPS[group]
            + FLAG_AREAS[area] * FLAG_AREA_SIZE
            + section * FLAG_SECTION_SIZE
            + number // 32 * 4
        )
        return word, 0x80000000 >> (number % 32)

    def get_flag(self, flag_id: int) -> bool:
        word, mask = self._flag_pos(flag_id)
        return bool(struct.unpack_from("<I", self._data, word)[0] & mask)

    def set_flag(self, flag_id: int, value: bool) -> None:
        word, mask = self._flag_pos(flag_id)
        current = struct.unpack_from("<I", self._data, word)[0]
        struct.pack_into(
            "<I", self._data, word, current | mask if value else current & ~mask
        )

    # --- Bonfires --------------------------------------------------------- #

    def _bonfire_record(self, entity: int) -> int:
        """Offset of a bonfire's record (see BONFIRE_RECORD_TYPE), or -1 when
        the character has not visited its map."""
        key = struct.pack("<II", BONFIRE_RECORD_TYPE, entity)
        data = bytes(self._data)
        first = data.find(key)
        if first < 0 or data.find(key, first + 1) >= 0:
            return -1
        return first

    def bonfire_level(self, entity: int) -> int | None:
        """The bonfire's kindle value (0 unlit, 10 lit, 20/30/40 kindled), or
        None when its map has not been visited."""
        off = self._bonfire_record(entity)
        if off < 0:
            return None
        return struct.unpack_from("<I", self._data, off + BONFIRE_LEVEL_OFFSET)[0]

    def set_bonfire_lit(self, entity: int, lit: bool) -> bool:
        """Light (kindle value 10, kept when already kindled) or unlight
        (0) a bonfire. False when its map has not been visited."""
        off = self._bonfire_record(entity)
        if off < 0:
            return False
        level = struct.unpack_from("<I", self._data, off + BONFIRE_LEVEL_OFFSET)[0]
        new = (level or BONFIRE_LIT_LEVEL) if lit else 0
        struct.pack_into("<I", self._data, off + BONFIRE_LEVEL_OFFSET, new)
        return True

    # --- CHR block -------------------------------------------------------- #

    def chr_records(self) -> dict[tuple[int, int], tuple[int, int]]:
        """{(area, block): (offset of the part bits, part count)} for every
        map record of the CHR block (see CHR BLOCK). Empty when the block is
        not found once after the flag array or a record size does not match
        its part count."""
        base = self.flag_base()
        data = bytes(self._data)
        magic = data.find(CHR_MAGIC, max(base, 0))
        if base < 0 or magic < 0 or data.find(CHR_MAGIC, magic + 1) >= 0:
            return {}
        out = {}
        off = magic + CHR_RECORDS_FROM_MAGIC
        while off + CHR_RECORD_HEADER <= len(data):
            key, size, count = struct.unpack_from("<III", data, off)
            if key == CHR_END:
                return out
            if size != CHR_RECORD_HEADER + (count + 7) // 8:
                return {}
            out[(key >> 24, (key >> 16) & 0xFF)] = (off + CHR_RECORD_HEADER, count)
            off += size
        return {}

    def part_spawns_dead(self, area: int, block: int, index: int) -> bool:
        rec = self.chr_records().get((area, block))
        if rec is None or index >= rec[1]:
            return False
        return bool(self._data[rec[0] + index // 8] >> (index % 8) & 1)

    def clear_part_dead(self, area: int, block: int, index: int) -> None:
        """Let an enemy part spawn alive; maps without a record are skipped."""
        rec = self.chr_records().get((area, block))
        if rec is not None and index < rec[1]:
            self._data[rec[0] + index // 8] &= ~(1 << (index % 8)) & 0xFF

    # --- NPC states ------------------------------------------------------- #

    def npc_state(self, npc: dict) -> str:
        """Alive, Hostile, Dead or Not met, from the NPC's state range in
        data/npcs.json (lo..hi, with its dead and hostile flags)."""
        on = {f for f in range(npc["lo"], npc["hi"] + 1) if self.get_flag(f)}
        if on & set(npc["dead"]):
            return "Dead"
        if on & set(npc["hostile"]):
            return "Hostile"
        return "Alive" if on else "Not met"

    def set_npc_state(self, npc: dict, alive: bool) -> None:
        """Clear the NPC's state range and set its first state (alive) or its
        dead flag, as the game's NPC death event does. Reviving also clears
        the NPC's spawn-dead part bits and its revive_clear flags."""
        if not alive and not npc["dead"]:
            raise ValueError(f"{npc['name']} has no death state")
        target = npc["lo"] if alive else npc["dead"][0]
        for f in range(npc["lo"], npc["hi"] + 1):
            self.set_flag(f, f == target)
        if alive:
            # Death also leaves the NPC's parts spawning dead and, for some
            # NPCs, flags outside the range (npcs.json revive_clear).
            for area, block, index in npc.get("parts", []):
                self.clear_part_dead(area, block, index)
            for f in npc.get("revive_clear", []):
                self.set_flag(f, False)


# --- Utility (module-level) -------------------------------------------------- #


# --- Save file --------------------------------------------------------------- #


@dataclass
class DSRSave:
    """
    Complete DSR save file (BND4 container).
    Provides access to all 10 character slots and the system slot.
    """

    _raw: bytearray = field(default_factory=bytearray, repr=False)
    characters: list[DSRCharacter | None] = field(default_factory=list)
    system_data: bytearray = field(default_factory=bytearray, repr=False)

    @classmethod
    def from_file(cls, path: str | Path) -> DSRSave:
        raw = bytearray(Path(path).read_bytes())
        if len(raw) != FILE_SIZE:
            raise ValueError(
                f"Unexpected file size {len(raw):#x}, expected {FILE_SIZE:#x}"
            )
        if raw[:4] != b"BND4":
            raise ValueError("Not a BND4 file")
        save = cls(_raw=raw)
        save._load_characters()
        return save

    def _load_characters(self) -> None:
        self.characters = []
        for i in range(CHARACTER_SLOTS):
            off = SLOTS_OFFSET + i * SLOT_SIZE
            iv = bytes(self._raw[off : off + 16])
            ciphertext = bytes(self._raw[off + 16 : off + 16 + SLOT_DATA_SIZE])
            plaintext = _decrypt(iv, ciphertext)
            char = DSRCharacter(slot_index=i, _data=bytearray(plaintext))
            self.characters.append(char if not char.is_empty else None)

        sys_off = SLOTS_OFFSET + 10 * SLOT_SIZE
        sys_iv = bytes(self._raw[sys_off : sys_off + 16])
        sys_ciphertext = bytes(self._raw[sys_off + 16 : sys_off + 16 + SLOT_DATA_SIZE])
        self.system_data = bytearray(_decrypt(sys_iv, sys_ciphertext))

    def save_to_file(self, path: str | Path) -> None:
        """Re-encrypt modified characters and write the file."""
        raw = bytearray(self._raw)
        for i, char in enumerate(self.characters):
            if char is None:
                continue
            off = SLOTS_OFFSET + i * SLOT_SIZE
            iv = bytes(raw[off : off + 16])
            ciphertext = _encrypt(iv, char.get_raw())
            new_iv = _md5(ciphertext)
            raw[off : off + 16] = new_iv
            raw[off + 16 : off + 16 + SLOT_DATA_SIZE] = ciphertext

        sys_off = SLOTS_OFFSET + 10 * SLOT_SIZE
        sys_iv = bytes(raw[sys_off : sys_off + 16])
        sys_ciphertext = _encrypt(sys_iv, bytes(self.system_data))
        sys_new_iv = _md5(sys_ciphertext)
        raw[sys_off : sys_off + 16] = sys_new_iv
        raw[sys_off + 16 : sys_off + 16 + SLOT_DATA_SIZE] = sys_ciphertext

        atomic_write(path, raw)

    def verify_checksums(self) -> list[tuple[int, bool]]:
        """
        Return (slot_index, is_valid) pairs for all slots, including slot 10.
        A slot is valid when md5(ciphertext) == stored IV.
        """
        results = []
        for i in range(SLOT_COUNT):
            off = SLOTS_OFFSET + i * SLOT_SIZE
            stored_iv = bytes(self._raw[off : off + 16])
            ciphertext = bytes(self._raw[off + 16 : off + 16 + SLOT_DATA_SIZE])
            results.append((i, _md5(ciphertext) == stored_iv))
        return results


# --- Utility ----------------------------------------------------------------- #


def _weapon_level_from_item(item: DSRItem) -> int:
    """
    The DS1 weapon level (WL, 0-15) matchmaking uses for a held weapon:
      15-level paths (plain):                      WL = level
      10-level paths (Magic, Divine, Fire):        WL = 5 + level
      5-level paths (other infusions, soul gear):  WL = 10 + level, soul
                                                   weapons 5 + level * 2
      Ascended Pyromancy Flame: 15; not upgradable: 0
    """
    from er_save_manager.games.DSR import catalog

    hit = catalog.lookup(item.category, item.item_id)
    if hit is None:
        return 0
    entry, level = hit
    cap = entry["max_upgrade"]
    if entry["level_step"] > 1 and cap == ASCENDED_FLAME_CAP:
        return 15
    if cap == 15:
        return level
    if cap == 10:
        return 5 + level
    if cap == 5:
        return 10 + level if entry["infusion"] else min(5 + level * 2, 15)
    return 0
