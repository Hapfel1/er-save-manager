"""Issue view for the non-Elden Ring games, laid out like the Elden Ring
Character Details dialog (see games/save_check.py for the checks)."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from er_save_manager.games import save_check
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import center_window

_RULE = "=" * 50


def show_issues(parent, game_key: str, save_path, slot_idx: int, name: str, reload):
    """Show the issues of one character plus save-wide ones, with a fix button.

    reload is called after a successful fix.
    """
    if not save_path or not Path(save_path).is_file():
        CTkMessageBox.showwarning("No Save", "No save file loaded!", parent=parent)
        return

    all_issues = save_check.check(game_key, save_path)
    own = [i for i in all_issues if i.slot == slot_idx]
    shared = [i for i in all_issues if i.slot is None]
    fixable = [i for i in own + shared if i.fixable]
    unfixable = [i for i in own + shared if not i.fixable]

    info = [_RULE, f"  CHARACTER: {name}", _RULE, ""]
    if fixable:
        info += [_RULE, "ISSUES DETECTED:", _RULE]
        info += [f"  - {i.text}" for i in fixable if i.slot is not None]
        save_wide = [i for i in fixable if i.slot is None]
        if save_wide:
            info += ["", "  Save file:"]
            info += [f"  - {i.text}" for i in save_wide]
        info += ["", "Click 'Fix All Issues' to correct everything"]
    elif not unfixable:
        info += [_RULE, "NO ISSUES DETECTED", _RULE, "", "Character appears healthy!"]
    if unfixable:
        info += [
            "",
            _RULE,
            "STRUCTURAL NOTES (informational, no automatic fix):",
            _RULE,
        ]
        info += [f"  {i.text}" for i in unfixable]

    dialog = ctk.CTkToplevel(parent)
    dialog.title(f"Character Details - {name}")
    dialog.update_idletasks()
    parent.update_idletasks()
    center_window(dialog, 640, 520, parent=parent)
    dialog.resizable(True, True)
    dialog.update_idletasks()
    dialog.lift()
    dialog.focus_force()

    main_frame = ctk.CTkFrame(dialog, corner_radius=10)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    ctk.CTkLabel(
        main_frame,
        text=f"Character Details - {name}",
        font=("Segoe UI", 16, "bold"),
    ).pack(anchor="w", padx=10, pady=(8, 6))

    info_box = ctk.CTkTextbox(
        main_frame,
        font=("Consolas", 13),
        wrap="word",
        fg_color=("#f5f5f5", "#111827"),
        text_color=("#1f1f28", "#e5e7eb"),
    )
    info_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    info_box.insert("1.0", "\n".join(info))
    info_box.configure(state="disabled")

    button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    button_frame.pack(fill="x", padx=6, pady=(0, 4))
    if fixable:
        ctk.CTkButton(
            button_frame,
            text="Fix All Issues",
            command=lambda: _fix_all(
                dialog, game_key, Path(save_path), slot_idx, fixable, reload
            ),
            width=150,
        ).pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="Close", command=dialog.destroy, width=100).pack(
        side="right", padx=5
    )

    dialog.lift()
    dialog.focus_force()
    dialog.grab_set()


def _fix_all(dialog, game_key, save_path: Path, slot_idx, fixable, reload) -> None:
    from er_save_manager.backup.manager import BackupManager

    parent = dialog.master
    dialog.destroy()
    if not CTkMessageBox.askyesno(
        "Confirm Fix",
        f"Fix all {len(fixable)} issue(s) in Slot {slot_idx + 1}?\n\n"
        "A backup will be created first.",
        parent=parent,
    ):
        return
    try:
        BackupManager(save_path).create_backup(
            description=f"before_fix_slot_{slot_idx + 1}",
            operation=f"fix_slot_{slot_idx + 1}",
            save=None,
        )
        save_check.repair(game_key, save_path)
    except Exception as exc:
        CTkMessageBox.showerror("Error", f"Failed to fix issues:\n{exc}", parent=parent)
        return
    if reload:
        reload()
    summary = "\n".join(f"- {i.text}" for i in fixable)
    CTkMessageBox.showinfo(
        "Success",
        f"Fixed {len(fixable)} issue(s):\n\n{summary}\n\n"
        "Backup saved to backup manager.",
        parent=parent,
    )
