# Vanilla Save Files

When loading a `.sl2` save file, the tool shows a warning. This page explains what it means and what precautions to take.

## What Is the Warning?

Loading a `.sl2` file (the vanilla PC save format) triggers a one-time warning:

> **Warning - Vanilla Save File Detected**
>
> You are loading a Vanilla save file (.sl2)
> WARNING: Modifying save files can result in a BAN if:
> • You connect to the official servers having modified saves
> What should be fine:
> • Corruption Fixes and Teleports
> • Spawning in valid items, runes, modifying NG count, gestures, event flags, changing invasion zones
> What will ban you:
> • Editing attributes to invalid values, spawning in cut content, spawning in DLC spells without owning it
> • If you think it might ban you it probably will
> If you play the vanilla game offline you will be fine.
> Do you understand and want to continue?

You can dismiss it with **Yes, Continue** or cancel the load with **No, Cancel**. Checking **Don't show this warning again** disables it for future loads (can be re-enabled in [Settings](settings.md)).

---

## Why Does This Risk Exist?

When you play online, FromSoftware's servers receive your character data and can flag values that fall outside what the game would normally produce. The tool does not bypass EAC or interact with the game process - it only edits the save file on disk - but a modified save taken online is detectable server-side. All the changes made by the tool are validated, so spawning in items, reviving bosses, etc. should be fine but i cannot give any guarantees.

The risk is specifically:

- **Going online with a save that has been edited** - FromSoftware's servers may detect stat values, item counts, or flag states outside normal game ranges

There is **no risk** if you only play offline with modified saves.

---

## How to Stay Safe

### Option 1: Play Offline

### Option 2: Use Seamless Co-op

The [Seamless Co-op mod](https://www.nexusmods.com/eldenring/mods/510) uses `.co2` save files that are separate from vanilla saves and never connects to Fromsofts Servers. Editing `.co2` files carries no risk since they are never loaded by the EAC-protected game binary and never synced with FromSoftware's servers.

---

## Disabling the Warning

The warning appears every time you load a `.sl2` file unless disabled.

**To disable:** Check **Don't show this warning again** in the dialog, or go to **Settings → General → Show EAC warning when loading .sl2 files** and uncheck it.

**To re-enable:** Go to **Settings → General → Show EAC warning when loading .sl2 files** and check it.

---

[← Troubleshooting](troubleshooting-tab.md) | [Linux Save Location →](linux-compatdata.md)