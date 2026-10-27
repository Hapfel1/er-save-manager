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
    data = f.read(max_chars * 2)
    return data.decode("utf-16le", errors="replace").split("\x00", 1)[0]


@dataclass
class Settings:
    """Game options, same byte layout as the in-memory option data at
    GameDataMan+0x58. Only the first 0x30 bytes of the 0x140-byte block are
    used; the rest is zero padding.
    """

    camera_speed: int = 0
    controller_vibration: int = 0
    brightness: int = 0
    sound_type: int = 0
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
    cross_region_play: int = 0
    voice_chat: int = 0
    display_player_names: int = 0
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
    is_raytracing_on: int = (
        0  # 0 = Ray Tracing Quality off; quality level is in GraphicsConfig.xml
    )
    mark_new_items: int = 0
    show_recent_tabs: int = 0
    unk0x24: int = 0
    unk0x2c: int = 0
    show_tutorials: int = 0
    camera_auto_rotation: int = 0

    @classmethod
    def read(cls, f: BytesIO) -> Settings:
        """Read Settings from stream"""
        obj = cls()
        obj.camera_speed = struct.unpack("<B", f.read(1))[0]
        obj.controller_vibration = struct.unpack("<B", f.read(1))[0]
        obj.brightness = struct.unpack("<B", f.read(1))[0]
        obj.sound_type = struct.unpack("<B", f.read(1))[0]
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
        obj.cross_region_play = struct.unpack("<B", f.read(1))[0]
        obj.voice_chat = struct.unpack("<B", f.read(1))[0]
        obj.display_player_names = struct.unpack("<B", f.read(1))[0]
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
        obj.show_tutorials = struct.unpack("<B", f.read(1))[0]
        obj.camera_auto_rotation = struct.unpack("<B", f.read(1))[0]
        return obj

    def write(self, f: BytesIO) -> None:
        """Write Settings to stream (mirrors read order)."""
        f.write(struct.pack("<B", self.camera_speed))
        f.write(struct.pack("<B", self.controller_vibration))
        f.write(struct.pack("<B", self.brightness))
        f.write(struct.pack("<B", self.sound_type))
        f.write(struct.pack("<B", self.music_volume))
        f.write(struct.pack("<B", self.sound_effects_volume))
        f.write(struct.pack("<B", self.voice_volume))
        f.write(struct.pack("<B", self.display_blood))
        f.write(struct.pack("<B", self.subtitles))
        f.write(struct.pack("<B", self.hud))
        f.write(struct.pack("<B", self.camera_x_axis))
        f.write(struct.pack("<B", self.camera_y_axis))
        f.write(struct.pack("<B", self.toggle_auto_lockon))
        f.write(struct.pack("<B", self.camera_auto_wall_recovery))
        f.write(struct.pack("<B", self.unk0xe))
        f.write(struct.pack("<B", self.unk0xf))
        f.write(struct.pack("<B", self.reset_camera_y_axis))
        f.write(struct.pack("<B", self.cinematic_effects))
        f.write(struct.pack("<B", self.unk0x12))
        f.write(struct.pack("<B", self.cross_region_play))
        f.write(struct.pack("<B", self.voice_chat))
        f.write(struct.pack("<B", self.display_player_names))
        f.write(struct.pack("<B", self.manual_attack_aim))
        f.write(struct.pack("<B", self.autotarget))
        f.write(struct.pack("<B", self.launchsettings))
        f.write(struct.pack("<B", self.send_summon_sign))
        f.write(struct.pack("<B", self.unk0x1a))
        f.write(struct.pack("<B", self.hdr))
        f.write(struct.pack("<B", self.hdr_adjust_brightness))
        f.write(struct.pack("<B", self.hdr_maximum_brightness))
        f.write(struct.pack("<B", self.hdr_adjust_saturation))
        f.write(struct.pack("<B", self.unk0x1f))
        f.write(struct.pack("<B", self.master_volume))
        f.write(struct.pack("<B", self.is_raytracing_on))
        f.write(struct.pack("<B", self.mark_new_items))
        f.write(struct.pack("<B", self.show_recent_tabs))
        f.write(struct.pack("<Q", self.unk0x24))
        f.write(struct.pack("<H", self.unk0x2c))
        f.write(struct.pack("<B", self.show_tutorials))
        f.write(struct.pack("<B", self.camera_auto_rotation))


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
    place_name_id: int = 0
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

        obj.level = struct.unpack("<I", f.read(4))[0]
        obj.seconds_played = struct.unpack("<I", f.read(4))[0]
        obj.runes_memory = struct.unpack("<I", f.read(4))[0]
        obj.map_id = f.read(4)
        obj.place_name_id = struct.unpack("<I", f.read(4))[0]

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

        obj.profiles = [Profile.read(f) for _ in range(10)]

        return obj


@dataclass
class MenuSystemSaveLoad:
    """Menu system data with character presets"""

    raw_data: bytes = b""
    parsed: object = None  # CSMenuSystemSaveLoad from character_presets module
    offset: int = -1  # absolute position in the save, from f.tell() at parse time

    @classmethod
    def read(cls, f: BytesIO) -> MenuSystemSaveLoad:
        """Read MenuSystemSaveLoad - 0x1808 bytes"""
        obj = cls()
        obj.offset = f.tell()
        obj.raw_data = f.read(0x1808)

        # Parse presets if character_presets module is available
        try:
            from .character_presets import CSMenuSystemSaveLoad

            preset_stream = BytesIO(obj.raw_data)
            obj.parsed = CSMenuSystemSaveLoad.read(preset_stream)
        except ImportError:
            pass

        return obj

    def write(self, f: BytesIO) -> None:
        """Write back (use parsed if modified, else raw)"""
        if self.parsed:
            preset_stream = BytesIO()
            self.parsed.write(preset_stream)
            f.write(preset_stream.getvalue())
        else:
            f.write(self.raw_data)


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
    """Control bindings in the layout of KeyAssignParam.

    data holds one 20-byte record per logical action (KeyAssignParam row
    order): pad key, keyboard key, keyboard modifier, mouse key, mouse
    modifier. Control options follow at BINDING_COUNT * 20.
    """

    BINDING_COUNT = 26
    # Control option bytes, offsets in data
    MOUSE_SENSITIVITY = 0x208  # 0-10, default 5
    MOUSE_X_AXIS = 0x209  # 1 normal, 0 reverse
    MOUSE_Y_AXIS = 0x20A  # 1 normal, 0 reverse
    MAP_MENU_CURSOR_MOVEMENT = 0x20B  # 1 keyboard and mouse (default), 0 keyboard only
    TARGET_CHANGE_SENSITIVITY = 0x20C  # default 1
    PROMPT_DEVICE = 0x210  # on-screen prompts: 0 gamepad, 1 keyboard and mouse

    size: int = 0
    data: bytes = b""

    def _option(self, offset: int) -> int:
        return self.data[offset] if len(self.data) > offset else 0

    @property
    def mouse_sensitivity(self) -> int:
        return self._option(self.MOUSE_SENSITIVITY)

    @property
    def mouse_x_axis(self) -> int:
        return self._option(self.MOUSE_X_AXIS)

    @property
    def mouse_y_axis(self) -> int:
        return self._option(self.MOUSE_Y_AXIS)

    @property
    def map_menu_cursor_movement(self) -> int:
        return self._option(self.MAP_MENU_CURSOR_MOVEMENT)

    @property
    def target_change_sensitivity(self) -> int:
        return self._option(self.TARGET_CHANGE_SENSITIVITY)

    @property
    def prompt_device(self) -> int:
        return self._option(self.PROMPT_DEVICE)

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

        obj.version = struct.unpack("<I", f.read(4))[0]

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

        # Skip rest; the PC entry is 0x60000 bytes of data after its checksum
        bytes_read = f.tell() - start_pos
        remaining = (0x60000 if is_ps else 0x60010) - bytes_read
        if remaining > 0:
            f.read(remaining)

        return obj
