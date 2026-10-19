# World State & Teleportation

View character location and teleport to any of 875 known safe locations, a custom coordinate, or a point on the world map. The world map also edits the character's map markers and beacons.

## Overview

The World State tab displays character location information and provides teleportation:

- View current map and coordinates
- Teleport to a known location (searchable list of 875 locations)
- Teleport by clicking a tile, grace or dungeon on the world map
- Custom coordinate teleportation
- Move bloodstain to player's current position
- Add, move, delete, export, import and copy map markers
- Unlock graces, map areas or a whole map, with their map pieces and play regions
- Convergence saves get the Convergence world map with its own grace positions
- Legendary trophy progress and item history
- List, protect and delete the character's messages

---

## Interface Layout

### Left Column: Character Info

**Character:**

- The **Character** bar under the file row picks the character; its data loads as soon as one is selected

**Current Location Display:**

- Map name (e.g., "Limgrave - First Step")
- Coordinates (X, Y, Z)
- Map ID (4-byte array)

**Messages:**

- Number of own messages and of cached messages from other players
- Manage Messages button

### Right Column: Teleportation

**Mode Selection:**

- Known Locations
- Custom Coordinates

**Known Locations:**

- Search bar to filter by name or Map ID
- Scrollable list of all matching locations, tagged `[DLC]` where applicable
- **Teleport to Selected Location** button

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

- Resolved from Map ID against the 875-entry location database
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

1. Pick the character in the **Character** bar
2. Switch to **Known Locations** mode
3. Type in the search bar to filter (matches name or Map ID)
4. Select a location from the list
5. Click **Teleport to Selected Location**

**DLC locations:** Selecting a location flagged `[DLC]` on a character without Shadow of the Erdtree access shows a warning before teleporting, since it will cause an infinite loading screen if the DLC isn't owned.

Teleporting to a known location also adds that location's region unlock ID if the character doesn't already have it, so the map isn't left partially fogged after warping in.

---

## The World Map

The map window shows the game's own map for the Lands Between, the Underground and the Realm of
Shadow, fully revealed. Switch between them with the buttons at the top left. On a Convergence save
the map shows the Convergence map art, graces and locations instead.

- Scroll to zoom, drag with the left mouse button to pan (right or middle button pans too)
- Sites of Grace and dungeons use the game's map icons (legacy dungeons, catacombs and caves are
  drawn at their place on the map); locked graces are grayed out. The blue dot is the character
- Hovering an overworld tile outlines it; hovering any icon or tile shows its name and, for graces,
  whether it is unlocked
- The list on the left searches every grace, dungeon and tile by name or map ID; selecting an
  entry switches to its map, centers on it and selects it
- **Character** at the top left switches the character (the same as the Character bar)
- The bloodstain shows where the character last died, with its runes; **Move Bloodstain to
  Player** in the right panel moves it to the character's position
- The legend under the location list explains the icons
- The checkboxes at the top hide graces, dungeons or markers, turn tile selection off, or show the
  outline of every teleport tile (**Grid**). Tile selection is off while adding markers or beacons
- Open it with **Open World Map** on the World Map card in the Teleportation column, or **Edit
  Markers on Map** in the left column

### Teleporting from the Map

1. Pick the character in the **Character** bar
2. Click **Open World Map**
3. Click a tile, grace or dungeon, or pick it from the list
4. Click **Teleport Here**

### Locking and Unlocking Graces and Map Areas

Select a Site of Grace on the map. The panel shows whether it is unlocked; **Unlock** / **Lock**
sets its event flag (the same as the Sites of Grace dialog in the Event Flags tab), makes a backup
and saves the file. Unlocking a grace also adds its play region, so the area shows as discovered.

- **Unlock Area** reveals the map piece of the selected location's area and unlocks its graces
- **Unlock Whole Map** does the same for every area of the map that is shown (Lands Between,
  Underground or Realm of Shadow)

Both ask first, list what changes, and add the play regions of the unlocked graces. A backup is
made before saving.

### Map Markers

The side panel lists the character's map markers and beacons (up to 100 markers and 10 beacons).

- **Place on click**: while checked, a click on the map places a marker with the icon chosen next
  to it
- Drag a marker to move it; select one and pick an icon to change its icon
- **Delete** (or the Delete key) removes the selected marker or beacon; **Clear Map** removes
  everything on the shown map, **Clear All** everything on all maps
- **Export...** writes the markers to a JSON file; **Import...** reads one and asks whether to
  replace or append
- **Copy To...** copies the markers to another character in the same save, replacing or appending
- Changes are staged until **Apply All** in the unapplied-changes bar of the main window, which
  writes them together with the other staged edits after one backup. **Revert** discards them

Marker icons are listed by the number the save stores (1-10). Characters last saved by an old
game version keep an older marker layout that the editor does not change; loading and saving them
in game converts it.

---

## Item History

**Show Item History** in the left column lists:

- **Legendary Items**: the items the four Legendary trophies count, and which ones this character
  has already been credited with
- **All Items**: every item in the database, marked acquired or missing. The game remembers every
  item type the character has picked up, also after it was sold, discarded or used up. Filter by
  base game or DLC, category, state and name

---

## Custom Coordinate Teleportation

### How It Works

Directly modify character's position coordinates in save file. Intended for precise placement the known-location list doesn't cover.

**Steps:**

1. Pick the character in the **Character** bar
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

## Messages

**Manage Messages...** opens a list of the messages stored in the slot, with the text as the game shows it,
the attached gesture and the location.

- **My Messages:** the messages the character wrote (up to 10). Select one or more and use Protect,
  Unprotect or Delete. A backup is created before every change.
- **Cached Messages:** messages of other players the game stored for the area the character is in.
  Read-only; the game refreshes them during online play.

Changes only last in offline play. Online, the game restores the character's messages from its server,
which undoes deletes and protection changes.

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
