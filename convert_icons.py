"""
Convert all PNG/JPG/DDS images in a folder to 64x64 WebP.

Usage:
    python convert_icons.py <input_folder> [output_folder]

If output_folder is omitted, converted files are placed alongside the originals.
Existing .webp files in the output are skipped unless --overwrite is passed.
"""

import argparse
import sys
from pathlib import Path

SUPPORTED = {".png", ".jpg", ".jpeg", ".dds", ".tga", ".bmp"}


def convert(input_folder: Path, output_folder: Path, overwrite: bool) -> None:
    sources = [p for p in input_folder.rglob("*") if p.suffix.lower() in SUPPORTED]

    if not sources:
        print(f"No images found in {input_folder}")
        return

    output_folder.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image
    except ImportError:
        sys.exit("Pillow is required: pip install Pillow")

    ok = skipped = errors = 0

    for src in sorted(sources):
        dest = output_folder / (src.stem + ".webp")
        if dest.exists() and not overwrite:
            skipped += 1
            continue
        try:
            img = Image.open(src).convert("RGBA").resize((64, 64), Image.LANCZOS)
            img.save(dest, format="WEBP", quality=90)
            ok += 1
            print(f"  {src.name} -> {dest.name}")
        except Exception as e:
            errors += 1
            print(f"  ERROR {src.name}: {e}")

    print(f"\nDone: {ok} converted, {skipped} skipped, {errors} errors")
    print(f"Output: {output_folder}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_folder", help="Folder containing source images")
    parser.add_argument(
        "output_folder",
        nargs="?",
        help="Where to write .webp files (default: same as input)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-convert files that already exist as .webp",
    )
    args = parser.parse_args()

    input_folder = Path(args.input_folder)
    if not input_folder.is_dir():
        sys.exit(f"Not a directory: {input_folder}")

    output_folder = Path(args.output_folder) if args.output_folder else input_folder
    convert(input_folder, output_folder, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
