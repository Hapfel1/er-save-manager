"""
Copy a save file to another mod extension.

The game, or the mod loader, picks the save file by extension: .sl2 for the
unmodded game, .co2 for Seamless Co-op, .cnv for Convergence and .cnvco2 for
Convergence with Seamless Co-op. All of them hold the same format, so a copy
under the new name loads. A character can still hold content that the other
setup lacks, and such characters are never written to the target:

- Convergence content (Convergence-only items or Convergence event flags)
  going to an extension without Convergence.
- Seamless Co-op items going to the vanilla extension (.sl2).
- Weapons above +15 going to Convergence, which caps upgrades at +15.

The source file is never written. An existing target is backed up before it
is changed. When the target already holds characters, each chosen character
goes into a free slot or replaces one character, and the rest stay.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from er_save_manager.games.game_profiles import PROFILES_BY_KEY
from er_save_manager.games.save_identify import KNOWN_GAMES, identify_game

CHARACTER_SLOTS = 10


@dataclass(frozen=True)
class Flavor:
    ext: str
    label: str
    seamless: bool
    convergence: bool


FLAVORS: dict[str, Flavor] = {
    ".sl2": Flavor(".sl2", "Vanilla", False, False),
    ".co2": Flavor(".co2", "Seamless Co-op", True, False),
    ".cnv": Flavor(".cnv", "Convergence", False, True),
    ".cnvco2": Flavor(".cnvco2", "Convergence + Seamless Co-op", True, True),
}

# Extensions recognized on a source file only. Convergence 3.0.3 and later
# load .cnvco2 instead of .cnv.co2.
_SOURCE_ONLY: dict[str, Flavor] = {".cnv.co2": FLAVORS[".cnvco2"]}

# Extensions of files the game and the editor write next to a save.
_RESERVED = (".bak", ".tmp", ".backups", ".zip")
_CUSTOM_EXT = re.compile(r"\.[a-z0-9]+(\.[a-z0-9]+)*")

BAN_NOTE = (
    "Items the game does not have can crash it on load, and on a vanilla .sl2 "
    "save used online they can get the account banned."
)


class ExtensionCopyError(Exception):
    """The copy cannot be made; the message is shown to the user."""


def target_extensions(game_key: str) -> list[str]:
    """Extensions a save of this game can be copied to."""
    return [e for e in PROFILES_BY_KEY[game_key].extensions if e in FLAVORS]


def custom_flavor(game_key: str, ext: str) -> Flavor:
    """Flavor of an extension outside the standard list, as set in the mod's
    own settings. Anything but .sl2 keeps the save off the official servers;
    the editor reads a name with ".cnv" as Convergence (ER only)."""
    ext = ext.strip().lower()
    if not ext.startswith("."):
        ext = "." + ext
    if ext in FLAVORS and ext in target_extensions(game_key):
        return FLAVORS[ext]
    if (
        not _CUSTOM_EXT.fullmatch(ext)
        or len(ext) > 16
        or ext in FLAVORS
        or ext.endswith(_RESERVED)
    ):
        raise ExtensionCopyError(f"{ext} cannot be used as a save extension.")
    convergence = game_key == "elden_ring" and ".cnv" in ext
    label = "Custom, Convergence" if convergence else "Custom"
    return Flavor(ext, label, True, convergence)


def split_name(path: Path) -> tuple[str, str]:
    """(name up to the first dot, extension from the first dot), so
    ER0000.cnv.co2 splits into ER0000 and .cnv.co2."""
    base, dot, rest = path.name.partition(".")
    return base, (dot + rest).lower()


def flavor_of(path: Path, game_key: str = "elden_ring") -> Flavor | None:
    _, ext = split_name(path)
    known = FLAVORS.get(ext) or _SOURCE_ONLY.get(ext)
    if known or not ext:
        return known
    try:
        return custom_flavor(game_key, ext)
    except ExtensionCopyError:
        return None


def target_path(source: Path, ext: str) -> Path:
    base, _ = split_name(source)
    return source.with_name(base + ext)


# ---- per-game access -------------------------------------------------------


class _Game:
    """Character slot access for one game. Subclasses import lazily, so only
    the loaded game's parser is imported."""

    def load(self, path: Path):
        raise NotImplementedError

    def occupied(self, save, i: int) -> bool:
        raise NotImplementedError

    def name(self, save, i: int) -> str:
        raise NotImplementedError

    def delete(self, save, i: int) -> None:
        raise NotImplementedError

    def transfer(self, source, i: int, target, j: int) -> None:
        raise NotImplementedError

    def write(self, save, path: Path) -> None:
        raise NotImplementedError

    def seamless_items(self, save, i: int) -> list[str]:
        """Names of the Seamless Co-op items character i holds."""
        return []

    def convergence_content(self, save, i: int) -> list[str]:
        """Convergence items character i holds, plus "event flags" when only
        Convergence flags are set; empty for a vanilla character."""
        return []

    def weapons_over_cap(self, save, i: int, cap: int) -> list[str]:
        return []

    def free_slot_note(self, save, i: int) -> str | None:
        """Why a free target slot might not show the character in game."""
        return None


class _EldenRing(_Game):
    # Event flag blob bits (MSB-first bit index) that only Convergence sets.
    _CONVERGENCE_BITS = (
        760,
        13100,
        15730,
        15740,
        15750,
        15760,
        15770,
        15780,
        15790,
        11062000,
        11076505,
        11076601,
    )
    _cache: dict[str, dict[int, str]] = {}

    def load(self, path):
        from er_save_manager.parser import Save

        save = Save.from_file(str(path))
        if save.is_ps:
            raise ExtensionCopyError(
                "PlayStation saves have no PC extension to change."
            )
        return save

    def occupied(self, save, i):
        return not save.character_slots[i].is_empty()

    def name(self, save, i):
        # The slot's own name; ProfileSummary entries can be stale.
        return save.character_slots[i].get_character_name() or f"Slot {i + 1}"

    def delete(self, save, i):
        from er_save_manager.transfer.character_ops import CharacterOperations

        CharacterOperations.delete_slot(save, i)

    def transfer(self, source, i, target, j):
        from er_save_manager.transfer.character_ops import CharacterOperations

        CharacterOperations.transfer_slot(source, i, target, j)

    def write(self, save, path):
        save.recalculate_checksums()
        save.to_file(str(path))

    @classmethod
    def _tables(cls) -> tuple[dict[int, str], dict[int, str]]:
        """(Convergence-only id -> name, Seamless Co-op id -> name)."""
        if not cls._cache:
            from er_save_manager.data.item_database import get_item_database

            db = get_item_database()
            vanilla = {
                it.full_id
                for it in db.items
                if not it.category_name.startswith("Convergence")
            }
            cls._cache["cnv"] = {
                it.full_id: it.name
                for it in db.items
                if it.category_name.startswith("Convergence")
                and it.full_id not in vanilla
            }
            cls._cache["seamless"] = {
                it.full_id: it.name
                for it in db.get_items_by_category("Seamless Co-op Items")
            }
        return cls._cache["cnv"], cls._cache["seamless"]

    @staticmethod
    def _item_ids(slot) -> set[int]:
        """Full item ids of everything held or stored. Weapons, armor and
        ashes resolve through the gaitem map; goods and talismans carry the
        id in the handle."""
        gaitems = {
            g.gaitem_handle: g.item_id & 0xFFFFFFFF
            for g in slot.gaitem_map
            if g.gaitem_handle not in (0, 0xFFFFFFFF)
        }
        ids: set[int] = set()
        for inv in (slot.inventory_held, slot.inventory_storage_box):
            if not inv:
                continue
            for item in list(inv.common_items) + list(inv.key_items):
                handle = item.gaitem_handle & 0xFFFFFFFF
                if item.quantity <= 0 or handle in (0, 0xFFFFFFFF):
                    continue
                prefix = handle >> 28
                if prefix == 0xA:
                    ids.add(0x20000000 | (handle & 0xFFFFFF))
                elif prefix == 0xB:
                    ids.add(0x40000000 | (handle & 0xFFFFFF))
                elif handle in gaitems:
                    ids.add(gaitems[handle])
        ids.discard(0xFFFFFFFF)
        return ids

    def seamless_items(self, save, i):
        _, seamless = self._tables()
        ids = self._item_ids(save.character_slots[i])
        return sorted({seamless[x] for x in ids if x in seamless})

    def convergence_content(self, save, i):
        cnv, _ = self._tables()
        slot = save.character_slots[i]
        found = set()
        for x in self._item_ids(slot):
            # Weapons: ids carry affinity * 100 + upgrade on the base id.
            root = x - x % 10000 if x & 0xF0000000 == 0 else x
            if x in cnv or root in cnv:
                found.add(cnv.get(x) or cnv[root])
        if found:
            return sorted(found)
        flags = slot.event_flags or b""
        for bit in self._CONVERGENCE_BITS:
            byte = bit >> 3
            if byte < len(flags) and flags[byte] >> (7 - (bit & 7)) & 1:
                return ["event flags"]
        return []

    def weapons_over_cap(self, save, i, cap):
        from er_save_manager.data.item_database import get_item_database

        db = get_item_database()
        out = set()
        for x in self._item_ids(save.character_slots[i]):
            if x & 0xF0000000 != 0:
                continue
            level = x % 100
            if level > cap:
                item = db.get_item_by_id(x - x % 10000)
                out.add(f"{item.name if item else hex(x)} +{level}")
        return sorted(out)


class _DarkSouls3(_Game):
    _seamless: dict[int, str] | None = None

    def load(self, path):
        from er_save_manager.games.DS3.save import DS3Save

        return DS3Save.from_file(path)

    def occupied(self, save, i):
        return save.characters[i] is not None

    def name(self, save, i):
        return save.characters[i].name or f"Slot {i + 1}"

    def delete(self, save, i):
        from er_save_manager.games.DS3 import character_ops

        character_ops.delete_slot(save, i)

    def transfer(self, source, i, target, j):
        from er_save_manager.games.DS3 import character_ops

        character_ops.transfer_slot(source, i, target, j)

    def write(self, save, path):
        save.save_to_file(path)

    def seamless_items(self, save, i):
        cls = type(self)
        if cls._seamless is None:
            from er_save_manager.games.DS3 import catalog

            cls._seamless = {
                int(item["Id"], 0): item["Name"]
                for items in catalog.items().values()
                for item in items
                if catalog.is_seamless(item)
            }
        char = save.characters[i]
        held = char.iter_inventory() + char.iter_storage()
        return sorted(
            {
                cls._seamless[e.item_id]
                for e in held
                if char.is_real_item(e) and e.item_id in cls._seamless
            }
        )

    def free_slot_note(self, save, i):
        return _NEVER_CREATED_NOTE


class _DarkSoulsRemastered(_Game):
    def load(self, path):
        from er_save_manager.games.DSR.save import DSRSave

        return DSRSave.from_file(path)

    def occupied(self, save, i):
        return save.characters[i] is not None

    def name(self, save, i):
        return save.characters[i].name or f"Slot {i + 1}"

    def delete(self, save, i):
        from er_save_manager.games.DSR import character_ops

        character_ops.delete_slot(save, i)

    def transfer(self, source, i, target, j):
        from er_save_manager.games.DSR import character_ops

        character_ops.transfer_slot(source, i, target, j)

    def write(self, save, path):
        save.save_to_file(path)

    def seamless_items(self, save, i):
        from er_save_manager.games.DSR import catalog

        names = set()
        for item in save.characters[i].iter_items():
            hit = catalog.lookup(item.category, item.item_id)
            if hit and hit[0]["seamless"]:
                names.add(hit[0]["name"])
        return sorted(names)

    def free_slot_note(self, save, i):
        return _NEVER_CREATED_NOTE


class _DarkSouls2(_Game):
    def load(self, path):
        from er_save_manager.games.DS2.save import DS2Save

        return DS2Save.from_file(path)

    def occupied(self, save, i):
        from er_save_manager.games.DS2.save import SlotState

        return save.slot_state(i) is SlotState.CHARACTER

    def name(self, save, i):
        return save.slot_display_name(i) or f"Slot {i}"

    def delete(self, save, i):
        from er_save_manager.games.DS2.character_ops import DS2CharacterOperations

        DS2CharacterOperations.delete_slot(save, i)

    def transfer(self, source, i, target, j):
        from er_save_manager.games.DS2.character_ops import DS2CharacterOperations

        DS2CharacterOperations.transfer_slot(source, i, target, j, force=True)

    def write(self, save, path):
        save.save_to_file(path)

    def seamless_items(self, save, i):
        from er_save_manager.games.DS2.item_database import SEAMLESS_ITEMS

        by_id = {
            int.from_bytes(bytes.fromhex(h), "little"): name
            for name, h in SEAMLESS_ITEMS.items()
        }
        char = save.characters[i]
        return sorted(
            {
                by_id[e.item_id]
                for e in char.inventory() + char.key_items()
                if e.item_id in by_id
            }
        )

    def free_slot_note(self, save, i):
        from er_save_manager.games.DS2.save import SlotState

        if save.slot_state(i) is SlotState.NEVER_CREATED:
            return _NEVER_CREATED_NOTE
        return None


class _Nightreign(_Game):
    def load(self, path):
        from er_save_manager.games.NR.parser import NightreignSave

        return NightreignSave.from_file(path)

    def occupied(self, save, i):
        return not save.slots[i].is_empty()

    def name(self, save, i):
        return save.slots[i].player_name or f"Slot {i + 1}"

    def delete(self, save, i):
        from er_save_manager.games.NR import character_ops

        character_ops.delete_slot(save, i)

    def transfer(self, source, i, target, j):
        from er_save_manager.games.NR import character_ops

        character_ops.transfer_slot(source, i, target, j)

    def write(self, save, path):
        save.write_file(path)


_NEVER_CREATED_NOTE = (
    "A slot never used by the game's character creation may stay blank on the "
    "load screen. Create a throwaway character in it first if that happens."
)

_GAMES: dict[str, _Game] = {
    "elden_ring": _EldenRing(),
    "dark_souls_3": _DarkSouls3(),
    "dark_souls_remastered": _DarkSoulsRemastered(),
    "dark_souls_2": _DarkSouls2(),
    "nightreign": _Nightreign(),
}

SUPPORTED_GAMES = frozenset(_GAMES)


# ---- plan ------------------------------------------------------------------


@dataclass
class SourceCharacter:
    slot: int
    name: str
    # Reasons the character cannot go to the target; empty when it can.
    blockers: list[str] = field(default_factory=list)
    # Shown, but the character is still copied.
    notes: list[str] = field(default_factory=list)


@dataclass
class Plan:
    game_key: str
    source: Path
    target: Path
    source_flavor: Flavor | None
    target_flavor: Flavor
    characters: list[SourceCharacter]
    target_exists: bool
    # Occupied target slots as (slot, name).
    target_characters: list[tuple[int, str]]
    free_slots: list[int]
    free_slot_notes: dict[int, str]

    @property
    def blocked(self) -> list[SourceCharacter]:
        return [c for c in self.characters if c.blockers]

    @property
    def copyable(self) -> list[SourceCharacter]:
        return [c for c in self.characters if not c.blockers]

    @property
    def merges(self) -> bool:
        """True when the target keeps its characters and receives the chosen
        ones in its free slots."""
        return bool(self.target_characters)


def short_list(items: list[str], shown: int = 4) -> str:
    if len(items) <= shown:
        return ", ".join(items)
    return ", ".join(items[:shown]) + f" and {len(items) - shown} more"


def _check(
    game: _Game, save, i: int, src: Flavor | None, dst: Flavor
) -> SourceCharacter:
    try:
        name = game.name(save, i)
    except Exception:
        name = f"Slot {i + 1}"
    char = SourceCharacter(i, name)
    try:
        _check_content(game, save, char, src, dst)
    except Exception as e:
        char.blockers.append(f"Could not read the character: {e}")
    return char


def _check_content(
    game: _Game, save, char: SourceCharacter, src: Flavor | None, dst: Flavor
) -> None:
    i = char.slot
    if not dst.seamless and not dst.convergence:
        items = game.seamless_items(save, i)
        if items:
            char.blockers.append("Seamless Co-op items: " + short_list(items))
    cnv = game.convergence_content(save, i)
    if cnv and not dst.convergence:
        char.blockers.append("Convergence content: " + short_list(cnv))
    elif not cnv and src and src.convergence and not dst.convergence:
        char.notes.append(
            "No Convergence items or flags found, so this looks like a vanilla "
            "character. A Convergence character early in the game can look "
            "the same."
        )
    if dst.convergence and not (src and src.convergence):
        over = game.weapons_over_cap(save, i, 15)
        if over:
            char.blockers.append(
                "Weapons above +15 (Convergence max): " + short_list(over)
            )


def make_plan(game_key: str, source: Path, ext: str) -> Plan:
    """Check the source characters and the target file for copying source
    to the extension ext (a standard one or a custom one). Raises
    ExtensionCopyError when no copy is possible."""
    source = Path(source)
    game = _GAMES.get(game_key)
    if game is None:
        raise ExtensionCopyError("This game is not supported.")
    dst = custom_flavor(game_key, ext)
    ext = dst.ext
    try:
        with source.open("rb") as f:
            magic = f.read(4)
    except OSError as e:
        raise ExtensionCopyError(f"Could not read the save:\n{e}") from e
    if magic != b"BND4":
        raise ExtensionCopyError("PlayStation saves have no PC extension to change.")

    target = target_path(source, ext)
    if target.resolve() == source.resolve():
        raise ExtensionCopyError(f"The save already uses {ext}.")

    src = flavor_of(source, game_key)
    target_exists = target.exists()
    if target_exists and game_key in KNOWN_GAMES:
        found = identify_game(target)
        if found != game_key:
            raise ExtensionCopyError(
                f"{target.name} already exists and is not a "
                f"{PROFILES_BY_KEY[game_key].name} save. Move it away first."
            )

    try:
        save = game.load(source)
    except ExtensionCopyError:
        raise
    except Exception as e:
        raise ExtensionCopyError(f"Could not load the save:\n{e}") from e

    characters = [
        _check(game, save, i, src, dst)
        for i in range(CHARACTER_SLOTS)
        if game.occupied(save, i)
    ]

    target_characters: list[tuple[int, str]] = []
    free: list[int] = []
    notes: dict[int, str] = {}
    if target_exists:
        try:
            tsave = game.load(target)
        except Exception as e:
            raise ExtensionCopyError(
                f"{target.name} already exists but could not be loaded:\n{e}"
            ) from e
        for i in range(CHARACTER_SLOTS):
            if game.occupied(tsave, i):
                target_characters.append((i, game.name(tsave, i)))
            else:
                free.append(i)
                note = game.free_slot_note(tsave, i)
                if note:
                    notes[i] = note

    return Plan(
        game_key,
        source,
        target,
        src,
        dst,
        characters,
        target_exists,
        target_characters,
        free,
        notes,
    )


# ---- apply -----------------------------------------------------------------


def _backup_target(plan: Plan) -> None:
    if not plan.target_exists:
        return
    from er_save_manager.backup.manager import BackupManager

    BackupManager(plan.target).create_backup(
        description=f"before_copy_from_{plan.source.name}",
        operation="extension_copy",
    )


def _copy_bytes(source: Path, target: Path) -> None:
    tmp = target.with_name(target.name + ".tmp")
    try:
        shutil.copyfile(source, tmp)
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)


def write_copy(plan: Plan, slots: list[int]) -> None:
    """Make the target a copy of the source holding only the given slots.
    Replaces an existing target (backed up first)."""
    chosen = set(slots)
    allowed = {c.slot for c in plan.copyable}
    if not chosen <= allowed:
        raise ExtensionCopyError("A blocked character cannot be copied.")
    _backup_target(plan)

    drop = [c.slot for c in plan.characters if c.slot not in chosen]
    if not drop:
        _copy_bytes(plan.source, plan.target)
        return

    game = _GAMES[plan.game_key]
    save = game.load(plan.source)
    for i in drop:
        game.delete(save, i)
    game.write(save, plan.target)


def write_merge(plan: Plan, pairs: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Copy characters into an existing target as (source slot, target slot)
    pairs. A target slot may be free or hold a character, which is then
    replaced; the target's other characters stay."""
    allowed = {c.slot for c in plan.copyable}
    sources = [i for i, _ in pairs]
    targets = [j for _, j in pairs]
    if not set(sources) <= allowed:
        raise ExtensionCopyError("A blocked character cannot be copied.")
    if len(set(sources)) != len(sources) or len(set(targets)) != len(targets):
        raise ExtensionCopyError("Each character needs its own target slot.")
    if not all(0 <= j < CHARACTER_SLOTS for j in targets):
        raise ExtensionCopyError("Target slot out of range.")
    _backup_target(plan)

    game = _GAMES[plan.game_key]
    source = game.load(plan.source)
    target = game.load(plan.target)
    for i, j in pairs:
        game.transfer(source, i, target, j)
    game.write(target, plan.target)
    return pairs
