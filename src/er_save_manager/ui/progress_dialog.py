"""Progress bar dialog for long-running operations."""

from __future__ import annotations

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds


class ProgressDialog:
    """Non-blocking progress dialog with status updates."""

    def __init__(
        self, parent, title: str = "Loading", initial_message: str = "Wait..."
    ):
        """Create progress dialog.

        Args:
            parent: Parent window
            title: Dialog title
            initial_message: Initial status message
        """
        self.dialog = ds.create(parent, title)
        self.dialog.attributes("-topmost", True)
        main = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main.pack(fill=ctk.BOTH, expand=True, padx=20, pady=16)

        self.status_label = ctk.CTkLabel(
            main,
            text=initial_message,
            font=ds.BOLD,
            anchor="w",
            justify="left",
            wraplength=360,
        )
        self.status_label.pack(fill=ctk.X)

        self.progress = ctk.CTkProgressBar(main, mode="indeterminate", width=360)
        self.progress.pack(fill=ctk.X, pady=(10, 8))
        self.progress.start()

        # Secondary line, empty until update_status() passes a detail
        self.detail_label = ctk.CTkLabel(
            main,
            text="",
            font=ds.SMALL,
            text_color=ds.MUTED,
            anchor="w",
            justify="left",
            wraplength=360,
        )
        self.detail_label.pack(fill=ctk.X)

        ds.finish(self.dialog, parent, min_width=400)

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
