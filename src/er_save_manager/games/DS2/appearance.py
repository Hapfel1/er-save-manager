"""
DS2 character appearance: the profile's appearance block.

Block layout (offsets from APPEARANCE_OFFSET):
  0x00  eye color, RGB u8
  0x03  hair color, RGB u8
  0x06  eyebrow color, RGB u8
  0x09  beard color, RGB u8
  0x0C  tattoo color, RGBA u8 (alpha 32-255 in the menu)
  0x10  50 s8 FaceGen symmetric shape coefficients
  0x42  30 s8 FaceGen asymmetric shape coefficients
  0x60  50 s8 FaceGen symmetric texture coefficients
  0x92  u8 gender, 0 male, 1 female
  0x94  u8 hairstyle = hair model fg_70NN number
  0x95  u8 bits 0-3 tattoo (0-11, 15 none), bits 4-6 physique (1, 2),
        bit 7 set
  0x96  u8 eyebrow
  0x98  u8 beard, 255 none
  0x99  u8 build = ChrEditParamBodyScale row (male 0-7, female 20-27)
  rest  not mapped; copies and JSON files carry it unchanged.

The load screen records keep a copy, see DS2Save.sync_appearance_cache.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .save import APPEARANCE_SIZE

if TYPE_CHECKING:
    from .save import Character

JSON_FORMAT = "ds2_appearance"
JSON_VERSION = 1

GENDERS = ["Male", "Female"]  # index = stored value
EYE_COLOR = 0x00
HAIR_COLOR = 0x03
EYEBROW_COLOR = 0x06
BEARD_COLOR = 0x09
TATTOO_COLOR = 0x0C
GENDER = 0x92
HAIRSTYLE = 0x94
TATTOO_PHYSIQUE = 0x95
EYEBROW = 0x96
BEARD = 0x98
BUILD = 0x99
COLORS = (
    ("Hair color", HAIR_COLOR),
    ("Eyebrow color", EYEBROW_COLOR),
    ("Eye color", EYE_COLOR),
    ("Beard color", BEARD_COLOR),
    ("Tattoo color", TATTOO_COLOR),
)
# Hairstyle values per gender: the game's hair models fg_7001-fg_7011 (male)
# and fg_7020-fg_7030 (female) in /model/parts/face.
HAIRSTYLES = {
    0: (1, 2, 3, 4, 5, 6, 7, 8, 9, 11),
    1: (20, 21, 22, 23, 24, 25, 26, 27, 28, 30),
}
# Build values per gender in menu order (left to right, top to bottom).
BUILDS = {
    0: tuple(range(8)),
    1: tuple(range(20, 28)),
}
NO_BEARD = 0xFF
NO_TATTOO = 0xF


@dataclass(frozen=True)
class Part:
    """A creation menu selection stored in bits shift..shift+bits of one byte.
    options maps gender to (label, value) pairs in menu order."""

    label: str
    offset: int
    shift: int
    bits: int
    options: dict[int, tuple[tuple[str, int], ...]]

    def get(self, block: bytes) -> int:
        return (block[self.offset] >> self.shift) & ((1 << self.bits) - 1)

    def set(self, block: bytes, value: int) -> bytes:
        mask = ((1 << self.bits) - 1) << self.shift
        byte = (block[self.offset] & ~mask) | ((value << self.shift) & mask)
        return set_u8(block, self.offset, byte)

    def choices(self, gender: int) -> tuple[tuple[str, int], ...]:
        return self.options.get(gender, ())


def _numbered(name: str, values, extra=()) -> tuple[tuple[str, int], ...]:
    return tuple(extra) + tuple((f"{name} {i + 1}", v) for i, v in enumerate(values))


def _same(choices: tuple[tuple[str, int], ...]) -> dict:
    return {0: choices, 1: choices}


PARTS = (
    Part(
        "Build",
        BUILD,
        0,
        8,
        {g: _numbered("Build", v) for g, v in BUILDS.items()},
    ),
    Part("Physique", TATTOO_PHYSIQUE, 4, 3, _same(_numbered("Physique", (1, 2)))),
    Part(
        "Hairstyle",
        HAIRSTYLE,
        0,
        8,
        {g: _numbered("Hairstyle", v) for g, v in HAIRSTYLES.items()},
    ),
    Part("Eyebrow", EYEBROW, 0, 8, _same(_numbered("Eyebrow", range(10)))),
    Part(
        "Beard",
        BEARD,
        0,
        8,
        _same(_numbered("Beard", range(6), (("None", NO_BEARD),))),
    ),
    Part(
        "Tattoo",
        TATTOO_PHYSIQUE,
        0,
        4,
        _same(_numbered("Tattoo", range(12), (("None", NO_TATTOO),))),
    ),
)


def get_rgb(block: bytes, offset: int) -> tuple[int, int, int]:
    return tuple(block[offset : offset + 3])


def set_rgb(block: bytes, offset: int, rgb) -> bytes:
    out = bytearray(block)
    out[offset : offset + 3] = bytes(max(0, min(255, int(v))) for v in rgb)
    return bytes(out)


def set_u8(block: bytes, offset: int, value: int) -> bytes:
    out = bytearray(block)
    out[offset] = value & 0xFF
    return bytes(out)


def set_gender(block: bytes, gender: int) -> bytes:
    """Block with the other gender; selections with per-gender values
    (build, hairstyle) keep their menu position."""
    current = block[GENDER]
    out = set_u8(block, GENDER, gender)
    if gender == current or current >= len(GENDERS):
        return out
    for part in PARTS:
        values = [v for _label, v in part.choices(current)]
        new = [v for _label, v in part.choices(gender)]
        if values != new and part.get(block) in values:
            out = part.set(out, new[values.index(part.get(block))])
    return out


@dataclass
class Appearance:
    block: bytes

    @classmethod
    def from_character(cls, char: Character) -> Appearance:
        return cls(char.appearance_block)

    def apply_to(self, char: Character) -> None:
        self.validate()
        char.appearance_block = self.block

    def validate(self) -> None:
        if len(self.block) != APPEARANCE_SIZE:
            raise ValueError(f"Appearance block must be {APPEARANCE_SIZE} bytes")
        if self.block[GENDER] not in (0, 1):
            raise ValueError("Gender must be 0 or 1")

    def to_json(self) -> dict:
        return {
            "format": JSON_FORMAT,
            "version": JSON_VERSION,
            "block": self.block.hex(),
        }

    @classmethod
    def from_json(cls, d: dict) -> Appearance:
        if not isinstance(d, dict) or d.get("format") != JSON_FORMAT:
            raise ValueError("Not a Dark Souls II appearance file")
        if d.get("version") != JSON_VERSION:
            raise ValueError(f"Unsupported appearance file version {d.get('version')}")
        try:
            app = cls(bytes.fromhex(d["block"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid appearance file: {exc}") from exc
        app.validate()
        return app
