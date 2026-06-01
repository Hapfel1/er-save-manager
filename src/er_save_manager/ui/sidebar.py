"""
Sidebar navigation widget.

Defines screen groups per game. Renders grouped nav buttons with a left
accent bar on the active item and a Settings button pinned to the bottom.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import customtkinter as ctk

# Palette
_BG = "#1a1a26"
_PANEL2 = "#2c2c42"
_FG = "#e8e8f2"
_FG_ALT = "#a6adc8"
_FAINT = "#7f849c"
_ACCENT = "#cba6f7"
_BORDER = "#36364f"

_SIDEBAR_W = 200
_BTN_HEIGHT = 34
_LABEL_TOP = 14
_LABEL_BOT = 4


# ---------------------------------------------------------------------------
# Layout definitions
# ---------------------------------------------------------------------------


@dataclass
class SidebarGroup:
    label: str
    screens: list[str]


SIDEBAR_LAYOUT: dict[str, list[SidebarGroup]] = {
    "elden_ring": [
        SidebarGroup("Rescue", ["Home", "Save Fixer"]),
        SidebarGroup(
            "Character", ["Character Management", "Character Editor", "Appearance"]
        ),
        SidebarGroup("World", ["World State", "Event Flags", "Gestures"]),
        SidebarGroup("Tools", ["SteamID Patcher", "Advanced Tools"]),
    ],
    "dark_souls_remastered": [
        SidebarGroup("Inspect", ["Home", "Save Inspector"]),
        SidebarGroup("Character", ["Character Editor", "Inventory", "NPCs & Bosses"]),
        SidebarGroup("World", ["Event Flags", "World State"]),
    ],
    "dark_souls_3": [
        SidebarGroup("Inspect", ["Home", "Save Inspector"]),
        SidebarGroup("Character", ["Character Editor", "Inventory"]),
        SidebarGroup("World", ["Bosses", "World State"]),
        SidebarGroup("Tools", ["SteamID Patcher"]),
    ],
}

_LITE_SCREENS: list[SidebarGroup] = [
    SidebarGroup("Tools", ["Home", "SteamID Patcher"]),
]

_SETTINGS_SCREEN = "Settings"


def get_layout(game_key: str) -> list[SidebarGroup]:
    return SIDEBAR_LAYOUT.get(game_key, _LITE_SCREENS)


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------


class Sidebar(ctk.CTkFrame):
    """
    Left-side navigation panel.

    Active item shows a left accent bar. Settings is pinned to the bottom.

    Args:
        parent:    Parent widget.
        game_key:  Active game key.
        on_select: Called with the screen name when a button is clicked.
    """

    def __init__(self, parent, game_key: str, on_select: Callable[[str], None]):
        super().__init__(
            parent,
            corner_radius=0,
            width=_SIDEBAR_W,
            fg_color=_BG,
        )
        self.grid_propagate(False)

        self._on_select = on_select
        self._buttons: dict[str, ctk.CTkFrame] = {}  # name -> row frame
        self._btn_labels: dict[str, ctk.CTkLabel] = {}
        self._btn_bars: dict[str, ctk.CTkFrame] = {}  # name -> accent bar
        self._active: str | None = None

        self._build(game_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select(self, screen_name: str) -> None:
        """Highlight the button for screen_name."""
        if self._active == screen_name:
            return
        if self._active and self._active in self._buttons:
            self._set_active_style(self._active, active=False)
        self._active = screen_name
        if screen_name in self._buttons:
            self._set_active_style(screen_name, active=True)

    def rebuild(self, game_key: str) -> None:
        """Tear down and rebuild for a different game."""
        for widget in self.winfo_children():
            widget.destroy()
        self._buttons.clear()
        self._btn_labels.clear()
        self._btn_bars.clear()
        self._active = None
        for r in range(5):
            self.grid_rowconfigure(r, weight=0)
        self._build(game_key)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self, game_key: str) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)  # divider
        self.grid_rowconfigure(2, weight=0)  # settings
        self.grid_columnconfigure(0, weight=1)

        nav = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=_BG,
            scrollbar_button_hover_color=_PANEL2,
        )
        nav.grid(row=0, column=0, sticky="nsew")

        for group in get_layout(game_key):
            ctk.CTkLabel(
                nav,
                text=group.label.upper(),
                font=("Segoe UI", 9, "bold"),
                text_color=_FAINT,
                anchor="w",
            ).pack(fill="x", padx=16, pady=(_LABEL_TOP, _LABEL_BOT))

            for screen in group.screens:
                self._make_nav_btn(nav, screen)

        # Divider
        ctk.CTkFrame(self, height=1, fg_color=_BORDER).grid(
            row=1, column=0, sticky="ew", padx=0, pady=0
        )

        # Settings pin
        self._make_settings_btn()

    def _make_nav_btn(self, parent, screen: str) -> None:
        """Build a nav button row with a hidden left accent bar."""
        row = ctk.CTkFrame(
            parent, fg_color="transparent", height=_BTN_HEIGHT, cursor="hand2"
        )
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)

        # Left accent bar (1px wide, hidden by default)
        bar = ctk.CTkFrame(row, width=3, fg_color="transparent", corner_radius=0)
        bar.pack(side="left", fill="y")

        label = ctk.CTkLabel(
            row,
            text=screen,
            font=("Segoe UI", 12, "normal"),
            text_color=_FG_ALT,
            anchor="w",
            padx=10,
        )
        label.pack(side="left", fill="both", expand=True)

        def cmd(s=screen):
            return self._on_click(s)

        row.bind("<Button-1>", lambda e, c=cmd: c())
        label.bind("<Button-1>", lambda e, c=cmd: c())
        row.bind("<Enter>", lambda e, r=row, s=screen: self._on_hover(r, s, True))
        row.bind("<Leave>", lambda e, r=row, s=screen: self._on_hover(r, s, False))
        label.bind("<Enter>", lambda e, r=row, s=screen: self._on_hover(r, s, True))
        label.bind("<Leave>", lambda e, r=row, s=screen: self._on_hover(r, s, False))

        self._buttons[screen] = row
        self._btn_labels[screen] = label
        self._btn_bars[screen] = bar

    def _make_settings_btn(self) -> None:
        """Build the pinned Settings button with a visible border."""
        row = ctk.CTkFrame(
            self,
            fg_color="transparent",
            height=_BTN_HEIGHT + 4,
            corner_radius=8,
            cursor="hand2",
        )
        row.grid(row=2, column=0, sticky="ew", padx=12, pady=(6, 10))
        row.grid_propagate(False)

        bar = ctk.CTkFrame(row, width=3, fg_color="transparent", corner_radius=0)
        bar.pack(side="left", fill="y")

        label = ctk.CTkLabel(
            row,
            text=_SETTINGS_SCREEN,
            font=("Segoe UI", 12),
            text_color=_FG_ALT,
            anchor="w",
            padx=10,
        )
        label.pack(side="left", fill="both", expand=True)

        def cmd():
            return self._on_click(_SETTINGS_SCREEN)

        row.bind("<Button-1>", lambda e, c=cmd: c())
        label.bind("<Button-1>", lambda e, c=cmd: c())
        row.bind("<Enter>", lambda e, r=row: r.configure(fg_color=_PANEL2))
        row.bind(
            "<Leave>",
            lambda e, r=row: r.configure(
                fg_color="transparent" if _SETTINGS_SCREEN != self._active else _PANEL2
            ),
        )

        self._buttons[_SETTINGS_SCREEN] = row
        self._btn_labels[_SETTINGS_SCREEN] = label
        self._btn_bars[_SETTINGS_SCREEN] = bar

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def _on_click(self, screen_name: str) -> None:
        self.select(screen_name)
        self._on_select(screen_name)

    def _on_hover(self, row: ctk.CTkFrame, screen: str, entering: bool) -> None:
        if screen == self._active:
            return
        row.configure(fg_color=_PANEL2 if entering else "transparent")

    def _set_active_style(self, screen: str, *, active: bool) -> None:
        row = self._buttons.get(screen)
        label = self._btn_labels.get(screen)
        bar = self._btn_bars.get(screen)
        if row:
            row.configure(fg_color=_PANEL2 if active else "transparent")
        if label:
            label.configure(
                text_color=_FG if active else _FG_ALT,
                font=("Segoe UI", 12, "bold") if active else ("Segoe UI", 12, "normal"),
            )
        if bar:
            bar.configure(fg_color=_ACCENT if active else "transparent")
