# Elden Ring Save Manager Documentation

Welcome to the Elden Ring Save Manager documentation. This tool provides comprehensive save file management, corruption fixing, and character editing for Elden Ring.

```{toctree}
:maxdepth: 2
:caption: User Guide

user-guide/installation
user-guide/quick-start
user-guide/save-file-fixer
user-guide/character-management
user-guide/character-editor
user-guide/appearance-editor
user-guide/community-browser
user-guide/steamid-patcher
user-guide/event-flags
user-guide/boss-respawner
user-guide/gestures-regions
user-guide/backup-manager
user-guide/troubleshooting-tab
```

```{toctree}
:maxdepth: 2
:caption: Technical Documentation

technical/save-file-structure
technical/character-slot-structure
technical/checksum-system
technical/event-flag-system
technical/parser-architecture
technical/offset-tracking
technical/backup-system
technical/fix-system
technical/community-integration
```

```{toctree}
:maxdepth: 2
:caption: Reference

reference/event-flags
reference/item-ids
reference/map-ids
reference/file-formats
```

```{toctree}
:maxdepth: 2
:caption: Developer Guide

developer/building
developer/contributing
developer/testing
developer/cli-reference
```

```{toctree}
:maxdepth: 1
:caption: Resources

resources/faq
resources/troubleshooting
resources/keyboard-shortcuts
```

## Quick Links

- [Installation](user-guide/installation.md) - Get started
- [Quick Start Guide](user-guide/quick-start.md) - Learn the basics
- [Save File Fixer](user-guide/save-file-fixer.md) - Fix infinite loading screens
- [GitHub Repository](https://github.com/Hapfel1/er-save-manager)
- [Report Issues](https://github.com/Hapfel1/er-save-manager/issues)

## Features

- **Automated Corruption Detection & Fixing** - Detect and repair infinite loading screens
- **Character Management** - Export, import, move characters between saves
- **Community Integration** - Browse and share characters and appearance presets
- **Character Editing** - Modify stats, runes, name, level
- **Appearance Customization** - Create and share character presets
- **Event Flags** - Toggle quest progress, boss defeats, grace unlocks
- **SteamID Patching** - Transfer saves between Steam accounts
- **Backup System** - Automatic and manual backups with restore
- **Diagnostics** - Troubleshoot game and save file issues

## Platform Support

- **Windows**: Native executable
- **Linux**: AppImage with Steam/Proton support
- **Steam Deck**: Fully supported with auto-detection

## Credits

**Save File Research:**
- [ER-Save-Lib](https://github.com/ClayAmore/ER-Save-Lib) - Rust reference implementation
- [Umgak](https://github.com/Umgak) - Event Flag Manager from TGA Cheat Table
- [SoulsModding Wiki](https://soulsmodding.com/doku.php?id=er-refmat:main)

**Special Thanks:**
- [2Pz](https://github.com/2Pz) - Automated build workflow
- [Ghostlyswat12](https://github.com/Ghostlyswat12) - Testing
- Community contributors and preset creators

## License

MIT License - see [LICENSE](https://github.com/Hapfel1/er-save-manager/blob/main/LICENSE)
