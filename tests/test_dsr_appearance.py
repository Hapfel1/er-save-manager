"""DSR appearance: accessors, FaceGen controls, presets, JSON and load-screen sync."""

from __future__ import annotations

import struct

import pytest

from er_save_manager.games.DSR import appearance as app
from er_save_manager.games.DSR.character_ops import (
    _DIR_EMPTY_TEMPLATE,
    DIR_EYE_RGBA_OFFSET,
    DIR_FACE_DATA_OFFSET,
    DIR_HAIR_ITEM_OFFSET,
    DIR_HAIR_RGBA_OFFSET,
    _dir_entry_offset,
    _sync_dir_appearance,
)
from er_save_manager.games.DSR.save import (
    FACE_DATA_SIZE,
    OFF_FACE_DATA,
    SLOT_DATA_SIZE,
    DSRCharacter,
    DSRSave,
)


def _character() -> DSRCharacter:
    char = DSRCharacter(slot_index=0, _data=bytearray(OFF_FACE_DATA + 0x100))
    char.hair_item_id = 1000
    char.body_type = 1
    char.hair_rgba = (60 / 255, 60 / 255, 50 / 255, 1.0)
    char.eye_rgba = (127 / 255, 165 / 255, 178 / 255, 1.0)
    char.face_data = app.face_preset(1, 0)
    return char


def test_accessors_round_trip():
    char = _character()
    char.physique, char.face_type, char.hair_type, char.color_preset = 8, 9, 3, 4
    assert (char.physique, char.face_type, char.hair_type, char.color_preset) == (
        8,
        9,
        3,
        4,
    )
    assert char.face_data == app.face_preset(1, 0)
    with pytest.raises(ValueError):
        char.face_data = b"\x00" * (FACE_DATA_SIZE - 1)


def test_game_tables():
    assert len(app.shape_controls()) == 63  # age, gender, 61 geometry
    assert len(app.skin_controls()) == 36
    assert len(app.physique_names()) == app.PHYSIQUE_COUNT
    for body in (0, 1):
        assert len(app.face_names(body)) == app.TYPE_COUNT
        assert len(app.hair_names(body)) == app.TYPE_COUNT
    assert app.color_preset_rgb(0) == (60, 60, 50)
    assert app.color_preset_rgb(9) == (250, 100, 60)
    assert app.face_names(1)[0] == "Commoner"
    assert app.face_names(0)[2] == "Astora Royalty"


def test_face_bytes_round_trip_through_coefficients():
    face = bytes(range(0, 200, 2))
    assert app.coeffs_to_face(app.face_to_coeffs(face)) == face


def test_control_reaches_target_and_keeps_other_block():
    coeffs = app.face_to_coeffs(app.face_preset(1, 4))
    shape = app.shape_controls()[5]
    moved = shape.apply(coeffs, shape.value(coeffs) + 40)
    assert shape.value(moved) == pytest.approx(shape.value(coeffs) + 40)
    assert moved[app.GEO_SIZE :] == coeffs[app.GEO_SIZE :]

    skin = app.skin_controls()[0]
    moved = skin.apply(coeffs, skin.value(coeffs) - 25)
    assert skin.value(moved) == pytest.approx(skin.value(coeffs) - 25)
    assert moved[: app.GEO_SIZE] == coeffs[: app.GEO_SIZE]


def test_named_controls_share_the_slider_range():
    mean = app.face_to_coeffs(bytes([128]) * FACE_DATA_SIZE)
    for ctl in app.shape_controls()[2:] + app.skin_controls():
        assert ctl.slider_range(mean) == app.CONTROL_RANGE
    # A face beyond the range widens its own slider so it stays representable
    eye = next(c for c in app.shape_controls() if c.label == "small / large")
    far = eye.apply(mean, -2 * app.CONTROL_RANGE)
    assert eye.slider_range(far) == pytest.approx(2 * app.CONTROL_RANGE)


def test_age_moves_both_blocks():
    coeffs = app.face_to_coeffs(app.face_preset(0, 1))
    age = app.shape_controls()[0]
    moved = age.apply(coeffs, age.value(coeffs) + 30)
    assert moved[: app.GEO_SIZE] != coeffs[: app.GEO_SIZE]
    assert moved[app.GEO_SIZE :] != coeffs[app.GEO_SIZE :]


def test_bytes_clamp():
    assert (
        app.coeffs_to_face([500.0] * 50 + [-500.0] * 50) == b"\xff" * 50 + b"\x00" * 50
    )


def test_json_round_trip_and_apply():
    src = _character()
    src.physique, src.face_type, src.hair_type, src.color_preset = 2, 5, 6, 7
    data = app.Appearance.from_character(src).to_json()
    loaded = app.Appearance.from_json(data)
    dst = _character()
    loaded.apply_to(dst)
    assert app.Appearance.from_character(dst) == app.Appearance.from_character(src)


@pytest.mark.parametrize(
    "field,value",
    [
        ("format", "er_appearance"),
        ("version", 2),
        ("physique", 9),
        ("face_type", 10),
        ("body_type", 2),
        ("hair_rgba", [0.5, 0.5, 1.5, 1.0]),
        ("face_data", "00"),
    ],
)
def test_json_rejects_bad_values(field, value):
    data = app.Appearance.from_character(_character()).to_json()
    data[field] = value
    with pytest.raises(ValueError):
        app.Appearance.from_json(data)


def _save_with(char: DSRCharacter, entry: bytes) -> DSRSave:
    system = bytearray(SLOT_DATA_SIZE)
    off = _dir_entry_offset(char.slot_index)
    system[off : off + len(entry)] = entry
    return DSRSave(characters=[char], system_data=system)


def test_dir_sync_writes_colors_and_face():
    char = _character()
    char.slot_index = 3
    entry = bytearray(_DIR_EMPTY_TEMPLATE)
    entry[0x28:0x2A] = b"K\x00"  # a real entry, not the empty template
    save = _save_with(char, bytes(entry))
    _sync_dir_appearance(save, 3, char)
    off = _dir_entry_offset(3)
    got = save.system_data[off : off + len(entry)]
    assert struct.unpack_from("<4f", got, DIR_HAIR_RGBA_OFFSET) == pytest.approx(
        char.hair_rgba
    )
    assert struct.unpack_from("<4f", got, DIR_EYE_RGBA_OFFSET) == pytest.approx(
        char.eye_rgba
    )
    assert (
        bytes(got[DIR_FACE_DATA_OFFSET : DIR_FACE_DATA_OFFSET + 100]) == char.face_data
    )
    assert struct.unpack_from("<I", got, DIR_HAIR_ITEM_OFFSET)[0] == 1000


def test_dir_sync_leaves_empty_template():
    char = _character()
    char.slot_index = 3
    save = _save_with(char, _DIR_EMPTY_TEMPLATE)
    _sync_dir_appearance(save, 3, char)
    off = _dir_entry_offset(3)
    assert bytes(save.system_data[off : off + len(_DIR_EMPTY_TEMPLATE)]) == (
        _DIR_EMPTY_TEMPLATE
    )


@pytest.mark.parametrize(
    ("body_type", "hair_type", "item_id"),
    [(1, 0, 1000), (1, 7, 1700), (0, 0, 3000), (0, 7, 3700)],
)
def test_apply_sets_equipped_hair(body_type, hair_type, item_id):
    char = _character()
    a = app.Appearance.from_character(char)
    a.body_type, a.hair_type = body_type, hair_type
    a.apply_to(char)
    assert char.hair_item_id == item_id
