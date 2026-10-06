"""
DSR Character Editor Tab
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.games.DSR.save import (
    MAX_HUMANITY,
    MAX_SOULS,
    MAX_STAT,
    NAME_MAX_CHARS,
    STAT_KEYS,
    calc_level_from_stats,
    class_base_stats,
)
from er_save_manager.ui import palette
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel, game_blocks_write


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
    def __init__(self, parent, get_dsr_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = -1
        self._stat_vars: dict[str, tk.StringVar] = {}
        self._name_var = tk.StringVar()
        self._body_type_var = tk.StringVar(value="Type A (Male)")
        self._class_var = tk.StringVar(value=_CLASSES[0])
        self._covenant_var = tk.StringVar(value=_COVENANTS[0])
        self._ng_var = tk.StringVar(value="0")
        self._playtime_var = tk.StringVar(value="--")
        # Starting class index at last load; used for level recalc
        self._loaded_class_idx: int = 0
        # False when the loaded stats sit below their own class's base
        # (modded or edited character); class minimums are then not enforced.
        self._enforce_class_min = True

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

        ctk.CTkLabel(
            header, text="Character Editor", font=("Segoe UI", 16, "bold")
        ).pack(side="left")
        ctk.CTkButton(
            header,
            text="Load Character",
            command=self._load_selected,
            width=130,
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

    # --- Stats tab ------------------------------------------------------------ #

    def _build_stats_tab(self, parent) -> None:
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        bind_mousewheel(frame)

        top_row = ctk.CTkFrame(frame, fg_color="transparent")
        top_row.pack(fill="x", pady=5, padx=10)

        af = ctk.CTkFrame(top_row, fg_color="transparent")
        af.pack(side="left", fill="both", expand=True, padx=(0, 5))
        ctk.CTkLabel(af, text="Attributes", font=("Segoe UI", 12, "bold")).pack(
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
        ctk.CTkLabel(rf, text="Resources", font=("Segoe UI", 12, "bold")).pack(
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
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
            wraplength=520,
            justify="left",
        )
        self._class_note.pack(anchor="w", padx=15)
        ctk.CTkLabel(
            frame,
            text="Saving VIT updates derived max HP. Saving END updates max Stamina. Level is recalculated from stats automatically.",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=15, pady=(4, 0))
        ctk.CTkButton(
            frame, text="Apply Changes", command=self._apply_stats, width=200
        ).pack(pady=16)

    # --- Identity tab --------------------------------------------------------- #

    def _build_identity_tab(self, parent) -> None:
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        bind_mousewheel(frame)

        cf = ctk.CTkFrame(frame, fg_color="transparent")
        cf.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(cf, text="Character Identity", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0)
        )

        rows = [
            ("Name:", self._name_var, "entry", None),
            (
                "Body Type:",
                self._body_type_var,
                "combo",
                ["Type A (Male)", "Type B (Female)"],
            ),
            ("Class:", self._class_var, "combo", _CLASSES),
            ("Covenant:", self._covenant_var, "combo", _COVENANTS),
            ("NG+:", self._ng_var, "combo", [str(i) for i in range(8)]),
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
        ctk.CTkLabel(cf, text="Play Time:").grid(
            row=len(rows) + 1, column=0, sticky="w", padx=5, pady=5
        )
        ctk.CTkLabel(cf, textvariable=self._playtime_var).grid(
            row=len(rows) + 1, column=1, sticky="w", padx=5, pady=5
        )

        ctk.CTkLabel(
            frame,
            text="Name supports up to 16 characters. Both name copies in the save are updated.",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=15, pady=(4, 0))
        ctk.CTkButton(
            frame, text="Apply Changes", command=self._apply_identity, width=200
        ).pack(pady=16)

    # --- Refresh / load ------------------------------------------------------- #

    def refresh(self) -> None:
        save = self._get_dsr_save()
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
        save = self._get_dsr_save()
        if save is None:
            CTkMessageBox.showwarning(
                "No Save", "No DSR save loaded.", parent=self.parent
            )
            return
        if save.characters[idx] is None:
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {idx + 1} is empty.", parent=self.parent
            )
            return
        self._current_slot = idx
        self._populate(idx)

    def _populate(self, slot_idx: int) -> None:
        save = self._get_dsr_save()
        if save is None:
            return
        char = save.characters[slot_idx]
        if char is None:
            return
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
        self._name_var.set(char.name)
        self._body_type_var.set(
            "Type A (Male)" if char.body_type == 1 else "Type B (Female)"
        )
        cls = int(char.player_class)
        self._class_var.set(_CLASSES[cls] if cls < len(_CLASSES) else str(cls))
        cov = int(char.covenant)
        self._covenant_var.set(_COVENANTS[cov] if cov < len(_COVENANTS) else str(cov))
        self._ng_var.set(str(char.ng_plus))
        h = int(char.play_seconds // 3600)
        m = int((char.play_seconds % 3600) // 60)
        s = int(char.play_seconds % 60)
        self._playtime_var.set(f"{h}h {m:02d}m {s:02d}s")

    def _recalc_level(self) -> None:
        """Recalculate and update the level field from current stat inputs."""
        try:
            vit = int(self._stat_vars["vit"].get())
            atn = int(self._stat_vars["atn"].get())
            end = int(self._stat_vars["end"].get())
            str_ = int(self._stat_vars["str"].get())
            dex = int(self._stat_vars["dex"].get())
            int_ = int(self._stat_vars["int"].get())
            fth = int(self._stat_vars["fth"].get())
            res = int(self._stat_vars["res"].get())
        except ValueError:
            return
        lvl = calc_level_from_stats(
            self._loaded_class_idx, vit, atn, end, str_, dex, int_, fth, res
        )
        self._stat_vars["level"].set(str(max(1, lvl)))

    # --- Apply ---------------------------------------------------------------- #

    def _apply_stats(self) -> None:
        if _game_blocks_write(self.parent):
            return

        if self._current_slot < 0:
            CTkMessageBox.showwarning(
                "No Character", "Load a character first.", parent=self.parent
            )
            return
        save, save_path = self._get_dsr_save(), self._get_save_path()
        if save is None or save_path is None:
            return
        if not CTkMessageBox.askyesno(
            "Confirm",
            f"Apply stat changes to Slot {self._current_slot + 1}?\n\nA backup will be created.",
            parent=self.parent,
        ):
            return
        char = save.characters[self._current_slot]
        if char is None:
            return
        try:
            stats = {key: int(self._stat_vars[key].get()) for key in STAT_KEYS}
            souls = int(self._stat_vars["souls"].get())
            humanity = int(self._stat_vars["humanity"].get())
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Value",
                "Stats, souls and humanity must be numbers.",
                parent=self.parent,
            )
            return
        problems = self._stat_problems(stats, self._loaded_class_idx)
        if not 0 <= souls <= MAX_SOULS:
            problems.append(f"Souls must be 0-{MAX_SOULS:,}")
        if not 0 <= humanity <= MAX_HUMANITY:
            problems.append(f"Humanity must be 0-{MAX_HUMANITY}")
        if problems:
            CTkMessageBox.showerror(
                "Invalid Value", "\n".join(problems), parent=self.parent
            )
            return
        for key, value in stats.items():
            char.set_stat(key, value, update_derived=True)
        char.level = max(
            1, calc_level_from_stats(self._loaded_class_idx, *stats.values())
        )
        char.souls = souls
        char.humanity = humanity
        try:
            _backup_and_save(
                save, save_path, f"edit_stats_slot_{self._current_slot + 1}"
            )
            self._show_toast("Stats applied. Backup created.")
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
        save, save_path = self._get_dsr_save(), self._get_save_path()
        if save is None or save_path is None:
            return
        if not CTkMessageBox.askyesno(
            "Confirm",
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
        new_class = (
            _CLASSES.index(self._class_var.get())
            if self._class_var.get() in _CLASSES
            else int(char.player_class)
        )
        stats = {key: char.get_stat(key) for key in STAT_KEYS}
        problems = self._stat_problems(stats, new_class)
        if problems:
            CTkMessageBox.showerror(
                "Class Minimum Conflict",
                f"The saved stats do not fit {_CLASSES[new_class]}:\n"
                + "\n".join(problems),
                parent=self.parent,
            )
            return
        try:
            char.name = self._name_var.get()
            char.body_type = 1 if self._body_type_var.get() == "Type A (Male)" else 0
            if new_class != int(char.player_class):
                char.player_class = type(char.player_class)(new_class)
                # Level counts from the class's own starting level and stats.
                char.level = max(1, calc_level_from_stats(new_class, *stats.values()))
                self._loaded_class_idx = new_class
                self._stat_vars["level"].set(str(char.level))
            char.covenant = type(char.covenant)(
                _COVENANTS.index(self._covenant_var.get())
            )
            char.ng_plus = int(self._ng_var.get())
        except (ValueError, IndexError) as exc:
            CTkMessageBox.showerror("Invalid Value", str(exc), parent=self.parent)
            return
        try:
            _backup_and_save(
                save, save_path, f"edit_identity_slot_{self._current_slot + 1}"
            )
            self._show_toast("Identity applied. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _stat_problems(self, stats: dict[str, int], class_idx: int) -> list[str]:
        """Stats above the cap or below the class's starting values."""
        problems = [
            f"{key.upper()} above {MAX_STAT}"
            for key, value in stats.items()
            if value > MAX_STAT
        ]
        base = class_base_stats(class_idx)
        if self._enforce_class_min and base is not None:
            problems += [
                f"{key.upper()} below the class minimum of {base[key]}"
                for key, value in stats.items()
                if value < base[key]
            ]
        else:
            problems += [
                f"{key.upper()} below 1" for key, value in stats.items() if value < 1
            ]
        return problems

    def _slot_idx(self) -> int:
        val = self._slot_var.get()
        if not val:
            return -1
        try:
            return int(val.split(" - ")[0].replace("Slot", "").strip()) - 1
        except (ValueError, IndexError):
            return -1
