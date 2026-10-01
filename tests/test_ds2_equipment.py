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

    equipped = equip_build(character, build, {})
    assert equipped.missing == [] and equipped.no_slots == []

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
    # Spells follow the block, index 28 onward; the rest of the list is empty.
    heal = lo.spells[0][0]
    assert [block(0x7C, k) for k in range(2)] == [heal, 0xFFFFFFFF]
    assert index(28) == positions[heal][0] and index(29) == 0xFFFF


AFFINITY = 34040000
HEAL = 32010000


class _Regulation:
    """Attunement 13 gives 2 slots, Affinity takes 3, every
    other spell 1."""

    def attunement_slots(self, attunement):
        return {13: 2}.get(attunement, 0)

    def spell_slots(self, item_id):
        return 3 if item_id == AFFINITY else 1

    def allowed_infusions(self, item_id):
        return (0,)

    def max_held(self, item_id):
        return 10

    def max_upgrade(self, item_id, category):
        return 0

    def durability(self, item_id):
        return None


def _spell_import(ring: str):
    """Import a build attuning Affinity then Heal twice, with
    attunement 13 and the given ring, into an empty character."""
    from er_save_manager.games.DS2.save import EQUIPMENT_INDEX_OFFSET
    from er_save_manager.games.DS2.soulsplanner import (
        apply_items,
        equip_build,
        parse_build_html,
    )

    page = (
        "<script>savedBuild={class_:'sorcerer',armor:'Naked;Naked;Naked;Naked',"
        f"weapons:'',rings:'{ring}',"
        "spells:'Affinity;Heal;Heal',items:'',vigor:10,"
        "endurance:10,vitality:10,attunement:13,strength:10,dexterity:10,"
        "adaptability:10,intelligence:10,faith:10};</script>"
    )
    build = parse_build_html(page, "1")
    data = bytearray(EQUIPMENT_INDEX_OFFSET + 0x80)
    data[:INVENTORY_START] = _character().raw()
    character = Character(data, regulation_source=_Regulation)
    character.set_stat("attunement", 13)
    apply_items(character, build.items, {}, {})
    equipped = equip_build(character, build, {})
    spells = [
        struct.unpack_from("<I", data, EQUIPMENT_OFFSET + 0x7C + 4 * k)[0]
        for k in range(3)
    ]
    heal_copies = [e for e in character.inventory() if e.item_id == HEAL]
    return equipped, spells, heal_copies, data


def test_duplicate_spell_spawns_and_attunes_each_copy():
    from er_save_manager.games.DS2.save import EQUIPMENT_INDEX_OFFSET

    equipped, spells, heal_copies, data = _spell_import("No_Ring")
    # 2 slots: the 3-slot spell is skipped, both Heals still fit.
    assert equipped.no_slots == ["Affinity"]
    assert spells == [HEAL, HEAL, 0xFFFFFFFF]
    assert len(heal_copies) == 2
    positions = {
        struct.unpack_from("<H", data, EQUIPMENT_INDEX_OFFSET + 2 * (28 + k))[0]
        for k in range(2)
    }
    assert positions == {(e.offset - INVENTORY_START) // 16 for e in heal_copies}


def test_ring_slots_count_toward_attunement():
    equipped, spells, _, _ = _spell_import("Southern_Ritual_Band")
    # 2 slots + 1 from the ring: the 3-slot spell fits and fills them.
    assert equipped.no_slots == ["Heal", "Heal"]
    assert spells == [AFFINITY, 0xFFFFFFFF, 0xFFFFFFFF]


def test_attuned_spell_counts_as_equipped():
    character = _character()
    struct.pack_into("<I", character.raw(), EQUIPMENT_OFFSET + 0x7C, HEAL)
    assert HEAL in character.equipped_item_ids()


def test_owned_copies_only_cover_their_share():
    from er_save_manager.games.DS2.save import EQUIPMENT_INDEX_OFFSET, InventoryItem
    from er_save_manager.games.DS2.soulsplanner import (
        owned_items,
        parse_build_html,
        without_owned,
    )

    page = (
        "<script>savedBuild={class_:'sorcerer',armor:'',weapons:'',rings:'',"
        "spells:'Heal;Heal;Affinity',items:'Lifegem;Lifegem',vigor:10,"
        "endurance:10,vitality:10,attunement:13,strength:10,dexterity:10,"
        "adaptability:10,intelligence:10,faith:10};</script>"
    )
    build = parse_build_html(page, "1")
    data = bytearray(EQUIPMENT_INDEX_OFFSET + 0x80)
    character = Character(data, regulation_source=_Regulation)
    lifegem = next(i.item_id for i in build.items if i.name == "Lifegem")
    # One Heal carried, one Heal in the item box, which cannot be attuned.
    for pos, item_id, in_box in (
        (3, HEAL, False),
        (4, HEAL, True),
        (5, lifegem, False),
    ):
        entry = InventoryItem(INVENTORY_START + 16 * pos, item_id, 0, 1, 0)
        entry.in_box = in_box
        character.write_inventory_slot(entry)

    owned = owned_items(character, build.items)
    assert {item.name: count for item, count in owned} == {"Heal": 1, "Lifegem": 2}
    left = {item.name: item.count for item in without_owned(build.items, owned)}
    assert left == {"Heal": 1, "Affinity": 1}
    assert next(i for i in build.items if i.name == "Heal").count == 2
