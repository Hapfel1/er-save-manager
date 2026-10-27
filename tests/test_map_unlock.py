"""Grace, map piece and play region unlock (editors.map_unlock)."""

import struct

from er_save_manager.data.grace_data import grace_region_ids
from er_save_manager.data.locations import get_grace_locations
from er_save_manager.data.map_pieces import MAP_PIECES
from er_save_manager.editors.map_unlock import add_regions, set_regions, unlock
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


def test_set_regions_moves_only_the_list(sanitized_save):
    idx = _first_slot(sanitized_save)
    slot = sanitized_save.character_slots[idx]
    start = slot.data_start
    ids = list(slot.unlocked_regions.region_ids)
    list_start = slot.horse_offset - 4 * len(ids) - 4
    before = bytes(sanitized_save._raw_data)
    after_list = before[slot.horse_offset : start + SLOT_DATA_SIZE]

    kept = ids[1:]
    set_regions(sanitized_save, idx, kept)
    after = bytes(sanitized_save._raw_data)
    assert len(after) == len(before)
    assert after[:list_start] == before[:list_start]
    assert after[start + SLOT_DATA_SIZE :] == before[start + SLOT_DATA_SIZE :]
    moved = slot.horse_offset - 4
    assert after[moved : moved + len(after_list)] == after_list
    assert after[start + SLOT_DATA_SIZE - 4 : start + SLOT_DATA_SIZE] == bytes(4)
    regions = sanitized_save.character_slots[idx].unlocked_regions
    assert regions.region_ids == kept and regions.count == len(kept)

    set_regions(sanitized_save, idx, ids)
    assert (
        bytes(sanitized_save._raw_data)[: start + SLOT_DATA_SIZE - 4]
        == (before[: start + SLOT_DATA_SIZE - 4])
    )


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


def test_unlock_pieces_only_leaves_graces_and_regions(sanitized_save):
    idx = _first_slot(sanitized_save)
    slot = sanitized_save.character_slots[idx]
    graces = [g.flag_id for g in get_grace_locations()]
    before = {f: EventFlags.get_flag(slot.event_flags, f) for f in graces}
    regions = list(slot.unlocked_regions.region_ids)
    result = unlock(sanitized_save, idx, piece_flags=[62010, 62020])
    assert result.graces == 0
    assert result.regions == 0
    slot = sanitized_save.character_slots[idx]
    assert EventFlags.get_flag(slot.event_flags, 62010)
    assert EventFlags.get_flag(slot.event_flags, 62020)
    assert {f: EventFlags.get_flag(slot.event_flags, f) for f in graces} == before
    assert slot.unlocked_regions.region_ids == regions


def test_underground_pieces_extend_lands_between_area():
    from er_save_manager.editors.map_unlock import _set_bounds

    ug = next(p for p in MAP_PIECES if p.map_no == 1)
    flags = bytearray(EventFlags.EVENT_FLAGS_SIZE)
    EventFlags.set_flag(flags, ug.flag_id, True)
    data = bytearray(0x1000)
    _set_bounds(data, bytes(flags))
    assert struct.unpack_from("<4fI", data, 0x08) == (*ug.rect, 1)


def test_grace_piece_splits_overlapping_underground_pieces():
    from er_save_manager.data.map_pieces import grace_piece

    # Ainsel River Downstream lies in the Ainsel River, Lake of Rot and
    # Deeproot Depths rectangles; it belongs to Ainsel River (62060).
    downstream = next(
        g for g in get_grace_locations() if g.name.endswith("Ainsel River Downstream")
    )
    assert grace_piece(downstream.flag_id) == 62060
    shoreside = next(
        g for g in get_grace_locations() if g.name.endswith("Lake of Rot Shoreside")
    )
    assert grace_piece(shoreside.flag_id) == 62061


def test_progress_overlay_shades_only_locked_pieces():
    from pathlib import Path

    from PIL import ImageChops

    from er_save_manager.ui.map_view import _MapImages

    maps = Path(__file__).parent.parent / "src" / "resources" / "maps"
    images = _MapImages(maps)
    flags = images.progress_flags(1)
    assert set(flags) == {p.flag_id for p in MAP_PIECES if p.map_no == 1 and p.fragment}
    plain = images.levels(1)[0].copy()
    shaded = images.levels(1, frozenset({62060}))[0]
    box = ImageChops.difference(plain, shaded).getbbox()
    assert box is not None
    # Changed pixels stay within Ainsel River's rectangle plus one map tile
    # (its art runs past the travel area) and the edge blur
    left, top, right, bottom = next(p.rect for p in MAP_PIECES if p.flag_id == 62060)
    margin = 256 * images.scale + 16
    s = images.scale
    assert box[0] >= left * s - margin and box[2] <= right * s + margin
    assert box[1] >= top * s - margin and box[3] <= bottom * s + margin
