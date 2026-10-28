"""
Character Info Editor Module (customtkinter)
Handles character information editing (name, body type, class, etc.)
"""

import contextlib
import tkinter as tk

import customtkinter as ctk

from er_save_manager.data.starting_classes import get_all_classes, get_class_data
from er_save_manager.ui.pending import FieldTracker, StageError, var_state
from er_save_manager.ui.utils import (
    bind_mousewheel,
    patch_combo_scroll,
    trace_variable,
)
from er_save_manager.validation.names import name_problem, utf16_len

# Index = stored body type
_BODY_TYPES = ["Type A", "Type B"]
# Index = stored voice type
_VOICE_TYPES = ["Young", "Mature", "Aged"]

# Starting classes in the Tarnished Pack DLC slots (archetypes 10-11, which
# Convergence uses for its Tarnished Edition classes). Hidden from the class
# dropdown unless the character owns the DLC.
_TARNISHED_PACK_CLASS_NAMES = frozenset(
    {"Idus Knight", "Heavy Knight", "Retainer (Alt)", "Dreadnought (Alt)"}
)
_TARNISHED_PACK_FLAG = 6953


# Name field: 16 UTF-16 code units plus a terminator.
_MAX_NAME_UNITS = 16

# Keepsake names by stored value: CharMakeMenuListItemParam rows
# 100300-100309 (value, captionId -> GR_MenuText).
_KEEPSAKES = (
    "None",
    "Crimson Amber Medallion",
    "Lands Between Rune",
    "Golden Seed",
    "Fanged Imp Ashes",
    "Cracked Pot",
    "Stonesword Key",
    "Bewitching Branch",
    "Boiled Prawn",
    "Shabriri's Woe",
)
_KEEPSAKES_CONVERGENCE = (
    "None",
    "Golden Seed",
    "Sacred Tear",
    "Memory Stone",
    "Imbued Sword Key",
    "Combat Remnant",
    "Heirloom Remnant",
    "Enchanted Remnant",
    "Warding Remnant",
    "Fanged Imp Ashes",
)

# Index = ClearCount; flags 50-57 mark the same journey
_NG_LABELS = (
    "NG (0)",
    "NG+ (1)",
    "NG+2 (2)",
    "NG+3 (3)",
    "NG+4 (4)",
    "NG+5 (5)",
    "NG+6 (6)",
    "NG+7 (7)",
)

# The load screen profile stores seconds played as a u32.
_MAX_PLAYTIME_SECONDS = 0xFFFFFFFF
_MAX_PLAYTIME_HOURS = _MAX_PLAYTIME_SECONDS // 3600


def _playtime_error(hours: str, minutes: str, seconds: str) -> str:
    """Return an error message for the playtime fields, or "" if valid."""
    values = []
    for name, text, limit in (
        ("Hours", hours, _MAX_PLAYTIME_HOURS),
        ("Minutes", minutes, 59),
        ("Seconds", seconds, 59),
    ):
        try:
            value = int(text.strip())
        except ValueError:
            return f"{name} must be a whole number"
        if not 0 <= value <= limit:
            return f"{name} must be 0-{limit:,}"
        values.append(value)
    if values[0] * 3600 + values[1] * 60 + values[2] > _MAX_PLAYTIME_SECONDS:
        return "Playtime is too large"
    return ""


def _time_of_day_error(hour: str, minute: str, second: str) -> str:
    """Return an error message for the time of day fields, or "" if valid."""
    for name, text, limit in (
        ("Hour", hour, 23),
        ("Minute", minute, 59),
        ("Second", second, 59),
    ):
        try:
            value = int(text.strip())
        except ValueError:
            return f"{name} must be a whole number"
        if not 0 <= value <= limit:
            return f"{name} must be 0-{limit}"
    return ""


def _keepsake_names(is_convergence: bool) -> tuple[str, ...]:
    return _KEEPSAKES_CONVERGENCE if is_convergence else _KEEPSAKES


def _unknown_keepsake(value: int) -> str:
    """Label for a stored keepsake value outside the game's list."""
    return f"Unknown ({value})"


def _owns_tarnished_pack(slot) -> bool:
    """Check the Tarnished Pack DLC ownership flag on a character slot."""
    if not getattr(slot, "event_flags", None):
        return False
    from er_save_manager.parser.event_flags import EventFlags

    return EventFlags.get_flag(slot.event_flags, _TARNISHED_PACK_FLAG)


class CharacterInfoEditor:
    """Editor for character information and progression"""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_char_slot_callback,
        get_save_path_callback,
    ):
        """
        Initialize character info editor

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_char_slot_callback: Function that returns current character slot index
            get_save_path_callback: Function that returns save file path
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_char_slot = get_char_slot_callback
        self.get_save_path = get_save_path_callback

        self.char_name_var = None
        self.char_name_count_label = None
        self.char_body_type_var = None
        self.char_archetype_var = None
        self.char_voice_var = None
        self.char_gift_var = None
        self.char_ng_level_var = None
        self.char_playtime_h_var = None
        self.char_playtime_m_var = None
        self.char_playtime_s_var = None
        self.playtime_error_label = None
        self.time_h_var = None
        self.time_m_var = None
        self.time_s_var = None
        self.time_error_label = None
        self.tracker = FieldTracker(
            self._tracked_state,
            {
                "body": "Body type",
                "class": "Archetype",
                "voice": "Voice type",
                "gift": "Keepsake",
                "ng": "NG+ level",
                "play": "Play time",
                "time": "Time of day",
            },
        )
        self._loading = False

        self.frame = None
        # Called with the new archetype int when the user changes the class
        # combo; returns a check that prepare() runs, or None.
        self.on_archetype_change = None
        self._confirm_class = None

    def setup_ui(self):
        """Setup the character info editor UI"""
        self.frame = ctk.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
        )
        self.frame.pack(fill=ctk.BOTH, expand=True)
        bind_mousewheel(self.frame)

        creation_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        creation_frame.pack(fill=ctk.X, pady=5, padx=10)
        ctk.CTkLabel(
            creation_frame,
            text="Character creation",
            font=("Inter", 12, "bold"),
        ).grid(row=0, column=0, columnspan=5, sticky=ctk.W, padx=5, pady=(5, 0))

        ctk.CTkLabel(creation_frame, text="Name:").grid(
            row=1, column=0, sticky=ctk.W, padx=5, pady=5
        )
        self.char_name_var = ctk.StringVar(value="")
        name_entry = ctk.CTkEntry(
            creation_frame,
            textvariable=self.char_name_var,
            width=200,
        )
        name_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5)

        self.char_name_count_label = ctk.CTkLabel(
            creation_frame,
            text=f"0/{_MAX_NAME_UNITS}",
            font=("Inter", 8),
        )
        self.char_name_count_label.grid(row=1, column=4, padx=5, pady=5)
        self.name_error_label = ctk.CTkLabel(
            creation_frame, text="", text_color="red", font=("Inter", 10)
        )
        self.name_error_label.grid(row=1, column=5, sticky=ctk.W, padx=5)

        def update_name_count(*args):
            # Checked on every change instead of with key validation, so
            # pasted and loaded names are covered too; prepare() blocks.
            name = self.char_name_var.get()
            count = utf16_len(name)
            self.char_name_count_label.configure(text=f"{count}/{_MAX_NAME_UNITS}")
            self.name_error_label.configure(
                text=name_problem(name.strip(), _MAX_NAME_UNITS) or ""
            )

        trace_variable(self.char_name_var, "w", update_name_count)

        ctk.CTkLabel(creation_frame, text="Body type:").grid(
            row=2, column=0, sticky=ctk.W, padx=5, pady=5
        )
        self.char_body_type_var = ctk.StringVar(value=_BODY_TYPES[0])
        body_type_combo = ctk.CTkComboBox(
            creation_frame,
            variable=self.char_body_type_var,
            values=_BODY_TYPES,
            state="readonly",
            width=140,
        )
        body_type_combo.grid(row=2, column=1, padx=5, pady=5)

        # Archetype (starting class)
        ctk.CTkLabel(creation_frame, text="Archetype:").grid(
            row=2, column=2, sticky=ctk.W, padx=5, pady=5
        )
        self.char_archetype_var = ctk.StringVar(value="Vagabond")
        self.char_archetype_combo = ctk.CTkComboBox(
            creation_frame,
            variable=self.char_archetype_var,
            values=["Vagabond"],  # Will be populated dynamically on load
            state="readonly",
            width=140,
        )
        self.char_archetype_combo.grid(row=2, column=3, padx=5, pady=5)

        def _on_archetype_combo_change(*_args):
            # Loading a slot is not a class change; the stats editor reads
            # the stored class itself.
            if self.on_archetype_change is None or self._loading:
                return
            class_name = self.char_archetype_var.get()
            save_file = self.get_save_file()
            is_convergence = save_file.is_convergence if save_file else False
            for i, c in get_all_classes(is_convergence).items():
                if c["name"] == class_name:
                    self._confirm_class = self.on_archetype_change(i)
                    return

        self.char_archetype_var.trace_add("write", _on_archetype_combo_change)

        ctk.CTkLabel(creation_frame, text="Voice type:").grid(
            row=3, column=0, sticky=ctk.W, padx=5, pady=5
        )
        self.char_voice_var = ctk.StringVar(value=_VOICE_TYPES[0])
        voice_combo = ctk.CTkComboBox(
            creation_frame,
            variable=self.char_voice_var,
            values=_VOICE_TYPES,
            state="readonly",
            width=140,
        )
        voice_combo.grid(row=3, column=1, padx=5, pady=5)

        ctk.CTkLabel(creation_frame, text="Keepsake:").grid(
            row=3, column=2, sticky=ctk.W, padx=5, pady=5
        )
        self.char_gift_var = ctk.StringVar(value=_KEEPSAKES[0])
        self.char_gift_combo = ctk.CTkComboBox(
            creation_frame,
            variable=self.char_gift_var,
            values=list(_KEEPSAKES),
            state="readonly",
            width=200,
        )
        self.char_gift_combo.grid(row=3, column=3, padx=5, pady=5)
        patch_combo_scroll(self.char_gift_combo)

        progression_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        progression_frame.pack(fill=ctk.X, pady=5, padx=10)
        ctk.CTkLabel(
            progression_frame,
            text="Game progression",
            font=("Inter", 12, "bold"),
        ).grid(row=0, column=0, columnspan=6, sticky=ctk.W, padx=5, pady=(5, 0))

        # NG+ Level (event flag and ClearCount)
        ctk.CTkLabel(
            progression_frame,
            text="NG+ level:",
        ).grid(row=1, column=0, sticky=ctk.W, padx=5, pady=5)
        self.char_ng_level_var = ctk.StringVar(value="NG (0)")
        ng_combo = ctk.CTkComboBox(
            progression_frame,
            variable=self.char_ng_level_var,
            values=list(_NG_LABELS),
            state="readonly",
            width=140,
        )
        ng_combo.grid(row=1, column=1, padx=5, pady=5)

        # Playtime
        playtime_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        playtime_frame.pack(fill=ctk.X, pady=5, padx=10)
        ctk.CTkLabel(
            playtime_frame,
            text="Playtime",
            font=("Inter", 12, "bold"),
        ).grid(row=0, column=0, columnspan=6, sticky=ctk.W, padx=5, pady=(5, 0))

        ctk.CTkLabel(playtime_frame, text="Hours:").grid(
            row=1, column=0, sticky=ctk.W, padx=5, pady=5
        )
        self.char_playtime_h_var = tk.StringVar(value="0")
        ctk.CTkEntry(
            playtime_frame,
            textvariable=self.char_playtime_h_var,
            width=80,
        ).grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(playtime_frame, text="Minutes:").grid(
            row=1, column=2, sticky=ctk.W, padx=5, pady=5
        )
        self.char_playtime_m_var = tk.StringVar(value="0")
        ctk.CTkEntry(
            playtime_frame,
            textvariable=self.char_playtime_m_var,
            width=80,
        ).grid(row=1, column=3, padx=5, pady=5)

        ctk.CTkLabel(playtime_frame, text="Seconds:").grid(
            row=1, column=4, sticky=ctk.W, padx=5, pady=5
        )
        self.char_playtime_s_var = tk.StringVar(value="0")
        ctk.CTkEntry(
            playtime_frame,
            textvariable=self.char_playtime_s_var,
            width=80,
        ).grid(row=1, column=5, padx=5, pady=5)

        self.playtime_error_label = ctk.CTkLabel(
            playtime_frame, text="", text_color="red", font=("Inter", 10)
        )
        self.playtime_error_label.grid(
            row=2, column=0, columnspan=6, sticky=ctk.W, padx=5
        )
        for var in (
            self.char_playtime_h_var,
            self.char_playtime_m_var,
            self.char_playtime_s_var,
        ):
            trace_variable(var, "w", lambda *_a: self._on_playtime_change())

        # In-game time of day (WorldAreaTime)
        time_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        time_frame.pack(fill=ctk.X, pady=5, padx=10)
        ctk.CTkLabel(
            time_frame,
            text="Time of day",
            font=("Inter", 12, "bold"),
        ).grid(row=0, column=0, columnspan=6, sticky=ctk.W, padx=5, pady=(5, 0))

        self.time_h_var = tk.StringVar(value="0")
        self.time_m_var = tk.StringVar(value="0")
        self.time_s_var = tk.StringVar(value="0")
        for col, (label, var) in enumerate(
            (
                ("Hour:", self.time_h_var),
                ("Minute:", self.time_m_var),
                ("Second:", self.time_s_var),
            )
        ):
            ctk.CTkLabel(time_frame, text=label).grid(
                row=1, column=col * 2, sticky=ctk.W, padx=5, pady=5
            )
            ctk.CTkEntry(time_frame, textvariable=var, width=80).grid(
                row=1, column=col * 2 + 1, padx=5, pady=5
            )
            trace_variable(var, "w", lambda *_a: self._on_playtime_change())

        self.time_error_label = ctk.CTkLabel(
            time_frame, text="", text_color="red", font=("Inter", 10)
        )
        self.time_error_label.grid(row=2, column=0, columnspan=6, sticky=ctk.W, padx=5)

    def _playtime_error(self) -> str:
        return _playtime_error(
            self.char_playtime_h_var.get(),
            self.char_playtime_m_var.get(),
            self.char_playtime_s_var.get(),
        )

    def _time_of_day_error(self) -> str:
        if self.time_h_var is None:
            return ""
        return _time_of_day_error(
            self.time_h_var.get(), self.time_m_var.get(), self.time_s_var.get()
        )

    def _on_playtime_change(self) -> None:
        error = self._playtime_error()
        time_error = self._time_of_day_error()
        if self.playtime_error_label is not None:
            self.playtime_error_label.configure(text=error)
        if self.time_error_label is not None:
            self.time_error_label.configure(text=time_error)

    def _tracked_state(self) -> dict:
        state = var_state(
            {
                "name": self.char_name_var,
                "body": self.char_body_type_var,
                "class": self.char_archetype_var,
                "voice": self.char_voice_var,
                "gift": self.char_gift_var,
                "ng": self.char_ng_level_var,
                "play_h": self.char_playtime_h_var,
                "play_m": self.char_playtime_m_var,
                "play_s": self.char_playtime_s_var,
                "time_h": self.time_h_var,
                "time_m": self.time_m_var,
                "time_s": self.time_s_var,
            }
        )()
        # One field each for play time and time of day, as h:mm:ss
        for key in ("play", "time"):
            h, m, sec = (state.pop(f"{key}_{part}") for part in "hms")
            state[key] = f"{h}:{m:0>2}:{sec:0>2}"
        return state

    def load_character_info(self):
        """Load character info from current character slot"""
        self._loading = True
        try:
            self._load_character_info_fields()
        finally:
            self._loading = False
        self.tracker.mark_clean()

    def _load_character_info_fields(self):
        save_file = self.get_save_file()
        if not save_file:
            return

        slot_idx = self.get_char_slot()
        if slot_idx < 0 or slot_idx >= len(save_file.characters):
            return

        slot = save_file.characters[slot_idx]

        if not slot or slot.is_empty():
            return

        if hasattr(slot, "player_game_data") and slot.player_game_data:
            char = slot.player_game_data

            self.char_name_var.set(getattr(char, "character_name", ""))
            body = getattr(char, "gender", 0)
            self.char_body_type_var.set(
                _BODY_TYPES[body] if body < len(_BODY_TYPES) else str(body)
            )

            archetype_id = getattr(char, "archetype", 0)
            is_convergence = save_file.is_convergence
            class_data = get_class_data(archetype_id, is_convergence)
            class_name = class_data["name"] if class_data else f"Class {archetype_id}"

            all_classes = get_class_data(0, is_convergence)
            if all_classes:
                owns_dlc = _owns_tarnished_pack(slot)
                class_names = []
                for _i, c in sorted(get_all_classes(is_convergence).items()):
                    if c["name"] in _TARNISHED_PACK_CLASS_NAMES and not owns_dlc:
                        continue
                    class_names.append(c["name"])
                # Always keep the character's current class selectable, even if
                # it's a gated one and the flag got cleared some other way.
                if class_name not in class_names:
                    class_names.append(class_name)
                self.char_archetype_combo.configure(values=class_names)

            self.char_archetype_var.set(class_name)

            voice = getattr(char, "voice_type", 0)
            self.char_voice_var.set(
                _VOICE_TYPES[voice] if voice < len(_VOICE_TYPES) else str(voice)
            )
            # A stored value outside the list stays selectable and is
            # written back unchanged.
            keepsakes = list(_keepsake_names(is_convergence))
            gift = getattr(char, "gift", 0)
            if gift >= len(keepsakes):
                keepsakes.append(_unknown_keepsake(gift))
            self.char_gift_combo.configure(values=keepsakes)
            self.char_gift_var.set(keepsakes[min(gift, len(keepsakes) - 1)])

        # Play time lives in the slot header; the load screen copy follows it
        seconds_played = getattr(slot, "play_time_ms", 0) // 1000
        self.char_playtime_h_var.set(str(seconds_played // 3600))
        self.char_playtime_m_var.set(str((seconds_played % 3600) // 60))
        self.char_playtime_s_var.set(str(seconds_played % 60))

        time_of_day = slot.world_area_time
        self.time_h_var.set(str(time_of_day.hour))
        self.time_m_var.set(str(time_of_day.minute))
        self.time_s_var.set(str(time_of_day.second))

        # Load NG+ level from ClearCount if possible, else from event flags
        clearcount = None
        if hasattr(slot, "unk_gamedataman_0x120_or_gamedataman_0x130"):
            clearcount = getattr(
                slot, "unk_gamedataman_0x120_or_gamedataman_0x130", None
            )
        if clearcount is not None and 0 <= clearcount <= 7:
            self.char_ng_level_var.set(_NG_LABELS[clearcount])
        else:
            self._load_ng_level(save_file, slot_idx)

    def prepare(self):
        """Validate the fields and return the function that writes them into
        the in-memory save (Apply All in the main window)."""
        save_file = self.get_save_file()
        if not save_file:
            raise StageError("Load a save file first.")
        slot_idx = self.get_char_slot()
        if not 0 <= slot_idx < len(save_file.characters):
            raise StageError("No character loaded.")
        slot = save_file.characters[slot_idx]
        if not getattr(slot, "player_game_data", None):
            raise StageError("Could not access character data.")
        if not hasattr(slot, "player_game_data_offset"):
            raise StageError("Offset not tracked.")

        playtime_error = self._playtime_error() or self._time_of_day_error()
        if playtime_error:
            self._on_playtime_change()
            raise StageError(playtime_error)

        class_name = self.char_archetype_var.get()
        is_convergence = save_file.is_convergence
        stored_archetype = slot.player_game_data.archetype
        archetype_id = next(
            (
                i
                for i, c in get_all_classes(is_convergence).items()
                if c["name"] == class_name
            ),
            stored_archetype,
        )
        class_changed = archetype_id != stored_archetype
        # The stored class stays even when the DLC flag is missing.
        if (
            class_changed
            and class_name in _TARNISHED_PACK_CLASS_NAMES
            and not _owns_tarnished_pack(slot)
        ):
            raise StageError(
                f"'{class_name}' requires the Tarnished Pack DLC (event flag "
                f"{_TARNISHED_PACK_FLAG}) to be set on this character first."
            )
        try:
            body = _BODY_TYPES.index(self.char_body_type_var.get())
            voice = _VOICE_TYPES.index(self.char_voice_var.get())
        except ValueError:
            raise StageError("Body type and voice type are invalid.") from None
        keepsake = self.char_gift_var.get()
        keepsakes = _keepsake_names(is_convergence)
        stored_gift = slot.player_game_data.gift
        if keepsake in keepsakes:
            gift = keepsakes.index(keepsake)
        elif keepsake == _unknown_keepsake(stored_gift):
            gift = stored_gift
        else:
            raise StageError(f"Keepsake: '{keepsake}' is not a keepsake.")
        char_name = self.char_name_var.get().strip()
        problem = name_problem(char_name, _MAX_NAME_UNITS)
        if problem:
            raise StageError(problem)
        if class_changed and self._confirm_class is not None:
            # Same class minimum check as the Stats tab; raises StageError
            # when an attribute is below the new class minimum.
            self._confirm_class()
        target_level = int(self.char_ng_level_var.get().split("(")[1].rstrip(")"))
        time_of_day = (
            int(self.time_h_var.get()),
            int(self.time_m_var.get()),
            int(self.time_s_var.get()),
        )

        def commit() -> None:
            from io import BytesIO

            from er_save_manager.parser.slot_rebuild import rebuild_slot

            if isinstance(save_file._raw_data, bytes):
                save_file._raw_data = bytearray(save_file._raw_data)
            char = slot.player_game_data
            char.character_name = char_name
            summary = (
                save_file.user_data_10_parsed.profile_summary
                if getattr(save_file, "user_data_10_parsed", None)
                else None
            )
            if summary and summary.profiles and slot_idx < len(summary.profiles):
                summary.profiles[slot_idx].character_name = char_name

                # Also write to raw data so it persists to file
                from er_save_manager.transfer.character_ops import (
                    CharacterOperations,
                )

                _, profiles_base = CharacterOperations.get_profile_summary_offsets(
                    save_file
                )
                profile_offset = profiles_base + slot_idx * 0x24C

                # Character name: 16 wide chars = 32 bytes + 2 byte terminator
                name_bytes = char_name.encode("utf-16-le")
                name_bytes = (name_bytes + b"\x00" * 32)[:32]
                save_file._raw_data[profile_offset : profile_offset + 32] = name_bytes
                save_file._raw_data[profile_offset + 32 : profile_offset + 34] = (
                    b"\x00\x00"
                )

            char.gender = body
            char.archetype = archetype_id
            char.voice_type = voice
            char.gift = gift

            # ClearCount (NG+ playthroughs, raw field)
            if hasattr(slot, "unk_gamedataman_0x120_or_gamedataman_0x130"):
                slot.unk_gamedataman_0x120_or_gamedataman_0x130 = target_level

            char_bytes = BytesIO()
            char.write(char_bytes)
            char_data = char_bytes.getvalue()
            # player_game_data_offset is absolute in the raw file
            abs_offset = slot.player_game_data_offset
            save_file._raw_data[abs_offset : abs_offset + len(char_data)] = char_data

            self._apply_ng_level(save_file, slot_idx, force_clearcount=target_level)
            self._apply_playtime(save_file, slot_idx, slot)
            (
                slot.world_area_time.hour,
                slot.world_area_time.minute,
                slot.world_area_time.second,
            ) = time_of_day

            rebuilt_bytes = rebuild_slot(slot)
            abs_offset = save_file.slot_data_offset(slot_idx)
            save_file._raw_data[abs_offset : abs_offset + len(rebuilt_bytes)] = (
                rebuilt_bytes
            )

        return commit

    def _load_ng_level(self, save_file, slot_idx):
        """Load NG+ level from event flags using EventFlags.get_flag (matches event flag tab)"""
        try:
            from er_save_manager.parser.event_flags import EventFlags

            ng_flag_ids = [50, 51, 52, 53, 54, 55, 56, 57]
            slot = save_file.characters[slot_idx]
            flags = slot.event_flags

            ng_bits = []
            for flag_id in ng_flag_ids:
                try:
                    is_set = EventFlags.get_flag(flags, flag_id)
                except Exception:
                    is_set = 0
                ng_bits.append(1 if is_set else 0)

            # Strict logic:
            # - If only flag 50 is set, show NG (0)
            # - If only one of 51-57 is set, show that NG+
            # - Otherwise, default to NG (0)
            if ng_bits[0] == 1 and sum(ng_bits[1:]) == 0:
                self.char_ng_level_var.set("NG (0)")
            elif sum(ng_bits[1:]) == 1 and ng_bits[0] == 0:
                idx = ng_bits[1:].index(1) + 1
                self.char_ng_level_var.set(_NG_LABELS[idx])
            else:
                self.char_ng_level_var.set("NG (0)")
        except Exception:
            self.char_ng_level_var.set("NG (0)")

    def _apply_ng_level(self, save_file, slot_idx, force_clearcount=None):
        """Apply NG+ level changes to save file using EventFlags.set_flag (matches event flag tab). Optionally force ClearCount."""
        try:
            from er_save_manager.parser.event_flags import EventFlags

            ng_string = self.char_ng_level_var.get()
            target_level = int(ng_string.split("(")[1].rstrip(")"))

            ng_flag_ids = [50, 51, 52, 53, 54, 55, 56, 57]
            slot = save_file.characters[slot_idx]
            # Always operate on a mutable buffer
            flags = (
                bytearray(slot.event_flags)
                if not isinstance(slot.event_flags, bytearray)
                else slot.event_flags
            )

            for flag_id in ng_flag_ids:
                with contextlib.suppress(Exception):
                    EventFlags.set_flag(flags, flag_id, False)

            target_flag_id = ng_flag_ids[target_level]
            with contextlib.suppress(Exception):
                EventFlags.set_flag(flags, target_flag_id, True)

            slot.event_flags = bytes(flags)

            # Update ClearCount (the actual playthrough counter)
            # If force_clearcount is provided, use it, else set to target_level
            if hasattr(slot, "unk_gamedataman_0x120_or_gamedataman_0x130"):
                cc_val = (
                    force_clearcount if force_clearcount is not None else target_level
                )
                slot.unk_gamedataman_0x120_or_gamedataman_0x130 = cc_val

        except Exception:
            raise

    def _apply_playtime(self, save_file, slot_idx: int, slot) -> None:
        """
        Write play time to the slot header (play_time_ms) and the load screen
        profile (seconds_played). WorldAreaTime is the time of day and stays.
        """
        import struct

        if (
            self.char_playtime_h_var is None
            or self.char_playtime_m_var is None
            or self.char_playtime_s_var is None
        ):
            return

        # apply_changes rejects invalid fields before anything is written.
        total_seconds = (
            int(self.char_playtime_h_var.get()) * 3600
            + int(self.char_playtime_m_var.get()) * 60
            + int(self.char_playtime_s_var.get())
        )

        slot.play_time_ms = total_seconds * 1000
        struct.pack_into(
            "<Q", save_file._raw_data, slot.data_start + 8, slot.play_time_ms
        )

        if (
            hasattr(save_file, "user_data_10_parsed")
            and save_file.user_data_10_parsed
            and save_file.user_data_10_parsed.profile_summary
        ):
            profiles = save_file.user_data_10_parsed.profile_summary.profiles
            if profiles and slot_idx < len(profiles):
                profiles[slot_idx].seconds_played = total_seconds

            from er_save_manager.transfer.character_ops import CharacterOperations

            _, profiles_base = CharacterOperations.get_profile_summary_offsets(
                save_file
            )
            profile_size = 0x24C
            # seconds_played is at +0x26 within the Profile struct:
            # +0x00 name (32 bytes) + terminator (2 bytes) + level (4 bytes) = 0x26
            sp_offset = profiles_base + slot_idx * profile_size + 0x26
            save_file._raw_data[sp_offset : sp_offset + 4] = struct.pack(
                "<I", total_seconds
            )
