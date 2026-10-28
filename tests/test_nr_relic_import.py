"""Relic JSON import row checks and rollback (games/NR/relic_ops.py)."""

import pytest

from er_save_manager.games.NR.parser import _parse_slot
from er_save_manager.games.NR.relic_ops import (
    ids_problem,
    rollback_on_error,
    sort_import_rows,
)

E = 0xFFFFFFFF
# Grand Luminous Scene, three normal effects.
GRAND = {"id": 1007222, "effects": [7060100, 7090100, 7001702], "curses": [E, E, E]}
BAD_ROWS = [
    dict(GRAND, effects=[-1, 7090100, 7001702]),
    dict(GRAND, curses=[2**32, E, E]),
    dict(GRAND, id=99999999),
    dict(GRAND, id=-5),
    dict(GRAND, id=1007222.9),
    dict(GRAND, id="1007222"),
    dict(GRAND, id=True),
    dict(GRAND, effects="123"),
    dict(GRAND, effects=[7060100, 7090100, 7001702, 7000000]),
    {"effects": GRAND["effects"]},
    [1, 2, 3],
    5,
]


def test_import_rows():
    assert sort_import_rows([GRAND]) == (
        [(GRAND["id"], GRAND["effects"], GRAND["curses"])],
        [],
        [],
    )
    for row in BAD_ROWS:
        relics, skipped, _ = sort_import_rows([row, GRAND])
        assert len(relics) == 1, row
        assert len(skipped) == 1 and skipped[0].startswith("Row 1: "), row
    assert sort_import_rows([{"id": 123456}])[1] == ["Row 1: Unknown relic ID 123456."]
    # An unknown effect only warns
    relics, skipped, warnings = sort_import_rows(
        [dict(GRAND, effects=[7060100, 7090100, 123])]
    )
    assert len(relics) == 1 and skipped == [] and warnings


def test_ids_problem_names_the_field():
    assert "Effect 2" in ids_problem(GRAND["id"], [1, -1, E], [E, E, E])
    assert "Curse 1" in ids_problem(GRAND["id"], [E, E, E], [2**32, E, E])
    assert ids_problem(GRAND["id"], GRAND["effects"], GRAND["curses"]) is None


def test_rollback_restores_slot_bytes():
    slot = _parse_slot(bytearray(0x100000), 0)
    before = bytes(slot.decrypted)
    buffer = slot.decrypted
    with pytest.raises(RuntimeError), rollback_on_error(slot):
        slot.decrypted[0x20:0x20] = b"\x01" * 72
        raise RuntimeError("spawn failed")
    assert bytes(slot.decrypted) == before
    assert slot.decrypted is buffer
