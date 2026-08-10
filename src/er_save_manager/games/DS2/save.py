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
           Confirmed to hold per-character data (differs between characters
           starting at offset 0x732, identical padding after ~0x5A87F), but
           the internal structure is not mapped. Not floats/ASCII text in
           any recognizable pattern; contents preserved as-is on save.
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
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

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
NG_OFFSET = 1028
NG_PLUS_MAX = 7

STAT_OFFSETS = {
    "level": 0x38,
    "vigor": 32,
    "attunement": 38,
    "endurance": 34,
    "vitality": 36,
    "strength": 40,
    "dexterity": 42,
    "intelligence": 46,
    "faith": 48,
    "adaptability": 44,
}

LEVEL_STAT_KEYS = [k for k in STAT_OFFSETS if k != "level"]


INVENTORY_START = 0x1E2C
INVENTORY_END = 0x10E1C
INVENTORY_SLOT_SIZE = 16

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

    def __init__(self, data: bytearray) -> None:
        self._data = data

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
        return struct.unpack_from("<H", self._data, NG_OFFSET)[0]

    @new_game_plus.setter
    def new_game_plus(self, value: int) -> None:
        struct.pack_into("<H", self._data, NG_OFFSET, max(0, min(int(value), 0xFFFF)))

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

    STACKABLE_CATEGORIES = {"goods", "bolts", "spells", "upgrade"}

    _DEFAULT_TEMPLATE = {
        "weapons": (0x00192D50, 0x42200000, 0x00000000),
        "armors": (0x0142E0A4, 0x437F0000, 0x00000000),
        "rings": (0x02628110, 0x42F00000, 0x00000000),
    }

    def _region(self, category: str) -> tuple[int, int]:
        if category == "keys":
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

    def add_item(
        self, item_id: int, category: str, quantity: int = 1, stack: bool = True
    ) -> bool:
        """Add an item to inventory (or key items for category == "keys").

        For stackable categories, increases an existing stack's quantity
        unless stack=False forces a new slot. Returns False if there is no
        empty slot available.
        """
        start, end = self._region(category)
        stackable = category in self.STACKABLE_CATEGORIES

        if stackable and stack:
            existing = self._find_item(item_id, start, end)
            if existing is not None:
                existing.quantity = min(int(quantity), 99)
                self.write_inventory_slot(existing)
                return True

        empty = self._find_empty_slot(start, end)
        if empty is None:
            return False

        if stackable:
            new_item = InventoryItem(
                empty.offset, item_id, 0, min(int(quantity), 99), 0
            )
        elif category in self._DEFAULT_TEMPLATE:
            existing = self._find_item_by_category(category, start, end)
            if existing is not None:
                unk_1, dur, unk_2 = existing.unk_1, existing.quantity, existing.unk_2
            else:
                unk_1, dur, unk_2 = self._DEFAULT_TEMPLATE[category]
            new_item = InventoryItem(empty.offset, item_id, unk_1, dur, unk_2)
        else:
            new_item = InventoryItem(empty.offset, item_id, 0, 1, 0)

        self.write_inventory_slot(new_item)
        return True

    def _find_item_by_category(
        self, category: str, start: int, end: int
    ) -> InventoryItem | None:
        """Find any existing non-empty item in the region, used to copy a
        realistic unk_1/durability template for a brand new item."""
        from er_save_manager.games.DS2.item_database import build_item_db

        db = build_item_db()
        for item in parse_inventory(self._data, start, end):
            if item.item_id == 0:
                continue
            info = db.get(item.item_id)
            if info and info[1] == category:
                return item
        return None

    def delete_item(self, item_id: int, category: str) -> bool:
        """Zero out the first matching item slot. Returns False if not found."""
        start, end = self._region(category)
        existing = self._find_item(item_id, start, end)
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
            Character(container.get_entry(PROFILE_ENTRY_START + i))
            for i in range(CHARACTER_SLOTS)
        ]

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
