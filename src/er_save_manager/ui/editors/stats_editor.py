"""
Stats Editor Module
Handles character stats editing UI and logic
"""

import logging
import tkinter as tk

import customtkinter as ctk

from er_save_manager.data import (
    calculate_level_from_stats,
    get_class_data,
    runes_to_reach_level,
)
from er_save_manager.data.grace_data import (
    Grace,
    get_graces,
    grace_from_last_rested,
    last_rested_grace_value,
)
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import FieldTracker, StageError
from er_save_manager.ui.utils import (
    bind_mousewheel,
    patch_combo_scroll,
    trace_variable,
)

logger = logging.getLogger(__name__)

# The game caps held runes at 999,999,999.
MAX_RUNES = 999_999_999
# Runes memory is a u32 and keeps counting past the held runes cap.
MAX_RUNES_MEMORY = 0xFFFFFFFF
MAX_SCADUTREE = 20
MAX_REVERED_SPIRIT_ASH = 10
MAX_MEMORY_STONES = 8
MAX_MATCHMAKING_LEVEL = 25

# Memory Stone goods; the held quantity matches PlayerGameData memory_stone_count
_MEMORY_STONE = 0x4000272E


# Region shown for a last rested grace the dropdowns cannot represent.
_CURRENT_GRACE_REGION = "Current value"


def _range_error(text: str, limit: int) -> str:
    """Return an error message for text outside 0..limit, or "" if valid."""
    text = text.strip()
    if not text:
        return "cannot be empty"
    try:
        value = int(text)
    except ValueError:
        return f"whole number 0-{limit}"
    if not 0 <= value <= limit:
        return f"must be 0-{limit}"
    return ""


def _sync_memory_stones(save_file, slot_idx: int, slot, count: int) -> str | None:
    """Set the held Memory Stone quantity to count; return a note on failure."""
    from er_save_manager.parser import inventory_ops

    handle = 0xB0000000 | (_MEMORY_STONE & 0x0FFFFFFF)
    held = sum(
        item.quantity
        for item in slot.inventory_held.key_items + slot.inventory_held.common_items
        if item.gaitem_handle == handle
    )
    if held == count:
        return None
    try:
        if count == 0:
            inventory_ops.remove_item(save_file, slot_idx, _MEMORY_STONE)
        elif held:
            inventory_ops.set_quantity(save_file, slot_idx, _MEMORY_STONE, count)
        else:
            inventory_ops.add_item(save_file, slot_idx, _MEMORY_STONE, count)
    except Exception as e:
        logger.exception("Memory Stone sync failed")
        return f"Memory Stone item could not be updated: {e}"
    return None


_ATTR_KEYS = frozenset(
    {
        "vigor",
        "mind",
        "endurance",
        "strength",
        "dexterity",
        "intelligence",
        "faith",
        "arcane",
    }
)


class StatsEditor:
    """Stats editor for character attributes, level, and runes"""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_char_slot_callback,
        get_save_path_callback,
    ):
        """
        Initialize stats editor

        Args:
            parent: Parent customtkinter widget
            get_save_file_callback: Function that returns current save file
            get_char_slot_callback: Function that returns current character slot index
            get_save_path_callback: Function that returns save file path
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_char_slot = get_char_slot_callback
        self.get_save_path = get_save_path_callback

        self.stat_vars = {}
        self._attr_error_labels: dict[str, ctk.CTkLabel] = {}
        self._attr_entries: dict[str, ctk.CTkEntry] = {}
        self.level_var = None
        self.calculated_level_var = None
        self.level_warning_var = None

        self._logger = logging.getLogger(__name__)
        self._current_archetype: int = 9  # tracks archetype for per-stat minimums
        self.level_warning_label = None
        self.runes_var = None
        self.recover_runes_button = None
        self.bloodstain_var = None
        # Bloodstain runes moved into the runes field, cleared from the
        # bloodstain on apply
        self._recovered_runes = 0
        self.great_rune_on_var = None
        self.great_rune_id_var = None
        self.last_grace_var = None
        self.matchmaking_level_var = None
        self.scadutree_blessing_var = None
        self.revered_spirit_ash_var = None
        self.memory_stone_var = None
        # Field name -> (variable, limit, label, hint) for the 0..limit fields;
        # the label shows the hint, or the error while the value is invalid.
        self._range_fields: dict[str, tuple[tk.StringVar, int, ctk.CTkLabel, str]] = {}
        self.grace_region_var = None
        self.grace_region_combo = None
        self.grace_combo = None
        self._grace_options: dict[str, dict[str, Grace]] = {}
        self._last_grace_raw = 0
        self._last_grace_loaded: tuple[str, str] = ("", "")
        self._matchmaking_min = 0  # floor derived from inventory scan
        self.tracker = FieldTracker(
            self._tracked_state,
            {
                "great_rune_on": "Great Rune active",
                "great_rune": "Active Great Rune",
                "grace": "Last rested grace",
                "scadutree": "Scadutree Blessing",
                "revered_spirit_ash": "Revered Spirit Ash Blessing",
                "memory_stones": "Memory Stones",
                "matchmaking": "Matchmaking level",
            },
        )

        self.frame = None

    def setup_ui(self):
        """Setup the stats editor UI"""
        self.frame = ctk.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
        )
        self.frame.pack(fill=ctk.BOTH, expand=True)

        bind_mousewheel(self.frame)

        # Single row: Attributes and Resources side by side
        top_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        top_row.pack(fill=ctk.X, pady=5, padx=10)

        stats_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        stats_frame.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=(0, 5))

        ctk.CTkLabel(
            stats_frame,
            text="Attributes",
            font=("Inter", 12, "bold"),
        ).pack(anchor=ctk.W, padx=5, pady=(5, 0))

        stats_grid = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_grid.pack(fill=ctk.X, padx=5, pady=5)

        attributes = [
            ("Vigor", "vigor"),
            ("Mind", "mind"),
            ("Endurance", "endurance"),
            ("Strength", "strength"),
            ("Dexterity", "dexterity"),
            ("Intelligence", "intelligence"),
            ("Faith", "faith"),
            ("Arcane", "arcane"),
        ]

        for i, (label, key) in enumerate(attributes):
            ctk.CTkLabel(stats_grid, text=f"{label}:").grid(
                row=i, column=0, sticky=ctk.W, padx=5, pady=5
            )

            var = tk.StringVar(value="0")
            self.stat_vars[key] = var
            entry = ctk.CTkEntry(
                stats_grid,
                textvariable=var,
                width=120,
            )
            entry.grid(row=i, column=1, padx=5, pady=5)
            self._attr_entries[key] = entry

            error_label = ctk.CTkLabel(
                stats_grid,
                text="",
                text_color="red",
                font=("Inter", 10),
                width=80,
            )
            error_label.grid(row=i, column=2, padx=(0, 5), pady=5, sticky=ctk.W)
            self._attr_error_labels[key] = error_label

            entry.bind("<KeyRelease>", lambda e, k=key: self._on_attr_change(k))
            entry.bind("<FocusOut>", lambda e, k=key: self._on_attr_change(k))

        # Max HP/FP/Stamina on the right (base max values only, no active HP/FP/SP)
        resources_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        resources_frame.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=(5, 0))

        ctk.CTkLabel(
            resources_frame,
            text="Max health/FP/stamina",
            font=("Inter", 12, "bold"),
        ).pack(anchor=ctk.W, padx=5, pady=(5, 0))

        resources_grid = ctk.CTkFrame(resources_frame, fg_color="transparent")
        resources_grid.pack(fill=ctk.X, padx=5, pady=5)

        resources = [
            ("Max HP", "base_max_hp"),
            ("Max FP", "base_max_fp"),
            ("Max Stamina", "base_max_sp"),
        ]

        for i, (label, key) in enumerate(resources):
            ctk.CTkLabel(resources_grid, text=f"{label}:").grid(
                row=i, column=0, sticky=ctk.W, padx=5, pady=5
            )

            var = ctk.IntVar(value=0)
            self.stat_vars[key] = var
            # Read-only: the game derives these from the attributes on load.
            ctk.CTkEntry(
                resources_grid,
                textvariable=var,
                width=120,
                state="disabled",
            ).grid(row=i, column=1, padx=5, pady=5)

        # Bottom row: Level & Runes in one compact frame
        bottom_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        bottom_row.pack(fill=ctk.X, pady=5, padx=10)

        other_frame = ctk.CTkFrame(bottom_row, fg_color=("gray86", "gray25"))
        other_frame.pack(fill=ctk.X)

        ctk.CTkLabel(
            other_frame,
            text="Level & runes",
            font=("Inter", 12, "bold"),
            text_color=("black", "white"),
        ).grid(row=0, column=0, columnspan=5, sticky=ctk.W, padx=5, pady=(5, 0))

        content_row = 1

        ctk.CTkLabel(other_frame, text="Level:", text_color=("black", "white")).grid(
            row=content_row, column=0, sticky=ctk.W, padx=5, pady=5
        )

        self.level_var = tk.StringVar(value="0")
        ctk.CTkEntry(
            other_frame,
            textvariable=self.level_var,
            width=120,
            fg_color=("gray86", "gray25"),
            text_color=("black", "white"),
            border_color=("gray70", "gray40"),
            border_width=1,
        ).grid(row=content_row, column=1, padx=5, pady=5)

        ctk.CTkLabel(
            other_frame, text="Calculated level:", text_color=("black", "white")
        ).grid(row=content_row, column=2, sticky=ctk.W, padx=(20, 5), pady=5)

        self.calculated_level_var = ctk.IntVar(value=0)
        ctk.CTkLabel(
            other_frame,
            textvariable=self.calculated_level_var,
            text_color=("black", "white"),
            font=("Inter", 10, "bold"),
        ).grid(row=content_row, column=3, padx=5, pady=5)

        self.level_warning_var = ctk.StringVar(value="")
        self.level_warning_label = ctk.CTkLabel(
            other_frame,
            textvariable=self.level_warning_var,
            text_color="red",
            font=("Inter", 11),
        )
        self.level_warning_label.grid(
            row=content_row, column=4, padx=10, pady=5, sticky=ctk.W
        )

        ctk.CTkLabel(other_frame, text="Runes:", text_color=("black", "white")).grid(
            row=content_row + 1, column=0, sticky=ctk.W, padx=5, pady=5
        )

        self.runes_var = tk.StringVar(value="0")
        ctk.CTkEntry(
            other_frame,
            textvariable=self.runes_var,
            width=120,
            fg_color=("gray86", "gray25"),
            text_color=("black", "white"),
            border_color=("gray70", "gray40"),
            border_width=1,
        ).grid(
            row=content_row + 1, column=1, columnspan=2, sticky=ctk.W, padx=5, pady=5
        )

        self.recover_runes_button = ctk.CTkButton(
            other_frame,
            text="Recover Lost Runes",
            command=self._recover_lost_runes,
            width=150,
            state="disabled",
        )
        self.recover_runes_button.grid(
            row=content_row + 1, column=3, padx=5, pady=5, sticky=ctk.W
        )
        self.bloodstain_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            other_frame,
            textvariable=self.bloodstain_var,
            text_color=("black", "white"),
            font=("Inter", 11),
        ).grid(row=content_row + 1, column=4, padx=10, pady=5, sticky=ctk.W)

        # Great rune / rune arc
        rune_frame = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        rune_frame.pack(fill=ctk.X, pady=5, padx=10)

        ctk.CTkLabel(
            rune_frame,
            text="Great Rune & Rune Arc",
            font=("Inter", 12, "bold"),
            text_color=("black", "white"),
        ).grid(row=0, column=0, columnspan=4, sticky=ctk.W, padx=5, pady=(5, 0))

        # One flag covers both: using a Rune Arc activates the equipped Great Rune.
        self.great_rune_on_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            rune_frame,
            text="Great Rune active (Rune Arc used)",
            variable=self.great_rune_on_var,
            text_color=("black", "white"),
        ).grid(row=1, column=0, columnspan=2, sticky=ctk.W, padx=5, pady=5)

        ctk.CTkLabel(
            rune_frame, text="Active Great Rune:", text_color=("black", "white")
        ).grid(row=2, column=0, sticky=ctk.W, padx=5, pady=5)

        _GREAT_RUNES = [
            ("None", 0),
            ("Godrick's Great Rune", 0xB00000BF),
            ("Radahn's Great Rune", 0xB00000C0),
            ("Morgott's Great Rune", 0xB00000C1),
            ("Rykard's Great Rune", 0xB00000C2),
            ("Mohg's Great Rune", 0xB00000C3),
            ("Malenia's Great Rune", 0xB00000C4),
        ]
        self._great_rune_options = _GREAT_RUNES
        self.great_rune_id_var = tk.StringVar(value=_GREAT_RUNES[0][0])
        ctk.CTkComboBox(
            rune_frame,
            variable=self.great_rune_id_var,
            values=[name for name, _ in _GREAT_RUNES],
            state="readonly",
            width=260,
        ).grid(row=2, column=1, columnspan=2, sticky=ctk.W, padx=5, pady=(5, 10))

        # Blessings and memory stones
        blessing_frame = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        blessing_frame.pack(fill=ctk.X, pady=5, padx=10)

        ctk.CTkLabel(
            blessing_frame,
            text="Blessings & Memory Stones",
            font=("Inter", 12, "bold"),
            text_color=("black", "white"),
        ).grid(row=0, column=0, columnspan=3, sticky=ctk.W, padx=5, pady=(5, 0))

        self.scadutree_blessing_var = tk.StringVar(value="0")
        self.revered_spirit_ash_var = tk.StringVar(value="0")
        self.memory_stone_var = tk.StringVar(value="0")
        for row, (key, label, var, limit) in enumerate(
            (
                (
                    "scadutree",
                    "Scadutree Blessing:",
                    self.scadutree_blessing_var,
                    MAX_SCADUTREE,
                ),
                (
                    "revered_spirit_ash",
                    "Revered Spirit Ash Blessing:",
                    self.revered_spirit_ash_var,
                    MAX_REVERED_SPIRIT_ASH,
                ),
                (
                    "memory_stones",
                    "Memory Stones:",
                    self.memory_stone_var,
                    MAX_MEMORY_STONES,
                ),
            ),
            start=1,
        ):
            ctk.CTkLabel(
                blessing_frame, text=label, text_color=("black", "white")
            ).grid(row=row, column=0, sticky=ctk.W, padx=5, pady=5)
            ctk.CTkEntry(blessing_frame, textvariable=var, width=80).grid(
                row=row, column=1, sticky=ctk.W, padx=5, pady=5
            )
            hint = ctk.CTkLabel(
                blessing_frame,
                text=f"0-{limit}",
                text_color=("gray50", "gray70"),
                font=("Inter", 9),
            )
            hint.grid(row=row, column=2, sticky=ctk.W, padx=5, pady=5)
            self._range_fields[key] = (var, limit, hint, f"0-{limit}")
            trace_variable(var, "w", lambda *_a, k=key: self._on_range_change(k))

        # Last rested grace
        grace_frame = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        grace_frame.pack(fill=ctk.X, pady=5, padx=10)

        ctk.CTkLabel(
            grace_frame,
            text="Last rested grace",
            font=("Inter", 12, "bold"),
            text_color=("black", "white"),
        ).grid(row=0, column=0, columnspan=2, sticky=ctk.W, padx=5, pady=(5, 0))

        ctk.CTkLabel(grace_frame, text="Region:", text_color=("black", "white")).grid(
            row=1, column=0, sticky=ctk.W, padx=5, pady=5
        )
        self.grace_region_var = tk.StringVar(value="")
        self.grace_region_combo = ctk.CTkComboBox(
            grace_frame,
            variable=self.grace_region_var,
            values=[],
            state="readonly",
            width=300,
            command=self._on_grace_region_changed,
        )
        patch_combo_scroll(self.grace_region_combo)
        self.grace_region_combo.grid(row=1, column=1, padx=5, pady=5, sticky=ctk.W)

        ctk.CTkLabel(grace_frame, text="Grace:", text_color=("black", "white")).grid(
            row=2, column=0, sticky=ctk.W, padx=5, pady=5
        )
        self.last_grace_var = tk.StringVar(value="")
        self.grace_combo = ctk.CTkComboBox(
            grace_frame,
            variable=self.last_grace_var,
            values=[],
            state="readonly",
            width=300,
        )
        patch_combo_scroll(self.grace_combo)
        self.grace_combo.grid(row=2, column=1, padx=5, pady=(5, 10), sticky=ctk.W)

        # Matchmaking weapon level
        mm_frame = ctk.CTkFrame(self.frame, fg_color=("gray86", "gray25"))
        mm_frame.pack(fill=ctk.X, pady=5, padx=10)

        ctk.CTkLabel(
            mm_frame,
            text="Matchmaking weapon level",
            font=("Inter", 12, "bold"),
            text_color=("black", "white"),
        ).grid(row=0, column=0, columnspan=3, sticky=ctk.W, padx=5, pady=(5, 0))

        ctk.CTkLabel(
            mm_frame,
            text="Level (0-25):",
            text_color=("black", "white"),
        ).grid(row=1, column=0, sticky=ctk.W, padx=5, pady=5)

        self.matchmaking_level_var = tk.StringVar(value="0")
        ctk.CTkEntry(
            mm_frame,
            textvariable=self.matchmaking_level_var,
            width=60,
            fg_color=("gray86", "gray25"),
            text_color=("black", "white"),
            border_color=("gray70", "gray40"),
            border_width=1,
        ).grid(row=1, column=1, padx=5, pady=5, sticky=ctk.W)

        self._mm_min_label = ctk.CTkLabel(
            mm_frame,
            text="Min from inventory: --",
            text_color=("gray50", "gray60"),
            font=("Inter", 10),
        )
        self._mm_min_label.grid(row=1, column=2, padx=10, pady=5, sticky=ctk.W)

        mm_error = ctk.CTkLabel(mm_frame, text="", font=("Inter", 10))
        mm_error.grid(row=1, column=3, padx=5, pady=5, sticky=ctk.W)
        self._range_fields["matchmaking"] = (
            self.matchmaking_level_var,
            MAX_MATCHMAKING_LEVEL,
            mm_error,
            "",
        )
        trace_variable(
            self.matchmaking_level_var,
            "w",
            lambda *_a: self._on_range_change("matchmaking"),
        )

    def load_stats(self):
        """Load stats from current character slot"""
        # Errors belong to the edits that load or discard replaces.
        for label in self._attr_error_labels.values():
            label.configure(text="")
        save_file = self.get_save_file()
        if not save_file:
            return

        slot_idx = self.get_char_slot()
        if slot_idx < 0 or slot_idx >= len(save_file.characters):
            return

        slot = save_file.characters[slot_idx]
        if not hasattr(slot, "player_game_data") or not slot.player_game_data:
            return

        char = slot.player_game_data
        self._current_archetype = getattr(char, "archetype", 9)

        # Debug: log raw values loaded from save
        try:
            self._logger.debug(
                "Loaded stats for slot %s: vig=%s mind=%s end=%s str=%s dex=%s int=%s fth=%s arc=%s lvl=%s runes=%s base_hp=%s base_fp=%s base_sp=%s",
                slot_idx,
                getattr(char, "vigor", None),
                getattr(char, "mind", None),
                getattr(char, "endurance", None),
                getattr(char, "strength", None),
                getattr(char, "dexterity", None),
                getattr(char, "intelligence", None),
                getattr(char, "faith", None),
                getattr(char, "arcane", None),
                getattr(char, "level", None),
                getattr(char, "runes", None),
                getattr(char, "base_max_hp", None),
                getattr(char, "base_max_fp", None),
                getattr(char, "base_max_sp", None),
            )
        except Exception:
            self._logger.exception("Failed logging stats for slot %s", slot_idx)

        for key in _ATTR_KEYS:
            self.stat_vars[key].set(str(getattr(char, key, 0)))

        # Load base max resources only
        self.stat_vars["base_max_hp"].set(getattr(char, "base_max_hp", 0))
        self.stat_vars["base_max_fp"].set(getattr(char, "base_max_fp", 0))
        self.stat_vars["base_max_sp"].set(getattr(char, "base_max_sp", 0))

        self.level_var.set(str(getattr(char, "level", 0)))
        self.runes_var.set(str(getattr(char, "runes", 0)))
        self._recovered_runes = 0
        self._refresh_bloodstain(slot)

        self.great_rune_on_var.set(bool(getattr(char, "great_rune_on", False)))
        rune_id = slot.equipped_items.great_rune
        rune_name = next(
            (n for n, v in self._great_rune_options if v == rune_id),
            self._great_rune_options[0][0],
        )
        self.great_rune_id_var.set(rune_name)

        self._load_last_grace(slot, bool(getattr(save_file, "is_convergence", False)))

        # Load matchmaking weapon level and compute inventory floor
        self.matchmaking_level_var.set(
            str(getattr(char, "matchmaking_weapon_level", 0))
        )
        self.scadutree_blessing_var.set(str(char.scadutree_blessing))
        self.revered_spirit_ash_var.set(str(char.revered_spirit_ash_blessing))
        self.memory_stone_var.set(str(char.memory_stone_count))
        self._refresh_matchmaking_min(slot)

        self.calculate_character_level()
        self.tracker.mark_clean()

    def _tracked_state(self) -> dict:
        """Every field Apply All writes, as shown."""
        variables = {key: self.stat_vars[key] for key in _ATTR_KEYS} | {
            "runes": self.runes_var,
            "great_rune_on": self.great_rune_on_var,
            "great_rune": self.great_rune_id_var,
            "grace_region": self.grace_region_var,
            "grace": self.last_grace_var,
        }
        state = {}
        for key, var in variables.items():
            try:
                state[key] = str(var.get())
            except tk.TclError:
                state[key] = None
        for key, (var, _limit, _label, _hint) in self._range_fields.items():
            state[key] = var.get()
        return state

    @staticmethod
    def _bloodstain_runes(slot) -> int:
        """Runes held by the bloodstain, 0 if there is none to pick up."""
        stain = getattr(slot, "blood_stain", None)
        if stain is None or stain.unk0x30 == -1:
            return 0
        return max(0, stain.runes)

    def _refresh_bloodstain(self, slot) -> None:
        runes = self._bloodstain_runes(slot) if not self._recovered_runes else 0
        if self._recovered_runes:
            text = f"{self._recovered_runes:,} runes recovered (Apply All to save)"
        elif runes:
            text = f"Bloodstain: {runes:,} runes"
        else:
            text = "No bloodstain"
        self.bloodstain_var.set(text)
        self.recover_runes_button.configure(state="normal" if runes else "disabled")

    def _recover_lost_runes(self) -> None:
        """Move the bloodstain runes into the held runes field."""
        save_file = self.get_save_file()
        slot_idx = self.get_char_slot()
        if not save_file or not 0 <= slot_idx < len(save_file.characters):
            return
        slot = save_file.characters[slot_idx]
        stain_runes = self._bloodstain_runes(slot)
        if not stain_runes:
            return
        try:
            runes = int(self.runes_var.get())
        except (ValueError, tk.TclError):
            runes = slot.player_game_data.runes
        if runes + stain_runes > MAX_RUNES:
            CTkMessageBox.showwarning(
                "Recover Lost Runes",
                f"Held runes would exceed {MAX_RUNES:,}. The total is capped and "
                "the excess is lost.",
                parent=self.parent,
            )
        self.runes_var.set(str(min(MAX_RUNES, runes + stain_runes)))
        self._recovered_runes = stain_runes
        self._refresh_bloodstain(slot)

    def changes(self) -> int:
        # Recovered runes also clear the bloodstain on apply.
        return self.tracker.changes() + (1 if self._recovered_runes else 0)

    def details(self):
        rows = self.tracker.details()
        if self._recovered_runes:
            rows.append(("Bloodstain", f"{self._recovered_runes:,} runes", "recovered"))
        return rows

    def calculate_character_level(self):
        """Calculate expected character level from attributes based on starting class"""
        try:
            archetype = 9  # Default to Wretch

            save_file = self.get_save_file()
            if save_file:
                slot_idx = self.get_char_slot()
                try:
                    slot = save_file.characters[slot_idx]
                    if (
                        slot
                        and hasattr(slot, "player_game_data")
                        and slot.player_game_data
                    ):
                        archetype = slot.player_game_data.archetype
                except Exception:
                    pass

            vigor, mind, endurance, strength, dexterity, intelligence, faith, arcane = (
                int(self.stat_vars[key].get().strip())
                for key in (
                    "vigor",
                    "mind",
                    "endurance",
                    "strength",
                    "dexterity",
                    "intelligence",
                    "faith",
                    "arcane",
                )
            )

            is_convergence = False
            save_file = self.get_save_file()
            if save_file and hasattr(save_file, "is_convergence"):
                is_convergence = save_file.is_convergence

            calculated_level = calculate_level_from_stats(
                vigor,
                mind,
                endurance,
                strength,
                dexterity,
                intelligence,
                faith,
                arcane,
                archetype,
                is_convergence,
            )

            self.calculated_level_var.set(str(calculated_level))

            # Show class name in warning if available
            class_data = get_class_data(archetype, is_convergence)
            class_name = class_data.get("name", "Unknown")

            try:
                current_level = int(self.level_var.get())
            except (ValueError, TypeError):
                current_level = 0

            if current_level != calculated_level:
                self.level_warning_var.set(
                    f"⚠ Mismatch. Recommend {calculated_level} (based on {class_name})"
                )
            else:
                self.level_warning_var.set("")

        except Exception:
            self.calculated_level_var.set("0")
            self.level_warning_var.set("")

    def on_archetype_changed(self, archetype_id: int) -> None:
        """Called when the user changes the starting class in the Info tab.

        Updates internal archetype tracking, recalculates level, and warns if
        any current stat falls below the new class minimum.
        """
        save_file = self.get_save_file()
        is_convergence = (
            save_file.is_convergence
            if save_file and hasattr(save_file, "is_convergence")
            else False
        )
        self._current_archetype = archetype_id
        class_data = get_class_data(archetype_id, is_convergence)
        if not class_data:
            return

        stat_keys = [
            "vigor",
            "mind",
            "endurance",
            "strength",
            "dexterity",
            "intelligence",
            "faith",
            "arcane",
        ]
        violations: list[str] = []
        for key in stat_keys:
            stat_min = class_data.get(key, 1)
            try:
                current = int(self._attr_entries[key].get().strip())
            except (ValueError, AttributeError):
                current = 0
            if current < stat_min:
                label = key.capitalize()
                violations.append(f"{label}: current {current}, minimum {stat_min}")

        # Re-validate all entries so error labels update immediately.
        for key in stat_keys:
            self._on_attr_change(key)

        self.calculate_character_level()

        if violations:
            violation_text = "\n".join(violations)
            CTkMessageBox.showwarning(
                "Class Minimum Conflict",
                f"The following stats are below the minimum for {class_data['name']}:\n\n"
                f"{violation_text}\n\n"
                f"Raise these stats to at least the minimum before applying.",
                parent=self.parent,
            )

    def _on_attr_change(self, key: str) -> None:
        # Validate against class base minimum and 99 cap.
        save_file = self.get_save_file()
        is_convergence = (
            save_file.is_convergence
            if save_file and hasattr(save_file, "is_convergence")
            else False
        )
        class_data = get_class_data(self._current_archetype, is_convergence)
        stat_min = class_data.get(key, 1) if class_data else 1

        raw = self._attr_entries[key].get().strip()
        if not raw:
            msg = "cannot be empty"
        else:
            try:
                val = int(raw)
                if val < stat_min:
                    msg = f"min {stat_min}"
                elif val > 99:
                    msg = "max 99"
                else:
                    msg = ""
            except ValueError:
                msg = f"min {stat_min} - 99"
        self._attr_error_labels[key].configure(text=msg)
        self.calculate_character_level()

    def _on_range_change(self, key: str) -> None:
        var, limit, label, hint = self._range_fields[key]
        error = _range_error(var.get(), limit)
        label.configure(
            text=error or hint,
            text_color="red" if error else ("gray50", "gray70"),
        )

    def _range_value(self, key: str) -> int:
        return int(self._range_fields[key][0].get().strip())

    def _load_last_grace(self, slot, convergence: bool) -> None:
        """Fill the region/grace dropdowns and select the slot's last grace."""
        by_region: dict[str, list[Grace]] = {}
        for grace in get_graces(include_convergence=convergence):
            if last_rested_grace_value(grace, convergence) is not None:
                by_region.setdefault(grace.region, []).append(grace)
        self._grace_options = {}
        for region, graces in by_region.items():
            names = [g.name for g in graces]
            # Convergence has graces sharing a name within a region.
            self._grace_options[region] = {
                (f"{g.name} ({g.flag_id})" if names.count(g.name) > 1 else g.name): g
                for g in graces
            }

        raw = getattr(slot, "last_rested_grace", 0)
        self._last_grace_raw = raw
        grace = grace_from_last_rested(raw, convergence) if raw else None
        selected = next(
            (
                (region, label)
                for region, graces in self._grace_options.items()
                for label, g in graces.items()
                if grace is not None
                and g.flag_id == grace.flag_id
                and last_rested_grace_value(g, convergence) == raw
            ),
            None,
        )
        if selected is None:
            # Keep values the dropdowns cannot produce (unset, unknown, or a
            # grace from the other regulation) selectable as they are.
            if raw == 0:
                label = "None"
            elif grace is not None:
                label = f"{grace.name} ({raw})"
            else:
                label = f"Unknown ({raw})"
            self._grace_options = {
                _CURRENT_GRACE_REGION: {label: None},
                **self._grace_options,
            }
            selected = (_CURRENT_GRACE_REGION, label)
        self._last_grace_loaded = selected

        self.grace_region_combo.configure(values=list(self._grace_options))
        self.grace_region_var.set(selected[0])
        self.grace_combo.configure(values=list(self._grace_options[selected[0]]))
        self.last_grace_var.set(selected[1])

    def _on_grace_region_changed(self, region: str) -> None:
        labels = list(self._grace_options.get(region, {}))
        self.grace_combo.configure(values=labels)
        if region == self._last_grace_loaded[0]:
            self.last_grace_var.set(self._last_grace_loaded[1])
        else:
            self.last_grace_var.set(labels[0] if labels else "")

    def _selected_last_grace(self, convergence: bool) -> int:
        """Return the last_rested_grace value for the current selection."""
        selected = (self.grace_region_var.get(), self.last_grace_var.get())
        if selected == self._last_grace_loaded:
            return self._last_grace_raw
        grace = self._grace_options.get(selected[0], {}).get(selected[1])
        value = last_rested_grace_value(grace, convergence) if grace else None
        return self._last_grace_raw if value is None else value

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
            raise StageError("Character has no game data.")
        if getattr(slot, "player_game_data_offset", -1) < 0:
            raise StageError("Offset not tracked - cannot save changes.")

        for key, (var, limit, _label, _hint) in self._range_fields.items():
            if _range_error(var.get(), limit):
                self._on_range_change(key)
                raise StageError("Fix the values marked in red before applying.")
        if any(self._attr_error_labels[k].cget("text") for k in _ATTR_KEYS):
            raise StageError("Fix the attributes marked in red before applying.")

        try:
            runes = int(self.runes_var.get().strip())
        except ValueError:
            runes = -1
        if not 0 <= runes <= MAX_RUNES:
            raise StageError(
                f"Runes must be a whole number between 0 and {MAX_RUNES:,}."
            )

        # Silently correct level to match attributes
        calculated_level = (
            int(self.calculated_level_var.get())
            if self.calculated_level_var.get()
            else 0
        )
        self.level_var.set(str(calculated_level))

        stats = {}
        for key in sorted(_ATTR_KEYS):
            try:
                stats[key] = int(self.stat_vars[key].get().strip())
            except ValueError:
                self._on_attr_change(key)
                raise StageError(
                    f"{key.capitalize()} must be a whole number."
                ) from None
        level = int(self.level_var.get()) if self.level_var.get() else 0
        great_rune_on = bool(self.great_rune_on_var.get())
        mm_value = self._range_value("matchmaking")
        mm_min = self._matchmaking_min
        scadutree = self._range_value("scadutree")
        revered = self._range_value("revered_spirit_ash")
        memory_stones = self._range_value("memory_stones")
        rune_name = self.great_rune_id_var.get()
        rune_handle = next(
            (v for n, v in self._great_rune_options if n == rune_name), 0
        )
        recovered = self._recovered_runes
        last_grace = self._selected_last_grace(
            bool(getattr(save_file, "is_convergence", False))
        )

        def commit() -> list[str]:
            from io import BytesIO

            from er_save_manager.parser.slot_rebuild import rebuild_slot
            from er_save_manager.ui.editors.equipment_editor import (
                _find_equip_index,
            )

            notes: list[str] = []
            if isinstance(save_file._raw_data, bytes):
                save_file._raw_data = bytearray(save_file._raw_data)
            char = slot.player_game_data
            for key, value in stats.items():
                setattr(char, key, value)

            old_level = char.level
            char.level = level
            # Runes memory counts every rune ever gained, so added runes and
            # the cost of added levels raise it. It never drops below the
            # cost of all levels above the class start plus held runes.
            # Bloodstain runes were counted when first gained.
            runes_gained = max(0, runes - char.runes - recovered)
            if char.level > old_level:
                runes_gained += runes_to_reach_level(old_level, char.level)
            char.runes = runes
            start_level = get_class_data(
                char.archetype, getattr(save_file, "is_convergence", False)
            )["level"]
            floor = runes_to_reach_level(start_level, char.level) + runes
            char.runes_memory = min(
                MAX_RUNES_MEMORY,
                max(char.runes_memory + runes_gained, floor),
            )

            char.great_rune_on = great_rune_on

            # Matchmaking weapon level - clamp to inventory floor
            value = mm_value
            if value < mm_min:
                notes.append(
                    f"Matchmaking weapon level cannot be set below {mm_min} "
                    "(highest upgrade level found in inventory). It was raised "
                    f"to {mm_min}."
                )
                value = mm_min
            char.matchmaking_weapon_level = value

            char.scadutree_blessing = scadutree
            char.revered_spirit_ash_blessing = revered
            char.memory_stone_count = memory_stones

            # Write back to raw data using tracked offset
            char_bytes = BytesIO()
            char.write(char_bytes)
            char_data = char_bytes.getvalue()
            if len(char_data) != 432:  # PlayerGameData is exactly 432 bytes
                raise RuntimeError(
                    "PlayerGameData serialization error: expected 432 bytes, "
                    f"got {len(char_data)}"
                )
            abs_offset = slot.player_game_data_offset
            save_file._raw_data[abs_offset : abs_offset + len(char_data)] = char_data

            # Patch ProfileSummary level in USER_DATA_10
            # Layout: checksum(16) + version(4) + steam_id(8) + settings(0x140)
            #         + menu_system(0x1808) + active_profiles(10)
            #         + slot_idx * Profile(0x24C) + name(32) + terminator(2)
            if hasattr(save_file, "_user_data_10_offset"):
                import struct as _struct

                _ps_off = 0 if save_file.is_ps else 16
                _profile_summary_off = (
                    save_file._user_data_10_offset + _ps_off + 4 + 8 + 0x140 + 0x1808
                )
                _level_off = _profile_summary_off + 10 + slot_idx * 0x24C + 0x22
                save_file._raw_data[_level_off : _level_off + 4] = _struct.pack(
                    "<I", char.level
                )
                # Profile: level u32, seconds played u32, runes memory u32
                _memory_off = _level_off + 8
                save_file._raw_data[_memory_off : _memory_off + 4] = _struct.pack(
                    "<I", char.runes_memory
                )
                # Update parsed object to stay in sync
                summary = (
                    save_file.user_data_10_parsed.profile_summary
                    if save_file.user_data_10_parsed
                    else None
                )
                if summary and slot_idx < len(summary.profiles):
                    profile = summary.profiles[slot_idx]
                    profile.level = char.level
                    profile.runes_memory = char.runes_memory

            # Great rune ID and last grace require full slot rebuild
            # (both live outside PlayerGameData)
            rune_index = _find_equip_index(slot, rune_handle)
            if rune_handle and rune_index == 0xFFFFFFFF:
                notes.append(
                    f"{rune_name} is not in the held inventory, so it was not "
                    "equipped. The other changes are still saved."
                )
            else:
                slot.equipped_items.great_rune = rune_handle
                slot.equipped_items.great_rune_equip_index = rune_index

            stone_note = _sync_memory_stones(
                save_file, slot_idx, slot, char.memory_stone_count
            )
            if stone_note:
                notes.append(stone_note)

            if recovered:
                # Same state the game writes when the bloodstain is picked up
                slot.blood_stain.unk0x30 = -1
                slot.blood_stain.runes = -1

            slot.last_rested_grace = last_grace

            rebuilt = rebuild_slot(slot)
            save_file._raw_data[slot.data_start : slot.data_start + len(rebuilt)] = (
                rebuilt
            )
            self._recovered_runes = 0
            return notes

        return commit

    def _refresh_matchmaking_min(self, slot) -> None:
        """Recompute inventory floor and update the label."""
        from er_save_manager.editors.matchmaking_utils import get_max_weapon_upgrade

        self._matchmaking_min = get_max_weapon_upgrade(slot)
        if hasattr(self, "_mm_min_label") and self._mm_min_label:
            self._mm_min_label.configure(
                text=f"Min from inventory: {self._matchmaking_min}"
            )
