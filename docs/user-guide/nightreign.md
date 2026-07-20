# Elden Ring Nightreign

Save editing support for Nightreign, covering hero profiles, relics, and murk.

## Overview

Nightreign support is a reduced tab set:

- Save Inspector
- Editor
- SteamID Patcher
- Backup Manager (top-level button)
- Settings

Nightreign saves are AES-encrypted BND4 containers; the parser decrypts each slot before reading and re-encrypts on write, using the original IV.

---

## Save Inspector

Shows all 10 slots with name, which hero was used, relic count, murk, and Marks of Night. Select a row and click **Edit Slot** to open the Editor tab for that slot.

---

## Editor

The Editor tab has two sub-tabs:

### Overview

- Player name
- Murk
- Sovereign Sigils

### Relics

- Searchable list of all relics currently on the character
- Edit panel with name pickers for each relic's effects and curses
- Relic spawner - add a new relic by picking its base relic and up to three effects
- Remove relic

**Relic compatibility:** each relic effect is tagged by tier (normal, deep, special) and by which of the 10 heroes it can be used on (Wylder, Guardian, Ironeye, Duchess, Raider, Revenant, Recluse, Executor, Scholar, Undertaker). The name pickers only show effects valid for the tier/hero combination you're editing.

**Vessel relic slots:** each hero has vessel loadouts with 6 relic slots each; assigning a relic to a vessel slot uses the relic's in-inventory handle.

---

## Data Tracked Per Slot

- Player name
- Murk and Marks of Night
- Relic states (up to 5120 item state slots per slot, of which the first 84 are reserved)
- Per-hero profile blocks: active flag, hero name, total runs, appearance data
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
