"""Command-line interface for ER Save Manager."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .backup import BackupManager
from .fixes import ALL_FIXES, TELEPORT_LOCATIONS, TeleportFix
from .parser import load_save


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _parse_slot(value: str) -> int:
    """Accept slot as 1-10 (preferred) or 0-9 (legacy). Returns 0-based index."""
    try:
        n = int(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError("slot must be an integer") from e

    if 1 <= n <= 10:
        return n - 1
    if 0 <= n <= 9:
        return n
    raise argparse.ArgumentTypeError("slot must be in range 1-10 (or 0-9)")


def cmd_list(args: argparse.Namespace) -> int:
    """List characters in a save file."""
    save_path = Path(args.save).expanduser()
    save = load_save(str(save_path))

    print(f"Save file: {save_path.name}")
    print(f"Platform: {'PlayStation' if save.is_ps else 'PC'}")
    print()

    for slot_idx in range(10):
        slot = save.character_slots[slot_idx]
        if slot.is_empty():
            if args.all:
                print(f"  Slot {slot_idx + 1}: (empty)")
            continue

        name = slot.get_character_name() or f"Character {slot_idx + 1}"
        level = slot.get_level()
        map_id = slot.map_id.to_decimal() if slot.map_id else "Unknown"

        # Check for issues
        has_issues, issues = slot.has_corruption()
        status = " [ISSUES]" if has_issues else ""

        print(f"  Slot {slot_idx + 1}: {name} (Lv.{level}) - Map: {map_id}{status}")

        if args.verbose and has_issues:
            for issue in issues:
                print(f"           - {issue}")

    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Check save file for corruption."""
    save_path = Path(args.save).expanduser()
    save = load_save(str(save_path))

    found_issues = False

    for slot_idx in range(10):
        slot = save.character_slots[slot_idx]
        if slot.is_empty():
            continue

        name = slot.get_character_name() or f"Character {slot_idx + 1}"

        # Get correct SteamID for comparison
        correct_steam_id = None
        if save.user_data_10_parsed:
            correct_steam_id = save.user_data_10_parsed.steam_id

        has_issues, issues = slot.has_corruption(correct_steam_id)

        if has_issues:
            found_issues = True
            print(f"Slot {slot_idx + 1} ({name}):")
            for issue in issues:
                print(f"  - {issue}")
            print()

    if not found_issues:
        print("No corruption detected.")

    return 0 if not found_issues else 1


def cmd_fix(args: argparse.Namespace) -> int:
    """Fix corruption in a character slot."""
    save_path = Path(args.save).expanduser()
    save = load_save(str(save_path))
    slot_idx = args.slot

    slot = save.character_slots[slot_idx]
    if slot.is_empty():
        _eprint(f"Slot {slot_idx + 1} is empty")
        return 1

    name = slot.get_character_name() or f"Character {slot_idx + 1}"
    print(f"Fixing slot {slot_idx + 1} ({name})...")

    # Create backup
    backup_mgr = BackupManager(save_path)
    backup_path = backup_mgr.create_pre_write_backup(save, "fix")
    print(f"Backup created: {backup_path.name}")

    # Apply all fixes
    applied_fixes = []
    for fix_class in ALL_FIXES:
        fix = fix_class()
        if fix.detect(save, slot_idx):
            result = fix.apply(save, slot_idx)
            if result.applied:
                applied_fixes.append(result)
                print(f"  - {fix.name}: {result.description}")

    # Optional teleport
    if args.teleport:
        teleport = TeleportFix(args.teleport)
        result = teleport.apply(save, slot_idx)
        if result.applied:
            applied_fixes.append(result)
            print(f"  - Teleport: {result.description}")

    if applied_fixes:
        # Recalculate checksums and save
        save.recalculate_checksums()
        save.to_file(str(save_path))
        print(f"\nFixed {len(applied_fixes)} issue(s). Save file updated.")
    else:
        print("\nNo fixes needed.")

    return 0


def cmd_backup_create(args: argparse.Namespace) -> int:
    """Create a backup of the save file."""
    save_path = Path(args.save).expanduser()

    if not save_path.exists():
        _eprint(f"Save file not found: {save_path}")
        return 1

    backup_mgr = BackupManager(save_path)
    backup_path = backup_mgr.create_backup(
        description=args.name or "",
        operation="manual",
    )
    print(f"Backup created: {backup_path}")
    return 0


def cmd_backup_list(args: argparse.Namespace) -> int:
    """List backups for a save file."""
    save_path = Path(args.save).expanduser()
    backup_mgr = BackupManager(save_path)

    backups = backup_mgr.list_backups()
    if not backups:
        print("No backups found.")
        return 0

    print(f"Backups for {save_path.name}:")
    for backup in backups:
        size_mb = backup.file_size / (1024 * 1024)
        print(f"  {backup.filename}")
        print(f"    Created: {backup.timestamp}")
        print(f"    Size: {size_mb:.2f} MB")
        if backup.description:
            print(f"    Description: {backup.description}")
        print()

    return 0


def cmd_backup_restore(args: argparse.Namespace) -> int:
    """Restore a backup."""
    save_path = Path(args.save).expanduser()
    backup_mgr = BackupManager(save_path)

    try:
        backup_mgr.restore_backup(args.backup)
        print(f"Restored: {args.backup}")
        return 0
    except FileNotFoundError as e:
        _eprint(str(e))
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser."""
    p = argparse.ArgumentParser(
        prog="er-save-manager",
        description="Elden Ring Save Manager - Editor, Backup Manager, and Corruption Fixer",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = p.add_subparsers(dest="command", metavar="COMMAND")

    # list command
    p_list = sub.add_parser("list", help="List characters in a save file")
    p_list.add_argument("--save", required=True, help="Path to save file")
    p_list.add_argument("-a", "--all", action="store_true", help="Show empty slots")
    p_list.add_argument("-v", "--verbose", action="store_true", help="Show issues")
    p_list.set_defaults(_handler=cmd_list)

    # check command
    p_check = sub.add_parser("check", help="Check save file for corruption")
    p_check.add_argument("--save", required=True, help="Path to save file")
    p_check.set_defaults(_handler=cmd_check)

    # fix command
    p_fix = sub.add_parser("fix", help="Fix corruption in a character slot")
    p_fix.add_argument("--save", required=True, help="Path to save file")
    p_fix.add_argument(
        "--slot", required=True, type=_parse_slot, help="Character slot (1-10)"
    )
    p_fix.add_argument(
        "--teleport",
        choices=list(TELEPORT_LOCATIONS.keys()),
        help="Teleport to safe location",
    )
    p_fix.set_defaults(_handler=cmd_fix)

    # backup commands
    p_backup = sub.add_parser("backup", help="Backup management")
    backup_sub = p_backup.add_subparsers(dest="backup_command", metavar="ACTION")

    p_backup_create = backup_sub.add_parser("create", help="Create a backup")
    p_backup_create.add_argument("--save", required=True, help="Path to save file")
    p_backup_create.add_argument("--name", help="Backup description")
    p_backup_create.set_defaults(_handler=cmd_backup_create)

    p_backup_list = backup_sub.add_parser("list", help="List backups")
    p_backup_list.add_argument("--save", required=True, help="Path to save file")
    p_backup_list.set_defaults(_handler=cmd_backup_list)

    p_backup_restore = backup_sub.add_parser("restore", help="Restore a backup")
    p_backup_restore.add_argument("--save", required=True, help="Path to save file")
    p_backup_restore.add_argument("--backup", required=True, help="Backup filename")
    p_backup_restore.set_defaults(_handler=cmd_backup_restore)

    return p


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()

    if not argv:
        parser.print_help()
        return 0

    args = parser.parse_args(argv)
    handler = getattr(args, "_handler", None)

    if handler is None:
        parser.print_help()
        return 2

    try:
        return int(handler(args))
    except SystemExit:
        raise
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        _eprint(f"Error: {e}")
        if "--debug" in argv:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
