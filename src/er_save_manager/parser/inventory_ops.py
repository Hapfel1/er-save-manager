"""
Inventory operations for Elden Ring save files.

Supported categories and their storage mechanism:

  0x00000000  Weapons       gaitem prefix 0x8, size 21 (has gem_gaitem_handle)
  0x10000000  Armor         gaitem prefix 0x9, size 16
  0x20000000  Talismans     A0 direct handle, no gaitem entry
  0x40000000  Goods/Spells  B0 direct handle, no gaitem entry
  0x80000000  Gems/AoW      gaitem prefix 0xC, size 8 - gaitem entry only, no inventory entry

All public functions mutate the Save object in place. The caller must call
save.recalculate_checksums() and save.to_file() after all operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save

_CAT_WEAPON = 0x00000000
_CAT_ARMOR = 0x10000000
_CAT_TALISMAN = 0x20000000
_CAT_GOODS = 0x40000000
_CAT_GEM = 0x80000000

_PREFIX_WEAPON = 0x80000000  # gaitem handle prefix, size 21
_PREFIX_ARMOR = 0x90000000  # gaitem handle prefix, size 16
_PREFIX_TALISMAN = 0xA0000000  # direct handle, no gaitem entry
_PREFIX_DIRECT = 0xB0000000  # goods and spells direct handle
_PREFIX_GEM = 0xC0000000  # gaitem handle prefix, size 8

SLOT_DATA_SIZE = 0x280000

# Upgrade caps by reinforcement type
UPGRADE_CAP_STANDARD = 25
UPGRADE_CAP_SOMBER = 10
UPGRADE_CAP_ASH = 10


# ---- category helpers -------------------------------------------------------


def _category(full_item_id: int) -> int:
    return full_item_id & 0xF0000000


def _needs_gaitem(full_item_id: int) -> bool:
    return _category(full_item_id) in (_CAT_WEAPON, _CAT_ARMOR, _CAT_GEM)


# Goods base IDs (without 0x40000000) that go in key_items, not common_items.
# Sourced from KeyItems.csv plus cookbooks/whetblades which appear in separate CSVs.
_KEY_ITEM_BASE_IDS: frozenset[int] = frozenset(
    [
        # Multiplayer items
        100,  # Tarnished's Furled Finger
        101,  # Duelist's Furled Finger
        102,  # Bloody Finger
        103,  # Finger Severer
        104,  # White Cipher Ring
        105,  # Blue Cipher Ring
        106,  # Tarnished's Wizened Finger
        107,  # Phantom Bloody Finger
        108,  # Taunter's Tongue
        109,  # Small Golden Effigy
        110,  # Small Red Effigy
        111,  # Festering Bloody Finger
        112,  # Recusant Finger
        113,  # Phantom Bloody Finger
        114,  # Phantom Recusant Finger
        115,  # Memory of Grace
        130,  # Spectral Steed Whistle
        135,  # Phantom Great Rune
        # Great Runes (powered)
        191,  # Godrick's Great Rune
        192,  # Radahn's Great Rune
        193,  # Morgott's Great Rune
        194,  # Rykard's Great Rune
        195,  # Mohg's Great Rune
        196,  # Malenia's Great Rune
        # Other key items
        2090,  # Deathroot
        8000,  # Stonesword Key
        8010,  # Rusty Key
        8102,  # Lucent Baldachin's Blessing
        8105,  # Dectus Medallion (Left)
        8106,  # Dectus Medallion (Right)
        8107,  # Rold Medallion
        8109,  # Academy Glintstone Key
        8111,  # Carian Inverted Statue
        8121,  # Dark Moon Ring
        8126,  # Fingerprint Grape
        8127,  # Letter from Volcano Manor
        8128,  # Tonic of Forgetfulness
        8129,  # Serpent's Amnion
        8130,  # Rya's Necklace
        8131,  # Irina's Letter
        8132,  # Letter from Volcano Manor
        8133,  # Red Letter
        8134,  # Drawing-Room Key
        8136,  # Rya's Necklace
        8137,  # Volcano Manor Invitation
        8142,  # Amber Starlight
        8143,  # Seluvis's Introduction
        8144,  # Sellen's Primal Glintstone
        8146,  # Miniature Ranni
        # Great Runes (unpowered)
        8148,  # Godrick's Great Rune (Unpowered)
        8149,  # Radahn's Great Rune (Unpowered)
        8150,  # Morgott's Great Rune (Unpowered)
        8151,  # Rykard's Great Rune (Unpowered)
        8152,  # Mohg's Great Rune (Unpowered)
        8153,  # Malenia's Great Rune (Unpowered)
        # Quest items continued
        8154,  # Lord of Blood's Favor
        8155,  # Lord of Blood's Favor (Soaked)
        8156,  # Burial Crow's Letter
        8158,  # Spirit Calling Bell
        8159,  # Fingerslayer Blade
        8161,  # Sewing Needle
        8162,  # Gold Sewing Needle
        8163,  # Tailoring Tools
        8164,  # Seluvis's Potion
        8166,  # Amber Draught
        8167,  # Letter to Patches
        8168,  # Dancer's Castanets
        8169,  # Sellian Sealbreaker
        8171,  # Chrysalids' Memento
        8172,  # Black Knifeprint
        8173,  # Letter to Bernahl
        8174,  # Academy Glintstone Key (Spare)
        8175,  # Haligtree Secret Medallion (Left)
        8176,  # Haligtree Secret Medallion (Right)
        8181,  # Burial Crow's Letter
        8182,  # Mending Rune of Perfect Order
        8183,  # Mending Rune of the Death-Prince
        8184,  # Mending Rune of the Fell Curse
        8185,  # Larval Tear
        8186,  # Imbued Sword Key
        8187,  # Miniature Ranni (Lifeless)
        8188,  # Golden Tailoring Tools
        8189,  # Iji's Confession
        8190,  # Knifeprint Clue
        8191,  # Cursemark of Death
        8192,  # Asimi's Husk
        8193,  # Seedbed Curse
        8194,  # The Stormhawk King
        8196,  # Unalloyed Gold Needle
        8197,  # Sewer-Gaol Key
        8198,  # Meeting Place Map
        8199,  # Discarded Palace Key
        # Crafting
        8500,  # Crafting Kit
        # Whetstone / whetblades
        8590,  # Whetstone Knife
        8970,  # Iron Whetblade
        8971,  # Red-Hot Whetblade
        8972,  # Sanctified Whetblade
        8973,  # Glintstone Whetblade
        8974,  # Black Whetblade
        8975,  # Unalloyed Gold Needle (Snapped)
        8976,  # Unalloyed Gold Needle (Repaired)
        8977,  # Valkyrie's Prosthesis
        8978,  # Sellia's Secret
        8979,  # Beast Eye
        8980,  # Weathered Dagger
        # Great Rune of the Unborn
        10080,
        10060,  # Dragon Heart
        10070,  # Lost Ashes of War
        # Containers and upgrades
        10030,  # Memory Stone
        10040,  # Talisman Pouch
        9500,  # Cracked Pot
        9501,  # Ritual Pot
        9510,  # Perfume Bottle
        2009500,  # Hefty Cracked Pot
        # Vanilla cookbooks
        9300,
        9301,
        9302,
        9303,
        9305,
        9306,
        9307,
        9308,
        9309,
        9310,
        9311,
        9312,
        9313,
        9320,
        9321,
        9322,
        9323,
        9325,
        9326,
        9327,
        9328,
        9329,
        9330,
        9331,
        9340,
        9341,
        9342,
        9343,
        9344,
        9345,
        9346,
        9347,
        9348,
        9360,
        9361,
        9363,
        9364,
        9365,
        9380,
        9383,
        9384,
        9385,
        9386,
        9387,
        9388,
        9389,
        9390,
        9391,
        9392,
        9400,
        9401,
        9402,
        9403,
        9420,
        9421,
        9422,
        9423,
        9440,
        9441,
        # DLC key items
        2008000,  # Miquella's Great Rune
        2008003,  # Igon's Furled Finger
        2008004,  # Well Depths Key
        2008005,  # Gaol Upper Level Key
        2008006,  # Gaol Lower Level Key
        2008007,  # Cross Map
        2008008,  # Hole-Laden Necklace
        2008011,  # Heart of Bayle
        2008012,  # New Cross Map
        2008013,  # Storeroom Key
        2008014,  # Secret Rite Scroll
        2008019,  # Black Syrup
        2008021,  # Messmer's Kindling
        2008023,  # Keep Wall Key
        2008033,  # Larval Tear (Spirit)
        2008036,  # Prayer Room Key
        # Crystal Tears
        11000,  # Crimsonspill Crystal Tear
        11001,  # Greenspill Crystal Tear
        11002,  # Crimson Crystal Tear
        11003,  # Crimson Crystal Tear
        11004,  # Cerulean Crystal Tear
        11005,  # Cerulean Crystal Tear
        11006,  # Speckled Hardtear
        11007,  # Crimson Bubbletear
        11008,  # Opaline Bubbletear
        11009,  # Crimsonburst Crystal Tear
        11010,  # Greenburst Crystal Tear
        11011,  # Opaline Hardtear
        11012,  # Winged Crystal Tear
        11013,  # Thorny Cracked Tear
        11014,  # Spiked Cracked Tear
        11015,  # Windy Crystal Tear
        11016,  # Ruptured Crystal Tear
        11017,  # Ruptured Crystal Tear
        11018,  # Leaden Hardtear
        11019,  # Twiggy Cracked Tear
        11020,  # Crimsonwhorl Bubbletear
        11021,  # Strength-knot Crystal Tear
        11022,  # Dexterity-knot Crystal Tear
        11023,  # Intelligence-knot Crystal Tear
        11024,  # Faith-knot Crystal Tear
        11025,  # Cerulean Hidden Tear
        11026,  # Stonebarb Cracked Tear
        11027,  # Purifying Crystal Tear
        11028,  # Flame-Shrouding Cracked Tear
        11029,  # Magic-Shrouding Cracked Tear
        11030,  # Lightning-Shrouding Cracked Tear
        11031,  # Holy-Shrouding Cracked Tear
        # DLC Crystal Tears
        2011000,  # Viridian Hidden Tear
        2011010,  # Crimsonburst Dried Tear
        2011020,  # Crimson-Sapping Cracked Tear
        2011030,  # Cerulean-Sapping Cracked Tear
        2011040,  # Oil-Soaked Tear
        2011050,  # Bloodsucking Cracked Tear
        2011060,  # Glovewort Crystal Tear
        2011070,  # Deflecting Hardtear
        # Maps
        8600,  # Map: Limgrave
        8601,  # Map: Weeping Peninsula
        8602,  # Map: Limgrave
        8603,  # Map: Liurnia
        8604,  # Map: Liurnia
        8605,  # Map: Liurnia
        8606,  # Map: Altus Plateau
        8607,  # Map: Leyndell
        8608,  # Map: Mt. Gelmir
        8609,  # Map: Caelid
        8610,  # Map: Dragonbarrow
        8611,  # Map: Mountaintops of the Giants
        8612,  # Map: Mountaintops of the Giants
        8613,  # Map: Ainsel River
        8614,  # Map: Lake of Rot
        8615,  # Map: Siofra River
        8616,  # Map: Mohgwyn Palace
        8617,  # Map: Deeproot Depths
        8618,  # Map: Consecrated Snowfield
        # DLC Maps
        2008600,  # Map: Gravesite Plain
        2008601,  # Map: Scadu Altus
        2008602,  # Map: Southern Shore
        2008603,  # Map: Rauh Ruins
        2008604,  # Map: Abyss
        # Convergence Maps (separate IDs from base game)
        8620,  # Map: Limgrave
        8621,  # Map: Caelid
        8622,  # Map: Liurnia
        8623,  # Map: Altus Plateau
        8624,  # Map: Mountaintops of the Giants
        8625,  # Map: Consecrated Snowfield
        8626,  # Map: Farum Azula
        8627,  # Map: Underground
        8628,  # Map: Realm of Shadow
        8660,  # Map: Mirage Riddle
        # Bell Bearings and Spellbooks (MerchantItems)
        8850,  # Conspectus Scroll
        8851,  # Royal House Scroll
        8855,  # Fire Monks' Prayerbook
        8856,  # Giant's Prayerbook
        8857,  # Godskin Prayerbook
        8858,  # Two Fingers' Prayerbook
        8859,  # Assassin's Prayerbook
        8860,  # Erdtree Prayerbook
        8861,  # Erdtree Codex
        8862,  # Golden Order Principia
        8863,  # Golden Order Principles
        8864,  # Dragon Cult Prayerbook
        8865,  # Ancient Dragon Prayerbook
        8866,  # Academy Scroll
        8910,  # Pidia's Bell Bearing
        8911,  # Seluvis's Bell Bearing
        8912,  # Patches' Bell Bearing
        8913,  # Sellen's Bell Bearing
        8915,  # D's Bell Bearing
        8916,  # Bernahl's Bell Bearing
        8917,  # Miriel's Bell Bearing
        8918,  # Gostoc's Bell Bearing
        8919,  # Thops's Bell Bearing
        8920,  # Kale's Bell Bearing
        8921,  # Nomadic Merchant's Bell Bearing [1]
        8922,  # Nomadic Merchant's Bell Bearing [2]
        8923,  # Nomadic Merchant's Bell Bearing [3]
        8924,  # Nomadic Merchant's Bell Bearing [4]
        8925,  # Nomadic Merchant's Bell Bearing [5]
        8926,  # Isolated Merchant's Bell Bearing [1]
        8927,  # Isolated Merchant's Bell Bearing [2]
        8928,  # Nomadic Merchant's Bell Bearing [6]
        8929,  # Hermit Merchant's Bell Bearing [1]
        8930,  # Nomadic Merchant's Bell Bearing [7]
        8931,  # Nomadic Merchant's Bell Bearing [8]
        8932,  # Nomadic Merchant's Bell Bearing [9]
        8933,  # Nomadic Merchant's Bell Bearing [10]
        8934,  # Nomadic Merchant's Bell Bearing [11]
        8935,  # Isolated Merchant's Bell Bearing [3]
        8936,  # Hermit Merchant's Bell Bearing [2]
        8937,  # Abandoned Merchant's Bell Bearing
        8938,  # Hermit Merchant's Bell Bearing [3]
        8939,  # Imprisoned Merchant's Bell Bearing
        8940,  # Iji's Bell Bearing
        8941,  # Rogier's Bell Bearing
        8942,  # Blackguard's Bell Bearing
        8943,  # Corhyn's Bell Bearing
        8944,  # Gowry's Bell Bearing
        8945,  # Bone Peddler's Bell Bearing
        8946,  # Meat Peddler's Bell Bearing
        8947,  # Medicine Peddler's Bell Bearing
        8948,  # Gravity Stone Peddler's Bell Bearing
        8951,  # Smithing-Stone Miner's Bell Bearing [1]
        8952,  # Smithing-Stone Miner's Bell Bearing [2]
        8953,  # Smithing-Stone Miner's Bell Bearing [3]
        8954,  # Smithing-Stone Miner's Bell Bearing [4]
        8955,  # Somberstone Miner's Bell Bearing [1]
        8956,  # Somberstone Miner's Bell Bearing [2]
        8957,  # Somberstone Miner's Bell Bearing [3]
        8958,  # Somberstone Miner's Bell Bearing [4]
        8959,  # Somberstone Miner's Bell Bearing [5]
        8960,  # Glovewort Picker's Bell Bearing [1]
        8961,  # Glovewort Picker's Bell Bearing [2]
        8962,  # Glovewort Picker's Bell Bearing [3]
        8963,  # Ghost-Glovewort Picker's Bell Bearing [1]
        8964,  # Ghost-Glovewort Picker's Bell Bearing [2]
        8965,  # Ghost-Glovewort Picker's Bell Bearing [3]
        # DLC Bell Bearings
        2008900,  # Moore's Bell Bearing
        2008901,  # Ymir's Bell Bearing
        2008902,  # Herbalist's Bell Bearing
        2008903,  # Mushroom-Seller's Bell Bearing [1]
        2008904,  # Mushroom-Seller's Bell Bearing [2]
        2008905,  # Greasemonger's Bell Bearing
        2008906,  # Moldmonger's Bell Bearing
        2008907,  # Igon's Bell Bearing
        2008908,  # Spellmachinist's Bell Bearing
        2008909,  # String-Seller's Bell Bearing
        # Convergence Crystal Tears
        11032,  # Stone-Shrouding Cracked Tear
        11033,  # Arcane-Knot Crystal Tear
        11034,  # Knight's Crystal Tear
        11035,  # Battlemage's Crystal Tear
        11036,  # Templar's Crystal Tear
        11037,  # Barbarian's Crystal Tear
        11038,  # Assassin's Crystal Tear
        11039,  # Inquisitor's Crystal Tear
        11040,  # Rogue's Crystal Tear
        11041,  # Zealot's Crystal Tear
        11042,  # Witch's Crystal Tear
        11043,  # Cultist's Crystal Tear
        11050,  # Waterblade Cracked Tear
        11051,  # Stonetalon Cracked Tear
        11052,  # Windbarb Cracked Tear
        11053,  # Shadowblade Cracked Tear
        11054,  # Stoneblade Cracked Tear
        11055,  # Stonehoof Cracked Tear
        11056,  # Ceruleanburst Crystal Tear
        11057,  # Ceruleanspill Crystal Tear
        # Convergence Bell Bearings
        8981,  # Shadow Stone Miner's Bell Bearing [1]
        8982,  # Shadow Stone Miner's Bell Bearing [2]
        8983,  # Shadow Stone Miner's Bell Bearing [3]
        8984,  # Somber Shadow Stone Miner's Bell Bearing [1]
        8985,  # Somber Shadow Stone Miner's Bell Bearing [2]
        8986,  # Somber Shadow Stone Miner's Bell Bearing [3]
        # Convergence Steeds
        2500,  # Funeral Steed
        2501,  # Frenzied Mule
        2502,  # Carian Knight Steed
        2503,  # Erdtree Steed
        # Convergence Keystones
        8060,  # Keystone 1
        8061,  # Keystone 2
        8062,  # Keystone 3
        8063,  # Keystone 4
        8064,  # Keystone 5
        # Convergence Perfumer items and Putrid Key
        8138,  # Putrid Key
        8510,  # Perfumer Hammer Shell
        8511,  # Perfumer's Fire Core
        8512,  # Perfumer's Frost Core
        8513,  # Perfumer's Lightning Core
        8514,  # Perfumer's Frenzy Core
        # DLC cookbooks
        2009301,
        2009302,
        2009303,
        2009304,
        2009305,
        2009306,
        2009307,
        2009308,
        2009309,
        2009310,
        2009311,
        2009312,
        2009313,
        2009314,
        2009315,
        2009316,
        2009317,
        2009318,
        2009319,
        2009320,
        2009321,
        2009322,
        2009323,
        2009324,
        2009325,
        2009326,
        2009327,
        2009328,
        2009329,
        2009330,
        2009331,
        2009332,
        2009333,
        2009334,
        2009335,
        2009336,
        2009337,
        2009338,
        2009339,
        2009340,
        2009341,
        2009342,
        2009343,
        2009344,
        2009345,
    ]
)


def _is_key_item(full_item_id: int) -> bool:
    """Return True if this goods item belongs in key_items rather than common_items."""
    if _category(full_item_id) != _CAT_GOODS:
        return False
    return (full_item_id & 0x0FFFFFFF) in _KEY_ITEM_BASE_IDS


def _gaitem_prefix(full_item_id: int) -> int:
    cat = _category(full_item_id)
    if cat == _CAT_WEAPON:
        return _PREFIX_WEAPON
    if cat == _CAT_ARMOR:
        return _PREFIX_ARMOR
    if cat == _CAT_GEM:
        return _PREFIX_GEM
    raise ValueError(f"no gaitem prefix for item 0x{full_item_id:08X}")


def _direct_handle(full_item_id: int) -> int:
    """Direct inventory handle for goods, spells, and talismans."""
    base = full_item_id & 0x00FFFFFF
    if _category(full_item_id) == _CAT_TALISMAN:
        return (_PREFIX_TALISMAN | base) & 0xFFFFFFFF
    return (_PREFIX_DIRECT | base) & 0xFFFFFFFF


def validate_upgrade(
    upgrade: int, reinforcement: str = "standard", convergence: bool = False
) -> int:
    """
    Clamp and validate upgrade level for the given reinforcement type.

    Args:
        upgrade: Requested upgrade level.
        reinforcement: "standard" (max 25), "somber" (max 10), or "ash" (max 10).
        convergence: When True, standard and somber caps are both 15.

    Returns:
        Clamped upgrade level.

    Raises:
        ValueError: Unknown reinforcement type.
    """
    caps = {
        "standard": UPGRADE_CAP_STANDARD,
        "somber": UPGRADE_CAP_SOMBER,
        "ash": UPGRADE_CAP_ASH,
    }
    if reinforcement not in caps:
        raise ValueError(f"unknown reinforcement type {reinforcement!r}")
    cap = caps[reinforcement]
    if convergence and reinforcement in ("standard", "somber"):
        cap = 15
    if upgrade < 0 or upgrade > cap:
        raise ValueError(f"{reinforcement} upgrade must be 0-{cap}, got {upgrade}")
    return upgrade


# ---- gaitem map helpers -----------------------------------------------------


def _next_gaitem_handle(slot, prefix: int) -> int:
    """
    Generate the next available gaitem handle for weapons, armor, or gems.

    Upper 16 bits encode category. Lower 16 bits are a sequential counter
    shared across all categories so handles from different categories never collide.

    The second byte (bits 16-23) is mirrored from the first non-empty gaitem entry.
    PC saves use 0x80; PS/Switch saves use 0x81-0x87. Writing 0x80 on console
    saves causes the game engine to treat items as phantom/invalid.
    """
    max_lower16 = 0
    second_byte = 0x80  # PC default
    for g in slot.gaitem_map:
        if g.gaitem_handle == 0:
            continue
        g_prefix = g.gaitem_handle & 0xF0000000
        if g_prefix in (_PREFIX_WEAPON, _PREFIX_ARMOR, _PREFIX_GEM):
            lower16 = g.gaitem_handle & 0x0000FFFF
            if lower16 > max_lower16:
                max_lower16 = lower16
            if second_byte == 0x80:
                second_byte = (g.gaitem_handle >> 16) & 0xFF

    next_lower16 = (max_lower16 + 1) & 0xFFFF
    category_high = {
        _PREFIX_WEAPON: 0x80,
        _PREFIX_ARMOR: 0x90,
        _PREFIX_GEM: 0xC0,
    }[prefix]
    return (category_high << 24) | (second_byte << 16) | next_lower16


def _find_empty_gaitem_slot(slot, prefix: int) -> int:
    """
    Return index of the best empty gaitem slot for the given prefix.

    Gems go before the first weapon entry (AoW region) - use the first
    available empty there to keep gems compactly packed.

    Weapons and armor go after the first weapon entry. Return the LAST
    available empty in that region so that the insert position equals the
    last-empty position. The INSERT-before + DELETE-last-empty algorithm in
    _patch_slot_with_gaitem_insert is only orphan-free when they coincide.

    Returns -1 if no suitable slot exists.
    """
    first_weapon_idx = -1
    for i, g in enumerate(slot.gaitem_map):
        if g.gaitem_handle != 0 and (g.gaitem_handle & 0xF0000000) == _PREFIX_WEAPON:
            first_weapon_idx = i
            break

    if prefix == _PREFIX_GEM:
        for i, g in enumerate(slot.gaitem_map):
            if first_weapon_idx != -1 and i >= first_weapon_idx:
                break
            if g.gaitem_handle == 0:
                return i
        return -1

    start = (first_weapon_idx + 1) if first_weapon_idx != -1 else 0
    result = -1
    for i in range(start, len(slot.gaitem_map)):
        if slot.gaitem_map[i].gaitem_handle == 0:
            result = i
    return result


def _find_gaitem_by_item(slot, full_item_id: int):
    """
    Find a gaitem entry matching full_item_id.

    For weapons, matches on base_id (ignores upgrade suffix and infusion code).
    For gems, matches on either full_item_id or base_id.
    For armor and other types, matches on exact item_id.

    Returns (gaitem_index, gaitem_entry) or (-1, None).
    """
    cat_bits = _category(full_item_id)
    base_id = full_item_id & 0x0FFFFFFF
    for i, g in enumerate(slot.gaitem_map):
        if g.gaitem_handle == 0:
            continue
        g_prefix = g.gaitem_handle & 0xF0000000
        if cat_bits == _CAT_WEAPON:
            if g_prefix != _PREFIX_WEAPON:
                continue
            stored_base = (g.item_id & 0x0FFFFFFF) // 10000 * 10000
            want_base = base_id // 10000 * 10000
            if stored_base == want_base:
                return i, g
        elif cat_bits == _CAT_GEM:
            if g_prefix != _PREFIX_GEM:
                continue
            # Match either base_id or full_item_id
            if g.item_id == base_id or g.item_id == full_item_id:
                return i, g
        else:
            if _category(g.item_id) != cat_bits:
                continue
            if g.item_id == full_item_id:
                return i, g
    return -1, None


def _gaitem_last_empty(slot, slot_data_base: int) -> int | None:
    """Return absolute buffer offset of the last empty gaitem entry, or None."""
    result = None
    for i, g in enumerate(slot.gaitem_map):
        if g.gaitem_handle == 0:
            result = slot_data_base + slot.gaitem_offsets[i]
    return result


# ---- inventory helpers ------------------------------------------------------


def _global_next_acq_index(slot) -> int:
    """Return next globally unique acquisition index (max across all inventories + 2)."""
    max_seen = 0
    for inv in (slot.inventory_held, slot.inventory_storage_box):
        for it in inv.common_items:
            # Ignore corrupted indices that exceed the 32-bit signed integer limit
            if (
                it.gaitem_handle != 0
                and it.acquisition_index < 0x7FFFFFFF
                and it.acquisition_index > max_seen
            ):
                max_seen = it.acquisition_index
        for it in inv.key_items:
            # Ignore corrupted indices that exceed the 32-bit signed integer limit
            if (
                it.gaitem_handle != 0
                and it.acquisition_index < 0x7FFFFFFF
                and it.acquisition_index > max_seen
            ):
                max_seen = it.acquisition_index
    return max_seen + 2


def _first_empty_inv_slot(inventory) -> int:
    """Return index of first common_items slot with gaitem_handle == 0, or -1."""
    for i, it in enumerate(inventory.common_items):
        if it.gaitem_handle == 0:
            return i
    return -1


def _first_empty_key_slot(inventory) -> int:
    """Return index of first key_items slot with gaitem_handle == 0, or -1."""
    for i, it in enumerate(inventory.key_items):
        if it.gaitem_handle == 0:
            return i
    return -1


def _find_handle_slot(item_list, handle: int) -> int:
    """Return index of the entry with the given gaitem_handle, or -1."""
    for i, it in enumerate(item_list):
        if it.gaitem_handle == handle:
            return i
    return -1


def _select_inventory(slot, location: str):
    if location == "held":
        return slot.inventory_held
    if location == "storage":
        return slot.inventory_storage_box
    raise ValueError(f"location must be 'held' or 'storage', got {location!r}")


# ---- binary patch helpers ---------------------------------------------------


def _patch_slot(save: Save, slot_idx: int, slot) -> None:
    """
    Write modified inventory bytes directly into save._raw_data.

    Serializes only the affected Inventory structs and patches their exact byte
    ranges, leaving all other slot data untouched.
    """
    from io import BytesIO

    slot_data_base = save.slot_data_offset(slot_idx)

    if slot.inventory_held_offset:
        buf = BytesIO()
        slot.inventory_held.write(buf)
        data = buf.getvalue()
        abs_off = slot_data_base + slot.inventory_held_offset
        save._raw_data[abs_off : abs_off + len(data)] = data

    if slot.inventory_storage_offset:
        buf = BytesIO()
        slot.inventory_storage_box.write(buf)
        data = buf.getvalue()
        abs_off = slot_data_base + slot.inventory_storage_offset
        save._raw_data[abs_off : abs_off + len(data)] = data


def _patch_slot_with_gaitem_insert(
    save: Save,
    slot_idx: int,
    slot,
    gaitem_idx: int,
    new_gaitem_bytes: bytes,
    old_gaitem_size: int,
) -> int:
    """
    Insert/replace a gaitem entry in the binary slot data.

    Returns the net byte shift applied to everything after the gaitem region
    (inventory, event flags, etc.) so the caller can update in-memory offsets.

    delta == 0: direct overwrite. Net shift = 0.

    delta > 0 (expand, e.g. empty 8 -> armor 16 or weapon 21):
        1. INSERT new entry at entry_abs.
        2. Delete 8 bytes at last_ga_empty (shifted position after step 1).
        3. Trim (new_size - 8) bytes from slot end.
        Net shift = new_size - 8.

    delta < 0 (shrink, e.g. weapon 21 -> empty 8):
        1. INSERT small entry at entry_abs.
        2. Delete old large entry.
        3. Append abs(delta) zeros at slot end.
        Net shift = -(old_size - new_size).
    """
    slot_data_base = save.slot_data_offset(slot_idx)
    entry_abs_off = slot_data_base + slot.gaitem_offsets[gaitem_idx]
    new_size = len(new_gaitem_bytes)
    delta = new_size - old_gaitem_size

    if delta == 0:
        save._raw_data[entry_abs_off : entry_abs_off + new_size] = new_gaitem_bytes
        return 0

    if delta > 0:
        # Prefer trimming genuine trailing zero bytes at the slot end.
        # If there aren't enough, rebuild_slot re-serializes the slot
        # (preserving real trailing data - see slot_rebuild.py) and the
        # trim below proceeds regardless, intentionally cutting into
        # that trailing data rather than failing the add. See the note
        # further down for why this is a deliberate tradeoff.
        trim = delta
        slot_end_before = slot_data_base + SLOT_DATA_SIZE
        trailing_zeros = 0
        for i in range(slot_end_before - 1, slot_end_before - trim - 1, -1):
            if i >= 0 and save._raw_data[i] == 0:
                trailing_zeros += 1
            else:
                break

        if trailing_zeros < trim:
            from er_save_manager.parser.slot_rebuild import rebuild_slot

            # rebuild_slot re-serializes the slot from the parsed structure
            # and preserves every byte captured on read, including
            # slot.rest - it no longer manufactures extra zero-padding
            # here (see slot_rebuild.py). If the slot's real trailing
            # bytes still don't cover `trim` after this, the add proceeds
            # anyway and the trim below cuts into that trailing data
            # rather than blocking the add. That trailing region's exact
            # contents are not currently identified (see slot_rebuild.py
            # notes on slot.rest).
            rebuilt = rebuild_slot(slot)
            save._raw_data[slot_data_base : slot_data_base + SLOT_DATA_SIZE] = rebuilt
            entry_abs_off = slot_data_base + slot.gaitem_offsets[gaitem_idx]

        last_empty_abs = _gaitem_last_empty(slot, slot_data_base)

        save._raw_data[entry_abs_off:entry_abs_off] = new_gaitem_bytes

        if last_empty_abs is not None:
            shifted = last_empty_abs + new_size
            del save._raw_data[shifted : shifted + 8]
        else:
            inv_shifted = slot_data_base + slot.inventory_held_offset + new_size
            del save._raw_data[inv_shifted - 8 : inv_shifted]

        if trim > 0:
            current_end = slot_data_base + SLOT_DATA_SIZE + new_size - 8
            del save._raw_data[current_end - trim : current_end]

        return new_size - 8

    else:
        abs_delta = -delta
        save._raw_data[entry_abs_off:entry_abs_off] = new_gaitem_bytes
        del save._raw_data[
            entry_abs_off + new_size : entry_abs_off + new_size + old_gaitem_size
        ]
        slot_end = slot_data_base + SLOT_DATA_SIZE - abs_delta
        save._raw_data[slot_end:slot_end] = bytes(abs_delta)
        return -abs_delta


# ---- gaitem construction ----------------------------------------------------


def _make_gaitem(full_item_id: int, handle: int, upgrade: int = 0):
    """
    Create a Gaitem struct for weapons, armor, or gems.

    Weapons: item_id = base_id + upgrade (no category bits, cat = 0x00).
    Armor:   item_id = full_item_id (0x10000000 | base, fits in int32).
    Gems:    item_id = base_id only (0x80000000 bit NOT stored; derived from 0xC0 handle).
    """
    from er_save_manager.parser.er_types import Gaitem

    cat = _category(full_item_id)
    base_id = full_item_id & 0x0FFFFFFF
    g = Gaitem()
    g.gaitem_handle = handle

    if cat == _CAT_WEAPON:
        g.item_id = base_id + upgrade
    elif cat == _CAT_GEM:
        g.item_id = base_id
    else:
        g.item_id = full_item_id  # armor

    if cat in (_CAT_WEAPON, _CAT_ARMOR):
        g.unk0x10 = 0
        g.unk0x14 = 0
        if cat == _CAT_WEAPON:
            g.gem_gaitem_handle = 0
            g.unk0x1c = 0

    return g


# ---- core gaitem operations -------------------------------------------------


def insert_gaitem(
    save: Save,
    slot_idx: int,
    full_item_id: int,
    upgrade: int = 0,
    gem_handle: int = 0,
) -> tuple[int, int]:
    """
    Insert a gaitem entry into the slot's gaitem map without touching inventory.

    Used for AoW gems (which exist only in the gaitem map) and as the first
    step of add_item for weapons and armor.

    Args:
        save: Parsed Save instance.
        slot_idx: Character slot index 0-9.
        full_item_id: Full item id with category bits.
        upgrade: Upgrade level for weapons (0 for others).
        gem_handle: Ash of War handle to link to a weapon gaitem.

    Returns:
        (gaitem_handle, net_shift) - handle assigned to the new entry, and the
        net byte shift applied to everything after the gaitem region.

    Raises:
        ValueError: Category has no gaitem, map is full.
    """
    from io import BytesIO

    if not _needs_gaitem(full_item_id):
        raise ValueError(f"item 0x{full_item_id:08X} does not use a gaitem entry")

    slot = save.character_slots[slot_idx]
    if slot.is_empty():
        raise ValueError(f"slot {slot_idx} is empty")

    prefix = _gaitem_prefix(full_item_id)
    handle = _next_gaitem_handle(slot, prefix)

    empty_g = _find_empty_gaitem_slot(slot, prefix)
    if empty_g == -1:
        raise ValueError("gaitem map is full")

    new_gaitem = _make_gaitem(full_item_id, handle, upgrade)

    if _category(full_item_id) == _CAT_WEAPON and gem_handle:
        new_gaitem.gem_gaitem_handle = (
            gem_handle - 0x100000000 if gem_handle >= 0x80000000 else gem_handle
        )

    buf = BytesIO()
    new_gaitem.write(buf)
    new_gaitem_bytes = buf.getvalue()
    gaitem_size = len(new_gaitem_bytes)
    size_delta = gaitem_size - 8

    # Patch the binary first so rebuild_slot (called when trailing zeros
    # are exhausted) serializes the original map without the new weapon.
    # Updating gaitem_map before the patch caused rebuild to write the weapon
    # twice, corrupting everything that followed.
    net_shift = _patch_slot_with_gaitem_insert(
        save, slot_idx, slot, empty_g, new_gaitem_bytes, old_gaitem_size=8
    )
    slot.gaitem_map[empty_g] = new_gaitem

    entry_rel = slot.gaitem_offsets[empty_g]
    for i, off in enumerate(slot.gaitem_offsets):
        if off > entry_rel:
            slot.gaitem_offsets[i] += size_delta

    if net_shift != 0:
        slot.player_game_data_offset += net_shift
        slot.inventory_held_offset += net_shift
        slot.inventory_storage_offset += net_shift
        slot.gestures_offset += net_shift
        slot.horse_offset += net_shift
        slot.blood_stain_offset += net_shift
        slot.event_flags_offset += net_shift
        slot.coordinates_offset += net_shift
        slot.net_man_offset += net_shift
        slot.weather_offset += net_shift
        slot.time_offset += net_shift
        slot.steamid_offset += net_shift
        slot.dlc_offset += net_shift

    return handle, net_shift


def _remove_gaitem(save: Save, slot_idx: int, slot, gaitem_idx: int) -> int:
    """
    Remove a gaitem entry from the slot, replacing it with an empty 8-byte slot.

    Returns the net byte shift (negative = gaitem region shrank).
    """
    from io import BytesIO

    from er_save_manager.parser.er_types import Gaitem

    old_gaitem_size = slot.gaitem_map[gaitem_idx].get_size()
    gaitem_size_delta = 8 - old_gaitem_size

    empty_gaitem = Gaitem()
    buf = BytesIO()
    empty_gaitem.write(buf)
    empty_bytes = buf.getvalue()

    slot.gaitem_map[gaitem_idx] = empty_gaitem

    net_shift = _patch_slot_with_gaitem_insert(
        save,
        slot_idx,
        slot,
        gaitem_idx,
        empty_bytes,
        old_gaitem_size=old_gaitem_size,
    )

    if gaitem_size_delta != 0:
        for i in range(gaitem_idx + 1, len(slot.gaitem_offsets)):
            slot.gaitem_offsets[i] += gaitem_size_delta
        slot.player_game_data_offset += net_shift
        slot.inventory_held_offset += net_shift
        slot.inventory_storage_offset += net_shift
        slot.gestures_offset += net_shift
        slot.horse_offset += net_shift
        slot.blood_stain_offset += net_shift
        slot.event_flags_offset += net_shift
        slot.coordinates_offset += net_shift
        slot.net_man_offset += net_shift
        slot.weather_offset += net_shift
        slot.time_offset += net_shift
        slot.steamid_offset += net_shift
        slot.dlc_offset += net_shift

    return net_shift


def _update_inv_counters(slot, inventory, location: str, acq_idx: int) -> None:
    """Update acquisition and equip index counters after adding an inventory entry."""
    slot.inventory_held.acquisition_index_counter = acq_idx
    if location == "storage":
        inv_s = slot.inventory_storage_box
        inv_s.equip_index_counter = (
            0x80 if inv_s.equip_index_counter == 0 else inv_s.equip_index_counter + 1
        )
        inv_s.acquisition_index_counter = acq_idx
    else:
        slot.inventory_held.equip_index_counter += 1


# ---- public API -------------------------------------------------------------


def add_item(
    save: Save,
    slot_idx: int,
    full_item_id: int,
    quantity: int,
    location: str = "held",
    upgrade: int = 0,
    gem_full_id: int = 0,
    reinforcement: str = "standard",
    convergence: bool = False,
) -> dict:
    """
    Add an item to the character's inventory.

    Args:
        save: Parsed Save instance.
        slot_idx: Character slot index 0-9.
        full_item_id: Full item id including category bits.
        quantity: Stack size (use 1 for weapons/armor/talismans/gems).
        location: "held" or "storage".
        upgrade: Upgrade level. Validated against reinforcement type.
        gem_full_id: Full id of an Ash of War to attach to a weapon. The gem
                     is added to the gaitem map only (no inventory entry).
        reinforcement: "standard", "somber", or "ash" - determines upgrade cap.
        convergence: When True, standard and somber upgrade caps are both 15.

    Returns:
        Dict with keys: gaitem_handle, full_item_id, quantity, acquisition_index,
        inventory_slot, location, new_common_item_count.

    Raises:
        ValueError: Unknown category, invalid upgrade, item already present,
                    gaitem map full, or inventory full.
    """
    from er_save_manager.parser.equipment import InventoryItem

    cat = _category(full_item_id)
    if cat not in (_CAT_WEAPON, _CAT_ARMOR, _CAT_TALISMAN, _CAT_GOODS, _CAT_GEM):
        raise ValueError(
            f"unknown item category 0x{cat:08X} for item 0x{full_item_id:08X}"
        )

    if cat == _CAT_WEAPON and upgrade:
        upgrade = validate_upgrade(upgrade, reinforcement, convergence)

    # AoW: insert gem into gaitem map only (no inventory entry needed).
    gem_handle = 0
    if cat == _CAT_WEAPON and gem_full_id and _category(gem_full_id) == _CAT_GEM:
        try:
            gem_handle, _ = insert_gaitem(save, slot_idx, gem_full_id)
        except Exception:
            gem_handle = 0  # continue without AoW on failure

    slot = save.character_slots[slot_idx]
    if slot.is_empty():
        raise ValueError(f"slot {slot_idx} is empty")

    inventory = _select_inventory(slot, location)

    handle = None
    gaitem_slot = None

    if _needs_gaitem(full_item_id):
        handle, _ = insert_gaitem(save, slot_idx, full_item_id, upgrade, gem_handle)
        # Re-read slot after insert_gaitem updated offsets
        slot = save.character_slots[slot_idx]
        inventory = _select_inventory(slot, location)
        # Find the gaitem slot we just inserted
        gaitem_slot, _ = _find_gaitem_by_item(slot, full_item_id)
    else:
        handle = _direct_handle(full_item_id)

    # Reject if already in inventory (talismans allow duplicates)
    if cat != _CAT_TALISMAN:
        item_list = (
            inventory.key_items
            if _is_key_item(full_item_id)
            else inventory.common_items
        )
        for it in item_list:
            if it.gaitem_handle == handle and it.quantity > 0:
                raise ValueError(
                    f"item 0x{full_item_id:08X} already present (handle 0x{handle:08X})"
                )

    acq_idx = _global_next_acq_index(slot)

    is_key = _is_key_item(full_item_id)
    if is_key:
        inv_slot = _first_empty_key_slot(inventory)
        if inv_slot == -1:
            raise ValueError(f"key_items inventory is full in {location}")
    else:
        inv_slot = _first_empty_inv_slot(inventory)
        if inv_slot == -1:
            if location == "held":
                # Held inventory full - fall back to storage
                location = "storage"
                inventory = _select_inventory(slot, location)
                inv_slot = _first_empty_inv_slot(inventory)
                if inv_slot == -1:
                    raise ValueError("both held and storage inventories are full")
            else:
                raise ValueError("storage inventory is full")

    entry = InventoryItem()
    entry.gaitem_handle = handle
    entry.quantity = quantity
    entry.acquisition_index = acq_idx

    if is_key:
        inventory.key_items[inv_slot] = entry
    else:
        inventory.common_items[inv_slot] = entry
    if is_key:
        inventory.key_item_count += 1
    else:
        inventory.common_item_count += 1
    _update_inv_counters(slot, inventory, location, acq_idx)

    _patch_slot(save, slot_idx, slot)

    return {
        "gaitem_handle": handle,
        "full_item_id": full_item_id,
        "quantity": quantity,
        "acquisition_index": acq_idx,
        "inventory_slot": inv_slot,
        "location": location,
        "new_common_item_count": inventory.common_item_count,
        **({"gaitem_slot": gaitem_slot} if gaitem_slot is not None else {}),
    }


def remove_item(
    save: Save,
    slot_idx: int,
    full_item_id: int,
    location: str = "held",
) -> dict:
    """
    Remove an item from the inventory.

    Zeros the inventory slot, decrements common_item_count, and for gaitem
    items also removes the gaitem map entry.

    Returns:
        Dict with keys: gaitem_handle, full_item_id, inventory_slot, location,
        old_quantity, new_common_item_count.
    """
    from er_save_manager.parser.equipment import InventoryItem

    cat = _category(full_item_id)
    if cat not in (_CAT_WEAPON, _CAT_ARMOR, _CAT_TALISMAN, _CAT_GOODS, _CAT_GEM):
        raise ValueError(
            f"unknown item category 0x{cat:08X} for item 0x{full_item_id:08X}"
        )

    slot = save.character_slots[slot_idx]
    if slot.is_empty():
        raise ValueError(f"slot {slot_idx} is empty")

    inventory = _select_inventory(slot, location)

    if _needs_gaitem(full_item_id):
        gaitem_idx, g = _find_gaitem_by_item(slot, full_item_id)
        if gaitem_idx == -1:
            raise ValueError(f"item 0x{full_item_id:08X} not found in gaitem map")
        handle = g.gaitem_handle
    else:
        handle = _direct_handle(full_item_id)
        gaitem_idx = -1

    # _is_key_item classifies by display category (KeyItems.csv), which does
    # not always match the raw list the item is actually stored in. Search
    # the expected list first, then fall back to the other list.
    is_key = _is_key_item(full_item_id)
    item_list = inventory.key_items if is_key else inventory.common_items
    inv_slot = _find_handle_slot(item_list, handle)
    if inv_slot == -1:
        other_list = inventory.common_items if is_key else inventory.key_items
        other_slot = _find_handle_slot(other_list, handle)
        if other_slot != -1:
            is_key = not is_key
            item_list = other_list
            inv_slot = other_slot

    if inv_slot == -1:
        raise ValueError(
            f"item 0x{full_item_id:08X} not found in {location!r} inventory "
            f"(handle 0x{handle:08X})"
        )
    old_qty = item_list[inv_slot].quantity

    item_list[inv_slot] = InventoryItem()
    if is_key:
        inventory.key_item_count = max(0, inventory.key_item_count - 1)
    else:
        inventory.common_item_count = max(0, inventory.common_item_count - 1)

    if gaitem_idx != -1:
        _remove_gaitem(save, slot_idx, slot, gaitem_idx)
        # Re-read slot after _remove_gaitem updated offsets
        slot = save.character_slots[slot_idx]
        inventory = _select_inventory(slot, location)

    _patch_slot(save, slot_idx, slot)

    return {
        "gaitem_handle": handle,
        "full_item_id": full_item_id,
        "inventory_slot": inv_slot,
        "location": location,
        "old_quantity": old_qty,
        "new_common_item_count": inventory.common_item_count,
    }


def set_quantity(
    save: Save,
    slot_idx: int,
    full_item_id: int,
    quantity: int,
    location: str = "held",
) -> dict:
    """
    Set the stack quantity of an existing inventory entry.

    Only meaningful for stackable items (goods/spells).

    Returns:
        Dict with keys: gaitem_handle, full_item_id, inventory_slot, location,
        old_quantity, new_quantity.
    """
    if quantity < 1:
        raise ValueError(f"quantity must be >= 1, got {quantity}")

    cat = _category(full_item_id)
    if cat not in (_CAT_WEAPON, _CAT_ARMOR, _CAT_TALISMAN, _CAT_GOODS, _CAT_GEM):
        raise ValueError(
            f"unknown item category 0x{cat:08X} for item 0x{full_item_id:08X}"
        )

    slot = save.character_slots[slot_idx]
    if slot.is_empty():
        raise ValueError(f"slot {slot_idx} is empty")

    inventory = _select_inventory(slot, location)

    if _needs_gaitem(full_item_id):
        _, g = _find_gaitem_by_item(slot, full_item_id)
        if g is None:
            raise ValueError(f"item 0x{full_item_id:08X} not found in gaitem map")
        handle = g.gaitem_handle
    else:
        handle = _direct_handle(full_item_id)

    # _is_key_item classifies by display category (KeyItems.csv), which does
    # not always match the raw list the item is actually stored in. Search
    # the expected list first, then fall back to the other list.
    is_key = _is_key_item(full_item_id)
    item_list = inventory.key_items if is_key else inventory.common_items
    inv_slot = _find_handle_slot(item_list, handle)
    if inv_slot == -1:
        other_list = inventory.common_items if is_key else inventory.key_items
        other_slot = _find_handle_slot(other_list, handle)
        if other_slot != -1:
            item_list = other_list
            inv_slot = other_slot

    if inv_slot == -1:
        raise ValueError(
            f"item 0x{full_item_id:08X} not found in {location!r} inventory "
            f"(handle 0x{handle:08X})"
        )
    old_qty = item_list[inv_slot].quantity

    item_list[inv_slot].quantity = quantity
    _patch_slot(save, slot_idx, slot)

    return {
        "gaitem_handle": handle,
        "full_item_id": full_item_id,
        "inventory_slot": inv_slot,
        "location": location,
        "old_quantity": old_qty,
        "new_quantity": quantity,
    }
