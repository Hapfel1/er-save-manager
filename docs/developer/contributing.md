# Contributing to Elden Ring Save Manager

Thank you for considering contributing! This document provides guidelines for contributing to the project.

---

## Code of Conduct

Be respectful and constructive. We're all here to make a better tool.

---

## How to Contribute

### Reporting Bugs

**Before submitting:**
1. Search existing issues
2. Check if already reported
3. Verify bug in latest version

**Bug report should include:**
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Save file
- Error logs
- Operating system and version
- Tool version

**Where to report:**
- GitHub Issues

### Suggesting Features

**Feature requests should include:**
- Clear use case
- Why it would be useful
- How it should work
- Any similar features in other tools

### Contributing Code

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes with tests
4. Follow code style guidelines
5. Commit with clear messages
6. Push to your fork
7. Submit pull request

---

## Development Setup

### Requirements

- Python 3.13+
- uv or pip
- Git

### Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/er-save-manager.git
cd er-save-manager

# Create virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e ".[dev]"
```

### Running

```bash
uv run python run_gui.py
```

---

### Format & Lint

```bash
uv run ruff check
uv run ruff format
```

---

## Pull Request Process

### Before Submitting

1. Code follows style guidelines
2. Documentation updated
3. Commit messages clear

### PR Description

**Should include:**
- What changes were made
- Why changes were made
- Related issue numbers
- Testing performed
- Screenshots (if UI changes)

**Template:**
```markdown
## Description
Brief description of changes

## Related Issues
Fixes #123

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Screenshots
If applicable
```

---

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

---

## Adding New Features

### Parser Changes

**When modifying parser:**
1. Update offset tracking
2. Add write-back support
3. Update checksum calculation
4. Test with multiple save versions
5. Document new structures

### New Fixes

**Creating a fix:**
1. Inherit from `BaseFix`
2. Implement `detect()` method
3. Implement `apply()` method
4. Add to `ALL_FIXES` list
5. Write tests
6. Document fix behavior

**Example:**
```python
class MyCustomFix(BaseFix):
    name = "My Fix"
    description = "Fixes issue X"
    
    def detect(self, save: Save, slot_index: int) -> bool:
        # Detection logic
        return issue_detected
    
    def apply(self, save: Save, slot_index: int) -> FixResult:
        # Fix logic
        return FixResult(applied=True, description="Fixed X")
```

### UI Changes

**When modifying UI:**
1. Follow existing patterns
2. Use Qt signals/slots properly
3. Handle errors gracefully
4. Add progress indicators
5. Test on all platforms

---

## Documentation

### Where to Document

- Code: Docstrings and comments
- User guide: `docs/user-guide/`
- Technical: `docs/technical/`
---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing!