# Dark Souls III

Save editing for Dark Souls III: stats, inventory with visual item picker and editor, bosses, NPCs, bonfires, gestures and NG+, with Convergence and Cinders item data.

## Overview

DS3 support is a reduced tab set:

- Save Inspector
- Character Editor
- Character Management
- Inventory
- Bosses
- World State
- NPCs
- SteamID Patcher
- Backup Manager (top-level button)
- Settings

---

## Save Inspector

Lists all character slots for the loaded save. Selecting a slot and clicking Edit Character loads it in every editing tab.

---

## Character Editor

Edit the nine DS3 attributes, Souls, name and NG+ cycle. Level follows the attributes automatically (every DS3 class has level = attribute total - 89). Name and level changes are also written to the load screen's character list so it does not show stale values.

---

## Inventory

The item spawner is on the left and the character's items (held, key items and the storage box) on the right.

- **Game data** picks the item list: Vanilla, Convergence or Cinders. Each list is built from that game's own files (item parameters, item names and menu icons), so names, stack sizes, upgrade caps and icons match what the game shows. Pick the list matching the mod the character was played with.
- **Spawning** places items the way the game does when you pick something up: weapons and armor get their own item entry, goods stack, key items go to the key item list, and items can be sent to the storage box instead of the inventory. Infused weapons are listed once with an **Infusion** choice and its icon.
- **Visual Picker** shows the spawn list as an icon grid by category.
- **Editing**: stackable items can have their quantity changed, weapons their upgrade level and infusion, items can move between the inventory and the storage box, and items that are not equipped can be removed. Equipped items and items on the quick/belt slots are protected; unequip them in game first.
- **Visual Editor** shows the character's items as an icon grid with the same editing options.
- **Cut content** (vanilla items no item lot, shop or starting class hands out) is hidden by default and asks for confirmation before spawning.

If a character's inventory was damaged by an earlier version of this editor, inventory editing is disabled for that character and the reason is shown. Bosses, NPCs, bonfires and gestures stay editable. Restore a backup from before the earlier edit to edit items again.

---

## Bosses

Kill or respawn any boss, including DLC bosses. This sets or clears the boss's defeat flag and, for main story bosses, the "defeated" progression flag other scripts read. Boss souls are not given or taken.

---

## World State

- **New Game+**: set the playthrough cycle. The playthrough flags scripts check are kept in step.
- **Bonfires**: light or unlight bonfires by area. Lit bonfires are warp destinations once the Firelink Shrine bonfire is lit.
- **Gestures**: unlock or lock gestures.

---

## NPCs

Revive a dead or hostile NPC, or mark one dead. Only the NPC's alive/hostile/dead state changes; quest progress is left as it is, so an NPC whose questline already moved on stays where it left off.

---

## SteamID Patcher

Transfer a DS3 save between Steam accounts, same mechanism as the Elden Ring version.

---

## Safety

Every edit creates a backup first, and the game must be closed while editing. Offsets are read from the save's own structure; a character whose layout does not match (for example saves from some randomizer mods) is shown read-only for the affected features instead of being written.

---

## Related Features

- **[Backup Manager](backup-manager.md)**
- **[SteamID Patcher](steamid-patcher.md)**
