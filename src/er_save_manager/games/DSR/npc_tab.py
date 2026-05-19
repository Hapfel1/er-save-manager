"""
DSR NPCs & Bosses Tab

Scrollable list of all 31 NPC/boss entries. Each toggle immediately
creates a backup and writes the save. No separate Save button.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

if TYPE_CHECKING:
    from er_save_manager.games.DSR.save import DSRSave

_DATA_DIR = Path(__file__).parent / "data"
_NPC_DATA: list[dict] | None = None


def _load_npc_data() -> list[dict]:
    global _NPC_DATA
    if _NPC_DATA is None:
        _NPC_DATA = json.loads(
            (_DATA_DIR / "npc_data.json").read_text(encoding="utf-8")
        )["npcs"]
    return _NPC_DATA


_BOSSES = {
    "Dark Sun Gwyndolin (boss)",
    "Chaos Witch Quelaag (boss)",
    "Ornstein and Smough (boss)",
    "Artorias the Abysswalker (boss)",
}


def _backup_and_save(dsr_save: DSRSave, save_path: Path, operation: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=operation, save=None)
    dsr_save.save_to_file(save_path)


def _clean_name(raw: str) -> str:
    return raw.replace(" (boss)", "").replace(" (blackmish)", " (blacksmith)")


class DSRNPCTab:
    """NPC and boss alive/dead manager. Matches ER editor visual style."""

    def __init__(
        self,
        parent,
        get_dsr_save: Callable[[], DSRSave | None],
        get_save_path: Callable[[], Path | None],
        show_toast: Callable[[str], None],
    ) -> None:
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = 0

    def setup_ui(self) -> None:
        self.parent.grid_rowconfigure(2, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        # Header row
        header = ctk.CTkFrame(self.parent, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))

        ctk.CTkLabel(header, text="NPCs & Bosses", font=("Segoe UI", 16, "bold")).pack(
            side="left"
        )

        # Slot selector
        ctk.CTkFrame(header, fg_color="transparent").pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkLabel(header, text="Slot:").pack(side="left", padx=(0, 6))
        self._slot_var = ctk.StringVar()
        self._slot_combo = ctk.CTkComboBox(
            header,
            variable=self._slot_var,
            values=[],
            state="readonly",
            width=220,
        )
        self._slot_combo.pack(side="left", padx=(0, 8))
        ctk.CTkButton(header, text="Load", command=self._load_selected, width=70).pack(
            side="left", padx=4
        )

        # Bulk action buttons
        bulk_bar = ctk.CTkFrame(self.parent, fg_color="transparent")
        bulk_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

        ctk.CTkLabel(
            bulk_bar,
            text="Bulk actions will backup and apply immediately:",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            bulk_bar,
            text="Respawn All NPCs",
            width=140,
            command=lambda: self._bulk("npcs", True),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            bulk_bar,
            text="Respawn All Bosses",
            width=145,
            command=lambda: self._bulk("bosses", True),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            bulk_bar,
            text="Kill All NPCs",
            width=110,
            fg_color=("#a03030", "#802020"),
            hover_color=("#c03030", "#a02020"),
            command=lambda: self._bulk("npcs", False),
        ).pack(side="left", padx=4)

        # Scrollable list
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(outer, corner_radius=10)
        self._scroll.pack(fill="both", expand=True, padx=4, pady=4)
        bind_mousewheel(self._scroll)

        self._placeholder = ctk.CTkLabel(
            self._scroll,
            text="No save file loaded.",
            text_color=("gray50", "gray60"),
        )
        self._placeholder.pack(anchor="w", padx=6, pady=6)

    # --- Refresh -------------------------------------------------------------- #

    def refresh(self) -> None:
        save = self._get_dsr_save()
        if save is None:
            self._slot_combo.configure(values=[])
            return
        options = []
        for i, char in enumerate(save.characters):
            label = f"Slot {i + 1} - {char.name}" if char else f"Slot {i + 1} - Empty"
            options.append(label)
        self._slot_combo.configure(values=options)
        self._slot_var.set(options[0] if options else "")
        self._current_slot = 0
        self._rebuild_rows()

    def load_slot(self, slot_idx: int) -> None:
        options = self._slot_combo.cget("values")
        if options and slot_idx < len(options):
            self._slot_var.set(options[slot_idx])
        self._current_slot = slot_idx
        self._rebuild_rows()

    # --- Internal helpers ----------------------------------------------------- #

    def _load_selected(self) -> None:
        save = self._get_dsr_save()
        if save is None:
            CTkMessageBox.showwarning(
                "No Save", "No DSR save loaded.", parent=self.parent
            )
            return
        idx = self._slot_idx()
        if idx < 0:
            return
        if save.characters[idx] is None:
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {idx + 1} is empty.", parent=self.parent
            )
            return
        self._current_slot = idx
        self._rebuild_rows()

    def _rebuild_rows(self) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()

        save = self._get_dsr_save()
        char = save.characters[self._current_slot] if save else None
        if char is None:
            ctk.CTkLabel(
                self._scroll,
                text="Empty slot or no save loaded.",
                text_color=("gray50", "gray60"),
            ).pack(anchor="w", padx=6, pady=40)
            return

        npcs = _load_npc_data()
        for section_name, entries in [
            ("NPCs", [n for n in npcs if n["name"] not in _BOSSES]),
            ("Bosses", [n for n in npcs if n["name"] in _BOSSES]),
        ]:
            ctk.CTkLabel(
                self._scroll,
                text=section_name,
                font=("Segoe UI", 12, "bold"),
            ).pack(anchor="w", padx=12, pady=(12, 2))
            for npc in entries:
                self._add_row(char, npc)

    def _add_row(self, char, npc: dict) -> None:
        alive = char.get_npc_alive(npc)
        name = _clean_name(npc["name"])

        # Mirror ER inspector row style
        row = ctk.CTkFrame(
            self._scroll,
            fg_color=("#f5f5f5", "#2a2a3e"),
            corner_radius=6,
        )
        row.pack(fill="x", padx=4, pady=3)
        row.grid_columnconfigure(1, weight=1)

        badge_color = ("#2a6e2a", "#1e7e1e") if alive else ("#8b2222", "#7a1a1a")
        ctk.CTkLabel(
            row,
            text="ALIVE" if alive else "DEAD",
            fg_color=badge_color,
            corner_radius=4,
            width=50,
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, padx=(8, 6), pady=6)

        ctk.CTkLabel(
            row,
            text=name,
            anchor="w",
            font=("Segoe UI", 11),
            text_color=("#333333", "#cccccc"),
        ).grid(row=0, column=1, sticky="w", padx=4, pady=6)

        ctk.CTkButton(
            row,
            text="Respawn",
            width=80,
            command=lambda n=npc, r=row: self._toggle(n, True, r),
        ).grid(row=0, column=2, padx=4, pady=6)
        ctk.CTkButton(
            row,
            text="Kill",
            width=60,
            fg_color=("#a03030", "#802020"),
            hover_color=("#c03030", "#a02020"),
            command=lambda n=npc, r=row: self._toggle(n, False, r),
        ).grid(row=0, column=3, padx=(0, 8), pady=6)

    def _toggle(self, npc: dict, alive: bool, row: ctk.CTkFrame) -> None:
        save = self._get_dsr_save()
        save_path = self._get_save_path()
        if save is None or save_path is None or self._current_slot < 0:
            return
        char = save.characters[self._current_slot]
        if char is None:
            return
        char.set_npc_alive(npc, alive)
        try:
            action = "respawn" if alive else "kill"
            _backup_and_save(
                save,
                save_path,
                f"npc_{action}_{npc['name'].split()[0].lower()}_slot_{self._current_slot + 1}",
            )
            # Update badge in place
            for child in row.winfo_children():
                if isinstance(child, ctk.CTkLabel) and child.cget("text") in (
                    "ALIVE",
                    "DEAD",
                ):
                    badge_color = (
                        ("#2a6e2a", "#1e7e1e") if alive else ("#8b2222", "#7a1a1a")
                    )
                    child.configure(
                        text="ALIVE" if alive else "DEAD", fg_color=badge_color
                    )
                    break
            self._show_toast(
                f"{_clean_name(npc['name'])} {'respawned' if alive else 'killed'}."
            )
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _bulk(self, group: str, alive: bool) -> None:
        save = self._get_dsr_save()
        save_path = self._get_save_path()
        if save is None or save_path is None or self._current_slot < 0:
            CTkMessageBox.showwarning(
                "No Save", "No character loaded.", parent=self.parent
            )
            return
        char = save.characters[self._current_slot]
        if char is None:
            return
        action = "respawn" if alive else "kill"
        if not CTkMessageBox.askyesno(
            "Confirm",
            f"{'Respawn' if alive else 'Kill'} all {group}?\n\nA backup will be created.",
            parent=self.parent,
        ):
            return
        npcs = _load_npc_data()
        entries = (
            [n for n in npcs if n["name"] in _BOSSES]
            if group == "bosses"
            else [n for n in npcs if n["name"] not in _BOSSES]
        )
        for npc in entries:
            char.set_npc_alive(npc, alive)
        try:
            _backup_and_save(
                save, save_path, f"bulk_{action}_{group}_slot_{self._current_slot + 1}"
            )
            self._show_toast(f"All {group} {action}ed. Backup created.")
            self._rebuild_rows()
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
