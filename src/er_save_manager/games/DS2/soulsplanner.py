"""
Import of Dark Souls II builds from soulsplanner.com.

The planner has no export. A build page (soulsplanner.com/darksouls2/<id>)
embeds the build as a JS object literal in an inline script:

  var plannerId='darksouls2',savedBuild={class_:'knight',gender:0,
    covenant:'No_Covenant',armor:'<head>;<chest>;<hands>;<legs>',
    weapons:'<weapon>;<infusion>;... (6 pairs)',grip:0,
    rings:'<4 slugs>',spells:'<14 slugs>',items:'<10 slugs>',
    vigor:50,endurance:28,...};

Values are planner slugs (see soulsplanner_database). Builds carry no upgrade
levels, so those are chosen at import. The planner lists weapons left then
right hand per set (lh1, rh1, lh2, rh2, lh3, rh3), the order of the save's
equipment block, so a build can also be equipped slot for slot.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from er_save_manager.games.DS2.item_database import UNSAFE_IDS, build_item_db
from er_save_manager.games.DS2.regulation import INFUSION_NAMES
from er_save_manager.games.DS2.save import KEEP_SLOT, LEVEL_STAT_KEYS, Character
from er_save_manager.games.DS2.soulsplanner_database import (
    ARMOR,
    ITEMS,
    RINGS,
    SPELLS,
    WEAPONS,
)

_BUILD_URL = "https://soulsplanner.com/darksouls2/{build_id}"
_HOSTS = frozenset({"soulsplanner.com", "www.soulsplanner.com"})
_PATH_PATTERN = re.compile(r"^/darksouls2/(\d+)/?$")
_SAVED_BUILD_PATTERN = re.compile(r"savedBuild\s*=\s*\{(.*?)\}\s*;", re.DOTALL)
# Object literal fields: bare keys, single-quoted strings or integers.
_FIELD_PATTERN = re.compile(r"(\w+)\s*:\s*(?:'((?:[^'\\]|\\.)*)'|(-?\d+))")
_FETCH_TIMEOUT = 15

# Stacking categories whose amount is chosen at import. Spells stack too, but
# are always learned with a full set of uses (see Character.add_item).
QUANTITY_CATEGORIES = frozenset(Character.STACKABLE_CATEGORIES - {"spells"})

# The planner's empty-slot placeholders.
_EMPTY_SLUGS = frozenset({"Naked", "No_Ring", "No_Spell", "No_Item", "Bare_Fists"})
_NO_INFUSION = "No_Infusion"

# Every starting class satisfies level == attribute sum - 53, and so does every
# level-up, which adds one point. Checked against all eight planner classes and
# the characters of a real save.
LEVEL_STAT_OFFSET = 53
STAT_MIN = 1
STAT_MAX = 99


class PlannerError(ValueError):
    """The link or page could not be turned into a build."""


@dataclass
class PlannerItem:
    """One distinct item of a build. count is how many slots hold it."""

    slug: str
    item_id: int
    name: str
    category: str
    infusion: int = 0
    count: int = 1


# A build slot: (item id, infusion index), None when the build leaves it
# empty, or UNKNOWN_SLOT when it holds an item that cannot be imported.
Slot = tuple[int, int] | None | object
UNKNOWN_SLOT = object()


@dataclass
class PlannerLoadout:
    """The build's equipment per slot, in the save's equipment order."""

    weapons: list[Slot] = field(default_factory=list)  # L1, R1, L2, R2, L3, R3
    armor: list[Slot] = field(default_factory=list)  # head, chest, hands, legs
    rings: list[Slot] = field(default_factory=list)
    belt: list[Slot] = field(default_factory=list)


@dataclass
class PlannerBuild:
    build_id: str
    class_name: str
    stats: dict[str, int]
    items: list[PlannerItem]
    # Slugs with no known item id, never added.
    unknown: list[str] = field(default_factory=list)
    loadout: PlannerLoadout = field(default_factory=PlannerLoadout)

    @property
    def level(self) -> int:
        return sum(self.stats.values()) - LEVEL_STAT_OFFSET


@dataclass
class ImportResult:
    added: int = 0
    no_space: list[str] = field(default_factory=list)
    infusion_fallback: list[str] = field(default_factory=list)


def parse_build_id(text: str) -> str:
    """Build id from a planner link or a bare id. Raises PlannerError.

    The link's host must be exactly one of _HOSTS. Only the id is kept, the
    page is always fetched from _BUILD_URL.
    """
    text = text.strip()
    if text.isdigit():
        return text
    if "://" not in text:
        text = f"https://{text}"
    try:
        parts = urllib.parse.urlsplit(text)
        host = (parts.hostname or "").lower()
    except ValueError as e:
        raise PlannerError("Not a soulsplanner.com build link.") from e
    if parts.scheme.lower() not in ("http", "https") or host not in _HOSTS:
        raise PlannerError("Not a soulsplanner.com build link.")
    match = _PATH_PATTERN.match(parts.path)
    if match is None:
        raise PlannerError(
            "Only Dark Souls II builds (soulsplanner.com/darksouls2/...) "
            "can be imported."
        )
    return match.group(1)


def fetch_build_html(build_id: str) -> str:
    """Download a build page. Raises PlannerError on network failure."""
    request = urllib.request.Request(
        _BUILD_URL.format(build_id=build_id),
        headers={"User-Agent": "Mozilla/5.0 (er-save-manager)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_FETCH_TIMEOUT) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise PlannerError(f"Build {build_id} does not exist.") from e
        raise PlannerError(f"soulsplanner.com returned HTTP {e.code}.") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise PlannerError(f"Could not reach soulsplanner.com: {e}") from e


def _slugs(value: str) -> list[str]:
    return [s for s in value.split(";") if s]


def parse_build_html(html: str, build_id: str) -> PlannerBuild:
    """Build from a planner page. Raises PlannerError when the page holds no
    readable build."""
    match = _SAVED_BUILD_PATTERN.search(html)
    if match is None:
        raise PlannerError("Build not found on soulsplanner.com.")
    fields: dict[str, str | int] = {}
    for key, text, number in _FIELD_PATTERN.findall(match.group(1)):
        fields[key] = int(number) if number else text

    try:
        stats = {key: int(fields[key]) for key in LEVEL_STAT_KEYS}
    except (KeyError, ValueError) as e:
        raise PlannerError(f"The build is missing attribute {e}.") from e

    item_db = build_item_db()
    found: dict[tuple[int, int], PlannerItem] = {}
    unknown: list[str] = []

    loadout = PlannerLoadout()

    def add(slug: str, table: dict[str, int], infusion: int = 0) -> Slot:
        if slug in _EMPTY_SLUGS:
            return None
        item_id = table.get(slug)
        info = item_db.get(item_id) if item_id is not None else None
        if info is None or item_id in UNSAFE_IDS:
            unknown.append(slug.replace("_", " "))
            return UNKNOWN_SLOT
        key = (item_id, infusion)
        if key in found:
            found[key].count += 1
        else:
            found[key] = PlannerItem(slug, item_id, info[0], info[1], infusion)
        return key

    weapons = _slugs(str(fields.get("weapons", "")))
    for weapon, infusion_slug in zip(weapons[0::2], weapons[1::2], strict=False):
        infusion_name = "Normal" if infusion_slug == _NO_INFUSION else infusion_slug
        infusion = (
            INFUSION_NAMES.index(infusion_name)
            if infusion_name in INFUSION_NAMES
            else 0
        )
        loadout.weapons.append(add(weapon, WEAPONS, infusion))
    for key, table, slots in (
        ("armor", ARMOR, loadout.armor),
        ("rings", RINGS, loadout.rings),
        ("spells", SPELLS, None),
        ("items", ITEMS, loadout.belt),
    ):
        for slug in _slugs(str(fields.get(key, ""))):
            slot = add(slug, table)
            if slots is not None:
                slots.append(slot)

    return PlannerBuild(
        build_id=build_id,
        class_name=str(fields.get("class_", "")).capitalize(),
        stats=stats,
        items=list(found.values()),
        unknown=unknown,
        loadout=loadout,
    )


def load_build(link: str) -> PlannerBuild:
    build_id = parse_build_id(link)
    return parse_build_html(fetch_build_html(build_id), build_id)


def stat_problems(build: PlannerBuild) -> list[str]:
    """Attributes outside the range the game allows."""
    return [
        f"{name.capitalize()} {value}"
        for name, value in build.stats.items()
        if not STAT_MIN <= value <= STAT_MAX
    ]


def apply_stats(character: Character, build: PlannerBuild) -> None:
    """Write the build's attributes and the level they add up to."""
    for name, value in build.stats.items():
        character.set_stat(name, value)
    character.set_stat("level", build.level)


def owned_items(character: Character, items: list[PlannerItem]) -> list[PlannerItem]:
    """Items the character already has a copy of, carried or in the item box.
    Weapons count regardless of upgrade and infusion."""
    return [item for item in items if character.owns(item.item_id, include_box=True)]


def display_name(item: PlannerItem) -> str:
    name = item.name
    if item.infusion:
        name = f"{INFUSION_NAMES[item.infusion]} {name}"
    # Only weapons get one copy per build slot, other items are added once.
    if item.category == "weapons" and item.count > 1:
        name = f"{name} x{item.count}"
    return name


def apply_items(
    character: Character,
    items: list[PlannerItem],
    upgrades: dict[tuple[int, int], int],
    quantities: dict[int, int],
) -> ImportResult:
    """Add the items, one copy per build slot for weapons. upgrades maps
    (item_id, infusion) to the upgrade level of a weapon or armor piece,
    quantities maps the item id of a QUANTITY_CATEGORIES item to its amount.
    An amount added onto an owned stack is capped at the stack limit."""
    result = ImportResult()
    for item in items:
        name = display_name(item)
        if item.category == "weapons":
            upgrade = upgrades.get((item.item_id, item.infusion), 0)
            written = character.add_copies(
                item.item_id,
                "weapons",
                item.count,
                upgrade=upgrade,
                infusion=item.infusion,
            )
            result.added += written
            if written < item.count:
                result.no_space.append(name)
            if written and item.infusion not in character.allowed_infusions(
                item.item_id
            ):
                result.infusion_fallback.append(name)
            continue
        upgrade = upgrades.get((item.item_id, item.infusion), 0)
        quantity = quantities.get(item.item_id, 1)
        if character.add_item(
            item.item_id, item.category, quantity=quantity, upgrade=upgrade
        ):
            result.added += 1
        else:
            result.no_space.append(name)
    return result


def has_loadout(build: PlannerBuild) -> bool:
    lo = build.loadout
    return any(
        isinstance(slot, tuple)
        for slot in (*lo.weapons, *lo.armor, *lo.rings, *lo.belt)
    )


def equip_build(
    character: Character,
    build: PlannerBuild,
    upgrades: dict[tuple[int, int], int],
) -> list[str]:
    """Equip the build slot for slot from the carried inventory, emptying
    slots the build leaves empty. Each slot takes a different carried copy,
    preferring one with the build's infusion and the upgrade chosen at
    import. A slot holding an item that cannot be imported (such as the
    Estus Flask) keeps what the character has there. Returns the names of
    build items no carried copy was found for; their slots are left empty."""
    item_db = build_item_db()
    carried = [
        entry for entry in character.inventory() if entry.item_id and not entry.in_box
    ]
    used: set[int] = set()
    missing: list[str] = []

    def pick(slot: Slot, category: str):
        if slot is None:
            return None
        if slot is UNKNOWN_SLOT:
            return KEEP_SLOT
        item_id, infusion = slot
        infusion = infusion if infusion in character.allowed_infusions(item_id) else 0
        upgrade = upgrades.get(slot, 0)
        copies = [e for e in carried if e.item_id == item_id and e.offset not in used]
        if category == "weapons":
            copies.sort(key=lambda e: (e.infusion != infusion, e.upgrade != upgrade))
        elif category == "armors":
            copies.sort(key=lambda e: e.upgrade != upgrade)
        if not copies:
            missing.append(item_db.get(item_id, (str(item_id),))[0])
            return None
        used.add(copies[0].offset)
        return copies[0]

    def slots(build_slots: list[Slot], size: int, category: str) -> list:
        """Picks for every slot of a group; slots past the build's list are
        empty."""
        padded = list(build_slots[:size]) + [None] * (size - len(build_slots))
        return [pick(slot, category) for slot in padded]

    lo = build.loadout
    character.equip(
        slots(lo.weapons, 6, "weapons"),
        slots(lo.armor, 4, "armors"),
        slots(lo.rings, 4, "rings"),
        slots(lo.belt, 10, "goods"),
    )
    return missing
