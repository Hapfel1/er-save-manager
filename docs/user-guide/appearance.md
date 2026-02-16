# Appearance & Presets

Manage character appearance with 15 preset slots - view, export, import, and share appearance data.

## Overview

The Appearance tab manages character appearance presets stored in your save file:
- 15 preset slots available
- View preset details (face, body, colors)
- Export presets to JSON files
- Import presets from JSON files
- Copy presets to other saves
- Browse and download community presets

**When to Use:**
- Save favorite character appearances
- Share appearances with friends
- Transfer appearances between characters
- Download community-created presets
- Back up appearance before changing

---

## Interface Layout

### Preset List

**Displays all 15 slots:**
- Preset slot number (1-15)
- Status: "Empty" or "Preset X"
- Selection indicator (highlighted when selected)

**Selection:**
- Click preset to select
- Selected preset highlighted
- One preset selected at a time

### Action Buttons

**Main Actions:**
- **View Details** - View complete preset data
- **Export to JSON** - Save preset to file
- **Import from JSON** - Load preset from file
- **Delete Preset** - Clear selected preset slot
- **Copy to Another Save** - Transfer to different save file
- **Browse Community Presets** - Open community browser

---

## Preset Slots

### What Are Preset Slots?

The save file contains 15 appearance preset storage slots:
- Used for quick appearance changes at Mirror
- Store face and body customization
- Independent of active characters
- Shared across all characters in save

### Slot Status

**Empty Slot:**
- Shows as "(Empty)"
- Can import preset
- Can be populated from community

**Occupied Slot:**
- Shows as "Preset X"
- Contains appearance data
- Can be viewed/exported/deleted

---

## Viewing Preset Details

### How to View

1. Select preset from list
2. Click **View Details**
3. Dialog shows complete preset data

### Details Displayed

**Face Structure:**
- Face model selection
- Age appearance
- Facial aesthetic value
- 40+ bone structure parameters
  - Brow ridge, cheekbones, jaw, chin, nose, mouth, eyes

**Colors:**
- Skin color (RGB + luster + pores)
- Left eye color
- Right eye color
- Hair color
- Beard color (if applicable)
- Eyebrow color
- Eyeliner color
- Eye shadow color
- Lipstick color

**Hair/Facial Hair:**
- Hair model
- Eyebrow model
- Beard model
- Eyelashes
- Stubble

**Body:**
- Head size
- Chest size
- Abdomen size
- Arm thickness
- Leg thickness
- Body proportions

**Additional:**
- Tattoo/marking selection
- Cosmetic adjustments

---

## Exporting Presets

### Export to JSON

Creates human-readable JSON file with all preset data.

**Steps:**
1. Select preset slot
2. Click **Export to JSON**
3. Choose save location
4. Enter filename
5. JSON file created

### JSON Structure

```json
{
  "version": 1,
  "format": "elden_ring_face_preset",
  "face_model": 5,
  "hair_model": 12,
  "eyebrow_model": 3,
  "beard_model": 0,
  "apparent_age": 128,
  "facial_aesthetic": 128,
  "bone_structure": {
    "brow_ridge_height": 128,
    "inner_brow_ridge": 128,
    ...
  },
  "body": {
    "head_size": 128,
    "chest_size": 128,
    ...
  },
  "colors": {
    "skin_color_r": 200,
    "skin_color_g": 180,
    "skin_color_b": 170,
    ...
  }
}
```

### Use Cases

**Sharing:**
- Send to friends
- Upload to community
- Post in Discord/Reddit

**Backup:**
- Before changing appearance
- Archive favorite looks
- Store build-specific appearances

**Editing:**
- Manual tweaking in text editor
- Batch modifications
- Custom color schemes

---

## Importing Presets

### Import from JSON

Loads preset from JSON file into selected slot.

**Steps:**
1. Select target preset slot (empty or occupied)
2. Click **Import from JSON**
3. Browse to `.json` file
4. Confirm import
5. Preset loaded into slot

### What Gets Imported

**Complete appearance data:**
- All facial parameters
- All color values
- Body proportions
- Hair/facial hair selections

**Automatic backup created before import**

### Validation

**Before import:**
- Checks JSON format
- Verifies version compatibility
- Validates value ranges

**After import:**
- Preset stored in save
- Available at Mirror in-game
- Changes saved

---

## Deleting Presets

### Delete Preset

Clears selected preset slot, making it empty.

**Steps:**
1. Select preset to delete
2. Click **Delete Preset**
3. Confirm deletion
4. Slot becomes empty

**Safety:**
- Confirmation required
- Automatic backup created
- Can restore from backup

---

## Copy to Another Save

### Cross-Save Preset Transfer

Copy preset from current save to different save file.

**Steps:**
1. Load source save file
2. Select preset slot to copy
3. Click **Copy to Another Save**
4. Select target save file
5. Choose target preset slot
6. Confirm copy

**Result:**
- Preset exists in both saves
- Source unchanged
- Target slot populated

---

## Community Preset Browser

### Browse Community Presets

Access community-shared appearance presets.

**Steps:**
1. Click **Browse Community Presets**
2. Browser dialog opens
3. Browse or search presets
4. Select preset
5. Download to preset slot

### Browser Features

**Browsing:**
- Grid view with preview images
- Face preview (front view)
- Body preview (full character)
- Preset name and description
- Like count, download count
- Uploader name

**Filters:**
- Search by name
- Filter by popularity
- Sort by downloads
- Recent uploads

**Actions:**
- Download to slot
- Like preset
- Report inappropriate content

### Downloading from Community

**Steps:**
1. Find preset in browser
2. Click preset to view details
3. Click **Download**
4. Select target preset slot
5. Preset downloaded and imported

**What You Get:**
- Complete appearance data
- Ready to use at Mirror
- Local copy in your save

### Uploading to Community

**GitHub Account needed!**

**Steps:**
1. Select the **Contribute** tab
2. Select your preset slot
3. Fill in details:
   - Preset name
   - Description
   - Tags
4. Attach images
5. Click **Submit**, a browser window will open where you have to drag the generated zip archive in.
6. Click **Create** on the prefilled Issue in gitHub and wait for a maintainer to review and merge it

**Guidelines:**
- Original creations preferred
- Clear, appropriate preview images
- Accurate descriptions

---

## In-Game Usage

### Using Presets at Mirror

**In Elden Ring:**
1. Visit Mirror of the Roundtable
2. Select "Cosmetics"
3. Choose "Load Preset"
4. Your saved presets appear (1-15)
5. Select preset to apply

---

## Troubleshooting

### "Cannot export preset"

**Cause:** Slot is empty

**Solution:**
- Select occupied preset slot
- Verify slot contains data

### "Import failed"

**Cause:** Invalid JSON file

**Solutions:**
- Check JSON file format
- Verify not corrupted
- Re-download if from community
- Try different slot

### "Preset not showing in-game"

**Cause:** Changes not saved

**Solutions:**
1. Verify import completed
2. Save file after import
3. Reload save in game
4. Check correct save file loaded

### "Community browser won't load"

**Cause:** Connection issue

**Solutions:**
- Check internet connection
- Verify server status
- Try again later
- Clear cache in settings

---

## Related Features

- **[Character Management](character-management.md)** - Export complete characters
- **[Community Browser](character-browser.md)** - Browse full character builds
- **[Backup Manager](backup-manager.md)** - Restore if issues occur

---

## FAQ

**Q: How many presets can I have?**  
A: 15 slots in the save file.

**Q: Can I use presets on any character?**  
A: Yes, all characters in the save share the 15 preset slots.

**Q: Do presets work across platforms?**  
A: Yes, JSON format is universal.

**Q: Can I edit JSON files manually?**  
A: Yes, but be careful with value ranges (typically 0-255).

**Q: Will presets change my character's stats?**  
A: No, only appearance. Stats unchanged.

---

[← Character Editor](character-editor.md) | [Next: World State →](world-state.md)