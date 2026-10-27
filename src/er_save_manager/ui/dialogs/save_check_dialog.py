"""Issue view for the non-Elden Ring games, laid out like the Elden Ring
Character Details dialog (see games/save_check.py for the checks)."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from er_save_manager.games import save_check
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.toast import notify

_WRAP = 540


def show_issues(parent, game_key: str, save_path, slot_idx: int, name: str, reload):
    """Show the issues of one character plus save-wide ones, with a fix button.

    reload is called after a successful fix.
    """
    if not save_path or not Path(save_path).is_file():
        notify(parent, "No save file loaded.", "warning")
        return

    all_issues = save_check.check(game_key, save_path)
    own = [i for i in all_issues if i.slot == slot_idx]
    shared = [i for i in all_issues if i.slot is None]
    fixable = [i for i in own + shared if i.fixable]
    unfixable = [i for i in own + shared if not i.fixable]

    dialog = ds.create(parent, f"Character Details - {name}")

    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill="both", expand=True, padx=20, pady=16)

    buttons = []
    if fixable:
        buttons.append(
            {
                "text": "Fix All Issues",
                "width": 130,
                "command": lambda: _fix_all(
                    dialog, game_key, Path(save_path), slot_idx, fixable, reload
                ),
            }
        )
    buttons.append({"text": "Close", "command": dialog.destroy, "primary": not fixable})
    ds.button_row(main, buttons)

    if fixable:
        ds.header(main, f"{name}: {len(fixable)} issue(s) found", icon="⚠")
    elif unfixable:
        ds.header(main, f"{name}: no fixable issues", icon="ℹ", icon_color=ds.INFO)
    else:
        ds.header(main, f"{name}: no issues found", icon="✓", icon_color=ds.FOUND)

    def section(body, title, items, color=None):
        ctk.CTkLabel(body, text=title, font=ds.BOLD).pack(anchor="w", pady=(10, 0))
        group = ds.box(body, pady=(4, 0))
        for i, item in enumerate(items):
            ctk.CTkLabel(
                group,
                text=f"•  {item.text}",
                font=ds.FONT,
                text_color=color,
                wraplength=_WRAP - 24,
                justify="left",
                anchor="w",
            ).pack(
                fill="x",
                padx=12,
                pady=(8 if i == 0 else 2, 8 if i == len(items) - 1 else 2),
            )

    def build(body):
        own_fix = [i for i in fixable if i.slot is not None]
        save_wide = [i for i in fixable if i.slot is None]
        if own_fix:
            section(body, "Character", own_fix, ds.WARNING)
        if save_wide:
            section(body, "Save file", save_wide, ds.WARNING)
        if unfixable:
            section(body, "Structural notes (no automatic fix)", unfixable)
        if not fixable and not unfixable:
            ctk.CTkLabel(
                body, text="The character appears healthy.", font=ds.FONT
            ).pack(anchor="w", pady=(10, 0))
        elif fixable:
            ctk.CTkLabel(
                body,
                text="Fix All Issues corrects everything above; a backup is made first.",
                font=ds.SMALL,
                text_color=ds.MUTED,
            ).pack(anchor="w", pady=(10, 0))

    ds.content(main, build, max_height=440, width=_WRAP)
    ds.finish(dialog, parent, min_width=460)


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
        CTkMessageBox.showerror(
            "Fix Failed", f"Failed to fix issues:\n{exc}", parent=parent
        )
        return
    if reload:
        reload()
    summary = "\n".join(f"- {i.text}" for i in fixable)
    CTkMessageBox.showinfo(
        "Issues Fixed",
        f"Fixed {len(fixable)} issue(s):\n\n{summary}\n\n"
        "Backup saved to backup manager.",
        parent=parent,
    )
