"""
Region ID database for Elden Ring.

Region IDs are stored in the Regions struct (count + list of u32 IDs).
When teleporting to a map, add the corresponding region ID to ensure
the map label appears on screen. ID 0 means no region unlock is needed.

Values sourced from community research into save file region unlock flags.
"""

from __future__ import annotations

# region_id -> region name
REGIONS: dict[int, str] = {
    # Limgrave
    6100000: "Limgrave - The First Step",
    6100001: "Limgrave - Seaside Ruins",
    6100002: "Limgrave - Agheel Lake North",
    6100003: "Limgrave - Summonwater Village Outskirts",
    6100004: "Limgrave - Mistwood Outskirts",
    6100090: "Limgrave - Church of Dragon Communion",
    6101000: "Limgrave - Stormhill Shack",
    6101010: "Limgrave - Margit, the Fell Omen",
    6102000: "Limgrave - Weeping Peninsula (West)",
    6102001: "Limgrave - Weeping Peninsula (East)",
    6102002: "Limgrave - Castle Morne",
    # Liurnia
    6200000: "Liurnia - Lake-Facing Cliffs",
    6200001: "Liurnia - Liurnia Highway South",
    6200002: "Liurnia - Liurnia Lake Shore",
    6200004: "Liurnia - Eastern Tableland",
    6200005: "Liurnia - Crystalline Woods",
    6200006: "Liurnia - The Ravine",
    6200007: "Liurnia - Main Caria Manor Gate",
    6200008: "Liurnia - Behind Caria Manor",
    6200010: "Liurnia - Royal Moongazing Grounds",
    6200090: "Liurnia - Grand Lift of Dectus",
    6201000: "Liurnia - Bellum Church",
    6202000: "Liurnia - Moonlight Altar",
    # Altus Plateau
    6300000: "Altus Plateau - Stormcaller Church",
    6300001: "Altus Plateau - The Shaded Castle",
    6300002: "Altus Plateau - Altus Highway Junction",
    6300004: "Altus Plateau - Dominula, Windmill Village",
    6300005: "Altus Plateau - Rampartside Path",
    6300030: "Altus Plateau - Castellan's Hall",
    6301000: "Altus Plateau - Capital Outskirts",
    6301090: "Altus Plateau - Capital Rampart",
    6302000: "Altus Plateau - Ninth Mt. Gelmir Campsite",
    6302001: "Altus Plateau - Road of Iniquity",
    6302002: "Altus Plateau - Seethewater Terminus",
    # Caelid
    6400000: "Caelid - Caelid Highway South",
    6400001: "Caelid - Caelem Ruins",
    6400002: "Caelid - Chamber Outside the Plaza",
    6400010: "Caelid - Redmane Castle Plaza",
    6400020: "Caelid - Chair-Crypt of Sellia",
    6400040: "Caelid - Starscourge Radahn",
    6401000: "Caelid - Swamp of Aeonia",
    6402000: "Caelid - Dragonbarrow West",
    6402001: "Caelid - Bestial Sanctum",
    # Mountaintops / Forbidden Lands
    6500000: "Mountaintops - Forbidden Lands",
    6500090: "Mountaintops - Grand Lift of Rold",
    6501000: "Mountaintops - Zamor Ruins",
    6501001: "Mountaintops - Central Mountaintops",
    6502000: "Mountaintops - Consecrated Snowfield",
    6502001: "Mountaintops - Inner Consecrated Snowfield",
    6502002: "Mountaintops - Ordina, Liturgical Town",
    # Underground
    6600000: "Siofra River",
    6600001: "Ainsel River Main",
    6600002: "Ainsel River Downstream",
    6600003: "Ainsel River Downstream (deep)",
    6600004: "Lake of Rot",
    6600005: "Deeproot Depths",
    6600006: "Nokron, Eternal City",
    6600007: "Nokstella, Eternal City",
    # Crumbling Farum Azula
    6700000: "Crumbling Farum Azula",
    6700001: "Crumbling Farum Azula - Dragon Temple",
    6700002: "Crumbling Farum Azula - Beside the Great Bridge",
    # Haligtree
    6800000: "Miquella's Haligtree",
    # DLC - Land of Shadow
    6900000: "Gravesite Plain",
    6900001: "Scadu Altus",
    6900002: "Abyssal Woods",
    6900003: "Ancient Ruins of Rauh",
    6900004: "Cerulean Coast / Jagged Peak",
    6900005: "Enir-Ilim",
    6900006: "Shadow Keep",
    # Dungeons (discovered on enter, no separate region ID)
    1000000: "Stormveil Castle",
    1100000: "Leyndell, Royal Capital",
    1100010: "Leyndell - Erdtree Sanctuary",
    1101000: "Roundtable Hold",
    1400000: "Academy of Raya Lucaria",
    1600000: "Volcano Manor",
    1800001: "Stranded Graveyard",
    1900000: "Stone Platform",
}


def get_region_name(region_id: int) -> str:
    return REGIONS.get(region_id, f"Region {region_id}")


def is_dlc_region(region_id: int) -> bool:
    return 6900000 <= region_id <= 6999999
