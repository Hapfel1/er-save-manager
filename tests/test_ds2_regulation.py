"""DS2 regulation fallback for saves whose regulation entry holds no params."""

from __future__ import annotations

import struct
import zlib

from er_save_manager.games.DS2.regulation import REGULATION_ENTRY, Regulation


class _Container:
    def __init__(self, entry: bytes) -> None:
        self._entry = entry

    def get_entry(self, index: int) -> bytes:
        assert index == REGULATION_ENTRY
        return self._entry


def _entry(payload: bytes) -> bytes:
    compressed = zlib.compress(payload)
    return struct.pack("<II", len(compressed), len(payload)) + compressed


def test_entry_without_params_falls_back_to_vanilla():
    regulation = Regulation.from_container(_Container(bytes(0x100)))
    assert len(regulation.boss_fights()) == len(Regulation.vanilla().boss_fights())
    # Not a BND4 archive, as read from the SpEffect EMEVD archive some saves hold.
    regulation = Regulation.from_container(_Container(_entry(b"BND3" + bytes(0x40))))
    assert regulation.class_base(30) is not None


def test_vanilla_tables():
    regulation = Regulation.vanilla()
    pursuer = next(f for f in regulation.boss_fights() if f.row_id == 1010000)
    # bonfireId: Cardinal Tower, the bonfire whose Ascetic respawns the Pursuer.
    assert pursuer.bonfire_id == 10655
    assert regulation.class_base(30).level == 13
    assert regulation.max_upgrade(1000000, "weapons") == 10
    assert regulation.durability(1000000) == 60.0
