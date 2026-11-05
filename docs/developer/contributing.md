# Contributing to Elden Ring Save Manager

Thank you for considering contributing. This document provides guidelines for contributing to the project.

---

## Code of Conduct

Everyone taking part follows the [Code of Conduct](https://github.com/Hapfel1/er-save-manager/blob/main/.github/CODE_OF_CONDUCT.md). Security problems go through the [security policy](https://github.com/Hapfel1/er-save-manager/blob/main/.github/SECURITY.md), not public issues.

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
- Save file, zipped (GitHub does not accept .sl2 or .co2 directly)
- `errors.log` from the settings data folder (`%APPDATA%\ER Save Manager` on Windows, `~/.local/share/er-save-manager` on Linux), written whenever the app shows an error dialog
- For save loading problems, `er_save_manager.log`: on the Settings tab, type `STRAWBERRY` to show the Advanced section, tick **Verbose logging to file**, load the save again, and take the file from the folder of the save
- Operating system and version
- Tool version

**Where to report:**

- [GitHub Issues](https://github.com/Hapfel1/er-save-manager/issues/new/choose), using the matching form
- Questions and help: the [Discord server](https://dsc.gg/er-saveman)

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
- [uv](https://github.com/astral-sh/uv)
- Git

### Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/er-save-manager.git
cd er-save-manager

# Create the environment with the locked dependencies
uv sync --locked --dev
```

### Running

```bash
uv run python run_gui.py
```

---

### Format, Lint and Test

```bash
uv run ruff check
uv run ruff format
uv run pytest
```

---

## Pull Request Process

### Before Submitting

1. `ruff check`, `ruff format` and `pytest` pass
2. Documentation updated
3. Commit messages clear

### PR Description

**Should include:**

- What changes were made
- Why changes were made
- Related issue numbers
- Testing performed
- Screenshots (if UI changes)

The pull request form on GitHub prefills a short template.

---

## Project Structure

```
src/er_save_manager/
    parser/         # Elden Ring save parsing and write-back
    fixes/          # Save Fixer checks (BaseFix subclasses)
    games/          # Other games: DSR, DS2, DS3, NR, plus SteamID patchers
    editors/        # Elden Ring world state editing
    data/           # Game data (items, event flags, locations, bosses)
    backup/         # Backup manager
    transfer/       # Character export, import and copy
    platform/       # Save location detection, Steam and Proton paths
    validation/     # Save validation
    addons/         # Troubleshooter add-on download
    ui/             # CustomTkinter GUI: tabs/, dialogs/, editors/
tests/              # pytest suite
resources/          # Icons, fonts, Windows manifest, Linux desktop files
scripts/            # Build, release and data generation scripts
build-windows.py    # Windows build (cx_Freeze)
build-linux.sh      # Linux AppImage build (PyInstaller)
run_gui.py          # GUI entry point
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
2. Use CustomTkinter widgets and the shared helpers in `ui/`
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

By contributing, you agree that your contributions will be licensed under the project's [Source Available License](https://github.com/Hapfel1/er-save-manager/blob/main/LICENSE).

---

Thank you for contributing.