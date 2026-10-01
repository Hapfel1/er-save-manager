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


def test_equip_writes_ids_and_inventory_positions():
    from er_save_manager.games.DS2.save import EQUIPMENT_INDEX_OFFSET, InventoryItem
    from er_save_manager.games.DS2.soulsplanner import equip_build, parse_build_html
    from tests.test_ds2_soulsplanner import _PAGE

    build = parse_build_html(_PAGE, "1")
    data = bytearray(EQUIPMENT_INDEX_OFFSET + 0x80)
    data[: INVENTORY_START + 0] = _character().raw()[:INVENTORY_START]
    # Leave the R3 weapon and belt 1 slots holding something the build cannot
    # import; they must stay as they are.
    struct.pack_into("<I", data, EQUIPMENT_OFFSET + 0x18, 1234567)
    struct.pack_into("<I", data, EQUIPMENT_OFFSET + 0x54, 60155000)
    character = Character(data)

    positions: dict[int, list[int]] = {}
    for pos, item in enumerate(
        [i for i in build.items for _ in range(i.count)], start=3
    ):
        entry = InventoryItem(INVENTORY_START + 16 * pos, item.item_id, 0, 1, 0)
        character.write_inventory_slot(entry)
        positions.setdefault(item.item_id, []).append(pos)

    assert equip_build(character, build, {}) == []

    def block(rel, k):
        return struct.unpack_from("<I", data, EQUIPMENT_OFFSET + rel + 4 * k)[0]

    def index(i):
        return struct.unpack_from("<H", data, EQUIPMENT_INDEX_OFFSET + 2 * i)[0]

    lo = build.loadout
    fume, spear, dagger = lo.weapons[0][0], lo.weapons[1][0], lo.weapons[2][0]
    assert [block(0x04, k) for k in range(6)] == [
        fume,
        spear,
        dagger,
        dagger,
        3400000,
        1234567,
    ]
    # Index order is R1, L1, R2, L2, R3, L3; the two daggers use two copies.
    assert index(0) == positions[spear][0] and index(1) == positions[fume][0]
    assert {index(2), index(3)} == set(positions[dagger])
    assert index(5) == 0xFFFF  # L3 bare fists
    assert index(4) == 0  # R3 kept as it was
    assert block(0x1C, 3) == lo.armor[3][0] - 10000000
    assert [block(0x44, k) for k in range(4)][3] == 0xFFFFFFFF
    assert block(0x54, 0) == 60155000  # Estus Flask kept
    assert block(0x54, 1) == lo.belt[1][0]
    assert index(18 + 1) == positions[lo.belt[1][0]][0]
