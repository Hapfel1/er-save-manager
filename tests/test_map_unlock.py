"""Grace, map piece and play region unlock (editors.map_unlock)."""

from er_save_manager.data.grace_data import grace_region_ids
from er_save_manager.data.locations import get_grace_locations
from er_save_manager.data.map_pieces import MAP_PIECES
from er_save_manager.editors.map_unlock import add_regions, unlock
from er_save_manager.parser import Save
from er_save_manager.parser.event_flags import EventFlags
from er_save_manager.parser.inventory_ops import SLOT_DATA_SIZE


def _first_slot(save):
    return next(i for i, s in enumerate(save.character_slots) if not s.is_empty())


def test_grace_regions_from_play_region_param():
    # PlayRegionParam 6100000 has mapMenuUnlockEventId 76101 (The First Step)
    assert 6100000 in grace_region_ids(76101, convergence=False)
    # Convergence adds region 6102003 for grace 76158
    assert 6102003 not in grace_region_ids(76158, convergence=False)
    assert 6102003 in grace_region_ids(76158, convergence=True)


def test_add_regions_keeps_slot_size_and_other_slots(sanitized_save):
    idx = _first_slot(sanitized_save)
    start = sanitized_save.slot_data_offset(idx)
    before = bytes(sanitized_save._raw_data)
    count = sanitized_save.character_slots[idx].unlocked_regions.count
    new = [999000001, 999000002]
    assert add_regions(sanitized_save, idx, new + new) == 2
    after = bytes(sanitized_save._raw_data)
    assert len(after) == len(before)
    assert after[:start] == before[:start]
    end = start + SLOT_DATA_SIZE
    assert after[end:] == before[end:]
    regions = sanitized_save.character_slots[idx].unlocked_regions
    assert regions.count == count + 2
    assert regions.region_ids[-2:] == new
    assert add_regions(sanitized_save, idx, new) == 0


def test_unlock_round_trip(sanitized_save, sanitized_save_copy):
    idx = _first_slot(sanitized_save)
    graces = [g.flag_id for g in get_grace_locations()]
    pieces = [p.flag_id for p in MAP_PIECES]
    unlock(sanitized_save, idx, graces, pieces)
    sanitized_save.recalculate_checksums()
    sanitized_save.to_file(sanitized_save_copy)

    reloaded = Save.from_file(str(sanitized_save_copy))
    slot = reloaded.character_slots[idx]
    for flag_id in graces + pieces:
        assert EventFlags.get_flag(slot.event_flags, flag_id)
    wanted = {r for f in graces for r in grace_region_ids(f, convergence=False)}
    assert wanted <= set(slot.unlocked_regions.region_ids)
    assert slot.unlocked_regions.count == len(slot.unlocked_regions.region_ids)
