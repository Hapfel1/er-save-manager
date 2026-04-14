"""
dump_inventory.py - Dump full held and storage inventory for a slot.

Usage:
    python dump_inventory.py <save_file> [slot_index]
"""

from __future__ import annotations

import struct
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


def dump_inv(label, inventory, gaitem_map):
    handle_to_gaitem = {g.gaitem_handle: g for g in gaitem_map if g.gaitem_handle != 0}

    print(f"\n=== {label} ===")
    print(f"  common_item_count  : {inventory.common_item_count}")
    print(f"  acq_index_counter  : {inventory.acquisition_index_counter}")
    print(f"  equip_index_counter: {inventory.equip_index_counter}")
    print()

    used = [
        (i, it) for i, it in enumerate(inventory.common_items) if it.gaitem_handle != 0
    ]
    print(f"  {len(used)} non-zero slots:")

    for i, it in used:
        prefix = (it.gaitem_handle >> 28) & 0xF
        g = handle_to_gaitem.get(it.gaitem_handle)
        raw = struct.pack("<III", it.gaitem_handle, it.quantity, it.acquisition_index)

        if g:
            item_info = f"item_id=0x{g.item_id:08X}  unk0x10={g.unk0x10}"
        else:
            item_info = "(no gaitem entry - direct handle)"

        print(
            f"    [{i:4d}] 0x{it.gaitem_handle:08X}  prefix=0x{prefix:X}"
            f"  qty={it.quantity:5d}  acq={it.acquisition_index:6d}"
            f"  raw={raw.hex()}  {item_info}"
        )


def main():
    if len(sys.argv) < 2:
        print("usage: python dump_inventory.py <save_file> [slot_index]")
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

    dump_inv("HELD INVENTORY", slot.inventory_held, slot.gaitem_map)
    dump_inv("STORAGE BOX", slot.inventory_storage_box, slot.gaitem_map)


if __name__ == "__main__":
    main()
