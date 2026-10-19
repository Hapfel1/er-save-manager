"""
DSR character appearance: FaceGen face controls, presets and JSON files.

The 100 face bytes are FaceGen coefficients, 50 geometry then 50 texture,
stored as u8 with 128 as the mean face. Each named control (the game's
si.ctl) is a direction in one of the two coefficient spaces; its value is
the dot product with the centered bytes. Values stay in byte units, so the
unknown coefficient scale of the u8 encoding cancels out. Setting a control
moves the coefficients along its own direction only, as FaceGen does.

data/appearance.json is generated from the game's si.ctl, FaceGenParam,
MenuColorTableParam and menu text.
"""

from __future__ import annotations

import functools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .save import FACE_DATA_SIZE, HAIR_ITEM_BASE

if TYPE_CHECKING:
    from .save import DSRCharacter

_DATA_PATH = Path(__file__).parent / "data" / "appearance.json"
GEO_SIZE = FACE_DATA_SIZE // 2
PHYSIQUE_COUNT = 9
TYPE_COUNT = 10  # face types, hair types, color presets
JSON_FORMAT = "dsr_appearance"
JSON_VERSION = 1
# Half-range of a named control slider in byte units: the creation menu's
# Eye Size slider at its right end sits here. si.ctl control vectors are all
# unit length, so one value fits every named control.
CONTROL_RANGE = 63.3
# Age and gender sliders reach this far past the widest value among the
# game's own faces.
RANGE_MARGIN = 1.5


@functools.cache
def _data() -> dict:
    return json.loads(_DATA_PATH.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class FaceControl:
    """One named slider. group/label split the si.ctl name at " - ";
    span is the slider half-range in byte units."""

    group: str
    label: str
    geo: tuple[float, ...] | None
    tex: tuple[float, ...] | None
    span: float

    def value(self, coeffs: list[float]) -> float:
        if self.geo is not None:
            return sum(v * c for v, c in zip(self.geo, coeffs[:GEO_SIZE], strict=True))
        return sum(v * c for v, c in zip(self.tex, coeffs[GEO_SIZE:], strict=True))

    def apply(self, coeffs: list[float], target: float) -> list[float]:
        """Coefficients with this control at target. Age and gender move
        both blocks by the same amount along their own directions."""
        delta = target - self.value(coeffs)
        out = list(coeffs)
        for vec, start in ((self.geo, 0), (self.tex, GEO_SIZE)):
            if vec is None:
                continue
            norm = sum(v * v for v in vec)
            for i, v in enumerate(vec):
                out[start + i] += delta * v / norm
        return out

    def slider_range(self, coeffs: list[float]) -> float:
        return max(self.span, abs(self.value(coeffs)))


def _split(name: str) -> tuple[str, str]:
    group, _, label = name.partition(" - ")
    return group, label or group


@functools.cache
def shape_controls() -> tuple[FaceControl, ...]:
    """Age and the FaceGen gender control first, then the geometry controls.
    The gender control is labelled with Dark Souls III's menu name for it."""
    d = _data()
    out = [
        FaceControl(
            "Overall",
            "Age",
            tuple(d["age"]["geo"]),
            tuple(d["age"]["tex"]),
            d["age"]["range"] * RANGE_MARGIN,
        ),
        FaceControl(
            "Overall",
            "Facial aesthetic",
            tuple(d["gender"]["geo"]),
            tuple(d["gender"]["tex"]),
            d["gender"]["range"] * RANGE_MARGIN,
        ),
    ]
    for c in d["controls"]:
        if c["block"] == "geo":
            out.append(
                FaceControl(*_split(c["name"]), tuple(c["vector"]), None, CONTROL_RANGE)
            )
    return tuple(out)


@functools.cache
def skin_controls() -> tuple[FaceControl, ...]:
    return tuple(
        FaceControl(*_split(c["name"]), None, tuple(c["vector"]), CONTROL_RANGE)
        for c in _data()["controls"]
        if c["block"] == "tex"
    )


def face_to_coeffs(face: bytes) -> list[float]:
    neutral = _data()["neutral"]
    return [float(b - neutral) for b in face]


def coeffs_to_face(coeffs: list[float]) -> bytes:
    neutral = _data()["neutral"]
    return bytes(max(0, min(255, round(c) + neutral)) for c in coeffs)


def face_preset(body_type: int, face_type: int) -> bytes:
    """Face data of a character creation face type."""
    return bytes(_data()["face_presets"][str(1 if body_type == 1 else 0)][face_type])


def color_preset_rgb(index: int) -> tuple[int, int, int]:
    return tuple(_data()["color_presets"][index])


def physique_names() -> list[str]:
    return list(_data()["physique_names"])


def face_names(body_type: int) -> list[str]:
    return list(_data()["face_names"][str(1 if body_type == 1 else 0)])


def hair_names(body_type: int) -> list[str]:
    return list(_data()["hair_names"][str(1 if body_type == 1 else 0)])


def color_names() -> list[str]:
    return list(_data()["color_names"])


def hair_item_id(body_type: int, hair_type: int) -> int:
    """Equipped hair part id; the game draws this, not the hairstyle byte."""
    return HAIR_ITEM_BASE[body_type] + 100 * hair_type


@dataclass
class Appearance:
    body_type: int
    physique: int
    face_type: int
    hair_type: int
    color_preset: int
    hair_rgba: tuple[float, float, float, float]
    eye_rgba: tuple[float, float, float, float]
    face_data: bytes

    @classmethod
    def from_character(cls, char: DSRCharacter) -> Appearance:
        return cls(
            body_type=char.body_type,
            physique=char.physique,
            face_type=char.face_type,
            hair_type=char.hair_type,
            color_preset=char.color_preset,
            hair_rgba=tuple(char.hair_rgba),
            eye_rgba=tuple(char.eye_rgba),
            face_data=char.face_data,
        )

    def apply_to(self, char: DSRCharacter) -> None:
        self.validate()
        char.body_type = self.body_type
        char.physique = self.physique
        char.face_type = self.face_type
        char.hair_type = self.hair_type
        char.hair_item_id = hair_item_id(self.body_type, self.hair_type)
        char.color_preset = self.color_preset
        char.hair_rgba = self.hair_rgba
        char.eye_rgba = self.eye_rgba
        char.face_data = self.face_data

    def validate(self) -> None:
        if self.body_type not in (0, 1):
            raise ValueError("Body type must be 0 or 1")
        if not 0 <= self.physique < PHYSIQUE_COUNT:
            raise ValueError(f"Physique must be 0-{PHYSIQUE_COUNT - 1}")
        for name in ("face_type", "hair_type", "color_preset"):
            if not 0 <= getattr(self, name) < TYPE_COUNT:
                raise ValueError(
                    f"{name.replace('_', ' ').capitalize()} must be 0-{TYPE_COUNT - 1}"
                )
        for name in ("hair_rgba", "eye_rgba"):
            rgba = getattr(self, name)
            if len(rgba) != 4 or not all(
                math.isfinite(v) and 0.0 <= v <= 1.0 for v in rgba
            ):
                raise ValueError(f"{name} must be four values from 0 to 1")
        if len(self.face_data) != FACE_DATA_SIZE:
            raise ValueError(f"Face data must be {FACE_DATA_SIZE} bytes")

    def to_json(self) -> dict:
        return {
            "format": JSON_FORMAT,
            "version": JSON_VERSION,
            "body_type": self.body_type,
            "physique": self.physique,
            "face_type": self.face_type,
            "hair_type": self.hair_type,
            "color_preset": self.color_preset,
            "hair_rgba": list(self.hair_rgba),
            "eye_rgba": list(self.eye_rgba),
            "face_data": self.face_data.hex(),
        }

    @classmethod
    def from_json(cls, d: dict) -> Appearance:
        if not isinstance(d, dict) or d.get("format") != JSON_FORMAT:
            raise ValueError("Not a Dark Souls Remastered appearance file")
        if d.get("version") != JSON_VERSION:
            raise ValueError(f"Unsupported appearance file version {d.get('version')}")
        try:
            app = cls(
                body_type=int(d["body_type"]),
                physique=int(d["physique"]),
                face_type=int(d["face_type"]),
                hair_type=int(d["hair_type"]),
                color_preset=int(d["color_preset"]),
                hair_rgba=tuple(float(v) for v in d["hair_rgba"]),
                eye_rgba=tuple(float(v) for v in d["eye_rgba"]),
                face_data=bytes.fromhex(d["face_data"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid appearance file: {exc}") from exc
        app.validate()
        return app
