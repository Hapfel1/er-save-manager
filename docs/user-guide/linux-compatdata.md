# Linux Save File Location & compatdata

On Linux, Elden Ring runs through Proton and stores saves inside Steam's `compatdata` folder. This page explains how that works, when the tool warns you about it, and what to do.

## How Elden Ring Saves Work on Linux

Elden Ring is a Windows game running through Proton (Steam's compatibility layer). Proton creates a virtual Windows environment called a **compatdata** folder for each game. The save file is stored inside this virtual `AppData` path:

**Standard Steam:**
```
~/.local/share/Steam/steamapps/compatdata/1245620/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing/<SteamID>/ER0000.sl2
```

**Flatpak Steam:**
```
~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/compatdata/1245620/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing/<SteamID>/ER0000.sl2
```

`1245620` is Elden Ring's Steam App ID. This is the **default** compatdata location.

---

## The Non-Standard Location Warning

The tool shows this warning when it detects your save file is inside a compatdata folder **other than `1245620`**:

> **Non-Standard Save Location**
>
> Your save file is located in:
> `/path/to/your/save/ER0000.sl2`
>
> This is NOT the default Steam compatdata location!
>
> If you remove the custom launcher (e.g. `ersc_launcher.exe`) from Steam, Steam will remove that compatdata folder and your save will get lost.

### When Does This Happen?

This happens when you use a **custom launcher** added as a non-Steam game or as a Steam launch option that points to a different executable — most commonly:

- **Seamless Co-op** (`ersc_launcher.exe`) — when added as a separate Steam game entry
- **Mod Engine 2** or similar mod loaders — when launched as a separate game entry
- Any other launcher added as a **non-Steam game** or separate Steam library entry

Each separate Steam game entry gets its own compatdata folder with a different ID (e.g., `2898770` instead of `1245620`). If that entry is removed from Steam, Steam deletes its compatdata folder and the save inside it.

### What Happens If You Ignore It?

- As long as the custom launcher entry stays in Steam, nothing happens
- If you remove the launcher from Steam, its compatdata folder is deleted
- **Your save file is deleted with it** — there is no recycle bin

---

## The Buttons in the Warning Dialog

### Copy to Default

Copies the save file to the default `1245620` compatdata location:

```
~/.local/share/Steam/steamapps/compatdata/1245620/pfx/.../EldenRing/<SteamID>/ER0000.sl2
```

- The **original file is left in place** — nothing is deleted
- You now have two copies: one at the non-standard location, one at the default
- The tool switches to tracking the default-location copy going forward

Use this if you want the save protected regardless of whether the custom launcher entry stays in Steam.

### Keep Current

Dismisses the warning and continues using the save at its current location. No files are moved.

Use this if you understand the risk and intentionally keep saves in the non-standard location.

### Don't Show Again

Dismisses the warning and disables it permanently for future loads.

Can be re-enabled in **Settings → General → Show Linux save location warnings**.

---

## Fixing the Root Cause: Steam Launch Options

The proper fix is to force the custom launcher to use the same compatdata folder as the base game, so both the vanilla game and the custom launcher share one save file location.

### The Launch Option

The tool displays the correct Steam launch option in the warning dialog. Copy it and add it to the custom launcher's **Steam launch options**.

**Standard Steam:**
```
STEAM_COMPAT_LIBRARY_PATHS=$HOME/.local/share/Steam/steamapps/ STEAM_COMPAT_DATA_PATH=$STEAM_COMPAT_LIBRARY_PATHS/compatdata/1245620/ %command%
```

**Flatpak Steam:**
```
STEAM_COMPAT_LIBRARY_PATHS=$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/ STEAM_COMPAT_DATA_PATH=$STEAM_COMPAT_LIBRARY_PATHS/compatdata/1245620/ %command%
```

### How to Apply

1. Open **Steam**
2. Right-click the custom launcher entry → **Properties**
3. Under **General**, find **Launch Options**
4. Paste the launch option from the warning dialog
5. Close Properties

After applying, the custom launcher will write saves to the same `1245620` compatdata folder as the base game. The non-standard location warning will no longer appear.

---

## Save Locations Summary

| Setup | Save Location | Warning? |
|-------|---------------|----------|
| Vanilla game (Steam) | `compatdata/1245620/...` | Never |
| Seamless Co-op (correct launch option set) | `compatdata/1245620/...` | Never |
| Seamless Co-op (separate Steam entry, no launch option) | `compatdata/<other_id>/...` | Yes |
| Non-Steam game / custom launcher, no launch option | `compatdata/<other_id>/...` | Yes |
| Save not in compatdata at all | Anywhere else | Never |

Files outside compatdata entirely (e.g. manually placed elsewhere) do not trigger the warning — the check only applies when a file is inside a compatdata folder with a non-standard ID.

---

## Auto-Detection

When you click **Auto-Find**, the tool searches for save files in these locations (in order):

**Standard Steam:**

1. `~/.local/share/Steam/steamapps/compatdata/` — all subfolders
2. `~/.steam/steam/steamapps/compatdata/` — symlink, same location
3. Additional Steam library folders from `libraryfolders.vdf`

**Flatpak Steam:**

1. `~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/compatdata/`

It finds all `ER0000.sl2` and `ER0000.co2` files across all compatdata subfolders. If it finds a save in a non-`1245620` subfolder, it loads it but shows the warning.

---

## FAQ

**Q: I use Seamless Co-op. Which save format does it use?**
Seamless Co-op uses `.co2` files, stored in a separate folder from vanilla `.sl2` files. The tool loads both formats. The compatdata warning applies regardless of format — it's about the folder location, not the file extension.

**Q: I set the launch option but the warning still appears.**
The launch option takes effect the next time you launch the game through Steam. After launching with the option set, the new save will be at the `1245620` location. You may need to copy your existing save to that location first (use the **Copy to Default** button in the warning).

**Q: I have saves in both locations. Which one does the game use?**
Whichever location the game or launcher writes to. After setting the launch option, the launcher uses `1245620`. The old save at the non-standard location is ignored by the game but still exists on disk.

**Q: Is it safe to delete the old compatdata folder after copying?**
Only if you are certain you have the save copied correctly and the game loads it. Verify in-game first. The old compatdata folder may also contain other game files — deleting it removes everything for that entry.

**Q: The tool can't find my save automatically.**
Use the **Browse** button to locate it manually. Common non-standard locations to check:
```
~/.local/share/Steam/steamapps/compatdata/<any_id>/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing/
```
Replace `<any_id>` with the subfolder IDs you see in `~/.local/share/Steam/steamapps/compatdata/`.

---

[← EAC Warning](eac-warning.md) | [Save File Structure →](../technical/save-file-structure.md)