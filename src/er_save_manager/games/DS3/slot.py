"""
DS3 decrypted slot data parser.

=== SLOT STRUCTURE OVERVIEW ===

[0x0000:0x0070]  Pre-gaitem header (version, steam pointer, unknown)
[0x0070:gaitem_end]  Gaitem table (6144 variable-size entries; see below)
[gaitem_end+120]  Character name (UTF-16LE, 32 bytes / 16 chars)
[gaitem_end+0x13F]  'fixed' anchor - all character stats use negative offsets from here

=== GAITEM TABLE (starts at 0x70) ===

6144 total slots. Entry size depends on type:
  Empty / Goods / Rings: 8 bytes  (gaitem_handle == 0, or type 0xA/0xB)
  Weapons (type 0x8xxx):  60 bytes
  Armor   (type 0x9xxx):  60 bytes

Weapon/armor 60-byte entry layout:
  [0:4]   gaitem_handle u32 LE  (bits 31-28 = type, bits 15-0 = sequential index)
  [4:8]   item_id u32 LE        (base weapon/armor ID from params)
  [8:12]  sort index u32 LE     (gaitem sort key, typically equals sequential counter)
  [12:16] upgrade_level u32 LE  (0-10 for regular, 0-5 for special)
  [16:20] unknown u32
  [20:60] gem sockets (5 x 8 bytes; 0x80000000 = empty socket)

=== CHARACTER STATS (relative to 'fixed' anchor) ===

All offsets are 'fixed + distance' where distances are negative (stats sit before anchor).
'fixed' = gaitem_end + 0x13F

  Souls:       fixed - 219  u32 LE
  HP:          fixed - 303  u32 LE  (live value; game reads this directly)
  FP:          fixed - 291  u32 LE
  Stamina:     fixed - 275  u32 LE
  Level:       fixed - 223  u16 LE
  Vigor:       fixed - 267  u16 LE
  Attunement:  fixed - 263  u16 LE
  Endurance:   fixed - 259  u16 LE
  Vitality:    fixed - 227  u16 LE
  Strength:    fixed - 255  u16 LE
  Dexterity:   fixed - 251  u16 LE
  Intelligence:fixed - 247  u16 LE
  Faith:       fixed - 243  u16 LE
  Luck:        fixed - 239  u16 LE

=== INVENTORY TABLE ===

Starts at: inventory_start = fixed + 0x1DD
Each entry: 16 bytes
  [0:4]   gaitem_handle u32 LE
  [4:8]   item_id u32 LE
  [8:12]  quantity u32 LE
  [12:16] index u32 LE  (lower 12 bits = sequential counter, upper 4 bits random)

Counters (signed i16 LE):
  first:  inventory_start - 4
  second: inventory_start + 0x8808  (= inventory_end)

=== STORAGE BOX ===

Computed via dynamic chain from fixed:
  inventory_end      = inventory_start + 0x8808
  above_storage_ctr  = inventory_end + 0x11C
  above_storage_size = u32 at above_storage_ctr
  table_1_end        = above_storage_ctr + 4 + above_storage_size * 8
  storage_box_start  = table_1_end + 0x190
  storage_box_end    = storage_box_start + 0x8800

=== NEW GAME PLUS / EVENT FLAGS ===

  gesture_end        = storage_box_end + 0xC + 0xA4
  table_2_size       = u32 at gesture_end
  table_2_end        = gesture_end + 4 + table_2_size * 4
  new_game_plus_off  = table_2_end + 0x92           (u16 LE; 0=NG, 1=NG+, ...)
  event_flag_start   = new_game_plus_off + 0xBCC

Boss/bonfire state base: event_flag_start - 0x12
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass

# Item type bits (upper nibble of gaitem_handle)
ITEM_TYPE_WEAPON = 0x80000000
ITEM_TYPE_ARMOR = 0x90000000
ITEM_TYPE_RING = 0xA0000000
ITEM_TYPE_GOOD = 0xB0000000

GAITEM_TABLE_OFFSET = 0x70
GAITEM_SLOT_COUNT = 6144
GAITEM_BASE_SIZE = 8
GAITEM_WA_SIZE = 60

# Offsets relative to gaitem_end
_NAME_REL = 120
_FIXED_REL = 0x13F
_NAME_LEN = 32  # bytes (16 UTF-16LE chars)

# Distances from 'fixed' (all negative - stats precede the anchor)
_SOULS_DIST = -219
_HP_DIST = -303
_FP_DIST = -291
_STAMINA_DIST = -275
_LEVEL_DIST = -223
_VIGOR_DIST = -267
_ATN_DIST = -263
_END_DIST = -259
_VIT_DIST = -227
_STR_DIST = -255
_DEX_DIST = -251
_INT_DIST = -247
_FTH_DIST = -243
_LUCK_DIST = -239

# Inventory
_INV_REL_FIXED = 0x1DD  # inventory_start = fixed + _INV_REL_FIXED
_INV_SIZE = 0x880C  # total inventory section (entries + 12 bytes of counters/pad)
_INV_DATA_SIZE = 0x8800  # entry area only: 2176 x 16-byte entries
_INV_C2_REL = 0x8808  # second counter = inv_start + _INV_C2_REL (i16)
_INV_ENTRY_SIZE = 16
_MAX_INV_SLOTS = _INV_DATA_SIZE // _INV_ENTRY_SIZE  # 2176

# Storage box chain offsets from inventory_end
_ABOVE_STORAGE_CTR_REL = 0x11C  # inventory_end + this = above_storage_counter offset
_STORAGE_BOX_FROM_TABLE1 = 0x190  # table_1_end + this = storage_box_start
_STORAGE_BOX_SIZE = 0x8800
_GESTURE_FROM_STORAGE_END = 0x0C
_GESTURE_SIZE = 0xA4

# Gaitem INSERT+TRIM constants
_INSERT_EXPAND = 60  # new weapon/armor gaitem entry size
_TRIM_NET = 52  # bytes trimmed from end of slot data to compensate
_END_TAIL = 0xD  # preserved trailing bytes at end of slot


def _scan_gaitem(
    data: bytearray, start: int = GAITEM_TABLE_OFFSET, slots: int = GAITEM_SLOT_COUNT
) -> int:
    """
    Scan the gaitem table and return the offset immediately after all entries.
    Variable-length: weapons/armor are 60 bytes; everything else is 8 bytes.
    """
    offset = start
    for _ in range(slots):
        if offset + GAITEM_BASE_SIZE > len(data):
            break
        handle = struct.unpack_from("<I", data, offset)[0]
        type_bits = handle & 0xF0000000
        if handle != 0 and type_bits in (ITEM_TYPE_WEAPON, ITEM_TYPE_ARMOR):
            offset += GAITEM_WA_SIZE
        else:
            offset += GAITEM_BASE_SIZE
    return offset


def _read_u16(data: bytearray, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def _read_u32(data: bytearray, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _write_u16(data: bytearray, off: int, val: int) -> None:
    struct.pack_into("<H", data, off, val & 0xFFFF)


def _write_u32(data: bytearray, off: int, val: int) -> None:
    struct.pack_into("<I", data, off, val & 0xFFFFFFFF)


@dataclass
class DS3GaitemEntry:
    """Single 8- or 60-byte gaitem table entry."""

    handle: int
    item_id: int
    offset: int  # absolute offset within slot data
    size: int  # 8 or 60

    @property
    def type_bits(self) -> int:
        return self.handle & 0xF0000000

    @property
    def is_empty(self) -> bool:
        return self.handle == 0


@dataclass
class DS3InventoryEntry:
    """Single 16-byte inventory table entry."""

    handle: int
    item_id: int
    quantity: int
    index: int
    offset: int  # absolute offset within slot data

    @property
    def type_bits(self) -> int:
        return self.handle & 0xF0000000

    @property
    def is_empty(self) -> bool:
        return self.handle == 0 and self.item_id == 0


class DS3Slot:
    """
    Parsed character slot from a single decrypted DS3 save entry.

    All offsets tracked from the gaitem scan - no hardcoded absolute positions.
    The gaitem_end value is the primary anchor; everything else derives from it.
    """

    def __init__(self, slot_index: int, data: bytearray) -> None:
        self.slot_index = slot_index
        self._data = data
        self._gaitem_end: int | None = None  # cached
        self._dynamic: dict | None = None  # cached dynamic chain

    # --- Empty check --------------------------------------------------------- #

    @property
    def is_empty(self) -> bool:
        """Slot has no character if name bytes are all zero."""
        try:
            ge = self._get_gaitem_end()
            name_off = ge + _NAME_REL
            if name_off + _NAME_LEN > len(self._data):
                return True
            return all(b == 0 for b in self._data[name_off : name_off + _NAME_LEN])
        except Exception:
            return True

    # --- Gaitem/anchor computation ------------------------------------------- #

    def _get_gaitem_end(self) -> int:
        if self._gaitem_end is None:
            self._gaitem_end = _scan_gaitem(self._data)
        return self._gaitem_end

    def _get_fixed(self) -> int:
        return self._get_gaitem_end() + _FIXED_REL

    @staticmethod
    def _probe_inv_size(data: bytearray, inv_start: int) -> int:
        """
        Return the inventory section size (0x8808 or 0x880C) for this slot.

        The 4-byte difference exists in saves with a larger shop/trade history block.
        Both sizes are tried; whichever yields a plausible above_storage_size wins.
        """
        for candidate in (_INV_SIZE, 0x8808):
            above_ctr = inv_start + candidate + _ABOVE_STORAGE_CTR_REL
            if above_ctr + 4 > len(data):
                continue
            val = struct.unpack_from("<I", data, above_ctr)[0]
            if val < 200000:
                return candidate
        return _INV_SIZE  # fallback

    def _get_dynamic(self) -> dict:
        """
        Compute all dynamic offsets from fixed anchor.
        Result is cached; call _invalidate_cache() after any INSERT/TRIM.
        """
        if self._dynamic is not None:
            return self._dynamic

        fixed = self._get_fixed()
        inv_start = fixed + _INV_REL_FIXED
        inv_size = self._probe_inv_size(self._data, inv_start)
        inv_end = inv_start + inv_size  # used for above_ctr_off only
        inv_data_end = inv_start + _INV_DATA_SIZE  # iteration bound (2176 entries)
        inv_c2_off = inv_start + (inv_size - 4)  # second counter (i16)
        above_ctr_off = inv_end + _ABOVE_STORAGE_CTR_REL
        above_size = _read_u32(self._data, above_ctr_off)
        table1_end = above_ctr_off + 4 + above_size * 8
        storage_start = table1_end + _STORAGE_BOX_FROM_TABLE1
        storage_end = storage_start + _STORAGE_BOX_SIZE
        gesture_start = storage_end + _GESTURE_FROM_STORAGE_END
        gesture_end = gesture_start + _GESTURE_SIZE
        table2_size = _read_u32(self._data, gesture_end)
        table2_end = gesture_end + 4 + table2_size * 4
        ng_plus_off = table2_end + 0x92
        ef_start = ng_plus_off + 0xBCC
        boss_base = ef_start - 0x12

        self._dynamic = {
            "inv_start": inv_start,
            "inv_end": inv_end,
            "inv_data_end": inv_data_end,
            "inv_c2_off": inv_c2_off,
            "storage_start": storage_start,
            "storage_end": storage_end,
            "ng_plus_off": ng_plus_off,
            "ef_start": ef_start,
            "boss_base": boss_base,
        }
        return self._dynamic

    def _invalidate_cache(self) -> None:
        """Must be called after any operation that shifts offsets (INSERT/TRIM)."""
        self._gaitem_end = None
        self._dynamic = None

    # --- Character name ------------------------------------------------------ #

    @property
    def name(self) -> str:
        ge = self._get_gaitem_end()
        off = ge + _NAME_REL
        raw = bytes(self._data[off : off + _NAME_LEN])
        # Stop at first UTF-16LE null pair (0x00 0x00 on even boundary)
        end = 0
        while end + 1 < _NAME_LEN:
            if raw[end] == 0 and raw[end + 1] == 0:
                break
            end += 2
        return raw[:end].decode("utf-16-le", errors="replace")

    @name.setter
    def name(self, value: str) -> None:
        ge = self._get_gaitem_end()
        off = ge + _NAME_REL
        self._data[off : off + _NAME_LEN] = b"\x00" * _NAME_LEN
        encoded = value.encode("utf-16-le")
        max_bytes = _NAME_LEN - 2
        self._data[off : off + min(len(encoded), max_bytes)] = encoded[:max_bytes]

    # --- Stats --------------------------------------------------------------- #

    @property
    def souls(self) -> int:
        return _read_u32(self._data, self._get_fixed() + _SOULS_DIST)

    @souls.setter
    def souls(self, val: int) -> None:
        _write_u32(self._data, self._get_fixed() + _SOULS_DIST, val)

    @property
    def hp(self) -> int:
        return _read_u32(self._data, self._get_fixed() + _HP_DIST)

    @hp.setter
    def hp(self, val: int) -> None:
        _write_u32(self._data, self._get_fixed() + _HP_DIST, val)

    @property
    def fp(self) -> int:
        return _read_u32(self._data, self._get_fixed() + _FP_DIST)

    @fp.setter
    def fp(self, val: int) -> None:
        _write_u32(self._data, self._get_fixed() + _FP_DIST, val)

    @property
    def stamina(self) -> int:
        return _read_u32(self._data, self._get_fixed() + _STAMINA_DIST)

    @stamina.setter
    def stamina(self, val: int) -> None:
        _write_u32(self._data, self._get_fixed() + _STAMINA_DIST, val)

    @property
    def level(self) -> int:
        return _read_u16(self._data, self._get_fixed() + _LEVEL_DIST)

    @level.setter
    def level(self, val: int) -> None:
        _write_u16(self._data, self._get_fixed() + _LEVEL_DIST, val)

    def get_stat(self, key: str) -> int:
        dist = _STAT_DISTS.get(key.lower())
        if dist is None:
            raise ValueError(f"Unknown stat: {key!r}")
        return _read_u16(self._data, self._get_fixed() + dist)

    def set_stat(self, key: str, val: int) -> None:
        dist = _STAT_DISTS.get(key.lower())
        if dist is None:
            raise ValueError(f"Unknown stat: {key!r}")
        _write_u16(self._data, self._get_fixed() + dist, val)

    # --- NG+ ----------------------------------------------------------------- #

    @property
    def ng_plus(self) -> int:
        off = self._get_dynamic()["ng_plus_off"]
        return _read_u16(self._data, off)

    @ng_plus.setter
    def ng_plus(self, val: int) -> None:
        off = self._get_dynamic()["ng_plus_off"]
        _write_u16(self._data, off, val)

    # --- Gaitem iteration ---------------------------------------------------- #

    def iter_gaitem(self) -> list[DS3GaitemEntry]:
        """Return all gaitem entries (including empties)."""
        entries = []
        offset = GAITEM_TABLE_OFFSET
        for _ in range(GAITEM_SLOT_COUNT):
            if offset + GAITEM_BASE_SIZE > len(self._data):
                break
            handle = _read_u32(self._data, offset)
            item_id = _read_u32(self._data, offset + 4)
            type_bits = handle & 0xF0000000
            if handle != 0 and type_bits in (ITEM_TYPE_WEAPON, ITEM_TYPE_ARMOR):
                size = GAITEM_WA_SIZE
            else:
                size = GAITEM_BASE_SIZE
            entries.append(DS3GaitemEntry(handle, item_id, offset, size))
            offset += size
        return entries

    # --- Inventory iteration ------------------------------------------------- #

    def iter_inventory(self) -> list[DS3InventoryEntry]:
        dyn = self._get_dynamic()
        entries = []
        off = dyn["inv_start"]
        end = dyn["inv_data_end"]
        while off < end:
            handle = _read_u32(self._data, off)
            item_id = _read_u32(self._data, off + 4)
            qty = _read_u32(self._data, off + 8)
            idx = _read_u32(self._data, off + 12)
            entries.append(DS3InventoryEntry(handle, item_id, qty, idx, off))
            off += _INV_ENTRY_SIZE
        return entries

    def iter_storage(self) -> list[DS3InventoryEntry]:
        dyn = self._get_dynamic()
        entries = []
        off = dyn["storage_start"]
        end = dyn["storage_end"]
        while off < end:
            handle = _read_u32(self._data, off)
            item_id = _read_u32(self._data, off + 4)
            qty = _read_u32(self._data, off + 8)
            idx = _read_u32(self._data, off + 12)
            entries.append(DS3InventoryEntry(handle, item_id, qty, idx, off))
            off += _INV_ENTRY_SIZE
        return entries

    # --- Boss / bonfire flags ------------------------------------------------ #

    def get_boss_defeated(self, offset: int, defeat_value: int) -> bool:
        """
        Read boss defeat state.
        offset is relative to boss_base (event_flag_start - 0x12).
        defeat_value is the byte value that means 'defeated'.
        """
        base = self._get_dynamic()["boss_base"]
        abs_off = base + offset
        if abs_off >= len(self._data):
            return False
        fmt = "<H" if defeat_value > 0xFF else "<B"
        val = struct.unpack_from(fmt, self._data, abs_off)[0]
        return val == defeat_value

    def set_boss_defeated(self, offset: int, defeat_value: int, defeated: bool) -> None:
        base = self._get_dynamic()["boss_base"]
        abs_off = base + offset
        fmt = "<H" if defeat_value > 0xFF else "<B"
        val = defeat_value if defeated else 0
        struct.pack_into(fmt, self._data, abs_off, val)

    def get_bonfire_unlocked(self, offset: int, unlock_value: int) -> bool:
        base = self._get_dynamic()["boss_base"]
        abs_off = base + offset
        if abs_off >= len(self._data):
            return False
        fmt = "<H" if unlock_value > 0xFF else "<B"
        val = struct.unpack_from(fmt, self._data, abs_off)[0]
        return val == unlock_value

    def set_bonfire_unlocked(
        self, offset: int, unlock_value: int, unlocked: bool
    ) -> None:
        base = self._get_dynamic()["boss_base"]
        abs_off = base + offset
        fmt = "<H" if unlock_value > 0xFF else "<B"
        val = unlock_value if unlocked else 0
        struct.pack_into(fmt, self._data, abs_off, val)

    # --- Inventory counters -------------------------------------------------- #

    def _increment_inv_counters(self) -> None:
        dyn = self._get_dynamic()
        inv_start = dyn["inv_start"]
        c1_off = inv_start - 4
        c1 = struct.unpack_from("<h", self._data, c1_off)[0] + 1
        struct.pack_into("<h", self._data, c1_off, c1)
        c2_off = dyn["inv_c2_off"]
        c2 = struct.unpack_from("<h", self._data, c2_off)[0] + 1
        struct.pack_into("<h", self._data, c2_off, c2)

    def _increment_storage_counter(self) -> None:
        dyn = self._get_dynamic()
        ctr_off = dyn["storage_start"] - 4
        ctr = _read_u32(self._data, ctr_off) + 1
        _write_u32(self._data, ctr_off, ctr)

    # --- Item index helper --------------------------------------------------- #

    def _next_inv_index(self) -> tuple[int, ...]:
        """Compute sequential counter + random nibble for new inventory entries."""
        all_entries = self.iter_inventory()
        highest = (
            max(
                (
                    e.index & 0x00000FFF
                    for e in all_entries
                    if e.index & 0x00000FFF != 0
                ),
                default=0,
            )
            + 1
        )
        hi = highest.to_bytes(2, "little")
        rb = os.urandom(1)[0]
        return hi[0], (rb & 0xF0) | (hi[1] & 0x0F)

    # --- Add goods / rings --------------------------------------------------- #

    def add_goods_rings(self, item_id: int, item_type: int, quantity: int) -> bool:
        """
        Add a goods or ring item to inventory.

        item_id: raw item ID from params (e.g., 0x4000006C for goods)
        item_type: ITEM_TYPE_GOOD or ITEM_TYPE_RING
        quantity: desired stack size (clamped to 1-99)

        Updates an existing stack if one exists (goods only).
        Falls back to storage if inventory is full.
        Returns True on success.
        """
        qty = max(1, min(quantity, 99))
        dyn = self._get_dynamic()
        inv_start = dyn["inv_start"]
        inv_end = dyn["inv_data_end"]

        # Update existing goods stack
        if item_type == ITEM_TYPE_GOOD:
            off = inv_start
            while off < inv_end:
                h = _read_u32(self._data, off)
                iid = _read_u32(self._data, off + 4)
                if (h & 0xF0000000) == ITEM_TYPE_GOOD and iid == item_id:
                    _write_u32(self._data, off + 8, qty)
                    return True
                off += _INV_ENTRY_SIZE

        # Find first empty inventory slot
        first_empty = None
        off = inv_start
        while off < inv_end:
            h = _read_u32(self._data, off)
            iid = _read_u32(self._data, off + 4)
            if h == 0 and iid == 0:
                first_empty = off
                break
            off += _INV_ENTRY_SIZE

        if first_empty is None:
            return self._add_to_storage(item_id, item_type, qty)

        # Build 16-byte entry
        slot = _build_goods_ring_slot(item_id, item_type, qty, self._next_inv_index())
        self._data[first_empty : first_empty + _INV_ENTRY_SIZE] = slot
        self._increment_inv_counters()
        return True

    # --- Add weapons / armor (INSERT + TRIM) --------------------------------- #

    def add_weapon_armor(self, item_id: int, item_type: int, upgrade: int = 0) -> bool:
        """
        Add a weapon or armor to inventory using the INSERT+TRIM algorithm.

        Inserts a 60-byte gaitem entry at the first available empty gaitem slot,
        removes the next 8-byte empty gaitem slot, adds a 16-byte inventory entry,
        then trims 52 bytes from the safe zero region near end of slot data to
        maintain constant total plaintext size.

        upgrade: 0-10 for regular weapons, 0-5 for special/boss.
        """
        gaitem_entries = self.iter_gaitem()
        empties = [e for e in gaitem_entries if e.is_empty]
        if len(empties) < 2:
            return False

        # Sequential gaitem handle index
        ga_max = (
            max(
                (e.handle & 0x0000FFFF for e in gaitem_entries if e.handle != 0),
                default=0,
            )
            + 1
        )
        ga_hi = ga_max.to_bytes(2, "little")

        # Build 60-byte gaitem entry
        ga_slot = _build_wa_gaitem_slot(ga_hi, item_id, item_type, upgrade)
        insert_at = empties[0].offset

        # INSERT: replace 8-byte empty slot with 60-byte weapon entry (+52 bytes net so far)
        self._data = (
            self._data[:insert_at]
            + ga_slot
            + self._data[insert_at + GAITEM_BASE_SIZE :]
        )
        self._invalidate_cache()

        # Re-scan to find the new first empty gaitem slot (after insertion)
        post_entries = self.iter_gaitem_raw(slots=GAITEM_SLOT_COUNT + 1)
        post_empties = [e for e in post_entries if e.is_empty]
        if not post_empties:
            # Rollback: this shouldn't happen but guard anyway
            return False
        del_at = post_empties[0].offset

        # DELETE: remove next 8-byte empty gaitem slot (-8 bytes, net +44 from start)
        self._data = self._data[:del_at] + self._data[del_at + GAITEM_BASE_SIZE :]
        self._invalidate_cache()

        # Add inventory entry
        dyn = self._get_dynamic()
        inv_start = dyn["inv_start"]
        inv_end = dyn["inv_data_end"]

        first_empty = None
        off = inv_start
        while off < inv_end:
            h = _read_u32(self._data, off)
            iid = _read_u32(self._data, off + 4)
            if h == 0 and iid == 0:
                first_empty = off
                break
            off += _INV_ENTRY_SIZE

        if first_empty is None:
            # Inventory full - write to storage instead; still trim to balance INSERT
            inv_slot = _build_wa_inv_slot(
                ga_hi, item_id, item_type, self._next_inv_index()
            )
            self._add_raw_to_storage(inv_slot)
        else:
            inv_slot = _build_wa_inv_slot(
                ga_hi, item_id, item_type, self._next_inv_index()
            )
            self._data[first_empty : first_empty + _INV_ENTRY_SIZE] = inv_slot
            self._increment_inv_counters()

        # TRIM: remove _TRIM_NET bytes from the safe zero area near end of slot
        # Preserves the last _END_TAIL bytes (fixed trailing bytes)
        trim_end = len(self._data) - _END_TAIL
        trim_start = trim_end - _TRIM_NET
        if trim_start < 0:
            return False
        self._data = self._data[:trim_start] + self._data[trim_end:]
        self._invalidate_cache()
        return True

    # --- Remove item --------------------------------------------------------- #

    def remove_item(self, inv_offset: int) -> None:
        """Zero out an inventory entry at the given absolute offset."""
        self._data[inv_offset : inv_offset + _INV_ENTRY_SIZE] = (
            b"\x00" * _INV_ENTRY_SIZE
        )

    # --- Storage fallback ---------------------------------------------------- #

    def _add_to_storage(self, item_id: int, item_type: int, quantity: int) -> bool:
        slot = _build_goods_ring_slot(
            item_id, item_type, quantity, self._next_inv_index()
        )
        return self._add_raw_to_storage(slot)

    def _add_raw_to_storage(self, slot: bytearray) -> bool:
        dyn = self._get_dynamic()
        off = dyn["storage_start"]
        end = dyn["storage_end"]
        while off < end:
            h = _read_u32(self._data, off)
            iid = _read_u32(self._data, off + 4)
            if h == 0 and iid == 0:
                self._data[off : off + _INV_ENTRY_SIZE] = slot
                self._increment_storage_counter()
                return True
            off += _INV_ENTRY_SIZE
        return False

    def iter_gaitem_raw(self, slots: int = GAITEM_SLOT_COUNT) -> list[DS3GaitemEntry]:
        """Scan gaitem with a custom slot count (used internally during INSERT)."""
        entries = []
        offset = GAITEM_TABLE_OFFSET
        for _ in range(slots):
            if offset + GAITEM_BASE_SIZE > len(self._data):
                break
            handle = _read_u32(self._data, offset)
            item_id = _read_u32(self._data, offset + 4)
            type_bits = handle & 0xF0000000
            if handle != 0 and type_bits in (ITEM_TYPE_WEAPON, ITEM_TYPE_ARMOR):
                size = GAITEM_WA_SIZE
            else:
                size = GAITEM_BASE_SIZE
            entries.append(DS3GaitemEntry(handle, item_id, offset, size))
            offset += size
        return entries

    def get_raw(self) -> bytearray:
        return self._data


# --- Stat key to distance map ------------------------------------------------ #

_STAT_DISTS: dict[str, int] = {
    "vig": _VIGOR_DIST,
    "atn": _ATN_DIST,
    "end": _END_DIST,
    "vit": _VIT_DIST,
    "str": _STR_DIST,
    "dex": _DEX_DIST,
    "int": _INT_DIST,
    "fth": _FTH_DIST,
    "lck": _LUCK_DIST,
}


# --- Slot builder helpers ---------------------------------------------------- #


def _build_goods_ring_slot(
    item_id: int, item_type: int, qty: int, idx_bytes: tuple[int, int]
) -> bytearray:
    """Build a 16-byte inventory entry for a goods or ring item."""
    slot = bytearray(16)
    # gaitem_handle: type nibble + lower 24 bits of item_id
    gh = (item_type & 0xFF000000) | (item_id & 0x00FFFFFF)
    _write_u32(slot, 0, gh)
    _write_u32(slot, 4, item_id)
    _write_u32(slot, 8, qty)
    # Index field: [idx_lo][idx_hi_nibble+random][0xCF][0x1F]
    slot[12] = idx_bytes[0]
    slot[13] = idx_bytes[1]
    slot[14] = 0xCF
    slot[15] = 0x1F
    return slot


def _build_wa_gaitem_slot(
    ga_hi: bytes, item_id: int, item_type: int, upgrade: int
) -> bytearray:
    """Build a 60-byte gaitem table entry for a weapon or armor."""
    # Type constant bytes: 0x80 for weapons, 0x90 for armor
    type_byte = 0x80 if item_type == ITEM_TYPE_WEAPON else 0x90
    slot = bytearray(60)
    # [0:2] = sequential handle counter (ga_hi = 2-byte LE)
    slot[0] = ga_hi[0]
    slot[1] = ga_hi[1]
    # [2:4] = type flags
    slot[2] = type_byte
    slot[3] = type_byte
    # [4:8] = item_id
    _write_u32(slot, 4, item_id)
    # [8:12] = sort index (same value as counter)
    _write_u32(slot, 8, int.from_bytes(ga_hi, "little"))
    # [12:16] = upgrade level
    _write_u32(slot, 12, upgrade & 0xFF)
    # [16:20] = unknown, leave zero
    # [20:60] = 5 gem sockets, each 8 bytes; 0x80000000 = empty socket
    for i in range(5):
        _write_u32(slot, 20 + i * 8, 0x80000000)
    return slot


def _build_wa_inv_slot(
    ga_hi: bytes, item_id: int, item_type: int, idx_bytes: tuple[int, int]
) -> bytearray:
    """Build a 16-byte inventory entry for a weapon or armor."""
    type_byte = 0x80 if item_type == ITEM_TYPE_WEAPON else 0x90
    slot = bytearray(16)
    # gaitem_handle: [counter_lo][counter_hi][type_byte][type_byte]
    slot[0] = ga_hi[0]
    slot[1] = ga_hi[1]
    slot[2] = type_byte
    slot[3] = type_byte
    # item_id
    _write_u32(slot, 4, item_id)
    # quantity = 1
    _write_u32(slot, 8, 1)
    # index bytes
    slot[12] = idx_bytes[0]
    slot[13] = idx_bytes[1]
    slot[14] = 0xCF
    slot[15] = 0x1F
    return slot
