"""Bookmarks Panel Widget - Shows and manages bookmarks."""

from tkinter import ttk

import customtkinter as ctk


class BookmarksPanel(ctk.CTkFrame):
    """Panel showing bookmarks with add/remove/navigate functionality."""

    def __init__(self, parent, bookmarks_manager, on_bookmark_click=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.bookmarks_manager = bookmarks_manager
        self.on_bookmark_click = on_bookmark_click

        self._setup_ui()

    def _setup_ui(self):
        """Create the bookmarks panel UI."""
        # Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            title_frame,
            text="Bookmarks",
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")

        # Button controls
        btn_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        btn_frame.pack(side="right")

        ctk.CTkButton(
            btn_frame,
            text="Add",
            width=50,
            height=24,
            font=("Segoe UI", 9),
            command=self._on_add_bookmark,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame,
            text="Remove",
            width=60,
            height=24,
            font=("Segoe UI", 9),
            command=self._on_remove_bookmark,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame,
            text="Clear",
            width=50,
            height=24,
            font=("Segoe UI", 9),
            command=self._on_clear_bookmarks,
        ).pack(side="left", padx=2)

        # Bookmarks list
        list_frame = ctk.CTkFrame(self, fg_color=("gray95", "gray10"))
        list_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        # Style for the listbox
        appearance = ctk.get_appearance_mode()
        if appearance == "Dark":
            bg_color = "#1a1a1a"
            fg_color = "#e0e0e0"
            select_bg = "#264F78"
            select_fg = "#ffffff"
        else:
            bg_color = "#ffffff"
            fg_color = "#1a1a1a"
            select_bg = "#0078D7"
            select_fg = "#ffffff"

        style = ttk.Style()
        style.configure(
            "Bookmarks.Treeview",
            background=bg_color,
            foreground=fg_color,
            fieldbackground=bg_color,
            borderwidth=0,
            font=("Consolas", 9),
        )
        style.map(
            "Bookmarks.Treeview",
            background=[("selected", select_bg)],
            foreground=[("selected", select_fg)],
        )

        # Treeview for bookmarks
        self.tree = ttk.Treeview(
            list_frame,
            columns=("offset", "name", "annotation"),
            show="tree headings",
            style="Bookmarks.Treeview",
            yscrollcommand=scrollbar.set,
            selectmode="browse",
        )

        self.tree.heading("#0", text="")
        self.tree.heading("offset", text="Offset")
        self.tree.heading("name", text="Name")
        self.tree.heading("annotation", text="Note")

        self.tree.column("#0", width=20, minwidth=20, stretch=False)
        self.tree.column("offset", width=80, minwidth=60)
        self.tree.column("name", width=120, minwidth=80)
        self.tree.column("annotation", width=150, minwidth=100)

        self.tree.pack(fill="both", expand=True, padx=2, pady=2)
        scrollbar.configure(command=self.tree.yview)

        # Bind events
        self.tree.bind("<Double-Button-1>", self._on_tree_double_click)

    def refresh_bookmarks(self):
        """Refresh the bookmarks display."""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add bookmarks
        for bookmark in self.bookmarks_manager.get_all_bookmarks():
            # Create colored indicator
            self.tree.insert(
                "",
                "end",
                text="●",
                values=(
                    f"0x{bookmark.offset:08X}",
                    bookmark.name,
                    bookmark.annotation[:50]
                    + ("..." if len(bookmark.annotation) > 50 else ""),
                ),
                tags=(f"color_{bookmark.color}",),
            )

            # Configure tag color
            self.tree.tag_configure(
                f"color_{bookmark.color}", foreground=bookmark.color
            )

    def _on_add_bookmark(self):
        """Show dialog to add bookmark."""
        if self.on_bookmark_click:
            self.on_bookmark_click("add", None)

    def _on_remove_bookmark(self):
        """Remove selected bookmark."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        offset_str = self.tree.set(item, "offset")

        try:
            offset = int(offset_str, 16)
            self.bookmarks_manager.remove_bookmark(offset)
            self.bookmarks_manager.save_bookmarks()
            self.refresh_bookmarks()
        except ValueError:
            pass

    def _on_clear_bookmarks(self):
        """Clear all bookmarks."""
        self.bookmarks_manager.clear_bookmarks()
        self.bookmarks_manager.save_bookmarks()
        self.refresh_bookmarks()

    def _on_tree_double_click(self, event):
        """Handle double-click on bookmark to navigate."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        offset_str = self.tree.set(item, "offset")

        try:
            offset = int(offset_str, 16)
            if self.on_bookmark_click:
                self.on_bookmark_click("navigate", offset)
        except ValueError:
            pass
