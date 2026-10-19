"""Small dialogs and widgets shared by the community preset and character browsers."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette
from er_save_manager.ui.utils import open_url

GITHUB_LOGIN_URL = "https://github.com/login"


def metrics_text(likes: int, downloads: int) -> str:
    return f"{likes} likes  ·  {downloads} downloads"


def github_notice(parent, action: str, retry: str = "", **pack) -> ctk.CTkFrame:
    """Info box: a GitHub login is needed before the browser opens for action."""
    box = ds.box(parent, **({"pady": (0, 12)} | pack))
    row = ctk.CTkFrame(box, fg_color="transparent")
    row.pack(fill=tk.X, padx=12, pady=(10, 0))
    ctk.CTkLabel(row, text=".", font=("Inter SemiBold", 20), text_color=ds.INFO).pack(
        side=tk.LEFT, padx=(0, 10)
    )
    ctk.CTkLabel(row, text="GitHub account required", font=ds.BOLD).pack(side=tk.LEFT)
    ctk.CTkLabel(
        box,
        text=f"Log into GitHub in your browser before {action}." + retry,
        font=ds.FONT,
        justify=tk.LEFT,
        anchor="w",
        wraplength=520,
    ).pack(fill=tk.X, padx=12, pady=(4, 0))
    link = ctk.CTkLabel(
        box,
        text=GITHUB_LOGIN_URL,
        font=ds.FONT,
        text_color=palette.BLUE_TEXT,
        cursor="hand2",
        anchor="w",
    )
    link.pack(fill=tk.X, padx=12, pady=(2, 10))
    link.bind("<Button-1>", lambda _e: open_url(GITHUB_LOGIN_URL))
    return box


def like_report_row(
    parent, has_liked: bool, on_like: Callable[[], None], on_report: Callable[[], None]
) -> ctk.CTkFrame:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    ds.button(
        row,
        "Liked" if has_liked else "Like",
        on_like,
        width=90,
        state="disabled" if has_liked else "normal",
    ).pack(side=tk.LEFT, padx=(0, 8))
    ds.button(row, "Report", on_report, primary=False, width=90).pack(side=tk.LEFT)
    return row


def ask_report(parent, kind: str, name: str, author: str) -> str | None:
    """Ask why a preset or character is reported; None when cancelled."""
    result: list[str | None] = [None]
    dialog = ds.create(parent, f"Report {kind}")
    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

    def submit():
        message = text.get("1.0", tk.END).strip()
        if not message:
            status.configure(text="Enter a reason for the report.")
            return
        result[0] = message
        dialog.destroy()

    ds.button_row(
        main,
        [
            {"text": "Submit Report", "command": submit, "width": 130},
            {"text": "Cancel", "command": dialog.destroy, "primary": False},
        ],
    )
    status = ctk.CTkLabel(main, text="", font=ds.SMALL, text_color=ds.ERROR)
    status.pack(side=tk.BOTTOM, anchor="w", pady=(6, 0))

    ds.header(main, f"Report {name}", font=ds.TITLE_LARGE)
    ctk.CTkLabel(
        main, text=f"by {author}", font=ds.SMALL, text_color=ds.MUTED, anchor="w"
    ).pack(fill=tk.X, pady=(2, 12))
    github_notice(main, "reporting")
    ctk.CTkLabel(
        main,
        text="Report only genuine issues (inappropriate content, etc.)",
        font=ds.FONT,
        anchor="w",
    ).pack(fill=tk.X)
    ctk.CTkLabel(main, text="Reason for report:", font=ds.BOLD, anchor="w").pack(
        fill=tk.X, pady=(12, 4)
    )
    text = ctk.CTkTextbox(main, height=120, font=ds.FONT)
    text.pack(fill=tk.X)
    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    ds.finish(dialog, parent, min_width=560)
    text.focus_set()
    dialog.wait_window()
    return result[0]


def show_submission_link(parent, submission_url: str | None) -> None:
    """Link to finish a submission by hand when the browser did not open it."""
    dialog = ds.create(parent, "Use This Link to Submit")
    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

    buttons = [{"text": "Close", "command": dialog.destroy, "primary": False}]
    if submission_url:

        def copy_url():
            dialog.clipboard_clear()
            dialog.clipboard_append(submission_url)
            copy_btn.configure(text="Copied")
            dialog.after(2000, lambda: copy_btn.configure(text="Copy Link"))

        buttons.insert(0, {"text": "Copy Link", "command": copy_url, "width": 110})
    _, widgets = ds.button_row(main, buttons)
    copy_btn = widgets[0]

    ds.header(main, "GitHub not logged in", font=ds.TITLE_LARGE)
    if submission_url:
        ctk.CTkLabel(
            main,
            text="Log in to GitHub, then copy and paste this link in your browser "
            "to finish the submission.",
            font=ds.FONT,
            anchor="w",
            justify=tk.LEFT,
            wraplength=600,
        ).pack(fill=tk.X, pady=(6, 8))
        box = ctk.CTkTextbox(main, height=110, wrap="char", font=ds.SMALL)
        box.pack(fill=tk.X)
        box.insert("1.0", submission_url)
        box.configure(state="disabled")
    else:
        ctk.CTkLabel(
            main,
            text="Could not generate a submission URL. Log in to GitHub and try again.",
            font=ds.FONT,
            text_color=ds.ERROR,
            anchor="w",
        ).pack(fill=tk.X, pady=(6, 0))
    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    ds.finish(dialog, parent, min_width=640)


def show_submission_ready(
    heading: str,
    package_text: str,
    zip_path: str,
    steps: list[str],
    open_folder: Callable[[], None],
) -> None:
    """Shown after the submission ZIP is written and GitHub was opened."""
    dialog = ds.create(None, "Submission Ready")
    dialog.attributes("-topmost", True)
    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

    ds.button_row(
        main,
        [
            {"text": "Open Folder", "command": open_folder, "width": 120},
            {"text": "Close", "command": dialog.destroy, "primary": False},
        ],
    )
    ds.header(main, heading, icon="✓", icon_color=ds.FOUND, font=ds.TITLE_LARGE)
    ctk.CTkLabel(
        main,
        text=f"{package_text} Your browser has opened to GitHub.",
        font=ds.FONT,
        text_color=ds.MUTED,
        anchor="w",
    ).pack(fill=tk.X, pady=(4, 12))

    ctk.CTkLabel(main, text="Next steps", font=ds.BOLD, anchor="w").pack(fill=tk.X)
    box = ds.box(main)
    for i, step in enumerate(steps):
        ctk.CTkLabel(
            box, text=f"{i + 1}.  {step}", font=ds.FONT, anchor="w", justify=tk.LEFT
        ).pack(
            fill=tk.X,
            padx=12,
            pady=(8 if i == 0 else 2, 8 if i == len(steps) - 1 else 2),
        )

    ctk.CTkLabel(main, text="Package", font=ds.BOLD, anchor="w").pack(
        fill=tk.X, pady=(4, 0)
    )
    ctk.CTkLabel(
        main,
        text=str(Path(zip_path)),
        font=ds.SMALL,
        text_color=ds.MUTED,
        anchor="w",
        justify=tk.LEFT,
        wraplength=560,
    ).pack(fill=tk.X)
    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    ds.finish(dialog, None, min_width=600)
