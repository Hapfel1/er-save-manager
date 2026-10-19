"""
Elden Ring Save Parser - Equipment and Inventory Structures

Contains all equipment, inventory, and item-related structures.
Based on ER-Save-Lib Rust implementation.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from io import BytesIO
from itertools import chain
from operator import attrgetter

from er_save_manager.parser.er_types import read_exact

# ============================================================================
# BASE CLASS FOR EQUIPMENT SLOTS
# ============================================================================


@dataclass
class EquipmentSlots:
    """
    Base class for equipment slot structures (88 bytes).

    Contains 22 fields representing:
    - 6 weapon slots (left/right hand 1/2/3)
    - 4 ammo slots (arrows/bolts 1/2)
    - 4 armor slots (head/chest/arms/legs)
    - 4 talisman slots
    - arrows3/bolts3, hair and talisman5: slots of the in-memory ChrAsm that the
      game never fills (always empty in saves)

    Used by: EquippedItemsEquipIndex, EquippedItemsItemIds, EquippedItemsGaitemHandles
    """

    left_hand_armament1: int = 0
    right_hand_armament1: int = 0
    left_hand_armament2: int = 0
    right_hand_armament2: int = 0
    left_hand_armament3: int = 0
    right_hand_armament3: int = 0
    arrows1: int = 0
    bolts1: int = 0
    arrows2: int = 0
    bolts2: int = 0
    arrows3: int = 0
    bolts3: int = 0
    head: int = 0
    chest: int = 0
    arms: int = 0
    legs: int = 0
    hair: int = 0
    talisman1: int = 0
    talisman2: int = 0
    talisman3: int = 0
    talisman4: int = 0
    talisman5: int = 0

    @classmethod
    def read(cls, f: BytesIO):
        """Read equipment slots from stream (88 bytes)"""
        return cls(
            left_hand_armament1=struct.unpack("<I", f.read(4))[0],
            right_hand_armament1=struct.unpack("<I", f.read(4))[0],
            left_hand_armament2=struct.unpack("<I", f.read(4))[0],
            right_hand_armament2=struct.unpack("<I", f.read(4))[0],
            left_hand_armament3=struct.unpack("<I", f.read(4))[0],
            right_hand_armament3=struct.unpack("<I", f.read(4))[0],
            arrows1=struct.unpack("<I", f.read(4))[0],
            bolts1=struct.unpack("<I", f.read(4))[0],
            arrows2=struct.unpack("<I", f.read(4))[0],
            bolts2=struct.unpack("<I", f.read(4))[0],
            arrows3=struct.unpack("<I", f.read(4))[0],
            bolts3=struct.unpack("<I", f.read(4))[0],
            head=struct.unpack("<I", f.read(4))[0],
            chest=struct.unpack("<I", f.read(4))[0],
            arms=struct.unpack("<I", f.read(4))[0],
            legs=struct.unpack("<I", f.read(4))[0],
            hair=struct.unpack("<I", f.read(4))[0],
            talisman1=struct.unpack("<I", f.read(4))[0],
            talisman2=struct.unpack("<I", f.read(4))[0],
            talisman3=struct.unpack("<I", f.read(4))[0],
            talisman4=struct.unpack("<I", f.read(4))[0],
            talisman5=struct.unpack("<I", f.read(4))[0],
        )

    def write(self, f: BytesIO):
        """Write equipment slots to stream (88 bytes)"""
        f.write(struct.pack("<I", self.left_hand_armament1))
        f.write(struct.pack("<I", self.right_hand_armament1))
        f.write(struct.pack("<I", self.left_hand_armament2))
        f.write(struct.pack("<I", self.right_hand_armament2))
        f.write(struct.pack("<I", self.left_hand_armament3))
        f.write(struct.pack("<I", self.right_hand_armament3))
        f.write(struct.pack("<I", self.arrows1))
        f.write(struct.pack("<I", self.bolts1))
        f.write(struct.pack("<I", self.arrows2))
        f.write(struct.pack("<I", self.bolts2))
        f.write(struct.pack("<I", self.arrows3))
        f.write(struct.pack("<I", self.bolts3))
        f.write(struct.pack("<I", self.head))
        f.write(struct.pack("<I", self.chest))
        f.write(struct.pack("<I", self.arms))
        f.write(struct.pack("<I", self.legs))
        f.write(struct.pack("<I", self.hair))
        f.write(struct.pack("<I", self.talisman1))
        f.write(struct.pack("<I", self.talisman2))
        f.write(struct.pack("<I", self.talisman3))
        f.write(struct.pack("<I", self.talisman4))
        f.write(struct.pack("<I", self.talisman5))


# ============================================================================
# EQUIPMENT INDEXES
# ============================================================================


@dataclass
class EquippedItemsEquipIndex(EquipmentSlots):
    """
    Equipment slot indexes (88 bytes).

    Indexes into inventory arrays for currently equipped items.
    Inherits all 22 fields from EquipmentSlots.
    """

    pass


@dataclass
class ActiveWeaponSlotsAndArmStyle:
    """Active weapon slots and arm style (0x1C = 28 bytes)"""

    arm_style: int = 0
    left_hand_weapon_active_slot: int = 0
    right_hand_weapon_active_slot: int = 0
    left_arrow_active_slot: int = 0
    right_arrow_active_slot: int = 0
    left_bolt_active_slot: int = 0
    right_bolt_active_slot: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> ActiveWeaponSlotsAndArmStyle:
        """Read ActiveWeaponSlotsAndArmStyle from stream (28 bytes)"""
        return cls(
            arm_style=struct.unpack("<I", f.read(4))[0],
            left_hand_weapon_active_slot=struct.unpack("<I", f.read(4))[0],
            right_hand_weapon_active_slot=struct.unpack("<I", f.read(4))[0],
            left_arrow_active_slot=struct.unpack("<I", f.read(4))[0],
            right_arrow_active_slot=struct.unpack("<I", f.read(4))[0],
            left_bolt_active_slot=struct.unpack("<I", f.read(4))[0],
            right_bolt_active_slot=struct.unpack("<I", f.read(4))[0],
        )

    def write(self, f: BytesIO):
        """Write ActiveWeaponSlotsAndArmStyle to stream (28 bytes)"""
        f.write(struct.pack("<I", self.arm_style))
        f.write(struct.pack("<I", self.left_hand_weapon_active_slot))
        f.write(struct.pack("<I", self.right_hand_weapon_active_slot))
        f.write(struct.pack("<I", self.left_arrow_active_slot))
        f.write(struct.pack("<I", self.right_arrow_active_slot))
        f.write(struct.pack("<I", self.left_bolt_active_slot))
        f.write(struct.pack("<I", self.right_bolt_active_slot))


@dataclass
class EquippedItemsItemIds(EquipmentSlots):
    """
    Equipment item IDs (88 bytes).

    Item IDs of currently equipped items.
    Inherits all 22 fields from EquipmentSlots.
    """

    pass


@dataclass
class EquippedItemsGaitemHandles(EquipmentSlots):
    """
    Equipment Gaitem handles (88 bytes).

    Gaitem handles for currently equipped items.
    Inherits all 22 fields from EquipmentSlots.
    """

    pass


@dataclass
class InventoryItem:
    """Single inventory item (12 bytes)"""

    gaitem_handle: int = 0
    quantity: int = 0
    acquisition_index: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> InventoryItem:
        """Read InventoryItem from stream (12 bytes)"""
        return cls(
            gaitem_handle=struct.unpack("<I", f.read(4))[0],
            quantity=struct.unpack("<I", f.read(4))[0],
            acquisition_index=struct.unpack("<I", f.read(4))[0],
        )

    def write(self, f: BytesIO):
        """Write InventoryItem to stream (12 bytes)"""
        f.write(struct.pack("<I", self.gaitem_handle))
        f.write(struct.pack("<I", self.quantity))
        f.write(struct.pack("<I", self.acquisition_index))


_INVENTORY_ITEM_FIELDS = attrgetter("gaitem_handle", "quantity", "acquisition_index")


def _read_items(f: BytesIO, count: int) -> list[InventoryItem]:
    """Read count InventoryItem records with one read call."""
    data = read_exact(f, 12 * count)
    return [InventoryItem(h, q, a) for h, q, a in struct.iter_unpack("<3I", data)]


@dataclass
class Inventory:
    """
    Inventory structure (variable size based on capacities)

    Capacities differ between held and storage
    - Held: common_capacity=0xa80 (2688), key_capacity=0x180 (384)
    - Storage: common_capacity=0x780 (1920), key_capacity=0x80 (128)
    """

    common_item_count: int = 0
    common_items: list[InventoryItem] = field(default_factory=list)
    key_item_count: int = 0
    key_items: list[InventoryItem] = field(default_factory=list)
    equip_index_counter: int = 0
    acquisition_index_counter: int = 0

    @classmethod
    def read(cls, f: BytesIO, common_capacity: int, key_capacity: int) -> Inventory:
        """
        Read Inventory from stream with specified capacities.

        Args:
            f: BytesIO stream
            common_capacity: Max common items (0xa80 for held, 0x780 for storage)
            key_capacity: Max key items (0x180 for held, 0x80 for storage)

        Returns:
            Inventory instance
        """
        obj = cls()

        obj.common_item_count = struct.unpack("<I", f.read(4))[0]
        obj.common_items = _read_items(f, common_capacity)

        obj.key_item_count = struct.unpack("<I", f.read(4))[0]
        obj.key_items = _read_items(f, key_capacity)

        obj.equip_index_counter = struct.unpack("<I", f.read(4))[0]
        obj.acquisition_index_counter = struct.unpack("<I", f.read(4))[0]

        return obj

    def write(self, f: BytesIO):
        """Write Inventory to stream"""

        # One pack call per item array: same bytes as InventoryItem.write per
        # entry, but fast enough to re-serialize after every single add.
        def pack_items(items: list[InventoryItem]) -> bytes:
            fields = map(_INVENTORY_ITEM_FIELDS, items)
            return struct.pack(f"<{3 * len(items)}I", *chain.from_iterable(fields))

        f.write(struct.pack("<I", self.common_item_count))
        f.write(pack_items(self.common_items))

        f.write(struct.pack("<I", self.key_item_count))
        f.write(pack_items(self.key_items))

        f.write(struct.pack("<I", self.equip_index_counter))
        f.write(struct.pack("<I", self.acquisition_index_counter))


# ============================================================================
# SPELLS
# ============================================================================


@dataclass
class Spell:
    """Single spell slot (8 bytes)"""

    spell_id: int = 0
    unk0x4: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> Spell:
        """Read Spell from stream (8 bytes)"""
        return cls(
            spell_id=struct.unpack("<I", f.read(4))[0],
            unk0x4=struct.unpack("<I", f.read(4))[0],
        )

    def write(self, f: BytesIO):
        """Write Spell to stream (8 bytes)"""
        f.write(struct.pack("<I", self.spell_id))
        f.write(struct.pack("<I", self.unk0x4))


@dataclass
class EquippedSpells:
    """Equipped spells (0x74 = 116 bytes: 14 spells - 8 bytes + 4 bytes active index)"""

    spell_slots: list[Spell] = field(default_factory=list)
    active_index: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> EquippedSpells:
        """Read EquippedSpells from stream (116 bytes)"""
        obj = cls()
        obj.spell_slots = [Spell.read(f) for _ in range(14)]
        obj.active_index = struct.unpack("<I", f.read(4))[0]
        return obj

    def write(self, f: BytesIO):
        """Write EquippedSpells to stream (116 bytes)"""
        for spell in self.spell_slots:
            spell.write(f)
        f.write(struct.pack("<I", self.active_index))


# ============================================================================
# EQUIPPED ITEMS (QUICK ITEMS AND POUCH)
# ============================================================================


@dataclass
class EquippedItem:
    """Single equipped item (8 bytes)"""

    gaitem_handle: int = 0
    equip_index: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> EquippedItem:
        """Read EquippedItem from stream (8 bytes)"""
        return cls(
            gaitem_handle=struct.unpack("<I", f.read(4))[0],
            equip_index=struct.unpack("<I", f.read(4))[0],
        )

    def write(self, f: BytesIO):
        """Write EquippedItem to stream (8 bytes)"""
        f.write(struct.pack("<I", self.gaitem_handle))
        f.write(struct.pack("<I", self.equip_index))


@dataclass
class EquippedItems:
    """Equipped items (0x8C = 140 bytes: 10 quick + 6 pouch + equipped Great Rune)

    great_rune is the Great Rune goods handle (0xB0000000 | goods id, 0 when
    none); great_rune_equip_index is its key item list index.
    """

    quick_items: list[EquippedItem] = field(default_factory=list)
    active_quick_item_index: int = 0
    pouch_items: list[EquippedItem] = field(default_factory=list)
    great_rune: int = 0
    great_rune_equip_index: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> EquippedItems:
        """Read EquippedItems from stream (140 bytes)"""
        obj = cls()
        obj.quick_items = [EquippedItem.read(f) for _ in range(10)]
        obj.active_quick_item_index = struct.unpack("<I", f.read(4))[0]
        obj.pouch_items = [EquippedItem.read(f) for _ in range(6)]
        obj.great_rune = struct.unpack("<I", f.read(4))[0]
        obj.great_rune_equip_index = struct.unpack("<I", f.read(4))[0]
        return obj

    def write(self, f: BytesIO):
        """Write EquippedItems to stream (140 bytes)"""
        for item in self.quick_items:
            item.write(f)
        f.write(struct.pack("<I", self.active_quick_item_index))
        for item in self.pouch_items:
            item.write(f)
        f.write(struct.pack("<I", self.great_rune))
        f.write(struct.pack("<I", self.great_rune_equip_index))


# ============================================================================
# GESTURES, PROJECTILES, PHYSICS
# ============================================================================


@dataclass
class EquippedGestures:
    """Equipped gestures (0x18 = 24 bytes: 6 gestures - 4 bytes)"""

    gesture_ids: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, f: BytesIO) -> EquippedGestures:
        """Read EquippedGestures from stream (24 bytes)"""
        obj = cls()
        obj.gesture_ids = [struct.unpack("<I", f.read(4))[0] for _ in range(6)]
        return obj

    def write(self, f: BytesIO):
        """Write EquippedGestures to stream (24 bytes)"""
        for gesture_id in self.gesture_ids:
            f.write(struct.pack("<I", gesture_id))


@dataclass
class Projectile:
    """Auto-replenish setting of one item (8 bytes)

    id is a weapon (ammo) or 0x40000000 | goods id; auto_replenish is 1 when
    the chest's Auto-refill option is on for the item.
    """

    id: int = 0
    auto_replenish: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> Projectile:
        """Read Projectile from stream (8 bytes)"""
        return cls(
            id=struct.unpack("<I", f.read(4))[0],
            auto_replenish=struct.unpack("<I", f.read(4))[0],
        )

    def write(self, f: BytesIO):
        """Write Projectile to stream (8 bytes)"""
        f.write(struct.pack("<I", self.id))
        f.write(struct.pack("<I", self.auto_replenish))


@dataclass
class AcquiredProjectiles:
    """
    Auto-replenish settings (VARIABLE size based on count)
    Structure: 4 bytes count + (count x 8 bytes entries)

    One entry per ammo or goods item with EquipParamGoods autoReplenishType
    1 (default off) or 2 (default on) the character has obtained; the player
    can change each entry in game.
    """

    count: int = 0
    projectiles: list[Projectile] = field(default_factory=list)

    @classmethod
    def read(cls, f: BytesIO) -> AcquiredProjectiles:
        """Read AcquiredProjectiles from stream (variable size based on count)"""
        obj = cls()
        obj.count = struct.unpack("<I", f.read(4))[0]

        # Read exactly count projectiles (each is 8 bytes)
        data = read_exact(f, 8 * obj.count)
        obj.projectiles = [Projectile(i, r) for i, r in struct.iter_unpack("<2I", data)]

        return obj

    def write(self, f: BytesIO):
        """Write AcquiredProjectiles to stream"""
        f.write(struct.pack("<I", self.count))
        for proj in self.projectiles:
            proj.write(f)


@dataclass
class EquippedArmamentsAndItems:
    """Complete equipped state (0x9C = 156 bytes: 39 items - 4 bytes)"""

    left_hand_armament1: int = 0
    right_hand_armament1: int = 0
    left_hand_armament2: int = 0
    right_hand_armament2: int = 0
    left_hand_armament3: int = 0
    right_hand_armament3: int = 0
    arrows1: int = 0
    bolts1: int = 0
    arrows2: int = 0
    bolts2: int = 0
    arrows3: int = 0
    bolts3: int = 0
    head: int = 0
    chest: int = 0
    arms: int = 0
    legs: int = 0
    hair: int = 0
    talisman1: int = 0
    talisman2: int = 0
    talisman3: int = 0
    talisman4: int = 0
    talisman5: int = 0
    quickitem1: int = 0
    quickitem2: int = 0
    quickitem3: int = 0
    quickitem4: int = 0
    quickitem5: int = 0
    quickitem6: int = 0
    quickitem7: int = 0
    quickitem8: int = 0
    quickitem9: int = 0
    quickitem10: int = 0
    pouch1: int = 0
    pouch2: int = 0
    pouch3: int = 0
    pouch4: int = 0
    pouch5: int = 0
    pouch6: int = 0
    unk0x98: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> EquippedArmamentsAndItems:
        """Read EquippedArmamentsAndItems from stream (156 bytes)"""
        return cls(
            left_hand_armament1=struct.unpack("<I", f.read(4))[0],
            right_hand_armament1=struct.unpack("<I", f.read(4))[0],
            left_hand_armament2=struct.unpack("<I", f.read(4))[0],
            right_hand_armament2=struct.unpack("<I", f.read(4))[0],
            left_hand_armament3=struct.unpack("<I", f.read(4))[0],
            right_hand_armament3=struct.unpack("<I", f.read(4))[0],
            arrows1=struct.unpack("<I", f.read(4))[0],
            bolts1=struct.unpack("<I", f.read(4))[0],
            arrows2=struct.unpack("<I", f.read(4))[0],
            bolts2=struct.unpack("<I", f.read(4))[0],
            arrows3=struct.unpack("<I", f.read(4))[0],
            bolts3=struct.unpack("<I", f.read(4))[0],
            head=struct.unpack("<I", f.read(4))[0],
            chest=struct.unpack("<I", f.read(4))[0],
            arms=struct.unpack("<I", f.read(4))[0],
            legs=struct.unpack("<I", f.read(4))[0],
            hair=struct.unpack("<I", f.read(4))[0],
            talisman1=struct.unpack("<I", f.read(4))[0],
            talisman2=struct.unpack("<I", f.read(4))[0],
            talisman3=struct.unpack("<I", f.read(4))[0],
            talisman4=struct.unpack("<I", f.read(4))[0],
            talisman5=struct.unpack("<I", f.read(4))[0],
            quickitem1=struct.unpack("<I", f.read(4))[0],
            quickitem2=struct.unpack("<I", f.read(4))[0],
            quickitem3=struct.unpack("<I", f.read(4))[0],
            quickitem4=struct.unpack("<I", f.read(4))[0],
            quickitem5=struct.unpack("<I", f.read(4))[0],
            quickitem6=struct.unpack("<I", f.read(4))[0],
            quickitem7=struct.unpack("<I", f.read(4))[0],
            quickitem8=struct.unpack("<I", f.read(4))[0],
            quickitem9=struct.unpack("<I", f.read(4))[0],
            quickitem10=struct.unpack("<I", f.read(4))[0],
            pouch1=struct.unpack("<I", f.read(4))[0],
            pouch2=struct.unpack("<I", f.read(4))[0],
            pouch3=struct.unpack("<I", f.read(4))[0],
            pouch4=struct.unpack("<I", f.read(4))[0],
            pouch5=struct.unpack("<I", f.read(4))[0],
            pouch6=struct.unpack("<I", f.read(4))[0],
            unk0x98=struct.unpack("<I", f.read(4))[0],
        )

    def write(self, f: BytesIO):
        """Write EquippedArmamentsAndItems to stream (156 bytes)"""
        f.write(struct.pack("<I", self.left_hand_armament1))
        f.write(struct.pack("<I", self.right_hand_armament1))
        f.write(struct.pack("<I", self.left_hand_armament2))
        f.write(struct.pack("<I", self.right_hand_armament2))
        f.write(struct.pack("<I", self.left_hand_armament3))
        f.write(struct.pack("<I", self.right_hand_armament3))
        f.write(struct.pack("<I", self.arrows1))
        f.write(struct.pack("<I", self.bolts1))
        f.write(struct.pack("<I", self.arrows2))
        f.write(struct.pack("<I", self.bolts2))
        f.write(struct.pack("<I", self.arrows3))
        f.write(struct.pack("<I", self.bolts3))
        f.write(struct.pack("<I", self.head))
        f.write(struct.pack("<I", self.chest))
        f.write(struct.pack("<I", self.arms))
        f.write(struct.pack("<I", self.legs))
        f.write(struct.pack("<I", self.hair))
        f.write(struct.pack("<I", self.talisman1))
        f.write(struct.pack("<I", self.talisman2))
        f.write(struct.pack("<I", self.talisman3))
        f.write(struct.pack("<I", self.talisman4))
        f.write(struct.pack("<I", self.talisman5))
        f.write(struct.pack("<I", self.quickitem1))
        f.write(struct.pack("<I", self.quickitem2))
        f.write(struct.pack("<I", self.quickitem3))
        f.write(struct.pack("<I", self.quickitem4))
        f.write(struct.pack("<I", self.quickitem5))
        f.write(struct.pack("<I", self.quickitem6))
        f.write(struct.pack("<I", self.quickitem7))
        f.write(struct.pack("<I", self.quickitem8))
        f.write(struct.pack("<I", self.quickitem9))
        f.write(struct.pack("<I", self.quickitem10))
        f.write(struct.pack("<I", self.pouch1))
        f.write(struct.pack("<I", self.pouch2))
        f.write(struct.pack("<I", self.pouch3))
        f.write(struct.pack("<I", self.pouch4))
        f.write(struct.pack("<I", self.pouch5))
        f.write(struct.pack("<I", self.pouch6))
        f.write(struct.pack("<I", self.unk0x98))


@dataclass
class EquippedPhysics:
    """Wondrous Physick tears (0xC = 12 bytes)"""

    slot1: int = 0
    slot2: int = 0
    unk0x8: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> EquippedPhysics:
        """Read EquippedPhysics from stream (12 bytes)"""
        return cls(
            slot1=struct.unpack("<I", f.read(4))[0],
            slot2=struct.unpack("<I", f.read(4))[0],
            unk0x8=struct.unpack("<I", f.read(4))[0],
        )

    def write(self, f: BytesIO):
        """Write EquippedPhysics to stream (12 bytes)"""
        f.write(struct.pack("<I", self.slot1))
        f.write(struct.pack("<I", self.slot2))
        f.write(struct.pack("<I", self.unk0x8))


# ============================================================================
# TROPHY EQUIP DATA
# ============================================================================


@dataclass
class TrophyEquipData:
    """Legendary item trophy progress (0x34 = 52 bytes)

    Three 128-bit sets, one bit per legendary item ever acquired (kept after
    the item is sold or discarded). Bit n is the n-th legendary item of that
    type in ascending item id order:
    - legendary_weapons: the 9 Legendary Armaments
    - legendary_goods: the 7 legendary sorceries/incantations (bits 0-6),
      then the 6 Legendary Ashen Remains (bits 7-12)
    - legendary_talismans: the 8 Legendary Talismans
    unk0x0 is always 0.
    """

    unk0x0: int = 0
    legendary_weapons: bytes = field(default_factory=lambda: b"\x00" * 0x10)
    legendary_goods: bytes = field(default_factory=lambda: b"\x00" * 0x10)
    legendary_talismans: bytes = field(default_factory=lambda: b"\x00" * 0x10)

    @classmethod
    def read(cls, f: BytesIO) -> TrophyEquipData:
        """Read TrophyEquipData from stream (52 bytes)"""
        return cls(
            unk0x0=struct.unpack("<I", f.read(4))[0],
            legendary_weapons=f.read(0x10),
            legendary_goods=f.read(0x10),
            legendary_talismans=f.read(0x10),
        )

    def write(self, f: BytesIO):
        """Write TrophyEquipData to stream (52 bytes)"""
        f.write(struct.pack("<I", self.unk0x0))
        f.write(self.legendary_weapons)
        f.write(self.legendary_goods)
        f.write(self.legendary_talismans)
