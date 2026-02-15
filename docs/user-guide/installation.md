# Installation

Get started with Elden Ring Save Manager on your platform.

---

## Windows

### Requirements
- Windows 10 or later
- No additional dependencies required

### Installation Steps

1. **Download** the latest release
   - Go to [Releases](https://github.com/Hapfel1/er-save-manager/releases)
   - Download `EldenRingSaveManager.exe`

2. **Run the executable**
   - No installation needed - it's a portable application
   - Double-click to launch

3. **Optional: Create shortcut**
   - Right-click `EldenRingSaveManager.exe` → Send to → Desktop

### Save File Location

Windows saves are located at:
```
%APPDATA%\EldenRing\<steamid>\ER0000.sl2
```

The tool auto-detects this location.

---

## Linux / Steam Deck

### Requirements
- FUSE (for AppImage)
- Steam or Proton compatibility layer

### Installation Steps

1. **Download** the latest release
   - Go to [Releases](https://github.com/Hapfel1/er-save-manager/releases)
   - Download `EldenRingSaveManager.AppImage`

2. **Make executable**
   ```bash
   chmod +x EldenRingSaveManager.AppImage
   ```

3. **Run**
   ```bash
   ./EldenRingSaveManager.AppImage
   ```

### FUSE Installation

If you get a FUSE error:

**Ubuntu/Debian:**
```bash
sudo apt install fuse
```

**Arch Linux:**
```bash
sudo pacman -S fuse2
```

**Fedora:**
```bash
sudo dnf install fuse
```

### Save File Location

**Native Steam:**
```
~/.steam/steam/steamapps/compatdata/1245620/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing/
```

**Flatpak Steam:**
```
~/.var/app/com.valvesoftware.Steam/.steam/steam/steamapps/compatdata/1245620/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing/
```

The tool auto-detects both paths.

### Steam Deck Specific

1. Switch to **Desktop Mode** (Steam button → Power → Switch to Desktop)
2. Follow Linux installation steps above
3. The tool detects Steam Deck environment automatically
4. Can be added to Steam as non-Steam game for Gaming Mode access

---

## macOS

**Status:** Not officially supported

The tool may work via Wine/Crossover but is untested. If you try it:
- Install Wine/Crossover
- Run the Windows .exe through Wine
- Save location will be in Wine prefix

Community feedback welcome!

---

## From Source

For developers or those who want the latest development version.

### Requirements

- Python 3.11 or later
- pip or uv package manager
- Git

### Installation

**Using uv (recommended):**
```bash
# Clone repository
git clone https://github.com/Hapfel1/er-save-manager.git
cd er-save-manager

# Create virtual environment and install
uv venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

# Install dependencies
uv pip install -e .
```

**Using pip:**
```bash
# Clone and enter directory
git clone https://github.com/Hapfel1/er-save-manager.git
cd er-save-manager

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install
pip install -e .
```

### Running

**GUI:**
```bash
python -m er_save_manager.ui.gui
```

**CLI:**
```bash
python -m er_save_manager.cli --help
```

See **[Building from Source](Building-from-Source)** for more details.

---

## Verification

After installation, verify the tool works:

1. **Launch** the application
2. Click **Auto-Detect** - should find your save file
3. Click **Load Save File**
4. If successful, you'll see your character list

If auto-detect fails, use **Browse** to manually locate your save file.

---

## Updating

### Portable Versions (Windows/Linux)

1. Download new version from Releases
2. Replace old executable/AppImage
3. Your settings and backups are preserved

### Source Installation

```bash
cd er-save-manager
git pull
pip install -e .  # or uv pip install -e .
```

---

## Troubleshooting

**"Application won't start" (Windows):**
- Install [Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
- Run as administrator
- Check antivirus isn't blocking

**"FUSE error" (Linux):**
- Install FUSE package (see above)
- Try running with `--appimage-extract-and-run` flag

**"Save file not found":**
- Use **Browse** button to manually locate save
- Check you have Elden Ring installed
- For Linux: verify Proton prefix path

**"Permission denied" (Linux):**
- Make sure AppImage is executable: `chmod +x`
- Check save file permissions

See **[Troubleshooting](Troubleshooting)** for more issues.

---

## Next Steps

- **[Quick Start Guide](Quick-Start-Guide)** - Learn the basics
- **[Save File Fixer](Save-File-Fixer)** - Fix infinite loading screens
- **[Character Editor](Character-Editor)** - Edit your character

---

[← Back to Home](Home)
