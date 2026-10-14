"""Tests for MenuSaveLoad marker records, the map marker editor and world map geometry."""

from __future__ import annotations

import struct
from io import BytesIO

import pytest

from er_save_manager.data.world_map import (
    MAP_LANDS_BETWEEN,
    MAP_REALM_OF_SHADOW,
    MAP_UNDERGROUND,
    global_to_map,
    location_map_point,
    map_to_global,
    tile_map_rect,
)
from er_save_manager.editors.map_markers import (
    BEACON,
    MARKER,
    MapMarkerEditor,
    copy_markers,
)
from er_save_manager.parser import load_save
from er_save_manager.parser.world import MapMarkerRecord, MenuSaveLoad


def _slot_bytes(save, idx):
    slot = save.character_slots[idx]
    return bytes(save._raw_data[slot.data_start : slot.data_start + 0x280000])


def test_menu_save_load_keeps_corrupt_size():
    raw = struct.pack("<HHI", 0, 0, 0x12345678) + bytes(range(256)) * 16 + b"TAIL"
    f = BytesIO(raw)
    block = MenuSaveLoad.read(f)
    assert f.read() == b"TAIL"
    out = BytesIO()
    block.write(out)
    assert out.getvalue() == raw[: 8 + 0x1000]


def test_marker_record_round_trip():
    rec = MapMarkerRecord(7, 1234.5, 678.25, 10, 3, 0)
    assert MapMarkerRecord.unpack(rec.pack(), 0) == rec
    assert MapMarkerRecord().pack() == bytes.fromhex(
        "ffffffff" + "00" * 9 + "01" + "0000"
    )


def test_fixture_marker_layout(sanitized_save):
    for i in range(10):
        slot = sanitized_save.get_slot(i)
        if not slot.version:
            continue
        block = slot.menu_profile_save_load
        assert block.has_marker_layout
        assert len(block.records(True)) == 10
        assert len(block.records(False)) == 100


def test_apply_without_changes_is_byte_identical(sanitized_save):
    before = _slot_bytes(sanitized_save, 0)
    editor = MapMarkerEditor(sanitized_save, 0)
    editor.apply()
    assert _slot_bytes(sanitized_save, 0) == before


def test_add_move_delete_apply_and_reparse(sanitized_save, sanitized_save_copy):
    editor = MapMarkerEditor(sanitized_save, 1)
    assert editor.supported
    before = len(editor.markers)
    a = editor.add(4000.0, 5000.0, MAP_LANDS_BETWEEN, icon=4)
    b = editor.add(5000.0, 4000.0, MAP_REALM_OF_SHADOW, icon=2)
    editor.move(b, 5100.0, 4100.0)
    editor.delete(a)
    editor.apply()
    sanitized_save.recalculate_checksums()
    sanitized_save.to_file(str(sanitized_save_copy))

    reloaded = MapMarkerEditor(load_save(str(sanitized_save_copy)), 1)
    assert len(reloaded.markers) == before + 1
    m = next(
        m for m in reloaded.markers if m.map == MAP_REALM_OF_SHADOW and m.icon == 2
    )
    assert (m.x, m.y, m.kind) == (5100.0, 4100.0, MARKER)


def test_delete_empties_record_and_keeps_others_in_place(sanitized_save):
    editor = MapMarkerEditor(sanitized_save, 0)
    first = editor.add(1.0, 2.0, 0)
    second = editor.add(3.0, 4.0, 0)
    editor.apply()
    editor.delete(first)
    editor.apply()
    records = sanitized_save.get_slot(0).menu_profile_save_load.records(False)
    assert records[first.index].is_empty
    assert records[second.index].id == second.id


def test_ids_continue_from_highest(sanitized_save):
    editor = MapMarkerEditor(sanitized_save, 0)
    top = max((m.id for m in editor.markers), default=0)
    assert editor.add(1.0, 1.0, 0).id == top + 1


def test_capacity(sanitized_save):
    editor = MapMarkerEditor(sanitized_save, 0)
    editor.clear()
    for i in range(100):
        assert editor.add(float(i), 0.0, 0) is not None
    assert editor.add(0.0, 0.0, 0) is None
    assert editor.add(0.0, 0.0, 0, kind=BEACON) is not None


def test_clear_filters(sanitized_save):
    editor = MapMarkerEditor(sanitized_save, 0)
    editor.clear()
    editor.add(0.0, 0.0, MAP_LANDS_BETWEEN)
    editor.add(0.0, 0.0, MAP_UNDERGROUND)
    editor.add(0.0, 0.0, MAP_LANDS_BETWEEN, kind=BEACON)
    assert editor.clear(MARKER, MAP_UNDERGROUND) == 1
    assert editor.clear(MARKER) == 1
    assert [m.kind for m in editor.markers] == [BEACON]


def test_export_import_and_copy(sanitized_save, tmp_path):
    src = MapMarkerEditor(sanitized_save, 0)
    src.clear()
    src.add(10.0, 20.0, MAP_LANDS_BETWEEN, icon=5)
    path = tmp_path / "markers.json"
    src.export_file(path)

    dst = MapMarkerEditor(sanitized_save, 2)
    count = len(dst.markers)
    assert dst.import_file(path, replace=False) == (1, 0)
    assert len(dst.markers) == count + 1
    assert dst.import_file(path, replace=True) == (1, 0)
    assert len(dst.markers) == 1

    with pytest.raises(ValueError):
        dst.merge({"markers": []}, replace=False)

    copy_markers(sanitized_save, src.to_dict(), 3, replace=True)
    copied = MapMarkerEditor(sanitized_save, 3).markers
    assert [(m.x, m.y, m.icon) for m in copied] == [(10.0, 20.0, 5)]


def test_world_map_transform():
    assert global_to_map(7168.0, 16640.0) == (0.0, 0.0)
    assert map_to_global(*global_to_map(12000.0, 9000.0)) == (12000.0, 9000.0)
    left, top, right, bottom = tile_map_rect(42, 36)
    assert (right - left, bottom - top) == (256, 256)


def test_location_map_point_layers():
    assert location_map_point("m60_42_36_00", 0.0, 0.0)[0] == MAP_LANDS_BETWEEN
    assert location_map_point("m61_47_41_00", 0.0, 0.0)[0] == MAP_REALM_OF_SHADOW
    point = location_map_point("m12_01_00_00", 0.0, 0.0)
    assert point is not None and point[0] == MAP_UNDERGROUND
    # Leyndell converts to m60 through its conversion rows.
    assert location_map_point("m11_00_00_00", 0.0, 0.0)[0] == MAP_LANDS_BETWEEN
