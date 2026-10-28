"""
DS3 decrypted character slot.

All offsets are derived from the slot's own data at parse time: the section
directory in the slot header, the gaitem table walk, and the fixed-size
structures that follow it. Nothing is addressed by absolute position.

=== SLOT HEADER ===

[0x00]  u32  Plaintext size after this field (0xC0000)
[0x04]  u32  Version (0x62)
[0x0C]  u32  Play time, milliseconds
[0x10..0x60]  Section directory, (u32 offset, u32 size) pairs:
  0x10  Player data: everything from the gaitem table to the event flags
  0x18  Player game data: gaitem table through the gesture list
  0x28, 0x30  Two small sections chained after 0x18, inside 0x10; the
              0x30 section is [u32 0][u32 NG+ counter]
  0x38  Event flags ([u32 prefix][flag blocks]), right after 0x10
  0x40, 0x48, 0x50, 0x58  Remaining sections, back to back
The pair at 0x20 is (0x5C, u32 value) and is not a section. The directory
is the only record of section offsets, so any change in data size must
grow the sections containing it and shift every section after it.
Everything after the last section is stale buffer content that the game
ignores, which is what absorbs growth.

=== GAITEM TABLE ===

Starts 4 bytes into the player data section. 6144 entries; entry k holds a
handle whose low 16 bits equal k, or handle 0 when unused. The game
renumbers handles on every save, so handles are position indices.
  Unused / goods / rings: 8 bytes  [u32 handle][u32 item id]
  Weapons (0x8...) and armor (0x9...): 60 bytes
    +0x00 u32 handle   +0x04 u32 item id   +0x08 u32 durability
    +0x0C u32 unknown (0 on new items)     +0x10 u32 1
    +0x14 5 x (u32 0x80000000, u32 0)      empty gem slots
Weapon item ids encode infusion and upgrade: base + infusion*100 + level.
Orphaned weapon/armor entries (no inventory reference) are dropped by the
game on its next save, so removing an item never needs to shrink the table.

=== PLAYER BLOCK (relative to gaitem end) ===

  +0x10 base max HP, +0x1C base max FP, +0x2C base max stamina (u32)
  +0x34 Vigor, Attunement, Endurance, Strength, Dexterity, Intelligence,
        Faith, Luck (u32 each), +0x5C Vitality, +0x60 level, +0x64 souls
  +0x78 name, UTF-16LE, 16 characters + terminator
  +0x9A body type (u8, 1 male, 0 female)
  +0x9E starting class (u8, CharaInitParam row 3000 + class)
  +0xA3 highest weapon upgrade level reached (u8, weapon level matchmaking)
  +0x1F0 22 x u32 equip slots, each an inventory index or 0xFFFFFFFF
  +0x264 22 x u32 item id of each equip slot (type nibble cleared)
  +0x2BC 22 x u32 handle of each equip slot (0 when empty)
  +0x318 inventory
Equip slot order: left/right hand 1-3 (L1 R1 L2 R2 L3 R3), arrow 1, bolt 1,
arrow 2, bolt 2, two unknown slots, head, chest, hands, legs, one unknown
slot, rings 1-4, covenant. An empty hand slot points at a Fists entry, an
empty armor slot at a bare armor entry (item id 900000 + 1000 * piece).
The character-select directory keeps a copy of the 22 item ids.

Further into the player data section sits the appearance block: "FACE",
u32 version 3, u32 block size 0xF4 (header included). Its offset varies
with the data before it. Other players' faces in later sections carry the
same header. Field layout: appearance.py.

=== INVENTORY (same layout for the storage box) ===

  [u32 count] common[0x780]   count is real common items + 2 in held
                              inventory, the exact count in storage
  [u32 count] key[0x80]       key items (goodsType 1), held inventory only
  [u32 count] third[0x80]     unused by editing
  [u32 last index]
Entry: [u32 handle][u32 item id][u32 quantity][u32 index]
  Empty entry: handle 0, item id 0xFFFFFFFF.
  Index low 12 bits: 0x80 + position for common items, position for key
  items (equip slots and quick slots reference this); high 20 bits: sort
  key, param sortId (x100 for weapons and armor, plus weapon level).
Goods and ring handles are the item id with the type nibble replaced by
0xB / 0xA and never have gaitem entries.

After the held inventory:
  14 x (u32 spell id, u32 0xFFFFFFFF) attunement records, packed from the
     first, empty (0xFFFFFFFF, 0)
  s32 selected attunement record, -1 with none (0 on the first attunement)
  10 x (u32 handle, u32 index position) quick items, empty (0, 0xFFFFFFFF)
  u32 unknown, 6 x (u32 handle, u32 index position) unknown item slots
     (Darksign, Black Separation Crystal, White Circlet on new characters)
  then a count-prefixed table of 8-byte records, directly followed by a
  second copy of item ids with the type nibble (0xFFFFFFFF when empty): 22
  equip slots, 10 quick items, 6 unknown item slots. Then the storage box,
  the gesture list and a count-prefixed list of visited region ids.
A quick item record keeps the handle the item had when it was slotted:
upgrading an Estus Flask leaves the record's handle at the old flask.

=== GESTURES ===

41 x [u16 value][u16 k] directly after the storage box. value is
2*(k+1) + unlocked; k is the gesture id from the executable's gesture table.

=== EVENT FLAGS ===

Flags live in 1280-byte blocks of 10 groups x 128 bytes; each group holds
1000 flags as u32 little-endian words with the lowest flag in the most
significant bit. Block 0 holds global flags 0-9999; map flags
(1AAB0000-1AAB9999) use the per-map block in _EVENT_FLAG_BLOCKS.

=== CHARACTER DEATH STATE ===

The section at directory pair 0x40 starts with [u32 0][u32 size] and a CHR
block of that size: [b" RHC"][u32 version], then one record per map the
character has state for, ended by u32 0xFFFFFFFF:
  [u32 map key][u32 record size][u32 bit count][bits, (count + 7) // 8 bytes]
Record size counts the 12 header bytes and the bitfield.
The map key of mAA_BB is AA << 24 | BB << 16. Each bit is one enemy part of
that map's MSB in part order (bit k = byte k // 8, mask 1 << k % 8) and is
set while that character is dead. An NPC whose bit is set is spawned dead
on load, and its death event then sets the dead flag again, so reviving
needs the bit cleared as well as the flags.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, fields
from itertools import pairwise

ITEM_TYPE_WEAPON = 0x80000000
ITEM_TYPE_ARMOR = 0x90000000
ITEM_TYPE_RING = 0xA0000000
ITEM_TYPE_GOOD = 0xB0000000

# Item id type prefixes (upper nibble of the id, not the handle).
ID_WEAPON = 0x0
ID_ARMOR = 0x1
ID_RING = 0x2
ID_GOOD = 0x4
_HANDLE_FOR_ID = {
    ID_WEAPON: ITEM_TYPE_WEAPON,
    ID_ARMOR: ITEM_TYPE_ARMOR,
    ID_RING: ITEM_TYPE_RING,
    ID_GOOD: ITEM_TYPE_GOOD,
}

# --- Slot header ------------------------------------------------------------- #

_PLAY_TIME_OFFSET = 0x0C
_DIR_PLAYER_DATA = 0x10
_DIR_EVENT_FLAGS = 0x38
# Directory pairs that describe byte ranges in the slot, in file order.
_DIR_PAIRS = (0x10, 0x18, 0x28, 0x30, 0x38, 0x40, 0x48, 0x50, 0x58)
_GAITEM_FROM_PLAYER_DATA = 4

# --- Gaitem table ------------------------------------------------------------ #

GAITEM_SLOT_COUNT = 6144
GAITEM_BASE_SIZE = 8
GAITEM_WA_SIZE = 60
_GAITEM_GROWTH = GAITEM_WA_SIZE - GAITEM_BASE_SIZE
_GAITEM_UNKNOWN_ONE = 1
_EMPTY_GEM_SLOT = 0x80000000
_GEM_SLOTS = 5
_WA_HANDLE_FLAGS = 0x00800000

# --- Player block (relative to gaitem end) ----------------------------------- #

_HP_REL = 0x10
_FP_REL = 0x1C
_STAMINA_REL = 0x2C
_STAT_REL = {
    "vig": 0x34,
    "atn": 0x38,
    "end": 0x3C,
    "str": 0x40,
    "dex": 0x44,
    "int": 0x48,
    "fth": 0x4C,
    "lck": 0x50,
    "vit": 0x5C,
}
_LEVEL_REL = 0x60
_SOULS_REL = 0x64
_SOUL_MEMORY_REL = 0x68
_NAME_REL = 0x78
_NAME_LEN = 32  # bytes, 16 UTF-16 code units; a u16 terminator follows
NAME_MAX_CHARS = _NAME_LEN // 2
# u8 starting class, CharaInitParam row 3000 + class (3000-3009 vanilla,
# more rows in Convergence and Cinders).
_CLASS_REL = 0x9E
_BODY_TYPE_REL = 0x9A
# u8 of unknown meaning; the load-screen directory entry mirrors it.
_DIR_MIRROR_U8_REL = 0xA0
# u8 highest weapon upgrade level reached, +5-cap weapons counting double.
# The game raises it on an upgrade and never lowers it, so weapons upgraded
# outside the game leave it stale.
_WEAPON_LEVEL_REL = 0xA3
_FACE_HEADER = b"FACE" + struct.pack("<I", 3)
_FACE_SIZE_FIELD = 8
_EQUIP_SLOTS_REL = 0x1F0
_EQUIP_SLOT_COUNT = 22
_EQUIP_IDS_REL = 0x264
_EQUIP_HANDLES_REL = 0x2BC
# Arm style u32 and six active weapon slot u32s, up to the id block.
_ARM_STYLE_REL = 0x248
_EQUIP_ID_MASK = 0x0FFFFFFF
# Equip slot groups by slot number. Slots 10, 11 and 16 are unidentified.
EQUIP_HANDS = range(6)
EQUIP_AMMO = range(6, 10)
EQUIP_ARMOR = range(12, 16)
EQUIP_RINGS = range(17, 21)
EQUIP_COVENANT = 21
# Arrow slots 6 and 8, bolt slots 7 and 9. Ammo ids are family * 1000:
# thousands digit 0 or 2 for arrows and greatarrows, 4 for bolts.
_EQUIP_BOLT_SLOTS = frozenset({7, 9})
_BOLT_FAMILY_DIGIT = 4
# Covenant items are rings with ids below the first real ring (Life Ring).
_COVENANT_ID_LIMIT = 20000
FISTS_ID = 110000
# Ammo ids, arrows to the last bolt family in any source.
_AMMO_ID_MIN = 400000
_AMMO_ID_END = 500000
BARE_ARMOR_BASE = 900000
_ARMOR_PIECE_STEP = 1000
_INVENTORY_REL = 0x318
ATTUNE_SLOTS = 14
_ATTUNE_RECORD = 8
QUICK_SLOTS = 10
_QUICK_RECORD = 8
# Second id copy: equip slots, then quick items.
_COPY_QUICK_REL = 4 * 22

MAX_STAT = 99
MAX_SOULS = 999_999_999

# --- Inventory --------------------------------------------------------------- #

_ENTRY_SIZE = 16
_COMMON_CAP = 0x780
_KEY_CAP = 0x80
_THIRD_CAP = 0x80
_COMMON_BYTES = 4 + _COMMON_CAP * _ENTRY_SIZE
_KEY_BYTES = 4 + _KEY_CAP * _ENTRY_SIZE
_THIRD_BYTES = 4 + _THIRD_CAP * _ENTRY_SIZE
_INVENTORY_BYTES = _COMMON_BYTES + _KEY_BYTES + _THIRD_BYTES + 4
_COMMON_INDEX_BASE = 0x80
_INDEX_POS_MASK = 0xFFF
_EMPTY_ID = 0xFFFFFFFF
# The game keeps one entry with this handle among new characters' goods.
_PLACEHOLDER_HANDLE = 0xB0FFFFFF

# Held inventory end to the count of an 8-byte record table; the storage
# box count follows that table after a fixed gap.
_TABLE1_FROM_INV_END = 0x118
_TABLE1_ENTRY = 8
_STORAGE_FROM_TABLE1_END = 0x18C

# --- Gestures, NG+ ------------------------------------------------------------ #

GESTURE_COUNT = 41
_GESTURE_ENTRY = 4
_DIR_BEFORE_NG = 0x30
_NG_MAX = 7
# common.emevd event 700 sets flag 50 + cycle for NG..NG+5 and flag 56 for
# NG+6 and above. Flags 57 and 58 are unused by any script; older versions
# of this tool set them, so they are cleared along with the rest.
_LAP_FLAG_BASE = 50
_LAP_FLAG_MAX = 6
_LAP_FLAG_CLEAR = 8

# --- Event flags ------------------------------------------------------------- #

_FLAG_BLOCK_BYTES = 1280
_FLAG_GROUP_BYTES = 128
_FLAG_PREFIX = 4
# Map block key (flag // 10000) to block index, one block per map.
_EVENT_FLAG_BLOCKS = {
    1300: 3,  # High Wall of Lothric
    1301: 4,  # Lothric Castle
    1310: 5,  # Undead Settlement
    1320: 7,  # Archdragon Peak
    1330: 9,  # Road of Sacrifices, Farron Keep
    1341: 11,  # Grand Archives
    1350: 12,  # Cathedral of the Deep
    1370: 15,  # Irithyll, Anor Londo
    1380: 16,  # Catacombs, Smouldering Lake
    1390: 17,  # Irithyll Dungeon, Profaned Capital
    1400: 18,  # Cemetery of Ash, Firelink Shrine, Untended Graves
    1410: 19,  # Kiln of the First Flame
    1450: 20,  # Painted World of Ariandel
    1500: 23,  # The Dreg Heap
    1510: 24,  # The Ringed City
    1511: 25,  # Filianore's Rest
}
_GLOBAL_FLAG_LIMIT = 10000

# --- Character death state --------------------------------------------------- #

_DIR_CHR_STATE = 0x40
_CHR_SECTION_HEADER = 8
_CHR_MAGIC = b" RHC"
_CHR_BLOCK_HEADER = 8
_CHR_MAP_HEADER = 12
_CHR_END = 0xFFFFFFFF


class LayoutError(Exception):
    """The slot does not match the known DS3 layout."""


def _read_u32(data: bytearray, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _write_u32(data: bytearray, off: int, val: int) -> None:
    struct.pack_into("<I", data, off, val & 0xFFFFFFFF)


def _scan_gaitem(data: bytearray, start: int) -> int:
    """Return the offset just past the gaitem table starting at start."""
    offset = start
    for _ in range(GAITEM_SLOT_COUNT):
        handle = _read_u32(data, offset)
        if handle and handle & 0xF0000000 in (ITEM_TYPE_WEAPON, ITEM_TYPE_ARMOR):
            offset += GAITEM_WA_SIZE
        else:
            offset += GAITEM_BASE_SIZE
    return offset


def id_kind(item_id: int) -> int:
    """Return the id type prefix (ID_WEAPON, ID_ARMOR, ID_RING, ID_GOOD)."""
    return item_id >> 28


@dataclass
class DS3GaitemEntry:
    handle: int
    item_id: int
    offset: int
    size: int

    @property
    def type_bits(self) -> int:
        return self.handle & 0xF0000000

    @property
    def is_empty(self) -> bool:
        return self.handle == 0


@dataclass
class DS3InventoryEntry:
    handle: int
    item_id: int
    quantity: int
    index: int
    offset: int
    position: int
    is_key: bool = False

    @property
    def type_bits(self) -> int:
        return self.handle & 0xF0000000

    @property
    def is_empty(self) -> bool:
        return self.handle == 0 or self.item_id == _EMPTY_ID


@dataclass
class _Layout:
    gaitem_start: int
    gaitem_end: int
    inv: int  # held inventory count field
    storage: int  # storage count field
    gestures: int
    ng_plus: int
    flags: int  # first flag byte (block 0)
    used_end: int  # end of the last directory section
    id_copy: int  # second copy of the equip and quick item ids


class DS3Slot:
    """
    Parsed character slot. Offsets are recomputed after any operation that
    changes the data size; everything else writes in place.
    """

    def __init__(self, slot_index: int, data: bytearray) -> None:
        self.slot_index = slot_index
        self._data = data
        self._gaitem_end: int | None = None
        # (offset, handle) per gaitem position, built on first use.
        self._gaitem_cache: tuple[list[int], list[int]] | None = None
        self._layout: _Layout | None = None
        self._layout_error: str | None = None
        # "" once validated, a message when invalid, None before checking.
        self._inventory_error: str | None = None

    # --- Layout ------------------------------------------------------------ #

    @property
    def is_empty(self) -> bool:
        """Empty slots have no data after the size field."""
        if self._data[4:12] == bytes(8):
            return True
        try:
            return not self.name
        except LayoutError:
            return True

    @property
    def play_time_ms(self) -> int:
        return _read_u32(self._data, _PLAY_TIME_OFFSET)

    def _dir(self, field: int) -> tuple[int, int]:
        return struct.unpack_from("<II", self._data, field)

    def _check_directory(self) -> tuple[int, int]:
        """Validate the section directory; return (flag data start, used end)."""
        pairs = [self._dir(f) for f in _DIR_PAIRS]
        (player_off, player_size), pgd = pairs[0], pairs[1]
        # 0x18, 0x28 and 0x30 chain inside the player data section, which
        # ends where the event flags start; 0x38 onward are contiguous.
        chained = [pgd, pairs[2], pairs[3]]
        outer = [(player_off, player_size), *pairs[4:]]
        if player_off != pgd[0]:
            raise LayoutError("slot section directory is not consistent")
        for (a_off, a_size), (b_off, _) in [*pairwise(chained), *pairwise(outer)]:
            if a_off + a_size != b_off:
                raise LayoutError("slot section directory is not contiguous")
        used_end = pairs[-1][0] + pairs[-1][1]
        if used_end > len(self._data):
            raise LayoutError("slot sections extend past the slot")
        return self._dir(_DIR_EVENT_FLAGS)[0] + _FLAG_PREFIX, used_end

    def _parse_layout(self) -> _Layout:
        data = self._data
        flags, used_end = self._check_directory()
        player_off = self._dir(_DIR_PLAYER_DATA)[0]
        pgd_off, pgd_size = self._dir(_DIR_PAIRS[1])

        gaitem_start = player_off + _GAITEM_FROM_PLAYER_DATA
        gaitem_end = _scan_gaitem(data, gaitem_start)
        inv = gaitem_end + _INVENTORY_REL
        table1 = inv + _INVENTORY_BYTES + _TABLE1_FROM_INV_END
        table1_count = _read_u32(data, table1)
        if table1_count > 0x10000:
            raise LayoutError("storage box offset chain is not valid")
        storage = table1 + 4 + table1_count * _TABLE1_ENTRY + _STORAGE_FROM_TABLE1_END
        gestures = storage + _INVENTORY_BYTES
        if gestures + GESTURE_COUNT * _GESTURE_ENTRY > pgd_off + pgd_size:
            raise LayoutError("player data offsets exceed their section")
        # The gesture list has a fixed, self-describing shape, which confirms
        # the whole chain from the gaitem table to here.
        for k in range(GESTURE_COUNT):
            value, order = struct.unpack_from(
                "<HH", data, gestures + k * _GESTURE_ENTRY
            )
            if order != k or value >> 1 != k + 1:
                raise LayoutError("character data is not where expected")
        ng_off, ng_size = self._dir(_DIR_BEFORE_NG)
        ng_plus = ng_off + ng_size - 4
        if _read_u32(data, ng_plus) > _NG_MAX:
            raise LayoutError("NG+ counter is out of range")
        return _Layout(
            gaitem_start,
            gaitem_end,
            inv,
            storage,
            gestures,
            ng_plus,
            flags,
            used_end,
            table1 + 4 + table1_count * _TABLE1_ENTRY,
        )

    def _validate_lists(self) -> None:
        """Reject inventory lists that are misaligned or malformed."""
        layout = self._get_layout()
        for base, where in ((layout.inv, "inventory"), (layout.storage, "storage")):
            key_count = _read_u32(self._data, base + _COMMON_BYTES)
            third_count = _read_u32(self._data, base + _COMMON_BYTES + _KEY_BYTES)
            if key_count > _KEY_CAP or third_count > _THIRD_CAP:
                raise LayoutError(
                    f"{where} list counts are out of range; the slot may "
                    "have been edited by an older tool version"
                )
            for entry in self._iter_list(base, _COMMON_CAP, False) + self._iter_list(
                base + _COMMON_BYTES, _KEY_CAP, True
            ):
                if not self._entry_ok(entry):
                    kind = "key item" if entry.is_key else where
                    raise LayoutError(
                        f"malformed {kind} entry at position {entry.position}; "
                        "the slot may have been edited by an older tool version"
                    )

    @staticmethod
    def _entry_ok(e: DS3InventoryEntry) -> bool:
        if e.handle == 0:
            return e.item_id in (_EMPTY_ID, 0)
        if e.handle == _PLACEHOLDER_HANDLE:
            return True
        return _HANDLE_FOR_ID.get(id_kind(e.item_id)) == e.handle & 0xF0000000

    def _get_layout(self) -> _Layout:
        if self._layout is None:
            if self._layout_error is not None:
                raise LayoutError(self._layout_error)
            try:
                self._layout = self._parse_layout()
            except LayoutError as exc:
                self._layout_error = str(exc)
                raise
            except struct.error as exc:
                self._layout_error = f"slot data is truncated ({exc})"
                raise LayoutError(self._layout_error) from exc
        return self._layout

    @property
    def layout_error(self) -> str | None:
        """None when gestures, NG+ and inventory offsets resolve, else why not."""
        try:
            self._get_layout()
        except LayoutError as exc:
            return str(exc)
        return None

    @property
    def flags_error(self) -> str | None:
        """None when event flags can be read and written, else why not."""
        try:
            self._check_directory()
        except (LayoutError, struct.error) as exc:
            return str(exc)
        return None

    @property
    def inventory_error(self) -> str | None:
        """None when the inventory can be edited safely, else why not."""
        if self._inventory_error is None:
            try:
                self._validate_lists()
                self._inventory_error = ""
            except LayoutError as exc:
                self._inventory_error = str(exc)
        return self._inventory_error or None

    def _require_inventory(self) -> None:
        error = self.inventory_error
        if error:
            raise LayoutError(error)

    def _shift_cached(self, at: int, delta: int) -> None:
        """Move cached offsets at or after at by delta, matching an insert of
        delta bytes there; list contents and validity are unchanged."""
        if self._gaitem_end is not None and self._gaitem_end >= at:
            self._gaitem_end += delta
        if self._layout is not None:
            self._layout = _Layout(
                *(
                    getattr(self._layout, f.name) + delta
                    if getattr(self._layout, f.name) >= at
                    else getattr(self._layout, f.name)
                    for f in fields(_Layout)
                )
            )

    def _player(self, rel: int) -> int:
        """Absolute offset of a player block field. Needs only the gaitem walk,
        so identity and stats stay readable when a later list is malformed."""
        if self._gaitem_end is None:
            start = self._dir(_DIR_PLAYER_DATA)[0] + _GAITEM_FROM_PLAYER_DATA
            self._gaitem_end = _scan_gaitem(self._data, start)
        return self._gaitem_end + rel

    # --- Identity and stats ------------------------------------------------ #

    @property
    def name(self) -> str:
        off = self._player(_NAME_REL)
        raw = bytes(self._data[off : off + _NAME_LEN])
        end = 0
        while end + 1 < _NAME_LEN and raw[end : end + 2] != b"\x00\x00":
            end += 2
        return raw[:end].decode("utf-16-le", errors="replace")

    @name.setter
    def name(self, value: str) -> None:
        off = self._player(_NAME_REL)
        encoded = value[:NAME_MAX_CHARS].encode("utf-16-le")[:_NAME_LEN]
        self._data[off : off + _NAME_LEN + 2] = encoded.ljust(_NAME_LEN + 2, b"\x00")

    @property
    def starting_class(self) -> int:
        return self._data[self._player(_CLASS_REL)]

    @starting_class.setter
    def starting_class(self, value: int) -> None:
        self._data[self._player(_CLASS_REL)] = value & 0xFF

    @property
    def body_type(self) -> int:
        return self._data[self._player(_BODY_TYPE_REL)]

    @body_type.setter
    def body_type(self, value: int) -> None:
        self._data[self._player(_BODY_TYPE_REL)] = value & 0xFF

    @property
    def dir_mirror_u8(self) -> int:
        return self._data[self._player(_DIR_MIRROR_U8_REL)]

    @property
    def arm_style_block(self) -> bytes:
        """Arm style and active weapon slots, as the directory entry copies them."""
        off = self._player(_ARM_STYLE_REL)
        return bytes(self._data[off : off + _EQUIP_IDS_REL - _ARM_STYLE_REL])

    @property
    def weapon_level(self) -> int:
        return self._data[self._player(_WEAPON_LEVEL_REL)]

    @weapon_level.setter
    def weapon_level(self, value: int) -> None:
        self._data[self._player(_WEAPON_LEVEL_REL)] = value & 0xFF

    def _face_span(self) -> tuple[int, int]:
        """(offset, size) of the appearance block: the one FACE header between
        the player block and the end of the player data section."""
        start = self._player(0)
        section_off, section_size = self._dir(_DIR_PLAYER_DATA)
        end = section_off + section_size
        off = self._data.find(_FACE_HEADER, start, end)
        if off < 0 or self._data.find(_FACE_HEADER, off + 1, end) >= 0:
            raise LayoutError("Appearance block not found in the player data")
        size = _read_u32(self._data, off + _FACE_SIZE_FIELD)
        if not len(_FACE_HEADER) + 4 <= size <= end - off:
            raise LayoutError(f"Appearance block size {size:#x} out of range")
        return off, size

    @property
    def face_block(self) -> bytes:
        off, size = self._face_span()
        return bytes(self._data[off : off + size])

    @face_block.setter
    def face_block(self, block: bytes) -> None:
        off, size = self._face_span()
        if len(block) != size or block[: len(_FACE_HEADER)] != _FACE_HEADER:
            raise ValueError("Appearance block does not match the slot's layout")
        self._data[off : off + size] = block

    def _u32_prop(rel: int):  # noqa: N805
        def getter(self) -> int:
            return _read_u32(self._data, self._player(rel))

        def setter(self, val: int) -> None:
            _write_u32(self._data, self._player(rel), val)

        return property(getter, setter)

    souls = _u32_prop(_SOULS_REL)
    soul_memory = _u32_prop(_SOUL_MEMORY_REL)
    hp = _u32_prop(_HP_REL)
    fp = _u32_prop(_FP_REL)
    stamina = _u32_prop(_STAMINA_REL)
    level = _u32_prop(_LEVEL_REL)
    del _u32_prop

    def get_stat(self, key: str) -> int:
        rel = _STAT_REL.get(key.lower())
        if rel is None:
            raise ValueError(f"Unknown stat: {key!r}")
        return _read_u32(self._data, self._player(rel))

    def set_stat(self, key: str, val: int) -> None:
        rel = _STAT_REL.get(key.lower())
        if rel is None:
            raise ValueError(f"Unknown stat: {key!r}")
        _write_u32(self._data, self._player(rel), val)

    # --- NG+ ------------------------------------------------------------------ #

    @property
    def ng_plus(self) -> int:
        return _read_u32(self._data, self._get_layout().ng_plus)

    @ng_plus.setter
    def ng_plus(self, val: int) -> None:
        _write_u32(self._data, self._get_layout().ng_plus, val)
        # The playthrough flags are one-hot; keep them consistent with the
        # counter so scripts that check the current lap agree with it.
        lap = min(val, _LAP_FLAG_MAX)
        for n in range(_LAP_FLAG_CLEAR + 1):
            self.set_flag(_LAP_FLAG_BASE + n, n == lap)

    # --- Event flags ------------------------------------------------------- #

    def _flag_pos(self, flag_id: int) -> tuple[int, int]:
        if 0 <= flag_id < _GLOBAL_FLAG_LIMIT:
            block = 0
        else:
            block = _EVENT_FLAG_BLOCKS.get(flag_id // 10000)
            if block is None:
                raise ValueError(f"Event flag {flag_id} is in an unmapped block")
        group = (flag_id // 1000) % 10
        bit = flag_id % 1000
        flags_start = self._check_directory()[0]
        word = flags_start + block * _FLAG_BLOCK_BYTES + group * _FLAG_GROUP_BYTES
        word += (bit // 32) * 4
        # Little-endian u32 with flag 0 in bit 31: byte 3 holds flags 0-7.
        byte = word + 3 - (bit % 32) // 8
        return byte, 0x80 >> (bit % 8)

    def get_flag(self, flag_id: int) -> bool:
        byte, mask = self._flag_pos(flag_id)
        return bool(self._data[byte] & mask)

    def set_flag(self, flag_id: int, on: bool) -> None:
        byte, mask = self._flag_pos(flag_id)
        if on:
            self._data[byte] |= mask
        else:
            self._data[byte] &= ~mask & 0xFF

    # --- Character death state ---------------------------------------------- #

    @staticmethod
    def _chr_map_key(map_name: str) -> int:
        """CHR record key of a map name such as "m40_00"."""
        return int(map_name[1:3]) << 24 | int(map_name[4:6]) << 16

    def _chr_maps(self) -> dict[int, tuple[int, int]]:
        """Map key -> (bitfield offset, bit count) for each CHR record."""
        self._check_directory()
        sec_off, sec_size = self._dir(_DIR_CHR_STATE)
        start = sec_off + _CHR_SECTION_HEADER
        end = start + _read_u32(self._data, sec_off + 4)
        if end > sec_off + sec_size or self._data[start : start + 4] != _CHR_MAGIC:
            raise LayoutError("character state block is not where expected")
        maps: dict[int, tuple[int, int]] = {}
        pos = start + _CHR_BLOCK_HEADER
        while pos + 4 <= end:
            key = _read_u32(self._data, pos)
            if key == _CHR_END:
                return maps
            count = _read_u32(self._data, pos + 8)
            bits = pos + _CHR_MAP_HEADER
            pos = bits + (count + 7) // 8
            if pos > end:
                break
            maps[key] = (bits, count)
        raise LayoutError("character state block is malformed")

    def _chr_bit(self, map_name: str, index: int) -> tuple[int, int] | None:
        """(byte offset, mask) of an enemy part's death bit, None when the
        save holds no record for its map."""
        record = self._chr_maps().get(self._chr_map_key(map_name))
        if record is None or not 0 <= index < record[1]:
            return None
        return record[0] + index // 8, 1 << index % 8

    def character_dead(self, map_name: str, index: int) -> bool | None:
        """Death bit of enemy part index in map_name, None without a record."""
        pos = self._chr_bit(map_name, index)
        return None if pos is None else bool(self._data[pos[0]] & pos[1])

    def set_character_dead(self, map_name: str, index: int, dead: bool) -> bool:
        """Set or clear a death bit; False when the save has no record for
        the map (nothing to change there)."""
        pos = self._chr_bit(map_name, index)
        if pos is None:
            return False
        byte, mask = pos
        if dead:
            self._data[byte] |= mask
        else:
            self._data[byte] &= ~mask & 0xFF
        return True

    # --- Gestures -------------------------------------------------------------- #

    def gesture_unlocked(self, gesture_id: int) -> bool:
        off = self._get_layout().gestures + gesture_id * _GESTURE_ENTRY
        return bool(struct.unpack_from("<H", self._data, off)[0] & 1)

    def set_gesture_unlocked(self, gesture_id: int, unlocked: bool) -> None:
        if not 0 <= gesture_id < GESTURE_COUNT:
            raise ValueError(f"Gesture id {gesture_id} out of range")
        off = self._get_layout().gestures + gesture_id * _GESTURE_ENTRY
        struct.pack_into("<H", self._data, off, 2 * (gesture_id + 1) + int(unlocked))

    # --- Gaitem table ------------------------------------------------------ #

    def iter_gaitem(self) -> list[DS3GaitemEntry]:
        entries = []
        offset = self._get_layout().gaitem_start
        for _ in range(GAITEM_SLOT_COUNT):
            handle = _read_u32(self._data, offset)
            item_id = _read_u32(self._data, offset + 4)
            wa = handle and handle & 0xF0000000 in (ITEM_TYPE_WEAPON, ITEM_TYPE_ARMOR)
            size = GAITEM_WA_SIZE if wa else GAITEM_BASE_SIZE
            entries.append(DS3GaitemEntry(handle, item_id, offset, size))
            offset += size
        return entries

    def _gaitem_slots(self) -> tuple[list[int], list[int]]:
        """(offsets, handles) per gaitem position, cached across edits."""
        if self._gaitem_cache is None:
            offsets: list[int] = []
            handles: list[int] = []
            offset = self._get_layout().gaitem_start
            for _ in range(GAITEM_SLOT_COUNT):
                handle = _read_u32(self._data, offset)
                offsets.append(offset)
                handles.append(handle)
                wa = handle and handle & 0xF0000000 in (
                    ITEM_TYPE_WEAPON,
                    ITEM_TYPE_ARMOR,
                )
                offset += GAITEM_WA_SIZE if wa else GAITEM_BASE_SIZE
            self._gaitem_cache = (offsets, handles)
        return self._gaitem_cache

    def _find_gaitem(self, handle: int) -> DS3GaitemEntry | None:
        offsets, handles = self._gaitem_slots()
        # A handle's low 16 bits are its table position.
        pos = handle & 0xFFFF
        if not (pos < len(handles) and handles[pos] == handle):
            pos = next((i for i, h in enumerate(handles) if h == handle), None)
            if pos is None:
                return None
        off = offsets[pos]
        wa = handle & 0xF0000000 in (ITEM_TYPE_WEAPON, ITEM_TYPE_ARMOR)
        return DS3GaitemEntry(
            handle,
            _read_u32(self._data, off + 4),
            off,
            GAITEM_WA_SIZE if wa else GAITEM_BASE_SIZE,
        )

    def _alloc_gaitem(self, item_id: int, handle_type: int, durability: int) -> int:
        """
        Turn an unused 8-byte gaitem entry into a 60-byte weapon/armor entry
        and return its handle. The slot grows by 52 bytes at that point; every
        directory section after it shifts and the stale tail shrinks.
        """
        layout = self._get_layout()
        if layout.used_end + _GAITEM_GROWTH > len(self._data):
            raise ValueError(
                "No room left in the slot for another weapon or armor entry"
            )
        offsets, handles = self._gaitem_slots()
        # The game assigns positions in acquisition order; continue after the
        # highest one in use and wrap around to the first free position.
        start = next(
            (i + 1 for i in range(GAITEM_SLOT_COUNT - 1, -1, -1) if handles[i]), 0
        )
        order = list(range(start, GAITEM_SLOT_COUNT)) + list(range(start))
        pos = next((i for i in order if not handles[i]), None)
        if pos is None:
            raise ValueError("Gaitem table is full")
        entry_off = offsets[pos]
        insert_at = entry_off + GAITEM_BASE_SIZE

        self._shift_directory(insert_at, _GAITEM_GROWTH)
        tail = len(self._data) - _GAITEM_GROWTH
        self._data[insert_at:] = bytes(_GAITEM_GROWTH) + self._data[insert_at:tail]

        handle = handle_type | _WA_HANDLE_FLAGS | pos
        body = struct.pack(
            "<IIIII", handle, item_id, durability, 0, _GAITEM_UNKNOWN_ONE
        )
        body += struct.pack("<II", _EMPTY_GEM_SLOT, 0) * _GEM_SLOTS
        self._data[entry_off : entry_off + GAITEM_WA_SIZE] = body
        handles[pos] = handle
        offsets[pos + 1 :] = [o + _GAITEM_GROWTH for o in offsets[pos + 1 :]]
        self._shift_cached(insert_at, _GAITEM_GROWTH)
        return handle

    def _shift_directory(self, at: int, delta: int) -> None:
        for field in _DIR_PAIRS:
            off, size = self._dir(field)
            if off >= at:
                off += delta
            elif at < off + size:
                size += delta
            struct.pack_into("<II", self._data, field, off, size)

    # --- Inventory iteration ---------------------------------------------- #

    def _iter_list(
        self, count_off: int, cap: int, is_key: bool
    ) -> list[DS3InventoryEntry]:
        out = []
        base = count_off + 4
        for pos in range(cap):
            off = base + pos * _ENTRY_SIZE
            h, iid, qty, idx = struct.unpack_from("<IIII", self._data, off)
            out.append(DS3InventoryEntry(h, iid, qty, idx, off, pos, is_key))
        return out

    def _iter_entry(self, count_off: int, pos: int, is_key: bool) -> DS3InventoryEntry:
        off = count_off + 4 + pos * _ENTRY_SIZE
        h, iid, qty, idx = struct.unpack_from("<IIII", self._data, off)
        return DS3InventoryEntry(h, iid, qty, idx, off, pos, is_key)

    def _scan_list(
        self, count_off: int, cap: int, stack_id: int | None
    ) -> tuple[int | None, int | None]:
        """(position of a real entry holding stack_id, first free position)
        in one pass over the raw list; either is None when absent. Batch
        spawns call this once per item, so it avoids building entries."""
        base = count_off + 4
        raw = memoryview(self._data)[base : base + cap * _ENTRY_SIZE]
        free = None
        for pos, (h, iid, _qty, _idx) in enumerate(struct.iter_unpack("<IIII", raw)):
            if h == 0:
                if free is None and iid in (_EMPTY_ID, 0):
                    free = pos
                    if stack_id is None:
                        break
            elif iid == stack_id and h != _PLACEHOLDER_HANDLE:
                return pos, free
        return None, free

    def iter_inventory(self) -> list[DS3InventoryEntry]:
        """Held common and key items, including empty entries."""
        inv = self._get_layout().inv
        return self._iter_list(inv, _COMMON_CAP, False) + self._iter_list(
            inv + _COMMON_BYTES, _KEY_CAP, True
        )

    def iter_storage(self) -> list[DS3InventoryEntry]:
        return self._iter_list(self._get_layout().storage, _COMMON_CAP, False)

    @staticmethod
    def is_real_item(entry: DS3InventoryEntry) -> bool:
        return not entry.is_empty and entry.handle != _PLACEHOLDER_HANDLE

    def entry_at(self, offset: int) -> DS3InventoryEntry | None:
        for entry in self.iter_inventory() + self.iter_storage():
            if entry.offset == offset:
                return entry
        return None

    def bad_storage_indices(self) -> int:
        """
        Number of storage box index problems the game hides items over:
        stored entries with an index position below 0x80 and a last-index
        field below 0x80 + the highest used position. Older storage box
        spawns wrote both.
        """
        if self.inventory_error:
            return 0
        base = self._get_layout().storage
        real = [e for e in self._iter_list(base, _COMMON_CAP, False) if e.handle]
        if not real:
            return 0
        bad = sum(1 for e in real if e.index & _INDEX_POS_MASK < _COMMON_INDEX_BASE)
        last = _read_u32(self._data, self._last_index_off(base))
        return bad + (last < _COMMON_INDEX_BASE + real[-1].position)

    def fix_storage_indices(self) -> int:
        """Give stored entries with an index position below 0x80 the position
        0x80 + their slot, raise the last-index field to 0x80 + the highest
        used position. Returns the number of problems fixed."""
        fixed = self.bad_storage_indices()
        if not fixed:
            return 0
        base = self._get_layout().storage
        real = [e for e in self._iter_list(base, _COMMON_CAP, False) if e.handle]
        for e in real:
            if e.index & _INDEX_POS_MASK < _COMMON_INDEX_BASE:
                index = self._index(e.index >> 12, _COMMON_INDEX_BASE + e.position)
                _write_u32(self._data, e.offset + 12, index)
        last_off = self._last_index_off(base)
        top = _COMMON_INDEX_BASE + real[-1].position
        _write_u32(self._data, last_off, max(_read_u32(self._data, last_off), top))
        return fixed

    def in_storage(self, entry: DS3InventoryEntry) -> bool:
        storage = self._get_layout().storage
        return storage < entry.offset < storage + _COMMON_BYTES

    # --- Equipped / quick slot references -------------------------------- #

    def is_equipped(self, entry: DS3InventoryEntry) -> bool:
        """True when an equip slot or a quick/belt slot references the entry."""
        if self.in_storage(entry):
            return False
        layout = self._get_layout()
        eq = layout.gaitem_end + _EQUIP_SLOTS_REL
        for k in range(_EQUIP_SLOT_COUNT):
            if (
                _read_u32(self._data, eq + k * 4) == entry.index & _INDEX_POS_MASK
                and not entry.is_key
            ):
                return True
        # Quick and belt slots are (handle, index) pairs between the held
        # inventory and the storage box.
        start = layout.inv + _INVENTORY_BYTES
        pair = struct.pack("<II", entry.handle, entry.index & _INDEX_POS_MASK)
        return self._data.find(pair, start, layout.storage) != -1

    # --- Equipment ------------------------------------------------------- #

    def equip_slot(self, k: int) -> tuple[int, int, int]:
        """(inventory index, item id, handle) stored for equip slot k."""
        base = self._get_layout().gaitem_end
        return (
            _read_u32(self._data, base + _EQUIP_SLOTS_REL + 4 * k),
            _read_u32(self._data, base + _EQUIP_IDS_REL + 4 * k),
            _read_u32(self._data, base + _EQUIP_HANDLES_REL + 4 * k),
        )

    def equipped_ids(self) -> list[int]:
        """Item ids of the 22 equip slots, as the directory copy holds them."""
        return [self.equip_slot(k)[1] for k in range(_EQUIP_SLOT_COUNT)]

    def equipped_entry(self, k: int) -> DS3InventoryEntry | None:
        """Held common entry equip slot k references; None when the slot is
        empty or its index matches no entry."""
        index = self.equip_slot(k)[0]
        if index == _EMPTY_ID:
            return None
        for entry in self.iter_inventory():
            if (
                not entry.is_key
                and self.is_real_item(entry)
                and entry.index & _INDEX_POS_MASK == index
            ):
                return entry
        return None

    @staticmethod
    def equip_slot_accepts(k: int, item_id: int) -> bool:
        """Whether an inventory item id fits equip slot k by item type: hands
        take weapons other than ammo, ammo slots arrows or bolts, armor slots
        their own piece, ring slots rings and the covenant slot covenant
        items. Unidentified slots accept nothing."""
        kind = id_kind(item_id)
        bare = item_id & _EQUIP_ID_MASK
        family_digit = bare // 1000 % 10
        if k in EQUIP_HANDS or k in EQUIP_AMMO:
            if kind != ID_WEAPON:
                return False
            is_ammo = _AMMO_ID_MIN <= bare < _AMMO_ID_END
            if k in EQUIP_HANDS:
                return not is_ammo
            return is_ammo and (family_digit == _BOLT_FAMILY_DIGIT) == (
                k in _EQUIP_BOLT_SLOTS
            )
        if k in EQUIP_ARMOR:
            return kind == ID_ARMOR and family_digit == k - EQUIP_ARMOR.start
        if k in EQUIP_RINGS:
            return kind == ID_RING and bare >= _COVENANT_ID_LIMIT
        if k == EQUIP_COVENANT:
            return kind == ID_RING and bare < _COVENANT_ID_LIMIT
        return False

    @staticmethod
    def equip_placeholder_id(k: int) -> int | None:
        """Inventory item id an empty hand (Fists) or armor slot (bare piece)
        points at; None for slots that can hold nothing."""
        if k in EQUIP_HANDS:
            return FISTS_ID
        if k in EQUIP_ARMOR:
            return (ID_ARMOR << 28) | (
                BARE_ARMOR_BASE + (k - EQUIP_ARMOR.start) * _ARMOR_PIECE_STEP
            )
        return None

    def set_equip(self, k: int, entry: DS3InventoryEntry | None) -> None:
        """Point equip slot k at a held common entry, writing its index, item
        id and handle, or empty the slot (index and id 0xFFFFFFFF, handle 0).
        Hand and armor slots are never empty in game: pass the Fists or bare
        armor entry instead. Raises ValueError for an entry that is not a
        held common item or does not fit the slot."""
        if not 0 <= k < _EQUIP_SLOT_COUNT:
            raise ValueError(f"Equip slot {k} out of range")
        if entry is None:
            index, item_id, handle = _EMPTY_ID, _EMPTY_ID, 0
        else:
            if entry.is_key or self.in_storage(entry) or not self.is_real_item(entry):
                raise ValueError(f"Item {entry.item_id:#x} is not a held item")
            if not self.equip_slot_accepts(k, entry.item_id):
                raise ValueError(f"Item {entry.item_id:#x} does not fit equip slot {k}")
            index = entry.index & _INDEX_POS_MASK
            item_id = entry.item_id & _EQUIP_ID_MASK
            handle = entry.handle
        layout = self._get_layout()
        base = layout.gaitem_end
        _write_u32(self._data, base + _EQUIP_SLOTS_REL + 4 * k, index)
        _write_u32(self._data, base + _EQUIP_IDS_REL + 4 * k, item_id)
        _write_u32(self._data, base + _EQUIP_HANDLES_REL + 4 * k, handle)
        _write_u32(
            self._data,
            layout.id_copy + 4 * k,
            _EMPTY_ID if entry is None else entry.item_id,
        )

    # --- Quick items and attunement -------------------------------------- #

    def _attune_off(self) -> int:
        return self._get_layout().inv + _INVENTORY_BYTES

    def _quick_off(self) -> int:
        return self._attune_off() + ATTUNE_SLOTS * _ATTUNE_RECORD + 4

    def quick_entry(self, k: int) -> DS3InventoryEntry | None:
        """Held common entry in quick item slot k, None when empty."""
        handle, index = struct.unpack_from(
            "<II", self._data, self._quick_off() + k * _QUICK_RECORD
        )
        if handle == 0 or index == _EMPTY_ID:
            return None
        for entry in self.iter_inventory():
            if (
                not entry.is_key
                and self.is_real_item(entry)
                and entry.index & _INDEX_POS_MASK == index
            ):
                return entry
        return None

    def set_quick_item(self, k: int, entry: DS3InventoryEntry | None) -> None:
        """Put a held common goods entry in quick item slot k (handle and
        index position, plus its id in the second copy), or empty the slot.
        Raises ValueError for an entry that is not a held common good."""
        if not 0 <= k < QUICK_SLOTS:
            raise ValueError(f"Quick item slot {k} out of range")
        if entry is None:
            handle, index, item_id = 0, _EMPTY_ID, _EMPTY_ID
        else:
            if (
                entry.is_key
                or self.in_storage(entry)
                or not self.is_real_item(entry)
                or id_kind(entry.item_id) != ID_GOOD
            ):
                raise ValueError(f"Item {entry.item_id:#x} is not a held good")
            handle = entry.handle
            index = entry.index & _INDEX_POS_MASK
            item_id = entry.item_id
        struct.pack_into(
            "<II", self._data, self._quick_off() + k * _QUICK_RECORD, handle, index
        )
        _write_u32(
            self._data, self._get_layout().id_copy + _COPY_QUICK_REL + 4 * k, item_id
        )

    def attuned_spells(self) -> list[int]:
        """Spell ids (goods ids without the type nibble) of the attunement
        records, in order."""
        base = self._attune_off()
        ids = []
        for k in range(ATTUNE_SLOTS):
            spell_id = _read_u32(self._data, base + k * _ATTUNE_RECORD)
            if spell_id != _EMPTY_ID:
                ids.append(spell_id)
        return ids

    def attune(self, spell_ids: list[int]) -> None:
        """Replace the attunement records, packed from the first. The
        selected record stays when it still holds a spell, else moves to the
        first (or -1 with no spells). Raises ValueError for more than
        ATTUNE_SLOTS spells."""
        if len(spell_ids) > ATTUNE_SLOTS:
            raise ValueError(f"At most {ATTUNE_SLOTS} spells can be attuned")
        base = self._attune_off()
        for k in range(ATTUNE_SLOTS):
            record = (
                (spell_ids[k] & _EQUIP_ID_MASK, _EMPTY_ID)
                if k < len(spell_ids)
                else (_EMPTY_ID, 0)
            )
            struct.pack_into("<II", self._data, base + k * _ATTUNE_RECORD, *record)
        selected_off = base + ATTUNE_SLOTS * _ATTUNE_RECORD
        selected = struct.unpack_from("<i", self._data, selected_off)[0]
        if not spell_ids:
            selected = -1
        elif not 0 <= selected < len(spell_ids):
            selected = 0
        struct.pack_into("<i", self._data, selected_off, selected)

    # --- Counters and sort keys ------------------------------------------ #

    def _held_count(self, delta: int) -> None:
        off = self._get_layout().inv
        _write_u32(self._data, off, _read_u32(self._data, off) + delta)

    def _key_count(self, delta: int) -> None:
        off = self._get_layout().inv + _COMMON_BYTES
        _write_u32(self._data, off, _read_u32(self._data, off) + delta)

    def _storage_count(self, delta: int) -> None:
        off = self._get_layout().storage
        _write_u32(self._data, off, _read_u32(self._data, off) + delta)

    def _last_index_off(self, list_base: int) -> int:
        return list_base + _COMMON_BYTES + _KEY_BYTES + _THIRD_BYTES

    @staticmethod
    def _index(sort_key: int, position_index: int) -> int:
        return ((sort_key << 12) | (position_index & _INDEX_POS_MASK)) & 0xFFFFFFFF

    # --- Adding items ---------------------------------------------------- #

    def add_item(
        self,
        item_id: int,
        quantity: int = 1,
        *,
        sort_key: int = 0,
        durability: int = 0,
        key_item: bool = False,
        max_quantity: int = 99,
        to_storage: bool = False,
    ) -> DS3InventoryEntry:
        """
        Add an item the way the game stores a pickup.

        Stackable items (goods and ammo) merge into an existing stack of the
        same id, capped at max_quantity; a stack already above the cap keeps
        its quantity. Weapons and armor get a new gaitem
        entry. Key items go to the key list and cannot be stored.
        Raises ValueError when the item cannot be placed.
        """
        self._require_inventory()
        kind = id_kind(item_id)
        handle_type = _HANDLE_FOR_ID.get(kind)
        if handle_type is None:
            raise ValueError(f"Unsupported item id {item_id:#010x}")
        if key_item and to_storage:
            raise ValueError("Key items cannot be placed in the storage box")
        layout = self._get_layout()
        quantity = max(1, min(quantity, max_quantity))
        stackable = kind == ID_GOOD or (kind == ID_WEAPON and max_quantity > 1)

        if key_item:
            list_off, cap, is_key = layout.inv + _COMMON_BYTES, _KEY_CAP, True
        elif to_storage:
            list_off, cap, is_key = layout.storage, _COMMON_CAP, False
        else:
            list_off, cap, is_key = layout.inv, _COMMON_CAP, False
        stack, position = self._scan_list(list_off, cap, item_id if stackable else None)
        if stack is not None:
            entry = self._iter_entry(list_off, stack, is_key)
            entry.quantity = max(
                entry.quantity, min(entry.quantity + quantity, max_quantity)
            )
            _write_u32(self._data, entry.offset + 8, entry.quantity)
            return entry
        if position is None:
            raise ValueError(
                "No free storage box slot" if to_storage else "No free inventory slot"
            )

        if kind in (ID_WEAPON, ID_ARMOR):
            handle = self._alloc_gaitem(item_id, handle_type, durability)
            # The insert shifted everything after the gaitem table.
            layout = self._get_layout()
            if key_item:
                list_off = layout.inv + _COMMON_BYTES
            elif to_storage:
                list_off = layout.storage
            else:
                list_off = layout.inv
        else:
            handle = handle_type | (item_id & 0x0FFFFFFF)

        if is_key:
            pos_index = position
        else:
            # The storage box uses the held rule: 0x80 + position, and the
            # last-index field is 0x80 + the highest used position.
            last_off = self._last_index_off(list_off)
            last = _read_u32(self._data, last_off)
            pos_index = _COMMON_INDEX_BASE + position
            _write_u32(self._data, last_off, max(last, pos_index))

        offset = list_off + 4 + position * _ENTRY_SIZE
        index = self._index(sort_key, pos_index)
        struct.pack_into("<IIII", self._data, offset, handle, item_id, quantity, index)

        if is_key:
            self._key_count(1)
        elif to_storage:
            self._storage_count(1)
        else:
            self._held_count(1)
        return DS3InventoryEntry(
            handle, item_id, quantity, index, offset, position, is_key
        )

    # --- Editing existing entries ------------------------------------------ #

    def set_quantity(self, entry: DS3InventoryEntry, quantity: int) -> None:
        self._require_inventory()
        _write_u32(self._data, entry.offset + 8, max(1, quantity))

    def set_weapon_level(self, entry: DS3InventoryEntry, level: int) -> int:
        """Change a weapon's upgrade level. Returns the new item id."""
        if id_kind(entry.item_id) != ID_WEAPON:
            raise ValueError("Only weapons have upgrade levels")
        index = _read_u32(self._data, entry.offset + 12)
        old_level = entry.item_id % 100
        sort_key = ((index >> 12) - old_level + level) & 0xFFFFF
        return self.set_weapon_id(entry, entry.item_id - old_level + level, sort_key)

    def set_weapon_id(
        self, entry: DS3InventoryEntry, new_id: int, sort_key: int
    ) -> int:
        """
        Turn a weapon into another weapon id (another level or infusion of
        the same weapon). The gaitem entry and handle stay, so equip and
        quick slots keep pointing at it; equip slots get the new id. Returns
        the new item id.
        """
        self._require_inventory()
        if id_kind(entry.item_id) != ID_WEAPON or id_kind(new_id) != ID_WEAPON:
            raise ValueError("Only weapons can change id")
        gaitem = self._find_gaitem(entry.handle)
        if gaitem is None or gaitem.size != GAITEM_WA_SIZE:
            raise ValueError("Weapon has no gaitem entry")
        _write_u32(self._data, gaitem.offset + 4, new_id)
        _write_u32(self._data, entry.offset + 4, new_id)
        index = _read_u32(self._data, entry.offset + 12)
        _write_u32(self._data, entry.offset + 12, self._index(sort_key, index))
        # Equip slots holding this weapon carry its id twice.
        layout = self._get_layout()
        base = layout.gaitem_end
        for k in range(_EQUIP_SLOT_COUNT):
            if (
                _read_u32(self._data, base + _EQUIP_SLOTS_REL + 4 * k)
                == index & _INDEX_POS_MASK
                and _read_u32(self._data, base + _EQUIP_HANDLES_REL + 4 * k)
                == entry.handle
            ):
                _write_u32(
                    self._data, base + _EQUIP_IDS_REL + 4 * k, new_id & _EQUIP_ID_MASK
                )
                _write_u32(self._data, layout.id_copy + 4 * k, new_id)
        entry.item_id = new_id
        return new_id

    def move_item(
        self, entry: DS3InventoryEntry, max_quantity: int = 0
    ) -> DS3InventoryEntry:
        """
        Move a held common item to the storage box or a stored item back.

        The entry keeps its handle, so weapons and armor keep their gaitem
        entry. Stored items keep the index they had when held, as the game
        does; items taken out get the held index for their new position.
        With max_quantity > 1 the stack merges into an existing stack of the
        same item at the destination, capped at max_quantity. Without such a
        stack, a stack above max_quantity is refused (the remainder would need
        a second entry).
        """
        self._require_inventory()
        if entry.is_key:
            raise ValueError("Key items cannot be placed in the storage box")
        if self.is_equipped(entry):
            raise ValueError("Item is equipped; unequip it in game first")
        layout = self._get_layout()
        to_storage = not self.in_storage(entry)
        dest = layout.storage if to_storage else layout.inv
        entries = self._iter_list(dest, _COMMON_CAP, False)

        target = None
        if max_quantity > 1:
            target = next(
                (
                    e
                    for e in entries
                    if self.is_real_item(e) and e.item_id == entry.item_id
                ),
                None,
            )
        if target is not None:
            moved = min(entry.quantity, max_quantity - target.quantity)
            if moved <= 0:
                raise ValueError("The destination stack is already full")
            _write_u32(self._data, target.offset + 8, target.quantity + moved)
            if moved < entry.quantity:
                _write_u32(self._data, entry.offset + 8, entry.quantity - moved)
                return self.entry_at(target.offset)
        else:
            if max_quantity > 1 and entry.quantity > max_quantity:
                raise ValueError(
                    f"the destination holds at most {max_quantity}; "
                    "lower the quantity first"
                )
            free = next((e for e in entries if e.handle == 0), None)
            if free is None:
                raise ValueError("No free slot at the destination")
            last_off = self._last_index_off(dest)
            last = _read_u32(self._data, last_off)
            # Stored items keep the index they had when held; the storage
            # last-index field still tracks 0x80 + the highest position.
            pos_index = _COMMON_INDEX_BASE + free.position
            if to_storage:
                index = entry.index
            else:
                index = (entry.index & ~_INDEX_POS_MASK & 0xFFFFFFFF) | pos_index
            _write_u32(self._data, last_off, max(last, pos_index))
            struct.pack_into(
                "<IIII",
                self._data,
                free.offset,
                entry.handle,
                entry.item_id,
                entry.quantity,
                index,
            )
            target = free

        struct.pack_into("<IIII", self._data, entry.offset, 0, _EMPTY_ID, 0, 0)
        if to_storage:
            self._held_count(-1)
            if target.handle == 0:
                self._storage_count(1)
        else:
            self._storage_count(-1)
            if target.handle == 0:
                self._held_count(1)
        return self.entry_at(target.offset)

    def remove_item(self, entry: DS3InventoryEntry) -> None:
        """
        Clear an inventory or storage entry. Equipped items are refused, since
        an equip slot pointing at a cleared entry leaves the character in a
        state the game never produces. The item's gaitem entry is left in
        place; the game drops unreferenced entries on its next save.
        """
        self._require_inventory()
        if self.is_equipped(entry):
            raise ValueError("Item is equipped; unequip it in game first")
        storage = self.in_storage(entry)
        struct.pack_into("<IIII", self._data, entry.offset, 0, _EMPTY_ID, 0, 0)
        if entry.is_key:
            self._key_count(-1)
        elif storage:
            self._storage_count(-1)
        elif entry.handle != _PLACEHOLDER_HANDLE:
            self._held_count(-1)

    def get_raw(self) -> bytearray:
        return self._data
