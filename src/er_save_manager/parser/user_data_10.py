"""
Elden Ring Save Parser - USER_DATA_10 (Common Section)

Contains global save data including:
- SteamID
- Settings
- Profile Summary with seconds played for each character
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from io import BytesIO


def read_wstring(f: BytesIO, max_chars: int) -> str:
    """Read a wide string (UTF-16LE) of max_chars characters"""
    data = f.read(max_chars * 2)
    return data.decode("utf-16le").rstrip("\x00")


@dataclass
class Settings:
    """Game settings"""

    camera_speed: int = 0
    controller_vibration: int = 0
    brightness: int = 0
    unk0x3: int = 0
    music_volume: int = 0
    sound_effects_volume: int = 0
    voice_volume: int = 0
    display_blood: int = 0
    subtitles: int = 0
    hud: int = 0
    camera_x_axis: int = 0
    camera_y_axis: int = 0
    toggle_auto_lockon: int = 0
    camera_auto_wall_recovery: int = 0
    unk0xe: int = 0
    unk0xf: int = 0
    reset_camera_y_axis: int = 0
    cinematic_effects: int = 0
    unk0x12: int = 0
    perform_matchmaking: int = 0
    unk0x14: int = 0
    unk0x15: int = 0
    manual_attack_aim: int = 0
    autotarget: int = 0
    launchsettings: int = 0
    send_summon_sign: int = 0
    unk0x1a: int = 0
    hdr: int = 0
    hdr_adjust_brightness: int = 0
    hdr_maximum_brightness: int = 0
    hdr_adjust_saturation: int = 0
    unk0x1f: int = 0
    master_volume: int = 0
    is_raytracing_on: int = 0
    mark_new_items: int = 0
    show_recent_tabs: int = 0
    unk0x24: int = 0
    unk0x2c: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> Settings:
        """Read Settings from stream"""
        obj = cls()
        obj.camera_speed = struct.unpack("<B", f.read(1))[0]
        obj.controller_vibration = struct.unpack("<B", f.read(1))[0]
        obj.brightness = struct.unpack("<B", f.read(1))[0]
        obj.unk0x3 = struct.unpack("<B", f.read(1))[0]
        obj.music_volume = struct.unpack("<B", f.read(1))[0]
        obj.sound_effects_volume = struct.unpack("<B", f.read(1))[0]
        obj.voice_volume = struct.unpack("<B", f.read(1))[0]
        obj.display_blood = struct.unpack("<B", f.read(1))[0]
        obj.subtitles = struct.unpack("<B", f.read(1))[0]
        obj.hud = struct.unpack("<B", f.read(1))[0]
        obj.camera_x_axis = struct.unpack("<B", f.read(1))[0]
        obj.camera_y_axis = struct.unpack("<B", f.read(1))[0]
        obj.toggle_auto_lockon = struct.unpack("<B", f.read(1))[0]
        obj.camera_auto_wall_recovery = struct.unpack("<B", f.read(1))[0]
        obj.unk0xe = struct.unpack("<B", f.read(1))[0]
        obj.unk0xf = struct.unpack("<B", f.read(1))[0]
        obj.reset_camera_y_axis = struct.unpack("<B", f.read(1))[0]
        obj.cinematic_effects = struct.unpack("<B", f.read(1))[0]
        obj.unk0x12 = struct.unpack("<B", f.read(1))[0]
        obj.perform_matchmaking = struct.unpack("<B", f.read(1))[0]
        obj.unk0x14 = struct.unpack("<B", f.read(1))[0]
        obj.unk0x15 = struct.unpack("<B", f.read(1))[0]
        obj.manual_attack_aim = struct.unpack("<B", f.read(1))[0]
        obj.autotarget = struct.unpack("<B", f.read(1))[0]
        obj.launchsettings = struct.unpack("<B", f.read(1))[0]
        obj.send_summon_sign = struct.unpack("<B", f.read(1))[0]
        obj.unk0x1a = struct.unpack("<B", f.read(1))[0]
        obj.hdr = struct.unpack("<B", f.read(1))[0]
        obj.hdr_adjust_brightness = struct.unpack("<B", f.read(1))[0]
        obj.hdr_maximum_brightness = struct.unpack("<B", f.read(1))[0]
        obj.hdr_adjust_saturation = struct.unpack("<B", f.read(1))[0]
        obj.unk0x1f = struct.unpack("<B", f.read(1))[0]
        obj.master_volume = struct.unpack("<B", f.read(1))[0]
        obj.is_raytracing_on = struct.unpack("<B", f.read(1))[0]
        obj.mark_new_items = struct.unpack("<B", f.read(1))[0]
        obj.show_recent_tabs = struct.unpack("<B", f.read(1))[0]
        obj.unk0x24 = struct.unpack("<Q", f.read(8))[0]
        obj.unk0x2c = struct.unpack("<H", f.read(2))[0]
        return obj


@dataclass
class ProfileEquipment:
    """Equipment info in profile summary"""

    raw_data: bytes = b""

    @classmethod
    def read(cls, f: BytesIO) -> ProfileEquipment:
        """Read ProfileEquipment - 0xE8 bytes"""
        obj = cls()
        obj.raw_data = f.read(0xE8)
        return obj


@dataclass
class Profile:
    """Profile data for a single character slot in ProfileSummary"""

    character_name: str = ""
    level: int = 0
    seconds_played: int = 0
    runes_memory: int = 0
    map_id: bytes = b""
    unk0x34: int = 0
    face_data: bytes = b""
    equipment: ProfileEquipment = None
    body_type: int = 0
    archetype: int = 0
    starting_gift: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> Profile:
        """Read Profile from stream - 0x24C bytes total"""
        obj = cls()

        # Character name (16 wide chars)
        obj.character_name = read_wstring(f, 16)

        # Terminator (2 bytes)
        f.read(2)

        # Stats
        obj.level = struct.unpack("<I", f.read(4))[0]
        obj.seconds_played = struct.unpack("<I", f.read(4))[0]
        obj.runes_memory = struct.unpack("<I", f.read(4))[0]
        obj.map_id = f.read(4)
        obj.unk0x34 = struct.unpack("<I", f.read(4))[0]

        # Face data (0x124 bytes)
        obj.face_data = f.read(0x124)

        # Equipment (0xE8 bytes)
        obj.equipment = ProfileEquipment.read(f)

        # Character creation data
        obj.body_type = struct.unpack("<B", f.read(1))[0]
        obj.archetype = struct.unpack("<B", f.read(1))[0]
        obj.starting_gift = struct.unpack("<B", f.read(1))[0]

        # Unknown fields (3 bytes + 4 bytes = 7 bytes total)
        f.read(7)

        return obj


@dataclass
class ProfileSummary:
    """Profile summary containing basic info for all 10 character slots"""

    active_profiles: list[bool] = field(default_factory=list)
    profiles: list[Profile] = field(default_factory=list)

    @classmethod
    def read(cls, f: BytesIO) -> ProfileSummary:
        """Read ProfileSummary from stream"""
        obj = cls()

        # Active profiles (10 bytes)
        obj.active_profiles = [
            bool(struct.unpack("<B", f.read(1))[0]) for _ in range(10)
        ]

        # 10 profiles
        obj.profiles = [Profile.read(f) for _ in range(10)]

        return obj


@dataclass
class MenuSystemSaveLoad:
    """Menu system data - just read as raw for now"""

    raw_data: bytes = b""

    @classmethod
    def read(cls, f: BytesIO) -> MenuSystemSaveLoad:
        """Read MenuSystemSaveLoad - 0x1808 bytes"""
        obj = cls()
        obj.raw_data = f.read(0x1808)
        return obj


@dataclass
class PCOptionData:
    """PC-specific options - just read as raw"""

    raw_data: bytes = b""

    @classmethod
    def read(cls, f: BytesIO) -> PCOptionData:
        """Read PCOptionData - 0xB2 bytes"""
        obj = cls()
        obj.raw_data = f.read(0xB2)
        return obj


@dataclass
class KeyConfigSaveLoad:
    """Key configuration data"""

    size: int = 0
    data: bytes = b""

    @classmethod
    def read(cls, f: BytesIO) -> KeyConfigSaveLoad:
        """Read KeyConfigSaveLoad"""
        obj = cls()
        f.read(4)  # Skip unk0x0, unk0x2
        obj.size = struct.unpack("<I", f.read(4))[0]
        obj.data = f.read(obj.size)
        return obj


@dataclass
class UserData10:
    """
    USER_DATA_10 - Common section with global save data

    Contains:
    - Version
    - SteamID
    - Settings
    - Profile Summary (with seconds_played for each character)
    """

    version: int = 0
    steam_id: int = 0
    settings: Settings = None
    menu_system_save_load: MenuSystemSaveLoad = None
    profile_summary: ProfileSummary = None
    pc_option_data: PCOptionData = None
    key_config_save_load: KeyConfigSaveLoad = None

    @classmethod
    def read(cls, f: BytesIO, is_ps: bool) -> UserData10:
        """
        Read USER_DATA_10 from stream

        Args:
            f: BytesIO stream positioned at start of USER_DATA_10
            is_ps: True if PlayStation save
        """
        obj = cls()
        start_pos = f.tell()

        # Skip checksum on PC
        if not is_ps:
            f.read(16)

        # Version (4 bytes)
        obj.version = struct.unpack("<I", f.read(4))[0]

        # SteamID (8 bytes)
        obj.steam_id = struct.unpack("<Q", f.read(8))[0]

        # Settings (0x140 bytes based on CSV)
        # Actually Settings is smaller but includes padding
        obj.settings = Settings.read(f)
        # Read remaining padding to reach MenuSystemSaveLoad
        settings_end = f.tell()
        settings_expected_end = start_pos + (16 if not is_ps else 0) + 4 + 8 + 0x140
        padding = settings_expected_end - settings_end
        if padding > 0:
            f.read(padding)

        # MenuSystemSaveLoad (0x1808 bytes)
        obj.menu_system_save_load = MenuSystemSaveLoad.read(f)

        # ProfileSummary (0x1702 bytes)
        obj.profile_summary = ProfileSummary.read(f)

        # gamedataman fields (5 bytes)
        f.read(5)

        # PCOptionData (PC only, 0xB2 bytes)
        if not is_ps:
            obj.pc_option_data = PCOptionData.read(f)

        # KeyConfigSaveLoad (variable size)
        obj.key_config_save_load = KeyConfigSaveLoad.read(f)

        # game_man_0x118 (8 bytes)
        f.read(8)

        # Skip rest
        bytes_read = f.tell() - start_pos
        remaining = 0x60000 - bytes_read
        if remaining > 0:
            f.read(remaining)

        return obj
