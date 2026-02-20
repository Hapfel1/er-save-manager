# World State & Teleportation

View character location and teleport using custom coordinates (known location list currently disabled).

## Overview

The World State tab displays character location information and provides custom coordinate teleportation:

- View current map and coordinates
- Custom coordinate teleportation
- Location validation

**Note:** Known location list is temporarily disabled pending verification. Only custom coordinate entry is available.

---

## Interface Layout

### Left Column: Character Info

**Character Slot Selector:**

- Select slot (1-10)
- Load button to load character data

**Current Location Display:**

- Map name (e.g., "Limgrave - First Step")
- Coordinates (X, Y, Z)
- Map ID (4-byte array)

### Right Column: Teleportation

**Mode Selection:**

- Custom coordinates (only available mode currently)

**Custom Coordinates Entry:**

- X coordinate input
- Y coordinate input  
- Z coordinate input
- Map ID input (4 values: M, AA, BB, CC)

**Teleport Button:**

- Apply teleport to selected character
- Creates automatic backup before teleporting

---

## Viewing Current Location

### Loading Character Data

**Steps:**

1. Select character slot (1-10)
2. Click **Load**
3. Character location displayed

### Location Information

**Map Name:**

- Resolved from Map ID
- Shows area name (e.g., "Roundtable Hold", "Limgrave", "Liurnia")
- If unknown: Shows "Unknown Location"

**Coordinates:**

- **X:** East-West position
- **Y:** Vertical height
- **Z:** North-South position

**Map ID:**

- Format: `[M, AA, BB, CC]`
- M:
- AA:
- BB:
- CC:

---

## Custom Coordinate Teleportation

### How It Works

Directly modify character's position coordinates in save file.

**Steps:**

1. Load character data
2. Enter custom coordinates:
   - X value (float)
   - Y value (float)
   - Z value (float)
3. Enter Map ID values:
   - M
   - AA
   - BB
   - CC
4. Click **Teleport**
5. Automatic backup created
6. Coordinates written to save

**Result:** Character teleports to specified coordinates on next game load

---

## Map ID System

### Format Explanation

Map ID: `[M, AA, BB, CC]`

**M (Major Region):**

- 60: Main world
- 61: Underground
- Other values for special areas

**AA (Area):**

- Specific region within major zone
- Example: 40 = Limgrave, 51 = Liurnia

**BB (Block):**

- Subdivision of area
- Grid coordinate

**CC (Sub-block):**

- Fine-grained location
- Usually 00 for main areas

---

## Safety Features

### Automatic Backup

**Before every teleport:**

- Full save backup created
- Timestamp included
- Stored in backup folder
- Easy restore if coordinates invalid

### Coordinate Validation

**Basic checks:**

- Verifies values are numbers
- Ensures Map ID bytes are 0-255
- Warns about unusual values

**No guarantee teleport will work:**

- Invalid coordinates may cause:
  - Infinite loading screen
  - Fall through world
  - Stuck state

### Recovery

**If teleport causes issues:**

1. Close game
2. Open Backup Manager
3. Restore backup before teleport
4. Try different coordinates

---

## Known Location List (Currently Disabled)

The known location dropdown is temporarily disabled pending verification of coordinates.

**When re-enabled will include:**

- All known grace locations

**Check for updates** in future versions for re-enabled known location list.

---

## Related Features

- **[Save File Fixer](save-file-fixer.md)** - Fix teleport-related corruption
- **[Backup Manager](backup-manager.md)** - Restore after bad teleport
- **[Troubleshooting](troubleshooting-tab.md)** - Diagnose loading issues

---

## FAQ

**Q: Why is the known location list disabled?**  
A: Coordinates are being verified and tested. Custom coordinates still work.

**Q: Can teleporting break my save?**  
A: Invalid coordinates can cause loading issues, but the backup system prevents permanent damage.

**Q: Can I teleport to DLC areas?**  
A: Yes, but you must own the DLC or the game won't load.

---

[← Appearance](appearance.md) | [Next: Event Flags →](event-flags.md)