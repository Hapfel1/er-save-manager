"""
Context bar - slim single-row strip at the top of the window.

Shows: game combo | file | active character | game-running dot | Back up / Discord / Ko-fi
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

# Palette
_BG = "#1a1a26"
_PANEL = "#232336"
_PANEL2 = "#2c2c42"
_FG = "#e8e8f2"
_FG_ALT = "#a6adc8"
_FAINT = "#7f849c"
_ACCENT = "#cba6f7"
_BORDER = "#36364f"
_GOOD = "#a6e3a1"
_WARN = "#f9e2af"

_BAR_H = 50
_CHIP_H = 30


class ContextBar(ctk.CTkFrame):
    """
    Slim top bar with game selector, file, character context, and action buttons.

    Args:
        parent:           Parent widget.
        game_var:         StringVar holding the current game display name.
        file_path_var:    StringVar holding the current save file path.
        get_slot_index:   Returns the currently selected slot index (0-9, -1 = none).
        get_save:         Returns the loaded Save object or None.
        is_running:       Returns True if the game process is running.
        on_backup:        Callback for "Back up now".
        on_discord:       Callback for Discord button.
        on_kofi:          Callback for Ko-fi button.
        game_names:       List of game display names for the selector.
        on_game_changed:  Callback when game selection changes.
    """

    def __init__(
        self,
        parent,
        game_var: tk.StringVar,
        file_path_var: tk.StringVar,
        get_slot_index: Callable[[], int],
        get_save: Callable,
        is_running: Callable[[], bool],
        on_backup: Callable,
        on_discord: Callable,
        on_kofi: Callable,
        game_names: list[str] | None = None,
        on_game_changed: Callable | None = None,
    ):
        super().__init__(
            parent,
            height=_BAR_H,
            corner_radius=0,
            fg_color=_PANEL,
        )
        self.pack_propagate(False)
        self.grid_propagate(False)

        self._file_path_var = file_path_var
        self._get_slot = get_slot_index
        self._get_save = get_save
        self._is_running = is_running

        self._build(
            game_var, on_backup, on_discord, on_kofi, game_names, on_game_changed
        )

        file_path_var.trace_add("write", lambda *_: self.refresh())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        self._refresh_file()
        self._refresh_character()
        self._refresh_running()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(
        self, game_var, on_backup, on_discord, on_kofi, game_names, on_game_changed
    ) -> None:
        # Bottom border line
        border = ctk.CTkFrame(self, height=1, fg_color=_BORDER, corner_radius=0)
        border.pack(side="bottom", fill="x")

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14)

        # ---- Left ----
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="y")

        if game_names and on_game_changed:
            ctk.CTkComboBox(
                left,
                values=game_names,
                variable=game_var,
                state="readonly",
                width=200,
                height=_CHIP_H,
                font=("Segoe UI", 11, "bold"),
                command=on_game_changed,
                button_color=_PANEL2,
                border_color=_BORDER,
                border_width=1,
                fg_color=_PANEL2,
                text_color=_ACCENT,
                dropdown_fg_color=_PANEL2,
                dropdown_text_color=_FG,
                dropdown_hover_color="#45475a",
            ).pack(side="left", padx=(0, 12), pady=10)
        else:
            ctk.CTkLabel(
                left,
                textvariable=game_var,
                font=("Segoe UI", 11, "bold"),
                text_color=_ACCENT,
                fg_color=_PANEL2,
                corner_radius=6,
                padx=10,
                pady=3,
            ).pack(side="left", padx=(0, 12), pady=10)

        # File icon + name
        self._file_var = tk.StringVar(value="No file loaded")
        ctk.CTkLabel(
            left,
            text="",
            font=("Segoe UI", 13),
            text_color=_FAINT,
        ).pack(side="left", pady=10)
        ctk.CTkLabel(
            left,
            textvariable=self._file_var,
            font=("Segoe UI", 11),
            text_color=_FG_ALT,
        ).pack(side="left", padx=(4, 0), pady=10)

        # Separator (hidden until save loaded)
        self._char_sep = ctk.CTkFrame(left, width=1, height=20, fg_color=_BORDER)
        self._char_sep.pack(side="left", padx=14)
        self._char_sep.pack_forget()

        # Character block (hidden until save loaded)
        self._char_frame = ctk.CTkFrame(left, fg_color="transparent")
        self._char_frame.pack(side="left")
        self._char_frame.pack_forget()

        self._char_name_var = tk.StringVar()
        self._char_detail_var = tk.StringVar()

        char_text = ctk.CTkFrame(self._char_frame, fg_color="transparent")
        char_text.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(
            char_text,
            textvariable=self._char_name_var,
            font=("Segoe UI", 12, "bold"),
            text_color=_FG,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            char_text,
            textvariable=self._char_detail_var,
            font=("Segoe UI", 10),
            text_color=_FAINT,
            anchor="w",
        ).pack(anchor="w")

        # ---- Right ----
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right", fill="y")

        ctk.CTkButton(
            right,
            text="Ko-fi",
            command=on_kofi,
            width=56,
            height=_CHIP_H,
            font=("Segoe UI", 11),
            fg_color=_PANEL2,
            text_color=_FG_ALT,
            hover_color="#45475a",
            border_width=1,
            border_color=_BORDER,
        ).pack(side="right", padx=(3, 0), pady=10)

        ctk.CTkButton(
            right,
            text="Discord",
            command=on_discord,
            width=68,
            height=_CHIP_H,
            font=("Segoe UI", 11),
            fg_color=_PANEL2,
            text_color=_FG_ALT,
            hover_color="#45475a",
            border_width=1,
            border_color=_BORDER,
        ).pack(side="right", padx=3, pady=10)

        ctk.CTkButton(
            right,
            text="Back up now",
            command=on_backup,
            width=108,
            height=_CHIP_H,
            font=("Segoe UI", 11, "bold"),
        ).pack(side="right", padx=(3, 10), pady=10)

        # Game-running indicator
        self._running_dot = ctk.CTkFrame(
            right, width=8, height=8, corner_radius=4, fg_color=_GOOD
        )
        self._running_dot.pack(side="right", padx=(0, 4), pady=10)
        self._running_dot.pack_propagate(False)

        self._running_var = tk.StringVar(value="Game closed")
        ctk.CTkLabel(
            right,
            textvariable=self._running_var,
            font=("Segoe UI", 11),
            text_color=_GOOD,
        ).pack(side="right", padx=(0, 6), pady=10)

        # Store label ref to recolor
        self._running_label = right.winfo_children()[-1]

        self.refresh()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_file(self) -> None:
        path = self._file_path_var.get()
        self._file_var.set(Path(path).name if path else "No file loaded")

    def _refresh_character(self) -> None:
        save = self._get_save()
        slot_idx = self._get_slot()

        if save is None or slot_idx < 0:
            self._char_sep.pack_forget()
            self._char_frame.pack_forget()
            return

        try:
            char = save.characters[slot_idx]
            if char.is_empty():
                self._char_sep.pack_forget()
                self._char_frame.pack_forget()
                return

            name = "Unknown"
            detail = f"Slot {slot_idx + 1}"

            try:
                profiles = save.user_data_10_parsed.profile_summary.profiles
                if profiles and slot_idx < len(profiles):
                    p = profiles[slot_idx]
                    name = p.character_name or "Unknown"
                    level = getattr(p, "level", None)
                    if level is not None:
                        detail = f"Slot {slot_idx + 1} · RL {level}"
            except Exception:
                pass

            self._char_name_var.set(name)
            self._char_detail_var.set(detail)
            self._char_sep.pack(side="left", padx=14)
            self._char_frame.pack(side="left")

        except Exception:
            self._char_sep.pack_forget()
            self._char_frame.pack_forget()

    def _refresh_running(self) -> None:
        try:
            running = self._is_running()
        except Exception:
            running = False

        if running:
            self._running_var.set("Game running")
            self._running_dot.configure(fg_color=_WARN)
            if hasattr(self, "_running_label"):
                self._running_label.configure(text_color=_WARN)
        else:
            self._running_var.set("Game closed")
            self._running_dot.configure(fg_color=_GOOD)
            if hasattr(self, "_running_label"):
                self._running_label.configure(text_color=_GOOD)
