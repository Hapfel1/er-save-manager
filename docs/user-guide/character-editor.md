# Character Editor

Edit character stats, runes, name, level, and build attributes directly.

## Overview

The Character Editor allows you to modify:

- Character name (max 16 characters)
- Stats (Vigor, Mind, Endurance, Strength, Dexterity, Intelligence, Faith, Arcane)
- Runes held
- Character creation details (body type, class, starting gift, voice)
- Progression info (NG level, talisman slots, spirit tuning, flasks)

**When to Use:**

- Respec character build
- Adjust stats for PvP/PvE
- Fix level/stat inconsistencies
- Test different builds
- Prepare character for NG+

---

## Interface Layout

### Character Creation Section

**Editable Fields:**

- **Name** - Character name (max 16 characters, UTF-16)
  - Character counter shows X/16
  - Validated to prevent exceeding limit
- **Body Type** - Character body type selection
- **Starting Class** - Class/Archetype selection
- **Voice** - Voice type selection
- **Keepsake** - Starting gift selection

### Stats Section

**Eight Core Stats:**

- **Vigor**
- **Mind** 
- **Endurance**
- **Strength** 
- **Dexterity**
- **Intelligence**
- **Faith**
- **Arcane**

**Display Shows:**

- Current value
- Input field for new value
- Valid range indicators

### Progression Section

**Editable Fields:**

- **Runes Held** - Current runes
- **Level** - Character level (calculated from stats)
- **NG Level** - New Game Plus cycle (0-7+)
- **Playtime** - Hours, minutes and seconds played
- **Scadutree Blessing** / **Revered Spirit Ash Blessing** - Shadow of the Erdtree blessing levels
- **Memory Stones** - Memory Stones obtained (0-8)

---

## Usage

### Editing Character Name

1. Load save file
2. Go to **Character Editor** tab
3. Pick the character in the **Character** bar
4. Type new name in **Name** field
5. Character count updates (max 16 chars)
6. Click **Apply All** in the unapplied-changes bar

**Validation:**

- Maximum 16 characters enforced
- UTF-16 encoding supported (supports special characters)
- Empty names not allowed

### Editing Stats

**Steps:**

1. Load the save file and pick the character in the **Character** bar
2. Locate stat to modify in Stats section
3. Enter new value in input field
4. Repeat for other stats as needed
5. Click **Apply All** in the unapplied-changes bar

**Constraints:**

- Minimum: Base class values
- Maximum: 99 per stat
- Level auto-calculated from total stats


### Editing Runes

1. Find **Runes Held** field in Progression section
2. Enter new amount
3. Click **Apply All** in the unapplied-changes bar

**Note:** Runes are currency held, not accumulated runes spent

### Editing Level

Level is automatically calculated from stat totals. To change level:

1. Adjust individual stats
2. Total stat points determine level
3. Level updates automatically

**Formula:** Level = Sum(Stats - Base Stats) + Starting Level

### Editing NG Level

1. Find **NG Level** in Progression section
2. Select Level
3. Click **Apply All** in the unapplied-changes bar

**Valid Range:** 0-7 (game supports up to NG+7)

---

## Character Creation Details

### Body Type

Selection between available body types. Determines base character model.

### Starting Class

View and modify the starting class/archetype.

**Available Classes:**

- Vagabond
- Warrior
- Hero
- Bandit
- Astrologer
- Prophet
- Samurai
- Prisoner
- Confessor
- Wretch

**Note:** Changing class doesn't change stats automatically - adjust stats separately

### Voice Type

Character voice selection for grunts and sounds.

**Options:**

- Young (Voice 1-3)
- Mature (Voice 1-3)

### Keepsake (Starting Gift)

The gift chosen at character creation.

**Available Keepsakes:**

- Crimson Amber Medallion
- Lands Between Rune
- Golden Seed
- Fanged Imp Ashes
- Cracked Pot
- Stonesword Key
- Bewitching Branch
- Boiled Prawn
- Shabriri's Woe
- None

---

## Progression Details

### Playtime

Hours, minutes and seconds of play time. Written to the character's own play time and to the load screen
entry. The in-game time of day is not changed.

### Blessings & Memory Stones

- **Scadutree Blessing** (0-20) and **Revered Spirit Ash Blessing** (0-10), as shown on the status screen
- **Memory Stones** (0-8): the number of Memory Stones the character has. The held Memory Stone item is set
  to the same quantity, added if missing and removed at 0

---

## Great Rune, Rune Arc & Matchmaking

### Great Rune Active (Rune Arc used)

Toggles whether the equipped Great Rune's effect is active, the state a Rune Arc puts it in. The game
stores one flag for this, so there is no separate Rune Arc option.

### Active Great Rune

Dropdown to select which Great Rune is equipped:

- None
- Godrick's Great Rune
- Radahn's Great Rune
- Morgott's Great Rune
- Rykard's Great Rune
- Mohg's Great Rune
- Malenia's Great Rune

The rune has to be in the held inventory. If it is not, the editor keeps the current Great Rune and
saves the other changes.

### Last Rested Grace

Grace ID (hex) for the last Site of Grace the character rested at.

### Matchmaking Weapon Level

Sets the weapon level used for online matchmaking, on the game's 0-25 standard scale. Somber weapon upgrades are mapped to their standard-scale equivalent when computing this (e.g. Somber +5 = matchmaking level 12).

**Constraints:**

- Value cannot be set lower than the highest matchmaking level found across weapons currently in held and storage inventory. This floor is shown next to the field and is recalculated whenever the character is loaded.
- Values entered below the floor are rejected and reset to the floor with a warning.

---

## Safety Features

### Automatic Backup

Created before every character edit:

- Timestamp included
- Original state preserved
- Easy restore from Backup Manager

### Validation

**Before applying changes:**

- Stats within valid ranges (1-99)
- Name length ≤16 characters
- Runes within limits
- NG level valid

**After applying:**

- Checksums recalculated
- Save file integrity maintained
- Changes verified

### Apply All

The **Character** bar under the file row picks the character for every tab that edits one, and the first character is loaded when a save opens. All edits are staged until they are applied. The unapplied-changes bar lists every page with edits, across all tabs. It names the changed fields (for example "3 unapplied changes: Name, Vigor, Mind"); **Review** opens every change with its old and new value and a **Show** link to its page.

1. Review the list in the bar
2. Click **Apply All**
3. One backup is created
4. All staged edits are written in one save
5. Checksums updated

**Discard** drops the staged edits instead. Switching characters, loading another save, switching games or closing the window with unapplied changes asks whether to apply or discard them first.

---

## Troubleshooting

### "Invalid stat value"

**Cause:** Stat outside valid range

**Solution:**

- Check stat is 1-99
- Verify no decimals
- Check typing errors

### "Name too long"

**Cause:** Name exceeds 16 characters

**Solution:**

- Shorten name
- Counter shows current length

### "Changes not applied"

**Cause:** The edits were not applied

**Solution:**

- Click **Apply All** in the unapplied-changes bar
- Wait for confirmation

### Character won't load in-game

**Cause:** Invalid stats or corruption

**Solutions:**

1. Restore from automatic backup
2. Check stats are reasonable
3. Run Save File Fixer
4. Verify checksums updated

---

## Related Features

- **[Save File Fixer](save-file-fixer.md)** - Fix corruption
- **[Backup Manager](backup-manager.md)** - Restore previous state
- **[Character Management](character-management.md)** - Export/import characters

---

## FAQ

**Q: Will editing stats break my save?**  
A: No, tool recalculates checksums. Stats within 1-99 are safe.

**Q: Can I exceed level 713?**  
A: Level is calculated from stats. Max stats (99 each) = level 713.

**Q: Does changing NG level give me items/bosses?**  
A: No, it only changes the cycle counter. World state unchanged.

---

[← Character Browser](character-browser.md) | [Next: Appearance →](appearance.md)