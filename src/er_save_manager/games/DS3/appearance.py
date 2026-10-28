"""
DS3 character appearance: the slot's FACE block, menu sliders, parts and JSON files.

Offsets from the "FACE" magic:
  0x0C  9 x u32 part ids: face, hair, left pupil, right pupil, brow, beard,
        accessory, tattoo/mark, eyelashes
  0x30  9 x RGBA u8 colors, same order (face = base skin color)
  0x54  tattoo/mark position X, position Y, angle, scale (u8 each)
  0x58  body scales: head, chest, abdomen, right arm, right leg, left arm,
        left leg (u8 each)
  0x72  apparent age, facial aesthetic, form emphasis, caricature texture
  0x76  61 FaceGen shape controls, 0xB3 36 skin controls, 0xD7 26 asymmetry
        controls (u8 each)

Bytes 0x72..0xF0 are FaceParam bytes 47..175 in the same order. Every slider
is a u8 from 0 (the menu's left caption) to 255; FaceRangeParam maps it to
the game's internal value. Controls without a menu slider keep their bytes.

data/appearance.json is generated from FaceParam, FaceRangeParam,
CharMakeMenuTopParam, CharMakeMenuListItemParam and the menu text; the
part icons in data/appearance_icons.jpg come from the character creation
icon atlas.
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from .slot import DS3Slot

_DATA_DIR = Path(__file__).parent / "data"
_HEADER = b"FACE"
_HEADER_SIZE = 12
_SKIN_COLOR = 0x30
JSON_FORMAT = "ds3_appearance"
JSON_VERSION = 1
BODY_TYPES = ("Type B", "Type A")  # index = stored body type


@functools.cache
def _data() -> dict:
    return json.loads((_DATA_DIR / "appearance.json").read_text(encoding="utf-8"))


@functools.cache
def _icon_sheet() -> Image.Image:
    return Image.open(_DATA_DIR / "appearance_icons.jpg").convert("RGB")


@dataclass(frozen=True)
class Slider:
    label: str
    min_caption: str
    max_caption: str
    # Every offset gets the same value (arms and legs set both sides).
    offsets: tuple[int, ...]


@dataclass(frozen=True)
class SliderGroup:
    name: str
    sliders: tuple[Slider, ...]


@dataclass(frozen=True)
class PartOption:
    value: int
    icon: int


@dataclass(frozen=True)
class Part:
    name: str
    part_offset: int
    color_offset: int
    options: tuple[PartOption, ...]


@functools.cache
def slider_groups() -> tuple[SliderGroup, ...]:
    return tuple(
        SliderGroup(
            g["name"],
            tuple(
                Slider(s["label"], s["min"], s["max"], tuple(s["offsets"]))
                for s in g["sliders"]
            ),
        )
        for g in _data()["groups"]
    )


def group(name: str) -> SliderGroup:
    return next(g for g in slider_groups() if g.name == name)


@functools.cache
def parts() -> tuple[Part, ...]:
    return tuple(
        Part(
            p["name"],
            p["part"],
            p["color"],
            tuple(PartOption(o["value"], o["icon"]) for o in p["options"]),
        )
        for p in _data()["parts"]
    )


def template_names(body_type: int) -> list[str]:
    return [t["name"] for t in _data()["templates"][str(1 if body_type == 1 else 0)]]


def icon_image(icon: int) -> Image.Image | None:
    pos = _data()["icons"].get(str(icon))
    if pos is None:
        return None
    size = _data()["icon_size"]
    x, y = pos
    return _icon_sheet().crop((x, y, x + size, y + size))


def apply_template(face: bytes, body_type: int, index: int) -> bytes:
    """Face with a base template's sliders and skin color, as picking a face
    preset in character creation sets them."""
    t = _data()["templates"][str(1 if body_type == 1 else 0)][index]
    sliders = bytes.fromhex(t["sliders"])
    start = _data()["slider_start"]
    out = bytearray(face)
    out[start : start + len(sliders)] = sliders
    out[_SKIN_COLOR : _SKIN_COLOR + 3] = bytes(t["skin"])
    return bytes(out)


def set_u8(face: bytes, offsets, value: int) -> bytes:
    out = bytearray(face)
    for off in offsets:
        out[off] = max(0, min(255, int(value)))
    return bytes(out)


def get_part(face: bytes, part: Part) -> int:
    return int.from_bytes(face[part.part_offset : part.part_offset + 4], "little")


def set_part(face: bytes, part: Part, value: int) -> bytes:
    out = bytearray(face)
    out[part.part_offset : part.part_offset + 4] = int(value).to_bytes(4, "little")
    return bytes(out)


def get_rgb(face: bytes, offset: int) -> tuple[int, int, int]:
    return tuple(face[offset : offset + 3])


def set_rgb(face: bytes, offset: int, rgb) -> bytes:
    out = bytearray(face)
    out[offset : offset + 3] = bytes(max(0, min(255, int(v))) for v in rgb)
    return bytes(out)


@dataclass
class Appearance:
    body_type: int
    face: bytes

    @classmethod
    def from_character(cls, char: DS3Slot) -> Appearance:
        return cls(body_type=char.body_type, face=char.face_block)

    def apply_to(self, char: DS3Slot) -> None:
        self.validate()
        current = char.face_block
        if len(current) != len(self.face):
            raise ValueError(
                f"Appearance block is {len(self.face)} bytes, the character's is "
                f"{len(current)}"
            )
        char.body_type = self.body_type
        char.face_block = self.face

    def validate(self) -> None:
        if self.body_type not in (0, 1):
            raise ValueError("Body type must be 0 or 1")
        if self.face[:4] != _HEADER or len(self.face) < _HEADER_SIZE:
            raise ValueError("Not a Dark Souls III appearance block")
        size = int.from_bytes(self.face[8:12], "little")
        if size != len(self.face):
            raise ValueError("Appearance block size does not match its header")

    def to_json(self) -> dict:
        return {
            "format": JSON_FORMAT,
            "version": JSON_VERSION,
            "body_type": self.body_type,
            "face": self.face.hex(),
        }

    @classmethod
    def from_json(cls, d: dict) -> Appearance:
        if not isinstance(d, dict) or d.get("format") != JSON_FORMAT:
            raise ValueError("Not a Dark Souls III appearance file")
        if d.get("version") != JSON_VERSION:
            raise ValueError(f"Unsupported appearance file version {d.get('version')}")
        body_type = d.get("body_type")
        # bool is an int subclass; True/False are not body types.
        if type(body_type) is not int or body_type not in (0, 1):
            raise ValueError("body_type must be 0 or 1 in the appearance file")
        face = d.get("face")
        try:
            face = bytes.fromhex(face)
        except (TypeError, ValueError):
            raise ValueError(
                "face must be a hex string in the appearance file"
            ) from None
        app = cls(body_type=body_type, face=face)
        app.validate()
        return app
