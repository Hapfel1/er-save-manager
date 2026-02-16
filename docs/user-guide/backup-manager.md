# Backup Manager

Comprehensive backup system with automatic and manual backups for complete save protection.

## Overview

The Backup Manager provides safety for all save file modifications through automatic and manual backup creation, with easy restore functionality.

**Features:**
- Automatic backups before any modification
- Manual backup creation with custom names
- Browse and restore previous backups
- Backup pruning with retention policies
- Backup verification
- Metadata tracking

---

## Automatic Backups

### When Created

Automatic backups are created before any changes are written by the save manager

**Location:** `{save_file_name}.backups/` folder next to save file

### Backup Naming

```
{save_name}_{date}_{time}_{operation}.bak

Examples:
ER0000_2026-02-15_10-30-00_fix.bak
ER0000_2026-02-15_10-35-00_character_import.bak
ER0000_2026-02-15_11-00-00_steamid_patch.bak
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
2. Go to **Backup Manager** tab
3. Click **Create Backup**
4. Enter optional description
5. Backup created with timestamp

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

### Backup Information

Click any backup to view:
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
2. Click **Restore Backup**
3. Review what will be replaced
4. Confirm restoration
5. Current save backed up first
6. Backup restored

**Result:** Save file replaced with backup state

### Safety Features

**Before restore:**
- Current save automatically backed up
- Shows characters that will be replaced
- Requires confirmation

**After restore:**
- Validates restored file
- Recalculates checksums if needed
- Verifies game can load

**Backup naming (safety):**
```
ER0000_2026-02-15_14-00-00_before_restore.bak
```

---

## Storage & Organization

### Backup Folder Structure

```
ER0000.co2.backups/
├── metadata.json
├── ER0000_2026-02-15_10-00-00_fix.bak
├── ER0000_2026-02-15_10-30-00_manual.bak
├── ER0000_2026-02-15_11-00-00_character_edit.bak
└── ...
```

### Disk Space

- Backups are zipped to a gz file by default to save disk space


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
- Verify backup first
- Try different backup
- Check file permissions
- Restore from earlier backup

### "Out of disk space"

**Cause:** Too many backups

**Solutions:**
- Prune old backups
- Reduce retention count
- Move backups to external drive
- Delete unnecessary backups

---

## FAQ

**Q: Where are backups stored?**  
A: In `.backups` folder next to save file.

**Q: Can I restore from backup without the tool?**  
A: Yes, manually extract and copy the .backup file and rename it.

**Q: Do backups include all 10 character slots?**  
A: Yes, complete save file backed up.

**Q: Can I share backups?**  
A: Yes, but SteamID will need patching for other accounts.

---

[← Troubleshooting](troubleshooting-tab.md) | [Next: Settings →](settings.md)