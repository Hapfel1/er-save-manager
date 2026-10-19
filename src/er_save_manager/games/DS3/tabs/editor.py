"""
DS3 Character Editor tab.

Sub-tabs: Stats | Identity | Equipment | Inventory.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.games.DS3 import catalog
from er_save_manager.games.DS3.character_ops import (
    _sync_dir_name_level,
    sync_dir_equipment,
)
from er_save_manager.games.DS3.slot import (
    ATTUNE_SLOTS,
    MAX_SOULS,
    MAX_STAT,
    NAME_MAX_CHARS,
)
from er_save_manager.games.DS3.tabs.equipment import DS3EquipAdapter
from er_save_manager.ui import palette
from er_save_manager.ui.editors.ds_equipment import AttunementSection, EquipmentPanel
from er_save_manager.ui.pending import FieldTracker, PendingPage, StageError, var_state
from er_save_manager.ui.utils import (
    bind_mousewheel,
    game_blocks_write,
    patch_combo_scroll,
)


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(parent, "darksoulsiii.exe", "Dark Souls III")


def _backup_and_save(ds3_save, save_path: Path, operation: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=operation, save=None)
    ds3_save.save_to_file(save_path)


class DS3EditorTab:
    def __init__(
        self,
        parent,
        get_save,
        get_save_path,
        show_toast,
        source_var=None,
        register_pending=None,
    ) -> None:
        self.parent = parent
        self._register_pending = register_pending
        self._get_save = get_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = -1
        self._stat_vars: dict[str, tk.StringVar] = {}
        self._name_var = tk.StringVar()
        self._ng_var = tk.StringVar(value="0")
        self._class_var = tk.StringVar()
        # Game data source (vanilla or a mod), shared with the Inventory tab;
        # it selects the class table.
        self._source_var = source_var or tk.StringVar(value=catalog.SOURCES["vanilla"])
        self._source_var.trace_add("write", lambda *_: self._on_source_change())
        # Source whose class table the Class box shows; lags the source
        # variable until _on_source_change has re-selected the class.
        self._class_source = self._source
        # False when the loaded stats sit below their own class's base
        # (modded or edited character); class minimums are then not enforced.
        self._enforce_class_min = True
        self._playtime_var = tk.StringVar(value="--")
        # Level and attribute sum as loaded, for a class index the source has
        # no row for: the level then moves by the change in the sum.
        self._loaded_level = 0
        self._loaded_sum = 0
        self.inventory = None
        self._stats_tracker = FieldTracker(self._stats_state)
        self._identity_tracker = FieldTracker(
            var_state({"name": self._name_var, "ng": self._ng_var})
        )

    def setup_ui(self) -> None:
        for _ in self.setup_steps():
            pass

    def setup_steps(self):
        """Build the UI in stages; each yield lets the window redraw and handle
        input between stages (gui.py resumes it one stage per turn)."""
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(
            header, text="Character Editor", font=("Segoe UI", 16, "bold")
        ).pack(side="left")
        ctk.CTkLabel(header, text="Game data:").pack(side="left", padx=(20, 6))
        ctk.CTkSegmentedButton(
            header, values=list(catalog.SOURCES.values()), variable=self._source_var
        ).pack(side="left")

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
        self._attunement = AttunementSection(ATTUNE_SLOTS)
        self._equip_panel = EquipmentPanel(
            tabs.add("Equipment"), self._attunement.build
        )
        self._attunement.attach(self._equip_panel)
        yield
        from er_save_manager.games.DS3.tabs.inventory import DS3InventoryTab

        self.inventory = DS3InventoryTab(
            tabs.add("Inventory"),
            get_save=self._get_save,
            get_save_path=self._get_save_path,
            show_toast=self._show_toast,
            source_var=self._source_var,
        )
        yield from self.inventory.setup_steps()
        # A save or character may have been loaded while the tab was building.
        self.inventory.load_slot(self._current_slot)
        self._register_pages()

    # --- Stats tab ----------------------------------------------------------- #

    def _build_stats_tab(self, parent) -> None:
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        bind_mousewheel(frame)

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", pady=5, padx=10)

        af = ctk.CTkFrame(top, fg_color="transparent")
        af.pack(side="left", fill="both", expand=True, padx=(0, 5))
        ctk.CTkLabel(af, text="Attributes", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=5, pady=(5, 0)
        )
        ag = ctk.CTkFrame(af, fg_color="transparent")
        ag.pack(fill="x", padx=5, pady=5)
        for i, (label, key) in enumerate(
            [
                ("Vigor", "vig"),
                ("Attunement", "atn"),
                ("Endurance", "end"),
                ("Vitality", "vit"),
                ("Strength", "str"),
                ("Dexterity", "dex"),
                ("Intelligence", "int"),
                ("Faith", "fth"),
                ("Luck", "lck"),
            ]
        ):
            ctk.CTkLabel(ag, text=f"{label}:").grid(
                row=i, column=0, sticky="w", padx=5, pady=5
            )
            var = tk.StringVar(value="10")
            self._stat_vars[key] = var
            ctk.CTkEntry(ag, textvariable=var, width=120).grid(
                row=i, column=1, padx=5, pady=5
            )

        rf = ctk.CTkFrame(top, fg_color="transparent")
        rf.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ctk.CTkLabel(rf, text="Resources", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=5, pady=(5, 0)
        )
        rg = ctk.CTkFrame(rf, fg_color="transparent")
        rg.pack(fill="x", padx=5, pady=5)
        for i, (label, key) in enumerate(
            [
                ("Level", "level"),
                ("Souls", "souls"),
                ("HP", "hp"),
                ("FP", "fp"),
                ("Stamina", "stamina"),
            ]
        ):
            ctk.CTkLabel(rg, text=f"{label}:").grid(
                row=i, column=0, sticky="w", padx=5, pady=5
            )
            var = tk.StringVar(value="0")
            self._stat_vars[key] = var
            # The game derives HP, FP and stamina from the attributes on load;
            # level follows from the class and the attributes.
            derived = key in ("level", "hp", "fp", "stamina")
            ctk.CTkEntry(
                rg,
                textvariable=var,
                width=120,
                state="disabled" if derived else "normal",
            ).grid(row=i, column=1, padx=5, pady=5)
        row = i + 1
        ctk.CTkLabel(rg, text="Class:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self._class_combo = ctk.CTkComboBox(
            rg,
            variable=self._class_var,
            values=[c.name for c in self._classes()],
            state="readonly",
            width=160,
            command=lambda _v: self._auto_recalc_level(),
        )
        self._class_combo.grid(row=row, column=1, padx=5, pady=5)
        patch_combo_scroll(self._class_combo)
        self._class_note = ctk.CTkLabel(
            frame,
            text="",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
            wraplength=520,
            justify="left",
        )
        self._class_note.pack(anchor="w", padx=15)

    # --- Identity tab -------------------------------------------------------- #

    def _build_identity_tab(self, parent) -> None:
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        bind_mousewheel(frame)

        cf = ctk.CTkFrame(frame, fg_color="transparent")
        cf.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(cf, text="Character identity", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0)
        )
        ctk.CTkLabel(cf, text="Name:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ctk.CTkEntry(cf, textvariable=self._name_var, width=200).grid(
            row=1, column=1, padx=5, pady=5, sticky="w"
        )
        ctk.CTkLabel(cf, text="NG+:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        ctk.CTkComboBox(
            cf,
            variable=self._ng_var,
            values=[str(i) for i in range(8)],
            state="readonly",
            width=200,
        ).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(
            frame,
            text="Name supports up to 16 characters.",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=15, pady=(4, 0))

    # --- Refresh ------------------------------------------------------------- #

    def refresh(self) -> None:
        # A new save: the loaded character belongs to the old one.
        self.load_slot(-1)

    def load_slot(self, slot_idx: int) -> None:
        """Show the character in slot_idx; -1 or an empty slot clears the tab."""
        save = self._get_save()
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

    def _clear(self) -> None:
        self._stats_tracker.clear()
        self._identity_tracker.clear()
        for var in self._stat_vars.values():
            var.set("")
        self._name_var.set("")
        self._ng_var.set("0")
        self._class_var.set("")
        if hasattr(self, "_class_note"):
            self._class_note.configure(text="")
        self._load_equipment()

    def _populate(self, slot_idx: int) -> None:
        save = self._get_save()
        if save is None:
            return
        char = save.characters[slot_idx]
        if char is None:
            return
        self._fill_stats(char)
        self._fill_identity(char)
        self._load_equipment()

    def _fill_stats(self, char) -> None:
        # Remove traces before writing to avoid premature recalc
        for key in catalog.STAT_KEYS:
            for tid in self._stat_vars[key].trace_info():
                self._stat_vars[key].trace_remove(tid[0], tid[1])

        for key in catalog.STAT_KEYS:
            self._stat_vars[key].set(str(char.get_stat(key)))
        self._stat_vars["level"].set(str(char.level))
        self._loaded_level = char.level
        self._loaded_sum = sum(char.get_stat(k) for k in catalog.STAT_KEYS)

        # Bind traces so any stat change auto-updates the level field
        for key in catalog.STAT_KEYS:
            self._stat_vars[key].trace_add(
                "write", lambda *_: self._auto_recalc_level()
            )
        self._stat_vars["souls"].set(str(char.souls))
        self._stat_vars["hp"].set(str(char.hp))
        self._stat_vars["fp"].set(str(char.fp))
        self._stat_vars["stamina"].set(str(char.stamina))
        self._show_loaded_class()
        self._stats_tracker.mark_clean()

    def _fill_identity(self, char) -> None:
        self._name_var.set(char.name)
        self._ng_var.set("0" if char.layout_error else str(char.ng_plus))
        self._identity_tracker.mark_clean()

    def _stats_state(self) -> dict:
        state = var_state(
            {k: self._stat_vars[k] for k in (*catalog.STAT_KEYS, "souls")}
        )()
        # By index: a game data switch shows another name for the same class.
        name = self._class_var.get()
        state["class"] = next(
            (
                i
                for i, c in enumerate(catalog.starting_classes(self._class_source))
                if c.name == name
            ),
            None,
        )
        return state

    # --- Equipment ----------------------------------------------------------- #

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
        char = self._loaded_char()
        if char is None:
            panel.load(None)
            return
        error = char.layout_error or char.inventory_error
        if error:
            panel.load(None, f"Equipment cannot be edited: {error}")
            return
        panel.load(DS3EquipAdapter(char, self._source))

    def _equipment_changes(self) -> int:
        panel = getattr(self, "_equip_panel", None)
        if panel is None or panel.adapter is None:
            return 0
        return len(panel.staged) + (1 if self._attunement.changed() else 0)

    def _prepare_equipment(self):
        adapter = self._equip_panel.adapter
        staged = self._equip_panel.staged
        save, slot = self._get_save(), self._current_slot
        if adapter is None or save is None:
            raise StageError("No character loaded.")

        def commit() -> None:
            adapter.apply(staged)
            sync_dir_equipment(save, slot)

        return commit

    # --- Class and level ----------------------------------------------------- #

    @property
    def _source(self) -> str:
        label = self._source_var.get()
        return next(k for k, v in catalog.SOURCES.items() if v == label)

    def _classes(self) -> list[catalog.StartingClass]:
        return catalog.starting_classes(self._source)

    def _selected_class(self) -> catalog.StartingClass | None:
        name = self._class_var.get()
        return next((c for c in self._classes() if c.name == name), None)

    def _loaded_char(self):
        save = self._get_save()
        if save is None or self._current_slot < 0:
            return None
        return save.characters[self._current_slot]

    def _on_source_change(self) -> None:
        self._load_equipment()
        if not hasattr(self, "_class_combo"):
            self._class_source = self._source
            return
        self._class_combo.configure(values=[c.name for c in self._classes()])
        clean = self._stats_tracker.changes() == 0
        self._show_loaded_class()
        self._class_source = self._source
        # The class and level from the other class table are no edit, as on load
        if clean:
            self._stats_tracker.mark_clean()

    def _show_loaded_class(self) -> None:
        """Select the loaded character's class in the current source's table,
        explain any mismatch, and derive the level."""
        char = self._loaded_char()
        if char is None:
            return
        classes = self._classes()
        index = char.starting_class
        notes = []
        if index < len(classes):
            cls = classes[index]
            self._class_var.set(cls.name)
            self._enforce_class_min = all(
                char.get_stat(k) >= v for k, v in cls.stats.items()
            )
            if not self._enforce_class_min:
                notes.append(
                    "Stats are below this class's starting values (wrong game "
                    "data or an edited character), so class minimums are not "
                    "enforced."
                )
            derived = cls.level_for({k: char.get_stat(k) for k in catalog.STAT_KEYS})
            if derived != char.level:
                notes.append(
                    f"The stored level {char.level} does not match the class and "
                    "attributes (wrong game data or an edited level). Apply "
                    f"All writes level {derived}."
                )
        else:
            self._class_var.set("")
            self._enforce_class_min = False
            notes.append(
                f"The character's class (index {index}) is not a "
                f"{self._source_var.get()} class. "
                "Select the game data the character was made with."
            )
        self._class_note.configure(text="\n".join(notes))
        self._auto_recalc_level()

    def _derived_level(self, stats: dict[str, int]) -> int:
        """Class level plus the attribute points above the class base; without
        a class, the loaded level moved by the change in the attribute sum."""
        cls = self._selected_class()
        if cls is not None:
            return cls.level_for(stats)
        return self._loaded_level + sum(stats.values()) - self._loaded_sum

    def _auto_recalc_level(self) -> None:
        try:
            stats = {k: int(self._stat_vars[k].get()) for k in catalog.STAT_KEYS}
        except ValueError:
            return  # user mid-typing, skip
        self._stat_vars["level"].set(str(self._derived_level(stats)))

    # --- Pending changes ----------------------------------------------------- #

    def _register_pages(self) -> None:
        if self._register_pending is None:
            return

        def page(name, changes, prepare, discard):
            return PendingPage(
                name, changes, prepare, discard, lambda: self._tabs.set(name)
            )

        self._register_pending(
            page(
                "Stats",
                self._stats_tracker.changes,
                self._prepare_stats,
                lambda: self._refill(self._fill_stats),
            )
        )
        self._register_pending(
            page(
                "Identity",
                self._identity_tracker.changes,
                self._prepare_identity,
                lambda: self._refill(self._fill_identity),
            )
        )
        self._register_pending(
            page(
                "Equipment",
                self._equipment_changes,
                self._prepare_equipment,
                self._load_equipment,
            )
        )

    def _refill(self, fill) -> None:
        char = self._loaded_char()
        if char is not None:
            fill(char)

    def _prepare_stats(self):
        save, char = self._get_save(), self._loaded_char()
        if char is None:
            raise StageError("No character loaded.")
        slot = self._current_slot
        cls = self._selected_class()
        class_idx = self._classes().index(cls) if cls is not None else None
        try:
            stats = {key: int(self._stat_vars[key].get()) for key in catalog.STAT_KEYS}
            souls = int(self._stat_vars["souls"].get())
        except ValueError:
            raise StageError("Stats and souls must be numbers.") from None
        level = self._derived_level(stats)
        problems = [
            f"{key.upper()} above {MAX_STAT}"
            for key, v in stats.items()
            if v > MAX_STAT
        ]
        if cls is not None and self._enforce_class_min:
            problems += [
                f"{key.upper()} below the {cls.name} minimum of {cls.stats[key]}"
                for key, v in stats.items()
                if v < cls.stats[key]
            ]
        else:
            problems += [f"{key.upper()} below 1" for key, v in stats.items() if v < 1]
        if level < 1:
            problems.append(f"Level must be at least 1 (got {level})")
        if not 0 <= souls <= MAX_SOULS:
            problems.append(f"Souls must be 0-{MAX_SOULS:,}")
        if problems:
            raise StageError("\n".join(problems))

        def commit() -> None:
            for key, v in stats.items():
                char.set_stat(key, v)
            char.level = level
            char.souls = souls
            if class_idx is not None:
                char.starting_class = class_idx
            # The load screen reads name and level from its own directory copy.
            _sync_dir_name_level(save, slot, char.name, char.level)

        return commit

    def _prepare_identity(self):
        save, char = self._get_save(), self._loaded_char()
        if char is None:
            raise StageError("No character loaded.")
        slot = self._current_slot
        name = self._name_var.get()
        if len(name) > NAME_MAX_CHARS:
            raise StageError(f"The name can be at most {NAME_MAX_CHARS} characters.")
        ng = int(self._ng_var.get())
        if ng != char.ng_plus and char.layout_error:
            raise StageError(f"NG+ cannot be changed: {char.layout_error}")

        def commit() -> None:
            char.name = name
            if ng != char.ng_plus:
                char.ng_plus = ng
            _sync_dir_name_level(save, slot, char.name, char.level)

        return commit
