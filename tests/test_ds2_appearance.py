"""DS2 appearance block: accessors, gender switch, JSON and load-screen copies."""

from __future__ import annotations

import pytest

from er_save_manager.games.DS2 import appearance as app
from er_save_manager.games.DS2.save import (
    APPEARANCE_OFFSET,
    APPEARANCE_SIZE,
    CHARACTER_SELECT_ENTRY,
    NAME_OFFSET,
    OCCUPANCY_ENTRY,
    PROFILE_ENTRY_START,
    Character,
    DS2Save,
)

# Default male face block of a new character (eye, hair, brow, beard, tattoo
# colors; hairstyle 4).
_DEFAULT_COLORS = bytes.fromhex("4c6580806a55806a55806a55804b6480")


def _block(gender: int = 0, hair: int = 4) -> bytes:
    out = bytearray(APPEARANCE_SIZE)
    out[: len(_DEFAULT_COLORS)] = _DEFAULT_COLORS
    out[app.GENDER] = gender
    out[app.HAIRSTYLE] = hair
    return bytes(out)


def test_block_accessor_round_trip():
    char = Character(bytearray(NAME_OFFSET + 64))
    char.appearance_block = _block(hair=7)
    assert char.appearance_block == _block(hair=7)
    data = char._data
    assert data[APPEARANCE_OFFSET + app.HAIRSTYLE] == 7
    with pytest.raises(ValueError):
        char.appearance_block = b"\x00" * (APPEARANCE_SIZE - 1)


def test_colors():
    block = _block()
    assert app.get_rgb(block, app.HAIR_COLOR) == (0x80, 0x6A, 0x55)
    block = app.set_rgb(block, app.HAIR_COLOR, (255, 0, 300))
    assert app.get_rgb(block, app.HAIR_COLOR) == (255, 0, 255)
    assert block[app.TATTOO_COLOR + 3] == 0x80  # tattoo alpha kept


def test_gender_keeps_hairstyle_and_build_position():
    female = app.set_gender(app.set_u8(_block(hair=4), app.BUILD, 7), 1)
    assert (female[app.GENDER], female[app.HAIRSTYLE], female[app.BUILD]) == (1, 23, 27)
    male = app.set_gender(female, 0)
    assert (male[app.HAIRSTYLE], male[app.BUILD]) == (4, 7)
    # A value outside the known lists is left as it is
    assert app.set_gender(_block(hair=127), 1)[app.HAIRSTYLE] == 127


def _part(label: str) -> app.Part:
    return next(p for p in app.PARTS if p.label == label)


def test_part_bytes():
    # Tattoo and physique share a byte
    tattoo, physique = _part("Tattoo"), _part("Physique")
    block = app.set_u8(_block(), app.TATTOO_PHYSIQUE, 0xA4)
    assert (tattoo.get(block), physique.get(block)) == (4, 2)
    block = tattoo.set(block, app.NO_TATTOO)
    assert block[app.TATTOO_PHYSIQUE] == 0xAF
    block = physique.set(block, 1)
    assert block[app.TATTOO_PHYSIQUE] == 0x9F

    block = _part("Beard").set(_block(), 3)
    block = _part("Eyebrow").set(block, 9)
    assert (block[app.BEARD], block[app.EYEBROW]) == (3, 9)
    assert _part("Beard").choices(1)[0] == ("None", app.NO_BEARD)


def test_json_round_trip():
    a = app.Appearance(_block(gender=1, hair=22))
    assert app.Appearance.from_json(a.to_json()) == a
    with pytest.raises(ValueError):
        app.Appearance.from_json({"format": "dsr_appearance", "version": 1})
    with pytest.raises(ValueError):
        app.Appearance.from_json(app.Appearance(_block(gender=2)).to_json())


class _Container:
    def __init__(self) -> None:
        self.entries = {i: bytearray(0x2000) for i in range(CHARACTER_SELECT_ENTRY + 1)}

    def get_entry(self, index: int) -> bytearray:
        return self.entries[index]


def test_cache_sync_writes_both_records():
    container = _Container()
    save = DS2Save(container)
    block = _block(gender=1, hair=25)
    save.characters[3].appearance_block = block
    save.sync_appearance_cache(3)
    occ = bytes(container.entries[OCCUPANCY_ENTRY])
    select = bytes(container.entries[CHARACTER_SELECT_ENTRY])
    assert occ.count(block) == 1
    assert select.count(block) == 1
    # Other slots untouched
    assert container.entries[PROFILE_ENTRY_START + 2][APPEARANCE_OFFSET] == 0
