# Event Flags & Boss Respawner

View, edit, and toggle event flags - including boss respawning functionality with 948 documented flags.

## Overview

Event flags are binary switches (ON/OFF) that track game state:

- Boss defeats
- Grace site discoveries
- NPC quest progression  
- Item pickups
- Door/gate unlocks
- World changes

The Event Flags tab provides:

- 948 documented flags organized by category
- Boss respawn functionality
- Search and filter
- Bulk operations
- Advanced custom flag editor

---

## Interface Layout

### Top Section

**Character Slot Selector:**

- Choose slot (1-10)
- Load Flags button
- Advanced... button (custom flag editor)
- Apply Changes button
- Unlock All in Category button
- Boss Respawn... button

### Category Selection

**Main Categories:**

- Boss
- Grace
- Quest
- Item
- Achievement
- NPC
- Area
- Misc

**Subcategories:**

- Varies by main category
- Example: Boss → Demigods, Dragons, Dungeon Bosses, etc.

### Flag List

**Displays:**

- Checkbox for each flag
- Flag name (description)
- Current state (checked = ON, unchecked = OFF)
- Flag ID number

**Search:**

- Text search to filter flags
- Searches flag names
- Real-time filtering

---

## Using Event Flags

### Loading Flags

**Steps:**

1. Select character slot
2. Click **Load Flags**
3. Flag list populates with current states
4. Category defaults to first category

**Result:** All 948 flags loaded with current ON/OFF states

### Viewing Flags

**By Category:**

1. Select main category dropdown
2. Select subcategory (if available)
3. Flag list updates to show matching flags

**By Search:**

1. Type search term
2. Flags filtered by name
3. Matching flags displayed

### Toggling Flags

**Single Flag:**

1. Find flag in list
2. Click checkbox to toggle ON/OFF
3. State changes immediately in interface
4. Changes not saved until **Apply Changes**

**Multiple Flags:**

1. Check/uncheck multiple flags
2. All changes tracked
3. Click **Apply Changes** to save all at once

### Unlock All in Category

**Bulk unlock:**

1. Select category and subcategory
2. Click **Unlock All in Category**
3. All flags in current view set to ON
4. Click **Apply Changes** to save

**Use Cases:**

- Unlock all graces in area
- Unlock all gestures
- Mark all bosses defeated

### Applying Changes

**Steps:**

1. Make flag changes
2. Click **Apply Changes**
3. Automatic backup created
4. Changes written to save
5. Checksums recalculated
6. Confirmation shown

**Important:** Changes only saved after clicking **Apply Changes**

---

## Boss Respawner

### Opening Boss Respawner

**Steps:**

1. Load event flags for character
2. Click **Boss Respawn...**
3. Boss Respawn dialog opens

### Boss Respawn Dialog

**Interface:**

- **Boss Location dropdown** - Select boss location
- **Boss list** - All bosses in category
- **Checkboxes** - Select bosses to respawn
- **Respawn Selected button**
- **Respawn All in Category button**

### Boss List Display

**Each boss shows:**

- Boss name
- Current status: "Defeated" or "Alive"
- Checkbox to select for respawn

### Respawning Bosses

**Single Boss:**

1. Select boss category
2. Find boss in list
3. Check boss checkbox
4. Click **Respawn Selected**
5. Boss defeat flag cleared
6. Boss respawns in-game

**Multiple Bosses:**

1. Select category
2. Check multiple bosses
3. Click **Respawn Selected**
4. All selected bosses respawn

**All in Category:**

1. Select category
2. Click **Respawn All in Category**
3. All bosses in category respawn

### How Boss Respawn Works

**Process:**

1. Identifies boss defeat flag(s)
2. Sets flag(s) to OFF (0)
3. Teleports character to Roundtable Hold
4. Saves changes to character
5. Recalculates checksums
6. Game treats boss as not defeated

**Result:** Boss respawns at original location

**Notes:**

- Great Runes remain if obtained
- Achievements remain earned
- Can obtain drops again
- Progression bosses may need re-defeating for story

---

## Advanced Flag Editor

### Opening Advanced Editor

**Steps:**

1. Load event flags
2. Click **Advanced...**
3. Advanced editor dialog opens

### Advanced Editor Features

**Custom Flag ID:**

- Enter any 8-digit flag ID
- Access undocumented flags
- Toggle ON/OFF manually
- For advanced users/modders

**Use Cases:**

- Accessing hidden flags
- Mod-specific flags
- Testing custom content
- Research/documentation

**Warning:** Incorrect flags can break quests or progression

---

## Flag Categories Explained

### Boss Flags

**What They Do:**

- Track boss defeat status
- Control boss respawning
- Affect world state after defeat

**Common Boss Flags:**

- 1035500800: Margit
- 1036540800: Godrick
- 1035520800: Radahn
- 1034500800: Rennala
- 1042380800: Morgott
- 1045520800: Malenia

### Grace Flags

**What They Do:**

- Track discovered Sites of Grace
- Enable fast travel
- Control grace visibility

**Examples:**

- 71000: First Step
- 71050: Church of Elleh
- 71100: Gatefront Ruins

### Quest Flags

**What They Do:**

- Track NPC quest progression
- Control dialogue options
- Trigger quest events

**Warning:** Changing quest flags can break progression

### Item Flags

**What They Do:**

- Mark items as picked up
- Prevent re-obtaining
- Track key items

### Achievement Flags

**What They Do:**

- Unlock achievements
- Track completion requirements
- Control ending access

---

## Safety Features

### Automatic Backup

**Before applying changes:**

- Full save backup created
- Timestamp included
- Easy restore if issues

### Validation

**Checks performed:**

- Flag IDs valid
- Event flag buffer accessible
- Save file loaded

### Confirmation

**For risky operations:**

- Respawn all bosses
- Unlock all in category
- Bulk operations

---

## Troubleshooting

### "Event flags not loaded"

**Cause:** No character selected or slot empty

**Solution:**

- Select character slot
- Click Load Flags
- Verify slot has character

### "Changes not applied"

**Cause:** Forgot to click Apply Changes

**Solution:**

- Click **Apply Changes** button
- Wait for confirmation

### "Quest broken after changing flags"

**Cause:** Wrong flags modified

**Solution:**

- Restore from automatic backup
- Research correct flag sequence
- Consult community resources

---

## Related Features

- **[Save File Fixer](save-file-fixer.md)** - Fix flag corruption (Ranni quest)
- **[Backup Manager](backup-manager.md)** - Restore after flag changes
- **[Gestures](gestures.md)** - Unlock gestures via flags

---

## FAQ

**Q: Can I unlock achievements with flags?**  
A: Flags control in-game state. Steam achievements are handled separately.

**Q: Will respawning bosses give Great Runes again?**  
A: No, Great Runes are only obtained once (flag separate from defeat).

**Q: Can I reset entire character progress?**  
A: Theoretically yes by clearing flags, but extremely complex and risky.

**Q: Do event flags transfer between characters?**  
A: No, each character has their own event flags.

**Q: Can I use flags to skip game sections?**  
A: Yes, but may break quest progression or cause softlocks.

---

[← World State](world-state.md) | [Next: Gestures →](gestures.md)