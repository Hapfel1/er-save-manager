"""
Nightreign SteamID patcher tab.
Delegates to er_save_manager.games.nightreign_steamid.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox


class NRSteamIDTab:
    def __init__(
        self,
        parent,
        get_nr_save: Callable,
        get_save_path: Callable,
        reload_callback: Callable,
        show_toast: Callable,
    ) -> None:
        self.parent = parent
        self._get_nr_save = get_nr_save
        self._get_save_path = get_save_path
        self._reload = reload_callback
        self._show_toast = show_toast
        self._new_id_var = tk.StringVar()
        self._detected_var = tk.StringVar(value="(load a save first)")

    def setup_ui(self) -> None:
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(outer, text="SteamID Patcher", font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=14, pady=(12, 6)
        )
        ctk.CTkLabel(
            outer,
            text=(
                "Patches the SteamID embedded in the Nightreign save. "
                "Required when copying a save to a different Steam account."
            ),
            wraplength=700,
            justify="left",
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=14, pady=(0, 12))

        grid = ctk.CTkFrame(outer, fg_color="transparent")
        grid.pack(anchor="nw", padx=14)

        ctk.CTkLabel(grid, text="Detected SteamID:", anchor="w", width=160).grid(
            row=0, column=0, sticky="w", pady=6
        )
        ctk.CTkLabel(grid, textvariable=self._detected_var, anchor="w").grid(
            row=0, column=1, sticky="w", padx=(6, 0), pady=6
        )
        ctk.CTkLabel(grid, text="New SteamID (64-bit):", anchor="w", width=160).grid(
            row=1, column=0, sticky="w", pady=6
        )
        ctk.CTkEntry(grid, textvariable=self._new_id_var, width=220).grid(
            row=1, column=1, padx=(6, 0), pady=6
        )

        ctk.CTkButton(
            outer, text="Apply SteamID Patch", command=self._apply, width=200
        ).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkLabel(
            outer,
            text="Creates a backup before patching.",
            font=("Segoe UI", 10),
            text_color=("gray45", "gray60"),
        ).pack(anchor="w", padx=14)

    def refresh(self) -> None:
        save = self._get_nr_save()
        if save and save.profile:
            self._detected_var.set(str(save.profile.steam_id))
        else:
            self._detected_var.set("(no save loaded)")

    def _apply(self) -> None:
        save_path = self._get_save_path()
        if not save_path:
            CTkMessageBox.showerror(
                "No Save", "Load a save file first.", parent=self.parent
            )
            return
        raw = self._new_id_var.get().strip()
        if not raw:
            CTkMessageBox.showerror(
                "Missing Input", "Enter the new SteamID64.", parent=self.parent
            )
            return
        try:
            new_id = int(raw)
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Input",
                "SteamID must be a decimal integer.",
                parent=self.parent,
            )
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.games.nightreign_steamid import patch_steamid_nr

            BackupManager(save_path).create_backup(
                operation="nr_steamid_patch", save=None
            )
            ok, msg = patch_steamid_nr(Path(save_path), new_id)
            if ok:
                self._reload()
                self._show_toast("SteamID patched.")
            else:
                CTkMessageBox.showerror("Patch Failed", msg, parent=self.parent)
        except Exception as e:
            CTkMessageBox.showerror("Patch Failed", str(e), parent=self.parent)
