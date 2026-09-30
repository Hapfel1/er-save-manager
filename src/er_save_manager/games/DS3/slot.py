"""
DS3 decrypted character slot.

All offsets are derived from the slot's own data at parse time: the section
directory in the slot header, the gaitem table walk, and the fixed-size
structures that follow it. Nothing is addressed by absolute position.

=== SLOT HEADER ===

[0x00]  u32  Plaintext size after this field (0xC0000)
[0x04]  u32  Version (0x62)
[0x0C]  u32  Play time
[0x10..0x60]  Section directory, (u32 offset, u32 size) pairs:
  0x10  Player data: everything from the gaitem table to the event flags
  0x18  Player game data: gaitem table through the gesture list
  0x28, 0x30  Two small sections chained after 0x18, inside 0x10; the
              NG+ counter (u16) is the first field after the 0x30 section
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
  +0x1F0 22 x u32 equip slots, each an inventory index or 0xFFFFFFFF
  +0x318 inventory

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

After the held inventory: 8-byte (handle, index) quick/belt slots, then a
count-prefixed table of 8-byte records, the storage box, the gesture list
and a count-prefixed list of visited region ids.

=== GESTURES ===

41 x [u16 value][u16 k] directly after the storage box. value is
2*(k+1) + unlocked; k is the gesture id from the executable's gesture table.

=== EVENT FLAGS ===

Flags live in 1280-byte blocks of 10 groups x 128 bytes; each group holds
1000 flags as u32 little-endian words with the lowest flag in the most
significant bit. Block 0 holds global flags 0-9999; map flags
(1AAB0000-1AAB9999) use the per-map block in _EVENT_FLAG_BLOCKS.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
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
_NAME_REL = 0x78
_NAME_LEN = 32  # bytes, 16 UTF-16 code units including the terminator
_EQUIP_SLOTS_REL = 0x1F0
_EQUIP_SLOT_COUNT = 22
_INVENTORY_REL = 0x318

# Level equals the attribute sum minus this for every starting class.
LEVEL_STAT_OFFSET = 89

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
# Global flags 50-58 mark the current playthrough (NG, NG+, ... NG+8).
_LAP_FLAG_BASE = 50
_LAP_FLAG_MAX = 8

# --- Event flags ------------------------------------------------------------- #

_FLAG_BLOCK_BYTES = 1280
_FLAG_GROUP_BYTES = 128
_FLAG_PREFIX = 4
# Map block key (flag // 10000) to block index, one block per map. Derived
# from boss, bonfire and NPC flags whose state is known in real saves.
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


class DS3Slot:
    """
    Parsed character slot. Offsets are recomputed after any operation that
    changes the data size; everything else writes in place.
    """

    def __init__(self, slot_index: int, data: bytearray) -> None:
        self.slot_index = slot_index
        self._data = data
        self._gaitem_end: int | None = None
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

    def _dir(self, field: int) -> tuple[int, int]:
        return struct.unpack_from("<II", self._data, field)

    def _check_directory(self) -> tuple[int, int]:
        """Validate the section directory; return (flag data start, used end)."""
        pairs = [self._dir(f) for f in _DIR_PAIRS]
        (player_off, player_size), pgd = pairs[0], pairs[1]
        # 0x18, 0x28 and 0x30 chain inside the player data section, which
        # ends where the event flags start; 0x38 onward are contiguous.
        chained = [pgd, pairs[2], pairs[3]]
        outer = [(player_off, player_size)] + pairs[4:]
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
        ng_plus = ng_off + ng_size
        if struct.unpack_from("<H", data, ng_plus)[0] > _NG_MAX:
            raise LayoutError("NG+ counter is out of range")
        return _Layout(
            gaitem_start, gaitem_end, inv, storage, gestures, ng_plus, flags, used_end
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

    def _invalidate(self) -> None:
        self._gaitem_end = None
        self._layout = None
        self._layout_error = None
        self._inventory_error = None

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
        encoded = value.encode("utf-16-le")[: _NAME_LEN - 2]
        self._data[off : off + _NAME_LEN] = encoded.ljust(_NAME_LEN, b"\x00")

    def _u32_prop(rel: int):  # noqa: N805
        def getter(self) -> int:
            return _read_u32(self._data, self._player(rel))

        def setter(self, val: int) -> None:
            _write_u32(self._data, self._player(rel), val)

        return property(getter, setter)

    souls = _u32_prop(_SOULS_REL)
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
        return struct.unpack_from("<H", self._data, self._get_layout().ng_plus)[0]

    @ng_plus.setter
    def ng_plus(self, val: int) -> None:
        struct.pack_into("<H", self._data, self._get_layout().ng_plus, val)
        # The playthrough flags are one-hot; keep them consistent with the
        # counter so scripts that check the current lap agree with it.
        lap = min(val, _LAP_FLAG_MAX)
        for n in range(_LAP_FLAG_MAX + 1):
            self.set_flag(_LAP_FLAG_BASE + n, n == lap)

    # --- Event flags ------------------------------------------------------- #

    @staticmethod
    def flag_supported(flag_id: int) -> bool:
        return (
            0 <= flag_id < _GLOBAL_FLAG_LIMIT or flag_id // 10000 in _EVENT_FLAG_BLOCKS
        )

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

    def _find_gaitem(self, handle: int) -> DS3GaitemEntry | None:
        for entry in self.iter_gaitem():
            if entry.handle == handle:
                return entry
        return None

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
        entries = self.iter_gaitem()
        used = [i for i, e in enumerate(entries) if not e.is_empty]
        # The game assigns positions in acquisition order; continue after the
        # highest one in use and wrap around to the first free position.
        start = (max(used) + 1) if used else 0
        order = list(range(start, GAITEM_SLOT_COUNT)) + list(range(0, start))
        pos = next((i for i in order if entries[i].is_empty), None)
        if pos is None:
            raise ValueError("Gaitem table is full")
        entry_off = entries[pos].offset
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
        self._invalidate()
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
        same id, capped at max_quantity. Weapons and armor get a new gaitem
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
        entries = self._iter_list(list_off, cap, is_key)

        if stackable:
            for entry in entries:
                if self.is_real_item(entry) and entry.item_id == item_id:
                    new_qty = min(entry.quantity + quantity, max_quantity)
                    _write_u32(self._data, entry.offset + 8, new_qty)
                    entry.quantity = new_qty
                    return entry

        free = next(
            (e for e in entries if e.handle == 0 and e.item_id in (_EMPTY_ID, 0)), None
        )
        if free is None:
            raise ValueError("No free inventory slot")
        position = free.position

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
            last_off = self._last_index_off(list_off)
            last = _read_u32(self._data, last_off)
            if to_storage:
                # Stored items keep the index they had when held; new ones
                # continue the storage box's own counter.
                pos_index = (last + 1) & _INDEX_POS_MASK
                _write_u32(self._data, last_off, pos_index)
            else:
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
        quick slots keep pointing at it. Returns the new item id.
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
        same item at the destination, capped at max_quantity.
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
            free = next((e for e in entries if e.handle == 0), None)
            if free is None:
                raise ValueError("No free slot at the destination")
            last_off = self._last_index_off(dest)
            last = _read_u32(self._data, last_off)
            if to_storage:
                index = entry.index
                pos_index = entry.index & _INDEX_POS_MASK
            else:
                pos_index = _COMMON_INDEX_BASE + free.position
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
