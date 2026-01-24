"""
Region database for Elden Ring
Maps region IDs to names
Note: This is a placeholder - region IDs need to be mapped from game data
"""

# Known regions (partial list - needs completion)
REGIONS = {
    # Limgrave regions
    60000: "Limgrave",
    60010: "Mistwood",
    60020: "Stormhill",
    60030: "Weeping Peninsula",
    60040: "Stormveil Castle",
    # Liurnia regions
    60100: "Liurnia of the Lakes",
    60110: "Academy of Raya Lucaria",
    60120: "Caria Manor",
    60130: "Moonlight Altar",
    # Caelid regions
    60200: "Caelid",
    60210: "Dragonbarrow",
    60220: "Redmane Castle",
    # Altus Plateau regions
    60300: "Altus Plateau",
    60310: "Mt. Gelmir",
    60320: "Volcano Manor",
    60330: "Leyndell, Royal Capital",
    # Mountaintops regions
    60400: "Mountaintops of the Giants",
    60410: "Consecrated Snowfield",
    60420: "Mohgwyn Palace",
    # Underground regions
    60500: "Siofra River",
    60510: "Ainsel River",
    60520: "Lake of Rot",
    60530: "Nokron, Eternal City",
    60540: "Nokstella, Eternal City",
    60550: "Deeproot Depths",
    # Endgame regions
    60600: "Crumbling Farum Azula",
    60610: "Leyndell, Ashen Capital",
    # DLC regions (Shadow of the Erdtree)
    60700: "Gravesite Plain",
    60710: "Scadu Altus",
    60720: "Abyssal Woods",
    60730: "Ancient Ruins of Rauh",
    60740: "Cerulean Coast",
    60750: "Charo's Hidden Grave",
    60760: "Shadow Keep",
    60770: "Enir-Ilim",
}


def get_region_name(region_id: int) -> str:
    """Get region name from ID"""
    return REGIONS.get(region_id, f"Unknown Region ({region_id})")


def is_dlc_region(region_id: int) -> bool:
    """Check if region is from DLC"""
    return region_id >= 60700


def get_all_regions() -> dict[int, str]:
    """Get all region mappings"""
    return REGIONS.copy()


def get_base_game_regions() -> dict[int, str]:
    """Get only base game regions"""
    return {k: v for k, v in REGIONS.items() if k < 60700}


def get_dlc_regions() -> dict[int, str]:
    """Get only DLC regions"""
    return {k: v for k, v in REGIONS.items() if k >= 60700}


# Region categories
REGION_CATEGORIES = {
    "Limgrave": [60000, 60010, 60020, 60030, 60040],
    "Liurnia": [60100, 60110, 60120, 60130],
    "Caelid": [60200, 60210, 60220],
    "Altus Plateau": [60300, 60310, 60320, 60330],
    "Mountaintops": [60400, 60410, 60420],
    "Underground": [60500, 60510, 60520, 60530, 60540, 60550],
    "Endgame": [60600, 60610],
    "DLC": [60700, 60710, 60720, 60730, 60740, 60750, 60760, 60770],
}


def get_regions_by_category(category: str) -> list[int]:
    """Get all region IDs in a category"""
    return REGION_CATEGORIES.get(category, [])
