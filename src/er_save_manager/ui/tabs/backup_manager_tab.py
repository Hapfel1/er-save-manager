"""
Backup Manager Tab
Manages save file backups for all supported FromSoftware games.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


class BackupManagerTab:
    """Tab for backup management across all supported games."""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_save_path_callback,
        reload_callback,
        show_toast_callback,
    ):
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback
        self.show_toast = show_toast_callback

        self.backup_stats_var = None
        self._game_var: tk.StringVar | None = None
        self._profiles: list = []

    def _get_profiles(self):
        if not self._profiles:
            from er_save_manager.games.game_profiles import GAME_PROFILES

            self._profiles = GAME_PROFILES
        return self._profiles

    def _selected_profile(self):
        if not self._game_var:
            return None
        name = self._game_var.get()
        for p in self._get_profiles():
            if p.name == name:
                return p
        return None

    def set_active_profile(self, profile_name: str):
        """Called by gui.py when the global game selection changes."""
        for p in self._get_profiles():
            if p.name == profile_name:
                if self._game_var:
                    self._game_var.set(profile_name)
                self._on_game_changed(profile_name)
                return

    def setup_ui(self):
        title_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        title_frame.pack(fill=tk.X, pady=10)

        ctk.CTkLabel(
            title_frame,
            text="Backup Manager",
            font=("Segoe UI", 16, "bold"),
        ).pack()

        ctk.CTkLabel(
            title_frame,
            text="Manage save file backups for all supported FromSoftware games",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack()

        # Hidden game var - driven by global selector via set_active_profile
        profiles = self._get_profiles()
        game_names = [p.name for p in profiles]
        self._game_var = tk.StringVar(value=game_names[0] if game_names else "")

        # Main button
        ctk.CTkButton(
            self.parent,
            text="Open Backup Manager Window",
            command=self.show_backup_manager,
        ).pack(pady=(10, 10))

        # Quick stats
        stats_frame = ctk.CTkFrame(self.parent)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            stats_frame,
            text="Quick Stats",
            font=("Segoe UI", 12, "bold"),
            text_color=("gray70", "gray50"),
        ).pack(anchor=tk.W, padx=15, pady=(10, 5))

        self.backup_stats_var = tk.StringVar(
            value="Load a save file or select a game to view backup statistics"
        )
        ctk.CTkLabel(
            stats_frame,
            textvariable=self.backup_stats_var,
            font=("Consolas", 10),
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=15, pady=10)

        info_frame = ctk.CTkFrame(self.parent)
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        ctk.CTkLabel(
            info_frame,
            text="Backup Information",
            font=("Segoe UI", 12, "bold"),
            text_color=("gray70", "gray50"),
        ).pack(anchor=tk.W, padx=15, pady=(10, 5))

        info_text = (
            "Automatic Backups:\n"
            "  Fix Corruption, Teleport, Edit Stats, Import Preset,\n"
            "  Patch SteamID, Recalculate Checksums\n\n"
            "Backup Format:\n"
            "  Timestamp: YYYY-MM-DD_HH-MM-SS\n"
            "  Location: [save_name].<ext>.backups/\n"
            "  Metadata: Character info, operation type, changes made"
        )

        ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=("Segoe UI", 11),
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=15, pady=10)

        self._on_game_changed(self._game_var.get())

    def _on_game_changed(self, _value=None):
        profile = self._selected_profile()
        if profile is None:
            return
        # Show note for Elden Ring (currently loaded game context)
        if profile.key == "elden_ring":
            self._game_note_var.set("(currently loaded game)")
        else:
            self._game_note_var.set("")
        self.update_backup_stats()

    def _resolve_save_path_for_profile(self) -> Path | None:
        """
        Get the relevant save path for backup stats.
        For Elden Ring: use the currently loaded save.
        For other games: find the first save file via PlatformUtils.
        """
        profile = self._selected_profile()
        if profile is None:
            return None

        if profile.key == "elden_ring":
            save_path = self.get_save_path()
            if save_path:
                return Path(save_path)

        from er_save_manager.platform.utils import PlatformUtils

        paths = PlatformUtils.find_all_save_files(profile)
        if paths:
            return paths[0]

        return None

    def update_backup_stats(self):
        if not self.backup_stats_var:
            return

        save_path = self._resolve_save_path_for_profile()
        if not save_path:
            profile = self._selected_profile()
            game_name = profile.name if profile else "selected game"
            self.backup_stats_var.set(
                f"No save file found for {game_name}.\n"
                "Load a save file or check that the game has been launched at least once."
            )
            return

        try:
            from er_save_manager.backup.manager import BackupManager

            manager = BackupManager(save_path)
            backups = manager.list_backups()

            if not backups:
                self.backup_stats_var.set(
                    f"Save: {save_path.name}\nNo backups found for this save file"
                )
                return

            total_size = sum(b.file_size for b in backups)
            lines = [
                f"Save: {save_path.name}",
                f"Total Backups: {len(backups)}",
                f"Total Size: {total_size / (1024 * 1024):.1f} MB",
                f"Latest: {backups[0].timestamp[:19].replace('T', ' ') if backups else 'N/A'}",
            ]
            self.backup_stats_var.set("\n".join(lines))

        except Exception as e:
            self.backup_stats_var.set(f"Error loading backup stats: {e}")

    def _check_auto_backup_first_run(self, profile):
        """Show auto-backup setup wizard the first time Backup Manager is opened for a game."""
        try:
            from er_save_manager.backup.process_monitor import (
                show_auto_backup_first_run_dialog,
            )
            from er_save_manager.ui.settings import get_settings

            settings = get_settings()
            done: list = settings.get("auto_backup_first_run_done", [])
            if profile.key not in done:
                show_auto_backup_first_run_dialog(
                    parent=self.parent,
                    profile=profile,
                )
        except Exception as e:
            print(f"Auto-backup first-run check failed: {e}")

    def open_for_profile(self, profile):
        """
        Open backup manager window directly for a given profile.
        Used by the top-level Backup Manager button in gui.py so the
        helper instance doesn't need setup_ui() called.
        """
        from er_save_manager.platform.utils import PlatformUtils

        save_path = None
        if profile.key == "elden_ring":
            sp = self.get_save_path()
            if sp:
                save_path = Path(sp)
        if not save_path:
            paths = PlatformUtils.find_all_save_files(profile)
            if paths:
                save_path = paths[0]

        if not save_path:
            CTkMessageBox.showwarning(
                "No Save File",
                f"No save file found for {profile.name}.\n\n"
                "Launch the game at least once so the save file is created,\n"
                "then try again.",
                parent=self.parent,
            )
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.ui.utils import force_render_dialog

            self._check_auto_backup_first_run(profile)

            manager = BackupManager(save_path)
            dialog = ctk.CTkToplevel(self.parent)
            dialog.title(f"Backup Manager - {profile.name}")
            width, height = 900, 600
            dialog.update_idletasks()
            self.parent.update_idletasks()
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            dialog.geometry(
                f"{width}x{height}+{px + pw // 2 - width // 2}+{py + ph // 2 - height // 2}"
            )
            force_render_dialog(dialog)
            dialog.grab_set()
            self._build_backup_dialog_content(dialog, manager, profile, save_path)
        except Exception as e:
            import traceback

            traceback.print_exc()
            CTkMessageBox.showerror(
                "Error", f"Failed to open backup manager:\n{e}", parent=self.parent
            )

    def show_backup_manager(self):
        profile = self._selected_profile()
        if profile is None:
            CTkMessageBox.showwarning(
                "No Game", "Please select a game.", parent=self.parent
            )
            return

        # For ER: require a loaded save
        save_path = self._resolve_save_path_for_profile()
        if not save_path:
            CTkMessageBox.showwarning(
                "No Save File",
                f"No save file found for {profile.name}.\n\n"
                "Launch the game at least once so the save file is created,\n"
                "then try again.",
                parent=self.parent,
            )
            return

        self._check_auto_backup_first_run(profile)

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.ui.utils import force_render_dialog

            manager = BackupManager(save_path)

            dialog = ctk.CTkToplevel(self.parent)
            dialog.title(f"Backup Manager - {profile.name}")
            width, height = 900, 600
            dialog.update_idletasks()
            self.parent.update_idletasks()
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            dialog.geometry(
                f"{width}x{height}+{px + pw // 2 - width // 2}+{py + ph // 2 - height // 2}"
            )

            force_render_dialog(dialog)
            dialog.grab_set()

            self._build_backup_dialog_content(dialog, manager, profile, save_path)

        except Exception as e:
            import traceback

            traceback.print_exc()
            CTkMessageBox.showerror(
                "Error", f"Failed to open backup manager:\n{e}", parent=self.parent
            )

    def _build_backup_dialog_content(self, dialog, manager, profile, save_path: Path):
        from er_save_manager.ui.utils import force_render_dialog

        ctk.CTkLabel(
            dialog,
            text=f"Backup Manager - {profile.name}",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        ctk.CTkLabel(
            dialog,
            text=str(save_path),
            font=("Consolas", 9),
            text_color=("gray40", "gray60"),
        ).pack(pady=(0, 6))

        list_frame = ctk.CTkFrame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            list_frame,
            text="Backups",
            font=("Segoe UI", 12, "bold"),
            text_color=("gray70", "gray50"),
        ).pack(anchor=tk.W, padx=10, pady=(0, 5))

        sort_var = tk.StringVar(value="Newest")
        sort_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        sort_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

        ctk.CTkLabel(sort_frame, text="Sort by:", font=("Segoe UI", 10, "bold")).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ctk.CTkComboBox(
            sort_frame,
            values=["Newest", "Oldest", "Operation", "Size"],
            variable=sort_var,
            state="readonly",
            width=140,
        ).pack(side=tk.LEFT)

        scrollable_frame = ctk.CTkScrollableFrame(list_frame)
        scrollable_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(scrollable_frame)

        selected_backup = [None]
        backup_items = {}

        def sort_backups(backups):
            sel = sort_var.get()
            if sel == "Oldest":
                return sorted(backups, key=lambda b: b.timestamp)
            if sel == "Operation":
                return sorted(backups, key=lambda b: (b.operation or "", b.timestamp))
            if sel == "Size":
                return sorted(backups, key=lambda b: b.file_size, reverse=True)
            return sorted(backups, key=lambda b: b.timestamp, reverse=True)

        def refresh_list():
            for w in scrollable_frame.winfo_children():
                w.destroy()
            backup_items.clear()
            selected_backup[0] = None

            backups = sort_backups(manager.list_backups())
            if not backups:
                ctk.CTkLabel(
                    scrollable_frame,
                    text="No backups found",
                    text_color=("gray70", "gray50"),
                ).pack(pady=20)
                return

            for backup in backups:
                ts = backup.timestamp[:19].replace("T", " ") if backup.timestamp else ""
                size_mb = f"{backup.file_size / (1024 * 1024):.1f} MB"

                item_frame = ctk.CTkFrame(
                    scrollable_frame,
                    fg_color=("gray86", "gray25"),
                    corner_radius=6,
                )
                item_frame.pack(fill=tk.X, padx=5, pady=3)

                content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
                content_frame.pack(fill=tk.X, padx=10, pady=8)

                ctk.CTkLabel(
                    content_frame,
                    text=backup.filename,
                    font=("Segoe UI", 10, "bold"),
                    justify=tk.LEFT,
                ).pack(anchor=tk.W)

                info_text = f"{ts}  |  {backup.operation or 'manual'}  |  {backup.description or ''}  |  {size_mb}"
                ctk.CTkLabel(
                    content_frame,
                    text=info_text,
                    font=("Segoe UI", 11),
                    text_color=("gray40", "gray70"),
                    justify=tk.LEFT,
                ).pack(anchor=tk.W, pady=(3, 0))

                backup_items[backup.filename] = {
                    "frame": item_frame,
                    "metadata": backup,
                }

                def make_select(fname):
                    def _select(event=None):
                        selected_backup[0] = fname
                        for fn, item in backup_items.items():
                            item["frame"].configure(
                                fg_color=("gray75", "gray35")
                                if fn == fname
                                else ("gray86", "gray25")
                            )

                    return _select

                item_frame.bind("<Button-1>", make_select(backup.filename))
                for child in item_frame.winfo_children():
                    child.bind("<Button-1>", make_select(backup.filename))
                for grandchild in content_frame.winfo_children():
                    grandchild.bind("<Button-1>", make_select(backup.filename))

            self.update_backup_stats()

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        def create_backup():
            try:
                manager.create_backup(description="manual", operation="manual_backup")
                refresh_list()
                self.update_backup_stats()
                self.show_toast("Backup created", duration=2500)
            except Exception as e:
                CTkMessageBox.showerror(
                    "Error", f"Failed to create backup:\n{e}", parent=dialog
                )

        def restore_backup():
            if not selected_backup[0]:
                CTkMessageBox.showwarning(
                    "No Selection", "Select a backup to restore.", parent=dialog
                )
                return

            # For non-ER games the save is not loaded in the editor, just file-copy
            is_er_loaded = (
                profile.key == "elden_ring"
                and self.get_save_file() is not None
                and str(self.get_save_path()) == str(save_path)
            )

            if not CTkMessageBox.askyesno(
                "Confirm Restore",
                f"Restore backup '{selected_backup[0]}'?\n\nCurrent save will be backed up first.",
                parent=dialog,
            ):
                return

            try:
                manager.restore_backup(selected_backup[0])
            except Exception as e:
                CTkMessageBox.showerror(
                    "Error", f"Failed to restore backup:\n{e}", parent=dialog
                )
                return

            if is_er_loaded and self.reload_save:
                try:
                    self.reload_save()
                except Exception as e:
                    print(f"Warning: Failed to reload save after restore: {e}")

            if dialog.winfo_exists():
                refresh_list()
            self.update_backup_stats()
            self.show_toast("Backup restored", duration=3000)

        def delete_backup():
            if not selected_backup[0]:
                CTkMessageBox.showwarning(
                    "No Selection", "Select a backup to delete.", parent=dialog
                )
                return
            if not CTkMessageBox.askyesno(
                "Confirm Delete",
                f"Delete backup '{selected_backup[0]}'?\n\nThis cannot be undone.",
                parent=dialog,
            ):
                return
            try:
                manager.delete_backup(selected_backup[0])
                refresh_list()
                self.update_backup_stats()
                self.show_toast("Backup deleted", duration=2500)
            except Exception as e:
                CTkMessageBox.showerror(
                    "Error", f"Failed to delete backup:\n{e}", parent=dialog
                )

        def view_details():
            if not selected_backup[0]:
                CTkMessageBox.showwarning(
                    "No Selection", "Select a backup to view.", parent=dialog
                )
                return

            info = manager.get_backup_info(selected_backup[0])
            if not info:
                CTkMessageBox.showwarning(
                    "Not Found", "Backup metadata not found.", parent=dialog
                )
                return

            dd = ctk.CTkToplevel(dialog)
            dd.title("Backup Details")
            dd.geometry("600x450")
            dd.transient(dialog)
            force_render_dialog(dd)
            dd.grab_set()

            dd.update_idletasks()
            dialog.update_idletasks()
            dx = dialog.winfo_rootx() + dialog.winfo_width() // 2 - 300
            dy = dialog.winfo_rooty() + dialog.winfo_height() // 2 - 225
            dd.geometry(f"600x450+{dx}+{dy}")

            main_frame = ctk.CTkFrame(dd)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            ctk.CTkLabel(
                main_frame,
                text="Backup Information",
                font=("Segoe UI", 16, "bold"),
            ).pack(pady=(0, 15))

            details_text = ctk.CTkTextbox(
                main_frame, width=540, height=280, font=("Segoe UI", 11)
            )
            details_text.pack(pady=(0, 15))

            lines = [
                f"Filename: {info.filename}",
                f"Timestamp: {info.timestamp}",
                f"Operation: {info.operation}",
                f"Description: {info.description}",
                f"Size: {info.file_size / (1024 * 1024):.2f} MB",
                f"\nBackup Location:\n{manager.backup_folder}",
            ]
            if info.character_summary:
                lines.append("\nCharacters:")
                for char in info.character_summary:
                    lines.append(
                        f"  Slot {char['slot']}: {char['name']} (Lv.{char['level']})"
                    )

            details_text.insert("1.0", "\n".join(lines))
            details_text.configure(state="disabled")

            ctk.CTkButton(
                main_frame, text="Close", command=dd.destroy, width=120
            ).pack()

        def open_backup_folder():
            import os
            import subprocess

            try:
                if os.name == "nt":
                    os.startfile(manager.backup_folder)
                else:
                    subprocess.run(["xdg-open", str(manager.backup_folder)])
            except Exception as e:
                CTkMessageBox.showerror(
                    "Error", f"Failed to open folder:\n{e}", parent=dialog
                )

        for text, cmd in [
            ("Create Backup", create_backup),
            ("Restore", restore_backup),
            ("View Details", view_details),
            ("Delete", delete_backup),
            ("Refresh", refresh_list),
            ("Open Folder", open_backup_folder),
        ]:
            ctk.CTkButton(button_frame, text=text, command=cmd, width=120).pack(
                side=tk.LEFT, padx=5
            )

        ctk.CTkButton(
            button_frame, text="Close", command=dialog.destroy, width=120
        ).pack(side=tk.RIGHT, padx=5)

        refresh_list()
