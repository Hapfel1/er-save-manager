"""DS2 character editor tab: slot picker + Stats/Inventory subtabs."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from er_save_manager.games.DS2.bonfire_tab import DS2BonfirePanel
from er_save_manager.games.DS2.inventory_tab import DS2InventoryPanel
from er_save_manager.games.DS2.npc_tab import DS2NpcPanel
from er_save_manager.games.DS2.regulation import ClassBase
from er_save_manager.games.DS2.save import (
    CHARACTER_SLOTS,
    LEVEL_STAT_KEYS,
    NG_PLUS_MAX,
    STARTING_CLASSES,
    DS2Save,
    SlotState,
)
from er_save_manager.games.DS2.soulsplanner_import import import_soulsplanner
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.scrollable_frame import ScrollableFrame
from er_save_manager.ui.utils import game_blocks_write


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(parent, "darksoulsii.exe", "Dark Souls II")


_HINT_COLOR = ("gray40", "gray70")

# Largest torch time the game allows, 99:59:59.
_TORCH_MAX_SECONDS = 99 * 3600 + 59 * 60 + 59
_TORCH_FORMAT_HINT = "H:MM:SS, max 99:59:59"


def _format_torch(seconds: float) -> str:
    """H:MM:SS, rounded to the second like the game shows it."""
    total = round(seconds)
    return f"{total // 3600}:{total % 3600 // 60:02d}:{total % 60:02d}"


def _parse_torch(text: str) -> int:
    """Seconds from "H:MM:SS", "M:SS" or plain seconds. Raises ValueError for
    anything else or a time above _TORCH_MAX_SECONDS."""
    parts = [int(part) for part in text.strip().split(":")]
    if not 1 <= len(parts) <= 3 or any(part < 0 for part in parts):
        raise ValueError(text)
    if any(part >= 60 for part in parts[1:]):
        raise ValueError(text)
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + part
    if seconds > _TORCH_MAX_SECONDS:
        raise ValueError(text)
    return seconds


class DS2EditorTab:
    """
    Args:
        parent: parent widget the tab content is built into.
        get_save: callable returning the current DS2Save, or None if unloaded.
        get_save_path: callable returning the current save file path.
        show_toast: callable(message, duration) for transient status messages.
    """

    def __init__(self, parent, get_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self.get_save = get_save
        self.get_save_path = get_save_path
        self.show_toast = show_toast
        self._slot_index = 0
        self._stat_vars: dict[str, tk.StringVar] = {}
        self.inventory_panel: DS2InventoryPanel | None = None
        self.bonfire_panel: DS2BonfirePanel | None = None
        self.npc_panel: DS2NpcPanel | None = None

        self._baseline_stats: dict[str, int] = {}
        self._baseline_level: int = 0
        # Starting level and attributes of the loaded character's class, None
        # when unknown; the level is then derived from the loaded stats.
        self._class_base: ClassBase | None = None
        # Starting class picked in the Class box, written on apply.
        self._class_id: int = 0
        self._suppress_recalc = False

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        for _ in self.setup_steps():
            pass

    def setup_steps(self):
        """Build the UI in stages; each yield lets the window redraw and handle
        input between stages (gui.py resumes it one stage per turn)."""
        top = ctk.CTkFrame(self.parent, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Character slot:").pack(side="left")
        self.slot_var = tk.StringVar(value=self._slot_display_names()[0])
        self.slot_menu = ctk.CTkOptionMenu(
            top,
            variable=self.slot_var,
            values=self._slot_display_names(),
            width=220,
        )
        self.slot_menu.pack(side="left", padx=(5, 15))

        ctk.CTkButton(top, text="Load Slot", command=self._on_load_slot).pack(
            side="left", padx=5
        )
        ctk.CTkButton(
            top, text="Import Soulsplanner Build", command=self._on_import_build
        ).pack(side="left", padx=5)

        self.slot_status_label = ctk.CTkLabel(top, text="")
        self.slot_status_label.pack(side="left", padx=(15, 0))

        self.tabview = ctk.CTkTabview(self.parent)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tabview.add("Stats")
        self.tabview.add("Inventory")
        self.tabview.add("Bonfires")
        self.tabview.add("NPCs")

        self._build_stats_tab(self.tabview.tab("Stats"))

        yield
        self.inventory_panel = DS2InventoryPanel(
            self.tabview.tab("Inventory"),
            get_save=self.get_save,
            get_slot_index=lambda: self._slot_index,
            get_save_path=self.get_save_path,
            show_toast=self.show_toast,
        )
        yield from self.inventory_panel.setup_steps()

        yield
        self.bonfire_panel = DS2BonfirePanel(
            self.tabview.tab("Bonfires"),
            get_save=self.get_save,
            get_slot_index=lambda: self._slot_index,
            get_save_path=self.get_save_path,
            show_toast=self.show_toast,
        )
        self.bonfire_panel.setup_ui()

        yield
        self.npc_panel = DS2NpcPanel(
            self.tabview.tab("NPCs"),
            get_save=self.get_save,
            get_slot_index=lambda: self._slot_index,
            get_save_path=self.get_save_path,
            show_toast=self.show_toast,
        )
        self.npc_panel.setup_ui()

        yield
        self.refresh()

    def _build_stats_tab(self, parent) -> None:
        # Packed before the scroll area so it stays visible on short windows.
        ctk.CTkButton(
            parent, text="Apply Changes", command=self._apply_changes, height=34
        ).pack(side="bottom", fill="x", padx=10, pady=10)

        body = ScrollableFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True)

        fields = ctk.CTkFrame(body, fg_color="transparent")
        fields.pack(fill="x", padx=10, pady=(10, 5))

        self.name_var = tk.StringVar()
        self.souls_var = tk.StringVar()

        self._add_field(fields, "Name", self.name_var, row=0)
        self._add_field(fields, "Souls", self.souls_var, row=1)

        ctk.CTkLabel(fields, text="NG+:").grid(
            row=2, column=0, sticky="w", padx=5, pady=3
        )
        self.ng_var = tk.StringVar(value="0")
        ctk.CTkComboBox(
            fields,
            variable=self.ng_var,
            values=[str(i) for i in range(NG_PLUS_MAX + 1)],
            state="readonly",
            width=140,
        ).grid(row=2, column=1, sticky="w", padx=5, pady=3)

        ctk.CTkLabel(fields, text="HP:").grid(
            row=3, column=0, sticky="w", padx=5, pady=3
        )
        self.hp_label = ctk.CTkLabel(fields, text="-", text_color=("gray40", "gray70"))
        self.hp_label.grid(row=3, column=1, sticky="w", padx=5, pady=3)

        ctk.CTkLabel(fields, text="Torch time:").grid(
            row=4, column=0, sticky="w", padx=5, pady=3
        )
        self.torch_var = tk.StringVar()
        self._torch_loaded = ""
        self._torch_entry = ctk.CTkEntry(fields, textvariable=self.torch_var, width=140)
        self._torch_entry.grid(row=4, column=1, sticky="w", padx=5, pady=3)
        self._torch_border = self._torch_entry.cget("border_color")
        ctk.CTkButton(
            fields,
            text="Max",
            width=50,
            command=lambda: self.torch_var.set(_format_torch(_TORCH_MAX_SECONDS)),
        ).grid(row=4, column=2, sticky="w", padx=5, pady=3)
        self._torch_hint = ctk.CTkLabel(
            fields, text=_TORCH_FORMAT_HINT, text_color=_HINT_COLOR
        )
        self._torch_hint.grid(row=4, column=3, sticky="w", padx=5, pady=3)
        self.torch_var.trace_add("write", lambda *_: self._check_torch())

        ctk.CTkLabel(fields, text="Class:").grid(
            row=5, column=0, sticky="w", padx=5, pady=3
        )
        self.class_var = tk.StringVar()
        ctk.CTkComboBox(
            fields,
            variable=self.class_var,
            values=list(STARTING_CLASSES.values()),
            state="readonly",
            width=140,
            command=self._on_class_selected,
        ).grid(row=5, column=1, sticky="w", padx=5, pady=3)

        ctk.CTkLabel(fields, text="Soul memory:").grid(
            row=6, column=0, sticky="w", padx=5, pady=3
        )
        self.soul_memory_label = ctk.CTkLabel(fields, text="-", text_color=_HINT_COLOR)
        self.soul_memory_label.grid(
            row=6, column=1, columnspan=3, sticky="w", padx=5, pady=3
        )

        stats_frame = ctk.CTkFrame(body, fg_color="transparent")
        stats_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(
            stats_frame, text="Level & Attributes", font=("Segoe UI", 12, "bold")
        ).grid(row=0, column=0, columnspan=6, sticky="w", padx=5, pady=(0, 5))

        ctk.CTkLabel(stats_frame, text="Level:").grid(
            row=1, column=0, sticky="w", padx=5, pady=3
        )
        self.level_var = tk.StringVar()
        ctk.CTkEntry(stats_frame, textvariable=self.level_var, width=140).grid(
            row=1, column=1, sticky="w", padx=5, pady=3
        )
        self.level_status_label = ctk.CTkLabel(
            stats_frame, text="", font=("Segoe UI", 10)
        )
        self.level_status_label.grid(
            row=1, column=2, columnspan=4, sticky="w", padx=5, pady=3
        )

        for i, stat_name in enumerate(LEVEL_STAT_KEYS):
            var = tk.StringVar()
            var.trace_add("write", lambda *_: self._recalc_level())
            self._stat_vars[stat_name] = var
            self._add_field(
                stats_frame,
                stat_name.capitalize(),
                var,
                row=2 + i // 3,
                col=(i % 3) * 2,
            )

    def _add_field(self, parent, label, var, row, col=0):
        ctk.CTkLabel(parent, text=f"{label}:").grid(
            row=row, column=col, sticky="w", padx=5, pady=3
        )
        ctk.CTkEntry(parent, textvariable=var, width=140).grid(
            row=row, column=col + 1, sticky="w", padx=5, pady=3
        )

    # ------------------------------------------------------------------
    # Slot handling
    # ------------------------------------------------------------------

    def _slot_labels(self) -> dict[int, str]:
        """Picker label per offered slot index, in slot order.

        Never-created slots are hidden, as in the inspector, so the picker only
        offers slots that hold a character or a pre-creation run. A save with no
        such slot lists all of them so the picker is never empty.
        """
        save: DS2Save | None = self.get_save()
        if save is None:
            return {i: f"{i} - (no save loaded)" for i in range(CHARACTER_SLOTS)}

        offered = [
            i
            for i in range(CHARACTER_SLOTS)
            if save.slot_state(i) is not SlotState.NEVER_CREATED
        ]
        labels = {}
        for i in offered or range(CHARACTER_SLOTS):
            state = save.slot_state(i)
            if state is SlotState.CHARACTER:
                labels[i] = f"{i} - {save.slot_display_name(i)}"
            else:
                labels[i] = f"{i} - ({state.value})"
        return labels

    def _slot_display_names(self) -> list[str]:
        return list(self._slot_labels().values())

    @staticmethod
    def _slot_index_from_display(value: str) -> int:
        try:
            return int(value.split(" - ")[0])
        except (ValueError, IndexError):
            return 0

    def _on_load_slot(self) -> None:
        self._slot_index = self._slot_index_from_display(self.slot_var.get())
        self.refresh()

    def slot_var_set(self, slot_index: int) -> None:
        """Programmatically select a slot (e.g. from the inspector's
        double-click), then load it."""
        labels = self._slot_labels()
        if slot_index in labels:
            self.slot_var.set(labels[slot_index])
        self._on_load_slot()

    # ------------------------------------------------------------------
    # Level auto-recalc
    # ------------------------------------------------------------------

    def _recalc_level(self) -> None:
        """Called whenever a stat entry changes. Updates the Level field to
        what the stats add up to (see _expected_level) and flags stats below
        the class's starting values."""
        if self._suppress_recalc or not self._baseline_stats:
            return

        computed_level = self._expected_level()
        if computed_level is None:
            self.level_status_label.configure(
                text="Enter whole numbers for all stats to recalculate level",
                text_color="orange",
            )
            return

        self._suppress_recalc = True
        self.level_var.set(str(computed_level))
        self._suppress_recalc = False
        below = self._stats_below_class()
        if below:
            self.level_status_label.configure(
                text="Below the class's starting value: " + ", ".join(below),
                text_color="orange",
            )
            return
        self.level_status_label.configure(
            text=f"(auto-calculated from stat changes: {computed_level})",
            text_color=("gray40", "gray70"),
        )

    def _stats_below_class(self) -> list[str]:
        """Stats entered below the class's starting values, as display
        names. Empty when the class is unknown or a stat is not a number."""
        if self._class_base is None:
            return []
        try:
            return [
                f"{stat_name.capitalize()} (min {self._class_base.stats[stat_name]})"
                for stat_name, var in self._stat_vars.items()
                if int(var.get()) < self._class_base.stats[stat_name]
            ]
        except ValueError:
            return []

    def _check_torch(self) -> bool:
        """Validate the torch time as it is typed. Shows how a valid entry will
        be saved, or what is wrong with an invalid one. Returns whether the
        entry can be applied."""
        text = self.torch_var.get().strip()
        if text == self._torch_loaded:
            valid, hint = True, _TORCH_FORMAT_HINT
        else:
            try:
                valid, hint = True, f"= {_format_torch(_parse_torch(text))}"
            except ValueError:
                valid, hint = False, f"Use {_TORCH_FORMAT_HINT}"
        self._torch_hint.configure(
            text=hint, text_color=_HINT_COLOR if valid else "orange"
        )
        self._torch_entry.configure(
            border_color=self._torch_border if valid else "orange"
        )
        return valid

    def _expected_level(self) -> int | None:
        """Class starting level plus the stats gained over the class's
        starting values, or the loaded level plus the stat changes when the
        class is unknown. None when a stat is not a number."""
        if self._class_base is not None:
            base_level, base_stats = self._class_base.level, self._class_base.stats
        else:
            base_level, base_stats = self._baseline_level, self._baseline_stats
        try:
            delta = sum(
                int(var.get()) - base_stats[stat_name]
                for stat_name, var in self._stat_vars.items()
            )
        except ValueError:
            return None
        return base_level + delta

    # ------------------------------------------------------------------
    # Refresh / apply
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        save: DS2Save | None = self.get_save()

        labels = self._slot_labels()
        if self._slot_index not in labels:
            self._slot_index = next(iter(labels))
        self.slot_menu.configure(values=list(labels.values()))
        self.slot_var.set(labels[self._slot_index])

        if save is None:
            return

        if save.slot_state(self._slot_index) is SlotState.NEVER_CREATED:
            self.slot_status_label.configure(
                text="Never created in-game - edits here will not appear at the load screen",
                text_color="orange",
            )
        else:
            self.slot_status_label.configure(text="")

        character = save.characters[self._slot_index]
        self.name_var.set(character.name)
        self.souls_var.set(str(character.souls))
        self.ng_var.set(str(character.new_game_plus))
        self.hp_label.configure(text=str(character.hp))
        self._torch_loaded = _format_torch(character.torch_seconds)
        self.torch_var.set(self._torch_loaded)

        self._suppress_recalc = True
        for stat_name, var in self._stat_vars.items():
            var.set(str(character.get_stat(stat_name)))
        self._suppress_recalc = False

        self._baseline_stats = {k: character.get_stat(k) for k in LEVEL_STAT_KEYS}
        self._baseline_level = character.get_stat("level")
        self.level_var.set(str(self._baseline_level))
        self.level_status_label.configure(text="")
        self._class_id = character.starting_class
        self._class_base = character.class_base()
        self.class_var.set(self._class_display(self._class_id))
        self._show_soul_memory(character)
        expected_level = self._expected_level()
        if expected_level is not None and expected_level != self._baseline_level:
            self.level_status_label.configure(
                text=f"Stats add up to level {expected_level} for this class",
                text_color="orange",
            )

        if self.inventory_panel is not None:
            self.inventory_panel.refresh()
        if self.bonfire_panel is not None:
            self.bonfire_panel.refresh()
        if self.npc_panel is not None:
            self.npc_panel.refresh()

    @staticmethod
    def _class_display(class_id: int) -> str:
        return STARTING_CLASSES.get(class_id, f"Unknown ({class_id})")

    def _on_class_selected(self, class_name: str) -> None:
        """Switch the starting class used for the level and the minimum
        stats. Stats below the new class's starting values are raised to
        them after asking; declining keeps the previous class."""
        save: DS2Save | None = self.get_save()
        new_id = next(k for k, v in STARTING_CLASSES.items() if v == class_name)
        if save is None or new_id == self._class_id:
            self.class_var.set(self._class_display(self._class_id))
            return
        character = save.characters[self._slot_index]
        base = character.class_base(new_id)
        if base is None:
            self.show_toast("Class data unavailable in this save", duration=3000)
            self.class_var.set(self._class_display(self._class_id))
            return
        try:
            stats = {name: int(var.get()) for name, var in self._stat_vars.items()}
        except ValueError:
            self.show_toast("Enter whole numbers for all stats first", duration=3000)
            self.class_var.set(self._class_display(self._class_id))
            return

        below = character.stats_below_class(stats, new_id)
        if below:
            changes = "\n".join(
                f"{name.capitalize()}: {stats[name]} -> {base.stats[name]}"
                for name in below
            )
            if not CTkMessageBox.askyesno(
                "Change Starting Class",
                f"{class_name} starts with higher values for:\n{changes}\n\n"
                "Raise these stats to them? The level goes up to match.",
                parent=self.parent,
            ):
                self.class_var.set(self._class_display(self._class_id))
                return

        self._class_id = new_id
        self._class_base = base
        self._suppress_recalc = True
        for name in below:
            self._stat_vars[name].set(str(base.stats[name]))
        self._suppress_recalc = False
        self._recalc_level()

    def _show_soul_memory(self, character) -> None:
        text = f"{character.soul_memory:,} (this cycle {character.soul_memory_cycle:,})"
        required = character.required_soul_memory()
        if required is not None and required > character.soul_memory:
            text += f", below the {required:,} its level and souls need"
        self.soul_memory_label.configure(
            text=text,
            text_color=(
                "orange"
                if required is not None and required > character.soul_memory
                else _HINT_COLOR
            ),
        )

    def _apply_changes(self) -> None:
        if _game_blocks_write(self.parent):
            return

        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return

        try:
            entered_level = int(self.level_var.get())
            stat_values = {
                stat_name: int(var.get()) for stat_name, var in self._stat_vars.items()
            }
            souls = int(self.souls_var.get())
            ng_plus = int(self.ng_var.get())
        except ValueError:
            self.show_toast("Invalid numeric value, changes not applied", duration=2500)
            return
        # Written only when edited, so saving other fields keeps the stored
        # fraction of a second.
        torch_seconds = None
        if not self._check_torch():
            self.show_toast(f"Torch time must be {_TORCH_FORMAT_HINT}", duration=3000)
            return
        if self.torch_var.get().strip() != self._torch_loaded:
            torch_seconds = _parse_torch(self.torch_var.get())

        expected_level = self._expected_level()
        if expected_level is None or entered_level != expected_level:
            self.show_toast(
                f"Level ({entered_level}) does not match what these stats add up to "
                f"({expected_level}). Adjust stats or Level to match before saving.",
                duration=4000,
            )
            return
        below = self._stats_below_class()
        if below:
            self.show_toast(
                "Stats below the class's starting values: " + ", ".join(below),
                duration=4000,
            )
            return

        character = save.characters[self._slot_index]
        class_changed = self._class_id != character.starting_class
        if class_changed:
            # Before the soul memory sync, which counts level-ups from the
            # class's starting level.
            character.starting_class = self._class_id
            save.sync_class_cache(self._slot_index)
        character.name = self.name_var.get()
        character.souls = souls
        character.new_game_plus = ng_plus
        if torch_seconds is not None:
            character.torch_seconds = torch_seconds
        character.set_stat("level", entered_level)
        for stat_name, value in stat_values.items():
            character.set_stat(stat_name, value)
        soul_memory_added = character.sync_soul_memory()

        save_path = self.get_save_path()
        if not save_path:
            self.show_toast("No save path to write to", duration=2000)
            return

        self._backup(
            save_path, f"before_stats_edit_slot_{self._slot_index}", "edit_stats"
        )

        try:
            save.save_to_file(save_path)
        except Exception as e:
            self.show_toast(f"Failed to write save: {e}", duration=3000)
            return

        self.refresh()
        message = "Changes saved to disk"
        if class_changed:
            message += f", class set to {self._class_display(self._class_id)}"
        if soul_memory_added:
            message += f", soul memory raised by {soul_memory_added:,}"
        self.show_toast(message, duration=3000)

    def _on_import_build(self) -> None:
        if _game_blocks_write(self.parent):
            return
        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return
        import_soulsplanner(
            self.parent,
            save,
            self._slot_index,
            self.get_save_path,
            self.show_toast,
            on_done=self.refresh,
        )

    def _backup(self, save_path, description: str, operation: str) -> None:
        if not save_path:
            return
        try:
            from pathlib import Path

            from er_save_manager.backup.manager import BackupManager

            BackupManager(Path(save_path)).create_backup(
                description=description, operation=operation
            )
        except Exception:
            pass
