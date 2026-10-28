"""Cut-off, empty and other-game files are refused before slot parsing."""

from __future__ import annotations

import struct

import pytest

from er_save_manager.games.save_identify import incomplete_reason, tail_cut_reason
from er_save_manager.parser.save import Save


def _write(tmp_path, data: bytes, name: str = "ER0000.sl2"):
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_whole_save_is_complete(sanitized_save_path):
    assert incomplete_reason(sanitized_save_path) is None
    assert tail_cut_reason(sanitized_save_path) is None


def test_cut_off_save_is_refused(sanitized_save_path, tmp_path):
    data = sanitized_save_path.read_bytes()
    count = struct.unpack_from("<I", data, 0xC)[0]
    last_entry = struct.unpack_from("<I", data, 0x40 + (count - 1) * 0x20 + 0x10)[0]
    for keep in (0, 0x50, 0x100000, last_entry - 0x10):
        cut = _write(tmp_path, data[:keep])
        assert incomplete_reason(cut), keep
        assert tail_cut_reason(cut) is None
        with pytest.raises(ValueError):
            Save.from_file(str(cut))


def test_cut_regulation_data_loads(sanitized_save_path, tmp_path):
    data = sanitized_save_path.read_bytes()
    names = [
        c.get_character_name()
        for c in Save.from_file(str(sanitized_save_path)).characters
    ]
    for cut in (0x10, 0xD4C):
        short = _write(tmp_path, data[:-cut])
        assert incomplete_reason(short) is None
        assert tail_cut_reason(short)
        save = Save.from_file(str(short))
        assert [c.get_character_name() for c in save.characters] == names


def test_other_files_are_refused(sanitized_save_path, tmp_path):
    data = bytearray(sanitized_save_path.read_bytes())
    # Entry 0 size of a Sekiro save
    struct.pack_into("<Q", data, 0x48, 0x100010)
    with pytest.raises(ValueError, match="Not an Elden Ring save"):
        Save.from_file(str(_write(tmp_path, data, "S0000.sl2")))

    ps = _write(tmp_path, bytes.fromhex("cb019c2c") + bytes(1000), "memory.dat")
    assert incomplete_reason(ps)
    with pytest.raises(ValueError, match="Not a complete save file"):
        Save.from_file(str(ps))
