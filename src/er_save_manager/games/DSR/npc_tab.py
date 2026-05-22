"""
DSR NPCs & Bosses Tab

NPCs section: 27 entries from npc_data.json, multi-bit alive detection.
Bosses section: all 22 bosses from dsr_named_flags.json.
  - 14 use global kill flags (IDs 2-17): fully editable.
  - 8 use map-specific flags (11xxxxxx): displayed read-only. The Pattern1
    bitfield encoding (anchor + flag_id//8) cannot reach these offsets within
    the slot's 393KB boundary.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

if TYPE_CHECKING:
    pass

_DATA_DIR = Path(__file__).parent / "data"
_NPC_DATA: list[dict] | None = None
_FLAGS_DB: dict | None = None


def _load_npc_data() -> list[dict]:
    global _NPC_DATA
    if _NPC_DATA is None:
        _NPC_DATA = json.loads(
            (_DATA_DIR / "npc_data.json").read_text(encoding="utf-8")
        )["npcs"]
    return _NPC_DATA


def _load_flags_db() -> dict:
    global _FLAGS_DB
    if _FLAGS_DB is None:
        _FLAGS_DB = json.loads(
            (_DATA_DIR / "dsr_named_flags.json").read_text(encoding="utf-8")
        )
    return _FLAGS_DB


def _is_boss(name: str) -> bool:
    return bool(re.search(r"\(boss\)", name, re.IGNORECASE))


def _clean_name(raw: str) -> str:
    name = re.sub(r"\s*\(boss\)\s*$", "", raw, flags=re.IGNORECASE)
    name = re.sub(r"\bblackmish\b", "blacksmith", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*\([^)]+\)\s*$", "", name)
    return name.strip()


def _backup_and_save(dsr_save, save_path: Path, op: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=op, save=None)
    dsr_save.save_to_file(save_path)


class DSRNPCTab:
    def __init__(self, parent, get_dsr_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = 0

    def setup_ui(self) -> None:
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(header, text="NPCs & Bosses", font=("Segoe UI", 16, "bold")).pack(
            side="left"
        )
        ctk.CTkButton(header, text="Load", command=self._load_selected, width=70).pack(
            side="right", padx=(6, 0)
        )
        self._slot_var = ctk.StringVar()
        self._slot_combo = ctk.CTkComboBox(
            header, variable=self._slot_var, values=[], state="readonly", width=220
        )
        self._slot_combo.pack(side="right")
        ctk.CTkLabel(header, text="Slot:").pack(side="right", padx=(0, 6))

        bulk_bar = ctk.CTkFrame(outer, fg_color="transparent")
        bulk_bar.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(
            bulk_bar,
            text="Changes apply and backup immediately:",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            bulk_bar,
            text="Respawn All NPCs",
            width=140,
            command=lambda: self._bulk_npcs(True),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            bulk_bar,
            text="Kill All NPCs",
            width=110,
            fg_color=("#a03030", "#802020"),
            hover_color=("#c03030", "#a02020"),
            command=lambda: self._bulk_npcs(False),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            bulk_bar,
            text="Respawn All Bosses",
            width=145,
            command=lambda: self._bulk_bosses(False),
        ).pack(side="left", padx=4)

        list_outer = ctk.CTkFrame(outer, fg_color="transparent")
        list_outer.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._scroll = ctk.CTkScrollableFrame(list_outer, corner_radius=10)
        self._scroll.pack(fill="both", expand=True)
        bind_mousewheel(self._scroll)

    # --- Refresh -------------------------------------------------------------- #

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
        self._current_slot = 0
        self._rebuild_rows()

    def load_slot(self, slot_idx: int) -> None:
        options = self._slot_combo.cget("values")
        if options and slot_idx < len(options):
            self._slot_var.set(options[slot_idx])
        self._current_slot = slot_idx
        self._rebuild_rows()

    # --- Build rows ----------------------------------------------------------- #

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

        # NPCs (npc_data.json multi-bit detection)
        npcs = [n for n in _load_npc_data() if not _is_boss(n["name"])]
        ctk.CTkLabel(self._scroll, text="NPCs", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=12, pady=(12, 2)
        )
        for npc in npcs:
            self._add_npc_row(char, npc)

        # Bosses (flags DB)
        accessible = [
            b for b in _load_flags_db()["boss_kills"] if b.get("accessible", True)
        ]
        inaccessible = [
            b for b in _load_flags_db()["boss_kills"] if not b.get("accessible", True)
        ]

        ctk.CTkLabel(self._scroll, text="Bosses", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=12, pady=(14, 2)
        )
        for boss in accessible:
            self._add_boss_row(char, boss, editable=True)

        if inaccessible:
            ctk.CTkLabel(
                self._scroll,
                text="The following bosses use map-specific event flags (11xxxxxx) that cannot be "
                "reached via the save file's global flag encoding. State is unknown and cannot "
                "be edited here.",
                wraplength=700,
                justify="left",
                font=("Segoe UI", 9),
                text_color=("gray50", "gray60"),
            ).pack(anchor="w", padx=12, pady=(10, 4))
            for boss in inaccessible:
                self._add_boss_row(char, boss, editable=False)

    def _add_npc_row(self, char, npc: dict) -> None:
        alive = char.get_npc_alive(npc)
        name = _clean_name(npc["name"])
        row = ctk.CTkFrame(
            self._scroll, fg_color=("#f5f5f5", "#2a2a3e"), corner_radius=6
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
            command=lambda n=npc, r=row: self._toggle_npc(n, True, r),
        ).grid(row=0, column=2, padx=4, pady=6)
        ctk.CTkButton(
            row,
            text="Kill",
            width=60,
            fg_color=("#a03030", "#802020"),
            hover_color=("#c03030", "#a02020"),
            command=lambda n=npc, r=row: self._toggle_npc(n, False, r),
        ).grid(row=0, column=3, padx=(0, 8), pady=6)

    def _add_boss_row(self, char, boss: dict, editable: bool) -> None:
        if editable:
            killed = char.get_flag(boss["id"])
            badge_text = "KILLED" if killed else "ALIVE"
            badge_color = ("#8b2222", "#7a1a1a") if killed else ("#2a6e2a", "#1e7e1e")
        else:
            badge_text = "N/A"
            badge_color = ("#555", "#444")

        row = ctk.CTkFrame(
            self._scroll, fg_color=("#f5f5f5", "#2a2a3e"), corner_radius=6
        )
        row.pack(fill="x", padx=4, pady=3)
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            row,
            text=badge_text,
            fg_color=badge_color,
            corner_radius=4,
            width=55,
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, padx=(8, 6), pady=6)

        name_color = ("#333333", "#cccccc") if editable else ("gray50", "gray55")
        ctk.CTkLabel(
            row,
            text=boss["name"],
            anchor="w",
            font=("Segoe UI", 11),
            text_color=name_color,
        ).grid(row=0, column=1, sticky="w", padx=4, pady=6)
        ctk.CTkLabel(
            row,
            text=boss["area"],
            anchor="w",
            font=("Segoe UI", 9),
            text_color=("gray50", "gray60"),
        ).grid(row=1, column=1, sticky="w", padx=4, pady=(0, 4))

        if editable:
            ctk.CTkButton(
                row,
                text="Respawn",
                width=80,
                command=lambda b=boss, r=row: self._toggle_boss(b, False, r),
            ).grid(row=0, column=2, rowspan=2, padx=4, pady=6)
            ctk.CTkButton(
                row,
                text="Kill",
                width=60,
                fg_color=("#a03030", "#802020"),
                hover_color=("#c03030", "#a02020"),
                command=lambda b=boss, r=row: self._toggle_boss(b, True, r),
            ).grid(row=0, column=3, rowspan=2, padx=(0, 8), pady=6)
        else:
            ctk.CTkLabel(
                row,
                text="map flag",
                font=("Segoe UI", 8),
                text_color=("gray50", "gray55"),
            ).grid(row=0, column=2, rowspan=2, padx=12, pady=6)

    # --- Toggles -------------------------------------------------------------- #

    def _toggle_npc(self, npc: dict, alive: bool, row: ctk.CTkFrame) -> None:
        save, save_path, char = self._get_char()
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

    def _toggle_boss(self, boss: dict, killed: bool, row: ctk.CTkFrame) -> None:
        save, save_path, char = self._get_char()
        if char is None:
            return
        char.set_flag(boss["id"], killed)
        try:
            action = "kill" if killed else "respawn"
            _backup_and_save(
                save,
                save_path,
                f"boss_{action}_{boss['id']}_slot_{self._current_slot + 1}",
            )
            badge_color = ("#8b2222", "#7a1a1a") if killed else ("#2a6e2a", "#1e7e1e")
            for child in row.winfo_children():
                if isinstance(child, ctk.CTkLabel) and child.cget("text") in (
                    "KILLED",
                    "ALIVE",
                ):
                    child.configure(
                        text="KILLED" if killed else "ALIVE", fg_color=badge_color
                    )
                    break
            self._show_toast(f"{boss['name']} {'killed' if killed else 'respawned'}.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _bulk_npcs(self, alive: bool) -> None:
        save, save_path, char = self._get_char()
        if char is None:
            CTkMessageBox.showwarning(
                "No Save", "No character loaded.", parent=self.parent
            )
            return
        action = "Respawn" if alive else "Kill"
        if not CTkMessageBox.askyesno(
            "Confirm",
            f"{action} all NPCs?\n\nA backup will be created.",
            parent=self.parent,
        ):
            return
        for npc in [n for n in _load_npc_data() if not _is_boss(n["name"])]:
            char.set_npc_alive(npc, alive)
        try:
            _backup_and_save(
                save,
                save_path,
                f"bulk_{action.lower()}_npcs_slot_{self._current_slot + 1}",
            )
            self._rebuild_rows()
            self._show_toast(f"All NPCs {action.lower()}ed.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _bulk_bosses(self, killed: bool) -> None:
        save, save_path, char = self._get_char()
        if char is None:
            CTkMessageBox.showwarning(
                "No Save", "No character loaded.", parent=self.parent
            )
            return
        action = "Kill" if killed else "Respawn"
        if not CTkMessageBox.askyesno(
            "Confirm",
            f"{action} all bosses?\n\nOnly the 14 globally-tracked bosses can be toggled.\n"
            "A backup will be created.",
            parent=self.parent,
        ):
            return
        for boss in _load_flags_db()["boss_kills"]:
            if boss.get("accessible", True):
                char.set_flag(boss["id"], killed)
        try:
            _backup_and_save(
                save,
                save_path,
                f"bulk_{action.lower()}_bosses_slot_{self._current_slot + 1}",
            )
            self._rebuild_rows()
            self._show_toast(f"All accessible bosses {action.lower()}ed.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    # --- Helpers -------------------------------------------------------------- #

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

    def _get_char(self):
        save = self._get_dsr_save()
        save_path = self._get_save_path()
        if save is None or save_path is None:
            return None, None, None
        char = (
            save.characters[self._current_slot]
            if 0 <= self._current_slot < len(save.characters)
            else None
        )
        return save, save_path, char

    def _slot_idx(self) -> int:
        val = self._slot_var.get()
        if not val:
            return -1
        try:
            return int(val.split(" - ")[0].replace("Slot", "").strip()) - 1
        except (ValueError, IndexError):
            return -1
