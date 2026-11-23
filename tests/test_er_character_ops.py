"""Elden Ring character copy, swap, export and import."""

import pytest

from er_save_manager.parser.save import Save
from er_save_manager.transfer.character_ops import CharacterOperations as ops


def _identity(save: Save, slot: int) -> tuple:
    meta = ops.extract_character_metadata(save, slot)
    return meta["level"], meta["class"], meta["body_type"], meta["stats"]


def test_copy_swap_export_import_survive_reload(sanitized_save_copy, tmp_path):
    save = Save.from_file(str(sanitized_save_copy))
    before = {i: _identity(save, i) for i in range(5)}

    ops.copy_slot(save, 0, 4)
    ops.swap_slots(save, 1, 2)
    erc = tmp_path / "slot3.erc"
    ops.export_character(save, 3, str(erc))
    ops.import_character(save, 0, str(erc))
    save.to_file(str(sanitized_save_copy))

    reloaded = Save.from_file(str(sanitized_save_copy))
    assert _identity(reloaded, 4) == before[0]
    assert _identity(reloaded, 1) == before[2]
    assert _identity(reloaded, 2) == before[1]
    assert _identity(reloaded, 0) == before[3]

    erc.write_bytes(erc.read_bytes()[:100])
    with pytest.raises(ValueError):
        ops.read_erc(str(erc))
