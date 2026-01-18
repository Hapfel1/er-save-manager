"""
SteamID Patcher Tab
Patches SteamID in save files for account transfers
"""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


class SteamIDPatcherTab:
    """Tab for SteamID patching operations"""
    
    def __init__(self, parent, get_save_file_callback, get_save_path_callback, reload_callback):
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
        
        # Info
        info_frame = ttk.LabelFrame(self.parent, text="Information", padding=15)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        info = """What is SteamID Patching?
When you transfer a save file to another computer or Steam account, the SteamID
mismatch can cause issues. This tool updates the SteamID in all character slots.

How to use:
1. Load the save file you want to transfer
2. Enter the target Steam account's SteamID (17 digits)
3. Click "Patch SteamID" to update the save file
4. A backup is automatically created before patching

Warning:
• Make sure you have the correct SteamID
• Patching to the wrong SteamID may cause save corruption
• Always test the patched save file before deleting the original"""
        
        ttk.Label(
            info_frame,
            text=info,
            font=("Segoe UI", 9),
            justify=tk.LEFT,
        ).pack(anchor=tk.W)
    
    def update_steamid_display(self):
        """Update current SteamID display"""
        save_file = self.get_save_file()
        if not save_file:
            self.current_steamid_var.set("No save file loaded")
            return
        
        try:
            if save_file.user_data_10_parsed:
                steamid = save_file.user_data_10_parsed.steam_id
                self.current_steamid_var.set(f"Current SteamID: {steamid}")
            else:
                self.current_steamid_var.set("SteamID: Unknown")
        except Exception:
            self.current_steamid_var.set("SteamID: Error reading")
    
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
            from er_save_manager.fixes.steamid import SteamIDFix
            
            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_steamid_patch_{new_steamid[:8]}",
                    operation="patch_steamid",
                    save=save_file,
                )
            
            # Apply SteamID fix to all slots
            patched_count = 0
            for slot_idx in range(10):
                fix = SteamIDFix(int(new_steamid))
                result = fix.apply(save_file, slot_idx)
                if result.applied:
                    patched_count += 1
            
            if patched_count > 0:
                save_file.recalculate_checksums()
                if save_path:
                    save_file.to_file(Path(save_path))
                
                if self.reload_save:
                    self.reload_save()
                
                messagebox.showinfo(
                    "Success",
                    f"Patched {patched_count} character slot(s)!\n\nBackup saved to backup manager.",
                )
            else:
                messagebox.showinfo("No Changes", "No character slots needed patching")
        
        except Exception as e:
            messagebox.showerror("Error", f"SteamID patch failed:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def auto_detect_steamid(self):
        """Auto-detect SteamID from system"""
        try:
            import winreg
            
            # Try to get Steam user ID from registry
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam\ActiveProcess"
            )
            user_id, _ = winreg.QueryValueEx(key, "ActiveUser")
            winreg.CloseKey(key)
            
            if user_id and user_id != 0:
                # Convert to SteamID64 format
                steamid64 = 76561197960265728 + user_id
                self.new_steamid_var.set(str(steamid64))
                messagebox.showinfo("Detected", f"SteamID detected: {steamid64}")
            else:
                messagebox.showwarning(
                    "Not Found", "Could not detect SteamID. Please enter manually."
                )
        
        except Exception as e:
            messagebox.showwarning(
                "Detection Failed", 
                f"Could not auto-detect SteamID:\n{str(e)}\n\nNote: Auto-detection only works on Windows."
            )
