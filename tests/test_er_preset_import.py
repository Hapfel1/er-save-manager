from io import BytesIO

from er_save_manager.parser.character_presets import FacePreset


def test_elden_sliders_null_controls_use_defaults():
    data = {
        "base": {"body_type": "B"},
        "skin_color": {"skin_r": "255", "skin_g": "194", "skin_b": "175"},
        "eyebrows": {"brow": "15", "roots": None, "white": None},
        "right_eye": {"iris_size": "215", "iris_r": "0", "position": "128"},
        "left_eye": {"iris_size": None, "iris_r": None, "position": None},
        "tattoo_mark_eyepatch": {"tattoo": None, "flip": None, "eyepatch": None},
        "body": {"head": "80", "body_hair": "0", "body_hair_r": None},
    }

    preset = FacePreset.from_elden_bling(data)

    assert preset.get_body_type() == 0
    assert (preset.left_iris_size, preset.left_iris_color_r) == (215, 0)
    assert (preset.eyepatch_model, preset.tattoo_mark_flip) == (0, 0)
    assert preset.head_size == 80
    assert FacePreset.dict_problem(preset.to_dict()) is None
    out = BytesIO()
    preset.write(out)
    assert len(out.getvalue()) == 0x130
