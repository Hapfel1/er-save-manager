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
- **Talisman Slots** - Number of talisman slots unlocked
- **Spirit Tuning Level** - Maximum spirit ash upgrade level
- **Crimson Flask** - Total Crimson Tears flasks
- **Cerulean Flask** - Total Cerulean Tears flasks

---

## Usage

### Editing Character Name

1. Load save file
2. Go to **Character Editor** tab
3. Select character slot
4. Type new name in **Name** field
5. Character count updates (max 16 chars)
6. Click **Apply Changes**

**Validation:**
- Maximum 16 characters enforced
- UTF-16 encoding supported (supports special characters)
- Empty names not allowed

### Editing Stats

**Steps:**
1. Load save file and load character slot
2. Locate stat to modify in Stats section
3. Enter new value in input field
4. Repeat for other stats as needed
5. Click **Apply Changes**

**Constraints:**
- Minimum: Base class values
- Maximum: 99 per stat
- Level auto-calculated from total stats


### Editing Runes

1. Find **Runes Held** field in Progression section
2. Enter new amount
3. Click **Apply Changes**

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
3. Click **Apply Changes**

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

### Talisman Slots

Number of talisman slots unlocked (0-4).

### Spirit Tuning Level

Maximum upgrade level for Spirit Ashes (0-10).

**Unlocks:**
- Glovewort levels through Roderika dialogue
- Final unlock (+10) after specific quest progression

### Flask Counts

Total number of flasks:
- **Crimson Tears** - HP recovery
- **Cerulean Tears** - FP recovery

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

### Apply Changes Button

All edits are temporary until clicking **Apply Changes**:
1. Review all changes
2. Click **Apply Changes**
3. Backup created automatically
4. Changes written to save
5. Checksums updated
6. Save file ready

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

**Cause:** Forgot to click Apply Changes

**Solution:**
- Click **Apply Changes** button
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

**Q: Can I change my class after creation?**  
A: You can change the class field, but it doesn't automatically adjust stats. Manually set stats for desired class.

**Q: Will editing stats break my save?**  
A: No, tool recalculates checksums. Stats within 1-99 are safe.

**Q: Can I exceed level 713?**  
A: Level is calculated from stats. Max stats (99 each) = level 713.

**Q: Does changing NG level give me items/bosses?**  
A: No, it only changes the cycle counter. World state unchanged.

---

[← Character Browser](character-browser.md) | [Next: Appearance →](appearance.md)