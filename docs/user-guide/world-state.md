# World State & Teleportation

View character location and teleport to any of 451 known safe locations, a custom coordinate, or a point on an interactive overworld map.

## Overview

The World State tab displays character location information and provides teleportation:

- View current map and coordinates
- Teleport to a known location (searchable list of 451 locations)
- Teleport by clicking a point on an interactive overworld map
- Custom coordinate teleportation
- Move bloodstain to player's current position

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

- Known Locations
- Custom Coordinates

**Known Locations:**

- Search bar to filter by name or Map ID
- Scrollable list of all matching locations, tagged `[DLC]` where applicable
- **Teleport to Selected Location** button
- **Open Map** button - opens an interactive overworld map image; click a location marker to teleport there directly

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

- Resolved from Map ID against the 451-entry location database
- Shows area name (e.g., "Roundtable Hold", "Limgrave", "Liurnia")
- If unknown: Shows "Unknown Location"

**Coordinates:**

- **X:** East-West position
- **Y:** Vertical height
- **Z:** North-South position

**Map ID:**

- Format: `[M, AA, BB, CC]`

---

## Teleporting to a Known Location

1. Load character data
2. Switch to **Known Locations** mode
3. Type in the search bar to filter (matches name or Map ID)
4. Select a location from the list
5. Click **Teleport to Selected Location**

**DLC locations:** Selecting a location flagged `[DLC]` on a character without Shadow of the Erdtree access shows a warning before teleporting, since it will cause an infinite loading screen if the DLC isn't owned.

Teleporting to a known location also adds that location's region unlock ID if the character doesn't already have it, so the map isn't left partially fogged after warping in.

---

## Teleporting via the Interactive Map

1. Load character data
2. Click **Open Map**
3. The overworld map image opens with all small-tile locations marked, and the character's current map highlighted
4. Click a marker to teleport there

---

## Custom Coordinate Teleportation

### How It Works

Directly modify character's position coordinates in save file. Intended for precise placement the known-location list doesn't cover.

**Steps:**

1. Load character data
2. Switch to **Custom Coordinates** mode
3. Enter custom coordinates:
   - X value (float)
   - Y value (float)
   - Z value (float)
4. Enter Map ID values:
   - M
   - AA
   - BB
   - CC
5. Click **Teleport**
6. Automatic backup created
7. Coordinates written to save

**Result:** Character teleports to specified coordinates on next game load

---

## Move Bloodstain to Player

Moves the character's bloodstain (death marker with lost runes) to the character's current coordinates and map. Useful when a bloodstain is stranded in an unreachable or corrupted location.

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
- Warns about DLC locations without DLC access

**No guarantee teleport will work for custom coordinates:**

- Invalid custom coordinates may cause:
  - Infinite loading screen
  - Fall through world
  - Stuck state
- Known locations use verified safe coordinates and don't carry this risk (aside from the DLC-ownership case above)

### Recovery

**If teleport causes issues:**

1. Close game
2. Open Backup Manager
3. Restore backup before teleport
4. Try a known location instead of custom coordinates

---

## Related Features

- **[Save File Fixer](save-file-fixer.md)** - Fix teleport-related corruption
- **[Backup Manager](backup-manager.md)** - Restore after bad teleport
- **[Troubleshooting](troubleshooting-tab.md)** - Diagnose loading issues

---

## FAQ

**Q: Can teleporting break my save?**
A: Custom coordinates can cause loading issues if invalid, but the backup system prevents permanent damage. Known locations use verified safe coordinates.

**Q: Can I teleport to DLC areas?**
A: Yes, but you must own the DLC or the game won't load. The tool warns before teleporting to a DLC location if it doesn't detect DLC access.

---

[← Appearance](appearance.md) | [Next: Event Flags →](event-flags.md)
