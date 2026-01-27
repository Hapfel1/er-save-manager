"""Backup pruning warning dialog (customtkinter version)."""

import customtkinter as ctk

from er_save_manager.backup.manager import BackupMetadata
from er_save_manager.ui.settings import get_settings


class BackupPruningWarningDialog(ctk.CTkToplevel):
    """Dialog warning user about backups that will be pruned (customtkinter version)."""

    def __init__(
        self,
        parent: ctk.CTk,
        pruned_backups: list[BackupMetadata],
        max_backups: int,
    ):
        """Initialize backup pruning warning dialog.

        Args:
            parent: Parent window
            pruned_backups: List of backups that will be pruned
            max_backups: Maximum backups setting
        """
        super().__init__(parent)
        self.title("Backup Limit Reached")
        self.geometry("500x400")
        self.resizable(True, True)
        self.pruned_backups = pruned_backups
        self.max_backups = max_backups
        self.dont_show_again_var = ctk.BooleanVar(value=False)

        # Center on parent
        self.transient(parent)

        # Force rendering on Linux before grab_set
        from er_save_manager.ui.utils import force_render_dialog
        force_render_dialog(self)
        self.grab_set()

        # Handle window close button
        self.protocol("WM_DELETE_WINDOW", self._on_ok)

        self._setup_ui()

        # Force update to ensure window appears
        self.update_idletasks()

    def _setup_ui(self):
        """Setup UI components."""
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Title label
        title_label = ctk.CTkLabel(
            main_frame,
            text="Backup Limit Reached",
            font=("Segoe UI", 12, "bold"),
        )
        title_label.pack(anchor="w", pady=(0, 10))

        # Description label
        desc_text = f"You have reached the maximum number of backups ({self.max_backups}). The following old backups will be permanently deleted:"
        desc_label = ctk.CTkLabel(
            main_frame, text=desc_text, wraplength=480, justify="left"
        )
        desc_label.pack(anchor="w", pady=(0, 10))

        # Backups list with scrollbar
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Create scrollable frame for backups
        from er_save_manager.ui.utils import bind_mousewheel

        scrollable_list = ctk.CTkScrollableFrame(list_frame)
        scrollable_list.pack(fill="both", expand=True)

        # Bind mousewheel for scrolling on Linux and other platforms
        bind_mousewheel(scrollable_list)

        # Populate with backup info
        for backup in self.pruned_backups:
            timestamp = backup.timestamp[:10]  # Just the date part
            display_text = f"{backup.filename} ({timestamp})"
            label = ctk.CTkLabel(
                scrollable_list,
                text=display_text,
                text_color=("gray40", "gray70"),
                font=("Segoe UI", 11),
                justify="left",
            )
            label.pack(anchor="w", padx=10, pady=4)

        # Don't show again checkbox
        checkbox = ctk.CTkCheckBox(
            main_frame,
            text="Don't show this warning again",
            variable=self.dont_show_again_var,
        )
        checkbox.pack(anchor="w", pady=(0, 10))

        # Button frame
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        ok_button = ctk.CTkButton(button_frame, text="OK", command=self._on_ok)
        ok_button.pack(side="right", padx=(5, 0))

        # Bind Enter key
        self.bind("<Return>", lambda e: self._on_ok())

    def _on_ok(self):
        """Handle OK button click."""
        dont_show = self.dont_show_again_var.get()
        if dont_show:
            settings = get_settings()
            settings["show_backup_pruning_warning"] = False
            settings.save()

        self.destroy()

    def show(self):
        """Show dialog and return dont_show_again status."""
        self.wait_window()
        return self.dont_show_again_var.get()
