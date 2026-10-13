# Save File Structure

Technical reference for the Elden Ring save file.

- All values are little-endian.
- Offsets inside a character slot are relative to the start of the character data (after the PC checksum).
- The slot is one sequential structure with several variable-length blocks. A fixed offset is only valid up
  to the first variable block; everything after it has to be located by reading the slot in order.
- Field names are the parser's names. `unk` fields are not understood; their observed values are given.

---

## Contents

- [File layout](#file-layout)
- [Character slot](#character-slot)
- [PlayerGameData](#playergamedata)
- [Item and equipment blocks](#item-and-equipment-blocks)
- [Appearance (FaceData)](#appearance-facedata)
- [Gestures and regions](#gestures-and-regions)
- [Torrent, bloodstain and menu data](#torrent-bloodstain-and-menu-data)
- [Item history and tutorials](#item-history-and-tutorials)
- [Event flags](#event-flags)
- [World state blocks](#world-state-blocks)
- [Position](#position)
- [NetMan](#netman)
- [Slot tail](#slot-tail)
- [USER_DATA_10](#user_data_10)
- [USER_DATA_11](#user_data_11)
- [Checksums](#checksums)
- [Writing a save](#writing-a-save)

---

## File layout

The PC file is a BND4 archive with 12 entries: ten character slots, USER_DATA_10 (global data) and
USER_DATA_11 (regulation). Total size 28,967,888 bytes (0x1BA03D0).

| File offset | Size | Content |
|---|---|---|
| 0x0 | 0x40 | BND4 header |
| 0x40 | 12 x 0x20 | entry table |
| 0x1C0 | | entry names (UTF-16, `USER_DATA000` to `USER_DATA011`) |
| 0x300 + k x 0x280010 | 0x280010 | slot k (k = 0-9): MD5, then 0x280000 bytes of character data |
| 0x19003A0 | 0x60010 | USER_DATA_10: MD5, then 0x60000 bytes |
| 0x19603B0 | 0x240020 | USER_DATA_11: MD5, then regulation data |

**BND4 header:**

| Offset | Type | Value |
|---|---|---|
| 0x00 | char[4] | `BND4` |
| 0x0C | uint32 | entry count (12) |
| 0x10 | uint64 | header size (0x40) |
| 0x18 | char[8] | version string `00000001` |
| 0x20 | uint64 | entry header size (0x20) |
| 0x28 | uint64 | data start (0x300) |
| 0x30 | uint8 | 1 (UTF-16 names) |

**Entry header (0x20 bytes):**

| Offset | Type | Field |
|---|---|---|
| 0x00 | uint32 | flags (0x50) |
| 0x04 | int32 | -1 |
| 0x08 | uint64 | entry size (0x280010 for slots, 0x60010, 0x240020) |
| 0x10 | uint32 | file offset of the entry data |
| 0x14 | uint32 | file offset of the entry name |
| 0x18 | uint64 | 0 |

### PlayStation

PlayStation saves (exported `memory.dat`) are not a BND4 archive:

| | PC | PlayStation |
|---|---|---|
| Magic | `42 4E 44 34` (`BND4`) | `CB 01 9C 2C` |
| Header | 0x300 bytes | 0x70 bytes |
| Slot size | 0x10 MD5 + 0x280000 | 0x280000, no checksum |
| Slot k | 0x300 + k x 0x280010 | 0x70 + k x 0x280000 |
| USER_DATA_10 | MD5 + 0x60000 | 0x60000, no checksum, no PCOptionData |
| SteamID in slots | account Steam64 | 0 |

Everything inside a slot is identical on both platforms.

---

## Character slot

A slot is empty when `version` (its first uint32) is 0. The checksum does not mark empty slots: an empty
slot carries the MD5 of its data like any other.

Fields in file order:

| Field | Type | Size |
|---|---|---|
| version | uint32 | 4 |
| map_id | MapId | 4 |
| play_time_ms | uint64 | 8 |
| unk0x10 | bytes | 16 |
| gaitem_map | Gaitem[5118 or 5120] | variable |
| player_game_data | PlayerGameData | 0x1B0 |
| sp_effects | SPEffect[13] | 0xD0 |
| equipped_items_equip_index | EquipmentSlots | 0x58 |
| active_weapon_slots_and_arm_style | ActiveWeaponSlotsAndArmStyle | 0x1C |
| equipped_items_item_id | EquipmentSlots | 0x58 |
| equipped_items_gaitem_handle | EquipmentSlots | 0x58 |
| inventory_held | Inventory | 0x9010 |
| equipped_spells | EquippedSpells | 0x74 |
| equipped_items | EquippedItems | 0x8C |
| equipped_gestures | uint32[6] | 0x18 |
| acquired_projectiles | AcquiredProjectiles | variable |
| equipped_armaments_and_items | EquippedArmamentsAndItems | 0x9C |
| equipped_physics | EquippedPhysics | 0xC |
| face_data | FaceData | 0x12F |
| inventory_storage_box | Inventory | 0x6010 |
| gestures | uint32[64] | 0x100 |
| unlocked_regions | Regions | variable |
| horse | RideGameData | 0x28 |
| control_byte_maybe | uint8 | 1 |
| blood_stain | BloodStain | 0x44 |
| unk_gamedataman_0x120_or_gamedataman_0x130 | uint32 | 4 |
| unk_gamedataman_0x88 | uint32 | 4 |
| menu_profile_save_load | MenuSaveLoad | variable |
| trophy_equip_data | TrophyEquipData | 0x34 |
| gaitem_game_data | GaitemGameData | 0x1B588 |
| tutorial_data | TutorialData | variable |
| gameman_0x8c, 0x8d, 0x8e | uint8 x 3 | 3 |
| total_deaths_count | uint32 | 4 |
| character_type | int32 | 4 |
| in_online_session_flag | uint8 | 1 |
| character_type_online | uint32 | 4 |
| last_rested_grace | uint32 | 4 |
| not_alone_flag | uint8 | 1 |
| in_game_countdown_timer | uint32 | 4 |
| unk_gamedataman_0x124_or_gamedataman_0x134 | uint32 | 4 |
| event_flags | bytes | 0x1BF99F |
| event_flags_terminator | uint8 | 1 |
| field_area | FieldArea | variable |
| world_area | WorldArea | variable |
| world_geom_man | WorldGeomMan | variable |
| world_geom_man2 | WorldGeomMan | variable |
| rend_man | RendMan | variable |
| player_coordinates | PlayerCoordinates | 0x3D |
| game_man_0x5be, 0x5bf | uint8 x 2 | 2 |
| spawn_point_entity_id | uint32 | 4 |
| game_man_0xb64 | uint32 | 4 |
| temp_spawn_point_entity_id | uint32 (version >= 65) | 4 or 0 |
| game_man_0xcb3 | uint8 (version >= 66) | 1 or 0 |
| net_man | NetMan | 0x20004 |
| world_area_weather | WorldAreaWeather | 0xC |
| world_area_time | WorldAreaTime | 0xC |
| base_version | BaseVersion | 0x10 |
| steam_id | uint64 | 8 |
| ps5_activity | uint8[32] | 0x20 |
| dlc | DLC | 0x32 |
| player_data_hash | PlayerGameDataHash | 0x80 |
| rest | bytes | to 0x280000 |

The gaitem map has 5118 entries when `version <= 81`, 5120 otherwise. `rest` is leftover serializer
buffer: it is never read by the game and absorbs size changes of the blocks before it.

**MapId** (used throughout): 4 bytes `[DD, CC, BB, AA]` naming map `mAA_BB_CC_DD`. `00 24 2A 3C` is
`m60_42_36_00`.

**Scalar fields:**

| Field | Meaning |
|---|---|
| map_id | map the character is in (load screen map) |
| play_time_ms | play time in milliseconds |
| unk0x10 | 16 bytes rewritten with a new value whenever the game writes the slot; not a digest of the slot |
| control_byte_maybe | unknown |
| unk_gamedataman_0x120_or_gamedataman_0x130 | NG+ cycle (0 = first playthrough) |
| unk_gamedataman_0x88 | always 0 |
| gameman_0x8c-0x8e | unknown |
| total_deaths_count | deaths |
| character_type | -1 by default |
| character_type_online | 8 by default |
| last_rested_grace | BonfireWarpParam `bonfireEntityId` + 1000 of the last grace rested at, 0 if none |
| unk_gamedataman_0x124_or_gamedataman_0x134 | random 0-99, rerolled on every area load |
| game_man_0x5bf | 1 after warping to a grace, 0 after resting at one |
| spawn_point_entity_id | entity id the character respawns at |
| game_man_0xb64 | 0, or a spawn point entity id |
| game_man_0xcb3 | 0 or 1, unknown |

---

## PlayerGameData

0x1B0 bytes: the in-memory `CS::PlayerGameData` from its offset 0x8.

| Offset | Size | Field | Notes |
|---|---|---|---|
| 0x00 | 4 | unk0x0 | |
| 0x04 | 4 | unk0x4 | |
| 0x08 | 4 | hp | |
| 0x0C | 4 | max_hp | |
| 0x10 | 4 | base_max_hp | |
| 0x14 | 4 | fp | |
| 0x18 | 4 | max_fp | |
| 0x1C | 4 | base_max_fp | |
| 0x20 | 4 | unk0x20 | |
| 0x24 | 4 | sp | stamina |
| 0x28 | 4 | max_sp | |
| 0x2C | 4 | base_max_sp | |
| 0x30 | 4 | unk0x30 | |
| 0x34 | 4 x 8 | vigor, mind, endurance, strength, dexterity, intelligence, faith, arcane | |
| 0x54 | 4 | unk0x54 | |
| 0x58 | 4 | unk0x58 | |
| 0x5C | 4 | unk0x5c | humanity, always 0 |
| 0x60 | 4 | level | |
| 0x64 | 4 | runes | runes held |
| 0x68 | 4 | runes_memory | total runes ever gained |
| 0x6C | 4 | unk0x6c | |
| 0x70 | 4 x 7 | poison, rot, bleed, death, frost, sleep, madness buildup | |
| 0x8C | 4 | unk0x8c | |
| 0x90 | 4 | unk0x90 | character type, 0 |
| 0x94 | 32 | character_name | UTF-16LE, 16 characters |
| 0xB4 | 2 | terminator | |
| 0xB6 | 1 | gender | body type |
| 0xB7 | 1 | archetype | starting class |
| 0xB8 | 1 | unk0xb8 | "appearance", 0 |
| 0xB9 | 1 | unk0xb9 | |
| 0xBA | 1 | voice_type | |
| 0xBB | 1 | gift | starting keepsake |
| 0xBC | 1 | unk0xbc | |
| 0xBD | 1 | memory_stone_count | Memory Stones used, 0-8 |
| 0xBE | 1 | additional_talisman_slot_count | |
| 0xBF | 1 | summon_spirit_level | spirit ash upgrade level |
| 0xC0 | 4 | online session count | +1 per online session: co-op host, summoned phantom, invasion |
| 0xC4 | 4 | unknown counter | grows with play time, not changed by online sessions |
| 0xC8 | 16 | unknown | almost always 0 |
| 0xD8 | 1 | furl_calling_finger_on | |
| 0xD9 | 1 | unk0xd9 | |
| 0xDA | 1 | matchmaking_weapon_level | highest weapon upgrade reached |
| 0xDB | 1 | white_cipher_ring_on | |
| 0xDC | 1 | blue_cipher_ring_on | |
| 0xDD | 23 | unk0xdd | |
| 0xF4 | 1 | scadutree_blessing | 0-20 |
| 0xF5 | 1 | revered_spirit_ash_blessing | 0-10 |
| 0xF6 | 1 | unk0xf6 | |
| 0xF7 | 1 | great_rune_on | Great Rune activated with a Rune Arc; cleared on death |
| 0xF8 | 1 | unk0xf8 | |
| 0xF9 | 1 | max_crimson_flask_count | |
| 0xFA | 1 | max_cerulean_flask_count | |
| 0xFB | 13 | unk0xfb | |
| 0x108 | 4 | saved HP | written when the character leaves for another world (summoned or invading) |
| 0x10C | 4 | saved FP | written together with 0x108 |
| 0x110 | 18 | password | multiplayer password, UTF-16LE, 8 characters + terminator |
| 0x122 | 18 x 5 | group_password1-5 | |
| 0x17C | 3 | unknown | crimson / cerulean charges and a flag; 0x17C changes together with 0x108 |
| 0x17F | 49 | unknown | 0x180 and 0x184 hold small values |

**Runes memory:** the game only ever adds to `runes_memory`, so a consistent character satisfies
`runes_memory >= cost(class start level -> level) + runes`. The cost of level L to L + 1 is
`int((x + 0.1) * (L + 81)^2) + 1` with `x = max(0, (L - 11) * 0.02)`. The class start level is the level of
the CharaInitParam row of `archetype`.

### SPEffect (16 bytes, 13 entries)

| Offset | Type | Field |
|---|---|---|
| 0x00 | int32 | sp_effect_id |
| 0x04 | float | remaining_time |
| 0x08 | uint32 | 0 |
| 0x0C | uint32 | 0 |

An entry is active when `sp_effect_id != 0` and `remaining_time > 0`.

---

## Item and equipment blocks

### Gaitem (8, 16 or 21 bytes)

The item instance table. Entry size depends on the handle, so the table has to be read in order.

| Offset | Size | Field | Present for |
|---|---|---|---|
| 0x00 | 4 | gaitem_handle | all |
| 0x04 | 4 | item_id | all |
| 0x08 | 4 | unk0x10 | weapons and armor (0) |
| 0x0C | 4 | unk0x14 | weapons and armor (0) |
| 0x10 | 4 | gem_gaitem_handle | weapons: handle of the equipped Ash of War |
| 0x14 | 1 | unk0x1c | weapons |

| Handle top nibble | Kind | Entry size |
|---|---|---|
| handle 0 | empty | 8 |
| 0x8 | weapon | 21 |
| 0x9 | armor | 16 |
| 0xC | Ash of War | 8 |

**Handle bits:** 28-31 category, 16-23 generation (0x80-0xFF, +1 every time the index wraps), 0-15 index into
the game's gaitem array. The index is below 0x1400 and unique across categories; an index of 0x1400 or more
crashes the game on load. Talismans and goods have no gaitem entry: their handle is the item id with the
category nibble 0xA (talisman) or 0xB (goods).

`gem_gaitem_handle` points to the Ash of War's own 0xC entry; that entry does not point back.

**Item ids:** a weapon id is `base + upgrade`, with the affinity in `(id // 100) % 100`. Armor ids carry
`0x10000000`, talismans `0x20000000`, goods `0x40000000`, Ashes of War `0x80000000` where a category tag is
used.

### Inventory

Held inventory and storage box share the layout:

| Field | Type | Held | Storage |
|---|---|---|---|
| common_item_count | uint32 | | |
| common_items | InventoryItem[] | 0xA80 | 0x780 |
| key_item_count | uint32 | | |
| key_items | InventoryItem[] | 0x180 | 0x80 |
| equip_index_counter | uint32 | | |
| acquisition_index_counter | uint32 | | |

**InventoryItem (12 bytes):** `uint32 gaitem_handle` (0 = empty), `uint32 quantity`, `uint32 acquisition_index`.

- The counts are the number of occupied entries.
- `equip_index_counter` is the highest entry index in use: key items use 0 to len(key) - 1, common items
  len(key) + position. The game never goes above 3071 (held) or 2047 (storage).
- New acquisition indices are `max(highest index in both inventories, acquisition_index_counter) + 1`. The
  game renumbers all acquisition indices by a constant on every save.
- The list (key or common) an item sits in does not always follow its item classification.

### EquipmentSlots (0x58)

Three parallel copies: inventory index, item id and gaitem handle per slot.

| Offset | Slot | Offset | Slot |
|---|---|---|---|
| 0x00 | left hand 1 | 0x30 | head |
| 0x04 | right hand 1 | 0x34 | chest |
| 0x08 | left hand 2 | 0x38 | arms |
| 0x0C | right hand 2 | 0x3C | legs |
| 0x10 | left hand 3 | 0x40 | hair (unused) |
| 0x14 | right hand 3 | 0x44 | talisman 1 |
| 0x18 | arrows 1 | 0x48 | talisman 2 |
| 0x1C | bolts 1 | 0x4C | talisman 3 |
| 0x20 | arrows 2 | 0x50 | talisman 4 |
| 0x24 | bolts 2 | 0x54 | talisman 5 (unused) |
| 0x28 | arrows 3 (unused) | | |
| 0x2C | bolts 3 (unused) | | |

### ActiveWeaponSlotsAndArmStyle (0x1C)

Seven uint32: `arm_style`, active left weapon slot, active right weapon slot, left arrow slot, right
arrow slot, left bolt slot, right bolt slot.

### EquippedSpells (0x74)

14 x `(uint32 spell_id, int32 unk)` (unk is -1 on filled slots, 0 on empty ones), then `uint32 active_index`.

### EquippedItems (0x8C)

| Offset | Size | Field |
|---|---|---|
| 0x00 | 10 x 8 | quick items: (gaitem_handle, equip_index) |
| 0x50 | 4 | active quick item index |
| 0x54 | 6 x 8 | pouch items |
| 0x84 | 4 | great_rune: goods handle `0xB0000000 \| id` (goods 191-196), 0 if none |
| 0x88 | 4 | great_rune_equip_index: key item index, -1 if none |

The equipped Great Rune is only active while `PlayerGameData.great_rune_on` is set.

### Gesture wheel (0x18)

Six uint32, one per wheel slot. See [Gestures and regions](#gestures-and-regions) for the encoding.

### AcquiredProjectiles (variable)

The chest auto-refill settings: `uint32 count`, then `count` x `(uint32 id, uint32 auto_replenish)`. `id` is
an ammo weapon id or `0x40000000 | goods id`; `auto_replenish` 1 means auto-refill ON. Every ammo or goods
item the character has obtained whose EquipParamGoods `autoReplenishType` is 1 (default off) or 2 (default on)
has an entry.

### EquippedArmamentsAndItems (0x9C)

The 22 slots of EquipmentSlots as item ids (0x00-0x57), 10 quick items (0x58), 6 pouch items (0x80) and
an int32 at 0x98 (always -1).

### EquippedPhysics (0xC)

Wondrous Physick tears: slot 1, slot 2, int32 -1.

---

## Appearance (FaceData)

0x12F bytes. The `FACE` block uses the same layout as the USER_DATA_10 appearance presets
(`FacePreset`, whose field names such as `unk0x14` are offsets from the `FACE` magic).

| Offset | Size | Field |
|---|---|---|
| 0x000 | 4 | marker (-1) |
| 0x004 | 4 | magic `FACE` |
| 0x008 | 4 | uint32 4 |
| 0x00C | 4 | uint32 block size (0x120) |
| 0x010 | 32 | 8 model ids (uint8 + 3 padding each): face, hair, eye, eyebrow, beard, accessory, decal, eyelash |
| 0x030 | 64 | facial structure sliders |
| 0x070 | 64 | FaceGen parameters not exposed in character creation (128 or 0; 0x070 and 0x08E vary) |
| 0x0B0 | 7 | body scale: head, chest, abdomen, right arm, right leg, left arm, left leg |
| 0x0B7 | 91 | colors: skin, cosmetics, tattoo, body hair, eyes, hair, beard, eyebrows, eyelashes, accessory |
| 0x112 | 1 | eye effect (255 = Frenzied Flame); only set in the ProfileSummary copy |
| 0x113 | 17 | padding |
| 0x124 | 1 | uint8 1 |
| 0x125 | 2 | 2 x uint8 0/1, unknown |
| 0x127 | 4 | int32 face param override slot 0 (FaceParam id, -1 = none) |
| 0x12B | 4 | int32 face param override slot 1 (FaceParam id, -1 = none) |

The preset field `unk0xb1` (2 bytes) holds the left arm and left leg scale.

**Face param overrides** are set by the EMEVD instruction Set Character Face Param Override. common.emevd
event 1800 sets slot 0 together with event flag 9420; event 1801 sets slot 1 to 80000 together with flag
9421 once flag 9430 is set. The slot 0 id depends on the first flag that is set:

| Flag | Source | Slot 0 | Load screen eyes |
|---|---|---|---|
| 9431 | accepting the Frenzied Flame | 81000 | eye model 10, eye effect 255 |
| 9432 | White Mask Varre's quest | 81001 | unchanged |
| 9433 | common event 3080 (4 of flags 290500-290999) | 81002 | eye model 11 |

Accepting the Frenzied Flame sets 9430 and 9431 together (both overrides) and flag 108. common.emevd
event 920 clears 9431. The slot `FACE` block keeps the base appearance; the game applies the override when
drawing the character, and only the ProfileSummary copy holds the result.

---

## Gestures and regions

Gestures are numbered by an index k (0 = Bow, 7 = Wave, 20 = Point Forwards, ...). The gesture id used in
the gesture table is `2k + 1` (1 Bow, 15 Wave, 41 Point Forwards). Each structure stores it differently:

| Structure | Stored value |
|---|---|
| gestures (unlocked list, 64 x uint32) | `2k` or `2k + 1` (low bit unknown), -2 = empty |
| equipped_gestures (wheel) | `2k`, -2 = empty |
| message gesture (NetMan) | `k`, 0xFF = none |

**Regions:** `uint32 count`, then `count` region ids (1001000, 1800010, 6100000, ...).

---

## Torrent, bloodstain and menu data

### RideGameData (0x28)

| Offset | Type | Field |
|---|---|---|
| 0x00 | float[3] | coordinates |
| 0x0C | MapId | map_id |
| 0x10 | float[4] | angle |
| 0x20 | int32 | hp |
| 0x24 | uint32 | state: 1 inactive, 3 dead, 13 active |

`hp == 0` with `state == 13` causes an infinite loading screen; state 3 fixes it.

### BloodStain (0x44)

Same layout as the in-memory bloodstain at GameDataMan+0x48.

| Offset | Type | Field |
|---|---|---|
| 0x00 | float[3] | coordinates |
| 0x0C | float[4] | angle |
| 0x1C | uint32 x 5 | unknown; 0, or values with 0x24 = 0x2C and 0x28 = 1 |
| 0x30 | int32 | 0 while a bloodstain exists, -1 otherwise |
| 0x34 | int32 | runes (-1 = none) |
| 0x38 | MapId | map_id |
| 0x3C | uint32 | 0, or unknown values |
| 0x40 | uint32 | unknown; a death writes `0x8FF0 << 16 \| n` with n different per death location. Other values: -1, 0, `0x0FF0xxxx` and values with a high half below 0x200 |

On death the game writes position, angle, map, runes and 0x40, and sets 0x30 to 0. Recovering the runes
sets 0x30 and runes back to -1 and keeps the other fields.

### MenuSaveLoad (variable)

Outer header `uint16 0, uint16 0, uint32 size`, then `size` bytes of data (0x1000; 0 with no data on some
level 1 characters). The data starts with a nested chunk header `uint16 1, uint16 version, uint32 size`
(version 2 / size 0xFDC; older characters version 0 / 0xF10, followed by the terminator chunk at 0xF18).
Version 2 offsets below are from the start of the data, after the outer header, so
data+0x000..0x007 is the nested header and 0x008 is its first field:

| Offset | Content |
|---|---|
| 0x008 | 2 x (float, float), unknown |
| 0x018 | uint32, unknown |
| 0x108 | 10 beacon records |
| 0x1A8 | 100 map marker records |
| 0x7E8 | int64, -2 or -1 |
| 0x7F0 | 0x7E0 bytes up to 0xFD0, unknown |
| 0xFD0 | 2 x float: world map cursor position (x, y) |
| 0xFD8 | 8 bytes, 0 |
| 0xFE0 | uint8 0 or 1, then 3 bytes of uninitialized memory (last field of the nested chunk) |
| 0xFE4 | terminator chunk: `uint16 0xFFFF, uint16 0, uint32 0`; zero up to 0x1000 |

**Beacon / marker record (16 bytes):**

| Offset | Type | Field |
|---|---|---|
| 0x00 | int32 | id (-1 = empty); beacons use an increasing sequence number |
| 0x04 | float | x on the world map |
| 0x08 | float | y on the world map |
| 0x0C | uint8 | map: 0 Lands Between, 10 Realm of Shadow |
| 0x0D | uint8 | marker icon (1 for beacons and empty records) |
| 0x0E | uint16 | 0, or 0xFFFF on a newly placed beacon |

---

## Item history and tutorials

### TrophyEquipData (0x34)

| Offset | Size | Field |
|---|---|---|
| 0x00 | 4 | 0 |
| 0x04 | 16 | legendary_weapons |
| 0x14 | 16 | legendary_goods |
| 0x24 | 16 | legendary_talismans |

Progress of the "Legendary" trophies: one bit per legendary item ever acquired (kept after selling or
discarding), bit n = n-th item of the type in ascending id order.

- Weapons: Sword of Night and Flame, Dark Moon Greatsword, Marais Executioner's Sword, Golden Order
  Greatsword, Ruins Greatsword, Grafted Blade Greatsword, Eclipse Shotel, Devourer's Scepter, Bolt of Gransax.
- Goods: bits 0-6 Comet Azur, Founding Rain of Stars, Stars of Ruin, Ranni's Dark Moon, Flame of the Fell
  God, Elden Stars, Greyoll's Roar; bits 7-12 Black Knife Tiche, Mimic Tear, Cleanrot Knight Finlay, Ancient
  Dragon Knight Kristoff, Redmane Knight Ogha, Lhutel the Headless.
- Talismans: Erdtree's Favor +2, Radagon's Soreseal, Moon of Nokstella, Marika's Soreseal, Old Lord's
  Talisman, Radagon Icon, Godfrey Icon, Dragoncrest Greatshield Talisman.

### GaitemGameData (0x1B588)

Every item type the character has ever acquired: `int64 count`, then 14000 entries of 8 bytes
(`uint32 item_id`, `uint8 1`, 3 bytes padding). The first `count` entries are live and sorted by item id;
the rest hold stale data. Slots written by older game versions (slot version 151 and below) use the same
0x1B580 bytes as 7000 records of 16 bytes: `uint32 item_id`, `uint8 1`, 3 bytes (`FF FF FF` or 0),
`uint32` unknown, `uint32` unknown; `count` is then the number of 16-byte records. `item_id` carries the category tag: weapons as base id, armor `0x10000000 |`,
talismans `0x20000000 |`, goods `0x40000000 |`, Ashes of War `0x80000000 |`.

### TutorialData (variable)

`uint16 174, uint16 1, uint32 size (0x400)`, then `uint32 count` and TutorialParam row ids of the
tutorial pop-ups already shown (the first `count` are live). 174 and 1 are constant, most likely a block
type and version (the same header shape as KeyConfigSaveLoad and MenuSaveLoad).

---

## Event flags

0x1BF99F bytes followed by one terminator byte. Flags are grouped in blocks of 1000 flags (125 bytes).
Where a block is stored comes from the game's CSFD4VirtualMemoryFlag tree, shipped as
`eventflag_bst.txt` (one line per block: `block,position`).

For flag N:

1. `block = N // 1000`, `index = N % 1000`
2. `byte = bst[block] * 125 + index // 8`
3. `bit = 7 - index % 8` (the lowest flag of a byte is the most significant bit)

A block that is not in the tree has no storage.

**Flag semantics:**

| Flags | Meaning |
|---|---|
| NPC base .. base+19 | each NPC owns a 20-flag block: base..base+4 life state (one at a time, dead = base+3), base+5..base+17 location and quest state, base+18 init latch. Quest progress is skipped while base is off |
| boss defeat | first flag of each boss entry; reward pickup flags are separate |
| ItemLotParam `getItemFlagId` | item pickup collected |
| ShopLineupParam `eventFlag_forStock` | purchase counter: `bit_length(sellQuantity)` flags, LSB first, value = number bought; clearing them restocks the item |
| 6080 | first entry to a colosseum |
| 9420, 9421, 9430-9433 | face param overrides (see [FaceData](#appearance-facedata)) |
| 9800-9809 | exactly one is set, picked at random by common.emevd event 980; used to choose between alternative NPC placements |

DLC NPC blocks: Igon 4260, St. Trina 4280, Priestess 4300, Jolan 4320, Queelign 4340, Hornsent 4360, Moore
4380, Ansbach 4400, Freyja 4420, Leda 4440, Thiollier 4460, Grandam 4480, Ymir 4500, Dane 4560. Kenneth
Haight is 3580; Irina and Hyetta share 3380.

---

## World state blocks

FieldArea, WorldArea, WorldGeomMan, WorldGeomMan2 and RendMan follow the event flags. Each is
`int32 size` followed by `size` bytes; a size of 0 means no data. FieldArea and WorldArea are at most
0x10000 bytes, the others at most 0x100000.

| Block | Magic | Content | Maps covered | On rest |
|---|---|---|---|---|
| FieldArea | none | dungeon to open world tile adjacency | | |
| WorldArea | `CHR ` | enemy parts in a non-default state | maps loaded around the player | kills are dropped; event-driven entries are written again on load |
| WorldGeomMan | `MOEG` | broken and picked up assets | maps loaded around the player | states 1 and 3 are dropped, state 2 kept |
| WorldGeomMan2 | `FOEG` | permanently picked up one-time nodes | every map ever visited | unchanged |
| RendMan | none | ground decals | around the player | |

WorldArea and WorldGeomMan records exist only while the map is loaded, including records with no entries.
Open world LOD tiles (`m60_XX_YY_01`, `_02`) get records too: an asset placed on a coarser tile is stored
under that tile. Every entry names a part in the map's MSB (`map/mapstudio/<map>.msb`).

### FieldArea

`uint32 count`, then `count` x `(MapId map, uint32 n, n x MapId)`: a dungeon or legacy dungeon and the open
world tiles next to it. `count` is usually 0.

### WorldArea (CHR)

| Offset | Type | Field |
|---|---|---|
| 0x00 | char[4] | `CHR ` |
| 0x04 | uint32 | version (0x21042700) |
| 0x08 | uint64 | 0 |
| 0x10 | | records, then the terminator record |

**Record** (size a multiple of 16):

| Offset | Type | Field |
|---|---|---|
| 0x00 | char[4] | `CSBC` |
| 0x04 | MapId | map (0xFFFFFFFF = terminator) |
| 0x08 | uint32 | record size: align16(16 + 4n) |
| 0x0C | uint32 | `enemy_part_count << 14 \| n` |
| 0x10 | uint32[n] | entries, then zero padding |

`enemy_part_count` is the number of enemy parts in the map's MSB. The terminator is `CSBC FF FF FF FF` and
8 zero bytes.

**Entry (uint32):** bits 0-1 state (3 = killed or disabled; 1 and 2 are rare and not understood), bits 2-15
MSB part instance, bits 16-29 character model, bit 30 always 1. `0x50D78CAB` is `c4311_9002` in state 3.

Entries are regular enemies killed since the last rest plus parts kept dead or disabled by map events
(defeated field bosses, NPCs that are elsewhere). Kills are dropped when the player rests; event-driven
entries, including every part of a defeated boss, are written again whenever the map loads.

### WorldGeomMan (MOEG) and WorldGeomMan2 (FOEG)

| Offset | Type | Field |
|---|---|---|
| 0x00 | char[4] | `MOEG` or `FOEG` |
| 0x04 | uint32 | version (0x21042600) |
| 0x08 | | records, then a terminator record (`FF FF FF FF` + 12 zero bytes) |

**Record:**

| Offset | Type | Field |
|---|---|---|
| 0x00 | MapId | map (0xFFFFFFFF = terminator) |
| 0x04 | uint32 | record size (16 + 8n) |
| 0x08 | uint32 | n |
| 0x0C | uint32 | per-map constant, unknown |
| 0x10 | 8n | entries |

**Entry:** `uint32 key = instance << 15 | state`, `uint32 model = 10000000 + AEG id` (AEG id = AssetEnvironmentGeometryParam
row, `AEGxxx_yyy` = xxx * 1000 + yyy). Key `0x11940003` with model 10099720 is `AEG099_720_9000`.

| Block | State | Meaning |
|---|---|---|
| WorldGeomMan | 1 | asset broken |
| WorldGeomMan | 3 | picked up since the last rest |
| WorldGeomMan | 2 | picked up permanently (a one-time node's state 3 becomes 2 on rest) |
| WorldGeomMan2 | 1 | picked up permanently |

Permanent pickups are the assets with a `pickUpItemLotParamId` and `isEnableRepick = 1` in
AssetEnvironmentGeometryParam: Arteria Leaf, smithing and somber smithing stones, Grave and Ghost
Glovewort, Trina's and Miquella's Lily, butterflies, Golden Centipede, Formic Rock and the DLC equivalents.
Other pickups (Rowa Fruit, Erdleaf Flower, ...) respawn and only appear in WorldGeomMan in state 3.

| Action | WorldArea | WorldGeomMan | WorldGeomMan2 |
|---|---|---|---|
| Kill a regular enemy | entry added, state 3 | | |
| Break a crate | | entry added, state 1 | |
| Pick a respawning plant | | entry added, state 3 | |
| Pick a one-time node | | entry added, state 3 | entry added, state 1 |
| Rest | kills dropped | states 1 and 3 dropped, 3 of one-time nodes becomes 2 | unchanged |

### RendMan

`uint32 count`, then `count` decals of 40 bytes:

| Offset | Type | Field |
|---|---|---|
| 0x00 | uint32 | DecalParam row |
| 0x04 | int16[9] | three points (x, y, z) in 1/8 units, local to the player's map |
| 0x16 | uint16 | 0 |
| 0x18 | uint32[4] | unknown (the first three are equal on point decals) |

Persistent decals around the player: blood (445000, 610003), black liquid (442204, 443400), burn marks
(442600), point trails (3000xxxxx, one point repeated) and triangles (6001xxxxx).

---

## Position

### PlayerCoordinates (0x3D)

| Offset | Type | Field |
|---|---|---|
| 0x00 | float[3] | coordinates |
| 0x0C | MapId | map_id |
| 0x10 | float[4] | angle |
| 0x20 | uint8 | game_man_0xbf0 |
| 0x21 | float[3] | unk_coordinates |
| 0x2D | float[4] | unk_angle |

On `m60` / `m61` the coordinates are local to the small (`_00`) tile; the global position is
`tile * 256 + 128 + local` per axis. `unk_coordinates` / `unk_angle` are a second position without a map
id that dying, warping and resting do not change.

---

## NetMan

0x20004 bytes: `uint32 2`, then 0x20000 bytes holding a chain of chunks. Each chunk is
`uint16 type, uint16 version, uint32 size, size bytes`; the chain ends with a type 0xFFFF chunk of size 0
and the rest of the buffer is zero.

| Type | Version | Content |
|---|---|---|
| 2 | 0 | empty list |
| 5 | 0 | empty list |
| 6 | 2 | messages |
| 8 | 0 | 12-byte header, then a list of 12-byte entries |
| 9 | 0 | empty list |
| 7 | 1 | empty list |
| 0xFFFF | 0 | terminator |

Every chunk payload is a sub-entry list: `uint32 kind, uint32 size, size bytes`, padded to 4 bytes, ended by
a kind 0xFFFF entry of size 0. A chunk is intact when its list ends exactly at the chunk end. A chain that
does not reach the terminator inside the buffer is corrupt.

### Chunk 6: messages

| Kind | Size | Count | Content |
|---|---|---|---|
| 0 | 600 | up to 10 | messages written by the player |
| 1 | 606 | about 100 | other players' messages cached for the area the player is in |
| 2 | 8 (first: 12) | 10 | 8-byte ids, newest first; a new one is added when the player is summoned into another world |

Each message carries a copy of its author's character so that the author's phantom can be shown when the
message is read.

**Own message (kind 0):**

| Offset | Size | Field |
|---|---|---|
| 0x00 | 4 | uint32, the same on every message of one author, unknown |
| 0x04 | 8 | ids, unknown |
| 0x0C | 4 | MapId |
| 0x10 | 20 | unknown |
| 0x24 | 12 | position (float[3]) |
| 0x30 | 4 | angle (float) |
| 0x34 | 2 | uint16 template (BloodMsg FMG id, e.g. 10000 "<?bmsg?> ahead") |
| 0x36 | 1 | gesture index k, 0xFF = none |
| 0x37 | 1 | unknown |
| 0x38 | 4 | uint32 word (BloodMsg FMG id, e.g. 30001 "enemy"); a template with two blanks uses it in both |
| 0x3C | 4 | 0 |
| 0x40 | 4 | 2 x uint16: 0 on a new message, growing later; likely the ratings received |
| 0x44 | 2 | 0 |
| 0x46 | 1 | protected (1 = cannot be deleted) |
| 0x47 | 1 | 0 |
| 0x48 | 24 | weapon ids, EquipmentSlots order (left 1, right 1, left 2, ...) |
| 0x60 | 24 | arrow and bolt ids, -1 = none |
| 0x78 | 16 | armor ids: head, chest, arms, legs |
| 0x88 | 20 | -1, then zeros |
| 0x9C | 28 | ActiveWeaponSlotsAndArmStyle |
| 0xB8 | 0x120 | `FACE` block |
| 0x1D8 | 32 | author name (UTF-16LE) |

The equipment, weapon slots and appearance are copied from the character when the message is written.
Deleting a message removes its entry; protecting it sets 0x46. Ratings given to other players' messages
are not stored. When an 11th message is written the oldest one is removed.

**Cached message (kind 1):** author equipment first, `FACE` block at 0x74, name at 0x194 (right after the
`FACE` block), then MapId at 0x1C4, position 0x1CC, angle 0x1D8, template 0x1DC, gesture 0x1DE, word 0x1E0.
602-byte entries also occur: their part before the `FACE` block is 4 bytes shorter, which moves every
later field 4 bytes back (`FACE` at 0x70, name at 0x190). The list is refreshed during online play.

### Chunk 8

A 12-byte header (three uint32: 1, 1, then a value from 1 to 13, unknown) followed by entries of 12 bytes (`uint32 id`,
`uint32 0 or 10`, 4 flag bytes). The set of entries changes rarely; the game writes them in a different
order on each save. Meaning unknown.

---

## Slot tail

### WorldAreaWeather (0xC)

`uint16 area_id`, `uint16 weather_type`, `uint32 timer`, `uint32 0`. `area_id == 0` while the character is
in a real location indicates corruption.

### WorldAreaTime (0xC)

`uint32 hour, minute, second`: the in-game time of day (new characters start at about 08:00). Values
outside 0-23 / 0-59 are corrupt.

### BaseVersion (0x10)

| Offset | Field |
|---|---|
| 0x00 | base_version_copy (= base_version) |
| 0x04 | base_version (0 < base_version <= slot version) |
| 0x08 | is_latest_version (0 or 1) |
| 0x0C | 0 |

### SteamID (8)

The account's Steam64 on PC, 0 on PlayStation. It must match USER_DATA_10 for the game to load the slot
on PC.

### PS5Activity (0x20)

One uint8 per PlayStation 5 activity card (0 not started, 1 in progress, 2 completed), written on every
platform:

| Byte | Activity |
|---|---|
| 0 | main story (2 after Hoarah Loux) |
| 1 | Godrick the Grafted |
| 2 | Starscourge Radahn |
| 3 | Morgott, the Omen King |
| 4 | Fire Giant |
| 5 | Maliketh, the Black Blade |
| 6 | Hoarah Loux |
| 7 | Colosseum (0 or 1, follows event flag 6080) |
| 8-31 | 0 |

### DLC (0x32)

| Offset | Field |
|---|---|
| 0x00 | The Ring preorder gesture |
| 0x01 | entered Shadow of the Erdtree |
| 0x02 | Ring of Miquella preorder gesture |
| 0x03 | Tarnished Edition pack |
| 0x04 | 46 bytes, 0 |

A set byte 1 or 3 makes the slot fail to load without the matching content. Non-zero bytes in 0x04-0x31
indicate corruption.

### PlayerGameDataHash (0x80)

11 uint32 checksums followed by 0x54 bytes of uninitialized memory. The game rewrites it on every save. Each
checksum is an Adler-32 variant over little-endian bytes: `lo` starts at 1 and adds every byte, `hi` adds
`lo` after every byte, both modulo 0xFFF1, result `(lo | hi << 16) * 2`.

| Offset | Entry | Input |
|---|---|---|
| 0x00 | 0 | level (uint32) |
| 0x04 | 1 | vigor..arcane (8 x uint32) + PlayerGameData 0x54 (uint32) |
| 0x08 | 2 | archetype (uint8 as uint32) |
| 0x0C | 3 | PlayerGameData 0xB8 (1 byte) |
| 0x10 | 4 | unknown |
| 0x14 | 5 | runes held |
| 0x18 | 6 | runes memory |
| 0x1C | 7 | weapon item ids: L1, L2, L3, R1, R2, R3, arrows 1, arrows 2, bolts 1, bolts 2 |
| 0x20 | 8 | item id slots 12-15 (armor), 17-20 (talismans), 21 (talisman 5) |
| 0x24 | 9 | quick items (inputs unknown) |
| 0x28 | 10 | 14 equipped spell ids |
| 0x2C | | 0x54 bytes, uninitialized |

The hash sits at the position reached by parsing, not at the end of the slot.

---

## USER_DATA_10

0x60010 bytes at 0x19003A0 on PC. Offsets include the 16-byte checksum; on PlayStation subtract 0x10.

| Offset | Size | Field |
|---|---|---|
| 0x00 | 16 | MD5 (PC only) |
| 0x10 | 4 | version |
| 0x14 | 8 | steam_id |
| 0x1C | 0x140 | Settings |
| 0x15C | 0x1808 | MenuSystemSaveLoad (appearance presets) |
| 0x1964 | 0x1702 | ProfileSummary |
| 0x3066 | 5 | GameMan bytes |
| 0x306B | 0xB2 | PCOptionData (PC only) |
| | 8 + 0x2000 | KeyConfigSaveLoad |
| | 8 | game_man_0x118 |
| | | remainder |

The remainder (about 0x5AEE0 bytes) is leftover buffer content (random bytes or old float data) with no
structure.

Graphics options (screen mode, resolution, quality settings, ray tracing quality) are not in the save; the
game keeps them in `GraphicsConfig.xml` in the `EldenRing` folder.

### Settings (0x140)

One uint8 per option; the first 0x30 bytes are used, the rest is zero. Same order as the in-memory option
data at GameDataMan+0x58.

| Offset | Option | Offset | Option |
|---|---|---|---|
| 0x00 | camera speed | 0x18 | launch setting |
| 0x01 | controller vibration | 0x19 | send summon sign |
| 0x02 | brightness | 0x1A | unknown (default 1) |
| 0x03 | sound type | 0x1B | HDR |
| 0x04 | music volume | 0x1C | HDR brightness |
| 0x05 | sound effects volume | 0x1D | HDR maximum brightness |
| 0x06 | voice volume | 0x1E | HDR saturation |
| 0x07 | display blood | 0x1F | unknown (default 1) |
| 0x08 | subtitles | 0x20 | master volume |
| 0x09 | HUD | 0x21 | ray tracing (0 off, 1 any quality) |
| 0x0A | camera X axis | 0x22 | mark new items |
| 0x0B | camera Y axis | 0x23 | show recent items tab |
| 0x0C | toggle auto lock-on | 0x24-0x2D | 0 |
| 0x0D | camera auto wall recovery | 0x2E | show tutorials |
| 0x0E | unknown (0) | 0x2F | camera auto rotation |
| 0x0F | unknown (default 1) | | |
| 0x10 | reset camera Y axis | | |
| 0x11 | cinematic effects | | |
| 0x12 | unknown (0) | | |
| 0x13 | cross-region play | | |
| 0x14 | voice chat | | |
| 0x15 | display player names | | |
| 0x16 | manual attack aiming | | |
| 0x17 | auto-target | | |

0x03, 0x0E, 0x0F, 0x12, 0x1A and 0x1F have no option in the PC menu.

### MenuSystemSaveLoad (0x1808)

`uint16, uint16, uint32 size` (0x1800), then 15 appearance presets of 0x130 bytes, then a list of 16-byte
records (empty record: `FF FF 00 00 00 00 00 00 01 00 00 00 00 00 00 00`; meaning unknown). The block is
always 0x1808 bytes, regardless of `size`.

**Preset (0x130):** a 0x18-byte header (0x08 = 1 on a used preset, 0x09 = body type, 0x0A-0x17
uninitialized memory that changes on every save, including 0x14 where FaceData has its marker), then the
`FACE` block, 0x118 bytes long: the slot copy without its last 8 padding bytes. A preset is empty when the
`FACE` magic is missing.

### ProfileSummary (0x1702)

10 x uint8 `active_profiles` (1 = slot in use), then 10 profiles of 0x24C bytes: the load screen copy of each
character.

| Offset | Size | Field |
|---|---|---|
| 0x00 | 32 | character_name (UTF-16LE) |
| 0x20 | 2 | terminator |
| 0x22 | 4 | level |
| 0x26 | 4 | seconds_played (`play_time_ms / 1000`) |
| 0x2A | 4 | runes_memory |
| 0x2E | 4 | map_id |
| 0x32 | 4 | place_name_id (PlaceName text id of the load screen location) |
| 0x36 | 0x124 | face_data (first 0x124 bytes of FaceData, with face param overrides applied) |
| 0x15A | 0xE8 | equipment |
| 0x242 | 1 | body_type |
| 0x243 | 1 | archetype |
| 0x244 | 1 | starting_gift |
| 0x245 | 7 | `00 00 01 00 00 00 00` |

**Profile equipment (58 uint32):**

| Words | Content |
|---|---|
| 0 | -1 |
| 1 | 0 |
| 2-8 | ActiveWeaponSlotsAndArmStyle |
| 9-30 | 22 equipment slots as tagged ids: weapons `0x80000000 \| (id & 0x7FFFFF)`, armor `0x90000000 \| id`, talismans `0xA0000000 \| id`, 0 if empty |
| 31-52 | 22 equipment slots as item ids (as `equipped_items_item_id`) |
| 53-54 | -1, or the same id twice (69000000, 69001000, 69100000); meaning unknown |
| 55-57 | 0 |

### GameMan bytes (5)

Unknown.

### PCOptionData (0xB2, PC only)

A header (`00 05 d0 02 00 00 1e 05`, then zeros to 0x12), then 40 x `(uint16 key, uint16 flag)` where `key` is a
Windows virtual-key code. It does not hold the key bindings; its purpose is unknown.

### KeyConfigSaveLoad (8 + 0x2000)

`uint16 0x1F, uint16 1, uint32 size (0x2000)`, then the control bindings in KeyAssignParam row order (row =
`key` in KeyAssignMenuItemParam: 1 Move Forwards, 13 Switch Sorcery/Incantation, 22 Event Action, ...). 26
records of 20 bytes:

| Offset | Type | Field |
|---|---|---|
| 0x00 | int32 | pad key (-1 = none) |
| 0x04 | int32 | keyboard key (-1 = none) |
| 0x08 | int32 | keyboard modifier |
| 0x0C | int32 | mouse key |
| 0x10 | int32 | mouse modifier |

Binding an input that another action uses gives that action the old input. Control options follow the
bindings (offsets in the data):

| Offset | Option | Values |
|---|---|---|
| 0x208 | mouse sensitivity | 0-10, default 5 |
| 0x209 | mouse X axis | 1 normal, 0 reversed |
| 0x20A | mouse Y axis | 1 normal, 0 reversed |
| 0x20B | map menu cursor movement | 1 keyboard and mouse (default), 0 keyboard only |
| 0x20C | target changing sensitivity | default 1 |
| 0x20D | 3 bytes | 0 |
| 0x210 | device for on-screen prompts | 0 gamepad, 1 keyboard and mouse |

The rest of the 0x2000 bytes is zero.

---

## USER_DATA_11

0x240020 bytes at 0x19603B0 on PC: MD5 over the following 0x240010 bytes, which hold the regulation data.

---

## Checksums

MD5, PC only, stored in front of each character slot and both USER_DATA sections:

| Section | Checksum at | Data from | Data size |
|---|---|---|---|
| Slot k | 0x300 + k x 0x280010 | checksum + 0x10 | 0x280000 |
| USER_DATA_10 | 0x19003A0 | 0x19003B0 | 0x60000 |
| USER_DATA_11 | 0x19603B0 | 0x19603C0 | 0x240010 |

```python
import hashlib

def slot_checksum(slot_entry: bytes) -> bytes:
    return hashlib.md5(slot_entry[0x10:]).digest()
```

---

## Writing a save

- **Offsets come from the parse.** Every block after the gaitem map can move; positions must be taken
  from where the parser found them, never computed from constants.
- **Size changes shift the slot.** Growing a gaitem entry, adding inventory history or changing a world
  state block moves every later block. The slot stays 0x280000 bytes: growth is taken from `rest`,
  shrinking pads it. Afterwards the slot has to be parsed again before anything else is written.
- **Rebuilds need a faithful parse.** Re-serializing a slot from parsed fields is only safe when the slot
  round-trips byte-identical; on a misparsed slot it writes the misread structures back.
- **Keep copies in sync.** ProfileSummary (name, level, play time, runes memory, map, equipment, body
  type, class, gift), PlayerGameDataHash and the checksums have to be rewritten after an edit.
- **NetMan repair.** CSNetMan.bin, the clean NetMan replacement, covers the 4 bytes before the NetMan
  region as well (the top 3 bytes of `temp_spawn_point_entity_id` and `game_man_0xcb3`); only its bytes
  from offset 4 are written. A damaged chunk can be replaced on its own, keeping the intact ones.
  A damaged message chunk can be rebuilt from its own bytes: kind, size and the `FACE` block identify
  every whole entry, so only the damaged entries are lost.
- **Atomic writes.** Write to a temporary file and rename it over the save.

---

[← Back to Home](../index.md)
