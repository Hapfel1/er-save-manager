"""First steps shown in place of the character list until a save is loaded."""

from __future__ import annotations

import threading

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette

# Set by the main window: Auto-Find, Browse, and (process name, game name)
# of the active game
_auto_find = None
_browse = None
_game = None


def configure(auto_find, browse, game) -> None:
    global _auto_find, _browse, _game
    _auto_find, _browse, _game = auto_find, browse, game


def available() -> bool:
    return _game is not None


def create(parent) -> GetStartedPanel:
    """Panel for the active game."""
    process_name, game_name = _game()
    return GetStartedPanel(parent, game_name, process_name, _auto_find, _browse)


# Game process check interval while the panel shows
_POLL_MS = 3000
_DONE = (("#D6EED2", "#24392B"), palette.GREEN_TEXT)
_TODO = (palette.PURPLE_TINT, palette.PURPLE_TEXT)


class GetStartedPanel(ctk.CTkFrame):
    """Close the game, load a save, pick a character. The first step
    follows the game process and offers Force Close while it runs."""

    def __init__(
        self,
        parent,
        game_name: str,
        process_name: str,
        auto_find,
        browse,
    ):
        super().__init__(parent, fg_color="transparent")
        from er_save_manager.ui.dialogs.game_running import _ProcessWatch

        self._game_name = game_name
        self._process_name = process_name
        self._watch = _ProcessWatch(process_name)
        self._shown_running: bool | None = None

        ctk.CTkLabel(self, text="Get started", font=ds.TITLE_LARGE).pack(
            anchor="w", pady=(4, 6)
        )
        step1 = self._step("1", f"Close {game_name}")
        self._num1 = step1[0]
        self._text1 = ctk.CTkLabel(
            step1[1],
            text="Checking whether the game is running...",
            font=ds.FONT,
            text_color=ds.MUTED,
            anchor="w",
            justify="left",
            wraplength=640,
        )
        self._text1.pack(anchor="w")
        self._force_row = ctk.CTkFrame(step1[1], fg_color="transparent")
        # Theme font and height, as the buttons of the file row
        ctk.CTkButton(
            self._force_row,
            text="Force Close",
            command=self._force_close,
            fg_color=ds.SECONDARY,
            width=120,
        ).pack(side="left")
        ctk.CTkLabel(
            self._force_row,
            text="Ends the game at once; progress since its last autosave is lost.",
            font=ds.SMALL,
            text_color=ds.MUTED,
        ).pack(side="left", padx=(10, 0))

        _num, body = self._step("2", "Load your save")
        ctk.CTkLabel(
            body,
            text="Auto-Find looks in the usual save folders. Browse if your "
            "saves are elsewhere or come from a console.",
            font=ds.FONT,
            text_color=ds.MUTED,
            anchor="w",
            justify="left",
            wraplength=640,
        ).pack(anchor="w")
        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(anchor="w", pady=(6, 0))
        # Same look as Auto-Find and Browse in the file row above
        ctk.CTkButton(buttons, text="Auto-Find", command=auto_find, width=110).pack(
            side="left"
        )
        ctk.CTkButton(buttons, text="Browse", command=browse, width=110).pack(
            side="left", padx=(8, 0)
        )

        _num, body = self._step("3", "Pick a character")
        ctk.CTkLabel(
            body,
            text="Then check it here, or edit it in the other tabs. A backup "
            "is made before every change, and the message after an edit "
            "offers Undo.",
            font=ds.FONT,
            text_color=ds.MUTED,
            anchor="w",
            justify="left",
            wraplength=640,
        ).pack(anchor="w")

        self._watch.check()
        self.after(300, self._tick)

    def _step(self, number: str, title: str):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=6)
        num = ctk.CTkLabel(
            row,
            text=number,
            width=28,
            height=28,
            corner_radius=14,
            fg_color=_TODO[0],
            text_color=_TODO[1],
            font=ds.BOLD,
        )
        num.pack(side="left", anchor="n", padx=(0, 12))
        body = ctk.CTkFrame(row, fg_color="transparent")
        body.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(body, text=title, font=ds.BOLD, anchor="w").pack(anchor="w")
        return num, body

    def _tick(self) -> None:
        if not self.winfo_exists():
            return
        running = self._watch.running
        if running is not None and running != self._shown_running:
            self._shown_running = running
            if running:
                self._num1.configure(text="1", fg_color=_TODO[0], text_color=_TODO[1])
                self._text1.configure(
                    text=f"{self._game_name} is running and overwrites the save "
                    "while it runs. Quit to the desktop from the game's menu.",
                    text_color=palette.WARNING_TEXT,
                )
                self._force_row.pack(anchor="w", pady=(6, 0))
            else:
                self._num1.configure(text="✓", fg_color=_DONE[0], text_color=_DONE[1])
                self._text1.configure(
                    text="The game is not running.", text_color=ds.MUTED
                )
                self._force_row.pack_forget()
        self._watch.check()
        self.after(_POLL_MS, self._tick)

    def _force_close(self) -> None:
        from er_save_manager.platform import PlatformUtils

        self._text1.configure(text="Closing the game...", text_color=ds.MUTED)
        self._shown_running = None
        threading.Thread(
            target=PlatformUtils.kill_game_process,
            args=(self._process_name,),
            daemon=True,
        ).start()
