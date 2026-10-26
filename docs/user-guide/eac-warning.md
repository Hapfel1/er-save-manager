# Vanilla Save Files

Loading a vanilla save shows an online ban warning first. This page explains what it means and what precautions to take.

## What Is the Warning?

Vanilla saves are the ones the official servers see: `.sl2` on PC, the PlayStation `memory.dat` export and the Dark Souls III PS4 `userdata` files. The Dark Souls III PS4 text names the PlayStation Network account instead of the Steam account. Loading one opens the **Vanilla Save File** dialog, written for the game that is selected (Elden Ring, Nightreign, Dark Souls III, Dark Souls II or Dark Souls Remastered):

- How that game checks saves and what a ban means there (for example, Dark Souls III checks the save on load and on every save, offline included, and bans in a weekly wave)
- **Generally safe** - edits community testing found safe, such as corruption fixes, teleports and spawning normally obtainable items
- **Known to ban** (or **Reported to ban**) - edits that got accounts banned, such as attributes that do not fit the level or starting class, or cut content
- Under each risky edit the editor already prevents, a **Not possible with the save manager** line says how its validation blocks it
- **Offline** - playing only offline with an edited save carries no ban risk, where that holds for the game

The lists come from community testing, not from FromSoftware or Bandai Namco, and detection can change with any patch. Nothing in them is a guarantee.

**Continue** loads the save, **Cancel** stops the load. Checking **Don't show this warning again** disables it for future loads (it can be re-enabled in [Settings](settings.md)).

---

## Why Does This Risk Exist?

When you play online, FromSoftware's servers receive your character data and can flag values that fall outside what the game would normally produce. The tool does not bypass EAC or interact with the game process - it only edits the save file on disk - but a modified save taken online is detectable server-side. The editor validates its changes, so spawning in items, reviving bosses and similar edits should be fine, but there is no guarantee.

---

## How to Stay Safe

### Option 1: Play Offline

### Option 2: Use Seamless Co-op

The [Seamless Co-op mod](https://www.nexusmods.com/eldenring/mods/510) uses `.co2` save files that are separate from vanilla saves and never connect to FromSoftware's servers. Editing `.co2` files carries no ban risk, and the warning is not shown for them.

---

## Disabling the Warning

**To disable:** Check **Don't show this warning again** in the dialog, or go to **Settings → General → Show online ban warning when loading vanilla saves** and uncheck it.

**To re-enable:** Go to **Settings → General → Show online ban warning when loading vanilla saves** and check it.

---

[← Troubleshooting](troubleshooting-tab.md) | [Linux Save Location →](linux-compatdata.md)
