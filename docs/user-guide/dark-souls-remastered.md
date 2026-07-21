# Dark Souls Remastered

Save editing support for Dark Souls Remastered (DSR), covering character stats, bonfires, and NG+.

## Overview

DSR support is a reduced tab set focused on the core editing tasks:

- Save Inspector
- Character Editor
- Inventory
- NPCs & Bosses
- Event Flags
- World State (bonfires and NG+)
- SteamID Patcher
- Backup Manager (top-level button)
- Settings

---

## Save Inspector

Lists all character slots with name and status. Selecting a slot and clicking **Edit Slot** jumps to the Character Editor with that slot loaded.

---

## Character Editor

### Identity

- **Name** - up to 16 characters, written to both name fields stored in the save
- **Body Type** - Type A (Male) / Type B (Female)
- **Class** - starting class selection
- **Covenant** - current covenant
- **NG+** - New Game+ cycle (0-7)
- **Play Time** - read-only, computed from stored playtime

### Attributes

The eight core DS1 stats:

- Vitality
- Attunement
- Endurance
- Strength
- Dexterity
- Intelligence
- Faith
- Resistance

Editing **Vitality** recalculates max HP; editing **Endurance** recalculates max Stamina. Level is recalculated automatically from the stat total and starting class whenever a stat changes, so you don't need to set it manually.

### Resources

- **Level** - auto-calculated, editable directly if needed
- **Souls** - current soul count
- **Humanity** - humanity count

All changes require **Apply Changes**, which creates a backup before writing.

---

## Inventory

Edit inventory items, with support for SeamlessCoop items.

---

## NPCs & Bosses

Boss revival and NPC revival for repeated fights and quest resets.

---

## Event Flags

Read and toggle DSR event flags.

---

## World State

### Bonfires

- **Unlock All Warpable Bonfires** - unlocks all 20 warpable bonfires, including the Firelink Shrine warp
- Individual bonfire control isn't available: the 3 bytes that encode which bonfires are warpable are bit flags, but no public documentation maps which bit corresponds to which bonfire, so only bulk unlock is offered

### New Game+ Counter

- Shows current NG+ cycle
- Set to any value 0-7 (0 = NG, 1 = NG+, 2 = NG++, etc.) and click **Apply**

---

## SteamID Patcher

Transfer a DSR save between Steam accounts, same as the Elden Ring version.

---

## Safety

Every write (stats, identity, bonfires, NG+) creates a backup first via the Backup Manager, tagged with the operation performed, so any change can be rolled back.

---

## Related Features

- **[Backup Manager](backup-manager.md)**
- **[SteamID Patcher](steamid-patcher.md)**
