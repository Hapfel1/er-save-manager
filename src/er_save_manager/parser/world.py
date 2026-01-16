"""
Elden Ring Save Parser - World State and Game Data Structures

Contains world state, game progression, and miscellaneous game data structures.
Based on ER-Save-Lib Rust implementation.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from io import BytesIO

from .er_types import FloatVector3, FloatVector4, HorseState, MapId

# ============================================================================
# FACE DATA - Character appearance customization
# ============================================================================


@dataclass
class FaceData:
    """
    Character appearance and body customization (0x12F = 303 bytes when in_profile_summary=False)

    Contains 100+ fields for facial features, body proportions, colors, etc.
    Stored as raw bytes for simplicity - can be expanded to individual fields if needed.
    """

    raw_data: bytes = field(default_factory=lambda: b"\x00" * 0x12F)

    @classmethod
    def read(cls, f: BytesIO, in_profile_summary: bool = False) -> FaceData:
        """
        Read FaceData from stream.

        Args:
            f: BytesIO stream
            in_profile_summary: If True, reads 0x120 bytes; if False, reads 0x12F bytes

        Returns:
            FaceData instance
        """
        size = 0x120 if in_profile_summary else 0x12F
        return cls(raw_data=f.read(size))

    def write(self, f: BytesIO):
        """Write FaceData to stream"""
        f.write(self.raw_data)


# ============================================================================
# GESTURES AND REGIONS
# ============================================================================


@dataclass
class Gestures:
    """All gesture IDs (variable size based on version)"""

    gesture_ids: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, f: BytesIO) -> Gestures:
        """Read Gestures from stream (256 bytes = 64 u32s)"""
        start_pos = f.tell()
        result = cls.read_with_count(f, 64)
        end_pos = f.tell()
        bytes_read = end_pos - start_pos
        if bytes_read != 256:
            pass
        return result

    @classmethod
    def read_with_count(cls, f: BytesIO, count: int) -> Gestures:
        """Read Gestures with specified count"""
        obj = cls()
        obj.gesture_ids = [struct.unpack("<I", f.read(4))[0] for _ in range(count)]
        return obj

    def write(self, f: BytesIO):
        """Write Gestures to stream"""
        for gesture_id in self.gesture_ids:
            f.write(struct.pack("<I", gesture_id))


@dataclass
class Regions:
    """
    Unlocked regions (variable size based on count)

    After count, reads exactly that many region IDs.
    """

    count: int = 0
    region_ids: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, f: BytesIO) -> Regions:
        """Read Regions from stream (variable size based on count)"""
        obj = cls()
        obj.count = struct.unpack("<I", f.read(4))[0]
        obj.region_ids = [struct.unpack("<I", f.read(4))[0] for _ in range(obj.count)]
        return obj

        return obj

    def write(self, f: BytesIO):
        """Write Regions to stream"""
        f.write(struct.pack("<I", self.count))
        for region_id in self.region_ids:
            f.write(struct.pack("<I", region_id))


# ============================================================================
# TORRENT / HORSE DATA
# ============================================================================


@dataclass
class RideGameData:
    """
    Torrent/Horse data (0x28 = 40 bytes)

    Contains position, HP, and state.
    """

    coordinates: FloatVector3 = field(default_factory=FloatVector3)
    map_id: MapId = field(default_factory=MapId)
    angle: FloatVector4 = field(default_factory=FloatVector4)
    hp: int = 0
    state: HorseState = HorseState.INACTIVE

    @classmethod
    def read(cls, f: BytesIO) -> RideGameData:
        """Read RideGameData from stream (40 bytes)"""
        return cls(
            coordinates=FloatVector3.read(f),
            map_id=MapId.read(f),
            angle=FloatVector4.read(f),
            hp=struct.unpack("<i", f.read(4))[0],
            state=HorseState(struct.unpack("<I", f.read(4))[0]),
        )

    def write(self, f: BytesIO):
        """Write RideGameData to stream (40 bytes)"""
        self.coordinates.write(f)
        self.map_id.write(f)
        self.angle.write(f)
        f.write(struct.pack("<i", self.hp))
        f.write(struct.pack("<I", int(self.state)))

    def has_bug(self) -> bool:
        """
        Check if Torrent has the infinite loading bug.

        Bug condition: HP is 0 AND state is ACTIVE (13)
        Should be: HP is 0 AND state is DEAD (3)

        Returns:
            True if bug is present
        """
        return self.hp == 0 and self.state == HorseState.ACTIVE

    def fix_bug(self):
        """Fix the Torrent infinite loading bug by setting state to DEAD"""
        if self.has_bug():
            self.state = HorseState.DEAD


# ============================================================================
# BLOOD STAIN
# ============================================================================


@dataclass
class BloodStain:
    """Death bloodstain data (0x44 = 68 bytes)"""

    coordinates: FloatVector3 = field(default_factory=FloatVector3)
    angle: FloatVector4 = field(default_factory=FloatVector4)
    unk0x1c: int = 0
    unk0x20: int = 0
    unk0x24: int = 0
    unk0x28: int = 0
    unk0x2c: int = 0
    unk0x30: int = 0
    runes: int = 0
    map_id: MapId = field(default_factory=MapId)
    unk0x3c: int = 0
    unk0x38: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> BloodStain:
        """Read BloodStain from stream (68 bytes)"""
        return cls(
            coordinates=FloatVector3.read(f),
            angle=FloatVector4.read(f),
            unk0x1c=struct.unpack("<I", f.read(4))[0],
            unk0x20=struct.unpack("<I", f.read(4))[0],
            unk0x24=struct.unpack("<I", f.read(4))[0],
            unk0x28=struct.unpack("<I", f.read(4))[0],
            unk0x2c=struct.unpack("<I", f.read(4))[0],
            unk0x30=struct.unpack("<i", f.read(4))[0],
            runes=struct.unpack("<i", f.read(4))[0],
            map_id=MapId.read(f),
            unk0x3c=struct.unpack("<I", f.read(4))[0],
            unk0x38=struct.unpack("<I", f.read(4))[0],
        )

    def write(self, f: BytesIO):
        """Write BloodStain to stream (68 bytes)"""
        self.coordinates.write(f)
        self.angle.write(f)
        f.write(struct.pack("<I", self.unk0x1c))
        f.write(struct.pack("<I", self.unk0x20))
        f.write(struct.pack("<I", self.unk0x24))
        f.write(struct.pack("<I", self.unk0x28))
        f.write(struct.pack("<I", self.unk0x2c))
        f.write(struct.pack("<i", self.unk0x30))
        f.write(struct.pack("<i", self.runes))
        self.map_id.write(f)
        f.write(struct.pack("<I", self.unk0x3c))
        f.write(struct.pack("<I", self.unk0x38))


# ============================================================================
# MENU PROFILE SAVE LOAD
# ============================================================================


@dataclass
class MenuSaveLoad:
    """Menu profile save/load data (variable size based on size field)"""

    unk0x0: int = 0
    unk0x2: int = 0
    size: int = 0
    data: bytes = b""

    @classmethod
    def read(cls, f: BytesIO) -> MenuSaveLoad:
        """Read MenuSaveLoad from stream"""
        obj = cls()
        obj.unk0x0 = struct.unpack("<H", f.read(2))[0]
        obj.unk0x2 = struct.unpack("<H", f.read(2))[0]
        obj.size = struct.unpack("<I", f.read(4))[0]

        # Validate size to prevent reading corrupted data
        # MenuSaveLoad is always 0x1008 bytes total (header 8 + data 0x1000)
        if obj.size > 0x10000 or obj.size < 0:  # Max 64KB, min 0
            obj.size = 0x1000

        obj.data = f.read(obj.size)
        return obj

    def write(self, f: BytesIO):
        """Write MenuSaveLoad to stream"""
        f.write(struct.pack("<H", self.unk0x0))
        f.write(struct.pack("<H", self.unk0x2))
        f.write(struct.pack("<I", self.size))
        f.write(self.data)


# ============================================================================
# GAITEM GAME DATA
# ============================================================================


@dataclass
class GaitemGameDataEntry:
    """Single gaitem game data entry (16 bytes with padding)"""

    id: int = 0
    unk0x4: int = 0
    next_item_id: int = 0
    unk0xc: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> GaitemGameDataEntry:
        """Read GaitemGameDataEntry from stream (16 bytes)"""
        obj = cls()
        obj.id = struct.unpack("<I", f.read(4))[0]
        obj.unk0x4 = struct.unpack("<B", f.read(1))[0]
        f.read(3)  # padding
        obj.next_item_id = struct.unpack("<I", f.read(4))[0]
        obj.unk0xc = struct.unpack("<B", f.read(1))[0]
        f.read(3)  # padding
        return obj

    def write(self, f: BytesIO):
        """Write GaitemGameDataEntry to stream (16 bytes)"""
        f.write(struct.pack("<I", self.id))
        f.write(struct.pack("<B", self.unk0x4))
        f.write(b"\x00" * 3)  # padding
        f.write(struct.pack("<I", self.next_item_id))
        f.write(struct.pack("<B", self.unk0xc))
        f.write(b"\x00" * 3)  # padding


@dataclass
class GaitemGameData:
    """Gaitem game data (8 bytes + 7000 entries x 16 bytes = 0x1B458 bytes total)"""

    count: int = 0
    entries: list[GaitemGameDataEntry] = field(default_factory=list)

    @classmethod
    def read(cls, f: BytesIO) -> GaitemGameData:
        """Read GaitemGameData from stream"""
        obj = cls()
        obj.count = struct.unpack("<q", f.read(8))[0]  # i64
        obj.entries = [GaitemGameDataEntry.read(f) for _ in range(7000)]
        return obj

    def write(self, f: BytesIO):
        """Write GaitemGameData to stream"""
        f.write(struct.pack("<q", self.count))
        for entry in self.entries:
            entry.write(f)


# ============================================================================
# TUTORIAL DATA
# ============================================================================


@dataclass
class TutorialDataChunk:
    """Tutorial data chunk (variable size)"""

    count: int = 0
    tutorial_ids: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, f: BytesIO, total_size: int) -> TutorialDataChunk:
        """Read TutorialDataChunk from stream"""
        obj = cls()
        obj.count = struct.unpack("<I", f.read(4))[0]

        # Read remaining data based on total_size (not based on count)
        num_ids = (total_size - 4) // 4
        if num_ids > 0:
            obj.tutorial_ids = [
                struct.unpack("<I", f.read(4))[0] for _ in range(num_ids)
            ]

        return obj

    def write(self, f: BytesIO):
        """Write TutorialDataChunk to stream"""
        f.write(struct.pack("<I", self.count))
        for tutorial_id in self.tutorial_ids:
            f.write(struct.pack("<I", tutorial_id))


@dataclass
class TutorialData:
    """Tutorial completion data (variable size based on size field)"""

    unk0x0: int = 0
    unk0x2: int = 0
    size: int = 0
    data: TutorialDataChunk = field(default_factory=TutorialDataChunk)

    @classmethod
    def read(cls, f: BytesIO) -> TutorialData:
        """Read TutorialData from stream"""
        obj = cls()
        obj.unk0x0 = struct.unpack("<H", f.read(2))[0]
        obj.unk0x2 = struct.unpack("<H", f.read(2))[0]
        obj.size = struct.unpack("<I", f.read(4))[0]

        # Validate size
        if obj.size > 0x10000 or obj.size < 0:
            obj.size = 0x400

        obj.data = TutorialDataChunk.read(f, obj.size)

        return obj

    def write(self, f: BytesIO):
        """Write TutorialData to stream"""
        f.write(struct.pack("<H", self.unk0x0))
        f.write(struct.pack("<H", self.unk0x2))
        f.write(struct.pack("<I", self.size))
        self.data.write(f)


# ============================================================================
# FIELD AREA
# ============================================================================


@dataclass
class FieldArea:
    """Field area data (variable size based on size field)"""

    size: int = 0
    data: bytes = b""

    @classmethod
    def read(cls, f: BytesIO) -> FieldArea:
        """Read FieldArea from stream"""
        obj = cls()
        obj.size = struct.unpack("<i", f.read(4))[0]

        # Size field indicates how many DATA bytes to read (NOT including the size field itself)
        if obj.size > 0 and obj.size < 0x10000:
            obj.data = f.read(obj.size)
        else:
            obj.data = b""
            if obj.size != 0:
                pass

        return obj

    def write(self, f: BytesIO):
        """Write FieldArea to stream"""
        f.write(struct.pack("<i", self.size))
        if self.size > 4:
            f.write(self.data)


# ============================================================================
# WORLD AREA (Complex nested structure)
# ============================================================================


@dataclass
class WorldBlockChrData:
    """World block character data (variable size)"""

    magic: bytes = b"\x00\x00\x00\x00"
    map_id: MapId = field(default_factory=MapId)
    size: int = 0
    unk0xc: int = 0
    data: bytes = b""

    @classmethod
    def read(cls, f: BytesIO) -> WorldBlockChrData:
        """Read WorldBlockChrData from stream"""
        obj = cls()

        # Read header (16 bytes total)
        magic_bytes = f.read(4)
        if len(magic_bytes) < 4:
            # Hit end of stream, return terminator block
            obj.size = -1
            return obj

        obj.magic = magic_bytes
        obj.map_id = MapId.read(f)
        obj.size = struct.unpack("<i", f.read(4))[0]
        obj.unk0xc = struct.unpack("<I", f.read(4))[0]

        if obj.size > 0x10:
            obj.data = f.read(obj.size - 0x10)
        return obj

    def write(self, f: BytesIO):
        """Write WorldBlockChrData to stream"""
        f.write(self.magic)
        self.map_id.write(f)
        f.write(struct.pack("<i", self.size))
        f.write(struct.pack("<I", self.unk0xc))
        if self.size > 0x10:
            f.write(self.data)


@dataclass
class WorldAreaChrData:
    """World area character data (variable size with multiple blocks)"""

    magic: bytes = b"\x00\x00\x00\x00"
    unk_0x21042700: int = 0
    unk0x8: int = 0
    unk0xc: int = 0
    blocks: list[WorldBlockChrData] = field(default_factory=list)

    @classmethod
    def read(cls, f: BytesIO) -> WorldAreaChrData:
        """Read WorldAreaChrData from stream"""
        obj = cls()
        obj.magic = f.read(4)
        obj.unk_0x21042700 = struct.unpack("<I", f.read(4))[0]
        obj.unk0x8 = struct.unpack("<I", f.read(4))[0]
        obj.unk0xc = struct.unpack("<I", f.read(4))[0]

        # Read blocks until size < 1 (with safety limit)
        max_blocks = 100  # Safety limit to prevent infinite loops
        for _ in range(max_blocks):
            block = WorldBlockChrData.read(f)
            obj.blocks.append(block)
            if block.size < 1:
                break

        return obj

    def write(self, f: BytesIO):
        """Write WorldAreaChrData to stream"""
        f.write(self.magic)
        f.write(struct.pack("<I", self.unk_0x21042700))
        f.write(struct.pack("<I", self.unk0x8))
        f.write(struct.pack("<I", self.unk0xc))
        for block in self.blocks:
            block.write(f)


@dataclass
class WorldArea:
    """World area (variable size)"""

    size: int = 0
    data: WorldAreaChrData = field(default_factory=WorldAreaChrData)

    @classmethod
    def read(cls, f: BytesIO) -> WorldArea:
        """Read WorldArea from stream (variable size based on size field)"""
        obj = cls()
        obj.size = struct.unpack("<i", f.read(4))[0]

        # Size field indicates how many DATA bytes to read
        if obj.size > 0 and obj.size < 0x10000:
            raw_data = f.read(obj.size)

            # Try to parse WorldAreaChrData from the data
            if obj.size >= 8:
                inner_stream = BytesIO(raw_data)
                try:
                    obj.data = WorldAreaChrData.read(inner_stream)
                except Exception:
                    obj.data = WorldAreaChrData()
            else:
                obj.data = WorldAreaChrData()
        else:
            obj.data = WorldAreaChrData()
            if obj.size != 0:
                pass

        return obj

    def write(self, f: BytesIO):
        """Write WorldArea to stream"""
        f.write(struct.pack("<i", self.size))
        self.data.write(f)


# ============================================================================
# WORLD GEOM MAN (Geometry Manager)
# ============================================================================


@dataclass
class WorldGeomDataChunk:
    """World geometry data chunk (variable size)"""

    map_id: MapId = field(default_factory=MapId)
    size: int = 0
    unk_0x8: int = 0
    data: bytes = b""

    @classmethod
    def read(cls, f: BytesIO) -> WorldGeomDataChunk:
        """Read WorldGeomDataChunk from stream"""
        obj = cls()
        obj.map_id = MapId.read(f)
        obj.size = struct.unpack("<i", f.read(4))[0]
        obj.unk_0x8 = struct.unpack("<Q", f.read(8))[0]
        if obj.size > 0x10:
            obj.data = f.read(obj.size - 0x10)
        return obj

    def write(self, f: BytesIO):
        """Write WorldGeomDataChunk to stream"""
        self.map_id.write(f)
        f.write(struct.pack("<i", self.size))
        f.write(struct.pack("<Q", self.unk_0x8))
        if self.size > 0x10:
            f.write(self.data)


@dataclass
class WorldGeomData:
    """World geometry data (variable size with multiple chunks)"""

    magic: bytes = b"\x00\x00\x00\x00"
    unk_0x4: int = 0
    chunks: list[WorldGeomDataChunk] = field(default_factory=list)

    @classmethod
    def read(cls, f: BytesIO) -> WorldGeomData:
        """Read WorldGeomData from stream"""
        obj = cls()
        obj.magic = f.read(4)
        obj.unk_0x4 = struct.unpack("<I", f.read(4))[0]
        # Read chunks until size < 1 (with safety limit)
        max_chunks = 50  # Safety limit to prevent infinite loops
        for _ in range(max_chunks):
            chunk = WorldGeomDataChunk.read(f)
            obj.chunks.append(chunk)
            if chunk.size < 1:
                break

        return obj

    def write(self, f: BytesIO):
        """Write WorldGeomData to stream"""
        f.write(self.magic)
        f.write(struct.pack("<I", self.unk_0x4))
        for chunk in self.chunks:
            chunk.write(f)


@dataclass
class WorldGeomMan:
    """World geometry manager (variable size)"""

    size: int = 0
    data: WorldGeomData = field(default_factory=WorldGeomData)

    @classmethod
    def read(cls, f: BytesIO) -> WorldGeomMan:
        """Read WorldGeomMan from stream (variable size based on size field)"""
        obj = cls()
        obj.size = struct.unpack("<i", f.read(4))[0]

        # Size field indicates how many DATA bytes to read
        if obj.size > 0 and obj.size < 0x100000:
            raw_data = f.read(obj.size)

            # Try to parse the data
            if obj.size >= 8:
                inner_stream = BytesIO(raw_data)
                try:
                    obj.data = WorldGeomData.read(inner_stream)
                except Exception:
                    obj.data = WorldGeomData()
            else:
                obj.data = WorldGeomData()
        else:
            obj.data = WorldGeomData()
            if obj.size != 0:
                pass

        return obj

    def write(self, f: BytesIO):
        """Write WorldGeomMan to stream"""
        f.write(struct.pack("<i", self.size))
        self.data.write(f)


# ============================================================================
# REND MAN (Renderer Manager)
# ============================================================================


@dataclass
class StageManEntry:
    """Stage manager entry (variable size based on parent size)"""

    data: bytes = b""

    @classmethod
    def read(cls, f: BytesIO, entry_size: int) -> StageManEntry:
        """Read StageManEntry from stream"""
        obj = cls()
        if entry_size > 0:
            obj.data = f.read(entry_size)
        return obj

    def write(self, f: BytesIO):
        """Write StageManEntry to stream"""
        if len(self.data) > 0:
            f.write(self.data)


@dataclass
class StageMan:
    """Stage manager (variable size)"""

    count: int = 0
    entries: list[StageManEntry] = field(default_factory=list)

    @classmethod
    def read(cls, f: BytesIO, total_size: int) -> StageMan:
        """Read StageMan from stream"""
        obj = cls()
        obj.count = struct.unpack("<i", f.read(4))[0]

        # CRITICAL: Validate count to prevent hanging on corrupted data
        if obj.count > 0 and obj.count < 1000:  # Reasonable count limit
            entry_size = (total_size - 4) // obj.count
            # Also validate entry_size is reasonable
            if entry_size > 0 and entry_size < 0x10000:
                obj.entries = [
                    StageManEntry.read(f, entry_size) for _ in range(obj.count)
                ]
        elif obj.count >= 1000:
            pass

        return obj

    def write(self, f: BytesIO):
        """Write StageMan to stream"""
        f.write(struct.pack("<i", self.count))
        for entry in self.entries:
            entry.write(f)


@dataclass
class RendMan:
    """Renderer manager (variable size)"""

    size: int = 0
    data: StageMan = field(default_factory=StageMan)

    @classmethod
    def read(cls, f: BytesIO) -> RendMan:
        """Read RendMan from stream (variable size based on size field)"""
        obj = cls()
        obj.size = struct.unpack("<i", f.read(4))[0]

        # Size field indicates how many DATA bytes to read
        if obj.size > 0 and obj.size < 0x100000:
            obj.data = f.read(obj.size)
        else:
            obj.data = b""
            if obj.size != 0:
                pass

        return obj

    def write(self, f: BytesIO):
        """Write RendMan to stream"""
        f.write(struct.pack("<i", self.size))
        self.data.write(f)


# ============================================================================
# PLAYER COORDINATES
# ============================================================================


@dataclass
class PlayerCoordinates:
    """Player position and coordinates (0x39 = 57 bytes)"""

    coordinates: FloatVector3 = field(default_factory=FloatVector3)
    map_id: MapId = field(default_factory=MapId)
    angle: FloatVector4 = field(default_factory=FloatVector4)
    game_man_0xbf0: int = 0
    unk_coordinates: FloatVector3 = field(default_factory=FloatVector3)
    unk_angle: FloatVector4 = field(default_factory=FloatVector4)

    @classmethod
    def read(cls, f: BytesIO) -> PlayerCoordinates:
        """Read PlayerCoordinates from stream (57 bytes)"""
        return cls(
            coordinates=FloatVector3.read(f),
            map_id=MapId.read(f),
            angle=FloatVector4.read(f),
            game_man_0xbf0=struct.unpack("<B", f.read(1))[0],
            unk_coordinates=FloatVector3.read(f),
            unk_angle=FloatVector4.read(f),
        )

    def write(self, f: BytesIO):
        """Write PlayerCoordinates to stream (57 bytes)"""
        self.coordinates.write(f)
        self.map_id.write(f)
        self.angle.write(f)
        f.write(struct.pack("<B", self.game_man_0xbf0))
        self.unk_coordinates.write(f)
        self.unk_angle.write(f)


# ============================================================================
# NETWORK MANAGER
# ============================================================================


@dataclass
class NetMan:
    """Network manager (0x20004 = 131,076 bytes)"""

    unk0x0: int = 0
    data: bytes = field(default_factory=lambda: b"\x00" * 0x20000)

    @classmethod
    def read(cls, f: BytesIO) -> NetMan:
        """Read NetMan from stream (131,076 bytes)"""
        return cls(
            unk0x0=struct.unpack("<I", f.read(4))[0],
            data=f.read(0x20000),
        )

    def write(self, f: BytesIO):
        """Write NetMan to stream (131,076 bytes)"""
        f.write(struct.pack("<I", self.unk0x0))
        f.write(self.data)


# ============================================================================
# WORLD AREA WEATHER
# ============================================================================


@dataclass
class WorldAreaWeather:
    """World area weather (0xC = 12 bytes)"""

    area_id: int = 0
    weather_type: int = 0
    timer: int = 0
    padding: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> WorldAreaWeather:
        """Read WorldAreaWeather from stream (12 bytes)"""
        return cls(
            area_id=struct.unpack("<H", f.read(2))[0],
            weather_type=struct.unpack("<H", f.read(2))[0],
            timer=struct.unpack("<I", f.read(4))[0],
            padding=struct.unpack("<I", f.read(4))[0],
        )

    def write(self, f: BytesIO):
        """Write WorldAreaWeather to stream (12 bytes)"""
        f.write(struct.pack("<H", self.area_id))
        f.write(struct.pack("<H", self.weather_type))
        f.write(struct.pack("<I", self.timer))
        f.write(struct.pack("<I", self.padding))

    def is_corrupted(self) -> bool:
        """Check if weather is corrupted (AreaId == 0)"""
        return self.area_id == 0


# ============================================================================
# WORLD AREA TIME
# ============================================================================


@dataclass
class WorldAreaTime:
    """World area time (0xC = 12 bytes)"""

    hour: int = 0
    minute: int = 0
    second: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> WorldAreaTime:
        """Read WorldAreaTime from stream (12 bytes)"""
        return cls(
            hour=struct.unpack("<I", f.read(4))[0],
            minute=struct.unpack("<I", f.read(4))[0],
            second=struct.unpack("<I", f.read(4))[0],
        )

    def write(self, f: BytesIO):
        """Write WorldAreaTime to stream (12 bytes)"""
        f.write(struct.pack("<I", self.hour))
        f.write(struct.pack("<I", self.minute))
        f.write(struct.pack("<I", self.second))

    def is_zero(self) -> bool:
        """Check if time is 00:00:00 (potentially corrupted)"""
        return self.hour == 0 and self.minute == 0 and self.second == 0

    @classmethod
    def from_seconds(cls, total_seconds: int) -> WorldAreaTime:
        """Create WorldAreaTime from total seconds"""
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        return cls(hours, minutes, secs)

    def __str__(self):
        return f"{self.hour:02d}:{self.minute:02d}:{self.second:02d}"


# ============================================================================
# BASE VERSION
# ============================================================================


@dataclass
class BaseVersion:
    """Base game version (0x10 = 16 bytes)"""

    base_version_copy: int = 0
    base_version: int = 0
    is_latest_version: int = 0
    unk0xc: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> BaseVersion:
        """Read BaseVersion from stream (16 bytes)"""
        return cls(
            base_version_copy=struct.unpack("<I", f.read(4))[0],
            base_version=struct.unpack("<I", f.read(4))[0],
            is_latest_version=struct.unpack("<I", f.read(4))[0],
            unk0xc=struct.unpack("<I", f.read(4))[0],
        )

    def write(self, f: BytesIO):
        """Write BaseVersion to stream (16 bytes)"""
        f.write(struct.pack("<I", self.base_version_copy))
        f.write(struct.pack("<I", self.base_version))
        f.write(struct.pack("<I", self.is_latest_version))
        f.write(struct.pack("<I", self.unk0xc))


# ============================================================================
# PS5 ACTIVITY AND DLC
# ============================================================================


@dataclass
class PS5Activity:
    """PS5 activity data (0x20 = 32 bytes)"""

    data: bytes = field(default_factory=lambda: b"\x00" * 0x20)

    @classmethod
    def read(cls, f: BytesIO) -> PS5Activity:
        """Read PS5Activity from stream (32 bytes)"""
        return cls(data=f.read(0x20))

    def write(self, f: BytesIO):
        """Write PS5Activity to stream (32 bytes)"""
        f.write(self.data)


@dataclass
class DLC:
    """DLC data (0x32 = 50 bytes)"""

    data: bytes = field(default_factory=lambda: b"\x00" * 0x32)

    @classmethod
    def read(cls, f: BytesIO) -> DLC:
        """Read DLC from stream (50 bytes)"""
        return cls(data=f.read(0x32))

    def write(self, f: BytesIO):
        """Write DLC to stream (50 bytes)"""
        f.write(self.data)


# ============================================================================
# PLAYER GAME DATA HASH
# ============================================================================


@dataclass
class PlayerGameDataHash:
    """
    Player game data hash (0x80 = 128 bytes)

    This hash is calculated from player data and equipment.
    Used for integrity checking.
    """

    level: int = 0
    stats: int = 0
    archetype: int = 0
    playergame_data_0xc0: int = 0
    padding: int = 0
    runes: int = 0
    runes_memory: int = 0
    equipped_weapons: int = 0
    equipped_armors_and_talismans: int = 0
    equipped_items: int = 0
    equipped_spells: int = 0
    rest: bytes = field(default_factory=lambda: b"\x00" * 0x54)

    @classmethod
    def read(cls, f: BytesIO) -> PlayerGameDataHash:
        """Read PlayerGameDataHash from stream (128 bytes)"""
        return cls(
            level=struct.unpack("<I", f.read(4))[0],
            stats=struct.unpack("<I", f.read(4))[0],
            archetype=struct.unpack("<I", f.read(4))[0],
            playergame_data_0xc0=struct.unpack("<I", f.read(4))[0],
            padding=struct.unpack("<I", f.read(4))[0],
            runes=struct.unpack("<I", f.read(4))[0],
            runes_memory=struct.unpack("<I", f.read(4))[0],
            equipped_weapons=struct.unpack("<I", f.read(4))[0],
            equipped_armors_and_talismans=struct.unpack("<I", f.read(4))[0],
            equipped_items=struct.unpack("<I", f.read(4))[0],
            equipped_spells=struct.unpack("<I", f.read(4))[0],
            rest=f.read(0x54),
        )

    def write(self, f: BytesIO):
        """Write PlayerGameDataHash to stream (128 bytes)"""
        f.write(struct.pack("<I", self.level))
        f.write(struct.pack("<I", self.stats))
        f.write(struct.pack("<I", self.archetype))
        f.write(struct.pack("<I", self.playergame_data_0xc0))
        f.write(struct.pack("<I", self.padding))
        f.write(struct.pack("<I", self.runes))
        f.write(struct.pack("<I", self.runes_memory))
        f.write(struct.pack("<I", self.equipped_weapons))
        f.write(struct.pack("<I", self.equipped_armors_and_talismans))
        f.write(struct.pack("<I", self.equipped_items))
        f.write(struct.pack("<I", self.equipped_spells))
        f.write(self.rest)
