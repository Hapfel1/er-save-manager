"""
Dark Souls II: Scholar of the First Sin save file parser.

File layout (DS2SOFS0000.sl2, PC):
  BND4 container, identical shell to DS3/ER saves.

  [0x0000:0x0004]  Magic "BND4"
  [0x000C:0x0010]  Entry count u32 LE (23 in a full 10-slot save)
  [0x0040:0x0040+N*32]  Entry table, 32 bytes per entry

Entry table row (32 bytes at ENTRIES_START + index * ENTRY_STRIDE):
  +0x08  u32  Total entry size in file (checksum + IV + ciphertext)
  +0x10  u32  Absolute data offset in file

Per-entry blob at data_offset:
  [0x00:0x10]  MD5 checksum of (IV + ciphertext)
  [0x10:0x20]  AES-CBC IV (16 bytes)
  [0x20:end]   AES-128-CBC ciphertext

Decrypted plaintext layout (differs from DS3, which uses plain PKCS7):
  [0x00:0x04]  u32 LE length N of the actual game data
  [0x04:0x04+N]  game data
  [0x04+N:]    padding to the next 16-byte boundary, pad byte value == pad_len,
               omitted entirely when already aligned (pad_len == 0)

AES-128-CBC key (all DS2 SOTFS PC saves):
  59 9F 9B 69 96 40 A5 52 36 EE 2D 70 83 5E C7 44

Entry map (23 total):
  0        Global slot-occupancy summary (name + flag per character slot)
  1-10     Per-character profile slot: name, stats, souls, HP, NG+, inventory
  11-20    Per-character large slot (~501KB), one per character slot.
           Holds per-character data (differs between characters starting at
           offset 0x732, identical padding after ~0x5A87F). Mostly unmapped.
           Bonfire levels, the last rested bonfire, NPC flags and NPC kill
           records are located through the bonfire id array (see Bonfires);
           everything else is preserved as-is on save.
  21       Single ~2MB entry: zlib-compressed (8-byte size header, then a
           standard zlib stream) nested BND4 archive of ~170 real entries.
           This is the game's static param/regulation data (EnemyParam,
           ItemParam, WeaponParam, SpEffectParam, RegulationEnglish.fmg,
           etc), embedded for version checking. NOT per-character save
           state; not useful for event flags or world state.
  22       Single ~13KB entry: same per-slot name cache as entry 0 (see
           CHARACTER_SELECT_ENTRY below). Rest of the entry unmapped.

Entry 21 is re-encrypted unchanged on save, and entry 22 only gets its name
cache updated. Entries 11-20 are only changed by bonfire and NPC edits.

Key source: DS2 SOTFS PC AES key from the souls_givifier project (jtesta).
Profile slot field offsets
(name/stats/souls/hp/ng/inventory) from the Dark-Souls-2-Save-Editor-PS4-PC
project
"""

from __future__ import annotations

import struct
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from er_save_manager.games.DS2.bonfire_database import BONFIRES
from er_save_manager.games.DS2.item_database import (
    SEAMLESS_ITEMS,
    SEAMLESS_MAX_STACK,
)
from er_save_manager.games.DS2.npc_database import NPCS, NpcEntry
from er_save_manager.games.DS2.regulation import ClassBase, Regulation

DS2_KEY = bytes.fromhex("599f9b699640a55236ee2d70835ec744")

_BND4_MAGIC = b"BND4"
_ENTRIES_START = 0x40
_ENTRY_STRIDE = 32
_MD5_SIZE = 16
_IV_SIZE = 16
_HEADER_SIZE = _MD5_SIZE + _IV_SIZE

TOTAL_ENTRIES = 23
OCCUPANCY_ENTRY = 0
PROFILE_ENTRY_START = 1
CHARACTER_SLOTS = 10
BIG_ENTRY_START = PROFILE_ENTRY_START + CHARACTER_SLOTS  # 11-20, one per slot

# Profile slot field offsets, relative to the start of a decrypted profile
# entry's game data (entries 1-10).
NAME_OFFSET = 960
NAME_SIZE = 32
# The load screen caches hold the name in 28 bytes.
NAME_MAX_CHARS = 14
SOULS_OFFSET = 60
HP_OFFSET = 72
# Stored 1-based: 1 is the first playthrough, 2 is NG+1, and so on.
# Character.new_game_plus exposes the 0-based cycle.
NG_OFFSET = 1028
NG_PLUS_MAX = 7

# Souls gained in total and in the current cycle, both u32. The game adds
# every soul gained to both; the cycle count restarts on NG+. Online
# matchmaking uses the total. Over one in-game session soul memory rose by
# exactly the souls gained (28730), and the two counts match on every
# unedited first-cycle character.
SOUL_MEMORY_OFFSET = 0x40
SOUL_MEMORY_CYCLE_OFFSET = 0x44

# Starting class, a u32 holding PlayerStatusParam row id / 10 - 1. Every
# unedited character's attributes are at or above that row's (12 characters,
# 6 classes); Bandit and Deprived are unconfirmed on a real character.
# Created-but-unused slots hold Deprived. The load screen caches in entries 0
# and 22 keep a u16 copy (see _CACHE_CLASS_FROM_NAME).
STARTING_CLASS_OFFSET = 0x400
STARTING_CLASSES = {
    1: "Warrior",
    2: "Knight",
    4: "Bandit",
    6: "Cleric",
    7: "Sorcerer",
    8: "Explorer",
    9: "Swordsman",
    10: "Deprived",
}

# Remaining torch time in seconds, a float32.
TORCH_TIME_OFFSET = 0x11E94

# Profile order of the attributes matches the game's class param rows:
# vigor, endurance, vitality, attunement, strength, dexterity,
# intelligence, faith, adaptability.
STAT_OFFSETS = {
    "level": 0x38,
    "vigor": 0x20,
    "attunement": 0x26,
    "endurance": 0x22,
    "vitality": 0x24,
    "strength": 0x28,
    "dexterity": 0x2A,
    "intelligence": 0x2C,
    "faith": 0x2E,
    "adaptability": 0x30,
}

LEVEL_STAT_KEYS = [k for k in STAT_OFFSETS if k != "level"]


INVENTORY_START = 0x1E2C
INVENTORY_END = 0x10E1C
INVENTORY_SLOT_SIZE = 16

# Equipment block in the profile entry: a u32 header, then equipped items by
# item id (u32 each, 0xFFFFFFFF for an empty slot). Which carried entry a slot
# uses is in the index table at EQUIPMENT_INDEX_OFFSET:
#   +0x04  6 weapon slots, left and right hand alternating; 3400000 is the
#          unarmed placeholder
#   +0x1C  4 armor slots (head, chest, hands, legs) holding the armor param
#          id, which is the inventory item id minus 10000000
#   +0x2C  2 u32 of unknown use (0 on every character seen)
#   +0x34  4 slots, empty on every character seen (arrows and bolts)
#   +0x44  4 ring slots
#   +0x54  10 belt item slots
# Mapped from a before/after pair with a weapon, a helm, a ring and a belt
# item changed in game, and checked on every created character of two saves.
# The attuned spells follow the block (outside the load screen's copy) as 14
# slots packed from the first, one per spell whatever its slot cost. Mapped
# from a before/after pair attuning two 1-slot spells and one attuning the
# 3-slot Affinity alone, which took a single slot.
EQUIPMENT_OFFSET = 0x188
EQUIPMENT_HEADER = 0x1E
_EQUIP_WEAPONS = (0x04, 6)
_EQUIP_ARMOR = (0x1C, 4)
_EQUIP_AMMO = (0x34, 4)
_EQUIP_RINGS = (0x44, 4)
_EQUIP_BELT = (0x54, 10)
_EQUIP_SPELLS = (0x7C, 14)
_UNARMED_ID = 3400000
_ARMOR_ID_OFFSET = 10000000
_EMPTY_EQUIP = 0xFFFFFFFF
# Armor param ids of the bare head, chest, hands and legs, held by an armor
# slot with nothing equipped.
_BARE_ARMOR_IDS = (11001100, 11001101, 11001102, 11001103)

# Which carried entry each equipment slot uses: u16 inventory positions
# (index into the list at INVENTORY_START), 0xFFFF for an empty slot. Weapons
# are ordered right then left hand per set (R1, L1, R2, L2, R3, L3), the
# reverse pairing of the id block, then 4 armor, 4 ring, 4 ammo, 10 belt and
# 14 spell slots. Mapped from the before/after pairs above (the equip write
# rebuilt from each matches the game's byte for byte) and checked against the
# weapon, armor, ring and belt slots of 10 characters.
EQUIPMENT_INDEX_OFFSET = 0x11E30
_INDEX_WEAPONS = 0
_INDEX_ARMOR = 6
_INDEX_RINGS = 10
_INDEX_BELT = 18
_INDEX_SPELLS = 28

# u8 index of the selected attuned spell, 0xFF with none selected. The game
# set it from 0xFF to 0 on attuning a first spell in both spell pairs, and it
# is 0 on every character seen with a spell attuned.
_SELECTED_SPELL_OFFSET = 0x10E2D
_NO_SELECTED_SPELL = 0xFF

# Equippable items that add attunement slots, by item id: Black Witch Hat and
# Southern Ritual Band, +1 and +2. Their effect is a SpEffect, which the
# embedded params do not include, so the counts are soulsplanner.com's.
_ATTUNEMENT_SLOT_ITEMS = {21501100: 1, 40350000: 1, 40350001: 2, 40350002: 3}
_EMPTY_INDEX = 0xFFFF

# Entry 22 keeps a copy of every slot's equipment block for the load screen,
# at this offset plus _OCC_STRIDE per slot. It matched the profile's block on
# 124 of 128 created characters; the rest had never been written.
_SELECT_EQUIPMENT_OFFSET = 0xD0
_EQUIPMENT_BLOCK_SIZE = 0x7C

# Passed to Character.equip for a slot to leave unchanged.
KEEP_SLOT = object()

# Stack limit used for items the regulation does not know.
_DEFAULT_MAX_STACK = 99
_SEAMLESS_IDS = frozenset(
    int.from_bytes(bytes.fromhex(h), "little") for h in SEAMLESS_ITEMS.values()
)

# Categories stored in the key item list instead of the main inventory.
KEY_LIST_CATEGORIES = frozenset({"keys", "gestures"})

# Categories where an item can be owned only once.
UNIQUE_CATEGORIES = frozenset({"gestures", "seamless"})

# Non-stackable categories where quantity means separate inventory entries.
MULTI_COPY_CATEGORIES = frozenset({"weapons"})

# Categories whose items carry an upgrade level in their inventory entry.
UPGRADABLE_CATEGORIES = frozenset({"weapons", "armors"})
_UPGRADE_MASK = 0xFF
_INFUSION_SHIFT = 8

# Bit of an inventory entry's unk_1 that marks it as stored in the item box.
# Box items share the main inventory list with carried ones. Moving two stacks
# to the box in game emptied their slots and wrote them, flag set and quantity
# kept, into the slots after the last used entry, in the order they were
# moved. The slot the first move freed was not reused by the second. Carried
# entries hold 0 here.
ITEM_BOX_FLAG = 0x100

KEY_ITEMS_START = 0x10E30
KEY_ITEMS_END = 0x11DF0

# Candidate event/quest/boss flag region in the profile entry. Unmapped,
# only used by the WIP world state tab.
FLAG_REGION_START = 0x11E00
FLAG_REGION_END = 0x1B2FC

# Bonfire state in a slot's large entry. An array of ascending u16 ids, one per
# bonfire in BONFIRES, is followed by one level byte per id. The level array
# starts _BONFIRE_ID_CAPACITY ids after the id array, which is 0x200 bytes at
# two bytes per id. A level is 0 when unlit and 1 when lit, and grows when
# Bonfire Ascetics are used. Saves hold up to two copies of the pair, and a
# slot can lack the second. Both were rewritten when the game lit every bonfire
# on one slot, so every copy found is updated.
_BONFIRE_ID_CAPACITY = 256
# The stored level stops at 99, so a larger byte marks a copy as unreadable.
_BONFIRE_PLAUSIBLE_LEVEL = 99
# Highest level the editor writes. Difficulty stops rising at level 8 while the
# stored level keeps counting up to 99.
BONFIRE_MAX_LEVEL = 8

# Two more structures sit at fixed distances from the first bonfire id array in
# the same entry, so they are found through it. Every slot with bonfire data
# has them at these distances.
# - The last rested bonfire is a u32 id, _LAST_RESTED_AFTER_IDS bytes after the
#   id array. It held a valid bonfire id in all four saved characters checked
#   and nowhere else in the entry did.
# - The NPC flag object starts _NPC_FLAGS_BEFORE_IDS bytes before the id array.
#   Killing an NPC changed exactly that NPC's two flag bytes in the layout the
#   cheat tables describe.
_LAST_RESTED_AFTER_IDS = 0xC04
_NPC_FLAGS_BEFORE_IDS = 0x15A0
# Bytes a kill writes for each NPC, as (offset from the first bonfire id
# array, length in bytes). They are zero while the NPC was never killed.
# Everyone except Lenigrast has a single-byte marker, 0 while alive and 1 once
# killed. Kills checked against a before/after save pair:
# - Lenigrast (full record, matched the game's save byte for byte), Herald,
#   Melentia, Gavlan: two kills each.
# - Strowen: four kills.
# - Gilligan, Milibeth, Grandahl, Saulden: one kill, 0 in every other sample
#   including the 64 bytes around each marker.
# - Creighton, Benhart, Maughlin, Navlaan, Magerold, Cromwell, Rat King, Tark,
#   Targray, Pate: kill count not recorded.
# Unconfirmed entries are marked below. Earlier larger records for Herald and
# Melentia came from a volatile buffer that changes on ordinary play and were
# false positives.
_NPC_KILL_RECORDS: dict[str, tuple[tuple[int, int], ...]] = {
    "Blacksmith Lenigrast": (
        (-0x27576, 1),
        (-0x27440, 4),
        (-0x27040, 2),
        (-0x2703D, 1),
        (-0x5B8, 2),
        (0x5A94, 2),
        (0x119C, 6),
        (0x11A4, 4),
    ),
    "Emerald Herald": ((-0x27570, 1),),
    "Merchant Hag Melentia": ((-0x26A72, 1),),
    "Laddersmith Gilligan": ((-0x24948, 1),),
    "Housekeeper Milibeth": ((-0x28098, 1),),
    "Strowen": ((-0x28095, 1),),
    "Darkdiver Grandahl": ((-0x1F0C8, 1),),
    "Lonesome Gavlan": ((-0x23E34, 1),),
    "Saulden, the Crestfallen Warrior": ((-0x27582, 1),),
    "Creighton the Wanderer": ((-0x21D08, 1),),
    "Benhart of Jugo": ((-0x129A8, 1),),
    "Maughlin the Armourer": ((-0x27580, 1),),
    "Royal Sorcerer Navlaan": ((-0x13FC6, 1),),
    "Magerold of Lanafir": ((-0x23326, 1),),
    "Cromwell the Pardoner": ((-0x25F60, 1),),
    "The Rat King": ((-0x1E5B8, 1),),
    "Manscorpion Tark": ((-0x1F0C0, 1),),
    "Blue Sentinel Targray": ((-0x1FBD6, 1),),
    "Mild Mannered Pate": ((-0x23E38, 1),),
    # Unconfirmed: each pair shares its only candidate byte, so clearing it may
    # not revive the right NPC.
    "Rosabeth of Melfia": ((-0x129A4, 1),),
    "Stone Trader Chloanne": ((-0x129A4, 1),),
    "Titchy Gren": ((-0x21D04, 1),),
    "Weaponsmith Ornifex": ((-0x21D04, 1),),
    # Unconfirmed: one kill each with two candidate bytes. The one listed is
    # the candidate not shared with another NPC.
    "Steady Hand McDuff": ((-0x25451, 1),),
    "Carhillion of the Fold": ((-0x23E36, 1),),
    "Straid of Olaphis": ((-0x25452, 1),),
    "Felkin the Outcast": ((-0x21D06, 1),),
}
# The byte after Lenigrast's last entry held 0 before his kill and 3 after it,
# but holds other values in slots without that kill, so it is cleared only
# together with a present record.
_LENIGRAST_RECORD_TAIL = 0x11A8

# Occupancy entry (entry 0) layout: fixed stride per character slot.
_OCC_STRIDE = 496
_OCC_FLAG_OFFSET = 892
_OCC_NAME_OFFSET = 1286
_OCC_NAME_SIZE = 28

CHARACTER_SELECT_ENTRY = 22
_SELECT_NAME_OFFSET = 442
_SELECT_NAME_SIZE = 28
# Per-slot load screen record in entries 0 and 22: u16 level at name + 0x4A,
# u16 starting class at name + 0x4C. The class matched the profile's on every
# created character of two saves (15 slots, 6 class values).
_CACHE_LEVEL_FROM_NAME = 0x4A
_CACHE_CLASS_FROM_NAME = 0x4C


class Bonfires:
    """View over the bonfire levels in one slot's large entry.

    The id arrays are found by their content rather than by a fixed offset. A
    copy whose level bytes are implausible is ignored, so unreadable slot data
    yields no blocks.
    """

    def __init__(self, data: bytearray) -> None:
        self._data = data
        self._ids = list(BONFIRES)
        pattern = struct.pack(f"<{len(self._ids)}H", *self._ids)
        self._id_offsets: list[int] = []
        self._level_offsets: list[int] = []
        content = bytes(data)
        start = 0
        while (found := content.find(pattern, start)) != -1:
            levels = found + _BONFIRE_ID_CAPACITY * 2
            end = levels + len(self._ids)
            if end <= len(data) and max(data[levels:end]) <= _BONFIRE_PLAUSIBLE_LEVEL:
                self._id_offsets.append(found)
                self._level_offsets.append(levels)
            start = found + len(pattern)

    @property
    def found(self) -> bool:
        return bool(self._level_offsets)

    @property
    def anchor(self) -> int:
        """Offset of the first bonfire id array, the reference point for the
        other structures stored beside it."""
        return self._id_offsets[0]

    def levels(self) -> dict[int, int]:
        """Bonfire id to level, read from the first copy."""
        base = self._level_offsets[0]
        return {
            bonfire_id: self._data[base + index]
            for index, bonfire_id in enumerate(self._ids)
        }

    @property
    def last_rested(self) -> int | None:
        """Id of the bonfire the character last rested at, or None when the
        stored value is not a known bonfire."""
        offset = self.anchor + _LAST_RESTED_AFTER_IDS
        if offset + 4 > len(self._data):
            return None
        value = struct.unpack_from("<I", self._data, offset)[0]
        return value if value in BONFIRES else None

    def set_lit(self, bonfire_ids: Iterable[int], lit: bool) -> int:
        """Light or unlight bonfires in every copy and return how many changed
        in the first copy. Lighting keeps levels above 0. Unlighting resets the
        level to 0 and never touches the last rested bonfire, since the game
        loads the character there."""
        wanted = {b for b in bonfire_ids if b in BONFIRES}
        if not lit:
            wanted.discard(self.last_rested)
        changed = 0
        for copy, base in enumerate(self._level_offsets):
            for index, bonfire_id in enumerate(self._ids):
                if bonfire_id not in wanted:
                    continue
                current = self._data[base + index]
                if lit and current == 0:
                    self._data[base + index] = 1
                elif not lit and current != 0:
                    self._data[base + index] = 0
                else:
                    continue
                if copy == 0:
                    changed += 1
        return changed

    def set_level(self, bonfire_ids: Iterable[int], level: int) -> int:
        """Set the level of bonfires in every copy and return how many changed
        in the first copy. A level of 1 or more lights an unlit bonfire. Raises
        ValueError outside 1 to BONFIRE_MAX_LEVEL, since level 0 is unlighting,
        which set_lit handles."""
        if not 1 <= level <= BONFIRE_MAX_LEVEL:
            raise ValueError(f"Bonfire level must be 1 to {BONFIRE_MAX_LEVEL}")
        wanted = {b for b in bonfire_ids if b in BONFIRES}
        changed = 0
        for copy, base in enumerate(self._level_offsets):
            for index, bonfire_id in enumerate(self._ids):
                if bonfire_id not in wanted or self._data[base + index] == level:
                    continue
                self._data[base + index] = level
                if copy == 0:
                    changed += 1
        return changed

    def unlock_all(self) -> int:
        """Light every unlit bonfire in every copy and return how many bonfires
        were newly lit in the first copy. Levels above 0 are kept."""
        return self.set_lit(self._ids, True)


@dataclass
class NpcState:
    entry: NpcEntry
    hostile: bool
    dead: bool


class NpcStates:
    """View over the NPC hostile and dead flags in one slot's large entry.

    A flag byte is 0 while clear and holds bits once set, so a flag counts as
    set when its byte is non-zero. An NPC also counts as dead while their kill
    record is stored, because with the record left over they stay dead in game
    even with their flags clear. Reviving clears both flags and the record, which
    is the state before the kill. Calming clears the hostile flag only.
    """

    def __init__(self, data: bytearray, base: int, anchor: int) -> None:
        self._data = data
        self._base = base
        self._anchor = anchor

    def _record_spans(self, name: str) -> list[tuple[int, int]]:
        return [
            (self._anchor + offset, length)
            for offset, length in _NPC_KILL_RECORDS.get(name, ())
            if self._anchor + offset >= 0
            and self._anchor + offset + length <= len(self._data)
        ]

    def _record_present(self, name: str) -> bool:
        return any(any(self._data[o : o + n]) for o, n in self._record_spans(name))

    def _clear_record(self, name: str) -> bool:
        if not self._record_present(name):
            return False
        for offset, length in self._record_spans(name):
            self._data[offset : offset + length] = bytes(length)
        if name == "Blacksmith Lenigrast":
            tail = self._anchor + _LENIGRAST_RECORD_TAIL
            if tail < len(self._data):
                self._data[tail] = 0
        return True

    def states(self) -> list[NpcState]:
        result = []
        for entry in NPCS:
            hostile = entry.hostile is not None and bool(
                self._data[self._base + entry.hostile]
            )
            dead = (
                entry.dead is not None and bool(self._data[self._base + entry.dead])
            ) or self._record_present(entry.name)
            result.append(NpcState(entry, hostile, dead))
        return result

    def revive(self, names: Iterable[str]) -> int:
        """Clear the dead and hostile flags and the kill record of the named
        NPCs and return how many changed."""
        wanted = set(names)
        changed = 0
        for entry in NPCS:
            if entry.name not in wanted:
                continue
            touched = False
            for offset in (entry.hostile, entry.dead):
                if offset is not None and self._data[self._base + offset]:
                    self._data[self._base + offset] = 0
                    touched = True
            if self._clear_record(entry.name):
                touched = True
            changed += touched
        return changed

    def calm(self, names: Iterable[str]) -> int:
        """Clear the hostile flag of the named NPCs and return how many
        changed."""
        wanted = set(names)
        changed = 0
        for entry in NPCS:
            if entry.name not in wanted or entry.hostile is None:
                continue
            if self._data[self._base + entry.hostile]:
                self._data[self._base + entry.hostile] = 0
                changed += 1
        return changed


class SlotState(Enum):
    """What a character slot holds. The values double as display labels."""

    NEVER_CREATED = "never created in-game"
    PRE_CREATION = "pre-character creation"
    CHARACTER = "character"


def _make_padding(data_len: int) -> bytes:
    """Padding so 4 + data_len + len(padding) lands on a 16-byte boundary."""
    pad_len = (16 - ((data_len + 4) % 16)) % 16
    if pad_len == 0:
        return b""
    return bytes([pad_len] * pad_len)


def _decrypt(iv: bytes, ciphertext: bytes) -> bytearray:
    decryptor = Cipher(algorithms.AES(DS2_KEY), modes.CBC(iv)).decryptor()
    plain = decryptor.update(ciphertext) + decryptor.finalize()
    if len(plain) < 4:
        raise ValueError("Decrypted DS2 entry shorter than its length prefix")
    data_len = struct.unpack_from("<I", plain, 0)[0]
    if data_len > len(plain) - 4:
        raise ValueError(
            f"DS2 entry length prefix {data_len} exceeds available plaintext "
            f"({len(plain) - 4} bytes)"
        )
    return bytearray(plain[4 : 4 + data_len])


def _encrypt(iv: bytes, data: bytearray) -> bytes:
    plain = struct.pack("<I", len(data)) + bytes(data) + _make_padding(len(data))
    encryptor = Cipher(algorithms.AES(DS2_KEY), modes.CBC(iv)).encryptor()
    return encryptor.update(plain) + encryptor.finalize()


def _md5(data: bytes) -> bytes:
    import hashlib

    return hashlib.md5(data).digest()


def _read_entry_header(raw: bytes, index: int) -> tuple[int, int]:
    pos = _ENTRIES_START + index * _ENTRY_STRIDE
    size = struct.unpack_from("<I", raw, pos + 8)[0]
    data_offset = struct.unpack_from("<I", raw, pos + 16)[0]
    return size, data_offset


@dataclass
class _Entry:
    index: int
    size: int
    offset: int
    iv: bytes = field(repr=False)
    ciphertext: bytes = field(repr=False)
    _plaintext: bytearray | None = field(default=None, repr=False)


class DS2Container:
    """
    BND4 container for a DS2 SOTFS PC save file.
    """

    def __init__(self, raw: bytearray, entries: list[_Entry]) -> None:
        self._raw = raw
        self._entries = entries

    @classmethod
    def from_file(cls, path: str | Path) -> DS2Container:
        raw = bytearray(Path(path).read_bytes())
        if raw[:4] != _BND4_MAGIC:
            raise ValueError("Not a BND4 file")

        entry_count = struct.unpack_from("<I", raw, 0x0C)[0]
        if entry_count < TOTAL_ENTRIES:
            raise ValueError(
                f"Expected at least {TOTAL_ENTRIES} entries, found {entry_count}"
            )

        entries = []
        for i in range(entry_count):
            size, offset = _read_entry_header(raw, i)
            blob = bytes(raw[offset : offset + size])
            iv = blob[_MD5_SIZE : _MD5_SIZE + _IV_SIZE]
            ciphertext = blob[_HEADER_SIZE:]
            entries.append(_Entry(i, size, offset, iv, ciphertext))

        return cls(raw, entries)

    def get_entry(self, index: int) -> bytearray:
        entry = self._entries[index]
        if entry._plaintext is None:
            entry._plaintext = _decrypt(entry.iv, entry.ciphertext)
        return entry._plaintext

    def set_entry(self, index: int, data: bytearray) -> None:
        self._entries[index]._plaintext = data

    def save_to_file(self, path: str | Path) -> None:
        out = bytearray(self._raw)
        for entry in self._entries:
            if entry._plaintext is None:
                continue
            ciphertext = _encrypt(entry.iv, entry._plaintext)
            new_md5 = _md5(entry.iv + ciphertext)
            blob = new_md5 + entry.iv + ciphertext
            if len(blob) != entry.size:
                raise RuntimeError(
                    f"Entry {entry.index}: re-encrypted size {len(blob)} != "
                    f"original {entry.size}. Plaintext length must not change."
                )
            out[entry.offset : entry.offset + entry.size] = blob

        target = Path(path)
        tmp_path = target.with_suffix(target.suffix + ".tmp")
        tmp_path.write_bytes(bytes(out))
        tmp_path.replace(target)


@dataclass
class InventoryItem:
    offset: int
    item_id: int
    unk_1: int
    quantity: int
    unk_2: int

    @classmethod
    def from_bytes(cls, data: bytes, offset: int) -> InventoryItem:
        item_id, unk_1, quantity, unk_2 = struct.unpack_from("<IIII", data, offset)
        return cls(offset, item_id, unk_1, quantity, unk_2)

    def to_bytes(self) -> bytes:
        return struct.pack("<IIII", self.item_id, self.unk_1, self.quantity, self.unk_2)

    @property
    def in_box(self) -> bool:
        return bool(self.unk_1 & ITEM_BOX_FLAG)

    @in_box.setter
    def in_box(self, stored: bool) -> None:
        if stored:
            self.unk_1 |= ITEM_BOX_FLAG
        else:
            self.unk_1 &= ~ITEM_BOX_FLAG

    # unk_2 packs two bytes for equipment. The low byte is the upgrade level of
    # weapons and armor (seen as 1 and 3 on weapons, 1 and 2 on armor). The
    # next byte is the weapon infusion index (see regulation.INFUSION_NAMES),
    # seen as 1 to 9 on one Rapier per infusion. Each setter keeps the other
    # bytes.
    @property
    def upgrade(self) -> int:
        return self.unk_2 & _UPGRADE_MASK

    @upgrade.setter
    def upgrade(self, level: int) -> None:
        self.unk_2 = (self.unk_2 & ~_UPGRADE_MASK) | (int(level) & _UPGRADE_MASK)

    @property
    def infusion(self) -> int:
        return (self.unk_2 >> _INFUSION_SHIFT) & 0xFF

    @infusion.setter
    def infusion(self, index: int) -> None:
        self.unk_2 = (self.unk_2 & ~(0xFF << _INFUSION_SHIFT)) | (
            (int(index) & 0xFF) << _INFUSION_SHIFT
        )


@dataclass
class BulkAddResult:
    """Outcome counts of Character.add_items_bulk."""

    added: int = 0
    updated: int = 0  # existing stacks that were added onto
    skipped_owned: int = 0  # non-stackable items already owned
    clamped: int = 0  # items whose requested upgrade exceeded their cap
    infusion_fallback: int = 0  # weapons added plain, infusion not allowed
    no_space: int = 0  # entries dropped because no empty slot was left


def parse_inventory(data: bytes, start: int, end: int) -> list[InventoryItem]:
    items = []
    offset = start
    while offset < end:
        items.append(InventoryItem.from_bytes(data, offset))
        offset += INVENTORY_SLOT_SIZE
    return items


def _decode_name(raw: bytes) -> str:
    """Name stored as NUL-terminated UTF-16. Bytes after the terminator are
    ignored, since they can hold leftovers."""
    return raw.decode("utf-16-le", errors="ignore").split("\x00", 1)[0]


def _is_valid_name(name: str) -> bool:
    """Whether a decoded name is a real one rather than uninitialized data.

    The game allows punctuation and non-Latin letters in names, so any
    printable text counts. Never-created slots hold a default profile whose
    name starts with a control character, which fails this check.
    """
    return bool(name.strip()) and name.isprintable() and "\ufffd" not in name


class Character:
    """View over one decrypted profile slot entry (entries 1-10)."""

    def __init__(
        self,
        data: bytearray,
        regulation_source: Callable[[], Regulation] | None = None,
    ) -> None:
        self._data = data
        self._regulation_source = regulation_source

    @property
    def name(self) -> str:
        return _decode_name(bytes(self._data[NAME_OFFSET : NAME_OFFSET + NAME_SIZE]))

    @name.setter
    def name(self, value: str) -> None:
        encoded = value.encode("utf-16-le")[:NAME_SIZE].ljust(NAME_SIZE, b"\x00")
        self._data[NAME_OFFSET : NAME_OFFSET + NAME_SIZE] = encoded

    @property
    def souls(self) -> int:
        return struct.unpack_from("<I", self._data, SOULS_OFFSET)[0]

    @souls.setter
    def souls(self, value: int) -> None:
        struct.pack_into(
            "<I", self._data, SOULS_OFFSET, max(0, min(int(value), 0xFFFFFFFF))
        )

    @property
    def soul_memory(self) -> int:
        return struct.unpack_from("<I", self._data, SOUL_MEMORY_OFFSET)[0]

    @property
    def soul_memory_cycle(self) -> int:
        return struct.unpack_from("<I", self._data, SOUL_MEMORY_CYCLE_OFFSET)[0]

    @property
    def starting_class(self) -> int:
        return struct.unpack_from("<I", self._data, STARTING_CLASS_OFFSET)[0]

    @starting_class.setter
    def starting_class(self, value: int) -> None:
        if value not in STARTING_CLASSES:
            raise ValueError(f"unknown starting class {value}")
        struct.pack_into("<I", self._data, STARTING_CLASS_OFFSET, value)

    @property
    def starting_class_name(self) -> str | None:
        return STARTING_CLASSES.get(self.starting_class)

    def class_base(self, class_id: int | None = None) -> ClassBase | None:
        """Starting level and attributes of a class, the character's own by
        default. None when the class or the regulation is unknown."""
        if class_id is None:
            class_id = self.starting_class
        if class_id not in STARTING_CLASSES:
            return None
        regulation = self._regulation()
        if regulation is None:
            return None
        return regulation.class_base((class_id + 1) * 10)

    def stats_below_class(
        self, stats: dict[str, int], class_id: int | None = None
    ) -> list[str]:
        """Attributes in stats lower than a class (the character's own by
        default) starts with, which no unedited character can have. Empty when
        the class is unknown."""
        base = self.class_base(class_id)
        if base is None:
            return []
        return [name for name, value in stats.items() if value < base.stats[name]]

    def expected_level(self, stats: dict[str, int]) -> int | None:
        """Level the attributes add up to from the class's start, or None when
        the class is unknown."""
        base = self.class_base()
        if base is None:
            return None
        return base.level + sum(stats[name] - base.stats[name] for name in base.stats)

    def required_soul_memory(self) -> int | None:
        """Least soul memory an unedited character with this level and souls
        held can have: the cost of every level-up since the class's start plus
        the souls held. None when the class or level costs are unknown."""
        base = self.class_base()
        regulation = self._regulation()
        if base is None or regulation is None:
            return None
        spent = regulation.level_up_souls(base.level, self.get_stat("level"))
        if spent is None:
            return None
        return spent + self.souls

    def sync_soul_memory(self) -> int:
        """Raise soul memory to required_soul_memory, adding the same amount
        to the cycle count as gaining those souls in game would. Never lowers
        either. Returns the amount added, 0 when unchanged or unknown."""
        required = self.required_soul_memory()
        if required is None or required <= self.soul_memory:
            return 0
        added = min(required, 0xFFFFFFFF) - self.soul_memory
        cycle = min(self.soul_memory_cycle + added, 0xFFFFFFFF)
        struct.pack_into("<I", self._data, SOUL_MEMORY_OFFSET, self.soul_memory + added)
        struct.pack_into("<I", self._data, SOUL_MEMORY_CYCLE_OFFSET, cycle)
        return added

    @property
    def hp(self) -> int:
        return struct.unpack_from("<I", self._data, HP_OFFSET)[0]

    @hp.setter
    def hp(self, value: int) -> None:
        struct.pack_into(
            "<I", self._data, HP_OFFSET, max(0, min(int(value), 0xFFFFFFFF))
        )

    @property
    def torch_seconds(self) -> float:
        return struct.unpack_from("<f", self._data, TORCH_TIME_OFFSET)[0]

    @torch_seconds.setter
    def torch_seconds(self, value: float) -> None:
        struct.pack_into("<f", self._data, TORCH_TIME_OFFSET, max(0.0, float(value)))

    @property
    def new_game_plus(self) -> int:
        stored = struct.unpack_from("<H", self._data, NG_OFFSET)[0]
        return max(0, stored - 1)

    @new_game_plus.setter
    def new_game_plus(self, value: int) -> None:
        stored = int(value) + 1
        struct.pack_into("<H", self._data, NG_OFFSET, max(1, min(stored, 0xFFFF)))

    def get_stat(self, stat_name: str) -> int:
        off = STAT_OFFSETS[stat_name]
        return struct.unpack_from("<H", self._data, off)[0]

    def set_stat(self, stat_name: str, value: int) -> None:
        off = STAT_OFFSETS[stat_name]
        struct.pack_into("<H", self._data, off, max(0, min(int(value), 0xFFFF)))

    def inventory(self) -> list[InventoryItem]:
        return parse_inventory(self._data, INVENTORY_START, INVENTORY_END)

    def key_items(self) -> list[InventoryItem]:
        return parse_inventory(self._data, KEY_ITEMS_START, KEY_ITEMS_END)

    def equipped_item_ids(self) -> set[int]:
        """Inventory item ids the character has equipped (weapons, armor,
        ammo, rings, belt items and attuned spells). Empty when the
        equipment block does not start with its known header, so an unknown
        layout never blocks edits it cannot judge. The block names items by id only, so every carried
        copy of an equipped id counts as possibly equipped."""
        if (
            struct.unpack_from("<I", self._data, EQUIPMENT_OFFSET)[0]
            != EQUIPMENT_HEADER
        ):
            return set()
        ids: set[int] = set()
        for (rel, count), id_offset in (
            (_EQUIP_WEAPONS, 0),
            (_EQUIP_ARMOR, _ARMOR_ID_OFFSET),
            (_EQUIP_AMMO, 0),
            (_EQUIP_RINGS, 0),
            (_EQUIP_BELT, 0),
            (_EQUIP_SPELLS, 0),
        ):
            for k in range(count):
                value = struct.unpack_from(
                    "<I", self._data, EQUIPMENT_OFFSET + rel + 4 * k
                )[0]
                if value not in (_EMPTY_EQUIP, 0, _UNARMED_ID):
                    ids.add(value + id_offset)
        return ids

    def has_equipment_block(self) -> bool:
        return (
            struct.unpack_from("<I", self._data, EQUIPMENT_OFFSET)[0]
            == EQUIPMENT_HEADER
        )

    def attunement_slots(self) -> int | None:
        """Attunement slots from the attunement stat and the equipped items
        that add some. None when the regulation cannot be read."""
        regulation = self._regulation()
        if regulation is None:
            return None
        slots = regulation.attunement_slots(self.get_stat("attunement"))
        if slots is None:
            return None
        return slots + sum(
            _ATTUNEMENT_SLOT_ITEMS.get(item_id, 0)
            for item_id in self.equipped_item_ids()
        )

    def spell_slots(self, item_id: int) -> int | None:
        """Attunement slots a spell takes, or None when unknown."""
        regulation = self._regulation()
        return regulation.spell_slots(item_id) if regulation else None

    def equip(
        self,
        weapons: list[InventoryItem | object | None] = (),
        armor: list[InventoryItem | object | None] = (),
        rings: list[InventoryItem | object | None] = (),
        belt: list[InventoryItem | object | None] = (),
        spells: list[InventoryItem | object | None] = (),
    ) -> None:
        """Equip carried inventory entries; None empties a slot and KEEP_SLOT
        leaves it as it is, as do slots past the end of a list. weapons is
        in the id block's order (L1, R1, L2, R2, L3, R3), armor is head,
        chest, hands, legs. spells is the attunement list, which the game
        keeps packed from the first slot. Ammo is left as it is. Raises
        ValueError for an unknown block layout or an entry that is not
        carried."""
        if not self.has_equipment_block():
            raise ValueError("equipment block not found")
        for entry in (*weapons, *armor, *rings, *belt, *spells):
            if isinstance(entry, InventoryItem) and (
                entry.in_box or not INVENTORY_START <= entry.offset < INVENTORY_END
            ):
                raise ValueError(f"item {entry.item_id} is not carried")

        def write(block_rel, index, k, entry, item_id_for_empty, id_offset=0):
            if entry is KEEP_SLOT:
                return
            struct.pack_into(
                "<I",
                self._data,
                EQUIPMENT_OFFSET + block_rel + 4 * k,
                item_id_for_empty if entry is None else entry.item_id - id_offset,
            )
            position = (
                _EMPTY_INDEX
                if entry is None
                else (entry.offset - INVENTORY_START) // INVENTORY_SLOT_SIZE
            )
            struct.pack_into(
                "<H", self._data, EQUIPMENT_INDEX_OFFSET + 2 * index, position
            )

        for k, entry in enumerate(weapons[: _EQUIP_WEAPONS[1]]):
            # Block L1, R1, ... and index R1, L1, ...: swap within each set.
            write(_EQUIP_WEAPONS[0], _INDEX_WEAPONS + (k ^ 1), k, entry, _UNARMED_ID)
        for k, entry in enumerate(armor[: _EQUIP_ARMOR[1]]):
            write(
                _EQUIP_ARMOR[0],
                _INDEX_ARMOR + k,
                k,
                entry,
                _BARE_ARMOR_IDS[k],
                _ARMOR_ID_OFFSET,
            )
        for k, entry in enumerate(rings[: _EQUIP_RINGS[1]]):
            write(_EQUIP_RINGS[0], _INDEX_RINGS + k, k, entry, _EMPTY_EQUIP)
        for k, entry in enumerate(belt[: _EQUIP_BELT[1]]):
            write(_EQUIP_BELT[0], _INDEX_BELT + k, k, entry, _EMPTY_EQUIP)
        for k, entry in enumerate(spells[: _EQUIP_SPELLS[1]]):
            write(_EQUIP_SPELLS[0], _INDEX_SPELLS + k, k, entry, _EMPTY_EQUIP)
        first_spell = struct.unpack_from(
            "<I", self._data, EQUIPMENT_OFFSET + _EQUIP_SPELLS[0]
        )[0]
        if (
            first_spell not in (_EMPTY_EQUIP, 0)
            and self._data[_SELECTED_SPELL_OFFSET] == _NO_SELECTED_SPELL
        ):
            self._data[_SELECTED_SPELL_OFFSET] = 0

    def equipment_block(self) -> bytes:
        return bytes(
            self._data[EQUIPMENT_OFFSET : EQUIPMENT_OFFSET + _EQUIPMENT_BLOCK_SIZE]
        )

    def write_inventory_slot(self, item: InventoryItem) -> None:
        self._data[item.offset : item.offset + INVENTORY_SLOT_SIZE] = item.to_bytes()

    def raw(self) -> bytearray:
        return self._data

    STACKABLE_CATEGORIES = {"goods", "bolts", "spells", "upgrade"}

    # Fallback durability (float bit pattern) for new weapons, armor and rings
    # when the regulation does not know the item and no owned item can be used
    # as a reference. These are the lowest values seen on game-written items,
    # so they never exceed an item's max.
    _DEFAULT_DURABILITY = {
        "weapons": 0x41F00000,  # 30.0
        "armors": 0x420C0000,  # 35.0
        "rings": 0x428C0000,  # 70.0
    }

    def _regulation(self) -> Regulation | None:
        """The save's regulation, or None when absent or unreadable."""
        if self._regulation_source is None:
            return None
        try:
            return self._regulation_source()
        except ValueError:
            return None

    def max_stack(self, item_id: int) -> int:
        """Largest stack of an item. Falls back to 99 when the regulation does
        not know the item."""
        if item_id in _SEAMLESS_IDS:
            return SEAMLESS_MAX_STACK
        regulation = self._regulation()
        held = regulation.max_held(item_id) if regulation else None
        return held if held else _DEFAULT_MAX_STACK

    def max_upgrade(self, item_id: int, category: str) -> int:
        """Highest upgrade level, or 0 when unknown or the regulation cannot
        be read."""
        regulation = self._regulation()
        return regulation.max_upgrade(item_id, category) if regulation else 0

    def allowed_infusions(self, item_id: int) -> tuple[int, ...]:
        """Infusion indices a weapon can take. Only 0 (plain) when the item
        cannot be infused or the regulation cannot be read."""
        regulation = self._regulation()
        return regulation.allowed_infusions(item_id) if regulation else (0,)

    def _effective_infusion(self, item_id: int, infusion: int) -> int:
        """The requested infusion when the weapon allows it, else 0."""
        return infusion if infusion in self.allowed_infusions(item_id) else 0

    def _region(self, category: str) -> tuple[int, int]:
        if category in KEY_LIST_CATEGORIES:
            return KEY_ITEMS_START, KEY_ITEMS_END
        return INVENTORY_START, INVENTORY_END

    def _find_empty_slot(self, start: int, end: int) -> InventoryItem | None:
        for item in parse_inventory(self._data, start, end):
            if item.item_id == 0:
                return item
        return None

    def _slot_after_last_used(self) -> InventoryItem | None:
        """The empty slot right after the last used entry of the main list, or
        None when the last slot is used."""
        last = None
        for item in parse_inventory(self._data, INVENTORY_START, INVENTORY_END):
            if item.item_id:
                last = item.offset
        offset = INVENTORY_START if last is None else last + INVENTORY_SLOT_SIZE
        if offset >= INVENTORY_END:
            return None
        return InventoryItem.from_bytes(self._data, offset)

    def free_slots(self, category: str) -> int:
        """Number of empty slots in the list a category is stored in."""
        start, end = self._region(category)
        return sum(
            1
            for offset in range(start, end, INVENTORY_SLOT_SIZE)
            if struct.unpack_from("<I", self._data, offset)[0] == 0
        )

    def _find_item(
        self, item_id: int, start: int, end: int, in_box: bool | None = None
    ) -> InventoryItem | None:
        """First entry of an item, limited to box or carried entries when
        in_box is given."""
        for item in parse_inventory(self._data, start, end):
            if item.item_id == item_id and in_box in (None, item.in_box):
                return item
        return None

    def owns(self, item_id: int, include_box: bool = False) -> bool:
        """Whether the character carries the item. Copies in the item box
        count only with include_box."""
        return (
            self._find_item(
                item_id,
                INVENTORY_START,
                INVENTORY_END,
                in_box=None if include_box else False,
            )
            or self._find_item(item_id, KEY_ITEMS_START, KEY_ITEMS_END)
        ) is not None

    def _find_item_anywhere(self, item_id: int) -> InventoryItem | None:
        """Find an item in either list, so entries written to the wrong list
        by older versions can still be edited and removed."""
        return self._find_item(item_id, INVENTORY_START, INVENTORY_END) or (
            self._find_item(item_id, KEY_ITEMS_START, KEY_ITEMS_END)
        )

    def add_item(
        self,
        item_id: int,
        category: str,
        quantity: int = 1,
        stack: bool = True,
        upgrade: int = 0,
        infusion: int = 0,
        in_box: bool = False,
    ) -> bool:
        """Add an item to inventory, or to the item box with in_box (the key
        item list for the categories in KEY_LIST_CATEGORIES, which ignore
        in_box).

        For stackable categories, adds to an existing stack in the same
        location unless stack=False forces a new slot. Returns False if there
        is no empty slot available or the item is in a unique category and
        already owned. The resulting quantity is capped at the item's stack
        limit, the same in the item box as carried, and
        upgrade at its maximum level. A weapon infusion the weapon does not
        allow is written as 0. Adds one entry, see add_copies for several.

        Spells are the exception: quantity and stack are ignored, a new entry
        is always written with a full set of uses, and an existing copy of
        the same spell never blocks or absorbs it, matching how a spell is
        actually learned in game and how owning several copies works.
        """
        # A unique item stored in the item box still counts, or adding one
        # would make a second copy.
        if category in UNIQUE_CATEGORIES and self.owns(item_id, include_box=True):
            return False
        start, end = self._region(category)
        box = in_box and category not in KEY_LIST_CATEGORIES

        if category == "spells":
            # A spell is always learned with a full set of uses, and owning a
            # second copy of the same spell is normal, each with its own use
            # count, so this never merges into an existing entry.
            empty = self._find_empty_slot(start, end)
            if empty is None:
                return False
            new_item = InventoryItem(
                empty.offset, item_id, 0, self.max_stack(item_id), 0
            )
            new_item.in_box = box
            self.write_inventory_slot(new_item)
            return True

        stackable = category in self.STACKABLE_CATEGORIES

        if stackable and stack:
            existing = self._find_item(item_id, start, end, in_box=box)
            if existing is not None:
                existing.quantity = min(
                    existing.quantity + int(quantity), self.max_stack(item_id)
                )
                self.write_inventory_slot(existing)
                return True

        empty = self._find_empty_slot(start, end)
        if empty is None:
            return False

        if stackable:
            new_item = InventoryItem(
                empty.offset, item_id, 0, min(int(quantity), self.max_stack(item_id)), 0
            )
        elif category in self._DEFAULT_DURABILITY:
            # unk_1 and unk_2 are 0 in game-written entries.
            level = 0
            if category in UPGRADABLE_CATEGORIES:
                level = min(int(upgrade), self.max_upgrade(item_id, category))
            new_item = InventoryItem(
                empty.offset,
                item_id,
                0,
                self._durability_for(item_id, category),
                level,
            )
            if category == "weapons":
                new_item.infusion = self._effective_infusion(item_id, int(infusion))
        else:
            new_item = InventoryItem(empty.offset, item_id, 0, 1, 0)

        new_item.in_box = box
        self.write_inventory_slot(new_item)
        return True

    def _durability_lookup(self, category: str) -> Callable[[int], int]:
        """Return a function mapping an item id to the durability bit pattern
        for a new copy of it.

        Uses the maximum durability from the regulation. Items the regulation
        does not know use the highest durability of an owned copy of the same
        item (an unused copy holds its max), then the lowest durability among
        owned items of the category so the value never exceeds the item's max,
        then _DEFAULT_DURABILITY. The inventory is scanned once, so the result
        reflects the state at call time.
        """
        from er_save_manager.games.DS2.item_database import build_item_db

        def as_float(bits: int) -> float:
            return struct.unpack("<f", struct.pack("<I", bits))[0]

        db = build_item_db()
        best_by_item: dict[int, int] = {}
        same_category: list[int] = []
        for item in parse_inventory(self._data, INVENTORY_START, INVENTORY_END):
            if item.item_id == 0:
                continue
            info = db.get(item.item_id)
            if not info or info[1] != category:
                continue
            same_category.append(item.quantity)
            best = best_by_item.get(item.item_id)
            if best is None or as_float(item.quantity) > as_float(best):
                best_by_item[item.item_id] = item.quantity

        fallback = (
            min(same_category, key=as_float)
            if same_category
            else self._DEFAULT_DURABILITY[category]
        )
        regulation = self._regulation()

        def lookup(item_id: int) -> int:
            maximum = regulation.durability(item_id) if regulation else None
            if maximum is not None:
                return struct.unpack("<I", struct.pack("<f", maximum))[0]
            return best_by_item.get(item_id, fallback)

        return lookup

    def _durability_for(self, item_id: int, category: str) -> int:
        return self._durability_lookup(category)(item_id)

    def _write_entries(
        self,
        item_id: int,
        count: int,
        level: int,
        infusion: int,
        empty: Iterator[InventoryItem],
        durability: Callable[[int], int],
        in_box: bool = False,
    ) -> list[InventoryItem]:
        """Write up to count equipment entries into the empty slots and return
        the entries written, fewer than count when the slots run out."""
        written: list[InventoryItem] = []
        for _ in range(count):
            slot = next(empty, None)
            if slot is None:
                break
            entry = InventoryItem(slot.offset, item_id, 0, durability(item_id), level)
            entry.infusion = infusion
            entry.in_box = in_box
            self.write_inventory_slot(entry)
            written.append(entry)
        return written

    def add_copies(
        self,
        item_id: int,
        category: str,
        count: int,
        upgrade: int = 0,
        infusion: int = 0,
        in_box: bool = False,
    ) -> int:
        """Add count separate entries of one weapon, armor piece or ring, to
        the item box with in_box, with a single inventory scan. Upgrade is clamped to the item's maximum and a
        weapon infusion it does not allow is written as 0. Returns how many
        entries were written, fewer than count when the inventory is full."""
        if category not in self._DEFAULT_DURABILITY:
            raise ValueError(f"{category} has no equipment entries")
        start, end = self._region(category)
        empty = iter(
            [s for s in parse_inventory(self._data, start, end) if s.item_id == 0]
        )
        level = 0
        if category in UPGRADABLE_CATEGORIES:
            level = min(int(upgrade), self.max_upgrade(item_id, category))
        effective = (
            self._effective_infusion(item_id, int(infusion))
            if category == "weapons"
            else 0
        )
        return len(
            self._write_entries(
                item_id,
                max(0, int(count)),
                level,
                effective,
                empty,
                self._durability_lookup(category),
                in_box,
            )
        )

    def add_items_bulk(
        self,
        item_ids: Iterable[int],
        category: str,
        quantity: int = 1,
        upgrade: int = 0,
        infusion: int = 0,
        in_box: bool = False,
    ) -> BulkAddResult:
        """Add many items of one category with a single inventory scan, to the
        item box with in_box (ignored for the key item list).

        Stackable items already in that location get quantity added to their
        stack, matching add_item, capped per item at its stack limit. Owned
        and copy counts only look at that location, except for unique
        categories, where a copy anywhere counts. For
        weapons, quantity is the number of copies wanted of each exact variant
        (same item, upgrade and infusion) and only the missing copies are
        added. Other items already owned are skipped. Upgrade is clamped per
        item to its maximum level. A weapon that does not allow the infusion is
        added plain.

        Spells ignore quantity entirely: one new, fully-charged entry is
        added per id, regardless of copies already owned, matching add_item.
        """
        result = BulkAddResult()
        start, end = self._region(category)
        slots = parse_inventory(self._data, start, end)

        owned: dict[int, InventoryItem] = {}
        variants: Counter[tuple[int, int, int]] = Counter()
        unique = category in UNIQUE_CATEGORIES
        box = in_box and category not in KEY_LIST_CATEGORIES
        for slot in slots:
            if slot.item_id and (unique or slot.in_box == box):
                owned.setdefault(slot.item_id, slot)
                variants[(slot.item_id, slot.upgrade, slot.infusion)] += 1
        empty = iter([slot for slot in slots if slot.item_id == 0])

        is_spell = category == "spells"
        stackable = category in self.STACKABLE_CATEGORIES and not is_spell
        upgradable = category in UPGRADABLE_CATEGORIES
        multi_copy = category in MULTI_COPY_CATEGORIES
        durability = (
            self._durability_lookup(category)
            if category in self._DEFAULT_DURABILITY
            else None
        )

        for item_id in item_ids:
            if is_spell:
                # Same reasoning as add_item: always a new, fully-charged
                # entry, never merged into one already owned.
                slot = next(empty, None)
                if slot is None:
                    result.no_space += 1
                    continue
                new_item = InventoryItem(
                    slot.offset, item_id, 0, self.max_stack(item_id), 0
                )
                new_item.in_box = box
                self.write_inventory_slot(new_item)
                result.added += 1
                continue

            existing = owned.get(item_id)
            if existing is not None and stackable:
                existing.quantity = min(
                    existing.quantity + int(quantity), self.max_stack(item_id)
                )
                self.write_inventory_slot(existing)
                result.updated += 1
                continue
            if existing is not None and not multi_copy:
                result.skipped_owned += 1
                continue

            level = 0
            if upgradable:
                level = min(int(upgrade), self.max_upgrade(item_id, category))
            effective = (
                self._effective_infusion(item_id, int(infusion)) if multi_copy else 0
            )

            wanted = 1
            if multi_copy:
                wanted = max(0, int(quantity)) - variants[(item_id, level, effective)]
                if wanted <= 0:
                    result.skipped_owned += 1
                    continue

            if stackable:
                slot = next(empty, None)
                if slot is None:
                    result.no_space += 1
                    continue
                new_item = InventoryItem(
                    slot.offset,
                    item_id,
                    0,
                    min(int(quantity), self.max_stack(item_id)),
                    0,
                )
                new_item.in_box = box
                self.write_inventory_slot(new_item)
                owned[item_id] = new_item
                result.added += 1
                continue

            if durability is None:
                slot = next(empty, None)
                if slot is None:
                    result.no_space += 1
                    continue
                new_item = InventoryItem(slot.offset, item_id, 0, 1, 0)
                new_item.in_box = box
                self.write_inventory_slot(new_item)
                owned[item_id] = new_item
                result.added += 1
                continue

            written = self._write_entries(
                item_id, wanted, level, effective, empty, durability, box
            )
            result.added += len(written)
            result.no_space += wanted - len(written)
            if written:
                variants[(item_id, level, effective)] += len(written)
                owned.setdefault(item_id, written[0])
                if upgradable and level < int(upgrade):
                    result.clamped += 1
                if multi_copy and effective != int(infusion):
                    result.infusion_fallback += 1
        return result

    def delete_entry(self, item: InventoryItem) -> bool:
        """Zero the exact inventory slot of an entry, as opposed to delete_item
        which removes the first slot holding the item id. Returns False if the
        slot no longer holds that item."""
        current = InventoryItem.from_bytes(self._data, item.offset)
        if current.item_id != item.item_id:
            return False
        self._data[item.offset : item.offset + INVENTORY_SLOT_SIZE] = bytes(
            INVENTORY_SLOT_SIZE
        )
        return True

    def move_entry(
        self, item: InventoryItem, to_box: bool, stackable: bool
    ) -> InventoryItem:
        """Move an entry between the carried inventory and the item box the
        way the game does: write it with the box flag changed into the slot
        after the last used entry (the first free slot when the list is full
        at the end), then empty its old slot. Returns the moved entry.

        Raises ValueError with the reason when the entry changed since it was
        read, is in the key item list, is already there, has a stack of the
        same item waiting at the destination (how the game merges those is
        not known), would carry more than the stack limit, or no slot is free.
        """
        current = InventoryItem.from_bytes(self._data, item.offset)
        if current.item_id != item.item_id or current.item_id == 0:
            raise ValueError("The entry changed, reload and try again")
        if not INVENTORY_START <= item.offset < INVENTORY_END:
            raise ValueError("Key items cannot be stored in the item box")
        if current.in_box == to_box:
            raise ValueError(
                "Already in the item box" if to_box else "Already in the inventory"
            )
        if stackable:
            if self._find_item(
                current.item_id, INVENTORY_START, INVENTORY_END, in_box=to_box
            ):
                where = "item box" if to_box else "inventory"
                raise ValueError(f"The {where} already has a stack of this item")
            limit = self.max_stack(current.item_id)
            if not to_box and current.quantity > limit:
                raise ValueError(f"Stack is above the carry limit of {limit}")
        empty = self._slot_after_last_used() or self._find_empty_slot(
            INVENTORY_START, INVENTORY_END
        )
        if empty is None:
            raise ValueError("No free inventory slot")

        moved = InventoryItem(
            empty.offset,
            current.item_id,
            current.unk_1,
            current.quantity,
            current.unk_2,
        )
        moved.in_box = to_box
        self.write_inventory_slot(moved)
        self._data[item.offset : item.offset + INVENTORY_SLOT_SIZE] = bytes(
            INVENTORY_SLOT_SIZE
        )
        return moved

    def delete_item(self, item_id: int) -> bool:
        """Zero out the first matching item slot in either list. Returns
        False if not found."""
        existing = self._find_item_anywhere(item_id)
        if existing is None:
            return False
        self._data[existing.offset : existing.offset + INVENTORY_SLOT_SIZE] = bytes(
            INVENTORY_SLOT_SIZE
        )
        return True


class DS2Save:
    """Top-level DS2 SOTFS save: container plus the 10 character slots."""

    def __init__(self, container: DS2Container) -> None:
        self.container = container
        self.characters = [
            Character(
                container.get_entry(PROFILE_ENTRY_START + i),
                regulation_source=lambda: self.regulation,
            )
            for i in range(CHARACTER_SLOTS)
        ]

    @cached_property
    def regulation(self) -> Regulation:
        """Param data embedded in the save, parsed on first use."""
        return Regulation.from_container(self.container)

    @classmethod
    def from_file(cls, path: str | Path) -> DS2Save:
        return cls(DS2Container.from_file(path))

    def slot_occupancy(self) -> dict[int, str]:
        """Character name per occupied slot, read from the entry 0 summary.

        The per-slot flag byte is set once a slot has ever been formatted,
        including slots left as an unnamed level 1 character, so occupancy
        is decided by a non-empty name instead.
        """
        occ_data = self.container.get_entry(OCCUPANCY_ENTRY)
        result: dict[int, str] = {}
        for i in range(CHARACTER_SLOTS):
            name_off = _OCC_NAME_OFFSET + _OCC_STRIDE * i
            if name_off + _OCC_NAME_SIZE > len(occ_data):
                continue
            name = _decode_name(bytes(occ_data[name_off : name_off + _OCC_NAME_SIZE]))
            if _is_valid_name(name):
                result[i] = name
        return result

    def slot_display_name(self, slot_index: int) -> str:
        """Best available name for a slot, or "" if none is trustworthy.

        The profile name is used when it passes _is_valid_name. Otherwise the
        entry 0 cache is used, since slot_occupancy() already filters it. A
        profile name that fails validation is treated as uninitialized data
        and is never returned, so callers do not display garbage characters.
        """
        profile_name = self.characters[slot_index].name
        if _is_valid_name(profile_name):
            return profile_name
        return self.slot_occupancy().get(slot_index, "")

    def sync_name_caches(self) -> None:
        occ_data = self.container.get_entry(OCCUPANCY_ENTRY)
        select_data = self.container.get_entry(CHARACTER_SELECT_ENTRY)

        for i, character in enumerate(self.characters):
            name = character.name
            if not _is_valid_name(name):
                continue
            encoded = name.encode("utf-16-le")[:_OCC_NAME_SIZE].ljust(
                _OCC_NAME_SIZE, b"\x00"
            )

            occ_off = _OCC_NAME_OFFSET + _OCC_STRIDE * i
            if occ_off + _OCC_NAME_SIZE <= len(occ_data):
                occ_data[occ_off : occ_off + _OCC_NAME_SIZE] = encoded

            select_off = _SELECT_NAME_OFFSET + _OCC_STRIDE * i
            if select_off + _SELECT_NAME_SIZE <= len(select_data):
                select_data[select_off : select_off + _SELECT_NAME_SIZE] = encoded

    def sync_level_caches(self) -> None:
        """Copy every named character's level to the load screen records in
        entries 0 and 22."""
        for entry, name_offset in (
            (OCCUPANCY_ENTRY, _OCC_NAME_OFFSET),
            (CHARACTER_SELECT_ENTRY, _SELECT_NAME_OFFSET),
        ):
            data = self.container.get_entry(entry)
            for i, character in enumerate(self.characters):
                if not _is_valid_name(character.name):
                    continue
                off = name_offset + _CACHE_LEVEL_FROM_NAME + _OCC_STRIDE * i
                if off + 2 <= len(data):
                    struct.pack_into("<H", data, off, character.get_stat("level"))

    def sync_equipment_cache(self, slot_index: int) -> None:
        """Copy a slot's equipment block to the load screen's copy in entry
        22, as the game does when it saves."""
        character = self.characters[slot_index]
        if not character.has_equipment_block():
            return
        select_data = self.container.get_entry(CHARACTER_SELECT_ENTRY)
        off = _SELECT_EQUIPMENT_OFFSET + _OCC_STRIDE * slot_index
        if off + _EQUIPMENT_BLOCK_SIZE <= len(select_data):
            select_data[off : off + _EQUIPMENT_BLOCK_SIZE] = character.equipment_block()

    def sync_class_cache(self, slot_index: int) -> None:
        """Copy a slot's starting class to the load screen records in
        entries 0 and 22."""
        value = struct.pack("<H", self.characters[slot_index].starting_class)
        for entry, name_offset in (
            (OCCUPANCY_ENTRY, _OCC_NAME_OFFSET),
            (CHARACTER_SELECT_ENTRY, _SELECT_NAME_OFFSET),
        ):
            data = self.container.get_entry(entry)
            off = name_offset + _CACHE_CLASS_FROM_NAME + _OCC_STRIDE * slot_index
            if off + 2 <= len(data):
                data[off : off + 2] = value

    def clear_name_cache(self, slot_index: int) -> None:
        """Zero the entry 0 / entry 22 cached name for one slot. Needed
        when deleting a slot, since sync_name_caches() only ever writes
        valid-looking names and will not overwrite a stale cached name
        with an empty one on its own.
        """
        occ_data = self.container.get_entry(OCCUPANCY_ENTRY)
        select_data = self.container.get_entry(CHARACTER_SELECT_ENTRY)

        occ_off = _OCC_NAME_OFFSET + _OCC_STRIDE * slot_index
        occ_data[occ_off : occ_off + _OCC_NAME_SIZE] = bytes(_OCC_NAME_SIZE)

        select_off = _SELECT_NAME_OFFSET + _OCC_STRIDE * slot_index
        select_data[select_off : select_off + _SELECT_NAME_SIZE] = bytes(
            _SELECT_NAME_SIZE
        )

    def is_slot_initialized(self, slot_index: int) -> bool:
        """Whether the slot's entry 0 record byte is set. The byte is 0 in
        slots that were never entered, but it is not a dedicated flag: named
        characters hold values such as 76, 102 and 240 there. Only use it for
        slots without a name, see slot_state."""
        occ_data = self.container.get_entry(OCCUPANCY_ENTRY)
        flag_off = _OCC_FLAG_OFFSET + _OCC_STRIDE * slot_index
        if flag_off >= len(occ_data):
            return False
        return occ_data[flag_off] != 0

    def bonfires(self, slot_index: int) -> Bonfires | None:
        """The slot's bonfire levels, or None when the slot holds none."""
        view = Bonfires(self.container.get_entry(BIG_ENTRY_START + slot_index))
        return view if view.found else None

    def npcs(self, slot_index: int) -> NpcStates | None:
        """The slot's NPC flags, or None when the slot holds no bonfire data to
        locate them from."""
        data = self.container.get_entry(BIG_ENTRY_START + slot_index)
        view = Bonfires(data)
        if not view.found:
            return None
        base = view.anchor - _NPC_FLAGS_BEFORE_IDS
        top = max(o for e in NPCS for o in (e.hostile, e.dead) if o is not None)
        if base < 0 or base + top >= len(data):
            return None
        return NpcStates(data, base, view.anchor)

    def slot_state(self, slot_index: int) -> SlotState:
        """Classify a slot.

        A slot with a name always holds a character. The character is named
        in the tutorial, so a slot that has been entered exists before it has
        a name. For unnamed slots the entry 0 record byte tells the two cases
        apart (see is_slot_initialized), since the profile of an unnamed slot
        is the same default character in both.
        """
        if self.slot_display_name(slot_index):
            return SlotState.CHARACTER
        if not self.is_slot_initialized(slot_index):
            return SlotState.NEVER_CREATED
        return SlotState.PRE_CREATION

    def save_to_file(self, path: str | Path) -> None:
        for i, character in enumerate(self.characters):
            self.container.set_entry(PROFILE_ENTRY_START + i, character.raw())
        self.sync_name_caches()
        self.sync_level_caches()
        self.container.save_to_file(path)
