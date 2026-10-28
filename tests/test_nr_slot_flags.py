"""Nightreign slot operations keep the global in-use flags and load-screen
summaries in step with the slot data."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from er_save_manager.games.NR import character_ops as co

SLOT_SIZE = 64
HEADER = bytes.fromhex("10001000")


def _summary(save, i: int) -> bytes:
    return bytes(save.entries[10].decrypted[co._summary_span(i)])


@pytest.fixture
def save(monkeypatch):
    monkeypatch.setattr(
        co,
        "_parse_slot",
        lambda data, i: SimpleNamespace(
            is_empty=lambda: not any(data[4:]),
            player_name="Hapfel",
            steam_id_offset=-1,
        ),
    )
    entries = [
        SimpleNamespace(decrypted=bytearray(HEADER + bytes(SLOT_SIZE - 4)))
        for _ in range(10)
    ]
    entries[0].decrypted[8] = 1
    glob = bytearray(co._summary_span(9).stop)
    glob[co._E10_SLOT_IN_USE] = 1
    glob[co._summary_span(0)] = b"\x01" * co._E10_SUMMARY_STRIDE
    glob[co._summary_span(1)] = b"\x02" * co._E10_SUMMARY_STRIDE
    entries.append(SimpleNamespace(decrypted=glob))
    s = SimpleNamespace(entries=entries, is_ps=False, profile=None)
    s.slots = [co._parse_slot(e.decrypted, i) for i, e in enumerate(entries[:10])]
    return s


def test_copy_marks_the_slot_in_use_and_copies_the_summary(save):
    co.copy_slot(save, 0, 3)
    assert save.entries[10].decrypted[co._E10_SLOT_IN_USE + 3] == 1
    assert _summary(save, 3) == _summary(save, 0)


def test_delete_matches_a_game_made_empty_slot(save):
    empty_summary = _summary(save, 1)
    co.delete_slot(save, 0)
    assert bytes(save.entries[0].decrypted) == HEADER + bytes(SLOT_SIZE - 4)
    assert save.entries[10].decrypted[co._E10_SLOT_IN_USE] == 0
    assert _summary(save, 0) == empty_summary


def test_swap_moves_flags_and_summaries(save):
    first = _summary(save, 0)
    co.swap_slots(save, 0, 4)
    assert save.entries[10].decrypted[co._E10_SLOT_IN_USE + 4] == 1
    assert save.entries[10].decrypted[co._E10_SLOT_IN_USE] == 0
    assert _summary(save, 4) == first
