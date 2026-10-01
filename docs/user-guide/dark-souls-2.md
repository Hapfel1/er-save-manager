# Dark Souls II

Save editing for Dark Souls II: Scholar of the First Sin: stats, inventory with visual item picker and editor, Souls Planner build import, bonfires and NPCs.

## Overview

DS2 support is a reduced tab set:

- Save Inspector
- Character Management
- Character Editor (Stats, Inventory, Bonfires and NPCs sub-tabs)
- SteamID Patcher
- Backup Manager (top-level button)
- Settings

---

## Save Inspector

Lists all character slots for the loaded save. Selecting a slot and clicking Edit Character opens it in the Character Editor.

---

## Character Management

Copy, transfer, swap, export, import and delete character slots, within a save or between two saves.

---

## Character Editor

Pick a slot and click **Load Slot**. The editor has four sub-tabs.

### Stats

Edit name, Souls, NG+ cycle (up to NG+7), torch time and the attributes. Level is recalculated from the attributes. A slot that was never created in game can be edited, but the edits do not show on the load screen.

### Inventory

The item spawner is on the left and the character's items on the right.

- **Add Item**: pick a category, search, and add one item, several (Ctrl or Shift click) or **Add All Listed**. Quantity, upgrade level and infusion are capped per item, and fields that do not apply to the selection are greyed out. Items can be added to the inventory or the item box.
- **Visual Picker** shows the spawn list as an icon grid by category, with the same options and multi-select.
- **Editing**: set quantity, upgrade level or infusion, move items between the inventory and the item box, or remove them. Equipped items cannot be removed or stored; unequip them in game first.
- **Visual View** shows the character's items as an icon grid with the same editing options.
- **Seamless Co-op items** are offered only when a Seamless Co-op `.co2` save is loaded.
- **Unsafe items** (items that can get an account soft-banned online) ask for confirmation before being added. They are safe on Seamless Co-op saves.

### Bonfires

Light or unlight bonfires, set their Bonfire Ascetic level (1 to 8), or unlock all of them at once. Lighting keeps a bonfire's level, unlighting resets it, and Set Level also lights unlit bonfires. The bonfire the character last rested at always stays lit. **Visual View** shows every bonfire as its picture, with unlit ones greyed out.

### NPCs

Lists each NPC with its state (alive, hostile or dead). **Revive** clears the NPC's dead and hostile flags; **Calm** clears only the hostile flag. Quest progress is left as it is.

---

## Souls Planner Build Import

**Import Soulsplanner Build** in the Character Editor takes a [soulsplanner.com](https://soulsplanner.com) Dark Souls II build link and applies it to the loaded slot:

1. Choose **Stats Only**, **Items Only** or **Stats and Items**, and whether to equip the build's loadout afterwards.
2. For items the character already owns, choose to add the build's copies anyway or only the copies still missing.
3. Builds do not store upgrade levels or amounts, so these are picked per item (with All Min and All Max shortcuts).

---

## SteamID Patcher

Transfer a DS2 save between Steam accounts, same mechanism as the Elden Ring version.

---

## Safety

Every edit creates a backup first, and the game must be closed while editing.

---

## Related Features

- **[Backup Manager](backup-manager.md)**
- **[SteamID Patcher](steamid-patcher.md)**
