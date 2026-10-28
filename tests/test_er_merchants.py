"""Elden Ring merchant lineups (data/merchants*.json) and quest step links."""

from __future__ import annotations

from er_save_manager.data.merchants import get_merchants
from er_save_manager.data.quest_locations import quest_steps, quests_for_block
from er_save_manager.data.shop_stock import get_stock
from er_save_manager.data.world_map import location_map_point
from er_save_manager.parser.event_flags import EventFlags


def test_merchant_tables():
    for cnv in (False, True):
        merchants = get_merchants(cnv)
        off = [
            m.name
            for m in merchants
            if location_map_point(m.map_id, m.position[0], m.position[2], cnv) is None
        ]
        assert off == []

        # Every limited row the restock checklist knows is in a lineup with
        # the same counter flag and quantity
        lineup = {
            i.flag_id: i.quantity for m in merchants for i in m.lineup if i.limited
        }
        stock = {r.flag_id: r.quantity for r in get_stock(cnv)}
        assert {f: q for f, q in stock.items() if lineup.get(f) != q} == {}

        flags = [
            f
            for m in merchants
            for i in m.lineup
            for f in (*i.counter_flags, i.release_flag)
            if f
        ]
        assert [f for f in flags if not EventFlags.has_flag(f)] == []


def test_counter_changes():
    item = next(i for m in get_merchants() for i in m.lineup if i.quantity == 5)
    sold = item.counter_changes(5)
    assert [sold[f] for f in item.counter_flags] == [True, False, True]
    assert not any(item.counter_changes(0).values())


def test_quest_tables_by_block():
    assert quests_for_block(3180) == ("White Mask Varre",)
    assert quests_for_block(4700) == ("Kale",)
    assert quests_for_block(4040) == ("D Hunter of the Dead",)
    assert set(quests_for_block(3380)) == {"Hyetta", "Irina"}
    moving = [s for s in quest_steps(3180) if s.places]
    assert moving and all(p[1].startswith("m") for s in moving for p in s.places)
