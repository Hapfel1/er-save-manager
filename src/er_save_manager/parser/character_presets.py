"""
Elden Ring Character Presets Parser

Handles CSMenuSystemSaveLoad structure containing 15 character appearance presets.
Each preset is 0x130 bytes with detailed facial customization data.

Structure:
- CSMenuSystemSaveLoad: 0x1800 bytes total
  - Header: 8 bytes
  - 15 FacePreset slots: 15 * 0x130 bytes
  - Padding: remaining bytes
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from io import BytesIO


@dataclass
class FacePreset:
    """
    Single character appearance preset (0x130 bytes / 304 bytes)

    Contains complete facial customization data including:
    - Body type and face models
    - Facial structure parameters (68 values)
    - Colors and cosmetics (50+ values)
    """

    # Header section (0x18 bytes)
    unk0x00: bytes = b""  # 20 bytes, includes body_type at offset 0x9
    face_data_marker: int = -1  # -1 = empty, 0 = active

    # Magic section (0xC bytes)
    magic: bytes = b""  # "FACE" or empty
    alignment: int = 0
    size: int = 0

    # Face models (with 3-byte padding after each)
    face_model: int = 0
    hair_model: int = 0
    unk0x14: int = 0
    eyebrow_model: int = 0
    beard_model: int = 0
    eyepatch_model: int = 0
    unk0x24: int = 0
    unk0x28: int = 0

    # Facial structure (68 parameters starting at 0x2C)
    apparent_age: int = 0
    facial_aesthetic: int = 0
    form_emphasis: int = 0
    unk0x2f: int = 0
    brow_ridge_height: int = 0
    inner_brow_ridge: int = 0
    outer_brow_ridge: int = 0
    cheekbone_height: int = 0
    cheekbone_depth: int = 0
    cheekbone_width: int = 0
    cheekbone_protrusion: int = 0
    cheeks: int = 0
    chin_tip_position: int = 0
    chin_length: int = 0
    chin_protrusion: int = 0
    chin_depth: int = 0
    chin_size: int = 0
    chin_height: int = 0
    chin_width: int = 0
    eye_position: int = 0
    eye_size: int = 0
    eye_slant: int = 0
    eye_spacing: int = 0
    nose_size: int = 0
    nose_forehead_ratio: int = 0
    unk0x45: int = 0
    face_protrusion: int = 0
    vertical_face_ratio: int = 0
    facial_feature_slant: int = 0
    horizontal_face_ratio: int = 0
    unk0x4a: int = 0
    forehead_depth: int = 0
    forehead_protrusion: int = 0
    unk0x4d: int = 0
    jaw_protrusion: int = 0
    jaw_width: int = 0
    lower_jaw: int = 0
    jaw_contour: int = 0
    lip_shape: int = 0
    lip_size: int = 0
    lip_fullness: int = 0
    mouth_expression: int = 0
    lip_protrusion: int = 0
    lip_thickness: int = 0
    mouth_protrusion: int = 0
    mouth_slant: int = 0
    occlusion: int = 0
    mouth_position: int = 0
    mouth_width: int = 0
    mouth_chin_distance: int = 0
    nose_ridge_depth: int = 0
    nose_ridge_length: int = 0
    nose_position: int = 0
    nose_tip_height: int = 0
    nostril_slant: int = 0
    nostril_size: int = 0
    nostril_width: int = 0
    nose_protrusion: int = 0
    nose_bridge_height: int = 0
    bridge_protrusion1: int = 0
    bridge_protrusion2: int = 0
    nose_bridge_width: int = 0
    nose_height: int = 0
    nose_slant: int = 0

    # Unknown block (64 bytes at 0x6C)
    unk0x6c: bytes = b""

    # Body proportions (5 bytes at 0xAC)
    head_size: int = 0
    chest_size: int = 0
    abdomen_size: int = 0
    arms_size: int = 0
    legs_size: int = 0

    # Unknown (2 bytes at 0xB1)
    unk0xb1: bytes = b""

    # Skin and cosmetics (88 bytes starting at 0xB3)
    skin_color_r: int = 0
    skin_color_g: int = 0
    skin_color_b: int = 0
    skin_luster: int = 0
    pores: int = 0
    stubble: int = 0
    dark_circles: int = 0
    dark_circle_color_r: int = 0
    dark_circle_color_g: int = 0
    dark_circle_color_b: int = 0
    cheeks_color_intensity: int = 0
    cheek_color_r: int = 0
    cheek_color_g: int = 0
    cheek_color_b: int = 0
    eye_liner: int = 0
    eye_liner_color_r: int = 0
    eye_liner_color_g: int = 0
    eye_liner_color_b: int = 0
    eye_shadow_lower: int = 0
    eye_shadow_lower_color_r: int = 0
    eye_shadow_lower_color_g: int = 0
    eye_shadow_lower_color_b: int = 0
    eye_shadow_upper: int = 0
    eye_shadow_upper_color_r: int = 0
    eye_shadow_upper_color_g: int = 0
    eye_shadow_upper_color_b: int = 0
    lip_stick: int = 0
    lip_stick_color_r: int = 0
    lip_stick_color_g: int = 0
    lip_stick_color_b: int = 0
    tattoo_mark_position_horizontal: int = 0
    tattoo_mark_position_vertical: int = 0
    tattoo_mark_angle: int = 0
    tattoo_mark_expansion: int = 0
    tattoo_mark_color_r: int = 0
    tattoo_mark_color_g: int = 0
    tattoo_mark_color_b: int = 0
    unk0xd8: int = 0
    tattoo_mark_flip: int = 0
    body_hair: int = 0
    body_hair_color_r: int = 0
    body_hair_color_g: int = 0
    body_hair_color_b: int = 0
    right_iris_color_r: int = 0
    right_iris_color_g: int = 0
    right_iris_color_b: int = 0
    right_iris_size: int = 0
    right_eye_clouding: int = 0
    right_eye_clouding_color_r: int = 0
    right_eye_clouding_color_g: int = 0
    right_eye_clouding_color_b: int = 0
    right_eye_white_color_r: int = 0
    right_eye_white_color_g: int = 0
    right_eye_white_color_b: int = 0
    right_eye_position: int = 0
    left_iris_color_r: int = 0
    left_iris_color_g: int = 0
    left_iris_color_b: int = 0
    left_iris_size: int = 0
    left_eye_clouding: int = 0
    left_eye_clouding_color_r: int = 0
    left_eye_clouding_color_g: int = 0
    left_eye_clouding_color_b: int = 0
    left_eye_white_color_r: int = 0
    left_eye_white_color_g: int = 0
    left_eye_white_color_b: int = 0
    left_eye_position: int = 0
    hair_color_r: int = 0
    hair_color_g: int = 0
    hair_color_b: int = 0
    luster: int = 0
    hair_root_darkness: int = 0
    white_hairs: int = 0
    beard_color_r: int = 0
    beard_color_g: int = 0
    beard_color_b: int = 0
    beard_luster: int = 0
    beard_root_darkness: int = 0
    beard_white_hairs: int = 0
    brow_color_r: int = 0
    brow_color_g: int = 0
    brow_color_b: int = 0
    brow_luster: int = 0
    brow_root_darkness: int = 0
    brow_white_hairs: int = 0
    eye_lash_color_r: int = 0
    eye_lash_color_g: int = 0
    eye_lash_color_b: int = 0
    eye_patch_color_r: int = 0
    eye_patch_color_g: int = 0
    eye_patch_color_b: int = 0

    # Padding (10 bytes at end)
    pad: bytes = b""

    @classmethod
    def read(cls, f: BytesIO) -> FacePreset:
        """Read FacePreset from stream (0x130 bytes)"""
        obj = cls()

        # Header (0x18 bytes)
        obj.unk0x00 = f.read(0x14)  # 20 bytes
        obj.face_data_marker = struct.unpack("<i", f.read(4))[0]

        # Magic section
        obj.magic = f.read(4)
        obj.alignment = struct.unpack("<I", f.read(4))[0]
        obj.size = struct.unpack("<I", f.read(4))[0]

        # Face models (each followed by 3 bytes padding)
        obj.face_model = struct.unpack("<B", f.read(1))[0]
        f.read(3)  # padding
        obj.hair_model = struct.unpack("<B", f.read(1))[0]
        f.read(3)  # padding
        obj.unk0x14 = struct.unpack("<B", f.read(1))[0]
        f.read(3)  # padding
        obj.eyebrow_model = struct.unpack("<B", f.read(1))[0]
        f.read(3)  # padding
        obj.beard_model = struct.unpack("<B", f.read(1))[0]
        f.read(3)  # padding
        obj.eyepatch_model = struct.unpack("<B", f.read(1))[0]
        f.read(3)  # padding
        obj.unk0x24 = struct.unpack("<B", f.read(1))[0]
        f.read(3)  # padding
        obj.unk0x28 = struct.unpack("<B", f.read(1))[0]
        f.read(3)  # padding

        # Facial structure (68 bytes)
        obj.apparent_age = struct.unpack("<B", f.read(1))[0]
        obj.facial_aesthetic = struct.unpack("<B", f.read(1))[0]
        obj.form_emphasis = struct.unpack("<B", f.read(1))[0]
        obj.unk0x2f = struct.unpack("<B", f.read(1))[0]
        obj.brow_ridge_height = struct.unpack("<B", f.read(1))[0]
        obj.inner_brow_ridge = struct.unpack("<B", f.read(1))[0]
        obj.outer_brow_ridge = struct.unpack("<B", f.read(1))[0]
        obj.cheekbone_height = struct.unpack("<B", f.read(1))[0]
        obj.cheekbone_depth = struct.unpack("<B", f.read(1))[0]
        obj.cheekbone_width = struct.unpack("<B", f.read(1))[0]
        obj.cheekbone_protrusion = struct.unpack("<B", f.read(1))[0]
        obj.cheeks = struct.unpack("<B", f.read(1))[0]
        obj.chin_tip_position = struct.unpack("<B", f.read(1))[0]
        obj.chin_length = struct.unpack("<B", f.read(1))[0]
        obj.chin_protrusion = struct.unpack("<B", f.read(1))[0]
        obj.chin_depth = struct.unpack("<B", f.read(1))[0]
        obj.chin_size = struct.unpack("<B", f.read(1))[0]
        obj.chin_height = struct.unpack("<B", f.read(1))[0]
        obj.chin_width = struct.unpack("<B", f.read(1))[0]
        obj.eye_position = struct.unpack("<B", f.read(1))[0]
        obj.eye_size = struct.unpack("<B", f.read(1))[0]
        obj.eye_slant = struct.unpack("<B", f.read(1))[0]
        obj.eye_spacing = struct.unpack("<B", f.read(1))[0]
        obj.nose_size = struct.unpack("<B", f.read(1))[0]
        obj.nose_forehead_ratio = struct.unpack("<B", f.read(1))[0]
        obj.unk0x45 = struct.unpack("<B", f.read(1))[0]
        obj.face_protrusion = struct.unpack("<B", f.read(1))[0]
        obj.vertical_face_ratio = struct.unpack("<B", f.read(1))[0]
        obj.facial_feature_slant = struct.unpack("<B", f.read(1))[0]
        obj.horizontal_face_ratio = struct.unpack("<B", f.read(1))[0]
        obj.unk0x4a = struct.unpack("<B", f.read(1))[0]
        obj.forehead_depth = struct.unpack("<B", f.read(1))[0]
        obj.forehead_protrusion = struct.unpack("<B", f.read(1))[0]
        obj.unk0x4d = struct.unpack("<B", f.read(1))[0]
        obj.jaw_protrusion = struct.unpack("<B", f.read(1))[0]
        obj.jaw_width = struct.unpack("<B", f.read(1))[0]
        obj.lower_jaw = struct.unpack("<B", f.read(1))[0]
        obj.jaw_contour = struct.unpack("<B", f.read(1))[0]
        obj.lip_shape = struct.unpack("<B", f.read(1))[0]
        obj.lip_size = struct.unpack("<B", f.read(1))[0]
        obj.lip_fullness = struct.unpack("<B", f.read(1))[0]
        obj.mouth_expression = struct.unpack("<B", f.read(1))[0]
        obj.lip_protrusion = struct.unpack("<B", f.read(1))[0]
        obj.lip_thickness = struct.unpack("<B", f.read(1))[0]
        obj.mouth_protrusion = struct.unpack("<B", f.read(1))[0]
        obj.mouth_slant = struct.unpack("<B", f.read(1))[0]
        obj.occlusion = struct.unpack("<B", f.read(1))[0]
        obj.mouth_position = struct.unpack("<B", f.read(1))[0]
        obj.mouth_width = struct.unpack("<B", f.read(1))[0]
        obj.mouth_chin_distance = struct.unpack("<B", f.read(1))[0]
        obj.nose_ridge_depth = struct.unpack("<B", f.read(1))[0]
        obj.nose_ridge_length = struct.unpack("<B", f.read(1))[0]
        obj.nose_position = struct.unpack("<B", f.read(1))[0]
        obj.nose_tip_height = struct.unpack("<B", f.read(1))[0]
        obj.nostril_slant = struct.unpack("<B", f.read(1))[0]
        obj.nostril_size = struct.unpack("<B", f.read(1))[0]
        obj.nostril_width = struct.unpack("<B", f.read(1))[0]
        obj.nose_protrusion = struct.unpack("<B", f.read(1))[0]
        obj.nose_bridge_height = struct.unpack("<B", f.read(1))[0]
        obj.bridge_protrusion1 = struct.unpack("<B", f.read(1))[0]
        obj.bridge_protrusion2 = struct.unpack("<B", f.read(1))[0]
        obj.nose_bridge_width = struct.unpack("<B", f.read(1))[0]
        obj.nose_height = struct.unpack("<B", f.read(1))[0]
        obj.nose_slant = struct.unpack("<B", f.read(1))[0]

        # Unknown block (64 bytes)
        obj.unk0x6c = f.read(64)

        # Body proportions (5 bytes)
        obj.head_size = struct.unpack("<B", f.read(1))[0]
        obj.chest_size = struct.unpack("<B", f.read(1))[0]
        obj.abdomen_size = struct.unpack("<B", f.read(1))[0]
        obj.arms_size = struct.unpack("<B", f.read(1))[0]
        obj.legs_size = struct.unpack("<B", f.read(1))[0]

        # Unknown (2 bytes)
        obj.unk0xb1 = f.read(2)

        # Skin and cosmetics (88 bytes)
        obj.skin_color_r = struct.unpack("<B", f.read(1))[0]
        obj.skin_color_g = struct.unpack("<B", f.read(1))[0]
        obj.skin_color_b = struct.unpack("<B", f.read(1))[0]
        obj.skin_luster = struct.unpack("<B", f.read(1))[0]
        obj.pores = struct.unpack("<B", f.read(1))[0]
        obj.stubble = struct.unpack("<B", f.read(1))[0]
        obj.dark_circles = struct.unpack("<B", f.read(1))[0]
        obj.dark_circle_color_r = struct.unpack("<B", f.read(1))[0]
        obj.dark_circle_color_g = struct.unpack("<B", f.read(1))[0]
        obj.dark_circle_color_b = struct.unpack("<B", f.read(1))[0]
        obj.cheeks_color_intensity = struct.unpack("<B", f.read(1))[0]
        obj.cheek_color_r = struct.unpack("<B", f.read(1))[0]
        obj.cheek_color_g = struct.unpack("<B", f.read(1))[0]
        obj.cheek_color_b = struct.unpack("<B", f.read(1))[0]
        obj.eye_liner = struct.unpack("<B", f.read(1))[0]
        obj.eye_liner_color_r = struct.unpack("<B", f.read(1))[0]
        obj.eye_liner_color_g = struct.unpack("<B", f.read(1))[0]
        obj.eye_liner_color_b = struct.unpack("<B", f.read(1))[0]
        obj.eye_shadow_lower = struct.unpack("<B", f.read(1))[0]
        obj.eye_shadow_lower_color_r = struct.unpack("<B", f.read(1))[0]
        obj.eye_shadow_lower_color_g = struct.unpack("<B", f.read(1))[0]
        obj.eye_shadow_lower_color_b = struct.unpack("<B", f.read(1))[0]
        obj.eye_shadow_upper = struct.unpack("<B", f.read(1))[0]
        obj.eye_shadow_upper_color_r = struct.unpack("<B", f.read(1))[0]
        obj.eye_shadow_upper_color_g = struct.unpack("<B", f.read(1))[0]
        obj.eye_shadow_upper_color_b = struct.unpack("<B", f.read(1))[0]
        obj.lip_stick = struct.unpack("<B", f.read(1))[0]
        obj.lip_stick_color_r = struct.unpack("<B", f.read(1))[0]
        obj.lip_stick_color_g = struct.unpack("<B", f.read(1))[0]
        obj.lip_stick_color_b = struct.unpack("<B", f.read(1))[0]
        obj.tattoo_mark_position_horizontal = struct.unpack("<B", f.read(1))[0]
        obj.tattoo_mark_position_vertical = struct.unpack("<B", f.read(1))[0]
        obj.tattoo_mark_angle = struct.unpack("<B", f.read(1))[0]
        obj.tattoo_mark_expansion = struct.unpack("<B", f.read(1))[0]
        obj.tattoo_mark_color_r = struct.unpack("<B", f.read(1))[0]
        obj.tattoo_mark_color_g = struct.unpack("<B", f.read(1))[0]
        obj.tattoo_mark_color_b = struct.unpack("<B", f.read(1))[0]
        obj.unk0xd8 = struct.unpack("<B", f.read(1))[0]
        obj.tattoo_mark_flip = struct.unpack("<B", f.read(1))[0]
        obj.body_hair = struct.unpack("<B", f.read(1))[0]
        obj.body_hair_color_r = struct.unpack("<B", f.read(1))[0]
        obj.body_hair_color_g = struct.unpack("<B", f.read(1))[0]
        obj.body_hair_color_b = struct.unpack("<B", f.read(1))[0]
        obj.right_iris_color_r = struct.unpack("<B", f.read(1))[0]
        obj.right_iris_color_g = struct.unpack("<B", f.read(1))[0]
        obj.right_iris_color_b = struct.unpack("<B", f.read(1))[0]
        obj.right_iris_size = struct.unpack("<B", f.read(1))[0]
        obj.right_eye_clouding = struct.unpack("<B", f.read(1))[0]
        obj.right_eye_clouding_color_r = struct.unpack("<B", f.read(1))[0]
        obj.right_eye_clouding_color_g = struct.unpack("<B", f.read(1))[0]
        obj.right_eye_clouding_color_b = struct.unpack("<B", f.read(1))[0]
        obj.right_eye_white_color_r = struct.unpack("<B", f.read(1))[0]
        obj.right_eye_white_color_g = struct.unpack("<B", f.read(1))[0]
        obj.right_eye_white_color_b = struct.unpack("<B", f.read(1))[0]
        obj.right_eye_position = struct.unpack("<B", f.read(1))[0]
        obj.left_iris_color_r = struct.unpack("<B", f.read(1))[0]
        obj.left_iris_color_g = struct.unpack("<B", f.read(1))[0]
        obj.left_iris_color_b = struct.unpack("<B", f.read(1))[0]
        obj.left_iris_size = struct.unpack("<B", f.read(1))[0]
        obj.left_eye_clouding = struct.unpack("<B", f.read(1))[0]
        obj.left_eye_clouding_color_r = struct.unpack("<B", f.read(1))[0]
        obj.left_eye_clouding_color_g = struct.unpack("<B", f.read(1))[0]
        obj.left_eye_clouding_color_b = struct.unpack("<B", f.read(1))[0]
        obj.left_eye_white_color_r = struct.unpack("<B", f.read(1))[0]
        obj.left_eye_white_color_g = struct.unpack("<B", f.read(1))[0]
        obj.left_eye_white_color_b = struct.unpack("<B", f.read(1))[0]
        obj.left_eye_position = struct.unpack("<B", f.read(1))[0]
        obj.hair_color_r = struct.unpack("<B", f.read(1))[0]
        obj.hair_color_g = struct.unpack("<B", f.read(1))[0]
        obj.hair_color_b = struct.unpack("<B", f.read(1))[0]
        obj.luster = struct.unpack("<B", f.read(1))[0]
        obj.hair_root_darkness = struct.unpack("<B", f.read(1))[0]
        obj.white_hairs = struct.unpack("<B", f.read(1))[0]
        obj.beard_color_r = struct.unpack("<B", f.read(1))[0]
        obj.beard_color_g = struct.unpack("<B", f.read(1))[0]
        obj.beard_color_b = struct.unpack("<B", f.read(1))[0]
        obj.beard_luster = struct.unpack("<B", f.read(1))[0]
        obj.beard_root_darkness = struct.unpack("<B", f.read(1))[0]
        obj.beard_white_hairs = struct.unpack("<B", f.read(1))[0]
        obj.brow_color_r = struct.unpack("<B", f.read(1))[0]
        obj.brow_color_g = struct.unpack("<B", f.read(1))[0]
        obj.brow_color_b = struct.unpack("<B", f.read(1))[0]
        obj.brow_luster = struct.unpack("<B", f.read(1))[0]
        obj.brow_root_darkness = struct.unpack("<B", f.read(1))[0]
        obj.brow_white_hairs = struct.unpack("<B", f.read(1))[0]
        obj.eye_lash_color_r = struct.unpack("<B", f.read(1))[0]
        obj.eye_lash_color_g = struct.unpack("<B", f.read(1))[0]
        obj.eye_lash_color_b = struct.unpack("<B", f.read(1))[0]
        obj.eye_patch_color_r = struct.unpack("<B", f.read(1))[0]
        obj.eye_patch_color_g = struct.unpack("<B", f.read(1))[0]
        obj.eye_patch_color_b = struct.unpack("<B", f.read(1))[0]

        # Padding (10 bytes)
        obj.pad = f.read(10)

        return obj

    def write(self, f: BytesIO) -> None:
        """Write FacePreset to stream (0x130 bytes)"""
        # Header
        f.write(self.unk0x00)
        f.write(struct.pack("<i", self.face_data_marker))

        # Magic section
        f.write(self.magic)
        f.write(struct.pack("<I", self.alignment))
        f.write(struct.pack("<I", self.size))

        # Face models (each followed by 3 bytes padding)
        f.write(struct.pack("<B", self.face_model))
        f.write(b"\x00" * 3)
        f.write(struct.pack("<B", self.hair_model))
        f.write(b"\x00" * 3)
        f.write(struct.pack("<B", self.unk0x14))
        f.write(b"\x00" * 3)
        f.write(struct.pack("<B", self.eyebrow_model))
        f.write(b"\x00" * 3)
        f.write(struct.pack("<B", self.beard_model))
        f.write(b"\x00" * 3)
        f.write(struct.pack("<B", self.eyepatch_model))
        f.write(b"\x00" * 3)
        f.write(struct.pack("<B", self.unk0x24))
        f.write(b"\x00" * 3)
        f.write(struct.pack("<B", self.unk0x28))
        f.write(b"\x00" * 3)

        # Facial structure
        f.write(struct.pack("<B", self.apparent_age))
        f.write(struct.pack("<B", self.facial_aesthetic))
        f.write(struct.pack("<B", self.form_emphasis))
        f.write(struct.pack("<B", self.unk0x2f))
        f.write(struct.pack("<B", self.brow_ridge_height))
        f.write(struct.pack("<B", self.inner_brow_ridge))
        f.write(struct.pack("<B", self.outer_brow_ridge))
        f.write(struct.pack("<B", self.cheekbone_height))
        f.write(struct.pack("<B", self.cheekbone_depth))
        f.write(struct.pack("<B", self.cheekbone_width))
        f.write(struct.pack("<B", self.cheekbone_protrusion))
        f.write(struct.pack("<B", self.cheeks))
        f.write(struct.pack("<B", self.chin_tip_position))
        f.write(struct.pack("<B", self.chin_length))
        f.write(struct.pack("<B", self.chin_protrusion))
        f.write(struct.pack("<B", self.chin_depth))
        f.write(struct.pack("<B", self.chin_size))
        f.write(struct.pack("<B", self.chin_height))
        f.write(struct.pack("<B", self.chin_width))
        f.write(struct.pack("<B", self.eye_position))
        f.write(struct.pack("<B", self.eye_size))
        f.write(struct.pack("<B", self.eye_slant))
        f.write(struct.pack("<B", self.eye_spacing))
        f.write(struct.pack("<B", self.nose_size))
        f.write(struct.pack("<B", self.nose_forehead_ratio))
        f.write(struct.pack("<B", self.unk0x45))
        f.write(struct.pack("<B", self.face_protrusion))
        f.write(struct.pack("<B", self.vertical_face_ratio))
        f.write(struct.pack("<B", self.facial_feature_slant))
        f.write(struct.pack("<B", self.horizontal_face_ratio))
        f.write(struct.pack("<B", self.unk0x4a))
        f.write(struct.pack("<B", self.forehead_depth))
        f.write(struct.pack("<B", self.forehead_protrusion))
        f.write(struct.pack("<B", self.unk0x4d))
        f.write(struct.pack("<B", self.jaw_protrusion))
        f.write(struct.pack("<B", self.jaw_width))
        f.write(struct.pack("<B", self.lower_jaw))
        f.write(struct.pack("<B", self.jaw_contour))
        f.write(struct.pack("<B", self.lip_shape))
        f.write(struct.pack("<B", self.lip_size))
        f.write(struct.pack("<B", self.lip_fullness))
        f.write(struct.pack("<B", self.mouth_expression))
        f.write(struct.pack("<B", self.lip_protrusion))
        f.write(struct.pack("<B", self.lip_thickness))
        f.write(struct.pack("<B", self.mouth_protrusion))
        f.write(struct.pack("<B", self.mouth_slant))
        f.write(struct.pack("<B", self.occlusion))
        f.write(struct.pack("<B", self.mouth_position))
        f.write(struct.pack("<B", self.mouth_width))
        f.write(struct.pack("<B", self.mouth_chin_distance))
        f.write(struct.pack("<B", self.nose_ridge_depth))
        f.write(struct.pack("<B", self.nose_ridge_length))
        f.write(struct.pack("<B", self.nose_position))
        f.write(struct.pack("<B", self.nose_tip_height))
        f.write(struct.pack("<B", self.nostril_slant))
        f.write(struct.pack("<B", self.nostril_size))
        f.write(struct.pack("<B", self.nostril_width))
        f.write(struct.pack("<B", self.nose_protrusion))
        f.write(struct.pack("<B", self.nose_bridge_height))
        f.write(struct.pack("<B", self.bridge_protrusion1))
        f.write(struct.pack("<B", self.bridge_protrusion2))
        f.write(struct.pack("<B", self.nose_bridge_width))
        f.write(struct.pack("<B", self.nose_height))
        f.write(struct.pack("<B", self.nose_slant))

        # Unknown block
        f.write(self.unk0x6c)

        # Body proportions
        f.write(struct.pack("<B", self.head_size))
        f.write(struct.pack("<B", self.chest_size))
        f.write(struct.pack("<B", self.abdomen_size))
        f.write(struct.pack("<B", self.arms_size))
        f.write(struct.pack("<B", self.legs_size))

        # Unknown
        f.write(self.unk0xb1)

        # Skin and cosmetics
        f.write(struct.pack("<B", self.skin_color_r))
        f.write(struct.pack("<B", self.skin_color_g))
        f.write(struct.pack("<B", self.skin_color_b))
        f.write(struct.pack("<B", self.skin_luster))
        f.write(struct.pack("<B", self.pores))
        f.write(struct.pack("<B", self.stubble))
        f.write(struct.pack("<B", self.dark_circles))
        f.write(struct.pack("<B", self.dark_circle_color_r))
        f.write(struct.pack("<B", self.dark_circle_color_g))
        f.write(struct.pack("<B", self.dark_circle_color_b))
        f.write(struct.pack("<B", self.cheeks_color_intensity))
        f.write(struct.pack("<B", self.cheek_color_r))
        f.write(struct.pack("<B", self.cheek_color_g))
        f.write(struct.pack("<B", self.cheek_color_b))
        f.write(struct.pack("<B", self.eye_liner))
        f.write(struct.pack("<B", self.eye_liner_color_r))
        f.write(struct.pack("<B", self.eye_liner_color_g))
        f.write(struct.pack("<B", self.eye_liner_color_b))
        f.write(struct.pack("<B", self.eye_shadow_lower))
        f.write(struct.pack("<B", self.eye_shadow_lower_color_r))
        f.write(struct.pack("<B", self.eye_shadow_lower_color_g))
        f.write(struct.pack("<B", self.eye_shadow_lower_color_b))
        f.write(struct.pack("<B", self.eye_shadow_upper))
        f.write(struct.pack("<B", self.eye_shadow_upper_color_r))
        f.write(struct.pack("<B", self.eye_shadow_upper_color_g))
        f.write(struct.pack("<B", self.eye_shadow_upper_color_b))
        f.write(struct.pack("<B", self.lip_stick))
        f.write(struct.pack("<B", self.lip_stick_color_r))
        f.write(struct.pack("<B", self.lip_stick_color_g))
        f.write(struct.pack("<B", self.lip_stick_color_b))
        f.write(struct.pack("<B", self.tattoo_mark_position_horizontal))
        f.write(struct.pack("<B", self.tattoo_mark_position_vertical))
        f.write(struct.pack("<B", self.tattoo_mark_angle))
        f.write(struct.pack("<B", self.tattoo_mark_expansion))
        f.write(struct.pack("<B", self.tattoo_mark_color_r))
        f.write(struct.pack("<B", self.tattoo_mark_color_g))
        f.write(struct.pack("<B", self.tattoo_mark_color_b))
        f.write(struct.pack("<B", self.unk0xd8))
        f.write(struct.pack("<B", self.tattoo_mark_flip))
        f.write(struct.pack("<B", self.body_hair))
        f.write(struct.pack("<B", self.body_hair_color_r))
        f.write(struct.pack("<B", self.body_hair_color_g))
        f.write(struct.pack("<B", self.body_hair_color_b))
        f.write(struct.pack("<B", self.right_iris_color_r))
        f.write(struct.pack("<B", self.right_iris_color_g))
        f.write(struct.pack("<B", self.right_iris_color_b))
        f.write(struct.pack("<B", self.right_iris_size))
        f.write(struct.pack("<B", self.right_eye_clouding))
        f.write(struct.pack("<B", self.right_eye_clouding_color_r))
        f.write(struct.pack("<B", self.right_eye_clouding_color_g))
        f.write(struct.pack("<B", self.right_eye_clouding_color_b))
        f.write(struct.pack("<B", self.right_eye_white_color_r))
        f.write(struct.pack("<B", self.right_eye_white_color_g))
        f.write(struct.pack("<B", self.right_eye_white_color_b))
        f.write(struct.pack("<B", self.right_eye_position))
        f.write(struct.pack("<B", self.left_iris_color_r))
        f.write(struct.pack("<B", self.left_iris_color_g))
        f.write(struct.pack("<B", self.left_iris_color_b))
        f.write(struct.pack("<B", self.left_iris_size))
        f.write(struct.pack("<B", self.left_eye_clouding))
        f.write(struct.pack("<B", self.left_eye_clouding_color_r))
        f.write(struct.pack("<B", self.left_eye_clouding_color_g))
        f.write(struct.pack("<B", self.left_eye_clouding_color_b))
        f.write(struct.pack("<B", self.left_eye_white_color_r))
        f.write(struct.pack("<B", self.left_eye_white_color_g))
        f.write(struct.pack("<B", self.left_eye_white_color_b))
        f.write(struct.pack("<B", self.left_eye_position))
        f.write(struct.pack("<B", self.hair_color_r))
        f.write(struct.pack("<B", self.hair_color_g))
        f.write(struct.pack("<B", self.hair_color_b))
        f.write(struct.pack("<B", self.luster))
        f.write(struct.pack("<B", self.hair_root_darkness))
        f.write(struct.pack("<B", self.white_hairs))
        f.write(struct.pack("<B", self.beard_color_r))
        f.write(struct.pack("<B", self.beard_color_g))
        f.write(struct.pack("<B", self.beard_color_b))
        f.write(struct.pack("<B", self.beard_luster))
        f.write(struct.pack("<B", self.beard_root_darkness))
        f.write(struct.pack("<B", self.beard_white_hairs))
        f.write(struct.pack("<B", self.brow_color_r))
        f.write(struct.pack("<B", self.brow_color_g))
        f.write(struct.pack("<B", self.brow_color_b))
        f.write(struct.pack("<B", self.brow_luster))
        f.write(struct.pack("<B", self.brow_root_darkness))
        f.write(struct.pack("<B", self.brow_white_hairs))
        f.write(struct.pack("<B", self.eye_lash_color_r))
        f.write(struct.pack("<B", self.eye_lash_color_g))
        f.write(struct.pack("<B", self.eye_lash_color_b))
        f.write(struct.pack("<B", self.eye_patch_color_r))
        f.write(struct.pack("<B", self.eye_patch_color_g))
        f.write(struct.pack("<B", self.eye_patch_color_b))

        # Padding
        f.write(self.pad)

    def is_empty(self) -> bool:
        """Check if preset slot is empty"""
        return self.magic != b"FACE"

    def get_body_type(self) -> int:
        """Extract body type from unk0x00 at offset 0x9"""
        if len(self.unk0x00) >= 10:
            return self.unk0x00[9]
        return 0

    def to_dict(self) -> dict:
        """Export ALL parameters to dictionary"""
        return {
            # Basic info
            "body_type": self.get_body_type(),
            # Face models
            "face_model": self.face_model,
            "hair_model": self.hair_model,
            "eyebrow_model": self.eyebrow_model,
            "beard_model": self.beard_model,
            "eyepatch_model": self.eyepatch_model,
            # Facial structure (68 parameters)
            "apparent_age": self.apparent_age,
            "facial_aesthetic": self.facial_aesthetic,
            "form_emphasis": self.form_emphasis,
            "brow_ridge_height": self.brow_ridge_height,
            "inner_brow_ridge": self.inner_brow_ridge,
            "outer_brow_ridge": self.outer_brow_ridge,
            "cheekbone_height": self.cheekbone_height,
            "cheekbone_depth": self.cheekbone_depth,
            "cheekbone_width": self.cheekbone_width,
            "cheekbone_protrusion": self.cheekbone_protrusion,
            "cheeks": self.cheeks,
            "chin_tip_position": self.chin_tip_position,
            "chin_length": self.chin_length,
            "chin_protrusion": self.chin_protrusion,
            "chin_depth": self.chin_depth,
            "chin_size": self.chin_size,
            "chin_height": self.chin_height,
            "chin_width": self.chin_width,
            "eye_position": self.eye_position,
            "eye_size": self.eye_size,
            "eye_slant": self.eye_slant,
            "eye_spacing": self.eye_spacing,
            "nose_size": self.nose_size,
            "nose_forehead_ratio": self.nose_forehead_ratio,
            "face_protrusion": self.face_protrusion,
            "vertical_face_ratio": self.vertical_face_ratio,
            "facial_feature_slant": self.facial_feature_slant,
            "horizontal_face_ratio": self.horizontal_face_ratio,
            "forehead_depth": self.forehead_depth,
            "forehead_protrusion": self.forehead_protrusion,
            "jaw_protrusion": self.jaw_protrusion,
            "jaw_width": self.jaw_width,
            "lower_jaw": self.lower_jaw,
            "jaw_contour": self.jaw_contour,
            "lip_shape": self.lip_shape,
            "lip_size": self.lip_size,
            "lip_fullness": self.lip_fullness,
            "mouth_expression": self.mouth_expression,
            "lip_protrusion": self.lip_protrusion,
            "lip_thickness": self.lip_thickness,
            "mouth_protrusion": self.mouth_protrusion,
            "mouth_slant": self.mouth_slant,
            "occlusion": self.occlusion,
            "mouth_position": self.mouth_position,
            "mouth_width": self.mouth_width,
            "mouth_chin_distance": self.mouth_chin_distance,
            "nose_ridge_depth": self.nose_ridge_depth,
            "nose_ridge_length": self.nose_ridge_length,
            "nose_position": self.nose_position,
            "nose_tip_height": self.nose_tip_height,
            "nostril_slant": self.nostril_slant,
            "nostril_size": self.nostril_size,
            "nostril_width": self.nostril_width,
            "nose_protrusion": self.nose_protrusion,
            "nose_bridge_height": self.nose_bridge_height,
            "bridge_protrusion1": self.bridge_protrusion1,
            "bridge_protrusion2": self.bridge_protrusion2,
            "nose_bridge_width": self.nose_bridge_width,
            "nose_height": self.nose_height,
            "nose_slant": self.nose_slant,
            # Body proportions
            "head_size": self.head_size,
            "chest_size": self.chest_size,
            "abdomen_size": self.abdomen_size,
            "arms_size": self.arms_size,
            "legs_size": self.legs_size,
            # Skin
            "skin_color": [self.skin_color_r, self.skin_color_g, self.skin_color_b],
            "skin_luster": self.skin_luster,
            "pores": self.pores,
            "stubble": self.stubble,
            # Cosmetics - Dark Circles
            "dark_circles": self.dark_circles,
            "dark_circle_color_r": self.dark_circle_color_r,
            "dark_circle_color_g": self.dark_circle_color_g,
            "dark_circle_color_b": self.dark_circle_color_b,
            # Cosmetics - Cheek Color
            "cheeks_color_intensity": self.cheeks_color_intensity,
            "cheek_color_r": self.cheek_color_r,
            "cheek_color_g": self.cheek_color_g,
            "cheek_color_b": self.cheek_color_b,
            # Cosmetics - Eye Liner
            "eye_liner": self.eye_liner,
            "eye_liner_color_r": self.eye_liner_color_r,
            "eye_liner_color_g": self.eye_liner_color_g,
            "eye_liner_color_b": self.eye_liner_color_b,
            # Cosmetics - Eye Shadow (Lower)
            "eye_shadow_lower": self.eye_shadow_lower,
            "eye_shadow_lower_color_r": self.eye_shadow_lower_color_r,
            "eye_shadow_lower_color_g": self.eye_shadow_lower_color_g,
            "eye_shadow_lower_color_b": self.eye_shadow_lower_color_b,
            # Cosmetics - Eye Shadow (Upper)
            "eye_shadow_upper": self.eye_shadow_upper,
            "eye_shadow_upper_color_r": self.eye_shadow_upper_color_r,
            "eye_shadow_upper_color_g": self.eye_shadow_upper_color_g,
            "eye_shadow_upper_color_b": self.eye_shadow_upper_color_b,
            # Cosmetics - Lipstick
            "lip_stick": self.lip_stick,
            "lip_stick_color_r": self.lip_stick_color_r,
            "lip_stick_color_g": self.lip_stick_color_g,
            "lip_stick_color_b": self.lip_stick_color_b,
            # Tattoo/Mark
            "tattoo_mark_position_horizontal": self.tattoo_mark_position_horizontal,
            "tattoo_mark_position_vertical": self.tattoo_mark_position_vertical,
            "tattoo_mark_angle": self.tattoo_mark_angle,
            "tattoo_mark_expansion": self.tattoo_mark_expansion,
            "tattoo_mark_color_r": self.tattoo_mark_color_r,
            "tattoo_mark_color_g": self.tattoo_mark_color_g,
            "tattoo_mark_color_b": self.tattoo_mark_color_b,
            "tattoo_mark_flip": self.tattoo_mark_flip,
            # Body Hair
            "body_hair": self.body_hair,
            "body_hair_color_r": self.body_hair_color_r,
            "body_hair_color_g": self.body_hair_color_g,
            "body_hair_color_b": self.body_hair_color_b,
            # Right Eye Details
            "right_iris_color_r": self.right_iris_color_r,
            "right_iris_color_g": self.right_iris_color_g,
            "right_iris_color_b": self.right_iris_color_b,
            "right_iris_size": self.right_iris_size,
            "right_eye_clouding": self.right_eye_clouding,
            "right_eye_clouding_color_r": self.right_eye_clouding_color_r,
            "right_eye_clouding_color_g": self.right_eye_clouding_color_g,
            "right_eye_clouding_color_b": self.right_eye_clouding_color_b,
            "right_eye_white_color_r": self.right_eye_white_color_r,
            "right_eye_white_color_g": self.right_eye_white_color_g,
            "right_eye_white_color_b": self.right_eye_white_color_b,
            "right_eye_position": self.right_eye_position,
            # Left Eye Details
            "left_iris_color_r": self.left_iris_color_r,
            "left_iris_color_g": self.left_iris_color_g,
            "left_iris_color_b": self.left_iris_color_b,
            "left_iris_size": self.left_iris_size,
            "left_eye_clouding": self.left_eye_clouding,
            "left_eye_clouding_color_r": self.left_eye_clouding_color_r,
            "left_eye_clouding_color_g": self.left_eye_clouding_color_g,
            "left_eye_clouding_color_b": self.left_eye_clouding_color_b,
            "left_eye_white_color_r": self.left_eye_white_color_r,
            "left_eye_white_color_g": self.left_eye_white_color_g,
            "left_eye_white_color_b": self.left_eye_white_color_b,
            "left_eye_position": self.left_eye_position,
            # Legacy eye color format (for backwards compatibility)
            "eye_color_left": [
                self.left_iris_color_r,
                self.left_iris_color_g,
                self.left_iris_color_b,
            ],
            "eye_color_right": [
                self.right_iris_color_r,
                self.right_iris_color_g,
                self.right_iris_color_b,
            ],
            # Hair Details
            "hair_color": [self.hair_color_r, self.hair_color_g, self.hair_color_b],
            "hair_color_r": self.hair_color_r,
            "hair_color_g": self.hair_color_g,
            "hair_color_b": self.hair_color_b,
            "luster": self.luster,
            "hair_root_darkness": self.hair_root_darkness,
            "white_hairs": self.white_hairs,
            # Beard Details
            "beard_color_r": self.beard_color_r,
            "beard_color_g": self.beard_color_g,
            "beard_color_b": self.beard_color_b,
            "beard_luster": self.beard_luster,
            "beard_root_darkness": self.beard_root_darkness,
            "beard_white_hairs": self.beard_white_hairs,
            # Eyebrow Details
            "brow_color_r": self.brow_color_r,
            "brow_color_g": self.brow_color_g,
            "brow_color_b": self.brow_color_b,
            "brow_luster": self.brow_luster,
            "brow_root_darkness": self.brow_root_darkness,
            "brow_white_hairs": self.brow_white_hairs,
            # Eyelash Details
            "eye_lash_color_r": self.eye_lash_color_r,
            "eye_lash_color_g": self.eye_lash_color_g,
            "eye_lash_color_b": self.eye_lash_color_b,
            # Eye Patch Details
            "eye_patch_color_r": self.eye_patch_color_r,
            "eye_patch_color_g": self.eye_patch_color_g,
            "eye_patch_color_b": self.eye_patch_color_b,
            # CRITICAL: Unknown/binary fields that must be preserved
            "_unk0x00": list(self.unk0x00),
            "_face_data_marker": self.face_data_marker,
            "_magic": self.magic.decode("ascii", errors="ignore") if self.magic else "",
            "_alignment": self.alignment,
            "_size": self.size,
            "_unk0x14": self.unk0x14,
            "_unk0x24": self.unk0x24,
            "_unk0x28": self.unk0x28,
            "_unk0x2f": self.unk0x2f,
            "_unk0x45": self.unk0x45,
            "_unk0x4a": self.unk0x4a,
            "_unk0x4d": self.unk0x4d,
            "_unk0x6c": list(self.unk0x6c),
            "_unk0xb1": list(self.unk0xb1),
            "_pad": list(self.pad),
        }

    @classmethod
    def from_dict(cls, data: dict) -> FacePreset:
        """
        Create FacePreset from dictionary (exported JSON format)

        Args:
            data: Dictionary with preset parameters

        Returns:
            FacePreset object
        """
        preset = cls()

        # CRITICAL: Restore unknown fields from JSON or use safe defaults
        # These fields contain essential face data that must be preserved!
        preset.unk0x00 = bytes(data.get("_unk0x00", [0] * 20))
        preset.face_data_marker = data.get("_face_data_marker", 32767)

        magic_str = data.get("_magic", "FACE")
        preset.magic = magic_str.encode("ascii") if magic_str else b"FACE"
        preset.alignment = data.get("_alignment", 4)
        preset.size = data.get("_size", 0x120)

        preset.unk0x6c = bytes(data.get("_unk0x6c", [0] * 64))
        preset.unk0xb1 = bytes(data.get("_unk0xb1", [0, 0]))
        preset.pad = bytes(data.get("_pad", [0] * 10))

        # If body_type is explicitly provided, override it in unk0x00
        # (for backward compatibility with old JSONs that don't have _unk0x00)
        if "body_type" in data and "_unk0x00" not in data:
            body_type = data["body_type"]
            unk_list = list(preset.unk0x00)
            if len(unk_list) >= 10:
                unk_list[8] = 0x01
                unk_list[9] = body_type
                preset.unk0x00 = bytes(unk_list)

        # Face models
        preset.face_model = data.get("face_model", 0)
        preset.hair_model = data.get("hair_model", 0)
        preset.unk0x14 = data.get("_unk0x14", 0)
        preset.eyebrow_model = data.get("eyebrow_model", 0)
        preset.beard_model = data.get("beard_model", 0)
        preset.eyepatch_model = data.get("eyepatch_model", 0)
        preset.unk0x24 = data.get("_unk0x24", 0)
        preset.unk0x28 = data.get("_unk0x28", 3)

        # Facial structure
        preset.apparent_age = data.get("apparent_age", 128)
        preset.facial_aesthetic = data.get("facial_aesthetic", 128)
        preset.form_emphasis = data.get("form_emphasis", 128)
        preset.unk0x2f = data.get("_unk0x2f", 0)
        preset.brow_ridge_height = data.get("brow_ridge_height", 128)
        preset.inner_brow_ridge = data.get("inner_brow_ridge", 128)
        preset.outer_brow_ridge = data.get("outer_brow_ridge", 128)
        preset.cheekbone_height = data.get("cheekbone_height", 128)
        preset.cheekbone_depth = data.get("cheekbone_depth", 128)
        preset.cheekbone_width = data.get("cheekbone_width", 128)
        preset.cheekbone_protrusion = data.get("cheekbone_protrusion", 128)
        preset.cheeks = data.get("cheeks", 128)
        preset.chin_tip_position = data.get("chin_tip_position", 128)
        preset.chin_length = data.get("chin_length", 128)
        preset.chin_protrusion = data.get("chin_protrusion", 128)
        preset.chin_depth = data.get("chin_depth", 128)
        preset.chin_size = data.get("chin_size", 128)
        preset.chin_height = data.get("chin_height", 128)
        preset.chin_width = data.get("chin_width", 128)
        preset.eye_position = data.get("eye_position", 128)
        preset.eye_size = data.get("eye_size", 128)
        preset.eye_slant = data.get("eye_slant", 128)
        preset.eye_spacing = data.get("eye_spacing", 128)
        preset.nose_size = data.get("nose_size", 128)
        preset.nose_forehead_ratio = data.get("nose_forehead_ratio", 128)
        preset.unk0x45 = data.get("_unk0x45", 0)
        preset.face_protrusion = data.get("face_protrusion", 128)
        preset.vertical_face_ratio = data.get("vertical_face_ratio", 128)
        preset.facial_feature_slant = data.get("facial_feature_slant", 128)
        preset.horizontal_face_ratio = data.get("horizontal_face_ratio", 128)
        preset.unk0x4a = data.get("_unk0x4a", 0)
        preset.forehead_depth = data.get("forehead_depth", 128)
        preset.forehead_protrusion = data.get("forehead_protrusion", 128)
        preset.unk0x4d = data.get("_unk0x4d", 0)
        preset.jaw_protrusion = data.get("jaw_protrusion", 128)
        preset.jaw_width = data.get("jaw_width", 128)
        preset.lower_jaw = data.get("lower_jaw", 128)
        preset.jaw_contour = data.get("jaw_contour", 128)
        preset.lip_shape = data.get("lip_shape", 128)
        preset.lip_size = data.get("lip_size", 128)
        preset.lip_fullness = data.get("lip_fullness", 128)
        preset.mouth_expression = data.get("mouth_expression", 128)
        preset.lip_protrusion = data.get("lip_protrusion", 128)
        preset.lip_thickness = data.get("lip_thickness", 128)
        preset.mouth_protrusion = data.get("mouth_protrusion", 128)
        preset.mouth_slant = data.get("mouth_slant", 128)
        preset.occlusion = data.get("occlusion", 128)
        preset.mouth_position = data.get("mouth_position", 128)
        preset.mouth_width = data.get("mouth_width", 128)
        preset.mouth_chin_distance = data.get("mouth_chin_distance", 128)
        preset.nose_ridge_depth = data.get("nose_ridge_depth", 128)
        preset.nose_ridge_length = data.get("nose_ridge_length", 128)
        preset.nose_position = data.get("nose_position", 128)
        preset.nose_tip_height = data.get("nose_tip_height", 128)
        preset.nostril_slant = data.get("nostril_slant", 128)
        preset.nostril_size = data.get("nostril_size", 128)
        preset.nostril_width = data.get("nostril_width", 128)
        preset.nose_protrusion = data.get("nose_protrusion", 128)
        preset.nose_bridge_height = data.get("nose_bridge_height", 128)
        preset.bridge_protrusion1 = data.get("bridge_protrusion1", 128)
        preset.bridge_protrusion2 = data.get("bridge_protrusion2", 128)
        preset.nose_bridge_width = data.get("nose_bridge_width", 128)
        preset.nose_height = data.get("nose_height", 128)
        preset.nose_slant = data.get("nose_slant", 128)

        # Body proportions
        preset.head_size = data.get("head_size", 128)
        preset.chest_size = data.get("chest_size", 128)
        preset.abdomen_size = data.get("abdomen_size", 128)
        preset.arms_size = data.get("arms_size", 128)
        preset.legs_size = data.get("legs_size", 128)

        # Colors - handle both formats (array or individual)
        skin_color = data.get("skin_color", [205, 180, 165])
        preset.skin_color_r = (
            skin_color[0]
            if isinstance(skin_color, list)
            else data.get("skin_color_r", 205)
        )
        preset.skin_color_g = (
            skin_color[1]
            if isinstance(skin_color, list)
            else data.get("skin_color_g", 180)
        )
        preset.skin_color_b = (
            skin_color[2]
            if isinstance(skin_color, list)
            else data.get("skin_color_b", 165)
        )

        hair_color = data.get("hair_color", [45, 35, 30])
        preset.hair_color_r = (
            hair_color[0]
            if isinstance(hair_color, list)
            else data.get("hair_color_r", 45)
        )
        preset.hair_color_g = (
            hair_color[1]
            if isinstance(hair_color, list)
            else data.get("hair_color_g", 35)
        )
        preset.hair_color_b = (
            hair_color[2]
            if isinstance(hair_color, list)
            else data.get("hair_color_b", 30)
        )

        eye_color_left = data.get("eye_color_left", [85, 120, 145])
        preset.left_iris_color_r = (
            eye_color_left[0]
            if isinstance(eye_color_left, list)
            else data.get("left_iris_color_r", 85)
        )
        preset.left_iris_color_g = (
            eye_color_left[1]
            if isinstance(eye_color_left, list)
            else data.get("left_iris_color_g", 120)
        )
        preset.left_iris_color_b = (
            eye_color_left[2]
            if isinstance(eye_color_left, list)
            else data.get("left_iris_color_b", 145)
        )

        eye_color_right = data.get("eye_color_right", [85, 120, 145])
        preset.right_iris_color_r = (
            eye_color_right[0]
            if isinstance(eye_color_right, list)
            else data.get("right_iris_color_r", 85)
        )
        preset.right_iris_color_g = (
            eye_color_right[1]
            if isinstance(eye_color_right, list)
            else data.get("right_iris_color_g", 120)
        )
        preset.right_iris_color_b = (
            eye_color_right[2]
            if isinstance(eye_color_right, list)
            else data.get("right_iris_color_b", 145)
        )

        # Set values for other color/cosmetic fields
        preset.skin_luster = data.get("skin_luster", 128)
        preset.pores = data.get("pores", 0)
        preset.stubble = data.get("stubble", 0)
        preset.dark_circles = data.get("dark_circles", 0)
        preset.dark_circle_color_r = data.get("dark_circle_color_r", 0)
        preset.dark_circle_color_g = data.get("dark_circle_color_g", 0)
        preset.dark_circle_color_b = data.get("dark_circle_color_b", 0)
        preset.cheeks_color_intensity = data.get("cheeks_color_intensity", 0)
        preset.cheek_color_r = data.get("cheek_color_r", 0)
        preset.cheek_color_g = data.get("cheek_color_g", 0)
        preset.cheek_color_b = data.get("cheek_color_b", 0)
        preset.eye_liner = data.get("eye_liner", 0)
        preset.eye_liner_color_r = data.get("eye_liner_color_r", 0)
        preset.eye_liner_color_g = data.get("eye_liner_color_g", 0)
        preset.eye_liner_color_b = data.get("eye_liner_color_b", 0)
        preset.eye_shadow_lower = data.get("eye_shadow_lower", 0)
        preset.eye_shadow_lower_color_r = data.get("eye_shadow_lower_color_r", 0)
        preset.eye_shadow_lower_color_g = data.get("eye_shadow_lower_color_g", 0)
        preset.eye_shadow_lower_color_b = data.get("eye_shadow_lower_color_b", 0)
        preset.eye_shadow_upper = data.get("eye_shadow_upper", 0)
        preset.eye_shadow_upper_color_r = data.get("eye_shadow_upper_color_r", 0)
        preset.eye_shadow_upper_color_g = data.get("eye_shadow_upper_color_g", 0)
        preset.eye_shadow_upper_color_b = data.get("eye_shadow_upper_color_b", 0)
        preset.lip_stick = data.get("lip_stick", 0)
        preset.lip_stick_color_r = data.get("lip_stick_color_r", 0)
        preset.lip_stick_color_g = data.get("lip_stick_color_g", 0)
        preset.lip_stick_color_b = data.get("lip_stick_color_b", 0)
        preset.tattoo_mark_position_horizontal = data.get(
            "tattoo_mark_position_horizontal", 128
        )
        preset.tattoo_mark_position_vertical = data.get(
            "tattoo_mark_position_vertical", 128
        )
        preset.tattoo_mark_angle = data.get("tattoo_mark_angle", 128)
        preset.tattoo_mark_expansion = data.get("tattoo_mark_expansion", 128)
        preset.tattoo_mark_color_r = data.get("tattoo_mark_color_r", 0)
        preset.tattoo_mark_color_g = data.get("tattoo_mark_color_g", 0)
        preset.tattoo_mark_color_b = data.get("tattoo_mark_color_b", 0)
        preset.unk0xd8 = 128
        preset.tattoo_mark_flip = data.get("tattoo_mark_flip", 0)
        preset.body_hair = data.get("body_hair", 0)
        preset.body_hair_color_r = data.get("body_hair_color_r", 0)
        preset.body_hair_color_g = data.get("body_hair_color_g", 0)
        preset.body_hair_color_b = data.get("body_hair_color_b", 0)
        preset.right_iris_size = data.get("right_iris_size", 128)
        preset.right_eye_clouding = data.get("right_eye_clouding", 0)
        preset.right_eye_clouding_color_r = data.get("right_eye_clouding_color_r", 0)
        preset.right_eye_clouding_color_g = data.get("right_eye_clouding_color_g", 0)
        preset.right_eye_clouding_color_b = data.get("right_eye_clouding_color_b", 0)
        preset.right_eye_white_color_r = data.get("right_eye_white_color_r", 255)
        preset.right_eye_white_color_g = data.get("right_eye_white_color_g", 255)
        preset.right_eye_white_color_b = data.get("right_eye_white_color_b", 255)
        preset.right_eye_position = data.get("right_eye_position", 128)
        preset.left_iris_size = data.get("left_iris_size", 128)
        preset.left_eye_clouding = data.get("left_eye_clouding", 0)
        preset.left_eye_clouding_color_r = data.get("left_eye_clouding_color_r", 0)
        preset.left_eye_clouding_color_g = data.get("left_eye_clouding_color_g", 0)
        preset.left_eye_clouding_color_b = data.get("left_eye_clouding_color_b", 0)
        preset.left_eye_white_color_r = data.get("left_eye_white_color_r", 255)
        preset.left_eye_white_color_g = data.get("left_eye_white_color_g", 255)
        preset.left_eye_white_color_b = data.get("left_eye_white_color_b", 255)
        preset.left_eye_position = data.get("left_eye_position", 128)
        preset.luster = data.get("luster", 128)
        preset.hair_root_darkness = data.get("hair_root_darkness", 128)
        preset.white_hairs = data.get("white_hairs", 0)
        preset.beard_color_r = data.get("beard_color_r", 45)
        preset.beard_color_g = data.get("beard_color_g", 35)
        preset.beard_color_b = data.get("beard_color_b", 30)
        preset.beard_luster = data.get("beard_luster", 128)
        preset.beard_root_darkness = data.get("beard_root_darkness", 128)
        preset.beard_white_hairs = data.get("beard_white_hairs", 0)
        preset.brow_color_r = data.get("brow_color_r", 45)
        preset.brow_color_g = data.get("brow_color_g", 35)
        preset.brow_color_b = data.get("brow_color_b", 30)
        preset.brow_luster = data.get("brow_luster", 128)
        preset.brow_root_darkness = data.get("brow_root_darkness", 128)
        preset.brow_white_hairs = data.get("brow_white_hairs", 0)
        preset.eye_lash_color_r = data.get("eye_lash_color_r", 0)
        preset.eye_lash_color_g = data.get("eye_lash_color_g", 0)
        preset.eye_lash_color_b = data.get("eye_lash_color_b", 0)
        preset.eye_patch_color_r = data.get("eye_patch_color_r", 0)
        preset.eye_patch_color_g = data.get("eye_patch_color_g", 0)
        preset.eye_patch_color_b = data.get("eye_patch_color_b", 0)

        return preset


@dataclass
class CSMenuSystemSaveLoad:
    """
    Character preset container (0x1800 bytes / 6144 bytes)

    Contains 15 character appearance preset slots.
    Located in USER_DATA_10 at offset 0x14C (after Version, SteamID, Settings).
    """

    unk0x0: int = 0
    unk0x2: int = 0
    size: int = 0
    presets: list[FacePreset] = field(default_factory=list)
    padding: bytes = b""

    @classmethod
    def read(cls, f: BytesIO) -> CSMenuSystemSaveLoad:
        """Read CSMenuSystemSaveLoad from stream (0x1800 bytes)"""
        obj = cls()

        # Header (8 bytes)
        obj.unk0x0 = struct.unpack("<H", f.read(2))[0]
        obj.unk0x2 = struct.unpack("<H", f.read(2))[0]
        obj.size = struct.unpack("<I", f.read(4))[0]

        # Read 15 presets
        obj.presets = []
        for _ in range(15):
            preset = FacePreset.read(f)
            obj.presets.append(preset)

        # Read remaining padding
        bytes_read = 8 + (15 * 0x130)
        remaining = 0x1800 - bytes_read
        if remaining > 0:
            obj.padding = f.read(remaining)

        return obj

    def write(self, f: BytesIO) -> None:
        """Write CSMenuSystemSaveLoad to stream"""
        # Header
        f.write(struct.pack("<H", self.unk0x0))
        f.write(struct.pack("<H", self.unk0x2))
        f.write(struct.pack("<I", self.size))

        # Write 15 presets
        for preset in self.presets:
            preset.write(f)

        # Write padding
        f.write(self.padding)

    def get_active_presets(self) -> list[tuple[int, FacePreset]]:
        """Get list of (slot_index, preset) for non-empty presets"""
        active = []
        for idx, preset in enumerate(self.presets):
            if not preset.is_empty():
                active.append((idx, preset))
        return active

    def copy_preset(self, source_idx: int, dest_idx: int) -> bool:
        """Copy preset from one slot to another"""
        if source_idx < 0 or source_idx >= 15:
            return False
        if dest_idx < 0 or dest_idx >= 15:
            return False

        source = self.presets[source_idx]
        if source.is_empty():
            return False

        # Deep copy all fields
        self.presets[dest_idx] = FacePreset.read(
            BytesIO(
                BytesIO(
                    lambda: (dest := BytesIO(), source.write(dest), dest.getvalue())[
                        2
                    ]()
                )
            )
        )

        return True

    def clear_preset(self, idx: int) -> None:
        """Clear a preset slot"""
        if idx < 0 or idx >= 15:
            return

        self.presets[idx] = FacePreset()
