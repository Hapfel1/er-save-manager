"""Settings tab for application configuration (customtkinter version)."""

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.settings import get_settings
from er_save_manager.ui.utils import bind_mousewheel


class SettingsTab:
    """UI tab for application settings (customtkinter version)."""

    def __init__(
        self, parent, get_save_path_callback=None, get_default_save_path_callback=None
    ):
        """Initialize settings tab."""
        self.parent = parent
        self.settings = get_settings()
        self.get_save_path = get_save_path_callback
        self.get_default_save_path = get_default_save_path_callback

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
        ).pack(anchor="w", padx=32, pady=(0, 10))

        # Update Notifications
        self.show_update_notifications_var = tk.BooleanVar(
            value=self.settings.get("show_update_notifications", True)
        )
        ctk.CTkCheckBox(
            frame,
            text="Show update notifications on startup",
            variable=self.show_update_notifications_var,
            command=lambda: self.settings.set(
                "show_update_notifications", self.show_update_notifications_var.get()
            ),
        ).pack(anchor="w", padx=12, pady=5)

        ctk.CTkLabel(
            frame,
            text="Check for new versions and show notification dialog.",
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

        # Compress Backups
        self.compress_backups_var = tk.BooleanVar(
            value=self.settings.get("compress_backups", True)
        )
        ctk.CTkCheckBox(
            frame,
            text="Compress backups (gzip) to save disk space",
            variable=self.compress_backups_var,
            command=lambda: self.settings.set(
                "compress_backups", self.compress_backups_var.get()
            ),
        ).pack(anchor="w", padx=12, pady=5)

        ctk.CTkLabel(
            frame,
            text="Reduces backup size by ~90% but takes slightly longer to create/restore.",
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 10))

        # Auto-Backup on Game Launch
        self.auto_backup_on_launch_var = tk.BooleanVar(
            value=self.settings.get("auto_backup_on_game_launch", False)
        )

        auto_backup_check = ctk.CTkCheckBox(
            frame,
            text="Auto-backup when Elden Ring launches",
            variable=self.auto_backup_on_launch_var,
            command=self._on_auto_backup_toggle,
        )
        auto_backup_check.pack(anchor="w", padx=12, pady=5)

        ctk.CTkLabel(
            frame,
            text="Automatically creates a backup before each game session.",
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 5))

        # Save file selection for auto-backup
        save_select_frame = ctk.CTkFrame(frame, fg_color="transparent")
        save_select_frame.pack(fill="x", padx=32, pady=(0, 10))

        ctk.CTkLabel(
            save_select_frame,
            text="Monitored save file:",
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 10),
        ).pack(anchor="w")

        path_display_frame = ctk.CTkFrame(save_select_frame, fg_color="transparent")
        path_display_frame.pack(fill="x", pady=(3, 0))

        auto_backup_path = self.settings.get("auto_backup_save_path", "")
        path_display_text = auto_backup_path if auto_backup_path else "(not configured)"

        self.auto_backup_path_var = tk.StringVar(value=path_display_text)
        ctk.CTkLabel(
            path_display_frame,
            textvariable=self.auto_backup_path_var,
            text_color=("gray50", "gray60"),
            font=("Consolas", 9),
            wraplength=500,
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            path_display_frame,
            text="Choose...",
            width=80,
            command=self._choose_auto_backup_save,
        ).pack(side="right", padx=(5, 0))

        # Max Backups
        max_backup_frame = ctk.CTkFrame(frame, fg_color="transparent")
        max_backup_frame.pack(fill="x", padx=12, pady=(10, 5))

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

    def _on_auto_backup_toggle(self):
        """Handle auto-backup toggle."""
        enabled = self.auto_backup_on_launch_var.get()
        self.settings.set("auto_backup_on_game_launch", enabled)

        # If enabling, check if save path is configured
        if enabled:
            save_path = self.settings.get("auto_backup_save_path", "")
            if not save_path or not Path(save_path).exists():
                CTkMessageBox.showwarning(
                    "Configure Save File",
                    "Please choose which save file to monitor for auto-backup.",
                    parent=self.parent,
                )
                self._choose_auto_backup_save()

    def _choose_auto_backup_save(self):
        """Let user choose which save file to monitor."""
        import os
        import tkinter.filedialog as filedialog
        from pathlib import Path

        # Check if there's a currently loaded save file
        current_save = None
        if self.get_save_path:
            current_save = self.get_save_path()

        # If save is loaded, offer to use it
        if current_save and Path(current_save).exists():
            result = CTkMessageBox.askyesnocancel(
                "Choose Save File",
                f"Currently loaded save file:\n\n{current_save}\n\n"
                "Would you like to use this save file for auto-backup?\n\n"
                "Yes - Use current save\n"
                "No - Browse for a different save\n"
                "Cancel - Don't configure",
                parent=self.parent,
                font_size=11,
            )

            if result is None:  # Cancel
                return
            elif result:  # Yes - use current save
                file_path = str(Path(current_save).resolve())
                self.settings.set("auto_backup_save_path", file_path)
                self.auto_backup_path_var.set(file_path)

                CTkMessageBox.showinfo(
                    "Auto-Backup Configured",
                    f"Auto-backup will now monitor:\n\n{file_path}\n\n"
                    "A backup will be created automatically when Elden Ring launches.",
                    parent=self.parent,
                )
                return
            # If No, continue to file browser below

        # Get default save location
        initial_dir = os.path.expanduser("~")
        if self.get_default_save_path:
            default_path = self.get_default_save_path()
            if default_path and Path(default_path).exists():
                initial_dir = str(default_path)

        file_path = filedialog.askopenfilename(
            title="Choose Save File for Auto-Backup",
            filetypes=[
                ("Elden Ring Save", "*.sl2;*.co2"),
                ("PC Save Files", "*.sl2"),
                ("Console Save Files", "*.co2"),
                ("All files", "*.*"),
            ],
            initialdir=initial_dir,
            parent=self.parent,
        )

        if file_path:
            file_path = str(Path(file_path).resolve())
            self.settings.set("auto_backup_save_path", file_path)
            self.auto_backup_path_var.set(file_path)

            CTkMessageBox.showinfo(
                "Auto-Backup Configured",
                f"Auto-backup will now monitor:\n\n{file_path}\n\n"
                "A backup will be created automatically when Elden Ring launches.",
                parent=self.parent,
            )

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
            parent=self.parent,
        ):
            self.settings.reset_to_defaults()

            # Update UI
            self.show_eac_warning_var.set(True)
            self.remember_location_var.set(True)
            self.show_linux_save_warning_var.set(True)
            self.show_update_notifications_var.set(True)
            self.show_backup_pruning_warning_var.set(True)
            self.compress_backups_var.set(True)
            self.auto_backup_on_launch_var.set(False)
            self.auto_backup_path_var.set("(not configured)")
            self.max_backups_var.set(50)
            self.theme_var.set("dark")

            CTkMessageBox.showinfo(
                "Success", "Settings have been reset to defaults.", parent=self.parent
            )

    def _on_theme_changed(self, value=None):
        """Handle theme change."""
        theme = self.theme_var.get()
        self.settings.set("theme", theme)
        CTkMessageBox.showinfo(
            "Theme Changed",
            f"Theme changed to {theme}.\n\nPlease restart the application for full effect.",
            parent=self.parent,
        )
