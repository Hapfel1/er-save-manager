#!/bin/sh

set -e

# Build er-save-manager as a standalone (one-file) binary for Linux
#
# Usage with uv:
#     uv sync --dev
#     uv run ./build-linux.sh
#
# Usage with pip (activate venv first):
#     pip install -r requirements-dev.txt
#     ./build-linux.sh

# pyinstaller does not cross-compile. Build results will be wrong on other OSes.
if [ "$(uname)" != Linux ]; then
	echo "This script only works on Linux."
	exit 1
fi

# Get version from pyproject.toml
version=$(grep --max-count=1 '^version\s*=' pyproject.toml | cut -d '"' -f2)

echo "Building GUI with PyInstaller..."

# Build with GUI entry point and include all UI modules
# Using --onefile for single executable distribution
pyinstaller --clean --noconfirm \
	--name er-save-manager \
	--onefile \
	--windowed \
	--icon resources/icon/icon.png \
	--copy-metadata er-save-manager \
	--add-data resources:resources \
	--hidden-import PIL._tkinter_finder \
	--hidden-import PIL.ImageTk \
	--hidden-import PIL._imagingtk \
	--hidden-import er_save_manager.ui \
	--hidden-import er_save_manager.ui.gui \
	--hidden-import er_save_manager.ui.editors \
	--hidden-import er_save_manager.platform \
	--hidden-import er_save_manager.ui.editors.equipment_editor \
	--hidden-import er_save_manager.ui.editors.stats_editor \
	--hidden-import er_save_manager.ui.editors.character_info_editor \
	--hidden-import er_save_manager.ui.editors.inventory_editor \
	--hidden-import er_save_manager.ui.dialogs \
	--hidden-import er_save_manager.ui.dialogs.character_details \
	--hidden-import er_save_manager.ui.dialogs.save_selector \
	--hidden-import er_save_manager.ui.dialogs.preset_browser \
	--hidden-import er_save_manager.ui.dialogs.browser_submission \
	--hidden-import er_save_manager.ui.dialogs.backup_pruning_warning \
	--hidden-import er_save_manager.ui.widgets \
	--hidden-import er_save_manager.ui.widgets.scrollable_frame \
	--hidden-import er_save_manager.ui.tabs \
	--hidden-import er_save_manager.ui.tabs.character_management_tab \
	--hidden-import er_save_manager.ui.tabs.save_inspector_tab \
	--hidden-import er_save_manager.ui.tabs.appearance_tab \
	--hidden-import er_save_manager.ui.tabs.world_state_tab \
	--hidden-import er_save_manager.ui.tabs.steamid_patcher_tab \
	--hidden-import er_save_manager.ui.tabs.event_flags_tab \
	--hidden-import er_save_manager.ui.tabs.gestures_regions_tab \
	--hidden-import er_save_manager.ui.tabs.hex_editor_tab \
	--hidden-import er_save_manager.ui.tabs.advanced_tools_tab \
	--hidden-import er_save_manager.ui.tabs.backup_manager_tab \
	--optimize 2 \
	--strip \
	--distpath "dist/linux-$version" \
	run_gui.py

echo "Build complete: dist/linux-$version/er-save-manager"
