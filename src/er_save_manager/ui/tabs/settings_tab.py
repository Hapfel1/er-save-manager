"""Settings tab for application configuration (customtkinter version)."""

import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.settings import get_settings
from er_save_manager.ui.utils import bind_mousewheel


class SettingsTab:
    """UI tab for application settings (customtkinter version)."""

    def __init__(self, parent):
        """Initialize settings tab."""
        self.parent = parent
        self.settings = get_settings()

    def setup_ui(self):
        """Create settings UI."""
        # Set dark mode on startup if theme is not set or is dark
        theme_value = self.settings.get("theme", None)
        if theme_value is None or theme_value == "dark":
            ctk.set_appearance_mode("dark")
        elif theme_value == "bright":
            ctk.set_appearance_mode("light")

        # Main container with scrolling
        scroll_frame = ctk.CTkScrollableFrame(self.parent, corner_radius=12)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        bind_mousewheel(scroll_frame)

        # Title with reset button
        title_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            title_frame,
            text="Settings",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        ctk.CTkButton(
            title_frame,
            text="Reset to Defaults",
            command=self.reset_to_defaults,
            width=140,
        ).pack(side="right")

        # Settings sections
        self._create_general_settings(scroll_frame)
        self._create_backup_settings(scroll_frame)
        self._create_ui_settings(scroll_frame)

    def _create_general_settings(self, parent):
        """Create general settings section."""
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text="General",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        # EAC Warning
        self.show_eac_warning_var = tk.BooleanVar(
            value=self.settings.get("show_eac_warning", True)
        )
        ctk.CTkCheckBox(
            frame,
            text="Show EAC warning when loading .sl2 files",
            variable=self.show_eac_warning_var,
            command=lambda: self.settings.set(
                "show_eac_warning", self.show_eac_warning_var.get()
            ),
        ).pack(anchor="w", padx=12, pady=5)

        ctk.CTkLabel(
            frame,
            text="Disabling this will skip the anti-cheat warning dialog.",
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 10))

        # Remember Last Location
        self.remember_location_var = tk.BooleanVar(
            value=self.settings.get("remember_last_location", True)
        )
        ctk.CTkCheckBox(
            frame,
            text="Remember last opened save file location",
            variable=self.remember_location_var,
            command=lambda: self.settings.set(
                "remember_last_location", self.remember_location_var.get()
            ),
        ).pack(anchor="w", padx=12, pady=5)

        # Linux Save Location Warning
        self.show_linux_save_warning_var = tk.BooleanVar(
            value=self.settings.get("show_linux_save_warning", True)
        )
        ctk.CTkCheckBox(
            frame,
            text="Show Linux save location warnings (non-default compatdata)",
            variable=self.show_linux_save_warning_var,
            command=lambda: self.settings.set(
                "show_linux_save_warning", self.show_linux_save_warning_var.get()
            ),
        ).pack(anchor="w", padx=12, pady=5)

        ctk.CTkLabel(
            frame,
            text="Linux: Warns when save is not in default compatdata folder.",
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 12))

    def _create_backup_settings(self, parent):
        """Create backup settings section."""
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text="Backups",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        # Max Backups
        max_backup_frame = ctk.CTkFrame(frame, fg_color="transparent")
        max_backup_frame.pack(fill="x", padx=12, pady=5)

        ctk.CTkLabel(max_backup_frame, text="Maximum backups to keep:").pack(
            side="left", padx=(0, 10)
        )

        self.max_backups_var = tk.StringVar(
            value=str(self.settings.get("max_backups", 50))
        )
        spinbox = ctk.CTkEntry(
            max_backup_frame,
            textvariable=self.max_backups_var,
            width=80,
        )
        spinbox.pack(side="left")

        # Save backup limit when it changes
        def save_backup_limit(*args):
            try:
                value = int(self.max_backups_var.get())
                if value > 0:
                    self.settings.set("max_backups", value)
            except ValueError:
                pass  # Ignore non-integer values

        self.max_backups_var.trace_add("write", save_backup_limit)

        ctk.CTkLabel(
            frame,
            text="Older backups are automatically deleted when this limit is reached.",
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 10))

        # Backup Pruning Warning
        self.show_backup_pruning_warning_var = tk.BooleanVar(
            value=self.settings.get("show_backup_pruning_warning", True)
        )
        ctk.CTkCheckBox(
            frame,
            text="Show warning when backups are automatically deleted",
            variable=self.show_backup_pruning_warning_var,
            command=lambda: self.settings.set(
                "show_backup_pruning_warning",
                self.show_backup_pruning_warning_var.get(),
            ),
        ).pack(anchor="w", padx=12, pady=(0, 12))

    def _create_ui_settings(self, parent):
        """Create UI settings section."""
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text="User Interface",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        # Theme
        theme_frame = ctk.CTkFrame(frame, fg_color="transparent")
        theme_frame.pack(fill="x", padx=12, pady=5)

        ctk.CTkLabel(theme_frame, text="Theme:").pack(side="left", padx=(0, 10))

        # Map old 'default' to 'bright' for compatibility
        theme_value = self.settings.get("theme", "dark")
        if theme_value == "default":
            theme_value = "bright"
        self.theme_var = tk.StringVar(value=theme_value)
        theme_combo = ctk.CTkComboBox(
            theme_frame,
            variable=self.theme_var,
            values=["bright", "dark"],
            state="readonly",
            width=150,
            command=self._on_theme_changed,
        )
        theme_combo.pack(side="left")

        ctk.CTkLabel(
            frame,
            text="(Restart required for full theme application)",
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 12))

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        if CTkMessageBox.askyesno(
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\n\n"
            "This cannot be undone.",
        ):
            self.settings.reset_to_defaults()

            # Update UI
            self.show_eac_warning_var.set(True)
            self.remember_location_var.set(True)
            self.show_linux_save_warning_var.set(True)
            self.show_backup_pruning_warning_var.set(True)
            self.max_backups_var.set(50)
            self.theme_var.set("dark")

            CTkMessageBox.showinfo("Success", "Settings have been reset to defaults.")

    def _on_theme_changed(self, value=None):
        """Handle theme change."""
        theme = self.theme_var.get()
        # Save as 'bright' or 'dark', but if 'bright', you may want to map to 'default' for legacy compatibility
        self.settings.set("theme", theme)
        CTkMessageBox.showinfo(
            "Theme Changed",
            f"Theme changed to {theme}.\n\nPlease restart the application for full effect.",
        )
