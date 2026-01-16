# Elden Ring Save Manager

A comprehensive save file editor, backup manager, and corruption fixer for Elden Ring.

## Features

- **Backup Manager**: Automatic and manual backups with restore functionality
- **Corruption Fixer**: Fix infinite loading screens, Torrent bug, warp sickness, and more
- **Character Editor**: Edit stats, runes, appearance, and equipment
- **Inventory Editor**: Add, remove, and modify items
- **Event Flags**: Unlock graces, toggle boss defeats, manage quest progress
- **SteamID Patcher**: Transfer saves between Steam accounts
- **Character Transfer**: Copy characters between saves or export/import
- **Appearance Presets**: Save and load character appearances
- **Hex Editor**: Save and load character appearances

## Installation

Download the latest release from [Releases](https://github.com/Hapfel1/er-save-manager/releases).

## Usage

1. Run `Elden Ring Save Manager.exe`
2. Select your save file (auto-detected from default location)
3. Select a character and choose an action

## Building from Source

See [DEVELOPMENT.# Elden Ring Save Manager

A comprehensive save file editor, backup manager, and corruption fixer for Elden Ring.

## Features

- **Backup Manager**: Automatic and manual backups with restore functionality
- **Corruption Fixer**: Fix infinite loading screens, Torrent bug, warp sickness, and more
- **Character Editor**: Edit stats, runes, appearance, and equipment (coming soon)
- **Inventory Editor**: Add, remove, and modify items (coming soon)
- **Event Flags**: Unlock graces, toggle boss defeats, manage quest progress (coming soon)
- **SteamID Patcher**: Transfer saves between Steam accounts
- **Character Transfer**: Copy characters between saves or export/import (coming soon)
- **Appearance Presets**: Save and load character appearances (coming soon)

## Corruption Fixes

- **Torrent Bug**: Fixes infinite loading when horse HP=0 with state=ACTIVE
- **SteamID Mismatch**: Syncs character SteamID with save file
- **Weather Sync**: Fixes AreaID mismatch with current map
- **Time Sync**: Recalculates time from seconds played
- **Ranni Softlock**: Fixes Ranni's Tower quest progression block
- **Warp Sickness**: Fixes stuck warps (Radahn, Morgott, Radagon, Sealing Tree)
- **DLC Flag**: Clears Shadow of the Erdtree entry flag
- **Invalid DLC Data**: Clears garbage data in unused DLC slots

## Installation

Download the latest release from [Releases](https://github.com/YOUR_USERNAME/er-save-manager/releases).

## Usage

### Command Line

```bash
# List characters
er-save-manager list --save "C:\Path\To\ER0000.sl2"

# Check for corruption
er-save-manager check --save "C:\Path\To\ER0000.sl2"

# Fix corruption (creates automatic backup)
er-save-manager fix --save "C:\Path\To\ER0000.sl2" --slot 1

# Fix with teleport to safe location
er-save-manager fix --save "C:\Path\To\ER0000.sl2" --slot 1 --teleport limgrave

# Create manual backup
er-save-manager backup create --save "C:\Path\To\ER0000.sl2" --name "my-backup"

# List backups
er-save-manager backup list --save "C:\Path\To\ER0000.sl2"

# Restore backup
er-save-manager backup restore --save "C:\Path\To\ER0000.sl2" --backup "backup_file.bak"
```

## Building from Source

See [DEVELOPMENT.md](DEVELOPMENT.md)

## License

MIT License - see [LICENSE](LICENSE)

## Credits

Based on research from:
- [ER-Save-Lib](https://github.com/ClayAmore/ER-Save-Lib) Rust implementation
- Community save file research and event flag documentation
md](DEVELOPMENT.md)

## License

MIT License - see [LICENSE](LICENSE)