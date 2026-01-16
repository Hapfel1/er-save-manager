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
