Save File Load: 
- Auto-Find, make it work for Linux, search with find and ER0000 plus any ending in the compatdata folders as well as look in the default compatdata folder (How would you deal with autofind in Linux given the compatdata can be anything?
Just do a find and return the locations)
- create a class for centralized platform utlilites
- give a tooltip on what to add as a launch option and add the option to move the save file to the default compatdata location
or like a warning that the save file may disappear if the launcher exe is removed from steam

Backup-Manager:
- Think about how to handle different save files with the same name that may get replaced: Maybe attach a name to a save file that gets saved with it so you can also load different save files and back them up?

Character Manager:
- Make the window scrollable and the selection of the operations in sub tabs next to eachother, not in a list below eachother
- Implement the Operation functionality

Character Editor:
-  Put Health/FP/Stamina next to Attributes as there is a lot of free space in the window and put apply changes and revert in its own tab like view details & issues has its own action tab in the save inspector
- Also calculate characterlevel and change it based on changing attributes, give a warning if it is not the same before applying and recommend setting it to the actual level (Example: you change vigor from 12 to 15, so your character level should go from 9 to 12 which needs to be changed too)
- Make Health/FP/Stamina only the max values editable, the active values have no need for that

- Implement Equipment Editor
- Implement Character Info

Appearance:
- Fix Import (failed to import preset from json)
- Give option to delete presets/edit them in there too
- Implement Tab for preset browser with presets (coming in the future)

World State: 
- Implement World State
- Implement Teleportation feature with dropdown list of all known locations (give documentation txt for that) / also the option to type in custom coords with a warning ofc

SteamID Patcher:
- Fix Current Save file: SteamID: Unable to read
- Add option to paste in steamprofile link to get the ID

Event Flags:
- Implement event flag load
- Add documentatio
- Expand common scripts to be used / split up in categories/tabs if needed

Gestures&Regions:
- Implement together with documentation and unlocking features

Hex Editor:
- Make it scrollable and editable

Save File Fixer:
- make sure to implement the disable dlc flag function



Whole feature list below
# Elden Ring Save Editor - Complete Function Breakdown

Each function listed with: description, data source, read/write requirements, and dependencies.

---

## 1. BACKUP MANAGER

### 1.1 Create Backup
- **Description**: Copy current save file to backup location with metadata
- **Input**: Save file path, optional name/description
- **Output**: Backup file + metadata JSON entry
- **Requirements**:
  - File copy operation
  - Generate timestamp
  - Parse save to extract character summary (names, levels) for metadata
  - Create backup folder if not exists
  - Optional: zstd/gzip compression

### 1.2 List Backups
- **Description**: Show all backups for a save file
- **Input**: Save file path (to find associated backup folder)
- **Output**: List of backups with timestamp, size, description, character summary
- **Requirements**:
  - Read metadata JSON
  - List files in backup folder
  - Sort/filter capabilities

### 1.3 Restore Backup
- **Description**: Replace current save with selected backup
- **Input**: Backup file path, target save path
- **Output**: Restored save file
- **Requirements**:
  - Create backup of current before restore (safety)
  - File copy operation
  - Optional: decompress if compressed
  - Validate backup integrity before restore

### 1.4 Restore Single Slot
- **Description**: Copy one character slot from backup into current save
- **Input**: Backup path, source slot index, target slot index
- **Output**: Modified current save with merged slot
- **Requirements**:
  - Parse both backup and current save
  - Extract character slot data (UserDataX)
  - Extract profile summary data
  - Write slot to target position
  - Update checksums
  - Update active slots array in USER_DATA_10

### 1.5 Compare Backups
- **Description**: Show differences between two saves/backups
- **Input**: Two save file paths
- **Output**: Diff report (changed values per slot)
- **Requirements**:
  - Parse both saves fully
  - Compare field by field
  - Format readable output

### 1.6 Delete Backup
- **Description**: Remove a backup file and its metadata entry
- **Input**: Backup identifier
- **Output**: None
- **Requirements**:
  - Delete file
  - Update metadata JSON

### 1.7 Prune Backups
- **Description**: Delete old backups based on policy
- **Input**: Keep count or age threshold
- **Output**: Deleted backup list
- **Requirements**:
  - Sort backups by date
  - Delete oldest until policy satisfied

### 1.8 Verify Backup Integrity
- **Description**: Check backup file is valid and not corrupted
- **Input**: Backup path
- **Output**: Valid/invalid status with details
- **Requirements**:
  - Parse save structure
  - Validate checksums
  - Check magic bytes

---

## 2. CHARACTER MANAGEMENT

### 2.1 List Characters
- **Description**: Display all 10 character slots with summary info
- **Input**: Save file
- **Output**: List with name, level, playtime, location, status
- **Data Sources**:
  - `USER_DATA_10.ProfileSummary.profiles[i]`: name, level, seconds_played
  - `UserDataX.map_id`: current location
  - `UserDataX.player_game_data`: detailed stats
  - `USER_DATA_10.ProfileSummary.active_slots[i]`: slot active flag
- **Requirements**:
  - Parse save header
  - Parse USER_DATA_10 for profile summary
  - Parse each UserDataX for detailed info
  - Run corruption detection per slot

### 2.2 Copy Character (Same Save)
- **Description**: Duplicate character from one slot to another
- **Input**: Save path, source slot (0-9), target slot (0-9)
- **Output**: Modified save with copied character
- **Data to Copy**:
  - `UserDataX` (entire ~2.6MB character data)
  - `USER_DATA_10.ProfileSummary.profiles[target]` from source
  - Set `USER_DATA_10.ProfileSummary.active_slots[target] = 1`
- **Requirements**:
  - Read source slot raw bytes
  - Write to target slot position
  - Copy profile summary entry
  - Update active slots
  - Recalculate target slot checksum
  - Recalculate USER_DATA_10 checksum

### 2.3 Copy Character (Different Save)
- **Description**: Copy character from one save file to another
- **Input**: Source save + slot, target save + slot
- **Output**: Modified target save
- **Data to Copy**: Same as 2.2
- **Additional Requirements**:
  - Patch SteamID in copied character to match target save
  - Handle version differences between saves

### 2.4 Export Character
- **Description**: Save character data to standalone file
- **Input**: Save path, slot index, output path
- **Output**: .erc file containing character data
- **File Format** (.erc):
  ```
  Magic: "ERC\0" (4 bytes)
  Version: uint32
  Flags: uint32 (has_profile, compressed, etc.)
  SteamID: uint64 (original, for reference)
  ProfileData: 0x24C bytes (from ProfileSummary)
  UserDataX: ~2.6MB (character slot)
  Checksum: MD5 of above
  ```
- **Requirements**:
  - Extract UserDataX raw bytes
  - Extract ProfileSummary entry
  - Write custom file format

### 2.5 Import Character
- **Description**: Load character from .erc file into save slot
- **Input**: Save path, slot index, .erc file path
- **Output**: Modified save with imported character
- **Requirements**:
  - Validate .erc file format and checksum
  - Patch SteamID to match target save
  - Write UserDataX to slot
  - Write ProfileSummary entry
  - Update active slots
  - Recalculate checksums

### 2.6 Export Character as JSON
- **Description**: Export character data as human-readable JSON
- **Input**: Save path, slot index
- **Output**: JSON file with all parsed fields
- **Requirements**:
  - Full UserDataX parsing
  - Serialize all structures to JSON
  - Include readable names (not just IDs)

### 2.7 Import Character from JSON
- **Description**: Apply JSON modifications to character
- **Input**: Save path, slot index, JSON file
- **Output**: Modified save
- **Requirements**:
  - Parse JSON
  - Map fields to binary offsets
  - Write modified values
  - Recalculate checksums

### 2.8 Swap Character Slots
- **Description**: Exchange two character slots
- **Input**: Save path, slot A, slot B
- **Output**: Modified save with swapped characters
- **Requirements**:
  - Temp storage for one slot
  - Copy A to temp, B to A, temp to B
  - Swap ProfileSummary entries
  - Recalculate both checksums

### 2.9 Delete Character
- **Description**: Clear a character slot
- **Input**: Save path, slot index
- **Output**: Modified save with empty slot
- **Requirements**:
  - Zero out UserDataX data (or set to empty template)
  - Clear ProfileSummary entry
  - Set active_slots[i] = 0
  - Recalculate checksums

---

## 3. APPEARANCE PRESETS

### 3.1 View Face Data
- **Description**: Display all facial/body parameters
- **Input**: Save path, slot index
- **Output**: Structured display of all FaceData fields
- **Data Source**: `UserDataX.face_data` (0x12F bytes)
- **Display Modes**:
  - **Standard Mode**: Shows documented/named fields only
  - **Advanced Mode**: Shows ALL bytes including unknown/undocumented fields with hex values
- **Fields** (partial list):
  - Face model, Hair model, Eyebrow model, Beard model
  - Age, Facial aesthetic, Form emphasis
  - Bone structure (40+ parameters)
  - Body proportions (head, chest, abdomen, arms, legs)
  - Skin color (RGB + luster + pores)
  - Makeup (eyeliner, eyeshadow, lipstick colors)
  - Eye colors (left/right independent)
  - Hair/beard/brow colors and properties
  - Tattoo/markings
  - **Advanced**: unk0x45, unk0x4a, unk0x4d, unk0x6c[64], unk0xb1[2], unk0xd8, pad[10]

### 3.2 Export Face Preset (Binary)
- **Description**: Save face data to standalone binary file
- **Input**: Save path, slot index, output path
- **Output**: .erface file
- **File Format** (.erface):
  ```
  Magic: "FACE" (4 bytes)
  Version: uint32
  Size: uint32 (0x12F for full, 0x120 for profile)
  FaceData: raw bytes
  Checksum: MD5
  ```
- **Requirements**:
  - Extract FaceData bytes
  - Write file with header

### 3.3 Export Face Preset (JSON)
- **Description**: Save face data as human-readable/editable JSON
- **Input**: Save path, slot index, output path
- **Output**: .json file
- **JSON Structure**:
  ```json
  {
    "version": 1,
    "format": "elden_ring_face_preset",
    "face_model": 5,
    "hair_model": 12,
    "eyebrow_model": 3,
    "beard_model": 0,
    "apparent_age": 128,
    "facial_aesthetic": 128,
    "bone_structure": {
      "brow_ridge_height": 128,
      "inner_brow_ridge": 128,
      ...
    },
    "body": {
      "head_size": 128,
      "chest_size": 128,
      ...
    },
    "colors": {
      "skin": {"r": 200, "g": 180, "b": 160, "luster": 128},
      "hair": {"r": 50, "g": 40, "b": 30, "luster": 128, "root_darkness": 0, "white_hairs": 0},
      ...
    },
    "advanced": {
      "unk0x45": "0x80",
      "unk0x4a": "0x00",
      ...
    }
  }
  ```
- **Requirements**:
  - Parse all FaceData fields
  - Serialize to JSON with readable names
  - Include advanced/unknown fields for completeness

### 3.4 Import Face Preset (Binary)
- **Description**: Apply binary face preset to character
- **Input**: Save path, slot index, .erface file
- **Output**: Modified save
- **Requirements**:
  - Validate .erface file
  - Write FaceData to correct offset in UserDataX
  - Also update ProfileSummary.profiles[i].face_data (0x124 bytes)
  - Recalculate checksums

### 3.5 Import Face Preset (JSON)
- **Description**: Apply JSON face preset to character
- **Input**: Save path, slot index, .json file
- **Output**: Modified save
- **Requirements**:
  - Parse JSON
  - Validate all fields
  - Convert to binary FaceData format
  - Write to UserDataX and ProfileSummary
  - Recalculate checksums

### 3.6 Copy Face Between Characters
- **Description**: Copy appearance from one slot to another
- **Input**: Save path, source slot, target slot
- **Output**: Modified save
- **Requirements**:
  - Read source FaceData
  - Write to target FaceData offset
  - Update target ProfileSummary face_data
  - Recalculate target checksum

### 3.7 In-Game Preset Slot Management
- **Description**: Manage the 15 face preset slots stored in save
- **Input**: Save path
- **Output**: List of stored presets / modified save
- **Data Source**: `USER_DATA_10.MenuSystemSaveLoad.Preset[15]` (0x130 bytes each)
- **Operations**:
  - List all 15 preset slots (show which are empty/used)
  - Export preset slot to file
  - Import file to preset slot
  - Copy character face to preset slot
  - Apply preset slot to character
  - Clear preset slot

---

## 4. STATS EDITOR

### Display Modes
- **Standard Mode**: Shows documented fields with friendly names
- **Advanced Mode**: Shows ALL fields including unknown bytes, internal values, padding

### 4.1 View Stats
- **Description**: Display all character statistics
- **Input**: Save path, slot index
- **Output**: Formatted stats display
- **Data Source**: `UserDataX.player_game_data` (PlayerGameData struct, 0x1B0 bytes)
- **Standard Fields**:
  - HP: current, max, base_max
  - FP: current, max, base_max
  - Stamina: current, max, base_max
  - Attributes: vigor, mind, endurance, strength, dexterity, intelligence, faith, arcane
  - Level
  - Runes (current)
  - Runes memory (total acquired)
  - Status buildups: poison, rot, bleed, death, frost, sleep, madness
  - Character name, gender, archetype, voice type, gift
  - Flask counts
  - Online settings (passwords, cipher rings, etc.)
- **Advanced Fields** (shown in Advanced Mode):
  - unk0x0, unk0x4, unk0x20, unk0x30 (internal HP/FP/SP values)
  - unk0x54, unk0x58, unk0x5c (post-attribute unknowns)
  - unk0x6c (post-runes unknown)
  - unk0x8c, unk0x90 (post-buildup unknowns)
  - unk0xb8, unk0xb9, unk0xbc, unk0xbd (character creation unknowns)
  - unk0xc0[0x18] (24-byte unknown block)
  - unk0xd9, unk0xdd[0x1A], unk0xf8 (online setting unknowns)
  - unk0xfb[0x15] (post-flask unknowns)
  - unk0x17c[0x34] (trailing padding)

### 4.2 Edit Level
- **Description**: Change character level
- **Input**: Save path, slot index, new level (1-713)
- **Output**: Modified save
- **Data Location**: `PlayerGameData.level` (offset 0x60 in struct)
- **Requirements**:
  - Validate level range
  - Write uint32 at correct offset
  - Also update `ProfileSummary.profiles[i].level`
  - Recalculate checksums

### 4.3 Edit Attributes
- **Description**: Change individual stat
- **Input**: Save path, slot index, stat name, new value (1-99)
- **Output**: Modified save
- **Data Locations** (offsets in PlayerGameData):
  - vigor: 0x34
  - mind: 0x38
  - endurance: 0x3C
  - strength: 0x40
  - dexterity: 0x44
  - intelligence: 0x48
  - faith: 0x4C
  - arcane: 0x50
- **Requirements**:
  - Validate stat range (1-99)
  - Write uint32
  - Optionally recalculate level from stats
  - Recalculate checksums

### 4.4 Edit Runes
- **Description**: Set current runes held
- **Input**: Save path, slot index, amount
- **Output**: Modified save
- **Data Location**: `PlayerGameData.runes` (offset 0x64)
- **Requirements**:
  - Write uint32
  - Recalculate checksum

### 4.5 Edit Runes Memory
- **Description**: Set total runes ever acquired
- **Input**: Save path, slot index, amount
- **Output**: Modified save
- **Data Location**: `PlayerGameData.runes_memory` (offset 0x68)
- **Requirements**:
  - Write uint32
  - Also update `ProfileSummary.profiles[i].runes_memory`
  - Recalculate checksums

### 4.6 Clear Status Buildups
- **Description**: Reset all status effect buildups to 0
- **Input**: Save path, slot index
- **Output**: Modified save
- **Data Locations** (offsets in PlayerGameData):
  - poison_buildup: 0x70
  - rot_buildup: 0x74
  - bleed_buildup: 0x78
  - death_buildup: 0x7C
  - frost_buildup: 0x80
  - sleep_buildup: 0x84
  - madness_buildup: 0x88
- **Requirements**:
  - Write 0 to each uint32
  - Recalculate checksum

### 4.7 Edit Flask Counts
- **Description**: Set HP/FP flask allocation
- **Input**: Save path, slot index, crimson count, cerulean count
- **Output**: Modified save
- **Data Locations**:
  - max_crimson_flask_count: PlayerGameData offset 0xF9 (uint8)
  - max_cerulean_flask_count: PlayerGameData offset 0xFA (uint8)
- **Requirements**:
  - Validate total doesn't exceed max (14)
  - Write uint8 values
  - Recalculate checksum

### 4.8 Edit Character Name
- **Description**: Rename character
- **Input**: Save path, slot index, new name (max 16 chars)
- **Output**: Modified save
- **Data Locations**:
  - `PlayerGameData.character_name` (UTF-16LE, 32 bytes)
  - `ProfileSummary.profiles[i].character_name` (UTF-16LE, 32 bytes)
- **Requirements**:
  - Validate name length
  - Encode as UTF-16LE
  - Pad with nulls to 32 bytes
  - Write to both locations
  - Recalculate checksums

### 4.9 Calculate Level from Stats
- **Description**: Compute what level should be based on attributes
- **Input**: All 8 attributes
- **Output**: Calculated level
- **Formula**: 
  ```
  level = (vigor - base) + (mind - base) + ... for all stats
  base values depend on starting class
  ```
- **Requirements**:
  - Know starting class base stats
  - Sum all stat increases

---

## 5. INVENTORY EDITOR

### 5.1 View Inventory
- **Description**: List all items in held inventory or storage
- **Input**: Save path, slot index, inventory type (held/storage)
- **Output**: Item list with IDs, names, quantities
- **Data Sources**:
  - Held: `UserDataX.inventory_held` (0xA80 entries, 0x180 key items)
  - Storage: `UserDataX.inventory_storage_box` (0x780 entries, 0x80 key items)
  - Item resolution: `UserDataX.gaitem_map` (5120 entries)
- **Requirements**:
  - Parse Inventory structure
  - Resolve gaitem_handle to item_id via gaitem_map
  - Look up item names in database

### 5.2 Add Item
- **Description**: Add item to inventory
- **Input**: Save path, slot index, item_id, quantity
- **Output**: Modified save
- **Requirements**:
  - Find empty inventory slot
  - Generate new gaitem_handle
  - Add entry to gaitem_map
  - Add entry to inventory
  - Update inventory count
  - Handle item type variations (weapons need extra data)
  - Recalculate checksum

### 5.3 Remove Item
- **Description**: Delete item from inventory
- **Input**: Save path, slot index, gaitem_handle or inventory index
- **Output**: Modified save
- **Requirements**:
  - Find item in inventory
  - Clear inventory slot
  - Clear gaitem_map entry
  - Update inventory count
  - Recalculate checksum

### 5.4 Edit Item Quantity
- **Description**: Change stack size of item
- **Input**: Save path, slot index, gaitem_handle, new quantity
- **Output**: Modified save
- **Requirements**:
  - Find item in inventory
  - Update quantity field
  - Validate max stack size
  - Recalculate checksum

### 5.5 Move Item to Storage
- **Description**: Transfer item from held to storage box
- **Input**: Save path, slot index, gaitem_handle
- **Output**: Modified save
- **Requirements**:
  - Remove from held inventory
  - Add to storage inventory
  - Recalculate checksum

### 5.6 Bulk Add Items
- **Description**: Add all items in a category
- **Input**: Save path, slot index, category (weapons/armor/spells/etc)
- **Output**: Modified save
- **Requirements**:
  - Item database by category
  - Loop add for each item
  - Handle inventory space limits

### 5.7 View Equipped Items
- **Description**: Show what's currently equipped
- **Input**: Save path, slot index
- **Output**: Equipment layout
- **Data Sources**:
  - `UserDataX.equipped_items_equip_index`: slot assignments
  - `UserDataX.equipped_items_item_ids`: item IDs per slot
  - `UserDataX.equipped_items_gaitem_handles`: handles per slot
  - `UserDataX.equipped_armaments_and_items`: weapons/armor
  - `UserDataX.equipped_spells`: spell slots
- **Requirements**:
  - Parse each equipment structure
  - Resolve IDs to names

### 5.8 Equip Item
- **Description**: Put item in equipment slot
- **Input**: Save path, slot index, slot type, slot index, gaitem_handle
- **Output**: Modified save
- **Requirements**:
  - Validate item can go in slot type
  - Update equipped_items_equip_index
  - Update equipped_items_gaitem_handles
  - Recalculate checksum

---

## 6. WORLD STATE EDITOR

### 6.1 View Location
- **Description**: Show current map and coordinates
- **Input**: Save path, slot index
- **Output**: Map name, X/Y/Z coordinates
- **Data Sources**:
  - `UserDataX.map_id`: 4 bytes [AA, BB, CC, DD]
  - `UserDataX.player_coordinates`: X, Y, Z floats + rotation
- **Requirements**:
  - Parse MapId
  - Map to human-readable name (database)
  - Parse coordinates

### 6.2 Teleport to Location
- **Description**: Move character to specified location
- **Input**: Save path, slot index, target location (preset or coordinates)
- **Output**: Modified save
- **Data to Modify**:
  - `UserDataX.map_id` (offset 0x4 from slot start)
  - `UserDataX.player_coordinates.position` (X, Y, Z floats)
  - `UserDataX.player_coordinates.angle` (optional)
- **Requirements**:
  - Location database with map_id + coordinates
  - Write MapId bytes
  - Write coordinate floats
  - Recalculate checksum

### 6.3 View/Edit Weather
- **Description**: Check or change weather state
- **Input**: Save path, slot index
- **Output**: Current weather or modified save
- **Data Source**: `UserDataX.world_area_weather`
  - area_id: uint16
  - weather_type: uint16 (enum)
  - timer: uint32
- **Requirements**:
  - Parse WorldAreaWeather
  - Weather type enum mapping

### 6.4 View/Edit Time
- **Description**: Check or change in-game time
- **Input**: Save path, slot index
- **Output**: Current time (HH:MM:SS) or modified save
- **Data Source**: `UserDataX.world_area_time`
  - hour: uint32
  - minute: uint32
  - second: uint32
- **Requirements**:
  - Parse WorldAreaTime
  - Validate time values (0-23, 0-59, 0-59)

### 6.5 View/Edit Torrent
- **Description**: Check or fix horse state
- **Input**: Save path, slot index
- **Output**: Horse status or modified save
- **Data Source**: `UserDataX.horse` (RideGameData)
  - hp: uint32
  - max_hp: uint32
  - state: enum (Alive, Dead, Active)
  - map_id: bytes
- **Requirements**:
  - Parse RideGameData
  - Fix logic: if hp=0 and state=Active, set state=Alive and hp=max_hp

### 6.6 Edit Last Rested Grace
- **Description**: Change respawn point
- **Input**: Save path, slot index, grace entity ID
- **Output**: Modified save
- **Data Location**: `UserDataX.last_rested_grace` (uint32)
- **Requirements**:
  - Grace ID database
  - Write uint32
  - Recalculate checksum

---

## 7. EVENT FLAGS EDITOR

### Display Modes
- **Standard Mode**: Shows only documented/named flags organized by category
- **Advanced Mode**: Browse ALL 1,833,375 flags including undocumented ones by ID range

### 7.1 Get Flag
- **Description**: Read single event flag state
- **Input**: Save path, slot index, flag ID
- **Output**: True/False + flag name (if documented)
- **Data Source**: `UserDataX.event_flags` (~1.8MB, 1,833,375 flags)
- **Requirements**:
  - Load BST mapping (eventflag_bst.txt)
  - Calculate: block = flag_id // 8000
  - Look up block offset in BST
  - Calculate byte and bit position
  - Read bit
  - Look up flag name in database (if exists)

### 7.2 Set Flag
- **Description**: Set single event flag state
- **Input**: Save path, slot index, flag ID, state (true/false)
- **Output**: Modified save
- **Requirements**:
  - Same calculation as Get Flag
  - Write bit (set or clear)
  - Recalculate checksum

### 7.3 Browse Flags (Standard Mode)
- **Description**: Browse documented flags by category
- **Input**: Save path, slot index, category filter
- **Output**: Flag list with names, IDs, current states
- **Categories**:
  - Bosses (main game)
  - Bosses (DLC)
  - Sites of Grace (by region)
  - NPC Interactions
  - Quest Progress (by NPC)
  - Item Pickups
  - Map Unlocks
  - Achievements/Trophies
  - Multiplayer
  - Tutorial Flags
- **Requirements**:
  - Event flag database with categories
  - Batch read flags in category

### 7.4 Browse Flags (Advanced Mode)
- **Description**: Browse ALL flags by ID range
- **Input**: Save path, slot index, start ID, end ID (or block number)
- **Output**: Raw flag states for range
- **Features**:
  - View by block (8000 flags per block)
  - Jump to specific ID
  - Search for patterns (find all ON flags in range)
  - Show documented name if known, otherwise show "Unknown (ID)"
  - Bulk toggle for ranges
- **Requirements**:
  - Efficient range reading
  - Pagination for large ranges

### 7.5 Get Flags Batch
- **Description**: Read multiple flags at once
- **Input**: Save path, slot index, list of flag IDs
- **Output**: Dict of flag_id -> state
- **Requirements**:
  - Loop Get Flag
  - Optimize: cache BST lookup

### 7.6 Set Flags Batch
- **Description**: Set multiple flags at once
- **Input**: Save path, slot index, dict of flag_id -> state
- **Output**: Modified save
- **Requirements**:
  - Loop Set Flag
  - Single checksum recalc at end

### 7.5 List Boss Flags
- **Description**: Show all boss defeat states
- **Input**: Save path, slot index
- **Output**: Boss list with defeated status
- **Requirements**:
  - Boss flag ID database
  - Batch get flags

### 7.6 Toggle Boss Defeat
- **Description**: Mark boss as defeated or alive
- **Input**: Save path, slot index, boss name/ID, state
- **Output**: Modified save
- **Requirements**:
  - Look up boss flag ID
  - Set flag

### 7.7 List Grace Flags
- **Description**: Show all Site of Grace discovery states
- **Input**: Save path, slot index
- **Output**: Grace list with discovered status
- **Requirements**:
  - Grace flag ID database (discovered + rested flags)
  - Batch get flags

### 7.8 Unlock Grace
- **Description**: Discover a Site of Grace
- **Input**: Save path, slot index, grace name/ID
- **Output**: Modified save
- **Requirements**:
  - Look up grace flag IDs
  - Set discovery flag
  - Optionally set rested flag

### 7.9 Unlock All Graces
- **Description**: Discover all Sites of Grace
- **Input**: Save path, slot index, optional region filter
- **Output**: Modified save
- **Requirements**:
  - Grace database with regions
  - Batch set flags

### 7.10 View Quest State
- **Description**: Show NPC questline progress
- **Input**: Save path, slot index, NPC name
- **Output**: Current quest stage and description
- **Requirements**:
  - Quest flag database (per NPC, per stage)
  - Read relevant flags
  - Determine current stage

### 7.11 Set Quest Stage
- **Description**: Advance or regress questline
- **Input**: Save path, slot index, NPC name, stage
- **Output**: Modified save
- **Requirements**:
  - Quest flag database
  - Set flags for target stage
  - Clear flags for later stages (if regressing)

### 7.12 Export Flags
- **Description**: Save all flag states to file
- **Input**: Save path, slot index
- **Output**: Flags file (compressed bitfield or sparse list)
- **Requirements**:
  - Read all event_flags bytes
  - Write to file

### 7.13 Import Flags
- **Description**: Load flag states from file
- **Input**: Save path, slot index, flags file
- **Output**: Modified save
- **Requirements**:
  - Read flags file
  - Write to event_flags
  - Recalculate checksum

---

## 8. STEAMID PATCHER

### 8.1 View SteamIDs
- **Description**: Show SteamID at save level and per character
- **Input**: Save path
- **Output**: Save SteamID + each character's SteamID + clickable Steam profile links
- **Data Sources**:
  - Save level: `USER_DATA_10.steam_id` (offset 0x4 in USER_DATA_10)
  - Per character: `UserDataX.steam_id` (near end of slot)
- **Requirements**:
  - Parse USER_DATA_10
  - Parse each UserDataX
  - Format as clickable URL: `https://steamcommunity.com/profiles/{steam_id}`

### 8.2 Detect Mismatches
- **Description**: Find characters with wrong SteamID
- **Input**: Save path
- **Output**: List of mismatched slots with details
- **Requirements**:
  - Compare each character SteamID to save SteamID

### 8.3 Sync All SteamIDs
- **Description**: Set all character SteamIDs to match save
- **Input**: Save path
- **Output**: Modified save
- **Requirements**:
  - Get save SteamID from USER_DATA_10
  - Write to each active character's steam_id field
  - Recalculate all checksums

### 8.4 Set Custom SteamID
- **Description**: Change SteamID (for account transfer)
- **Input**: Save path, new SteamID via:
  - Direct uint64 input
  - Steam profile URL paste (extracts ID automatically)
  - Steam vanity URL paste (resolves via Steam API or scraping)
- **Output**: Modified save
- **URL Parsing**:
  ```
  Supported formats:
  - https://steamcommunity.com/profiles/76561199122397217
  - https://steamcommunity.com/id/customname
  - steamcommunity.com/profiles/76561199122397217
  - 76561199122397217 (raw ID)
  ```
- **Requirements**:
  - URL regex parsing
  - Extract SteamID64 from /profiles/ URL
  - For /id/ vanity URLs: resolve via Steam Web API or page scrape
  - Validate SteamID64 format (17 digits, starts with 7656)
  - Write new SteamID to USER_DATA_10.steam_id
  - Write to all active characters
  - Recalculate all checksums

### 8.5 Patch Single Character
- **Description**: Fix SteamID for one slot only
- **Input**: Save path, slot index, SteamID (or use save's)
- **Output**: Modified save
- **Requirements**:
  - Write SteamID to UserDataX.steam_id
  - Recalculate slot checksum

---

## GLOBAL SAFETY SYSTEM

### Mandatory Pre-Write Backup
- **Every** write operation creates timestamped backup first
- Backup naming: `{save_name}_{YYYY-MM-DD_HH-MM-SS}_before_{operation}.bak`
- Cannot be disabled (safety critical)
- Stored in dedicated backup folder

### Warning System
All warnings have "Don't show again" checkbox (stored in config)

#### DLC Location Warning
- **Trigger**: Teleporting to any DLC map location
- **Message**: "Warning: You are about to teleport to a Shadow of the Erdtree DLC location. If you do not own the DLC, this will cause an infinite loading screen. Continue?"
- **Options**: [Cancel] [Continue Anyway]
- **Checkbox**: "Don't warn me again for DLC locations"

#### Destructive Operation Warnings
- **Trigger**: Delete character, clear inventory, reset flags, bulk operations
- **Message**: Specific to operation, explains what will be lost
- **Options**: [Cancel] [Confirm]

#### Unusual Value Warnings
- **Trigger**: Setting stats outside normal ranges
- **Examples**:
  - Level > 713: "Level exceeds maximum possible (713)"
  - Stat > 99: "Attribute exceeds maximum (99)"
  - Negative values: "Negative values may corrupt save"
  - Runes > 999,999,999: "Rune count exceeds reasonable maximum"
- **Options**: [Cancel] [Apply Anyway]

#### Invalid Item Warnings
- **Trigger**: Adding item ID not in database
- **Message**: "Item ID {id} not recognized. This may be invalid or from a different game version."
- **Options**: [Cancel] [Add Anyway]

#### Checksum Override Warning
- **Trigger**: Hex edit that would invalidate checksum
- **Message**: "This edit will modify checksummed data. Checksum will be recalculated automatically."
- **Info only**: [OK]

### Warning Configuration
```
warnings:
  dlc_teleport: true
  destructive_operations: true
  unusual_values: true
  invalid_items: true
  show_checksum_info: true
```

---

## 9. CORRUPTION FIXES

### 9.1 Detect All Corruption
- **Description**: Scan save for all known issues
- **Input**: Save path
- **Output**: List of issues per slot
- **Checks**:
  - Torrent bug: horse.hp == 0 and horse.state == Active
  - SteamID mismatch: character.steam_id != save.steam_id
  - Weather sync: weather.area_id != map_id[3]
  - Time sync: time.hour == 0 and time.minute == 0 and time.second == 0
  - Ranni soft-lock: specific flag combination
  - Warp sickness: specific flag combinations (5 variants)
  - DLC trap: map_id indicates DLC area
  - Checksum mismatch: calculated != stored

### 9.2 Fix Torrent Bug
- **Description**: Repair horse state
- **Input**: Save path, slot index
- **Output**: Modified save
- **Fix**: Set horse.state = Alive, horse.hp = horse.max_hp
- **Requirements**:
  - Write to horse data offset
  - Recalculate checksum

### 9.3 Fix SteamID Mismatch
- **Description**: Sync character SteamID to save
- **Input**: Save path, slot index
- **Output**: Modified save
- **Fix**: Copy USER_DATA_10.steam_id to UserDataX.steam_id
- **Requirements**:
  - Read save SteamID
  - Write to character
  - Recalculate checksum

### 9.4 Fix Weather Sync
- **Description**: Correct weather area ID
- **Input**: Save path, slot index
- **Output**: Modified save
- **Fix**: Set weather.area_id = map_id[3]
- **Requirements**:
  - Read current map_id
  - Write area_id
  - Recalculate checksum

### 9.5 Fix Time Sync
- **Description**: Calculate time from playtime
- **Input**: Save path, slot index
- **Output**: Modified save
- **Fix**: 
  ```
  seconds = ProfileSummary.profiles[i].seconds_played
  hours = (seconds // 3600) % 24
  minutes = (seconds % 3600) // 60
  secs = seconds % 60
  ```
- **Requirements**:
  - Read seconds_played from ProfileSummary
  - Calculate H:M:S
  - Write to WorldAreaTime
  - Recalculate checksum

### 9.6 Fix Ranni Soft-lock
- **Description**: Clear blocking flags, enable progression flags
- **Input**: Save path, slot index
- **Output**: Modified save
- **Fix**: 
  - Set flag 1034500738 = OFF
  - Set 31 progression flags = ON
- **Requirements**:
  - Event flag set operations
  - Recalculate checksum

### 9.7 Fix Warp Sickness (5 variants)
- **Description**: Clear stuck warp states
- **Input**: Save path, slot index
- **Output**: Modified save
- **Variants and Fixes**:
  - Radahn Alive: Clear crater, remove marker
  - Radahn Dead: Clear marker, enable grace
  - Morgott: Clear throne room state
  - Radagon: Clear ending state
  - Sealing Tree: Clear DLC progression block
- **Requirements**:
  - Specific flag sets per variant
  - Recalculate checksum

### 9.8 Fix DLC Trap
- **Description**: Teleport out of DLC area
- **Input**: Save path, slot index, target location
- **Output**: Modified save
- **Fix**: Change map_id and coordinates to safe location
- **Requirements**:
  - Detect DLC map_id
  - Teleport operation

### 9.9 Repair Checksum
- **Description**: Recalculate and fix checksums
- **Input**: Save path
- **Output**: Modified save
- **Fix**: 
  ```
  for each active slot:
    checksum = MD5(slot_data[0x10:0x280010])
    write checksum to slot_data[0:0x10]
  user_data_10_checksum = MD5(user_data_10[0x10:0x60010])
  write to user_data_10[0:0x10]
  ```
- **Requirements**:
  - MD5 calculation
  - Write checksums

### 9.10 Fix All
- **Description**: Apply all applicable fixes
- **Input**: Save path, slot index (or all)
- **Output**: Modified save with all fixes applied
- **Requirements**:
  - Run detection
  - Apply each fix
  - Single checksum recalc at end

---

## 10. ONLINE SETTINGS

### 10.1 View Online Settings
- **Description**: Display multiplayer configuration
- **Input**: Save path, slot index
- **Output**: All online settings
- **Data Source**: `PlayerGameData` fields:
  - password (offset 0x110, 8 wide chars)
  - group_password1-5 (subsequent offsets)
  - furl_calling_finger_on (0xD8)
  - white_cipher_ring_on (0xDB)
  - blue_cipher_ring_on (0xDC)
  - great_rune_on (0xF7)
  - matchmaking_weapon_level (0xDA)

### 10.2 Edit Password
- **Description**: Set multiplayer password
- **Input**: Save path, slot index, password (max 8 chars)
- **Output**: Modified save
- **Requirements**:
  - Encode as UTF-16LE
  - Write to password field
  - Recalculate checksum

### 10.3 Edit Group Passwords
- **Description**: Set group passwords (1-5)
- **Input**: Save path, slot index, slot 1-5, password
- **Output**: Modified save
- **Requirements**:
  - Same as 10.2 for each slot

### 10.4 Toggle Online Flags
- **Description**: Enable/disable online features
- **Input**: Save path, slot index, flag name, state
- **Output**: Modified save
- **Requirements**:
  - Write boolean to appropriate offset
  - Recalculate checksum

---

## 11. GESTURES AND REGIONS

### 11.1 View Unlocked Gestures
- **Description**: List all gestures with unlock status
- **Input**: Save path, slot index
- **Output**: Gesture list
- **Data Source**: `UserDataX.gestures` (64 uint32 IDs)
- **Requirements**:
  - Gesture ID database

### 11.2 Unlock Gesture
- **Description**: Add gesture to character
- **Input**: Save path, slot index, gesture ID
- **Output**: Modified save
- **Requirements**:
  - Find empty slot in gestures array
  - Write gesture ID
  - Recalculate checksum

### 11.3 View Unlocked Regions
- **Description**: List discovered map regions
- **Input**: Save path, slot index
- **Output**: Region list
- **Data Source**: `UserDataX.unlocked_regions`
- **Requirements**:
  - Region ID database

### 11.4 Unlock Region
- **Description**: Discover map region
- **Input**: Save path, slot index, region ID
- **Output**: Modified save
- **Requirements**:
  - Add region to unlocked_regions
  - Recalculate checksum

---

## 12. UTILITIES

### 12.1 Validate Save
- **Description**: Check save file integrity
- **Input**: Save path
- **Output**: Validation report
- **Checks**:
  - Magic bytes (BND4)
  - Header size (0x2FC for PC, 0x6C for PS)
  - All checksums valid
  - Structure parseable
  - No obvious corruption

### 12.2 Compare Saves
- **Description**: Diff two save files
- **Input**: Save path 1, save path 2
- **Output**: Detailed diff report
- **Requirements**:
  - Parse both saves
  - Compare all fields
  - Format differences

### 12.3 Hex Editor (Full Featured)
- **Description**: Complete hex editor similar to 010 Editor
- **Input**: Save file path
- **Output**: Interactive hex editing interface

#### Core Features
- **Hex View**: 
  - Configurable bytes per row (8, 16, 32)
  - Address column (file offset)
  - Hex bytes with spacing
  - ASCII/Unicode text column
  - Alternating row colors
  - Current position indicator

- **Navigation**:
  - Scroll through entire file
  - Go to offset (decimal or hex)
  - Go to structure (jump to UserDataX[3], PlayerGameData, etc.)
  - Bookmarks (save/load positions with names)
  - History (back/forward navigation)

- **Selection**:
  - Click to select byte
  - Shift+click for range
  - Ctrl+click for multiple selections
  - Select all
  - Select structure (auto-select known structure boundaries)

- **Search**:
  - Find hex bytes (e.g., "FF 00 FF")
  - Find text (ASCII or UTF-16)
  - Find integer value (any endianness)
  - Find float value
  - Find all occurrences
  - Replace (with confirmation)
  - Regular expression search

- **Editing**:
  - Overwrite mode (default)
  - Type hex directly
  - Type ASCII in text column
  - Paste hex string
  - Fill selection with value
  - Undo/redo (unlimited)

- **Data Inspector** (side panel):
  - Show current selection interpreted as:
    - int8, uint8
    - int16, uint16 (LE/BE)
    - int32, uint32 (LE/BE)
    - int64, uint64 (LE/BE)
    - float32, float64 (LE/BE)
    - ASCII string
    - UTF-16LE string
    - Binary bits
    - Unix timestamp
  - Edit value in inspector (writes back to hex)

- **Structure Overlay**:
  - Color-code known structures
  - Show structure boundaries
  - Hover for structure/field name
  - Click to expand structure details
  - Based on save file template (like 010's .bt files)
  - Structures defined:
    - BND4 Header
    - Character Slots (10x)
    - Checksums
    - PlayerGameData
    - FaceData
    - Inventory
    - Event Flags
    - All parsed structures from parser

- **Comparison**:
  - Compare with another file
  - Highlight differences
  - Sync scroll between files
  - Jump to next/previous difference

- **Checksum Integration**:
  - Show checksum regions
  - Indicate if checksum valid/invalid
  - Auto-recalculate on save
  - Option to save without recalculating (for debugging)

- **Export/Import**:
  - Export selection as raw bytes
  - Export selection as hex string
  - Export selection as C array
  - Import and overwrite at offset

- **Keyboard Shortcuts**:
  - Ctrl+G: Go to offset
  - Ctrl+F: Find
  - Ctrl+H: Replace
  - Ctrl+Z/Y: Undo/Redo
  - Ctrl+B: Add bookmark
  - F3: Find next
  - Tab: Switch hex/text focus

---

## 13. DATA REQUIREMENTS

### 13.1 Item Database
- All item IDs with names
- Categories (weapon, armor, consumable, etc.)
- Subcategories (swords, greatswords, etc.)
- Max stack sizes
- Source: Game params or community databases

### 13.2 Event Flag Database
- Known flag IDs with descriptions
- Categories (boss, grace, quest, etc.)
- Quest stage mappings
- Source: Community research, Cheat Engine scripts

### 13.3 Location Database
- Map ID to name mapping
- Grace entity IDs
- Safe teleport coordinates
- Region groupings

### 13.4 Quest Database
- NPC questlines
- Stage definitions
- Required flags per stage
- Branching paths

### 13.5 BST Mapping
- Event flag block -> offset mapping
- From eventflag_bst.txt (already have)

---

## 14. FILE FORMAT SUMMARY

### Save File Structure (.sl2/.co2)
```
0x000: Magic "BND4" (4 bytes)
0x004: Header (0x2FC bytes PC, 0x6C bytes PS)
0x300: Character Slot 0 (0x280010 bytes = 0x10 checksum + 0x280000 data)
  ...repeat for slots 1-9...
0x19003A0: USER_DATA_10 (0x60010 bytes = 0x10 checksum + 0x60000 data)
0x1F003B0: USER_DATA_11 (regulation data)
```

### Character Slot Structure (UserDataX)
```
0x00: Version (uint32)
0x04: MapId (4 bytes)
0x08: Unknown (24 bytes)
0x20: GaitemMap (variable, ~5120 entries)
... : PlayerGameData (0x1B0 bytes)
... : SPEffects (13 * 0x10 bytes)
... : Equipment structures
... : Inventory (held)
... : FaceData (0x12F bytes)
... : Inventory (storage)
... : Gestures, Regions
... : Horse (RideGameData)
... : Event Flags (~1.8MB)
... : World state structures
... : SteamId (uint64)
... : DLC data
... : Hash data
```

### Checksum Calculation
```
MD5(slot_data[0x10:0x280010]) -> slot_data[0x00:0x10]
```

---

## 15. SOURCE REFERENCES

### From ER-Save-Lib (Rust)
Primary reference implementation for save file structure:
- `save.rs`: Save file container, platform detection, checksum handling
- `user_data_x.rs`: Character slot structure (UserDataX)
- `user_data_10.rs`: Common data, SteamID, ProfileSummary
- `user_data_11.rs`: Regulation data
- `save_api.rs`: High-level API for character copy, profile management

### From Save File Fixer Repository
Existing fix implementations to integrate:
- **Torrent Bug Fix**: `RideGameData` HP/state correction
- **SteamID Sync**: Copy from USER_DATA_10 to character slots
- **Weather Sync**: AreaID from MapId[3]
- **Time Sync**: Calculate from ProfileSummary.seconds_played
- **Ranni Soft-lock Fix**: Event flag manipulation (flag 1034500738 + 31 progression flags)
- **Warp Sickness Fixes**: 5 variants (Radahn alive/dead, Morgott, Radagon, Sealing Tree)
- **DLC Detection**: MapId check for Shadow of the Erdtree areas
- **Checksum Recalculation**: MD5 per slot + USER_DATA_10

### From 010 Editor Template (SL2.bt)
Binary structure definitions:
- All struct layouts with exact offsets
- Field types and sizes
- Enum definitions (WeatherType, HorseState, CharacterType, etc.)
- Variable-length structure handling (Gaitem, Inventory)
- Assertions for data validation

### From Cheat Engine Scripts
Event flag research:
- `EventFlag_code.cea`: Flag access via BST tree traversal
- `Ranni_s_Tower_Fix.cea`: Ranni quest flag IDs and fix logic
- Event flag divisor (8000)
- Block descriptor structure
- BST node structure for flag lookup

### From Community Research
- `eventflag_bst.txt`: Block ID to offset mapping (151K entries)
- `event_flags_er.txt`: Known flag IDs with descriptions
- Item ID databases
- Boss/Grace flag mappings
- Quest stage definitions

### Parser Expansion Needed
Areas where current parser needs extension:
1. **Gaitem Resolution**: Full item_id lookup from gaitem_handle
2. **Inventory Modification**: Add/remove items with proper handle allocation
3. **Write-back System**: Track all offsets for field-level writes
4. **USER_DATA_11**: Regulation data parsing (low priority)
5. **PS Format**: PlayStation-specific differences
6. **Version Handling**: Older save versions (pre-DLC, version <= 81)

---

## 16. IMPLEMENTATION NOTES

### Offset Tracking
Every parsed structure must track its file offset for write-back:
```python
@dataclass
class TrackedField:
    value: Any
    offset: int      # Absolute file offset
    size: int        # Field size in bytes
    dirty: bool = False  # Modified since load
```

### Checksum Regions
```
Slot 0:  0x300      - 0x28030F   (checksum at 0x300)
Slot 1:  0x280310   - 0x50031F   (checksum at 0x280310)
...
Slot 9:  0x1680390  - 0x190039F  (checksum at 0x1680390)
UD10:    0x19003A0  - 0x1F003AF  (checksum at 0x19003A0)
```

### Event Flag Calculation
```python
def get_flag_position(flag_id: int, bst_map: dict) -> tuple[int, int]:
    """Returns (byte_offset, bit_index) within event_flags block"""
    divisor = 8000
    block = flag_id // divisor
    index = flag_id - block * divisor
    
    if block not in bst_map:
        raise ValueError(f"Block {block} not in BST")
    
    block_offset = bst_map[block] * 8  # 8 bytes per block unit
    byte_index = index // 8
    bit_index = 7 - (index % 8)  # Big endian bit order
    
    return (block_offset + byte_index, bit_index)
```

### Platform Detection
```python
def detect_platform(data: bytes) -> str:
    """Detect save file platform from header size"""
    # Magic is always "BND4" at offset 0
    # Header size determines platform
    if len(data) < 0x300:
        return "unknown"
    
    # Check header size indicator or file structure
    # PC: header = 0x2FC bytes, slot size = 0x280010
    # PS: header = 0x6C bytes, slot size = 0x280000
    
    # Simple check: PC files have checksum per slot, PS don't
    pc_slot_start = 0x300
    ps_slot_start = 0x70
    
    # ... detection logic