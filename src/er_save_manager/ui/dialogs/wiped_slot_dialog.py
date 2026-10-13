"""Wiped character slot dialog: explains the slot and lists recovery sources."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.fixes.wiped_slot import (
    RecoverySource,
    extract_copy,
    find_game_backups,
    find_shadow_copies,
    manager_backup_count,
    windows_sources_available,
)
from er_save_manager.ui import palette
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import center_window, force_render_dialog

_WARNING = palette.WARNING_TEXT
_FOUND = palette.GREEN_TEXT
_MUTED = ("gray40", "gray65")
_BOX = ("gray90", "gray18")
_FONT = ("Segoe UI", 13)
_BOLD = ("Segoe UI Semibold", 13)
_SMALL = ("Segoe UI", 12)
_WIDTH = 640
_WRAP = _WIDTH - 60


def _status(source: RecoverySource) -> tuple[str, tuple[str, str]]:
    if source.character:
        name, level = source.character
        return f"has {name} (Lv. {level})", _FOUND
    return "does not have this character", _MUTED


def show_wiped_slot_dialog(
    parent, save_file, slot_idx, save_path, open_backup_settings=None
) -> None:
    name = f"Character {slot_idx + 1}"
    level = "?"
    try:
        profile = save_file.user_data_10_parsed.profile_summary.profiles[slot_idx]
        name = profile.character_name or name
        level = str(profile.level)
    except Exception:
        pass

    # (label, status text, status color)
    rows: list[tuple[str, str, tuple[str, str]]] = []
    shadows: list[RecoverySource] = []
    if save_path:
        baks = find_game_backups(save_path, slot_idx)
        for bak in baks:
            rows.append((f"Game backup {bak.path.name}", *_status(bak)))
        if not baks:
            rows.append(("Game backup (.bak)", "none next to the save", _MUTED))
        count = manager_backup_count(save_path)
        rows.append(
            (
                "Save manager backups",
                f"{count} in the Backup Manager" if count else "none for this save",
                _FOUND if count else _MUTED,
            )
        )
        if windows_sources_available():
            shadows = find_shadow_copies(save_path, slot_idx)
            for shadow in shadows:
                stamp = shadow.modified.strftime("%Y-%m-%d %H:%M")
                rows.append((f"Windows previous version {stamp}", *_status(shadow)))
            if not shadows:
                rows.append(("Windows previous versions", "none found", _MUTED))
    usable = [s for s in shadows if s.character]

    dialog = ctk.CTkToplevel(parent)
    dialog.attributes("-alpha", 0)
    dialog.title("Character Data Wiped")
    dialog.resizable(False, False)

    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill=tk.BOTH, expand=True, padx=20, pady=(16, 16))

    header = ctk.CTkFrame(main, fg_color="transparent")
    header.pack(fill=tk.X)
    ctk.CTkLabel(
        header, text="⚠", font=("Segoe UI Semibold", 24), text_color=_WARNING
    ).pack(side=tk.LEFT, padx=(0, 10))
    ctk.CTkLabel(
        header,
        text=f"Slot {slot_idx + 1} ({name}, Lv. {level}) has no character data",
        font=("Segoe UI Semibold", 15),
    ).pack(side=tk.LEFT)

    ctk.CTkLabel(
        main,
        text=(
            "Every byte of the slot is zero, but the load screen still lists the "
            "character. The game will start a new character here. The character "
            "cannot be repaired from this file; restore it from an older copy "
            "of the save."
        ),
        font=_FONT,
        wraplength=_WRAP,
        justify=tk.LEFT,
    ).pack(anchor=tk.W, pady=(10, 12))

    ctk.CTkLabel(main, text="Older copies", font=_BOLD).pack(anchor=tk.W)
    box = ctk.CTkFrame(main, fg_color=_BOX, corner_radius=8)
    box.pack(fill=tk.X, pady=(4, 8))
    box.grid_columnconfigure(1, weight=1)
    for i, (label, status, color) in enumerate(rows):
        pady = (8 if i == 0 else 2, 8 if i == len(rows) - 1 else 2)
        ctk.CTkLabel(box, text=label, font=_FONT).grid(
            row=i, column=0, sticky=tk.W, padx=(12, 20), pady=pady
        )
        ctk.CTkLabel(box, text=status, font=_FONT, text_color=color).grid(
            row=i, column=1, sticky=tk.W, padx=(0, 12), pady=pady
        )

    hints = []
    if usable:
        hints.append(
            "Extract Previous Versions saves the copies that have the character "
            "next to the save file."
        )
    elif windows_sources_available() and not shadows:
        hints.append(
            "Right-click the save folder > Properties > Previous Versions also "
            "lists File History copies, if File History covers that folder."
        )
    hints.append(
        "To restore only this character, load the older copy and use Character "
        "Management > Transfer to copy it into this save."
    )
    ctk.CTkLabel(
        main,
        text="\n".join(hints),
        font=_SMALL,
        text_color=_MUTED,
        wraplength=_WRAP,
        justify=tk.LEFT,
    ).pack(anchor=tk.W, pady=(0, 12))

    def close():
        dialog.grab_release()
        dialog.destroy()

    tip = ctk.CTkFrame(main, fg_color=_BOX, corner_radius=8)
    tip.pack(fill=tk.X, pady=(0, 14))
    ctk.CTkLabel(
        tip,
        text=(
            "Tip: turn on Auto-Backup on Game Launch and periodic backups so an "
            "older copy is always there."
        ),
        font=_SMALL,
        wraplength=_WRAP - 170 if open_backup_settings else _WRAP - 20,
        justify=tk.LEFT,
    ).pack(side=tk.LEFT, padx=12, pady=10)
    if open_backup_settings is not None:
        ctk.CTkButton(
            tip,
            text="Backup Settings",
            font=_FONT,
            width=140,
            height=30,
            command=lambda: (close(), open_backup_settings()),
        ).pack(side=tk.RIGHT, padx=12, pady=10)

    buttons = ctk.CTkFrame(main, fg_color="transparent")
    buttons.pack(fill=tk.X)
    ctk.CTkButton(
        buttons, text="Close", font=_FONT, width=100, height=32, command=close
    ).pack(side=tk.RIGHT)
    if save_path:
        ctk.CTkButton(
            buttons,
            text="Open Save Folder",
            font=_FONT,
            width=140,
            height=32,
            fg_color=("gray70", "gray35"),
            command=lambda: open_folder(Path(save_path)),
        ).pack(side=tk.RIGHT, padx=(0, 8))
    if usable:

        def extract():
            try:
                written = [extract_copy(s, save_path) for s in usable]
            except OSError as e:
                CTkMessageBox.showerror(
                    "Extract Failed", f"Could not write the copies:\n{e}", parent=dialog
                )
                return
            CTkMessageBox.showinfo(
                "Previous Versions Extracted",
                "Saved next to the save file:\n"
                + "\n".join(p.name for p in written)
                + "\n\nLoad one and use Character Management > Transfer to copy "
                "the character into your save.",
                parent=dialog,
            )
            open_folder(written[0])

        ctk.CTkButton(
            buttons,
            text="Extract Previous Versions",
            font=_FONT,
            width=180,
            height=32,
            command=extract,
        ).pack(side=tk.RIGHT, padx=(0, 8))

    dialog.update_idletasks()
    center_window(dialog, parent=parent)
    force_render_dialog(dialog)
    dialog.attributes("-alpha", 1)
    dialog.grab_set()
    dialog.protocol("WM_DELETE_WINDOW", close)
    dialog.wait_window()


def open_folder(path: Path) -> None:
    """Open the folder containing path, selecting the file where supported."""
    import platform
    import subprocess

    from er_save_manager.ui.utils import _get_subprocess_env

    try:
        if platform.system() == "Windows":
            subprocess.run(["explorer", f"/select,{path.resolve()}"])
        elif platform.system() == "Darwin":
            subprocess.run(["open", "-R", str(path)])
        else:
            subprocess.run(["xdg-open", str(path.parent)], env=_get_subprocess_env())
    except Exception as e:
        print(f"Failed to open folder: {e}")
