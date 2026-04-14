"""
test_inventory.py - Inventory add/set_quantity/remove test for all categories.

Usage:
    python test_inventory.py <save_file> [slot_index] [suite]

  suite:
    basic    - one item per category (default)
    multi    - add 3 weapons + 3 armor + 3 gems simultaneously, verify no overwrite
    all      - run basic then multi

Basic tests:
  0  Goods/held     Neutralizing Boluses
  1  Goods/storage  Stanching Boluses
  2  Talisman       Arsenal Charm         (base_id 1030, no goods conflict)
  3  Armor          Kaiden Helm
  4  Weapon         Dagger +5             (base_id + upgrade encoded in item_id)
  5  Gem/AoW        Ash of War: Lion's Claw

Multi test:
  Adds 3 weapons, 3 armor pieces, 3 AoWs in one pass, verifies all handles are
  distinct and no existing items were overwritten, then removes all 9.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
for _candidate in [SCRIPT_DIR, SCRIPT_DIR.parent, SCRIPT_DIR.parent.parent]:
    if (_candidate / "src").is_dir():
        sys.path.insert(0, str(_candidate / "src"))
        break
    if (_candidate / "er_save_manager").is_dir():
        sys.path.insert(0, str(_candidate))
        break

# ---------------------------------------------------------------------------
# Basic test suite
# (label, full_item_id, qty_add, qty_mod, location, upgrade, stackable)
# ---------------------------------------------------------------------------
BASIC_TESTS = [
    ("Goods/held", 0x40000384, 10, 25, "held", 0, True),  # Neutralizing Boluses
    ("Goods/storage", 0x4000038E, 5, 15, "storage", 0, True),  # Stanching Boluses
    # Talisman omitted: game validates talismans via event flags, rejects unearned ones
    ("Armor", 0x1000C350, 1, 1, "held", 0, False),  # Kaiden Helm
    (
        "Weapon",
        0x003085E0,
        1,
        1,
        "held",
        1,
        False,
    ),  # Claymore +1 (Sam owns this, base 3180000)
    (
        "Gem/AoW",
        0x80002774,
        1,
        1,
        "held",
        0,
        False,
    ),  # Ash of War: Impaling Thrust (Sam owns this)
]

# ---------------------------------------------------------------------------
# Multi-add test items - 3 weapons, 3 armor, 3 gems
# All chosen to be absent on a typical save.
# ---------------------------------------------------------------------------
MULTI_WEAPONS = [
    (0x003085E0, "Claymore"),  # base 3180000, Sam owns this
    (0x001E8480, "Uchigatana"),  # Sam owns this
    (0x0112A880, "Moonveil"),  # Sam owns this
]
MULTI_ARMOR = [
    (0x10009C40, "Iron Helmet"),  # base 40000
    (0x10009CA4, "Scale Armor"),  # base 40100
    (0x10009D08, "Iron Gauntlets"),  # base 40200
]
MULTI_GEMS = [
    (0x80002774, "Ash of War: Impaling Thrust"),  # Sam owns this
    (0x800078B4, "Ash of War: Stamp (Upward Cut)"),  # Sam owns this
    (0x8000EBF0, "Ash of War: Carian Grandeur"),  # Sam owns this
]

CHECKSUM_SIZE = 0x10
SLOT_DATA_SIZE = 0x280000
_slot_idx = 0
_Save = None


def _md5(data):
    return hashlib.md5(data).hexdigest()


def dump_checksum(save, label=""):
    offset = save._slot_offsets[_slot_idx]
    data = save._raw_data[
        offset + CHECKSUM_SIZE : offset + CHECKSUM_SIZE + SLOT_DATA_SIZE
    ]
    stored = save._raw_data[offset : offset + CHECKSUM_SIZE].hex()
    comp = _md5(data)
    status = "OK" if stored == comp else "MISMATCH"
    print(f"  [{label}] checksum: {stored[:16]}...  [{status}]")


def find_item_by_handle(save, handle, location):
    slot = save.character_slots[_slot_idx]
    inv = slot.inventory_held if location == "held" else slot.inventory_storage_box
    for it in inv.common_items:
        if it.gaitem_handle == handle:
            return it
    return None


def find_gaitem(save, handle):
    for i, g in enumerate(save.character_slots[_slot_idx].gaitem_map):
        if g.gaitem_handle == handle:
            return i, g
    return -1, None


def commit(save, save_path, label):
    save.recalculate_checksums()
    save.to_file(str(save_path))
    s2 = _Save.from_file(str(save_path))
    dump_checksum(s2, label=label)
    return s2


def pause(msg):
    try:
        input(f"    {msg} > ")
        return True
    except (KeyboardInterrupt, EOFError):
        print("    (skipped)")
        return False


def _resolve_handle(save, full_item_id):
    from er_save_manager.parser.inventory_ops import _direct_handle, _needs_gaitem

    if _needs_gaitem(full_item_id):
        for g in save.character_slots[_slot_idx].gaitem_map:
            if g.item_id == full_item_id and g.gaitem_handle != 0:
                return g.gaitem_handle
        return None
    return _direct_handle(full_item_id)


# ---------------------------------------------------------------------------
# Basic single-item test
# ---------------------------------------------------------------------------


def run_basic_test(
    label, full_item_id, qty_add, qty_mod, location, upgrade, stackable, save_path
):
    from er_save_manager.parser.inventory_ops import add_item, remove_item, set_quantity

    cat_name = {
        0x00000000: "Weapon",
        0x10000000: "Armor",
        0x20000000: "Talisman",
        0x40000000: "Goods",
        0x80000000: "Gem",
    }.get(full_item_id & 0xF0000000, "?")

    print(f"\n{'=' * 60}")
    print(
        f"TEST: {label}  [{cat_name}]  0x{full_item_id:08X}  loc={location}  upg={upgrade}  stackable={stackable}"
    )
    print(f"{'=' * 60}")

    save = _Save.from_file(str(save_path))
    slot = save.character_slots[_slot_idx]
    inv = slot.inventory_held if location == "held" else slot.inventory_storage_box
    print(
        f"  pre: item_count={inv.common_item_count}  held_acq_ctr={slot.inventory_held.acquisition_index_counter}"
    )

    handle = None
    try:
        r = add_item(save, _slot_idx, full_item_id, qty_add, location, upgrade)
        handle = r["gaitem_handle"]
        save = commit(save, save_path, label="add")

        # For gaitem items, also print unk0x10 to diagnose upgrade encoding
        if "gaitem_slot" in r:
            _, g = find_gaitem(save, handle)
            if g:
                print(
                    f"  gaitem: slot={r['gaitem_slot']} size={r['gaitem_size']} unk0x10={g.unk0x10} unk0x14={g.unk0x14}",
                    end="",
                )
                if g.gem_gaitem_handle is not None:
                    print(f" gem=0x{g.gem_gaitem_handle:08X}", end="")
                print()

        it = find_item_by_handle(save, handle, location)
        if it:
            print(
                f"  ADD PASS: handle=0x{handle:08X}  inv_slot={r['inventory_slot']}  qty={it.quantity}  acq={it.acquisition_index}"
            )
        else:
            print("  ADD FAIL: not found after write")
            return False

        print("  Load in-game. Confirm item appears.")
        if pause("ENTER after confirming"):
            time.sleep(0.5)
            save = _Save.from_file(str(save_path))
            it2 = find_item_by_handle(save, handle, location)
            print(f"  after game load: qty={it2.quantity if it2 else 'MISSING'}")
            if not it2 or it2.quantity == 0:
                print("  GAME REJECTED - stopping test")
                return False

    except ValueError as e:
        if "already present" in str(e) or "already in use" in str(e):
            print("  item already present - skipping add")
            save = _Save.from_file(str(save_path))
            handle = _resolve_handle(save, full_item_id)
            if handle is None:
                print("  cannot resolve handle, skipping")
                return False
        else:
            print(f"  ADD ERROR: {e}")
            return False

    if stackable:
        save = _Save.from_file(str(save_path))
        try:
            set_quantity(save, _slot_idx, full_item_id, qty_mod, location)
            save = commit(save, save_path, label="set_qty")
            it = find_item_by_handle(save, handle, location)
            if it and it.quantity == qty_mod:
                print(f"  SET_QTY PASS: qty={it.quantity}")
            else:
                print(
                    f"  SET_QTY FAIL: expected {qty_mod} got {it.quantity if it else 'MISSING'}"
                )
        except ValueError as e:
            print(f"  SET_QTY ERROR: {e}")

        print(f"  Load in-game. Confirm qty={qty_mod}.")
        if pause("ENTER after confirming"):
            time.sleep(0.5)
            save = _Save.from_file(str(save_path))
            it = find_item_by_handle(save, handle, location)
            print(f"  after game load: qty={it.quantity if it else 'MISSING'}")

    save = _Save.from_file(str(save_path))
    try:
        rem = remove_item(save, _slot_idx, full_item_id, location)
        save = commit(save, save_path, label="remove")
        it = find_item_by_handle(save, handle, location)
        _, g = find_gaitem(save, handle)
        inv_gone = not it or it.quantity == 0
        gaitem_gone = g is None or g.gaitem_handle == 0
        if inv_gone and gaitem_gone:
            print(
                f"  REMOVE PASS: slot={rem['inventory_slot']} qty={rem['old_quantity']}"
            )
        else:
            if not inv_gone:
                print(f"  REMOVE FAIL (inv): still present qty={it.quantity}")
            if not gaitem_gone:
                print("  REMOVE FAIL (gaitem): entry still present")
    except ValueError as e:
        print(f"  REMOVE ERROR: {e}")
        return False

    print("  Load in-game. Confirm item is gone.")
    if pause("ENTER after confirming"):
        time.sleep(0.5)
        save = _Save.from_file(str(save_path))
        it = find_item_by_handle(save, handle, location)
        if not it or it.quantity == 0:
            print("  REMOVE GAME PASS")
        else:
            print(f"  REMOVE GAME FAIL: still present qty={it.quantity}")

    return True


# ---------------------------------------------------------------------------
# Multi-add test: add all 9 items, verify, game load, remove all
# ---------------------------------------------------------------------------


def run_multi_test(save_path):
    from er_save_manager.parser.inventory_ops import add_item, remove_item

    print(f"\n{'=' * 60}")
    print("MULTI-ADD TEST: 3 weapons + 3 armor + 3 gems simultaneously")
    print(f"{'=' * 60}")

    all_items = (
        [(full_id, name, "Weapon") for full_id, name in MULTI_WEAPONS]
        + [(full_id, name, "Armor") for full_id, name in MULTI_ARMOR]
        + [(full_id, name, "Gem") for full_id, name in MULTI_GEMS]
    )

    # Snapshot existing gaitem handles before any adds
    save = _Save.from_file(str(save_path))
    pre_handles = {
        g.gaitem_handle
        for g in save.character_slots[_slot_idx].gaitem_map
        if g.gaitem_handle != 0
    }
    pre_inv_handles = {
        it.gaitem_handle
        for it in save.character_slots[_slot_idx].inventory_held.common_items
        if it.gaitem_handle != 0
    }
    print(
        f"  pre: {len(pre_handles)} occupied gaitem slots, {len(pre_inv_handles)} held inv slots"
    )

    # Add all items
    added = []  # (full_id, handle, name, cat)
    for full_id, name, cat in all_items:
        save = _Save.from_file(str(save_path))
        try:
            r = add_item(save, _slot_idx, full_id, 1, "held", 0)
            save.recalculate_checksums()
            save.to_file(str(save_path))
            added.append((full_id, r["gaitem_handle"], name, cat))
            print(
                f"  ADD: {name:35s} handle=0x{r['gaitem_handle']:08X}  gaitem_slot={r.get('gaitem_slot', 'N/A')}"
            )
        except ValueError as e:
            print(f"  ADD FAIL: {name}: {e}")

    # Verify all handles are distinct and no pre-existing items were overwritten
    print("\n  --- Verification ---")
    save = _Save.from_file(str(save_path))
    dump_checksum(save, label="post-all-adds")

    new_handles = {h for _, h, _, _ in added}
    handle_collisions = new_handles & pre_handles
    if handle_collisions:
        print(
            f"  FAIL: {len(handle_collisions)} new handles collide with pre-existing gaitem entries:"
        )
        for h in sorted(handle_collisions):
            print(f"    0x{h:08X}")
    else:
        print(
            f"  PASS: all {len(new_handles)} new handles are distinct from pre-existing entries"
        )

    if len(new_handles) != len(added):
        print(
            f"  FAIL: duplicate handles among newly added items ({len(added)} items, {len(new_handles)} unique handles)"
        )
    else:
        print(f"  PASS: all {len(added)} new items have unique handles")

    # Verify all items present in inventory and gaitem map
    all_ok = True
    for _full_id, handle, name, _cat in added:
        it = find_item_by_handle(save, handle, "held")
        gi, g = find_gaitem(save, handle)
        in_inv = it is not None and it.quantity > 0
        in_gaitem = g is not None and g.gaitem_handle != 0

        if in_inv and in_gaitem:
            inv_slot = next(
                (
                    i
                    for i, x in enumerate(
                        save.character_slots[_slot_idx].inventory_held.common_items
                    )
                    if x.gaitem_handle == handle
                ),
                -1,
            )
            print(
                f"  PRESENT: {name:35s} handle=0x{handle:08X}  inv_slot={inv_slot}  gaitem_slot={gi}"
            )
        else:
            print(
                f"  MISSING: {name:35s} handle=0x{handle:08X}  inv={in_inv}  gaitem={in_gaitem}"
            )
            all_ok = False

    if all_ok:
        print(f"\n  PASS: all {len(added)} items present and accounted for")

    print(
        "\n  Load in-game. Check that all 9 items appear (3 weapons, 3 armor, 3 AoW)."
    )
    print(
        "  Verify none of your existing weapons/armor/gems were replaced or corrupted."
    )
    if pause("ENTER after confirming"):
        time.sleep(0.5)
        save = _Save.from_file(str(save_path))
        missing_after = []
        for _full_id, handle, name, _cat in added:
            it = find_item_by_handle(save, handle, "held")
            if not it or it.quantity == 0:
                missing_after.append(name)
        if missing_after:
            print(f"  GAME REJECTED: {missing_after}")
        else:
            print(f"  GAME PASS: all {len(added)} items survived game load")

    # Remove all
    print(f"\n  --- Removing all {len(added)} items ---")
    remove_ok = 0
    for full_id, _handle, name, _cat in added:
        save = _Save.from_file(str(save_path))
        try:
            remove_item(save, _slot_idx, full_id, "held")
            save.recalculate_checksums()
            save.to_file(str(save_path))
            remove_ok += 1
            print(f"  REMOVED: {name}")
        except ValueError as e:
            print(f"  REMOVE FAIL: {name}: {e}")

    save = _Save.from_file(str(save_path))
    dump_checksum(save, label="post-all-removes")

    # Verify clean state
    post_handles = {
        g.gaitem_handle
        for g in save.character_slots[_slot_idx].gaitem_map
        if g.gaitem_handle != 0
    }
    leftover = post_handles - pre_handles
    if leftover:
        print(f"  FAIL: {len(leftover)} gaitem entries remain after removal:")
        for h in sorted(leftover):
            print(f"    0x{h:08X}")
    else:
        print(
            f"  PASS: gaitem map restored to pre-test state ({len(post_handles)} entries)"
        )

    print(
        "\n  Load in-game. Confirm all 9 test items are gone and nothing was corrupted."
    )
    if pause("ENTER after confirming"):
        time.sleep(0.5)
        save = _Save.from_file(str(save_path))
        still_present = []
        for _full_id, handle, name, _cat in added:
            it = find_item_by_handle(save, handle, "held")
            if it and it.quantity > 0:
                still_present.append(name)
        if still_present:
            print(f"  GAME FAIL: still present: {still_present}")
        else:
            print("  GAME PASS: all items absent after game load")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    global _slot_idx, _Save

    if len(sys.argv) < 2:
        print("usage: python test_inventory.py <save_file> [slot_index] [suite]")
        print("  suite: basic | multi | all  (default: basic)")
        sys.exit(1)

    save_path = Path(sys.argv[1]).resolve()
    slot_arg = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None
    suite_arg = (
        sys.argv[3]
        if len(sys.argv) > 3
        else (
            sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].isdigit() else "basic"
        )
    )

    from er_save_manager.parser.save import Save

    _Save = Save

    print("=" * 60)
    print("ER INVENTORY COMPREHENSIVE TEST")
    print(f"file:  {save_path}")
    print(f"suite: {suite_arg}")
    print("=" * 60)

    save = Save.from_file(str(save_path))
    active = save.get_active_slots()
    print(f"active slots: {active}")
    _slot_idx = slot_arg if slot_arg is not None else (active[0] if active else None)
    if _slot_idx is None:
        print("ERROR: no active slots")
        sys.exit(1)
    if slot_arg is None:
        print(f"auto-selected: {_slot_idx}")

    backup = save_path.with_suffix(save_path.suffix + ".bak")
    shutil.copy2(save_path, backup)
    print(f"backup: {backup}")

    results = []

    if suite_arg in ("basic", "all"):
        for row in BASIC_TESTS:
            label, full_id, qty_add, qty_mod, loc, upg, stackable = row
            ok = run_basic_test(
                label, full_id, qty_add, qty_mod, loc, upg, stackable, save_path
            )
            results.append((label, ok))

    if suite_arg in ("multi", "all"):
        run_multi_test(save_path)

    if results:
        print(f"\n{'=' * 60}")
        print("BASIC SUMMARY")
        for lbl, ok in results:
            print(f"  {'PASS' if ok else 'FAIL/SKIP'}  {lbl}")
        print("=" * 60)


if __name__ == "__main__":
    main()
