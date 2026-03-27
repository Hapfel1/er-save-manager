"""
SteamID Patcher Tab
Patches SteamID in save files for all supported FromSoftware games.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


class SteamIDPatcherTab:
    """Tab for SteamID patching operations across all supported games."""

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

        self.current_steamid_var = None
        self.new_steamid_var = None
        self.steam_url_var = None
        self._game_var: tk.StringVar | None = None
        self._profiles: list = []
        self._note_var: tk.StringVar | None = None
        self._note_frame: ctk.CTkFrame | None = None
        self._patch_btn: ctk.CTkButton | None = None

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

    def setup_ui(self):
        main_frame = ctk.CTkScrollableFrame(self.parent, corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(main_frame)

        ctk.CTkLabel(
            main_frame,
            text="SteamID Patcher",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(15, 5), padx=15, anchor="w")

        ctk.CTkLabel(
            main_frame,
            text="Transfer save files between Steam accounts by patching SteamID",
            font=("Segoe UI", 11),
            text_color=("#808080", "#a0a0a0"),
        ).pack(pady=(0, 10), padx=15, anchor="w")

        # Current save display
        current_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        current_frame.pack(fill=tk.X, padx=15, pady=(0, 12))

        ctk.CTkLabel(
            current_frame,
            text="Current Save File",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(12, 6), padx=12, anchor="w")

        self.current_steamid_var = tk.StringVar(value="No save file loaded")
        ctk.CTkLabel(
            current_frame,
            textvariable=self.current_steamid_var,
            font=("Consolas", 11),
            text_color=("#2a2a2a", "#e5e5f5"),
        ).pack(pady=(0, 12), padx=12, anchor="w")

        # Note / warning for selected game — hidden when empty
        self._note_frame = ctk.CTkFrame(
            main_frame, corner_radius=10, fg_color=("gray90", "gray18")
        )
        # Don't pack yet — _on_game_changed will show/hide based on content

        self._note_var = tk.StringVar(value="")
        self._note_label = ctk.CTkLabel(
            self._note_frame,
            textvariable=self._note_var,
            font=("Segoe UI", 11),
            text_color=("gray30", "gray70"),
            justify=tk.LEFT,
            wraplength=560,
        )
        self._note_label.pack(anchor="w", padx=12, pady=10)

        # Patch section
        patch_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        patch_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        ctk.CTkLabel(
            patch_frame,
            text="Patch SteamID",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(12, 8), padx=12, anchor="w")

        ctk.CTkLabel(
            patch_frame,
            text="Enter new SteamID (17-digit number):",
            font=("Segoe UI", 12),
            text_color=("gray40", "gray70"),
        ).pack(pady=(0, 6), padx=12, anchor="w")

        entry_row = ctk.CTkFrame(patch_frame, fg_color="transparent")
        entry_row.pack(fill=tk.X, pady=(0, 10), padx=12)

        self.new_steamid_var = tk.StringVar(value="")
        ctk.CTkEntry(
            entry_row,
            textvariable=self.new_steamid_var,
            font=("Consolas", 11),
            width=180,
            placeholder_text="76561198012345678",
        ).pack(side=tk.LEFT, padx=(0, 8))

        self._patch_btn = ctk.CTkButton(
            entry_row,
            text="Patch SteamID",
            command=self.patch_steamid,
            width=120,
        )
        self._patch_btn.pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            entry_row,
            text="Auto-Detect",
            command=self.auto_detect_steamid,
            width=110,
        ).pack(side=tk.LEFT)

        # Steam profile URL
        ctk.CTkLabel(
            patch_frame,
            text="Or paste Steam profile URL:",
            font=("Segoe UI", 12),
            text_color=("gray40", "gray70"),
        ).pack(pady=(12, 6), padx=12, anchor="w")

        url_row = ctk.CTkFrame(patch_frame, fg_color="transparent")
        url_row.pack(fill=tk.X, pady=(0, 12), padx=12)

        self.steam_url_var = tk.StringVar(value="")
        ctk.CTkEntry(
            url_row,
            textvariable=self.steam_url_var,
            font=("Consolas", 10),
            placeholder_text="https://steamcommunity.com/profiles/...",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        ctk.CTkButton(
            url_row,
            text="Parse URL",
            command=self.parse_steam_url,
            width=100,
        ).pack(side=tk.LEFT)

        ctk.CTkButton(
            patch_frame,
            text="How to Use / Help",
            command=self._show_help_dialog,
            text_color=("#2a5f3f", "#a8d5ba"),
            fg_color=("#d0f0e5", "#1a3a2a"),
            width=140,
        ).pack(pady=(0, 12), padx=12, anchor="w")

    def set_active_profile(self, profile_name: str):
        """Called by gui.py when the global game selection changes."""
        for p in self._get_profiles():
            if p.name == profile_name:
                # Store selected profile key directly — no internal dropdown
                self._active_profile_key = p.key
                self._on_game_changed()
                return

    def _selected_profile(self):
        # Use the key stored by set_active_profile (driven by global selector)
        key = getattr(self, "_active_profile_key", None)
        if key:
            for p in self._get_profiles():
                if p.key == key:
                    return p
        # Fallback: first profile (ER)
        profiles = self._get_profiles()
        return profiles[0] if profiles else None

    def _on_game_changed(self, _value=None):
        profile = self._selected_profile()
        if profile is None:
            return

        if not profile.supports_steamid_patch:
            note = (
                profile.steamid_patch_note
                or "SteamID patching is not supported for this game."
            )
            self._note_var.set(note)
            if self._note_frame:
                self._note_frame.pack(fill=tk.X, padx=15, pady=(0, 12))
            if self._patch_btn:
                self._patch_btn.configure(state="disabled")
        else:
            note = profile.steamid_patch_note or ""
            self._note_var.set(note)
            if self._note_frame:
                if note:
                    self._note_frame.pack(fill=tk.X, padx=15, pady=(0, 12))
                else:
                    self._note_frame.pack_forget()
            if self._patch_btn:
                self._patch_btn.configure(state="normal")

        # Defer the file scan off the UI thread
        import threading

        threading.Thread(target=self._refresh_steamid_display, daemon=True).start()

    def _refresh_steamid_display(self):
        profile = self._selected_profile()
        if profile is None:
            return

    def _refresh_steamid_display(self):
        """Scan the save file for its SteamID. Safe to call from a background thread."""
        profile = self._selected_profile()
        if profile is None:
            return

        def _set(text: str):
            try:
                self.current_steamid_var.set(text)
            except Exception:
                pass

        if profile.key == "elden_ring":
            # ER: read from already-parsed save object (main thread safe via StringVar)
            self.update_steamid_display()
            return

        from er_save_manager.games.generic_steamid import detect_steamid_in_file
        from er_save_manager.platform.utils import PlatformUtils

        paths = PlatformUtils.find_all_save_files(profile)
        if not paths:
            _set(f"No save file found for {profile.name}")
            return

        save_path = paths[0]
        try:
            steamid = detect_steamid_in_file(save_path)
        except Exception as e:
            _set(f"Save: {save_path.name}  |  Error: {e}")
            return

        if steamid:
            _set(f"Save: {save_path.name}  |  SteamID: {steamid}")
        else:
            _set(f"Save: {save_path.name}  |  SteamID: could not detect")

    def update_steamid_display(self):
        """Update current SteamID display for the loaded ER save."""
        save_file = self.get_save_file()
        if not save_file:
            self.current_steamid_var.set("No save file loaded")
            return

        try:
            if not save_file.user_data_10_parsed:
                self.current_steamid_var.set("SteamID: Unable to parse save file")
                return

            if not hasattr(save_file.user_data_10_parsed, "steam_id"):
                self.current_steamid_var.set("SteamID: Attribute not found")
                return

            steamid = save_file.user_data_10_parsed.steam_id

            if steamid == 0:
                self.current_steamid_var.set(
                    "SteamID: 0 (Invalid - save may be corrupted)"
                )
            elif steamid < 76561197960265728:
                self.current_steamid_var.set(f"SteamID: {steamid} (Invalid format)")
            else:
                self.current_steamid_var.set(f"Current SteamID: {steamid}")

        except Exception as e:
            self.current_steamid_var.set(f"SteamID: Error - {e}")

    def patch_steamid(self):
        profile = self._selected_profile()
        if profile is None:
            CTkMessageBox.showwarning(
                "No Game", "Please select a game.", parent=self.parent
            )
            return

        if not profile.supports_steamid_patch:
            CTkMessageBox.showwarning(
                "Not Supported",
                profile.steamid_patch_note
                or "SteamID patching is not supported for this game.",
                parent=self.parent,
            )
            return

        new_steamid_str = self.new_steamid_var.get().strip()
        if not new_steamid_str.isdigit() or len(new_steamid_str) != 17:
            CTkMessageBox.showerror(
                "Invalid SteamID",
                "SteamID must be exactly 17 digits",
                parent=self.parent,
            )
            return

        new_steamid = int(new_steamid_str)

        if profile.key == "elden_ring":
            self._patch_er(new_steamid)
        else:
            self._patch_generic(profile, new_steamid)

    def _patch_er(self, new_steamid: int):
        """Patch using the full ER save model (loaded save)."""
        import struct

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save",
                "Please load an Elden Ring save file first.",
                parent=self.parent,
            )
            return

        if not CTkMessageBox.askyesno(
            "Confirm Patch",
            f"Patch all character slots to SteamID: {new_steamid}?\n\nA backup will be created.",
            parent=self.parent,
        ):
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.fixes.steamid import SteamIdFix

            save_path = self.get_save_path()
            if save_path:
                BackupManager(Path(save_path)).create_backup(
                    description=f"before_steamid_patch_{str(new_steamid)[:8]}",
                    operation="patch_steamid",
                    save=save_file,
                )

            old_steamid = 0
            if save_file.user_data_10_parsed:
                old_steamid = save_file.user_data_10_parsed.steam_id
                save_file.user_data_10_parsed.steam_id = new_steamid

                steamid_offset = (
                    save_file._user_data_10_offset + (0 if save_file.is_ps else 16) + 4
                )
                save_file._raw_data[steamid_offset : steamid_offset + 8] = struct.pack(
                    "<Q", new_steamid
                )

                if (
                    hasattr(save_file.user_data_10_parsed, "profile_summary")
                    and save_file.user_data_10_parsed.profile_summary
                ):
                    for (
                        profile
                    ) in save_file.user_data_10_parsed.profile_summary.profiles:
                        if hasattr(profile, "steam_id"):
                            profile.steam_id = new_steamid

            patched_count = 0
            fix = SteamIdFix()
            for slot_idx in range(10):
                result = fix.apply(save_file, slot_idx)
                if result.applied:
                    patched_count += 1

            save_file.recalculate_checksums()
            if save_path:
                save_file.to_file(Path(save_path))

            if self.reload_save:
                self.reload_save()

            self.parent.after(
                100,
                lambda: CTkMessageBox.showinfo(
                    "Success",
                    f"Updated USER_DATA_10 SteamID\n"
                    f"Updated profile summary\n"
                    f"Synced {patched_count} character slot(s)\n\n"
                    f"Old SteamID: {old_steamid}\n"
                    f"New SteamID: {new_steamid}\n\n"
                    f"Backup saved to backup manager.",
                    parent=self.parent,
                ),
            )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"SteamID patch failed:\n{e}", parent=self.parent
            )

    def _patch_generic(self, profile, new_steamid: int):
        """Patch using generic BND4 byte-scan for non-ER games."""
        from er_save_manager.games.generic_steamid import patch_steamid_generic
        from er_save_manager.platform.utils import PlatformUtils

        paths = PlatformUtils.find_all_save_files(profile)
        if not paths:
            CTkMessageBox.showwarning(
                "No Save File",
                f"No save file found for {profile.name}.\n\n"
                "Launch the game at least once so the save file is created,\n"
                "then try again.",
                parent=self.parent,
            )
            return

        # If multiple saves found (multiple Steam accounts), let user pick
        save_path = paths[0]
        if len(paths) > 1:
            save_path = self._pick_save_path(paths)
            if save_path is None:
                return

        if not CTkMessageBox.askyesno(
            "Confirm Patch",
            f"Patch SteamID in:\n{save_path}\n\nNew SteamID: {new_steamid}\n\nA backup will be created.",
            parent=self.parent,
        ):
            return

        try:
            from er_save_manager.backup.manager import BackupManager

            BackupManager(save_path).create_backup(
                description=f"before_steamid_patch_{str(new_steamid)[:8]}",
                operation="patch_steamid",
            )

            result = patch_steamid_generic(save_path, new_steamid)

            if not result.success:
                CTkMessageBox.showerror(
                    "Patch Failed",
                    f"SteamID patch failed:\n{result.error}",
                    parent=self.parent,
                )
                return

            self._refresh_steamid_display()
            CTkMessageBox.showinfo(
                "Success",
                f"Patched {result.replacements} occurrence(s)\n\n"
                f"Old SteamID: {result.old_steamid}\n"
                f"New SteamID: {result.new_steamid}\n\n"
                f"Backup created before patching.",
                parent=self.parent,
            )

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"SteamID patch failed:\n{e}", parent=self.parent
            )

    def _pick_save_path(self, paths: list[Path]) -> Path | None:
        """Show dialog to pick from multiple save files."""
        from er_save_manager.ui.utils import force_render_dialog

        selected = [None]
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Select Save File")
        dialog.geometry("500x320")
        dialog.resizable(False, False)
        force_render_dialog(dialog)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Multiple save files found.\nSelect the one to patch:",
            font=("Segoe UI", 11),
        ).pack(pady=(15, 12), padx=15)

        list_frame = ctk.CTkScrollableFrame(dialog, corner_radius=8)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        bind_mousewheel(list_frame)

        for path in paths:

            def make_select(p):
                def _select():
                    selected[0] = p
                    dialog.destroy()

                return _select

            ctk.CTkButton(
                list_frame,
                text=str(path),
                font=("Consolas", 10),
                command=make_select(path),
                fg_color="transparent",
                text_color=("#2a2a2a", "#e5e5f5"),
                hover_color=("#c9a0dc", "#3b2f5c"),
                anchor="w",
            ).pack(fill=tk.X, padx=6, pady=4)

        ctk.CTkButton(dialog, text="Cancel", command=dialog.destroy, width=100).pack(
            pady=(0, 12)
        )

        dialog.wait_window()
        return selected[0]

    def parse_steam_url(self):
        url = self.steam_url_var.get().strip()
        if not url:
            CTkMessageBox.showwarning(
                "Empty URL", "Please enter a Steam profile URL", parent=self.parent
            )
            return

        import re

        if url.isdigit() and len(url) == 17:
            self.new_steamid_var.set(url)
            self.steam_url_var.set("")
            self.show_toast(f"SteamID: {url}", duration=2000)
            return

        match = re.search(r"/profiles/(\d{17})", url)
        if match:
            steamid = match.group(1)
            self.new_steamid_var.set(steamid)
            self.steam_url_var.set("")
            self.show_toast(f"Extracted SteamID: {steamid}", duration=2500)
            return

        # Try to resolve vanity URL
        match = re.search(r"/id/([^/]+)", url)
        if match:
            custom_name = match.group(1)
            self._resolve_vanity_url(custom_name)
            return

        CTkMessageBox.showerror(
            "Invalid URL",
            "Could not extract SteamID from URL.\n\nSupported formats:\n"
            "  https://steamcommunity.com/profiles/76561198012345678\n"
            "  https://steamcommunity.com/id/username",
            parent=self.parent,
        )

    def _resolve_vanity_url(self, custom_name: str):
        try:
            import json
            import urllib.request

            api_url = f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key=&vanityurl={custom_name}&format=json"
            with urllib.request.urlopen(api_url, timeout=5) as resp:
                data = json.loads(resp.read())

            if data.get("response", {}).get("success") == 1:
                steamid = data["response"]["steamid"]
                self.new_steamid_var.set(steamid)
                self.steam_url_var.set("")
                self.show_toast(f"Resolved: {steamid}", duration=2500)
            else:
                CTkMessageBox.showerror(
                    "Not Found",
                    f"Could not resolve Steam vanity URL: {custom_name}\n\n"
                    "Enter the SteamID directly instead.",
                    parent=self.parent,
                )
        except Exception as e:
            CTkMessageBox.showerror(
                "Resolution Failed",
                f"Failed to resolve vanity URL: {custom_name}\n\nError: {e}",
                parent=self.parent,
            )

    def auto_detect_steamid(self):
        """
        Auto-detect SteamID for the currently selected game.

        Strategy:
        - Find all save files for the game using PlatformUtils.find_all_save_files.
        - Extract SteamID from the save file's parent folder name (17-digit Steam64 subfolder).
        - Fallback: scan the save file bytes for a valid Steam64 ID.
        - If multiple accounts are found, show a selection dialog.
        """
        from er_save_manager.games.game_profiles import _folder_name_to_steam64
        from er_save_manager.games.generic_steamid import detect_steamid_in_file
        from er_save_manager.platform.utils import PlatformUtils

        profile = self._selected_profile()

        try:
            steam_users: list[tuple[str, int]] = []

            # Primary: find save files and extract SteamID from the folder name
            # (works for all games that use a SteamID subfolder structure)
            save_paths = PlatformUtils.find_all_save_files(profile)
            for save_path in save_paths:
                folder_name = save_path.parent.name
                steamid = _folder_name_to_steam64(folder_name, profile)
                if steamid is None:
                    continue
                label = f"Account {steamid} ({save_path.name})"
                if steamid not in {s for _, s in steam_users}:
                    steam_users.append((label, steamid))

            # Fallback: scan save file bytes for Steam64 IDs
            if not steam_users:
                for save_path in save_paths:
                    steamid = detect_steamid_in_file(save_path)
                    if steamid and steamid not in {s for _, s in steam_users}:
                        label = f"Account {steamid} ({save_path.name})"
                        steam_users.append((label, steamid))

            if not steam_users:
                game_name = profile.name if profile else "this game"
                CTkMessageBox.showwarning(
                    "Not Found",
                    f"Could not detect any Steam accounts for {game_name}.\n\n"
                    "Make sure the game has been launched at least once,\n"
                    "then try again. Or enter the SteamID manually.",
                    parent=self.parent,
                )
                return

            # Deduplicate preserving order
            seen: dict[int, str] = {}
            for name, sid in steam_users:
                if sid not in seen:
                    seen[sid] = name
            steam_users = [(name, sid) for sid, name in seen.items()]

            if len(steam_users) == 1:
                self.new_steamid_var.set(str(steam_users[0][1]))
                self.show_toast(f"SteamID detected: {steam_users[0][1]}", duration=2500)
                return

            self._show_account_selection_dialog(steam_users)

        except Exception as e:
            CTkMessageBox.showwarning(
                "Detection Failed",
                f"Could not auto-detect SteamID:\n{e}",
                parent=self.parent,
            )

    def _show_account_selection_dialog(self, accounts):
        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Select Steam Account")
        dialog.geometry("450x350")
        dialog.resizable(False, False)
        force_render_dialog(dialog)
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Multiple Steam accounts detected.\nSelect the account to use:",
            font=("Segoe UI", 11),
        ).pack(pady=(15, 12), padx=15)

        list_frame = ctk.CTkScrollableFrame(dialog, corner_radius=8)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        bind_mousewheel(list_frame)

        for account_name, steamid in accounts:

            def make_select(sid, name):
                def select_account():
                    self.new_steamid_var.set(str(sid))
                    dialog.destroy()
                    self.show_toast(f"Selected: {name}", duration=2500)

                return select_account

            btn_frame = ctk.CTkFrame(
                list_frame, corner_radius=8, fg_color=("#f0f0f0", "#2a2a3e")
            )
            btn_frame.pack(fill=tk.X, pady=4)

            ctk.CTkButton(
                btn_frame,
                text=f"{account_name}  ({steamid})",
                font=("Consolas", 10),
                command=make_select(steamid, account_name),
                fg_color="transparent",
                text_color=("#2a2a2a", "#e5e5f5"),
                hover_color=("#c9a0dc", "#3b2f5c"),
            ).pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        ctk.CTkButton(dialog, text="Cancel", command=dialog.destroy, width=100).pack(
            pady=(0, 15), side=tk.RIGHT, padx=15
        )

    def _show_help_dialog(self):
        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("SteamID Patcher - Help")
        width, height = 720, 620
        dialog.resizable(True, True)
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

        header = ctk.CTkFrame(dialog, corner_radius=10)
        header.pack(fill=tk.X, padx=14, pady=(14, 8))
        ctk.CTkLabel(
            header,
            text="SteamID Patcher - Help",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(8, 2), padx=10)
        ctk.CTkLabel(
            header,
            text="Patch SteamIDs when moving saves between Steam accounts.",
            font=("Segoe UI", 12),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=10, pady=(0, 8))

        body = ctk.CTkScrollableFrame(dialog, corner_radius=10)
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))
        bind_mousewheel(body)

        def add_section(title: str, text: str):
            section = ctk.CTkFrame(body, fg_color=("gray90", "gray18"), corner_radius=8)
            section.pack(fill=tk.X, expand=True, padx=8, pady=(0, 10))
            ctk.CTkLabel(
                section,
                text=title,
                font=("Segoe UI", 12, "bold"),
                text_color=("#111", "#e7e7ef"),
            ).pack(anchor="w", padx=10, pady=(8, 2))
            ctk.CTkLabel(
                section,
                text=text,
                font=("Segoe UI", 12),
                wraplength=640,
                justify=ctk.LEFT,
            ).pack(anchor="w", padx=10, pady=(0, 10))

        add_section(
            "Supported games",
            "Elden Ring, Elden Ring Nightreign, Dark Souls Remastered, Dark Souls II SotFS, "
            "Dark Souls III: Full SteamID patch supported.\n\n"
            "Sekiro: Shadows Die Twice: No file-level SteamID patch. Use SimpleSekiroSavegameHelper "
            "(RAM patch) to load foreign saves.\n\n"
            "Armored Core 6: Save files are AES-encrypted. Use the dedicated AC6SaveTransferTool "
            "by Nordgaren instead.",
        )

        add_section(
            "What is SteamID patching?",
            "When you move a save to another Steam account, the embedded SteamID no longer "
            "matches. The game refuses to load it. This tool rewrites the SteamID throughout "
            "the save file so the target account can load it.",
        )

        add_section(
            "Quick steps",
            "1) Select the game.\n"
            "2) Get the target SteamID via Auto-Detect, URL parse, or manual entry.\n"
            "3) Click Patch SteamID. A backup is created automatically.\n"
            "4) Load the patched save on the new account.",
        )

        add_section(
            "Elden Ring - extra detail",
            "For Elden Ring, load the save file first. The patch updates USER_DATA_10, "
            "the profile summary, and all 10 character slots, then recalculates checksums.",
        )

        add_section(
            "Other games (DS1/DS2/DS3/Nightreign)",
            "No need to load the save in the editor. The patcher scans the raw BND4 file "
            "for all occurrences of the old SteamID and replaces them. A backup is created first.",
        )

        ctk.CTkButton(dialog, text="Close", command=dialog.destroy, width=110).pack(
            pady=(0, 14)
        )
