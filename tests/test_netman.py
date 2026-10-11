"""CSNetMan chunk validation and repair."""

import struct

import pytest

from er_save_manager.fixes.netman import (
    NETMAN_SIZE,
    NetManFix,
    load_template,
    netman_problems,
    repair_netman,
)


def _region(save, slot_index):
    start = save.character_slots[slot_index].net_man_offset
    return start, bytes(save._raw_data[start : start + NETMAN_SIZE])


def _chunks(blob):
    """(type, chunk bytes) for each chunk in the chain, terminator excluded."""
    pos, out = 4, []
    while True:
        ctype, _, size = struct.unpack_from("<HHI", blob, pos)
        if ctype == 0xFFFF:
            return out
        out.append((ctype, blob[pos : pos + 8 + size]))
        pos += 8 + size


def _slots_with_netman(save):
    return [
        i
        for i, slot in enumerate(save.character_slots)
        if not slot.is_empty() and any(_region(save, i)[1])
    ]


@pytest.fixture
def template():
    data = load_template()
    assert data is not None
    return data


def test_template_is_valid(template):
    assert len(template) == NETMAN_SIZE
    assert netman_problems(template) == []


def test_game_written_netman_is_valid_and_unchanged(sanitized_save, template):
    slots = _slots_with_netman(sanitized_save)
    assert slots
    for i in slots:
        blob = _region(sanitized_save, i)[1]
        assert netman_problems(blob) == []
        assert repair_netman(blob, template) == (blob, [])
        assert NetManFix().detect(sanitized_save, i) is False


def test_damaged_chunk_is_rebuilt_and_neighbours_kept(sanitized_save, template):
    i = _slots_with_netman(sanitized_save)[0]
    start, blob = _region(sanitized_save, i)
    # Chunk 6 starts after chunks 2 and 5 (u32 2, then two 16-byte chunks)
    chunk6 = 4 + 32
    size = struct.unpack_from("<I", blob, chunk6 + 4)[0]
    damaged = bytearray(blob)
    struct.pack_into("<I", damaged, chunk6 + 4, size + 0x40)
    sanitized_save._raw_data[start : start + NETMAN_SIZE] = damaged

    fix = NetManFix()
    assert fix.detect(sanitized_save, i) is True
    result = fix.apply(sanitized_save, i)
    assert result.applied is True

    repaired = bytes(sanitized_save._raw_data[start : start + NETMAN_SIZE])
    assert netman_problems(repaired) == []
    old = dict(_chunks(blob))
    rebuilt = dict(_chunks(repaired))
    assert rebuilt[6] == dict(_chunks(template))[6]
    for ctype in (2, 5, 8, 9, 7):
        assert rebuilt[ctype] == old[ctype]
    assert fix.detect(sanitized_save, i) is False


def test_torn_region_of_any_length_is_rebuilt(template):
    for torn in (template[:100], template + bytes(64), template[:40] + template[60:]):
        repaired, _ = repair_netman(torn, template)
        assert len(repaired) == NETMAN_SIZE
        assert netman_problems(repaired) == []
