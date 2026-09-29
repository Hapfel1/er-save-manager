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
- **Inventory Editor** - Edit your inventory, spawn in items, import builds
- **Equipment Editor** - Edit equipped items, save and share loadouts
- **World State / Teleportation** - Known locations, custom coordinates and an interactive map
- **SteamID Patcher** - Transfer saves between Steam accounts
- **Event Flags Editor** - View and toggle 948+ documented event flags
- **Boss Respawner** - Respawn any boss for repeated fights
- **NPC Respawner and Quest Tracker**
- **Gestures** - Unlock all gestures including DLC and cut content
- **Invasion Regions & Game Settings**
- **Backup Manager** - Automatic and manual backups with restore functionality
- **Troubleshooting** - Diagnostic checks for game and save file issues

### :material-controller: Other FromSoftware Games

- [Nightreign](user-guide/nightreign.md) - Relic spawning and editing, Murk editing, character management
- [Dark Souls III](user-guide/dark-souls-3.md) - Stats, character management, boss revival, item spawning, world state
- [Dark Souls Remastered](user-guide/dark-souls-remastered.md) - Stats, character management, event flags, boss and NPC revival, item spawning
- **Dark Souls II SotFS** - Stats, item spawning, character management, bonfire editing, NPC revival
- Backup Manager and [SteamID Patcher](user-guide/steamid-patcher.md) for all of the above plus Armored Core 6 and Sekiro

### :material-wrench: Work in Progress

- **Hex Editor** - Not yet available

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

### Save File Research

- [ER-Save-Lib](https://github.com/ClayAmore/ER-Save-Lib) - Rust implementation and reverse engineering research
- [Sayuri](https://github.com/Umgak) - Event Flag Manager tables from the [TGA Cheat Table](https://github.com/The-Grand-Archives/Elden-Ring-CT-TGA)
- [?WikiName?](https://soulsmodding.com/doku.php?id=er-refmat:main) - Documentation
- [SimpleSekiroSavegameHelper](https://github.com/uberhalit/SimpleSekiroSavegameHelper) - Sekiro SteamID offsets and constants
- DS3 AES encryption key found by Atvaark, published in [DS3SaveUnpacker](https://github.com/tremwil/DS3SaveUnpacker) by tremwil
- Nightreign AES encryption key: TKGP and EonaCat
- [Dark-Souls-2-Save-Editor-PS4-PC](https://github.com/alfizari/Dark-Souls-2-Save-Editor-PS4-PC) - DS2 save format research and item ID lists
- [souls_givifier](https://github.com/jtesta/souls_givifier) - DS2 AES encryption key and SteamID detection/patching
- [Smithbox](https://github.com/vawser/Smithbox) - Param CSV exports, used to derive the DS2 param field layout
- Elden Ring event flag, boss, gesture and summoning pool data from the Cheat Engine scripts by Dasaav and Umgak
- Appearance import supports the Elden Bling Auto Sliders JSON format

### Community

- All preset contributors
- Testers: [2Pz](https://github.com/2Pz), [Ghostlyswat12](https://github.com/Ghostlyswat12)

### Special Thanks

- [2Pz](https://github.com/2Pz) - Automated build/release workflow
- [Sayuri](https://github.com/Umgak) - Save file research, item spawning validation and patience in answering questions

## License

Source Available License - see [LICENSE](https://github.com/Hapfel1/er-save-manager/blob/main/LICENSE)