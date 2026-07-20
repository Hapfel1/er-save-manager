# Save File Fixer

Automatically detect and repair common save corruption issues that cause infinite loading screens.

## Overview

The Save File Fixer scans your save file for known corruption patterns and provides one-click fixes. It's the most essential feature when dealing with infinite loading screens or corrupted saves.

**When to Use:**

- Game stuck on infinite loading screen
- Save file won't load
- Character appears corrupted
- After modding gone wrong
- After save transfer between PCs

---

## Supported Fixes

### 1. Torrent Bug

**Symptom:** Infinite loading screen, often after dying on horseback

**Cause:** Torrent HP = 0 while state = ACTIVE

**Fix Applied:**

- Sets Torrent HP to maximum
- Sets Torrent state to INACTIVE
- Clears invalid horse state flags

### 2. SteamID Mismatch

**Symptom:** Save won't load, shows as corrupted

**Cause:** Character SteamID doesn't match save file header

**Fix Applied:**

- Reads SteamID from USER_DATA_10
- Copies to each character slot
- Recalculates checksums

### 3. Weather Sync

**Symptom:** Corruption error

**Cause:** AreaID doesn't match current map location

**Fix Applied:**

- Reads current MapId
- Updates AreaID from MapId[3]
- Syncs weather data

### 4. Time Sync

**Symptom:** Corruption Error

**Cause:** Time desynchronized from actual playtime

**Fix Applied:**

- Reads seconds_played from profile
- Calculates hours:minutes:seconds
- Updates in-game time fields

### 5. Ranni Softlock

**Symptom:** Cannot progress Ranni's quest, tower remains locked

**Cause:** Event flag corruption in quest progression

**Fix Applied:**

- Identifies quest stage
- Resets flag 1034500738
- Corrects 31 progression flags
- Restores proper quest state

### 6. Warp Sickness

**Symptom:** Stuck at boss warp location

**Variants:**

- Radahn (Festival active/inactive)
- Morgott
- Radagon
- Sealing Tree

**Fix Applied:**

- Detects warp type from flags
- Clears specific warp flags
- Removes stuck warp state
- Teleports if needed

### 7. DLC Coordinate Stuck

**Symptom:** Infinite loading after attempting DLC access without ownership

**Cause:** Character at DLC coordinates without DLC flag

**Fix Applied:**

- Detects DLC map coordinates
- Teleports to Roundtable Hold
- Clears partial DLC data
- Preserves other progress

### 8. DLC Flag

**Symptom:** Cannot load character after DLC area visit

**Cause:** DLC entry flag set without DLC ownership

**Fix Applied:**

- Clears Shadow of the Erdtree entry flag
- Preserves other DLC data
- Maintains non-DLC progress

### 9. Invalid DLC Data

**Symptom:** Save won't load due to garbage data

**Cause:** Corrupted data in unused DLC slots [3-49]

**Fix Applied:**

- Zeroes out slots 3-49
- Preserves valid DLC data
- Maintains slot 0-2 data

### 10. Teleport Fallback

**Symptom:** Any other invalid coordinates causing infinite loading

**Cause:** Unknown location issues

**Fix Applied:**

- Emergency teleport to Roundtable Hold
- Safe coordinates guaranteed
- Last resort when other fixes don't work

### 11. Slot Checksum

**Symptom:** Save won't load, no other issue detected

**Cause:** The 16-byte MD5 checksum stored before a character slot doesn't match the slot's actual data. The game refuses to load a slot with an invalid checksum.

**Fix Applied:**

- Recalculates the MD5 over the slot's data region
- Writes the new checksum immediately before the slot

This fix runs as a final integrity pass, since any edit that changes slot bytes invalidates the existing checksum.

### 12. Deep Scan (Torn Write)

**Symptom:** A character slot loads with a valid checksum but the character is reset, has zeroed stats, or is otherwise blank

**Cause:** A torn write during a previous save inserted or removed bytes partway through the slot instead of overwriting it cleanly. Everything after the tear point is shifted, so the offsets the parser expects no longer line up with the actual data - the slot still hashes correctly because the checksum was computed over the shifted, internally consistent bytes.

**Fix Applied:**

- Locates the character's SteamID64 inside the raw slot bytes and walks backward through fixed-size trailing structures (NetMan, WorldAreaWeather, WorldAreaTime, BaseVersion) to find where NetMan actually starts
- Compares that against where NetMan should start based on the event flags region and other sized structures
- The difference between expected and actual position is the shift amount (the delta)
- Cuts or pads the save right after the event flags region to correct the shift
- Re-parses the corrected slot to confirm it is valid

**Result includes:**

- Shift delta in bytes
- Tear location
- Confidence level for the detected shift

This is currently the primary fix for the character slot corruption seen with Convergence and me3, where a pre-existing FromSoftware race condition during slot writes is amplified by heap churn from the `oversized_regulation_fix_after_er` hook.

---

## Usage

### Automatic Scan

1. Load your save file
2. Navigate to **Save Fixer** tab
3. Select your character in the list
4. Click **View All Issues**
5. Review detected problems in list

### Fix All at Once

1. After scanning, click **Fix All**
2. Confirm action
3. All detected issues fixed automatically
4. Automatic backup created before fixing

---

## Interface

### Scan Results

**List shows:**

- Issue name and type
- Severity (Critical/Warning/Info)
- Affected character slot
- Brief description
- Recommended action
---

## Examples

### Example 1: Infinite Loading After Death

**Scenario:** Character stuck loading after dying on Torrent

**Steps:**

1. Load save file
2. Scan for issues
3. **Detected:** "Torrent Bug - HP=0, State=ACTIVE"
4. Click Fix All
5. Save file

**Result:** Torrent HP restored, character loads normally

---

### Example 2: Save Won't Load After PC Transfer

**Scenario:** Copied save to new PC, won't load

**Steps:**

1. Load save file
2. Scan for issues
3. **Detected:** "SteamID Mismatch in slots 1, 2, 4"
4. Go to SteamID Patcher tab first
5. Patch SteamID to new account
6. Return to Fixer, rescan
7. Fix any remaining issues

**Result:** Save loads on new PC with correct Steam account

---

### Example 3: Multiple Issues

**Scenario:** Modded save with several corruptions

**Steps:**

1. Load save file
2. Scan for issues
3. **Detected:**
   - Torrent bug
   - Weather sync issue
   - Time sync issue
4. Click Fix All
5. Enable "Teleport to Roundtable"
6. Save file

**Result:** All issues resolved, character at safe location

---

## Safety Features

### Automatic Backup

**Every fix operation creates backup:**

- Timestamp included
- Original file preserved
- Metadata tracked
- Easy restore if needed

**Backup location:** `{save_name}.backups/`

### Validation

**Before applying fixes:**

- Verifies save integrity
- Checks for additional issues
- Validates fix compatibility
- Confirms changes are safe

**After applying fixes:**

- Recalculates checksums
- Validates new data
- Checks for new corruption
- Confirms save loads

### Rollback

If fix causes issues:

1. Go to Backup Manager tab
2. Select backup before fix
3. Click Restore
4. Original state restored

---

## Troubleshooting

### "No issues detected" but still won't load

**Possible causes:**

- Issue not yet detected by tool
- Corruption in unscanned area
- Hardware/game file issue

**Solutions:**

1. Try Teleport Fallback fix manually
2. Export characters to new save
3. Verify game files in Steam
4. Check [Troubleshooting Tab](troubleshooting-tab.md)

### Fix applied but issue persists

**Possible causes:**

- Character is corrupted beyond the tools functionality to fix it
- Fix didn't fully apply

**Solutions**
If the tool does not help at all, feel free to contact me on Discord, server link: https://dsc.gg/er-saveman

---

## Related Features

- **[Backup Manager](backup-manager.md)** - Manage backups created by fixer
- **[SteamID Patcher](steamid-patcher.md)** - Fix SteamID issues
- **[Troubleshooting Tab](troubleshooting-tab.md)** - Additional diagnostics
- **[Event Flags](event-flags.md)** - Manual flag manipulation

---

## FAQ

**Q: Will fixes work on modded saves?**  
A: Yes, but mod-specific issues may not be detected.

**Q: Can I undo a fix?**  
A: Yes, restore from automatic backup.

**Q: What if my issue isn't detected?**  
A: Try Teleport Fallback or report new issue type.

**Q: Are fixes safe for PvP?**  
A: Fixes restore valid game state. No cheats involved.

---

[← Back to Home](../index.md) | [Next: Character Management →](character-management.md)
