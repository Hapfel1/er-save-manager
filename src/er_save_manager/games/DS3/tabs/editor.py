"""
DS3 Character Editor tab.

Sub-tabs: Stats | Identity.
Each apply creates a backup then writes immediately.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


def _backup_and_save(ds3_save, save_path: Path, operation: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=operation, save=None)
    ds3_save.save_to_file(save_path)


class DS3EditorTab:
    def __init__(self, parent, get_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_save = get_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = -1
        self._stat_vars: dict[str, tk.StringVar] = {}
        self._name_var = tk.StringVar()
        self._ng_var = tk.StringVar(value="0")
        self._playtime_var = tk.StringVar(value="--")

    def setup_ui(self) -> None:
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(
            header, text="Character Editor", font=("Segoe UI", 16, "bold")
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
            segmented_button_selected_color=("purple3", "#6a4b85"),
            segmented_button_unselected_color=("gray70", "gray30"),
        )
        tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._build_stats_tab(tabs.add("Stats"))
        self._build_identity_tab(tabs.add("Identity"))

    # --- Stats tab ----------------------------------------------------------- #

    def _build_stats_tab(self, parent) -> None:
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        bind_mousewheel(frame)

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", pady=5, padx=10)

        # Attributes column
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

        # Resources column
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
            ctk.CTkEntry(rg, textvariable=var, width=120).grid(
                row=i, column=1, padx=5, pady=5
            )

        ctk.CTkLabel(
            frame,
            text="HP/FP/Stamina are live values stored in the save. "
            "The game may recalculate them on area load.",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=15, pady=(4, 0))
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
        ctk.CTkLabel(cf, text="Character Identity", font=("Segoe UI", 12, "bold")).grid(
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
        for key in ("vig", "atn", "end", "vit", "str", "dex", "int", "fth", "lck"):
            self._stat_vars[key].set(str(char.get_stat(key)))
        self._stat_vars["level"].set(str(char.level))
        self._stat_vars["souls"].set(str(char.souls))
        self._stat_vars["hp"].set(str(char.hp))
        self._stat_vars["fp"].set(str(char.fp))
        self._stat_vars["stamina"].set(str(char.stamina))
        self._name_var.set(char.name)
        self._ng_var.set(str(char.ng_plus))

    # --- Apply --------------------------------------------------------------- #

    def _apply_stats(self) -> None:
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
            "Confirm",
            f"Apply stat changes to Slot {self._current_slot + 1}?\n\nA backup will be created.",
            parent=self.parent,
        ):
            return
        char = save.characters[self._current_slot]
        if char is None:
            return
        try:
            for key in ("vig", "atn", "end", "vit", "str", "dex", "int", "fth", "lck"):
                char.set_stat(key, int(self._stat_vars[key].get()))
            char.level = int(self._stat_vars["level"].get())
            char.souls = int(self._stat_vars["souls"].get())
            char.hp = int(self._stat_vars["hp"].get())
            char.fp = int(self._stat_vars["fp"].get())
            char.stamina = int(self._stat_vars["stamina"].get())
        except ValueError as exc:
            CTkMessageBox.showerror("Invalid Value", str(exc), parent=self.parent)
            return
        try:
            _backup_and_save(
                save, save_path, f"ds3_edit_stats_slot_{self._current_slot + 1}"
            )
            self._show_toast("Stats applied. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _apply_identity(self) -> None:
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
            "Confirm",
            f"Apply identity changes to Slot {self._current_slot + 1}?\n\nA backup will be created.",
            parent=self.parent,
        ):
            return
        char = save.characters[self._current_slot]
        if char is None:
            return
        try:
            char.name = self._name_var.get()
            char.ng_plus = int(self._ng_var.get())
        except (ValueError, Exception) as exc:
            CTkMessageBox.showerror("Invalid Value", str(exc), parent=self.parent)
            return
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
