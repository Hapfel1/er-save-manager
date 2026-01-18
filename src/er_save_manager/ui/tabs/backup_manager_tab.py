"""
Backup Manager Tab
Central hub for managing save file backups
"""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk


class BackupManagerTab:
    """Tab for backup management"""
    
    def __init__(self, parent, get_save_file_callback, get_save_path_callback, reload_callback):
        """
        Initialize backup manager tab
        
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
        
        self.backup_stats_var = None
    
    def setup_ui(self):
        """Setup the backup manager tab UI"""
        title_frame = ttk.Frame(self.parent)
        title_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(
            title_frame,
            text="Backup Manager",
            font=("Segoe UI", 16, "bold"),
        ).pack()
        
        ttk.Label(
            title_frame,
            text="All save modifications automatically create timestamped backups with operation details",
            font=("Segoe UI", 9),
            foreground="gray",
        ).pack()
        
        # Main button
        ttk.Button(
            self.parent,
            text="Open Backup Manager Window",
            command=self.show_backup_manager,
            width=35,
        ).pack(pady=20)
        
        # Quick stats frame
        stats_frame = ttk.LabelFrame(self.parent, text="Quick Stats", padding=15)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.backup_stats_var = tk.StringVar(
            value="Load a save file to view backup statistics"
        )
        stats_label = ttk.Label(
            stats_frame,
            textvariable=self.backup_stats_var,
            font=("Consolas", 10),
            justify=tk.LEFT,
        )
        stats_label.pack(anchor=tk.W)
        
        # Info section
        info_frame = ttk.LabelFrame(
            self.parent, text="Backup Information", padding=15
        )
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        info_text = """Automatic Backups:
• Fix Corruption - Before fixing any character issues
• Teleport - Before moving character location
• Edit Stats - Before changing character attributes
• Import Preset - Before applying appearance changes
• Patch SteamID - Before account transfers
• Recalculate Checksums - Before save validation

Backup Format:
• Timestamp: YYYY-MM-DD_HH-MM-SS
• Location: [save_name].sl2.backups/
• Metadata: Character info, operation type, changes made"""
        
        ttk.Label(
            info_frame,
            text=info_text,
            font=("Segoe UI", 9),
            justify=tk.LEFT,
        ).pack(anchor=tk.W)
    
    def update_backup_stats(self):
        """Update backup statistics display"""
        save_path = self.get_save_path()
        if not save_path:
            self.backup_stats_var.set("Load a save file to view backup statistics")
            return
        
        try:
            from er_save_manager.backup.manager import BackupManager
            
            manager = BackupManager(Path(save_path))
            backups = manager.list_backups()
            
            if not backups:
                self.backup_stats_var.set("No backups found for this save file")
                return
            
            total_size = sum(b.file_size for b in backups)
            stats = []
            stats.append(f"Total Backups: {len(backups)}")
            stats.append(f"Total Size: {total_size / (1024 * 1024):.1f} MB")
            stats.append(f"Latest: {backups[0].timestamp if backups else 'N/A'}")
            
            self.backup_stats_var.set("\n".join(stats))
        
        except Exception as e:
            self.backup_stats_var.set(f"Error loading backup stats: {str(e)}")
    
    def show_backup_manager(self):
        """Show backup manager window"""
        save_file = self.get_save_file()
        save_path = self.get_save_path()
        
        if not save_file or not save_path:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        try:
            from er_save_manager.backup.manager import BackupManager
            
            manager = BackupManager(Path(save_path))
            
            dialog = tk.Toplevel(self.parent)
            dialog.title("Backup Manager")
            dialog.geometry("900x600")
            dialog.grab_set()
            
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"900x600+{x}+{y}")
            
            ttk.Label(
                dialog,
                text="Backup Manager",
                font=("Segoe UI", 14, "bold"),
                padding=10,
            ).pack()
            
            list_frame = ttk.LabelFrame(dialog, text="Backups", padding=10)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            columns = ("timestamp", "operation", "description", "size")
            tree = ttk.Treeview(
                list_frame, columns=columns, show="tree headings", height=15
            )
            
            tree.heading("#0", text="Filename")
            tree.heading("timestamp", text="Timestamp")
            tree.heading("operation", text="Operation")
            tree.heading("description", text="Description")
            tree.heading("size", text="Size")
            
            tree.column("#0", width=200)
            tree.column("timestamp", width=150)
            tree.column("operation", width=150)
            tree.column("description", width=250)
            tree.column("size", width=80)
            
            scrollbar = ttk.Scrollbar(
                list_frame, orient=tk.VERTICAL, command=tree.yview
            )
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            def refresh_list():
                tree.delete(*tree.get_children())
                backups = manager.list_backups()
                for backup in backups:
                    timestamp = (
                        backup.timestamp.split("T")[0]
                        + " "
                        + backup.timestamp.split("T")[1][:8]
                    )
                    size_mb = f"{backup.file_size / (1024 * 1024):.1f} MB"
                    tree.insert(
                        "",
                        tk.END,
                        text=backup.filename,
                        values=(
                            timestamp,
                            backup.operation,
                            backup.description,
                            size_mb,
                        ),
                    )
            
            refresh_list()
            
            button_frame = ttk.Frame(dialog, padding=10)
            button_frame.pack(fill=tk.X)
            
            def create_backup():
                desc = simpledialog.askstring(
                    "Create Backup",
                    "Enter backup description (optional):",
                    parent=dialog,
                )
                if desc is not None:
                    try:
                        manager.create_backup(
                            description=desc or "manual",
                            operation="manual_backup",
                            save=save_file,
                        )
                        refresh_list()
                        self.update_backup_stats()
                        messagebox.showinfo("Success", "Backup created successfully!")
                    except Exception as e:
                        messagebox.showerror(
                            "Error", f"Failed to create backup:\n{str(e)}"
                        )
            
            def restore_backup():
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning(
                        "No Selection", "Please select a backup to restore!"
                    )
                    return
                
                item = tree.item(selection[0])
                backup_name = item["text"]
                
                if not messagebox.askyesno(
                    "Confirm Restore",
                    f"Restore backup '{backup_name}'?\n\nCurrent save will be backed up first.",
                ):
                    return
                
                try:
                    manager.restore_backup(backup_name)
                    if self.reload_save:
                        self.reload_save()
                    refresh_list()
                    self.update_backup_stats()
                    messagebox.showinfo("Success", "Backup restored successfully!")
                except Exception as e:
                    messagebox.showerror(
                        "Error", f"Failed to restore backup:\n{str(e)}"
                    )
            
            def delete_backup():
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning(
                        "No Selection", "Please select a backup to delete!"
                    )
                    return
                
                item = tree.item(selection[0])
                backup_name = item["text"]
                
                if not messagebox.askyesno(
                    "Confirm Delete",
                    f"Delete backup '{backup_name}'?\n\nThis cannot be undone.",
                ):
                    return
                
                try:
                    manager.delete_backup(backup_name)
                    refresh_list()
                    self.update_backup_stats()
                    messagebox.showinfo("Success", "Backup deleted successfully!")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete backup:\n{str(e)}")
            
            def view_details():
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning(
                        "No Selection", "Please select a backup to view!"
                    )
                    return
                
                item = tree.item(selection[0])
                backup_name = item["text"]
                info = manager.get_backup_info(backup_name)
                
                if info:
                    details = []
                    details.append(f"Filename: {info.filename}")
                    details.append(f"Timestamp: {info.timestamp}")
                    details.append(f"Operation: {info.operation}")
                    details.append(f"Description: {info.description}")
                    details.append(f"Size: {info.file_size / (1024 * 1024):.2f} MB")
                    
                    if info.character_summary:
                        details.append("\nCharacters:")
                        for char in info.character_summary:
                            details.append(
                                f"  Slot {char['slot']}: {char['name']} (Lv.{char['level']})"
                            )
                    
                    messagebox.showinfo("Backup Details", "\n".join(details))
            
            ttk.Button(
                button_frame,
                text="Create Backup",
                command=create_backup,
                width=15,
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                button_frame,
                text="Restore",
                command=restore_backup,
                width=15,
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                button_frame,
                text="View Details",
                command=view_details,
                width=15,
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                button_frame,
                text="Delete",
                command=delete_backup,
                width=15,
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                button_frame,
                text="Refresh",
                command=refresh_list,
                width=15,
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                button_frame,
                text="Close",
                command=dialog.destroy,
                width=15,
            ).pack(side=tk.RIGHT, padx=5)
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open backup manager:\n{str(e)}")
            import traceback
            traceback.print_exc()
