"""
Backup Manager Tab
Manages save file backups for all supported FromSoftware games.
"""

from __future__ import annotations

import math
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.i18n import t
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

STAR_SIZE = 20
STAR_COLOR_ON = "#e5b54a"
STAR_COLOR_ON_OUTLINE = "#a87520"
STAR_COLOR_OFF = "#8a8a8a"
_STAR_IMAGES: dict[bool, ctk.CTkImage] = {}


def _star_polygon(cx: float, cy: float, r_outer: float, r_inner: float) -> list:
    """Vertices of a five-pointed star, first point straight up."""
    points = []
    for i in range(10):
        radius = r_outer if i % 2 == 0 else r_inner
        angle = -math.pi / 2 + i * math.pi / 5
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def get_star_image(locked: bool) -> ctk.CTkImage:
    """Cached star icon, filled when locked and outlined when not."""
    if locked in _STAR_IMAGES:
        return _STAR_IMAGES[locked]

    from PIL import Image, ImageDraw

    scale = 4
    canvas = STAR_SIZE * scale
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = scale
    r_outer = (canvas - 2 * margin) / 1.902
    cy = (canvas - 1.809 * r_outer) / 2 + r_outer
    points = _star_polygon(canvas / 2, cy, r_outer, r_outer * 0.382)

    if locked:
        draw.polygon(points, fill=STAR_COLOR_ON, outline=STAR_COLOR_ON_OUTLINE)
    else:
        draw.polygon(
            points, fill=None, outline=STAR_COLOR_OFF, width=round(scale * 1.5)
        )

    img = img.resize((STAR_SIZE, STAR_SIZE), Image.LANCZOS)
    image = ctk.CTkImage(light_image=img, dark_image=img, size=(STAR_SIZE, STAR_SIZE))
    _STAR_IMAGES[locked] = image
    return image


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
            text=t("Backup Manager"),
            font=("Segoe UI", 16, "bold"),
        ).pack()

        ctk.CTkLabel(
            title_frame,
            text=t("Manage save file backups for all supported FromSoftware games"),
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
            text=t("Open Backup Manager Window"),
            command=self.show_backup_manager,
        ).pack(pady=(10, 10))

        # Quick stats
        stats_frame = ctk.CTkFrame(self.parent)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            stats_frame,
            text=t("Quick Stats"),
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
            text=t("Backup Information"),
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
            "  Metadata: Character info, operation type, changes made\n\n"
            "Locked Backups:\n"
            "  Click the star next to a backup in the backup manager window\n"
            "  to lock it. Locked backups are never auto-deleted."
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
            self._game_note_var.set(t("(currently loaded game)"))
        else:
            self._game_note_var.set("")
        self.update_backup_stats()

    def _resolve_save_path_for_profile(self) -> Path | None:
        """
        Get the relevant save path for backup stats.
        Prefers the user-selected path for all games; falls back to disk scan.
        """
        profile = self._selected_profile()
        if profile is None:
            return None

        selected = self.get_save_path()
        if selected and Path(selected).exists():
            return Path(selected)

        if profile.key == "elden_ring":
            return None

        from er_save_manager.platform.utils import PlatformUtils

        paths = PlatformUtils.find_all_save_files(profile)
        return paths[0] if paths else None

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
            locked = sum(1 for b in backups if b.favorite)
            lines = [
                f"Save: {save_path.name}",
                f"Total Backups: {len(backups)}",
                f"Locked (exempt from limit): {locked}",
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
        selected = self.get_save_path()
        if selected and Path(selected).exists():
            save_path = Path(selected)

        if not save_path and profile.key != "elden_ring":
            paths = PlatformUtils.find_all_save_files(profile)
            if paths:
                save_path = paths[0]

        if not save_path:
            CTkMessageBox.showwarning(
                t("No Save File"),
                t(
                    "No save file found for {name}.\n\nLaunch the game at least once so the save file is created,\nthen try again."
                ).format(name=profile.name),
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
                t("Error"),
                t("Failed to open backup manager:\n{e}").format(e=e),
                parent=self.parent,
            )

    def show_backup_manager(self):
        profile = self._selected_profile()
        if profile is None:
            CTkMessageBox.showwarning(
                t("No Game"), t("Please select a game."), parent=self.parent
            )
            return

        # For ER: require a loaded save
        save_path = self._resolve_save_path_for_profile()
        if not save_path:
            CTkMessageBox.showwarning(
                t("No Save File"),
                t(
                    "No save file found for {name}.\n\nLaunch the game at least once so the save file is created,\nthen try again."
                ).format(name=profile.name),
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
                t("Error"),
                t("Failed to open backup manager:\n{e}").format(e=e),
                parent=self.parent,
            )

    def _build_backup_dialog_content(self, dialog, manager, profile, save_path: Path):
        from er_save_manager.ui.utils import force_render_dialog

        ctk.CTkLabel(
            dialog,
            text=t("Backup Manager - {name}").format(name=profile.name),
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
            text=t("Backups"),
            font=("Segoe UI", 12, "bold"),
            text_color=("gray70", "gray50"),
        ).pack(anchor=tk.W, padx=10, pady=(0, 2))

        ctk.CTkLabel(
            list_frame,
            text=t(
                "Click the star to lock a backup. Locked backups are never removed by the backup limit."
            ),
            font=("Segoe UI", 10),
            text_color=("gray40", "gray60"),
        ).pack(anchor=tk.W, padx=10, pady=(0, 5))

        sort_var = tk.StringVar(value="Newest")
        sort_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        sort_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

        ctk.CTkLabel(
            sort_frame, text=t("Sort by:"), font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=(0, 6))
        sort_combo = ctk.CTkComboBox(
            sort_frame,
            values=["Newest", "Oldest", "Operation", "Size", "Locked first"],
            variable=sort_var,
            state="readonly",
            width=140,
        )
        sort_combo.pack(side=tk.LEFT)

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
            if sel == "Locked first":
                by_date = sorted(backups, key=lambda b: b.timestamp, reverse=True)
                return sorted(by_date, key=lambda b: not b.favorite)
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
                    text=t("No backups found"),
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

                star_label = ctk.CTkLabel(
                    item_frame,
                    text="",
                    image=get_star_image(backup.favorite),
                    width=STAR_SIZE + 8,
                    cursor="hand2",
                )
                star_label.pack(side=tk.RIGHT, padx=(6, 12))

                content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
                content_frame.pack(
                    side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=8
                )

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

                def make_toggle_lock(fname, meta, label):
                    def _toggle(event=None):
                        new_state = not meta.favorite
                        try:
                            manager.set_favorite(fname, new_state)
                        except Exception as e:
                            CTkMessageBox.showerror(
                                t("Error"),
                                t("Failed to update lock state:\n{e}").format(e=e),
                                parent=dialog,
                            )
                            return
                        label.configure(image=get_star_image(new_state))
                        self.update_backup_stats()
                        self.show_toast(
                            t("Backup locked") if new_state else t("Backup unlocked"),
                            duration=2500,
                        )

                    return _toggle

                star_label.bind(
                    "<Button-1>", make_toggle_lock(backup.filename, backup, star_label)
                )

                backup_items[backup.filename] = {
                    "frame": item_frame,
                    "metadata": backup,
                    "star": star_label,
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
                    # Clicking the star must toggle the lock, not select the row.
                    if child is star_label:
                        continue
                    child.bind("<Button-1>", make_select(backup.filename))
                for grandchild in content_frame.winfo_children():
                    grandchild.bind("<Button-1>", make_select(backup.filename))

            self.update_backup_stats()

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        def ask_backup_label():
            """
            Modal prompt for a manual backup label.

            Returns the entered text, "" if left blank, or None if cancelled.
            """
            result = [None]

            pd = ctk.CTkToplevel(dialog)
            pd.title("Name Backup")
            pd.geometry("440x190")
            pd.transient(dialog)
            force_render_dialog(pd)
            pd.grab_set()

            pd.update_idletasks()
            dialog.update_idletasks()
            px = dialog.winfo_rootx() + dialog.winfo_width() // 2 - 220
            py = dialog.winfo_rooty() + dialog.winfo_height() // 2 - 95
            pd.geometry(f"440x190+{px}+{py}")

            frame = ctk.CTkFrame(pd)
            frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            ctk.CTkLabel(
                frame,
                text=t("Reason or name for this backup:"),
                font=("Segoe UI", 12, "bold"),
            ).pack(anchor=tk.W, pady=(0, 8))

            entry = ctk.CTkEntry(
                frame, placeholder_text=t("e.g. before convergence update")
            )
            entry.pack(fill=tk.X)
            entry.focus_set()

            def confirm(event=None):
                result[0] = entry.get().strip()
                pd.destroy()

            entry.bind("<Return>", confirm)
            pd.bind("<Escape>", lambda _e: pd.destroy())

            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill=tk.X, pady=(16, 0))
            ctk.CTkButton(row, text=t("Create"), command=confirm, width=100).pack(
                side=tk.RIGHT, padx=(6, 0)
            )
            ctk.CTkButton(
                row,
                text=t("Cancel"),
                command=pd.destroy,
                width=100,
                fg_color=("gray70", "gray40"),
                hover_color=("gray60", "gray30"),
            ).pack(side=tk.RIGHT)

            dialog.wait_window(pd)
            dialog.grab_set()
            return result[0]

        def create_backup():
            label = ask_backup_label()
            if label is None:
                return
            try:
                manager.create_backup(
                    description=label or "manual", operation="manual_backup"
                )
                refresh_list()
                self.update_backup_stats()
                self.show_toast(t("Backup created"), duration=2500)
            except Exception as e:
                CTkMessageBox.showerror(
                    t("Error"),
                    t("Failed to create backup:\n{e}").format(e=e),
                    parent=dialog,
                )

        def restore_backup():
            if not selected_backup[0]:
                CTkMessageBox.showwarning(
                    t("No Selection"), t("Select a backup to restore."), parent=dialog
                )
                return
            is_loaded_here = str(self.get_save_path()) == str(save_path)

            if not CTkMessageBox.askyesno(
                t("Confirm Restore"),
                t(
                    "Restore backup '{selected_backup}'?\n\nCurrent save will be backed up first."
                ).format(selected_backup=selected_backup[0]),
                parent=dialog,
            ):
                return

            try:
                manager.restore_backup(selected_backup[0])
            except Exception as e:
                CTkMessageBox.showerror(
                    t("Error"),
                    t("Failed to restore backup:\n{e}").format(e=e),
                    parent=dialog,
                )
                return

            if is_loaded_here and self.reload_save:
                try:
                    self.reload_save()
                except Exception as e:
                    print(f"Warning: Failed to reload save after restore: {e}")

            if dialog.winfo_exists():
                refresh_list()
            self.update_backup_stats()
            self.show_toast(t("Backup restored"), duration=3000)

        def delete_backup():
            if not selected_backup[0]:
                CTkMessageBox.showwarning(
                    t("No Selection"), t("Select a backup to delete."), parent=dialog
                )
                return
            item = backup_items.get(selected_backup[0])
            if item and item["metadata"].favorite:
                CTkMessageBox.showwarning(
                    t("Backup Locked"),
                    t(
                        "This backup is locked and cannot be deleted.\n\n"
                        "Click its star to unlock it first."
                    ),
                    parent=dialog,
                )
                return
            if not CTkMessageBox.askyesno(
                t("Confirm Delete"),
                t(
                    "Delete backup '{selected_backup}'?\n\nThis cannot be undone."
                ).format(selected_backup=selected_backup[0]),
                parent=dialog,
            ):
                return
            try:
                manager.delete_backup(selected_backup[0])
                refresh_list()
                self.update_backup_stats()
                self.show_toast(t("Backup deleted"), duration=2500)
            except Exception as e:
                CTkMessageBox.showerror(
                    t("Error"),
                    t("Failed to delete backup:\n{e}").format(e=e),
                    parent=dialog,
                )

        def view_details():
            if not selected_backup[0]:
                CTkMessageBox.showwarning(
                    t("No Selection"), t("Select a backup to view."), parent=dialog
                )
                return

            info = manager.get_backup_info(selected_backup[0])
            if not info:
                CTkMessageBox.showwarning(
                    t("Not Found"), t("Backup metadata not found."), parent=dialog
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
                text=t("Backup Information"),
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
                main_frame, text=t("Close"), command=dd.destroy, width=120
            ).pack()

        def open_backup_folder():
            import os
            import subprocess

            path = str(manager.backup_folder)
            try:
                if os.name == "nt":
                    os.startfile(manager.backup_folder)
                    return

                # On Linux, xdg-open inherits the process environment which can
                # trigger a readline symbol lookup error on Arch Linux (/bin/sh
                # undefined symbol: rl_print_keybinding). Use a sanitized env
                # and fall back to known file managers if xdg-open fails.
                env = os.environ.copy()
                env.pop("LD_PRELOAD", None)

                # Try xdg-open first with a clean environment.
                result = subprocess.run(
                    ["xdg-open", path],
                    env=env,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
                if result.returncode == 0:
                    return

                # Fall back through common file managers.
                for fm in ("nautilus", "thunar", "dolphin", "nemo", "pcmanfm", "caja"):
                    try:
                        subprocess.Popen(
                            [fm, path],
                            env=env,
                            stderr=subprocess.DEVNULL,
                        )
                        return
                    except FileNotFoundError:
                        continue

                CTkMessageBox.showerror(
                    t("Error"),
                    t("Could not open folder.\nPath: {path}").format(path=path),
                    parent=dialog,
                )
            except Exception as e:
                CTkMessageBox.showerror(
                    t("Error"),
                    t("Failed to open folder:\n{e}").format(e=e),
                    parent=dialog,
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
            button_frame, text=t("Close"), command=dialog.destroy, width=120
        ).pack(side=tk.RIGHT, padx=5)

        sort_combo.configure(command=lambda _choice: refresh_list())

        refresh_list()
