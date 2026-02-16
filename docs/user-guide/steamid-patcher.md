# SteamID Patcher

Transfer saves between Steam accounts by patching the SteamID throughout the save file.

## Overview

Elden Ring saves are tied to a SteamID. If the ID in the save doesn't match the account loading it, the game will refuse to load it. This tool rewrites the SteamID throughout the save file so it works on the target account.

---

## Setup

1. Download the [ER Save File Manager](https://www.nexusmods.com/eldenring/mods/9271)
2. Unpack the archive and run the executable
3. Load your save file using the **Browse** button, or let the tool find it automatically with **Auto-Find**
4. Switch to the **SteamID Patcher** tab

---

## Before You Start

Make sure the save file is fully loaded — the current SteamID will be displayed under **Current Save File** at the top of the tab.

A backup is created automatically before any patch is applied. You can restore it from the Backup Manager if anything goes wrong.

---

## Getting the Target SteamID

### Method 1 — Auto-Detect

Click **Auto-Detect**. The tool scans your system for logged-in Steam accounts.

If multiple accounts are found, a picker appears — select the correct one and the SteamID field is filled automatically.

Best used when patching to your own account or one that has been logged in on the same PC.

### Method 2 — Steam Profile URL

1. Open the target Steam profile in a browser and copy the URL
2. Paste it into the **Steam profile URL** field
3. Click **Parse URL**

Supported formats:
```
https://steamcommunity.com/profiles/76561198012345678
https://steamcommunity.com/id/username
```

### Method 3 — Manual Entry

Enter the 17-digit SteamID64 directly into the SteamID field and proceed to patching.

The ID must be exactly 17 digits, no spaces. Example: `76561198012345678`

---

## Applying the Patch

1. Once the SteamID field is filled, click **Patch SteamID**
2. A confirmation dialog shows the ID being written — confirm to proceed
3. A success message confirms how many slots were patched and shows the old vs. new SteamID

---

## After Patching

Copy the patched save file to the target account's Elden Ring save directory.

Default location on Windows:
```
%AppData%\EldenRing\<SteamID>\
```

The folder name must match the new SteamID. Launch the game on the target account — the save should load normally.

---

## Troubleshooting

**"SteamID must be exactly 17 digits"**  
Verify the number. SteamID64 is always 17 digits and starts with `7656119`.

**Custom `/id/` URL didn't resolve**  
The lookup requires internet access. Use a `/profiles/` URL instead, or enter the ID manually.

**Game still won't load the save after patching**  
Check that the save file is placed in the folder named after the new SteamID, not the original one.

**Something went wrong during patching**  
Open the Backup Manager and restore the backup created before the patch.

---

## Technical Details

### What Gets Patched

**SteamID locations in save file:**
1. USER_DATA_10 header (master SteamID)
2. Each character slot (10 total)
3. Profile summary metadata

**Total patches:** 11 SteamID instances

### Validation

**Before patching:**
- Verifies SteamID format (17 digits)
- Checks save file loaded
- Confirms write permission

**After patching:**
- Recalculates all checksums
- Validates new SteamID written
- Verifies save integrity

---

[← Character Browser](character-browser.md) | [Next: Event Flags →](event-flags.md)