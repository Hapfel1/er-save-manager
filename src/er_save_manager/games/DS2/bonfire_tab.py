"""
DS2 bonfire panel: shows which bonfires a slot has lit and their intensities,
and can light, unlight or set the intensity of them.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import ttk

import customtkinter as ctk

from er_save_manager.games.DS2.bonfire_database import BONFIRES
from er_save_manager.games.DS2.save import BONFIRE_MAX_INTENSITY, DS2Save, SlotState
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import game_blocks_write, raise_existing_window


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(parent, "darksoulsii.exe", "Dark Souls II")


def _lit_text(lit: bool, last_rested: bool) -> str:
    text = "Lit" if lit else "Unlit"
    return f"{text} (last rested)" if last_rested else text


class DS2BonfirePanel:
    """
    Args:
        parent: parent widget the panel is built into.
        get_save: callable returning the current DS2Save, or None if unloaded.
        get_slot_index: callable returning the currently selected slot index.
        get_save_path: callable returning the current save file path.
        show_toast: callable(message, duration) for transient status messages.
    """

    def __init__(
        self, parent, get_save, get_slot_index, get_save_path, show_toast
    ) -> None:
        self.parent = parent
        self.get_save = get_save
        self.get_slot_index = get_slot_index
        self.get_save_path = get_save_path
        self.show_toast = show_toast
        # Called after every refresh (visual bonfire view).
        self.listeners: list = []
        self._visual_win = None

    def setup_ui(self) -> None:
        header = ctk.CTkFrame(self.parent, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(header, text="Bonfires", font=("Segoe UI", 13, "bold")).pack(
            side="left"
        )
        self._summary_label = ctk.CTkLabel(header, text="")
        self._summary_label.pack(side="left", padx=(12, 0))
        ctk.CTkButton(
            header, text="Visual View", width=110, command=self._open_visual_view
        ).pack(side="right")

        buttons = ctk.CTkFrame(self.parent, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", padx=10, pady=(6, 10))
        self._light_button = ctk.CTkButton(
            buttons, text="Light Selected", command=self._on_light_selected, height=32
        )
        self._light_button.pack(side="left", fill="x", expand=True, padx=(0, 3))
        self._unlight_button = ctk.CTkButton(
            buttons,
            text="Unlight Selected",
            command=self._on_unlight_selected,
            height=32,
        )
        self._unlight_button.pack(side="left", fill="x", expand=True, padx=3)
        self._unlock_button = ctk.CTkButton(
            buttons, text="Unlock All Bonfires", command=self._on_unlock_all, height=32
        )
        self._unlock_button.pack(side="left", fill="x", expand=True, padx=(3, 0))

        intensity_row = ctk.CTkFrame(self.parent, fg_color="transparent")
        intensity_row.pack(side="bottom", fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(intensity_row, text="Intensity:").pack(side="left", padx=(0, 4))
        self._intensity_var = ctk.StringVar(value="1")
        self._intensity_combo = ctk.CTkComboBox(
            intensity_row,
            variable=self._intensity_var,
            values=[str(n) for n in range(1, BONFIRE_MAX_INTENSITY + 1)],
            state="readonly",
            width=70,
            command=lambda _v: self._update_buttons(),
        )
        self._intensity_combo.pack(side="left")
        self._set_intensity_button = ctk.CTkButton(
            intensity_row,
            text="Set Intensity",
            command=self._on_set_intensity,
            width=110,
        )
        self._set_intensity_button.pack(side="left", padx=6)

        ctk.CTkLabel(
            self.parent,
            text=(
                "Ctrl or Shift+click selects several. Intensity is what Bonfire "
                "Ascetics raise, plus 1 per NG+ cycle the game adds itself; it is "
                "kept when lighting or unlighting. Set "
                "Intensity also lights unlit bonfires. The last rested bonfire "
                "stays lit."
            ),
            text_color=("gray40", "gray60"),
            font=("Segoe UI", 11),
        ).pack(side="bottom", anchor="w", padx=10)

        self._tree = ttk.Treeview(
            self.parent,
            columns=("name", "state", "intensity"),
            show="headings",
            height=8,
            selectmode="extended",
        )
        self._tree.heading("name", text="Bonfire")
        self._tree.heading("state", text="State")
        self._tree.heading("intensity", text="Intensity")
        self._tree.column("name", width=300)
        self._tree.column("state", width=150)
        self._tree.column("intensity", width=80, anchor="center")
        self._tree.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._tree.bind("<<TreeviewSelect>>", lambda _e: self._on_selection())

        self._ids: list[int] = []
        self._lit: dict[int, bool] = {}
        self._intensities: dict[int, int] = {}
        self._min_intensity = 1
        self._last_rested: int | None = None
        self._has_character = False
        self.refresh()

    def refresh(self) -> None:
        self._load_rows()
        for listener in list(self.listeners):
            listener()

    def _load_rows(self) -> None:
        self._tree.delete(*self._tree.get_children())
        save: DS2Save | None = self.get_save()
        bonfires = save.bonfires(self.get_slot_index()) if save is not None else None

        self._ids, self._lit, self._intensities = [], {}, {}
        self._last_rested = None
        if bonfires is None:
            self._summary_label.configure(text="No bonfire data in this slot")
            self._update_buttons()
            return

        self._lit = bonfires.lit()
        self._intensities = bonfires.intensities()
        self._set_min_intensity(bonfires.min_intensity)
        self._last_rested = bonfires.last_rested
        for bonfire_id, lit in self._lit.items():
            self._ids.append(bonfire_id)
            self._tree.insert(
                "",
                "end",
                values=(
                    BONFIRES[bonfire_id],
                    _lit_text(lit, bonfire_id == self._last_rested),
                    self._intensities[bonfire_id],
                ),
            )
        lit_count = sum(self._lit.values())
        self._summary_label.configure(text=f"{lit_count} of {len(self._lit)} lit")

        # A slot with no character yet has nothing to travel from.
        self._has_character = (
            save.slot_state(self.get_slot_index()) is SlotState.CHARACTER
        )
        self._update_buttons()

    def _open_visual_view(self) -> None:
        if raise_existing_window(self._visual_win):
            return
        from er_save_manager.games.DS2.visual_bonfires import VisualBonfireBrowser

        self._visual_win = VisualBonfireBrowser(self.parent, self)

    def _selected_ids(self) -> list[int]:
        return [self._ids[self._tree.index(row)] for row in self._tree.selection()]

    def intensity_choices(self) -> list[str]:
        """Intensities a bonfire can have in the loaded character's cycle."""
        return [str(n) for n in range(self._min_intensity, BONFIRE_MAX_INTENSITY + 1)]

    def _set_min_intensity(self, minimum: int) -> None:
        self._min_intensity = minimum
        self._intensity_combo.configure(values=self.intensity_choices())
        if int(self._intensity_var.get()) < minimum:
            self._intensity_var.set(str(minimum))

    def _on_selection(self) -> None:
        """Show the shared intensity of the selected bonfires in the intensity
        box."""
        shared = {self._intensities[i] for i in self._selected_ids()}
        if len(shared) == 1:
            intensity = shared.pop()
            if intensity <= BONFIRE_MAX_INTENSITY:
                self._intensity_var.set(str(intensity))
        self._update_buttons()

    def _update_buttons(self) -> None:
        """Enable each button only when it would change something."""
        picked = self._selected_ids()
        intensity = int(self._intensity_var.get())
        can_set_intensity = any(
            not self._lit[i] or self._intensities[i] != intensity for i in picked
        )
        can_light = any(not self._lit[i] for i in picked)
        can_unlight = any(self._lit[i] and i != self._last_rested for i in picked)
        can_unlock = not all(self._lit.values())
        for button, enabled in (
            (self._light_button, can_light),
            (self._unlight_button, can_unlight),
            (self._unlock_button, can_unlock),
            (self._set_intensity_button, can_set_intensity),
        ):
            button.configure(
                state="normal" if enabled and self._has_character else "disabled"
            )

    def _apply(self, title: str, message: str, operation: str, mutate) -> None:
        """Confirm, then run mutate(bonfires) to change bonfires, back up and
        write. mutate returns how many bonfires it changed."""
        if _game_blocks_write(self.parent):
            return

        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return
        bonfires = save.bonfires(self.get_slot_index())
        if bonfires is None:
            self.show_toast("No bonfire data in this slot", duration=2000)
            return
        if not CTkMessageBox.askyesno(title, message, parent=self.parent):
            return

        changed = mutate(bonfires)
        save_path = self.get_save_path()
        if save_path:
            self._backup(save_path, f"before_{operation}", operation)
            try:
                save.save_to_file(save_path)
            except Exception as e:
                self.show_toast(f"Failed to write save: {e}", duration=3000)
                return
        self.refresh()
        self.show_toast(f"Changed {changed} bonfires", duration=2500)

    def _on_light_selected(self) -> None:
        ids = [i for i in self._selected_ids() if not self._lit[i]]
        self._apply(
            "Light bonfires",
            f"Light {len(ids)} selected bonfires?\n\nA backup is made first.",
            "light_bonfires",
            lambda bonfires: bonfires.set_lit(ids, True),
        )

    def _on_unlight_selected(self) -> None:
        ids = [
            i for i in self._selected_ids() if self._lit[i] and i != self._last_rested
        ]
        self._apply(
            "Unlight bonfires",
            f"Unlight {len(ids)} selected bonfires?\n\nA backup is made first.",
            "unlight_bonfires",
            lambda bonfires: bonfires.set_lit(ids, False),
        )

    def _on_set_intensity(self) -> None:
        intensity = int(self._intensity_var.get())
        ids = [
            i
            for i in self._selected_ids()
            if not self._lit[i] or self._intensities[i] != intensity
        ]
        self._apply(
            "Set bonfire intensity",
            f"Set {len(ids)} selected bonfires to intensity {intensity}?\n\n"
            "Unlit ones are lit. A backup is made first.",
            "set_bonfire_intensity",
            lambda bonfires: bonfires.set_intensity(ids, intensity),
        )

    def _on_unlock_all(self) -> None:
        ids = [i for i, lit in self._lit.items() if not lit]
        self._apply(
            "Unlock all bonfires",
            f"Light {len(ids)} unlit bonfires in this slot?\n\nA backup is made first.",
            "unlock_bonfires",
            lambda bonfires: bonfires.set_lit(ids, True),
        )

    def _backup(self, save_path, description: str, operation: str) -> None:
        try:
            from er_save_manager.backup.manager import BackupManager

            BackupManager(Path(save_path)).create_backup(
                description=description, operation=operation
            )
        except Exception:
            pass
