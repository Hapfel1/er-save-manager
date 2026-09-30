"""DS2 equipment block decoding (layout documented in DS2/save.py)."""

from __future__ import annotations

import struct

from er_save_manager.games.DS2.save import (
    EQUIPMENT_HEADER,
    EQUIPMENT_OFFSET,
    INVENTORY_START,
    Character,
)

RAPIER = 1500000
FARAAM_HELM_ITEM = 21320100
SECOND_DRAGON_RING = 40040001
AGED_FEATHER = 60355000


def _character(header: int = EQUIPMENT_HEADER) -> Character:
    data = bytearray(INVENTORY_START)
    base = EQUIPMENT_OFFSET
    struct.pack_into("<I", data, base, header)
    # Every slot empty, weapons unarmed, as a fresh block is.
    for rel in range(0x04, 0x7C, 4):
        struct.pack_into("<I", data, base + rel, 0xFFFFFFFF)
    for k in range(6):
        struct.pack_into("<I", data, base + 0x04 + 4 * k, 3400000)
    struct.pack_into("<I", data, base + 0x08, RAPIER)
    struct.pack_into("<I", data, base + 0x1C, FARAAM_HELM_ITEM - 10000000)
    struct.pack_into("<I", data, base + 0x50, SECOND_DRAGON_RING)
    struct.pack_into("<I", data, base + 0x58, AGED_FEATHER)
    return Character(data)


def test_equipped_ids_map_every_slot_kind():
    assert _character().equipped_item_ids() == {
        RAPIER,
        FARAAM_HELM_ITEM,
        SECOND_DRAGON_RING,
        AGED_FEATHER,
    }


def test_unknown_header_blocks_nothing():
    assert _character(header=0).equipped_item_ids() == set()
