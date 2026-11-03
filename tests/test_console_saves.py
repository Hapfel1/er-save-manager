"""
Console saves and copies between platforms (layouts in parser/platform.py,
games/ps_userdata.py and games/*/platform.py).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from er_save_manager.games import extension_copy as ec
from er_save_manager.games import ps_userdata
from er_save_manager.games.ds2_dsr_steamid import detect_steamid
from er_save_manager.games.DSR.save import DSRSave
from er_save_manager.games.save_identify import bnd4_game, identify_game
from er_save_manager.parser import Save
from er_save_manager.parser import platform as plat
from tests.test_ds3_ps4 import _write_folder as _write_ds3_folder
from tests.test_ds3_ps4 import slot_body  # noqa: F401  (fixture)
from tests.test_ps4_dsr_ds2 import _write_ds2_folder, _write_dsr_folder

STEAM_ID = 76561198000000123


def _files(folder: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()}


def _slots(save: Save) -> list[int]:
    return [i for i, s in enumerate(save.character_slots) if not s.is_empty()]


def _write_switch(save: Save, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in plat.switch2_files(plat.convert(save, plat.SWITCH2)).items():
        (folder / name).write_bytes(data)
    return folder / "ER_____0000_userdata0000"


def test_er_pc_ps_round_trip(sanitized_save):
    ps = Save.from_bytes(plat.ps_bytes(plat.convert(sanitized_save, plat.PS)))
    assert ps.platform == plat.PS and _slots(ps) == _slots(sanitized_save)
    assert ps.user_data_10_parsed.steam_id == 0
    # Console USER_DATA_10 lacks PCOptionData; the key config still parses.
    assert (
        ps.user_data_10_parsed.key_config_save_load
        == sanitized_save.user_data_10_parsed.key_config_save_load
    )

    data = plat.pc_bytes(plat.convert(ps, plat.PC, STEAM_ID))
    assert bnd4_game(data) == "elden_ring"
    pc = Save.from_bytes(data)
    assert _slots(pc) == _slots(sanitized_save)
    assert pc.user_data_10_parsed.steam_id == STEAM_ID
    assert {pc.character_slots[i].steam_id for i in _slots(pc)} == {STEAM_ID}
    assert pc.user_data_10_parsed.pc_option_data.raw_data == plat.DEFAULT_PC_OPTION_DATA
    assert plat.entries(pc)[11] == plat.entries(sanitized_save)[11]


def test_switch2_folder(sanitized_save, tmp_path):
    first = _write_switch(sanitized_save, tmp_path / "sw")
    assert identify_game(first) == "elden_ring" and not ps_userdata.is_ps_userdata(
        first
    )
    before = _files(first.parent)
    save = Save.from_file(str(first))
    assert save.platform == plat.SWITCH2 and _slots(save) == _slots(sanitized_save)
    save.to_file(str(first))
    assert _files(first.parent) == before
    save._raw_data[save._user_data_11_offset] ^= 0xFF
    save.to_file(str(first))
    after = _files(first.parent)
    assert [n for n in after if after[n] != before[n]] == ["ER_____0000_userdata0011"]

    (first.parent / "ER_____0000_userdata0007").unlink()
    with pytest.raises(ps_userdata.IncompleteFolderError, match="userdata0007"):
        Save.from_file(str(first))


def test_er_copy_between_platforms(sanitized_save_path, tmp_path):
    co2 = tmp_path / "ER0000.co2"
    shutil.copyfile(sanitized_save_path, co2)
    assert [f.ext for f in ec.targets("elden_ring", co2)][-2:] == [
        "memory.dat",
        "switch2",
    ]
    (tmp_path / "sw").mkdir()
    plan = ec.make_plan("elden_ring", co2, "switch2", tmp_path / "sw")
    # Consoles run the unmodded game: Seamless Co-op items block.
    assert plan.blocked and all("Seamless" in c.blockers[0] for c in plan.blocked)
    slot = plan.copyable[0].slot
    ec.write_copy(plan, [slot])
    assert Save.from_file(str(plan.target)).platform == plat.SWITCH2

    again = ec.make_plan("elden_ring", co2, "switch2", tmp_path / "sw")
    assert again.merges
    ec.write_merge(again, [(slot, again.free_slots[0])])
    assert len(_slots(Save.from_file(str(plan.target)))) == 2
    with pytest.raises(ec.ExtensionCopyError, match="folder"):
        ec.make_plan("elden_ring", plan.target, "switch2", tmp_path / "sw")

    (tmp_path / "pc").mkdir()
    back = ec.make_plan("elden_ring", plan.target, ".sl2", tmp_path / "pc")
    assert back.needs_steam_id
    with pytest.raises(ec.ExtensionCopyError):
        ec.write_copy(back, [slot])
    ec.write_copy(back, [slot], STEAM_ID)
    assert Save.from_file(str(back.target)).user_data_10_parsed.steam_id == STEAM_ID


def test_ds_copy_between_platforms(tmp_path, slot_body):  # noqa: F811
    for name in ("pc", "dsrpc", "ds2pc", "ds2ps"):
        (tmp_path / name).mkdir()
    _write_ds3_folder(tmp_path / "ds3", slot_body, range(10), with_global=True)
    with pytest.raises(ec.ExtensionCopyError, match="regulation"):
        ec.make_plan(
            "dark_souls_3", tmp_path / "ds3" / "userdata0000", ".sl2", tmp_path / "pc"
        )

    dsr = tmp_path / "dsr"
    _write_dsr_folder(dsr, encrypted=True)
    plan = ec.make_plan(
        "dark_souls_remastered", dsr / "userdata0000", ".sl2", tmp_path / "dsrpc"
    )
    ec.write_copy(plan, [c.slot for c in plan.copyable])
    pc = DSRSave.from_file(plan.target)
    assert pc.characters[0].name == "Tester" and all(
        ok for _, ok in pc.verify_checksums()
    )
    with pytest.raises(ec.ExtensionCopyError, match="PS4"):
        ec.make_plan("dark_souls_remastered", plan.target, "ps4", tmp_path / "pc")

    ds2 = _write_ds2_folder(tmp_path / "ds2")
    plan = ec.make_plan(
        "dark_souls_2", ds2 / "userdata0000", ".sl2", tmp_path / "ds2pc"
    )
    ec.write_copy(plan, [], STEAM_ID)
    assert detect_steamid(plan.target, "dark_souls_2") == STEAM_ID
    plan = ec.make_plan("dark_souls_2", plan.target, "ps4", tmp_path / "ds2ps")
    ec.write_copy(plan, [])
    assert _files(tmp_path / "ds2ps") == _files(ds2)


def test_console_labels_and_ban_warnings(sanitized_save, tmp_path):
    from er_save_manager.ui.dialogs.vanilla_save_warning import (
        _GAME_TEXT,
        is_vanilla_save,
        warning_key,
    )
    from er_save_manager.ui.gui import _console_labels

    assert _console_labels("elden_ring")[0] == "PS / Switch Save?"
    assert _console_labels("nightreign")[0] == "PS Save?"
    assert _console_labels("dark_souls_2")[0] == "PS4 Save?"

    ps = tmp_path / "memory.dat"
    ps.write_bytes(plat.ps_bytes(plat.convert(sanitized_save, plat.PS)))
    for path, key in (
        (_write_switch(sanitized_save, tmp_path / "sw"), "elden_ring_switch2"),
        (ps, "elden_ring_ps"),
    ):
        assert is_vanilla_save(str(path)) and key in _GAME_TEXT
        assert warning_key("elden_ring", str(path)) == key
