"""Tests for decoding WorldArea (CHR) and WorldGeomMan/WorldGeomMan2 (MOEG/FOEG)."""

from __future__ import annotations

import struct

from er_save_manager.parser.er_types import MapId
from er_save_manager.parser.world import (
    WorldAreaChrData,
    WorldChrEntry,
    WorldChrMapRecord,
    WorldGeomData,
    WorldGeomEntry,
    WorldGeomMapRecord,
)

# m60_42_36_00
MAP = MapId(bytes([0x00, 0x24, 0x2A, 0x3C]))


def test_fixture_blocks_decode_byte_identical(sanitized_save):
    decoded = 0
    for i in range(10):
        slot = sanitized_save.get_slot(i)
        if not slot.version:
            continue
        for block, data in (
            (slot.world_area.parse_chr(), slot.world_area.data),
            (slot.world_geom_man.parse_geom(), slot.world_geom_man.data),
            (slot.world_geom_man2.parse_geom(), slot.world_geom_man2.data),
        ):
            if not data:
                continue
            assert block is not None
            assert block.to_bytes() == data
            decoded += 1
    assert decoded > 0


def test_chr_entry_fields():
    entry = WorldChrEntry((1 << 30) | (4311 << 16) | (9002 << 2) | 3)
    assert entry.part_name == "c4311_9002"
    assert entry.state == 3


def test_chr_record_layout():
    chr_data = WorldAreaChrData(
        version=0x21042700,
        records=[
            WorldChrMapRecord(
                map_id=MAP,
                enemy_part_count=30,
                entries=[WorldChrEntry((1 << 30) | (4311 << 16) | (9002 << 2) | 3)],
            )
        ],
        terminator=b"CSBC" + b"\xff" * 4 + b"\x00" * 8,
    )
    data = chr_data.to_bytes()
    size, head = struct.unpack_from("<II", data, 24)
    assert size == 0x20
    assert head == (30 << 14) | 1
    decoded = WorldAreaChrData.from_bytes(data)
    assert decoded.records[0].map_name == "m60_42_36_00"
    assert decoded.records[0].entries[0].part_name == "c4311_9002"


def test_geom_entry_fields():
    entry = WorldGeomEntry((9000 << 15) | 2, 10099691)
    assert entry.part_name == "AEG099_691_9000"
    assert entry.aeg_id == 99691
    assert entry.state == 2


def test_geom_round_trip_and_rejects_bad_size():
    geom = WorldGeomData(
        magic=b"FOEG",
        version=0x21042600,
        records=[
            WorldGeomMapRecord(
                map_id=MAP,
                unk0xc=619,
                entries=[WorldGeomEntry((9000 << 15) | 1, 10099691)],
            )
        ],
        terminator=b"\xff" * 4 + b"\x00" * 12,
    )
    data = geom.to_bytes()
    decoded = WorldGeomData.from_bytes(data)
    assert decoded.records[0].entries[0].part_name == "AEG099_691_9000"
    assert decoded.to_bytes() == data

    broken = bytearray(data)
    struct.pack_into("<I", broken, 12, 0x30)
    assert WorldGeomData.from_bytes(bytes(broken)) is None
