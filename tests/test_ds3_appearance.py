"""DS3 appearance block, menu data and JSON files."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from er_save_manager.games.DS3 import appearance as A
from er_save_manager.games.DS3.character_ops import (
    DIR_BASE,
    DIR_FACE_OFFSET,
    DIR_STRIDE,
    _sync_dir_face,
)
from er_save_manager.games.DS3.slot import DS3Slot, LayoutError

FIXTURE = Path(__file__).parent / "fixtures" / "DS3_slot0_sanitized.bin.zip"
FACE_SIZE = 0xF4


@pytest.fixture(scope="module")
def slot_bytes() -> bytes:
    with zipfile.ZipFile(FIXTURE) as zf:
        return zf.read("DS3_slot0_sanitized.bin")


@pytest.fixture
def slot(slot_bytes) -> DS3Slot:
    return DS3Slot(0, bytearray(slot_bytes))


def test_reads_block_and_body_type(slot):
    face = slot.face_block
    assert len(face) == FACE_SIZE
    assert face[:4] == b"FACE"
    assert slot.body_type == 1


def test_fixture_face_is_the_commoner_template(slot):
    # A fresh character keeps its base template's sliders and skin color.
    face = slot.face_block
    assert A.template_names(1)[0] == "Commoner"
    assert A.apply_template(face, 1, 0) == face


def test_template_changes_only_sliders_and_skin(slot):
    face = slot.face_block
    new = A.apply_template(face, 1, 5)
    changed = {i for i in range(len(face)) if face[i] != new[i]}
    assert changed
    assert all(0x30 <= i < 0x33 or 0x72 <= i < 0xF1 for i in changed)


def test_slider_offsets_are_unique_and_inside_the_block():
    seen = set()
    for group in A.slider_groups():
        for slider in group.sliders:
            for off in slider.offsets:
                assert 0x54 <= off < 0xF1
                assert off not in seen
                seen.add(off)
    assert len(A.slider_groups()) == 16


def test_arms_and_legs_set_both_sides(slot):
    build = A.group("Build Detail")
    arms = next(s for s in build.sliders if s.label == "Arms")
    face = A.set_u8(slot.face_block, arms.offsets, 40)
    assert [face[o] for o in arms.offsets] == [40, 40]
    assert len(arms.offsets) == 2


def test_every_part_option_has_an_icon():
    for part in A.parts():
        assert part.options
        for opt in part.options:
            img = A.icon_image(opt.icon)
            assert img is not None and img.size == (64, 64)


def test_part_and_color_round_trip(slot):
    hair = A.parts()[0]
    face = A.set_part(slot.face_block, hair, 106)
    face = A.set_rgb(face, hair.color_offset, (1, 2, 300))
    assert A.get_part(face, hair) == 106
    assert A.get_rgb(face, hair.color_offset) == (1, 2, 255)
    assert face[hair.color_offset + 3] == slot.face_block[hair.color_offset + 3]


def test_apply_writes_block_and_body_type(slot):
    eyes = A.group("Eyes").sliders[1]
    face = A.set_u8(slot.face_block, eyes.offsets, 250)
    A.Appearance(0, face).apply_to(slot)
    assert slot.face_block == face
    assert slot.body_type == 0


def test_apply_refuses_bad_blocks(slot):
    face = slot.face_block
    with pytest.raises(ValueError):
        A.Appearance(1, face[:-1]).apply_to(slot)
    with pytest.raises(ValueError):
        A.Appearance(1, b"EACF" + face[4:]).apply_to(slot)
    with pytest.raises(ValueError):
        A.Appearance(2, face).apply_to(slot)


def test_second_header_in_player_data_is_refused(slot, slot_bytes):
    off, size = slot._face_span()
    data = bytearray(slot_bytes)
    data[off + size : off + size + 12] = data[off : off + 12]
    with pytest.raises(LayoutError):
        _ = DS3Slot(0, data).face_block


def test_json_round_trip(slot):
    app = A.Appearance.from_character(slot)
    assert A.Appearance.from_json(app.to_json()) == app
    with pytest.raises(ValueError):
        A.Appearance.from_json({"format": "dsr_appearance", "version": 1})


class _Parser:
    def __init__(self, entry10: bytearray) -> None:
        self._entry10 = entry10

    def get_slot(self, index: int) -> bytearray:
        assert index == 10
        return self._entry10


class _Save:
    def __init__(self, entry10: bytearray) -> None:
        self._parser = _Parser(entry10)


def test_directory_copy_follows_the_slot(slot):
    face = slot.face_block
    entry10 = bytearray(DIR_BASE + DIR_STRIDE * 10)
    at = DIR_BASE + DIR_STRIDE * 2 + DIR_FACE_OFFSET
    entry10[at : at + len(face)] = face
    new = A.set_u8(face, A.group("Eyes").sliders[0].offsets, 3)
    _sync_dir_face(_Save(entry10), 2, new)
    assert bytes(entry10[at : at + len(new)]) == new


def test_directory_without_block_is_left_alone(slot):
    entry10 = bytearray(DIR_BASE + DIR_STRIDE * 10)
    before = bytes(entry10)
    _sync_dir_face(_Save(entry10), 1, slot.face_block)
    assert bytes(entry10) == before
