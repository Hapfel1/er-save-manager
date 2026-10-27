"""Cut-off, empty and other-game files are refused before slot parsing."""

from __future__ import annotations

import struct

import pytest

from er_save_manager.games.save_identify import incomplete_reason
from er_save_manager.parser.save import Save


def test_whole_save_is_complete(sanitized_save_path):
    assert incomplete_reason(sanitized_save_path) is None


@pytest.mark.parametrize("keep", [0, 0x50, 0x100000, -0x10])
def test_cut_off_save_is_refused(sanitized_save_path, tmp_path, keep):
    data = sanitized_save_path.read_bytes()
    cut = tmp_path / "ER0000.sl2"
    cut.write_bytes(data[:keep])
    assert incomplete_reason(cut)
    with pytest.raises(ValueError):
        Save.from_file(str(cut))


def test_bnd4_of_another_game_is_refused(sanitized_save_path, tmp_path):
    data = bytearray(sanitized_save_path.read_bytes())
    # Entry 0 size of a Sekiro save.
    struct.pack_into("<Q", data, 0x48, 0x100010)
    other = tmp_path / "S0000.sl2"
    other.write_bytes(data)
    with pytest.raises(ValueError, match="Not an Elden Ring save"):
        Save.from_file(str(other))


def test_short_ps_save_is_refused(tmp_path):
    ps = tmp_path / "memory.dat"
    ps.write_bytes(bytes.fromhex("cb019c2c") + bytes(1000))
    assert incomplete_reason(ps)
    with pytest.raises(ValueError, match="Not a complete save file"):
        Save.from_file(str(ps))
