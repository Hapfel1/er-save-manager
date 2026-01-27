#!/usr/bin/env python3
"""Script to bump version in pyproject.toml."""

import re
import sys
from pathlib import Path

import tomlkit


def bump_version(new_version: str) -> None:
    """Update version in pyproject.toml, manifest, and version info files.

    Args:
        new_version: New version string (e.g., "1.2.3" or "v1.2.3")
    """
    # Remove 'v' prefix if present
    new_version = new_version.lstrip("v")

    # Convert version to Windows version format (X.Y.Z.0)
    version_parts = new_version.split(".")
    while len(version_parts) < 3:
        version_parts.append("0")
    ",".join(version_parts[:3]) + ",0"
    windows_version_str = ".".join(version_parts[:3]) + ".0"

    # Path to pyproject.toml
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

    # Read current content
    content = pyproject_path.read_text(encoding="utf-8")
    doc = tomlkit.parse(content)

    # Update version
    old_version = doc["project"]["version"]  # type: ignore[index]
    doc["project"]["version"] = new_version  # type: ignore[index]

    # Write back
    pyproject_path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    print(f"Version updated: {old_version} -> {new_version}")

    # Update version.txt with full version metadata for easy inspection and tooling
    version_txt_path = Path(__file__).parent.parent / "resources" / "version.txt"
    version_txt_content = (
        "version=" + windows_version_str + "\n"
        "file_version=" + windows_version_str + "\n"
        "product_version=" + windows_version_str + "\n"
        "company=ER Save Manager Contributors\n"
        "description=Elden Ring Save File Manager\n"
        "product=ER Save Manager\n"
        "original_filename=er-save-manager.exe\n"
        "copyright=Copyright (c) 2026\n"
    )
    version_txt_path.write_text(version_txt_content, encoding="utf-8")
    print(f"Updated {version_txt_path.name} to version {windows_version_str}")

    # Update app.manifest file - only update assemblyIdentity version
    manifest_path = Path(__file__).parent.parent / "resources" / "app.manifest"
    if manifest_path.exists():
        manifest_content = manifest_path.read_text(encoding="utf-8")
        # Find and update only the assemblyIdentity version attribute
        # Split around assemblyIdentity to avoid changing XML declaration
        lines = manifest_content.split("\n")
        for i, line in enumerate(lines):
            # Look for the version= line that's inside assemblyIdentity (has leading spaces)
            if "version=" in line and line.strip().startswith("version="):
                lines[i] = re.sub(
                    r'version="[\d.]+"',
                    f'version="{windows_version_str}"',
                    line,
                )
        manifest_content = "\n".join(lines)
        manifest_path.write_text(manifest_content, encoding="utf-8")
        print(f"Updated {manifest_path.name} to version {windows_version_str}")


if __name__ == "__main__":
    # Check for help first
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print("Usage: bump_version.py <new_version>")
        print()
        print("Examples:")
        print("  bump_version.py 1.2.4")
        print("  bump_version.py v1.2.4")
        sys.exit(0)

    if len(sys.argv) != 2:
        print("Usage: bump_version.py <new_version>")
        sys.exit(1)

    bump_version(sys.argv[1])
