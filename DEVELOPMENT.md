# Development

## Requirements
- Python **3.13+** (see `.python-version`)
- [`uv`](https://github.com/astral-sh/uv)

## Setup

```bash
uv sync --locked --dev
```

## Run

```bash
# CLI
uv run er-save-manager --help

# List characters
uv run er-save-manager list --save "C:\Path\To\ER0000.sl2"

# Check for corruption
uv run er-save-manager check --save "C:\Path\To\ER0000.sl2"

# Fix corruption
uv run er-save-manager fix --save "C:\Path\To\ER0000.sl2" --slot 1

# Fix with teleport
uv run er-save-manager fix --save "C:\Path\To\ER0000.sl2" --slot 1 --teleport limgrave

# Backup management
uv run er-save-manager backup create --save "C:\Path\To\ER0000.sl2" --name "before-edit"
uv run er-save-manager backup list --save "C:\Path\To\ER0000.sl2"
uv run er-save-manager backup restore --save "C:\Path\To\ER0000.sl2" --backup "backup_file.bak"
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

## Build (Windows exe)

```bash
uv run pyinstaller "Elden Ring Save Manager.spec"
```

## Project Structure

```
src/er_save_manager/
    __init__.py             # Package init, version
    cli.py                  # Command-line interface
    
    parser/                 # Save file parsing
        __init__.py
        save.py             # Main save file parser
        user_data_x.py      # Character slot parser
        user_data_10.py     # Common data (SteamID, profiles)
        character.py        # PlayerGameData
        equipment.py        # Inventory, spells
        world.py            # Coordinates, weather, DLC
        event_flags.py      # Event flag read/write
        er_types.py         # Shared types
    
    fixes/                  # Corruption fixes
        __init__.py
        base.py             # BaseFix interface
        torrent.py          # Torrent bug fix
        steamid.py          # SteamID sync
        weather.py          # Weather sync
        time_sync.py        # Time sync
        event_flags.py      # Quest/warp fixes
        dlc.py              # DLC flag fixes
        teleport.py         # Safe teleport
    
    backup/                 # Backup system
        __init__.py
        manager.py          # Backup operations

src/resources/
    eventflag_bst.txt       # Event flag BST mapping
```

## Release Process

### Automated Release Workflow

This project uses an automated release workflow that creates PRs with version bumps and changelogs based on conventional commits.

#### Conventional Commit Format

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for all commits:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Common types:**
- `feat`: New feature (✨ New Features in changelog)
- `fix`: Bug fix (🔧 Bug Fixes in changelog)
- `ui`: UI changes (🎨 User Interface in changelog)
- `docs`: Documentation (📖 Documentation in changelog)
- `perf`: Performance improvement (⚡ Performance in changelog)
- `refactor`: Code refactoring (♻️ Refactoring in changelog)
- `chore`: Maintenance (🧹 Maintenance in changelog)
- `test`, `ci`, `build`: Skipped in changelog

**Examples:**
```bash
git commit -m "feat: add auto-backup on save"
git commit -m "fix: correct corruption detection for DLC saves"
git commit -m "ui: improve character selection UI"
git commit -m "docs: update installation instructions"
```

#### How Releases Work

1. **Push to main**: When commits are merged to main, the workflow detects if a version bump is needed
2. **Create release branch**: If needed, creates `release-vX.Y.Z` with version bump and changelog
3. **Build artifacts**: Builds Windows executable on the release branch
4. **Create PR**: Opens a PR to main with changelog in the body
5. **Draft release**: Creates a draft GitHub release with the Windows artifact
6. **Review & merge**: Review the PR, and when merged, the release is ready to publish

#### Manual Version Bump (if needed)

```bash
# Bump version locally
uv run python scripts/bump_version.py v1.2.3

# Update changelog
git cliff --tag v1.2.3 -o CHANGELOG.md

# Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): bump to v1.2.3"
```

#### Troubleshooting

**Issue**: Release workflow doesn't trigger
- **Solution**: Ensure commits follow conventional commit format
- **Solution**: Check that commits since last release warrant a version bump

**Issue**: PR creation fails
- **Solution**: Ensure `PUSH_TOKEN` secret is configured with `repo` and `workflow` permissions

**Issue**: Build artifacts not attached
- **Solution**: Check build job logs for PyInstaller errors
- **Solution**: Ensure `.spec` file is up to date

