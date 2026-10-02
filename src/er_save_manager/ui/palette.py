"""Accent colors shared by every window, as (light mode, dark mode) pairs.

Purple follows the CTk "lavender" theme loaded in gui.py, so explicit colors
match every default button, switch and checkbox. Brighter accents use
Catppuccin Blue (Latte, Mocha), which sits next to the lavender purple and is
already the toast's info color. Loadout Mode keeps Catppuccin Sky, so that
state stands apart from ordinary blue buttons.

Pairs work directly as CTk colors; tk and ttk widgets take one color per
mode, chosen with pick().
"""

from __future__ import annotations

import customtkinter as ctk

# Lavender theme button colors: light purple, purple, hover.
PURPLE = ("#B19CD9", "#9370DB")
PURPLE_HOVER = ("#9370DB", "#7A5DC7")
# Accent text, labels and borders on regular backgrounds.
PURPLE_TEXT = ("#7A5DC7", "#B19CD9")
# Selected cells, list rows and tree rows.
PURPLE_SELECT = ("#B19CD9", "#7A5DC7")
# Row hover and the selected card in a list of cards; dark enough in dark
# mode to keep white text crisp.
PURPLE_TINT = ("#D4C6EF", "#3B2F5C")
# Text on PURPLE fills. The lavender theme uses light text in both modes,
# which is faint on light purple, so light mode gets Mocha Base.
ON_PURPLE = ("#1E1E2E", "#DCE4EE")

# Catppuccin Blue for highlighted actions: Frappe in light mode (as light as
# the lavender purple), Mocha in dark mode.
BLUE = ("#8CAAEE", "#89B4FA")
BLUE_HOVER = ("#7393DB", "#789EDC")
# Text on a BLUE fill (Mocha Base): both blues are light.
ON_BLUE = ("#1E1E2E", "#1E1E2E")
# Link and info text on regular backgrounds.
BLUE_TEXT = ("#1E66F5", "#89B4FA")
# Background of info boxes and tags.
BLUE_TINT = ("#CFDCF5", "#313953")

# Catppuccin Sky (Latte, Mocha), Sapphire on hover: Loadout Mode.
SKY = ("#04A5E5", "#89DCEB")
SKY_HOVER = ("#209FB5", "#74C7EC")
ON_SKY = ("#1E1E2E", "#1E1E2E")

# Toast fills, readable with TOAST_TEXT in both modes.
TOAST_COLORS = {
    "success": "#B19CD9",  # lavender light purple
    "info": "#89B4FA",  # Catppuccin Mocha Blue
    "warning": "#F9E2AF",  # Catppuccin Mocha Yellow
    "error": "#F38BA8",  # Catppuccin Mocha Red
}
TOAST_TEXT = "#11111B"


def apply_theme_overrides() -> None:
    """Adjust the loaded CTk theme; call after set_default_color_theme and
    before any widget is created.

    Widgets filled with the theme purple get ON_PURPLE text, so light mode
    is no longer light text on light purple.
    """
    theme = ctk.ThemeManager.theme
    for widget in ("CTkButton", "CTkSegmentedButton", "CTkOptionMenu"):
        if widget in theme:
            theme[widget]["text_color"] = list(ON_PURPLE)


def pick(pair: tuple[str, str]) -> str:
    """The color of a (light, dark) pair for the current appearance mode."""
    return pair[1] if ctk.get_appearance_mode() == "Dark" else pair[0]
