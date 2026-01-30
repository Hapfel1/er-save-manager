"""
Backup Manager Tab (customtkinter version)
Central hub for managing save file backups
"""

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


class BackupManagerTab:
    """Tab for backup management"""

    def __init__(
        self, parent, get_save_file_callback, get_save_path_callback, reload_callback
    ):
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
        title_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        title_frame.pack(fill=tk.X, pady=10)

        ctk.CTkLabel(
            title_frame,
            text="Backup Manager",
            font=("Segoe UI", 16, "bold"),
        ).pack()

        ctk.CTkLabel(
            title_frame,
            text="All save modifications automatically create timestamped backups with operation details",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack()

        # Main button
        ctk.CTkButton(
            self.parent,
            text="Open Backup Manager Window",
            command=self.show_backup_manager,
        ).pack(pady=20)

        # Quick stats frame
        stats_frame = ctk.CTkFrame(self.parent)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        stats_label_title = ctk.CTkLabel(
            stats_frame,
            text="Quick Stats",
            font=("Segoe UI", 12, "bold"),
            text_color=("gray70", "gray50"),
        )
        stats_label_title.pack(anchor=tk.W, padx=15, pady=(10, 5))

        self.backup_stats_var = tk.StringVar(
            value="Load a save file to view backup statistics"
        )
        stats_label = ctk.CTkLabel(
            stats_frame,
            textvariable=self.backup_stats_var,
            font=("Consolas", 10),
            justify=tk.LEFT,
        )
        stats_label.pack(anchor=tk.W, padx=15, pady=10)

        # Info section
        info_frame = ctk.CTkFrame(self.parent)
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        info_label_title = ctk.CTkLabel(
            info_frame,
            text="Backup Information",
            font=("Segoe UI", 12, "bold"),
            text_color=("gray70", "gray50"),
        )
        info_label_title.pack(anchor=tk.W, padx=15, pady=(10, 5))

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

        ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=("Segoe UI", 11),
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=15, pady=10)

    def update_backup_stats(self):
        """Update backup statistics display"""
        # Guard against backup_stats_var not being initialized
        if not self.backup_stats_var:
            return

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
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        try:
            from er_save_manager.backup.manager import BackupManager
            from er_save_manager.ui.utils import force_render_dialog

            manager = BackupManager(Path(save_path))

            dialog = ctk.CTkToplevel(self.parent)
            dialog.title("Backup Manager")
            width, height = 900, 600
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

            ctk.CTkLabel(
                dialog,
                text="Backup Manager",
                font=("Segoe UI", 14, "bold"),
            ).pack(pady=10)

            list_frame = ctk.CTkFrame(dialog)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            list_label = ctk.CTkLabel(
                list_frame,
                text="Backups",
                font=("Segoe UI", 12, "bold"),
                text_color=("gray70", "gray50"),
            )
            list_label.pack(anchor=tk.W, padx=10, pady=(0, 5))

            # Sorting controls
            sort_var = tk.StringVar(value="Newest")
            sort_options = ["Newest", "Oldest", "Operation", "Description", "Size"]

            sort_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
            sort_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

            ctk.CTkLabel(
                sort_frame,
                text="Sort by:",
                font=("Segoe UI", 10, "bold"),
            ).pack(side=tk.LEFT, padx=(0, 6))

            sort_combo = ctk.CTkComboBox(
                sort_frame,
                values=sort_options,
                variable=sort_var,
                state="readonly",
                width=140,
            )
            sort_combo.pack(side=tk.LEFT)

            scrollable_frame = ctk.CTkScrollableFrame(list_frame)
            scrollable_frame.pack(fill=tk.BOTH, expand=True)
            bind_mousewheel(scrollable_frame)

            backup_items = {}

            def sort_backups(backups):
                selection = sort_var.get()
                if selection == "Oldest":
                    return sorted(backups, key=lambda b: b.timestamp)
                if selection == "Operation":
                    return sorted(
                        backups,
                        key=lambda b: (b.operation or "", b.timestamp),
                        reverse=False,
                    )
                if selection == "Description":
                    return sorted(
                        backups,
                        key=lambda b: (b.description or "", b.timestamp),
                        reverse=False,
                    )
                if selection == "Size":
                    return sorted(backups, key=lambda b: b.file_size, reverse=True)
                # Default "Newest"
                return sorted(backups, key=lambda b: b.timestamp, reverse=True)

            def refresh_list():
                for widget in scrollable_frame.winfo_children():
                    widget.destroy()
                backup_items.clear()

                backups = sort_backups(manager.list_backups())

                if not backups:
                    no_backups_label = ctk.CTkLabel(
                        scrollable_frame,
                        text="No backups found",
                        text_color=("gray70", "gray50"),
                    )
                    no_backups_label.pack(pady=20)
                    return

                for backup in backups:
                    timestamp = (
                        backup.timestamp.split("T")[0]
                        + " "
                        + backup.timestamp.split("T")[1][:8]
                    )
                    size_mb = f"{backup.file_size / (1024 * 1024):.1f} MB"

                    item_frame = ctk.CTkFrame(
                        scrollable_frame,
                        fg_color=("gray86", "gray25"),
                        corner_radius=6,
                    )
                    item_frame.pack(fill=tk.X, padx=5, pady=3)

                    content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
                    content_frame.pack(fill=tk.X, padx=10, pady=8)

                    filename_label = ctk.CTkLabel(
                        content_frame,
                        text=backup.filename,
                        font=("Segoe UI", 10, "bold"),
                        justify=tk.LEFT,
                    )
                    filename_label.pack(anchor=tk.W)

                    info_text = f"Timestamp: {timestamp} | Operation: {backup.operation} | Description: {backup.description} | Size: {size_mb}"
                    info_label = ctk.CTkLabel(
                        content_frame,
                        text=info_text,
                        font=("Segoe UI", 11),
                        text_color=("gray40", "gray70"),
                        justify=tk.LEFT,
                    )
                    info_label.pack(anchor=tk.W, pady=(3, 0))

                    backup_items[backup.filename] = {
                        "frame": item_frame,
                        "backup": backup,
                    }

                    item_frame.bind(
                        "<Button-1>",
                        lambda e, bf=item_frame: select_backup_item(bf),
                    )
                    filename_label.bind(
                        "<Button-1>",
                        lambda e, bf=item_frame: select_backup_item(bf),
                    )
                    info_label.bind(
                        "<Button-1>",
                        lambda e, bf=item_frame: select_backup_item(bf),
                    )

            selected_backup = [None]

            def select_backup_item(frame):
                for backup_name, item_data in backup_items.items():
                    if item_data["frame"] == frame:
                        item_data["frame"].configure(fg_color=("gray70", "gray30"))
                        selected_backup[0] = backup_name
                    else:
                        item_data["frame"].configure(fg_color=("gray86", "gray25"))

            refresh_list()

            # Re-sort when selection changes
            sort_combo.configure(command=lambda _value=None: refresh_list())

            button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            button_frame.pack(fill=tk.X, padx=10, pady=10)

            def create_backup():
                from er_save_manager.ui.utils import force_render_dialog

                dialog_window = ctk.CTkToplevel(dialog)
                dialog_window.title("Create Backup")
                dialog_window.geometry("400x150")
                dialog_window.grab_set()

                dialog_window.update_idletasks()
                x = (dialog_window.winfo_screenwidth() // 2) - 200
                y = (dialog_window.winfo_screenheight() // 2) - 75
                dialog_window.geometry(f"400x150+{x}+{y}")

                # Force rendering on Linux
                force_render_dialog(dialog_window)

                ctk.CTkLabel(
                    dialog_window,
                    text="Enter backup description (optional):",
                    font=("Segoe UI", 11),
                ).pack(pady=10)

                entry = ctk.CTkEntry(dialog_window, width=350)
                entry.pack(pady=5)
                entry.focus()

                result = {"value": None, "confirmed": False}

                def on_confirm():
                    result["value"] = entry.get()
                    result["confirmed"] = True
                    dialog_window.destroy()

                def on_cancel():
                    dialog_window.destroy()

                button_subframe = ctk.CTkFrame(dialog_window, fg_color="transparent")
                button_subframe.pack(pady=10)

                ctk.CTkButton(
                    button_subframe, text="OK", command=on_confirm, width=150
                ).pack(side=tk.LEFT, padx=5)

                ctk.CTkButton(
                    button_subframe, text="Cancel", command=on_cancel, width=150
                ).pack(side=tk.LEFT, padx=5)

                dialog_window.wait_window()

                if result["confirmed"]:
                    try:
                        manager.create_backup(
                            description=result["value"] or "manual",
                            operation="manual_backup",
                            save=save_file,
                        )
                    except Exception as e:
                        CTkMessageBox.showerror(
                            "Error", f"Failed to create backup:\n{str(e)}"
                        )
                        return

                    # Backup created successfully, now try to refresh UI
                    # (don't fail if UI refresh has issues)
                    try:
                        refresh_list()
                        self.update_backup_stats()
                    except Exception as ui_error:
                        print(f"Warning: Failed to refresh UI after backup: {ui_error}")

                    CTkMessageBox.showinfo("Success", "Backup created successfully!")

            def restore_backup():
                if not selected_backup[0]:
                    CTkMessageBox.showwarning(
                        "No Selection", "Please select a backup to restore!"
                    )
                    return

                if not CTkMessageBox.askyesno(
                    "Confirm Restore",
                    f"Restore backup '{selected_backup[0]}'?\n\nCurrent save will be backed up first.",
                ):
                    return

                try:
                    manager.restore_backup(selected_backup[0])
                except Exception as e:
                    CTkMessageBox.showerror(
                        "Error", f"Failed to restore backup:\n{str(e)}"
                    )
                    return

                # Restore succeeded, now try to refresh UI
                # (don't fail if UI refresh has issues)
                try:
                    # Try to reload, but don't fail if it doesn't work
                    if self.reload_save:
                        try:
                            self.reload_save()
                        except Exception as reload_error:
                            print(
                                f"Warning: Failed to reload save after restore: {reload_error}"
                            )

                    refresh_list()
                    self.update_backup_stats()
                except Exception as ui_error:
                    print(f"Warning: Failed to refresh UI after restore: {ui_error}")

                CTkMessageBox.showinfo(
                    "Success",
                    "Backup restored successfully!\n\nPlease reload your save file to see the changes.",
                )

            def delete_backup():
                if not selected_backup[0]:
                    CTkMessageBox.showwarning(
                        "No Selection", "Please select a backup to delete!"
                    )
                    return

                if not CTkMessageBox.askyesno(
                    "Confirm Delete",
                    f"Delete backup '{selected_backup[0]}'?\n\nThis cannot be undone.",
                ):
                    return

                try:
                    manager.delete_backup(selected_backup[0])
                    refresh_list()
                    self.update_backup_stats()
                    CTkMessageBox.showinfo("Success", "Backup deleted successfully!")
                except Exception as e:
                    CTkMessageBox.showerror(
                        "Error", f"Failed to delete backup:\n{str(e)}"
                    )

            def view_details():
                if not selected_backup[0]:
                    CTkMessageBox.showwarning(
                        "No Selection", "Please select a backup to view!"
                    )
                    return

                info = manager.get_backup_info(selected_backup[0])

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

                    CTkMessageBox.showinfo("Backup Details", "\n".join(details))

            ctk.CTkButton(
                button_frame,
                text="Create Backup",
                command=create_backup,
                width=120,
            ).pack(side=tk.LEFT, padx=5)

            ctk.CTkButton(
                button_frame,
                text="Restore",
                command=restore_backup,
                width=120,
            ).pack(side=tk.LEFT, padx=5)

            ctk.CTkButton(
                button_frame,
                text="View Details",
                command=view_details,
                width=120,
            ).pack(side=tk.LEFT, padx=5)

            ctk.CTkButton(
                button_frame,
                text="Delete",
                command=delete_backup,
                width=120,
            ).pack(side=tk.LEFT, padx=5)

            ctk.CTkButton(
                button_frame,
                text="Refresh",
                command=refresh_list,
                width=120,
            ).pack(side=tk.LEFT, padx=5)

            ctk.CTkButton(
                button_frame,
                text="Close",
                command=dialog.destroy,
                width=120,
            ).pack(side=tk.RIGHT, padx=5)

        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to open backup manager:\n{str(e)}"
            )
            import traceback

            traceback.print_exc()
