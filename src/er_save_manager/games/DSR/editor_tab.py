"""
DSR Character Editor tab.

Sub-tabs: Stats | Identity | Covenants | Equipment | Inventory.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.games.DSR.character_ops import (
    _sync_dir_name_level,
    sync_dir_equipment,
)
from er_save_manager.games.DSR.equipment_tab import DSREquipAdapter, equip_slots
from er_save_manager.games.DSR.save import (
    ATTUNE_SLOTS,
    COVENANT_OFFERING_ORDER,
    COVENANT_RANK_COUNTS,
    MAX_COVENANT_OFFERINGS,
    MAX_HUMANITY,
    MAX_SOULS,
    MAX_STAT,
    NAME_MAX_CHARS,
    STAT_KEYS,
    DSRCovenant,
    calc_level_from_stats,
    class_base_stats,
    covenant_rank,
)
from er_save_manager.ui import palette
from er_save_manager.ui.editors.ds_equipment import AttunementSection, EquipmentPanel
from er_save_manager.ui.pending import FieldTracker, PendingPage, StageError, var_state
from er_save_manager.ui.utils import bind_mousewheel, game_blocks_write
from er_save_manager.validation.names import name_problem
from er_save_manager.validation.numbers import parse_whole


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(
        parent, "darksoulsremastered.exe", "Dark Souls: Remastered"
    )


if TYPE_CHECKING:
    pass

_CLASSES = [
    "Warrior",
    "Knight",
    "Wanderer",
    "Thief",
    "Bandit",
    "Hunter",
    "Sorcerer",
    "Pyromancer",
    "Cleric",
    "Deprived",
]
_COVENANTS = [
    "None",
    "Way of White",
    "Princess Guard",
    "Warrior of Sunlight",
    "Darkwraith",
    "Path of the Dragon",
    "Gravelord Servant",
    "Forest Hunter",
    "Darkmoon Blade",
    "Chaos Servant",
]


def _backup_and_save(dsr_save, save_path: Path, operation: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=operation, save=None)
    dsr_save.save_to_file(save_path)


class DSREditorTab:
    def __init__(
        self, parent, get_dsr_save, get_save_path, show_toast, register_pending=None
    ) -> None:
        self.parent = parent
        self._register_pending = register_pending
        self._get_dsr_save = get_dsr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = -1
        self._stat_vars: dict[str, tk.StringVar] = {}
        self._name_var = tk.StringVar()
        self._class_var = tk.StringVar(value=_CLASSES[0])
        self._covenant_var = tk.StringVar(value=_COVENANTS[0])
        self._playtime_var = tk.StringVar(value="--")
        self._offering_vars = {c: tk.StringVar() for c in COVENANT_OFFERING_ORDER}
        self.inventory = None
        self._rank_vars = {c: tk.StringVar() for c in COVENANT_OFFERING_ORDER}
        # Starting class index at last load; used for level recalc
        self._loaded_class_idx: int = 0
        # False when the loaded stats sit below their own class's base
        # (modded or edited character); class minimums are then not enforced.
        self._enforce_class_min = True
        # Stat key -> label, filled while the Stats page is built
        self._stat_labels: dict[str, str] = {}
        self._stats_tracker = FieldTracker(self._stats_state, self._stat_labels)
        self._identity_tracker = FieldTracker(
            var_state(
                {
                    "name": self._name_var,
                    "class": self._class_var,
                    "covenant": self._covenant_var,
                }
            ),
        )
        self._covenant_tracker = FieldTracker(
            var_state(self._offering_vars),
            {c: f"{_COVENANTS[int(c)]} offerings" for c in COVENANT_OFFERING_ORDER},
        )

    def setup_ui(self) -> None:
        for _ in self.setup_steps():
            pass

    def setup_steps(self):
        """Build the UI in stages; each yield lets the window redraw and handle
        input between stages (gui.py resumes it one stage per turn)."""
        # Outer wrapper fills parent - fixes content being pushed down on CTkTabview frames
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(header, text="Character Editor", font=("Inter", 16, "bold")).pack(
            side="left"
        )

        tabs = ctk.CTkTabview(
            outer,
            command=self._on_subtab,
            fg_color=("gray90", "gray20"),
            segmented_button_fg_color=("gray80", "gray35"),
            segmented_button_selected_color=palette.PURPLE,
            segmented_button_unselected_color=("gray70", "gray30"),
        )
        tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._tabs = tabs
        self._build_stats_tab(tabs.add("Stats"))
        yield
        self._build_identity_tab(tabs.add("Identity"))
        yield
        self._build_covenants_tab(tabs.add("Covenants"))
        yield
        self._attunement = AttunementSection(ATTUNE_SLOTS)
        self._equip_panel = EquipmentPanel(
            tabs.add("Equipment"), self._attunement.build
        )
        self._attunement.attach(self._equip_panel)
        yield
        yield from self._equip_panel.prebuild(equip_slots())
        from er_save_manager.games.DSR.inventory_tab import DSRInventoryTab

        self.inventory = DSRInventoryTab(
            tabs.add("Inventory"),
            get_dsr_save=self._get_dsr_save,
            get_save_path=self._get_save_path,
            show_toast=self._show_toast,
        )
        self.inventory.setup_ui()
        # A save or character may have been loaded while the tab was building.
        self.inventory.load_slot(self._current_slot)
        self._register_pages()

    # --- Stats tab ------------------------------------------------------------ #

    def _build_stats_tab(self, parent) -> None:
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        bind_mousewheel(frame)

        top_row = ctk.CTkFrame(frame, fg_color="transparent")
        top_row.pack(fill="x", pady=5, padx=10)

        af = ctk.CTkFrame(top_row, fg_color="transparent")
        af.pack(side="left", fill="both", expand=True, padx=(0, 5))
        ctk.CTkLabel(af, text="Attributes", font=("Inter", 12, "bold")).pack(
            anchor="w", padx=5, pady=(5, 0)
        )
        ag = ctk.CTkFrame(af, fg_color="transparent")
        ag.pack(fill="x", padx=5, pady=5)
        for i, (label, key) in enumerate(
            [
                ("Vitality", "vit"),
                ("Attunement", "atn"),
                ("Endurance", "end"),
                ("Strength", "str"),
                ("Dexterity", "dex"),
                ("Intelligence", "int"),
                ("Faith", "fth"),
                ("Resistance", "res"),
            ]
        ):
            self._stat_labels[key] = label
            ctk.CTkLabel(ag, text=f"{label}:").grid(
                row=i, column=0, sticky="w", padx=5, pady=5
            )
            var = tk.StringVar(value="1")
            self._stat_vars[key] = var
            var.trace_add("write", lambda *_: self._recalc_level())
            ctk.CTkEntry(ag, textvariable=var, width=120).grid(
                row=i, column=1, padx=5, pady=5
            )

        rf = ctk.CTkFrame(top_row, fg_color="transparent")
        rf.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ctk.CTkLabel(rf, text="Resources", font=("Inter", 12, "bold")).pack(
            anchor="w", padx=5, pady=(5, 0)
        )
        rg = ctk.CTkFrame(rf, fg_color="transparent")
        rg.pack(fill="x", padx=5, pady=5)
        for i, (label, key) in enumerate(
            [
                ("Level", "level"),
                ("Souls", "souls"),
                ("Humanity", "humanity"),
            ]
        ):
            self._stat_labels[key] = label
            ctk.CTkLabel(rg, text=f"{label}:").grid(
                row=i, column=0, sticky="w", padx=5, pady=5
            )
            var = tk.StringVar(value="0")
            self._stat_vars[key] = var
            # Level follows from the stats and the starting class.
            ctk.CTkEntry(
                rg,
                textvariable=var,
                width=120,
                state="disabled" if key == "level" else "normal",
            ).grid(row=i, column=1, padx=5, pady=5)

        self._class_note = ctk.CTkLabel(
            frame,
            text="",
            font=("Inter", 10),
            text_color=("gray40", "gray70"),
            wraplength=520,
            justify="left",
        )
        self._class_note.pack(anchor="w", padx=15)
        ctk.CTkLabel(
            frame,
            text="Saving VIT updates derived max HP. Saving END updates max Stamina. Level is recalculated from stats automatically.",
            font=("Inter", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=15, pady=(4, 0))

    # --- Identity tab --------------------------------------------------------- #

    def _build_identity_tab(self, parent) -> None:
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        bind_mousewheel(frame)

        cf = ctk.CTkFrame(frame, fg_color="transparent")
        cf.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(cf, text="Character identity", font=("Inter", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0)
        )

        rows = [
            ("Name:", self._name_var, "entry", None),
            ("Class:", self._class_var, "combo", _CLASSES),
            ("Covenant:", self._covenant_var, "combo", _COVENANTS),
        ]
        for i, (label, var, kind, values) in enumerate(rows, start=1):
            ctk.CTkLabel(cf, text=label).grid(
                row=i, column=0, sticky="w", padx=5, pady=5
            )
            if kind == "entry":
                ctk.CTkEntry(cf, textvariable=var, width=200).grid(
                    row=i, column=1, padx=5, pady=5, sticky="w"
                )
            else:
                ctk.CTkComboBox(
                    cf,
                    values=values,
                    variable=var,
                    state="readonly",
                    width=200,
                ).grid(row=i, column=1, padx=5, pady=5, sticky="w")

        # Play time read-only
        ctk.CTkLabel(cf, text="Play time:").grid(
            row=len(rows) + 1, column=0, sticky="w", padx=5, pady=5
        )
        ctk.CTkLabel(cf, textvariable=self._playtime_var).grid(
            row=len(rows) + 1, column=1, sticky="w", padx=5, pady=5
        )

        ctk.CTkLabel(
            frame,
            text=f"Name supports up to {NAME_MAX_CHARS} characters. Both name copies "
            "in the save are updated. NG+ is set on the World State tab.",
            font=("Inter", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=15, pady=(4, 0))

    # --- Covenants tab ------------------------------------------------------- #

    def _build_covenants_tab(self, parent) -> None:
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        bind_mousewheel(frame)

        cf = ctk.CTkFrame(frame, fg_color="transparent")
        cf.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(cf, text="Covenant offerings", font=("Inter", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=5, pady=(5, 0)
        )
        # Whole numbers only, up to the u8 the save stores.
        vcmd = cf.register(
            lambda text: text == ""
            or (text.isdigit() and int(text) <= MAX_COVENANT_OFFERINGS)
        )
        for i, cov in enumerate(COVENANT_OFFERING_ORDER, start=1):
            ctk.CTkLabel(cf, text=f"{_COVENANTS[int(cov)]}:").grid(
                row=i, column=0, sticky="w", padx=5, pady=5
            )
            var = self._offering_vars[cov]
            ctk.CTkEntry(
                cf,
                textvariable=var,
                width=90,
                validate="key",
                validatecommand=(vcmd, "%P"),
            ).grid(row=i, column=1, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(
                cf, textvariable=self._rank_vars[cov], width=80, anchor="w"
            ).grid(row=i, column=2, sticky="w", padx=5, pady=5)
            var.trace_add("write", lambda *_, c=cov: self._update_rank(c))

        *first, last = COVENANT_RANK_COUNTS
        need = f"{', '.join(str(n) for n in first)} and {last}"
        ctk.CTkLabel(
            frame,
            text=f"Ranks 1, 2 and 3 are reached at {need} offerings. Forest Hunter "
            "counts offerings but has no ranks. Counts go from 0 to "
            f"{MAX_COVENANT_OFFERINGS}. Rank rewards are not added.",
            font=("Inter", 10),
            text_color=("gray40", "gray70"),
            justify="left",
            wraplength=520,
        ).pack(anchor="w", padx=15, pady=(4, 0))

    def _update_rank(self, cov: DSRCovenant) -> None:
        try:
            count = int(self._offering_vars[cov].get())
        except ValueError:
            self._rank_vars[cov].set("")
            return
        if cov == DSRCovenant.ForestHunter:
            self._rank_vars[cov].set("No ranks")
        else:
            self._rank_vars[cov].set(f"Rank {covenant_rank(count)}")

    def _prepare_covenants(self):
        char = self._loaded_char()
        if char is None:
            raise StageError("No character loaded.")
        try:
            counts = {c: int(v.get()) for c, v in self._offering_vars.items()}
        except ValueError:
            counts = {}
        if len(counts) != len(COVENANT_OFFERING_ORDER) or not all(
            0 <= n <= MAX_COVENANT_OFFERINGS for n in counts.values()
        ):
            raise StageError(
                "Offering counts must be whole numbers from 0 to "
                f"{MAX_COVENANT_OFFERINGS}."
            )

        def commit() -> None:
            for cov, count in counts.items():
                char.set_covenant_offerings(cov, count)

        return commit

    # --- Refresh / load ------------------------------------------------------- #

    def refresh(self) -> None:
        # A new save: the loaded character belongs to the old one.
        self.load_slot(-1)

    def load_slot(self, slot_idx: int) -> None:
        """Show the character in slot_idx; -1 or an empty slot clears the tab."""
        save = self._get_dsr_save()
        if self.inventory is not None:
            self.inventory.load_slot(slot_idx)
        if (
            save is None
            or not 0 <= slot_idx < len(save.characters)
            or save.characters[slot_idx] is None
        ):
            self._current_slot = -1
            self._clear()
            return
        self._current_slot = slot_idx
        self._populate(slot_idx)

    def _loaded_char(self):
        save = self._get_dsr_save()
        if save is None or self._current_slot < 0:
            return None
        return save.characters[self._current_slot]

    def _clear(self) -> None:
        for tracker in (
            self._stats_tracker,
            self._identity_tracker,
            self._covenant_tracker,
        ):
            tracker.clear()
        for var in (*self._stat_vars.values(), *self._offering_vars.values()):
            var.set("")
        self._name_var.set("")
        self._playtime_var.set("--")
        if hasattr(self, "_class_note"):
            self._class_note.configure(text="")
        self._load_equipment()

    def _populate(self, slot_idx: int) -> None:
        save = self._get_dsr_save()
        if save is None:
            return
        char = save.characters[slot_idx]
        if char is None:
            return
        self._fill_stats(char)
        self._fill_identity(char)
        self._fill_covenants(char)
        h = int(char.play_seconds // 3600)
        m = int((char.play_seconds % 3600) // 60)
        s = int(char.play_seconds % 60)
        self._playtime_var.set(f"{h}h {m:02d}m {s:02d}s")
        self._load_equipment()

    def _fill_stats(self, char) -> None:
        self._loaded_class_idx = int(char.player_class)
        for key in ("vit", "atn", "end", "str", "dex", "int", "fth", "res"):
            self._stat_vars[key].set(str(char.get_stat(key)))
        base = class_base_stats(self._loaded_class_idx)
        self._enforce_class_min = base is not None and all(
            char.get_stat(k) >= v for k, v in base.items()
        )
        self._class_note.configure(
            text=""
            if self._enforce_class_min
            else "Stats are below this class's starting values (modded or edited "
            "character), so class minimums are not enforced."
        )
        self._stat_vars["level"].set(str(char.level))
        self._stat_vars["souls"].set(str(char.souls))
        self._stat_vars["humanity"].set(str(char.humanity))
        self._stats_tracker.mark_clean()

    def _fill_identity(self, char) -> None:
        self._name_var.set(char.name)
        cls = int(char.player_class)
        self._class_var.set(_CLASSES[cls] if cls < len(_CLASSES) else str(cls))
        cov = int(char.covenant)
        self._covenant_var.set(_COVENANTS[cov] if cov < len(_COVENANTS) else str(cov))
        self._identity_tracker.mark_clean()

    def _fill_covenants(self, char) -> None:
        for cov, var in self._offering_vars.items():
            var.set(str(char.covenant_offerings(cov)))
        self._covenant_tracker.mark_clean()

    def _stats_state(self) -> dict:
        return var_state({k: v for k, v in self._stat_vars.items() if k != "level"})()

    def _refill(self, fill) -> None:
        char = self._loaded_char()
        if char is not None:
            fill(char)

    def _register_pages(self) -> None:
        if self._register_pending is None:
            return
        for name, tracker, prepare, fill in (
            ("Stats", self._stats_tracker, self._prepare_stats, self._fill_stats),
            (
                "Identity",
                self._identity_tracker,
                self._prepare_identity,
                self._fill_identity,
            ),
            (
                "Covenants",
                self._covenant_tracker,
                self._prepare_covenants,
                self._fill_covenants,
            ),
        ):
            self._register_pending(
                PendingPage(
                    name,
                    tracker.changes,
                    prepare,
                    lambda f=fill: self._refill(f),
                    lambda n=name: self._tabs.set(n),
                    tracker.details,
                )
            )
        self._register_pending(
            PendingPage(
                "Equipment",
                self._equipment_changes,
                self._prepare_equipment,
                self._load_equipment,
                lambda: self._tabs.set("Equipment"),
                self._equipment_details,
            )
        )

    # --- Equipment ------------------------------------------------------------ #

    def select(self, name: str) -> None:
        """Show the sub-tab called name."""
        self._tabs.set(name)
        self._on_subtab()

    def _on_subtab(self) -> None:
        # Inventory edits change what the equipment pickers offer.
        panel = getattr(self, "_equip_panel", None)
        if (
            self._tabs.get() == "Equipment"
            and panel is not None
            and not panel.staged
            and not self._attunement.changed()
        ):
            self._load_equipment()

    def _load_equipment(self) -> None:
        panel = getattr(self, "_equip_panel", None)
        if panel is None:
            return
        save = self._get_dsr_save()
        char = (
            save.characters[self._current_slot]
            if save is not None and self._current_slot >= 0
            else None
        )
        panel.load(DSREquipAdapter(char) if char is not None else None)

    def _equipment_changes(self) -> int:
        panel = getattr(self, "_equip_panel", None)
        if panel is None or panel.adapter is None:
            return 0
        return len(panel.staged) + (1 if self._attunement.changed() else 0)

    def _equipment_details(self):
        panel = getattr(self, "_equip_panel", None)
        if panel is None or panel.adapter is None:
            return []
        return panel.details() + self._attunement.details()

    def _prepare_equipment(self):
        adapter = self._equip_panel.adapter
        staged = self._equip_panel.staged
        save, slot = self._get_dsr_save(), self._current_slot
        if adapter is None or save is None:
            raise StageError("No character loaded.")
        try:
            adapter.check(staged)
        except ValueError as exc:
            raise StageError(str(exc)) from None

        def commit() -> None:
            adapter.apply(staged)
            sync_dir_equipment(save, slot)

        return commit

    def _recalc_level(self) -> None:
        """Level from the current stat inputs, "-" while one is not a stat
        value."""
        try:
            stats = [parse_whole(self._stat_vars[key].get()) for key in STAT_KEYS]
        except ValueError:
            stats = []
        if not stats or not all(1 <= v <= MAX_STAT for v in stats):
            self._stat_vars["level"].set("-")
            return
        lvl = calc_level_from_stats(self._loaded_class_idx, *stats)
        self._stat_vars["level"].set(str(max(1, lvl)))

    def _whole(self, key: str) -> int:
        try:
            return parse_whole(self._stat_vars[key].get())
        except ValueError:
            raise StageError(
                f"{self._stat_labels[key]} must be a whole number."
            ) from None

    # --- Apply ---------------------------------------------------------------- #

    def _prepare_stats(self):
        save, char = self._get_dsr_save(), self._loaded_char()
        if char is None:
            raise StageError("No character loaded.")
        slot = self._current_slot
        class_idx = self._loaded_class_idx
        stats = {key: self._whole(key) for key in STAT_KEYS}
        souls = self._whole("souls")
        humanity = self._whole("humanity")
        problems = self._stat_problems(stats, class_idx)
        if not 0 <= souls <= MAX_SOULS:
            problems.append(f"Souls must be 0-{MAX_SOULS:,}")
        if not 0 <= humanity <= MAX_HUMANITY:
            problems.append(f"Humanity must be 0-{MAX_HUMANITY}")
        if problems:
            raise StageError("\n".join(problems))

        def commit() -> None:
            for key, value in stats.items():
                char.set_stat(key, value, update_derived=True)
            char.level = max(1, calc_level_from_stats(class_idx, *stats.values()))
            char.souls = souls
            char.humanity = humanity
            # The load screen reads name and level from its own directory copy.
            _sync_dir_name_level(save, slot, char.name, char.level)

        return commit

    def _prepare_identity(self):
        save, char = self._get_dsr_save(), self._loaded_char()
        if char is None:
            raise StageError("No character loaded.")
        slot = self._current_slot
        name = self._name_var.get().strip(" ")
        problem = name_problem(name, NAME_MAX_CHARS)
        if problem:
            raise StageError(problem)
        new_class = (
            _CLASSES.index(self._class_var.get())
            if self._class_var.get() in _CLASSES
            else int(char.player_class)
        )
        # The Stats page's values, which Apply All writes first.
        try:
            stats = {key: parse_whole(self._stat_vars[key].get()) for key in STAT_KEYS}
        except ValueError:
            stats = {key: char.get_stat(key) for key in STAT_KEYS}
        problems = self._stat_problems(stats, new_class)
        if problems:
            raise StageError(
                f"The stats do not fit {_CLASSES[new_class]}:\n" + "\n".join(problems)
            )
        try:
            covenant = type(char.covenant)(_COVENANTS.index(self._covenant_var.get()))
        except ValueError as exc:
            raise StageError(str(exc)) from None

        def commit() -> None:
            char.name = name
            if new_class != int(char.player_class):
                char.player_class = type(char.player_class)(new_class)
                # Level counts from the class's own starting level and stats.
                now = [char.get_stat(key) for key in STAT_KEYS]
                char.level = max(1, calc_level_from_stats(new_class, *now))
            char.covenant = covenant
            _sync_dir_name_level(save, slot, char.name, char.level)

        return commit

    def _stat_problems(self, stats: dict[str, int], class_idx: int) -> list[str]:
        """Stats above the cap or below the class's starting values."""
        problems = [
            f"{self._stat_labels[key]} above {MAX_STAT}"
            for key, value in stats.items()
            if value > MAX_STAT
        ]
        base = class_base_stats(class_idx)
        if self._enforce_class_min and base is not None:
            problems += [
                f"{self._stat_labels[key]} below the class minimum of {base[key]}"
                for key, value in stats.items()
                if value < base[key]
            ]
        else:
            problems += [
                f"{self._stat_labels[key]} below 1"
                for key, value in stats.items()
                if value < 1
            ]
        return problems
