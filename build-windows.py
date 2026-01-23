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

# Explicitly include UI submodules for cx_Freeze
ui_packages = [
    "er_save_manager.ui",
    "er_save_manager.ui.editors",
    "er_save_manager.ui.dialogs",
    "er_save_manager.ui.widgets",
    "er_save_manager.ui.tabs",
]

# Add additional options like packages and excludes
build_exe_options = {
    # Explicitly include the entire package to handle relative imports
    "packages": ["er_save_manager"] + ui_packages,
    # Include all modules explicitly
    "includes": [
        "er_save_manager.ui.gui",
        "er_save_manager.ui.settings",
        "er_save_manager.platform",
        "er_save_manager.ui.editors.equipment_editor",
        "er_save_manager.ui.editors.stats_editor",
        "er_save_manager.ui.editors.character_info_editor",
        "er_save_manager.ui.editors.inventory_editor",
        "er_save_manager.ui.dialogs.character_details",
        "er_save_manager.ui.dialogs.save_selector",
        "er_save_manager.ui.widgets.scrollable_frame",
        "er_save_manager.ui.tabs.character_management_tab",
        "er_save_manager.ui.tabs.save_inspector_tab",
        "er_save_manager.ui.tabs.appearance_tab",
        "er_save_manager.ui.tabs.world_state_tab",
        "er_save_manager.ui.tabs.steamid_patcher_tab",
        "er_save_manager.ui.tabs.event_flags_tab",
        "er_save_manager.ui.tabs.gestures_regions_tab",
        "er_save_manager.ui.tabs.hex_editor_tab",
        "er_save_manager.ui.tabs.advanced_tools_tab",
        "er_save_manager.ui.tabs.backup_manager_tab",
        "er_save_manager.ui.tabs.settings_tab",
    ],
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
        # Use run_gui.py as the main entry point for GUI mode
        "run_gui.py",
        base=base,
        # Output executable name (without extension)
        target_name="Elden Ring Save Manager",
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
