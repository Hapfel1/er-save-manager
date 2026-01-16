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
# GUI (default)
uv run er-save-manager-gui

# CLI
uv run er-save-manager --help
```

## CLI Examples
```bash
# List characters
uv run er-save-manager list --save "C:\Path\To\ER0000.sl2"

# Check for corruption
uv run er-save-manager check --save "C:\Path\To\ER0000.sl2"

# Fix all issues
uv run er-save-manager fix --save "C:\Path\To\ER0000.sl2" --slot 1

# Create backup
uv run er-save-manager backup create --save "C:\Path\To\ER0000.sl2" --name "before-edit"

# Export character
uv run er-save-manager export --save "C:\Path\To\ER0000.sl2" --slot 1 --output char.erc
```

## Lint / Format
```bash
uv run ruff check
uv run ruff format
```

## Test
```bash
uv run pytest
```

## Build (Windows exe)
```bash
uv run pyinstaller "Elden Ring Save Manager.spec"
```