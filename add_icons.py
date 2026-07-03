"""
Add or update icons in icons.db.

Converts source images to 64x64 webp and upserts them into the icons table
keyed by filename (without extension). Name must match the item name closely
enough for icon_manager._norm_icon to resolve it; add an entry to
_NAME_OVERRIDES in icon_manager.py if it does not.

Usage:
    python add_icons.py <input_folder> [--db icons.db]

Source filename becomes the DB name, e.g. "Prime Marika's Hammer.png"
inserts as "Prime Marika's Hammer.webp".
"""

import argparse
import sqlite3
import sys
from io import BytesIO
from pathlib import Path

SUPPORTED = {".png", ".jpg", ".jpeg", ".dds", ".tga", ".bmp", ".webp"}


def add_icons(input_folder: Path, db_path: Path) -> None:
    sources = [p for p in input_folder.rglob("*") if p.suffix.lower() in SUPPORTED]
    if not sources:
        print(f"No images found in {input_folder}")
        return

    try:
        from PIL import Image
    except ImportError:
        sys.exit("Pillow is required: pip install Pillow")

    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE IF NOT EXISTS icons (name TEXT PRIMARY KEY, data BLOB)")

    added = updated = errors = 0

    for src in sorted(sources):
        name = src.stem + ".webp"
        try:
            img = Image.open(src).convert("RGBA").resize((64, 64), Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, format="WEBP", quality=90)
            data = buf.getvalue()

            exists = con.execute(
                "SELECT 1 FROM icons WHERE name = ?", (name,)
            ).fetchone()
            con.execute(
                "INSERT OR REPLACE INTO icons (name, data) VALUES (?, ?)",
                (name, data),
            )
            if exists:
                updated += 1
            else:
                added += 1
            print(f"  {src.name} -> {name}")
        except Exception as e:
            errors += 1
            print(f"  ERROR {src.name}: {e}")

    con.commit()
    con.close()
    print(f"\nDone: {added} added, {updated} updated, {errors} errors")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_folder", help="Folder containing source images")
    parser.add_argument("--db", default="icons.db", help="Path to icons.db")
    args = parser.parse_args()

    input_folder = Path(args.input_folder)
    if not input_folder.is_dir():
        sys.exit(f"Not a directory: {input_folder}")

    add_icons(input_folder, Path(args.db))


if __name__ == "__main__":
    main()
