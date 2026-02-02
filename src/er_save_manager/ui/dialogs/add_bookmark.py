"""Add Bookmark Dialog."""

import tkinter as tk

import customtkinter as ctk


class AddBookmarkDialog(ctk.CTkToplevel):
    """Dialog for adding or editing a bookmark."""

    def __init__(
        self, parent, bookmarks_manager, current_offset=0, existing_bookmark=None
    ):
        super().__init__(parent)

        self.bookmarks_manager = bookmarks_manager
        self.current_offset = current_offset
        self.existing_bookmark = existing_bookmark
        self.result = None

        self.title("Add Bookmark" if not existing_bookmark else "Edit Bookmark")
        self.geometry("450x300")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        self._setup_ui()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Focus name entry
        self.name_entry.focus()

    def _setup_ui(self):
        """Create dialog UI."""
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Offset
        ctk.CTkLabel(
            main_frame,
            text="Offset:",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.offset_var = tk.StringVar(
            value=f"0x{self.current_offset:08X}"
            if not self.existing_bookmark
            else f"0x{self.existing_bookmark.offset:08X}"
        )
        offset_entry = ctk.CTkEntry(
            main_frame,
            textvariable=self.offset_var,
            font=("Consolas", 11),
            width=200,
        )
        offset_entry.grid(row=0, column=1, sticky="w", pady=(0, 10))

        # Name
        ctk.CTkLabel(
            main_frame,
            text="Name:",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=1, column=0, sticky="w", pady=(0, 10))

        self.name_var = tk.StringVar(
            value="" if not self.existing_bookmark else self.existing_bookmark.name
        )
        self.name_entry = ctk.CTkEntry(
            main_frame,
            textvariable=self.name_var,
            font=("Segoe UI", 11),
            width=300,
            placeholder_text="e.g., Character Name",
        )
        self.name_entry.grid(row=1, column=1, sticky="w", pady=(0, 10))
        self.name_entry.bind("<Return>", lambda e: self._on_ok())

        # Annotation
        ctk.CTkLabel(
            main_frame,
            text="Note:",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=2, column=0, sticky="nw", pady=(0, 10))

        self.annotation_text = ctk.CTkTextbox(
            main_frame,
            font=("Segoe UI", 10),
            width=300,
            height=80,
        )
        self.annotation_text.grid(row=2, column=1, sticky="w", pady=(0, 10))

        if self.existing_bookmark and self.existing_bookmark.annotation:
            self.annotation_text.insert("1.0", self.existing_bookmark.annotation)

        # Color picker
        ctk.CTkLabel(
            main_frame,
            text="Color:",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=3, column=0, sticky="w", pady=(0, 10))

        color_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        color_frame.grid(row=3, column=1, sticky="w", pady=(0, 10))

        self.color_var = tk.StringVar(
            value="#FFD700"
            if not self.existing_bookmark
            else self.existing_bookmark.color
        )

        colors = [
            ("#FFD700", "Gold"),
            ("#FF6B6B", "Red"),
            ("#4ECDC4", "Cyan"),
            ("#95E1D3", "Green"),
            ("#F38181", "Pink"),
            ("#AA96DA", "Purple"),
        ]

        for i, (color, _name) in enumerate(colors):
            btn = ctk.CTkButton(
                color_frame,
                text="",
                width=30,
                height=30,
                fg_color=color,
                hover_color=color,
                command=lambda c=color: self.color_var.set(c),
            )
            btn.grid(row=0, column=i, padx=2)

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))

        ctk.CTkButton(
            button_frame,
            text="OK",
            width=100,
            command=self._on_ok,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=100,
            command=self._on_cancel,
        ).pack(side="left", padx=5)

    def _on_ok(self):
        """Handle OK button."""
        # Validate
        name = self.name_var.get().strip()
        if not name:
            return

        offset_str = self.offset_var.get().strip()
        try:
            if offset_str.startswith("0x"):
                offset = int(offset_str, 16)
            else:
                offset = int(offset_str)
        except ValueError:
            return

        annotation = self.annotation_text.get("1.0", "end-1c").strip()
        color = self.color_var.get()

        # Add bookmark
        self.bookmarks_manager.add_bookmark(offset, name, annotation, color)
        self.bookmarks_manager.save_bookmarks()

        self.result = (offset, name, annotation, color)
        self.destroy()

    def _on_cancel(self):
        """Handle Cancel button."""
        self.result = None
        self.destroy()
