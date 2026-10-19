# Elden Ring Nightreign

Save editing for Nightreign: player name, murk and Sovereign Sigils, relic spawning and editing, and chalice relic loadouts.

## Overview

Nightreign support uses these tabs:

- Save Inspector
- Character Management
- Character Editor
- Relics
- Loadouts
- SteamID Patcher
- Backup Manager (top-level button)
- Settings

Nightreign saves are AES-encrypted BND4 containers; the parser decrypts each slot before reading and re-encrypts on write, using the original IV. Decrypted PlayStation `memory.dat` saves are supported as well.

---

## Selecting a Character and Applying Changes

The **Character** bar under the file row picks the character for every tab that edits one; switching tabs keeps the selection. The first character is loaded when a save opens.

Character Editor and loadout slot edits are staged until they are applied: **Apply All** in the unapplied-changes bar writes them with one backup, **Discard** drops them. Relic actions (Spawn, Apply Edit, Remove, JSON import) write when clicked. Switching characters, loading another save, switching games or closing the window with unapplied changes asks whether to apply or discard them first.

---

## Save Inspector

Lists every character as a card with slot, Murk, play time, Sovereign Sigils and relic count, and a status on the right: **OK**, or the number of issues detected (hover for the list). **View All Issues** lists them for the whole save. Select a character and click **Edit Character** to open it in the editor tabs.

---

## Character Management

Copy, transfer, swap, export, import and delete character slots, within a save or between two saves.

---

## Character Editor

The character overview: player name, Murk and Sovereign Sigils.

---

## Relics

The character's relics as an icon grid, with a color and **Deep** filter and a search by name or ID. Selecting a relic shows its full effect texts in the detail pane, each with a status icon, and each deep relic curse below its effect.

- **Edit**: change the relic type, effects and curses with the pickers, then **Apply Edit**. **Remove** deletes the relic, **Copy to New Relic** loads it into the spawner.
- **New Relic** switches the detail pane to the spawner: pick the relic type from an icon grid (color, **Deep** and **Fixed** filters), then its effects and curses, and click **Spawn**.
- **Item Gib** (top bar) opens Relics in new-relic mode.
- **JSON** exports the character's relics or imports a list of relics.

**Roll rules**: relics are checked against the game's own roll tables. Each effect slot has its own effect pool, no effect appears twice, a relic holds at most one hero-specific effect, and on deep relics an effect from the curse pool carries a curse while other effects carry none. The pickers mark which effects and curses fit each slot. Spawning or importing a relic the game cannot roll is refused. Editing a relic into an unrollable one is refused as well; issues the relic already had before the edit, or unknown effects from mod data, only ask for confirmation, since the relic may come from an older game version. Effects are stored in the game's own order.

---

## Loadouts

Each hero's chalices and custom presets as an icon grid (pick the hero above it). Selecting one shows a card per relic slot: click a slot to pick from the character's relics that fit the slot's color and type, or clear it. Presets can be renamed, saved as a new preset or deleted.

Loadouts with modded vessels or more presets than the game's loadout block holds are supported. A note above the grid shows when the block is missing, modded or over capacity.

---

## Data Tracked Per Slot

- Player name
- Murk and Sovereign Sigils
- Relic states (up to 5120 item state slots per slot, of which the first 84 are reserved)
- Per-hero profile blocks: active flag, hero name, total runs, appearance data
- Chalice and preset relic loadouts
- Deep of Night Rank and score (from the global profile entry, shared across all slots)

---

## SteamID Patcher

Transfer a Nightreign save between Steam accounts, same mechanism as the Elden Ring version.

---

## Safety

Every edit creates a backup before writing, and the corrected slot is re-encrypted with its original IV so the save remains readable by the game.

---

## Related Features

- **[Backup Manager](backup-manager.md)**
- **[SteamID Patcher](steamid-patcher.md)**
