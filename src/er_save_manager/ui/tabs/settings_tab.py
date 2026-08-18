"""Settings tab for application configuration."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager import i18n
from er_save_manager.i18n import t
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.settings import get_settings
from er_save_manager.ui.utils import bind_mousewheel, pick_file


class SettingsTab:
    """UI tab for application settings."""

    def __init__(
        self,
        parent,
        get_save_path_callback=None,
        get_default_save_path_callback=None,
        active_game: str = "elden_ring",
        root=None,
    ):
        self.parent = parent
        self.root = root
        self.settings = get_settings()
        self.get_save_path = get_save_path_callback
        self.get_default_save_path = get_default_save_path_callback
        self.active_game = active_game

        # Per-game auto-backup path vars - populated in setup_ui
        self._auto_backup_path_vars: dict[str, tk.StringVar] = {}
        self._auto_backup_enabled_vars: dict[str, tk.BooleanVar] = {}
        self._auto_backup_interval_enabled_vars: dict[str, tk.BooleanVar] = {}
        self._auto_backup_interval_minutes_vars: dict[str, tk.StringVar] = {}
        self._auto_backup_interval_widgets: dict[str, tuple] = {}

        # Keypress buffer for secret unlock sequence
        self._key_buffer: str = ""
        # Reference to the advanced section frame (created on unlock)
        self._advanced_frame: ctk.CTkFrame | None = None

    def _count_existing_backups(self) -> int:
        """Count backups on disk for the currently loaded save, if any."""
        if self.get_save_path is None:
            return 0
        save_path = self.get_save_path()
        if not save_path:
            return 0
        try:
            from er_save_manager.backup.manager import BackupManager

            return len(BackupManager(save_path).list_backups())
        except Exception:
            return 0

    def setup_ui(self):
        theme_value = self.settings.get("theme", None)
        if theme_value is None or theme_value == "dark":
            ctk.set_appearance_mode("dark")
        elif theme_value == "bright":
            ctk.set_appearance_mode("light")

        scroll_frame = ctk.CTkScrollableFrame(self.parent, corner_radius=12)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        bind_mousewheel(scroll_frame)
        self._scroll_frame = scroll_frame

        # Bind at the root level so keypresses are captured regardless of focus.
        # The handler checks that this tab's frame is currently visible before acting.
        bind_target = self.root if self.root is not None else self.parent
        bind_target.bind_all("<KeyPress>", self._on_key_press, add=True)

        title_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            title_frame,
            text=t("Settings"),
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        ctk.CTkButton(
            title_frame,
            text=t("Reset to Defaults"),
            command=self.reset_to_defaults,
            width=140,
        ).pack(side="right")

        self._create_general_settings(scroll_frame)
        self._create_backup_settings(scroll_frame)
        self._create_ui_settings(scroll_frame)
        self._create_launch_settings(scroll_frame)

        if self.settings.get("advanced_mode_unlocked", False):
            self._create_advanced_settings(scroll_frame)

    def _create_general_settings(self, parent):
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text=t("General"),
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        # EAC Warning - Elden Ring only
        if self.active_game == "elden_ring":
            self.show_eac_warning_var = tk.BooleanVar(
                value=self.settings.get("show_eac_warning", True)
            )
            ctk.CTkCheckBox(
                frame,
                text=t("Show EAC warning when loading .sl2 files"),
                variable=self.show_eac_warning_var,
                command=lambda: self.settings.set(
                    "show_eac_warning", self.show_eac_warning_var.get()
                ),
            ).pack(anchor="w", padx=12, pady=5)
            ctk.CTkLabel(
                frame,
                text=t("Disabling this will skip the anti-cheat warning dialog."),
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
            text=t("Remember last opened save file location"),
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
            text=t("Show Linux save location warnings (non-default compatdata)"),
            variable=self.show_linux_save_warning_var,
            command=lambda: self.settings.set(
                "show_linux_save_warning", self.show_linux_save_warning_var.get()
            ),
        ).pack(anchor="w", padx=12, pady=5)
        ctk.CTkLabel(
            frame,
            text=t("Linux: Warns when save is not in the default compatdata folder."),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 10))

        # Update Notifications
        self.show_update_notifications_var = tk.BooleanVar(
            value=self.settings.get("show_update_notifications", True)
        )
        ctk.CTkCheckBox(
            frame,
            text=t("Show update notifications on startup"),
            variable=self.show_update_notifications_var,
            command=lambda: self.settings.set(
                "show_update_notifications",
                self.show_update_notifications_var.get(),
            ),
        ).pack(anchor="w", padx=12, pady=5)
        ctk.CTkLabel(
            frame,
            text=t("Check for new versions and show notification dialog."),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 12))

        # External file change notification
        self.external_file_change_var = tk.BooleanVar(
            value=self.settings.get("external_file_change_notification", True)
        )
        ctk.CTkCheckBox(
            frame,
            text=t("Notify when save file is modified externally"),
            variable=self.external_file_change_var,
            command=lambda: self.settings.set(
                "external_file_change_notification",
                self.external_file_change_var.get(),
            ),
        ).pack(anchor="w", padx=12, pady=5)
        ctk.CTkLabel(
            frame,
            text=t("Shows a dialog when another program modifies the loaded save."),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 12))

    def _create_backup_settings(self, parent):
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text=t("Backups"),
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        # Compress Backups
        self.compress_backups_var = tk.BooleanVar(
            value=self.settings.get("compress_backups", True)
        )
        ctk.CTkCheckBox(
            frame,
            text=t("Compress backups (zip) to save disk space"),
            variable=self.compress_backups_var,
            command=lambda: self.settings.set(
                "compress_backups", self.compress_backups_var.get()
            ),
        ).pack(anchor="w", padx=12, pady=5)
        ctk.CTkLabel(
            frame,
            text=t(
                "Reduces backup size by ~90% but takes slightly longer to create/restore."
            ),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 10))

        # Max Backups
        max_backup_frame = ctk.CTkFrame(frame, fg_color="transparent")
        max_backup_frame.pack(fill="x", padx=12, pady=(0, 5))
        ctk.CTkLabel(max_backup_frame, text=t("Maximum backups to keep:")).pack(
            side="left", padx=(0, 10)
        )
        self.max_backups_var = tk.StringVar(
            value=str(self.settings.get("max_backups", 50))
        )
        max_backups_entry = ctk.CTkEntry(
            max_backup_frame, textvariable=self.max_backups_var, width=80
        )
        max_backups_entry.pack(side="left")

        MIN_MAX_BACKUPS = 5

        def commit_backup_limit(*args):
            # Commits only on Enter/focus-out so a partially typed value
            # (e.g. "1" while changing 50 to 100) never gets saved and
            # triggers pruning down to that intermediate value.
            old_value = self.settings.get("max_backups", 50)
            try:
                value = int(self.max_backups_var.get())
            except ValueError:
                value = old_value
            value = max(value, MIN_MAX_BACKUPS)

            if value < old_value:
                existing_count = self._count_existing_backups()
                if existing_count > value:
                    excess = existing_count - value
                    proceed = CTkMessageBox.askyesno(
                        t("Lower Backup Limit"),
                        t(
                            "You currently have {existing_count} backups for the loaded save.\n\nLowering the limit to {value} will delete the {excess} oldest backup(s) the next time a backup is created.\n\nContinue?"
                        ).format(
                            existing_count=existing_count, value=value, excess=excess
                        ),
                        parent=self.root,
                    )
                    if not proceed:
                        self.max_backups_var.set(str(old_value))
                        return

            self.max_backups_var.set(str(value))
            self.settings.set("max_backups", value)

        max_backups_entry.bind("<Return>", commit_backup_limit)
        max_backups_entry.bind("<FocusOut>", commit_backup_limit)

        ctk.CTkLabel(
            frame,
            text=t(
                "Older backups are automatically deleted when this limit is reached."
            ),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 10))

        # Backup Pruning Warning
        self.show_backup_pruning_warning_var = tk.BooleanVar(
            value=self.settings.get("show_backup_pruning_warning", True)
        )
        ctk.CTkCheckBox(
            frame,
            text=t("Show warning when backups are automatically deleted"),
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
            text=t("Auto-Backup on Game Launch"),
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", padx=12, pady=(0, 4))

        ctk.CTkLabel(
            parent,
            text=(
                t(
                    "Automatically create a backup of your {name} save whenever the game launches."
                ).format(name=profile.name)
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

        game_frame = ctk.CTkFrame(
            parent, corner_radius=8, fg_color=("gray90", "gray18")
        )
        game_frame.pack(fill="x", padx=12, pady=(0, 6))

        header_row = ctk.CTkFrame(game_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=10, pady=(8, 4))

        enabled_var = tk.BooleanVar(value=enabled)
        self._auto_backup_enabled_vars[profile.key] = enabled_var

        ctk.CTkCheckBox(
            header_row,
            text=t("Enable auto-backup for {name}").format(name=profile.name),
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
            text=t("Monitored save file:"),
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
            text=t("Choose..."),
            width=80,
            command=lambda k=profile.key, p=profile: self._choose_game_auto_backup_save(
                k, p
            ),
        ).pack(side="right", padx=(6, 0))

        notify_row = ctk.CTkFrame(game_frame, fg_color="transparent")
        notify_row.pack(fill="x", padx=10, pady=(0, 8))

        self.show_auto_backup_notification_var = tk.BooleanVar(
            value=self.settings.get("show_auto_backup_notification", True)
        )
        ctk.CTkCheckBox(
            notify_row,
            text=t("Show toast notification when a backup is created via game launch"),
            variable=self.show_auto_backup_notification_var,
            font=("Segoe UI", 11),
            command=lambda: self.settings.set(
                "show_auto_backup_notification",
                self.show_auto_backup_notification_var.get(),
            ),
        ).pack(anchor="w")

        # Interval backup - requires auto-backup on game launch to be enabled
        interval_row = ctk.CTkFrame(game_frame, fg_color="transparent")
        interval_row.pack(fill="x", padx=10, pady=(0, 10))

        interval_minutes = game_cfg.get("interval_minutes", 30)
        interval_enabled_var = tk.BooleanVar(
            value=game_cfg.get("interval_enabled", False)
        )
        interval_minutes_var = tk.StringVar(value=str(interval_minutes))
        self._auto_backup_interval_enabled_vars[profile.key] = interval_enabled_var
        self._auto_backup_interval_minutes_vars[profile.key] = interval_minutes_var

        interval_checkbox = ctk.CTkCheckBox(
            interval_row,
            text=t("Also back up every"),
            variable=interval_enabled_var,
            font=("Segoe UI", 11),
            state="normal" if enabled else "disabled",
            command=lambda k=profile.key: self._on_game_auto_backup_interval_toggle(k),
        )
        interval_checkbox.pack(side="left")

        interval_entry = ctk.CTkEntry(
            interval_row,
            width=50,
            textvariable=interval_minutes_var,
            state="normal" if enabled else "disabled",
        )
        interval_entry.pack(side="left", padx=(6, 4))
        # Restrict keystrokes to digits so non-numeric input is rejected
        # before it ever reaches the commit/parse step.
        vcmd = interval_entry.register(lambda s: s == "" or s.isdigit())
        interval_entry.configure(validate="key", validatecommand=(vcmd, "%P"))
        interval_entry.bind(
            "<FocusOut>",
            lambda e, k=profile.key: self._on_game_auto_backup_interval_minutes_changed(
                k
            ),
        )
        interval_entry.bind(
            "<Return>",
            lambda e, k=profile.key: self._on_game_auto_backup_interval_minutes_changed(
                k
            ),
        )

        ctk.CTkLabel(
            interval_row,
            text=t("minutes while the game is running"),
            font=("Segoe UI", 11),
        ).pack(side="left")

        self._auto_backup_interval_widgets[profile.key] = (
            interval_checkbox,
            interval_entry,
        )

    def _on_game_auto_backup_toggle(self, game_key: str):
        enabled = self._auto_backup_enabled_vars[game_key].get()
        auto_backup_cfg: dict = dict(self.settings.get("auto_backup_games", {}))
        game_cfg = dict(auto_backup_cfg.get(game_key, {}))
        game_cfg["enabled"] = enabled

        if enabled:
            save_path = game_cfg.get("save_path", "")
            if not save_path or not Path(save_path).exists():
                CTkMessageBox.showwarning(
                    t("Configure Save File"),
                    t("Please choose which save file to monitor for auto-backup."),
                    parent=self.parent,
                )
                # Find the profile
                from er_save_manager.games.game_profiles import PROFILES_BY_KEY

                profile = PROFILES_BY_KEY.get(game_key)
                if profile:
                    self._choose_game_auto_backup_save(game_key, profile)
        else:
            # Interval backup requires auto-backup on game launch to be enabled
            game_cfg["interval_enabled"] = False
            if game_key in self._auto_backup_interval_enabled_vars:
                self._auto_backup_interval_enabled_vars[game_key].set(False)

        auto_backup_cfg[game_key] = game_cfg
        self.settings.set("auto_backup_games", auto_backup_cfg)

        if game_key in self._auto_backup_interval_widgets:
            checkbox, entry = self._auto_backup_interval_widgets[game_key]
            state = "normal" if enabled else "disabled"
            checkbox.configure(state=state)
            entry.configure(state=state)

    def _on_game_auto_backup_interval_toggle(self, game_key: str):
        interval_enabled = self._auto_backup_interval_enabled_vars[game_key].get()
        auto_backup_cfg: dict = dict(self.settings.get("auto_backup_games", {}))
        game_cfg = dict(auto_backup_cfg.get(game_key, {}))
        game_cfg["interval_enabled"] = interval_enabled
        game_cfg.setdefault("interval_minutes", self._parse_interval_minutes(game_key))
        auto_backup_cfg[game_key] = game_cfg
        self.settings.set("auto_backup_games", auto_backup_cfg)

    def _on_game_auto_backup_interval_minutes_changed(self, game_key: str):
        minutes = self._parse_interval_minutes(game_key)
        self._auto_backup_interval_minutes_vars[game_key].set(str(minutes))
        auto_backup_cfg: dict = dict(self.settings.get("auto_backup_games", {}))
        game_cfg = dict(auto_backup_cfg.get(game_key, {}))
        game_cfg["interval_minutes"] = minutes
        auto_backup_cfg[game_key] = game_cfg
        self.settings.set("auto_backup_games", auto_backup_cfg)

    def _parse_interval_minutes(self, game_key: str) -> int:
        """Parse the interval entry, falling back to the last saved value.

        Clamped to MIN_INTERVAL_MINUTES..MAX_INTERVAL_MINUTES (1 minute to
        24 hours) so a stray or malicious value can never produce a zero,
        negative, or absurdly small backup interval.
        """
        MIN_INTERVAL_MINUTES = 1
        MAX_INTERVAL_MINUTES = 1440

        auto_backup_cfg: dict = self.settings.get("auto_backup_games", {})
        old_value = auto_backup_cfg.get(game_key, {}).get("interval_minutes", 30)

        raw = self._auto_backup_interval_minutes_vars[game_key].get().strip()
        try:
            minutes = int(raw)
        except ValueError:
            minutes = old_value

        return min(max(minutes, MIN_INTERVAL_MINUTES), MAX_INTERVAL_MINUTES)

    def _choose_game_auto_backup_save(self, game_key: str, profile):
        from er_save_manager.platform.utils import PlatformUtils

        # Offer auto-detected saves first
        found = PlatformUtils.find_all_save_files(profile)
        if found:
            options = [str(p) for p in found]
            if len(options) == 1:
                choice = CTkMessageBox.askyesno(
                    t("Use Detected Save"),
                    t(
                        "Found save file:\n\n{options}\n\nUse this for auto-backup?"
                    ).format(options=options[0]),
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
                dlg.geometry("620x400")
                dlg.resizable(True, True)
                dlg.minsize(500, 300)
                force_render_dialog(dlg)
                dlg.grab_set()

                ctk.CTkLabel(
                    dlg,
                    text=t("Select save file to monitor:"),
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
                    text=t("Browse..."),
                    width=100,
                    command=lambda: [
                        selected.__setitem__(0, "__browse__"),
                        dlg.destroy(),
                    ],
                ).pack(side=tk.LEFT, padx=15, pady=(0, 12))
                ctk.CTkButton(
                    dlg, text=t("Cancel"), width=80, command=dlg.destroy
                ).pack(side=tk.RIGHT, padx=15, pady=(0, 12))
                dlg.wait_window()

                if selected[0] and selected[0] != "__browse__":
                    self._set_game_auto_backup_path(game_key, selected[0])
                    return

        # Fallback: file browser
        ext_str = " ".join(f"*{e}" for e in profile.extensions)
        file_path = pick_file(
            title=t("Choose Save File for Auto-Backup - {name}").format(
                name=profile.name
            ),
            filetypes=[(f"{profile.name} Save", ext_str), ("All files", "*.*")],
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
            text=t("User Interface"),
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        language_frame = ctk.CTkFrame(frame, fg_color="transparent")
        language_frame.pack(fill="x", padx=12, pady=5)

        ctk.CTkLabel(language_frame, text=t("Language:")).pack(
            side="left", padx=(0, 10)
        )

        # Endonyms keep the selector readable regardless of the active language
        auto_label = t("Auto (system)")
        self._language_options = {auto_label: "auto"}
        for code in i18n.available_languages():
            self._language_options[i18n.language_display_name(code)] = code
        code_to_label = {v: k for k, v in self._language_options.items()}

        saved_language = self.settings.get("language", "en")
        self.language_var = tk.StringVar(
            value=code_to_label.get(saved_language, code_to_label["en"])
        )
        ctk.CTkComboBox(
            language_frame,
            variable=self.language_var,
            values=list(self._language_options.keys()),
            state="readonly",
            width=150,
            command=self._on_language_changed,
        ).pack(side="left")

        ctk.CTkLabel(
            frame,
            text=t("Restart required to apply."),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 12))

        theme_frame = ctk.CTkFrame(frame, fg_color="transparent")
        theme_frame.pack(fill="x", padx=12, pady=5)

        ctk.CTkLabel(theme_frame, text=t("Theme:")).pack(side="left", padx=(0, 10))

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
            text=t("(Restart required for full theme application)"),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 12))

        scale_frame = ctk.CTkFrame(frame, fg_color="transparent")
        scale_frame.pack(fill="x", padx=12, pady=5)

        ctk.CTkLabel(scale_frame, text=t("UI Scale:")).pack(side="left", padx=(0, 10))

        _SCALE_OPTIONS = [
            "100%",
            "125%",
            "150%",
            "175%",
            "200%",
            "250%",
            "300%",
            "Auto",
        ]
        _scale_to_str = {
            1.0: "100%",
            1.25: "125%",
            1.5: "150%",
            1.75: "175%",
            2.0: "200%",
            2.5: "250%",
            3.0: "300%",
        }
        _str_to_scale = {v: k for k, v in _scale_to_str.items()}
        saved_scale = self.settings.get("ui_scale", None)
        initial_str = (
            _scale_to_str.get(saved_scale, "100%")
            if saved_scale is not None
            else "100%"
        )
        self.scale_var = tk.StringVar(value=initial_str)

        ctk.CTkComboBox(
            scale_frame,
            variable=self.scale_var,
            values=_SCALE_OPTIONS,
            state="readonly",
            width=150,
            command=lambda v: self._on_scale_changed(v, _str_to_scale),
        ).pack(side="left")

        ctk.CTkLabel(
            frame,
            text=t("Restart required to apply."),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
            wraplength=520,
            justify="left",
        ).pack(anchor="w", padx=32, pady=(0, 12))

    def _on_language_changed(self, value: str) -> None:
        code = self._language_options.get(value, "auto")
        self.settings.set("language", code)
        CTkMessageBox.showinfo(
            t("Language Changed"),
            t("Language set to {name}.\n\nRestart the application to apply.").format(
                name=value
            ),
            parent=self.parent,
        )

    def _on_scale_changed(self, value: str, str_to_scale: dict) -> None:
        if value == "Auto":
            self.settings.set("ui_scale", None)
        else:
            self.settings.set("ui_scale", str_to_scale.get(value, 1.0))
        CTkMessageBox.showinfo(
            t("Scale Changed"),
            t("UI scale set to {value}.\n\nRestart the application to apply.").format(
                value=value
            ),
            parent=self.parent,
        )

    def _on_key_press(self, event) -> None:
        """Accumulate keypresses and check for the unlock sequence STRAWBERRY.
        Only processes input when the Settings tab is the visible tab.
        """
        try:
            if not self.parent.winfo_ismapped():
                return
        except Exception:
            return
        ch = event.char
        if not ch or not ch.isprintable():
            return
        self._key_buffer = (self._key_buffer + ch.upper())[-10:]
        if self._key_buffer == "STRAWBERRY":
            self._key_buffer = ""
            if not self.settings.get("advanced_mode_unlocked", False):
                self.settings.set("advanced_mode_unlocked", True)
                self._show_unlock_popup()
                self._create_advanced_settings(self._scroll_frame)

    def _show_unlock_popup(self) -> None:
        """Show a small congratulations popup on first unlock."""
        root = self.root if self.root is not None else self.parent
        popup = ctk.CTkToplevel(root)
        popup.title("")
        popup.resizable(False, False)
        popup.transient(root)
        popup.grab_set()

        popup.update_idletasks()
        w, h = 260, 130
        rx = root.winfo_rootx() + (root.winfo_width() - w) // 2
        ry = root.winfo_rooty() + (root.winfo_height() - h) // 2
        popup.geometry(f"{w}x{h}+{rx}+{ry}")

        ctk.CTkLabel(
            popup,
            text="\U0001f353",
            font=("Segoe UI", 36),
        ).pack(pady=(16, 4))
        ctk.CTkLabel(
            popup,
            text=t("You found it!"),
            font=("Segoe UI", 13, "bold"),
        ).pack()
        ctk.CTkButton(
            popup,
            text=t("OK"),
            width=80,
            command=popup.destroy,
        ).pack(pady=(10, 0))

        popup.after(3000, lambda: popup.destroy() if popup.winfo_exists() else None)

    def _create_advanced_settings(self, parent) -> None:
        """Build the advanced/developer settings section."""
        if self._advanced_frame is not None:
            return

        frame = ctk.CTkFrame(
            parent, corner_radius=12, border_width=1, border_color=("gray60", "gray40")
        )
        frame.pack(fill="x", pady=(0, 10))
        self._advanced_frame = frame

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(
            header,
            text=t("Advanced"),
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text=t("Lock"),
            width=60,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray20"),
            command=self._lock_advanced,
        ).pack(side="right")

        ctk.CTkLabel(
            frame,
            text=t("These settings bypass safety checks. Use with care."),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Skip game running check
        self.skip_game_check_var = tk.BooleanVar(
            value=self.settings.get("skip_game_running_check", False)
        )
        ctk.CTkCheckBox(
            frame,
            text=t("Skip game-running check when loading saves"),
            variable=self.skip_game_check_var,
            command=lambda: self.settings.set(
                "skip_game_running_check", self.skip_game_check_var.get()
            ),
        ).pack(anchor="w", padx=12, pady=5)
        ctk.CTkLabel(
            frame,
            text=t(
                "Allows loading saves while the game is running. Risk of data loss."
            ),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 10))

        # Verbose logging
        self.verbose_logging_var = tk.BooleanVar(
            value=self.settings.get("verbose_logging", False)
        )
        ctk.CTkCheckBox(
            frame,
            text=t("Verbose logging to file"),
            variable=self.verbose_logging_var,
            command=lambda: self.settings.set(
                "verbose_logging", self.verbose_logging_var.get()
            ),
        ).pack(anchor="w", padx=12, pady=5)
        ctk.CTkLabel(
            frame,
            text=t("Writes er_save_manager.log next to the loaded save file."),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 12))

        # Icon export in Visual Item Picker
        self._icon_export_var = tk.BooleanVar(
            value=self.settings.get("icon_export_enabled", False)
        )
        ctk.CTkCheckBox(
            frame,
            text=t("Enable icon export in Visual Item Picker"),
            variable=self._icon_export_var,
            command=lambda: self.settings.set(
                "icon_export_enabled", self._icon_export_var.get()
            ),
        ).pack(anchor="w", padx=12, pady=5)
        ctk.CTkLabel(
            frame,
            text=t(
                "Adds a Save Icon button to the Visual Item Picker for exporting item icons."
            ),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=32, pady=(0, 12))

        # Warped face sliders button in Appearance tab
        self._debug_warped_face_var = tk.BooleanVar(
            value=self.settings.get("debug_warped_face_sliders", False)
        )
        ctk.CTkCheckBox(
            frame,
            text=t("Show Warped Face Sliders button in Appearance tab"),
            variable=self._debug_warped_face_var,
            command=lambda: self.settings.set(
                "debug_warped_face_sliders", self._debug_warped_face_var.get()
            ),
        ).pack(anchor="w", padx=12, pady=5)
        ctk.CTkLabel(
            frame,
            text=t(
                "Adds a button to edit the hidden secondary face deformation sliders on a selected preset."
            ),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
            wraplength=560,
            justify="left",
        ).pack(anchor="w", padx=32, pady=(0, 12))

    def _create_launch_settings(self, parent) -> None:
        """CPU 0 exclusion settings - Windows only."""
        import sys

        if sys.platform != "win32":
            return

        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text=t("Performance"),
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        self._cpu0_exclude_var = tk.BooleanVar(
            value=self.settings.get("cpu0_exclude_on_launch", False)
        )
        ctk.CTkCheckBox(
            frame,
            text=t(
                "Exclude CPU 0 from Elden Ring, Nightreign and DS3 affinity on launch"
            ),
            variable=self._cpu0_exclude_var,
            command=lambda: self.settings.set(
                "cpu0_exclude_on_launch", self._cpu0_exclude_var.get()
            ),
        ).pack(anchor="w", padx=12, pady=5)
        ctk.CTkLabel(
            frame,
            text=(
                t(
                    "When eldenring.exe, nightreign.exe or darksoulsiii.exe is detected, "
                    "CPU 0 is removed from its affinity mask. "
                    "Can reduce stutter caused by Windows scheduling on core 0."
                )
            ),
            text_color=("gray40", "gray70"),
            font=("Segoe UI", 11),
            wraplength=560,
            justify="left",
        ).pack(anchor="w", padx=32, pady=(0, 12))

    def _lock_advanced(self) -> None:
        """Hide the advanced section and clear the unlock flag."""
        self.settings.set("advanced_mode_unlocked", False)
        self.settings.set("skip_game_running_check", False)
        self.settings.set("verbose_logging", False)
        self.settings.set("icon_export_enabled", False)
        self.settings.set("debug_warped_face_sliders", False)
        if self._advanced_frame is not None:
            self._advanced_frame.destroy()
            self._advanced_frame = None

    def reset_to_defaults(self):
        if CTkMessageBox.askyesno(
            t("Reset Settings"),
            t(
                "Are you sure you want to reset all settings to defaults?\n\nThis cannot be undone."
            ),
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
            if hasattr(self, "scale_var"):
                self.scale_var.set("100%")
            for var in self._auto_backup_enabled_vars.values():
                var.set(False)
            for var in self._auto_backup_path_vars.values():
                var.set("(not configured)")
            for var in self._auto_backup_interval_enabled_vars.values():
                var.set(False)
            for var in self._auto_backup_interval_minutes_vars.values():
                var.set("30")
            for checkbox, entry in self._auto_backup_interval_widgets.values():
                checkbox.configure(state="disabled")
                entry.configure(state="disabled")
            # Reset advanced settings
            if self._advanced_frame is not None:
                self._advanced_frame.destroy()
                self._advanced_frame = None
            if hasattr(self, "skip_game_check_var"):
                self.skip_game_check_var.set(False)
            if hasattr(self, "verbose_logging_var"):
                self.verbose_logging_var.set(False)
            if hasattr(self, "_cpu0_exclude_var"):
                self._cpu0_exclude_var.set(False)
                self.settings.set("cpu0_exclude_on_launch", False)
            if hasattr(self, "_icon_export_var"):
                self._icon_export_var.set(False)
            if hasattr(self, "_debug_warped_face_var"):
                self._debug_warped_face_var.set(False)
            CTkMessageBox.showinfo(
                t("Success"),
                t("Settings have been reset to defaults."),
                parent=self.parent,
            )

    def _on_theme_changed(self, value=None):
        theme = self.theme_var.get()
        self.settings.set("theme", theme)
        CTkMessageBox.showinfo(
            t("Theme Changed"),
            t(
                "Theme changed to {theme}.\n\nPlease restart the application for full effect."
            ).format(theme=theme),
            parent=self.parent,
        )
