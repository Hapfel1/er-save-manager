"""
Build or extend fixes/EventFlagBits.bin.

The bitmap holds every event flag bit found set in a structurally clean
Elden Ring slot. DeepScanFix scores candidate splice points against it, so
more clean characters mean fewer unknown bits on a healthy layout.

A slot counts as clean when the SteamID sits at its parsed offset and the
world struct chain (CHR / MOEG / FOEG) starts right after the parsed event
flags. Identical event flag arrays are counted once.

Usage:
    python scripts/build_event_flag_bits.py <save or folder> [...] [--merge]
        [--exclude <save>:<slot>] [--out PATH]

--merge ORs the result into the existing bitmap instead of replacing it.
--exclude keeps a character out, e.g. the corrupted save being tested, so
its own flags cannot make a wrong splice look clean.
"""

from __future__ import annotations

import argparse
import logging
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from er_save_manager.fixes.deep_scan import (  # noqa: E402
    _EVENT_FLAGS_SIZE,
    _EVENT_FLAGS_TERMINATOR,
    _world_chain_end,
)
from er_save_manager.parser import Save  # noqa: E402

DEFAULT_OUT = ROOT / "src" / "er_save_manager" / "fixes" / "EventFlagBits.bin"
SAVE_SUFFIXES = {".sl2", ".co2", ".cnv", ".bak"}
MIN_SAVE_SIZE = 20 * 1024 * 1024


def iter_saves(inputs: list[Path]):
    for path in inputs:
        if path.is_dir():
            for p in sorted(path.rglob("*")):
                if p.is_file() and p.suffix.lower() in SAVE_SUFFIXES:
                    if p.stat().st_size >= MIN_SAVE_SIZE:
                        yield p
        elif path.is_file():
            yield path


def clean_event_flags(save: Save, slot_index: int) -> bytes | None:
    """The slot's event flags when the slot is structurally clean, else None."""
    slot = save.character_slots[slot_index]
    if slot.is_empty():
        return None
    raw = save._raw_data
    steam_id = getattr(save.user_data_10_parsed, "steam_id", 0)
    if not steam_id:
        return None
    if struct.unpack_from("<Q", raw, slot.steamid_offset)[0] != steam_id:
        return None
    start = slot.data_start
    slot_raw = bytes(raw[start : start + 0x280000])
    ef_rel = slot.event_flags_offset - start
    ef_end = ef_rel + _EVENT_FLAGS_SIZE + _EVENT_FLAGS_TERMINATOR
    if _world_chain_end(slot_raw, ef_end) is None:
        return None
    return slot_raw[ef_rel : ef_rel + _EVENT_FLAGS_SIZE]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()

    logging.disable(logging.CRITICAL)
    excluded = set()
    for item in args.exclude:
        path, _, slot = item.rpartition(":")
        excluded.add((Path(path).resolve(), int(slot)))

    acc = 0
    if args.merge and args.out.is_file():
        acc = int.from_bytes(zlib.decompress(args.out.read_bytes()), "big")

    seen: set[bytes] = set()
    for path in iter_saves(args.inputs):
        try:
            save = Save.from_file(str(path))
        except Exception:
            continue
        for slot_index in range(len(save.character_slots)):
            if (path.resolve(), slot_index) in excluded:
                continue
            try:
                ef = clean_event_flags(save, slot_index)
            except Exception:
                continue
            if ef is None or ef in seen:
                continue
            seen.add(ef)
            acc |= int.from_bytes(ef, "big")

    data = acc.to_bytes(_EVENT_FLAGS_SIZE, "big")
    args.out.write_bytes(zlib.compress(data, 9))
    print(f"{len(seen)} clean slots, {acc.bit_count()} bits set -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
