"""
SteamID Patcher Tab
Patches SteamID in save files for account transfers
"""

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


class SteamIDPatcherTab:
    """Tab for SteamID patching operations"""

    def __init__(
        self, parent, get_save_file_callback, get_save_path_callback, reload_callback
    ):
        """
        Initialize SteamID patcher tab

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_save_path_callback: Function that returns save file path
            reload_callback: Function to reload save file
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback

        self.current_steamid_var = None
        self.new_steamid_var = None
        self.steam_url_var = None

    def setup_ui(self):
        """Setup the SteamID patcher tab UI"""
        # Main scrollable container
        main_frame = ctk.CTkScrollableFrame(self.parent, corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(main_frame)

        # Header
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
        ).pack(pady=(0, 15), padx=15, anchor="w")

        # Current SteamID display
        current_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        current_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

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

        # Patch section
        patch_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        patch_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        ctk.CTkLabel(
            patch_frame,
            text="Patch SteamID",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(12, 8), padx=12, anchor="w")

        # Manual Entry Section
        ctk.CTkLabel(
            patch_frame,
            text="Enter new SteamID (17-digit number):",
            font=("Segoe UI", 12),
            text_color=("gray40", "gray70"),
        ).pack(pady=(0, 6), padx=12, anchor="w")

        steamid_entry_frame = ctk.CTkFrame(patch_frame, fg_color="transparent")
        steamid_entry_frame.pack(fill=tk.X, pady=(0, 10), padx=12)

        self.new_steamid_var = tk.StringVar(value="")
        steamid_entry = ctk.CTkEntry(
            steamid_entry_frame,
            textvariable=self.new_steamid_var,
            font=("Consolas", 11),
            width=180,
            placeholder_text="76561198012345678",
        )
        steamid_entry.pack(side=tk.LEFT, padx=(0, 8))

        ctk.CTkButton(
            steamid_entry_frame,
            text="Patch SteamID",
            command=self.patch_steamid,
            width=120,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            steamid_entry_frame,
            text="Auto-Detect",
            command=self.auto_detect_steamid,
            width=110,
        ).pack(side=tk.LEFT)

        # Steam Profile URL section
        ctk.CTkLabel(
            patch_frame,
            text="Or paste Steam profile URL:",
            font=("Segoe UI", 12),
            text_color=("gray40", "gray70"),
        ).pack(pady=(12, 6), padx=12, anchor="w")

        url_entry_frame = ctk.CTkFrame(patch_frame, fg_color="transparent")
        url_entry_frame.pack(fill=tk.X, pady=(0, 12), padx=12)

        self.steam_url_var = tk.StringVar(value="")
        url_entry = ctk.CTkEntry(
            url_entry_frame,
            textvariable=self.steam_url_var,
            font=("Consolas", 10),
            placeholder_text="https://steamcommunity.com/profiles/...",
        )
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        ctk.CTkButton(
            url_entry_frame,
            text="Parse URL",
            command=self.parse_steam_url,
            width=100,
        ).pack(side=tk.LEFT)

        # Help button
        ctk.CTkButton(
            patch_frame,
            text="❓ How to Use / Help",
            command=self._show_help_dialog,
            text_color=("#2a5f3f", "#a8d5ba"),
            fg_color=("#d0f0e5", "#1a3a2a"),
            width=140,
        ).pack(pady=(0, 12), padx=12, anchor="w")

    def _show_help_dialog(self):
        """Show comprehensive help dialog"""
        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("SteamID Patcher - Help")
        width, height = 720, 680
        dialog.resizable(True, True)
        dialog.update_idletasks()
        # Center over parent window
        self.parent.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        # Force rendering on Linux before grab_set
        force_render_dialog(dialog)
        dialog.grab_set()

        header = ctk.CTkFrame(dialog, corner_radius=10)
        header.pack(fill=tk.X, padx=14, pady=(14, 8))
        ctk.CTkLabel(
            header,
            text="SteamID Patcher - Complete Guide",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(8, 2), padx=10)
        ctk.CTkLabel(
            header,
            text="Patch SteamIDs safely when moving saves between Steam accounts.",
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
            "What is SteamID patching?",
            "When you move a save to another Steam account, the SteamID no longer matches and the game will refuse to load it. This tool rewrites the SteamID in all 10 character slots, the common USER_DATA_10 section, and the profile summary so the save loads on the target account.",
        )

        add_section(
            "Quick steps",
            "1) Load the save you want to transfer.\n"
            "2) Get the target SteamID using one of the methods below.\n"
            "3) Click Patch SteamID. A backup is created automatically.\n"
            "4) Load the patched save on the new account.",
        )

        add_section(
            "Method 1 — Auto-Detect",
            "• Click Auto-Detect.\n"
            "• If multiple accounts are found, pick from the list.\n"
            "• The SteamID field is filled automatically.",
        )

        add_section(
            "Method 2 — Paste profile URL",
            "• Copy the profile URL, e.g. steamcommunity.com/profiles/76561198012345678.\n"
            "• Paste into Steam profile URL.\n"
            "• Click Parse URL. Works for both /profiles/ and /id/ URLs.",
        )

        add_section(
            "Method 3 — Manual entry",
            "• Enter the 17-digit SteamID directly (e.g. 76561198012345678).\n"
            "• Use Patch SteamID to write it everywhere.",
        )

        add_section(
            "Supported formats",
            "✓ https://steamcommunity.com/profiles/76561198012345678\n"
            "✓ https://steamcommunity.com/id/username (auto-resolves)\n"
            "✓ 76561198012345678 (just the number)",
        )

        add_section(
            "Safety features",
            "✓ Automatic backup before patching\n"
            "✓ SteamID format validation\n"
            "✓ Confirmation dialog\n"
            "✓ Shows old vs new SteamID after success",
        )

        ctk.CTkButton(dialog, text="Close", command=dialog.destroy, width=110).pack(
            pady=(0, 14)
        )

    def update_steamid_display(self):
        """Update current SteamID display"""
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
            self.current_steamid_var.set(f"SteamID: Error - {str(e)}")

    def patch_steamid(self):
        """Patch SteamID in save file"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        new_steamid = self.new_steamid_var.get().strip()

        if not new_steamid.isdigit() or len(new_steamid) != 17:
            CTkMessageBox.showerror(
                "Invalid SteamID", "SteamID must be exactly 17 digits"
            )
            return

        if not CTkMessageBox.askyesno(
            "Confirm Patch",
            f"Patch all character slots to SteamID: {new_steamid}?\n\nA backup will be created.",
        ):
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.fixes.steamid import SteamIdFix

            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_steamid_patch_{new_steamid[:8]}",
                    operation="patch_steamid",
                    save=save_file,
                )

            old_steamid = 0
            if save_file.user_data_10_parsed:
                old_steamid = save_file.user_data_10_parsed.steam_id

            # Update USER_DATA_10
            if save_file.user_data_10_parsed:
                save_file.user_data_10_parsed.steam_id = int(new_steamid)

                steamid_offset = (
                    save_file._user_data_10_offset + (0 if save_file.is_ps else 16) + 4
                )
                import struct

                steamid_bytes = struct.pack("<Q", int(new_steamid))
                save_file._raw_data[steamid_offset : steamid_offset + 8] = steamid_bytes

                if (
                    hasattr(save_file.user_data_10_parsed, "profile_summary")
                    and save_file.user_data_10_parsed.profile_summary
                ):
                    for (
                        profile
                    ) in save_file.user_data_10_parsed.profile_summary.profiles:
                        if hasattr(profile, "steam_id"):
                            profile.steam_id = int(new_steamid)

            # Sync all character slots
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

            CTkMessageBox.showinfo(
                "Success",
                f"✓ Updated USER_DATA_10 SteamID\n"
                f"✓ Updated profile summary\n"
                f"✓ Synced {patched_count} character slot(s)\n\n"
                f"Old SteamID: {old_steamid}\n"
                f"New SteamID: {new_steamid}\n\n"
                f"Backup saved to backup manager.",
            )

        except Exception as e:
            CTkMessageBox.showerror("Error", f"SteamID patch failed:\n{str(e)}")

    def parse_steam_url(self):
        """Parse Steam profile URL to extract SteamID"""
        url = self.steam_url_var.get().strip()

        if not url:
            CTkMessageBox.showwarning("Empty URL", "Please enter a Steam profile URL")
            return

        try:
            import re

            if url.isdigit() and len(url) == 17:
                self.new_steamid_var.set(url)
                self.steam_url_var.set("")
                CTkMessageBox.showinfo("Success", f"SteamID: {url}")
                return

            match = re.search(r"/profiles/(\d{17})", url)
            if match:
                steamid = match.group(1)
                self.new_steamid_var.set(steamid)
                self.steam_url_var.set("")
                CTkMessageBox.showinfo("Success", f"Extracted SteamID: {steamid}")
                return

            custom_match = re.search(r"/id/([^/\s]+)", url)
            if custom_match:
                custom_name = custom_match.group(1)
                self._resolve_custom_url(custom_name)
                return  # Exit after resolving custom URL

            CTkMessageBox.showerror(
                "Invalid Format",
                "Could not find SteamID in the URL.\n\n"
                "Supported formats:\n"
                "• https://steamcommunity.com/profiles/76561198012345678\n"
                "• https://steamcommunity.com/id/username (will attempt to resolve)\n"
                "• Just the 17-digit SteamID number",
            )

        except Exception as e:
            CTkMessageBox.showerror("Parse Error", f"Failed to parse URL:\n{str(e)}")

    def _resolve_custom_url(self, custom_name):
        """Resolve custom Steam URL using steamid.io"""
        try:
            import re
            import urllib.parse
            import urllib.request

            custom_name = custom_name.strip().strip("/")
            lookup_url = f"https://steamid.io/lookup/{urllib.parse.quote(custom_name)}"

            req = urllib.request.Request(
                lookup_url, headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode()

                patterns = [
                    r'data-steamid64="(\d{17})"',
                    r'"steamid64":"(\d{17})"',
                    r"steamID64:\s*(\d{17})",
                    r">(\d{17})<",
                ]

                for pattern in patterns:
                    match = re.search(pattern, html)
                    if match:
                        steamid = match.group(1)
                        self.new_steamid_var.set(steamid)
                        self.steam_url_var.set("")
                        CTkMessageBox.showinfo(
                            "Success",
                            f"Resolved via steamid.io!\n\n"
                            f"Username: {custom_name}\n"
                            f"SteamID: {steamid}",
                        )
                        return

                CTkMessageBox.showerror(
                    "Not Found",
                    f"Could not find SteamID for: {custom_name}\n\n"
                    "Please check the username and try again.",
                )
                return  # Exit after showing not found error

        except Exception as e:
            CTkMessageBox.showerror(
                "Resolution Failed",
                f"Failed to resolve custom URL: {custom_name}\n\n"
                f"Error: {str(e)}\n\n"
                "Please use a /profiles/ URL or enter the SteamID directly.",
            )

    def auto_detect_steamid(self):
        """Auto-detect SteamID from system with multi-account support"""
        from er_save_manager.platform.utils import PlatformUtils

        try:
            steam_users = []

            if PlatformUtils.is_windows():
                # Windows: Use registry
                import winreg

                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam\ActiveProcess"
                    )
                    active_user_id, _ = winreg.QueryValueEx(key, "ActiveUser")
                    winreg.CloseKey(key)

                    if active_user_id and active_user_id != 0:
                        active_steamid64 = 76561197960265728 + active_user_id
                        steam_users.append(("Active Account", active_steamid64))
                except Exception:
                    pass

                try:
                    steam_key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"
                    )
                    steam_path, _ = winreg.QueryValueEx(steam_key, "SteamPath")
                    winreg.CloseKey(steam_key)

                    import os

                    loginusers_path = os.path.join(
                        steam_path, "config", "loginusers.vdf"
                    )
                    if os.path.exists(loginusers_path):
                        with open(loginusers_path, encoding="utf-8") as f:
                            content = f.read()
                            import re

                            pattern = (
                                r'"(765611\d{10})"\s*\{[^}]*"AccountName"\s*"([^"]+)"'
                            )
                            matches = re.findall(pattern, content)
                            for steamid, account_name in matches:
                                if steamid not in [str(s[1]) for s in steam_users]:
                                    steam_users.append((account_name, int(steamid)))
                except Exception:
                    pass

            elif PlatformUtils.is_linux():
                # Linux: Parse loginusers.vdf from Steam config
                import re

                # Check common Steam locations, including custom via symlink
                steam_base_paths = []

                # Check ~/.steam/steam symlink (follows custom installations)
                steam_symlink = Path.home() / ".steam" / "steam"
                if steam_symlink.exists() and steam_symlink.is_symlink():
                    steam_base_paths.append(steam_symlink.resolve())

                # Standard locations
                steam_base_paths.extend(
                    [
                        Path.home() / ".local" / "share" / "Steam",
                        Path.home()
                        / ".var"
                        / "app"
                        / "com.valvesoftware.Steam"
                        / ".local"
                        / "share"
                        / "Steam",
                    ]
                )

                for steam_base in steam_base_paths:
                    loginusers_path = steam_base / "config" / "loginusers.vdf"
                    if loginusers_path.exists():
                        try:
                            with open(loginusers_path, encoding="utf-8") as f:
                                content = f.read()
                                pattern = r'"(765611\d{10})"\s*\{[^}]*"AccountName"\s*"([^"]+)"'
                                matches = re.findall(pattern, content)
                                for steamid, account_name in matches:
                                    if steamid not in [str(s[1]) for s in steam_users]:
                                        steam_users.append((account_name, int(steamid)))
                        except Exception:
                            continue
                        break

            if not steam_users:
                CTkMessageBox.showwarning(
                    "Not Found",
                    "Could not detect any Steam accounts.\n\nPlease enter SteamID manually.",
                )
                return

            if len(steam_users) == 1:
                steamid = steam_users[0][1]
                self.new_steamid_var.set(str(steamid))
                CTkMessageBox.showinfo(
                    "Detected",
                    f"SteamID detected: {steamid}\n\nAccount: {steam_users[0][0]}",
                )
                return

            self._show_account_selection_dialog(steam_users)

        except Exception as e:
            CTkMessageBox.showwarning(
                "Detection Failed",
                f"Could not auto-detect SteamID:\n{str(e)}",
            )

    def _show_account_selection_dialog(self, accounts):
        """Show dialog to select from multiple Steam accounts"""
        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Select Steam Account")
        dialog.geometry("450x350")
        dialog.resizable(False, False)

        # Force rendering on Linux
        force_render_dialog(dialog)

        ctk.CTkLabel(
            dialog,
            text="Multiple Steam accounts detected.\nSelect the account to use:",
            font=("Segoe UI", 11),
        ).pack(pady=(15, 12), padx=15)

        # List frame with scrollable list
        list_frame = ctk.CTkScrollableFrame(dialog, corner_radius=8)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        bind_mousewheel(list_frame)

        selected_steamid = tk.StringVar(value="")

        for _idx, (account_name, steamid) in enumerate(accounts):
            btn_frame = ctk.CTkFrame(
                list_frame, corner_radius=8, fg_color=("#f0f0f0", "#2a2a3e")
            )
            btn_frame.pack(fill=tk.X, pady=4)

            def make_select(sid):
                def select_account():
                    selected_steamid.set(str(sid))
                    dialog.destroy()
                    CTkMessageBox.showinfo(
                        "Selected",
                        f"SteamID: {sid}\n\nAccount: {accounts[[a[1] for a in accounts].index(sid)][0]}",
                    )

                return select_account

            ctk.CTkButton(
                btn_frame,
                text=f"{account_name}: {steamid}",
                font=("Consolas", 10),
                command=make_select(steamid),
                fg_color="transparent",
                text_color=("#2a2a2a", "#e5e5f5"),
                hover_color=("#c9a0dc", "#3b2f5c"),
            ).pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Buttons
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=(0, 15), padx=15, fill=tk.X)

        ctk.CTkButton(
            button_frame, text="Cancel", command=dialog.destroy, width=100
        ).pack(side=tk.RIGHT)
