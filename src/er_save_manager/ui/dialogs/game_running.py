"""Dialog shown while the game blocks a load or write: waits for the game to
close and continues by itself, with Force Close as the fallback."""

from __future__ import annotations

import threading
import time

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette

# Process check interval while waiting
_POLL_MS = 1000
# How long Force Close waits for the process to end before reporting failure
_FORCE_TIMEOUT_S = 10.0


class _ProcessWatch:
    """Runs the process check on a worker thread; the UI reads the result.

    Tk calls stay on the UI thread: the worker only sets attributes.
    """

    def __init__(self, process_name: str):
        self.process_name = process_name
        self.running: bool | None = None
        self.busy = False

    def check(self) -> None:
        if self.busy:
            return
        self.busy = True

        def work():
            from er_save_manager.platform import PlatformUtils

            try:
                self.running = PlatformUtils.is_game_running(self.process_name)
            finally:
                self.busy = False

        threading.Thread(target=work, daemon=True).start()


def wait_for_game_close(parent, game_name: str, process_name: str) -> bool:
    """Wait for game_name to close. True once it has, False on Cancel."""
    dialog = ds.create(parent, f"Close {game_name} First")
    result = {"closed": False}
    watch = _ProcessWatch(process_name)
    force = {"started": 0.0, "failed": False}

    def close(closed: bool):
        result["closed"] = closed
        if dialog.winfo_exists():
            dialog.destroy()

    dialog.protocol("WM_DELETE_WINDOW", lambda: close(False))
    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill="both", expand=True, padx=20, pady=16)
    _row, (force_btn, _cancel) = ds.button_row(
        main,
        [
            {
                "text": "Force Close",
                "command": lambda: force_close(),
                "primary": False,
                "width": 120,
            },
            {"text": "Cancel", "command": lambda: close(False), "primary": False},
        ],
    )
    ds.header(main, f"Close {game_name} First", font=ds.TITLE_LARGE)
    ctk.CTkLabel(
        main,
        text=(
            f"{game_name} is running, and it overwrites the save while it "
            "runs. Quit to the desktop from the game's menu: this continues "
            "by itself once the game has closed."
        ),
        font=ds.FONT,
        wraplength=440,
        justify="left",
    ).pack(anchor="w", pady=(10, 8))
    status = ctk.CTkLabel(
        main,
        text="Waiting for the game to close...",
        font=ds.FONT,
        text_color=palette.PURPLE_TEXT,
        wraplength=440,
        justify="left",
    )
    status.pack(anchor="w")
    ctk.CTkLabel(
        main,
        text="Force Close ends the game at once and loses progress since its "
        "last autosave.",
        font=ds.SMALL,
        text_color=ds.MUTED,
        wraplength=440,
        justify="left",
    ).pack(anchor="w", pady=(8, 0))

    def force_close():
        from er_save_manager.platform import PlatformUtils

        force_btn.configure(state="disabled")
        status.configure(text="Closing the game...", text_color=palette.PURPLE_TEXT)
        force["started"] = time.monotonic()
        force["failed"] = False
        threading.Thread(
            target=PlatformUtils.kill_game_process, args=(process_name,), daemon=True
        ).start()

    def tick():
        if not dialog.winfo_exists():
            return
        if watch.running is False:
            close(True)
            return
        started = force["started"]
        if started and time.monotonic() - started > _FORCE_TIMEOUT_S:
            force["started"] = 0.0
            force_btn.configure(state="normal")
            status.configure(
                text=(
                    f"Could not close {game_name}. Quit from the game's menu "
                    "instead; anti-cheat or missing permissions can block "
                    "closing it from here."
                ),
                text_color=palette.WARNING_TEXT,
            )
        watch.check()
        dialog.after(_POLL_MS, tick)

    ds.finish(dialog, parent, min_width=480)
    watch.check()
    dialog.after(_POLL_MS, tick)
    dialog.wait_window()
    return result["closed"]
