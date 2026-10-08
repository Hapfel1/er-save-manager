"""
Elden Ring Save Parser - World State and Game Data Structures

Contains world state, game progression, and miscellaneous game data structures.
Based on ER-Save-Lib Rust implementation.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from io import BytesIO

from er_save_manager.parser.er_types import (
    FloatVector3,
    FloatVector4,
    HorseState,
    MapId,
)

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
        # size is normally 0x1000 (total 0x1008), clamped to that as a fallback if corrupted/out of range
        if obj.size > 0x10000:
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
    pad0x5: bytes = b"\x00\x00\x00"
    next_item_id: int = 0
    unk0xc: int = 0
    pad0x0d: bytes = b"\x00\x00\x00"

    @classmethod
    def read(cls, f: BytesIO) -> GaitemGameDataEntry:
        """Read GaitemGameDataEntry from stream (16 bytes)"""
        obj = cls()
        obj.id = struct.unpack("<I", f.read(4))[0]
        obj.unk0x4 = struct.unpack("<B", f.read(1))[0]
        obj.pad0x5 = f.read(3)
        obj.next_item_id = struct.unpack("<I", f.read(4))[0]
        obj.unk0xc = struct.unpack("<B", f.read(1))[0]
        obj.pad0x0d = f.read(3)
        return obj

    def write(self, f: BytesIO):
        """Write GaitemGameDataEntry to stream (16 bytes)"""
        f.write(struct.pack("<I", self.id))
        f.write(struct.pack("<B", self.unk0x4))
        f.write(
            self.pad0x5
            if isinstance(self.pad0x5, (bytes, bytearray)) and len(self.pad0x5) == 3
            else b"\x00\x00\x00"
        )
        f.write(struct.pack("<I", self.next_item_id))
        f.write(struct.pack("<B", self.unk0xc))
        f.write(
            self.pad0x0d
            if isinstance(self.pad0x0d, (bytes, bytearray)) and len(self.pad0x0d) == 3
            else b"\x00\x00\x00"
        )


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

        # Size field indicates how many DATA bytes to read (not including the size field itself)
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
# WORLD AREA
# ============================================================================


WORLD_RECORD_TERMINATOR = 0xFFFFFFFF


def _map_name(map_id: MapId) -> str:
    d = map_id.data
    return f"m{d[3]:02d}_{d[2]:02d}_{d[1]:02d}_{d[0]:02d}"


@dataclass
class WorldChrEntry:
    """
    Enemy part in a non-default state (u32).

    Bit 30 is always set, bits 16-29 hold the character model (cXXXX),
    bits 2-15 the MSB part instance and bits 0-1 the state. Model and instance
    name the MSB enemy part cXXXX_IIII of the owning map. State 3 is a kill
    since the last rest; 1 and 2 are rare and their meaning is unknown.
    """

    value: int = 0

    @property
    def model(self) -> int:
        return (self.value >> 16) & 0x3FFF

    @property
    def instance(self) -> int:
        return (self.value >> 2) & 0x3FFF

    @property
    def state(self) -> int:
        return self.value & 0x3

    @property
    def part_name(self) -> str:
        return f"c{self.model:04d}_{self.instance:04d}"


@dataclass
class WorldChrMapRecord:
    """
    Enemy state of one loaded map ("CSBC" record).

    Header: magic, MapId, u32 record size, u32 (enemy_part_count << 14 | n).
    Followed by n WorldChrEntry values, zero padded to a 16-byte multiple.
    enemy_part_count is the number of enemy parts in the map's MSB for the
    game version that wrote the save.
    """

    map_id: MapId = field(default_factory=MapId)
    enemy_part_count: int = 0
    entries: list[WorldChrEntry] = field(default_factory=list)

    @property
    def map_name(self) -> str:
        return _map_name(self.map_id)

    def write(self, f: BytesIO):
        n = len(self.entries)
        size = (16 + 4 * n + 15) // 16 * 16
        f.write(b"CSBC")
        self.map_id.write(f)
        f.write(struct.pack("<II", size, (self.enemy_part_count << 14) | n))
        for entry in self.entries:
            f.write(struct.pack("<I", entry.value))
        f.write(b"\x00" * (size - 16 - 4 * n))


@dataclass
class WorldAreaChrData:
    """
    Decoded WorldArea data: per-map enemy state for the maps around the player.

    Header: magic "CHR ", u32 version (0x21042700), u64 unknown (0).
    Then WorldChrMapRecord entries, ended by a 16-byte "CSBC" record whose
    MapId is 0xFFFFFFFF. A record exists while its map is loaded; kills are
    cleared on rest, event-driven dead/disabled parts are written again on load.
    """

    magic: bytes = b"CHR "
    version: int = 0
    unk0x8: int = 0
    records: list[WorldChrMapRecord] = field(default_factory=list)
    terminator: bytes = b""

    @classmethod
    def from_bytes(cls, data: bytes) -> WorldAreaChrData | None:
        """Decode WorldArea data; None when it does not re-encode byte-identical."""
        if len(data) < 32 or data[:4] != b"CHR ":
            return None
        obj = cls()
        obj.version, obj.unk0x8 = struct.unpack_from("<IQ", data, 4)
        pos = 16
        while pos + 16 <= len(data) and data[pos : pos + 4] == b"CSBC":
            raw_map, size, head = struct.unpack_from("<III", data, pos + 4)
            if raw_map == WORLD_RECORD_TERMINATOR:
                obj.terminator = data[pos : pos + 16]
                break
            n = head & 0x3FFF
            if size < 16 + 4 * n or pos + size > len(data):
                return None
            entries = struct.unpack_from(f"<{n}I", data, pos + 16)
            obj.records.append(
                WorldChrMapRecord(
                    map_id=MapId(data[pos + 4 : pos + 8]),
                    enemy_part_count=head >> 14,
                    entries=[WorldChrEntry(v) for v in entries],
                )
            )
            pos += size
        return obj if obj.terminator and obj.to_bytes() == data else None

    def to_bytes(self) -> bytes:
        f = BytesIO()
        f.write(self.magic)
        f.write(struct.pack("<IQ", self.version, self.unk0x8))
        for record in self.records:
            record.write(f)
        f.write(self.terminator)
        return f.getvalue()


@dataclass
class WorldArea:
    """World area (variable size)"""

    size: int = 0
    data: bytes = b""

    @classmethod
    def read(cls, f: BytesIO) -> WorldArea:
        """Read WorldArea from stream (variable size based on size field)"""
        obj = cls()
        obj.size = struct.unpack("<i", f.read(4))[0]

        if obj.size > 0 and obj.size < 0x10000:
            obj.data = f.read(obj.size)
        else:
            obj.data = b""
            if obj.size != 0:
                pass

        return obj

    def parse_chr(self) -> WorldAreaChrData | None:
        """Decoded enemy state, or None when empty or not decodable."""
        return WorldAreaChrData.from_bytes(self.data)

    def write(self, f: BytesIO):
        """Write WorldArea to stream"""
        f.write(struct.pack("<i", self.size))
        if self.size > 4:
            f.write(self.data)


# ============================================================================
# WORLD GEOM MAN (Geometry Manager)
# ============================================================================


@dataclass
class WorldGeomEntry:
    """
    Asset part in a non-default state (u32 key, u32 model).

    key bits 15-31 hold the MSB part instance and bits 0-14 the state;
    model is 10000000 + the AEG id (AssetEnvironmentGeometryParam row).
    Together they name the MSB asset part AEGxxx_yyy_iiii of the owning map.
    WorldGeomMan states: 1 broken, 3 picked since the last rest, 2 picked
    permanently. WorldGeomMan2 entries are always 1.
    """

    key: int = 0
    model: int = 0

    @property
    def instance(self) -> int:
        return self.key >> 15

    @property
    def state(self) -> int:
        return self.key & 0x7FFF

    @property
    def aeg_id(self) -> int:
        return self.model - 10000000

    @property
    def part_name(self) -> str:
        aeg = self.aeg_id
        return f"AEG{aeg // 1000:03d}_{aeg % 1000:03d}_{self.instance:04d}"


@dataclass
class WorldGeomMapRecord:
    """
    Asset state of one map.

    Header: MapId, u32 record size (16 + 8n), u32 n, u32 unknown.
    Followed by n WorldGeomEntry. The unknown u32 is constant per map and
    game version (same across characters); its meaning is not known.
    """

    map_id: MapId = field(default_factory=MapId)
    unk0xc: int = 0
    entries: list[WorldGeomEntry] = field(default_factory=list)

    @property
    def map_name(self) -> str:
        return _map_name(self.map_id)

    def write(self, f: BytesIO):
        n = len(self.entries)
        self.map_id.write(f)
        f.write(struct.pack("<III", 16 + 8 * n, n, self.unk0xc))
        for entry in self.entries:
            f.write(struct.pack("<II", entry.key, entry.model))


@dataclass
class WorldGeomData:
    """
    Decoded WorldGeomMan / WorldGeomMan2 data.

    Header: magic ("MOEG" for WorldGeomMan, "FOEG" for WorldGeomMan2) and a
    u32 version (0x21042600). Then WorldGeomMapRecord entries, ended by a
    16-byte record whose MapId is 0xFFFFFFFF.

    WorldGeomMan covers the maps around the player: broken assets and picked
    assets, cleared on rest except permanent pickups (state 2).
    WorldGeomMan2 keeps every map ever visited and lists the permanently
    picked one-time nodes (assets with isEnableRepick set in
    AssetEnvironmentGeometryParam: Arteria Leaf, smithing stones, gloveworts).
    """

    magic: bytes = b""
    version: int = 0
    records: list[WorldGeomMapRecord] = field(default_factory=list)
    terminator: bytes = b""

    @classmethod
    def from_bytes(cls, data: bytes) -> WorldGeomData | None:
        """Decode WorldGeomMan data; None when it does not re-encode byte-identical."""
        if len(data) < 24 or data[:4] not in (b"MOEG", b"FOEG"):
            return None
        obj = cls(magic=data[:4], version=struct.unpack_from("<I", data, 4)[0])
        pos = 8
        while pos + 16 <= len(data):
            raw_map, size, n, unk = struct.unpack_from("<IIII", data, pos)
            if raw_map == WORLD_RECORD_TERMINATOR:
                obj.terminator = data[pos : pos + 16]
                break
            if size != 16 + 8 * n or pos + size > len(data):
                return None
            values = struct.unpack_from(f"<{2 * n}I", data, pos + 16)
            obj.records.append(
                WorldGeomMapRecord(
                    map_id=MapId(data[pos : pos + 4]),
                    unk0xc=unk,
                    entries=[
                        WorldGeomEntry(values[k], values[k + 1])
                        for k in range(0, 2 * n, 2)
                    ],
                )
            )
            pos += size
        return obj if obj.terminator and obj.to_bytes() == data else None

    def to_bytes(self) -> bytes:
        f = BytesIO()
        f.write(self.magic)
        f.write(struct.pack("<I", self.version))
        for record in self.records:
            record.write(f)
        f.write(self.terminator)
        return f.getvalue()


@dataclass
class WorldGeomMan:
    """World geometry manager (variable size)"""

    size: int = 0
    data: bytes = b""

    @classmethod
    def read(cls, f: BytesIO) -> WorldGeomMan:
        """Read WorldGeomMan from stream (variable size based on size field)"""
        obj = cls()
        obj.size = struct.unpack("<i", f.read(4))[0]

        if obj.size > 0 and obj.size < 0x100000:
            obj.data = f.read(obj.size)
        else:
            obj.data = b""
            if obj.size != 0:
                pass

        return obj

    def parse_geom(self) -> WorldGeomData | None:
        """Decoded asset state, or None when empty or not decodable."""
        return WorldGeomData.from_bytes(self.data)

    def write(self, f: BytesIO):
        """Write WorldGeomMan to stream"""
        f.write(struct.pack("<i", self.size))
        if self.size > 4:
            f.write(self.data)


# ============================================================================
# REND MAN (Renderer Manager)
# ============================================================================


@dataclass
class RendManDecal:
    """
    Persistent ground decal (40 bytes).

    decal_id is a DecalParam row (blood splatter, burn marks, 3000xxxxx trail
    decals, 6001xxxxx triangle decals). points are three positions in 1/8
    world units, local to the player's map; point decals repeat one position.
    The four trailing u32 are unknown (the first three are equal on point
    decals).
    """

    decal_id: int = 0
    points: tuple[tuple[int, int, int], ...] = ((0, 0, 0), (0, 0, 0), (0, 0, 0))
    pad: int = 0
    unk: tuple[int, int, int, int] = (0, 0, 0, 0)

    SIZE = 40

    @classmethod
    def from_bytes(cls, data: bytes, offset: int = 0) -> RendManDecal:
        v = struct.unpack_from("<I9hH4I", data, offset)
        return cls(
            decal_id=v[0],
            points=(v[1:4], v[4:7], v[7:10]),
            pad=v[10],
            unk=v[11:15],
        )

    def to_bytes(self) -> bytes:
        return struct.pack(
            "<I9hH4I",
            self.decal_id,
            *self.points[0],
            *self.points[1],
            *self.points[2],
            self.pad,
            *self.unk,
        )

    @property
    def position(self) -> tuple[float, float, float]:
        x, y, z = self.points[0]
        return (x / 8, y / 8, z / 8)


@dataclass
class RendManData:
    """Decoded RendMan data: u32 count, then count RendManDecal."""

    decals: list[RendManDecal] = field(default_factory=list)

    @classmethod
    def from_bytes(cls, data: bytes) -> RendManData | None:
        """Decode RendMan data; None when it does not re-encode byte-identical."""
        if len(data) < 4:
            return None
        count = struct.unpack_from("<I", data, 0)[0]
        if len(data) != 4 + RendManDecal.SIZE * count:
            return None
        obj = cls(
            decals=[
                RendManDecal.from_bytes(data, 4 + RendManDecal.SIZE * k)
                for k in range(count)
            ]
        )
        return obj if obj.to_bytes() == data else None

    def to_bytes(self) -> bytes:
        return struct.pack("<I", len(self.decals)) + b"".join(
            d.to_bytes() for d in self.decals
        )


@dataclass
class RendMan:
    """Renderer manager (variable size)"""

    size: int = 0
    data: bytes = b""

    @classmethod
    def read(cls, f: BytesIO) -> RendMan:
        """Read RendMan from stream (variable size based on size field)"""
        obj = cls()
        obj.size = struct.unpack("<i", f.read(4))[0]

        if obj.size > 0 and obj.size < 0x100000:
            obj.data = f.read(obj.size)
        else:
            obj.data = b""
            if obj.size != 0:
                pass

        return obj

    def parse_decals(self) -> RendManData | None:
        """Decoded decals, or None when empty or not decodable."""
        return RendManData.from_bytes(self.data)

    def write(self, f: BytesIO):
        """Write RendMan to stream"""
        f.write(struct.pack("<i", self.size))
        if isinstance(self.data, bytes):
            f.write(self.data)
        else:
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
    """Network manager.

    Total blob in the save: 0x20004 bytes.
      [4 bytes, always 0x00000000] - hidden prefix consumed by variable-struct parsing
                                     before this point; NOT read by NetMan.read()
      [4 bytes, always 0x00000002] - unk0x0; net_man_offset points here
      [0x20000 bytes]              - network data

    CSNetMan.bin captures the full 0x20004-byte blob including the hidden prefix,
    so it must be written at (net_man_offset - 4), not at net_man_offset.
    """

    unk0x0: int = 0  # always 2
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
    """
    DLC ownership/entry flags (0x32 = 50 bytes)

    Structure (CSDlc) - array of 1-byte bools:
        [0] = pre-order gesture "The Ring"
        [1] = Shadow of the Erdtree DLC entry flag
        [2] = pre-order gesture "Ring of Miquella"
        [3] = Tarnished Edition pack flag.
        [4-49] = unused (must be 0, non-zero values prevent save from loading)
    """

    preorder_the_ring: int = 0
    shadow_of_erdtree: int = 0
    preorder_ring_of_miquella: int = 0
    tarnished_pack: int = 0
    unused: bytes = field(default_factory=lambda: b"\x00" * 46)

    @classmethod
    def read(cls, f: BytesIO) -> DLC:
        """Read DLC from stream (50 bytes)"""
        return cls(
            preorder_the_ring=struct.unpack("<B", f.read(1))[0],
            shadow_of_erdtree=struct.unpack("<B", f.read(1))[0],
            preorder_ring_of_miquella=struct.unpack("<B", f.read(1))[0],
            tarnished_pack=struct.unpack("<B", f.read(1))[0],
            unused=f.read(46),
        )

    def write(self, f: BytesIO):
        """Write DLC to stream (50 bytes)"""
        f.write(struct.pack("<B", self.preorder_the_ring))
        f.write(struct.pack("<B", self.shadow_of_erdtree))
        f.write(struct.pack("<B", self.preorder_ring_of_miquella))
        f.write(struct.pack("<B", self.tarnished_pack))
        f.write(self.unused)

    def has_dlc_flag(self) -> bool:
        """True if the character has entered the Shadow of the Erdtree DLC area."""
        return self.shadow_of_erdtree != 0

    def get_dlc_flag_value(self) -> int:
        return self.shadow_of_erdtree

    def clear_dlc_flag(self):
        self.shadow_of_erdtree = 0

    def has_tarnished_pack_flag(self) -> bool:
        """True if the Tarnished pack entry flag is set."""
        return self.tarnished_pack != 0

    def get_tarnished_pack_flag_value(self) -> int:
        return self.tarnished_pack

    def clear_tarnished_pack_flag(self):
        self.tarnished_pack = 0

    def has_invalid_flags(self) -> bool:
        """True if any unused slots [4-49] are non-zero."""
        return any(b != 0 for b in self.unused)

    def clear_invalid_flags(self):
        self.unused = b"\x00" * 46


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
