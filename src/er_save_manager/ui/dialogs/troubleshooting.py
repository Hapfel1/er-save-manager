"""Troubleshooting diagnostic dialog."""

from pathlib import Path

import customtkinter as ctk

from er_save_manager.diagnostics.checker import DiagnosticResult, TroubleshootingChecker
from er_save_manager.ui.utils import bind_mousewheel, force_render_dialog


class TroubleshootingDialog:
    """Dialog for running diagnostic checks."""

    def __init__(
        self,
        parent,
        game_folder: Path | None = None,
        save_file_path: Path | None = None,
    ):
        """Initialize troubleshooting dialog."""
        self.parent = parent
        self.game_folder = game_folder
        self.save_file_path = save_file_path

        self.dialog = None
        self.results_frame = None

    def show(self):
        """Show the troubleshooting dialog."""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("Troubleshooting & Diagnostics")
        self.dialog.geometry("700x600")
        self.dialog.transient(self.parent)

        force_render_dialog(self.dialog)

        # Center dialog over parent window
        dialog_width = 700
        dialog_height = 600

        # Ensure parent window geometry is updated
        self.parent.update_idletasks()
        self.dialog.update_idletasks()

        # Get parent window position and size
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        # Calculate center position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        # Ensure dialog doesn't go off-screen
        x = max(0, x)
        y = max(0, y)

        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        self.dialog.grab_set()

        # Main content
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            title_frame,
            text="Troubleshooting & Diagnostics",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        ctk.CTkButton(
            title_frame,
            text="Refresh",
            command=self._run_checks,
            width=100,
        ).pack(side="right")

        # Results scrollable frame
        self.results_frame = ctk.CTkScrollableFrame(main_frame, corner_radius=8)
        self.results_frame.pack(fill=ctk.BOTH, expand=True, pady=(0, 10))
        bind_mousewheel(self.results_frame)

        # Close button
        ctk.CTkButton(
            main_frame,
            text="Close",
            command=self.dialog.destroy,
            width=100,
        ).pack(pady=(5, 0))

        # Run initial checks
        self._run_checks()

    def _run_checks(self):
        """Run all diagnostic checks and display results."""
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        # Show loading message
        loading_label = ctk.CTkLabel(
            self.results_frame,
            text="Running diagnostic checks...",
            font=("Segoe UI", 12),
        )
        loading_label.pack(pady=20)

        # Force update to show loading message
        self.results_frame.update_idletasks()

        # Run checks
        checker = TroubleshootingChecker(
            game_folder=self.game_folder,
            save_file_path=self.save_file_path,
        )
        results = checker.run_all_checks()

        # Remove loading message
        loading_label.destroy()

        # Display results
        for result in results:
            self._create_result_widget(result)

    def _create_result_widget(self, result: DiagnosticResult):
        """Create a widget to display a diagnostic result."""
        # Container frame for each result
        result_frame = ctk.CTkFrame(self.results_frame, corner_radius=8)
        result_frame.pack(fill="x", padx=5, pady=5)

        # Status indicator and name
        header_frame = ctk.CTkFrame(result_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=12, pady=(10, 5))

        # Status icon based on result
        status_icons = {
            "ok": "✅",
            "warning": "⚠️",
            "error": "❌",
            "info": "ℹ️",
        }

        status_colors = {
            "ok": ("green", "lightgreen"),
            "warning": ("orange", "yellow"),
            "error": ("red", "salmon"),
            "info": ("gray", "lightgray"),
        }

        icon = status_icons.get(result.status, "ℹ️")
        color = status_colors.get(result.status, ("gray", "lightgray"))

        # Status icon
        ctk.CTkLabel(
            header_frame,
            text=icon,
            font=("Segoe UI", 14),
        ).pack(side="left", padx=(0, 8))

        # Name
        ctk.CTkLabel(
            header_frame,
            text=result.name,
            font=("Segoe UI", 12, "bold"),
            text_color=color,
        ).pack(side="left")

        # Message
        ctk.CTkLabel(
            result_frame,
            text=result.message,
            font=("Segoe UI", 11),
            wraplength=620,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 5))

        # Fix action if available
        if result.fix_available and result.fix_action:
            fix_frame = ctk.CTkFrame(
                result_frame, fg_color=("gray85", "gray25"), corner_radius=6
            )
            fix_frame.pack(fill="x", padx=12, pady=(5, 10))

            ctk.CTkLabel(
                fix_frame,
                text="💡 Suggested Fix:",
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w", padx=8, pady=(5, 2))

            ctk.CTkLabel(
                fix_frame,
                text=result.fix_action,
                font=("Segoe UI", 10),
                wraplength=590,
                justify="left",
            ).pack(anchor="w", padx=8, pady=(0, 5))
