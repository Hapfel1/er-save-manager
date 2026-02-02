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

    # Update version.txt with full version metadata
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

    # Update __init__.py __version__ variable
    init_py_path = (
        Path(__file__).parent.parent / "src" / "er_save_manager" / "__init__.py"
    )
    if init_py_path.exists():
        init_content = init_py_path.read_text(encoding="utf-8")

        # Replace __version__ = "old_version" with __version__ = "new_version"
        updated_init = re.sub(
            r'(__version__\s*=\s*")[^"]+(")',
            rf"\g<1>{new_version}\g<2>",
            init_content,
            count=1,
        )

        init_py_path.write_text(updated_init, encoding="utf-8")
        print(f"Updated {init_py_path.name} __version__ to {new_version}")

    # Update app.manifest file - replace assemblyIdentity version attribute
    manifest_path = Path(__file__).parent.parent / "resources" / "app.manifest"
    if manifest_path.exists():
        manifest_content = manifest_path.read_text(encoding="utf-8")

        # Normalize XML declaration version to 1.0
        manifest_content = re.sub(
            r'(<?xml[^>]*version=")[^"]+("[^>]*\?>)',
            r"\g<1>1.0\g<2>",
            manifest_content,
            count=1,
            flags=re.IGNORECASE,
        )

        # Replace only the assemblyIdentity version attribute
        updated_manifest = re.sub(
            r'(<assemblyIdentity[^>]*?\bversion=")[^"]+("[^>]*>)',
            rf"\g<1>{windows_version_str}\g<2>",
            manifest_content,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )

        manifest_path.write_text(updated_manifest, encoding="utf-8")
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
