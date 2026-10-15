"""
DS3 Character Editor tab.

Sub-tabs: Stats | Identity.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.games.DS3 import catalog
from er_save_manager.games.DS3.character_ops import _sync_dir_name_level
from er_save_manager.games.DS3.slot import (
    MAX_SOULS,
    MAX_STAT,
    NAME_MAX_CHARS,
    LayoutError,
)
from er_save_manager.ui import palette
from er_save_manager.ui.messagebox import CTkMessageBox
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
        self, parent, get_save, get_save_path, show_toast, source_var=None
    ) -> None:
        self.parent = parent
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
        # False when the loaded stats sit below their own class's base
        # (modded or edited character); class minimums are then not enforced.
        self._enforce_class_min = True
        self._playtime_var = tk.StringVar(value="--")
        # Level and attribute sum as loaded, for a class index the source has
        # no row for: the level then moves by the change in the sum.
        self._loaded_level = 0
        self._loaded_sum = 0

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
        ctk.CTkButton(
            header, text="Load Character", command=self._load_selected, width=130
        ).pack(side="right", padx=(6, 0))
        self._slot_var = tk.StringVar()
        self._slot_combo = ctk.CTkComboBox(
            header,
            variable=self._slot_var,
            values=[],
            state="readonly",
            width=240,
        )
        self._slot_combo.pack(side="right")
        ctk.CTkLabel(header, text="Slot:").pack(side="right", padx=(0, 6))

        tabs = ctk.CTkTabview(
            outer,
            fg_color=("gray90", "gray20"),
            segmented_button_fg_color=("gray80", "gray35"),
            segmented_button_selected_color=palette.PURPLE,
            segmented_button_unselected_color=("gray70", "gray30"),
        )
        tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._build_stats_tab(tabs.add("Stats"))
        yield
        self._build_identity_tab(tabs.add("Identity"))

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

        ctk.CTkButton(
            frame, text="Apply Changes", command=self._apply_stats, width=200
        ).pack(pady=16)

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
        ctk.CTkButton(
            frame, text="Apply Changes", command=self._apply_identity, width=200
        ).pack(pady=16)

    # --- Refresh ------------------------------------------------------------- #

    def refresh(self) -> None:
        save = self._get_save()
        if save is None:
            self._slot_combo.configure(values=[])
            return
        options = [
            f"Slot {i + 1} - {c.name}" if c else f"Slot {i + 1} - Empty"
            for i, c in enumerate(save.characters)
        ]
        self._slot_combo.configure(values=options)
        self._slot_var.set(options[0] if options else "")

    def load_slot(self, slot_idx: int) -> None:
        options = self._slot_combo.cget("values")
        if options and slot_idx < len(options):
            self._slot_var.set(options[slot_idx])
        self._current_slot = slot_idx
        self._populate(slot_idx)

    def _load_selected(self) -> None:
        idx = self._slot_idx()
        if idx < 0:
            return
        save = self._get_save()
        if save is None or save.characters[idx] is None:
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {idx + 1} is empty.", parent=self.parent
            )
            return
        self._current_slot = idx
        self._populate(idx)

    def _populate(self, slot_idx: int) -> None:
        save = self._get_save()
        if save is None:
            return
        char = save.characters[slot_idx]
        if char is None:
            return
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
        self._name_var.set(char.name)
        self._ng_var.set("0" if char.layout_error else str(char.ng_plus))
        self._show_loaded_class()

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
        if not hasattr(self, "_class_combo"):
            return
        self._class_combo.configure(values=[c.name for c in self._classes()])
        self._show_loaded_class()

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
                    f"Changes writes level {derived}."
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

    # --- Apply --------------------------------------------------------------- #

    def _apply_stats(self) -> None:
        if _game_blocks_write(self.parent):
            return

        if self._current_slot < 0:
            CTkMessageBox.showwarning(
                "No Character", "Load a character first.", parent=self.parent
            )
            return
        save = self._get_save()
        save_path = self._get_save_path()
        if save is None or save_path is None:
            return
        if not CTkMessageBox.askyesno(
            "Apply Stats",
            f"Apply stat changes to Slot {self._current_slot + 1}?\n\nA backup will be created.",
            parent=self.parent,
        ):
            return
        char = save.characters[self._current_slot]
        if char is None:
            return
        cls = self._selected_class()
        class_idx = self._classes().index(cls) if cls is not None else None
        try:
            stats = {key: int(self._stat_vars[key].get()) for key in catalog.STAT_KEYS}
            souls = int(self._stat_vars["souls"].get())
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Value",
                "Stats and souls must be numbers.",
                parent=self.parent,
            )
            return
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
            CTkMessageBox.showerror(
                "Invalid Value", "\n".join(problems), parent=self.parent
            )
            return
        for key, v in stats.items():
            char.set_stat(key, v)
        char.level = level
        char.souls = souls
        if class_idx is not None:
            char.starting_class = class_idx
        # The load screen reads name and level from its own directory copy.
        _sync_dir_name_level(save, self._current_slot, char.name, char.level)
        try:
            _backup_and_save(
                save, save_path, f"ds3_edit_stats_slot_{self._current_slot + 1}"
            )
            self._show_toast("Stats applied. Backup created.")
            self._populate(self._current_slot)
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _apply_identity(self) -> None:
        if _game_blocks_write(self.parent):
            return

        if self._current_slot < 0:
            CTkMessageBox.showwarning(
                "No Character", "Load a character first.", parent=self.parent
            )
            return
        save = self._get_save()
        save_path = self._get_save_path()
        if save is None or save_path is None:
            return
        if not CTkMessageBox.askyesno(
            "Apply Identity",
            f"Apply identity changes to Slot {self._current_slot + 1}?\n\nA backup will be created.",
            parent=self.parent,
        ):
            return
        char = save.characters[self._current_slot]
        if char is None:
            return
        if len(self._name_var.get()) > NAME_MAX_CHARS:
            CTkMessageBox.showerror(
                "Name Too Long",
                f"The name can be at most {NAME_MAX_CHARS} characters.",
                parent=self.parent,
            )
            return
        try:
            char.name = self._name_var.get()
            if int(self._ng_var.get()) != char.ng_plus:
                char.ng_plus = int(self._ng_var.get())
        except (ValueError, LayoutError) as exc:
            CTkMessageBox.showerror("Invalid Value", str(exc), parent=self.parent)
            return
        _sync_dir_name_level(save, self._current_slot, char.name, char.level)
        try:
            _backup_and_save(
                save, save_path, f"ds3_edit_identity_slot_{self._current_slot + 1}"
            )
            self._show_toast("Identity applied. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _slot_idx(self) -> int:
        val = self._slot_var.get()
        if not val:
            return -1
        try:
            return int(val.split(" - ")[0].replace("Slot", "").strip()) - 1
        except (ValueError, IndexError):
            return -1
