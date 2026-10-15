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
    """Killing Crestfallen Warrior moves its state from 1460 to 1462 (one
    byte, bit 3 to bit 1), and a pickup sets item lot flag 51020000 (top bit
    of its word's high byte)."""
    from er_save_manager.games.DSR.save import (
        FLAG_RECORD_TO_BASE,
        FLAG_SEARCH_START,
    )

    char = _character()
    char._data.extend(bytes(0x40000 - len(char._data)))
    record = FLAG_SEARCH_START + 0x300
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


def test_bonfire_record_lighting():
    """Lighting a bonfire (the Undead Asylum cell one) sets its record's
    kindle value from 0 to 10; kindled values are kept when lighting."""
    char = _character()
    char._data.extend(bytes(0x40000 - len(char._data)))
    rec = 0x36000
    struct.pack_into("<III", char._data, rec, 0x0B, 1811960, 0)
    struct.pack_into("<III", char._data, rec + 20, 0x0B, 1021960, 20)
    assert char.bonfire_level(1811960) == 0
    assert char.set_bonfire_lit(1811960, True)
    assert char.bonfire_level(1811960) == 10
    assert char.set_bonfire_lit(1021960, True) and char.bonfire_level(1021960) == 20
    assert char.set_bonfire_lit(1021960, False) and char.bonfire_level(1021960) == 0
    assert char.bonfire_level(1501961) is None
    assert not char.set_bonfire_lit(1501961, True)


def _flag_character() -> tuple[DSRCharacter, int]:
    from er_save_manager.games.DSR.save import FLAG_RECORD_TO_BASE, FLAG_SEARCH_START

    char = _character()
    char._data.extend(bytes(0x40000 - len(char._data)))
    record = FLAG_SEARCH_START + 0x1000
    char._data[record : record + 10] = bytes.fromhex("ffffffff123456000008")
    return char, record + FLAG_RECORD_TO_BASE


def test_ng_cycle_sits_before_the_flag_array():
    from er_save_manager.games.DSR.save import NG_CYCLE_FROM_FLAGS

    char, base = _flag_character()
    struct.pack_into("<II", char._data, base - NG_CYCLE_FROM_FLAGS, 2, 2)
    assert char.ng_plus == 2
    char.ng_plus = 3
    assert struct.unpack_from("<II", char._data, base - NG_CYCLE_FROM_FLAGS) == (3, 2)


def test_play_time_and_hp_fields():
    from er_save_manager.games.DSR.save import (
        OFF_HP_BASE,
        OFF_HP_CURRENT,
        OFF_HP_MAX,
        OFF_PLAY_MS,
    )

    char = _character()
    struct.pack_into("<I", char._data, OFF_PLAY_MS, 41_135_500)
    assert char.play_seconds == 41_135.5
    char.set_stat("vit", 30)
    for off in (OFF_HP_BASE, OFF_HP_MAX, OFF_HP_CURRENT):
        assert struct.unpack_from("<I", char._data, off)[0] == 1100


def test_covenant_offerings_and_rank():
    from er_save_manager.games.DSR.save import (
        OFF_COVENANT_OFFERINGS,
        DSRCovenant,
        covenant_rank,
    )

    char = _character()
    char.set_covenant_offerings(DSRCovenant.ChaosServant, 30)
    assert char._data[OFF_COVENANT_OFFERINGS + 6] == 30
    assert char.covenant_offerings(DSRCovenant.ChaosServant) == 30
    assert [covenant_rank(n) for n in (0, 9, 10, 29, 30, 79, 80, 255)] == [
        0, 0, 1, 1, 2, 2, 3, 3,
    ]  # fmt: skip


def test_npc_and_boss_data():
    import json
    from pathlib import Path

    data = Path(catalog.__file__).parent / "data"
    npcs = json.loads((data / "npcs.json").read_text(encoding="utf-8"))
    assert len({n["name"] for n in npcs}) == len(npcs)
    for npc in npcs:
        for flag in npc["dead"] + npc["hostile"]:
            assert npc["lo"] < flag <= npc["hi"], npc["name"]
    # Killing Crestfallen Warrior (save pair) finished his m10_02 hostility
    # and death event instances (11020510 / 11020530, slot 10).
    crestfallen = next(n for n in npcs if n["lo"] == 1460)
    assert {11020520, 11020540} <= set(crestfallen["revive_clear"])
    assert [10, 2, 8] in crestfallen["parts"]
    bosses = json.loads((data / "dsr_named_flags.json").read_text(encoding="utf-8"))
    ids = {b["id"] for b in bosses["boss_kills"]}
    # Defeat flags of the boss reward event (common.emevd event 970), with
    # Ornstein and Smough as their shared flag 12.
    assert ids == {
        2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17,
        11010901, 11010902, 11200900, 11210000, 11210001, 11210004,
        11410410, 11410900, 11410901, 11510900, 11810900,
    }  # fmt: skip


def _with_chr(char: DSRCharacter, base: int) -> int:
    """CHR block after the flag array with m10_02 (41 parts) and m10_01
    (174 parts); returns the m10_02 bit offset."""
    off = base + 0x16000
    struct.pack_into("<I", char._data, off - 4, 0x68)
    char._data[off : off + 8] = b" RHC" + bytes.fromhex("00030810")
    rec = off + 8
    for key, count in ((0x0A020000, 41), (0x0A010000, 174)):
        size = 12 + (count + 7) // 8
        struct.pack_into("<III", char._data, rec, key, size, count)
        rec += size
    struct.pack_into("<I", char._data, rec, 0xFFFFFFFF)
    return off + 8 + 12


def test_revive_clears_spawn_dead_bit_and_extra_flags():
    char, base = _flag_character()
    bits = _with_chr(char, base)
    assert set(char.chr_records()) == {(10, 2), (10, 1)}
    npc = {
        "name": "Crestfallen Warrior",
        "lo": 1460,
        "hi": 1489,
        "dead": [1462],
        "hostile": [1461],
        "parts": [[10, 2, 8], [16, 0, 3]],
        "revive_clear": [11020100],
    }
    char.set_npc_state(npc, alive=False)
    char._data[bits + 1] = 0x01  # what the game writes when he dies
    char.set_flag(11020100, True)
    assert char.part_spawns_dead(10, 2, 8)
    char.set_npc_state(npc, alive=True)
    assert not char.part_spawns_dead(10, 2, 8)
    assert not char.get_flag(11020100)
    assert char.npc_state(npc) == "Alive"


def test_flag_zero_check():
    from types import SimpleNamespace

    from er_save_manager.games.save_check import _dsr_flag0_set

    char, _base = _flag_character()
    save = SimpleNamespace(characters=[char, None])
    assert _dsr_flag0_set(save) == []
    char.set_flag(0, True)
    assert _dsr_flag0_set(save) == [0]
