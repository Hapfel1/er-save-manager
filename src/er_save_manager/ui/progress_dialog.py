"""Progress bar dialog for long-running operations."""

from __future__ import annotations

import customtkinter as ctk


class ProgressDialog:
    """Non-blocking progress dialog with status updates."""

    def __init__(
        self, parent, title: str = "Loading", initial_message: str = "Please wait..."
    ):
        """Create progress dialog.

        Args:
            parent: Parent window
            title: Dialog title
            initial_message: Initial status message
        """
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.resizable(False, False)

        # Center on parent
        self.dialog.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        x = parent_x + (parent_width - 400) // 2
        y = parent_y + (parent_height - 200) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # Make it non-resizable and on top
        self.dialog.grab_set()
        self.dialog.attributes("-topmost", True)

        # Status message
        self.status_label = ctk.CTkLabel(
            self.dialog,
            text=initial_message,
            font=("Segoe UI", 12),
            text_color=("gray40", "gray70"),
        )
        self.status_label.pack(pady=(20, 10), padx=20)

        # Progress bar
        self.progress = ctk.CTkProgressBar(self.dialog, mode="indeterminate")
        self.progress.pack(pady=10, padx=30, fill=ctk.X)
        self.progress.start()

        # Detail label (optional secondary info)
        self.detail_label = ctk.CTkLabel(
            self.dialog,
            text="",
            font=("Segoe UI", 10),
            text_color=("gray60", "gray50"),
        )
        self.detail_label.pack(pady=(5, 20), padx=20)

        # Keep reference to prevent garbage collection
        self.parent = parent

    def update_status(self, message: str, detail: str = ""):
        """Update status message.

        Args:
            message: Main status message
            detail: Optional detail/secondary message
        """
        self.status_label.configure(text=message)
        if detail:
            self.detail_label.configure(text=detail)
        self.dialog.update_idletasks()

    def close(self):
        """Close the progress dialog."""
        try:
            self.progress.stop()
            self.dialog.destroy()
        except Exception:
            pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
