# Elden Ring Save Manager

A comprehensive save file editor, backup manager, and corruption fixer for Elden Ring with an intuitive GUI and a community preset browser.

## Features

### Working Features

- **Save File Fixer**: Automatically detect and fix save corruption issues and infinite loading screens
- **Character Management**: Export, import, and move characters between saves
- **Character Editor**: Edit stats, runes, name, level, and build attributes
- **Appearance Editor**: View, export and import Presets
- **Community Preset Browser**: Browse, download, and contribute character appearance presets with likes and download tracking
- **SteamID Patcher**: Transfer saves between Steam accounts
- **Event Flags Editor**: Read and toggle event flags
- **Boss Respawner**: Respawn any boss for repeated fights
- **Gestures**: Unlock gestures
- **Backup Manager**: Automatic and manual backups with restore functionality
- **Troubleshooting**: Troubleshooter for checking game and save file related issues

### Work in Progress

- **World State / Teleportation**: Custom coordinate teleportation works, known location list needs verification (temporarily disabled)
- **Inventory Editor**: Item spawning requires additional reverse engineering
- **Hex Editor**: Not yet implemented

## Installation

Download the latest release from [Releases](https://github.com/Hapfel1/er-save-manager/releases).

### Platform Support

- **Windows**: Executable
- **Linux**: AppImage
  - Supports Steam (standard and Flatpak)
  - Supports SteamDeck fully
  - Auto-detects Proton compatdata locations
  - Warns about non-default save locations

## Usage

1. Run `Elden Ring Save Manager`
2. Use Auto-Detect or Browse to select your Save File
3. Press "Load Save File"
4. Use the tabs to access different features

## Feature Details

### Save File Fixer

Automatically detects and fixes common save corruption issues:

- **Torrent Bug**: Fixes infinite loading when Torrent HP=0 with state=ACTIVE
- **SteamID Mismatch**: Syncs character SteamID with save file header
- **Weather Sync**: Fixes AreaID mismatch with current map
- **Time Sync**: Recalculates in-game time from seconds played
- **Ranni Softlock**: Fixes Ranni's Tower softlock
- **Warp Sickness**: Fixes stuck warps (Radahn, Morgott, Radagon, Sealing Tree)
- **Stuck at DLC coordinates**: Teleports your character to the Roundtable if you tried accessing the DLC without owning it.
- **DLC Flag**: Clears Shadow of the Erdtree entry flag if accidentally set
- **Invalid DLC Data**: Clears garbage data in unused DLC slots
- **Teleport Fallback**: Teleports your character to the roundtable for any other invalid coordinates that cause an infinite loading screen

### Character Management

- **Export Characters**: Save individual characters to `.erc` files
- **Import Characters**: Load characters from `.erc` into any slot
- **Move Between Slots**: Reorganize characters within a save
- **Copy Between Saves**: Transfer characters to different save files
- **Delete a Character**

### Character Editor

- Edit base stats (Vigor, Mind, Endurance, Strength, Dexterity, Intelligence, Faith, Arcane)
- Modify character name and level
- Adjust runes held

### Appearance Editor

- View Details of a Preset
- Export/Import a Preset from/to a `.json` file
- Delete a Preset
- Copy a Prest to a different Save file
- Browse community presets

### Community Preset Browser

- Browse character appearance presets from the community
- Like your favorite presets
- Download tracking
- Submit your own presets to share with others
- Image preview (face and body)
- Search and filter functionality
- Report inappropriate content
- Local cache for fast loading

### SteamID Patcher

- Transfer saves between Steam accounts
- Patch the SteamID of the save file using ID or custom profile link resolution

### Event Flags

- Search and toggle event flags
- Documented and Custom

### Boss Respawner

- Respawn any boss for repeated fights
- Supports all main game and DLC bosses
- One-click respawn functionality

### Gestures

- Unlock gestures

### Backup Manager

- Automatic backups before any edit
- Manual backup creation with custom names
- Browse and restore previous backups
- Backup pruning with configurable retention
- One-click restore with confirmation

## Building from Source

See [DEVELOPMENT.md](DEVELOPMENT.md)

## License

MIT License - see [LICENSE](LICENSE)

## Credits

### Save File Research
- [ER-Save-Lib](https://github.com/ClayAmore/ER-Save-Lib) - Rust implementation and reverse engineering research
- [Umgak](https://github.com/Umgak) for allowing me to use her contributions to the [TGA Cheat Table](https://github.com/The-Grand-Archives/Elden-Ring-CT-TGA), specifically the Event Flag Manager's tables
- [?WikiName?](https://soulsmodding.com/doku.php?id=er-refmat:main) for the available documentation

### Community
- All preset contributors
- Testers: [2Pz](https://github.com/2Pz), [Ghostlyswat12](https://github.com/Ghostlyswat12)

### Special Thanks
- [2Pz](https://github.com/2Pz) for implenting an automated build/release workflow
