# Dark Souls III

Save editing support for Dark Souls III, covering stats, inventory, boss revival, and world state, with Convergence and Cinders mod support.

## Overview

DS3 support is a reduced tab set:

- Save Inspector
- Character Editor
- Inventory
- Bosses
- World State
- SteamID Patcher
- Backup Manager (top-level button)
- Settings

---

## Save Inspector

Lists all character slots for the loaded save. Selecting a slot and opening the Character Editor loads that slot's data.

---

## Character Editor

Edit the standard DS3 attributes (Vigor, Attunement, Endurance, Vitality, Strength, Dexterity, Intelligence, Faith, Luck), Souls, and NG+ cycle. As with Elden Ring, level is recalculated from stat totals and validated against the loaded character's starting class so the displayed level and stats stay consistent.

---

## Inventory

Item spawning and inventory editing. Supports items from both the **Convergence** and **Cinders** overhaul mods in addition to vanilla DS3 items.

---

## Bosses

Boss revival for repeated fights, covering the DS3 boss roster.

---

## World State

World state editing for DS3 saves (location/progression flags relevant to world state, separate from the boss revival list above).

---

## SteamID Patcher

Transfer a DS3 save between Steam accounts, same mechanism as the Elden Ring version.

---

## Safety

All edits go through the same tracked-offset write path as the other supported games: nothing is hardcoded, and a backup is created before any change is applied.

---

## Related Features

- **[Backup Manager](backup-manager.md)**
- **[SteamID Patcher](steamid-patcher.md)**
