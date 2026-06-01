"""
Home dashboard screen.

Shows a file-load strip, a save-health/status banner, and quick-action cards.
No save logic lives here - reads state and routes to existing screens.
"""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

# Palette - Catppuccin Mocha
_BG = "#1e1e2e"
_PANEL = "#181825"
_PANEL2 = "#313244"
_FG = "#cdd6f4"
_FG_ALT = "#a6adc8"
_FAINT = "#7f849c"
_ACCENT = "#cba6f7"
_BORDER = "#313244"
_GOOD = "#a6e3a1"
_GOOD_BG = "#1e3a2e"
_WARN = "#f9e2af"
_WARN_BG = "#3a2e1e"
_RED = "#f38ba8"
_RED_BG = "#3a1e2e"

_CARD_R = 10
_STRIP_H = 46
_BTN_H = 32


_ER_CARDS = [
    ("Fix a broken save", "Infinite loading, softlocks, crashes", "Save Fixer"),
    ("Edit stats & runes", "Level, attributes, held runes", "Character Editor"),
    ("Edit inventory", "Spawn items, import a build", "Character Editor"),
    ("Teleport", "Warp to a safe location", "World State"),
    ("Restore a backup", "Roll back to an earlier save", "Save Fixer"),
    ("Change appearance", "Import a face / body preset", "Appearance"),
]

_DSR_CARDS = [
    ("Edit character", "Souls, level, attributes, name", "Character Editor"),
    ("Edit inventory", "Add weapons, armor, items", "Inventory"),
    ("Bosses & NPCs", "Respawn or revive", "NPCs & Bosses"),
    ("Event flags", "Read and toggle flags", "Event Flags"),
    ("World state", "Bonfires & progression", "World State"),
    ("Restore a backup", "Roll back to an earlier save", "Save Inspector"),
]

_LITE_CARDS = [
    ("Back up now", "Snapshot the current save", "Save Fixer"),
    ("Restore a backup", "Roll back to an earlier save", "Save Fixer"),
    ("Transfer save", "Move between Steam accounts", "SteamID Patcher"),
]


def _cards_for(game_key: str) -> list[tuple[str, str, str]]:
    if game_key == "elden_ring":
        return _ER_CARDS
    if game_key == "dark_souls_remastered":
        return _DSR_CARDS
    return _LITE_CARDS


class HomeScreen:
    """
    Home dashboard.

    Args:
        parent:         Frame to build into.
        get_save:       Returns the loaded Save object or None.
        get_game_key:   Returns the active game key string.
        get_game_name:  Returns the active game display name.
        on_navigate:    Called with a screen name to navigate there.
        on_scan:        Navigates to the fix/scan screen.
        browse_file:    Callback for Browse button.
        auto_detect:    Callback for Auto-Find button.
        load_save:      Callback for Reload button.
        show_backup:    Callback for Backups button.
        open_trouble:   Callback for Troubleshoot button.
        open_itemgib:   Callback for Item Gib button.
        file_path_var:  StringVar for the file path entry.
        file_load_buttons: List to register disableable buttons into.
    """

    def __init__(
        self,
        parent,
        get_save: Callable,
        get_game_key: Callable[[], str],
        get_game_name: Callable[[], str],
        on_navigate: Callable[[str], None],
        on_scan: Callable,
        browse_file: Callable,
        auto_detect: Callable,
        load_save: Callable,
        show_backup: Callable,
        open_trouble: Callable,
        open_itemgib: Callable,
        file_path_var: tk.StringVar,
        file_load_buttons: list,
    ):
        self._parent = parent
        self._get_save = get_save
        self._get_game_key = get_game_key
        self._get_game_name = get_game_name
        self._on_navigate = on_navigate
        self._on_scan = on_scan
        self._file_path_var = file_path_var

        self._health_icon_box: ctk.CTkFrame | None = None
        self._health_icon_lbl: ctk.CTkLabel | None = None
        self._health_title_var = tk.StringVar(value="No save loaded")
        self._health_detail_var = tk.StringVar(
            value="Use Browse or Auto-Find below to load a save file"
        )
        self._cards_outer: ctk.CTkFrame | None = None

        self._build(
            browse_file,
            auto_detect,
            load_save,
            show_backup,
            open_trouble,
            open_itemgib,
            file_load_buttons,
        )

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Re-read save state and update banner and cards."""
        self._refresh_health()
        self._refresh_cards()

    # ------------------------------------------------------------------

    def _build(
        self,
        browse_file,
        auto_detect,
        load_save,
        show_backup,
        open_trouble,
        open_itemgib,
        file_load_buttons,
    ) -> None:
        # File-load strip pinned at top
        strip = ctk.CTkFrame(
            self._parent, corner_radius=0, height=_STRIP_H, fg_color=_PANEL
        )
        strip.pack(fill="x", side="top")
        strip.pack_propagate(False)

        strip_border = ctk.CTkFrame(strip, height=1, fg_color=_BORDER, corner_radius=0)
        strip_border.pack(side="bottom", fill="x")

        strip_inner = ctk.CTkFrame(strip, fg_color="transparent")
        strip_inner.pack(fill="both", expand=True, padx=10, pady=6)

        entry = ctk.CTkEntry(
            strip_inner,
            textvariable=self._file_path_var,
            height=_BTN_H,
            fg_color=_PANEL2,
            border_color=_BORDER,
            text_color=_FG_ALT,
            placeholder_text="Select a save file...",
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        def _reg(btn):
            file_load_buttons.append(btn)
            return btn

        for text, cmd, w in [
            ("Browse", browse_file, 80),
            ("Auto-Find", auto_detect, 88),
            ("Reload", load_save, 72),
            ("Backups", show_backup, 72),
            ("Troubleshoot", open_trouble, 100),
            ("Item Gib", open_itemgib, 76),
        ]:
            btn = ctk.CTkButton(
                strip_inner,
                text=text,
                command=cmd,
                width=w,
                height=_BTN_H,
                font=("Segoe UI", 11),
            )
            btn.pack(side="left", padx=2)
            if text in ("Browse", "Auto-Find", "Reload", "Item Gib"):
                _reg(btn)

        # Scrollable content area
        outer = ctk.CTkScrollableFrame(
            self._parent,
            fg_color="transparent",
            corner_radius=0,
        )
        outer.pack(fill="both", expand=True, padx=22, pady=16)

        # Health banner
        self._banner = ctk.CTkFrame(outer, fg_color=_PANEL, corner_radius=_CARD_R)
        self._banner.pack(fill="x", pady=(0, 20))

        banner_inner = ctk.CTkFrame(self._banner, fg_color="transparent")
        banner_inner.pack(fill="x", padx=18, pady=16)

        self._health_icon_box = ctk.CTkFrame(
            banner_inner,
            width=52,
            height=52,
            fg_color=_PANEL2,
            corner_radius=14,
        )
        self._health_icon_box.pack(side="left", padx=(0, 16))
        self._health_icon_box.pack_propagate(False)

        self._health_icon_lbl = ctk.CTkLabel(
            self._health_icon_box,
            text="?",
            font=("Segoe UI", 18, "bold"),
            text_color=_FAINT,
        )
        self._health_icon_lbl.place(relx=0.5, rely=0.5, anchor="center")

        text_col = ctk.CTkFrame(banner_inner, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            text_col,
            textvariable=self._health_title_var,
            font=("Segoe UI", 15, "bold"),
            text_color=_FG,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            text_col,
            textvariable=self._health_detail_var,
            font=("Segoe UI", 12),
            text_color=_FG_ALT,
            anchor="w",
        ).pack(anchor="w", pady=(3, 0))

        self._banner_btn = ctk.CTkButton(
            banner_inner,
            text="Re-scan",
            command=self._on_scan,
            width=90,
            height=34,
            font=("Segoe UI", 12),
            fg_color=_PANEL2,
            text_color=_FG,
            hover_color="#45475a",
        )
        self._banner_btn.pack(side="right")

        # Section label
        self._section_label = ctk.CTkLabel(
            outer,
            text="WHAT DO YOU WANT TO DO?",
            font=("Segoe UI", 10, "bold"),
            text_color=_FAINT,
            anchor="w",
        )
        self._section_label.pack(anchor="w", pady=(0, 10))

        # Cards container
        self._cards_outer = ctk.CTkFrame(outer, fg_color="transparent")
        self._cards_outer.pack(fill="x")

        self._refresh_health()
        self._refresh_cards()

    # ------------------------------------------------------------------

    def _refresh_health(self) -> None:
        save = self._get_save()
        game_key = self._get_game_key()
        game_name = self._get_game_name()

        if save is None:
            self._set_banner_neutral(
                "No save loaded",
                "Use Browse or Auto-Find above to load a save file",
                btn_text="Re-scan",
            )
            return

        if game_key not in ("elden_ring",):
            # DSR / DS3 / lite - auto-backup status banner
            self._health_icon_box.configure(fg_color=_GOOD_BG)
            self._health_icon_lbl.configure(
                text="OK", text_color=_GOOD, font=("Segoe UI", 13, "bold")
            )
            self._health_title_var.set(f"Auto-backup is on for {game_name}")
            self._health_detail_var.set(
                "Full character & world editing is available - a backup is taken before every edit"
            )
            self._banner_btn.configure(text="Back up now", command=self._on_scan)
            return

        # ER: run lightweight corruption scan in background
        self._set_banner_neutral(
            "Scanning save...", "Checking all slots for issues", btn_text="Re-scan"
        )

        def _check():
            try:
                issues = 0
                for char in save.characters:
                    try:
                        if char.is_empty():
                            continue
                        has_corr, _ = char.has_corruption(None)
                        if has_corr:
                            issues += 1
                    except Exception:
                        pass

                def _apply(n):
                    if n == 0:
                        self._health_icon_box.configure(fg_color=_GOOD_BG)
                        self._health_icon_lbl.configure(
                            text="OK", text_color=_GOOD, font=("Segoe UI", 13, "bold")
                        )
                        self._health_title_var.set("Your save looks healthy")
                        self._health_detail_var.set(
                            "Last scanned just now - 0 problems found - auto-backup is on"
                        )
                        self._banner_btn.configure(
                            text="Re-scan", command=self._on_scan
                        )
                    else:
                        self._health_icon_box.configure(fg_color=_WARN_BG)
                        self._health_icon_lbl.configure(
                            text=str(n), text_color=_WARN, font=("Segoe UI", 16, "bold")
                        )
                        self._health_title_var.set(
                            f"{n} issue{'s' if n > 1 else ''} detected"
                        )
                        self._health_detail_var.set(
                            "Open Save Fixer and select a character to view and apply fixes"
                        )
                        self._banner_btn.configure(
                            text="Fix now",
                            command=lambda: self._on_navigate("Save Fixer"),
                        )

                self._parent.after(0, lambda: _apply(issues))
            except Exception:
                pass

        threading.Thread(target=_check, daemon=True).start()

    def _set_banner_neutral(self, title: str, detail: str, btn_text: str) -> None:
        if self._health_icon_box:
            self._health_icon_box.configure(fg_color=_PANEL2)
        if self._health_icon_lbl:
            self._health_icon_lbl.configure(
                text="?", text_color=_FAINT, font=("Segoe UI", 18, "bold")
            )
        self._health_title_var.set(title)
        self._health_detail_var.set(detail)
        if hasattr(self, "_banner_btn"):
            self._banner_btn.configure(text=btn_text, command=self._on_scan)

    def _refresh_cards(self) -> None:
        if self._cards_outer is None:
            return
        for w in self._cards_outer.winfo_children():
            w.destroy()

        game_key = self._get_game_key()
        game_name = self._get_game_name()
        is_lite = game_key not in ("elden_ring", "dark_souls_remastered")

        # Section label text
        self._section_label.configure(
            text="AVAILABLE NOW" if is_lite else "WHAT DO YOU WANT TO DO?"
        )

        # Lite "coming soon" notice above cards
        if is_lite:
            notice = ctk.CTkFrame(
                self._cards_outer, fg_color=_WARN_BG, corner_radius=_CARD_R
            )
            notice.pack(fill="x", pady=(0, 14))
            ni = ctk.CTkFrame(notice, fg_color="transparent")
            ni.pack(fill="x", padx=16, pady=14)
            ctk.CTkLabel(
                ni,
                text=f"Save editing for {game_name} is in progress",
                font=("Segoe UI", 14, "bold"),
                text_color=_FG,
                anchor="w",
            ).pack(anchor="w")
            ctk.CTkLabel(
                ni,
                text="For now you can fully protect and move your saves - character editing is coming in a later update.",
                font=("Segoe UI", 12),
                text_color=_FG_ALT,
                anchor="w",
                wraplength=700,
            ).pack(anchor="w", pady=(4, 0))

        cols = 3
        cards = _cards_for(game_key)
        for i, (title, desc, target) in enumerate(cards):
            row = i // cols
            col = i % cols
            self._cards_outer.grid_columnconfigure(col, weight=1, uniform="cc")
            self._cards_outer.grid_rowconfigure(row, minsize=110)

            card = ctk.CTkFrame(
                self._cards_outer,
                fg_color=_PANEL,
                corner_radius=_CARD_R,
                cursor="hand2",
            )
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=14, pady=14)

            icon_box = ctk.CTkFrame(
                inner, width=36, height=36, fg_color=_PANEL2, corner_radius=9
            )
            icon_box.pack(anchor="w")
            icon_box.pack_propagate(False)

            ctk.CTkLabel(
                inner,
                text=title,
                font=("Segoe UI", 13, "bold"),
                text_color=_FG,
                anchor="w",
            ).pack(anchor="w", pady=(10, 0))
            ctk.CTkLabel(
                inner,
                text=desc,
                font=("Segoe UI", 11),
                text_color=_FAINT,
                anchor="w",
                wraplength=220,
            ).pack(anchor="w", pady=(2, 0))

            def cmd(t=target):
                return self._on_navigate(t)

            for w in (card, inner, icon_box):
                w.bind("<Button-1>", lambda e, c=cmd: c())
                w.bind("<Enter>", lambda e, f=card: f.configure(fg_color="#252536"))
                w.bind("<Leave>", lambda e, f=card: f.configure(fg_color=_PANEL))
