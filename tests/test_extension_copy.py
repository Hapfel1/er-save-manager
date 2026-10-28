"""Copying a save to another mod extension."""

import shutil
from pathlib import Path

import pytest

from er_save_manager.fixes.wiped_slot import SLOT_SIZE
from er_save_manager.games import extension_copy as ec
from er_save_manager.parser import Save


@pytest.fixture
def co2(sanitized_save_path, tmp_path) -> Path:
    path = tmp_path / "ER0000.co2"
    shutil.copyfile(sanitized_save_path, path)
    return path


def _occupied(path: Path) -> list[int]:
    save = Save.from_file(str(path))
    return [i for i, s in enumerate(save.character_slots) if not s.is_empty()]


def test_target_path():
    for name, ext, expected in (
        ("ER0000.co2", ".sl2", "ER0000.sl2"),
        ("ER0000.cnv.co2", ".cnvco2", "ER0000.cnvco2"),
        ("ER0000.cnvco2", ".cnv", "ER0000.cnv"),
        ("ER0000mine.sl2", ".co2", "ER0000mine.co2"),
    ):
        assert ec.target_path(Path("/x") / name, ext).name == expected


def test_blockers_follow_the_target_flavor(co2):
    plan = ec.make_plan("elden_ring", co2, ".sl2")
    blocked = {c.slot for c in plan.blocked}
    assert blocked and 1 not in blocked
    assert all(
        b.startswith("Seamless Co-op items") for c in plan.blocked for b in c.blockers
    )

    plan = ec.make_plan("elden_ring", co2, ".cnv")
    assert not any("Seamless" in b for c in plan.characters for b in c.blockers)

    plan = ec.make_plan("elden_ring", co2, ".cnvco2")
    assert {c.slot for c in plan.copyable} == {6, 7, 8}
    assert all("above +15" in c.blockers[0] for c in plan.blocked)


def test_extensions(co2):
    for ext, convergence in (("co3", False), (".CO3", False), (".cnv.co3", True)):
        plan = ec.make_plan("elden_ring", co2, ext)
        assert plan.target.name == "ER0000." + ext.lower().lstrip(".")
        assert plan.target_flavor.seamless
        assert plan.target_flavor.convergence is convergence
    for game, ext in (
        *(("elden_ring", e) for e in (".bak", ".co2.bak", ".a b", "")),
        ("dark_souls_3", ".cnv"),
        ("sekiro", ".co2"),
    ):
        with pytest.raises(ec.ExtensionCopyError):
            ec.make_plan(game, co2, ext)


def test_copy_keeps_only_chosen_characters(co2):
    plan = ec.make_plan("elden_ring", co2, ".sl2")
    before = co2.read_bytes()
    ec.write_copy(plan, [1])
    assert co2.read_bytes() == before
    assert _occupied(plan.target) == [1]


def test_copy_of_every_character_is_byte_identical(co2):
    plan = ec.make_plan("elden_ring", co2, ".cnvco2")
    # With no character left out the target is a plain copy of the file.
    plan.characters = plan.copyable
    ec.write_copy(plan, [c.slot for c in plan.characters])
    assert plan.target.read_bytes() == co2.read_bytes()


def test_blocked_character_is_refused(co2):
    plan = ec.make_plan("elden_ring", co2, ".sl2")
    with pytest.raises(ec.ExtensionCopyError):
        ec.write_copy(plan, [plan.blocked[0].slot])


def test_merge_fills_and_replaces_slots_and_keeps_the_rest(co2):
    ec.write_copy(ec.make_plan("elden_ring", co2, ".cnvco2"), [6, 7])
    plan = ec.make_plan("elden_ring", co2, ".cnvco2")
    assert plan.merges and [s for s, _ in plan.target_characters] == [6, 7]
    with pytest.raises(ec.ExtensionCopyError):
        ec.write_merge(plan, [(7, 0), (8, 0)])
    ec.write_merge(plan, [(8, 7), (6, 0)])
    assert list(plan.target.parent.glob("*.backups/*"))
    target = Save.from_file(str(plan.target))
    source = Save.from_file(str(co2))
    assert [i for i, s in enumerate(target.character_slots) if not s.is_empty()] == [
        0,
        6,
        7,
    ]
    assert (
        target.character_slots[7].get_character_name()
        == source.character_slots[8].get_character_name()
    )
    off_t, off_s = target.slot_data_offset(7), source.slot_data_offset(8)
    off_6t, off_6s = target.slot_data_offset(6), source.slot_data_offset(6)
    assert (
        target._raw_data[off_6t : off_6t + SLOT_SIZE]
        == source._raw_data[off_6s : off_6s + SLOT_SIZE]
    )
    assert (
        target._raw_data[off_t + 0x100 : off_t + 0x2000]
        == (source._raw_data[off_s + 0x100 : off_s + 0x2000])
    )


def test_non_pc_save_and_other_game_target_are_refused(tmp_path, co2):
    path = tmp_path / "ER0001.co2"
    path.write_bytes(bytes(64))
    with pytest.raises(ec.ExtensionCopyError):
        ec.make_plan("elden_ring", path, ".sl2")
    co2.with_name("ER0000.sl2").write_bytes(b"BND4" + b"\x00" * 64)
    with pytest.raises(ec.ExtensionCopyError):
        ec.make_plan("elden_ring", co2, ".sl2")
