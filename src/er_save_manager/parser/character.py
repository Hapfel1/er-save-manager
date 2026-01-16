"""
Elden Ring Save Parser - Character Data Structures

Contains PlayerGameData and SPEffect structures.
Based on ER-Save-Lib Rust implementation.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from io import BytesIO

from .er_types import Util

# ============================================================================
# PLAYER GAME DATA - Complete character stats and attributes
# ============================================================================


@dataclass
class PlayerGameData:
    """
    Complete player/character data structure (0x1B0 = 432 bytes)

    Contains all character stats, attributes, online settings, and metadata.
    This is one of the most important structures in the save file.
    """

    # Health, FP, Stamina (0x00-0x33)
    unk0x0: int = 0
    unk0x4: int = 0
    hp: int = 0
    max_hp: int = 0
    base_max_hp: int = 0
    fp: int = 0
    max_fp: int = 0
    base_max_fp: int = 0
    unk0x20: int = 0
    sp: int = 0
    max_sp: int = 0
    base_max_sp: int = 0
    unk0x30: int = 0

    # Attributes (0x34-0x53)
    vigor: int = 0
    mind: int = 0
    endurance: int = 0
    strength: int = 0
    dexterity: int = 0
    intelligence: int = 0
    faith: int = 0
    arcane: int = 0
    unk0x54: int = 0
    unk0x58: int = 0
    unk0x5c: int = 0

    # Level and Runes (0x60-0x6B)
    level: int = 0
    runes: int = 0
    runes_memory: int = 0
    unk0x6c: int = 0

    # Status buildups (0x70-0x8B)
    poison_buildup: int = 0
    rot_buildup: int = 0
    bleed_buildup: int = 0
    death_buildup: int = 0
    frost_buildup: int = 0
    sleep_buildup: int = 0
    madness_buildup: int = 0
    unk0x8c: int = 0
    unk0x90: int = 0

    # Character name (0x94-0xB3) - UTF-16LE, 16 chars max
    character_name: str = ""
    terminator: int = 0

    # Character creation (0xB4-0xBF)
    gender: int = 0
    archetype: int = 0
    unk0xb8: int = 0
    unk0xb9: int = 0
    voice_type: int = 0
    gift: int = 0
    unk0xbc: int = 0
    unk0xbd: int = 0
    additional_talisman_slot_count: int = 0
    summon_spirit_level: int = 0
    unk0xc0: bytes = field(default_factory=lambda: b"\x00" * 0x18)

    # Online settings (0xD8-0xF7)
    furl_calling_finger_on: bool = False
    unk0xd9: int = 0
    matchmaking_weapon_level: int = 0
    white_cipher_ring_on: bool = False
    blue_cipher_ring_on: bool = False
    unk0xdd: bytes = field(default_factory=lambda: b"\x00" * 0x1A)
    great_rune_on: bool = False
    unk0xf8: int = 0

    # Flask counts (0xF9-0xFA)
    max_crimson_flask_count: int = 0
    max_cerulean_flask_count: int = 0
    unk0xfb: bytes = field(default_factory=lambda: b"\x00" * 0x15)

    # Passwords (0x110-0x17B) - UTF-16LE, 8 chars max each
    password: str = ""
    password_terminator: int = 0
    group_password1: str = ""
    group_password1_terminator: int = 0
    group_password2: str = ""
    group_password2_terminator: int = 0
    group_password3: str = ""
    group_password3_terminator: int = 0
    group_password4: str = ""
    group_password4_terminator: int = 0
    group_password5: str = ""
    group_password5_terminator: int = 0

    # Padding (0x17C-0x1AF)
    unk0x17c: bytes = field(default_factory=lambda: b"\x00" * 0x34)

    @classmethod
    def read(cls, f: BytesIO) -> PlayerGameData:
        """
        Read PlayerGameData from stream (432 bytes total).
        Returns:
            PlayerGameData instance with all fields populated
        """
        obj = cls()

        # Health, FP, Stamina
        obj.unk0x0 = struct.unpack("<I", f.read(4))[0]
        obj.unk0x4 = struct.unpack("<I", f.read(4))[0]
        obj.hp = struct.unpack("<I", f.read(4))[0]
        obj.max_hp = struct.unpack("<I", f.read(4))[0]
        obj.base_max_hp = struct.unpack("<I", f.read(4))[0]
        obj.fp = struct.unpack("<I", f.read(4))[0]
        obj.max_fp = struct.unpack("<I", f.read(4))[0]
        obj.base_max_fp = struct.unpack("<I", f.read(4))[0]
        obj.unk0x20 = struct.unpack("<I", f.read(4))[0]
        obj.sp = struct.unpack("<I", f.read(4))[0]
        obj.max_sp = struct.unpack("<I", f.read(4))[0]
        obj.base_max_sp = struct.unpack("<I", f.read(4))[0]
        obj.unk0x30 = struct.unpack("<I", f.read(4))[0]

        # Attributes
        obj.vigor = struct.unpack("<I", f.read(4))[0]
        obj.mind = struct.unpack("<I", f.read(4))[0]
        obj.endurance = struct.unpack("<I", f.read(4))[0]
        obj.strength = struct.unpack("<I", f.read(4))[0]
        obj.dexterity = struct.unpack("<I", f.read(4))[0]
        obj.intelligence = struct.unpack("<I", f.read(4))[0]
        obj.faith = struct.unpack("<I", f.read(4))[0]
        obj.arcane = struct.unpack("<I", f.read(4))[0]
        obj.unk0x54 = struct.unpack("<I", f.read(4))[0]
        obj.unk0x58 = struct.unpack("<I", f.read(4))[0]
        obj.unk0x5c = struct.unpack("<I", f.read(4))[0]

        # Level and Runes
        obj.level = struct.unpack("<I", f.read(4))[0]
        obj.runes = struct.unpack("<I", f.read(4))[0]
        obj.runes_memory = struct.unpack("<I", f.read(4))[0]
        obj.unk0x6c = struct.unpack("<I", f.read(4))[0]

        # Status buildups
        obj.poison_buildup = struct.unpack("<I", f.read(4))[0]
        obj.rot_buildup = struct.unpack("<I", f.read(4))[0]
        obj.bleed_buildup = struct.unpack("<I", f.read(4))[0]
        obj.death_buildup = struct.unpack("<I", f.read(4))[0]
        obj.frost_buildup = struct.unpack("<I", f.read(4))[0]
        obj.sleep_buildup = struct.unpack("<I", f.read(4))[0]
        obj.madness_buildup = struct.unpack("<I", f.read(4))[0]
        obj.unk0x8c = struct.unpack("<I", f.read(4))[0]
        obj.unk0x90 = struct.unpack("<I", f.read(4))[0]

        # Character name (UTF-16LE, 16 chars)
        obj.character_name = Util.read_wstring(f, 16)
        obj.terminator = struct.unpack("<H", f.read(2))[0]

        # Character creation
        obj.gender = struct.unpack("<B", f.read(1))[0]
        obj.archetype = struct.unpack("<B", f.read(1))[0]
        obj.unk0xb8 = struct.unpack("<B", f.read(1))[0]
        obj.unk0xb9 = struct.unpack("<B", f.read(1))[0]
        obj.voice_type = struct.unpack("<B", f.read(1))[0]
        obj.gift = struct.unpack("<B", f.read(1))[0]
        obj.unk0xbc = struct.unpack("<B", f.read(1))[0]
        obj.unk0xbd = struct.unpack("<B", f.read(1))[0]
        obj.additional_talisman_slot_count = struct.unpack("<B", f.read(1))[0]
        obj.summon_spirit_level = struct.unpack("<B", f.read(1))[0]
        obj.unk0xc0 = f.read(0x18)

        # Online settings
        obj.furl_calling_finger_on = struct.unpack("<?", f.read(1))[0]
        obj.unk0xd9 = struct.unpack("<B", f.read(1))[0]
        obj.matchmaking_weapon_level = struct.unpack("<B", f.read(1))[0]
        obj.white_cipher_ring_on = struct.unpack("<?", f.read(1))[0]
        obj.blue_cipher_ring_on = struct.unpack("<?", f.read(1))[0]
        obj.unk0xdd = f.read(0x1A)
        obj.great_rune_on = struct.unpack("<?", f.read(1))[0]
        obj.unk0xf8 = struct.unpack("<B", f.read(1))[0]

        # Flask counts
        obj.max_crimson_flask_count = struct.unpack("<B", f.read(1))[0]
        obj.max_cerulean_flask_count = struct.unpack("<B", f.read(1))[0]
        obj.unk0xfb = f.read(0x15)

        # Passwords (UTF-16LE, 8 chars each)
        obj.password = Util.read_wstring(f, 8)
        obj.password_terminator = struct.unpack("<H", f.read(2))[0]
        obj.group_password1 = Util.read_wstring(f, 8)
        obj.group_password1_terminator = struct.unpack("<H", f.read(2))[0]
        obj.group_password2 = Util.read_wstring(f, 8)
        obj.group_password2_terminator = struct.unpack("<H", f.read(2))[0]
        obj.group_password3 = Util.read_wstring(f, 8)
        obj.group_password3_terminator = struct.unpack("<H", f.read(2))[0]
        obj.group_password4 = Util.read_wstring(f, 8)
        obj.group_password4_terminator = struct.unpack("<H", f.read(2))[0]
        obj.group_password5 = Util.read_wstring(f, 8)
        obj.group_password5_terminator = struct.unpack("<H", f.read(2))[0]

        # Padding
        obj.unk0x17c = f.read(0x34)

        return obj

    def write(self, f: BytesIO):
        """Write PlayerGameData to stream (432 bytes total)"""
        # Health, FP, Stamina
        f.write(struct.pack("<I", self.unk0x0))
        f.write(struct.pack("<I", self.unk0x4))
        f.write(struct.pack("<I", self.hp))
        f.write(struct.pack("<I", self.max_hp))
        f.write(struct.pack("<I", self.base_max_hp))
        f.write(struct.pack("<I", self.fp))
        f.write(struct.pack("<I", self.max_fp))
        f.write(struct.pack("<I", self.base_max_fp))
        f.write(struct.pack("<I", self.unk0x20))
        f.write(struct.pack("<I", self.sp))
        f.write(struct.pack("<I", self.max_sp))
        f.write(struct.pack("<I", self.base_max_sp))
        f.write(struct.pack("<I", self.unk0x30))

        # Attributes
        f.write(struct.pack("<I", self.vigor))
        f.write(struct.pack("<I", self.mind))
        f.write(struct.pack("<I", self.endurance))
        f.write(struct.pack("<I", self.strength))
        f.write(struct.pack("<I", self.dexterity))
        f.write(struct.pack("<I", self.intelligence))
        f.write(struct.pack("<I", self.faith))
        f.write(struct.pack("<I", self.arcane))
        f.write(struct.pack("<I", self.unk0x54))
        f.write(struct.pack("<I", self.unk0x58))
        f.write(struct.pack("<I", self.unk0x5c))

        # Level and Runes
        f.write(struct.pack("<I", self.level))
        f.write(struct.pack("<I", self.runes))
        f.write(struct.pack("<I", self.runes_memory))
        f.write(struct.pack("<I", self.unk0x6c))

        # Status buildups
        f.write(struct.pack("<I", self.poison_buildup))
        f.write(struct.pack("<I", self.rot_buildup))
        f.write(struct.pack("<I", self.bleed_buildup))
        f.write(struct.pack("<I", self.death_buildup))
        f.write(struct.pack("<I", self.frost_buildup))
        f.write(struct.pack("<I", self.sleep_buildup))
        f.write(struct.pack("<I", self.madness_buildup))
        f.write(struct.pack("<I", self.unk0x8c))
        f.write(struct.pack("<I", self.unk0x90))

        # Character name
        Util.write_wstring(f, self.character_name, 16)
        f.write(struct.pack("<H", self.terminator))

        # Character creation
        f.write(struct.pack("<B", self.gender))
        f.write(struct.pack("<B", self.archetype))
        f.write(struct.pack("<B", self.unk0xb8))
        f.write(struct.pack("<B", self.unk0xb9))
        f.write(struct.pack("<B", self.voice_type))
        f.write(struct.pack("<B", self.gift))
        f.write(struct.pack("<B", self.unk0xbc))
        f.write(struct.pack("<B", self.unk0xbd))
        f.write(struct.pack("<B", self.additional_talisman_slot_count))
        f.write(struct.pack("<B", self.summon_spirit_level))
        f.write(self.unk0xc0)

        # Online settings
        f.write(struct.pack("<?", self.furl_calling_finger_on))
        f.write(struct.pack("<B", self.unk0xd9))
        f.write(struct.pack("<B", self.matchmaking_weapon_level))
        f.write(struct.pack("<?", self.white_cipher_ring_on))
        f.write(struct.pack("<?", self.blue_cipher_ring_on))
        f.write(self.unk0xdd)
        f.write(struct.pack("<?", self.great_rune_on))
        f.write(struct.pack("<B", self.unk0xf8))

        # Flask counts
        f.write(struct.pack("<B", self.max_crimson_flask_count))
        f.write(struct.pack("<B", self.max_cerulean_flask_count))
        f.write(self.unk0xfb)

        # Passwords
        Util.write_wstring(f, self.password, 8)
        f.write(struct.pack("<H", self.password_terminator))
        Util.write_wstring(f, self.group_password1, 8)
        f.write(struct.pack("<H", self.group_password1_terminator))
        Util.write_wstring(f, self.group_password2, 8)
        f.write(struct.pack("<H", self.group_password2_terminator))
        Util.write_wstring(f, self.group_password3, 8)
        f.write(struct.pack("<H", self.group_password3_terminator))
        Util.write_wstring(f, self.group_password4, 8)
        f.write(struct.pack("<H", self.group_password4_terminator))
        Util.write_wstring(f, self.group_password5, 8)
        f.write(struct.pack("<H", self.group_password5_terminator))

        # Padding
        f.write(self.unk0x17c)


# ============================================================================
# SP EFFECT - Status effects
# ============================================================================


@dataclass
class SPEffect:
    """
    Status effect/buff/debuff (16 bytes per entry, 13 entries total)

    Examples: weapon buffs, spell effects, consumable effects, etc.
    """

    sp_effect_id: int = 0
    remaining_time: float = 0.0
    unk0x8: int = 0
    unk0x10: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> SPEffect:
        """Read SPEffect from stream (16 bytes)"""
        return cls(
            sp_effect_id=struct.unpack("<i", f.read(4))[0],
            remaining_time=struct.unpack("<f", f.read(4))[0],
            unk0x8=struct.unpack("<I", f.read(4))[0],
            unk0x10=struct.unpack("<I", f.read(4))[0],
        )

    def write(self, f: BytesIO):
        """Write SPEffect to stream (16 bytes)"""
        f.write(struct.pack("<i", self.sp_effect_id))
        f.write(struct.pack("<f", self.remaining_time))
        f.write(struct.pack("<I", self.unk0x8))
        f.write(struct.pack("<I", self.unk0x10))

    def is_active(self) -> bool:
        """Check if this effect is currently active"""
        return self.sp_effect_id != 0 and self.remaining_time > 0
