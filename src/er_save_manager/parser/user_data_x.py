"""
Elden Ring Save Parser - UserDataX (Character Slot)

This is the main sequential parser that reads an entire character slot in order.
Based on ER-Save-Lib Rust implementation - exact field order.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from io import BytesIO

from .character import PlayerGameData, SPEffect
from .equipment import (
    AcquiredProjectiles,
    ActiveWeaponSlotsAndArmStyle,
    EquippedArmamentsAndItems,
    EquippedGestures,
    EquippedItems,
    EquippedItemsEquipIndex,
    EquippedItemsGaitemHandles,
    EquippedItemsItemIds,
    EquippedPhysics,
    EquippedSpells,
    Inventory,
    TrophyEquipData,
)
from .er_types import Gaitem, MapId
from .world import (
    DLC,
    BaseVersion,
    BloodStain,
    FaceData,
    FieldArea,
    GaitemGameData,
    Gestures,
    MenuSaveLoad,
    NetMan,
    PlayerCoordinates,
    PlayerGameDataHash,
    PS5Activity,
    Regions,
    RendMan,
    RideGameData,
    TutorialData,
    WorldArea,
    WorldAreaTime,
    WorldAreaWeather,
    WorldGeomMan,
)


@dataclass
class UserDataX:
    """
    Complete character slot (UserDataX structure)

    This class sequentially parses EVERY field in exact order from the save file.
    Size: ~2.6MB per slot (varies based on version and data)
    """

    # Metadata (not from file, tracking info)
    data_start: int = 0
    horse_offset: int = 0
    weather_offset: int = 0
    time_offset: int = 0
    steamid_offset: int = 0
    # Header (4 + 4 + 8 + 16 = 32 bytes)
    version: int = 0
    map_id: MapId = field(default_factory=MapId)
    unk0x8: bytes = field(default_factory=lambda: b"\x00" * 8)
    unk0x10: bytes = field(default_factory=lambda: b"\x00" * 16)

    # Gaitem map (VARIABLE LENGTH! 5118 or 5120 entries)
    gaitem_map: list[Gaitem] = field(default_factory=list)

    # Player data (0x1B0 = 432 bytes)
    player_game_data: PlayerGameData = field(default_factory=PlayerGameData)

    # SP Effects (13 entries ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 16 bytes = 208 bytes, but actually reads different)
    sp_effects: list[SPEffect] = field(default_factory=list)

    # Equipment structures
    equipped_items_equip_index: EquippedItemsEquipIndex = field(
        default_factory=EquippedItemsEquipIndex
    )
    active_weapon_slots_and_arm_style: ActiveWeaponSlotsAndArmStyle = field(
        default_factory=ActiveWeaponSlotsAndArmStyle
    )
    equipped_items_item_id: EquippedItemsItemIds = field(
        default_factory=EquippedItemsItemIds
    )
    equipped_items_gaitem_handle: EquippedItemsGaitemHandles = field(
        default_factory=EquippedItemsGaitemHandles
    )

    # Inventory held (0xa80 common, 0x180 key)
    inventory_held: Inventory = field(default_factory=Inventory)

    # More equipment
    equipped_spells: EquippedSpells = field(default_factory=EquippedSpells)
    equipped_items: EquippedItems = field(default_factory=EquippedItems)
    equipped_gestures: EquippedGestures = field(default_factory=EquippedGestures)
    acquired_projectiles: AcquiredProjectiles = field(
        default_factory=AcquiredProjectiles
    )
    equipped_armaments_and_items: EquippedArmamentsAndItems = field(
        default_factory=EquippedArmamentsAndItems
    )
    equipped_physics: EquippedPhysics = field(default_factory=EquippedPhysics)

    # Face data (0x12F = 303 bytes when in_profile_summary=False)
    face_data: FaceData = field(default_factory=FaceData)

    # Inventory storage (CRITICAL: 0x780 common, 0x80 key)
    inventory_storage_box: Inventory = field(default_factory=Inventory)

    # Gestures and regions
    gestures: Gestures = field(default_factory=Gestures)
    unlocked_regions: Regions = field(default_factory=Regions)

    # Horse/Torrent
    horse: RideGameData = field(default_factory=RideGameData)

    # Control byte (1 byte)
    control_byte_maybe: int = 0

    # Blood stain
    blood_stain: BloodStain = field(default_factory=BloodStain)

    # Unknown fields (8 bytes total)
    unk_gamedataman_0x120_or_gamedataman_0x130: int = 0
    unk_gamedataman_0x88: int = 0

    # Menu and game data
    menu_profile_save_load: MenuSaveLoad = field(default_factory=MenuSaveLoad)
    trophy_equip_data: TrophyEquipData = field(default_factory=TrophyEquipData)
    gaitem_game_data: GaitemGameData = field(default_factory=GaitemGameData)
    tutorial_data: TutorialData = field(default_factory=TutorialData)

    # GameMan bytes (3 bytes)
    gameman_0x8c: int = 0
    gameman_0x8d: int = 0
    gameman_0x8e: int = 0

    # Death and character info
    total_deaths_count: int = 0
    character_type: int = 0
    in_online_session_flag: int = 0
    character_type_online: int = 0
    last_rested_grace: int = 0
    not_alone_flag: int = 0
    in_game_countdown_timer: int = 0
    unk_gamedataman_0x124_or_gamedataman_0x134: int = 0

    # Event flags (0x1BF99F = 1,833,375 bytes)
    event_flags: bytes = field(default_factory=lambda: b"\x00" * 0x1BF99F)
    event_flags_terminator: int = 0

    # World structures
    field_area: FieldArea = field(default_factory=FieldArea)
    world_area: WorldArea = field(default_factory=WorldArea)
    world_geom_man: WorldGeomMan = field(default_factory=WorldGeomMan)
    world_geom_man2: WorldGeomMan = field(default_factory=WorldGeomMan)
    rend_man: RendMan = field(default_factory=RendMan)

    # Player position
    player_coordinates: PlayerCoordinates = field(default_factory=PlayerCoordinates)

    # More GameMan bytes
    game_man_0x5be: int = 0
    game_man_0x5bf: int = 0
    spawn_point_entity_id: int = 0
    game_man_0xb64: int = 0

    # Version-specific fields
    temp_spawn_point_entity_id: int | None = None  # version >= 65
    game_man_0xcb3: int | None = None  # version >= 66

    # Network and world state
    net_man: NetMan = field(default_factory=NetMan)
    world_area_weather: WorldAreaWeather = field(default_factory=WorldAreaWeather)
    world_area_time: WorldAreaTime = field(default_factory=WorldAreaTime)
    base_version: BaseVersion = field(default_factory=BaseVersion)
    steam_id: int = 0
    ps5_activity: PS5Activity = field(default_factory=PS5Activity)
    dlc: DLC = field(default_factory=DLC)
    player_data_hash: PlayerGameDataHash = field(default_factory=PlayerGameDataHash)

    # Any remaining bytes
    rest: bytes = b""

    @classmethod
    def _find_gesture_start(
        cls, f: BytesIO, start_pos: int, max_pos: int
    ) -> int | None:
        original_pos = f.tell()

        # Search range: -1KB to +2KB
        search_start = max(start_pos - 1000, 0)
        search_end = min(start_pos + 2000, max_pos - 512)

        best_match = None
        best_score = 0

        for offset in range(search_start, search_end, 4):
            f.seek(offset)
            chunk = f.read(256)
            if len(chunk) < 256:
                continue

            score = 0

            # Pattern 1: VERY high 0xFF density (bitmask gestures)
            ff_count = chunk.count(0xFF)
            if ff_count > 220:  # Very strict - need 85%+ 0xFF
                score = 100
            elif ff_count > 180:  # Medium match
                score = 50

            # Pattern 2: Gesture ID validation (must be consecutive and valid)
            consecutive_valid = 0
            max_consecutive = 0
            for i in range(0, 64, 4):
                if i + 4 <= len(chunk):
                    val = struct.unpack("<I", chunk[i : i + 4])[0]
                    # Very strict gesture ID ranges
                    if val == 0 or val == 0xFFFFFFFE or (3000000 <= val <= 9000000):
                        consecutive_valid += 1
                        max_consecutive = max(max_consecutive, consecutive_valid)
                    else:
                        consecutive_valid = 0

            if max_consecutive >= 12:  # Need 12+ consecutive valid IDs
                score = max(score, 80)
            elif max_consecutive >= 8:
                score = max(score, 40)

            # Track best match
            if score > best_score:
                best_score = score
                best_match = offset

        f.seek(original_pos)

        # Only return if we have a STRONG match (score >= 80)
        if best_score >= 80 and best_match is not None:
            return best_match

        # No strong pattern - assume no mystery structure
        return start_pos

    @classmethod
    def read(
        cls, f: BytesIO, is_ps: bool, slot_start_offset: int, slot_size: int
    ) -> UserDataX:
        """
        Read complete UserDataX from stream with robust error handling.

        This version uses slot boundary tracking to handle
        version differences and unknown structures added in game updates.

        Args:
            f: BytesIO stream positioned at start of character slot data
            is_ps: True if PlayStation format (no checksum)
            slot_start_offset: Absolute file offset where slot data starts (after checksum)
            slot_size: Total size of slot data (0x280000 = 2,621,440 bytes)

        Returns:
            UserDataX instance with all fields populated
        """
        obj = cls()
        obj.data_start = slot_start_offset
        data_start = f.tell()  # Track where we started reading

        # Read version (4 bytes)
        obj.version = struct.unpack("<I", f.read(4))[0]

        # Empty slot check
        if obj.version == 0:
            # Read rest of slot to maintain alignment
            bytes_read = f.tell() - data_start
            remaining = slot_size - bytes_read
            if remaining > 0:
                f.read(remaining)
            return obj

        # Read map_id and header (4 + 8 + 16 = 28 bytes)
        obj.map_id = MapId.read(f)
        obj.unk0x8 = f.read(8)
        obj.unk0x10 = f.read(16)

        # Read Gaitem map (VARIABLE LENGTH!)
        gaitem_count = 0x13FE if obj.version <= 81 else 0x1400  # 5118 or 5120
        obj.gaitem_map = [Gaitem.read(f) for _ in range(gaitem_count)]

        # Track PlayerGameData offset (CRITICAL for stats editing)
        obj.player_game_data_offset = f.tell() - data_start
        obj.player_game_data = PlayerGameData.read(f)

        # Track SPEffects offset
        obj.sp_effects_offset = f.tell() - data_start
        obj.sp_effects = [SPEffect.read(f) for _ in range(13)]

        # Track equipment structures offsets
        obj.equipped_items_equip_index_offset = f.tell() - data_start
        obj.equipped_items_equip_index = EquippedItemsEquipIndex.read(f)
        obj.active_weapon_slots_and_arm_style = ActiveWeaponSlotsAndArmStyle.read(f)
        obj.equipped_items_item_id = EquippedItemsItemIds.read(f)
        obj.equipped_items_gaitem_handle = EquippedItemsGaitemHandles.read(f)

        # Track inventory held offset
        held_common_cap = 0xA80  # 2,688 common items
        held_key_cap = 0x180  # 384 key items
        obj.inventory_held_offset = f.tell() - data_start
        obj.inventory_held = Inventory.read(f, held_common_cap, held_key_cap)

        # Read more equipment
        obj.equipped_spells_offset = f.tell() - data_start
        obj.equipped_spells = EquippedSpells.read(f)
        obj.equipped_items_offset = f.tell() - data_start
        obj.equipped_items = EquippedItems.read(f)
        obj.equipped_gestures = EquippedGestures.read(f)
        obj.acquired_projectiles = AcquiredProjectiles.read(f)
        obj.equipped_armaments_and_items = EquippedArmamentsAndItems.read(f)
        obj.equipped_physics = EquippedPhysics.read(f)

        # Track FaceData offset (CRITICAL for appearance editing)
        obj.face_data_offset = f.tell() - data_start
        obj.face_data = FaceData.read(f, in_profile_summary=False)

        # Track inventory storage offset
        obj.inventory_storage_box_offset = f.tell() - data_start
        obj.inventory_storage_box = Inventory.read(f, 0x780, 0x80)

        # Parse remaining structures
        obj.gestures = Gestures.read(f)
        obj.unlocked_regions = Regions.read(f)
        obj.horse_offset = f.tell() - data_start
        obj.horse = RideGameData.read(f)
        obj.control_byte_maybe = struct.unpack("<B", f.read(1))[0]
        obj.blood_stain = BloodStain.read(f)
        obj.unk_gamedataman_0x120_or_gamedataman_0x130 = struct.unpack("<I", f.read(4))[
            0
        ]
        obj.unk_gamedataman_0x88 = struct.unpack("<I", f.read(4))[0]

        try:
            obj.menu_profile_save_load = MenuSaveLoad.read(f)
            obj.trophy_equip_data = TrophyEquipData.read(f)
            obj.gaitem_game_data = GaitemGameData.read(f)
            obj.tutorial_data = TutorialData.read(f)
        except Exception:
            raise

        obj.gameman_0x8c = struct.unpack("<B", f.read(1))[0]
        obj.gameman_0x8d = struct.unpack("<B", f.read(1))[0]
        obj.gameman_0x8e = struct.unpack("<B", f.read(1))[0]

        obj.total_deaths_count = struct.unpack("<I", f.read(4))[0]
        obj.character_type = struct.unpack("<i", f.read(4))[0]
        obj.in_online_session_flag = struct.unpack("<B", f.read(1))[0]
        obj.character_type_online = struct.unpack("<I", f.read(4))[0]
        obj.last_rested_grace = struct.unpack("<I", f.read(4))[0]
        obj.not_alone_flag = struct.unpack("<B", f.read(1))[0]
        obj.in_game_countdown_timer = struct.unpack("<I", f.read(4))[0]
        obj.unk_gamedataman_0x124_or_gamedataman_0x134 = struct.unpack("<I", f.read(4))[
            0
        ]

        obj.event_flags_offset = f.tell() - data_start
        obj.event_flags = f.read(0x1BF99F)
        obj.event_flags_terminator = struct.unpack("<B", f.read(1))[0]
        # There are 16 more bytes after the terminator

        obj.field_area = FieldArea.read(f)
        obj.world_area = WorldArea.read(f)
        obj.world_geom_man = WorldGeomMan.read(f)
        obj.world_geom_man2 = WorldGeomMan.read(f)
        obj.rend_man = RendMan.read(f)
        obj.coordinates_offset = f.tell() - data_start
        obj.player_coordinates = PlayerCoordinates.read(f)

        # 2 bytes padding after PlayerCoordinates
        f.read(2)
        obj.spawn_point_entity_id = struct.unpack("<I", f.read(4))[0]
        # 4 bytes padding
        obj.game_man_0xb64 = struct.unpack("<I", f.read(4))[0]

        if obj.version >= 65:
            obj.temp_spawn_point_entity_id = struct.unpack("<I", f.read(4))[0]
        if obj.version >= 66:
            obj.game_man_0xcb3 = struct.unpack("<B", f.read(1))[0]

        obj.net_man = NetMan.read(f)

        # DIAGNOSTIC: Show exact position and bytes
        current_pos = f.tell()
        current_pos + 0x300
        f.read(24)
        f.seek(current_pos)

        obj.weather_offset = f.tell() - data_start
        obj.world_area_weather = WorldAreaWeather.read(f)
        obj.time_offset = f.tell() - data_start
        obj.world_area_time = WorldAreaTime.read(f)
        obj.base_version = BaseVersion.read(f)
        obj.steamid_offset = f.tell()
        obj.steam_id = struct.unpack("<Q", f.read(8))[0]
        obj.ps5_activity = PS5Activity.read(f)
        obj.dlc = DLC.read(f)
        obj.player_data_hash = PlayerGameDataHash.read(f)

        # Always seek to exact slot boundary, then read rest
        slot_end_position = data_start + slot_size
        current_position = f.tell()

        if current_position > slot_end_position:
            # seek back to slot boundary
            f.seek(slot_end_position)
        elif current_position < slot_end_position:
            # read them as rest
            remaining = slot_end_position - current_position
            obj.rest = f.read(remaining)

        return obj

    def is_empty(self) -> bool:
        """Check if this is an empty character slot"""
        return self.version == 0

    def get_character_name(self) -> str:
        """Get character name"""
        return self.player_game_data.character_name

    def get_level(self) -> int:
        """Get character level"""
        return self.player_game_data.level

    def get_slot_map_id(self):
        """
        Get the MapId object.

        Returns:
            MapId object or None
        """
        if hasattr(self, "map_id"):
            return self.map_id
        return None

    def get_horse_data(self):
        """
        Get the horse/Torrent data.

        Returns:
            RideGameData object or None
        """
        if hasattr(self, "horse"):
            return self.horse
        return None

    def has_torrent_bug(self) -> bool:
        """Check if Torrent has the infinite loading bug (HP=0 with State=Active)"""
        if not hasattr(self, "horse") or self.horse is None:
            return False
        return self.horse.has_bug()

    def fix_torrent_bug(self):
        """Fix Torrent infinite loading bug by setting State to Dead"""
        if hasattr(self, "horse") and self.horse is not None:
            self.horse.fix_bug()

    def has_weather_corruption(self) -> bool:
        """
        Check if weather data appears corrupted.

        Corruption signs:
        - AreaId is 0 AND character is in a real game location
        - Timer value is unreasonably large (> 100000)
        """
        if not hasattr(self, "world_area_weather") or self.world_area_weather is None:
            return False

        weather = self.world_area_weather

        # Check for unreasonably large timer (clear corruption)
        if weather.timer > 100000:
            return True

        # Check if AreaId is 0 but character has a real map location
        # This indicates desync between map position and weather data
        if weather.area_id == 0:
            if hasattr(self, "map_id") and self.map_id is not None:
                # Check if map_id shows character is in a real location (not all zeros)
                if self.map_id.data != b"\x00\x00\x00\x00":
                    # Character is in game world but weather shows no area = corruption
                    return True

        return False

    def has_time_corruption(self, seconds_played: int | None = None) -> bool:
        """
        Check if time is corrupted by comparing with expected value.

        Args:
            seconds_played: Expected playtime in seconds from ProfileSummary

        Returns:
            True if corrupted
        """
        if not hasattr(self, "world_area_time") or self.world_area_time is None:
            return False

        time = self.world_area_time

        # Check for clearly invalid time values
        if time.minute > 59 or time.second > 59:
            return True

        # If seconds_played provided, compare with expected time
        if seconds_played is not None:
            expected_hours = seconds_played // 3600
            expected_minutes = (seconds_played % 3600) // 60
            expected_seconds = seconds_played % 60

            # Corrupted if time does not match expected value
            if (
                time.hour != expected_hours
                or time.minute != expected_minutes
                or time.second != expected_seconds
            ):
                return True
            return False

        # Without seconds_played, only check for all zeros
        if time.hour == 0 and time.minute == 0 and time.second == 0:
            return True

        return False

    def has_steamid_corruption(self, correct_steam_id: int = None) -> bool:
        """
        Check if SteamId is corrupted.

        Checks:
        1. SteamId is 0
        2. If correct_steam_id provided, check if it doesn't match USER_DATA_10

        Args:
            correct_steam_id: Expected SteamID from USER_DATA_10

        Returns:
            True if SteamId is corrupted
        """
        if not hasattr(self, "steam_id"):
            return False

        # Always corrupted if 0
        if self.steam_id == 0:
            return True

        # Check sync
        if correct_steam_id is not None and correct_steam_id != 0:
            if self.steam_id != correct_steam_id:
                return True

        return False

    def has_corruption(self, correct_steam_id: int = None) -> tuple[bool, list[str]]:
        """
        Check if this character slot has any corruption.

        Returns tuple with corruption details including values:
            (has_corruption, list_of_issue_strings)

        Issue strings format: "issue_type:value"
        """
        issues = []

        # Check Torrent bug
        if self.has_torrent_bug():
            horse = self.horse
            if horse:
                issues.append(f"torrent_bug:HP = {horse.hp},State = {horse.state.name}")

        # Check weather corruption
        if self.has_weather_corruption():
            weather = self.world_area_weather
            map_id = self.map_id
            if weather and map_id:
                issues.append(
                    f"weather_corruption:AreaId = {weather.area_id},Should be {map_id.data[3]}"
                )

        # Check time corruption (without ProfileSummary context)
        # Note: Cannot verify time matches seconds_played from here
        # Proper check happens in Save.fix_character_corruption which has slot index
        if self.has_time_corruption():
            time = self.world_area_time
            if time:
                issues.append(
                    f"time_corruption:Time = {time.hour:02d}:{time.minute:02d}:{time.second:02d}"
                )

        # Check SteamId corruption
        if self.has_steamid_corruption(correct_steam_id):
            issues.append(f"steamid_corruption:SteamId = {self.steam_id}")

        # Check event flag corruption (Ranni quest and warp sickness)
        if hasattr(self, "event_flags") and self.event_flags:
            try:
                from .event_flags import CorruptionDetector

                event_issues = CorruptionDetector.detect_all(self.event_flags)
                for issue in event_issues:
                    issues.append(f"eventflag:{issue}")
            except Exception:
                pass

        has_corruption = len(issues) > 0
        return (has_corruption, issues)
