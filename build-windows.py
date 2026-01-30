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
from cx_Freeze.finder import ModuleFinder


# Prefer version.txt (bump_version writes full metadata); fallback to pyproject
def load_version() -> str:
    version_txt = Path(__file__).parent / "resources" / "version.txt"
    if version_txt.exists():
        for line in version_txt.read_text(encoding="utf-8").splitlines():
            if line.startswith("version="):
                version_str = line.split("=", 1)[1].strip()
                # Strip trailing .0 for semantic versioning (0.5.0.0 -> 0.5.0)
                return version_str.rstrip("0").rstrip(".")
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    pyproject_content = pyproject_path.read_text(encoding="utf-8")
    pyproject_data = tomlkit.parse(pyproject_content)
    return pyproject_data["project"]["version"]  # type: ignore[index]


VERSION = load_version()

warnings.filterwarnings("ignore", category=SyntaxWarning)

if sys.platform != "win32":
    sys.exit("This script must be run on Windows to build a Windows binary.")

# Include necessary files without including source code
include_files = [
    ("src/resources/", "resources/"),
    ("resources/", "resources/"),
    ("resources/app.manifest", "app.manifest"),
]

# Explicitly include UI submodules for cx_Freeze
ui_packages = []

# Add additional options like packages and excludes
build_exe_options = {
    # Explicitly include the entire package to handle relative imports
    "packages": ["er_save_manager"] + ui_packages,
    # Include all modules explicitly
    "includes": [],
    "include_files": include_files,
    # Compress packages into library.zip to reduce file count (bloat)
    # Exclude specific packages that rely on __file__ for resource loading
    "zip_exclude_packages": ["er_save_manager", "customtkinter", "customtkinterthemes"],
    "zip_include_packages": ["*"],
    # Exclude unused heavy dependencies found in environment
    "excludes": ["unittest", "pydoc"],
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
        # Use run_gui.py as the main entry point for GUI mode
        "run_gui.py",
        base=base,
        # Output executable name (without extension)
        target_name="Elden Ring Save Manager",
        # Path to the icon file
        icon="resources/icon/icon.ico",
        # Windows manifest for security and compatibility
        manifest="resources/app.manifest",
    )
]


# Monkey patch to exclude tzdata and demos from tcl/tk (reduces build size significantly)

original_include_files = ModuleFinder.include_files


def patched_include_files(self, source_path, target_path, copy_dependent_files=True):
    source_path = Path(source_path)
    target_path = Path(target_path)

    # Intercept tcl/tk copying (which usually copies the whole folder)
    if str(target_path).startswith("share") and source_path.is_dir():
        if "tcl" in source_path.name or "tk" in source_path.name:
            # Manually walk and include files, skipping bloat
            for file_path in source_path.rglob("*"):
                if file_path.is_dir():
                    continue

                # Check for excluded folders
                rel_path = file_path.relative_to(source_path)
                if "tzdata" in rel_path.parts or "demos" in rel_path.parts:
                    continue  # Skip these bulky folders

                # Include this specific file
                final_target = target_path / rel_path
                original_include_files(
                    self, file_path, final_target, copy_dependent_files
                )
            return

    # Default behavior for everything else
    original_include_files(self, source_path, target_path, copy_dependent_files)


ModuleFinder.include_files = patched_include_files

# Setup configuration
setup(
    name="ER Save Manager",
    version=VERSION,
    description="Elden Ring Save Manager",
    options={"build_exe": build_exe_options},
    executables=executables,
)
