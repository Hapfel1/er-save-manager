# Elden Ring Save Manager

A comprehensive save file editor, backup manager, and corruption fixer for Elden Ring with an intuitive GUI, community Browsers, ItemGib and much more. Also supports editing Dark Souls Remastered, Dark Souls 2: Scholar of the first Sin, Dark Souls 3 and Nightreign Save Files.

## Documentation and User Guides

[https://elden-ring-save-manager.readthedocs.io/en/main/](https://elden-ring-save-manager.readthedocs.io/en/main/)

## Features

### Working Features

- **Save File Fixer**: Automatically detect and fix save corruption issues and infinite loading screens
- **Character Management**: Export, import, and move characters between saves
- **Community Character Browser**: Browse, download, and contribute characters with likes and download tracking
- **Character Editor**: Edit stats, runes, name, level, and build attributes
- **Inventory Editor**: Edit your inventory, spawn in items, import builds
- **Equipment Editor**: Edit your current equipped items, save and share loadouts
- **Appearance Editor**: View, export and import Presets
- **Community Preset Browser**: Browse, download, and contribute character appearance presets with likes and download tracking
- **World State / Teleportation**: 451 known safe locations to warp to as well as custom coordinate teleportation. Interactive map of the overworld for teleporting.
- **SteamID Patcher**: Transfer saves between Steam accounts
- **Event Flags Editor**: Read and toggle event flags
- **Boss Respawner**: Respawn/Kill any boss for repeated fights
- **NPC Respawner**: Respawn NPCs
- **NPC Quest Tracker**
- **Gestures**: Unlock gestures
- **Invasion Regions & Game Settings**: View and edit invasion regions and game settings
- **Backup Manager**: Automatic and manual backups with restore functionality
- **Troubleshooting**: Troubleshooter for checking game launch/connection related issues
- **Backup Manager and SteamID Patcher for**: Elden Ring, Elden Ring Nightreign, Armored Core 6, Sekiro, Dark Souls III, Dark Souls Remastered
- **DSR**: Stats Editing, Character Management, Event Flags, Boss Revival, NPC Revival, Item Spawning
- **DS3**: Stats Editing, Character Management, Item Spawning and Inventory Editing with Visual Item Picker, Boss Revival, NPC Revival, Bonfires, Gestures, NG+, Supports Convergence, Cinders and SeamlessCoop
- **Nightreign**: Relic spawning and editing, Chalice Loadouts and Presets, Editing Murk, Character Management
- **DS2**: Stats Editing, Item Spawning, Build Import from Souls Planner, Character Management, Bonfire Editing, NPC Revival

### Work in Progress

- **Implementing Save Editing for other Fromsoft Games**

## Installation

Download the latest release from [Releases](https://github.com/Hapfel1/er-save-manager/releases).

### Platform Support

- **Windows**: Executable
- **Linux**: AppImage
  - Supports Steam (standard and Flatpak)
  - Supports SteamDeck fully
  - Auto-detects Proton compatdata locations
  - Warns about non-default save locations
- **PlayStation/Switch Saves**: Supports editing decrypted console Save Files.

## Usage

1. Run `Elden Ring Save Manager`
2. Use Auto-Detect or Browse to select your Save File
3. Press "Load Save File"
4. Use the tabs to access different features

## Feature Details

### Save File Fixer

Automatically detects and fixes common save corruption issues:

- **Torrent Bug**: Fixes infinite loading when Torrent HP=0 with state=ACTIVE
- **Torn Save Files**: Detects and fixes torn writes in save files mostly caused by game crashes and fixes them.
- **Ranni Softlock**: Fixes Ranni's Tower softlock
- **Warp Sickness**: Fixes stuck warps (Radahn, Morgott, Radagon, Sealing Tree)
- **Stuck at DLC coordinates**: Teleports your character to the Roundtable if you tried accessing the DLC without owning it.
- **DLC Flag**: Clears Shadow of the Erdtree entry flag if accidentally set
- **Invalid DLC Data**: Clears garbage data in unused DLC slots
- **Teleport Fallback**: Teleports your character to the roundtable for any other invalid coordinates that cause an infinite loading screen

### Troubleshooting Tab

Automatically detects issues with your game installation, your save file and any software that could cause issues

- Scans and validates game files
- Checks for Steam Elevation
- Checks for interfering software that may stop the modded game from launching
- Checks for VPNs

### Character Management

- **Export Characters**: Save individual characters to `.erc` files
- **Import Characters**: Load characters from `.erc` into any slot
- **Move Between Slots**: Reorganize characters within a save
- **Copy Between Saves**: Transfer characters to different save files
- **Delete a Character**

### Community Character Browser

- Browse characters from the community and download characters from others
- Like your favorite characters
- Download tracking
- Submit your own characters to share with others
- Image preview (face and body)
- Search and filter functionality
- Report inappropriate content
- Local cache for fast loading
- Supports Convergence Mod for character submission
- Allows specifying and contributing any overhaul mod character

### Character Editor

- Edit base stats (Vigor, Mind, Endurance, Strength, Dexterity, Intelligence, Faith, Arcane)
- Modify character name and level
- Adjust runes held
- Edit NG level

### Inventory Editor

- Edit your inventory, remove items, spawn in items
- Full Item Validation to avoid any invalid items and allow Item Spawning for Vanilla Saves
- Supports SeamlessCoop and Convergence Items
- Visual Item Picker and Visual Inventory Editor with full Icon Support
- Loadout Mode for creating and sharing loadouts
- Share Loadouts via unique code
- Batch Adding Category functionality
- Build Import Functionality from the Elden Ring Build & Inventory Planner

### Equipment Editor

- Edit your current equipped items
- Save Loadouts and share them via JSON or unique Code
- Visual Equipment Viewer and Item Picker

### Appearance Editor

- View Details of a Preset
- Export/Import a Preset from/to a `.json` file (Supports importing from Elden Bling Sliders)
- Share Presets via unique Code
- Delete a Preset
- Copy a Preset to a different Save file
- Browse Community presets

### Community Preset Browser

- Browse character appearance presets from the community
- 104 NPC Appearance Presets from the Game's Data
- Like your favorite presets
- Download tracking
- Submit your own presets to share with others
- Image preview (face and body)
- Search and filter functionality
- Report inappropriate content
- Local cache for fast loading

### World State / Teleportation

- Display of current location
- 451 known locations to teleport to
- Interactive map of the overworld for teleporting
- Custom Coordinate Teleportation
- "Move Bloodstain to Player" function

### SteamID Patcher

- Transfer saves between Steam accounts
- Patch the SteamID of the save file using ID or custom profile link resolution

### Event Flags

- Search and toggle event flags
- Documented and Custom

### Boss Respawner

- Respawn any boss for repeated fights
- Kill any boss
- Supports all main game and DLC bosses
- One-click respawn functionality
- Check Boss Status

### NPC Respawner

- Respawn NPCs
- One-click respawn functionality

### NPC Quest Tracker

- Check NPC quest progress
- Modify steps, reset progress

### Gestures

- Unlock gestures

### Regions & Game Settings

- View and unlock invasion regions
- View and edit game settings

### Backup Manager

- Automatic backups before any edit
- Manual backup creation with custom names
- Browse and restore previous backups
- Backup pruning with configurable retention
- One-click restore with confirmation
- Function for Auto-Backup Creation on Game Launch

### Backup Manager and SteamID Patcher for other Fromsoftware Games

- Elden Ring Nightreign
- Armored Core 6
- Sekiro
- Dark Souls III
- Dark Souls II SotfS
- Dark Souls Remastered

### DSR

- Stats Editing
- Character Management
- Event Flags
- Boss Revival
- NPC Revival
- Item Spawning (Supports SeamlessCoop Items)

### DS3

- Stats Editing (level follows the attributes), name and NG+ cycle
- Character Management
- Item Spawning that stores items the way the game does, into the inventory or the storage box
- Item data, limits and icons read from the game files of Vanilla, Convergence and Cinders, with infusion selection and infusion icons
- SeamlessCoop items for `.co2` saves
- Visual Item Picker and Visual Inventory Editor with infused weapon badges
- Batch spawning and editing: quantity, upgrade level, infusion, moving between inventory and storage box, removal
- Equipped items are protected from removal, cut content is hidden by default and confirmed before spawning
- Boss Revival (all bosses including DLC)
- NPC Revival (revive or kill)
- Bonfires (light/unlight by area)
- Gestures (unlock/lock)
- NG+ cycle editing

### Nightreign 

- Relic spawning and editing
- Copy a relic to the spawner, JSON import/export of relics
- Loadouts tab: edit chalice relic loadouts and custom presets, including modded and over-capacity loadouts
- Editing Murk
- Character Management

### DS2

- Stats Editing
- Item Spawning (weapon upgrades and infusions, SeamlessCoop items for `.co2` saves)
- Visual Item Picker and Visual Inventory Editor with full Icon Support
- Multi-select batch editing in the visual picker and inventory
- Equipped items are protected from removal and storing
- Build Import from [Souls Planner](https://soulsplanner.com) links (stats and items)
- Character Management
- Bonfire Editing (light/unlight, Bonfire Ascetic level)
- NPC Revival

## Building from Source

See [DEVELOPMENT.md](DEVELOPMENT.md)

## License

Source Available License - see [LICENSE](LICENSE)

## Credits

### Save File Research
- [ER-Save-Lib](https://github.com/ClayAmore/ER-Save-Lib) - Rust implementation and reverse engineering research
- [Sayuri](https://github.com/Umgak) for allowing me to use her contributions to the [TGA Cheat Table](https://github.com/The-Grand-Archives/Elden-Ring-CT-TGA), specifically the Event Flag Manager's tables
- [?WikiName?](https://soulsmodding.com/doku.php?id=er-refmat:main) for the available documentation
- [SimpleSekiroSavegameHelper](https://github.com/uberhalit/SimpleSekiroSavegameHelper) for offsets and constants for Sekiro steamid patcher
- DS3 AES encryption key found by Atvaark, published in [DS3SaveUnpacker](https://github.com/tremwil/DS3SaveUnpacker) by tremwil
- Nightreign AES encryption key: TKGP and EonaCat
- DS2 Save format research based on the [Dark-Souls-2-Save-Editor-PS4-PC](https://github.com/alfizari/Dark-Souls-2-Save-Editor-PS4-PC)
- DS2 AES encryption key and SteamID detection/patching adapted from [souls_givifier](https://github.com/jtesta/souls_givifier)
- [Smithbox](https://github.com/vawser/Smithbox) param CSV exports, used to derive the DS2 param field layout
- Elden Ring event flag, boss, gesture and summoning pool data from the Cheat Engine scripts by Dasaav and Sayuri ([TGA Cheat Table](https://github.com/The-Grand-Archives/Elden-Ring-CT-TGA))
- [UXM Selective Unpack](https://github.com/Nordgaren/UXM-Selective-Unpack) archive keys and file name dictionaries, used to read DS3 game data for item, bonfire, boss, NPC and gesture data
- Smithbox param definitions, icon layouts and community row names, used for DS3 and DS2 item and icon data


### Community
- All preset contributors
- Testers: [2Pz](https://github.com/2Pz), [Ghostlyswat12](https://github.com/Ghostlyswat12)

### Special Thanks
- [2Pz](https://github.com/2Pz) for implementing an automated build/release workflow
- [Sayuri](https://github.com/Umgak) for her invaluable help on save file research and item spawning validation and her patience in answering questions.
