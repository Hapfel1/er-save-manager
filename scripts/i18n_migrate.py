#!/usr/bin/env python3
"""Wrap user-facing strings in translation calls.

Operates on the same call sites that scripts/i18n_lint.py reports. Rewrites
using exact AST source spans so surrounding formatting is preserved, then
verifies the result parses before writing.

    uv run scripts/i18n_migrate.py --path ui/tabs --dry-run
    uv run scripts/i18n_migrate.py --path ui/tabs

Literal strings become t("..."). F-strings become t("...{name}...").format(...)
so translators control placeholder order. F-strings whose placeholders cannot be
converted safely are skipped and reported for manual handling.

Review the diff afterwards. This is a mechanical aid, not a substitute for
reading the result.
"""

from __future__ import annotations

import argparse
import ast
import keyword
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src" / "er_save_manager"

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

TRANSLATION_FUNCS = {"t", "tn", "tc"}
IGNORED_VALUES = {"", "-", "...", "x", "n/a"}

IMPORT_LINE = "from er_save_manager.i18n import t"


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _is_translated(node: ast.expr) -> bool:
    if isinstance(node, ast.Call):
        if _call_name(node) in TRANSLATION_FUNCS:
            return True
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
    if _is_translated(node):
        return False
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        value = node.value.strip()
        if value.lower() in IGNORED_VALUES:
            return False
        return any(c.isalpha() for c in value)
    if isinstance(node, ast.JoinedStr):
        return any(
            isinstance(v, ast.Constant)
            and isinstance(v.value, str)
            and any(c.isalpha() for c in v.value)
            for v in node.values
        )
    if isinstance(node, ast.IfExp):
        return _needs_translation(node.body) or _needs_translation(node.orelse)
    return False


def _base_name(expr: ast.expr) -> str:
    """Derive a readable identifier stem from an interpolated expression."""
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    if isinstance(expr, ast.Call):
        return _call_name(expr) or "value"
    if isinstance(expr, ast.Subscript):
        return ast.unparse(expr.value).split(".")[-1]
    if isinstance(expr, ast.BinOp):
        # Name after the leading operand, so slot_idx + 1 yields "slot_idx"
        return _base_name(expr.left)
    if isinstance(expr, ast.IfExp):
        return _base_name(expr.body)
    return "value"


def _placeholder_name(expr: ast.expr, used: dict[str, str]) -> str:
    """Return a unique placeholder name, registering the full source expression."""
    source = ast.unparse(expr)
    if source in used:
        return used[source]

    base = re.sub(r"\W", "_", _base_name(expr)).strip("_").lower() or "value"
    if base[0].isdigit() or keyword.iskeyword(base):
        base = f"v_{base}"

    name = base
    counter = 2
    existing = set(used.values())
    while name in existing:
        name = f"{base}{counter}"
        counter += 1

    used[source] = name
    return name


def _convert_fstring(node: ast.JoinedStr) -> str | None:
    """Render an f-string as t(template).format(...), or None if unsafe."""
    template: list[str] = []
    used: dict[str, str] = {}
    kwargs: list[str] = []

    for part in node.values:
        if isinstance(part, ast.Constant) and isinstance(part.value, str):
            # Literal braces must survive into the format template
            template.append(part.value.replace("{", "{{").replace("}", "}}"))
            continue

        if not isinstance(part, ast.FormattedValue):
            return None

        # Nested f-strings inside a format spec cannot be flattened safely
        spec = ""
        if part.format_spec is not None:
            if not isinstance(part.format_spec, ast.JoinedStr):
                return None
            for spec_part in part.format_spec.values:
                if not (
                    isinstance(spec_part, ast.Constant)
                    and isinstance(spec_part.value, str)
                ):
                    return None
                spec += spec_part.value

        name = _placeholder_name(part.value, used)
        conversion = ""
        if part.conversion is not None and part.conversion != -1:
            conversion = "!" + chr(part.conversion)
        template.append("{" + name + conversion + (f":{spec}" if spec else "") + "}")

    for source, name in used.items():
        kwargs.append(f"{name}={source}")

    if not kwargs:
        return None

    literal = "".join(template)
    return f"t({literal!r}).format({', '.join(kwargs)})"


def _span(source_lines: list[bytes], node: ast.expr) -> tuple[int, int]:
    """Return absolute byte offsets for a node within the source.

    The AST reports col_offset as a UTF-8 byte offset, so lines containing
    multi-byte characters require byte-based indexing rather than character
    indexing.
    """
    starts = []
    offset = 0
    for line in source_lines:
        starts.append(offset)
        offset += len(line)
    begin = starts[node.lineno - 1] + node.col_offset
    end = starts[node.end_lineno - 1] + node.end_col_offset
    return begin, end


def _collect(tree: ast.AST) -> list[ast.expr]:
    targets: list[ast.expr] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg in UI_KEYWORDS and _needs_translation(kw.value):
                targets.append(kw.value)
        if _call_name(node) in UI_CALLS:
            for arg in node.args[:2]:
                if _needs_translation(arg):
                    targets.append(arg)
    return targets


def _insert_import(source: str, tree: ast.Module) -> str:
    if IMPORT_LINE in source:
        return source

    lines = source.splitlines(keepends=True)
    # Place after the final top-level import so ruff's isort ordering holds
    last = None
    for node in tree.body:
        if isinstance(node, ast.Import | ast.ImportFrom):
            last = node
    if last is None:
        return IMPORT_LINE + "\n\n\n" + source

    at = last.end_lineno
    lines.insert(at, IMPORT_LINE + "\n")
    return "".join(lines)


def migrate(path: Path, dry_run: bool) -> tuple[int, int]:
    """Rewrite one file. Returns (converted, skipped)."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        print(f"  skip (syntax): {path}")
        return 0, 0

    targets = _collect(tree)
    if not targets:
        return 0, 0

    raw = source.encode("utf-8")
    lines = raw.splitlines(keepends=True)
    edits: list[tuple[int, int, bytes]] = []
    skipped = 0

    for node in targets:
        begin, end = _span(lines, node)
        original = raw[begin:end].decode("utf-8")

        if isinstance(node, ast.IfExp):
            sub = [b for b in (node.body, node.orelse) if _needs_translation(b)]
            for branch in sub:
                b_begin, b_end = _span(lines, branch)
                edits.append(
                    (
                        b_begin,
                        b_end,
                        f"t({raw[b_begin:b_end].decode('utf-8')})".encode(),
                    )
                )
            continue

        if isinstance(node, ast.Constant):
            replacement = f"t({original})"
        else:
            converted = _convert_fstring(node)
            if converted is None:
                skipped += 1
                print(f"  manual: {path.name}:{node.lineno}: {original[:60]}")
                continue
            replacement = converted

        edits.append((begin, end, replacement.encode("utf-8")))

    if not edits:
        return 0, skipped

    # Apply back to front so earlier offsets stay valid
    result_bytes = raw
    for begin, end, replacement in sorted(edits, reverse=True):
        result_bytes = result_bytes[:begin] + replacement + result_bytes[end:]

    result = _insert_import(result_bytes.decode("utf-8"), tree)

    try:
        ast.parse(result)
    except SyntaxError as e:
        print(f"  FAILED (would break {path}): {e}")
        return 0, skipped

    if not dry_run:
        path.write_text(result, encoding="utf-8")

    return len(edits), skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, help="path substring under src/")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="path substring to skip, repeatable",
    )
    args = parser.parse_args()

    total_converted = total_skipped = 0
    for py_path in sorted(SRC.rglob("*.py")):
        rel = py_path.relative_to(SRC)
        if args.path not in str(rel):
            continue
        if any(skip in str(rel) for skip in args.exclude):
            print(f"      excluded             {rel}")
            continue
        converted, skipped = migrate(py_path, args.dry_run)
        if converted or skipped:
            print(f"{converted:5d} converted, {skipped:3d} manual  {rel}")
        total_converted += converted
        total_skipped += skipped

    verb = "would convert" if args.dry_run else "converted"
    print(f"\n{verb} {total_converted}, {total_skipped} need manual handling")
    return 0


if __name__ == "__main__":
    sys.exit(main())
