# Character Management

Manage characters across slots and save files - export, import, move, and delete.

---

## Overview

The Character Management tab provides complete control over your character slots:
- Export characters to standalone `.erc` files
- Import characters from `.erc` files
- Move characters between slots
- Copy characters to different save files
- Delete characters permanently

**When to Use:**
- Backing up favorite characters
- Sharing builds with friends
- Reorganizing character slots
- Transferring characters between saves
- Creating character templates

---

## Interface Layout

### Operation Selection

**Dropdown menu for all actions available**
- Copy Character
- Transfer to Another Save
- Swap Slots
- Export Character
- Import Character
- Delete Character

**Operation Details**
- Displays buttons related to the selected operation

---

## Copy Character

Copy a complete character to a different slot in the Save file

### Steps

1. Load your save file
2. Go to **Character Management** tab
3. Select **Copy Character** in the dropdown menu
4. Select both Slots
5. Click **ECopy Character...**

---

## Export Character

Save a complete character to a standalone file.

### What Gets Exported

**Complete character data (~2.6MB):**
- All stats (Vigor, Mind, Endurance, etc.)
- Runes held
- Character name and level
- All equipment (weapons, armor, talismans)
- Complete inventory (held + storage)
- Appearance (FaceData)
- Gestures unlocked
- Regions discovered
- Event flags (boss defeats, graces, quests)
- World state
- Torrent data
- DLC progress
- Original SteamID

### Steps

1. Load your save file
2. Go to **Character Management** tab
3. Select **Export Character** in the dropdown menu
4. Select your slot (you can check the Save Fixer Tab for a character list)
5. Click **Export Character...**
5. Choose save location
6. Enter filename
7. Click Save

**Result:** `.erc` file created containing all character data

### Use Cases

**Backup:** Export before risky operations
**Sharing:** Share builds with community
**Templates:** Create starter characters
**Cross-Save:** Transfer to other PCs
**Archival:** Store favorite builds

---

## Import Character

Load a character from `.erc` file into any slot.

### What Gets Imported

Everything from the `.erc` file:
- Complete character data
- Inventory and equipment
- Quest progress
- World state

### Automatic Adjustments

**SteamID Patching:**
- Original SteamID detected
- Automatically replaced with target save's SteamID
- Prevents corruption

**Profile Summary:**
- Character added to save's profile list
- Active slot flag set
- Playtime preserved

**Checksums:**
- Recalculated for target slot
- USER_DATA_10 checksum updated
- Save integrity maintained

### Steps

1. Load target save file
2. Go to **Character Management** tab
3. Select **Import Character** from the dropdown menu
3. Select target slot (empty or occupied)
4. Click **Import Character**
5. Browse to `.erc` file
6. **If slot occupied:** Confirm overwrite
7. Click Import

**Result:** Character loaded into slot, ready to play

### Safety Features

**Validation:**
- Checks `.erc` file format
- Verifies checksum
- Validates data integrity
- Confirms compatibility

**Backup:**
- Automatic backup before import
- Original save preserved
- Easy rollback if needed

**Warnings:**
- Shows if overwriting existing character
- Displays character being replaced
- Requires explicit confirmation

### Troubleshooting

**"Invalid .erc file"**
- File corrupted during download/transfer
- Wrong file type
- Incompatible version

**"Import failed"**
- Save file not loaded
- Target save corrupted
- File system error

**Character won't load in-game**
- SteamID patching failed (try SteamID Patcher)
- Event flag corruption (use Save Fixer)
- Restore from backup

---

## Swap Slots

Reorganize characters within the same save file.

### How It Works

**Process:**
2 character slots get swapped

### Steps

1. Select **Swap Slots** from the dropdown menu
2. Select Slot A and B
3. Click **Swap Slots**
4. Confirm

**Automatic backup created before move**

---

## Transfer to Another Save

Transfer character to another save file.

### Steps

1. Select **Transfer to Another Save** in the dropdown menu
2. Select your character
3. Click **Select Target Save** and select your target save file
4. Select the slot in your targets save file
5. confirm

### Automatic Adjustments

**SteamID:**
- Patched to target save's SteamID
- No manual patching needed

**Profile Summary:**
- Added to target save's profiles
- Playtime preserved
- Active slot marked

### Use Cases

- **Multiple Characters:** Spread across saves
- **Co-op:** Different saves for different groups
- **NG+ Prep:** Fresh save with prepared character
- **Backup Save:** Copy to backup save file

---

## Delete Character

Permanently remove character from slot.

### What Gets Deleted

**Character Data:**
- All stats and inventory
- Equipment and appearance
- Quest progress
- World state
- Event flags

**Profile Entry:**
- Removed from profile summary
- Active slot flag cleared
- Playtime data removed

**Result:** Slot becomes completely empty

### Steps

1. Select **Delete Character** from the dropdown
2. Select character slot to delete
3. Click **Delete Character**
4. Confirm

**Automatic backup created before deletion**

### Safety Features

**Confirmation Required:**
- Must type character name
- Prevents accidental deletion
- Clear warning message

**Automatic Backup:**
- Full save backup created
- Easy restore if mistake
- Stored in backup folder

**Validation:**
- Checks slot isn't already empty
- Verifies save is loaded
- Confirms write permission

### Recovery

**If deleted by mistake:**
1. Go to **Backup Manager** tab
2. Find backup before deletion
3. Click **Restore Backup**
4. Character restored

**Backup naming:**
```
ER0000_2026-02-15_14-30-00_delete.bak
```

---

## Safety & Backups

### Automatic Backups

**Created for:**
- Every import operation
- Every delete operation
- Every move operation
- Copy operations (source save)

**Backup naming:**
```
{save_name}_{date}_{time}_{operation}.bak
```

### Manual Backup

Before major operations:
1. Go to Backup Manager
2. Create manual backup
3. Add description
4. Proceed with operation

### Restore

If something goes wrong:
1. Open Backup Manager
2. Select backup before operation
3. Click Restore
4. Confirm restoration

---

## Troubleshooting

### Export Issues

**"Failed to export character"**
- Slot is empty (select different slot)
- Save file not fully loaded
- Write permission denied

**Exported file is corrupted**
- Try exporting again
- Check disk space
- Run disk check

### Import Issues

**"SteamID mismatch after import"**
- Use SteamID Patcher on imported character
- Or re-import (SteamID should auto-patch)

**"Character won't load in-game"**
1. Check with Save Fixer
2. Verify checksums
3. Try different slot
4. Restore from backup

### Move Issues

**"Destination slot not empty"**
- Slot contains character
- Export destination character first
- Or confirm overwrite

**"Move failed"**
- Source or destination corrupted
- Save not fully loaded
- Try export/import instead

---

## Related Features

- **[Backup Manager](backup-manager.md)** - Manage automatic backups
- **[SteamID Patcher](steamid-patcher.md)** - Fix SteamID issues
- **[Community Browser](character-browser.md)** - Share/download characters
- **[Save File Fixer](save-file-fixer.md)** - Fix corruption

---

## FAQ

**Q: Can I import a character multiple times?**  
A: Yes, into different slots or even different saves.

**Q: Can I edit .erc files?**  
A: Not directly.

**Q: What happens to quest flags?**  
A: Preserved in .erc, imported to new save. May cause quest issues.


---

[← Back to User Guide](../index.md) | [Next: Character Browser →](character-browser.md)