# Elden Ring Save Manager

<div class="grid cards" markdown>

-   :material-shield-check:{ .lg .middle } __Save File Fixer__

    ---

    Automatically detect and fix save corruption issues and infinite loading screens

    [:octicons-arrow-right-24: Get Started](user-guide/save-file-fixer.md)

-   :material-account-multiple:{ .lg .middle } __Character Management__

    ---

    Export, import, and move characters between saves with full backup support

    [:octicons-arrow-right-24: Learn More](user-guide/character-management.md)

-   :material-cloud-download:{ .lg .middle } __Community Browser__

    ---

    Browse, download, and share character builds and appearance presets

    [:octicons-arrow-right-24: Explore](user-guide/character-browser.md)

-   :material-tune:{ .lg .middle } __Character Editor__

    ---

    Edit stats, runes, name, level, and progression details

    [:octicons-arrow-right-24: Edit](user-guide/character-editor.md)

</div>

## Features

### :material-check-all: Working Features

- **Save File Fixer** - Automatically detect and fix save corruption issues
- **Character Management** - Export, import, and move characters between saves  
- **Community Character Browser** - Browse, download, and contribute characters
- **Character Editor** - Edit stats, runes, name, level, and build attributes
- **Appearance Editor** - View, export and import 15 preset slots
- **Community Preset Browser** - Browse and download appearance presets
- **SteamID Patcher** - Transfer saves between Steam accounts
- **Event Flags Editor** - View and toggle 948+ documented event flags
- **Boss Respawner** - Respawn any boss for repeated fights
- **Gestures** - Unlock all gestures including DLC and cut content
- **Backup Manager** - Automatic and manual backups with restore functionality
- **Troubleshooting** - Diagnostic checks for game and save file issues

### :material-wrench: Work in Progress

- **World State / Teleportation** - Custom coordinate teleportation (known location list needs verification)
- **Inventory Editor** - Item spawning requires additional reverse engineering
- **Hex Editor** - Not yet implemented

## Installation

=== "Windows"

    Download the latest Windows Version from [Releases](https://github.com/Hapfel1/er-save-manager/releases)
    
    Unpack the zip.
    Run the executable.
    

=== "Linux / Steam Deck"

    Download the latest Linux Version from [Releases](https://github.com/Hapfel1/er-save-manager/releases)

    Run the AppImage
    
    **Features:**
    - Auto-detects Steam (standard and Flatpak)
    - Finds Proton compatdata locations
    - Full Steam Deck support

## Quick Start

1. **Launch** the application
2. Click **Auto-Detect** or **Browse** to load your save file
3. Use tabs to access different features

!!! tip "First Time?"
    Check out the [Installation Guide](user-guide/installation.md) for platform-specific instructions!

## Corruption Fixes

The Save File Fixer can detect and repair:

- **Torrent Bug** - Infinite loading when horse HP=0 with state=ACTIVE
- **SteamID Mismatch** - Character SteamID doesn't match save file
- **Weather Sync** - AreaID mismatch with current map
- **Time Sync** - Recalculates time from seconds played
- **Ranni Softlock** - Fixes Ranni's Tower quest progression
- **Warp Sickness** - Stuck warps (Radahn, Morgott, Radagon, Sealing Tree)
- **DLC Issues** - Stuck at DLC coordinates, invalid DLC flag data
- **Teleport Fallback** - Emergency teleport to Roundtable Hold

[:octicons-arrow-right-24: Learn more about fixes](user-guide/save-file-fixer.md)

## Platform Support

| Platform | Support | Notes |
|----------|---------|-------|
| Windows  | :material-check: Full | Native executable |
| Linux    | :material-check: Full | AppImage with Steam/Proton support |
| Steam Deck | :material-check: Full | Auto-detection, optimized UI |
| macOS    | :material-close: Not supported | May work via Wine (untested) |

## Credits

### Research & Development

- [ER-Save-Lib](https://github.com/ClayAmore/ER-Save-Lib) - Rust implementation
- [Umgak](https://github.com/Umgak) - Event Flag Manager tables
- [?WikiName?](https://soulsmodding.com/doku.php?id=er-refmat:main) - Documentation

### Community

- All preset contributors
- Testers: [2Pz](https://github.com/2Pz), [Ghostlyswat12](https://github.com/Ghostlyswat12)

### Special Thanks

- [2Pz](https://github.com/2Pz) - Automated build/release workflow

## License

MIT License - see [LICENSE](https://github.com/Hapfel1/er-save-manager/blob/main/LICENSE)