"""
dump_gaitems.py - Dump all non-empty gaitem map entries for a character slot.

Usage:
    python dump_gaitems.py <save_file> [slot_index]

Prints gaitem_handle, item_id, unk0x10, unk0x14, gem_gaitem_handle, unk0x1c
for every occupied entry. Useful for understanding upgrade level encoding
and verifying add/remove correctness.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
for _candidate in [SCRIPT_DIR, SCRIPT_DIR.parent, SCRIPT_DIR.parent.parent]:
    if (_candidate / "src").is_dir():
        sys.path.insert(0, str(_candidate / "src"))
        break
    if (_candidate / "er_save_manager").is_dir():
        sys.path.insert(0, str(_candidate))
        break


def main():
    if len(sys.argv) < 2:
        print("usage: python dump_gaitems.py <save_file> [slot_index]")
        sys.exit(1)

    save_path = Path(sys.argv[1]).resolve()
    slot_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None

    from er_save_manager.parser.save import Save

    save = Save.from_file(str(save_path))
    active = save.get_active_slots()

    slot_idx = slot_arg if slot_arg is not None else (active[0] if active else None)
    if slot_idx is None:
        print("ERROR: no active slots")
        sys.exit(1)

    slot = save.character_slots[slot_idx]
    print(f"slot {slot_idx}: {slot.player_game_data.character_name}")
    print(f"gaitem_map entries: {len(slot.gaitem_map)}")
    print()

    PREFIX = {
        0x80000000: "Weapon",
        0x90000000: "Armor ",
        0xA0000000: "Spell ",
        0xB0000000: "Direct",
        0xC0000000: "Gem   ",
    }

    fmt = "{:4d}  0x{:08X}  {:6s}  item=0x{:08X}  unk0x10={:10}  unk0x14={:10}  gem={}  unk0x1c={}"

    for i, g in enumerate(slot.gaitem_map):
        if g.gaitem_handle == 0:
            continue
        prefix = g.gaitem_handle & 0xF0000000
        prefix_name = PREFIX.get(prefix, f"0x{prefix:08X}")
        print(
            fmt.format(
                i,
                g.gaitem_handle,
                prefix_name,
                g.item_id,
                g.unk0x10 if g.unk0x10 is not None else "None",
                g.unk0x14 if g.unk0x14 is not None else "None",
                f"0x{g.gem_gaitem_handle & 0xFFFFFFFF:08X}"
                if g.gem_gaitem_handle is not None
                else "None",
                g.unk0x1c if g.unk0x1c is not None else "None",
            )
        )


if __name__ == "__main__":
    main()
