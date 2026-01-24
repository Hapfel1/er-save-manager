"""Settings tab for application configuration."""

import tkinter as tk
from tkinter import messagebox, ttk

from er_save_manager.ui.settings import get_settings


class SettingsTab:
    """UI tab for application settings."""

    def __init__(self, parent):
        """Initialize settings tab."""
        self.parent = parent
        self.settings = get_settings()

    def setup_ui(self):
        """Create settings UI."""
        # Main container
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(
            title_frame,
            text="Settings",
            font=("Segoe UI", 16, "bold"),
        ).pack(side=tk.LEFT)

        ttk.Button(
            title_frame,
            text="Reset to Defaults",
            command=self.reset_to_defaults,
        ).pack(side=tk.RIGHT)

        # Settings sections
        self._create_general_settings(main_frame)
        self._create_backup_settings(main_frame)
        self._create_ui_settings(main_frame)

    def _create_general_settings(self, parent):
        """Create general settings section."""
        frame = ttk.LabelFrame(parent, text="General", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))

        # EAC Warning
        self.show_eac_warning_var = tk.BooleanVar(
            value=self.settings.get("show_eac_warning", True)
        )
        ttk.Checkbutton(
            frame,
            text="Show EAC warning when loading .sl2 files",
            variable=self.show_eac_warning_var,
            command=lambda: self.settings.set(
                "show_eac_warning", self.show_eac_warning_var.get()
            ),
        ).pack(anchor=tk.W, pady=5)

        ttk.Label(
            frame,
            text="Disabling this will skip the anti-cheat warning dialog.",
            font=("Segoe UI", 9),
            foreground="gray",
        ).pack(anchor=tk.W, padx=20)

        # Remember Last Location
        self.remember_location_var = tk.BooleanVar(
            value=self.settings.get("remember_last_location", True)
        )
        ttk.Checkbutton(
            frame,
            text="Remember last opened save file location",
            variable=self.remember_location_var,
            command=lambda: self.settings.set(
                "remember_last_location", self.remember_location_var.get()
            ),
        ).pack(anchor=tk.W, pady=5)

        # Linux Save Location Warning
        self.show_linux_save_warning_var = tk.BooleanVar(
            value=self.settings.get("show_linux_save_warning", True)
        )
        ttk.Checkbutton(
            frame,
            text="Show Linux save location warnings (non-default compatdata)",
            variable=self.show_linux_save_warning_var,
            command=lambda: self.settings.set(
                "show_linux_save_warning", self.show_linux_save_warning_var.get()
            ),
        ).pack(anchor=tk.W, pady=5)

        ttk.Label(
            frame,
            text="Linux: Warns when save is not in default compatdata folder.",
            font=("Segoe UI", 9),
            foreground="gray",
        ).pack(anchor=tk.W, padx=20)

    def _create_backup_settings(self, parent):
        """Create backup settings section."""
        frame = ttk.LabelFrame(parent, text="Backups", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))

        # Auto Backup
        self.auto_backup_var = tk.BooleanVar(
            value=self.settings.get("auto_backup", True)
        )
        ttk.Checkbutton(
            frame,
            text="Create backups automatically before modifications",
            variable=self.auto_backup_var,
            command=lambda: self.settings.set(
                "auto_backup", self.auto_backup_var.get()
            ),
        ).pack(anchor=tk.W, pady=5)

        # Backup on Save
        self.backup_on_save_var = tk.BooleanVar(
            value=self.settings.get("backup_on_save", True)
        )
        ttk.Checkbutton(
            frame,
            text="Create backup when saving changes",
            variable=self.backup_on_save_var,
            command=lambda: self.settings.set(
                "backup_on_save", self.backup_on_save_var.get()
            ),
        ).pack(anchor=tk.W, pady=5)

        # Max Backups
        max_backup_frame = ttk.Frame(frame)
        max_backup_frame.pack(fill=tk.X, pady=5)

        ttk.Label(max_backup_frame, text="Maximum backups to keep:").pack(side=tk.LEFT)

        self.max_backups_var = tk.IntVar(value=self.settings.get("max_backups", 50))
        max_backup_spinner = ttk.Spinbox(
            max_backup_frame,
            from_=10,
            to=200,
            textvariable=self.max_backups_var,
            width=10,
            command=lambda: self.settings.set(
                "max_backups", self.max_backups_var.get()
            ),
        )
        max_backup_spinner.pack(side=tk.LEFT, padx=10)

        ttk.Label(
            frame,
            text="Older backups are automatically deleted when this limit is reached.",
            font=("Segoe UI", 9),
            foreground="gray",
        ).pack(anchor=tk.W, padx=20)

    def _create_ui_settings(self, parent):
        """Create UI settings section."""
        frame = ttk.LabelFrame(parent, text="User Interface", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))

        # Theme (placeholder for future)
        theme_frame = ttk.Frame(frame)
        theme_frame.pack(fill=tk.X, pady=5)

        ttk.Label(theme_frame, text="Theme:").pack(side=tk.LEFT)

        self.theme_var = tk.StringVar(value=self.settings.get("theme", "default"))
        theme_combo = ttk.Combobox(
            theme_frame,
            textvariable=self.theme_var,
            values=["default"],
            state="readonly",
            width=15,
        )
        theme_combo.pack(side=tk.LEFT, padx=10)
        theme_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self.settings.set("theme", self.theme_var.get()),
        )

        ttk.Label(
            frame,
            text="(Dark theme support coming soon)",
            font=("Segoe UI", 9),
            foreground="gray",
        ).pack(anchor=tk.W, padx=20)

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        if messagebox.askyesno(
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\n\n"
            "This cannot be undone.",
            icon="warning",
        ):
            self.settings.reset_to_defaults()

            # Update UI
            self.show_eac_warning_var.set(True)
            self.remember_location_var.set(True)
            self.show_linux_save_warning_var.set(True)
            self.auto_backup_var.set(True)
            self.backup_on_save_var.set(True)
            self.max_backups_var.set(50)
            self.theme_var.set("default")

            messagebox.showinfo("Success", "Settings have been reset to defaults.")
