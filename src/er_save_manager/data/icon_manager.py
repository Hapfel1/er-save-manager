"""
Icon manager for the item browser.

Icons are stored in icons.db (SQLite) alongside this file.
Images are loaded on demand and cached in memory.
Returns PIL Images; callers create CTkImage at the desired display size.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage

_db: sqlite3.Connection | None = None
_available: dict[str, str] | None = None
_cache: dict[str, PILImage.Image] = {}

_SUFFIX_RE = re.compile(r"\s*-\s*MENU_Knowledge_\d+.*$", re.IGNORECASE)
_CAT_PRE_RE = re.compile(r"^\[.*?\]\s*")
_UPG_RE = re.compile(r"\s*\+\d+$")


def _db_path() -> Path:
    return Path(__file__).parent / "icons.db"


def _ensure_loaded() -> bool:
    global _db, _available
    if _available is not None:
        return _db is not None
    _available = {}
    p = _db_path()
    if not p.exists():
        return False
    _db = sqlite3.connect(f"file:{p}?mode=ro", uri=True, check_same_thread=False)
    for (name,) in _db.execute("SELECT name FROM icons"):
        key = _norm_icon(name[:-5] if name.endswith(".webp") else name)
        if key not in _available:
            _available[key] = name
    return True


def _norm_icon(s: str) -> str:
    s = _SUFFIX_RE.sub("", s).strip()
    s = re.sub(r"_s\b", "'s", s)
    s = re.sub(r"_\s", ": ", s)
    # Strip [Sorcery]/[Incantation] prefix - spells keyed without it
    # so lookups work whether the DB entry has the prefix or not
    s = _CAT_PRE_RE.sub("", s)
    # Strip Convergence weapon prefix and numeric ID suffix
    s = re.sub(r"^wep-", "", s, flags=re.I)
    s = re.sub(r"-\d+$", "", s)
    # Split camelCase so "CorpaMagica" -> "Corpa Magica"
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    # Normalize colon spacing ("Note : X" -> "Note: X")
    s = re.sub(r"\s*:\s*", ": ", s)
    # Strip diacritics to match _norm_db (consistent both directions)
    s = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    return s.lower()


def _norm_db(name: str) -> str:
    s = name.lower().replace("\u2019", "'").replace("\u2018", "'")
    # Strip diacritics so "Jolan" matches "Jolan", "Epee" matches "Epee"
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _ammo_lookup(key: str) -> str | None:
    """DB stores ammo as '{Type} - {Name}', icons as '{Name} {Type}'."""
    if _available is None:
        return None
    m = re.match(
        r"^(great arrow|greatbolt|arrow|bolt|ballista bolt)\s*-\s*(.+?)(\s*\(fletched\))?$",
        key,
        re.I,
    )
    if not m:
        return None
    type_, name = m.group(1).lower(), m.group(2).strip().lower()
    fletched = " (fletched)" if m.group(3) else ""
    for candidate in (
        f"{name} {type_}{fletched}",  # normal: "fire arrow"
        f"{name}{fletched}",  # standalone: "bone ballista bolt"
    ):
        if candidate in _available:
            return _available[candidate]
    return None


# Explicit DB name -> icon key overrides for naming mismatches in packs.
# Keys and values are both lowercase (post _norm_db / _norm_icon).
_NAME_OVERRIDES: dict[str, str] = {
    # Convergence weapon pack typos / word-order mismatches
    "blade of distant light": "blade of dsitant light",
    "blades of the prince": "blade of the prince",
    "caimar's battlestaff": "caimars battle staff",
    "emyr's great talons": "emyrs-great-talons",
    "glaive of the ancients": "glaive of ancients",
    # Convergence talismans
    "firemonk's filigree": "fire monk's filigree",
    "runebear's claw": "runebears claw",
    # Convergence rune - Dragonkin uses {N}_Rarity_Dragonkin_Rune filename format
    "faint rune of the dragonkin": "faint dragonkin rune",
    "shimmering rune of the dragonkin": "shimmering dragonkin rune",
    "glowing rune of the dragonkin": "glowing dragonkin rune",
    "shining rune of the dragonkin": "4 radiant dragonkin rune",
    "radiant rune of the dragonkin": "5 radient dragonkin rune",
    # Convergence rune - DB has "Shinning" typo for Glintstone tier 4
    "shinning rune of glintstone": "shining rune of glintstone",
    # Convergence rune tier 4: pack uses "Radiant" name, DB uses "Shining"
    "shining rune of magma": "radiant rune of magma",
    "shining rune of necromancy": "radiant rune of necromancy",
    "shining rune of frost": "radiant rune of frost",
    "shining rune of thorns": "radiant rune of thorns",
    "shining rune of fell flame": "radiant rune of fell flame",
    "shining rune of order": "radiant rune of order",
    "shining rune of beasts": "radiant rune of beasts",
    "shining rune of lightning": "radiant rune of lightning",
    "shining rune of ancestors": "radiant rune of ancestors",
    # Convergence rune tier 6: icon filenames use "6_Shadow_Rune_of_X" prefix
    "shadow rune of ancestors": "6_shadow_rune_of_ancestors",
    "shadow rune of beasts": "6_shadow_rune_of_beasts",
    "shadow rune of blackflame": "6_shadow_rune_of_blackflame",
    "shadow rune of bloodflame": "6_shadow_rune_of_bloodflame",
    "shadow rune of fell flame": "6_shadow_rune_of_fell_flame",
    "shadow rune of frenzy": "6_shadow_rune_of_frenzy",
    "shadow rune of frost": "6_shadow_rune_of_frost",
    "shadow rune of glintstone": "6_shadow_rune_of_glint",
    "shadow rune of gravity": "6_shadow_rune_of_gravity",
    "shadow rune of lightning": "6_shadow_rune_of_lightning",
    "shadow rune of magma": "6_shadow_rune_of_magma",
    "shadow rune of necromancy": "6_shadow_rune_of_necromancy",
    "shadow rune of night": "6_shadow_rune_of_night",
    "shadow rune of order": "6_shadow_rune_of_order",
    "shadow rune of rot": "6_shadow_rune_of_rot",
    "shadow rune of the dragonkin": "6_shadow_dragonkin_rune",
    "shadow rune of the storm": "6_shadow_rune_of_storm",
    "shadow rune of thorns": "6_shadow_rune_of_thorns",
    # Merchant items
    "golden order principles": "golden order principia",
    # Prattling Pate "You're beautiful" - double quotes in DB name, plain name in icon
    "prattling pate \u201cyou\u2019re beautiful\u201d": "prattling pate you're beautiful",
    'prattling pate "you\'re beautiful"': "prattling pate you're beautiful",
    # Ashes: DB name without "Ashes" suffix, icon stored with it
    "banished knight oleg": "banished knight oleg ashes",
    "banished knight engvall": "banished knight engvall ashes",
    "battlemage hugues": "battlemage hugues ashes",
    "cleanrot knight finlay": "cleanrot knight finlay ashes",
    "blackflame monk amon": "blackflame monk amon ashes",
    "ancient dragon knight kristoff": "ancient dragon knight kristoff ashes",
    "depraved perfumer carmaan": "depraved perfumer carmaan ashes",
    "blighted nox ancestor": "blighted nox ancenstor",
    # Key items
    "the stormhawk king": "the stormhawk king",
    # DLC weapons - flavor suffix in DB name, plain name in pack
    "greatsword of radahn (light)": "greatsword of radahn",
    "greatsword of radahn (relict)": "greatsword of radahn",
    # Convergence ashes - spelling mismatch
    "putrescence sorcerer": "putrescent sorcerer",
    # Convergence melee - typo in pack ("ride" instead of "rite")
    "deathrite dagger": "deathride-dagger",
    # 3.0 spell icons - apostrophe, abbreviation and underscore mismatches
    "ice guardian's reckoning": "ice guardian reckoning",
    "maker's lament": "makers lament",
    "lion's breath": "lions breath",
    "shadow of death": "shadow_of_death",
    "scadu rebirth": "scadu_rebirth",
    "putrid salvo": "putrid_salvo",
    "putrid shardstorm": "putrid_shardstorm",
    "thorn field": "thornfield",
    "creeping vines": "creep thorns",
    "terrifying presence": "terr presence",
    "frenzied lunge": "frenzy lunge",
    "blood of the maiden": "bloodof the maiden",
    "lulling dart-fly": "dartfly",
    "fleeting vapor-fly": "vaporfly",
    "gaze of the basilisk": "rot_gaze_of_the_basilisk",
    "frenzied flame blade": "frenzy_armament",
    # 3.0 weapons - icon filenames don't match item names
    # values use post-camelCase-split keys produced by _norm_icon
    "stormcaller's dirk": "storm dagger",
    "quicksilver fragment": "quicksilver dagger",
    "maddening brand": "frenzy ss",
    "maddening brand [frenzy]": "frenzy ss",
    "regalia of noxumbra": "regalia of noxumbra",
    "regal splitblade (gs)": "quality trick greatsword",
    "regal splitblade (dual light greatswords)": "quality trick greatsword",
    "greatsword of midra": "frenzy ugs",
    "fingerprint hexmark [frenzy]": "frenzy ugs",
    "galvanic culling blade [twinblade]": "dragonkin twinblade",
    "crucifix of eochaid": "crucifix of eochaid big",
    "cragsplitter": "strength spear",
    "rhys' swordspear": "rhys spear",
    "starcaller mattock": "starcaller mandril",
    "halberd of archea": "archea halberd",
    "glaive of the crusade": "glaive of crusade",
    "crystaline claw": "crystal pincer",
    "fingerslayer blade": "fingerslayer blade",
    "[conv] fingerslayer blade": "fingerslayer blade",
    "crescent moons": "moon cirque",
    "konrad's bloodletter": "konrad sword",
    "nia's passot": "nias passot",
    "primeval splinter": "crystal lgs",
    "[conv] primeval splinter": "crystal lgs",
    "goras' claw": "goras claws big",
    "smithscript rosary": "rosary",
    "scadu sapling": "scadu bow",
    "[conv] scadu sapling": "scadu bow",
    "devonia's longbow": "crucible bow",
    "demi-dragon cleaver": "dragonkin subject cleaver",
    "maliketh's black blade (restored)": "restored malikeths",
    # 3.0 spirit ashes
    "blaidd ashes": "blaidd",
    "titanus, shell-bound companion": "turtle",
    "noxumbra gaoler ashes": "jailers",
    "demidragon ashes": "demi dragons",
    "tempestcaller ashes": "tempestcaller",
    "twinned jellyfish ashes": "twin jellyfish",
}


def _lookup(name: str, category_name: str = "") -> str | None:
    if not _ensure_loaded() or _available is None:
        return None

    key = _norm_db(name)
    # Strip [Sorcery]/[Incantation] prefix so spell lookups work without prefixed icon entries
    key = _CAT_PRE_RE.sub("", key).strip()
    key = _UPG_RE.sub("", key).rstrip()

    # Direct override
    if key in _NAME_OVERRIDES:
        override = _NAME_OVERRIDES[key]
        if override in _available:
            return _available[override]

    if key in _available:
        return _available[key]

    # Category prefix fallback: "Weapon: Longsword" -> "Longsword"
    if ": " in key:
        bare = key.split(": ", 1)[1]
        if bare in _available:
            return _available[bare]

    if "(empty)" in key:
        no_empty = re.sub(r"\s*\(empty\)$", "", key, flags=re.I).rstrip()
        no_empty = _UPG_RE.sub("", no_empty).rstrip()
        if no_empty in _available:
            return _available[no_empty]

    # Unpowered great rune: strip "(Unpowered)"
    no_unpow = re.sub(r"\s*\(unpowered\)$", "", key, flags=re.I).rstrip()
    if no_unpow != key and no_unpow in _available:
        return _available[no_unpow]

    # Prattling Pate: `"Hello"` in DB -> `_Hello_` in icon filename
    pp = re.sub(r'"([^"]+)"', lambda m: f"_{m.group(1).lower()}_", key)
    if pp != key and pp in _available:
        return _available[pp]

    # Ammo: "Arrow - Fire" -> "Fire Arrow"
    ammo = _ammo_lookup(key)
    if ammo:
        return ammo

    # Talisman/item name: "Branchsword" -> "Branch Sword"
    alt = key.replace("branchsword", "branch sword")
    if alt != key and alt in _available:
        return _available[alt]

    # Numbered items: strip "[N]" suffix, try base name then [1]
    no_num = re.sub(r"\s*\[\d+\]$", "", key).rstrip()
    if no_num != key:
        if no_num in _available:
            return _available[no_num]
        one = no_num + " [1]"
        if one in _available:
            return _available[one]

    # "Axe Of Epiphany" -> try "Epiphany Axe" inversion (Convergence weapon naming)
    m = re.match(r"^(.+?)\s+of\s+(?:the\s+)?(.+)$", key)
    if m:
        inv = f"{m.group(2)} {m.group(1)}"
        if inv in _available:
            return _available[inv]

    # "Keystone 1" -> try "Keystone1" (Convergence key items stored without space)
    no_space = key.replace(" ", "")
    if no_space != key and no_space in _available:
        return _available[no_space]

    # Bell bearings: numbered ones (e.g. "[1]") fall back to generic icon
    _bb_key = no_num if no_num != key else key
    if _bb_key.endswith("bell bearing"):
        for _bb in (
            "general bell bearing",
            "patches_ _ kale_s _ gostoc_s _ blackguard_s _ pidia_s bell bearing",
        ):
            if _bb in _available:
                return _available[_bb]

    # Note/Map base-game icons lack the colon: "Note Gateway" vs "Note: Gateway"
    if key.startswith("note: "):
        no_colon = "note " + key[6:]
        if no_colon in _available:
            return _available[no_colon]
        for _fallback in (
            "note gateway",
            "note demi-human mobs",
            "note waypoint ruins",
        ):
            if _fallback in _available:
                return _available[_fallback]
    if key.startswith("map: "):
        region = key[5:]
        paren = f"map ({region})"
        if paren in _available:
            return _available[paren]
        for _fallback in (
            "map (limgrave, west)",
            "map (altus plateau)",
            "map (caelid)",
        ):
            if _fallback in _available:
                return _available[_fallback]

    # Convergence icon filenames after merge use camelCase-split names.
    # Catches remaining mismatches from merge normalization.
    cnv = re.sub(r"([a-z])([A-Z])", r"\1 \2", key).lower()
    cnv = re.sub(r"_s\b", "'s", cnv).replace("_", " ").strip()
    if cnv != key and cnv in _available:
        return _available[cnv]

    return None


def icons_available() -> bool:
    return _ensure_loaded()


def has_icon(name: str) -> bool:
    return _lookup(name) is not None


def get_icon(name: str, category_name: str = "") -> PILImage.Image | None:
    """Return a PIL RGBA image for the item name, or None if not found."""
    entry = _lookup(name, category_name)
    if entry is None:
        return None
    if entry in _cache:
        return _cache[entry]
    if _db is None:
        return None
    try:
        from PIL import Image

        row = _db.execute("SELECT data FROM icons WHERE name = ?", (entry,)).fetchone()
        if row is None:
            return None
        img = Image.open(BytesIO(row[0])).convert("RGBA")
        _cache[entry] = img
        return img
    except Exception:
        return None


def coverage_stats() -> dict[str, int]:
    _ensure_loaded()
    return {"total_icons": len(_available) if _available else 0, "cached": len(_cache)}


# ---- affinity icons ---------------------------------------------------------

# Maps affinity display name -> icon lookup name.
# Icons are stored as e.g. "Standard.webp" from Elden_Ring_Affinity_*.webp files.
# Vanilla affinity icons
_AFFINITY_ICON_VANILLA: dict[str, str] = {
    "Standard": "Standard",
    "Heavy": "Heavy",
    "Keen": "Keen",
    "Quality": "Quality",
    "Fire": "Fire",
    "Flame Art": "Flame Art",
    "Lightning": "Lightning",
    "Sacred": "Sacred",
    "Magic": "Magic",
    "Cold": "Cold",
    "Poison": "Poison",
    "Blood": "Blood",
    "Occult": "Occult",
}

# Convergence affinity icons - user imports these with matching filenames
_AFFINITY_ICON_CNV: dict[str, str] = {
    "Standard": "Standard",
    "Heavy": "Heavy",
    "Keen": "Keen",
    "Quality": "Quality",
    "Glint": "Glint",
    "Dragonkin": "Dragonkin",
    "Gravity": "Gravity",
    "Flame": "Flame",
    "Golden": "Golden",
    "Draconic": "Draconic",
    "Bestial": "Bestial",
    "Night": "Night",
    "Lava": "Lava",
    "Frenzy": "Frenzy",
    "Death": "Death",
    "Godslayer": "Godslayer",
    "Frost": "Frost",
    "Aberrant": "Aberrant",
    "Bloodflame": "Bloodflame",
    "Rotten": "Rotten",
    "Storm": "Storm",
    "Psionic": "Psionic",
}

# Combined map for backward-compat callers that don't pass is_convergence
_AFFINITY_ICON: dict[str, str] = {**_AFFINITY_ICON_VANILLA, **_AFFINITY_ICON_CNV}


def get_affinity_icon(
    affinity_name: str, is_convergence: bool = False
) -> PILImage.Image | None:
    """Return the icon for an affinity name, or None if unavailable."""
    table = _AFFINITY_ICON_CNV if is_convergence else _AFFINITY_ICON_VANILLA
    icon_name = table.get(affinity_name, affinity_name)
    return get_icon(icon_name)


def compose_weapon_icon(
    weapon: PILImage.Image,
    aow: PILImage.Image | None = None,
    affinity: PILImage.Image | None = None,
    overlay_size: int = 26,
) -> PILImage.Image:
    """
    Return a 64x64 composite: weapon base with optional AoW overlay (top-left)
    and affinity overlay (bottom-right).
    """
    try:
        from PIL import Image

        base = weapon.copy().convert("RGBA").resize((64, 64), Image.LANCZOS)
        if aow:
            sm = aow.convert("RGBA").resize((overlay_size, overlay_size), Image.LANCZOS)
            base.alpha_composite(sm, (2, 2))
        if affinity:
            sm = affinity.convert("RGBA").resize(
                (overlay_size, overlay_size), Image.LANCZOS
            )
            base.alpha_composite(sm, (64 - overlay_size - 2, 64 - overlay_size - 2))
        return base
    except Exception:
        return weapon
