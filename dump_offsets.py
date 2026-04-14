"""
dump_offsets.py - Print inventory offsets and gaitem_map size for a slot.

Run this before and after a game load to detect if the game changes the
gaitem_map (which would shift inventory_held_offset).

Usage:
    python dump_offsets.py <save_file> [slot_index]
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
        print("usage: python dump_offsets.py <save_file> [slot_index]")
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
    print(f"  version                  : {slot.version}")

    # Gaitem map serialized size
    gaitem_bytes = sum(g.get_size() for g in slot.gaitem_map)
    gaitem_count = sum(1 for g in slot.gaitem_map if g.gaitem_handle != 0)
    print(f"  gaitem_map entries       : {len(slot.gaitem_map)}")
    print(f"  gaitem_map occupied      : {gaitem_count}")
    print(f"  gaitem_map serialized    : {gaitem_bytes} bytes (0x{gaitem_bytes:X})")

    print(
        f"  inventory_held_offset    : {slot.inventory_held_offset} (0x{slot.inventory_held_offset:X})"
    )
    print(
        f"  inventory_storage_offset : {slot.inventory_storage_offset} (0x{slot.inventory_storage_offset:X})"
    )
    print(f"  inventory_held count     : {slot.inventory_held.common_item_count}")
    print(
        f"  inventory_held acq_ctr   : {slot.inventory_held.acquisition_index_counter}"
    )

    # Cross-check: verify the bytes at inventory_held_offset actually look like inventory
    slot_data_base = save._slot_offsets[slot_idx] + 0x10
    abs_off = slot_data_base + slot.inventory_held_offset
    raw_count = int.from_bytes(save._raw_data[abs_off : abs_off + 4], "little")
    print(
        f"  raw common_item_count at offset: {raw_count}  {'OK' if raw_count == slot.inventory_held.common_item_count else 'MISMATCH'}"
    )

    indices = sorted(
        g.gaitem_handle & 0x00FFFFFF for g in slot.gaitem_map if g.gaitem_handle != 0
    )
    if indices:
        print(f"  gaitem index range  : 0x{indices[0]:06X} - 0x{indices[-1]:06X}")


if __name__ == "__main__":
    main()
