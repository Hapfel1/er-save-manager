"""DS2 map object and treasure states (WorldObjects), door data and door
writes."""

from __future__ import annotations

import struct

from er_save_manager.games.DS2.save import EventFlags, WorldObjects
from er_save_manager.games.DS2.world_flags import (
    AREAS,
    DOORS,
    Door,
    DoorStatus,
    door_status,
    set_doors,
)

ANCHOR = 0x30000
CHAIN = ANCHOR + 0x7000
BLOCK = 0xC08
CAP = 192
M10_02, M10_04, M10_10 = 0x0A020000, 0x0A040000, 0x0A0A0000
MAPS = [M10_02, M10_04, M10_10]
LIVE_OBJECTS = ANCHOR + 0xC50
LIVE_TREASURE_IDS = ANCHOR + 0x4C64
LIVE_TREASURE_STATES = LIVE_TREASURE_IDS + 4 * 1024

CHEST = 10105020
PICKUP = 10106580
UNTAKEN_1 = 0x100401
TAKEN_1 = 0x1100001


def _u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def _put(data, offset, value):
    struct.pack_into("<I", data, offset, value)


def _block(data, index, map_id, objects, treasures):
    offset = CHAIN + index * BLOCK
    _put(data, offset, map_id)
    _put(data, offset + 4, len(objects))
    for k, (instance_id, state) in enumerate(objects):
        _put(data, offset + 8 + 8 * k, instance_id)
        # Upper bytes are uninitialized memory in real saves.
        _put(data, offset + 12 + 8 * k, 0xD61C0000 | state)
    ids = offset + 8 + 8 * CAP
    for k, (instance_id, state) in enumerate(treasures):
        _put(data, ids + 4 * k, instance_id)
        _put(data, ids + 4 * CAP + 4 * k, state)
    return offset


def _save():
    data = bytearray(CHAIN + 4 * BLOCK)
    _block(data, 0, M10_02, [(10025010, 20)], [(10026000, UNTAKEN_1)])
    _block(data, 1, M10_04, [(10045010, 20)], [])
    m10_10 = _block(
        data,
        2,
        M10_10,
        [(CHEST, 80), (PICKUP, 10), (10100409, 10)],
        # A leftover id from another map and a garbage state are not treasures.
        [(CHEST, TAKEN_1), (PICKUP, TAKEN_1), (10000, 0x4E25), (10106000, 0x3F800000)],
    )
    # Live object list: one map, records [u32][state in byte 2][u32][id * 4].
    _put(data, LIVE_OBJECTS, 1)
    _put(data, LIVE_OBJECTS + 4, M10_10)
    _put(data, LIVE_OBJECTS + 8, 2)
    for k, (instance_id, state) in enumerate([(CHEST, 80), (10100409, 10)]):
        record = LIVE_OBJECTS + 12 + 16 * k
        _put(data, record + 4, 0x01000000 | state << 16)
        _put(data, record + 12, 0xC0000000 | instance_id * 4)
    _put(data, LIVE_TREASURE_IDS + 8, CHEST)
    _put(data, LIVE_TREASURE_STATES + 8, TAKEN_1)
    return data, m10_10


def test_treasures_of_visited_maps_only():
    data, _ = _save()
    view = WorldObjects(data, ANCHOR, MAPS)
    found = {t.instance_id: t.taken for t in view.treasures()}
    assert found == {10026000: False, CHEST: True, PICKUP: True}
    # No chain at all: no objects
    view = WorldObjects(bytearray(ANCHOR + 0x8000), ANCHOR, MAPS)
    assert view.treasures() == []
    assert view.object_state(CHEST) is None


def test_respawn_writes_every_copy_and_closes_the_chest():
    data, m10_10 = _save()
    view = WorldObjects(data, ANCHOR, MAPS)
    assert view.respawn([CHEST, PICKUP, 10026000]) == 2
    states = m10_10 + 8 + 12 * CAP
    assert _u32(data, states) == UNTAKEN_1
    assert _u32(data, states + 4) == UNTAKEN_1
    assert _u32(data, LIVE_TREASURE_STATES + 8) == UNTAKEN_1
    assert view.object_state(CHEST) == 20
    assert _u32(data, m10_10 + 12) == 0xD61C0000 | 20
    assert _u32(data, LIVE_OBJECTS + 12 + 4) == 0x01000000 | 20 << 16
    # The ground pickup keeps its object state.
    assert view.object_state(PICKUP) == 10


def test_respawn_keeps_lot_mask():
    data, m10_10 = _save()
    states = m10_10 + 8 + 12 * CAP
    _put(data, states, 0x1100000 | 0x1F)
    WorldObjects(data, ANCHOR, MAPS).respawn([CHEST])
    assert _u32(data, states) == 0x100000 | 0x1F | 0x1F << 10


def test_set_object_state_writes_block_and_live_list():
    data, m10_10 = _save()
    view = WorldObjects(data, ANCHOR, MAPS)
    assert view.set_object_state(10100409, 30)
    assert _u32(data, m10_10 + 8 + 8 * 2 + 4) & 0xFF == 30
    assert _u32(data, LIVE_OBJECTS + 12 + 16 + 4) == 0x01000000 | 30 << 16
    assert not view.set_object_state(99999999, 30)


def test_door_open_and_close():
    data, _ = _save()
    flags = EventFlags(data, ANCHOR, MAPS)
    objects = WorldObjects(data, ANCHOR, MAPS)
    door = Door(M10_10, 110000076, 10100409, 30, "Soldier Key door", None)
    assert door_status(door, flags, objects) is DoorStatus.CLOSED
    assert set_doors([door], True, flags, objects) == 1
    assert flags.get_flag(110000076)
    assert objects.object_state(10100409) == 30
    assert door_status(door, flags, objects) is DoorStatus.OPEN
    assert set_doors([door], True, flags, objects) == 0
    flags.set_flag(110000076, False)
    assert door_status(door, flags, objects) is DoorStatus.PARTLY_OPEN
    assert set_doors([door], False, flags, objects) == 1
    assert door_status(door, flags, objects) is DoorStatus.CLOSED

    # A door whose object is not in the save is not written
    door = Door(M10_10, 110000072, 10100416, 30, "Soldier Key door", None)
    assert door_status(door, flags, objects) is DoorStatus.MISSING
    assert set_doors([door], True, flags, objects) == 0
    assert not flags.get_flag(110000072)


def test_door_table():
    assert DOORS
    for door in DOORS:
        assert door.label
        assert door.open_state in (20, 30)
        assert door.map_id in AREAS
        assert door.flag % 1_000_000 < 200
        assert door.object_id // 10_000 == (door.map_id >> 24) * 100 + (
            door.map_id >> 16 & 0xFF
        )
    assert len({d.flag for d in DOORS}) == len(DOORS)
