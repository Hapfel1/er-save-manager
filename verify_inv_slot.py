"""
verify_inv_slot.py - Read a specific inventory slot's raw bytes from disk.

Usage:
    python verify_inv_slot.py <save_file> [slot_index] [inv_slot]

Reads and displays the raw bytes of a specific inventory slot to verify
what was written, independent of the parser.
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


def main():
    if len(sys.argv) < 2:
        print("usage: python verify_inv_slot.py <save_file> [char_slot] [inv_slot]")
        sys.exit(1)

    save_path = Path(sys.argv[1]).resolve()
    char_slot = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    inv_target = int(sys.argv[3]) if len(sys.argv) > 3 else None

    from er_save_manager.parser.save import Save

    save = Save.from_file(str(save_path))
    slot = save.character_slots[char_slot]

    if slot.is_empty():
        print(f"slot {char_slot} is empty")
        sys.exit(1)

    inv = slot.inventory_held
    print(f"slot {char_slot}: {slot.player_game_data.character_name}")
    print(f"common_item_count : {inv.common_item_count}")
    print(f"acq_index_counter : {inv.acquisition_index_counter}")
    print(f"total common slots: {len(inv.common_items)}")
    print()

    # Dump all non-zero slots plus context around target
    targets = set()
    if inv_target is not None:
        targets = {
            max(0, inv_target - 2),
            max(0, inv_target - 1),
            inv_target,
            inv_target + 1,
            inv_target + 2,
        }

    print("Non-zero slots (and context around target if specified):")
    for i, it in enumerate(inv.common_items):
        show = it.gaitem_handle != 0 or i in targets
        if not show:
            continue
        raw = struct.pack("<III", it.gaitem_handle, it.quantity, it.acquisition_index)
        marker = " <-- TARGET" if i == inv_target else ""
        empty = " (EMPTY)" if it.gaitem_handle == 0 else ""
        print(
            f"  [{i:4d}] handle=0x{it.gaitem_handle:08X}  qty={it.quantity:5d}"
            f"  acq={it.acquisition_index:6d}  raw={raw.hex()}{marker}{empty}"
        )

    # Also check the slot rebuild matches what's on disk
    from er_save_manager.parser.slot_rebuild import rebuild_slot

    rebuilt = rebuild_slot(slot)
    slot_offset = save._slot_offsets[char_slot]
    on_disk = bytes(
        save._raw_data[slot_offset + 0x10 : slot_offset + 0x10 + len(rebuilt)]
    )

    if rebuilt == on_disk:
        print("\nrebuild matches disk: YES")
    else:
        # Find first difference
        for i, (a, b) in enumerate(zip(rebuilt, on_disk, strict=False)):
            if a != b:
                print(f"\nrebuild matches disk: NO (first diff at byte {i} = 0x{i:X})")
                print(f"  rebuilt: {rebuilt[max(0, i - 4) : i + 8].hex()}")
                print(f"  on_disk: {on_disk[max(0, i - 4) : i + 8].hex()}")
                break


if __name__ == "__main__":
    main()
