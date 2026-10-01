# Dark Souls Remastered

Save editing support for Dark Souls Remastered (DSR), covering character stats, inventory, bosses, NPCs, bonfires and NG+.

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

The item spawner is on the left and the character's inventory on the right. The item list, upgrade caps, durability and icons come from the game's own files.

- **Spawning** stores items the way the game does: key items in the key item slots, goods and ammo stacked, weapons with their infusion and upgrade level. Infused weapons are listed once with an **Infusion** choice.
- **Visual Picker** shows the spawn list as an icon grid.
- **Editing**: quantity, upgrade level and infusion, removal and **Repair All**. Select several items (Ctrl or Shift click) to edit them in one go; each item is capped at its own limits. Equipped items cannot be removed.
- **Visual Editor** shows the inventory as an icon grid with the same editing options.
- **Cut content** (for example the Mage Smith Coat and the Elite Cleric Helm and Armor) is hidden by default, shown by **Cut content** or by searching for it by name, and asks for confirmation before spawning. A character keeps a single Estus Flask.
- **SeamlessCoop items** are offered only when a SeamlessCoop `.co2` save is loaded.

---

## NPCs & Bosses

- **Bosses**: kill or respawn. Defeat flags are per playthrough, so bosses show as alive again after starting NG+.
- **NPCs**: kill or revive. Only the NPC's alive/hostile/dead state changes, the way the game's own NPC death event does it; quest progress is kept.

---

## Event Flags

Read and toggle DSR event flags.

---

## World State

### Bonfires

- Light or unlight bonfires, one, several or all at once. A bonfire can only be lit once the character has visited its map; lighting keeps any kindling already done. Bonfires are named by their area.

### New Game+ Counter

- Shows current NG+ cycle
- Set to any value 0-7 (0 = NG, 1 = NG+, 2 = NG++, etc.) and click **Apply**

---

## SteamID Patcher

Transfer a DSR save between Steam accounts, same as the Elden Ring version.

---

## Safety

Every write (stats, identity, inventory, bosses, NPCs, bonfires, NG+) creates a backup first via the Backup Manager, tagged with the operation performed, so any change can be rolled back.

---

## Related Features

- **[Backup Manager](backup-manager.md)**
- **[SteamID Patcher](steamid-patcher.md)**
