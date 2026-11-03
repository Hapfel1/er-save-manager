"""
Copy a save file to another mod extension or another platform.

The game, or the mod loader, picks the save file by extension: .sl2 for the
unmodded game, .co2 for Seamless Co-op, .cnv for Convergence and .cnvco2 for
Convergence with Seamless Co-op. All of them hold the same format, so a copy
under the new name loads.

A PlayStation or Switch 2 save holds the same character data in another
container: memory.dat (Elden Ring, Nightreign), a PS4 userdata folder (Dark
Souls III, Remastered, II) or a Switch 2 userdata folder (Elden Ring). A copy
to another platform goes into a chosen folder and is rebuilt in that
platform's layout. Consoles run the unmodded game. Where a new save of the
target platform cannot be built from the source (DS3 PS4 -> PC, DSR PC ->
PS4), only an existing save there can receive characters.

A character can still hold content that the other setup lacks, and such
characters are never written to the target:

- Convergence content (Convergence-only items or Convergence event flags)
  going to an extension without Convergence.
- Seamless Co-op items going to the vanilla extension (.sl2) or a console.
- Weapons above +15 going to Convergence, which caps upgrades at +15.

The source file is never written. An existing target is backed up before it
is changed. When the target already holds characters, each chosen character
goes into a free slot or replaces one character, and the rest stay.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from er_save_manager.games import ps_userdata
from er_save_manager.games.game_profiles import PROFILES_BY_KEY
from er_save_manager.games.save_identify import KNOWN_GAMES, identify_game
from er_save_manager.own_writes import atomic_write

CHARACTER_SLOTS = 10

PC = "pc"
PS = "ps"
SWITCH2 = "switch2"


@dataclass(frozen=True)
class Flavor:
    ext: str
    label: str
    seamless: bool
    convergence: bool
    platform: str = PC


FLAVORS: dict[str, Flavor] = {
    ".sl2": Flavor(".sl2", "Vanilla", False, False),
    ".co2": Flavor(".co2", "Seamless Co-op", True, False),
    ".cnv": Flavor(".cnv", "Convergence", False, True),
    ".cnvco2": Flavor(".cnvco2", "Convergence + Seamless Co-op", True, True),
}

# Extensions recognized on a source file only. Convergence 3.0.3 and later
# load .cnvco2 instead of .cnv.co2.
_SOURCE_ONLY: dict[str, Flavor] = {".cnv.co2": FLAVORS[".cnvco2"]}

MEMORY_DAT = "memory.dat"
_PS_MEMORY_DAT = Flavor(MEMORY_DAT, "PlayStation (memory.dat)", False, False, PS)
_PS4_FOLDER = Flavor("ps4", "PS4 (userdata folder)", False, False, PS)
_SWITCH2_FOLDER = Flavor("switch2", "Switch 2 (userdata folder)", False, False, SWITCH2)

# Console targets per game, by platform
CONSOLE_TARGETS: dict[str, dict[str, Flavor]] = {
    "elden_ring": {PS: _PS_MEMORY_DAT, SWITCH2: _SWITCH2_FOLDER},
    "nightreign": {PS: _PS_MEMORY_DAT},
    "dark_souls_3": {PS: _PS4_FOLDER},
    "dark_souls_remastered": {PS: _PS4_FOLDER},
    "dark_souls_2": {PS: _PS4_FOLDER},
}

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


def source_platform(path: Path) -> str:
    """PC, PS or SWITCH2 for a save file, by container (not by game)."""
    kind = ps_userdata.userdata_kind(path)
    if kind is not None:
        return SWITCH2 if kind[1] == ps_userdata.SWITCH2 else PS
    try:
        with Path(path).open("rb") as f:
            magic = f.read(4)
    except OSError as e:
        raise ExtensionCopyError(f"Could not read the save:\n{e}") from e
    return PC if magic == b"BND4" else PS


def targets(game_key: str, source: Path) -> list[Flavor]:
    """Standard targets for source: the other PC extensions, then the
    consoles other than the source's own platform."""
    platform = source_platform(source)
    consoles = [
        f for p, f in CONSOLE_TARGETS.get(game_key, {}).items() if p != platform
    ]
    if platform == PC:
        # Only the file's own extension is left out: a .cnv.co2 save can
        # still go to .cnvco2, which has the same flavor.
        _, own = split_name(source)
        pc = [FLAVORS[e] for e in target_extensions(game_key) if e != own]
    else:
        pc = [FLAVORS[e] for e in target_extensions(game_key)]
    return pc + consoles


def target_flavor(game_key: str, key: str) -> Flavor:
    """Flavor for a target key: a console target's ext or a PC extension."""
    for flavor in CONSOLE_TARGETS.get(game_key, {}).values():
        if flavor.ext == key:
            return flavor
    return custom_flavor(game_key, key)


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


def _is_folder_target(game_key: str, dst: Flavor) -> bool:
    return dst.platform == SWITCH2 or (dst.platform == PS and dst.ext != MEMORY_DAT)


def _folder_platform(dst: Flavor) -> str:
    return ps_userdata.SWITCH2 if dst.platform == SWITCH2 else ps_userdata.PS4


def platform_target(
    game_key: str, source: Path, dst: Flavor, folder: Path | None = None
) -> Path:
    """Path of the target for dst in folder (the source's folder when None).
    A folder target is named by its first userdata file."""
    source = Path(source)
    folder = Path(folder) if folder else source.parent
    if dst.platform == PC:
        if source_platform(source) == PC:
            base, _ = split_name(source)
        else:
            base, _ = split_name(Path(PROFILES_BY_KEY[game_key].save_filename))
        return folder / (base + dst.ext)
    if _is_folder_target(game_key, dst):
        return folder / ps_userdata.entry_file_name(0, _folder_platform(dst))
    return folder / MEMORY_DAT


def _target_exists(game_key: str, dst: Flavor, target: Path) -> bool:
    """True when the target is there; a folder target only when all its
    userdata files are. Raises for a folder holding some of them."""
    if not _is_folder_target(game_key, dst):
        return target.exists()
    platform = _folder_platform(dst)
    named = [
        c
        for c in ps_userdata._children(target.parent)
        if ps_userdata.entry_index(c, platform) is not None
    ]
    if not named:
        return False
    try:
        ps_userdata.require_folder(target, game_key, platform)
    except ps_userdata.IncompleteFolderError as e:
        raise ExtensionCopyError(
            f"{e}\n\nChoose an empty folder, or one with a complete save."
        ) from e
    return True


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

    def platform(self, save) -> str:
        return PS if save.is_ps else PC

    def cannot_build(self, source: str, target: str) -> str | None:
        """Why a new save of platform target cannot be made from a source
        save of platform source, None when it can."""
        return None

    def write_as(self, save, dst: Flavor, target: Path, steam_id: int) -> None:
        """Write save, in its current state, as a new save of dst.platform
        at target (a folder target: into target's folder)."""
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

        return Save.from_file(str(path))

    def platform(self, save):
        return save.platform

    def write_as(self, save, dst, target, steam_id):
        from er_save_manager.parser import platform as plat

        save.prepare_write()
        parts = plat.convert(save, dst.platform, steam_id)
        if dst.platform == SWITCH2:
            _write_files(target.parent, plat.switch2_files(parts))
        elif dst.platform == PS:
            atomic_write(target, plat.ps_bytes(parts))
        else:
            atomic_write(target, plat.pc_bytes(parts))

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

    def cannot_build(self, source, target):
        if source == PS and target == PC:
            return (
                "A PS4 save cannot become a new PC save: the PC file holds the "
                "game's regulation data, which a PS4 save has no copy of. "
                "Choose a folder with an existing PC save to copy the "
                "characters into."
            )
        return None

    def write_as(self, save, dst, target, steam_id):
        from er_save_manager.games.DS3 import platform as ds3p

        _write_files(target.parent, ds3p.to_ps4_files(save))

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

    def cannot_build(self, source, target):
        if source == PC and target == PS:
            return (
                "A PC save cannot become a new PS4 save: a PS4 save holds data "
                "the PC file has no copy of. Choose a folder with an existing "
                "PS4 save (exported from the console) to copy the characters "
                "into."
            )
        return None

    def write_as(self, save, dst, target, steam_id):
        from er_save_manager.games.DSR import platform as dsrp

        atomic_write(target, dsrp.to_pc_bytes(save))

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

    def write_as(self, save, dst, target, steam_id):
        from er_save_manager.games.DS2 import platform as ds2p

        if dst.platform == PC:
            atomic_write(target, ds2p.to_pc_bytes(save, steam_id))
        else:
            _write_files(target.parent, ds2p.to_ps4_files(save))

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

    def write_as(self, save, dst, target, steam_id):
        from er_save_manager.games.NR import platform as nrp

        atomic_write(target, nrp.convert(save, dst.platform == PS, steam_id))


def _write_files(folder: Path, files: dict[str, bytes]) -> None:
    for name, data in files.items():
        atomic_write(Path(folder) / name, data)


# Games whose PC saves carry a SteamID that a copy from a console must set
_STEAM_ID_GAMES = frozenset({"elden_ring", "nightreign", "dark_souls_2"})

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
    source_platform: str = PC

    @property
    def cross_platform(self) -> bool:
        return self.source_platform != self.target_flavor.platform

    @property
    def target_is_folder(self) -> bool:
        return _is_folder_target(self.game_key, self.target_flavor)

    @property
    def target_name(self) -> str:
        """The target as shown: its file, or its folder for a folder target."""
        if self.target_is_folder:
            return f"{self.target_flavor.label} in {self.target.parent.name}"
        return self.target.name

    @property
    def needs_steam_id(self) -> bool:
        """True when the copy creates a PC save from a console save and the
        game keeps a SteamID in it."""
        return (
            self.target_flavor.platform == PC
            and self.source_platform != PC
            and self.game_key in _STEAM_ID_GAMES
        )

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


def make_plan(
    game_key: str, source: Path, ext: str, folder: Path | None = None
) -> Plan:
    """Check the source characters and the target for copying source to the
    target ext: a PC extension (standard or custom) or a console target's
    ext. A target on the source's own platform defaults to the source's
    folder, as does any target when folder is None. Raises
    ExtensionCopyError when no copy is possible."""
    source = Path(source)
    game = _GAMES.get(game_key)
    if game is None:
        raise ExtensionCopyError("This game is not supported.")
    dst = target_flavor(game_key, ext)
    ext = dst.ext
    src_platform = source_platform(source)

    target = platform_target(game_key, source, dst, folder)
    if ps_userdata.save_identity(target) == ps_userdata.save_identity(source) or (
        target.resolve() == source.resolve()
    ):
        raise ExtensionCopyError(
            f"The save already uses {ext}."
            if dst.platform == PC
            else "Choose a folder other than the save's own folder."
        )

    if src_platform == PC:
        src = flavor_of(source, game_key)
    else:
        src = CONSOLE_TARGETS[game_key][src_platform]
    target_exists = _target_exists(game_key, dst, target)
    if not target_exists and dst.platform != src_platform:
        reason = game.cannot_build(src_platform, dst.platform)
        if reason:
            raise ExtensionCopyError(reason)
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
        src_platform,
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
    atomic_write(target, source.read_bytes())


def write_copy(plan: Plan, slots: list[int], steam_id: int | None = None) -> None:
    """Make the target a copy of the source holding only the given slots.
    Replaces an existing target (backed up first). steam_id is required
    when plan.needs_steam_id."""
    chosen = set(slots)
    allowed = {c.slot for c in plan.copyable}
    if not chosen <= allowed:
        raise ExtensionCopyError("A blocked character cannot be copied.")
    if plan.needs_steam_id and not steam_id:
        raise ExtensionCopyError("Choose the Steam account for the PC save.")
    game = _GAMES[plan.game_key]
    if plan.cross_platform:
        reason = game.cannot_build(plan.source_platform, plan.target_flavor.platform)
        if reason:
            raise ExtensionCopyError(reason)
    _backup_target(plan)

    drop = [c.slot for c in plan.characters if c.slot not in chosen]
    if not drop and not plan.cross_platform:
        _copy_bytes(plan.source, plan.target)
        return

    save = game.load(plan.source)
    for i in drop:
        game.delete(save, i)
    if plan.cross_platform:
        game.write_as(save, plan.target_flavor, plan.target, steam_id or 0)
    else:
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
