# Save File Structure

Complete technical documentation of Elden Ring save file format (.sl2 / .co2).

---

## Overview

**File Size:** ~26 MB (26,214,400 bytes for PC)

**Encoding:** Binary format with BND4 container (PC)

**Checksum:** MD5 per section (PC only, PlayStation has no checksums)

---

## PC Save File Layout (.sl2)

### Complete Structure

```
┌─────────────────────────────────────────────────────────┐
│ Offset      Size        Section                         │
├─────────────────────────────────────────────────────────┤
│ 0x000       4 bytes     Magic "BND4"                    │
│ 0x004       0x2FC       Header                          │
├─────────────────────────────────────────────────────────┤
│ 0x300       0x280010    Character Slot 0                │
│                         ├─ 0x10: MD5 Checksum           │
│                         └─ 0x280000: Character Data     │
├─────────────────────────────────────────────────────────┤
│ 0x280310    0x280010    Character Slot 1                │
│ 0x500320    0x280010    Character Slot 2                │
│ 0x780330    0x280010    Character Slot 3                │
│ 0xA00340    0x280010    Character Slot 4                │
│ 0xC80350    0x280010    Character Slot 5                │
│ 0xF00360    0x280010    Character Slot 6                │
│ 0x1180370   0x280010    Character Slot 7                │
│ 0x1400380   0x280010    Character Slot 8                │
│ 0x1680390   0x280010    Character Slot 9                │
├─────────────────────────────────────────────────────────┤
│ 0x19003A0   0x60010     USER_DATA_10                    │
│                         ├─ 0x10: MD5 Checksum           │
│                         ├─ SteamID (uint64)             │
│                         ├─ ProfileSummary (10 slots)    │
│                         └─ Active slot flags            │
├─────────────────────────────────────────────────────────┤
│ 0x1F003B0   0x240010    USER_DATA_11 (Regulation)       │
│                         ├─ 0x10: MD5 Checksum           │
│                         └─ Game regulation data         │
└─────────────────────────────────────────────────────────┘
```

### Header Structure (0x300 bytes)

```c
struct BND4Header {
    char magic[4];           // "BND4"
    uint32_t unk0x04;
    uint32_t unk0x08;
    uint32_t unk0x0C;
    // ... additional header data
    // Total: 0x300 bytes (PC) or 0x6C bytes (PS)
};
```

**Platform Detection:**
- PC: Header size = 0x2FC (764 bytes)
- PlayStation: Header size = 0x6C (108 bytes)

**Magic Bytes:**
- PC: `BND4` (0x42 0x4E 0x44 0x34)
- PlayStation: `0xCB 0x01 0x9C 0x2C`

---

## Character Slot Structure (UserDataX)

### Slot Layout

Each of 10 character slots follows this structure:

```
┌──────────────────────────────────────────┐
│ PC Format (with checksum):               │
├──────────────────────────────────────────┤
│ 0x00-0x0F   (16 bytes)   MD5 Checksum    │
│ 0x10-0x28000F (2.6MB)    Character Data  │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ PlayStation Format (no checksum):        │
├──────────────────────────────────────────┤
│ 0x00-0x27FFFF (2.6MB)    Character Data  │
└──────────────────────────────────────────┘
```

### Empty Slot Detection

**PC:** Checksum is all zeros (16 bytes of 0x00)
**PlayStation:** First 16 bytes all zeros

### Character Data Structure (0x280000 bytes)

```c
struct UserDataX {
    // Header (32 bytes)
    uint32_t version;              // 0x00: Save version
    uint8_t map_id[4];            // 0x04: Current location
    uint8_t unk0x08[8];           // 0x08: Unknown
    uint8_t unk0x10[16];          // 0x10: Unknown
    
    // Gaitem Map (variable length, ~5120 entries)
    Gaitem gaitem_map[5120];      // 0x20: Item references
    
    // Character Stats (0x1B0 = 432 bytes)
    PlayerGameData player_data;    // Character stats, runes, etc
    
    // SP Effects (208 bytes)
    SPEffect sp_effects[13];       // Active buffs/debuffs
    
    // Equipment (variable)
    EquippedItemsEquipIndex equip_index;
    ActiveWeaponSlots weapon_slots;
    EquippedItemsItemIds item_ids;
    EquippedItemsGaitemHandles item_handles;
    
    // Inventory - Held (0xA80 common, 0x180 key items)
    Inventory inventory_held;
    
    // Appearance (0x12F = 303 bytes)
    FaceData face_data;
    
    // Inventory - Storage (variable)
    Inventory inventory_storage;
    
    // Gestures and Regions
    Gestures gestures;
    Regions regions;
    
    // World State
    RideGameData horse;            // Torrent data
    
    // Event Flags (~1.8MB)
    uint8_t event_flags[~1.8MB];  // Bitfield
    
    // Additional World Data
    WorldArea world_area;
    WorldAreaTime time;
    WorldAreaWeather weather;
    
    // Identity
    uint64_t steam_id;             // Steam account ID
    
    // DLC Data
    DLC dlc;
    
    // Validation
    PlayerGameDataHash hash;
};
```

### Key Offsets (approximate, version-dependent)

```
0x00000000  Version
0x00000004  MapId
0x00000020  GaitemMap start
~0x00005000 PlayerGameData
~0x000051B0 SPEffects
~0x00006000 Equipment structures
~0x0000A000 Inventory (held)
~0x00010000 FaceData
~0x00020000 Inventory (storage)
~0x00030000 Gestures
~0x00032000 Regions
~0x00034000 RideGameData (Torrent)
~0x00040000 Event Flags
~0x001E0000 World state
~0x001E5000 SteamID
~0x001E6000 DLC data
~0x001E8000 Hash
```

**Note:** These are approximate. Parser tracks exact offsets during read.

---

## USER_DATA_10 Structure

### Layout

```c
struct UserData10 {
    // PC: Checksum first
    uint8_t checksum[16];         // 0x00: MD5 (PC only)
    
    // Steam ID
    uint64_t steam_id;            // 0x10: Steam account
    
    // Profile Summary
    ProfileSummary profile_summary;
    
    // Additional metadata
    uint8_t active_slots[10];     // Which slots are used
    
    // ... more metadata
};
```

### ProfileSummary Structure

```c
struct ProfileSummary {
    Profile profiles[10];         // One per character slot
};

struct Profile {
    wchar_t character_name[16];   // 0x00: UTF-16 name
    uint32_t level;               // 0x20: Character level
    uint32_t seconds_played;      // 0x24: Total playtime
    // ... additional fields (0x24C total per profile)
};
```

**Size per profile:** 0x24C (588 bytes)  
**Total for 10 profiles:** 0x16F8 (5,880 bytes)

### Active Slots Array

```c
uint8_t active_slots[10];  // 1 = slot in use, 0 = empty
```

**Location:** Near end of USER_DATA_10

---

## USER_DATA_11 Structure

**Purpose:** Game regulation data (item stats, scaling, etc.)

**Size:** 0x240000 (2,359,296 bytes) + 0x10 checksum

**Format:** Binary regulation blob

**Checksum:** MD5 at beginning (PC only)

**Note:** This section is rarely modified by save editors. Contains game balance data.

---

## Checksum System

### MD5 Calculation

**Algorithm:** Standard MD5 hash

**Applies to:**
- Each character slot (PC only)
- USER_DATA_10 (PC only)
- USER_DATA_11 (PC only)

### Checksum Calculation Per Section

```python
import hashlib

def calculate_checksum(data: bytes) -> bytes:
    """
    Calculate MD5 checksum for a section.
    
    Args:
        data: Section data (without the checksum itself)
    
    Returns:
        16-byte MD5 hash
    """
    return hashlib.md5(data).digest()
```

### Character Slot Checksum

```python
def checksum_character_slot(slot_data: bytes) -> bytes:
    """
    Calculate checksum for character slot.
    
    Args:
        slot_data: Complete slot (0x280010 bytes)
    
    Returns:
        MD5 hash to write at offset 0x00-0x0F
    """
    # Hash data portion (skip checksum area)
    character_data = slot_data[0x10:0x280010]
    return hashlib.md5(character_data).digest()
```

### Checksum Regions

| Section | Checksum Offset | Data Start | Data End | Data Size |
|---------|----------------|------------|----------|-----------|
| Slot 0 | 0x300 | 0x310 | 0x28030F | 0x280000 |
| Slot 1 | 0x280310 | 0x280320 | 0x50031F | 0x280000 |
| ... | ... | ... | ... | ... |
| Slot 9 | 0x1680390 | 0x16803A0 | 0x190039F | 0x280000 |
| UD10 | 0x19003A0 | 0x19003B0 | 0x1F003AF | 0x60000 |
| UD11 | 0x1F003B0 | 0x1F003C0 | 0x21403BF | 0x240000 |

---

## Version Detection

### Version Field

```c
uint32_t version;  // At offset 0x00 in character data
```

**Version-specific changes:**
- GaitemMap entry count (5118 vs 5120)
- DLC data presence
- Event flag layout
- Additional fields

### Handling Version Differences

```python
def parse_character_slot(data: bytes, offset: int) -> UserDataX:
    version = struct.unpack('<I', data[offset:offset+4])[0]
    
    if version >= 83:
        # Parse with DLC data
        has_dlc = True
        gaitem_count = 5120
    else:
        # Parse pre-DLC
        has_dlc = False
        gaitem_count = 5118
    
    # Continue parsing...
```

---


## Validation

### Integrity Checks

**Before Loading:**
1. Check magic bytes match platform
2. Verify file size is correct
3. Validate checksums (PC)
4. Check version is supported

**After Parsing:**
1. Verify slot count = 10
2. Check character data sizes
3. Validate MapId ranges
4. Verify SteamID consistency

### Corruption Detection

**Indicators:**
- Checksum mismatch
- Invalid version number
- Impossible stat values
- Malformed structures
- Truncated file

---

## Hex Dump Example

### File Header (First 32 bytes)

```
Offset    00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F
────────────────────────────────────────────────────────
00000000  42 4E 44 34 00 00 00 01 00 00 00 00 00 00 00 00  BND4............
00000010  40 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  @...............
```

### Character Slot Start (Offset 0x300)

```
Offset    00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F
────────────────────────────────────────────────────────
00000300  8A 3F 4C 91 D2 7E 44 B8 9C 1F 83 20 A7 E6 55 C9  .?L..~D.... ..U.  ← Checksum
00000310  53 00 00 00 3C 28 00 00 00 00 00 00 00 00 00 00  S...<(..........  ← Version + MapId
```

---

## Related Documentation

- **[Character Slot Structure](Character-Slot-Structure)** - Detailed UserDataX layout
- **[Checksum System](Checksum-System)** - Checksum calculation details
- **[Event Flag System](Event-Flag-System)** - Event flags structure
- **[Parser Architecture](Parser-Architecture)** - How parser reads this format

---

[← Back to Technical Documentation](Home#-technical-documentation)
