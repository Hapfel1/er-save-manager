# Dark Souls II

Save editing for Dark Souls II: Scholar of the First Sin: stats, equipment and attunement, inventory with visual item picker and editor, appearance, Souls Planner build import, bonfires, bosses and NPCs.

## Overview

DS2 support uses these tabs:

- Save Inspector
- Character Management
- Character Editor (Stats, Equipment and Inventory sub-tabs)
- Appearance
- World State (bonfires)
- NPCs & Bosses
- SteamID Patcher
- Backup Manager (top-level button)
- Settings

---

## Selecting a Character and Applying Changes

The **Character** bar under the file row picks the character for every tab that edits one; switching tabs keeps the selection. The first character is loaded when a save opens.

Edits are staged until they are applied. The unapplied-changes bar lists the pages with edits: **Apply All** writes all of them in one save write with one backup, **Discard** drops them. Switching characters, loading another save, switching games or closing the window with unapplied changes asks whether to apply or discard them first.

---

## Save Inspector

Lists every character as a card with slot, level, class, souls, NG+ and play time, and a status on the right: **OK**, or the number of issues detected (hover for the list). **View All Issues** lists them for the whole save. Select a character and click **Edit Character** to open it in the Character Editor.

---

## Character Management

Copy, transfer, swap, export, import and delete character slots, within a save or between two saves.

---

## Character Editor

### Stats

Edit name, class, Souls, NG+ cycle (up to NG+7), HP, torch time and the attributes. Level is recalculated from the attributes, and Soul Memory follows level and Souls edits. **Fix Cycle Soul Memory** repairs NG characters whose cycle Soul Memory is missing, which locks the Shrine of Winter. A slot that was never created in game can be edited, but the edits do not show on the load screen.

Names can be up to 14 characters, or 31 on a Seamless Co-op `.co2` save.

### Equipment

Every equipment slot of the character: right and left hand weapons 1-3, the four armor pieces, four rings, arrows and bolts 1-2 and ten belt items. Click a slot to pick from the items the character carries that fit it, with icons, categories and search.

**Attunement** lists the attuned spells in slot order, packed from the first slot as the game stores them. **Add Spell** picks from the carried spells; **Remove**, **Move Up** and **Move Down** change the list.

### Inventory

The item spawner is on the left and the character's items on the right.

- **Add Item**: pick a category, search, and add one item, several (Ctrl or Shift click) or **Add All Listed**. Quantity, upgrade level and infusion are capped per item, and fields that do not apply to the selection are greyed out. Items can be added to the inventory or the item box.
- **Visual Picker** shows the spawn list as an icon grid by category, with the same options and multi-select.
- **Editing**: set quantity, upgrade level or infusion, move items between the inventory and the item box, or remove them. Equipped items cannot be removed or stored; unequip them first.
- **Visual View** shows the character's items as an icon grid with the same editing options.
- **Seamless Co-op items** are offered only when a Seamless Co-op `.co2` save is loaded.
- **Unsafe items** (items that can get an account soft-banned online) ask for confirmation before being added. They are safe on Seamless Co-op saves.

### Souls Planner Build Import

**Import Soulsplanner Build** in the Character Editor takes a [soulsplanner.com](https://soulsplanner.com) Dark Souls II build link and applies it to the selected character:

1. Choose **Stats Only**, **Items Only** or **Stats and Items**, and whether to equip the build's loadout afterwards.
2. For items the character already owns, choose to add the build's copies anyway or only the copies still missing.
3. Builds do not store upgrade levels or amounts, so these are picked per item (with All Min and All Max shortcuts).

---

## Appearance

DS2 has no way to change a character's look after creation; this tab does it for created characters (a slot before character creation gets its look from the creation menu).

- **Copy and share** - load the look of another character from the same save or from another DS2 save file (**From Another Save...**), or export and import it as a JSON file. A copy carries the face, hair and all colors.
- **Body and face** - gender, build, physique, hairstyle, eyebrow, beard and tattoo, numbered in the creation menu's order (left to right, top to bottom). Changing the gender keeps the build's and the hairstyle's place in the list.
- **Colors** - hair, eyebrow, eye, beard and tattoo color with Red, Green and Blue sliders.

**Revert** reloads the saved appearance. Applying also updates the copies kept with the load-screen character list.

---

## World State

### Bonfires

Light or unlight bonfires, set their intensity (1 to 8), or **Unlock All Bonfires**. Intensity is what Bonfire Ascetics raise, plus 1 per NG+ cycle the game adds itself; it is kept when lighting or unlighting, and **Set Intensity** also lights unlit bonfires. The bonfire the character last rested at always stays lit. **Set as Last Rested** makes the selected bonfire the one death and the Homeward Bone return the character to (it is lit if needed; the character still loads where they saved). **Visual View** shows every bonfire as its picture, with unlit ones greyed out.

---

## NPCs & Bosses

### NPCs

Lists each NPC with its state (alive, hostile or dead). **Revive** clears the NPC's dead and hostile flags and the kill counts that keep a killed NPC from spawning; **Calm** clears only the hostile flags. Quest progress is left as it is.

### Bosses

Lists each boss with its state, defeat count and the Ascetic bonfire of its area. **Respawn Selected** returns defeated bosses to their arenas, **Kill Selected** marks them defeated and **Set Defeats** sets the defeat count. **Repair Selected** and **Repair All Invalid** fix boss records that block Bonfire Ascetic use, such as bosses killed in another player's world.

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
