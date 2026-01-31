"""Theme management for light/dark mode support."""

from tkinter import ttk


class ThemeManager:
    """Manages application themes (light/dark mode)."""

    # Light mode colors - Catppuccin Latte
    LIGHT_COLORS = {
        "bg": "#eff1f5",
        "fg": "#4c4f69",
        "fg_alt": "#6c6f85",
        "accent": "#985ce7",  # Mauve
        "accent_hover": "#a06aec",
        "bg_alt": "#e6e9ef",
        "border": "#ccd0da",
        "button_bg": "#eff1f5",
        "button_fg": "#4c4f69",
    }

    # Dark mode colors - Catppuccin Mocha
    DARK_COLORS = {
        "bg": "#1e1e2e",
        "fg": "#cdd6f4",
        "fg_alt": "#a6adc8",
        "accent": "#cba6f7",  # Mauve
        "accent_hover": "#b490e3",
        "bg_alt": "#111119",  # Darker for content boxes
        "border": "#313244",
        "button_bg": "#313244",
        "button_fg": "#cdd6f4",
    }

    def __init__(self, theme: str = "dark"):
        """Initialize theme manager.

        Args:
            theme: "bright" for light mode, "dark" for dark mode
        """
        # Force dark mode unless theme is explicitly 'bright'
        if not theme or theme not in ("bright", "dark"):
            theme = "dark"
        self.theme = theme
        self.colors = self.LIGHT_COLORS if theme == "bright" else self.DARK_COLORS

    def apply_theme(self, style: ttk.Style):
        """Apply theme to ttk.Style.

        Args:
            style: The ttk.Style object to configure
        """
        bg = self.colors["bg"]
        fg = self.colors["fg"]
        accent = self.colors["accent"]
        accent_hover = self.colors["accent_hover"]
        bg_alt = self.colors["bg_alt"]
        button_bg = self.colors["button_bg"]
        button_fg = self.colors["button_fg"]

        # Configure base styles
        style.configure(".", background=bg, foreground=fg)
        style.configure("TFrame", background=bg, foreground=fg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure(
            "TLabelFrame", background=bg, foreground=fg, borderwidth=2, relief="groove"
        )
        style.configure("TLabelFrame.Label", background=bg, foreground=fg)

        # Button styles - ALL buttons have pink hover
        style.configure(
            "TButton",
            background=button_bg,
            foreground=button_fg,
            borderwidth=1,
            relief="solid",
        )
        style.map(
            "TButton",
            background=[("active", accent), ("pressed", accent_hover)],
            foreground=[("active", button_fg)],
        )

        # Accent button - also pink hover
        style.configure(
            "Accent.TButton",
            background=accent,
            foreground=button_fg,
            padding=6,
            relief="solid",
        )
        style.map(
            "Accent.TButton",
            background=[("active", accent_hover), ("pressed", accent)],
            foreground=[("active", button_fg)],
        )

        # Entry styles
        style.configure(
            "TEntry",
            fieldbackground=bg_alt,
            foreground=fg,
            borderwidth=1,
            relief="solid",
            padding=2,
        )
        style.configure(
            "TCombobox", fieldbackground=bg_alt, foreground=fg, borderwidth=1
        )

        # Text widget colors
        style.configure("TText", background=bg_alt, foreground=fg, borderwidth=1)

        # Spinbox
        style.configure(
            "TSpinbox", fieldbackground=bg_alt, foreground=fg, borderwidth=1
        )

        # Checkbutton and Radiobutton - with pink hover
        style.configure("TCheckbutton", background=bg, foreground=fg)
        style.map("TCheckbutton", background=[("active", bg)])
        style.configure("TRadiobutton", background=bg, foreground=fg)
        style.map("TRadiobutton", background=[("active", bg)])

        # Treeview with border
        style.configure(
            "Treeview",
            background=bg_alt,
            foreground=fg,
            fieldbackground=bg_alt,
            borderwidth=2,
            relief="solid",
        )
        style.configure(
            "Treeview.Heading",
            background=button_bg,
            foreground=button_fg,
            borderwidth=1,
            relief="solid",
        )
        style.map(
            "Treeview",
            background=[("selected", accent)],
            foreground=[("selected", button_fg)],
        )

        # Notebook (tabs)
        style.configure("TNotebook", background=bg, borderwidth=1, relief="solid")
        style.configure(
            "TNotebook.Tab",
            background=button_bg,
            foreground=button_fg,
            padding=[10, 5],
            borderwidth=1,
            relief="raised",
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", accent)],
            foreground=[("selected", button_fg)],
        )

        # Panedwindow
        style.configure("TPanedwindow", background=bg, borderwidth=1, relief="solid")

        # Scrollbar
        style.configure("TScrollbar", background=button_bg, borderwidth=1)
        style.map("TScrollbar", background=[("active", accent)])

    def apply_tk_widget_colors(self, widget):
        """Apply theme colors to a tk widget and all its children.

        This is used for non-ttk widgets like tk.Listbox, tk.Frame, etc.

        Args:
            widget: The tk widget to apply colors to
        """
        import tkinter as tk_module

        bg = self.colors["bg"]
        fg = self.colors["fg"]
        bg_alt = self.colors["bg_alt"]
        accent = self.colors["accent"]

        # Configure the widget itself
        if isinstance(widget, tk_module.Listbox):
            widget.configure(
                background=bg_alt,
                foreground=fg,
                selectbackground=accent,
                selectforeground=fg,
                highlightthickness=0,
            )
        elif isinstance(widget, tk_module.Text):
            widget.configure(
                background=bg_alt,
                foreground=fg,
                insertbackground=fg,
                highlightthickness=0,
            )
        elif isinstance(widget, tk_module.Frame):
            widget.configure(background=bg)
        elif isinstance(widget, (tk_module.Label, tk_module.Button)):
            widget.configure(background=bg, foreground=fg)

        # Recursively apply to children
        try:
            for child in widget.winfo_children():
                self.apply_tk_widget_colors(child)
        except Exception:
            pass

    def set_theme(self, theme: str):
        """Change to a different theme.

        Args:
            theme: "bright" for light mode, "dark" for dark mode
        """
        # Force dark mode unless theme is explicitly 'bright'
        if not theme or theme not in ("bright", "dark"):
            theme = "dark"
        self.theme = theme
        self.colors = self.LIGHT_COLORS if theme == "bright" else self.DARK_COLORS

    def get_color(self, key: str) -> str:
        """Get a color from current theme.

        Args:
            key: Color key (e.g., "bg", "fg", "accent")

        Returns:
            Hex color string
        """
        return self.colors.get(key, "#000000")
