"""
Sidebar navigation widget.

Defines screen groups per game and renders grouped nav buttons with a
Settings button pinned to the bottom.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import customtkinter as ctk

# ---------------------------------------------------------------------------
# Group / layout definitions
# ---------------------------------------------------------------------------

@dataclass
class SidebarGroup:
    label: str
    screens: list[str]


# Per-game sidebar layout.  Each entry is a list of SidebarGroup objects.
# Settings is intentionally absent; it is always pinned to the bottom.
SIDEBAR_LAYOUT: dict[str, list[SidebarGroup]] = {
    "elden_ring": [
        SidebarGroup("Rescue", ["Save Fixer"]),
        SidebarGroup("Character", ["Character Management", "Character Editor", "Appearance"]),
        SidebarGroup("World", ["World State", "Event Flags", "Gestures"]),
        SidebarGroup("Tools", ["SteamID Patcher", "Advanced Tools"]),
    ],
    "dark_souls_remastered": [
        SidebarGroup("Inspect", ["Save Inspector"]),
        SidebarGroup("Character", ["Character Editor", "Inventory", "NPCs & Bosses"]),
        SidebarGroup("World", ["Event Flags", "World State"]),
    ],
    "dark_souls_3": [
        SidebarGroup("Inspect", ["Save Inspector"]),
        SidebarGroup("Character", ["Character Editor", "Inventory"]),
        SidebarGroup("World", ["Bosses", "World State"]),
        SidebarGroup("Tools", ["SteamID Patcher"]),
    ],
}

# Games not in SIDEBAR_LAYOUT get a single unlabelled group with only SteamID Patcher.
_LITE_SCREENS: list[SidebarGroup] = [
    SidebarGroup("Tools", ["SteamID Patcher"]),
]


def get_layout(game_key: str) -> list[SidebarGroup]:
    return SIDEBAR_LAYOUT.get(game_key, _LITE_SCREENS)


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

_SETTINGS_SCREEN = "Settings"

_BTN_WIDTH = 168
_BTN_HEIGHT = 32
_GROUP_LABEL_PAD_TOP = 12
_GROUP_LABEL_PAD_BOT = 2


class Sidebar(ctk.CTkFrame):
    """
    Left-side navigation panel.

    Renders grouped screen buttons for the active game profile.
    Settings is pinned to the bottom and always visible.

    Args:
        parent:    Parent widget.
        game_key:  Active game key from game_profiles.
        on_select: Called with the screen name when a button is clicked.
    """

    def __init__(
        self,
        parent,
        game_key: str,
        on_select: Callable[[str], None],
    ):
        super().__init__(parent, corner_radius=0, width=_BTN_WIDTH + 16)
        self.grid_propagate(False)

        self._on_select = on_select
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._active: str | None = None

        self._build(game_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select(self, screen_name: str) -> None:
        """Highlight the button for screen_name and update internal state."""
        if self._active == screen_name:
            return
        if self._active and self._active in self._buttons:
            self._set_active_style(self._buttons[self._active], active=False)
        self._active = screen_name
        if screen_name in self._buttons:
            self._set_active_style(self._buttons[screen_name], active=True)

    def rebuild(self, game_key: str) -> None:
        """Tear down and rebuild buttons for a different game."""
        for widget in self.winfo_children():
            widget.destroy()
        self._buttons.clear()
        self._active = None
        self._build(game_key)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build(self, game_key: str) -> None:
        self.grid_rowconfigure(0, weight=1)   # scrollable nav area expands
        self.grid_rowconfigure(1, weight=0)   # settings pin stays at bottom
        self.grid_columnconfigure(0, weight=1)

        # Nav area (top)
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 0))

        groups = get_layout(game_key)
        for group in groups:
            ctk.CTkLabel(
                nav,
                text=group.label.upper(),
                font=("Segoe UI", 9, "bold"),
                anchor="w",
                text_color=("gray50", "gray55"),
            ).pack(fill="x", padx=4, pady=(_GROUP_LABEL_PAD_TOP, _GROUP_LABEL_PAD_BOT))

            for screen in group.screens:
                btn = ctk.CTkButton(
                    nav,
                    text=screen,
                    width=_BTN_WIDTH,
                    height=_BTN_HEIGHT,
                    anchor="w",
                    fg_color="transparent",
                    text_color=("gray20", "gray90"),
                    hover_color=("gray80", "gray30"),
                    command=lambda s=screen: self._on_click(s),
                )
                btn.pack(fill="x", pady=1)
                self._buttons[screen] = btn

        # Divider
        ctk.CTkFrame(self, height=1, fg_color=("gray75", "gray30")).grid(
            row=1, column=0, sticky="ew", padx=8, pady=(4, 0)
        )

        # Settings pin (bottom)
        settings_btn = ctk.CTkButton(
            self,
            text=_SETTINGS_SCREEN,
            width=_BTN_WIDTH,
            height=_BTN_HEIGHT,
            anchor="w",
            fg_color="transparent",
            text_color=("gray20", "gray90"),
            hover_color=("gray80", "gray30"),
            command=lambda: self._on_click(_SETTINGS_SCREEN),
        )
        settings_btn.grid(row=2, column=0, padx=12, pady=(4, 8), sticky="ew")
        self._buttons[_SETTINGS_SCREEN] = settings_btn

    def _on_click(self, screen_name: str) -> None:
        self.select(screen_name)
        self._on_select(screen_name)

    def _set_active_style(self, btn: ctk.CTkButton, *, active: bool) -> None:
        if active:
            btn.configure(
                fg_color=("gray75", "gray35"),
                text_color=("gray5", "white"),
            )
        else:
            btn.configure(
                fg_color="transparent",
                text_color=("gray20", "gray90"),
            )
