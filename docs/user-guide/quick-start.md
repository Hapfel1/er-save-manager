# Quick Start Guide

Get up and running with Elden Ring Save Manager in minutes.

---

## First Launch

### 1. Open the Application

Launch the Elden Ring Save Manager executable or AppImage.

### 2. Load Your Save File

**Option A: Auto-Detect (Recommended)**
1. Click **Auto-Detect** button
2. Tool scans standard save locations
3. Save file loaded automatically if found

**Option B: Manual Browse**
1. Click **Browse** button
2. Navigate to your save file location
3. Select `ER0000.sl2` (PC) or `ER0000.co2` (PlayStation)
4. Click **Open**

### 3. Load and View Characters

1. Click **Load Save File** button
2. Wait for parsing (takes 2-5 seconds)
3. Character list appears showing all slots

You'll see:
- Character name
- Level
- Playtime
- Current location
- Status (OK or ISSUES detected)

---

## Common Tasks

### Fix Infinite Loading Screen

**Quick Fix:**
1. Go to **Save File Fixer** tab
2. Click **Scan for Issues**
3. Review detected problems
4. Click **Fix All**
5. Click **Save** (automatic backup created)
6. Test in-game

**See:** [Save File Fixer Guide](Save-File-Fixer)

---

### Export a Character

**Steps:**
1. Load your save file
2. Go to **Character Management** tab
3. Select the character slot (1-10)
4. Click **Export Character**
5. Choose filename and location
6. Save as `.erc` file

**Use Cases:**
- Backup specific character
- Share character with friends
- Move character to another save

**See:** [Character Management Guide](Character-Management)

---

### Change Character Stats

**Steps:**
1. Load save file
2. Go to **Character Editor** tab
3. Select character slot
4. Modify stats:
   - Vigor, Mind, Endurance
   - Strength, Dexterity, Intelligence
   - Faith, Arcane
5. Edit runes or name (optional)
6. Click **Apply Changes**
7. Click **Save**

**Note:** Level automatically recalculates based on stats.

**See:** [Character Editor Guide](Character-Editor)

---

### Respawn a Boss

**Steps:**
1. Load save file
2. Go to **Boss Respawner** tab
3. Select character slot
4. Search for boss name or browse list
5. Click **Respawn Boss**
6. Click **Save**
7. Boss is alive again in-game

**See:** [Boss Respawner Guide](Boss-Respawner)

---

### Create Manual Backup

**Steps:**
1. Load save file
2. Go to **Backup Manager** tab
3. Click **Create Backup**
4. Enter description (optional)
5. Backup created with timestamp

**Automatic Backups:**
Every save operation creates an automatic backup. You'll never lose progress.

**See:** [Backup Manager Guide](Backup-Manager)

---

### Browse Community Characters

**Download a Character:**
1. Go to **Community** tab
2. Select **Character Browser**
3. Browse or search for builds
4. Click character to view details
5. Click **Download**
6. Select target slot in your save
7. Character imports automatically

**Upload Your Character:**
1. Load save with character to share
2. Go to **Community** tab → **Character Browser**
3. Click **Upload**
4. Fill in details (name, description, build type)
5. Review preview
6. Click **Submit**

**See:** [Community Browser Guide](Community-Browser)

---

## Understanding the Interface

### Main Window

**Top Bar:**
- File path display
- Load/Save buttons
- Settings button

**Tabs:**
- Save File Fixer
- Character Management
- Character Editor
- Appearance Editor
- Community
- Event Flags
- Boss Respawner
- Gestures & Regions
- Backup Manager
- Troubleshooting

**Character List:**
Shows all 10 slots with status indicators:
- ✓ Green: No issues
- ⚠ Yellow: Minor issues
- ✗ Red: Critical corruption

### Status Indicators

**Save File Status:**
- "Loaded" - Save parsed successfully
- "Parsing..." - Currently loading
- "Error" - Failed to load

**Backup Status:**
- Shows last backup time
- Displays backup count

---

## Safety Features

### Automatic Backups

**Every operation creates a backup:**
- Character edits
- Corruption fixes
- SteamID patching
- Event flag changes
- Appearance modifications

**Backup Location:**
```
{save_file_name}.backups/
```

### Validation

**Automatic checks before saving:**
- Stat ranges valid
- Checksum calculation
- File integrity
- Version compatibility

**If validation fails:**
- Error message displayed
- Changes not saved
- Original file untouched

---

## Tips for Beginners

### 1. Always Backup First
Before experimenting, create a manual backup:
- Go to Backup Manager
- Create Backup
- Add description like "before testing"

### 2. Test Small Changes
- Start with simple edits (e.g., +10 Vigor)
- Test in-game
- Build confidence before major changes

### 3. Use Scan Before Save
Before saving, scan for issues:
- Save File Fixer tab
- Scan for Issues
- Fix any problems found

### 4. Keep Backups Organized
Use descriptive names:
- "before_pvp_build"
- "pre_dlc"
- "level_150_quality_build"

### 5. Learn Event Flags Gradually
Event flags are powerful but complex:
- Start with simple flags (unlock graces)
- Test each change
- Document what you toggle

---

## Common Workflows

### Workflow: Respec Character

Want to change your build?

1. **Load save** → select character
2. **Character Editor** tab
3. Lower unwanted stats
4. Raise desired stats
5. Level recalculates automatically
6. **Apply** and **Save**

### Workflow: Practice Boss Fight

Want to fight a boss again?

1. **Load save** → select character
2. **Boss Respawner** tab
3. Search for boss
4. **Respawn Boss**
5. **Save**
6. Boss alive in-game

### Workflow: Share Your Build

Want to share with community?

1. **Load save** → select character
2. **Community** tab → **Character Browser**
3. **Upload**
4. Fill details (stats shown automatically)
5. Add description of playstyle
6. **Submit**

### Workflow: Transfer Save to New PC

Moving to new computer?

1. **Export all characters** (Character Management)
2. Copy `.erc` files to new PC
3. Install tool on new PC
4. Create new save or use existing
5. **Import characters** one by one
6. **SteamID Patcher** → patch to new Steam account
7. **Save**

---

## Keyboard Shortcuts

**Main Window:**
- `Ctrl+O` - Open save
- `Ctrl+S` - Save current
- `Ctrl+B` - Create backup
- `Ctrl+R` - Reload
- `Ctrl+Q` - Quit

**Editors:**
- `Ctrl+Z` - Undo
- `Ctrl+A` - Apply changes
- `Esc` - Cancel

See **[Keyboard Shortcuts](Keyboard-Shortcuts)** for complete list.

---

## Getting Help

### In-App Help

- Hover tooltips on buttons/fields
- Status bar shows context help
- Error messages include solutions

### Documentation

- Check specific feature guides
- Read Technical Documentation for deep dives
- Browse FAQ

### Community Support

- [GitHub Issues](https://github.com/Hapfel1/er-save-manager/issues) - Bug reports
- [Discussions](https://github.com/Hapfel1/er-save-manager/discussions) - Questions
- Community Discord (if available)

---

## What's Next?

Now that you're familiar with basics:

### Learn Core Features
- **[Save File Fixer](Save-File-Fixer)** - Essential for corrupted saves
- **[Character Editor](Character-Editor)** - Customize your character
- **[Event Flags](Event-Flags)** - Advanced game state control

### Explore Advanced Features
- **[Appearance Editor](Appearance-Editor)** - Create unique looks
- **[Community Browser](Community-Browser)** - Share and download
- **[Troubleshooting Tab](Troubleshooting-Tab)** - Diagnose issues

### Understand the System
- **[Save File Structure](Save-File-Structure)** - How saves work
- **[Event Flag System](Event-Flag-System)** - Flag mechanics
- **[Backup System](Backup-System-Technical)** - Backup internals

---

## FAQ Quick Answers

**Q: Will I get banned for using this?**  
A: Save editing is client-side. However, using edited saves in PvP violates ToS. Use responsibly.

**Q: Can I undo changes?**  
A: Yes! Every operation creates automatic backup. Use Backup Manager to restore.

**Q: Does this work with mods?**  
A: Yes, including special support for Convergence mod.

**Q: Can I edit inventory?**  
A: Limited. Full inventory editor in development. Use event flags to unlock items.

**Q: Is this safe?**  
A: Tool is safe. Always backup before edits. Test changes incrementally.

See **[FAQ](FAQ)** for more questions.

---

[← Back to Home](Home) | [Next: Save File Fixer →](Save-File-Fixer)
