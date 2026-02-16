# Settings

Configure application behavior, backup options, and UI preferences.

## Overview

The Settings tab provides control over:

- General application settings
- Backup configuration (including auto-backup on game launch)
- UI theme and appearance
- Warning dialogs
- Update notifications

---

## Interface Layout

### Sections

**Three main sections:**

1. General Settings
2. Backup Settings  
3. UI Settings

**Reset to Defaults:**

- Button at top-right
- Restores all settings to default values

---

## General Settings

### EAC Warning

**Setting:** Show EAC warning when loading .sl2 files

**Default:** ON (checked)

**What it does:**

- Shows warning about Easy Anti-Cheat
- Reminds to use offline mode
- Prevents accidental online play with modified save

**When to disable:**

- You always play offline
- Understand EAC risks
- Don't want repeated warnings

### Remember Last Location

**Setting:** Remember last opened save file location

**Default:** ON (checked)

**What it does:**

- Saves last used folder
- Auto-navigates to last location when browsing
- Speeds up file selection

### Linux Save Location Warning

**Setting:** Show Linux save location warnings (non-default compatdata)

**Default:** ON (checked)

**What it does:**

- Warns when save file not in default Proton location
- Linux-specific warning
- Helps identify non-standard Steam installations

**When to disable:**

- Using custom Proton prefix intentionally
- Non-standard Steam location known and correct

**Platform:** Linux only

### Update Notifications

**Setting:** Show update notifications on startup

**Default:** ON (checked)

**What it does:**

- Checks for new versions on startup
- Shows notification if update available
- Links to download page

---

## Backup Settings

### Compress Backups

**Setting:** Compress backups (gzip) to save disk space

**Default:** ON (checked)

**What it does:**

- Compresses backup files with gzip
- Reduces size by ~90%
- Takes slightly longer to create/restore

**Storage Impact:**

- Uncompressed: ~26MB per backup
- Compressed: ~2-3MB per backup

**When to disable:**

- Prefer faster backup/restore
- Have plenty of disk space
- Want simple file handling

### Auto-Backup on Game Launch

**Setting:** Auto-backup when Elden Ring launches

**Default:** OFF (unchecked)

**What it does:**

- Monitors for Elden Ring process
- Creates automatic backup when game starts
- Protects against in-game corruption
- Runs in background

**How it works:**

1. Enable setting
2. Select save file to monitor
3. Tool monitors for game launch
4. Backup created when Elden Ring detected
5. Continues monitoring until disabled

**Requirements:**

- Save file must be selected
- Tool must be running
- Game process detectable

**Backup naming:**
```
ER0000_2026-02-15_18-30-00_game_launch.bak
```

### Save File Selection (Auto-Backup)

**Only visible when Auto-Backup enabled:**

- Dropdown showing current save path
- Select different save file
- Must be set for auto-backup to work

**Configuration:**

1. Enable "Auto-backup when Elden Ring launches"
2. Save file selection appears
3. Shows currently loaded save
4. Or select different save from dropdown
5. Backup monitors selected save

---

## UI Settings

### Theme

**Setting:** Application theme/appearance mode

**Options:**

- **Dark** (default)
- **Light**

**What it does:**

- Changes entire UI color scheme
- Dark: Dark background, light text
- Light: Light background, dark text

**Applied:** Application restart needed

---

## Settings Persistence

### How Settings Are Saved

**Storage location:**

- Windows: `%APPDATA%\EldenRingSaveManager\settings.json`
- Linux: `~/.local/share/EldenRingSaveManager/settings.json`

**Format:** JSON file

**When saved:**

- Immediately on change
- Persists between sessions
- Survives app updates

### Settings File Structure

```json
{
  "show_eac_warning": true,
  "remember_last_location": true,
  "show_linux_save_warning": true,
  "show_update_notifications": true,
  "compress_backups": true,
  "auto_backup_on_game_launch": false,
  "auto_backup_save_path": "",
  "theme": "dark"
}
```

---

## Reset to Defaults

### How to Reset

**Steps:**

1. Click **Reset to Defaults** button (top-right)
2. Confirm reset
3. All settings restored to defaults
4. Application may refresh UI

**What gets reset:**

- All general settings
- All backup settings
- All UI settings

**What doesn't reset:**

- Recent file history
- Backup files themselves
- Cache data

---

## Auto-Backup on Game Launch (Detailed)

### Setup

**Steps:**

1. Load your save file normally
2. Go to Settings tab
3. Check "Auto-backup when Elden Ring launches"
4. Select the save file you want to target
5. Setting saved

**Verification:**

- Checkbox stays checked
- Save path shows in dropdown
- Ready for monitoring

### How It Works

**Monitoring Process:**

1. Tool checks for Elden Ring process
2. When `eldenring.exe` is detected:
   - Creates backup of monitored save
   - Timestamps backup
   - Tags as "game_launch"
3. One backup per game session
4. Continues monitoring after game closes

**Background Operation:**

- Tool must remain running
- Minimized to tray works
- Works while tool in background

### Backup Location

**Same as manual backups:**
```
{save_name}.backups/
├── ER0000_2026-02-15_18-30-00_game_launch.bak
├── ER0000_2026-02-15_20-15-00_game_launch.bak
└── ...
```

### Disabling

**To stop auto-backup:**

1. Uncheck "Auto-backup when Elden Ring launches"
2. Monitoring stops immediately
3. Existing backups remain

---

## Troubleshooting

### "Settings not saving"

**Cause:** Permission issue or corrupted file

**Solutions:**

- Check write permissions
- Delete settings.json and restart
- Run without admin

### "Auto-backup not working"

**Cause:** Game not detected or save path wrong

**Solutions:**

- Verify save file selected
- Check game process name (eldenring.exe)
- Ensure tool running when game starts
- Try re-enabling setting

### "Theme not changing"

**Cause:** UI not refreshing

**Solution:**

- Restart application
- Force refresh (close/reopen tabs)
- Check theme setting persisted

---

## Related Features

- **[Backup Manager](backup-manager.md)** - Manage created backups
- **[Troubleshooting](troubleshooting-tab.md)** - Diagnose issues

---

## FAQ

**Q: Do settings sync across computers?**  
A: No, settings are local to each installation.

**Q: Can I backup settings file?**  
A: Yes, copy settings.json from application data folder.

**Q: Will reset delete my backups?**  
A: No, only resets settings. Backups untouched.

**Q: Does auto-backup work with modded game?**  
A: Yes, detects any Elden Ring process.

**Q: Can I set different themes per tab?**  
A: No, theme applies to entire application.

---

[← Gestures](gestures.md) | [Next: Troubleshooting →](troubleshooting-tab.md)