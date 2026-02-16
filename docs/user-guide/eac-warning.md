# EAC Warning & Vanilla Save Files

When loading a `.sl2` save file, the tool shows a warning about Easy Anti-Cheat. This page explains what it means and what precautions to take.

## What Is the Warning?

Loading a `.sl2` file (the vanilla PC save format) triggers a one-time warning:

> **EAC Warning - Vanilla Save File Detected**
>
> You are loading a Vanilla save file (.sl2).
>
> WARNING: Modifying save files can result in a BAN if:
> - Easy Anti-Cheat (EAC) is enabled
> - You play online with modified saves
>
> To avoid bans:
> 1. Launch Elden Ring with EAC disabled
> 2. Only play offline with modified saves
> 3. Do not use modified saves in online/multiplayer

You can dismiss it with **Yes, Continue** or cancel the load with **No, Cancel**. Checking **Don't show this warning again** disables it for future loads (can be re-enabled in [Settings](settings.md)).

---

## Why Does This Risk Exist?

When you play online, FromSoftware's servers receive your character data and can flag values that fall outside what the game would normally produce. The tool does not bypass EAC or interact with the game process — it only edits the save file on disk — but a modified save taken online is detectable server-side.

The risk is specifically:

- **Going online with a save that has been edited** — FromSoftware's servers may detect stat values, item counts, or flag states outside normal game ranges

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

## FAQ

**Q: Will the fixer get me banned?**
The fixer only restores values the game would produce normally (valid HP, correct coordinates, proper flags). If you play offline after fixing, the risk is effectively zero. If you play online with a fixed save, the risk is low but not zero — FromSoftware's servers may still check character state.

**Q: I just fixed an infinite loading screen. Is it safe to go online?**
After a fix, your save is back to a valid game state. Playing online after fixing a crash bug should be safe, but I don't give any guarantees.

**Q: Does the tool interact with the game while it's running?**
No. The tool only reads and writes the save file on disk. It does not inject into the game process, modify memory, or interact with EAC in any way.

---

[← Troubleshooting](troubleshooting-tab.md) | [Linux Save Location →](linux-compatdata.md)