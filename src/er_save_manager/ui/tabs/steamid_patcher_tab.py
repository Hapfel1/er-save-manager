"""
SteamID Patcher Tab
Patches SteamID in save files for account transfers
"""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


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
        ttk.Label(
            self.parent,
            text="SteamID Patcher",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=10)

        info_text = ttk.Label(
            self.parent,
            text="Transfer save files between Steam accounts by patching SteamID",
            font=("Segoe UI", 10),
            foreground="gray",
        )
        info_text.pack(pady=5)

        # Current SteamID display
        current_frame = ttk.LabelFrame(
            self.parent, text="Current Save File", padding=15
        )
        current_frame.pack(fill=tk.X, padx=20, pady=10)

        self.current_steamid_var = tk.StringVar(value="No save file loaded")
        ttk.Label(
            current_frame,
            textvariable=self.current_steamid_var,
            font=("Consolas", 10),
        ).pack(anchor=tk.W)

        # Patch section
        patch_frame = ttk.LabelFrame(self.parent, text="Patch SteamID", padding=15)
        patch_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(
            patch_frame,
            text="Enter new SteamID (17-digit number):",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=5)

        steamid_entry_frame = ttk.Frame(patch_frame)
        steamid_entry_frame.pack(fill=tk.X, pady=5)

        self.new_steamid_var = tk.StringVar()
        steamid_entry = ttk.Entry(
            steamid_entry_frame,
            textvariable=self.new_steamid_var,
            font=("Consolas", 11),
            width=20,
        )
        steamid_entry.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            steamid_entry_frame,
            text="Patch SteamID",
            command=self.patch_steamid,
            width=15,
        ).pack(side=tk.LEFT)

        ttk.Button(
            steamid_entry_frame,
            text="Auto-Detect from System",
            command=self.auto_detect_steamid,
            width=20,
        ).pack(side=tk.LEFT, padx=5)

        # Steam Profile URL section
        ttk.Label(
            patch_frame,
            text="Or paste Steam profile URL:",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=(15, 5))

        url_entry_frame = ttk.Frame(patch_frame)
        url_entry_frame.pack(fill=tk.X, pady=5)

        self.steam_url_var = tk.StringVar()
        url_entry = ttk.Entry(
            url_entry_frame,
            textvariable=self.steam_url_var,
            font=("Consolas", 10),
            width=50,
        )
        url_entry.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            url_entry_frame,
            text="Parse URL",
            command=self.parse_steam_url,
            width=12,
        ).pack(side=tk.LEFT)

        # Help button instead of large info section
        help_button_frame = ttk.Frame(patch_frame)
        help_button_frame.pack(fill=tk.X, pady=(15, 0))

        ttk.Button(
            help_button_frame,
            text="❓ How to Use / Help",
            command=self._show_help_dialog,
            width=20,
        ).pack(anchor=tk.W)

    def _show_help_dialog(self):
        """Show comprehensive help dialog"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("SteamID Patcher - Help")
        dialog.geometry("600x500")
        dialog.transient(self.parent)

        # Title
        ttk.Label(
            dialog,
            text="SteamID Patcher - Complete Guide",
            font=("Segoe UI", 14, "bold"),
            padding=10,
        ).pack()

        # Scrollable text
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            font=("Segoe UI", 10),
            padx=10,
            pady=10,
        )
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text.yview)

        help_text = """WHAT IS STEAMID PATCHING?

When you transfer a save file to another computer or Steam account, the SteamID mismatch can cause loading issues or prevent the save from being recognized. This tool updates the SteamID in:
• All 10 character slots
• USER_DATA_10 common section
• Profile summary

HOW TO USE:

Step 1: Load the save file you want to transfer

Step 2: Get the target SteamID using one of three methods:

Method 1 - Auto-Detect (Windows only):
• Click "Auto-Detect from System"
• If multiple accounts detected, select from list
• SteamID will be auto-filled

Method 2 - Parse Steam Profile URL:
• Copy Steam profile URL: steamcommunity.com/profiles/76561198012345678
• Paste into "Steam profile URL" field
• Click "Parse URL"
• Works with both /profiles/ and /id/ URLs

Method 3 - Manual Entry:
• Enter the 17-digit SteamID directly
• Format: 76561198012345678

Step 3: Click "Patch SteamID" to update the save file

Step 4: A backup is automatically created before patching


HOW TO FIND SOMEONE'S STEAMID:

1. Go to their Steam Community profile
2. Copy the URL from the address bar
3. If URL contains /profiles/NUMBER - use it directly
4. If URL contains /id/username - tool will attempt to resolve it
5. Paste into "Steam profile URL" field
6. Click "Parse URL"


SUPPORTED URL FORMATS:

✓ https://steamcommunity.com/profiles/76561198012345678
✓ https://steamcommunity.com/id/username (auto-resolves)
✓ 76561198012345678 (direct number)


WHAT GETS UPDATED:

✓ All 10 character slots
✓ USER_DATA_10 (common section)
✓ Profile summary for each character
✓ Checksums are recalculated


SAFETY FEATURES:

✓ Automatic backup before patching
✓ Validation of SteamID format
✓ Confirmation dialog
✓ Shows old and new SteamID in success message


WARNINGS:

⚠ Make sure you have the CORRECT SteamID
⚠ Patching to wrong SteamID may corrupt save
⚠ Test the patched save before deleting original
⚠ Keep backups of important saves


TROUBLESHOOTING:

Q: Auto-detect doesn't work?
A: Auto-detect only works on Windows and requires Steam to be installed

Q: Custom URL resolution fails?
A: Get the /profiles/ URL instead by clicking on the user's name

Q: Patch fails?
A: Make sure save file is loaded and not corrupted
"""

        text.insert("1.0", help_text)
        text.config(state="disabled")

        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy, width=15).pack(pady=10)

    def update_steamid_display(self):
        """Update current SteamID display"""
        save_file = self.get_save_file()
        if not save_file:
            self.current_steamid_var.set("No save file loaded")
            return

        try:
            # Check if USER_DATA_10 was parsed
            if not save_file.user_data_10_parsed:
                self.current_steamid_var.set("SteamID: Unable to parse save file")
                return

            # Check if steam_id attribute exists
            if not hasattr(save_file.user_data_10_parsed, "steam_id"):
                self.current_steamid_var.set("SteamID: Attribute not found")
                return

            # Get the SteamID
            steamid = save_file.user_data_10_parsed.steam_id

            # Validate it's a reasonable SteamID
            if steamid == 0:
                self.current_steamid_var.set(
                    "SteamID: 0 (Invalid - save may be corrupted)"
                )
            elif steamid < 76561197960265728:  # Minimum valid SteamID64
                self.current_steamid_var.set(f"SteamID: {steamid} (Invalid format)")
            else:
                self.current_steamid_var.set(f"Current SteamID: {steamid}")

        except Exception as e:
            self.current_steamid_var.set(f"SteamID: Error - {str(e)}")
            import traceback

            traceback.print_exc()

    def patch_steamid(self):
        """Patch SteamID in save file"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        new_steamid = self.new_steamid_var.get().strip()

        if not new_steamid.isdigit() or len(new_steamid) != 17:
            messagebox.showerror("Invalid SteamID", "SteamID must be exactly 17 digits")
            return

        if not messagebox.askyesno(
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

            # Store old SteamID for message
            old_steamid = 0
            if save_file.user_data_10_parsed:
                old_steamid = save_file.user_data_10_parsed.steam_id

            # STEP 1: Update USER_DATA_10 (common section) FIRST
            if save_file.user_data_10_parsed:
                save_file.user_data_10_parsed.steam_id = int(new_steamid)

                # Write to raw data at correct offset
                # USER_DATA_10 structure: [checksum 16] + [version 4] + [steamid 8]
                steamid_offset = (
                    save_file._user_data_10_offset + (0 if save_file.is_ps else 16) + 4
                )
                import struct

                steamid_bytes = struct.pack("<Q", int(new_steamid))
                save_file._raw_data[steamid_offset : steamid_offset + 8] = steamid_bytes

                # Also update in profile summary if exists
                if (
                    hasattr(save_file.user_data_10_parsed, "profile_summary")
                    and save_file.user_data_10_parsed.profile_summary
                ):
                    for (
                        profile
                    ) in save_file.user_data_10_parsed.profile_summary.profiles:
                        if hasattr(profile, "steam_id"):
                            profile.steam_id = int(new_steamid)

            # STEP 2: Now sync all character slots to the NEW save SteamID
            # SteamIdFix reads from USER_DATA_10 and syncs slots to it
            patched_count = 0
            fix = SteamIdFix()  # No arguments - it reads from save
            for slot_idx in range(10):
                result = fix.apply(save_file, slot_idx)
                if result.applied:
                    patched_count += 1

            # STEP 3: Recalculate checksums and save
            save_file.recalculate_checksums()
            if save_path:
                save_file.to_file(Path(save_path))

            if self.reload_save:
                self.reload_save()

            messagebox.showinfo(
                "Success",
                f"✓ Updated USER_DATA_10 SteamID\n"
                f"✓ Updated profile summary\n"
                f"✓ Synced {patched_count} character slot(s)\n\n"
                f"Old SteamID: {old_steamid}\n"
                f"New SteamID: {new_steamid}\n\n"
                f"Backup saved to backup manager.",
            )

        except Exception as e:
            messagebox.showerror("Error", f"SteamID patch failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def parse_steam_url(self):
        """Parse Steam profile URL to extract SteamID"""
        url = self.steam_url_var.get().strip()

        if not url:
            messagebox.showwarning("Empty URL", "Please enter a Steam profile URL")
            return

        try:
            import re

            # Direct SteamID64 input (just numbers)
            if url.isdigit() and len(url) == 17:
                self.new_steamid_var.set(url)
                self.steam_url_var.set("")  # Clear URL field
                messagebox.showinfo("Success", f"SteamID: {url}")
                return

            # Parse Steam profile URL formats:
            # https://steamcommunity.com/profiles/76561198012345678
            # steamcommunity.com/profiles/76561198012345678
            # /profiles/76561198012345678

            match = re.search(r"/profiles/(\d{17})", url)
            if match:
                steamid = match.group(1)
                self.new_steamid_var.set(steamid)
                self.steam_url_var.set("")  # Clear URL field
                messagebox.showinfo("Success", f"Extracted SteamID: {steamid}")
                return

            # Custom URL format - try to resolve via SteamDB API
            custom_match = re.search(r"/id/([^/\s]+)", url)
            if custom_match:
                custom_name = custom_match.group(1)
                self._resolve_custom_url(custom_name)
                return

            # No valid pattern found
            messagebox.showerror(
                "Invalid Format",
                "Could not find SteamID in the URL.\n\n"
                "Supported formats:\n"
                "• https://steamcommunity.com/profiles/76561198012345678\n"
                "• https://steamcommunity.com/id/username (will attempt to resolve)\n"
                "• Just the 17-digit SteamID number",
            )

        except Exception as e:
            messagebox.showerror("Parse Error", f"Failed to parse URL:\n{str(e)}")

    def _resolve_custom_url(self, custom_name):
        """Resolve custom Steam URL using steamid.io"""
        try:
            import re
            import urllib.parse
            import urllib.request

            # Clean up the custom name
            custom_name = custom_name.strip().strip("/")

            # Use steamid.io lookup
            lookup_url = f"https://steamid.io/lookup/{urllib.parse.quote(custom_name)}"

            req = urllib.request.Request(
                lookup_url, headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode()

                # Parse HTML to find SteamID
                # Look for patterns like: data-steamid64="76561198..."
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
                        self.steam_url_var.set("")  # Clear URL field
                        messagebox.showinfo(
                            "Success",
                            f"Resolved via steamid.io!\n\n"
                            f"Username: {custom_name}\n"
                            f"SteamID: {steamid}",
                        )
                        return

                # No pattern matched
                messagebox.showerror(
                    "Not Found",
                    f"Could not find SteamID for: {custom_name}\n\n"
                    "Please check the username and try again.",
                )

        except Exception as e:
            messagebox.showerror(
                "Resolution Failed",
                f"Failed to resolve custom URL: {custom_name}\n\n"
                f"Error: {str(e)}\n\n"
                "Please use a /profiles/ URL or enter the SteamID directly.",
            )

    def auto_detect_steamid(self):
        """Auto-detect SteamID from system with multi-account support"""
        try:
            import winreg

            # Get all Steam users from registry
            steam_users = []

            try:
                # Try to get active user first
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

            # Get all users from Steam installation
            try:
                steam_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"
                )
                steam_path, _ = winreg.QueryValueEx(steam_key, "SteamPath")
                winreg.CloseKey(steam_key)

                # Read loginusers.vdf to get all accounts
                import os

                loginusers_path = os.path.join(steam_path, "config", "loginusers.vdf")
                if os.path.exists(loginusers_path):
                    with open(loginusers_path, encoding="utf-8") as f:
                        content = f.read()
                        # Parse SteamIDs from VDF (simple regex)
                        import re

                        # Match "765611..." followed by account name
                        pattern = r'"(765611\d{10})"\s*\{[^}]*"AccountName"\s*"([^"]+)"'
                        matches = re.findall(pattern, content)
                        for steamid, account_name in matches:
                            if steamid not in [str(s[1]) for s in steam_users]:
                                steam_users.append((account_name, int(steamid)))
            except Exception:
                pass

            if not steam_users:
                messagebox.showwarning(
                    "Not Found",
                    "Could not detect any Steam accounts.\n\nPlease enter SteamID manually.",
                )
                return

            # If only one account, use it directly
            if len(steam_users) == 1:
                steamid = steam_users[0][1]
                self.new_steamid_var.set(str(steamid))
                messagebox.showinfo(
                    "Detected",
                    f"SteamID detected: {steamid}\n\nAccount: {steam_users[0][0]}",
                )
                return

            # Multiple accounts - show selection dialog
            self._show_account_selection_dialog(steam_users)

        except Exception as e:
            messagebox.showwarning(
                "Detection Failed",
                f"Could not auto-detect SteamID:\n{str(e)}\n\nNote: Auto-detection only works on Windows.",
            )

    def _show_account_selection_dialog(self, accounts):
        """Show dialog to select from multiple Steam accounts"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Select Steam Account")
        dialog.geometry("400x300")
        dialog.transient(self.parent)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text="Multiple Steam accounts detected.\nSelect the account to use:",
            font=("Segoe UI", 10),
            padding=10,
        ).pack()

        # Listbox with accounts
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(
            list_frame, yscrollcommand=scrollbar.set, font=("Consolas", 10), height=10
        )
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        # Populate listbox
        for account_name, steamid in accounts:
            listbox.insert(tk.END, f"{account_name}: {steamid}")

        listbox.selection_set(0)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        def on_select():
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                steamid = accounts[idx][1]
                self.new_steamid_var.set(str(steamid))
                dialog.destroy()
                messagebox.showinfo(
                    "Selected", f"SteamID: {steamid}\n\nAccount: {accounts[idx][0]}"
                )

        def on_cancel():
            dialog.destroy()

        ttk.Button(button_frame, text="Select", command=on_select, width=12).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Cancel", command=on_cancel, width=12).pack(
            side=tk.LEFT, padx=5
        )

        # Bind double-click
        listbox.bind("<Double-Button-1>", lambda e: on_select())
