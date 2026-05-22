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
+0x0060  4    Play time in frames at 30 fps (u32 LE)

--- HP / Stamina (live values, updated by game on load) ---
+0x0074  2    Unknown HP-related field
+0x0078  2    Current HP (u16 LE)
+0x007C  2    Max HP (u16 LE)
+0x0098  1    Stamina (u8)

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
+0x012A  1    Gender: 0=male, 1=female
+0x012E  1    Starting class (see DSRClass enum)
+0x0173  1    Covenant (see DSRCovenant enum)
+0x0179  1    Highest weapon upgrade level (used for matchmaking, must be calibrated)
+0x018C  34   Name, secondary copy (UTF-16LE, 16 chars + null terminator)

--- Equipment: slot indices into the inventory array ---
Each field is a u32 LE inventory slot index; 0xFFFFFFFF = nothing equipped.
+0x02A8  4    Left hand slot 1
+0x02AC  4    Right hand slot 1
+0x02B0  4    Left hand slot 2
+0x02B4  4    Right hand slot 2
+0x02C8  4    Helm slot
+0x02CC  4    Chest armor slot
+0x02D0  4    Gauntlets slot
+0x02D4  4    Leg armor slot
+0x02DC  4    Ring slot 1
+0x02E0  4    Ring slot 2

--- Equipment: cached item IDs (mirror of inventory, for quick lookup) ---
+0x0314  4    Left hand 1 item ID
+0x0318  4    Right hand 1 item ID
+0x031C  4    Left hand 2 item ID
+0x0320  4    Right hand 2 item ID
+0x0334  4    Helm item ID
+0x0338  4    Chest armor item ID
+0x033C  4    Gauntlets item ID
+0x0340  4    Leg armor item ID
+0x0348  4    Ring 1 item ID
+0x034C  4    Ring 2 item ID

--- Inventory ---
+0x0370  2048 * 28   Item array (2048 slots, 28 bytes each; see item layout below)
+0xE370  4           Highest used inventory slot index (u32 LE)

Key items occupy slots 0-63; weapons, armor, rings, consumables use slots 64-2047.

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
+0x0C  4   Inventory order index (u32 LE)
+0x10  4   Exists flag: 1=occupied, 0 or 0xFFFFFFFF=empty (u32 LE)
+0x14  4   Durability (u32 LE); Crystal infusion = base_durability / 10
+0x18  4   Unknown (u32 LE)

An empty slot has all bytes 0x00 or all 0xFF.

=== NPC / EVENT FLAG REGION ===

Pattern1: FF FF FF FF 00 00 00 00 FF FF FF FF 00 00 00 00
This 16-byte pattern repeats throughout the region starting at 0x1F000.
The last occurrence in range 0x1F000-0x1FFFF is the base anchor for NPC state bits
and bonfire flag bytes. All offsets below are relative to this anchor.

Anchor-relative offsets:
  -0xBC0   NG+ counter (u8; 0=NG, 1=NG+, 2=NG++, etc.)
  +0x6B    Bonfire warp data byte 1
  +0x6C    Bonfire warp data byte 2
  +0x6D    Bonfire warp data byte 3
  +0xAE    Bonfire warp enable flag

NPC alive/dead states are stored as individual bits relative to the same anchor.
See npc_data.json for per-NPC offset+bit definitions.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

from Crypto.Cipher import AES

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
OFF_PLAY_FRAMES = 0x0060  # u32 LE, frames at 30 fps
OFF_HP_CURRENT = 0x0078  # u16 LE
OFF_HP_MAX = 0x007C  # u16 LE
OFF_HP_UNKNOWN = 0x0074  # u16 LE, set to 0x000A on HP write
OFF_STAMINA = 0x0098  # u8
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
OFF_GENDER = 0x012A  # u8
OFF_CLASS = 0x012E  # u8
OFF_COVENANT = 0x0173  # u8
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

# Equipment cached item IDs (u32 LE each)
OFF_EQ_ID_LH1 = 0x0314
OFF_EQ_ID_RH1 = 0x0318
OFF_EQ_ID_LH2 = 0x031C
OFF_EQ_ID_RH2 = 0x0320
OFF_EQ_ID_HELM = 0x0334
OFF_EQ_ID_CHEST = 0x0338
OFF_EQ_ID_GAUNTLETS = 0x033C
OFF_EQ_ID_LEGS = 0x0340
OFF_EQ_ID_RING1 = 0x0348
OFF_EQ_ID_RING2 = 0x034C

# Inventory
OFF_INVENTORY = 0x0370  # start of item array
OFF_ITEMS_COUNT = 0xE370  # highest used slot index (u32 LE)
ITEM_SIZE = 28
MAX_INVENTORY_SLOTS = 2048
KEY_ITEM_SLOTS = 64  # key items occupy slots 0-63

# Slot occupancy check range: all-zero bytes here means empty character
EMPTY_CHECK_START = 0x0020
EMPTY_CHECK_END = 0x0090

# Pattern1 search range in decrypted slot data
PATTERN1_SEARCH_START = 0x1F000
PATTERN1_SEARCH_END = 0x1FFFF
PATTERN1 = bytes(
    [
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0x00,
        0x00,
        0x00,
        0x00,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
)

# Pattern1-anchor-relative offsets
ANCHOR_NG_PLUS = -0xBC0
ANCHOR_BONFIRE_1 = 0x6B
ANCHOR_BONFIRE_2 = 0x6C
ANCHOR_BONFIRE_3 = 0x6D
ANCHOR_BONFIRE_WARP = 0xAE

# VIT -> max HP lookup (game does not recalculate on load; must be set manually)
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
    return AES.new(AES_KEY, AES.MODE_CBC, iv).decrypt(ciphertext)


def _encrypt(iv: bytes, plaintext: bytes) -> bytes:
    return AES.new(AES_KEY, AES.MODE_CBC, iv).encrypt(plaintext)


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
    # Cached Pattern1 anchor: -2 = not yet computed, -1 = not found, >= 0 = offset
    _anchor_cache: int = field(default=-2, init=False, repr=False)

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
    def gender(self) -> int:
        return self._data[OFF_GENDER]

    @gender.setter
    def gender(self, value: int) -> None:
        self._data[OFF_GENDER] = value & 0xFF

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
                    self._data[OFF_STAMINA] = stamina & 0xFF

    def set_hp(self, value: int) -> None:
        """
        Set both current and max HP.
        Also sets the unknown HP field at 0x0074 to 0x000A as the game does.
        """
        struct.pack_into("<H", self._data, OFF_HP_MAX, value & 0xFFFF)
        struct.pack_into("<H", self._data, OFF_HP_CURRENT, value & 0xFFFF)
        struct.pack_into("<H", self._data, OFF_HP_UNKNOWN, 0x000A)

    @property
    def hp_current(self) -> int:
        return struct.unpack_from("<H", self._data, OFF_HP_CURRENT)[0]

    @property
    def hp_max(self) -> int:
        return struct.unpack_from("<H", self._data, OFF_HP_MAX)[0]

    @property
    def weapon_level(self) -> int:
        """Highest weapon upgrade level; must match actual inventory for correct matchmaking."""
        return self._data[OFF_WEAPON_LEVEL]

    @weapon_level.setter
    def weapon_level(self, value: int) -> None:
        self._data[OFF_WEAPON_LEVEL] = value & 0xFF

    # --- Play time ---

    @property
    def play_frames(self) -> int:
        """Elapsed play time in 30-fps frames."""
        return struct.unpack_from("<I", self._data, OFF_PLAY_FRAMES)[0]

    @property
    def play_seconds(self) -> float:
        return self.play_frames / 30.0

    # --- NG+ ---

    @property
    def ng_plus(self) -> int:
        anchor = self._find_pattern1()
        if anchor < 0:
            return 0
        off = anchor + ANCHOR_NG_PLUS
        if off < 0 or off >= len(self._data):
            return 0
        return self._data[off]

    @ng_plus.setter
    def ng_plus(self, value: int) -> None:
        anchor = self._find_pattern1()
        if anchor < 0:
            raise ValueError("Pattern1 not found; cannot set NG+ counter")
        off = anchor + ANCHOR_NG_PLUS
        if off < 0 or off >= len(self._data):
            raise ValueError("NG+ offset out of range")
        self._data[off] = value & 0xFF

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

    # --- NPC bit flags (Pattern1-relative) ---

    def get_npc_bit(self, byte_offset: int, bit: int) -> bool:
        """Read a single NPC state bit at anchor+byte_offset, bit position 0-7."""
        anchor = self._find_pattern1()
        if anchor < 0:
            raise ValueError("Pattern1 not found")
        abs_off = anchor + byte_offset
        return bool((self._data[abs_off] >> bit) & 1)

    def set_npc_bit(self, byte_offset: int, bit: int, value: bool) -> None:
        """Write a single NPC state bit at anchor+byte_offset, bit position 0-7."""
        anchor = self._find_pattern1()
        if anchor < 0:
            raise ValueError("Pattern1 not found")
        abs_off = anchor + byte_offset
        if value:
            self._data[abs_off] |= 1 << bit
        else:
            self._data[abs_off] &= ~(1 << bit)

    def get_bonfire_status(self) -> tuple[int, int, int, int] | None:
        """Return (byte1, byte2, byte3, warp_flag) from the bonfire region, or None."""
        anchor = self._find_pattern1()
        if anchor < 0:
            return None
        b1 = anchor + ANCHOR_BONFIRE_1
        b2 = anchor + ANCHOR_BONFIRE_2
        b3 = anchor + ANCHOR_BONFIRE_3
        bf = anchor + ANCHOR_BONFIRE_WARP
        if bf >= len(self._data):
            return None
        return (self._data[b1], self._data[b2], self._data[b3], self._data[bf])

    def set_bonfire_bytes(self, byte1: int, byte2: int, byte3: int, warp: int) -> None:
        anchor = self._find_pattern1()
        if anchor < 0:
            raise ValueError("Pattern1 not found")
        self._data[anchor + ANCHOR_BONFIRE_1] = byte1 & 0xFF
        self._data[anchor + ANCHOR_BONFIRE_2] = byte2 & 0xFF
        self._data[anchor + ANCHOR_BONFIRE_3] = byte3 & 0xFF
        self._data[anchor + ANCHOR_BONFIRE_WARP] = warp & 0xFF

    # --- Weapon level calibration ---

    def calibrate_weapon_level(self) -> int:
        """
        Recalculate and store the highest weapon upgrade level from inventory.
        Returns the computed level.
        """
        max_wl = 0
        for item in self.iter_items():
            if item.category == DSRItemCategory.WeaponShield:
                wl = _weapon_level_from_item(item)
                if wl > max_wl:
                    max_wl = wl
        self.weapon_level = max_wl
        return max_wl

    # --- Internal helpers ---

    def _find_pattern1(self) -> int:
        """
        Return absolute offset of the last Pattern1 hit in the search range, or -1.
        Cached after first computation: writing flags near the anchor would otherwise
        change the anchor byte and cause subsequent searches to find a different offset.
        """
        if self._anchor_cache == -2:
            pat = PATTERN1
            plen = len(pat)
            end = min(PATTERN1_SEARCH_END, len(self._data) - plen)
            last = -1
            for i in range(PATTERN1_SEARCH_START, end + 1):
                if self._data[i : i + plen] == pat:
                    last = i
            self._anchor_cache = last
        return self._anchor_cache

    def _read_utf16(self, offset: int, length: int) -> str:
        raw = bytes(self._data[offset : offset + length])
        # find null terminator
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
        db_item: dict,
        quantity: int = 1,
        upgrade: int = 0,
        infusion: int = 0,
    ) -> int:
        """
        Add an item to inventory from a DB entry dict (see data/items.json).

        db_item fields used: Type, Id, MaxStackCount, Category, Durability.
        For weapons, item_id = base_id + infusion*100 + upgrade.
        Key items (Category="key_items") use slots 0-63; all others 64-2047.
        Stackable items are stacked onto an existing slot if one exists.

        Returns the slot index used, or -1 if inventory is full.
        """
        type_numeric = int(db_item["Type"], 16) // 0x10000000
        base_id = int(db_item["Id"], 16)
        max_stack = int(db_item.get("MaxStackCount") or 1)
        clamp_qty = min(max(1, quantity), max_stack)

        # Weapons encode infusion and upgrade in the ID
        item_id = base_id + infusion * 100 + upgrade if type_numeric == 0 else base_id

        is_key = db_item.get("Category") == "key_items"
        slot_start = 0 if is_key else KEY_ITEM_SLOTS
        slot_end = KEY_ITEM_SLOTS if is_key else MAX_INVENTORY_SLOTS

        # Stack onto existing slot for stackable non-weapons
        if max_stack > 1 and type_numeric != 0:
            for slot_idx in range(slot_start, slot_end):
                existing = self.read_item(slot_idx)
                if (
                    not existing.is_empty
                    and existing.item_id == item_id
                    and existing.category == type_numeric
                ):
                    existing.quantity = min(existing.quantity + clamp_qty, max_stack)
                    self.write_item(slot_idx, existing)
                    return slot_idx

        # Find the first empty slot
        for slot_idx in range(slot_start, slot_end):
            if self.read_item(slot_idx).is_empty:
                new_item = DSRItem(
                    category=type_numeric,
                    item_id=item_id,
                    quantity=clamp_qty,
                    order=slot_idx,
                    exists=1,
                    durability=_calc_durability(db_item, infusion),
                    unknown=0,
                    slot_index=slot_idx,
                )
                self.write_item(slot_idx, new_item)
                self._update_max_item_slot(slot_idx)
                if type_numeric == 0:
                    wl = _weapon_level_from_item(new_item)
                    if wl > self.weapon_level:
                        self.weapon_level = wl
                return slot_idx
        return -1

    def remove_item(self, slot: int) -> None:
        """
        Clear an inventory slot.
        Fills the entry with 0xFF and sets the exists field to 0,
        matching the format the game uses for empty slots.
        """
        if not 0 <= slot < MAX_INVENTORY_SLOTS:
            raise IndexError(f"Slot {slot} out of range")
        off = OFF_INVENTORY + slot * ITEM_SIZE
        self._data[off : off + ITEM_SIZE] = b"\xff" * ITEM_SIZE
        struct.pack_into("<I", self._data, off + 16, 0)  # exists = 0

    # --- NPC / boss state ---------------------------------------------------- #

    def get_npc_alive(self, npc_def: dict) -> bool:
        """
        Return True if all bit conditions in npc_def indicate the NPC is alive.
        npc_def is one entry from data/npc_data.json (keys: name, bits).
        Each bit entry: offset (hex str), bit (0-7), reverse (bool).
        reverse=True means bit=0 indicates alive; False means bit=1 indicates alive.
        """
        anchor = self._find_pattern1()
        if anchor < 0:
            return False
        for entry in npc_def["bits"]:
            off = anchor + int(entry["offset"], 16)
            bit = entry["bit"]
            reverse = entry.get("reverse", False)
            val = bool((self._data[off] >> bit) & 1)
            if not ((not val) if reverse else val):
                return False
        return True

    def set_npc_alive(self, npc_def: dict, alive: bool) -> None:
        """
        Set all bit conditions in npc_def to the alive or dead state.
        See get_npc_alive for npc_def format.
        """
        anchor = self._find_pattern1()
        if anchor < 0:
            raise ValueError("Pattern1 not found")
        for entry in npc_def["bits"]:
            off = anchor + int(entry["offset"], 16)
            bit = entry["bit"]
            reverse = entry.get("reverse", False)
            # reverse=True: alive=clear, dead=set; reverse=False: alive=set, dead=clear
            write_val = (not alive) if reverse else alive
            if write_val:
                self._data[off] |= 1 << bit
            else:
                self._data[off] &= ~(1 << bit)

    # --- Bonfires ------------------------------------------------------------ #

    def unlock_all_bonfires(self) -> None:
        """
        Unlock all warpable bonfires.
        Sets the three bonfire data bytes and the warp enable flag.
        """
        self.set_bonfire_bytes(0xF0, 0xFF, 0xFF, 0x22)

    # --- Generic event flags ------------------------------------------------- #

    def get_flag(self, flag_id: int) -> bool:
        """
        Read a game event flag.

        Encoding: byte_offset = anchor + flag_id // 8, bit = flag_id % 8.
        Covers all global flags (2-17), NPC states (1000-1900), gesture flags
        (280-288), and utility flags up to ID ~2,124,719.
        Map-specific flags (11xxxxxx, 50xxxxxx) are out of range.
        """
        anchor = self._find_pattern1()
        if anchor < 0:
            raise ValueError("Pattern1 not found")
        off = anchor + flag_id // 8
        if off >= len(self._data):
            raise IndexError(
                f"Flag {flag_id} out of accessible range "
                f"(needs anchor+{flag_id // 8:#x}, available to anchor+{len(self._data) - anchor:#x})"
            )
        return bool((self._data[off] >> (flag_id % 8)) & 1)

    def set_flag(self, flag_id: int, value: bool) -> None:
        """Write a game event flag. See get_flag for encoding and range details."""
        anchor = self._find_pattern1()
        if anchor < 0:
            raise ValueError("Pattern1 not found")
        off = anchor + flag_id // 8
        if off >= len(self._data):
            raise IndexError(
                f"Flag {flag_id} out of accessible range "
                f"(needs anchor+{flag_id // 8:#x}, available to anchor+{len(self._data) - anchor:#x})"
            )
        if value:
            self._data[off] |= 1 << (flag_id % 8)
        else:
            self._data[off] &= ~(1 << (flag_id % 8))


# --- Utility (module-level) -------------------------------------------------- #


def _calc_durability(db_item: dict, infusion: int) -> int:
    """Return starting durability for a newly spawned item."""
    dur = int(db_item.get("Durability") or 0)
    if infusion == DSRInfusion.Crystal:
        dur = dur // 10
    return dur


# --- Save file --------------------------------------------------------------- #


@dataclass
class DSRSave:
    """
    Complete DSR save file (BND4 container).
    Provides access to all 10 character slots and the system slot.
    """

    _raw: bytearray = field(default_factory=bytearray, repr=False)
    characters: list[DSRCharacter | None] = field(default_factory=list)

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

    def get_character(self, slot: int) -> DSRCharacter | None:
        """Return the character in slot 0-9, or None if empty."""
        if not 0 <= slot < CHARACTER_SLOTS:
            raise IndexError(f"Slot {slot} out of range (0-9)")
        return self.characters[slot]

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
        Path(path).write_bytes(raw)

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


def _weapon_level_from_item(item: DSRItem, db_item: dict | None = None) -> int:
    """
    Compute the DS1 weapon level (WL) used for matchmaking from an inventory item.

    WL scale (0-15):
      MaxUpgrade=15 (standard path), Standard infusion:   WL = upgrade (0-15)
      MaxUpgrade=15, Crystal/Lightning/Raw/Enchanted/Occult/Chaos: cap at +5, WL = 10+upgrade
      MaxUpgrade=15, Magic/Divine/Fire:                   cap at +10, WL = 5+upgrade
      MaxUpgrade=5  (boss / unique weapons):              WL = 5 + upgrade*2
      MaxUpgrade=0 or no upgrade:                         WL = 0

    Without a db_item reference (no item DB available), falls back to
    returning the raw upgrade level (best-effort, never worse than 15).
    """
    if item.category != DSRItemCategory.WeaponShield:
        return 0
    # Pyromancy Flame (Ascended) is always WL 15
    if item.base_item_id == 0x145520:
        return 15
    ul = item.upgrade_level
    if db_item is None:
        return min(ul, 15)
    max_up = db_item.get("MaxUpgrade")
    if not max_up:
        return 0
    if max_up == 5:
        # Boss/unique path: WL = 5 + upgrade*2
        return min(5 + ul * 2, 15)
    # Standard path: cap depends on infusion
    infusion = item.infusion
    if infusion in (
        DSRInfusion.Crystal,
        DSRInfusion.Lightning,
        DSRInfusion.Raw,
        DSRInfusion.Enchanted,
        DSRInfusion.Occult,
        DSRInfusion.Chaos,
    ):
        cap = 5
    elif infusion in (DSRInfusion.Magic, DSRInfusion.Divine, DSRInfusion.Fire):
        cap = 10
    else:
        cap = 15
    if cap == 15:
        return ul
    if cap == 10:
        return 5 + ul
    return 10 + ul  # cap == 5
