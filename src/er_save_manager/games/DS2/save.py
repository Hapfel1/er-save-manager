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
           offset 0x732, identical padding after ~0x5A87F), but the internal
           structure is not mapped. Not floats/ASCII text in any recognizable
           pattern; contents preserved as-is on save.
  21       Single ~2MB entry: zlib-compressed (8-byte size header, then a
           standard zlib stream) nested BND4 archive of ~170 real entries.
           This is the game's static param/regulation data (EnemyParam,
           ItemParam, WeaponParam, SpEffectParam, RegulationEnglish.fmg,
           etc), embedded for version checking. NOT per-character save
           state; not useful for event flags or world state.
  22       Single ~13KB entry: same per-slot name cache as entry 0 (see
           CHARACTER_SELECT_ENTRY below). Rest of the entry unmapped.

Entries 11-22 are decrypted and re-encrypted unchanged on save since their
internal structure has not been reverse engineered yet.

Key source: DS2 SOTFS PC AES key from the souls_givifier project (jtesta).
Profile slot field offsets
(name/stats/souls/hp/ng/inventory) from the Dark-Souls-2-Save-Editor-PS4-PC
project
"""

from __future__ import annotations

import struct
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from er_save_manager.games.DS2.regulation import Regulation

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
SOULS_OFFSET = 60
HP_OFFSET = 72
# Stored 1-based: 1 is the first playthrough, 2 is NG+1, and so on.
# Character.new_game_plus exposes the 0-based cycle.
NG_OFFSET = 1028
NG_PLUS_MAX = 7

# Profile order of the attributes matches the game's class param rows:
# vigor, endurance, vitality, attunement, strength, dexterity,
# intelligence (0x2C), faith (0x2E), adaptability (0x30).
STAT_OFFSETS = {
    "level": 0x38,
    "vigor": 32,
    "attunement": 38,
    "endurance": 34,
    "vitality": 36,
    "strength": 40,
    "dexterity": 42,
    "intelligence": 44,
    "faith": 46,
    "adaptability": 48,
}

LEVEL_STAT_KEYS = [k for k in STAT_OFFSETS if k != "level"]


INVENTORY_START = 0x1E2C
INVENTORY_END = 0x10E1C
INVENTORY_SLOT_SIZE = 16

# Stack limit used for items the regulation does not know.
_DEFAULT_MAX_STACK = 99

# Categories stored in the key item list instead of the main inventory.
KEY_LIST_CATEGORIES = frozenset({"keys", "gestures"})

# Categories where an item can be owned only once.
UNIQUE_CATEGORIES = frozenset({"gestures"})

# Categories whose items carry an upgrade level in their inventory entry.
UPGRADABLE_CATEGORIES = frozenset({"weapons", "armors"})
_UPGRADE_MASK = 0xFF

KEY_ITEMS_START = 0x10E30
KEY_ITEMS_END = 0x11DF0

# Candidate event/quest/boss flag region: unmapped, see module docstring.
FLAG_REGION_START = 0x11E00
FLAG_REGION_END = 0x1B2FC

# Occupancy entry (entry 0) layout: fixed stride per character slot.
_OCC_STRIDE = 496
_OCC_FLAG_OFFSET = 892
_OCC_NAME_OFFSET = 1286
_OCC_NAME_SIZE = 28

CHARACTER_SELECT_ENTRY = 22
_SELECT_NAME_OFFSET = 442
_SELECT_NAME_SIZE = 28


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

    # The upgrade level is the low byte of unk_2 for weapons and armor. Seen
    # as 1 and 3 on upgraded weapons and 1 and 2 on upgraded armor, and 0 on
    # everything else. Higher bytes are preserved on write.
    @property
    def upgrade(self) -> int:
        return self.unk_2 & _UPGRADE_MASK

    @upgrade.setter
    def upgrade(self, level: int) -> None:
        self.unk_2 = (self.unk_2 & ~_UPGRADE_MASK) | (int(level) & _UPGRADE_MASK)


@dataclass
class BulkAddResult:
    """Outcome counts of Character.add_items_bulk."""

    added: int = 0
    updated: int = 0  # existing stacks whose quantity was set
    skipped_owned: int = 0  # non-stackable items already in the inventory
    clamped: int = 0  # items whose requested upgrade exceeded their cap
    no_space: int = 0  # items dropped because no empty slot was left


def parse_inventory(data: bytes, start: int, end: int) -> list[InventoryItem]:
    items = []
    offset = start
    while offset < end:
        items.append(InventoryItem.from_bytes(data, offset))
        offset += INVENTORY_SLOT_SIZE
    return items


_VALID_NAME_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_"
)


def _is_valid_name(name: str) -> bool:
    return bool(name) and all(c in _VALID_NAME_CHARS for c in name)


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
        raw = bytes(self._data[NAME_OFFSET : NAME_OFFSET + NAME_SIZE])
        return raw.decode("utf-16-le", errors="ignore").rstrip("\x00")

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
    def hp(self) -> int:
        return struct.unpack_from("<I", self._data, HP_OFFSET)[0]

    @hp.setter
    def hp(self, value: int) -> None:
        struct.pack_into(
            "<I", self._data, HP_OFFSET, max(0, min(int(value), 0xFFFFFFFF))
        )

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

    def write_inventory_slot(self, item: InventoryItem) -> None:
        self._data[item.offset : item.offset + INVENTORY_SLOT_SIZE] = item.to_bytes()

    def raw(self) -> bytearray:
        return self._data

    # ------------------------------------------------------------------
    # Inventory add / delete
    # ------------------------------------------------------------------

    STACKABLE_CATEGORIES = {"goods", "bolts", "spells", "upgrade", "seamless"}

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
        regulation = self._regulation()
        held = regulation.max_held(item_id) if regulation else None
        return held if held else _DEFAULT_MAX_STACK

    def max_upgrade(self, item_id: int, category: str) -> int:
        """Highest upgrade level, or 0 when unknown or the regulation cannot
        be read."""
        regulation = self._regulation()
        return regulation.max_upgrade(item_id, category) if regulation else 0

    def _region(self, category: str) -> tuple[int, int]:
        if category in KEY_LIST_CATEGORIES:
            return KEY_ITEMS_START, KEY_ITEMS_END
        return INVENTORY_START, INVENTORY_END

    def _find_empty_slot(self, start: int, end: int) -> InventoryItem | None:
        for item in parse_inventory(self._data, start, end):
            if item.item_id == 0:
                return item
        return None

    def _find_item(self, item_id: int, start: int, end: int) -> InventoryItem | None:
        for item in parse_inventory(self._data, start, end):
            if item.item_id == item_id:
                return item
        return None

    def owns(self, item_id: int) -> bool:
        return self._find_item_anywhere(item_id) is not None

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
    ) -> bool:
        """Add an item to inventory (or the key item list for the categories in
        KEY_LIST_CATEGORIES).

        For stackable categories, sets an existing stack's quantity unless
        stack=False forces a new slot. Returns False if there is no empty
        slot available or the item is in a unique category and already owned.
        quantity is capped at the item's stack limit and upgrade at its maximum
        level.
        """
        if category in UNIQUE_CATEGORIES and self.owns(item_id):
            return False
        start, end = self._region(category)
        stackable = category in self.STACKABLE_CATEGORIES

        if stackable and stack:
            existing = self._find_item(item_id, start, end)
            if existing is not None:
                existing.quantity = min(int(quantity), self.max_stack(item_id))
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
        else:
            new_item = InventoryItem(empty.offset, item_id, 0, 1, 0)

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

    def add_items_bulk(
        self,
        item_ids: Iterable[int],
        category: str,
        quantity: int = 1,
        upgrade: int = 0,
    ) -> BulkAddResult:
        """Add many items of one category with a single inventory scan.

        Stackable items already owned get their quantity set, matching
        add_item. Other items already owned are skipped. quantity is capped
        per item at its stack limit. For weapons and armor, upgrade is
        clamped per item to its maximum level.
        """
        result = BulkAddResult()
        start, end = self._region(category)
        slots = parse_inventory(self._data, start, end)

        owned: dict[int, InventoryItem] = {}
        for slot in slots:
            if slot.item_id:
                owned.setdefault(slot.item_id, slot)
        empty = iter([slot for slot in slots if slot.item_id == 0])

        stackable = category in self.STACKABLE_CATEGORIES
        upgradable = category in UPGRADABLE_CATEGORIES
        durability = (
            self._durability_lookup(category)
            if category in self._DEFAULT_DURABILITY
            else None
        )

        for item_id in item_ids:
            existing = owned.get(item_id)
            if existing is not None:
                if not stackable:
                    result.skipped_owned += 1
                    continue
                existing.quantity = min(int(quantity), self.max_stack(item_id))
                self.write_inventory_slot(existing)
                result.updated += 1
                continue

            slot = next(empty, None)
            if slot is None:
                result.no_space += 1
                continue

            level = 0
            if upgradable:
                level = min(int(upgrade), self.max_upgrade(item_id, category))
                if level < int(upgrade):
                    result.clamped += 1

            if stackable:
                new_item = InventoryItem(
                    slot.offset,
                    item_id,
                    0,
                    min(int(quantity), self.max_stack(item_id)),
                    0,
                )
            elif durability is not None:
                new_item = InventoryItem(
                    slot.offset, item_id, 0, durability(item_id), level
                )
            else:
                new_item = InventoryItem(slot.offset, item_id, 0, 1, 0)

            self.write_inventory_slot(new_item)
            owned[item_id] = new_item
            result.added += 1
        return result

    def delete_item(self, item_id: int, category: str) -> bool:
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
            name_bytes = occ_data[name_off : name_off + _OCC_NAME_SIZE]
            name = name_bytes.decode("utf-16-le", errors="ignore").rstrip("\x00")
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
        occ_data = self.container.get_entry(OCCUPANCY_ENTRY)
        flag_off = _OCC_FLAG_OFFSET + _OCC_STRIDE * slot_index
        if flag_off >= len(occ_data):
            return False
        return occ_data[flag_off] != 0

    def save_to_file(self, path: str | Path) -> None:
        for i, character in enumerate(self.characters):
            self.container.set_entry(PROFILE_ENTRY_START + i, character.raw())
        self.sync_name_caches()
        self.container.save_to_file(path)
