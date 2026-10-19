# Gestures

View and unlock all gestures including base game, DLC, and cut content gestures.

## Overview

The Gestures tab allows you to:

- View unlocked gestures for each character
- Unlock base game gestures
- Unlock DLC gestures
- Unlock cut content gestures (hidden/unused)
- Batch unlock operations
- Edit the six-gesture wheel
- View and edit the unlocked map regions

**Total Gestures Available:** 90+ (base + DLC + cut content)

---

## Interface Layout

### Character

The **Character** bar under the file row picks the character; the tab shows its gestures as soon as one is selected.

### Gestures List

**Displays:**

- All available gestures
- Checkbox for each gesture
- Gesture name
- Status indicators:
  - (DLC) - Shadow of the Erdtree gesture
  - (Cut) - Cut content/hidden gesture

**Visual Organization:**

- Scrollable list
- Grouped display
- Clear status indicators

### Action Buttons

**Main Actions:**

- **Select All Base** - Check all base game gestures
- **Select All + DLC** - Check base + DLC gestures
- **Deselect All** - Uncheck all gestures

---

### Gesture Wheel

The six gestures on the in-game wheel, each picked from the unlocked gestures.

### Unlocked Regions

**Unlocked Regions...** lists the map regions stored in the save. They control which areas show as discovered on the map. Check or uncheck regions (**All** / **None** for every region) and click **Apply** in that window; it writes immediately with its own backup.

---

## Unlocking Gestures

### Single Gesture

**Steps:**

1. Pick the character in the **Character** bar
2. Find gesture in list
3. Check checkbox to unlock
4. Click **Apply All** in the unapplied-changes bar

**Result:** Gesture unlocked for character

### Bulk Unlock - Base Game Only

**Steps:**

1. Pick the character in the **Character** bar
2. Click **Select All Base**
3. All non-DLC, non-cut gestures selected
4. Click **Apply All** in the unapplied-changes bar

**Result:** All base game gestures unlocked

### Bulk Unlock - Base + DLC

**Steps:**

1. Pick the character in the **Character** bar
2. Click **Select All + DLC**
3. All base and DLC gestures selected (excluding cut content)
4. Click **Apply All** in the unapplied-changes bar

**Result:** All obtainable gestures unlocked

### Deselect All

**Steps:**

1. Click **Deselect All**
2. All checkboxes cleared
3. Click **Apply All** to lock all gestures

**Use Case:** Reset gesture unlocks for challenge runs

---

## Applying Changes

Gesture and wheel edits are staged until they are applied. The unapplied-changes bar under the file row lists every page with edits:

1. Make gesture selections
2. Click **Apply All** in the unapplied-changes bar
3. One backup is created and all staged edits of every tab are written in one save
4. **Discard** drops the staged edits instead

Switching characters, loading another save, switching games or closing the window with unapplied changes asks whether to apply or discard them first.

---

## Safety Features

### Automatic Backup

**Before applying changes:**

- Full save backup created
- Timestamp included
- Stored in backup folder

### Validation

**Checks performed:**

- Character slot valid
- Save file loaded
- Gesture data accessible

---

## Troubleshooting

### "Gestures not loading"

**Cause:** Character slot empty or not selected

**Solution:**

- Pick the character in the **Character** bar
- Verify character exists in slot

### "Changes not applied"

**Cause:** The edits were not applied

**Solution:**

- Click **Apply All** in the unapplied-changes bar
- Wait for the confirmation message

---

## Related Features

- **[Event Flags](event-flags.md)** - Some gestures tied to flags
- **[Backup Manager](backup-manager.md)** - Restore if issues
- **[Character Editor](character-editor.md)** - Edit other character data

---

## FAQ

**Q: Will unlocking gestures break my save?**  
A: No, safe to unlock any gestures.

---

[← Event Flags](event-flags.md) | [Next: Settings →](settings.md)