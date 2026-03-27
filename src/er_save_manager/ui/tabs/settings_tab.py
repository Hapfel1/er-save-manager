"""Settings tab for application configuration."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.settings import get_settings
from er_save_manager.ui.utils import bind_mousewheel


class SettingsTab:
    """UI tab for application settings."""

    def __init__(
        self,
        parent,
        get_save_path_callback=None,
        get_default_save_path_callback=None,
        active_game: str = "elden_ring",
    ):
        self.parent = parent
        self.settings = get_settings()
        self.get_save_path = get_save_path_callback
        self.get_default_save_path = get_default_save_path_callback
        self.active_game = active_game

        # Per-game auto-backup path vars - populated in setup_ui
        self._auto_backup_path_vars: dict[str, tk.StringVar] = {}
        self._auto_backup_enabled_vars: dict[str, tk.BooleanVar] = {}

    def setup_ui(self):
        theme_value = self.settings.get("theme", None)
        if theme_value is None or theme_value == "dark":
            ctk.set_appearance_mode("dark")
        elif theme_value == "bright":
            ctk.set_appearance_mode("light")

        scroll_frame = ctk.CTkScrollableFrame(self.parent, corner_radius=12)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        bind_mousewheel(scroll_frame)

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

        self._create_general_settings(scroll_frame)
        self._create_backup_settings(scroll_frame)
        self._create_ui_settings(scroll_frame)

    def _create_general_settings(self, parent):
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text="General",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        # EAC Warning - Elden Ring only
        if self.active_game == "elden_ring":
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
        else:
            self.show_eac_warning_var = tk.BooleanVar(value=False)

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
            text="Linux: Warns when save is not in the default compatdata folder.",
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
                "show_update_notifications",
                self.show_update_notifications_var.get(),
            ),
        ).pack(anchor="w", padx=12, pady=5)
        ctk.CTkLabel(
            frame,
            text="Check for new versions and show notification dialog.",
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 12))

    def _create_backup_settings(self, parent):
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
            text="Compress backups (zip) to save disk space",
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

        # Max Backups
        max_backup_frame = ctk.CTkFrame(frame, fg_color="transparent")
        max_backup_frame.pack(fill="x", padx=12, pady=(0, 5))
        ctk.CTkLabel(max_backup_frame, text="Maximum backups to keep:").pack(
            side="left", padx=(0, 10)
        )
        self.max_backups_var = tk.StringVar(
            value=str(self.settings.get("max_backups", 50))
        )
        ctk.CTkEntry(
            max_backup_frame, textvariable=self.max_backups_var, width=80
        ).pack(side="left")

        def save_backup_limit(*args):
            try:
                value = int(self.max_backups_var.get())
                if value > 0:
                    self.settings.set("max_backups", value)
            except ValueError:
                pass

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

        # Auto-backup per game
        self._create_auto_backup_section(frame)

    def _create_auto_backup_section(self, parent):
        """Auto-backup configuration for the currently active game only."""
        from er_save_manager.games.game_profiles import PROFILES_BY_KEY

        profile = PROFILES_BY_KEY.get(self.active_game)
        if profile is None:
            return

        sep = ctk.CTkFrame(parent, height=1, fg_color=("gray70", "gray35"))
        sep.pack(fill="x", padx=12, pady=(4, 10))

        ctk.CTkLabel(
            parent,
            text="Auto-Backup on Game Launch",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", padx=12, pady=(0, 4))

        ctk.CTkLabel(
            parent,
            text=(
                f"Automatically create a backup of your {profile.name} save "
                "whenever the game launches."
            ),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
            wraplength=520,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 8))

        auto_backup_cfg: dict = self.settings.get("auto_backup_games", {})
        game_cfg = auto_backup_cfg.get(profile.key, {})
        enabled = game_cfg.get("enabled", False)
        save_path_str = game_cfg.get("save_path", "")

        game_frame = ctk.CTkFrame(parent, corner_radius=8, fg_color=("gray90", "gray18"))
        game_frame.pack(fill="x", padx=12, pady=(0, 6))

        header_row = ctk.CTkFrame(game_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=10, pady=(8, 4))

        enabled_var = tk.BooleanVar(value=enabled)
        self._auto_backup_enabled_vars[profile.key] = enabled_var

        ctk.CTkCheckBox(
            header_row,
            text=f"Enable auto-backup for {profile.name}",
            variable=enabled_var,
            font=("Segoe UI", 11),
            command=lambda k=profile.key: self._on_game_auto_backup_toggle(k),
        ).pack(side="left")

        path_row = ctk.CTkFrame(game_frame, fg_color="transparent")
        path_row.pack(fill="x", padx=10, pady=(0, 8))

        path_var = tk.StringVar(value=save_path_str or "(not configured)")
        self._auto_backup_path_vars[profile.key] = path_var

        ctk.CTkLabel(
            path_row,
            text="Monitored save file:",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w")

        file_row = ctk.CTkFrame(game_frame, fg_color="transparent")
        file_row.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(
            file_row,
            textvariable=path_var,
            font=("Consolas", 10),
            text_color=("gray50", "gray60"),
            wraplength=420,
            justify="left",
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            file_row,
            text="Choose...",
            width=80,
            command=lambda k=profile.key, p=profile: self._choose_game_auto_backup_save(k, p),
        ).pack(side="right", padx=(6, 0))

    def _on_game_auto_backup_toggle(self, game_key: str):
        enabled = self._auto_backup_enabled_vars[game_key].get()
        auto_backup_cfg: dict = dict(self.settings.get("auto_backup_games", {}))
        game_cfg = dict(auto_backup_cfg.get(game_key, {}))
        game_cfg["enabled"] = enabled

        if enabled:
            save_path = game_cfg.get("save_path", "")
            if not save_path or not Path(save_path).exists():
                CTkMessageBox.showwarning(
                    "Configure Save File",
                    "Please choose which save file to monitor for auto-backup.",
                    parent=self.parent,
                )
                # Find the profile
                from er_save_manager.games.game_profiles import PROFILES_BY_KEY

                profile = PROFILES_BY_KEY.get(game_key)
                if profile:
                    self._choose_game_auto_backup_save(game_key, profile)

        auto_backup_cfg[game_key] = game_cfg
        self.settings.set("auto_backup_games", auto_backup_cfg)

    def _choose_game_auto_backup_save(self, game_key: str, profile):
        import tkinter.filedialog as filedialog

        from er_save_manager.platform.utils import PlatformUtils

        # Offer auto-detected saves first
        found = PlatformUtils.find_all_save_files(profile)
        if found:
            options = [str(p) for p in found]
            if len(options) == 1:
                choice = CTkMessageBox.askyesno(
                    "Use Detected Save",
                    f"Found save file:\n\n{options[0]}\n\nUse this for auto-backup?",
                    parent=self.parent,
                )
                if choice:
                    self._set_game_auto_backup_path(game_key, options[0])
                    return
            # Multiple found - show simple picker
            elif len(options) > 1:
                from er_save_manager.ui.utils import force_render_dialog

                selected = [None]
                dlg = ctk.CTkToplevel(self.parent)
                dlg.title(f"Select Save - {profile.name}")
                dlg.geometry("520x300")
                dlg.resizable(False, False)
                force_render_dialog(dlg)
                dlg.grab_set()

                ctk.CTkLabel(
                    dlg,
                    text="Select save file to monitor:",
                    font=("Segoe UI", 11),
                ).pack(pady=(15, 8), padx=15)

                sf = ctk.CTkScrollableFrame(dlg, corner_radius=8)
                sf.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

                for opt in options:

                    def make_sel(v):
                        def _sel():
                            selected[0] = v
                            dlg.destroy()

                        return _sel

                    ctk.CTkButton(
                        sf,
                        text=opt,
                        font=("Consolas", 10),
                        fg_color="transparent",
                        text_color=("#2a2a2a", "#e5e5f5"),
                        hover_color=("#c9a0dc", "#3b2f5c"),
                        anchor="w",
                        command=make_sel(opt),
                    ).pack(fill=tk.X, padx=6, pady=3)

                ctk.CTkButton(
                    dlg,
                    text="Browse...",
                    width=100,
                    command=lambda: [
                        setattr(selected, "__browse__", True),
                        dlg.destroy(),
                    ],
                ).pack(side=tk.LEFT, padx=15, pady=(0, 12))
                ctk.CTkButton(dlg, text="Cancel", width=80, command=dlg.destroy).pack(
                    side=tk.RIGHT, padx=15, pady=(0, 12)
                )
                dlg.wait_window()

                if selected[0]:
                    self._set_game_auto_backup_path(game_key, selected[0])
                    return

        # Fallback: file browser
        ext_str = " ".join(f"*{e}" for e in profile.extensions)
        file_path = filedialog.askopenfilename(
            title=f"Choose Save File for Auto-Backup - {profile.name}",
            filetypes=[(f"{profile.name} Save", ext_str), ("All files", "*.*")],
            parent=self.parent,
        )
        if file_path:
            self._set_game_auto_backup_path(game_key, file_path)

    def _set_game_auto_backup_path(self, game_key: str, file_path: str):
        file_path = str(Path(file_path).resolve())
        auto_backup_cfg: dict = dict(self.settings.get("auto_backup_games", {}))
        game_cfg = dict(auto_backup_cfg.get(game_key, {}))
        game_cfg["save_path"] = file_path
        auto_backup_cfg[game_key] = game_cfg
        self.settings.set("auto_backup_games", auto_backup_cfg)
        if game_key in self._auto_backup_path_vars:
            self._auto_backup_path_vars[game_key].set(file_path)

    def _create_ui_settings(self, parent):
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text="User Interface",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        theme_frame = ctk.CTkFrame(frame, fg_color="transparent")
        theme_frame.pack(fill="x", padx=12, pady=5)

        ctk.CTkLabel(theme_frame, text="Theme:").pack(side="left", padx=(0, 10))

        theme_value = self.settings.get("theme", "dark")
        if theme_value == "default":
            theme_value = "bright"
        self.theme_var = tk.StringVar(value=theme_value)
        ctk.CTkComboBox(
            theme_frame,
            variable=self.theme_var,
            values=["bright", "dark"],
            state="readonly",
            width=150,
            command=self._on_theme_changed,
        ).pack(side="left")

        ctk.CTkLabel(
            frame,
            text="(Restart required for full theme application)",
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 12))

    def reset_to_defaults(self):
        if CTkMessageBox.askyesno(
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\n\nThis cannot be undone.",
            parent=self.parent,
        ):
            self.settings.reset_to_defaults()
            if self.active_game == "elden_ring" and hasattr(
                self, "show_eac_warning_var"
            ):
                self.show_eac_warning_var.set(True)
            self.remember_location_var.set(True)
            self.show_linux_save_warning_var.set(True)
            self.show_update_notifications_var.set(True)
            self.show_backup_pruning_warning_var.set(True)
            self.compress_backups_var.set(True)
            self.max_backups_var.set("50")
            self.theme_var.set("dark")
            for var in self._auto_backup_enabled_vars.values():
                var.set(False)
            for var in self._auto_backup_path_vars.values():
                var.set("(not configured)")
            CTkMessageBox.showinfo(
                "Success", "Settings have been reset to defaults.", parent=self.parent
            )

    def _on_theme_changed(self, value=None):
        theme = self.theme_var.get()
        self.settings.set("theme", theme)
        CTkMessageBox.showinfo(
            "Theme Changed",
            f"Theme changed to {theme}.\n\nPlease restart the application for full effect.",
            parent=self.parent,
        )
