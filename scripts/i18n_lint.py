#!/usr/bin/env python3
"""Report user-facing strings that are not wrapped in a translation call.

Serves two purposes: a migration checklist while strings are being converted,
and a regression guard afterwards so new untranslated strings are caught.

    uv run scripts/i18n_lint.py              summary per file
    uv run scripts/i18n_lint.py --detail     every site with line numbers
    uv run scripts/i18n_lint.py --path ui    limit to a subtree

Exits 1 when any site is found, so it can gate CI once the count reaches zero.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src" / "er_save_manager"

TRANSLATION_FUNCS = {"t", "tn", "tc"}

# Keyword arguments whose value reaches the screen.
UI_KEYWORDS = {
    "text",
    "title",
    "message",
    "placeholder_text",
    "label",
    "header",
    "tooltip",
}

# Deliberately excluded: "description". In this codebase it is the
# create_backup() argument that becomes part of the backup filename on disk,
# not display text. Translating it would produce localized filenames and break
# matching against existing backups.

# Calls whose leading positional arguments reach the screen.
UI_CALLS = {
    "showinfo",
    "showwarning",
    "showerror",
    "askyesno",
    "askokcancel",
    "askquestion",
    "askretrycancel",
    "show_toast",
    "toast",
    "set_status",
}

# Values that are identifiers or layout tokens rather than prose.
IGNORED_VALUES = {"", "-", "...", "x", "n/a"}


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _is_translated(node: ast.expr) -> bool:
    """True if the expression is already routed through a translation call.

    Handles the common wrappers: a bare t(...), a .format(...) on one, and
    f-strings or concatenations containing one.
    """
    if isinstance(node, ast.Call):
        name = _call_name(node)
        if name in TRANSLATION_FUNCS:
            return True
        # t("...").format(...) and similar method chains
        if isinstance(node.func, ast.Attribute):
            return _is_translated(node.func.value)
        return False
    if isinstance(node, ast.JoinedStr):
        return any(
            _is_translated(v.value)
            for v in node.values
            if isinstance(v, ast.FormattedValue)
        )
    if isinstance(node, ast.BinOp):
        return _is_translated(node.left) or _is_translated(node.right)
    return False


def _needs_translation(node: ast.expr) -> bool:
    """True if the expression puts literal prose on screen."""
    if _is_translated(node):
        return False
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        value = node.value.strip()
        if value.lower() in IGNORED_VALUES:
            return False
        return any(c.isalpha() for c in value)
    if isinstance(node, ast.JoinedStr):
        # An f-string with no literal letters is pure interpolation, for example
        # f"{count}" or f"{a}/{b}", and carries no translatable prose.
        return any(
            isinstance(v, ast.Constant)
            and isinstance(v.value, str)
            and any(c.isalpha() for c in v.value)
            for v in node.values
        )
    if isinstance(node, ast.IfExp):
        return _needs_translation(node.body) or _needs_translation(node.orelse)
    return False


def _preview(node: ast.expr) -> str:
    if isinstance(node, ast.Constant):
        text = str(node.value)
    else:
        try:
            text = ast.unparse(node)
        except Exception:
            text = "<expression>"
    text = " ".join(text.split())
    return text if len(text) <= 60 else text[:57] + "..."


def scan(
    path_filter: str | None, excludes: list[str] | None = None
) -> list[tuple[Path, int, str, str]]:
    findings: list[tuple[Path, int, str, str]] = []

    for py_path in sorted(SRC.rglob("*.py")):
        rel = py_path.relative_to(SRC)
        if path_filter and path_filter not in str(rel):
            continue
        if excludes and any(skip in str(rel) for skip in excludes):
            continue
        try:
            tree = ast.parse(py_path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            for keyword in node.keywords:
                if keyword.arg in UI_KEYWORDS and _needs_translation(keyword.value):
                    findings.append(
                        (
                            rel,
                            keyword.value.lineno,
                            keyword.arg,
                            _preview(keyword.value),
                        )
                    )

            if _call_name(node) in UI_CALLS:
                for arg in node.args[:2]:
                    if _needs_translation(arg):
                        findings.append(
                            (rel, arg.lineno, _call_name(node), _preview(arg))
                        )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--detail", action="store_true", help="list every site")
    parser.add_argument("--path", default=None, help="limit to a path substring")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="path substring to skip, repeatable",
    )
    args = parser.parse_args()

    findings = scan(args.path, args.exclude)

    if not findings:
        print("No untranslated user-facing strings found.")
        return 0

    if args.detail:
        for rel, lineno, kind, preview in findings:
            print(f"{rel}:{lineno}: {kind}= {preview}")
        print()

    per_file = Counter(rel for rel, _, _, _ in findings)
    for rel, count in per_file.most_common():
        print(f"{count:5d}  {rel}")

    print(f"\n{len(findings)} sites across {len(per_file)} files")
    return 1


if __name__ == "__main__":
    sys.exit(main())
