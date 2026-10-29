#!/usr/bin/env python3
"""Convert GitHub release notes (Markdown) into plain changelog lines for Nexus Mods.

Reads the release body on stdin and prints one change per line. Commit links,
PR references, the release title, the release date and separators are dropped.
Entries under a game heading (e.g. "### Elden Ring") are prefixed with it;
git-cliff group headings (emoji first, e.g. "### 🔧 Bug Fixes") are dropped,
since generated entries already carry their own "ER: " style prefix.
"""

import re
import sys

# " ([abc1234](url))" or " ([abc1234](url), [def5678](url))"
_COMMIT_LINKS = re.compile(
    r"\s*\(\[[0-9a-f]{7,40}\]\([^)]*\)(?:,\s*\[[0-9a-f]{7,40}\]\([^)]*\))*\)"
)
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
# GitHub PR references such as " (#438)"
_PR_REF = re.compile(r"\s*\(#\d+\)")


def convert(markdown: str) -> str:
    lines = []
    prefix = ""
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line or line == "---" or line.startswith(("## ", "**Released:**")):
            continue
        if line.startswith("### "):
            heading = line[4:].strip()
            prefix = f"{heading}: " if heading[:1].isascii() else ""
            continue
        if line.startswith(("- ", "* ")):
            line = line[2:]
        line = _LINK.sub(r"\1", _PR_REF.sub("", _COMMIT_LINKS.sub("", line))).strip()
        if line:
            lines.append(prefix + line)
    return "\n".join(lines)


if __name__ == "__main__":
    print(convert(sys.stdin.read()))
