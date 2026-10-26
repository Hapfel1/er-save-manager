# Dark Souls Remastered

Save editing for Dark Souls Remastered (DSR): stats, identity, covenants, equipment and attunement, inventory, appearance, bonfires, NG+, bosses, NPCs and event flags.

## Overview

DSR support uses these tabs:

- Save Inspector
- Character Management
- Character Editor (Stats, Identity, Covenants, Equipment and Inventory sub-tabs)
- Appearance
- World State (bonfires and NG+)
- NPCs & Bosses
- Event Flags
- Backup Manager (top-level button)
- Settings

DSR saves hold no SteamID, so there is no SteamID Patcher.

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

---

## Character Editor

### Stats

The eight attributes (Vitality, Attunement, Endurance, Strength, Dexterity, Intelligence, Faith, Resistance) and the resources:

- **Level** - recalculated from the attribute total and starting class whenever an attribute changes
- **Souls** - current soul count
- **Humanity** - humanity count

Saving **Vitality** updates max HP; saving **Endurance** updates max Stamina.

### Identity

- **Name** - up to 13 characters (the in-game limit), written to both name fields stored in the save
- **Class** - starting class
- **Covenant** - current covenant
- **NG+** - New Game+ cycle (0-7)
- **Play time** - read-only

### Covenants

Offering counts for the seven covenants that take offerings (Warrior of Sunlight, Darkwraith, Path of the Dragon, Gravelord Servant, Forest Hunter, Darkmoon Blade, Chaos Servant). Rank 1, 2 and 3 are reached at 10, 30 and 80 offerings; Forest Hunter has no ranks. Changing a count does not add the rank rewards.

### Equipment

Every equipment slot of the character: right and left hand weapons 1-2, the four armor pieces, arrows and bolts 1-2, two rings and five quick items. Click a slot to pick from the items the character carries that fit it, with icons, categories and search. Emptying a hand or armor slot puts the game's bare-hand or bare-body placeholder in it.

**Attunement** lists the attuned spells in slot order, packed from the first slot as the game stores them. **Add Spell** picks from the carried spells; **Remove**, **Move Up** and **Move Down** change the list.

### Inventory

The item spawner is on the left and the character's inventory on the right. The item list, upgrade caps, durability and icons come from the game's own files.

- **Spawning** stores items the way the game does: key items in the key item slots, goods and ammo stacked, weapons with their infusion and upgrade level. Infused weapons are listed once with an **Infusion** choice.
- **Visual Picker** shows the spawn list as an icon grid.
- **Editing**: quantity, upgrade level and infusion, removal and **Repair All**. Select several items (Ctrl or Shift click) to edit them in one go; each item is capped at its own limits. Equipped items cannot be removed.
- **Visual Editor** shows the inventory as an icon grid with the same editing options.
- **Cut content** (for example the Mage Smith Coat and the Elite Cleric Helm and Armor) is hidden by default, shown by **Cut content** or by searching for it by name, and asks for confirmation before spawning. A character keeps a single Estus Flask.
- **SeamlessCoop items** are offered only when a SeamlessCoop `.co2` save is loaded.

---

## Appearance

- **Body and hair** - body type (Type A / Type B), physique, face type and hairstyle, with the names from the character creation menu. Picking a face type replaces the face sliders with that face, as in the game.
- **Colors** - the color preset sets hair and eye color together; the Red, Green and Blue sliders change each color afterwards.
- **Face** - the game's face controls, split into Shape and Skin. Moving one slider can move related ones. Values are relative: 0 is the average face, and the slider ends reach past the most extreme faces the game ships.
- **Copy and share** (top of the tab) - load the appearance of another character from the same save or from another DSR save file (**From Another Save...**), or export and import it as a JSON file.

**Revert** reloads the saved appearance. Applying also updates the copy of the face, colors and hairstyle kept with the load-screen character list.

---

## World State

### Bonfires

Light or unlight bonfires, one, several or all at once (double-click toggles one). A bonfire can only be lit once the character has visited its map; lighting keeps any kindling already done. Lit bonfires are warp destinations once warping is unlocked. Bonfires are named by their area.

### New Game+ Counter

Shows the current NG+ cycle and sets it to any value 0-7 (0 = NG, 1 = NG+, 2 = NG++, etc.).

---

## NPCs & Bosses

- **Bosses**: kill or respawn. Defeat flags are per playthrough, so bosses show as alive again after starting NG+.
- **NPCs**: kill or revive. Only the NPC's alive/hostile/dead state changes, the way the game's own NPC death event does it; quest progress is kept.
- **Quest Progress**: each NPC's quest states (where they are, which path they took) with the current one marked. **Apply** moves the NPC to that state the way the game's events do: the NPC's other states are cleared. A backup is made first.
- Kingseeker Frampt and Darkstalker Kaathe cannot be killed. Attacking them makes them leave (shown as Hostile); Revive brings them back.

---

## Event Flags

- **NPC States** - the individual quest-state flags of every major NPC; select a row and click **Toggle Selected**.
- **World Flags** - persistent world flags (Rite of Kindling, Bottomless Box, Sin flags) and the gesture CanLearn flags (1 = not yet taught by the NPC, 0 = taught; they reset on NG+). Flags marked * are reset on NG+ or set by event scripts at load.
- **Flag Lookup** - read or set any event flag by its numeric ID.

---

## Safety

Every write creates a backup first via the Backup Manager, tagged with the operation performed, so any change can be rolled back.

---

## Related Features

- **[Backup Manager](backup-manager.md)**
