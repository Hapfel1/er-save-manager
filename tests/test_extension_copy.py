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


@pytest.mark.parametrize(
    ("name", "ext", "expected"),
    [
        ("ER0000.co2", ".sl2", "ER0000.sl2"),
        ("ER0000.cnv.co2", ".cnvco2", "ER0000.cnvco2"),
        ("ER0000.cnvco2", ".cnv", "ER0000.cnv"),
        ("ER0000mine.sl2", ".co2", "ER0000mine.co2"),
    ],
)
def test_target_path(name, ext, expected):
    assert ec.target_path(Path("/x") / name, ext).name == expected


def test_seamless_items_block_vanilla_target(co2):
    plan = ec.make_plan("elden_ring", co2, ".sl2")
    blocked = {c.slot for c in plan.blocked}
    assert blocked and 1 not in blocked
    assert all(
        b.startswith("Seamless Co-op items") for c in plan.blocked for b in c.blockers
    )


def test_seamless_items_allowed_for_convergence_target(co2):
    plan = ec.make_plan("elden_ring", co2, ".cnv")
    assert not any("Seamless" in b for c in plan.characters for b in c.blockers)


@pytest.mark.parametrize(
    ("ext", "convergence"), [("co3", False), (".CO3", False), (".cnv.co3", True)]
)
def test_custom_extension(co2, ext, convergence):
    plan = ec.make_plan("elden_ring", co2, ext)
    assert plan.target.name == "ER0000." + ext.lower().lstrip(".")
    assert plan.target_flavor.seamless
    assert plan.target_flavor.convergence is convergence


@pytest.mark.parametrize("ext", [".bak", ".co2.bak", ".a b", "", ".cnv"])
def test_bad_custom_extension_is_refused(co2, ext):
    with pytest.raises(ec.ExtensionCopyError):
        ec.make_plan("dark_souls_3" if ext == ".cnv" else "elden_ring", co2, ext)


def test_unsupported_game_is_refused(co2):
    with pytest.raises(ec.ExtensionCopyError):
        ec.make_plan("sekiro", co2, ".co2")


def test_upgrades_above_cap_block_convergence_target(co2):
    plan = ec.make_plan("elden_ring", co2, ".cnvco2")
    assert {c.slot for c in plan.copyable} == {6, 7, 8}
    assert all("above +15" in c.blockers[0] for c in plan.blocked)


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


def test_merge_fills_free_slots_and_keeps_target(co2):
    first = ec.make_plan("elden_ring", co2, ".cnvco2")
    ec.write_copy(first, [7])
    plan = ec.make_plan("elden_ring", co2, ".cnvco2")
    assert plan.merges and [s for s, _ in plan.target_characters] == [7]
    ec.write_merge(plan, [(6, 0), (8, 1)])
    assert _occupied(plan.target) == [0, 1, 7]
    assert list(plan.target.parent.glob("*.backups/*"))


def test_merge_replaces_one_character(co2):
    ec.write_copy(ec.make_plan("elden_ring", co2, ".cnvco2"), [6, 7])
    plan = ec.make_plan("elden_ring", co2, ".cnvco2")
    ec.write_merge(plan, [(8, 7)])
    target = Save.from_file(str(plan.target))
    source = Save.from_file(str(co2))
    assert _occupied(plan.target) == [6, 7]
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


def test_merge_refuses_two_characters_in_one_slot(co2):
    ec.write_copy(ec.make_plan("elden_ring", co2, ".cnvco2"), [6])
    plan = ec.make_plan("elden_ring", co2, ".cnvco2")
    with pytest.raises(ec.ExtensionCopyError):
        ec.write_merge(plan, [(7, 0), (8, 0)])


def test_non_pc_save_is_refused(tmp_path):
    path = tmp_path / "ER0000.co2"
    path.write_bytes(b"\x00" * 64)
    with pytest.raises(ec.ExtensionCopyError):
        ec.make_plan("elden_ring", path, ".sl2")


def test_target_of_another_game_is_refused(co2):
    co2.with_name("ER0000.sl2").write_bytes(b"BND4" + b"\x00" * 64)
    with pytest.raises(ec.ExtensionCopyError):
        ec.make_plan("elden_ring", co2, ".sl2")
