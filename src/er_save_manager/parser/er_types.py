"""
Elden Ring Save Parser - Basic Types

Contains fundamental data types used throughout the save file.
Based on ER-Save-Lib Rust implementation.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from io import BytesIO

# ============================================================================
# ENUMS
# ============================================================================


class HorseState(IntEnum):
    """Torrent/Horse state values"""

    INACTIVE = 1
    DEAD = 3
    ACTIVE = 13

    @classmethod
    def _missing_(cls, value):
        """Handle unknown state values"""
        pseudo_member = int.__new__(cls, value)
        pseudo_member._name_ = f"UNKNOWN_{value}"
        pseudo_member._value_ = value
        return pseudo_member


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


class Util:
    """Utility functions for reading/writing special types"""

    @staticmethod
    def read_wstring(f: BytesIO, max_chars: int) -> str:
        """
        Read UTF-16LE null-terminated string with max character count.

        Args:
            f: BytesIO stream to read from
            max_chars: Maximum number of characters (not bytes)

        Returns:
            Decoded string with trailing nulls stripped
        """
        bytes_to_read = max_chars * 2
        data = f.read(bytes_to_read)
        try:
            # Decode the full data
            decoded = data.decode("utf-16le", errors="ignore")
            # Strip trailing null characters
            return decoded.rstrip("\x00")
        except Exception:
            return ""

    @staticmethod
    def write_wstring(f: BytesIO, s: str, max_chars: int):
        """
        Write UTF-16LE string with padding to max_chars.

        Args:
            f: BytesIO stream to write to
            s: String to write
            max_chars: Maximum number of characters (not bytes)
        """
        encoded = s.encode("utf-16le")
        bytes_to_write = max_chars * 2
        if len(encoded) > bytes_to_write:
            encoded = encoded[:bytes_to_write]
        f.write(encoded)
        remaining = bytes_to_write - len(encoded)
        if remaining > 0:
            f.write(b"\x00" * remaining)


# ============================================================================
# BASIC DATA TYPES
# ============================================================================


@dataclass
class FloatVector3:
    """3D float vector (12 bytes)"""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def read(cls, f: BytesIO) -> FloatVector3:
        """Read FloatVector3 from stream"""
        x, y, z = struct.unpack("<fff", f.read(12))
        return cls(x, y, z)

    def write(self, f: BytesIO):
        """Write FloatVector3 to stream"""
        f.write(struct.pack("<fff", self.x, self.y, self.z))

    def __str__(self):
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"


@dataclass
class FloatVector4:
    """4D float vector (16 bytes) - typically used for quaternions/angles"""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 0.0

    @classmethod
    def read(cls, f: BytesIO) -> FloatVector4:
        """Read FloatVector4 from stream"""
        x, y, z, w = struct.unpack("<ffff", f.read(16))
        return cls(x, y, z, w)

    def write(self, f: BytesIO):
        """Write FloatVector4 to stream"""
        f.write(struct.pack("<ffff", self.x, self.y, self.z, self.w))

    def __str__(self):
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f}, {self.w:.2f})"


@dataclass
class MapId:
    """
    Map ID (4 bytes)
    Represents the current map/area in the game.
    """

    data: bytes = field(default_factory=lambda: b"\x00\x00\x00\x00")

    @classmethod
    def read(cls, f: BytesIO) -> MapId:
        """Read MapId from stream"""
        return cls(f.read(4))

    def write(self, f: BytesIO):
        """Write MapId to stream"""
        f.write(self.data)

    def to_decimal(self) -> str:
        """
        Convert to decimal map coordinates.
        Format: "AA BB CC DD"
        """
        return f"{self.data[3]:d} {self.data[2]:d} {self.data[1]:d} {self.data[0]:d}"

    def to_string_decimal(self) -> str:
        """Alias for to_decimal() for backward compatibility"""
        return self.to_decimal()

    def to_hex_string(self) -> str:
        """
        Convert to hex string format.
        Format: "AA_BB_CC_DD"
        """
        return f"{self.data[0]:02X}_{self.data[1]:02X}_{self.data[2]:02X}_{self.data[3]:02X}"

    def __str__(self):
        return self.to_decimal()

    def is_dlc(self) -> bool:
        """
        Check if this map ID is in the Shadow of the Erdtree DLC area.

        DLC includes:
        - m20-m29: DLC legacy dungeons (Belurat, Enir-Ilim, Shadow Keep, etc.)
        - m61: DLC overworld (Land of Shadow)

        Base game:
        - m10-m19: Base game legacy dungeons (Stormveil, Leyndell, etc.)
        - m30-m59: Base game mini-dungeons (catacombs, caves, etc.)
        - m60: Base game overworld (Limgrave, Liurnia, Caelid, etc.)

        MapId format: data = [data[0], data[1], data[2], data[3]]
        Display format: "data[3] data[2] data[1] data[0]"
        Map name: m{data[3]}_{data[2]}_{data[1]}_{data[0]:02d}

        Examples:
        - "60 42 36 0" → data=[0,36,42,60] → m60_42_36_00 → Limgrave (NOT DLC)
        - "61 42 36 0" → data=[0,36,42,61] → m61_42_36_00 → DLC overworld
        - "20 0 0 0"   → data=[0,0,0,20]   → m20_0_0_0    → DLC Belurat
        - "21 0 0 0"   → data=[0,0,0,21]   → m21_0_0_0    → DLC Shadow Keep
        - "11 10 0 0"  → data=[0,0,10,11]  → m11_10_0_0   → Roundtable (NOT DLC)

        Returns:
            True if this is a DLC Shadow of the Erdtree location
        """
        # Check the map prefix (data[3])
        map_prefix = self.data[3]

        # DLC includes:
        # - m20-m29: DLC legacy dungeons
        # - m61: DLC overworld
        return (20 <= map_prefix <= 29) or (map_prefix == 61)

    def to_bytes(self) -> bytes:
        """
        Convert MapId to bytes for writing to save file.

        Returns:
            4 bytes representing the map ID
        """
        return self.data


# ============================================================================
# GAITEM - Variable Length Structure (CRITICAL!)
# ============================================================================


@dataclass
class Gaitem:
    """
    Variable-length item structure (8-17 bytes)

    Size depends on gaitem_handle type flags:

    - Base size: 8 bytes (gaitem_handle + item_id)
    - If handle != 0 AND (handle & 0xF0000000) != 0xC0000000: +8 bytes
    - If (handle & 0xF0000000) == 0x80000000: +5 additional bytes

    Total possible sizes: 8, 16, or 21 bytes

    The save file contains 5118 (version <= 81) or 5120 (version > 81) of these.
    If not parsed correctly, allsubsequent data will be misaligned
    """

    gaitem_handle: int = 0
    item_id: int = 0
    unk0x10: int | None = None
    unk0x14: int | None = None
    gem_gaitem_handle: int | None = None
    unk0x1c: int | None = None

    @classmethod
    def read(cls, f: BytesIO) -> Gaitem:
        """
        Read Gaitem from stream with conditional field parsing.

        Returns:
            Gaitem instance with appropriate fields populated
        """
        # Always read base 8 bytes
        gaitem_handle = struct.unpack("<I", f.read(4))[0]
        item_id = struct.unpack("<I", f.read(4))[0]

        obj = cls(gaitem_handle=gaitem_handle, item_id=item_id)

        # Conditional reading based on handle type
        handle_type = gaitem_handle & 0xF0000000

        if gaitem_handle != 0 and handle_type != 0xC0000000:
            # Read additional 8 bytes
            obj.unk0x10 = struct.unpack("<i", f.read(4))[0]
            obj.unk0x14 = struct.unpack("<i", f.read(4))[0]

            if handle_type == 0x80000000:
                # Read additional 5 bytes (for gem items)
                obj.gem_gaitem_handle = struct.unpack("<i", f.read(4))[0]
                obj.unk0x1c = struct.unpack("<B", f.read(1))[0]

        return obj

    def write(self, f: BytesIO):
        """Write Gaitem to stream with conditional field writing"""
        # Always write base 8 bytes
        f.write(struct.pack("<I", self.gaitem_handle))
        f.write(struct.pack("<I", self.item_id))

        # Conditional writing based on handle type
        handle_type = self.gaitem_handle & 0xF0000000

        if self.gaitem_handle != 0 and handle_type != 0xC0000000:
            f.write(struct.pack("<i", self.unk0x10 or 0))
            f.write(struct.pack("<i", self.unk0x14 or 0))

            if handle_type == 0x80000000:
                f.write(struct.pack("<i", self.gem_gaitem_handle or 0))
                f.write(struct.pack("<B", self.unk0x1c or 0))

    def get_size(self) -> int:
        """
        Calculate the actual size of this Gaitem in bytes.

        Returns:
            Size in bytes (8, 16, or 21)
        """
        size = 8  # Base size
        handle_type = self.gaitem_handle & 0xF0000000

        if self.gaitem_handle != 0 and handle_type != 0xC0000000:
            size += 8
            if handle_type == 0x80000000:
                size += 5

        return size

    def __str__(self):
        return f"Gaitem(handle=0x{self.gaitem_handle:08X}, item_id={self.item_id}, size={self.get_size()})"
