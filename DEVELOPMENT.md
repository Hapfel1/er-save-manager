# Development

## Requirements
- Python **3.13+** (see `.python-version`)
- [`uv`](https://github.com/astral-sh/uv) - Fast Python package installer and resolver

## Setup

```bash
uv sync --locked --dev
```

## Run

```bash
# Run GUI (default)
uv run python run_gui.py
```

## Lint / Format

```bash
uv run ruff check
uv run ruff format
```

## Test

```bash
uv run pytest -v
```

## Build

### Windows (cx_Freeze)

```bash
uv run python build-windows.py build
```

Outputs to `dist/windows-{version}/`

### Linux (PyInstaller)

```bash
uv run ./build-linux.sh
```

Outputs to `dist/linux-{version}/`

**Note:** PyInstaller does not cross-compile. Build on the target platform.

## Project Structure

```
src/er_save_manager/
    __init__.py                 # Package init, version
    cli.py                      # Command-line interface (legacy)
    preset_manager.py           # Community preset download/cache
    preset_metrics.py           # Supabase metrics (likes/downloads)
    
    parser/                     # Save file parsing
        __init__.py
        save.py                 # Main save file parser
        user_data_x.py          # Character slot parser (UserDataX)
        user_data_10.py         # Common data (UserData10: SteamID, profiles)
        character.py            # PlayerGameData structure
        character_presets.py    # Appearance preset import/export
        equipment.py            # Inventory, spells, equipment
        world.py                # Coordinates, weather, DLC flags
        event_flags.py          # Event flag read/write
        slot_rebuild.py         # Character slot operations
        er_types.py             # Shared types (Vector3, MapId, etc.)
    
    fixes/                      # Corruption fixes
        __init__.py
        base.py                 # BaseFix interface
        torrent.py              # Torrent bug fix
        steamid.py              # SteamID sync
        weather.py              # Weather sync
        time_sync.py            # Time sync
        event_flags.py          # Quest/warp fixes
        dlc.py                  # DLC flag fixes
        teleport.py             # Safe teleport
    
    backup/                     # Backup system
        __init__.py
        manager.py              # Backup operations
    
    data/                       # Game data
        __init__.py
        boss_data.py            # Boss respawner data
        event_flags_db.py       # Event flag database
        gestures.py             # Gesture unlock data
        item_database.py        # Item IDs and names
        locations.py            # World locations for teleport
        region_ids_map.py       # Map region unlock IDs
        regions.py              # Region unlock data
        starting_classes.py     # Character class data
        items/                  # Item category text files
    
    editors/                    # High-level editors
        __init__.py
        world_state.py          # World state editor
    
    platform/                   # Platform-specific utilities
        __init__.py
        utils.py                # Save file detection, Steam paths
    
    transfer/                   # Character transfer
        __init__.py
        character_ops.py        # Export/import/move operations
    
    validation/                 # Save file validation
        __init__.py
    
    ui/                         # GUI (CustomTkinter)
        __init__.py
        gui.py                  # Main application window
        settings.py             # Settings manager
        theme.py                # Custom theme configuration
        utils.py                # UI utilities
        messagebox.py           # Custom message boxes
        backup_utils.py         # Backup UI utilities
        
        tabs/                   # Main UI tabs
            __init__.py
            character_management_tab.py
            save_inspector_tab.py
            appearance_tab.py
            world_state_tab.py
            steamid_patcher_tab.py
            event_flags_tab.py
            gestures_regions_tab.py
            hex_editor_tab.py       # WIP
            advanced_tools_tab.py
            backup_manager_tab.py
            settings_tab.py
        
        dialogs/                # Dialog windows
            __init__.py
            character_details.py    # Character info dialog
            save_selector.py        # Multi-save selector
            preset_browser.py       # Community preset browser
            browser_submission.py   # Preset submission dialog
            backup_pruning_warning.py
        
        editors/                # Inline editors
            __init__.py
            equipment_editor.py
            stats_editor.py
            character_info_editor.py
            inventory_editor.py     # WIP
        
        widgets/                # Custom widgets
            __init__.py
            scrollable_frame.py

resources/
    eventflag_bst.txt           # Event flag BST mapping
    icon/
        icon.ico                # Windows icon
        icon.png                # Linux/cross-platform icon
    linux/
        er-save-manager.desktop # Linux desktop entry

data/                           # User data (gitignored)
    settings.json               # User settings and preferences
    presets/
        cache.json              # Preset metadata cache
        preset_*.json           # Downloaded preset data
        thumbnails/             # Preset thumbnail images (permanent)
        full_images/            # Full preview images (LRU cache, 500MB, 7-day expiry)

scripts/                        # Build/release scripts
    bump_version.py
    create_release.sh
    extract_changelog.sh
    prepare_artifacts.sh

tests/                          # Unit tests
    __init__.py
    test_init.py

build-windows.py                # Windows build script (cx_Freeze)
build-linux.sh                  # Linux build script (PyInstaller)
run_gui.py                      # GUI entry point
main.py                         # CLI entry point (legacy)
pyproject.toml                  # Project metadata and dependencies
.python-version                 # Python version (3.13+)
```

## Architecture Notes

### Save File Structure

- **UserData10**: Common save data (SteamID, character list, profiles)
- **UserDataX**: Individual character slots (1-10)
- **PlayerGameData**: Core character data structure

### UI Architecture

- **CustomTkinter**: Modern themed UI framework
- **Tab-based layout**: Each feature in its own tab
- **Dialog system**: Modals for complex operations
- **Settings manager**: Persistent user preferences

### Platform Support

- **Windows**: Native paths, AppData save location
- **Linux**: Proton/Wine compatdata detection, multiple Steam paths
- **Save Detection**: Auto-detect from default locations or libraryfolders.vdf

## Adding New Features

### Adding a New Tab

1. Create `src/er_save_manager/ui/tabs/your_tab.py`
2. Import in `src/er_save_manager/ui/gui.py`
3. Add to notebook in `create_tabs()`
4. Update build scripts with `--hidden-import` (Linux) and `includes` (Windows)

### Adding Game Data

1. Add data file to `src/er_save_manager/data/`
2. Update `src/er_save_manager/data/__init__.py` if needed
3. Use in editors or UI tabs

### Adding a Corruption Fix

1. Create `src/er_save_manager/fixes/your_fix.py`
2. Inherit from `BaseFix`
3. Implement `detect()` and `apply()`
4. Add to fix list in advanced tools tab

## Troubleshooting

### Icon not showing in build
- Ensure `resources/icon/icon.ico` (Windows) and `resources/icon/icon.png` (Linux) exist
- Check build scripts include `--icon` parameter

### Missing UI modules in build
- Add to `--hidden-import` in `build-linux.sh`
- Add to `includes` list in `build-windows.py`

### Linux save file not detected
- Check `~/.local/share/Steam/config/libraryfolders.vdf` for custom library paths
- Verify compatdata folder exists: `~/.local/share/Steam/steamapps/compatdata/1245620/`
