"""Tests for chest Auto-refill entries, legendary trophy progress and GaitemGameData layouts."""

from __future__ import annotations

import struct

from er_save_manager.data.legendary_items import TROPHIES, trophy_progress
from er_save_manager.editors.auto_refill import default_on, read_entries, write_entries
from er_save_manager.parser import load_save
from er_save_manager.parser.equipment import TrophyEquipData
from er_save_manager.parser.world import GaitemGameData, GaitemGameDataEntry


def test_defaults():
    # Arrow (default on via EquipParamWeapon), Golden Rune [1] (goods, default off)
    assert default_on(50000000) is True
    assert default_on(0x40000000 | 2900) is False
    assert default_on(0x12345678) is None


def test_read_write_entries(sanitized_save, sanitized_save_copy):
    entries = read_entries(sanitized_save, 1)
    assert entries
    target = entries[0]
    target.on = not target.on
    assert write_entries(sanitized_save, 1, [target]) == 1
    assert write_entries(sanitized_save, 1, [target]) == 0
    sanitized_save.recalculate_checksums()
    sanitized_save.to_file(str(sanitized_save_copy))

    reread = read_entries(load_save(str(sanitized_save_copy)), 1)
    assert reread[0].item_id == target.item_id
    assert reread[0].on == target.on
    assert [(e.item_id, e.on) for e in reread[1:]] == [
        (e.item_id, e.on) for e in entries[1:]
    ]


def test_trophy_progress_bits():
    data = TrophyEquipData(
        legendary_weapons=(1 << 8).to_bytes(16, "little"),
        legendary_goods=(1 | 1 << 7).to_bytes(16, "little"),
        legendary_talismans=bytes(16),
    )
    progress = dict(trophy_progress(data))
    assert [c for _, c in progress["Legendary Armaments"]][-1] is True
    assert progress["Legendary Sorceries and Incantations"][0][1] is True
    assert progress["Legendary Ashen Remains"][0][1] is True
    assert not any(c for _, c in progress["Legendary Talismans"])
    assert sum(len(items) for _, _, _, items in TROPHIES) == 9 + 7 + 6 + 8


def _entries(raw: bytes) -> list[GaitemGameDataEntry]:
    return [
        GaitemGameDataEntry(*struct.unpack_from("<IB3s", raw, i * 8))
        for i in range(len(raw) // 8)
    ]


def test_gaitem_game_data_layouts():
    ids = [0x10, 0x20, 0x30]
    new = b"".join(struct.pack("<IB3x", i, 1) for i in ids) + bytes(8 * 13997)
    g = GaitemGameData(count=3, entries=_entries(new))
    assert g.record_size == 8
    assert g.acquired_item_ids() == ids

    old = b"".join(struct.pack("<IB3xII", i, 1, 3000, 0) for i in ids) + bytes(
        16 * 6997
    )
    g = GaitemGameData(count=3, entries=_entries(old))
    assert g.record_size == 16
    assert g.acquired_item_ids() == ids

    # count inflated over zeroed records
    g = GaitemGameData(count=10, entries=_entries(new))
    assert g.acquired_item_ids() == ids
