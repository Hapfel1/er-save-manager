"""
Safe spawn coordinate collector for Elden Ring map locations.

Workflow per location:
1. Patches save file with the next map ID (coords preserved)
2. Load character in-game (no-gravity ON)
3. Find solid ground, read X Y Z from Cheat Engine
4. Enter coords here -> script patches save with those coords
5. Reload character in-game to verify the spawn is safe
6. Confirm or redo

Usage:
    python3 collect_coords.py <path_to_save> [--slot 0] [--resume]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from er_save_manager.backup.manager import BackupManager
from er_save_manager.data.locations import LOCATIONS
from er_save_manager.editors.world_state import WorldStateEditor
from er_save_manager.parser.er_types import FloatVector3, MapId
from er_save_manager.parser.save import Save

# ---------------------------------------------------------------------------
# Progress helpers
# ---------------------------------------------------------------------------


def load_progress(f: Path) -> dict:
    if f.exists():
        with open(f) as fh:
            return json.load(fh)
    return {"completed": {}, "skipped": [], "last_index": 0}


def save_progress(f: Path, progress: dict) -> None:
    with open(f, "w") as fh:
        json.dump(progress, fh, indent=2)


def export_coords(progress: dict, out: Path) -> None:
    with open(out, "w") as fh:
        json.dump(progress["completed"], fh, indent=2)
    print(f"Exported {len(progress['completed'])} coords to {out}")


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------


def prompt_coords(
    prompt: str = "  Enter coords (X Y Z)",
) -> tuple[float, float, float] | str | None:
    """Returns (x,y,z), 'skip', 'redo', or None (quit)."""
    while True:
        raw = input(f"{prompt} or [s]kip / [q]uit / [r]edo: ").strip()
        if raw.lower() == "q":
            return None
        if raw.lower() == "s":
            return "skip"
        if raw.lower() == "r":
            return "redo"
        parts = raw.replace(",", " ").split()
        if len(parts) == 3:
            try:
                return float(parts[0]), float(parts[1]), float(parts[2])
            except ValueError:
                pass
        print("  Bad input. Format: 1234.5 -678.9 1234.0")


def prompt_verify() -> str | None:
    """Returns 'ok', 'redo', 'skip', or None (quit)."""
    while True:
        raw = (
            input("  Spawn safe? [y]es / [r]edo coords / [s]kip / [q]uit: ")
            .strip()
            .lower()
        )
        if raw in ("y", "yes"):
            return "ok"
        if raw in ("r", "redo"):
            return "redo"
        if raw in ("s", "skip"):
            return "skip"
        if raw in ("q", "quit"):
            return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("save", help="Path to save file (modified in-place)")
    parser.add_argument("--slot", type=int, default=0, help="Character slot (0-9)")
    parser.add_argument(
        "--resume", action="store_true", help="Resume from last position"
    )
    parser.add_argument(
        "--export", action="store_true", help="Export current progress and exit"
    )
    parser.add_argument("--filter", help="Only process locations matching this string")
    args = parser.parse_args()

    save_path = Path(args.save)
    if not save_path.exists():
        print(f"Save file not found: {save_path}")
        sys.exit(1)

    progress_file = Path("coords_progress.json")
    output_file = Path("safe_coords.json")
    progress = load_progress(progress_file)

    if args.export:
        export_coords(progress, output_file)
        return

    # Build location list: skip d0 != 0 (infinite loading), only collect for d1 != 0
    locations = [
        {"map_id_str": k, **vars(v)}
        for k, v in LOCATIONS.items()
        if v.map_bytes[0] == 0 and v.map_bytes[1] != 0
    ]

    if args.filter:
        f = args.filter.lower()
        locations = [
            loc
            for loc in locations
            if f in loc["name"].lower() or f in loc["map_id_str"]
        ]
        print(f"Filtered to {len(locations)} locations matching '{args.filter}'")

    start_index = progress["last_index"] if args.resume else 0

    print(f"\nSave: {save_path}  Slot: {args.slot}")
    print(f"Locations: {len(locations)} total, starting at {start_index}")
    print(f"Completed: {len(progress['completed'])}")
    print("\nWorkflow:")
    print("  1. Script patches save with map ID (coords preserved)")
    print("  2. Load in-game (no-gravity ON), find solid ground")
    print("  3. Enter X Y Z from Cheat Engine")
    print("  4. Reload to verify, confirm or redo\n")
    input("Press Enter to start...")

    backup_mgr = BackupManager(save_path)

    i = start_index
    while i < len(locations):
        loc = locations[i]
        map_id_str = loc["map_id_str"]
        name = loc["name"]
        dlc = " [DLC]" if loc.get("is_dlc") else ""

        if map_id_str in progress["completed"]:
            i += 1
            continue

        print(f"\n[{i + 1}/{len(locations)}] {map_id_str}  {name}{dlc}")

        # Load/reload save fresh for each location
        save = Save.from_file(str(save_path))
        slot = save.character_slots[args.slot]
        if slot.is_empty():
            print(f"  ERROR: slot {args.slot} is empty")
            sys.exit(1)

        editor = WorldStateEditor(save, args.slot)

        # --- Step 1: patch map ID, preserve existing coords ---
        backup_mgr.create_backup(
            description=f"collect_coords_{map_id_str}",
            operation="collect_coords",
            save=save,
        )
        info = editor.get_current_location()
        existing_coords = info["coordinates"] or FloatVector3(0.0, 0.0, 0.0)
        ok, msg = editor.teleport_to_custom(
            MapId(bytes(loc["map_bytes"])), existing_coords
        )
        if not ok:
            print(f"  WARN: {msg} — skipping")
            progress["skipped"].append(map_id_str)
            progress["last_index"] = i + 1
            save_progress(progress_file, progress)
            i += 1
            continue

        save.recalculate_checksums()
        save.to_file(str(save_path))
        print("  Save patched (map ID set). Load character now.")

        # --- Step 2: collect coords ---
        coords_result = prompt_coords()
        if coords_result is None:
            progress["last_index"] = i
            save_progress(progress_file, progress)
            export_coords(progress, output_file)
            print("Progress saved.")
            return
        if coords_result == "skip":
            progress["skipped"].append(map_id_str)
            progress["last_index"] = i + 1
            save_progress(progress_file, progress)
            i += 1
            continue
        if coords_result == "redo":
            continue

        x, y, z = coords_result

        # --- Step 3: patch coords, verify ---
        while True:
            save = Save.from_file(str(save_path))
            editor = WorldStateEditor(save, args.slot)

            ok, msg = editor.teleport_to_custom(
                MapId(bytes(loc["map_bytes"])),
                FloatVector3(x, y, z),
            )
            if not ok:
                print(f"  ERROR writing coords: {msg}")
                break

            save.recalculate_checksums()
            save.to_file(str(save_path))
            print(f"  Coords written: {x:.3f} {y:.3f} {z:.3f}. Reload to verify.")

            verdict = prompt_verify()
            if verdict is None:
                progress["last_index"] = i
                save_progress(progress_file, progress)
                export_coords(progress, output_file)
                return
            if verdict == "ok":
                break
            if verdict == "skip":
                x = y = z = None
                break
            if verdict == "redo":
                new = prompt_coords("  Enter new coords (X Y Z)")
                if new is None:
                    progress["last_index"] = i
                    save_progress(progress_file, progress)
                    export_coords(progress, output_file)
                    return
                if new in ("skip", "redo"):
                    x = y = z = None
                    break
                x, y, z = new

        if x is not None:
            progress["completed"][map_id_str] = {"x": x, "y": y, "z": z, "name": name}
            print(f"  Saved: {x}, {y}, {z}")
        else:
            progress["skipped"].append(map_id_str)

        progress["last_index"] = i + 1
        save_progress(progress_file, progress)
        i += 1

    print(f"\nAll done! {len(progress['completed'])} coords collected.")
    export_coords(progress, output_file)


if __name__ == "__main__":
    main()
