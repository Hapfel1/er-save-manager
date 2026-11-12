"""Batch Add limits: excluded goods, world supply caps, held counters, DLC spells."""

from __future__ import annotations

from er_save_manager.data.item_database import get_item_database
from er_save_manager.data.item_supply import remaining_supply
from er_save_manager.parser import inventory_ops
from er_save_manager.parser.event_flags import EventFlags
from er_save_manager.ui.editors.inventory_editor import (
    _SOTE_FLAG,
    _batch_excluded,
    _batch_goods_qty,
    _owns_sote,
    _sync_slot_counters,
)

_GOODS = 0x40000000


def test_batch_goods_limits(sanitized_save):
    db = get_item_database()
    item = lambda i: db.get_item_by_id(_GOODS | i)  # noqa: E731

    assert _batch_excluded(item(1025)) is not None  # Crimson flask +12
    assert _batch_excluded(item(8148)) is not None  # Unpowered Great Rune
    assert _batch_excluded(item(191)) is None

    fresh = sanitized_save.character_slots[6]  # NG, 4 flask charges, no seeds
    assert _batch_goods_qty(fresh, item(10010), "held", 99, 99, False) == (None, 43)
    assert _batch_goods_qty(fresh, item(10010), "held", 99, 99, True) == (None, 99)

    blessed = sanitized_save.character_slots[1]  # Scadutree Blessing 20
    assert remaining_supply(blessed, 2010000) == 0
    blessed.player_game_data.scadutree_blessing = 9
    assert remaining_supply(blessed, 2010000) == 50 - 17
    assert remaining_supply(blessed, 1001) is None


def test_memory_stone_count_follows_held_stack(sanitized_save):
    slot = sanitized_save.character_slots[6]
    inventory_ops.add_item(sanitized_save, 6, _GOODS | 10030, 3)
    _sync_slot_counters(sanitized_save, 6, _GOODS | 10030)
    assert slot.player_game_data.memory_stone_count == 3


def test_sote_ownership(sanitized_save):
    slot = sanitized_save.character_slots[6]
    assert _owns_sote(slot)
    slot.dlc.shadow_of_erdtree = 0
    flags = bytearray(slot.event_flags)
    EventFlags.set_flag(flags, _SOTE_FLAG, False)
    slot.event_flags = flags
    assert not _owns_sote(slot)
