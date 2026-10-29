"""Nightreign battle records: read and write through the offsets derived from
the loadout chunk end."""

from __future__ import annotations

import struct
from types import SimpleNamespace

from er_save_manager.games.NR import character_ops as co
from er_save_manager.games.NR import records as r

LOADOUT_OFFSET = 0x100
CHUNK_SIZE = 0x40
END = LOADOUT_OFFSET + 8 + CHUNK_SIZE
FARERS = END + r._NIGHTFARER_REL
LORDS = FARERS + r._NIGHTLORD_REL


def _slot(heroes: int = 10) -> SimpleNamespace:
    dec = bytearray(LORDS + 8 + 10 * 12 + 16)
    base = END + r._RECORDS_REL
    struct.pack_into("<III", dec, base, 833_827_117, 390, 187)
    struct.pack_into("<I", dec, base + r._DEPTHS_BLOCK + 0x64, 173_926_757)
    struct.pack_into("<I", dec, FARERS, heroes)
    for i in range(heroes):
        e = FARERS + 4 + i * 12
        dec[e] = i + 1
        struct.pack_into("<II", dec, e + 4, 39, 18)
    struct.pack_into("<I", dec, LORDS, 10)
    for i in range(10):
        struct.pack_into("<III", dec, LORDS + 8 + i * 12, i + 10, 0, i + 1)
    return SimpleNamespace(
        decrypted=dec,
        loadout=SimpleNamespace(offset=LOADOUT_OFFSET, chunk_size=CHUNK_SIZE),
    )


def test_reads_summary_fields_and_tables():
    rec = r.read_records(_slot())
    assert rec.values["expedition_time"] == 833_827_117
    assert rec.values["total_expeditions"] == 390
    assert rec.values["wins"] == 187
    assert rec.values["depths_runes_acquired"] == 173_926_757
    assert [f.name for f in rec.nightfarers][:3] == ["Wylder", "Guardian", "Ironeye"]
    assert rec.nightfarers[2].expeditions == 39
    assert rec.nightlords[7].name == "Heolstor the Nightlord"
    assert rec.nightlords[7].wins == 17


def test_modded_hero_count_keeps_the_nightlord_table_in_place():
    rec = r.read_records(_slot(heroes=13))
    assert len(rec.nightfarers) == 13
    assert rec.nightfarers[12].name == "Hero 13"
    assert [lord.wins for lord in rec.nightlords] == list(range(10, 20))


def test_table_with_unexpected_hero_ids_is_not_read():
    slot = _slot()
    slot.decrypted[FARERS + 4 + 12] = 7
    rec = r.read_records(slot)
    assert rec.nightfarers == [] and rec.nightlords == []
    assert rec.values["wins"] == 187


def test_no_loadout_chunk_means_no_records():
    slot = _slot()
    slot.loadout = None
    assert r.read_records(slot) is None


def test_write_round_trip_touches_only_the_edited_fields():
    slot = _slot()
    before = bytes(slot.decrypted)
    rec = r.read_records(slot)
    farers = [(f.expeditions, f.wins) for f in rec.nightfarers]
    farers[0] = (50, 25)
    lords = [lord.wins for lord in rec.nightlords]
    lords[1] = 99
    r.write_records(slot, rec, {"wins": 200}, farers, lords)
    again = r.read_records(slot)
    assert again.values["wins"] == 200
    assert again.values["total_expeditions"] == 390
    assert (again.nightfarers[0].expeditions, again.nightfarers[0].wins) == (50, 25)
    assert again.nightlords[1].wins == 99
    changed = [
        i for i, (a, b) in enumerate(zip(before, slot.decrypted, strict=True)) if a != b
    ]
    allowed = set(range(rec.base + 8, rec.base + 12))
    allowed |= set(range(FARERS + 8, FARERS + 16))
    allowed |= set(range(LORDS + 8 + 12, LORDS + 8 + 16))
    assert set(changed) <= allowed


def test_play_time_sync_writes_seconds_into_the_summary():
    glob = bytearray(co._summary_span(9).stop)
    slot = SimpleNamespace(play_time_ms=1_066_078_423)
    save = SimpleNamespace(
        slots=[slot], entries=[None] * 10 + [SimpleNamespace(decrypted=glob)]
    )
    co.sync_summary_play_time(save, 0)
    start = co._summary_span(0).start + co._SUMMARY_PLAY_TIME
    assert struct.unpack_from("<I", glob, start)[0] == 1_066_078
