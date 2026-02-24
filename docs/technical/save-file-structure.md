# Save File Structure

Complete technical reference for the Elden Ring save file format.

All sizes and offsets are sourced directly from the parser implementation.

---

## File Layout

**File size:** ~26 MB (26,214,400 bytes, PC)  
**Endianness:** Little-endian throughout  
**Checksum:** MD5 per section (PC only)

```
Offset       Size         Section
─────────────────────────────────────────────────────────
0x000        4 bytes      Magic
0x004        0x2FC        Header (PC) / 0x6C (PlayStation)
─────────────────────────────────────────────────────────
0x300        0x280010     Character Slot 0
0x280310     0x280010     Character Slot 1
0x500320     0x280010     Character Slot 2
0x780330     0x280010     Character Slot 3
0xA00340     0x280010     Character Slot 4
0xC80350     0x280010     Character Slot 5
0xF00360     0x280010     Character Slot 6
0x1180370    0x280010     Character Slot 7
0x1400380    0x280010     Character Slot 8
0x1680390    0x280010     Character Slot 9
─────────────────────────────────────────────────────────
0x19003A0    0x60010      USER_DATA_10 (SteamID, profiles)
0x1F003B0    0x240010     USER_DATA_11 (Regulation data)
─────────────────────────────────────────────────────────
```

### Platform Detection

| Magic bytes | Platform | Notes |
|------------|----------|-------|
| `42 4E 44 34` (`BND4`) | PC Steam | Standard |
| `53 4C 32 00` (`SL2\x00`) | PC (alt) | Accepted by parser |
| `CB 01 9C 2C` | PlayStation | No checksums |

---

## Character Slot (UserDataX)

Each slot is `0x280010` bytes on PC, `0x280000` on PlayStation.

```
PC slot layout:
  0x00-0x0F    16 bytes    MD5 checksum
  0x10-...     0x280000    Character data

PlayStation slot layout:
  0x00-...     0x280000    Character data (no checksum)
```

**Empty slot detection:** checksum bytes are all `0x00`.

The parser reads slots sequentially in this exact order:

```
Field                          Type                    Size
──────────────────────────────────────────────────────────────────────
version                        uint32                  4
map_id                         MapId                   4
unk0x8                         bytes                   8
unk0x10                        bytes                   16
gaitem_map                     Gaitem[]                5118×8 or 5120×8
player_game_data               PlayerGameData          432 (0x1B0)
sp_effects                     SPEffect[13]            208 (0xD0)
equipped_items_equip_index     EquipmentSlots          88 (0x58)
active_weapon_slots_and_arm    ActiveWeaponSlots        28 (0x1C)
equipped_items_item_id         EquipmentSlots          88 (0x58)
equipped_items_gaitem_handle   EquipmentSlots          88 (0x58)
inventory_held                 Inventory               variable
equipped_spells                EquippedSpells          116 (0x74)
equipped_items                 EquippedItems           140 (0x8C)
equipped_gestures              EquippedGestures        24 (0x18)
acquired_projectiles           AcquiredProjectiles     variable
equipped_armaments_and_items   EquippedArmamentsAndItems 156 (0x9C)
equipped_physics               EquippedPhysics         12 (0xC)
face_data                      FaceData                303 (0x12F)
inventory_storage_box          Inventory               variable
gestures                       Gestures                256 (0x100)
unlocked_regions               Regions                 variable
horse                          RideGameData            40 (0x28)
control_byte_maybe             uint8                   1
blood_stain                    BloodStain              68 (0x44)
unk_gamedataman_0x120          uint32                  4
unk_gamedataman_0x88           uint32                  4
menu_profile_save_load         MenuSaveLoad            variable
trophy_equip_data              TrophyEquipData         52 (0x34)
gaitem_game_data               GaitemGameData          variable
tutorial_data                  TutorialData            variable
gameman_0x8c                   uint8                   1
gameman_0x8d                   uint8                   1
gameman_0x8e                   uint8                   1
total_deaths_count             uint32                  4
character_type                 uint32                  4
in_online_session_flag         uint32                  4
character_type_online          uint32                  4
last_rested_grace              uint32                  4
not_alone_flag                 uint32                  4
in_game_countdown_timer        uint32                  4
unk_gamedataman_0x124          uint32                  4
event_flags                    bytes                   1,833,375 (0x1BF99F)
event_flags_terminator         uint32                  4
field_area                     FieldArea               variable
world_area                     WorldArea               variable
world_geom_man                 WorldGeomMan            variable
world_geom_man2                WorldGeomMan            variable
rend_man                       RendMan                 variable
player_coordinates             PlayerCoordinates       57 (0x39)
game_man_0x5be                 uint8                   1
game_man_0x5bf                 uint8                   1
spawn_point_entity_id          uint32                  4
game_man_0xb64                 uint32                  4
temp_spawn_point_entity_id     uint32 (version >= 65)  4 or 0
game_man_0xcb3                 uint32 (version >= 66)  4 or 0
net_man                        NetMan                  131,076 (0x20004)
world_area_weather             WorldAreaWeather        12 (0xC)
world_area_time                WorldAreaTime           12 (0xC)
base_version                   BaseVersion             16 (0x10)
steam_id                       uint64                  8
ps5_activity                   PS5Activity             32 (0x20)
dlc                            DLC                     50 (0x32)
player_data_hash               PlayerGameDataHash      128 (0x80)
rest                           bytes                   remainder
──────────────────────────────────────────────────────────────────────
```

Gaitem count: `5118` if `version <= 81`, `5120` if `version > 81`.

---

## PlayerGameData - 432 bytes (0x1B0)

Character stats, attributes, and metadata.

```
Offset  Size  Field
──────────────────────────────────────────────────
0x00    4     unk0x0
0x04    4     unk0x4
0x08    4     hp
0x0C    4     max_hp
0x10    4     base_max_hp
0x14    4     fp
0x18    4     max_fp
0x1C    4     base_max_fp
0x20    4     unk0x20
0x24    4     sp (stamina)
0x28    4     max_sp
0x2C    4     base_max_sp
0x30    4     unk0x30
──────────────────────────────────────────────────
0x34    4     vigor
0x38    4     mind
0x3C    4     endurance
0x40    4     strength
0x44    4     dexterity
0x48    4     intelligence
0x4C    4     faith
0x50    4     arcane
0x54    4     unk0x54
0x58    4     unk0x58
0x5C    4     unk0x5c
──────────────────────────────────────────────────
0x60    4     level
0x64    4     runes
0x68    4     runes_memory
0x6C    4     unk0x6c
──────────────────────────────────────────────────
0x70    4     poison_buildup
0x74    4     rot_buildup
0x78    4     bleed_buildup
0x7C    4     death_buildup
0x80    4     frost_buildup
0x84    4     sleep_buildup
0x88    4     madness_buildup
0x8C    4     unk0x8c
0x90    4     unk0x90
──────────────────────────────────────────────────
0x94    32    character_name (UTF-16LE, 16 chars max)
0xB4    2     terminator
──────────────────────────────────────────────────
0xB6    1     gender
0xB7    1     archetype
0xB8    1     unk0xb8
0xB9    1     unk0xb9
0xBA    1     voice_type
0xBB    1     gift
0xBC    1     unk0xbc
0xBD    1     unk0xbd
0xBE    1     additional_talisman_slot_count
0xBF    1     summon_spirit_level
0xC0    24    unk0xc0
──────────────────────────────────────────────────
0xD8    1     furl_calling_finger_on (bool)
0xD9    1     unk0xd9
0xDA    1     matchmaking_weapon_level
0xDB    1     white_cipher_ring_on (bool)
0xDC    1     blue_cipher_ring_on (bool)
0xDD    26    unk0xdd
0xF7    1     great_rune_on (bool)
0xF8    1     unk0xf8
──────────────────────────────────────────────────
0xF9    1     max_crimson_flask_count
0xFA    1     max_cerulean_flask_count
0xFB    21    unk0xfb
──────────────────────────────────────────────────
0x110   18    password (UTF-16LE, 8 chars + terminator)
0x122   18    group_password1
0x134   18    group_password2
0x146   18    group_password3
0x158   18    group_password4
0x16A   18    group_password5
──────────────────────────────────────────────────
0x17C   52    unk0x17c (padding)
──────────────────────────────────────────────────
       432    total
```

---

## SPEffect - 16 bytes per entry, 13 entries (208 bytes total)

Active status effects, buffs, weapon enchants.

```
Offset  Size  Type    Field
──────────────────────────────
0x00    4     int32   sp_effect_id
0x04    4     float   remaining_time
0x08    4     uint32  unk0x8
0x0C    4     uint32  unk0x10
──────────────────────────────
        16    total per entry
```

An entry is active when `sp_effect_id != 0` and `remaining_time > 0`.

---

## Equipment Slots - 88 bytes (0x58)

Used by three parallel structures: `EquippedItemsEquipIndex`, `EquippedItemsItemIds`, `EquippedItemsGaitemHandles`. All three have identical layout, differing only in what the values mean (inventory index, item ID, or gaitem handle).

```
Offset  Size  Field
──────────────────────────────
0x00    4     left_hand_armament1
0x04    4     right_hand_armament1
0x08    4     left_hand_armament2
0x0C    4     right_hand_armament2
0x10    4     left_hand_armament3
0x14    4     right_hand_armament3
0x18    4     arrows1
0x1C    4     bolts1
0x20    4     arrows2
0x24    4     bolts2
0x28    4     unk0x28
0x2C    4     unk0x2c
0x30    4     head
0x34    4     chest
0x38    4     arms
0x3C    4     legs
0x40    4     unk0x40
0x44    4     talisman1
0x48    4     talisman2
0x4C    4     talisman3
0x50    4     talisman4
0x54    4     unk0x54
──────────────────────────────
        88    total
```

---

## ActiveWeaponSlotsAndArmStyle - 28 bytes (0x1C)

```
Offset  Size  Field
──────────────────────────────
0x00    4     arm_style
0x04    4     left_hand_weapon_active_slot
0x08    4     right_hand_weapon_active_slot
0x0C    4     left_arrow_active_slot
0x10    4     right_arrow_active_slot
0x14    4     left_bolt_active_slot
0x18    4     right_bolt_active_slot
──────────────────────────────
        28    total
```

---

## Inventory - variable size

Two instances: held and storage box.

```
Field                  Type           Notes
──────────────────────────────────────────────────────────────
common_item_count      uint32         actual item count
common_items           InventoryItem  held: 0xA80 slots, storage: 0x780 slots
key_item_count         uint32         actual key item count
key_items              InventoryItem  held: 0x180 slots, storage: 0x80 slots
equip_index_counter    uint32
acquisition_index_counter uint32
──────────────────────────────────────────────────────────────
```

All slots are always written to disk (empty slots have zeroed data). Counts reflect actual items, capacity is fixed.

**InventoryItem - 12 bytes:**

```
Offset  Size  Field
──────────────────────────
0x00    4     gaitem_handle
0x04    4     quantity
0x08    4     acquisition_index
──────────────────────────
        12    total
```

---

## EquippedSpells - 116 bytes (0x74)

14 spell slots + active index.

```
Field           Type      Size   Notes
──────────────────────────────────────────────
spell_slots     Spell[14] 112    8 bytes each
active_index    uint32    4
──────────────────────────────────────────────
                          116    total
```

**Spell - 8 bytes:**

```
Offset  Size  Field
──────────────
0x00    4     spell_id
0x04    4     unk0x4
```

---

## EquippedItems - 140 bytes (0x8C)

Quick items and pouch items.

```
Field                   Type           Size   Notes
──────────────────────────────────────────────────────
quick_items             EquippedItem   80     10 × 8 bytes
active_quick_item_index uint32         4
pouch_items             EquippedItem   48     6 × 8 bytes
unk0x84                 uint32         4
unk0x88                 uint32         4
──────────────────────────────────────────────────────
                                       140    total
```

**EquippedItem - 8 bytes:**

```
Offset  Size  Field
──────────────────
0x00    4     gaitem_handle
0x04    4     equip_index
```

---

## EquippedGestures - 24 bytes (0x18)

6 equipped gesture IDs, each 4 bytes.

---

## AcquiredProjectiles - variable

```
Field        Type          Notes
──────────────────────────────────────────
count        uint32        number of entries
projectiles  Projectile[]  count × 8 bytes
──────────────────────────────────────────
```

**Projectile - 8 bytes:** `id` (uint32) + `unk0x4` (uint32).

---

## EquippedArmamentsAndItems - 156 bytes (0x9C)

Combined equipment state including quick items and pouch. Extends the 88-byte equipment slots with 10 quick item slots, 6 pouch slots, and 1 unknown field.

```
Offset  Size  Field
──────────────────────────────
0x00    88    (same as EquipmentSlots layout above)
0x58    4     quickitem1
0x5C    4     quickitem2
0x60    4     quickitem3
0x64    4     quickitem4
0x68    4     quickitem5
0x6C    4     quickitem6
0x70    4     quickitem7
0x74    4     quickitem8
0x78    4     quickitem9
0x7C    4     quickitem10
0x80    4     pouch1
0x84    4     pouch2
0x88    4     pouch3
0x8C    4     pouch4
0x90    4     pouch5
0x94    4     pouch6
0x98    4     unk0x98
──────────────────────────────
        156   total
```

---

## EquippedPhysics - 12 bytes (0xC)

Wondrous Physick tear slots.

```
Offset  Size  Field
──────────────────
0x00    4     slot1
0x04    4     slot2
0x08    4     unk0x8
```

---

## FaceData - 303 bytes (0x12F)

Character appearance data. Stored as raw bytes - contains 100+ fields for facial features, body proportions, and color sliders. When read from `ProfileSummary` (USER_DATA_10), reads `0x120` bytes instead of `0x12F`.

---

## Gestures - 256 bytes (0x100)

64 gesture IDs, each 4 bytes (`uint32`).

---

## Regions - variable

```
Field       Type      Notes
──────────────────────────────────────
count       uint32
region_ids  uint32[]  count × 4 bytes
──────────────────────────────────────
```

---

## RideGameData (Torrent) - 40 bytes (0x28)

```
Offset  Size  Type          Field
──────────────────────────────────────────
0x00    12    FloatVector3  coordinates (x, y, z)
0x0C    4     MapId         map_id
0x10    16    FloatVector4  angle (x, y, z, w)
0x20    4     int32         hp
0x24    4     uint32        state (HorseState enum)
──────────────────────────────────────────
        40    total
```

**HorseState values:** `INACTIVE = 0`, `ACTIVE = 13`, `DEAD = 3`

**Torrent bug:** `hp == 0` AND `state == ACTIVE (13)` causes infinite loading. Fix: set `state = DEAD (3)`.

---

## BloodStain - 68 bytes (0x44)

Death location and lost runes.

```
Offset  Size  Type          Field
──────────────────────────────────────
0x00    12    FloatVector3  coordinates
0x0C    16    FloatVector4  angle
0x1C    4     uint32        unk0x1c
0x20    4     uint32        unk0x20
0x24    4     uint32        unk0x24
0x28    4     uint32        unk0x28
0x2C    4     uint32        unk0x2c
0x30    4     uint32        unk0x30
0x34    4     uint32        runes
0x38    4     MapId         map_id
0x3C    4     uint32        unk0x3c
0x40    4     uint32        unk0x38
──────────────────────────────────────
        68    total
```

---

## Event Flags - 1,833,375 bytes (0x1BF99F)

Bitfield encoding all quest flags, boss defeats, grace unlocks, and world state. Each bit corresponds to a specific game event by ID. Followed by a 4-byte `event_flags_terminator`.

---

## PlayerCoordinates - 57 bytes (0x39)

```
Offset  Size  Type          Field
──────────────────────────────────────────
0x00    12    FloatVector3  coordinates
0x0C    4     MapId         map_id
0x10    16    FloatVector4  angle
0x20    1     uint8         game_man_0xbf0
0x21    12    FloatVector3  unk_coordinates
0x2D    16    FloatVector4  unk_angle
──────────────────────────────────────────
        57    total
```

---

## NetMan - 131,076 bytes (0x20004)

Network manager state. `unk0x0` (uint32, 4 bytes) followed by `0x20000` bytes of data.

---

## WorldAreaWeather - 12 bytes (0xC)

```
Offset  Size  Type    Field
──────────────────────────────
0x00    2     uint16  area_id
0x02    2     uint16  weather_type
0x04    4     uint32  timer
0x08    4     uint32  padding
──────────────────────────────
        12    total
```

**Corruption:** `area_id == 0` when character is in a real location, or `timer > 100000`.

---

## WorldAreaTime - 12 bytes (0xC)

```
Offset  Size  Type    Field
──────────────────────────
0x00    4     uint32  hour
0x04    4     uint32  minute
0x08    4     uint32  second
──────────────────────────
        12    total
```

Should match `seconds_played` from `ProfileSummary`. All zeros indicates corruption.

---

## BaseVersion - 16 bytes (0x10)

```
Offset  Size  Type    Field
──────────────────────────────────
0x00    4     uint32  base_version_copy
0x04    4     uint32  base_version
0x08    4     uint32  is_latest_version
0x0C    4     uint32  unk0xc
──────────────────────────────────
        16    total
```

---

## DLC - 50 bytes (0x32)

Raw bytes. Notable fields:

- `data[1]` - Shadow of the Erdtree entry flag. Non-zero = character has entered the DLC area. Causes infinite loading if DLC is not owned.
- `data[3:50]` - Unused. Should be all `0x00`. Non-zero values indicate corruption.

---

## PS5Activity - 32 bytes (0x20)

Raw bytes. PlayStation-specific activity data.

---

## PlayerGameDataHash - 128 bytes (0x80)

Integrity hash computed from player data and equipment.

```
Offset  Size  Field
──────────────────────────────────────────────
0x00    4     level
0x04    4     stats
0x08    4     archetype
0x0C    4     playergame_data_0xc0
0x10    4     padding
0x14    4     runes
0x18    4     runes_memory
0x1C    4     equipped_weapons
0x20    4     equipped_armors_and_talismans
0x24    4     equipped_items
0x28    4     equipped_spells
0x2C    84    rest
──────────────────────────────────────────────
        128   total
```

---

## USER_DATA_10

Located at `0x19003A0` (PC). Size: `0x60010` bytes including checksum.

```
Offset  Size    Field
──────────────────────────────────────────────────────
0x00    16      checksum (MD5, PC only)
0x10    8       steam_id (uint64)
0x18    ...     ProfileSummary (10 × 0x24C = 5,880 bytes)
...     10      active_slots (uint8[10], 1=in use 0=empty)
──────────────────────────────────────────────────────
```

**Profile - 0x24C (588 bytes) per slot:**

```
Offset  Size  Field
──────────────────────────────────────────────────
0x00    32    character_name (UTF-16LE, 16 chars)
0x20    4     level (uint32)
0x24    4     seconds_played (uint32)
0x120   ...   face_data (FaceData, 0x120 bytes in profile context)
...           additional fields
──────────────────────────────────────────────────
0x24C         total
```

---

## USER_DATA_11

Located at `0x1F003B0` (PC). Size: `0x240010` bytes including checksum.

Game regulation data (item stats, scaling, balance). Not edited by the save editor. MD5 checksum at start (PC only), followed by `0x240000` bytes of regulation blob.

---

## Checksums

MD5, PC only. Applied to each character slot and both USER_DATA sections.

```python
import hashlib

def recalculate(slot_data: bytes) -> bytes:
    # Skip first 16 bytes (existing checksum), hash the rest
    return hashlib.md5(slot_data[0x10:]).digest()
```

The parser tracks slot offsets dynamically during read. Checksums are recalculated using those tracked offsets, not hardcoded values.

| Section | Checksum at | Data from | Data size |
|---------|------------|-----------|-----------|
| Slot 0  | `0x300`    | `0x310`   | `0x280000` |
| Slot 1  | `0x280310` | `0x280320`| `0x280000` |
| ...     | ...        | ...       | `0x280000` |
| Slot 9  | `0x1680390`| `0x16803A0`| `0x280000`|
| UD10    | `0x19003A0`| `0x19003B0`| `0x60000` |
| UD11    | `0x1F003B0`| `0x1F003C0`| `0x240000`|

---

[← Back to Home](../index.md)