"""
Write THIRD_PARTY_NOTICES.txt for a release build.

The file holds the licence texts of everything a frozen build ships besides
the app's own code: the runtime Python packages (read from their installed
metadata, so versions match the build), the Python interpreter, and on Linux
the system libraries PyInstaller copied into the bundle (Debian/Ubuntu
copyright files, found with dpkg). Save format sources under MIT come first.

Usage:
    python scripts/third_party_notices.py OUTPUT [--bundle DIR]

--bundle is the built Linux onedir folder; its .so files are matched to the
packages that installed them.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import sysconfig
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement

APP_DIST = "er-save-manager"
RULE = "=" * 78

MIT_TEXT = """\
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# (project, url, use, copyright line) for MIT-licensed save format sources.
MIT_SOURCES = [
    (
        "ER-Save-Editor",
        "https://github.com/ClayAmore/ER-Save-Editor",
        "Elden Ring save structure layout and eventflag_bst.txt",
        "Copyright (c) 2024 ClayAmore",
    ),
    (
        "SimpleSekiroSavegameHelper",
        "https://github.com/uberhalit/SimpleSekiroSavegameHelper",
        "Sekiro SteamID offsets and constants",
        "Copyright (c) 2019",
    ),
    (
        "DS3SaveUnpacker",
        "https://github.com/tremwil/DS3SaveUnpacker",
        "Dark Souls III save AES key",
        "Copyright (c) 2020 William Tremblay",
    ),
    (
        "Dark-Souls-2-Save-Editor-PS4-PC",
        "https://github.com/alfizari/Dark-Souls-2-Save-Editor-PS4-PC",
        "Dark Souls II profile slot field offsets",
        "Copyright (c) 2024 Ahmed",
    ),
]

_LICENSE_NAME = re.compile(r"(LICEN[CS]E|COPYING|NOTICE|AUTHORS)", re.IGNORECASE)


def _section(title: str, body: str) -> str:
    return f"{RULE}\n{title}\n{RULE}\n\n{body.strip()}\n\n"


def runtime_distributions(root: str = APP_DIST) -> list[metadata.Distribution]:
    """Distributions the app needs at runtime, found by walking Requires-Dist."""
    seen: dict[str, metadata.Distribution] = {}
    pending = [root]
    while pending:
        name = pending.pop()
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        key = dist.metadata["Name"].lower().replace("_", "-")
        if key in seen:
            continue
        seen[key] = dist
        for spec in dist.requires or []:
            req = Requirement(spec)
            if req.marker is None or req.marker.evaluate({"extra": ""}):
                pending.append(req.name)
    seen.pop(APP_DIST, None)
    return sorted(seen.values(), key=lambda d: d.metadata["Name"].lower())


def _licence_files(dist: metadata.Distribution) -> list[Path]:
    files = []
    for f in dist.files or []:
        parts = Path(str(f)).parts
        if parts and parts[0].endswith(".dist-info") and _LICENSE_NAME.search(f.name):
            files.append(Path(dist.locate_file(f)))
    return sorted(files)


def package_sections() -> list[str]:
    out = []
    for dist in runtime_distributions():
        meta = dist.metadata
        licence = meta.get("License-Expression") or meta.get("License") or ""
        if len(licence) > 80 or "\n" in licence:
            licence = ""
        head = f"{meta['Name']} {dist.version}"
        if licence:
            head += f" ({licence})"
        if meta.get("Home-page"):
            head += f"\n{meta['Home-page']}"
        texts = [
            p.read_text(encoding="utf-8", errors="replace")
            for p in _licence_files(dist)
        ]
        if not texts:
            raise SystemExit(f"No licence file in the metadata of {meta['Name']}")
        out.append(_section(head, "\n\n".join(texts)))
    return out


def python_licence() -> Path:
    candidates = [
        Path(sys.base_prefix) / "LICENSE.txt",
        Path(sysconfig.get_path("stdlib")) / "LICENSE.txt",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise SystemExit("Python LICENSE.txt not found")


def system_library_sections(bundle: Path) -> list[str]:
    """Copyright files of the Debian/Ubuntu packages that own bundled .so files."""
    packages: set[str] = set()
    for lib in sorted(bundle.rglob("lib*.so*")):
        if not lib.is_file():
            continue
        result = subprocess.run(
            ["dpkg", "-S", f"*/{lib.name}"],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in result.stdout.splitlines():
            if line.startswith("diversion by"):
                continue
            for owner in line.split(": ", 1)[0].split(","):
                packages.add(owner.strip().split(":")[0])
    out = []
    for pkg in sorted(packages):
        copyright_file = Path("/usr/share/doc") / pkg / "copyright"
        if copyright_file.is_file():
            out.append(
                _section(
                    f"{pkg} (system library)",
                    copyright_file.read_text(errors="replace"),
                )
            )
    return out


def build(bundle: Path | None) -> str:
    parts = [
        "ER Save Manager includes the third-party software listed below. Each\n"
        "component is distributed under its own licence, reproduced in full.\n\n"
    ]
    for project, url, use, line in MIT_SOURCES:
        parts.append(
            _section(
                f"{project} (MIT)\n{url}\nUsed for: {use}", f"{line}\n\n{MIT_TEXT}"
            )
        )
    parts.extend(package_sections())
    parts.append(
        _section(
            f"Python {sys.version.split()[0]} (PSF-2.0) and the libraries it bundles",
            python_licence().read_text(encoding="utf-8", errors="replace"),
        )
    )
    if bundle is not None:
        parts.extend(system_library_sections(bundle))
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("output", type=Path)
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build(args.bundle), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
