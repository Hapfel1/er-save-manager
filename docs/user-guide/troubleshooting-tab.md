# Troubleshooting & Diagnostics

Automated diagnostic system for detecting game, save file, and system issues.

## Overview

The Troubleshooting tab runs comprehensive diagnostic checks:
- Game installation validation
- Save file integrity checks
- Steam configuration issues
- Interfering software detection
- Network/VPN detection
- System configuration problems

**Purpose:** Identify and help resolve common issues preventing game from launching or loading saves.

---

## Opening Troubleshooting

### Access

**Location:** Troubleshooting tab in main interface

### Interface

**Layout:**
- Title: "Troubleshooting & Diagnostics"
- Refresh button (re-run checks)
- Scrollable results list
- Close button

---

## Running Diagnostics

### Automatic Check

**On opening:**
1. Dialog displays "Running diagnostic checks..."
2. All checks execute
3. Results populate list
4. Shows status for each check

### Manual Refresh

**Re-run checks:**
1. Click **Refresh** button
2. Clears previous results
3. Runs all checks again
4. Updates with new results

---

## Diagnostic Results

### Result Format

**Each check displays:**
- **Status Icon:**
  - ✅ OK (green)
  - ⚠️ Warning (yellow)
  - ❌ Error (red)
  - ℹ️ Info (blue)
- **Check Name**
- **Status Message**

### Result Types

**OK (✅):**
- Check passed
- No action needed
- System working correctly

**Warning (⚠️):**
- Potential issue detected
- May not be critical
- Recommended to review

**Error (❌):**
- Problem detected
- Likely causing issues
- Action required

**Info (ℹ️):**
- Informational message
- No problem detected
- Helpful context

---

## Diagnostic Categories

### Game Installation Checks

**What's checked:**
- Game files present
- Install directory valid
- Game executable exists
- File integrity
- Version detection

**Common issues:**
- Missing game files
- Corrupted installation
- Wrong directory selected

**Fixes:**
- Verify game files in Steam
- Reinstall game
- Check game path

### Steam Configuration Checks

**What's checked:**
- Steam running
- Steam location correct
- Elevated privileges (admin mode)

**Common issues:**
- Steam running as admin (causes issues)

### Save File Checks

**What's checked:**
- Save file present
- Correct format
- File size valid
- Checksum integrity
- Version compatibility

**Common issues:**
- Corrupted save
- Wrong file format
- Checksum mismatch
- Version incompatible

**Fixes:**
- Run Save File Fixer
- Restore from backup

### Interfering Software Checks

**What's checked:**
- Anti-cheat software
- Antivirus conflicts
- Overlay software
- Screen capture tools
- RGB control software

**Common issues**
- Certain software blocking the modded game from launching

### Network Checks

**What's checked:**
- Running VPNs

---


## Related Features

- **[Save File Fixer](save-file-fixer.md)** - Fix detected save issues
- **[Settings](settings.md)** - Configure application
- **[Backup Manager](backup-manager.md)** - Restore from backups

---

## FAQ

**Q: How long do diagnostics take?**  
A: Usually 30-60 seconds for all checks.

**Q: Can diagnostics fix issues automatically?**  
A: Some issues, yes. Others require manual intervention.

**Q: Do I need to run diagnostics every time?**  
A: No, only when experiencing problems or after updates.

**Q: Will diagnostics modify my save?**  
A: No, diagnostics are read-only. Fixes require confirmation.

**Q: Can I skip checks I don't care about?**  
A: Currently all checks run together. Future may allow selective checks.

---

[← Settings](settings.md) | [EAC Warning →](eac-warning.md)