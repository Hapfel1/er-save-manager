"""
Backup Manager Tab
Manages save file backups for all supported FromSoftware games.
"""

from __future__ import annotations

import math
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel, open_folder

STAR_SIZE = 20
# Tk event.state modifier bits.
_SHIFT = 0x0001
_CONTROL = 0x0004
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
            text="Backup Manager",
            font=("Inter", 16, "bold"),
        ).pack()

        ctk.CTkLabel(
            title_frame,
            text="Manage save file backups for all supported FromSoftware games",
            font=("Inter", 11),
            text_color=("gray40", "gray70"),
        ).pack()

        # Hidden game var - driven by global selector via set_active_profile
        profiles = self._get_profiles()
        game_names = [p.name for p in profiles]
        self._game_var = tk.StringVar(value=game_names[0] if game_names else "")

        ctk.CTkButton(
            self.parent,
            text="Open Backup Manager Window",
            command=self.show_backup_manager,
        ).pack(pady=(10, 10))

        stats_frame = ctk.CTkFrame(self.parent)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            stats_frame,
            text="Quick stats",
            font=("Inter", 12, "bold"),
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
            text="Backup information",
            font=("Inter", 12, "bold"),
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
            font=("Inter", 11),
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
                "No Save File",
                f"No save file found for {profile.name}.\n\n"
                "Launch the game at least once so the save file is created,\n"
                "then try again.",
                parent=self.parent,
            )
            return

        try:
            from er_save_manager.backup.manager import BackupManager

            self._check_auto_backup_first_run(profile)

            manager = BackupManager(save_path)
            self._open_backup_window(manager, profile, save_path)
        except Exception as e:
            import traceback

            traceback.print_exc()
            CTkMessageBox.showerror(
                "Backup Manager Failed",
                f"Failed to open backup manager:\n{e}",
                parent=self.parent,
            )

    def show_backup_manager(self):
        profile = self._selected_profile()
        if profile is None:
            CTkMessageBox.showwarning("No Game", "Select a game.", parent=self.parent)
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

            manager = BackupManager(save_path)
            self._open_backup_window(manager, profile, save_path)

        except Exception as e:
            import traceback

            traceback.print_exc()
            CTkMessageBox.showerror(
                "Backup Manager Failed",
                f"Failed to open backup manager:\n{e}",
                parent=self.parent,
            )

    def _open_backup_window(self, manager, profile, save_path: Path):
        from er_save_manager.ui import dialog_style as ds

        dialog = ds.create(self.parent, f"Backup Manager - {profile.name}")
        dialog.resizable(True, True)
        self._build_backup_dialog_content(dialog, manager, profile, save_path)
        ds.finish(dialog, self.parent, width=900, height=600)

    def _build_backup_dialog_content(self, dialog, manager, profile, save_path: Path):
        from er_save_manager.ui import dialog_style as ds
        from er_save_manager.ui.utils import patch_combo_scroll

        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        button_frame = ctk.CTkFrame(main, fg_color="transparent")
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))

        header = ds.header(
            main, f"Backup Manager - {profile.name}", font=ds.TITLE_LARGE
        )
        sort_var = tk.StringVar(value="Newest")
        sort_combo = ctk.CTkComboBox(
            header,
            values=["Newest", "Oldest", "Operation", "Size", "Locked first"],
            variable=sort_var,
            state="readonly",
            width=140,
            font=ds.FONT,
            dropdown_font=ds.FONT,
        )
        sort_combo.pack(side=tk.RIGHT)
        patch_combo_scroll(sort_combo)
        ctk.CTkLabel(header, text="Sort by", font=ds.FONT).pack(
            side=tk.RIGHT, padx=(0, 8)
        )

        ctk.CTkLabel(
            main, text=str(save_path), font=ds.SMALL, text_color=ds.MUTED
        ).pack(anchor=tk.W, pady=(2, 0))
        ctk.CTkLabel(
            main,
            text="Click the star to lock a backup; the backup limit never removes "
            "locked backups. Ctrl+click or Shift+click selects several to delete.",
            font=ds.SMALL,
            text_color=ds.MUTED,
            wraplength=840,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(2, 8))

        scrollable_frame = ctk.CTkScrollableFrame(main, fg_color=ds.BOX)
        scrollable_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(scrollable_frame)

        # Selected filenames in display order; the anchor is the last plain
        # or Ctrl click, the start of a Shift range.
        selected: list[str] = []
        anchor = [None]
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
            selected.clear()
            anchor[0] = None

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
                    font=ds.BOLD,
                    justify=tk.LEFT,
                ).pack(anchor=tk.W)

                info_text = f"{ts}  |  {backup.operation or 'manual'}  |  {backup.description or ''}  |  {size_mb}"
                ctk.CTkLabel(
                    content_frame,
                    text=info_text,
                    font=ds.SMALL,
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
                                "Lock Change Failed",
                                f"Failed to update lock state:\n{e}",
                                parent=dialog,
                            )
                            return
                        label.configure(image=get_star_image(new_state))
                        self.update_backup_stats()
                        self.show_toast(
                            "Backup locked" if new_state else "Backup unlocked",
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
                        state = event.state if event is not None else 0
                        order = list(backup_items)
                        if state & _SHIFT and anchor[0] in backup_items:
                            a, b = sorted((order.index(anchor[0]), order.index(fname)))
                            chosen = set(order[a : b + 1])
                        elif state & _CONTROL:
                            chosen = set(selected) ^ {fname}
                            anchor[0] = fname
                        else:
                            chosen = {fname}
                            anchor[0] = fname
                        selected[:] = [fn for fn in order if fn in chosen]
                        for fn, item in backup_items.items():
                            item["frame"].configure(
                                fg_color=("gray75", "gray35")
                                if fn in chosen
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

        def ask_backup_label():
            """
            Modal prompt for a manual backup label.

            Returns the entered text, "" if left blank, or None if cancelled.
            """
            result = [None]

            pd = ds.create(dialog, "Name Backup")
            frame = ctk.CTkFrame(pd, fg_color="transparent")
            frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

            def confirm(event=None):
                result[0] = entry.get().strip()
                pd.destroy()

            ds.button_row(
                frame,
                [
                    {"text": "Create", "command": confirm},
                    {"text": "Cancel", "command": pd.destroy, "primary": False},
                ],
            )
            ds.header(frame, "Reason or name for this backup")
            entry = ctk.CTkEntry(
                frame,
                placeholder_text="e.g. before convergence update",
                font=ds.FONT,
                height=32,
                width=380,
            )
            entry.pack(fill=tk.X, pady=(10, 0))

            entry.bind("<Return>", confirm)
            pd.bind("<Escape>", lambda _e: pd.destroy())
            ds.finish(pd, dialog)
            entry.focus_set()

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
                self.show_toast("Backup created", duration=2500)
            except Exception as e:
                CTkMessageBox.showerror(
                    "Backup Failed", f"Failed to create backup:\n{e}", parent=dialog
                )

        def single_selection(action: str) -> str | None:
            if len(selected) != 1:
                CTkMessageBox.showwarning(
                    "No Selection" if not selected else "Several Selected",
                    f"Select one backup to {action}.",
                    parent=dialog,
                )
                return None
            return selected[0]

        def restore_backup():
            fname = single_selection("restore")
            if fname is None:
                return
            is_loaded_here = str(self.get_save_path()) == str(save_path)

            if not CTkMessageBox.askyesno(
                "Confirm Restore",
                f"Restore backup '{fname}'?\n\nCurrent save will be backed up first.",
                parent=dialog,
            ):
                return

            try:
                manager.restore_backup(fname)
            except Exception as e:
                CTkMessageBox.showerror(
                    "Restore Failed", f"Failed to restore backup:\n{e}", parent=dialog
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
            self.show_toast("Backup restored", duration=3000)

        def delete_backup():
            if not selected:
                CTkMessageBox.showwarning(
                    "No Selection",
                    "Select one or more backups to delete.",
                    parent=dialog,
                )
                return
            locked = [fn for fn in selected if backup_items[fn]["metadata"].favorite]
            targets = [fn for fn in selected if fn not in locked]
            if not targets:
                CTkMessageBox.showwarning(
                    "Backup Locked",
                    "The selected backups are locked and cannot be deleted.\n\n"
                    "Click a star to unlock it first.",
                    parent=dialog,
                )
                return
            what = (
                f"backup '{targets[0]}'"
                if len(targets) == 1
                else f"{len(targets)} backups"
            )
            note = f"\n\n{len(locked)} locked backup(s) will be kept." if locked else ""
            if not CTkMessageBox.askyesno(
                "Confirm Delete",
                f"Delete {what}?{note}\n\nThis cannot be undone.",
                parent=dialog,
            ):
                return
            failed = []
            for fn in targets:
                try:
                    manager.delete_backup(fn)
                except Exception as e:
                    failed.append(f"{fn}: {e}")
            refresh_list()
            self.update_backup_stats()
            if failed:
                CTkMessageBox.showerror(
                    "Delete Failed",
                    "Failed to delete:\n" + "\n".join(failed),
                    parent=dialog,
                )
            deleted = len(targets) - len(failed)
            if deleted:
                self.show_toast(
                    "Backup deleted" if deleted == 1 else f"{deleted} backups deleted",
                    duration=2500,
                )

        def view_details():
            fname = single_selection("view")
            if fname is None:
                return

            info = manager.get_backup_info(fname)
            if not info:
                CTkMessageBox.showwarning(
                    "Not Found", "Backup metadata not found.", parent=dialog
                )
                return

            dd = ds.create(dialog, "Backup Details")
            main_frame = ctk.CTkFrame(dd, fg_color="transparent")
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

            ds.button_row(main_frame, [{"text": "Close", "command": dd.destroy}])
            ds.header(main_frame, info.filename)

            rows = [
                ("Created", info.timestamp[:19].replace("T", " ")),
                ("Operation", info.operation or "manual"),
                ("Description", info.description or ""),
                ("Size", f"{info.file_size / (1024 * 1024):.2f} MB"),
                ("Folder", str(manager.backup_folder)),
            ]
            box = ds.box(main_frame, pady=(12, 0))
            box.grid_columnconfigure(1, weight=1)
            for i, (label, value) in enumerate(rows):
                pady = (8 if i == 0 else 2, 8 if i == len(rows) - 1 else 2)
                ctk.CTkLabel(box, text=label, font=ds.FONT, text_color=ds.MUTED).grid(
                    row=i, column=0, sticky="nw", padx=(12, 20), pady=pady
                )
                ctk.CTkLabel(
                    box, text=value, font=ds.FONT, wraplength=420, justify=tk.LEFT
                ).grid(row=i, column=1, sticky="w", padx=(0, 12), pady=pady)

            if info.character_summary:
                ctk.CTkLabel(main_frame, text="Characters", font=ds.BOLD).pack(
                    anchor=tk.W, pady=(10, 0)
                )
                chars = ds.box(main_frame, pady=(4, 0))
                summary = info.character_summary
                for i, char in enumerate(summary):
                    pady = (8 if i == 0 else 1, 8 if i == len(summary) - 1 else 1)
                    ctk.CTkLabel(
                        chars,
                        text=f"Slot {char['slot']}",
                        font=ds.FONT,
                        text_color=ds.MUTED,
                    ).grid(row=i, column=0, sticky="w", padx=(12, 20), pady=pady)
                    ctk.CTkLabel(
                        chars,
                        text=f"{char['name']} (Lv. {char['level']})",
                        font=ds.FONT,
                    ).grid(row=i, column=1, sticky="w", padx=(0, 12), pady=pady)

            ds.finish(dd, dialog, min_width=440)

        def open_backup_folder():
            if not open_folder(manager.backup_folder):
                CTkMessageBox.showerror(
                    "Folder Not Opened",
                    f"Could not open folder.\nPath: {manager.backup_folder}",
                    parent=dialog,
                )

        # Actions on the selection on the left, window actions on the right
        for text, cmd, primary in [
            ("Create Backup", create_backup, True),
            ("Restore", restore_backup, True),
            ("View Details", view_details, False),
            ("Delete", delete_backup, False),
        ]:
            ds.button(button_frame, text, cmd, primary=primary, width=120).pack(
                side=tk.LEFT, padx=(0, 8)
            )
        ds.button(button_frame, "Close", dialog.destroy, primary=False).pack(
            side=tk.RIGHT
        )
        for text, cmd in [
            ("Open Folder", open_backup_folder),
            ("Refresh", refresh_list),
        ]:
            ds.button(button_frame, text, cmd, primary=False, width=110).pack(
                side=tk.RIGHT, padx=(0, 8)
            )

        sort_combo.configure(command=lambda _choice: refresh_list())

        refresh_list()
