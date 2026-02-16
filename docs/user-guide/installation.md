# Installation

Get started with the Elden Ring Save Manager on your platform.

---

## Windows

### Requirements
- Windows 10 or later
- No additional dependencies required

### Installation Steps

1. **Download** the latest release
   - Go to [Releases](https://github.com/Hapfel1/er-save-manager/releases)
   - Download the Windows zip
   - Extract it

2. **Run the executable**
   - No installation needed - it's a portable application
   - Double-click to launch

3. **Optional: Create shortcut**
   - Right-click `Elden Ring Save Manager.exe` → Send to → Desktop

### Save File Location

Windows saves are located at:
```
%APPDATA%\EldenRing\<steamid>\ER0000.sl2/co2
```

The tool auto-detects this location.

---

## Linux / Steam Deck

### Installation Steps

1. **Download** the latest release
   - Go to [Releases](https://github.com/Hapfel1/er-save-manager/releases)
   - Download the Linux zip
   - Extract it

2. **Run the AppImage**
   - The AppImage should be executable by default, just run it

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

## From Source

For developers or those who want the latest development version.

### Requirements

- Python 3.13 or later
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

# Setup
uv sync --locked --dev
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

# Setup
uv sync --locked --dev
```

### Running

```bash
uv run python run_gui.py
```

See the [Contributing](../developer/contributing.md) guide for build details.

---

## Verification

After installation, verify the tool works:

1. **Launch** the application
2. Click **Auto-Detect** - should find your save file
3. Select the correct file
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

**Windows protected your PC**

- Click **More info** and then **Run anyway**
- This is the default warning by Windows for any unsigned executables. Signing an executable costs too much for it to be worth it.

**"Application won't start" (Windows):**

- Install [Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
- Check antivirus isn't blocking it

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

See [Troubleshooting](troubleshooting-tab.md) for more issues.

---

## Next Steps

- **[Save File Fixer](save-file-fixer.md)** - Fix infinite loading screens
- **[Character Editor](character-editor.md)** - Edit your character

---

[← Back to Home](../index.md)