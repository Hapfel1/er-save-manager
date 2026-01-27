"""
Region ID mapping for Elden Ring.
Maps location names to their corresponding region discovery IDs used in save files.
"""

# Location name to region ID mapping
# Region IDs are used in the save file's unlocked_regions list
LOCATION_TO_REGION = {
    # Limgrave
    "The First Step": 6100000,
    "Seaside Ruins": 6100001,
    "Agheel Lake North": 6100002,
    "Summonwater Village": 6100003,
    "Mistwood": 6100004,
    "Church of Dragon Communion": 6100090,
    "Stormhill": 6101000,
    "Margit, the Fell Omen": 6101010,
    "Castle Morne": 6102001,
    "Weeping Peninsula East": 6102002,
    "Weeping Peninsula West": 6102000,
    # Liurnia
    "Liurnia South": 6200000,
    "Liurnia South East": 6200001,
    "Liurnia South West": 6200002,
    "Liurnia East": 6200004,
    "Liurnia West": 6200005,
    "The Ravine": 6200006,
    "Main Caria Manor Gate": 6200007,
    "Caria Manor": 6200007,
    "Manor Lower Level": 6200007,
    "Behind Caria Manor": 6200008,
    "Royal Moongazing Grounds": 6200010,
    "Grand Lift of Dectus": 6200090,
    "Bellum Highway": 6201000,
    "Moonlight Altar": 6202000,
    # Raya Lucaria Academy
    "Raya Lucaria Grand Library": 1400000,
    "Debate Parlor": 1400010,
    "Main Academy Gate": 1400011,
    "School House Classroom": 1400015,
    "Church of the Cuckoo": 1400013,
    # Altus Plateau
    "Altus Highway Junction": 6300002,
    "Stormcaller Church": 6300000,
    "The Shaded Castle": 6300001,
    "Rampartside Path": 6300005,
    "Castellan's Hall": 6300030,
    "Dominula, Windmill Village": 6300004,
    "Ninth Mt. Gelmir Campsite": 6302000,
    "Road of Iniquity": 6302001,
    "Seethewater Terminus": 6302002,
    # Mt. Gelmir and Volcano Manor
    "Volcano Manor": 1600012,
    "Prison Town Church": 1600014,
    "Temple of Eiglay": 1600010,
    "Guest Hall": 1600016,
    "Audience Pathway": 1600006,
    "Abductor Virgin": 1600020,
    "Subterranean Inquisition Chamber": 1600022,
    "Rykard, Lord of Blasphemy": 1600000,
    "Capital Outskirts": 6301000,
    "Capital Rampart": 6301090,
    # Leyndell, Royal Capital
    "Erdtree Sanctuary": 1100010,
    "East Capital Rampart": 1100012,
    "Lower Capital Church": 1100015,
    "Avenue Balcony": 1100013,
    "Queen's Bedchamber": 1100001,
    "West Capital Rampart": 1100016,
    "Divine Bridge": 1100017,
    "Elden Throne": 1100000,
    # Leyndell, Ashen Capital
    "Leyndell, Capital of Ash": 1105011,
    "Ashen Queen's Bedchamber": 1105001,
    "Ashen Divine Bridge": 1105092,
    "Ashen Elden Throne": 1105000,
    # Stormveil Castle
    "Godrick the Grafted": 1000000,
    "Stormveil Main Gate": 1000001,
    "Gateside Chamber": 1000006,
    "Rampart Tower": 1000003,
    "Liftside Chamber": 1000005,
    # Caelid
    "Caelid North": 6400000,
    "Central Caelid": 6400001,
    "Chamber Outside the Plaza": 6400002,
    "Redmane Castle Plaza": 6400010,
    "Starscourge Radahn": 6400040,
    "Chair Crypt of Sellia": 6400020,
    "Swamp of Aeonia": 6401000,
    "Dragonbarrow": 6402000,
    "Bestial Sanctum": 6402001,
    # Mountaintops of the Giants
    "Forbidden Lands": 6500000,
    "Grand Lift of Rold": 6500090,
    "Zamor Ruins": 6501000,
    "Central Mountaintops": 6501001,
    # Consecrated Snowfield
    "Consecrated Snowfield": 6502000,
    "Mausoleum Midpoint": 6502001,
    "Inner Aeonian Swamp": 6502002,
    # Underground areas
    "Strandedgraveyard": 1800001,
    "Cave of Knowledge": 1800090,
    "Siofra River": 6600000,
    "Ainsel River Main": 6600001,
    "Ainsel River Downstream": 6600002,
    "Ainsel River Downstream II": 6600003,
    "Lake of Rot": 6600004,
    "Deeproot Depths": 6600005,
    "Nokron, Eternal City": 6600006,
    "Nokstella, Eternal City": 6600007,
    # Crumbling Farum Azula
    "Crumbling Beast Grave": 6700000,
    "Dragon Temple": 6700001,
    "Crumbling Farum Azula": 6700002,
    # Haligtree
    "Miquella's Haligtree": 6800000,
    # Endgame
    "Fractured Marika": 1900000,
    "Elden Beast": 1900001,
    # DLC - Shadow of the Erdtree
    "Gravesite Plain": 6900000,
    "Scadu Altus": 6900001,
    "Abyssal Woods": 6900002,
    "Ancient Ruins of Rauh": 6900003,
    "Cerulean Coast": 6900004,
    "Enir-Ilim": 6900005,
    "Shadow Keep": 6900006,
    # Generic region mappings (used when specific sub-region is unknown)
    "Limgrave": 6100000,  # The First Step region
    "Weeping Peninsula": 6102000,  # Weeping Peninsula West
    "Liurnia of the Lakes": 6200000,  # Liurnia South
    "Liurnia": 6200000,
    "Liurnia of the Lake": 6200000,
    "Altus Plateau": 6300000,  # Stormcaller Church
    "Mt. Gelmir": 6302000,  # Ninth Mt. Gelmir Campsite
    "Caelid": 6400000,  # Caelid North
    "Greyoll's Dragonbarrow": 6402000,  # Dragonbarrow
    "Mountaintops of the Giants": 6501000,  # Central Mountaintops
    "Flame Peak": 6501000,  # Same as Mountaintops
    "Leyndell, Royal Capital": 1100010,  # Erdtree Sanctuary
    "Roundtable Hold": 1800090,  # Cave of Knowledge (same area)
    "Stormveil Castle": 1000001,  # Stormveil Main Gate
    "Academy of Raya Lucaria": 1400000,  # Raya Lucaria Grand Library
    "Ainsel River": 6600001,  # Ainsel River Main
    "Stone Platform": 1900000,  # Fractured Marika / Elden Beast
    "Stranded Graveyard": 1800001,  # Cave of Knowledge
    "Specimen Storehouse": 6900006,  # Shadow Keep
    "Stone Coffin Fissure": 6900001,  # Scadu Altus
    "Rauh Base": 6900003,  # Ancient Ruins of Rauh
    "Land of the Tower": 6900000,  # Gravesite Plain
    "Belurat, Tower Settlement": 6900000,  # Gravesite Plain
    "Charo's Hidden Grave": 6900000,  # Gravesite Plain
    "Divine Tower of Liurnia": 6200000,  # Liurnia South
    "Foot of the Jagged Peak": 6900004,  # Cerulean Coast
    "Jagged Peak": 6900004,  # Cerulean Coast
    "Finger Ruins of Dheo": 6900001,  # Scadu Altus
    "Finger Ruins of Rhia": 6900004,  # Cerulean Coast
    "Central Scadu Altus": 6900001,  # Scadu Altus
    "Scaduview": 6900001,  # Scadu Altus
    # Directional sub-regions (map to parent region)
    "East Limgrave": 6100000,  # Limgrave
    "West Limgrave": 6100000,  # Limgrave
    "Far West Limgrave": 6100000,  # Limgrave
    "Northwest Limgrave Coast": 6100000,  # Limgrave
    "East Limgrave (Meteored)": 6100000,  # Limgrave
    "East Weeping Peninsula": 6102000,  # Weeping Peninsula
    "West Weeping Peninsula": 6102000,  # Weeping Peninsula
    "Southeast Weeping Peninsula Coast": 6102000,  # Weeping Peninsula
    "East Liurnia": 6200000,  # Liurnia
    "West Liurnia": 6200000,  # Liurnia
    "Northwest Liurnia": 6200000,  # Liurnia
    "Southeast Liurnia": 6200000,  # Liurnia
    "Southwest Liurnia": 6200000,  # Liurnia
    "Liurnia to Altus Plateau": 6200090,  # Grand Lift of Dectus
    "North Altus Plateau": 6300000,  # Altus Plateau
    "South Altus Plateau": 6300000,  # Altus Plateau
    "Northeast Altus Plateau": 6300000,  # Altus Plateau
    "Southeast Altus Plateau": 6300000,  # Altus Plateau
    "West Altus Plateau": 6300000,  # Altus Plateau
    "Far West Altus Plateau": 6300000,  # Altus Plateau
    "Northeast Altus Plateau (Ashen)": 1105011,  # Leyndell, Capital of Ash
    "North Caelid": 6400000,  # Caelid
    "South Caelid": 6400000,  # Caelid
    "Northeast Caelid": 6400000,  # Caelid
    "Northwest Caelid": 6400000,  # Caelid
    "Southeast Caelid": 6400000,  # Caelid
    "Far South Caelid": 6400000,  # Caelid
    "Northeast Mountaintops": 6501000,  # Mountaintops
    "Northwest Mountaintops": 6501000,  # Mountaintops
    "Southeast Mountaintops": 6501000,  # Mountaintops
    "Southwest Mountaintops": 6501000,  # Mountaintops
    "West Consecrated Snowfield": 6502000,  # Consecrated Snowfield
    "East Cerulean Coast; South Finger Ruins of Rhia; Dragon Communion Grand Altar": 6900004,  # Cerulean Coast
    "Southwest Cerulean Coast": 6900004,  # Cerulean Coast
    "Far South Cerulean Coast": 6900004,  # Cerulean Coast
    "East Scaduview": 6900001,  # Scadu Altus
    "West Scaduview": 6900001,  # Scadu Altus
    "Far East Scadu Altus; Finger Ruins of Dheo": 6900001,  # Scadu Altus
    "Northwest Gravesite Plain; West Scadu Altus; Rauh Ruins": 6900000,  # Gravesite Plain
    "Northwest Gravesite Plain; West Scadu Altus; Rauh Ruins (Unsealed)": 6900000,  # Gravesite Plain
    "Southeast Gravesite Plain; Fort Reprimand; Foot of the Jagged Peak; North Finger Ruins of Rhia; West Abyssal Woods": 6900000,  # Gravesite Plain
    "Southwest Gravesite Plain; Northwest Cerulean Coast": 6900000,  # Gravesite Plain
    "North Rauh Ruins": 6900003,  # Ancient Ruins of Rauh
    "North Jagged Peak; East Abyssal Woods": 6900004,  # Cerulean Coast (Jagged Peak area)
    "South Jagged Peak": 6900004,  # Cerulean Coast
}


def get_region_id(location_name: str) -> int:
    """Get region ID for a location name."""
    return LOCATION_TO_REGION.get(location_name, 0)


def get_region_name(region_id: int) -> str:
    """Get location name for a region ID."""
    for name, rid in LOCATION_TO_REGION.items():
        if rid == region_id:
            return name
    return f"Unknown Region {region_id}"
