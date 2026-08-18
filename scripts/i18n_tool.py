#!/usr/bin/env python3
"""Manage translation catalogs.

Requires Babel (dev dependency only, not needed at runtime):

    uv run scripts/i18n_tool.py extract     regenerate the .pot template
    uv run scripts/i18n_tool.py init de     create a new language catalog
    uv run scripts/i18n_tool.py update      merge the template into every .po
    uv run scripts/i18n_tool.py compile     build .mo files for the app
    uv run scripts/i18n_tool.py status      show per-language coverage

Typical loop after changing English strings: extract, update, then hand the
.po files to translators. Fuzzy entries in the merged .po mark strings whose
English source changed and need review.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
LOCALES = ROOT / "src" / "er_save_manager" / "locales"
POT = LOCALES / "er_save_manager.pot"
DOMAIN = "er_save_manager"


def _run(args: list[str]) -> int:
    print(" ".join(args))
    return subprocess.call(args, cwd=str(ROOT))


def extract() -> int:
    LOCALES.mkdir(parents=True, exist_ok=True)
    return _run(
        [
            sys.executable,
            "-m",
            "babel.messages.frontend",
            "extract",
            "-F",
            "babel.cfg",
            # Map the short aliases so Babel knows which argument is the msgid.
            # 1:1,2:2 on tn marks singular and plural; 1c on tc marks context.
            "-k",
            "t",
            "-k",
            "tn:1,2",
            "-k",
            "tc:1c,2",
            "-k",
            "N_",
            "--add-comments=translators:",
            "--project=ER Save Manager",
            "--copyright-holder=Hapfel",
            "--no-location" if "--no-location" in sys.argv else "--sort-by-file",
            "-o",
            str(POT),
            "src/er_save_manager",
        ]
    )


def init(language: str) -> int:
    if not POT.exists():
        print("No template found. Run extract first.")
        return 1
    return _run(
        [
            sys.executable,
            "-m",
            "babel.messages.frontend",
            "init",
            "-i",
            str(POT),
            "-d",
            str(LOCALES),
            "-D",
            DOMAIN,
            "-l",
            language,
        ]
    )


def update() -> int:
    if not POT.exists():
        print("No template found. Run extract first.")
        return 1
    return _run(
        [
            sys.executable,
            "-m",
            "babel.messages.frontend",
            "update",
            "-i",
            str(POT),
            "-d",
            str(LOCALES),
            "-D",
            DOMAIN,
        ]
    )


def compile_catalogs() -> int:
    if not LOCALES.is_dir():
        print("No locales directory. Run extract and init first.")
        return 1
    return _run(
        [
            sys.executable,
            "-m",
            "babel.messages.frontend",
            "compile",
            "-d",
            str(LOCALES),
            "-D",
            DOMAIN,
            # Refuse to compile catalogs with unresolved fuzzy entries silently;
            # they are compiled but reported so CI can surface them.
            "--statistics",
        ]
    )


def status() -> int:
    if not LOCALES.is_dir():
        print("No locales directory.")
        return 1
    try:
        from babel.messages.pofile import read_po
    except ImportError:
        print("Babel is not installed. Install dev dependencies first.")
        return 1

    found = False
    for po_path in sorted(LOCALES.rglob(f"{DOMAIN}.po")):
        found = True
        language = po_path.parent.parent.name
        with open(po_path, encoding="utf-8") as f:
            catalog = read_po(f)
        total = translated = fuzzy = 0
        for message in catalog:
            if not message.id:
                continue
            total += 1
            if message.fuzzy:
                fuzzy += 1
            elif message.string:
                translated += 1
        pct = (translated / total * 100) if total else 0.0
        print(
            f"{language:6s} {translated:5d}/{total:<5d} ({pct:5.1f}%)  fuzzy: {fuzzy}"
        )
    if not found:
        print("No catalogs yet. Run extract, then init <language>.")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    command = sys.argv[1]
    if command == "extract":
        return extract()
    if command == "init":
        if len(sys.argv) < 3:
            print("Usage: i18n_tool.py init <language-code>")
            return 1
        return init(sys.argv[2])
    if command == "update":
        return update()
    if command == "compile":
        return compile_catalogs()
    if command == "status":
        return status()

    print(f"Unknown command: {command}")
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
