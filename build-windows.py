"""Build script for Windows.

Usage with uv:
    uv sync --dev
    uv run ./build-windows.py build

Usage with pip (activate venv first):
    pip install -r requirements-dev.txt
    python build-windows.py build
"""

import sys
import warnings
from pathlib import Path

import tomlkit
from cx_Freeze import Executable, setup

# Get version from pyproject.toml instead of importing package
# This is more robust in CI environments.
pyproject_path = Path(__file__).parent / "pyproject.toml"
pyproject_content = pyproject_path.read_text(encoding="utf-8")
pyproject_data = tomlkit.parse(pyproject_content)
VERSION = pyproject_data["project"]["version"]  # type: ignore[index]

warnings.filterwarnings("ignore", category=SyntaxWarning)

if sys.platform != "win32":
    sys.exit("This script must be run on Windows to build a Windows binary.")

# Include necessary files without including source code
include_files = [
    ("resources/", "resources/"),
]

# Add additional options like packages and excludes
build_exe_options = {
    # Explicitly include the entire package to handle relative imports
    "packages": ["er_save_manager"],
    # Force exclude packages if needed
    "excludes": [],
    "include_files": include_files,
    # Don't compress into zip - this fixes relative import issues
    "zip_include_packages": [],
    # All packages as separate files
    "zip_exclude_packages": ["*"],
    # Output dir for built executables and dependencies
    "build_exe": f"dist/windows-{VERSION}/er-save-manager_{VERSION}",
    # Optimize .pyc files (2 strips docstrings)
    "optimize": 2,
}

# Base for the executable
# Use "gui" to hide console window for GUI app
# Use None for console application
base = "gui" if sys.platform == "win32" else None

# Define the main executable
executables = [
    Executable(
        # The main script of your project
        "src/er_save_manager/cli.py",
        base=base,
        # Output executable name (without extension)
        target_name="er-save-manager",
        # Path to the icon file
        icon="resources/icon/icon.ico",
    )
]

# Setup configuration
setup(
    name="ER Save Manager",
    version=VERSION,
    description="Elden Ring Save Manager",
    options={"build_exe": build_exe_options},
    executables=executables,
)
