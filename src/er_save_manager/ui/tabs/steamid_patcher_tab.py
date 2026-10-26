"""
SteamID Patcher Tab
Patches SteamID in save files for all supported FromSoftware games.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette
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
        self._active_profile_key: str = "elden_ring"
        self._profiles: list = []
        self._note_var: tk.StringVar | None = None
        self._note_frame: ctk.CTkFrame | None = None
        self._patch_btn: ctk.CTkButton | None = None
        self._current_frame: ctk.CTkFrame | None = None
        self._patch_frame: ctk.CTkFrame | None = None

    def _get_profiles(self):
        if not self._profiles:
            from er_save_manager.games.game_profiles import GAME_PROFILES

            self._profiles = GAME_PROFILES
        return self._profiles

    def _selected_profile(self):
        for p in self._get_profiles():
            if p.key == self._active_profile_key:
                return p
        profiles = self._get_profiles()
        return profiles[0] if profiles else None

    def set_active_profile(self, profile_name: str):
        """Called by gui.py when the global game selection changes."""
        for p in self._get_profiles():
            if p.name == profile_name:
                self._active_profile_key = p.key
                import threading

                threading.Thread(target=self._on_game_changed, daemon=True).start()
                return

    def setup_ui(self):
        main_frame = ctk.CTkScrollableFrame(self.parent, corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(main_frame)

        ctk.CTkLabel(
            main_frame,
            text="SteamID Patcher",
            font=("Inter", 18, "bold"),
        ).pack(pady=(15, 5), padx=15, anchor="w")

        ctk.CTkLabel(
            main_frame,
            text="Transfer save files between Steam accounts by patching SteamID",
            font=("Inter", 11),
            text_color=("#808080", "#a0a0a0"),
        ).pack(pady=(0, 10), padx=15, anchor="w")

        current_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        current_frame.pack(fill=tk.X, padx=15, pady=(0, 12))
        self._current_frame = current_frame

        ctk.CTkLabel(
            current_frame,
            text="Current save file",
            font=("Inter", 12, "bold"),
        ).pack(pady=(12, 6), padx=12, anchor="w")

        self.current_steamid_var = tk.StringVar(value="No save file loaded")
        ctk.CTkLabel(
            current_frame,
            textvariable=self.current_steamid_var,
            font=("Inter", 12),
        ).pack(pady=(0, 12), padx=12, anchor="w")

        # Note / warning for selected game - hidden when empty
        self._note_frame = ctk.CTkFrame(
            main_frame, corner_radius=10, fg_color=("gray90", "gray18")
        )
        # Don't pack yet - _on_game_changed will show/hide based on content

        self._note_var = tk.StringVar(value="")
        self._note_label = ctk.CTkLabel(
            self._note_frame,
            textvariable=self._note_var,
            font=("Inter", 11),
            text_color=("gray30", "gray70"),
            justify=tk.LEFT,
            wraplength=560,
        )
        self._note_label.pack(anchor="w", padx=12, pady=10)
        patch_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        patch_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        self._patch_frame = patch_frame

        ctk.CTkLabel(
            patch_frame,
            text="Patch SteamID",
            font=("Inter", 12, "bold"),
        ).pack(pady=(12, 8), padx=12, anchor="w")

        ctk.CTkLabel(
            patch_frame,
            text="Enter new SteamID (17-digit number):",
            font=("Inter", 12),
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

        ctk.CTkLabel(
            patch_frame,
            text="Or paste Steam profile URL:",
            font=("Inter", 12),
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
            fg_color=ds.SECONDARY,
            width=140,
        ).pack(pady=(0, 12), padx=12, anchor="w")

    def _on_game_changed(self, _value=None):
        profile = self._selected_profile()
        if profile is None:
            return

        def _update_ui():
            if self._patch_frame and not self._patch_frame.winfo_ismapped():
                self._patch_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
            if self._current_frame and not self._current_frame.winfo_ismapped():
                if self._patch_frame is not None:
                    self._current_frame.pack(
                        fill=tk.X, padx=15, pady=(0, 12), before=self._patch_frame
                    )
                else:
                    self._current_frame.pack(fill=tk.X, padx=15, pady=(0, 12))

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

        try:
            self.parent.after(0, _update_ui)
        except Exception:
            _update_ui()

        self._refresh_steamid_display()

    def _refresh_steamid_display(self):
        """Scan the save file for its SteamID. Safe to call from a background thread."""
        profile = self._selected_profile()
        if profile is None:
            return

        def _set(text: str):
            try:
                self.parent.after(0, lambda: self.current_steamid_var.set(text))
            except Exception:
                try:
                    self.current_steamid_var.set(text)
                except Exception:
                    pass

        if profile.key == "elden_ring":
            self.update_steamid_display()
            return

        if not profile.supports_steamid_patch:
            note = (
                profile.steamid_patch_note
                or "SteamID patching is not supported for this game."
            )
            _set(note)
            return

        from er_save_manager.games.generic_steamid import detect_steamid_in_file

        selected = self.get_save_path()
        if not selected or not Path(selected).exists():
            _set("No save file selected")
            return

        save_path = Path(selected)

        if profile.key == "dark_souls_3":
            from er_save_manager.games.DS3.parser import is_ps_userdata

            if is_ps_userdata(save_path):
                _set(
                    f"Save: {save_path.name}  |  PS4 saves have no SteamID. "
                    "Transferring a character to a PC save sets it."
                )
                return

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
            CTkMessageBox.showwarning("No Game", "Select a game.", parent=self.parent)
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
            # Disable button during patch to prevent double-click and avoid UI freeze
            if self._patch_btn:
                self._patch_btn.configure(state="disabled", text="Patching...")
            import threading

            def _run():
                try:
                    self._patch_generic(profile, new_steamid)
                finally:
                    try:
                        self.parent.after(
                            0,
                            lambda: (
                                self._patch_btn.configure(
                                    state="normal", text="Patch SteamID"
                                )
                                if self._patch_btn
                                else None
                            ),
                        )
                    except Exception:
                        pass

            threading.Thread(target=_run, daemon=True).start()

    def _patch_er(self, new_steamid: int):
        """Patch using the full ER save model (loaded save)."""
        import struct

        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save",
                "Load an Elden Ring save file first.",
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
                    "SteamID Patched",
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
                "Patch Failed", f"SteamID patch failed:\n{e}", parent=self.parent
            )

    def _patch_generic(self, profile, new_steamid: int):
        """Patch SteamID for non-ER games. Called from a background thread - dialogs use after(0,...)."""
        # Resolve save path (no auto-disk-scan; user must select a file first)
        selected = self.get_save_path()
        if not selected or not Path(selected).exists():
            self.parent.after(
                0,
                lambda: CTkMessageBox.showwarning(
                    "No Save File",
                    "Select a save file first using Browse or Auto-Find.",
                    parent=self.parent,
                ),
            )
            return
        save_path = Path(selected)

        # Confirm dialog must run on main thread - use a threading Event to wait
        import threading

        confirmed = threading.Event()
        confirmed_result = [False]

        def _ask():
            result = CTkMessageBox.askyesno(
                "Confirm Patch",
                f"Patch SteamID in:\n{save_path}\n\nNew SteamID: {new_steamid}\n\nA backup will be created.",
                parent=self.parent,
            )
            confirmed_result[0] = result
            confirmed.set()

        self.parent.after(0, _ask)
        confirmed.wait()
        if not confirmed_result[0]:
            return

        def _show_error(msg):
            self.parent.after(
                0,
                lambda: CTkMessageBox.showerror(
                    "Patch Failed", f"SteamID patch failed:\n{msg}", parent=self.parent
                ),
            )

        def _show_success(msg):
            self._refresh_steamid_display()
            # The DS2 and DS3 editors keep the decrypted save in memory and
            # would write the old SteamID back on their next save.
            if self.reload_save and profile.key in ("dark_souls_2", "dark_souls_3"):
                self.parent.after(
                    0, lambda: self.reload_save(toast_message="Save file reloaded")
                )
            self.parent.after(
                0,
                lambda: CTkMessageBox.showinfo(
                    "SteamID Patched",
                    f"{msg}\n\nBackup created before patching.",
                    parent=self.parent,
                ),
            )

        try:
            from er_save_manager.backup.manager import BackupManager

            BackupManager(save_path).create_backup(
                description=f"before_steamid_patch_{str(new_steamid)[:8]}",
                operation="patch_steamid",
            )

            if profile.key == "nightreign":
                from er_save_manager.games.nightreign_steamid import patch_steamid_nr

                success, msg = patch_steamid_nr(save_path, new_steamid)
            elif profile.key == "armored_core_6":
                from er_save_manager.games.ac6_steamid import patch_steamid_ac6

                success, msg = patch_steamid_ac6(save_path, new_steamid)
            elif profile.key == "dark_souls_3":
                from er_save_manager.games.ds3_steamid import patch_steamid_ds3

                success, msg = patch_steamid_ds3(save_path, new_steamid)
            elif profile.key == "dark_souls_2":
                from er_save_manager.games.ds2_dsr_steamid import patch_steamid

                success, msg = patch_steamid(save_path, new_steamid, profile.key)
            elif profile.key == "sekiro":
                from er_save_manager.games.sekiro_steamid import patch_steamid_sekiro

                success, msg = patch_steamid_sekiro(save_path, new_steamid)
            elif profile.key == "dark_souls_remastered":
                success, msg = (
                    True,
                    (
                        "Dark Souls Remastered does not store a SteamID inside the save file.\n\n"
                        "The game uses the save folder name to identify your account.\n"
                        "Use the folder-rename feature to move the save to the correct Steam account folder."
                    ),
                )
            else:
                success, msg = None, None

            if success is not None:
                if not success:
                    _show_error(msg)
                else:
                    _show_success(msg)
            else:
                from er_save_manager.games.generic_steamid import patch_steamid_generic

                result = patch_steamid_generic(save_path, new_steamid)
                if not result.success:
                    _show_error(result.error)
                else:
                    _show_success(
                        f"Patched {result.replacements} occurrence(s)\n\n"
                        f"Old SteamID: {result.old_steamid}\n"
                        f"New SteamID: {result.new_steamid}"
                    )

        except Exception as e:
            err = str(e)
            self.parent.after(
                0,
                lambda: CTkMessageBox.showerror(
                    "Patch Failed", f"SteamID patch failed:\n{err}", parent=self.parent
                ),
            )

    def _pick_save_path(self, paths: list[Path]) -> Path | None:
        """Show dialog to pick from multiple save files."""
        from er_save_manager.ui.dialogs.save_selector import SaveSelectorDialog

        chosen = SaveSelectorDialog.show(self.parent, paths, lambda _p: None)
        return Path(chosen) if chosen else None

    def parse_steam_url(self):
        url = self.steam_url_var.get().strip()
        if not url:
            CTkMessageBox.showwarning(
                "Empty URL", "Enter a Steam profile URL", parent=self.parent
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
        # Steam's XML profile endpoint requires no API key and returns
        # a <steamID64> element directly.
        try:
            import re
            import urllib.request

            xml_url = f"https://steamcommunity.com/id/{custom_name}/?xml=1"
            req = urllib.request.Request(xml_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                body = resp.read().decode("utf-8", errors="replace")

            match = re.search(r"<steamID64>(\d{17})</steamID64>", body)
            if match:
                steamid = match.group(1)
                self.new_steamid_var.set(steamid)
                self.steam_url_var.set("")
                self.show_toast(f"Resolved: {steamid}", duration=2500)
            else:
                CTkMessageBox.showerror(
                    "Not Found",
                    f"Could not resolve Steam vanity URL: {custom_name}\n\n"
                    "The profile may be private or the name may be incorrect.\n"
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

        Detection order:
        1. loginusers.vdf - returns persona names; read via plain text, no
           subprocess or credential-store APIs (safe on Windows Defender).
        2. Folder-name extraction from found save paths.
        3. Byte-scan fallback.
        """
        from er_save_manager.games.game_profiles import _folder_name_to_steam64
        from er_save_manager.games.generic_steamid import detect_steamid_in_file
        from er_save_manager.platform.utils import PlatformUtils

        profile = self._selected_profile()

        try:
            steam_users: list[tuple[str, int]] = []

            # --- Source 1: loginusers.vdf ---
            # All logged-in accounts, sorted by most-recently-used.
            # Not filtered by save existence: the patcher target account
            # typically has no save yet for this game.
            loginusers = PlatformUtils.get_loginusers_steam_accounts()
            for sid, persona in loginusers:
                label = f"{persona} ({sid})"
                if sid not in {s for _, s in steam_users}:
                    steam_users.append((label, sid))

            # --- Source 2: folder-name extraction from save paths ---
            if not steam_users:
                save_paths: list[Path] = []
                selected = self.get_save_path()
                if selected and Path(selected).exists():
                    save_paths.append(Path(selected))
                else:
                    save_paths = PlatformUtils.find_all_save_files(profile)

                for save_path in save_paths:
                    steamid = _folder_name_to_steam64(save_path.parent.name, profile)
                    if steamid and steamid not in {s for _, s in steam_users}:
                        label = f"Account {steamid} ({save_path.name})"
                        steam_users.append((label, steamid))

            # --- Source 3: byte-scan fallback ---
            if not steam_users:
                save_paths = PlatformUtils.find_all_save_files(profile)
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
        from er_save_manager.ui import dialog_style as ds

        dialog = ds.create(self.parent, "Select Steam Account")
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        ds.button_row(
            main, [{"text": "Cancel", "command": dialog.destroy, "primary": False}]
        )
        ds.header(main, "Select Steam Account", font=ds.TITLE_LARGE)
        ctk.CTkLabel(
            main, text="Click the account to use.", font=ds.SMALL, text_color=ds.MUTED
        ).pack(anchor="w", pady=(2, 8))

        def make_select(sid, name):
            def select_account(_event=None):
                self.new_steamid_var.set(str(sid))
                dialog.destroy()
                self.show_toast(f"Selected: {name}", duration=2500)

            return select_account

        def build(body):
            for account_name, steamid in accounts:
                row = ctk.CTkFrame(body, fg_color=ds.BOX, corner_radius=6)
                row.pack(fill=tk.X, pady=(0, 4))
                name_label = ctk.CTkLabel(row, text=account_name, font=ds.BOLD)
                name_label.pack(side=tk.LEFT, padx=(12, 16), pady=8)
                id_label = ctk.CTkLabel(
                    row, text=str(steamid), font=ds.FONT, text_color=ds.MUTED
                )
                id_label.pack(side=tk.RIGHT, padx=12, pady=8)
                select = make_select(steamid, account_name)
                for widget in (row, name_label, id_label):
                    widget.bind("<Button-1>", select)
                    widget.bind(
                        "<Enter>",
                        lambda _e, r=row: r.configure(fg_color=palette.PURPLE_TINT),
                    )
                    widget.bind(
                        "<Leave>", lambda _e, r=row: r.configure(fg_color=ds.BOX)
                    )

        ds.content(main, build, max_height=320, width=380)
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        ds.finish(dialog, self.parent, min_width=400)

    def _show_help_dialog(self):
        from er_save_manager.ui import dialog_style as ds

        dialog = ds.create(self.parent, "SteamID Patcher - Help")
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        ds.button_row(main, [{"text": "Close", "command": dialog.destroy}])
        ds.header(
            main,
            "SteamID Patcher",
            icon="ℹ",
            icon_color=palette.PURPLE_TEXT,
            font=ds.TITLE_LARGE,
        )
        ctk.CTkLabel(
            main,
            text="Patch SteamIDs when moving saves between Steam accounts.",
            font=ds.FONT,
            text_color=ds.MUTED,
        ).pack(anchor="w", pady=(2, 4))

        sections = []

        def add_section(title: str, text: str):
            sections.append((title, text.strip()))

        add_section(
            "Supported games",
            "Elden Ring, Elden Ring Nightreign, Dark Souls II SotFS, Armored Core 6, "
            "Dark Souls III, Sekiro: Full SteamID patch supported.\n\n",
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

        def build(body):
            for title, text in sections:
                ctk.CTkLabel(body, text=title, font=ds.BOLD).pack(
                    anchor="w", pady=(10, 0)
                )
                box = ds.box(body, pady=(4, 0))
                ctk.CTkLabel(
                    box, text=text, font=ds.FONT, wraplength=520, justify=ctk.LEFT
                ).pack(anchor="w", padx=12, pady=10)

        ds.content(main, build, max_height=480, width=560)
        ds.finish(dialog, self.parent)
