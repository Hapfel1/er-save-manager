#!/usr/bin/env python3
"""Verify the committed translation template matches the source.

Re-extracts strings into a temporary template and compares message ids against
the committed one. Catches the case where a commit adds or edits user-facing
text without running extract and update, which would leave translators unaware
that new strings exist or that existing ones changed.

    uv run scripts/i18n_check.py            fail if the template is stale
    uv run scripts/i18n_check.py --summary  also report per-language coverage

Writes a GitHub Actions job summary when GITHUB_STEP_SUMMARY is set.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
LOCALES = ROOT / "src" / "er_save_manager" / "locales"
POT = LOCALES / "er_save_manager.pot"
DOMAIN = "er_save_manager"


def _read_ids(path: Path) -> set[str]:
    from babel.messages.pofile import read_po

    with open(path, encoding="utf-8") as f:
        catalog = read_po(f)
    return {m.id if isinstance(m.id, str) else m.id[0] for m in catalog if m.id}


def _extract_to(target: Path) -> None:
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "babel.messages.frontend",
            "extract",
            "-F",
            "babel.cfg",
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
            "--sort-by-file",
            "-o",
            str(target),
            "src/er_save_manager",
        ],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _coverage() -> list[tuple[str, int, int, int]]:
    from babel.messages.pofile import read_po

    rows = []
    for po_path in sorted(LOCALES.rglob(f"{DOMAIN}.po")):
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
        rows.append((language, translated, total, fuzzy))
    return rows


def _write_summary(lines: list[str]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    if not POT.exists():
        print("No template at src/er_save_manager/locales/er_save_manager.pot")
        print("Run: uv run scripts/i18n_tool.py extract")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "fresh.pot"
        _extract_to(fresh)
        current_ids = _read_ids(fresh)

    committed_ids = _read_ids(POT)
    added = sorted(current_ids - committed_ids)
    removed = sorted(committed_ids - current_ids)

    lines: list[str] = []

    if args.summary:
        lines.append("## Translation coverage")
        lines.append("")
        lines.append("| Language | Translated | Total | Fuzzy |")
        lines.append("| --- | ---: | ---: | ---: |")
        for language, translated, total, fuzzy in _coverage():
            pct = (translated / total * 100) if total else 0.0
            lines.append(
                f"| {language} | {translated} ({pct:.1f}%) | {total} | {fuzzy} |"
            )
        lines.append("")

    if not added and not removed:
        print(f"Template is current ({len(committed_ids)} strings).")
        if lines:
            _write_summary(lines)
        return 0

    lines.append("## Translation template is stale")
    lines.append("")
    lines.append("Run `uv run scripts/i18n_tool.py extract` then `update`, and commit.")
    lines.append("")

    if added:
        lines.append(f"### {len(added)} new string(s)")
        lines.append("")
        for msgid in added[:40]:
            lines.append(f"- `{msgid[:100]}`")
        if len(added) > 40:
            lines.append(f"- ... and {len(added) - 40} more")
        lines.append("")

    if removed:
        lines.append(f"### {len(removed)} removed string(s)")
        lines.append("")
        for msgid in removed[:20]:
            lines.append(f"- `{msgid[:100]}`")
        if len(removed) > 20:
            lines.append(f"- ... and {len(removed) - 20} more")
        lines.append("")

    print("\n".join(lines))
    _write_summary(lines)
    return 1


if __name__ == "__main__":
    sys.exit(main())
