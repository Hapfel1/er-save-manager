"""
Nightreign Save File Parser

Container: BND4 with 14 entries, AES-128-CBC encrypted per-entry.
Key: 0x18F63266_05BD178A_5524523A_C0A0C609.
IV: prepended 16 bytes of each encrypted entry.
Checksum: MD5(decrypted[4 : len-28]) stored at decrypted[len-28 : len-12].
          Remaining 12 bytes (len-12 : len) are PKCS7-like padding (0x0C * 12).

Entry layout:
  Entry 0-9:  character slots (slot 0 = first character, etc.)
  Entry 10:   global profile data (SteamID, Deep of Night progress, hero appearances)
  Entry 11:   match history / leaderboard data (large, ~2.3MB)
  Entry 12:   regulation / param data (large, ~4MB)
  Entry 13:   additional game data (large, ~2MB)

--- Character Slot (entries 0-9) ---

Offset  Size  Field
0x0000     4  slot_header_magic (0x00100010)
0x0004     4  slot_data_size
0x0008     8  unknown_header
0x0010     8  unknown (all zeros when empty)
0x0014     -  item_states[] - variable-size entries, 5120 slots max
               each ItemState:
                 ga_handle(u32) + item_id(u32) = 8 bytes base
                 if ga_handle == 0: size = 8 (empty)
                 if type_bits == 0x80000000 (weapon): size = 88
                 if type_bits == 0x90000000 (armor):  size = 16
                 if type_bits == 0xC0000000 (relic):  size = 80
                   relic layout:
                     +0x00 ga_handle (u32)
                     +0x04 item_id (u32)       - 0x80000000 | real_item_id
                     +0x08 durability (u32)    - same as item_id for relics
                     +0x0C unk_1 (u32)         - 0xFFFFFFFF
                     +0x10 effect_1 (u32)      - AttachEffect ID or 0xFFFFFFFF
                     +0x14 effect_2 (u32)
                     +0x18 effect_3 (u32)
                     +0x1C padding[28] (fixed bytes)
                     +0x38 curse_1 (u32)
                     +0x3C curse_2 (u32)
                     +0x40 curse_3 (u32)
                     +0x44 unk_2 (u32)         - 0xFFFFFFFF
                     +0x48 end_padding[8]      - all zeros
  After item_states section (state cursor + 0x94):
    name_offset     = state_cursor + 0x94   (player_name, UTF-16LE, max 16 chars)
    sigs_offset     = name_offset - 64       (Marks of Night / Sigs, u32 LE)
    murk_offset    = name_offset + 52       (murk currency, u32 LE)
  After name section (name_offset + 0x5B8):
    entry_count_offset = name_offset + 0x5B8
    entry_offset       = entry_count_offset + 4
  ItemEntry array (3065 slots, each 14 bytes):
    +0x00 ga_handle (u32)     - type_bits | instance_id
    +0x04 item_amount (u32)
    +0x08 acquisition_id (u32)
    +0x0C is_favorite (u8)
    +0x0D is_new (u8)
  After ItemEntries (entries_end = entry_offset + 3065*14):
    entries_end + 0x6A  next_acquisition_id (u32) - always max(acquisition_id) + 1
    entries_end + 0x21A relic loadout chunk:
      +0x00 chunk_id (u16)        - 0x00C2
      +0x02 chunk_version (u16)   - 3
      +0x04 chunk_size (u32)      - 0x2C00 in every observed save; payload
                                    bytes after this field
      +0x08 unk (u16)             - 3
      +0x0A hero_count (u16)      - 10
      +0x0C universal_count (u16) - 4 (vessels usable by every hero, 19xxx)
      +0x0E hero_vessel_count (u16) - 70 (7 per hero, x000-x006)
      +0x10 preset_count (u16)    - 100
      +0x12 pad (u16)
      +0x14 hero blocks[hero_count], each 8 + universal_count * 28 bytes:
        +0x00 hero_type (u8)
        +0x01 cur_preset_idx (u8) - index into presets[], 0xFF = none
        +0x02 pad[2]
        +0x04 cur_vessel_id (u32)
        +0x08 universal_vessels[universal_count]:
               each vessel: vessel_id(u32) + relics[6](u32 each) = 28 bytes
      hero_vessels[hero_vessel_count], 28 bytes each (same layout); modded
        vessels are appended here even with 19xxx IDs
      zero padding to 8-byte alignment of the payload (4 bytes in vanilla)
      presets[preset_count], 80 bytes each (empty slots are always present):
          +0x00 header (u8)       - 0x01 = valid, 0x00 = empty
          +0x01 hero_id (u8)
          +0x02 unk (u8)
          +0x03 counter (u8)      - recency rank, 0 = newest; dense 0..n-1
                                    (a new preset takes 0, the rest move up)
          +0x04 name (36 bytes)   - UTF-16LE, max 18 chars
          +0x28 pad[4]
          +0x2C vessel_id (u32)
          +0x30 relics[6] (u32 each) = 24 bytes
          +0x48 timestamp (u64)   - Windows FILETIME in local time
        An empty preset slot is all zeros except vessel_id = 0xFFFFFFFF.
        Used presets are contiguous from index 0; the game never leaves gaps.
      Vessel relic slots 0-2 take normal relics, 3-5 deep relics; an empty
      slot is 0. A relic's color must equal the vessel slot color, except
      slot color 4 which accepts any color.
      Vanilla payload uses 11176 of 11264 bytes. Mods that add vessels grow
      it by 28 bytes per hero vessel and hero_count * 28 per universal
      vessel, plus alignment. From modded saves:
        +3 hero vessels: 11256 bytes, loads normally.
        +4 hero vessels: 11288 bytes; reported to crash before loading.
        +1 universal vessel: 11456 bytes; the game still writes the header
          counts and every preset that fits (97 of 100), but loads no
          presets, so the stored presets survive in the file.

--- Global Profile Data (entry 10) ---

Offset  Size  Field
0x0000     4  profile_magic (0x00060010)
0x0004     4  profile_data_size (0x012F = 303)
0x0008     8  steam_id (u64 LE)
0x0010     6  settings_bytes (byte array matching game launch settings)
0x0016     -  various settings flags
0x1330     4  don_rank (u32)               - Deep of Night rank (1 = rank 1)
0x1334     4  don_max_rank (u32)           - max rank achieved (32 = max displayed)
0x1338     4  unk_don_1 (u32)
0x133C     4  don_score (u32)              - points/exp toward next rank
0x1340     4  unk_don_2 (u32)
0x1344     4  unk_don_3 (u32)
0x1348     4  unk_don_4 (u32)
0x134C     4  unk_don_5 (u32)
0x1350     4  unk_don_6 (u32)
0x1354     4  unk_don_7 (u32)
0x1358     4  don_nightlord_progress (u32) - bosses cleared (3 in sample)
0x135C     4  unk_don_8 (u32)
0x1360   256  boss_records[16]:            - 16 boss run records
               each record 16 bytes:
                 best_score (u16) pad(u16) cleared_score (u16) pad(u16)
                 attempts (u32) unk (u32)
                 0xFFFF = not attempted
0x1460     4  run_count (u32)              - total expeditions
0x1464     4  unk_1464 (u32)              - 0xB4 = 180
0x1950  0x290 hero_profile[0]:             - Wylder profile block
0x1BE0  0x290 hero_profile[1]:             - Guardian
0x1E70  0x290 hero_profile[2]:             - Ironeye
0x2100  0x290 hero_profile[3]:             - Duchess
0x2390  0x290 hero_profile[4]:             - Raider
0x2620  0x290 hero_profile[5]:             - Revenant
0x28B0  0x290 hero_profile[6]:             - Recluse
0x2B40  0x290 hero_profile[7]:             - Executor
0x2DD0  0x290 hero_profile[8]:             - Scholar
0x3060  0x290 hero_profile[9]:             - Undertaker

  Hero profile block (0x290 bytes each):
    +0x00  4  unk_0 (u32)
    +0x04  4  unk_4 (u32)
    +0x08  4  hero_active_flag (u32)  - 1 = used/active
    +0x0C  4  unk_c (u32)
    +0x10  2  pad (u16)               - always 0x0000
    +0x12 30  hero_name (UTF-16LE)    - character name for this hero (15 chars max)
    +0x34  4  unk_34 (u32)            - 1
    +0x38  4  total_runs (u32)        - run count for this hero
    +0x3C  4  timestamp (u32)         - last played
    +0x40  4  unk_40 (u32)
    +0x44  4  unk_44 (u32)            - 10000 = 0x2710
    +0x48  4  b'FACE' magic
    +0x4C  4  appearance_count (u32)  - 4
    +0x50  4  appearance_entry_size (u32) - 0x120 = 288
    +0x54 288 appearance_slot[0]      - relic-equipped appearance
    +0x174 288 appearance_slot[1]
    +0x294 288 appearance_slot[2]     (note: these extend past the 0x290 block size
    ... (appearance data may overlap with the stated 0x290 spacing)
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from er_save_manager.own_writes import record_write

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False

# AES-128-CBC key (same key as DS2/ER Seamless Coop)
_NR_KEY = bytes(
    [
        0x18,
        0xF6,
        0x32,
        0x66,
        0x05,
        0xBD,
        0x17,
        0x8A,
        0x55,
        0x24,
        0x52,
        0x3A,
        0xC0,
        0xA0,
        0xC6,
        0x09,
    ]
)

_IV_SIZE = 16
_CHECKSUM_TAIL = 28  # last 28 bytes: MD5(16) + padding(12)

_BND4_MAGIC = b"BND4"
_ENTRY_MAGIC = bytes([0x40, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF])
_BND4_HEADER_SZ = 64
_ENTRY_STRIDE = 32

# Offsets relative to the end of the ItemEntry array
_ACQ_COUNTER_REL = 0x6A  # next acquisition_id (u32)
_LOADOUT_REL = 0x21A  # relic loadout chunk header

_LOADOUT_CHUNK_ID = 0x00C2
_LOADOUT_HEADER_SZ = 0x14  # chunk header (8) + count fields (12)
_VESSEL_SZ = 28  # vessel_id + 6 relic handles
_PRESET_SZ = 80
_NO_PRESET = 0xFF  # cur_preset_idx value for no selected preset
# Empty preset slot as the game writes it: zeros except vessel_id 0xFFFFFFFF
_EMPTY_PRESET = bytes(44) + b"\xff\xff\xff\xff" + bytes(32)
VANILLA_UNIVERSAL_VESSELS = 4
VANILLA_HERO_VESSELS = 70

# Item type prefix bits (upper byte of ga_handle)
ITEM_TYPE_NONE = 0x00000000
ITEM_TYPE_WEAPON = 0x80000000
ITEM_TYPE_ARMOR = 0x90000000
ITEM_TYPE_GOODS = 0xB0000000
ITEM_TYPE_RELIC = 0xC0000000

# Item state sizes by type
_STATE_SIZE = {
    ITEM_TYPE_NONE: 8,
    ITEM_TYPE_WEAPON: 88,
    ITEM_TYPE_ARMOR: 16,
    ITEM_TYPE_GOODS: 8,
    ITEM_TYPE_RELIC: 80,
}

STATE_SLOT_COUNT = 5120
ENTRY_SLOT_COUNT = 3065
STATE_KEEP_START = 84  # slots 0-83 are reserved/system

# Relic state field offsets (within the 80-byte relic state)
_RELIC_EFFECT_1 = 0x10
_RELIC_EFFECT_2 = 0x14
_RELIC_EFFECT_3 = 0x18
_RELIC_CURSE_1 = 0x38
_RELIC_CURSE_2 = 0x3C
_RELIC_CURSE_3 = 0x40
_RELIC_UNK_2 = 0x44

# Global profile (entry 10) offsets
_E10_STEAM_ID = 0x0008
_E10_DON_RANK = 0x1330
_E10_DON_MAX_RANK = 0x1334
_E10_DON_SCORE = 0x133C
_E10_DON_NL_PROG = 0x1358
_E10_BOSS_RECORDS = 0x1360  # 16 * 16 bytes
_E10_RUN_COUNT = 0x1460
_E10_HERO_BASE = 0x1950  # hero 0 profile block
_E10_HERO_STRIDE = 0x0290  # bytes per hero block

# Hero profile block field offsets (relative to hero block base)
_HERO_ACTIVE_FLAG = 0x08
_HERO_NAME_OFFSET = 0x12  # UTF-16LE, skipping 2-byte pad at +0x10
_HERO_NAME_MAX = 15  # characters
_HERO_TOTAL_RUNS = 0x38
_HERO_TIMESTAMP = 0x3C
_HERO_FACE_MAGIC = 0x48  # b'FACE'
_HERO_FACE_COUNT = 0x4C  # u32, should be 4
_HERO_FACE_SIZE = 0x50  # u32, should be 0x120 = 288
_HERO_FACE_DATA = 0x54  # 4 * 288 bytes appearance data

HERO_NAMES = [
    "Wylder",
    "Guardian",
    "Ironeye",
    "Duchess",
    "Raider",
    "Revenant",
    "Recluse",
    "Executor",
    "Scholar",
    "Undertaker",
]


# ---------------------------------------------------------------------------
# Low-level crypto
# ---------------------------------------------------------------------------


def _decrypt_entry(raw: bytes, offset: int, size: int) -> bytearray:
    """Decrypt a single BND4 entry from the raw file."""
    if not _CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package required for Nightreign saves")
    enc = raw[offset : offset + size]
    iv = enc[:_IV_SIZE]
    payload = enc[_IV_SIZE:]
    cipher = Cipher(algorithms.AES(_NR_KEY), modes.CBC(iv))
    dec = cipher.decryptor()
    return bytearray(dec.update(payload) + dec.finalize())


def _encrypt_entry(iv: bytes, decrypted: bytearray) -> bytes:
    """Re-encrypt a decrypted entry using the original IV."""
    if not _CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package required for Nightreign saves")
    cipher = Cipher(algorithms.AES(_NR_KEY), modes.CBC(iv))
    enc = cipher.encryptor()
    return iv + enc.update(bytes(decrypted)) + enc.finalize()


def _patch_checksum(dec: bytearray) -> None:
    """Recompute and write MD5 checksum into decrypted entry data."""
    checksum_off = len(dec) - _CHECKSUM_TAIL
    digest = hashlib.md5(dec[4:checksum_off]).digest()
    dec[checksum_off : checksum_off + 16] = digest


# ---------------------------------------------------------------------------
# BND4 container
# ---------------------------------------------------------------------------


@dataclass
class BND4Entry:
    """Metadata and decrypted content of one BND4 entry."""

    index: int
    size: int  # encrypted size (includes IV)
    data_offset: int  # absolute offset in raw file
    iv: bytes  # original IV (needed for re-encryption)
    decrypted: bytearray = field(default_factory=bytearray)

    def patch_and_encrypt(self) -> bytes:
        """Patch checksum and return re-encrypted bytes (same IV)."""
        _patch_checksum(self.decrypted)
        return _encrypt_entry(self.iv, self.decrypted)


def _parse_bnd4_entries(raw: bytes) -> list[BND4Entry]:
    """Parse the BND4 header and return decrypted entry list."""
    if raw[:4] != _BND4_MAGIC:
        raise ValueError(f"Not a BND4 file (magic={raw[:4].hex()})")
    num = struct.unpack_from("<I", raw, 12)[0]
    entries = []
    for i in range(num):
        pos = _BND4_HEADER_SZ + i * _ENTRY_STRIDE
        entry_magic = raw[pos : pos + 8]
        if entry_magic != _ENTRY_MAGIC:
            raise ValueError(f"Bad entry magic at index {i}: {entry_magic.hex()}")
        size, _, data_offset = struct.unpack_from("<3i", raw, pos + 8)
        enc = raw[data_offset : data_offset + size]
        iv = bytes(enc[:_IV_SIZE])
        dec = _decrypt_entry(raw, data_offset, size)
        entries.append(
            BND4Entry(
                index=i,
                size=size,
                data_offset=data_offset,
                iv=iv,
                decrypted=dec,
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Character slot data structures
# ---------------------------------------------------------------------------


@dataclass
class RelicState:
    """
    Parsed relic item state (80 bytes).
    Offsets are relative to the start of the relic state block.
    """

    ga_handle: int = 0
    item_id: int = 0
    durability: int = 0
    unk_1: int = 0xFFFFFFFF
    effect_1: int = 0xFFFFFFFF
    effect_2: int = 0xFFFFFFFF
    effect_3: int = 0xFFFFFFFF
    curse_1: int = 0xFFFFFFFF
    curse_2: int = 0xFFFFFFFF
    curse_3: int = 0xFFFFFFFF
    unk_2: int = 0xFFFFFFFF
    raw: bytearray = field(default_factory=bytearray)  # full 80-byte block
    state_index: int = -1  # index within the 5120-slot state array
    abs_offset: int = -1  # absolute offset within the slot data

    @property
    def real_item_id(self) -> int:
        return self.item_id & 0x00FFFFFF

    @property
    def instance_id(self) -> int:
        return self.ga_handle & 0x00FFFFFF

    @property
    def is_deep(self) -> bool:
        """Deep relics have real_item_id >= 2000000."""
        return self.real_item_id >= 2000000

    @classmethod
    def from_bytes(
        cls, data: bytearray, abs_offset: int, state_index: int
    ) -> RelicState:
        obj = cls()
        obj.abs_offset = abs_offset
        obj.state_index = state_index
        obj.raw = data[abs_offset : abs_offset + 80]
        (
            obj.ga_handle,
            obj.item_id,
            obj.durability,
            obj.unk_1,
            obj.effect_1,
            obj.effect_2,
            obj.effect_3,
        ) = struct.unpack_from("<7I", obj.raw, 0)
        obj.curse_1 = struct.unpack_from("<I", obj.raw, _RELIC_CURSE_1)[0]
        obj.curse_2 = struct.unpack_from("<I", obj.raw, _RELIC_CURSE_2)[0]
        obj.curse_3 = struct.unpack_from("<I", obj.raw, _RELIC_CURSE_3)[0]
        obj.unk_2 = struct.unpack_from("<I", obj.raw, _RELIC_UNK_2)[0]
        return obj

    def write_to(self, data: bytearray) -> None:
        """Write modified relic fields back to data at abs_offset."""
        struct.pack_into(
            "<7I",
            data,
            self.abs_offset,
            self.ga_handle,
            self.item_id,
            self.durability,
            self.unk_1,
            self.effect_1,
            self.effect_2,
            self.effect_3,
        )
        struct.pack_into("<I", data, self.abs_offset + _RELIC_CURSE_1, self.curse_1)
        struct.pack_into("<I", data, self.abs_offset + _RELIC_CURSE_2, self.curse_2)
        struct.pack_into("<I", data, self.abs_offset + _RELIC_CURSE_3, self.curse_3)
        struct.pack_into("<I", data, self.abs_offset + _RELIC_UNK_2, self.unk_2)

    def effects_list(self) -> list[int]:
        return [
            self.effect_1,
            self.effect_2,
            self.effect_3,
            self.curse_1,
            self.curse_2,
            self.curse_3,
        ]


@dataclass
class ItemEntry:
    """
    One 14-byte inventory entry.
    abs_offset is the absolute position within the slot data.
    """

    ga_handle: int = 0
    item_amount: int = 0
    acquisition_id: int = 0
    is_favorite: bool = False
    is_new: bool = False
    abs_offset: int = -1

    @property
    def type_bits(self) -> int:
        return self.ga_handle & 0xF0000000

    @property
    def instance_id(self) -> int:
        return self.ga_handle & 0x00FFFFFF

    @property
    def is_relic(self) -> bool:
        return self.type_bits == ITEM_TYPE_RELIC

    @property
    def is_empty(self) -> bool:
        return self.ga_handle == 0

    @classmethod
    def from_bytes(cls, data: bytearray, abs_offset: int) -> ItemEntry:
        obj = cls()
        obj.abs_offset = abs_offset
        (obj.ga_handle, obj.item_amount, obj.acquisition_id) = struct.unpack_from(
            "<3I", data, abs_offset
        )
        obj.is_favorite = bool(data[abs_offset + 12])
        obj.is_new = bool(data[abs_offset + 13])
        return obj

    def write_to(self, data: bytearray) -> None:
        struct.pack_into(
            "<3I",
            data,
            self.abs_offset,
            self.ga_handle,
            self.item_amount,
            self.acquisition_id,
        )
        data[self.abs_offset + 12] = int(self.is_favorite)
        data[self.abs_offset + 13] = int(self.is_new)


@dataclass
class VesselLoadout:
    """One vessel's relic assignment."""

    vessel_id: int = 0
    relics: list[int] = field(default_factory=lambda: [0] * 6)  # 6 ga_handles
    vessel_offset: int = -1  # abs offset of vessel_id field
    relics_offset: int = -1  # abs offset of relics[0]

    def write_to(self, data: bytearray) -> None:
        struct.pack_into("<I", data, self.vessel_offset, self.vessel_id)
        struct.pack_into("<6I", data, self.relics_offset, *self.relics)


@dataclass
class CustomPreset:
    """One 80-byte custom loadout preset."""

    hero_id: int = 0
    counter: int = 0  # sort key, 0 = newest
    name: str = ""
    vessel_id: int = 0
    relics: list[int] = field(default_factory=lambda: [0] * 6)
    timestamp: int = 0
    abs_offset: int = -1  # base of the 80-byte block
    index: int = -1  # position in the preset array (what cur_preset_idx refers to)

    @property
    def is_empty(self) -> bool:
        return self.hero_id == 0

    def write_to(self, data: bytearray) -> None:
        base = self.abs_offset
        data[base] = 0x01 if not self.is_empty else 0x00
        data[base + 1] = self.hero_id
        data[base + 3] = self.counter
        name_bytes = self.name.encode("utf-16-le").ljust(36, b"\x00")[:36]
        data[base + 4 : base + 40] = name_bytes
        struct.pack_into("<I", data, base + 44, self.vessel_id)
        struct.pack_into("<6I", data, base + 48, *self.relics)
        struct.pack_into("<Q", data, base + 72, self.timestamp)


@dataclass
class LoadoutInfo:
    """Header of the relic loadout chunk and its byte budget."""

    offset: int = -1  # abs offset of the chunk header
    chunk_size: int = 0  # payload capacity from the header
    hero_count: int = 0
    universal_count: int = 0
    hero_vessel_count: int = 0
    preset_count: int = 0

    @property
    def presets_rel(self) -> int:
        """Start of the preset array relative to the payload (after the 8-byte header).

        Presets hold a u64 timestamp, so the array is 8-byte aligned: vanilla
        pads 4 bytes after the 70 hero vessels, +3 modded vessels pad none.
        """
        rel = (
            _LOADOUT_HEADER_SZ
            - 8
            + self.hero_count * (8 + self.universal_count * _VESSEL_SZ)
            + self.hero_vessel_count * _VESSEL_SZ
        )
        return rel + (-rel) % 8

    @property
    def presets_offset(self) -> int:
        """Absolute offset of preset 0."""
        return self.offset + 8 + self.presets_rel

    @property
    def presets_that_fit(self) -> int:
        """Preset slots inside the chunk; fewer than preset_count on overflow."""
        room = max(0, self.chunk_size - self.presets_rel)
        return min(self.preset_count, room // _PRESET_SZ)

    @property
    def used_bytes(self) -> int:
        """Payload bytes required by the current counts (excludes the 8-byte chunk header)."""
        return self.presets_rel + self.preset_count * _PRESET_SZ

    @property
    def spare_bytes(self) -> int:
        return self.chunk_size - self.used_bytes

    @property
    def is_vanilla(self) -> bool:
        return (
            self.universal_count == VANILLA_UNIVERSAL_VESSELS
            and self.hero_vessel_count == VANILLA_HERO_VESSELS
        )


@dataclass
class HeroLoadout:
    """Parsed hero loadout section for one of the 10 heroes."""

    hero_type: int = 0  # 1-10
    cur_preset_idx: int = 0xFF
    cur_vessel_id: int = 0
    vessels: list[VesselLoadout] = field(default_factory=list)
    presets: list[CustomPreset] = field(default_factory=list)
    hero_base_offset: int = -1  # abs offset in slot data

    def get_vessel(self, vessel_id: int) -> VesselLoadout | None:
        for v in self.vessels:
            if v.vessel_id == vessel_id:
                return v
        return None


@dataclass
class NightreignSlot:
    """
    Parsed character slot (one of entries 0-9).
    All offset fields are absolute positions within the decrypted slot data.
    """

    slot_index: int = -1
    decrypted: bytearray = field(default_factory=bytearray)

    # Parsed inventory
    item_states: list = field(
        default_factory=list
    )  # list of (ga_handle, size, abs_off)
    relic_states: dict = field(default_factory=dict)  # ga_handle -> RelicState
    item_entries: list = field(default_factory=list)  # list[ItemEntry]
    relics: dict = field(default_factory=dict)  # ga_handle -> ItemEntry (relic only)

    # Key offsets (absolute within decrypted data)
    name_offset: int = -1
    sigs_offset: int = -1
    murk_offset: int = -1
    entry_count_offset: int = -1
    entry_offset: int = -1
    acq_counter_offset: int = -1

    # Vessel/loadout
    loadout: LoadoutInfo | None = None
    heroes: dict = field(default_factory=dict)  # hero_type -> HeroLoadout
    # Hero vessels whose ID does not map to a parsed hero (modded vessel IDs)
    unassigned_vessels: list = field(default_factory=list)
    free_presets: list = field(
        default_factory=list
    )  # abs offsets of empty preset slots

    def is_empty(self) -> bool:
        """Slot has no character data.

        Item state slots 0-83 are reserved/system slots and are always zero,
        even for a used character, so occupancy must be read from the player
        name and item entry count instead.
        """
        return not self.player_name and self.entry_count == 0

    @property
    def player_name(self) -> str:
        if self.name_offset < 0:
            return ""
        raw = self.decrypted[self.name_offset : self.name_offset + 32]
        return raw.decode("utf-16-le", errors="ignore").rstrip("\x00")

    @player_name.setter
    def player_name(self, value: str) -> None:
        if self.name_offset < 0:
            raise RuntimeError("slot not parsed")
        name_bytes = value.encode("utf-16-le").ljust(32, b"\x00")[:32]
        self.decrypted[self.name_offset : self.name_offset + 32] = name_bytes

    @property
    def murk(self) -> int:
        if self.murk_offset < 0:
            return 0
        return struct.unpack_from("<I", self.decrypted, self.murk_offset)[0]

    @murk.setter
    def murk(self, value: int) -> None:
        if self.murk_offset < 0:
            raise RuntimeError("slot not parsed")
        struct.pack_into("<I", self.decrypted, self.murk_offset, value)

    @property
    def marks_of_night(self) -> int:
        """Marks of Night (Sigs) currency."""
        if self.sigs_offset < 0:
            return 0
        return struct.unpack_from("<I", self.decrypted, self.sigs_offset)[0]

    @marks_of_night.setter
    def marks_of_night(self, value: int) -> None:
        if self.sigs_offset < 0:
            raise RuntimeError("slot not parsed")
        struct.pack_into("<I", self.decrypted, self.sigs_offset, value)

    @property
    def entry_count(self) -> int:
        if self.entry_count_offset < 0:
            return 0
        return struct.unpack_from("<I", self.decrypted, self.entry_count_offset)[0]

    @property
    def next_acquisition_id(self) -> int:
        if self.acq_counter_offset < 0:
            return 0
        return struct.unpack_from("<I", self.decrypted, self.acq_counter_offset)[0]

    def all_vessels(self) -> list[VesselLoadout]:
        """Every vessel loadout in the slot (universal per hero and hero-specific)."""
        return [
            v for h in self.heroes.values() for v in h.vessels
        ] + self.unassigned_vessels

    def all_presets(self) -> list[CustomPreset]:
        return [p for h in self.heroes.values() for p in h.presets]

    def _update_entry_count(self) -> None:
        count = sum(1 for e in self.item_entries if not e.is_empty)
        struct.pack_into("<I", self.decrypted, self.entry_count_offset, count)


# ---------------------------------------------------------------------------
# Global profile data (entry 10)
# ---------------------------------------------------------------------------


@dataclass
class BossRecord:
    """16-byte per-boss run record."""

    best_score: int = 0xFFFF  # 0xFFFF = never attempted
    cleared_score: int = 0xFFFF
    attempts: int = 0
    unk: int = 0
    abs_offset: int = -1

    @classmethod
    def from_bytes(cls, data: bytearray, abs_offset: int) -> BossRecord:
        obj = cls()
        obj.abs_offset = abs_offset
        obj.best_score = struct.unpack_from("<H", data, abs_offset)[0]
        obj.cleared_score = struct.unpack_from("<H", data, abs_offset + 4)[0]
        obj.attempts = struct.unpack_from("<I", data, abs_offset + 8)[0]
        obj.unk = struct.unpack_from("<I", data, abs_offset + 12)[0]
        return obj

    @property
    def attempted(self) -> bool:
        return self.best_score != 0xFFFF

    def write_to(self, data: bytearray) -> None:
        struct.pack_into("<H", data, self.abs_offset, self.best_score)
        struct.pack_into("<H", data, self.abs_offset + 4, self.cleared_score)
        struct.pack_into("<I", data, self.abs_offset + 8, self.attempts)
        struct.pack_into("<I", data, self.abs_offset + 12, self.unk)


@dataclass
class HeroProfile:
    """
    Per-hero profile inside entry 10 (one of 10 blocks of 0x290 bytes).
    Contains character name, run count, and appearance data.
    """

    hero_type: int = 0  # 1-10
    hero_index: int = 0  # 0-9
    active: bool = False
    hero_name: str = ""
    total_runs: int = 0
    timestamp: int = 0
    appearance: list[bytearray] = field(default_factory=list)  # up to 4 * 288 bytes
    abs_offset: int = -1  # base of this 0x290 block in entry 10

    @classmethod
    def from_bytes(
        cls, data: bytearray, hero_index: int, abs_offset: int
    ) -> HeroProfile:
        obj = cls()
        obj.abs_offset = abs_offset
        obj.hero_index = hero_index
        obj.hero_type = hero_index + 1
        obj.active = (
            struct.unpack_from("<I", data, abs_offset + _HERO_ACTIVE_FLAG)[0] == 1
        )
        raw_name = data[
            abs_offset + _HERO_NAME_OFFSET : abs_offset + _HERO_NAME_OFFSET + 30
        ]
        obj.hero_name = raw_name.decode("utf-16-le", errors="ignore").rstrip("\x00")
        obj.total_runs = struct.unpack_from("<I", data, abs_offset + _HERO_TOTAL_RUNS)[
            0
        ]
        obj.timestamp = struct.unpack_from("<I", data, abs_offset + _HERO_TIMESTAMP)[0]
        # Parse appearance slots if FACE magic is present
        face_off = abs_offset + _HERO_FACE_MAGIC
        if data[face_off : face_off + 4] == b"FACE":
            count = struct.unpack_from("<I", data, face_off + 4)[0]
            entry_sz = struct.unpack_from("<I", data, face_off + 8)[0]
            data_off = face_off + 12
            for _ in range(min(count, 4)):
                obj.appearance.append(bytearray(data[data_off : data_off + entry_sz]))
                data_off += entry_sz
        return obj

    def write_to(self, data: bytearray) -> None:
        name_bytes = self.hero_name.encode("utf-16-le").ljust(30, b"\x00")[:30]
        data[
            self.abs_offset + _HERO_NAME_OFFSET : self.abs_offset
            + _HERO_NAME_OFFSET
            + 30
        ] = name_bytes
        struct.pack_into(
            "<I", data, self.abs_offset + _HERO_TOTAL_RUNS, self.total_runs
        )

    @property
    def default_name(self) -> str:
        return (
            HERO_NAMES[self.hero_index]
            if self.hero_index < len(HERO_NAMES)
            else f"Hero{self.hero_type}"
        )


@dataclass
class NightreignProfile:
    """
    Parsed global profile data (entry 10).
    All offset fields are absolute positions within entry 10 decrypted data.
    """

    decrypted: bytearray = field(default_factory=bytearray)
    steam_id: int = 0

    # Deep of Night progress
    don_rank: int = 1
    don_max_rank: int = 1
    don_score: int = 0
    don_nightlord_prog: int = 0
    run_count: int = 0
    boss_records: list[BossRecord] = field(default_factory=list)

    # Per-hero profiles
    hero_profiles: list[HeroProfile] = field(default_factory=list)

    def set_don_rank(self, value: int) -> None:
        """Write Deep of Night rank directly to decrypted data."""
        self.don_rank = value
        struct.pack_into("<I", self.decrypted, _E10_DON_RANK, value)

    def set_don_score(self, value: int) -> None:
        """Write Deep of Night score/exp to decrypted data."""
        self.don_score = value
        struct.pack_into("<I", self.decrypted, _E10_DON_SCORE, value)

    def set_run_count(self, value: int) -> None:
        struct.pack_into("<I", self.decrypted, _E10_RUN_COUNT, value)
        self.run_count = value


# ---------------------------------------------------------------------------
# Slot parser
# ---------------------------------------------------------------------------


def _iter_item_states(data: bytearray, start: int, count: int):
    """
    Yield (ga_handle, type_bits, state_size, abs_offset) for each state slot.
    Advances cursor by each state's variable size.
    """
    cursor = start
    for _ in range(count):
        ga_handle = struct.unpack_from("<I", data, cursor)[0]
        type_bits = ga_handle & 0xF0000000
        size = _STATE_SIZE.get(type_bits, 8)
        yield ga_handle, type_bits, size, cursor
        cursor += size
    return cursor


def _parse_slot(dec: bytearray, slot_index: int) -> NightreignSlot:
    """
    Parse a decrypted character slot into a NightreignSlot.
    All offsets stored as absolute positions within dec.
    """
    slot = NightreignSlot(slot_index=slot_index, decrypted=dec)

    # --- Item state section ---
    cursor = 0x14  # START_OFFSET
    free_state_indices: list[int] = []

    for i in range(STATE_SLOT_COUNT):
        ga_handle = struct.unpack_from("<I", dec, cursor)[0]
        type_bits = ga_handle & 0xF0000000
        size = _STATE_SIZE.get(type_bits, 8)

        slot.item_states.append((ga_handle, size, cursor))

        if type_bits == ITEM_TYPE_RELIC and ga_handle != 0:
            rs = RelicState.from_bytes(dec, cursor, i)
            slot.relic_states[ga_handle] = rs
        elif ga_handle == 0 and i >= STATE_KEEP_START:
            free_state_indices.append(i)

        cursor += size

    # --- Player name, currencies ---
    cursor += 0x94
    slot.name_offset = cursor
    slot.sigs_offset = cursor - 64
    slot.murk_offset = cursor + 52

    # --- Item entry section ---
    cursor += 0x5B8
    slot.entry_count_offset = cursor
    cursor += 4
    slot.entry_offset = cursor

    for _i in range(ENTRY_SLOT_COUNT):
        entry = ItemEntry.from_bytes(dec, cursor)
        slot.item_entries.append(entry)
        if entry.is_relic and not entry.is_empty:
            slot.relics[entry.ga_handle] = entry
        cursor += 14

    # --- Next acquisition counter, relic loadout chunk ---
    entries_end = cursor
    slot.acq_counter_offset = entries_end + _ACQ_COUNTER_REL
    info = _parse_loadout_header(dec, entries_end + _LOADOUT_REL)
    if info is None:
        return slot  # empty slot or unknown chunk layout
    slot.loadout = info
    if info.presets_rel > info.chunk_size:
        return slot  # vessel data alone exceeds the chunk; layout unknown
    cursor = info.offset + _LOADOUT_HEADER_SZ

    def read_vessel(off: int) -> VesselLoadout:
        return VesselLoadout(
            vessel_id=struct.unpack_from("<I", dec, off)[0],
            relics=list(struct.unpack_from("<6I", dec, off + 4)),
            vessel_offset=off,
            relics_offset=off + 4,
        )

    for _ in range(info.hero_count):
        h_start = cursor
        hero_type = dec[cursor]
        preset_idx = dec[cursor + 1]
        cur_vessel = struct.unpack_from("<I", dec, cursor + 4)[0]
        cursor += 8
        vessels = []
        for _ in range(info.universal_count):
            vessels.append(read_vessel(cursor))
            cursor += _VESSEL_SZ
        slot.heroes[hero_type] = HeroLoadout(
            hero_type=hero_type,
            cur_preset_idx=preset_idx,
            cur_vessel_id=cur_vessel,
            vessels=vessels,
            hero_base_offset=h_start,
        )

    # Hero-specific vessels; the thousands digit of the ID is the hero_type
    for _ in range(info.hero_vessel_count):
        v = read_vessel(cursor)
        cursor += _VESSEL_SZ
        hero = slot.heroes.get(v.vessel_id // 1000)
        if hero is not None:
            hero.vessels.append(v)
        else:
            slot.unassigned_vessels.append(v)
    # On overflow the game writes only the presets that fit in the chunk
    cursor = info.presets_offset
    for i in range(info.presets_that_fit):
        p_base = cursor
        cursor += _PRESET_SZ
        hero_id = dec[p_base + 1]
        if hero_id == 0:
            slot.free_presets.append(p_base)
            continue
        preset = CustomPreset(
            hero_id=hero_id,
            counter=dec[p_base + 3],
            name=dec[p_base + 4 : p_base + 40]
            .decode("utf-16-le", errors="ignore")
            .rstrip("\x00"),
            vessel_id=struct.unpack_from("<I", dec, p_base + 44)[0],
            relics=list(struct.unpack_from("<6I", dec, p_base + 48)),
            timestamp=struct.unpack_from("<Q", dec, p_base + 72)[0],
            abs_offset=p_base,
            index=i,
        )
        if hero_id in slot.heroes:
            slot.heroes[hero_id].presets.append(preset)

    return slot


def _parse_loadout_header(dec: bytearray, offset: int) -> LoadoutInfo | None:
    """Read the loadout chunk header at offset, or None if it is not there."""
    if offset + _LOADOUT_HEADER_SZ > len(dec):
        return None
    chunk_id, _ver, size = struct.unpack_from("<HHI", dec, offset)
    if chunk_id != _LOADOUT_CHUNK_ID:
        return None
    _unk, heroes, universal, hero_vessels, presets = struct.unpack_from(
        "<5H", dec, offset + 8
    )
    info = LoadoutInfo(
        offset=offset,
        chunk_size=size,
        hero_count=heroes,
        universal_count=universal,
        hero_vessel_count=hero_vessels,
        preset_count=presets,
    )
    if offset + 8 + size > len(dec):
        return None
    return info


# ---------------------------------------------------------------------------
# Profile parser (entry 10)
# ---------------------------------------------------------------------------


def _parse_profile(dec: bytearray) -> NightreignProfile:
    """Parse decrypted entry 10 into NightreignProfile."""
    prof = NightreignProfile(decrypted=dec)
    prof.steam_id = struct.unpack_from("<Q", dec, _E10_STEAM_ID)[0]
    prof.don_rank = struct.unpack_from("<I", dec, _E10_DON_RANK)[0]
    prof.don_max_rank = struct.unpack_from("<I", dec, _E10_DON_MAX_RANK)[0]
    prof.don_score = struct.unpack_from("<I", dec, _E10_DON_SCORE)[0]
    prof.don_nightlord_prog = struct.unpack_from("<I", dec, _E10_DON_NL_PROG)[0]
    prof.run_count = struct.unpack_from("<I", dec, _E10_RUN_COUNT)[0]

    for i in range(16):
        off = _E10_BOSS_RECORDS + i * 16
        prof.boss_records.append(BossRecord.from_bytes(dec, off))

    for i in range(10):
        off = _E10_HERO_BASE + i * _E10_HERO_STRIDE
        prof.hero_profiles.append(HeroProfile.from_bytes(dec, i, off))

    return prof


def _filetime_now() -> int:
    """Current local time as a Windows FILETIME, the preset timestamp format."""
    delta = datetime.now() - datetime(1601, 1, 1)
    return (delta.days * 86400 + delta.seconds) * 10_000_000 + delta.microseconds * 10


def _preset_index(slot: NightreignSlot, abs_offset: int) -> int:
    """Index in the preset array of the preset block at abs_offset."""
    return (abs_offset - slot.loadout.presets_offset) // _PRESET_SZ


def _refresh_slot(slot: NightreignSlot) -> None:
    """Re-parse a slot in place after its loadout bytes changed."""
    fresh = _parse_slot(slot.decrypted, slot.slot_index)
    slot.__dict__.update(fresh.__dict__)


# ---------------------------------------------------------------------------
# Top-level save file
# ---------------------------------------------------------------------------


@dataclass
class NightreignSave:
    """
    Complete parsed Nightreign save file.

    Usage:
        save = NightreignSave.from_file("NR0000.sl2")
        slot = save.slots[0]
        print(slot.player_name, slot.murk)
        slot.murk = 99999
        save.write_file("NR0000_modified.sl2")
    """

    raw: bytearray = field(default_factory=bytearray)
    entries: list[BND4Entry] = field(default_factory=list)  # all 14 entries, decrypted

    # Parsed high-level views
    slots: list[NightreignSlot] = field(default_factory=list)  # entries 0-9
    profile: NightreignProfile | None = None  # entry 10

    @property
    def declared_end(self) -> int:
        """End of the last entry according to the BND4 header."""
        return max(e.data_offset + e.size for e in self.entries)

    @property
    def trailing_bytes(self) -> int:
        """Bytes past declared_end, left by relic spawns before the size fix."""
        return max(0, len(self.raw) - self.declared_end)

    @classmethod
    def from_file(cls, path: str | Path) -> NightreignSave:
        raw = bytearray(Path(path).read_bytes())
        return cls.from_bytes(raw)

    @classmethod
    def from_bytes(cls, raw: bytes | bytearray) -> NightreignSave:
        raw = bytearray(raw)
        entries = _parse_bnd4_entries(raw)
        slots = [_parse_slot(entries[i].decrypted, i) for i in range(10)]
        profile = _parse_profile(entries[10].decrypted)
        return cls(raw=raw, entries=entries, slots=slots, profile=profile)

    def write_file(self, path: str | Path) -> None:
        """Re-encrypt all modified entries and write save file."""
        out = bytearray(self.raw)
        for entry in self.entries:
            enc = entry.patch_and_encrypt()
            if len(enc) != entry.size:
                raise ValueError(
                    f"Entry {entry.index} re-encrypted to {len(enc)} bytes, "
                    f"header declares {entry.size}"
                )
            out[entry.data_offset : entry.data_offset + entry.size] = enc
        del out[self.declared_end :]
        target = Path(path)
        tmp_path = target.with_suffix(target.suffix + ".tmp")
        tmp_path.write_bytes(out)
        tmp_path.replace(target)
        record_write(target)

    def get_active_slots(self) -> list[NightreignSlot]:
        """Return only slots that contain a character."""
        return [s for s in self.slots if not s.is_empty()]

    # --- Convenience edit methods ---

    def set_murk(self, slot_index: int, value: int) -> None:
        self.slots[slot_index].murk = value

    def set_marks_of_night(self, slot_index: int, value: int) -> None:
        self.slots[slot_index].marks_of_night = value

    def set_don_rank(self, value: int) -> None:
        """Set Deep of Night rank in the global profile."""
        if self.profile is None:
            raise RuntimeError("profile not parsed")
        self.profile.set_don_rank(value)

    def set_don_score(self, value: int) -> None:
        if self.profile is None:
            raise RuntimeError("profile not parsed")
        self.profile.set_don_score(value)

    def get_relics(self, slot_index: int) -> dict[int, RelicState]:
        """Return all relic states for a slot keyed by ga_handle."""
        return self.slots[slot_index].relic_states

    def modify_relic(
        self,
        slot_index: int,
        ga_handle: int,
        relic_id: int | None = None,
        effect_1: int | None = None,
        effect_2: int | None = None,
        effect_3: int | None = None,
        curse_1: int | None = None,
        curse_2: int | None = None,
        curse_3: int | None = None,
    ) -> None:
        """Modify relic fields and write changes back to decrypted slot data."""
        slot = self.slots[slot_index]
        rs = slot.relic_states.get(ga_handle)
        if rs is None:
            raise KeyError(
                f"Relic ga_handle 0x{ga_handle:08X} not found in slot {slot_index}"
            )
        if relic_id is not None:
            rs.item_id = 0x80000000 | (relic_id & 0x00FFFFFF)
            rs.durability = rs.item_id
        if effect_1 is not None:
            rs.effect_1 = effect_1
        if effect_2 is not None:
            rs.effect_2 = effect_2
        if effect_3 is not None:
            rs.effect_3 = effect_3
        if curse_1 is not None:
            rs.curse_1 = curse_1
        if curse_2 is not None:
            rs.curse_2 = curse_2
        if curse_3 is not None:
            rs.curse_3 = curse_3
        rs.write_to(slot.decrypted)

    def set_vessel_relics(
        self, slot_index: int, hero_type: int, vessel_id: int, relics: list[int]
    ) -> None:
        """
        Set the 6 relic slots for a vessel and write to slot data.
        relics: list of 6 ga_handles (0 = empty).
        """
        if len(relics) != 6:
            raise ValueError("relics must have exactly 6 elements")
        hero = self.slots[slot_index].heroes.get(hero_type)
        if hero is None:
            raise KeyError(f"hero_type {hero_type} not found in slot {slot_index}")
        vessel = hero.get_vessel(vessel_id)
        if vessel is None:
            raise KeyError(f"vessel_id {vessel_id} not found for hero {hero_type}")
        vessel.relics = relics
        vessel.write_to(self.slots[slot_index].decrypted)

    def update_preset(
        self,
        slot_index: int,
        preset_index: int,
        name: str | None = None,
        relics: list[int] | None = None,
    ) -> None:
        """Rename a preset and/or replace its 6 relic handles (0 = empty)."""
        slot = self.slots[slot_index]
        preset = next((p for p in slot.all_presets() if p.index == preset_index), None)
        if preset is None:
            raise KeyError(f"preset {preset_index} not found in slot {slot_index}")
        if name is not None:
            if len(name) > 18:
                raise ValueError("Preset name cannot exceed 18 characters")
            preset.name = name
        if relics is not None:
            if len(relics) != 6:
                raise ValueError("relics must have exactly 6 elements")
            preset.relics = list(relics)
        preset.write_to(slot.decrypted)

    def create_preset(
        self,
        slot_index: int,
        hero_type: int,
        name: str,
        vessel_id: int,
        relics: list[int],
    ) -> int:
        """Add a preset in the first free slot and return its index.

        Matches the game: the new preset gets counter 0 (newest) and every
        other preset's counter moves up by one. The hero's current preset
        selection is left unchanged.
        """
        slot = self.slots[slot_index]
        if slot.loadout is None:
            raise RuntimeError("slot has no loadout section")
        if hero_type not in slot.heroes:
            raise KeyError(f"hero_type {hero_type} not found in slot {slot_index}")
        if len(name) > 18:
            raise ValueError("Preset name cannot exceed 18 characters")
        if len(relics) != 6:
            raise ValueError("relics must have exactly 6 elements")
        if not slot.free_presets:
            raise RuntimeError("All preset slots are in use")

        dec = slot.decrypted
        for p in slot.all_presets():
            dec[p.abs_offset + 3] = p.counter + 1
        base = min(slot.free_presets)
        preset = CustomPreset(
            hero_id=hero_type,
            counter=0,
            name=name,
            vessel_id=vessel_id,
            relics=list(relics),
            timestamp=_filetime_now(),
            abs_offset=base,
        )
        preset.write_to(dec)
        index = _preset_index(slot, base)
        _refresh_slot(slot)
        return index

    def delete_preset(self, slot_index: int, preset_index: int) -> None:
        """Delete a preset without leaving a gap in the preset array.

        The last used preset moves into the freed index (game-written saves
        never contain gaps), counters above the deleted one move down by one,
        and hero selections pointing at the deleted or moved preset follow.
        """
        slot = self.slots[slot_index]
        presets = slot.all_presets()
        target = next((p for p in presets if p.index == preset_index), None)
        if target is None:
            raise KeyError(f"preset {preset_index} not found in slot {slot_index}")
        last = max(presets, key=lambda p: p.index)
        dec = slot.decrypted

        for p in presets:
            if p.counter > target.counter:
                dec[p.abs_offset + 3] = p.counter - 1
        if last.index != target.index:
            dec[target.abs_offset : target.abs_offset + _PRESET_SZ] = dec[
                last.abs_offset : last.abs_offset + _PRESET_SZ
            ]
        dec[last.abs_offset : last.abs_offset + _PRESET_SZ] = _EMPTY_PRESET

        for hero in slot.heroes.values():
            sel_off = hero.hero_base_offset + 1
            if hero.cur_preset_idx == target.index:
                dec[sel_off] = _NO_PRESET
            elif hero.cur_preset_idx == last.index:
                dec[sel_off] = target.index
        _refresh_slot(slot)

    def dump_summary(self, slot_index: int) -> str:
        """Return a human-readable summary of the slot."""
        slot = self.slots[slot_index]
        lines = [f"Slot {slot_index}: {slot.player_name!r}"]
        lines.append(f"  murk: {slot.murk}  Marks of Night: {slot.marks_of_night}")
        lines.append(f"  Relics: {len(slot.relic_states)}")
        lines.append(f"  Entries: {slot.entry_count}")
        if self.profile:
            lines.append(
                f"  Deep of Night Rank: {self.profile.don_rank} (score {self.profile.don_score})"
            )
        return "\n".join(lines)
