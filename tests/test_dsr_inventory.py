"""DSR item catalog, icons and inventory writes."""

from __future__ import annotations

import struct

from er_save_manager.games.DSR import catalog
from er_save_manager.games.DSR.icon_manager import get_icon
from er_save_manager.games.DSR.save import (
    ITEM_SIZE,
    KEY_ITEM_SLOTS,
    MAX_INVENTORY_SLOTS,
    OFF_EQ_ID_RH1,
    OFF_EQ_RH1,
    OFF_INVENTORY,
    ORDER_SORT_SHIFT,
    DSRCharacter,
)


def _character() -> DSRCharacter:
    data = bytearray(OFF_INVENTORY + MAX_INVENTORY_SLOTS * ITEM_SIZE + 0x100)
    for slot in range(MAX_INVENTORY_SLOTS):
        off = OFF_INVENTORY + slot * ITEM_SIZE
        data[off : off + ITEM_SIZE] = b"\xff" * ITEM_SIZE
        struct.pack_into("<I", data, off + 16, 0)
    return DSRCharacter(slot_index=0, _data=data)


def _by_name(name: str) -> dict:
    return next(i for i in catalog.items() if i["name"] == name)


def test_every_listed_item_has_an_icon():
    missing = [i["name"] for i in catalog.items() if get_icon(i["icon_id"]) is None]
    assert not missing, missing[:5]


def test_weapon_ids_levels_and_infusions():
    fire = _by_name("Fire Longsword")
    assert fire["id"] == 201800 and fire["max_upgrade"] == 10
    assert catalog.lookup(0, 201805) == (fire, 5)
    assert catalog.display_name(0, 201805) == "Fire Longsword +5"
    labels = [v["infusion"] for v in catalog.infusion_variants(_by_name("Longsword"))]
    assert labels[0] == "Normal" and "Chaos" in labels
    flame = _by_name("Pyromancy Flame")
    assert flame["level_step"] == 100 and catalog.item_id_at(flame, 5) == 1330500


def test_seamless_goods_and_estus():
    blossom = next(i for i in catalog.items() if i["id"] == 389007)
    assert blossom["seamless"] and blossom["max_quantity"] == 5
    assert catalog.is_single(_by_name("Estus Flask"))


def test_add_item_writes_sort_key_and_key_slots():
    char = _character()
    fire = _by_name("Fire Longsword")
    slot = char.add_item(
        0,
        catalog.item_id_at(fire, 5),
        sort_key=catalog.sort_key(fire, 5),
        durability=fire["durability"],
    )
    assert slot >= KEY_ITEM_SLOTS
    item = char.read_item(slot)
    assert item.order == (fire["sort_id"] * 100 + 5) << ORDER_SORT_SHIFT | slot
    key = next(i for i in catalog.items() if i["key_item"])
    assert char.add_item(4, key["id"], key_item=True) < KEY_ITEM_SLOTS


def test_set_item_id_updates_equipped_cache():
    char = _character()
    slot = char.add_item(0, 201000, sort_key=11100, durability=200)
    struct.pack_into("<I", char._data, OFF_EQ_RH1, slot)
    struct.pack_into("<I", char._data, OFF_EQ_ID_RH1, 201000)
    char.set_item_id(slot, 201003)
    assert struct.unpack_from("<I", char._data, OFF_EQ_ID_RH1)[0] == 201003
    assert slot in char.equipped_slots()


def test_event_flag_layout_matches_save_pairs():
    """Positions from real before/after saves: killing Crestfallen Warrior
    moved its state from 1460 to 1462 (one byte, bit 3 to bit 1), and a
    pickup set item lot flag 51020000 (top bit of its word's high byte)."""
    from er_save_manager.games.DSR.save import (
        FLAG_RECORD_TO_BASE,
        NG_PLUS_OFFSET,
    )

    char = _character()
    char._data.extend(bytes(0x40000 - len(char._data)))
    record = NG_PLUS_OFFSET + 0x300
    char._data[record : record + 10] = bytes.fromhex("ffffffff123456000008")
    base = record + FLAG_RECORD_TO_BASE
    assert char.flag_base() == base
    char.set_flag(1460, True)
    assert char._data[base + 186] == 0x08
    char.set_flag(1460, False)
    char.set_flag(1462, True)
    assert char._data[base + 186] == 0x02
    char.set_flag(51020000, True)
    assert char._data[base + 0x5F00 + 3 * 0x500 + 3] == 0x80
    npc = {"lo": 1460, "hi": 1489, "dead": [1462], "hostile": [1461]}
    assert char.npc_state(npc) == "Dead"
    char.set_npc_state(npc, alive=True)
    assert char.npc_state(npc) == "Alive" and char.get_flag(1460)
