# Backup Manager

Comprehensive backup system with automatic and manual backups for complete save protection.

## Overview

The Backup Manager provides safety for all save file modifications through automatic and manual backup creation, with easy restore functionality.

**Features:**

- Automatic backups before any modification
- Manual backup creation with custom names
- Browse and restore previous backups
- Backup pruning with retention policies
- Locked backups the retention limit never removes
- Metadata tracking

The **Backup Manager** button in the top bar opens the Backup Manager window for the loaded save, in every supported game. It has **Create Backup**, **Restore**, **View Details**, **Delete**, **Open Folder** and **Refresh**, a **Sort by** choice and the backup list.

---

## Automatic Backups

### When Created

Automatic backups are created before any changes are written by the save manager

**Location:** `{save_file_name}.backups/` folder next to save file

### Backup Naming

```
{save_name}_{date}_{time}_{operation}.zip

Examples:
ER0000_2026-02-15_10-30-00_fix.zip
ER0000_2026-02-15_10-35-00_character_import.zip
ER0000_2026-02-15_11-00-00_steamid_patch.zip
```

### Metadata

Each backup includes:

- Timestamp (YYYY-MM-DD HH:MM:SS)
- Operation type (fix, edit, manual)
- Description
- File size

---

## Manual Backups

### Creating Manual Backups

1. Load save file
2. Click **Backup Manager** in the top bar
3. Click **Create Backup**
4. Enter a reason or name for the backup (optional)

---

## Backup List

### Viewing Backups

**List shows:**

- Filename
- Creation timestamp
- File size
- Description
- Operation type

**Sorted by:** Most recent first

### Locking Backups

Click the star of a backup to lock it. The backup limit in [Settings](settings.md) never removes locked backups.

### Deleting Backups

Select a backup and click **Delete**. Ctrl+click adds or removes single backups from the selection and Shift+click selects a range, so several backups can be deleted with one confirmation. Locked (starred) backups in the selection are kept. Restore and Details work on one selected backup.

### Backup Information

Select a backup and click **View Details** to see:

- Full metadata
- Character list with levels
- Exact file path
- Backup validity status

---

## Restoring Backups

### Full Restore

Replaces current save with selected backup.

**Steps:**

1. Select backup from list
2. Click **Restore**

**Result:** Save file replaced with backup state

### Safety Features

**Before restore:**

- Current save automatically backed up (skipped when the save file no longer exists)
- Shows characters that will be replaced
- Requires confirmation
- Refused while the game is running
- The backup being restored is never pruned by the backup limit

**Deleted save:** if the loaded save was deleted or moved, the editor shows a notice, and the
Backup Manager still opens from its backup folder; restoring a backup recreates the file.

**After restore:**

- Validates restored file
- Recalculates checksums if needed
- Verifies game can load

**Backup naming (safety):**
```
ER0000_2026-02-15_14-00-00_before_restore.zip
```

---

## Storage & Organization

### Backup Folder Structure

```
ER0000.co2.backups/
├── metadata.json
├── ER0000_2026-02-15_10-00-00_fix.zip
├── ER0000_2026-02-15_10-30-00_manual.zip
├── ER0000_2026-02-15_11-00-00_character_edit.zip
└── ...
```

A Dark Souls III PS4 save is a folder of `userdata` files. Its backups go to `userdata.backups/` in that folder, whichever userdata file was opened, and each backup zips every userdata file of the folder. Restoring writes all of them back.

### Disk Space

- Backups are zipped to a zip file by default to save disk space


---

## Troubleshooting

### "Backup folder not found"

**Cause:** Backup folder deleted or moved

**Solutions:**

- Backups are lost if folder deleted
- Create new manual backup
- Check recycle bin

### "Cannot restore backup"

**Cause:** Backup corrupted or incompatible

**Solutions:**

- Check the backup with **View Details**
- Try different backup
- Check file permissions
- Restore from earlier backup

### "Backup list is empty but backup files exist"

The backup list is stored in `metadata.json` in the backup folder. When it is unreadable or has
broken entries, the list is rebuilt from the backup files in the folder and the problem is written
to `errors.log` (see [Settings](settings.md#how-settings-are-saved)).

### "Auto-backup failed"

A failed auto-backup (save missing, backup folder not writable) shows an error notice naming the
game and is written to `errors.log`.

### "Out of disk space"

**Cause:** Too many backups

**Solutions:**

- Prune old backups
- Reduce retention count
- Move backups to external drive
- Delete unnecessary backups

Backups are written to a temporary file first, so a backup cut short by a full disk is removed instead of listed as valid.

---

## FAQ

**Q: Where are backups stored?**  
A: In `.backups` folder next to save file.

**Q: Can I restore from backup without the tool?**  
A: Yes, manually extract and copy the file.

**Q: Do backups include all 10 character slots?**  
A: Yes, complete save file backed up.

**Q: Can I share backups?**  
A: Yes, but SteamID will need patching for other accounts.

---

[← Troubleshooting](troubleshooting-tab.md) | [Next: Settings →](settings.md)