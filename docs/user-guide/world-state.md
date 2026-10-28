# World State & Teleportation

View character location and teleport to any of 875 known safe locations, a custom coordinate, or any spot on the world map. The world map also shows the character's progress (item pickups, NPCs, bosses, merchants, quests) and edits map markers and beacons.

## Overview

The World State tab displays character location information and provides teleportation:

- View current map and coordinates
- Teleport to a known location (searchable list of 875 locations)
- Teleport to any spot picked on the world map, or to a grace, dungeon, tile, pickup, boss, NPC or the bloodstain
- Custom coordinate teleportation, checked against the game's map data
- Warnings before teleports that can break the character (boss arenas, graces that are not spawned yet, DLC without ownership)
- Move bloodstain to player's current position
- Add, move, delete, export, import and copy map markers
- Unlock graces, map areas or a whole map, with their map pieces and play regions
- Item pickups, NPCs, bosses, merchants, quest steps, summoning pools, imp seals and paintings on the map, with respawn, revive, kill and restock
- Completion per region, exportable as a text file
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
- Scrollable list of all matching locations, tagged `[DLC]` where applicable and `[Boss Alive]` for graces that only appear after their boss
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

1. Pick the character in the **Character** bar
2. Character location displayed

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

**Graces behind a boss:** about 50 graces only appear once their boss is defeated (the boss's grace in the arena). Teleporting to one while the boss is alive puts the character in the boss arena, so the editor asks first.

**Ashen Capital:** on a vanilla save, teleporting into Leyndell, Ashen Capital while Maliketh is alive asks first, since that world state can get the account banned online.

Each of these warnings can be turned off in the dialog or in [Settings](settings.md#warning-dialogs).

---

## The World Map

The map window shows the game's own map for the Lands Between, the Underground and the Realm of
Shadow, fully revealed. Switch between them with the buttons at the top left. On a Convergence save
the map shows the Convergence map art, graces and locations instead.

- Scroll to zoom, drag with the left mouse button to pan (right or middle button pans too)
- Sites of Grace and dungeons use the game's map icons (legacy dungeons, catacombs and caves are
  drawn at their place on the map); locked graces are grayed out. The blue dot is the character
- Hovering any icon or tile shows its name and, for graces, whether it is unlocked
- The list on the left searches graces, dungeons, tiles, bosses, NPCs, merchants and items. Words
  match in any order, ignoring case and accents, and also match a pin's region and nearest grace,
  a boss's drop, an item's source and a merchant's stock. Repeated names get their region or
  grace added. Selecting an entry switches to its map, centers on it and selects it
- The selected entry gets a name tag; every other marker fades while it is selected
- **Character** at the top left switches the character (the same as the Character bar)
- The bloodstain shows where the character last died, with its runes; **Move Bloodstain to
  Player** in the right panel moves it to the character's position
- The legend under the location list explains the icons
- The checkboxes at the top turn the layers on and off: grid of teleport tiles, graces,
  dungeons, markers, NPC name tags (**Names**), plain dots instead of icons (**Dots**) and the
  progress layers below
- **Progress** (on by default) shades the areas of map fragments the character has not picked up
  with the game's unrevealed map art, so the map looks like it does for that character in game.
  The locations underneath stay visible and clickable, and the shading updates after an unlock
- Open it with **Open World Map** on the World Map card in the Teleportation column, or **Edit
  Markers on Map** in the left column

### Progress Layers

Each layer reads the selected character's event flags. Every write asks first and makes a backup.

- **Pickups** - item pickups as golden glows, gray once collected. **Types** filters them by item
  type (bell bearings and paintings have their own type). World pickups get **Respawn** and
  **Mark Collected**; boss, enemy and NPC rewards can be marked collected or respawned too, but a
  respawned reward is not placed back in the world
- **NPCs** - where each NPC currently stands, tinted when hostile or dead, with **Calm** and
  **Revive**. A marker shared by several NPCs opens a picker. Selecting an NPC also shows its quest
  steps as numbered pins along a dashed route; **Move Here** applies the quest up to that step
- **Bosses** - each boss with its reward as the icon (Remembrance and Great Rune bosses larger);
  **Kill** and **Respawn** (a respawn also moves the character to Roundtable Hold).
  **Remembrance Only** hides the other bosses
- **Merchants** - the full stock at each merchant; **Restock**, **Sold Out** and **Restock All**
- **Pools**, **Imp Seals**, **Paintings** - summoning pools (vanilla saves only), imp seals (the
  ones needing two keys marked) and painting vistas
- **Done %** in the list shows the completion of each region; selecting a region lists what is
  left. **Export Progress** writes the progress of any set of regions to a text file, optionally
  with the finished entries

On a Convergence save the layers use the Convergence data, including the mod's own bosses.

### Teleporting from the Map

1. Pick the character in the **Character** bar
2. Click **Open World Map**
3. Click a spot, grace, dungeon, pickup, boss, NPC or the bloodstain, or pick it from the list
4. Click **Teleport Here**

**Click** at the top picks what a click on empty map selects:

- **Pins** (default): the nearest walkable floor under the click. Where several floors lie under
  the click (a bridge and the ground below, castle levels), the side panel lists them under
  **Floors here** to pick one. A click with no floor near selects the tile
- **Tiles**: the overworld tile under the click; hovering a tile outlines it

A pin comes from the game's navigation mesh, not from a known safe spot, and can leave the
character under the ground, inside a wall or out of bounds, so a pin teleport asks first. Pins
inside a boss arena warn while that boss is alive. Pickups, bosses, NPCs and other markers
teleport to the floor nearest to them. The bloodstain teleports to its exact saved position,
after a warning when it holds runes.

### Locking and Unlocking Graces and Map Areas

Select a Site of Grace on the map. The panel shows whether it is unlocked and, for graces that
only appear after a boss, which boss (**Appears after**); **Unlock** / **Lock**
sets its event flag (the same as the Sites of Grace dialog in the Event Flags tab), makes a backup
and saves the file. Unlocking a grace also adds its play region, so the area shows as discovered.

- **Unlock Area** reveals the map piece of the selected location's area and unlocks its graces
- **Unlock Whole Map** does the same for the map that is shown (Lands Between, Underground or
  Realm of Shadow) and lists every map piece of it, so any set of pieces can be picked

Both open a dialog first: untick **Map pieces** to unlock only graces, or untick the graces to
reveal only map pieces. Graces whose boss is still alive are asked about separately: **Yes**
includes them, **No** skips them. Each grace belongs to one map piece, and only the graces of the picked
pieces are unlocked (all of the area or map when none or every piece is picked), with their play
regions. Revealing pieces also clears the fog of war over them (all fog of the map when every piece
is picked), extends the part of the map the map menu shows, and makes the Underground or Realm of
Shadow map available in game. A backup is made before saving.

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

**Checks before writing:**

- The line under the Map ID shows the map's name while typing; a map ID the game data does not
  know gets a warning
- A position with no floor within 4 units offers to move it to the nearest floor within 32 units.
  Past the edge of an overworld tile, this can change the map ID to the neighbouring tile
- Coordinates 0, 0, 0 on another map use that map's warp point (or the game's default spawn
  when it has none); on the same map they keep the current position

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
- Checks the map ID and the position against the game's map data
- Warns about DLC locations without DLC access, boss arenas and graces whose boss is alive

**No guarantee teleport will work for custom coordinates or map pins:**

- An invalid position may cause:
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
