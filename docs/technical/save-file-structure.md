# Save File Structure

Complete technical reference for the Elden Ring save file format.

All sizes and offsets are sourced directly from the parser implementation.

---

## File Layout

**File size:** 28,967,888 bytes (0x1BA03D0, PC)  
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
0x19603B0    0x240020     USER_DATA_11 (Regulation data)
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

**Empty slot detection:** `version == 0` (first u32 of the character data). On PC the parser also skips a slot whose checksum is all `0x00` without reading it.

The parser reads slots sequentially in this exact order:

```
Field                          Type                    Size
──────────────────────────────────────────────────────────────────────
version                        uint32                  4
map_id                         MapId                   4
play_time_ms                   uint64                  8
unk0x10                        bytes                   16
gaitem_map                     Gaitem[]                variable (see Gaitem below)
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
character_type                 int32                   4
in_online_session_flag         uint8                   1
character_type_online          uint32                  4
last_rested_grace              uint32                  4
not_alone_flag                 uint8                   1
in_game_countdown_timer        uint32                  4
unk_gamedataman_0x124          uint32                  4
event_flags                    bytes                   1,833,375 (0x1BF99F)
event_flags_terminator         uint8                   1
field_area                     FieldArea               variable
world_area                     WorldArea               variable
world_geom_man                 WorldGeomMan            variable
world_geom_man2                WorldGeomMan            variable
rend_man                       RendMan                 variable
player_coordinates             PlayerCoordinates       61 (0x3D)
game_man_0x5be                 uint8                   1
game_man_0x5bf                 uint8                   1
spawn_point_entity_id          uint32                  4
game_man_0xb64                 uint32                  4
temp_spawn_point_entity_id     uint32 (version >= 65)  4 or 0
game_man_0xcb3                 uint8 (version >= 66)   1 or 0
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

Notes on the scalar fields:

- `play_time_ms`: play time in milliseconds; ProfileSummary `seconds_played` is the same value in seconds.
- `unk0x10`: unknown. Rewritten with a new value on every save.
- `unk_gamedataman_0x120`: NG+ clear count (GameDataMan+0x120). `unk_gamedataman_0x88` is always 0.
- `unk_gamedataman_0x124`: unknown, 0-99. Set to a new value on every area load (loading the character,
  warping, resting).
- `character_type`: -1 by default. `character_type_online`: 8 by default.
- `game_man_0x5bf`: 1 after warping to a grace, 0 after resting at one.
- `game_man_0xb64` (0 or a spawn point entity id) and `game_man_0xcb3` (0/1): unknown.

---

## PlayerGameData - 432 bytes (0x1B0)

Character stats, attributes, and metadata. The block is the in-memory `CS::PlayerGameData` starting at
its offset 0x8, so memory offsets from cheat tables are save offset + 8.

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
0x5C    4     unk0x5c              humanity (unused, always 0)
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
0x90    4     unk0x90              character type, 0
──────────────────────────────────────────────────
0x94    32    character_name (UTF-16LE, 16 chars max)
0xB4    2     terminator
──────────────────────────────────────────────────
0xB6    1     gender
0xB7    1     archetype
0xB8    1     unk0xb8              "appearance", 0
0xB9    1     unk0xb9
0xBA    1     voice_type
0xBB    1     gift
0xBC    1     unk0xbc
0xBD    1     memory_stone_count (Memory Stones used, 0-8)
0xBE    1     additional_talisman_slot_count
0xBF    1     summon_spirit_level
0xC0    24    unk0xc0
──────────────────────────────────────────────────
0xD8    1     furl_calling_finger_on (bool)
0xD9    1     unk0xd9
0xDA    1     matchmaking_weapon_level
0xDB    1     white_cipher_ring_on (bool)
0xDC    1     blue_cipher_ring_on (bool)
0xDD    23    unk0xdd
0xF4    1     scadutree_blessing (0-20)
0xF5    1     revered_spirit_ash_blessing (0-10)
0xF6    1     unk0xf6
0xF7    1     great_rune_on (bool, set by using a Rune Arc)
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
0x17C   52    unk0x17c (not padding: 0x17C-0x17E and 0x180/0x184 vary, meaning unknown)
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
0x08    4     uint32  unk0x8      always 0
0x0C    4     uint32  unk0x10     always 0
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
0x28    4     arrows3              unused, always empty
0x2C    4     bolts3               unused, always empty
0x30    4     head
0x34    4     chest
0x38    4     arms
0x3C    4     legs
0x40    4     hair                 unused, always empty
0x44    4     talisman1
0x48    4     talisman2
0x4C    4     talisman3
0x50    4     talisman4
0x54    4     talisman5            unused, always empty
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

## Gaitem - variable size (8, 16, or 21 bytes per entry)

Item instance table. 5118 or 5120 entries back to back (see Gaitem count above), each entry's size depends on its own `gaitem_handle`, so entries must be read sequentially, there is no fixed stride.

```
Offset  Size  Field               Present when
────────────────────────────────────────────────────────────────────
0x00    4     gaitem_handle       always
0x04    4     item_id             always
0x08    4     unk0x10             handle != 0 AND (handle & 0xF0000000) != 0xC0000000
0x0C    4     unk0x14             same as unk0x10
0x10    4     gem_gaitem_handle   (handle & 0xF0000000) == 0x80000000 (weapon only)
0x14    1     unk0x1c             same as gem_gaitem_handle
────────────────────────────────────────────────────────────────────
```

Handle type is read from the top nibble of `gaitem_handle`: `0x80` = weapon, `0x90` = armor, `0xC0` = gem/Ash of War. A handle of `0` means an empty slot in the map (base 8 bytes only).

Resulting entry size:

- 8 bytes: empty (`handle == 0`), or gem/AoW (`0xC0` prefix)
- 16 bytes: armor (`0x90` prefix)
- 21 bytes: weapon (`0x80` prefix)

`gem_gaitem_handle` is a weapon's live reference to the gaitem entry of its equipped Ash of War (that AoW's own entry is a normal 8-byte `0xC0` entry elsewhere in the map, it does not point back). `unk0x10`, `unk0x14` and `unk0x1c` are unknown. The game writes `0`, and so does the manager on item creation.

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
0x04    4     unk0x4       -1 on filled slots, 0 on empty slots
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
great_rune              uint32         4      goods handle 0xB0000000 | id, 0 if none
great_rune_equip_index  uint32         4      key item list index, -1 if none
──────────────────────────────────────────────────────
                                       140    total
```

The equipped Great Rune is goods 191-196 (Godrick, Radahn, Morgott, Rykard, Mohg, Malenia). Whether its effect is active is `PlayerGameData.great_rune_on` (0xF7), set by a Rune Arc.

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

Auto-refill settings, despite the name.

```
Field        Type          Notes
──────────────────────────────────────────
count        uint32        number of entries
projectiles  Projectile[]  count × 8 bytes
──────────────────────────────────────────
```

**Projectile - 8 bytes:** `id` (uint32, ammo weapon id or `0x40000000 |` goods id) + `auto_replenish` (uint32, 1 = auto-refill from the chest on, toggled in the chest with Auto-refill ON/OFF).

Every ammo or goods item the character has obtained whose EquipParamGoods `autoReplenishType` is 1 (default off) or 2 (default on) gets an entry.

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
0x98    4     unk0x98              always -1
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
0x08    4     unk0x8       always -1
```

---

## FaceData - 303 bytes (0x12F)

Character appearance. The parser keeps it as raw bytes. The `FACE` block uses the same layout as the appearance presets in USER_DATA_10 (`FacePreset` in `character_presets.py`, where field names like `unk0x14` are offsets from the `FACE` magic). The ProfileSummary copy in USER_DATA_10 is the first `0x124` bytes.

```
Offset   Size   Field
──────────────────────────────────────────────────────────────
0x000    4      marker (-1)
0x004    4      magic "FACE"
0x008    4      uint32 4
0x00C    4      uint32 size of the FACE block (0x120)
0x010    32     8 model ids, u8 + 3 padding each: face, hair, eye, eyebrow,
                beard, accessory, decal (tattoo), eyelash
0x030    64     facial structure sliders (apparent age .. nose slant)
0x070    64     FaceGen parameters the character creator does not expose
                (128 or 0, except 0x8E)
0x0B0    7      body scale: head, chest, abdomen, right arm, right leg,
                left arm, left leg
0x0B7    91     skin, cosmetics, tattoo, body hair, eye, hair, beard, brow,
                eyelash and accessory colors
0x112    1      frenzied flame eye effect, normally 0
0x113    17     zero padding
0x124    1      uint8, always 1
0x125    1      uint8, 0/1, unknown
0x126    1      uint8, 0/1, unknown
0x127    4      int32 face param override, slot 0 (FaceParam id, -1 = none)
0x12B    4      int32 face param override, slot 1 (FaceParam id, -1 = none)
──────────────────────────────────────────────────────────────
         303    total
```

The preset field `unk0xb1` (2 bytes) holds the left arm and left leg scale; `arms` and `legs` are the right side.

The face param overrides are set by the EMEVD instruction Set Character Face Param Override. common.emevd
event 1800 sets slot 0 to FaceParam 81000-81002 together with event flag 9420; event 1801 sets slot 1 to
80000 together with flag 9421 once flag 9430 (set in m35_00) is on.

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

Same layout as the in-memory bloodstain at GameDataMan+0x48. On death the game writes the position, angle, `map_id` and `runes`, sets `unk0x30` from -1 to 0 and updates `unk0x38` (at 0x40). Recovering the runes sets `unk0x30` and `runes` back to -1 and leaves the other fields as they are, so `runes == -1` means there is no bloodstain. `unk0x38` is -1, a small number, or `0x0FF0000n` / `0x8FF0nnnn`; its meaning is unknown. `unk0x1c`-`unk0x2c` and `unk0x3c` are always 0.

---

## MenuSaveLoad - variable

Menu profile save and load data.

```
Offset  Size  Type    Field    Notes
────────────────────────────────────────────────────────────────
0x00    2     uint16  unk0x0
0x02    2     uint16  unk0x02
0x04    4     uint32  size
0x08    size          data     normally 0x1000 bytes
────────────────────────────────────────────────────────────────
```

`data` holds a nested chunk: u16 1, u16 version, u32 size (version 2, size 0xFDC on current saves; version 0,
size 0xF10 on older ones). Version 2 holds the world map beacons and markers, offsets from the start of
`data`:

```
0x008   2 x (float, float), unknown
0x018   uint32, unknown
0x01C   zero
0x108   10 beacon records
0x1A8   100 marker records
0x7E8   bitset up to the chunk end, unknown
```

Beacon and marker record, 16 bytes:

```
Offset  Size  Type    Field
──────────────────────────────────────────────────────
0x00    4     int32   id (-1 = empty); beacons use an increasing sequence number
0x04    4     float   x on the world map
0x08    4     float   y on the world map
0x0C    1     uint8   map (0 = Lands Between, 10 = Realm of Shadow)
0x0D    1     uint8   marker icon (beacons and empty records: 1)
0x0E    2     uint16  0, or 0xFFFF on a newly placed beacon
──────────────────────────────────────────────────────
```

---

## TrophyEquipData - 52 bytes (0x34)

```
Offset  Size  Type    Field
─────────────────────────────
0x00    4     uint32  unk0x0               always 0
0x04    16            legendary_weapons
0x14    16            legendary_goods
0x24    16            legendary_talismans
─────────────────────────────
        52    total
```

Progress of the four "Legendary" trophies. Each field is a 128-bit set with one bit per legendary item ever acquired; the bit stays set after the item is sold or discarded. Bit n is the n-th legendary item of that type in ascending item id order:

- `legendary_weapons`: Sword of Night and Flame, Dark Moon Greatsword, Marais Executioner's Sword, Golden Order Greatsword, Ruins Greatsword, Grafted Blade Greatsword, Eclipse Shotel, Devourer's Scepter, Bolt of Gransax
- `legendary_goods`: bits 0-6 Comet Azur, Founding Rain of Stars, Stars of Ruin, Ranni's Dark Moon, Flame of the Fell God, Elden Stars, Greyoll's Roar; bits 7-12 Black Knife Tiche, Mimic Tear, Cleanrot Knight Finlay, Ancient Dragon Knight Kristoff, Redmane Knight Ogha, Lhutel the Headless
- `legendary_talismans`: Erdtree's Favor +2, Radagon's Soreseal, Moon of Nokstella, Marika's Soreseal, Old Lord's Talisman, Radagon Icon, Godfrey Icon, Dragoncrest Greatshield Talisman

---

## GaitemGameData - 8 bytes + 14000x8 bytes (0x1B588)

Every item type the character has ever acquired.

```
Offset  Size    Type                   Field
──────────────────────────────────────────────
0x00    8       int64                  count
0x08    112000  GaitemGameDataEntry[]  entries (14000)
──────────────────────────────────────────────
        112008  total
```

The first `count` entries are live and sorted by `item_id`. Entries past `count` hold stale data and are preserved as read.

---

## GaitemGameDataEntry - 8 bytes

```
Offset  Size  Type    Field
──────────────────────────────────
0x00    4     uint32  item_id
0x04    1     uint8   acquired     1 on every live entry
0x05    3             pad          uninitialized on some entries
──────────────────────────────────
        8     total
```

`item_id` carries a category tag: weapons as base id without upgrade or affinity, `0x10000000 |` armor, `0x20000000 |` talisman, `0x40000000 |` goods, `0x80000000 |` Ash of War. Items stay listed after being sold or discarded.

---

## TutorialData - variable

Tutorial pop-ups the character has already been shown.

```
Offset  Size      Type               Field
─────────────────────────────────────────────────────────────────────
0x00    2         uint16             unk0x0       always 174
0x02    2         uint16             unk0x2       always 1
0x04    4         uint32             size         0x400
0x08    variable  TutorialDataChunk  data
─────────────────────────────────────────────────────────────────────
```

---

## TutorialDataChunk - variable

```
Offset  Size      Type      Field
────────────────────────────────────────
0x00    4         uint32    count
0x04    variable  uint32[]  tutorial_ids  TutorialParam row ids, first count are live
────────────────────────────────────────
```

---

## Event Flags - 1,833,375 bytes (0x1BF99F)

Bitfield encoding all quest flags, boss defeats, grace unlocks, and world state. Each bit corresponds to a specific game event by ID. Followed by a 1-byte `event_flags_terminator`.

---

## FieldArea, WorldArea, WorldGeomMan, WorldGeomMan2 and RendMan - variable

Each has a size, which is followed by size bytes of data.

```
Offset  Size  Type   Field  Notes
────────────────────────────────────────────────────
0x00    4     int32  size   (excludes it's own size)
0x04    size         data
────────────────────────────────────────────────────
```

FieldArea and WorldArea have a max size of 0x10000 while WorldGeomMan, WorldGeomMan2 and RendMan have a max size of 0x100000.
A size of 0 means the block has no data.

WorldArea, WorldGeomMan and WorldGeomMan2 hold the per-map world state: killed enemies, broken assets
and picked up items. RendMan holds ground decals (see below). All three are lists of per-map records keyed by a `MapId`. Each entry names a part
in that map's MSB (`map/mapstudio/<map>.msb`). The parser decodes them with `WorldArea.parse_chr()` and
`WorldGeomMan.parse_geom()`, RendMan with `RendMan.parse_decals()` (`parser/world.py`). All return
`None` if the data does not re-encode byte-identical.

### Overview

| Block | Magic | Content | Maps covered | Resting at a grace |
|-------|-------|---------|--------------|--------------------|
| WorldArea | `CHR ` | Enemy parts in a non-default state | Maps loaded around the player | Clears kills; event-driven entries come back on map load |
| WorldGeomMan | `MOEG` | Broken and picked up assets | Maps loaded around the player | Clears state 1 and 3, keeps state 2 |
| WorldGeomMan2 | `FOEG` | Permanently picked up one-time nodes | Every map ever visited | No change |

A record exists only while the game tracks the map. WorldArea and WorldGeomMan records appear when the
map loads and are dropped when it unloads, including records with no entries. LOD tiles of the open
world (`m60_XX_YY_01`, `_02`) get records too. Assets placed on a coarser tile are stored under that
tile: a breakable on `m60_42_37_00` may be listed under `m60_21_18_01`.

### FieldArea

No magic. `uint32 count`, then `count` records of `MapId map, uint32 n, n x MapId`. The record map is a
dungeon or legacy dungeon (Stranded Graveyard m18_00, catacombs m30/m31, Leyndell...), and the list holds
open world tiles (`m60_XX_YY_00`) next to it. `count` is usually 0.

### MapId in records

Records use the same 4-byte `MapId` as `PlayerCoordinates`: bytes `[DD, CC, BB, AA]` name map
`mAA_BB_CC_DD`. Example: `00 24 2A 3C` is `m60_42_36_00`.

### WorldArea (CHR) - enemy state

```
Offset  Size  Type    Field
──────────────────────────────────────────────────────────
0x00    4     char[4] magic ("CHR ")
0x04    4     uint32  version (0x21042700)
0x08    8     uint64  unknown (always 0)
0x10    ...           records, then a 16-byte terminator record
──────────────────────────────────────────────────────────
```

Record (`WorldChrMapRecord`), size is a multiple of 16:

```
Offset  Size  Type    Field
──────────────────────────────────────────────────────────
0x00    4     char[4] magic ("CSBC")
0x04    4     MapId   map_id (0xFFFFFFFF = terminator)
0x08    4     uint32  record_size (align16(16 + 4 * n))
0x0C    4     uint32  enemy_part_count << 14 | n
0x10    4 * n uint32  entries
...                   zero padding to record_size
──────────────────────────────────────────────────────────
```

`enemy_part_count` is the number of enemy parts in the map's MSB for the game version that wrote the
save. The terminator record is `CSBC FF FF FF FF` followed by 8 zero bytes.

Entry (`WorldChrEntry`, uint32):

```
Bits    Field
──────────────────────────────────────────────────────────
0-1     state (3 = killed since the last rest; 1 and 2 are rare, meaning unknown)
2-15    MSB part instance
16-29   character model (cXXXX)
30      always 1
──────────────────────────────────────────────────────────
```

Model and instance name the MSB enemy part: `0x50D78CAB` is `c4311_9002`, state 3.

Entries include regular enemies killed since the last rest and parts kept dead or disabled by map events.
For example, an NPC's part at a location they are not currently at is listed as long as that map is
loaded. Kills are removed when the player rests; event-driven entries are written again on every load.

### WorldGeomMan (MOEG) and WorldGeomMan2 (FOEG) - asset state

Both share one layout and differ only in magic and meaning.

```
Offset  Size  Type    Field
──────────────────────────────────────────────────────────
0x00    4     char[4] magic ("MOEG" or "FOEG")
0x04    4     uint32  version (0x21042600)
0x08    ...           records, then a 16-byte terminator record
──────────────────────────────────────────────────────────
```

Record (`WorldGeomMapRecord`):

```
Offset  Size  Type    Field
──────────────────────────────────────────────────────────
0x00    4     MapId   map_id (0xFFFFFFFF = terminator)
0x04    4     uint32  record_size (16 + 8 * n)
0x08    4     uint32  n
0x0C    4     uint32  unknown
0x10    8 * n         entries
──────────────────────────────────────────────────────────
```

The unknown u32 is constant for a map across characters but changes between game versions; its meaning
is not known. The terminator record is `FF FF FF FF` followed by 12 zero bytes.

Entry (`WorldGeomEntry`, 8 bytes):

```
Offset  Size  Type    Field
──────────────────────────────────────────────────────────
0x00    4     uint32  key: instance << 15 | state
0x04    4     uint32  model: 10000000 + AEG id
──────────────────────────────────────────────────────────
```

The AEG id is the AssetEnvironmentGeometryParam row (`AEGxxx_yyy` = `xxx * 1000 + yyy`). AEG id and
instance name the MSB asset part: key `0x11940003`, model `10099720` is `AEG099_720_9000`.

States:

| Block | State | Meaning |
|-------|-------|---------|
| WorldGeomMan | 1 | Asset broken (crates, pots, other breakables) |
| WorldGeomMan | 3 | Picked up since the last rest |
| WorldGeomMan | 2 | Picked up permanently (state 3 of a one-time node becomes 2 on rest) |
| WorldGeomMan2 | 1 | Picked up permanently |

Which pickups are permanent comes from AssetEnvironmentGeometryParam: assets with a
`pickUpItemLotParamId` and `isEnableRepick = 1` never respawn and are written to WorldGeomMan2. They are
the one-time nodes: Arteria Leaf, smithing and somber smithing stones, Grave and Ghost Glovewort,
Trina's and Miquella's Lily, butterflies, Golden Centipede, Formic Rock and the DLC equivalents.
Other pickups (Rowa Fruit, Erdleaf Flower, Cracked Crystal) respawn on rest and only appear in
WorldGeomMan with state 3.

### Examples

| Action | WorldArea | WorldGeomMan | WorldGeomMan2 |
|--------|-----------|--------------|---------------|
| Kill a regular enemy | `c4311_9002` state 3 added | - | - |
| Rest | entry removed | - | - |
| Break a crate | - | `AEG003_071_0103` state 1 added (under `m60_21_18_01`) | - |
| Rest | - | entry removed | - |
| Pick Rowa Fruit | - | `AEG099_720_9068` state 3 added | - |
| Rest | - | entry removed | - |
| Pick Arteria Leaf | - | `AEG099_691_9000` state 3 added | `AEG099_691_9000` state 1 added |
| Rest | - | state 3 becomes 2 | unchanged |

### RendMan - ground decals

```
Offset  Size     Type    Field
──────────────────────────────────────────────────────────
0x00    4        uint32  count
0x04    40 * n           decals
──────────────────────────────────────────────────────────
```

Decal (`RendManDecal`, 40 bytes):

```
Offset  Size  Type      Field
──────────────────────────────────────────────────────────
0x00    4     uint32    decal_id (DecalParam row)
0x04    18    int16[9]  three points (x, y, z) in 1/8 world units
0x16    2     uint16    padding (0)
0x18    16    uint32[4] unknown
──────────────────────────────────────────────────────────
```

Persistent decals around the player: blood splatter (445000, 610003), black liquid slashes (442204,
443400), burn marks (442600), and two unnamed families. 3000xxxxx decals repeat one point three times
and form trails about 2 units apart; 6001xxxxx decals are triangles with three distinct points.
Points are local to the player's map: on a point decal written where the player saved, point / 8
equals the player coordinates. On point decals the first three unknown u32 are equal.

### Editing

Adding or removing entries changes the block size, so every later section of the slot moves
(RendMan, PlayerCoordinates, NetMan, weather, time, BaseVersion, SteamID, DLC, PlayerGameDataHash).
Patching the bytes in place is not possible; the slot has to be rebuilt:

1. Re-encode the decoded block (`to_bytes()`) and set the block's `data` and `size`.
2. Rebuild the slot with `rebuild_slot()`, which serializes every section in order and pads or
   truncates to 0x280000 bytes. A shrinking block leaves zero padding at the slot end; a growing block
   is absorbed by `rest`, the stale serializer buffer at the end of the slot.
3. Re-parse the slot so the tracked offsets (coordinates, NetMan, SteamID, PlayerGameDataHash, ...)
   match the new layout, then update PlayerGameDataHash and the checksum.

A rebuild is only safe on a faithfully parsed slot (byte-identical round trip). On a misparsed slot,
for example a torn FieldArea, it writes the misread structures back and destroys data, so the
round trip has to be checked before editing. The editor does not write these blocks yet.

---

## PlayerCoordinates - 61 bytes (0x3D)

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
        61    total
```

`unk_coordinates`/`unk_angle` are a second position and rotation without a map id. Their purpose is
unknown. Dying, recovering runes, warping between graces and resting do not change them.

---

## NetMan - 131,076 bytes (0x20004)

Network manager state. `unk0x0` (uint32, always 2) followed by `0x20000` bytes of data.

The replacement template CSNetMan.bin starts 4 bytes before `net_man_offset`. Those 4 bytes belong to the
fields before NetMan (the top 3 bytes of `temp_spawn_point_entity_id` and `game_man_0xcb3`), so only the
template's bytes from offset 4 on are written.

The data is a list of chunks, each `uint16 type, uint16 version, uint32 size, size bytes`, ending with a
type `0xFFFF` chunk of size 0. The chunk order is 2, 5, 6, 8, 9, 7, 0xFFFF and the rest of the 0x20000
bytes is zero. A chain that does not reach the terminator within the buffer indicates corruption.

Every chunk holds a sub-entry list: `uint32 kind, uint32 size, size bytes`, each entry padded to 4 bytes,
ending with a kind `0xFFFF` entry of size 0. The list starts at the chunk's first byte, except in chunk 8,
which has a 12-byte header first. Chunks 2, 5, 9 and 7 hold an empty list (the terminator alone). A chunk
is valid when its list ends exactly at the chunk end.

**Repair:** the save fixer validates every chunk and rebuilds only the damaged ones from CSNetMan.bin. After
a torn write, intact chunks are found again at their shifted positions and kept.

```
Type  Version  Size      Content
──────────────────────────────────────────────────────────────────────
2     0        8         empty list
5     0        8         empty list
6     2        variable  other players' character snapshots
8     0        variable  12-byte header and a sub-entry list, meaning unknown
9     0        8         empty list
7     1        8         empty list
0xFFFF 0       0         terminator
──────────────────────────────────────────────────────────────────────
```

Chunk 6 entries of kind 0 or 1 are player records of about 600 bytes, followed by one kind 2 entry per
record holding an 8- or 12-byte id. A record holds the other player's equipment item ids, a full `FACE`
block, the character name (UTF-16) and a world position. The game updates a few bytes of every record on
each save.

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

In-game time of day (0-23, 0-59, 0-59). It is independent of play time, which is `play_time_ms` in the slot
header. New characters start at about 08:00.

---

## BaseVersion - 16 bytes (0x10)

```
Offset  Size  Type    Field
──────────────────────────────────
0x00    4     uint32  base_version_copy
0x04    4     uint32  base_version
0x08    4     uint32  is_latest_version
0x0C    4     uint32  unk0xc              always 0
──────────────────────────────────
        16    total
```

---

## DLC - 50 bytes (0x32)

```
Offset  Size  Field
──────────────────────────────────────────────
0x00    1     preorder_the_ring (gesture)
0x01    1     shadow_of_erdtree (entered the DLC)
0x02    1     preorder_ring_of_miquella (gesture)
0x03    1     tarnished_pack (Tarnished Edition)
0x04    46    unused
──────────────────────────────────────────────
        50    total
```

`shadow_of_erdtree` non-zero means the character has entered the DLC area; it causes a load error
if the DLC is not owned. `tarnished_pack` has the same failure mode without the Tarnished Edition.
The unused bytes should be all `0x00`; non-zero values indicate corruption.

---

## PS5Activity - 32 bytes (0x20)

Progress of the PlayStation 5 activity cards, one uint8 per activity: 0 not started, 1 in progress,
2 completed. Present on every platform.

```
Byte  Activity
──────────────────────────────────────────────────
0     main story (2 after Hoarah Loux)
1     Godrick the Grafted
2     Starscourge Radahn
3     Morgott, the Omen King
4     Fire Giant
5     Maliketh, the Black Blade
6     Hoarah Loux
7     0 or 1, follows event flag 6080; activity unknown
8-31  always 0
──────────────────────────────────────────────────
```

---

## PlayerGameDataHash - 128 bytes (0x80)

One checksum per tracked value, 11 x uint32 followed by 0x54 bytes. The game rewrites it on every save;
the editor recalculates it after edits (`parser/player_data_hash.py`). It sits at the parsed position
after DLC, not at the slot end.

Each checksum is an Adler-32 variant over little-endian bytes: `lo` starts at 1 and adds every byte,
`hi` adds `lo` after every byte, both are reduced modulo 0xFFF1, result `(lo | hi << 16) * 2`.

```
Offset  Entry  Input
──────────────────────────────────────────────────────────────────────
0x00    0      level (u32)
0x04    1      vigor..arcane (8 x u32) + PlayerGameData 0x54 (u32)
0x08    2      archetype (u8 as u32)
0x0C    3      PlayerGameData 0xB8 (1 byte)
0x10    4      unknown
0x14    5      runes held (u32)
0x18    6      runes memory (u32)
0x1C    7      equipped weapon item ids: L1, L2, L3, R1, R2, R3, arrows 1, arrows 2, bolts 1, bolts 2
0x20    8      equipped item id slots 12-15 (armor), 17-20 (talismans) and 21 (talisman5)
0x24    9      quick items (inputs unknown)
0x28    10     14 equipped spell ids
0x2C    -      0x54 bytes, uninitialized memory
──────────────────────────────────────────────────────────────────────
```

---

## USER_DATA_10

Located at `0x19003A0` (PC). Size: `0x60010` bytes including checksum. Offsets below are from the
section start on PC; PlayStation has no checksum, so subtract 0x10.

```
Offset  Size    Field
──────────────────────────────────────────────────────
0x00    16      checksum (MD5, PC only)
0x10    4       version (uint32)
0x14    8       steam_id (uint64)
0x1C    0x140   Settings (see below; first 0x30 bytes used, rest zero)
0x15C   0x1808  MenuSystemSaveLoad (appearance presets)
0x1964  0x1702  ProfileSummary
0x3066  5       GameMan bytes
0x306B  0xB2    PCOptionData (PC only)
...     var     KeyConfigSaveLoad (u16, u16, u32 size, size bytes)
...     8       game_man_0x118
...             unparsed remainder up to 0x60010
──────────────────────────────────────────────────────
```

**Settings:** one uint8 per option, same order as the in-memory option data at GameDataMan+0x58.

```
Offset  Field                      Offset  Field
──────────────────────────────────────────────────────────────────────
0x00    camera_speed               0x18    launchsettings
0x01    controller_vibration       0x19    send_summon_sign
0x02    brightness                 0x1A    unknown (default 1)
0x03    sound_type                 0x1B    hdr
0x04    music_volume               0x1C    hdr_adjust_brightness
0x05    sound_effects_volume       0x1D    hdr_maximum_brightness
0x06    voice_volume               0x1E    hdr_adjust_saturation
0x07    display_blood              0x1F    unknown (default 1)
0x08    subtitles                  0x20    master_volume
0x09    hud                        0x21    is_raytracing_on
0x0A    camera_x_axis              0x22    mark_new_items
0x0B    camera_y_axis              0x23    show_recent_tabs
0x0C    toggle_auto_lockon         0x24    10 bytes, always 0
0x0D    camera_auto_wall_recovery  0x2E    show_tutorials
0x0E    unknown (always 0)         0x2F    camera_auto_rotation
0x0F    unknown (default 1)
0x10    reset_camera_y_axis
0x11    cinematic_effects
0x12    unknown (always 0)
0x13    cross_region_play
0x14    voice_chat
0x15    display_player_names
0x16    manual_attack_aim
0x17    autotarget
──────────────────────────────────────────────────────────────────────
```

**PCOptionData - 0xB2 bytes (PC only):** keyboard bindings. 0x00-0x11 is a header (default
`00 05 d0 02 00 00 1e 05`, then zeros), followed by 40 entries of `uint16 key, uint16 flag` where `key` is a
Windows virtual-key code (`0x57` W, `0x53` S, `0x44` D, `0x41` A, `0x60`-`0x67` numpad, `0x25`-`0x28`
arrows, ...). The action order and the meaning of `flag` (0 or 4) are unknown.

**ProfileSummary - 0x1702 bytes:** 10 x uint8 `active_profiles` (1 = slot in use), then 10 x Profile.

**Profile - 0x24C (588 bytes) per slot:**

```
Offset  Size   Field
──────────────────────────────────────────────────
0x00    32     character_name (UTF-16LE, 16 chars)
0x20    2      terminator
0x22    4      level (uint32)
0x26    4      seconds_played (uint32)
0x2A    4      runes_memory (uint32)
0x2E    4      map_id (MapId)
0x32    4      place_name_id (PlaceName text id of the load screen location)
0x36    0x124  face_data
0x15A   0xE8   equipment (see below)
0x242   1      body_type
0x243   1      archetype
0x244   1      starting_gift
0x245   7      constant 00 00 01 00 00 00 00
──────────────────────────────────────────────────
0x24C          total
```

**Profile equipment - 0xE8 bytes (58 uint32):**

```
Word   Field
──────────────────────────────────────────────────────────────────────
0      -1
1      0
2-8    ActiveWeaponSlotsAndArmStyle (same 7 values as the slot)
9-30   22 equipment slots as tagged ids: weapons 0x80000000 | (id & 0x7FFFFF),
       armor 0x90000000 | id, talismans 0xA0000000 | id, 0 if empty
31-52  22 equipment slots as item ids (same order and values as
       equipped_items_item_id)
53-54  -1, or both 69000000 / 69001000 / 69100000 (meaning unknown)
55-57  0
──────────────────────────────────────────────────────────────────────
```

ProfileSummary is the load screen copy of each character. On every write the manager rebuilds the entry of
each edited slot from the slot itself (`parser/profile_sync.py`): name, level, play time (`play_time_ms` / 1000),
runes memory, map, equipment words 2-52, body type, class and starting gift. `place_name_id` and equipment
words 0-1 and 53-57 are kept. The profile's FACE block is only filled from the slot when the profile has
none: the game writes the eye colors and the frenzied flame byte differently into the two copies.

---

## USER_DATA_11

Located at `0x19603B0` (PC). Size: `0x240020` bytes. MD5 checksum at the start (PC only) over the
following `0x240010` bytes, which hold the game regulation data (item stats, scaling, balance). Not
edited by the save editor, so its checksum is never recalculated.

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
| UD11    | `0x19603B0`| `0x19603C0`| `0x240010`|

---

[← Back to Home](../index.md)