# Dark Souls III

Save editing for Dark Souls III: stats, identity, equipment and attunement, inventory with visual item picker and editor, appearance, bonfires, gestures, NG+, bosses and NPCs, with Convergence and Cinders item data.

## Overview

DS3 support uses these tabs:

- Save Inspector
- Character Management
- Character Editor (Stats, Identity, Equipment and Inventory sub-tabs)
- Appearance
- World State
- NPCs & Bosses
- SteamID Patcher
- Backup Manager (top-level button)
- Settings

---

## PlayStation 4 Saves

A decrypted PS4 export is a folder of `userdata` files: `userdata0000` to `userdata0009` hold the ten character slots and `userdata0010` holds the load-screen character list. Open any of them and every userdata file in the same folder is loaded with it. Edits write back only the files that changed, in the same format, so the folder can be imported to the console as it is.

A userdata file opened without the rest of its folder gives access to its own character only. The other slots show as **No File**, and the load-screen list is not updated, since it lives in `userdata0010`.

Auto-Find does not find PS4 saves; use **Browse**. The **PS4 Save?** button in the file row repeats these steps.

---

## Selecting a Character and Applying Changes

The **Character** bar under the file row picks the character for every tab that edits one; switching tabs keeps the selection. The first character is loaded when a save opens.

Edits are staged until they are applied. The unapplied-changes bar lists the pages with edits: **Apply All** writes all of them in one save write with one backup, **Discard** drops them. Switching characters, loading another save, switching games or closing the window with unapplied changes asks whether to apply or discard them first.

---

## Save Inspector

Lists every character as a card with slot, level, class, souls, NG+ and play time, and a status on the right: **OK**, or the number of issues detected (hover for the list). **View All Issues** lists them for the whole save. Select a character and click **Edit Character** to open it in the editor tabs.

---

## Character Management

Copy, transfer, swap, export, import and delete character slots, within a save or between two saves. The load-screen character list is kept in step.

Transfer and `.ds3c` export/import also move characters between a PS4 folder and a PC save. A character moved to PC gets the target save's SteamID; a character moved to PS4 has it cleared, as on the console.

---

## Character Editor

**Game data** at the top picks the item and class data: Vanilla, Convergence or Cinders. Each list is built from that game's own files (item parameters, item names and menu icons), so names, stack sizes, upgrade caps, icons and starting classes match what the game shows. Pick the one matching the mod the character was played with. When the character's class or level does not fit the selected game data, a warning sign appears next to the selector and the Stats sub-tab explains the mismatch.

### Stats

Edit the nine attributes and Souls. Level follows the attributes automatically (every DS3 class has level = attribute total - 89). Attributes cannot go below the starting class's base values unless the loaded character is already below them.

### Identity

Name (up to 16 characters), class and NG+ cycle. Name and level changes are also written to the load screen's character list so it does not show stale values.

### Equipment

Every equipment slot of the character: right and left hand weapons 1-3, the four armor pieces, arrows and bolts 1-2, four rings, the covenant and the quick items. Click a slot to pick from the items the character carries that fit it, with icons, categories and search. A slot can be emptied unless the game requires it to hold something.

Equipment changes are also written to the copy of the equipment kept with the load-screen character list.

**Attunement** lists the attuned spells in slot order, packed from the first slot as the game stores them. **Add Spell** picks from the carried spells; **Remove**, **Move Up** and **Move Down** change the list.

### Inventory

The item spawner is on the left and the character's items (held, key items and the storage box) on the right.

- **Spawning** places items the way the game does when you pick something up: weapons and armor get their own item entry, goods stack, key items go to the key item list, and items can be sent to the storage box instead of the inventory. Infused weapons are listed once with an **Infusion** choice and its icon. Stored items use the storage box's stack limits.
- **Visual Picker** shows the spawn list as an icon grid by category.
- **Editing**: stackable items can have their quantity changed, weapons their upgrade level and infusion, items can move between the inventory and the storage box, and items that are not equipped can be removed. Equipped items and items on the quick/belt slots are protected; unequip them first.
- **Visual Editor** shows the character's items as an icon grid with the same editing options.
- **Cut content** (vanilla items no item lot, shop or starting class hands out) is hidden by default and asks for confirmation before spawning.
- **Seamless Co-op items** (the pendants, Ominous Tome and Taunter's Orb) are offered only when a Seamless Co-op `.co2` save is loaded.
- **Estus Flasks**: a character holds one Estus Flask and one Ashen Estus Flask. Spawning another one while the character already has one is skipped; remove the existing flask first to switch levels.
- Fields that do not apply to the selection (quantity for unstackable items, upgrade for items without levels, infusion for items without infusions) are greyed out.

If a character's inventory was damaged by an earlier version of this editor, inventory editing is disabled for that character and the reason is shown. The other tabs stay editable. Restore a backup from before the earlier edit to edit items again.

---

## Appearance

- **Body** - body type and the five Build Detail sliders (head, chest, abdomen, arms, legs).
- **Face** - base template and every face slider of the character creation menu, with the menu's own names and captions, split into Shape and Skin. Picking a base template replaces the face sliders and the base skin color, as in the game.
- **Hair, eyes and tattoo** - hair, brow, beard, eyelashes, each pupil and the tattoo/mark, picked from the game's own icons, each with its color. The tattoo/mark position, angle and size are below it.
- **Copy and share** (top of the tab) - load the appearance of another character from the same save or from another DS3 save file (**From Another Save...**), or export and import it as a JSON file.

**Revert** reloads the saved appearance. Applying also updates the copy of the appearance kept with the load-screen character list.

---

## World State

- **New Game+**: set the playthrough cycle. The playthrough flags scripts check are kept in step.
- **Bonfires**: light or unlight bonfires by area. Lit bonfires are warp destinations once the Firelink Shrine bonfire is lit. A bonfire the game tracks with several world-state flags (High Wall of Lothric) gets exactly one of them set, so it is listed once in the warp menu.
- **Gestures**: unlock or lock gestures individually or all at once.

---

## NPCs & Bosses

### NPCs

Revive a dead or hostile NPC, or mark one dead. Only the NPC's alive/hostile/dead state changes; quest progress is left as it is, so an NPC whose questline already moved on stays where it left off.

**Quest Progress** lists each NPC's quest states with the current one marked. **Apply** moves the NPC to that state the way the game's events do, clearing the NPC's other states. Greirat, Orbeck, Cornyx, Irina and Karla keep earlier states set, as the game does for them; Apply clears only their later ones. A backup is made first.

### Bosses

Kill or respawn any boss, including DLC bosses, selected ones or all at once (double-click toggles one). This sets or clears the boss's defeat flag and, for main story bosses, the "defeated" progression flag other scripts read. Boss souls are not given or taken.

---

## SteamID Patcher

Transfer a DS3 save between Steam accounts, same mechanism as the Elden Ring version. PS4 saves hold no SteamID, so the patcher does not apply to them.

---

## Safety

Every write creates a backup first, and the game must be closed while editing. Offsets are read from the save's own structure; a character whose layout does not match (for example saves from some randomizer mods) is shown read-only for the affected features instead of being written.

---

## Related Features

- **[Backup Manager](backup-manager.md)**
- **[SteamID Patcher](steamid-patcher.md)**
